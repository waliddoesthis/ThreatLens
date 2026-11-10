"""End-to-end: question -> cited Answer."""

import re
import time

from threatlens import guard
from threatlens.config import settings
from threatlens.llm import router
from threatlens.llm.client import complete
from threatlens.llm.prompts import build_messages
from threatlens.retrieval.hybrid import get_retriever
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


def retrieve(question: str, expand: bool | None = None) -> list[RetrievedChunk]:
    """Hybrid search + rerank, plus two graph steps when `expand` (default: settings):

    - **link expansion**: ATT&CK techniques tagged by the Sigma rules among the candidates join
      the candidate pool, and their vote order is fused into the final ranking. A raw command
      line matches detection rules far better than a technique description; the rules' own
      tags lead to the technique.
    - **exact lookup**: documents whose id the question names (CVE, technique, advisory, rule)
      are put first, whatever the retrievers ranked.
    """
    expand = settings.graph_expansion if expand is None else expand
    r = get_retriever()
    cands = r.search(question, settings.top_k_retrieve)
    extra_order: list[int] | None = None
    if expand:
        have = {c.chunk.doc_id for c in cands}
        votes = r.graph.technique_votes([c.chunk.doc_id for c in cands])[: settings.graph_top_n]
        cands = cands + [
            RetrievedChunk(r.doc(d), score, "graph") for d, score in votes if d not in have
        ]
        pos = {c.chunk.doc_id: i for i, c in reversed(list(enumerate(cands)))}
        extra_order = [pos[d] for d, _ in votes]
    if settings.use_reranker:
        from threatlens.retrieval.rerank import rerank

        out = rerank(question, cands, settings.top_k_final, extra_order=extra_order)
    else:
        out = cands[: settings.top_k_final]
    if expand:
        named = [r.doc(d) for d in r.graph.ids_in(question)]
        ids = {c.doc_id for c in named}
        out = [RetrievedChunk(c, 1.0, "lookup") for c in named] + [
            c for c in out if c.chunk.doc_id not in ids
        ]
    return out


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

    return Answer(
        answer=res.text,
        citations=chunks,
        model=res.model,
        route_reason=reason,
        cost_usd=res.cost_usd,
        latency_ms=int((time.perf_counter() - t0) * 1000),
        guard_flags=flags,
    )
