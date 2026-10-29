"""Cross-encoder reranking of the fused candidates."""

from functools import lru_cache

from threatlens.config import settings
from threatlens.schema import RetrievedChunk


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(settings.reranker_model)


def rerank(query: str, candidates: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    if not candidates:
        return []
    scores = _model().predict([(query, c.chunk.text) for c in candidates])
    ranked = sorted(zip(candidates, scores, strict=True), key=lambda x: float(x[1]), reverse=True)[
        :top_k
    ]
    return [RetrievedChunk(c.chunk, float(s), "rerank") for c, s in ranked]
