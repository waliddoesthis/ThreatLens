"""Chunk-size and embedding-model ablations.

Each config gets its own index under data/index-ablation/<name>/ (built once, reused when its
meta.json matches), then dense / hybrid / hybrid+rerank+rrf are scored on the benchmark.

python eval/run_ablation.py [--only chunk|embedding]  ->  eval/results/ablation.md (+ .json)
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from run_retrieval_eval import evaluate, load_questions, usable_questions  # noqa: E402

from threatlens.config import settings  # noqa: E402
from threatlens.index.build import build  # noqa: E402
from threatlens.retrieval import hybrid  # noqa: E402

HERE = Path(__file__).parent
MODES = ["dense", "hybrid", "hybrid+rerank+rrf"]
DEFAULT = {"embedding_model": "BAAI/bge-small-en-v1.5", "chunk_size_words": 220,
           "chunk_overlap_words": 40}  # fmt: skip
# overlap kept at ~18% of the window so only the size changes
CHUNK = [
    {"chunk_size_words": 120, "chunk_overlap_words": 20},
    {},
    {"chunk_size_words": 400, "chunk_overlap_words": 70},
]
EMBEDDING = [
    {},
    {"embedding_model": "BAAI/bge-base-en-v1.5"},
    {"embedding_model": "intfloat/multilingual-e5-small"},
]


def name_of(cfg: dict) -> str:
    return f"{cfg['embedding_model'].split('/')[-1]}_{cfg['chunk_size_words']}w"


def run_config(cfg: dict, qs_all: list[dict]) -> tuple[list[dict], list[dict], dict]:
    for k, v in cfg.items():
        setattr(settings, k, v)
    settings.index_path = settings.data_dir / "index-ablation" / name_of(cfg)
    meta_file = settings.index_path / "meta.json"
    meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
    build_s = None
    if any(meta.get(k) != v for k, v in cfg.items()) or meta.get("vector_store") != (
        settings.vector_store
    ):
        t0 = time.perf_counter()
        build()
        build_s = round(time.perf_counter() - t0)
        meta = json.loads(meta_file.read_text())
    hybrid.get_retriever.cache_clear()
    retriever = hybrid.get_retriever()
    qs = usable_questions(qs_all, {c.doc_id for c in retriever.chunks})
    rows, by_type, _ = evaluate(retriever, qs, MODES)
    info = {"config": name_of(cfg), "n_chunks": meta["n_chunks"], "build_s": build_s} | cfg
    return [info | r for r in rows], [info | r for r in by_type], info


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--only", choices=["chunk", "embedding"])
    only = p.parse_args().only
    groups = {"chunk": CHUNK, "embedding": EMBEDDING}
    if only:
        groups = {only: groups[only]}
    qs = load_questions()
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    old = (
        json.loads((out / "ablation.json").read_text()) if (out / "ablation.json").exists() else {}
    )
    results = dict(old)
    done: dict[str, tuple] = {}
    for group, variants in groups.items():
        rows, by_type = [], []
        for v in variants:
            cfg = DEFAULT | v
            name = name_of(cfg)
            if name not in done:  # the default config appears in both groups
                done[name] = run_config(cfg, qs)
            r, bt, _ = done[name]
            rows += r
            by_type += bt
        results[group] = {"overall": rows, "by_type": by_type}
    (out / "ablation.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    md = [f"n = {results[next(iter(results))]['overall'][0]['n']} questions, "
          f"vector store: {settings.vector_store}, reranker: {settings.reranker_model}\n"]  # fmt: skip
    for group in ("chunk", "embedding"):
        if group not in results:
            continue
        rows = [
            {"config": r["config"], "chunks": r["n_chunks"]}
            | {k: r[k] for k in ("mode", "n", "recall@5", "recall@10", "mrr@10", "ndcg@10")}
            for r in results[group]["overall"]
        ]
        md += [f"## {group.capitalize()} ablation\n", _table(rows), ""]
    (out / "ablation.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


def _table(rows: list[dict]) -> str:
    cols = list(rows[0])
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append(
            "| "
            + " | ".join(f"{r[c]:.3f}" if isinstance(r[c], float) else str(r[c]) for c in cols)
            + " |"
        )
    return "\n".join(out)


if __name__ == "__main__":
    main()
