"""End-to-end: question -> cited Answer."""

import re
import time

from threatlens import guard
from threatlens.config import settings
from threatlens.llm import router
from threatlens.llm.client import complete
from threatlens.llm.prompts import build_messages
from threatlens.retrieval.hybrid import get_retriever
from threatlens.retrieval.translate import english_variant
from threatlens.schema import Answer, Chunk, RetrievedChunk

_CVE = re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.I)


def _nvd_fallback(question: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """If the question names a CVE that retrieval didn't find, fetch it live from NVD."""
    from threatlens.ingest.nvd import fetch_cve

    have = {c.chunk.doc_id.split(":", 1)[1].upper() for c in chunks}
    extra = []
    for cve in {m.upper() for m in _CVE.findall(question)} - have:
        try:
            doc = fetch_cve(cve)
        except Exception:
            continue
        if doc:
            ch = Chunk(
                chunk_id=f"{doc.id}#0",
                doc_id=doc.id,
                source=doc.source,
                title=doc.title,
                text=doc.text,
                url=doc.url,
                metadata=doc.metadata,
            )
            extra.append(RetrievedChunk(ch, 1.0, "nvd"))
    return extra + chunks


def retrieve(
    question: str, expand: bool | None = None, top_k: int | None = None
) -> list[RetrievedChunk]:
    """Hybrid search + fused rerank, plus two graph steps when `expand` (default: settings):

    - **link expansion** (pasted alerts / command lines only): the ATT&CK techniques tagged by
      the Sigma rules among the candidates take the last `graph_top_n` places of the context.
      A raw command line matches detection rules far better than a technique description, and
      the cross-encoder agrees with the retrievers; the rules' own tags lead to the technique.
      Reserved places instead of a re-ranking, so prose questions are untouched.
    - **exact lookup**: documents whose id the question names (CVE, technique, advisory, rule)
      are put first, whatever the retrievers ranked.

    French questions are additionally searched in English (retrieval.translate).
    """
    expand = settings.graph_expansion if expand is None else expand
    top_k = top_k or settings.top_k_final
    r = get_retriever()
    # a French question is also searched in English; the reranker then reads the English wording
    english = english_variant(question)
    cands = r.search(question, settings.top_k_retrieve, also=english)
    if settings.use_reranker:
        from threatlens.retrieval.rerank import rerank

        out = rerank(english or question, cands, len(cands))
    else:
        out = cands
    if not expand:
        return out[:top_k]

    linked: list[RetrievedChunk] = []
    if router.looks_like_log(question):
        votes = r.graph.technique_votes([c.chunk.doc_id for c in cands])[: settings.graph_top_n]
        linked = [RetrievedChunk(r.doc(d), score, "graph") for d, score in votes]
    named = [RetrievedChunk(r.doc(d), 1.0, "lookup") for d in r.graph.ids_in(question)]
    taken = {c.chunk.doc_id for c in named + linked}
    keep = [c for c in out if c.chunk.doc_id not in taken]
    return named + keep[: max(top_k - len(named) - len(linked), 0)] + linked


def answer(question: str, force_model: str | None = None, mode: str | None = None) -> Answer:
    """mode: "pipeline" (fixed chain below) or "agent" (the model picks tools); default settings."""
    if (mode or settings.answer_mode) == "agent":
        from threatlens import agent

        return agent.answer(question, force_model=force_model)
    t0 = time.perf_counter()
    flags = guard.check_query(question)

    chunks = _nvd_fallback(question, retrieve(question))
    chunks, doc_flags = guard.sanitize_chunks(chunks)
    flags += doc_flags

    model, reason = (force_model, "forced") if force_model else router.route(question, chunks)
    res = complete(model, build_messages(question, chunks))

    flags += guard.check_citations(res.text, {c.chunk.doc_id for c in chunks})
    return Answer(
        answer=res.text,
        citations=chunks,
        model=res.model,
        route_reason=reason,
        cost_usd=res.cost_usd,
        latency_ms=int((time.perf_counter() - t0) * 1000),
        guard_flags=flags,
    )
