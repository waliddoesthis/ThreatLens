"""How long does the analyst wait before the answer starts? Streamed answers, no judge.

python eval/run_stream_latency.py [--model M] [--mode pipeline|agent] [--stride N] [--limit N]
  -> eval/results/streaming-<model>[-agent].md (+ .jsonl, one row per question)

First token = retrieval + rerank + routing + the model reading the prompt; full answer = until the
last token. Both are measured in the same run, on the same questions, from the caller's side.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from statistics import mean, median

sys.path.insert(0, str(Path(__file__).parent))
from metrics import bootstrap_ci  # noqa: E402
from run_retrieval_eval import load_questions, usable_questions  # noqa: E402

from threatlens import pipeline  # noqa: E402
from threatlens.config import settings  # noqa: E402
from threatlens.retrieval.hybrid import get_retriever  # noqa: E402

HERE = Path(__file__).parent


def measure(question: str, model: str, mode: str) -> dict:
    t0 = time.perf_counter()
    sources_s = first_s = None
    for ev in pipeline.answer_events(question, force_model=model, mode=mode, stream=True):
        now = time.perf_counter() - t0
        if ev["type"] == "sources":
            sources_s = now
        elif ev["type"] == "token" and first_s is None:
            first_s = now
    total_s = time.perf_counter() - t0
    return {"sources_s": sources_s, "first_token_s": first_s or total_s, "total_s": total_s}


def percentile(values: list[float], q: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, int(q * len(s)))]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=settings.small_model)
    p.add_argument("--mode", choices=["pipeline", "agent"], default="pipeline")
    p.add_argument("--stride", type=int, default=4, help="every Nth question")
    p.add_argument("--limit", type=int, default=0, help="first N of those (0 = all)")
    args = p.parse_args()

    qs = usable_questions(load_questions(), {c.doc_id for c in get_retriever().chunks})
    qs = qs[:: args.stride]
    if args.limit:
        qs = qs[: args.limit]
    measure(qs[0]["question"], args.model, args.mode)  # warm-up: load the models, not timed

    stem = "streaming-" + re.sub(r"[^a-z0-9.]+", "-", args.model.split("/")[-1].lower()).strip("-")
    if args.mode == "agent":
        stem += "-agent"
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    rows = []
    with (out / f"{stem}.jsonl").open("w", encoding="utf-8") as f:
        for i, q in enumerate(qs, 1):
            row = {
                "id": q["id"],
                "type": q["type"],
                **measure(q["question"], args.model, args.mode),
            }
            rows.append(row)
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(
                f"[{i}/{len(qs)}] {q['id']} first token {row['first_token_s']:.1f} s, "
                f"full answer {row['total_s']:.1f} s",
                flush=True,
            )

    md = [
        f"Generator: `{args.model}` ({args.mode}), streamed · {len(rows)} questions "
        f"(every {args.stride}th), after one warm-up answer\n",
        "| Wait until | mean (95% CI) | median | p90 |",
        "|---|---|---|---|",
    ]
    for label, key in (
        ("sources shown", "sources_s"),
        ("first token", "first_token_s"),
        ("full answer", "total_s"),
    ):
        v = [r[key] for r in rows if r[key] is not None]
        lo, hi = bootstrap_ci(v)
        md.append(
            f"| {label} | {mean(v):.1f} s ({lo:.1f} to {hi:.1f}) | {median(v):.1f} s "
            f"| {percentile(v, 0.9):.1f} s |"
        )
    (out / f"{stem}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
