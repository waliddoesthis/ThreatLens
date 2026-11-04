"""Answer quality: faithfulness, relevancy (LLM judge) + citation accuracy (deterministic).

python eval/run_answer_eval.py [--model M] [--judge J] [--limit N] [--stride N] [--types cve detection ...]
  -> eval/results/answers-<model>.md (+ .jsonl with every answer, verdict and metric)

Every question goes through the real pipeline (retrieval, rerank, guard, prompt); only the
router is bypassed so one model is measured at a time. The per-question rows double as
labels for the learned router in M3 (was the small model good enough?).
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).parent))
from judge import judge  # noqa: E402
from metrics import citation_metrics  # noqa: E402
from run_retrieval_eval import load_questions, usable_questions  # noqa: E402

from threatlens import pipeline  # noqa: E402
from threatlens.config import settings  # noqa: E402
from threatlens.retrieval.hybrid import get_retriever  # noqa: E402

HERE = Path(__file__).parent
SUMMARY = [
    "faithfulness",
    "relevancy",
    "citation_validity",
    "gold_cited",
    "statement_coverage",
    "invented_ids",
    "latency_ms",
]


def evaluate_one(q: dict, model: str, judge_model: str) -> dict:
    ans = pipeline.answer(q["question"], force_model=model)
    provided = [c.chunk.doc_id for c in ans.citations]
    source_text = "\n".join(c.chunk.text for c in ans.citations)
    row = {
        "id": q["id"],
        "type": q["type"],
        "question": q["question"],
        "gold_ids": q["gold_ids"],
        "provided": provided,
        "answer": ans.answer,
        "latency_ms": float(ans.latency_ms),
        "cost_usd": ans.cost_usd,
    } | citation_metrics(ans.answer, provided, set(q["gold_ids"]), source_text)
    verdict = judge(judge_model, q["question"], ans.answer, ans.citations)
    return row | verdict


def summarise(rows: list[dict]) -> dict[str, float | int | None]:
    out: dict = {"n": len(rows)}
    for k in SUMMARY:
        vals = [r[k] for r in rows if r.get(k) is not None]
        out[k] = mean(vals) if vals else None
        if k in ("faithfulness", "gold_cited", "citation_validity"):
            out[f"{k}_n"] = len(vals)
    out["judge_failures"] = sum(1 for r in rows if r.get("faithfulness") is None)
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=settings.small_model)
    p.add_argument("--judge", default=settings.judge_model or settings.large_model)
    p.add_argument("--limit", type=int, default=0, help="first N questions (0 = all)")
    p.add_argument("--stride", type=int, default=1, help="every Nth question (quick CPU runs)")
    p.add_argument("--types", nargs="*", help="only these question types")
    args = p.parse_args()

    qs = usable_questions(load_questions(), {c.doc_id for c in get_retriever().chunks})
    if args.types:
        qs = [q for q in qs if q["type"] in args.types]
    qs = qs[:: args.stride]
    if args.limit:
        qs = qs[: args.limit]

    out = HERE / "results"
    out.mkdir(exist_ok=True)
    stem = "answers-" + re.sub(r"[^a-z0-9.]+", "-", args.model.split("/")[-1].lower()).strip("-")
    jsonl = out / f"{stem}.jsonl"
    rows: list[dict] = []
    t0 = time.perf_counter()
    with jsonl.open("w", encoding="utf-8") as f:
        for i, q in enumerate(qs, 1):
            row = evaluate_one(q, args.model, args.judge)
            rows.append(row)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            print(
                f"[{i}/{len(qs)}] {q['id']} faith={row['faithfulness']} "
                f"valid={row['citation_validity']} gold={row['gold_cited']}"
            )

    s = summarise(rows)
    by_type = {
        t: summarise([r for r in rows if r["type"] == t]) for t in sorted({r["type"] for r in rows})
    }
    (out / f"{stem}.json").write_text(
        json.dumps(
            {"model": args.model, "judge": args.judge, "overall": s, "by_type": by_type}, indent=2
        )  # fmt: skip
    )
    cols = ["n", *SUMMARY, "judge_failures"]

    def fmt(v) -> str:
        return "–" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v))

    md = [
        f"Generator: `{args.model}` · judge: `{args.judge}` · reranker: {settings.reranker_model}"
        f" · top {settings.top_k_final} chunks · {round(time.perf_counter() - t0)} s total\n",
        "| Scope | " + " | ".join(cols) + " |",
        "|" + "---|" * (len(cols) + 1),
        "| **all** | " + " | ".join(fmt(s[c]) for c in cols) + " |",
    ]
    md += [
        "| " + t + " | " + " | ".join(fmt(v[c]) for c in cols) + " |" for t, v in by_type.items()
    ]
    (out / f"{stem}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
