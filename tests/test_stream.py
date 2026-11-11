"""Streaming: same answer as the one-piece path, delivered as events. No models, no network."""

import json

import pytest
from fastapi.testclient import TestClient

from threatlens import agent, api, pipeline, tools
from threatlens.llm import client
from threatlens.llm.client import LLMResult
from threatlens.schema import Chunk, RetrievedChunk

DOC = Chunk("attack:T1003.001#0", "attack:T1003.001", "attack", "LSASS Memory", "Dumping.", "u", {})
PIECES = ["LSASS ", "dump ", "[attack:T1003.001] ", "[sigma:nope]"]


def fake_stream(model, messages, **kw):
    for p in PIECES:
        yield {"type": "token", "text": p}
    return LLMResult("".join(PIECES), model, 0.002, 900, first_token_ms=120)


@pytest.fixture(autouse=True)
def _stubs(monkeypatch):
    monkeypatch.setattr(pipeline, "retrieve", lambda q, expand=None: [RetrievedChunk(DOC, 0.9)])
    monkeypatch.setattr(pipeline, "stream_events", fake_stream)
    monkeypatch.setattr(agent, "stream_events", fake_stream)


def test_pipeline_events_are_sources_then_tokens_then_the_checked_answer():
    evs = list(pipeline.answer_events("How is LSASS dumped?", force_model="m", mode="pipeline"))

    assert [e["type"] for e in evs] == ["sources", *["token"] * 4, "done"]
    # sources arrive before the first token, so the UI can show them while the model writes
    assert [c.chunk.doc_id for c in evs[0]["citations"]] == ["attack:T1003.001"]
    ans = evs[-1]["answer"]
    assert ans.answer == "".join(e["text"] for e in evs[1:-1])
    assert ans.cost_usd == 0.002 and ans.first_token_ms >= 120
    # the citation check needs the whole text: its flags come with "done", not with "sources"
    assert evs[0]["guard_flags"] == [] and ans.guard_flags == ["invalid_citation:sigma:nope"]


def test_one_piece_path_is_the_same_generator_without_tokens(monkeypatch):
    monkeypatch.setattr(
        pipeline, "complete", lambda m, msgs, **k: LLMResult("ok [attack:T1003.001]", m, 0.0, 1)
    )
    evs = list(pipeline.answer_events("How is LSASS dumped?", force_model="m", stream=False))
    assert [e["type"] for e in evs] == ["sources", "done"]
    ans = pipeline.answer("How is LSASS dumped?", force_model="m", mode="pipeline")
    assert ans.answer == "ok [attack:T1003.001]" and ans.first_token_ms == 0


def test_agent_streams_its_steps_then_only_the_written_answer(monkeypatch):
    class R:
        chunks = [DOC]

    monkeypatch.setattr(tools, "_retriever", lambda: R())
    gather = iter(
        [
            LLMResult(
                "", "m", 0.001, 5, tool_calls=[{"id": "c1", "name": "nope", "arguments": "{}"}]
            ),
            LLMResult("DONE", "m", 0.001, 5),
        ]
    )
    monkeypatch.setattr(agent, "complete", lambda m, msgs, **k: next(gather))

    evs = list(pipeline.answer_events("How is LSASS dumped?", force_model="m", mode="agent"))

    # tool calls show up as they return; the gather turns ("DONE") are never streamed as text
    assert [e["type"] for e in evs] == ["step", "step", "sources", *["token"] * 4, "done"]
    assert [(e["tool"], e["seeded"]) for e in evs[:2]] == [("search", True), ("nope", False)]
    ans = evs[-1]["answer"]
    assert ans.answer == "".join(PIECES) and len(ans.steps) == 2
    assert ans.cost_usd == pytest.approx(0.004)


def test_api_stream_is_server_sent_events_and_reports_failures_in_band(monkeypatch):
    http = TestClient(api.app)
    r = http.post("/ask/stream", json={"question": "How is LSASS dumped?", "force_model": "m"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    evs = [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith("data: ")]
    assert [e["type"] for e in evs] == ["sources", *["token"] * 4, "done"]
    assert evs[0]["citations"][0]["chunk"]["doc_id"] == "attack:T1003.001"
    assert evs[-1]["answer"]["answer"] == "".join(PIECES)

    def boom(model, messages, **kw):
        yield {"type": "token", "text": "LSASS "}
        raise RuntimeError("model went away")

    monkeypatch.setattr(pipeline, "stream_events", boom)
    r = http.post("/ask/stream", json={"question": "How is LSASS dumped?", "force_model": "m"})
    evs = [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith("data: ")]
    assert evs[-1] == {"type": "error", "message": "RuntimeError: model went away"}


def test_client_stream_times_the_first_token_and_returns_the_full_text(monkeypatch):
    import sys
    import types

    def delta(text):
        choice = types.SimpleNamespace(delta=types.SimpleNamespace(content=text))
        return types.SimpleNamespace(choices=[choice])

    fake = types.SimpleNamespace(
        completion=lambda **kw: iter([delta(None), delta("Hel"), delta("lo"), delta("")]),
        stream_chunk_builder=lambda chunks, messages: None,
        completion_cost=lambda completion_response: 0.5,
    )
    monkeypatch.setitem(sys.modules, "litellm", fake)

    gen = client.stream_events("m", [{"role": "user", "content": "hi"}])
    tokens = []
    while True:
        try:
            tokens.append(next(gen)["text"])
        except StopIteration as stop:
            res = stop.value
            break
    assert tokens == ["Hel", "lo"] and res.text == "Hello"
    assert res.cost_usd == 0.5 and res.first_token_ms <= res.latency_ms
