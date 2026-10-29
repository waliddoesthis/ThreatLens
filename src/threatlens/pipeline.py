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


def retrieve(question: str) -> list[RetrievedChunk]:
    cands = get_retriever().search(question, settings.top_k_retrieve)
    if settings.use_reranker:
        from threatlens.retrieval.rerank import rerank

        return rerank(question, cands, settings.top_k_final)
    return cands[: settings.top_k_final]


def answer(question: str, force_model: str | None = None) -> Answer:
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
