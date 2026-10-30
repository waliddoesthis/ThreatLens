"""Retrieval ablation: bm25 / dense / hybrid / hybrid+rerank / hybrid+rerank+rrf.

python eval/run_retrieval_eval.py [--modes bm25 dense ...]  ->  eval/results/retrieval.md (+ .json)
"""

import argparse
import json
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).parent))
from metrics import dedupe, mrr_at_k, ndcg_at_k, recall_at_k  # noqa: E402

from threatlens.config import settings  # noqa: E402
from threatlens.retrieval.hybrid import get_retriever  # noqa: E402

HERE = Path(__file__).parent
MODES = ["bm25", "dense", "hybrid", "hybrid+rerank", "hybrid+rerank+rrf"]


def ranked_doc_ids(retriever, q: str, mode: str) -> list[str]:
    if mode.startswith("hybrid+rerank"):
        from threatlens.retrieval.rerank import rerank

        fuse = mode.endswith("+rrf")
        res = rerank(q, retriever.search(q, 30, "hybrid"), top_k=10, fuse=fuse)
    else:
        res = retriever.search(q, 30, mode)
    return dedupe([r.chunk.doc_id for r in res])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--modes", nargs="*", choices=MODES, default=MODES)
    modes = p.parse_args().modes
    qs = [
        json.loads(line)
        for line in (HERE / "questions.jsonl").open(encoding="utf-8")
        if line.strip()
    ]
    retriever = get_retriever()
    known = {c.doc_id for c in retriever.chunks}
    for q in qs:
        missing = set(q["gold_ids"]) - known
        if missing:  # e.g. ATT&CK renumbers techniques between releases
            print(f"[warn] {q['id']}: gold ids not in corpus: {sorted(missing)}")
    rows = []
    for mode in modes:
        r5, r10, mrr, ndcg = [], [], [], []
        for q in qs:
            gold = set(q["gold_ids"])
            ranked = ranked_doc_ids(retriever, q["question"], mode)
            r5.append(recall_at_k(ranked, gold, 5))
            r10.append(recall_at_k(ranked, gold, 10))
            mrr.append(mrr_at_k(ranked, gold, 10))
            ndcg.append(ndcg_at_k(ranked, gold, 10))
        rows.append(
            {
                "mode": mode,
                "recall@5": mean(r5),
                "recall@10": mean(r10),
                "mrr@10": mean(mrr),
                "ndcg@10": mean(ndcg),
            }
        )
        print(rows[-1])

    out = HERE / "results"
    out.mkdir(exist_ok=True)
    # qdrant is the reference run; other stores get their own files to compare against it
    stem = (
        "retrieval" if settings.vector_store == "qdrant" else f"retrieval-{settings.vector_store}"
    )
    (out / f"{stem}.json").write_text(json.dumps(rows, indent=2))
    md = ["| Mode | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |", "|---|---|---|---|---|"]
    md += [
        f"| {r['mode']} | {r['recall@5']:.3f} | {r['recall@10']:.3f} | {r['mrr@10']:.3f} "
        f"| {r['ndcg@10']:.3f} |"
        for r in rows
    ]
    header = f"n = {len(qs)} questions, vector store: {settings.vector_store}\n\n"
    (out / f"{stem}.md").write_text(header + "\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
