"""Thin LiteLLM wrapper returning text + cost + latency, in one piece or as a token stream."""

import time
from collections.abc import Iterator
from dataclasses import dataclass, field


@dataclass
class LLMResult:
    text: str
    model: str
    cost_usd: float
    latency_ms: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    # [{"id": ..., "name": ..., "arguments": "<json string>"}] when the model asked for tools
    tool_calls: list[dict] = field(default_factory=list)
    first_token_ms: int = 0  # streamed calls only: time until the first piece of text


def complete(
    model: str,
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 800,
    **kwargs,
) -> LLMResult:
    """kwargs go to litellm.completion, e.g. response_format={...} or tools=[...]."""
    import litellm

    t0 = time.perf_counter()
    resp = litellm.completion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )
    latency = int((time.perf_counter() - t0) * 1000)
    try:
        cost = float(litellm.completion_cost(completion_response=resp))
    except Exception:  # local models have no price -> 0
        cost = 0.0
    usage = getattr(resp, "usage", None)
    msg = resp.choices[0].message
    calls = [
        {"id": c.id, "name": c.function.name, "arguments": c.function.arguments or "{}"}
        for c in (getattr(msg, "tool_calls", None) or [])
    ]
    return LLMResult(
        text=msg.content or "",
        tool_calls=calls,
        model=model,
        cost_usd=cost,
        latency_ms=latency,
        prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
    )


def stream_events(
    model: str, messages: list[dict], temperature: float = 0.1, max_tokens: int = 800
) -> Iterator[dict]:
    """Yield {"type": "token", "text": ...} as the model writes; *return* the LLMResult.

    Use as `res = yield from stream_events(model, messages)` inside another generator.
    """
    import litellm

    t0 = time.perf_counter()
    chunks, parts, first = [], [], 0
    for chunk in litellm.completion(
        model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, stream=True
    ):
        chunks.append(chunk)
        piece = (chunk.choices[0].delta.content or "") if chunk.choices else ""
        if piece:
            first = first or int((time.perf_counter() - t0) * 1000)
            parts.append(piece)
            yield {"type": "token", "text": piece}
    try:  # rebuild the full response to price it; local models have no price -> 0
        full = litellm.stream_chunk_builder(chunks, messages=messages)
        cost = float(litellm.completion_cost(completion_response=full))
    except Exception:
        cost = 0.0
    latency = int((time.perf_counter() - t0) * 1000)
    return LLMResult("".join(parts), model, cost, latency, first_token_ms=first)
