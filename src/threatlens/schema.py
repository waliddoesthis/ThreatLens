"""Core data structures shared by every stage of the pipeline."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Document:
    id: str  # stable, source-prefixed: "attack:T1059.001"
    source: str  # attack | kev | sigma | certfr | nvd
    title: str
    text: str
    url: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class Chunk:
    chunk_id: str  # "<doc_id>#<n>"
    doc_id: str
    source: str
    title: str
    text: str
    url: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float
    stage: str = "hybrid"  # bm25 | dense | hybrid | rerank


@dataclass
class Answer:
    answer: str
    citations: list[RetrievedChunk]
    model: str
    route_reason: str
    cost_usd: float = 0.0
    latency_ms: int = 0
    guard_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def write_jsonl(path: Path, docs: Iterable[Document]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(asdict(d), ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: Path) -> Iterator[Document]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield Document(**json.loads(line))
