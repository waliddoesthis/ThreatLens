"""Build the dense (Qdrant local) and sparse (BM25) indexes.

python -m threatlens.index.build
Outputs in data/index/: chunks.jsonl, bm25.pkl, qdrant/
"""

import json
import pickle
from dataclasses import asdict

from rank_bm25 import BM25Okapi
from tqdm import tqdm

from threatlens.chunking import chunk_document
from threatlens.config import settings
from threatlens.index import COLLECTION, tokenize
from threatlens.schema import Chunk, read_jsonl


def load_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []
    files = sorted(settings.processed_dir.glob("*.jsonl"))
    if not files:
        raise SystemExit("No processed data. Run `make ingest` first.")
    for f in files:
        for doc in read_jsonl(f):
            chunks += chunk_document(doc, settings.chunk_size_words, settings.chunk_overlap_words)
    return chunks


def build() -> None:
    from qdrant_client import QdrantClient, models
    from sentence_transformers import SentenceTransformer

    out = settings.index_dir
    out.mkdir(parents=True, exist_ok=True)
    chunks = load_chunks()
    print(f"{len(chunks)} chunks")

    with (out / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")

    # Sparse
    bm25 = BM25Okapi([tokenize(f"{c.title} {c.text}") for c in chunks])
    with (out / "bm25.pkl").open("wb") as f:
        pickle.dump(bm25, f)
    print("BM25 index done")

    # Dense
    model = SentenceTransformer(settings.embedding_model)
    dim = model.get_sentence_embedding_dimension()
    client = QdrantClient(path=str(out / "qdrant"))
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    client.create_collection(
        COLLECTION, vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE)
    )
    batch = 256
    for i in tqdm(range(0, len(chunks), batch), desc="embedding"):
        part = chunks[i : i + batch]
        vecs = model.encode([c.text for c in part], normalize_embeddings=True)
        client.upsert(
            COLLECTION,
            points=[
                models.PointStruct(id=i + j, vector=v.tolist(), payload={"chunk_id": c.chunk_id})
                for j, (c, v) in enumerate(zip(part, vecs, strict=True))
            ],
        )
    client.close()
    print("Dense index done")


if __name__ == "__main__":
    build()
