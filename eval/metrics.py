"""Retrieval metrics on document ids (several chunks of one doc count once)."""

import math


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
