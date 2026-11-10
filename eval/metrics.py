"""Retrieval metrics on document ids (several chunks of one doc count once)."""

import math
import random
import re


def dedupe(ids: list[str]) -> list[str]:
    seen, out = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def recall_at_k(ranked: list[str], gold: set[str], k: int) -> float:
    return len(set(ranked[:k]) & gold) / len(gold) if gold else 0.0


def mrr_at_k(ranked: list[str], gold: set[str], k: int) -> float:
    for r, d in enumerate(ranked[:k], start=1):
        if d in gold:
            return 1.0 / r
    return 0.0


def ndcg_at_k(ranked: list[str], gold: set[str], k: int) -> float:
    dcg = sum(1.0 / math.log2(r + 1) for r, d in enumerate(ranked[:k], start=1) if d in gold)
    idcg = sum(1.0 / math.log2(r + 1) for r in range(1, min(len(gold), k) + 1))
    return dcg / idcg if idcg else 0.0


def bootstrap_ci(
    values: list[float], n_boot: int = 2000, alpha: float = 0.05, seed: int = 0
) -> tuple[float, float]:
    """Percentile bootstrap confidence interval of the mean of per-question scores.

    With ~100 questions one question moves a mean by ~0.01, so a table of means without an
    interval invites reading noise as a result. Seeded: the same scores give the same interval.
    """
    if not values:
        return 0.0, 0.0
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(n_boot))
    return means[int(n_boot * alpha / 2)], means[int(n_boot * (1 - alpha / 2)) - 1]


def paired_bootstrap(
    a: list[float], b: list[float], n_boot: int = 2000, seed: int = 0
) -> tuple[float, float, float]:
    """(mean of a-b, 95% CI low, high) resampling questions; a and b are scored on the same ones.

    If the interval contains 0, the two systems are not distinguishable on this benchmark.
    """
    diffs = [x - y for x, y in zip(a, b, strict=True)]
    lo, hi = bootstrap_ci(diffs, n_boot, seed=seed)
    return (sum(diffs) / len(diffs) if diffs else 0.0), lo, hi


# --- answer-level metrics (deterministic part; faithfulness uses an LLM judge) ---

_HEADING = re.compile(r"^\s*(#+\s|\*\*[^*]+\*\*:?\s*$)")
_BRACKETS = re.compile(r"\[[^\[\]]*\]")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\[])")


def statements(answer: str) -> list[str]:
    """Answer lines/sentences that state something (headings and short fragments dropped)."""
    out = []
    for line in answer.splitlines():
        line = line.strip().lstrip("-*• ").strip()
        if not line or _HEADING.match(line):
            continue
        out += [s for s in _SENT.split(line) if len(s) >= 25]
    return out


def citation_metrics(
    answer: str, provided: list[str], gold: set[str], source_text: str
) -> dict[str, float | None]:
    """
    - citation_validity: share of cited ids that were really in the provided sources
      (anything else is a hallucinated citation)
    - gold_cited: 1 if the answer cites a gold doc, None when no gold doc was retrieved
    - statement_coverage: share of statements carrying at least one citation
    - unsupported_ids: CVE / technique / mitigation ids stated in the answer that appear in no
      provided source (rule 4 of the system prompt)
    """
    from threatlens.citations import extract_citations, mentioned_ids

    cited = extract_citations(answer)
    prov = set(provided)
    sts = statements(answer)
    known = mentioned_ids(source_text) | {p.split(":", 1)[1].upper() for p in prov}
    return {
        "n_citations": float(len(cited)),
        "citation_validity": (len([c for c in cited if c in prov]) / len(cited)) if cited else None,
        "gold_cited": (1.0 if gold & set(cited) else 0.0) if gold & prov else None,
        "statement_coverage": (
            sum(1 for s in sts if extract_citations(s)) / len(sts) if sts else None
        ),
        # ids stated in prose; a bad id inside a citation is already counted by citation_validity
        "unsupported_ids": float(len(mentioned_ids(_BRACKETS.sub(" ", answer)) - known)),
    }
