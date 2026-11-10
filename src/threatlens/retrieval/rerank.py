"""Cross-encoder reranking of the fused candidates."""

from functools import lru_cache

from threatlens.config import settings
from threatlens.retrieval.hybrid import rrf
from threatlens.schema import RetrievedChunk


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(settings.reranker_model)


def rerank(
    query: str,
    candidates: list[RetrievedChunk],
    top_k: int,
    fuse: bool | None = None,
    extra_order: list[int] | None = None,
) -> list[RetrievedChunk]:
    """Rerank with the cross-encoder.

    fuse=True (default from settings) RRF-fuses the cross-encoder order with the incoming
    hybrid order instead of replacing it: the cross-encoder alone over-promotes narrow Sigma
    rules over the ATT&CK technique a question is about (see docs/DECISIONS.md).

    extra_order is an optional third ranking (candidate indexes, best first) to fuse in, used
    for the techniques that the candidates' Sigma rules point to.
    """
    if not candidates:
        return []
    fuse = settings.rerank_fusion if fuse is None else fuse
    scores = [float(s) for s in _model().predict([(query, c.chunk.text) for c in candidates])]
    ce_order = sorted(range(len(candidates)), key=lambda i: scores[i], reverse=True)
    if fuse:
        rankings = [list(range(len(candidates))), ce_order] + ([extra_order] if extra_order else [])
        order = [i for i, _ in rrf(rankings)]
    else:
        order = ce_order
    return [RetrievedChunk(candidates[i].chunk, scores[i], "rerank") for i in order[:top_k]]
