"""Cost-aware model router (M3).

v1 = transparent rules. v2 (todo) = logistic regression trained on eval data predicting
P(small model answer is good enough), routing to the small model when P > threshold.
The threshold is the decision knob that traces the quality-vs-cost Pareto front.
"""

import re
from dataclasses import dataclass

from threatlens.config import settings
from threatlens.schema import RetrievedChunk

_ID = re.compile(r"\b(CVE-\d{4}-\d{4,}|T\d{4}(?:\.\d{3})?)\b", re.I)
_COMPLEX = re.compile(
    r"\b(compare|why|explain|correlate|investigate|timeline|which .* and|plan|prioriti[sz]e)\b",
    re.I,
)


@dataclass
class RouteFeatures:
    n_words: int
    n_ids: int
    looks_like_log: bool
    complex_intent: bool
    top_score: float
    score_gap: float


def features(question: str, chunks: list[RetrievedChunk]) -> RouteFeatures:
    scores = [c.score for c in chunks]
    top = scores[0] if scores else 0.0
    gap = (scores[0] - scores[1]) if len(scores) > 1 else 0.0
    return RouteFeatures(
        n_words=len(question.split()),
        n_ids=len(_ID.findall(question)),
        looks_like_log=any(s in question for s in ("\\", "=", "EventID", ".exe", "cmd", "|")),
        complex_intent=bool(_COMPLEX.search(question)),
        top_score=top,
        score_gap=gap,
    )


def route(question: str, chunks: list[RetrievedChunk]) -> tuple[str, str]:
    """Return (model, reason)."""
    if settings.router_mode == "always_small":
        return settings.small_model, "forced small"
    if settings.router_mode == "always_large":
        return settings.large_model, "forced large"

    f = features(question, chunks)
    if f.looks_like_log or f.complex_intent or f.n_words > 60:
        return settings.large_model, "complex query (log / multi-step / long)"
    if chunks and chunks[0].stage == "rerank" and f.top_score < 0.0:
        return settings.large_model, "low retrieval confidence"
    if f.n_ids >= 1 and f.n_words <= 25:
        return settings.small_model, "simple lookup of a known identifier"
    return settings.small_model, "default: simple question"
