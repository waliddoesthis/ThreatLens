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
    query: str, candidates: list[RetrievedChunk], top_k: int, fuse: bool | None = None
) -> list[RetrievedChunk]:
    """Rerank with the cross-encoder.

    fuse=True (default from settings) RRF-fuses the cross-encoder order with the incoming
    hybrid order instead of replacing it: the cross-encoder alone over-promotes narrow Sigma
    rules over the ATT&CK technique a question is about (see docs/DECISIONS.md).
    """
    if not candidates:
        return []
    fuse = settings.rerank_fusion if fuse is None else fuse
    scores = [float(s) for s in _model().predict([(query, c.chunk.text) for c in candidates])]
    ce_order = sorted(range(len(candidates)), key=lambda i: scores[i], reverse=True)
    order = [i for i, _ in rrf([list(range(len(candidates))), ce_order])] if fuse else ce_order
    return [RetrievedChunk(candidates[i].chunk, scores[i], "rerank") for i in order[:top_k]]
