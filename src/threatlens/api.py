"""FastAPI service: uvicorn threatlens.api:app --reload"""

import json
from collections.abc import Iterator
from dataclasses import asdict

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from threatlens import __version__

app = FastAPI(title="ThreatLens", version=__version__)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    force_model: str | None = None
    mode: str | None = Field(default=None, pattern="^(pipeline|agent)$")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.post("/ask")
def ask(req: AskRequest) -> dict:
    from threatlens.pipeline import answer

    return answer(req.question, force_model=req.force_model, mode=req.mode).to_dict()


def _wire(ev: dict) -> dict:
    """An event of `pipeline.answer_events` as plain JSON."""
    if ev["type"] == "sources":
        return {**ev, "citations": [asdict(c) for c in ev["citations"]]}
    if ev["type"] == "done":
        return {"type": "done", "answer": ev["answer"].to_dict()}
    return ev


@app.post("/ask/stream")
def ask_stream(req: AskRequest) -> StreamingResponse:
    """Server-sent events: sources, then (agent mode) steps, then tokens, then the full Answer."""
    from threatlens.pipeline import answer_events

    def sse() -> Iterator[str]:
        try:
            for ev in answer_events(req.question, force_model=req.force_model, mode=req.mode):
                yield f"data: {json.dumps(_wire(ev), ensure_ascii=False)}\n\n"
        except Exception as e:  # the 200 is already sent: report the failure in the stream
            err = {"type": "error", "message": f"{type(e).__name__}: {e}"[:300]}
            yield f"data: {json.dumps(err)}\n\n"

    return StreamingResponse(
        sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},  # no proxy buffering
    )
