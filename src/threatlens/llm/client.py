"""Thin LiteLLM wrapper returning text + cost + latency."""

import time
from dataclasses import dataclass


@dataclass
class LLMResult:
    text: str
    model: str
    cost_usd: float
    latency_ms: int
    prompt_tokens: int = 0
    completion_tokens: int = 0


def complete(
    model: str, messages: list[dict], temperature: float = 0.1, max_tokens: int = 800
) -> LLMResult:
    import litellm

    t0 = time.perf_counter()
    resp = litellm.completion(
        model=model, messages=messages, temperature=temperature, max_tokens=max_tokens
    )
    latency = int((time.perf_counter() - t0) * 1000)
    try:
        cost = float(litellm.completion_cost(completion_response=resp))
    except Exception:  # local models have no price -> 0
        cost = 0.0
    usage = getattr(resp, "usage", None)
    return LLMResult(
        text=resp.choices[0].message.content or "",
        model=model,
        cost_usd=cost,
        latency_ms=latency,
        prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
    )
