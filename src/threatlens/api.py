"""FastAPI service: uvicorn threatlens.api:app --reload"""

from fastapi import FastAPI
from pydantic import BaseModel, Field

from threatlens import __version__

app = FastAPI(title="ThreatLens", version=__version__)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    force_model: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.post("/ask")
def ask(req: AskRequest) -> dict:
    from threatlens.pipeline import answer

    return answer(req.question, force_model=req.force_model).to_dict()
