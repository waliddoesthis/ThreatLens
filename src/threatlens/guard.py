"""Prompt-injection guard (M4). v1 = heuristics; v2 (todo) = small classifier.

Two jobs:
- check_query: flag suspicious user input
- sanitize_chunks: neutralise instructions hidden in retrieved documents (indirect injection)
"""

import re
from dataclasses import replace

from threatlens.schema import RetrievedChunk

INJECTION_PATTERNS = [
    r"ignore (all|any|the)? ?(previous|prior|above) (instructions|rules)",
    r"disregard (the )?(system|previous) (prompt|instructions)",
    r"you are now\b",
    r"new instructions?:",
    r"reveal (your|the) (system )?prompt",
    r"print (your|the) (system )?prompt",
    r"</?\s*(system|assistant)\s*>",
    r"act as (an? )?(unrestricted|jailbroken|dan)\b",
]
_RX = re.compile("|".join(INJECTION_PATTERNS), re.I)


def check_query(question: str) -> list[str]:
    return [f"query_injection:{m.group(0)[:40]}" for m in _RX.finditer(question)]


def sanitize_chunks(chunks: list[RetrievedChunk]) -> tuple[list[RetrievedChunk], list[str]]:
    flags, clean = [], []
    for rc in chunks:
        text = rc.chunk.text
        if _RX.search(text):
            flags.append(f"doc_injection:{rc.chunk.doc_id}")
            text = _RX.sub("[REMOVED: suspected injected instruction]", text)
        # stop documents from closing our <source> delimiter
        text = text.replace("</source>", "&lt;/source&gt;")
        # copy, never mutate: chunks are shared with the retriever's in-memory index
        clean.append(RetrievedChunk(replace(rc.chunk, text=text), rc.score, rc.stage))
    return clean, flags
