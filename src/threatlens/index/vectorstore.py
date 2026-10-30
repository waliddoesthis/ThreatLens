"""Dense vector store behind one small interface: Qdrant (default) or Chroma.

Select with VECTOR_STORE=qdrant|chroma. Both run embedded, storing under data/index/<name>/.
Point ids are chunk positions in data/index/chunks.jsonl, so either store plugs into
the same BM25 + RRF code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import numpy as np

from threatlens.config import settings
from threatlens.index import COLLECTION


class VectorStore(Protocol):
    def reset(self, dim: int) -> None: ...
    def add(self, ids: list[int], vectors: np.ndarray) -> None: ...
    def search(self, vector: np.ndarray, k: int) -> list[int]: ...
    def close(self) -> None: ...


class QdrantStore:
    def __init__(self, path: Path) -> None:
        from qdrant_client import QdrantClient

        self.client = QdrantClient(path=str(path))

    def reset(self, dim: int) -> None:
        from qdrant_client import models

        if self.client.collection_exists(COLLECTION):
            self.client.delete_collection(COLLECTION)
        self.client.create_collection(
            COLLECTION,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
        )

    def add(self, ids: list[int], vectors: np.ndarray) -> None:
        from qdrant_client import models

        self.client.upsert(
            COLLECTION,
            points=[
                models.PointStruct(id=i, vector=v.tolist())
                for i, v in zip(ids, vectors, strict=True)
            ],
        )

    def search(self, vector: np.ndarray, k: int) -> list[int]:
        res = self.client.query_points(COLLECTION, query=vector.tolist(), limit=k)
        return [int(p.id) for p in res.points]

    def close(self) -> None:
        self.client.close()


class ChromaStore:
    def __init__(self, path: Path) -> None:
        import chromadb

        self.client = chromadb.PersistentClient(path=str(path))
        self.col = None

    def _col(self):
        if self.col is None:
            self.col = self.client.get_collection(COLLECTION)
        return self.col

    def reset(self, dim: int) -> None:
        if COLLECTION in [c.name for c in self.client.list_collections()]:
            self.client.delete_collection(COLLECTION)
        # cosine to match Qdrant (Chroma defaults to L2). Qdrant's local mode searches exactly;
        # Chroma's HNSW is approximate and at ef_search=100 missed true neighbours (dense
        # R@5 0.886 vs 0.914), so search wider.
        self.col = self.client.create_collection(
            COLLECTION, configuration={"hnsw": {"space": "cosine", "ef_search": 200}}
        )

    def add(self, ids: list[int], vectors: np.ndarray) -> None:
        self._col().add(ids=[str(i) for i in ids], embeddings=vectors.tolist())

    def search(self, vector: np.ndarray, k: int) -> list[int]:
        res = self._col().query(query_embeddings=[vector.tolist()], n_results=k)
        return [int(i) for i in res["ids"][0]]

    def close(self) -> None:
        pass  # PersistentClient writes through; nothing to flush


STORES = {"qdrant": QdrantStore, "chroma": ChromaStore}


def get_store(name: str | None = None) -> VectorStore:
    name = name or settings.vector_store
    if name not in STORES:
        raise ValueError(f"VECTOR_STORE must be one of {sorted(STORES)}, got {name!r}")
    return STORES[name](settings.index_dir / name)
