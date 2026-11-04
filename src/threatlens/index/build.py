"""Build the dense (Qdrant local) and sparse (BM25) indexes.

python -m threatlens.index.build [--sparse-only]
Outputs in data/index/: chunks.jsonl, bm25.pkl, and qdrant/ or chroma/ (VECTOR_STORE)
"""

import argparse
import json
import pickle
import shutil
from dataclasses import asdict

from rank_bm25 import BM25Okapi
from tqdm import tqdm

from threatlens.chunking import chunk_document
from threatlens.config import settings
from threatlens.index import embedding_prefixes, tokenize
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


def build(sparse_only: bool = False) -> None:
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
    if sparse_only:
        return

    from sentence_transformers import SentenceTransformer

    from threatlens.index.vectorstore import get_store

    # Dense
    model = SentenceTransformer(settings.embedding_model)
    # start from an empty folder: a collection reset alone left stale points behind on Windows,
    # so the store held more vectors than chunks.jsonl and dense search returned dead ids
    shutil.rmtree(out / settings.vector_store, ignore_errors=True)
    store = get_store()
    store.reset(model.get_sentence_embedding_dimension())
    batch = 256
    passage_prefix = embedding_prefixes(settings.embedding_model)[1]
    for i in tqdm(range(0, len(chunks), batch), desc=f"embedding -> {settings.vector_store}"):
        part = chunks[i : i + batch]
        vecs = model.encode([passage_prefix + c.text for c in part], normalize_embeddings=True)
        store.add(list(range(i, i + len(part))), vecs)
    store.close()
    meta = {
        "embedding_model": settings.embedding_model,
        "chunk_size_words": settings.chunk_size_words,
        "chunk_overlap_words": settings.chunk_overlap_words,
        "vector_store": settings.vector_store,
        "n_chunks": len(chunks),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    print("Dense index done")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--sparse-only", action="store_true", help="BM25 only, no embedding model")
    build(p.parse_args().sparse_only)
