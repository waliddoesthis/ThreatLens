"""Retrieval ablation: bm25 / dense / hybrid / hybrid+rerank / hybrid+rerank+rrf.

python eval/run_retrieval_eval.py [--modes bm25 dense ...]
  -> eval/results/retrieval.md (+ .json, + per-question-type breakdown)
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).parent))
from metrics import dedupe, mrr_at_k, ndcg_at_k, recall_at_k  # noqa: E402

from threatlens.config import settings  # noqa: E402
from threatlens.retrieval.hybrid import get_retriever  # noqa: E402

HERE = Path(__file__).parent
MODES = ["bm25", "dense", "hybrid", "hybrid+rerank", "hybrid+rerank+rrf"]
METRICS = ["recall@5", "recall@10", "mrr@10", "ndcg@10"]


def load_questions() -> list[dict]:
    with (HERE / "questions.jsonl").open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def usable_questions(qs: list[dict], known: set[str]) -> list[dict]:
    """Drop gold ids absent from the corpus, and questions left with none.

    ATT&CK renumbers techniques and the CERT-FR feed only keeps recent advisories, so a stale
    label would silently count as a miss. Each drop is printed.
    """
    out = []
    for q in qs:
        missing = set(q["gold_ids"]) - known
        if missing:
            print(f"[warn] {q['id']}: gold ids not in corpus: {sorted(missing)}")
        gold = [g for g in q["gold_ids"] if g in known]
        if gold:
            out.append({**q, "gold_ids": gold})
    return out


def ranked_doc_ids(retriever, q: str, mode: str) -> list[str]:
    if mode.startswith("hybrid+rerank"):
        from threatlens.retrieval.rerank import rerank

        fuse = mode.endswith("+rrf")
        res = rerank(q, retriever.search(q, 30, "hybrid"), top_k=10, fuse=fuse)
    else:
        res = retriever.search(q, 30, mode)
    return dedupe([r.chunk.doc_id for r in res])


def score(ranked: list[str], gold: set[str]) -> dict[str, float]:
    return {
        "recall@5": recall_at_k(ranked, gold, 5),
        "recall@10": recall_at_k(ranked, gold, 10),
        "mrr@10": mrr_at_k(ranked, gold, 10),
        "ndcg@10": ndcg_at_k(ranked, gold, 10),
    }


def evaluate(retriever, qs: list[dict], modes: list[str]) -> tuple[list[dict], list[dict]]:
    """Returns (one row per mode, one row per (mode, question type))."""
    rows, by_type = [], []
    for mode in modes:
        per_q = [
            (q["type"], score(ranked_doc_ids(retriever, q["question"], mode), set(q["gold_ids"])))
            for q in qs
        ]
        rows.append({"mode": mode, "n": len(per_q)} | _avg([s for _, s in per_q]))
        groups = defaultdict(list)
        for t, s in per_q:
            groups[t].append(s)
        by_type += [{"mode": mode, "type": t, "n": len(v)} | _avg(v) for t, v in groups.items()]
        print(rows[-1])
    return rows, by_type


def _avg(scores: list[dict[str, float]]) -> dict[str, float]:
    return {m: mean(s[m] for s in scores) for m in METRICS}


def to_markdown(rows: list[dict], key: str = "mode") -> str:
    cols = [key] + (["type"] if "type" in rows[0] and key != "type" else []) + ["n"] + METRICS
    md = ["| " + " | ".join(c.capitalize() for c in cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        md.append(
            "| "
            + " | ".join(f"{r[c]:.3f}" if isinstance(r[c], float) else str(r[c]) for c in cols)
            + " |"
        )
    return "\n".join(md)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--modes", nargs="*", choices=MODES, default=MODES)
    modes = p.parse_args().modes
    retriever = get_retriever()
    qs = usable_questions(load_questions(), {c.doc_id for c in retriever.chunks})
    rows, by_type = evaluate(retriever, qs, modes)

    out = HERE / "results"
    out.mkdir(exist_ok=True)
    # qdrant is the reference run; other stores get their own files to compare against it
    stem = (
        "retrieval" if settings.vector_store == "qdrant" else f"retrieval-{settings.vector_store}"
    )
    (out / f"{stem}.json").write_text(json.dumps({"overall": rows, "by_type": by_type}, indent=2))
    header = (
        f"n = {len(qs)} questions, vector store: {settings.vector_store}, "
        f"embeddings: {settings.embedding_model}, reranker: {settings.reranker_model}, "
        f"chunks: {settings.chunk_size_words}/{settings.chunk_overlap_words} words\n\n"
    )
    body = to_markdown(rows) + "\n\n## By question type\n\n" + to_markdown(by_type) + "\n"
    (out / f"{stem}.md").write_text(header + body)
    print(body)


if __name__ == "__main__":
    main()
