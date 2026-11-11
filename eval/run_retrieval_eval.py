"""Retrieval ablation: bm25 / dense / hybrid / hybrid+rerank / hybrid+rerank+rrf.

python eval/run_retrieval_eval.py [--modes bm25 dense ... graph graph+translate] [--set core|alerts]
  -> eval/results/retrieval.md (+ .json, + per-question-type breakdown, + 95% bootstrap CIs)
  --set alerts scores eval/questions_alerts.jsonl (Atomic Red Team command lines)
  -> eval/results/retrieval-alerts.md
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).parent))
from metrics import (  # noqa: E402
    bootstrap_ci,
    dedupe,
    mrr_at_k,
    ndcg_at_k,
    paired_bootstrap,
    recall_at_k,
)

from threatlens.config import settings  # noqa: E402
from threatlens.index import corpus_refs  # noqa: E402
from threatlens.retrieval.hybrid import get_retriever  # noqa: E402

HERE = Path(__file__).parent
MODES = [
    "bm25",
    "dense",
    "hybrid",
    "hybrid+rerank",
    "hybrid+rerank+rrf",
    "graph",
    "graph+translate",
]
METRICS = ["recall@5", "recall@10", "mrr@10", "ndcg@10"]


SETS = {"core": "questions.jsonl", "alerts": "questions_alerts.jsonl"}
BASELINE = "hybrid"  # paired comparisons are reported against plain hybrid


def load_questions(name: str = "core") -> list[dict]:
    with (HERE / SETS[name]).open(encoding="utf-8") as f:
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


def cache_reranker() -> None:
    """Memoise cross-encoder scores for this run: three modes rescore the same pairs."""
    from threatlens.retrieval import rerank as rr

    model, memo = rr._model(), {}

    class Cached:
        def predict(self, pairs):
            todo = [p for p in dict.fromkeys(pairs) if p not in memo]
            if todo:
                memo.update(zip(todo, (float(s) for s in model.predict(todo)), strict=True))
            return [memo[p] for p in pairs]

    rr._model = lambda: Cached()


def ranked_doc_ids(retriever, q: str, mode: str) -> list[str]:
    if mode.startswith("graph"):
        # fused rerank + link expansion + exact id lookup; "+translate" (the production path)
        # also searches French questions in English, which needs the small LLM to be running
        from threatlens.pipeline import retrieve

        settings.translate_queries = mode.endswith("+translate")
        # link expansion reserves the last places of the context, so Recall@5 must be read on
        # a 5-chunk context and Recall@10 on a 10-chunk one, not on one list cut twice
        res = retrieve(q, expand=True, top_k=5) + retrieve(q, expand=True, top_k=10)
    elif mode.startswith("hybrid+rerank"):
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


def evaluate(
    retriever, qs: list[dict], modes: list[str]
) -> tuple[list[dict], list[dict], dict[str, list[dict]]]:
    """Returns (one row per mode, one row per (mode, question type), per-question scores)."""
    rows, by_type, raw = [], [], {}
    for mode in modes:
        per_q = [
            (q["type"], score(ranked_doc_ids(retriever, q["question"], mode), set(q["gold_ids"])))
            for q in qs
        ]
        raw[mode] = [s for _, s in per_q]
        rows.append({"mode": mode, "n": len(per_q)} | _avg([s for _, s in per_q]))
        groups = defaultdict(list)
        for t, s in per_q:
            groups[t].append(s)
        by_type += [{"mode": mode, "type": t, "n": len(v)} | _avg(v) for t, v in groups.items()]
        print(rows[-1])
    return rows, by_type, raw


def uncertainty(raw: dict[str, list[dict]]) -> tuple[list[dict], str]:
    """95% bootstrap CIs per mode, and each mode's paired difference to the hybrid baseline."""
    cis = []
    for mode, scores in raw.items():
        row = {"mode": mode}
        for m in ("recall@5", "mrr@10"):
            lo, hi = bootstrap_ci([s[m] for s in scores])
            row[m] = [round(lo, 3), round(hi, 3)]
        if BASELINE in raw and mode != BASELINE:
            d, lo, hi = paired_bootstrap(
                [s["recall@5"] for s in scores], [s["recall@5"] for s in raw[BASELINE]]
            )
            row["delta_recall@5_vs_hybrid"] = [round(d, 3), round(lo, 3), round(hi, 3)]
        cis.append(row)
    md = [
        "| Mode | Recall@5 95% CI | MRR@10 95% CI | Δ Recall@5 vs hybrid (95% CI) |",
        "|---|---|---|---|",
    ]
    for r in cis:
        d = r.get("delta_recall@5_vs_hybrid")
        delta = f"{d[0]:+.3f} ({d[1]:+.3f} to {d[2]:+.3f})" if d else "–"
        md.append(
            f"| {r['mode']} | {r['recall@5'][0]:.3f}–{r['recall@5'][1]:.3f} "
            f"| {r['mrr@10'][0]:.3f}–{r['mrr@10'][1]:.3f} | {delta} |"
        )
    return cis, "\n".join(md)


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
    p.add_argument("--set", choices=list(SETS), default="core", dest="qset")
    args = p.parse_args()
    modes = args.modes
    retriever = get_retriever()
    if any("rerank" in m or m.startswith("graph") for m in modes):
        cache_reranker()
    qs = usable_questions(load_questions(args.qset), {c.doc_id for c in retriever.chunks})
    rows, by_type, raw = evaluate(retriever, qs, modes)
    cis, ci_md = uncertainty(raw)

    out = HERE / "results"
    out.mkdir(exist_ok=True)
    # qdrant is the reference run; other stores get their own files to compare against it
    stem = (
        "retrieval" if settings.vector_store == "qdrant" else f"retrieval-{settings.vector_store}"
    )
    if args.qset != "core":
        stem += f"-{args.qset}"
    (out / f"{stem}.json").write_text(
        json.dumps({"overall": rows, "by_type": by_type, "uncertainty": cis}, indent=2),
        encoding="utf-8",
    )
    header = (
        f"n = {len(qs)} questions, vector store: {settings.vector_store}, "
        f"embeddings: {settings.embedding_model}, reranker: {settings.reranker_model}, "
        f"chunks: {settings.chunk_size_words}/{settings.chunk_overlap_words} words\n\n"
    )
    corpus = corpus_refs()
    if corpus:
        header += "Corpus: " + "; ".join(f"{k} {v}" for k, v in corpus.items()) + "\n\n"
    body = (
        to_markdown(rows)
        + "\n\n## Uncertainty (2,000 bootstrap resamples of the questions)\n\n"
        + ci_md
        + "\n\n## By question type\n\n"
        + to_markdown(by_type)
        + "\n"
    )
    (out / f"{stem}.md").write_text(header + body, encoding="utf-8")
    print(body)


if __name__ == "__main__":
    main()
