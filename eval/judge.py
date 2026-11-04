"""LLM-as-judge for answer faithfulness and relevancy.

The judge splits the answer into factual claims and marks each as supported or not by the
SOURCES the generator saw. faithfulness = supported / total claims (RAGAS-style), relevancy is a
1-5 score of how well the answer addresses the question. Plain prompt + JSON, no framework.
"""

from __future__ import annotations

import json
import re

from threatlens.llm.client import complete
from threatlens.llm.prompts import build_context
from threatlens.schema import RetrievedChunk

JUDGE_SYSTEM = """You grade answers written by a security assistant. You are strict and literal.

You receive SOURCES, a QUESTION and an ANSWER. Do two things:
1. List every factual claim the ANSWER makes (skip headings, greetings and statements that
   information is missing). For each claim decide whether the SOURCES state or directly imply it.
   General security knowledge that is NOT in the sources counts as unsupported.
2. Rate how well the ANSWER addresses the QUESTION: 1 (off-topic) to 5 (complete and direct).

Reply with JSON only:
{"claims": [{"claim": "...", "supported": true}], "relevancy": 4}"""


def judge_messages(question: str, answer: str, chunks: list[RetrievedChunk]) -> list[dict]:
    user = f"SOURCES:\n{build_context(chunks)}\n\nQUESTION:\n{question}\n\nANSWER:\n{answer}"
    return [{"role": "system", "content": JUDGE_SYSTEM}, {"role": "user", "content": user}]


def parse_verdict(text: str) -> dict | None:
    """Pull the JSON object out of the judge's reply; None if it is unusable."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    claims = [c for c in obj.get("claims", []) if isinstance(c, dict) and "supported" in c]
    rel = obj.get("relevancy")
    return {
        "claims": claims,
        "faithfulness": (
            sum(1 for c in claims if c["supported"] is True) / len(claims) if claims else None
        ),
        "relevancy": float(rel) if isinstance(rel, int | float) and 1 <= rel <= 5 else None,
    }


def judge(model: str, question: str, answer: str, chunks: list[RetrievedChunk]) -> dict:
    kwargs = {"response_format": {"type": "json_object"}} if model.startswith("ollama") else {}
    res = complete(model, judge_messages(question, answer, chunks), 0.0, 1500, **kwargs)
    return parse_verdict(res.text) or {"claims": [], "faithfulness": None, "relevancy": None}
