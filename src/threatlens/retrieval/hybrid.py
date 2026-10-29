"""Hybrid retrieval: BM25 + dense, fused with Reciprocal Rank Fusion."""

from __future__ import annotations

import json
import pickle
from functools import lru_cache

import numpy as np

from threatlens.config import settings
from threatlens.index import COLLECTION, tokenize
from threatlens.schema import Chunk, RetrievedChunk


def rrf(rankings: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion. rankings = lists of item ids, best first."""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


class HybridRetriever:
    def __init__(self) -> None:
        from qdrant_client import QdrantClient
        from sentence_transformers import SentenceTransformer

        idx = settings.index_dir
        with (idx / "chunks.jsonl").open(encoding="utf-8") as f:
            self.chunks = [Chunk(**json.loads(line)) for line in f]
        with (idx / "bm25.pkl").open("rb") as f:
            self.bm25 = pickle.load(f)
        self.encoder = SentenceTransformer(settings.embedding_model)
        self.qdrant = QdrantClient(path=str(idx / "qdrant"))

    def bm25_search(self, query: str, k: int) -> list[int]:
        scores = self.bm25.get_scores(tokenize(query))
        top = np.argsort(scores)[::-1][:k]
        return [int(i) for i in top if scores[i] > 0]

    def dense_search(self, query: str, k: int) -> list[int]:
        # bge models recommend this instruction prefix for queries
        qv = self.encoder.encode(
            "Represent this sentence for searching relevant passages: " + query,
            normalize_embeddings=True,
        )
        res = self.qdrant.query_points(COLLECTION, query=qv.tolist(), limit=k)
        return [int(p.id) for p in res.points]

    def search(
        self, query: str, k: int | None = None, mode: str = "hybrid"
    ) -> list[RetrievedChunk]:
        k = k or settings.top_k_retrieve
        if mode == "bm25":
            ids = self.bm25_search(query, k)
            return [
                RetrievedChunk(self.chunks[i], 1.0 / (r + 1), "bm25") for r, i in enumerate(ids)
            ]
        if mode == "dense":
            ids = self.dense_search(query, k)
            return [
                RetrievedChunk(self.chunks[i], 1.0 / (r + 1), "dense") for r, i in enumerate(ids)
            ]
        fused = rrf([self.bm25_search(query, k), self.dense_search(query, k)])[:k]
        return [RetrievedChunk(self.chunks[i], s, "hybrid") for i, s in fused]


@lru_cache(maxsize=1)
def get_retriever() -> HybridRetriever:
    return HybridRetriever()
