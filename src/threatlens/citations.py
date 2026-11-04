"""Parse what an answer cites and which security ids it mentions.

Answers cite sources as [source:id]; models sometimes group several ids in one bracket
([attack:T1059.001, sigma:abc]), so both forms are accepted. The UI and the answer eval share
this parser so a citation the UI would not link is not counted as one either.
"""

import re

SOURCES = ("attack", "kev", "sigma", "certfr", "nvd")
_BRACKET = re.compile(r"\[([^\[\]]+)\]")
_ID = re.compile(rf"^({'|'.join(SOURCES)}):(\S+)$", re.I)
# ids an answer can state as facts: CVEs, ATT&CK techniques/sub-techniques, mitigations
MENTIONED_ID = re.compile(r"\b(CVE-\d{4}-\d{4,}|T\d{4}(?:\.\d{3})?|M1\d{3})\b", re.I)


def extract_citations(text: str) -> list[str]:
    """Cited doc ids in order of first appearance, e.g. ['attack:T1059.001', 'kev:CVE-...']."""
    out: list[str] = []
    for group in _BRACKET.findall(text):
        for part in re.split(r"[,;]\s*|\s+", group.strip()):
            m = _ID.match(part.strip().rstrip("."))
            if m:
                cid = f"{m.group(1).lower()}:{m.group(2)}"
                if cid not in out:
                    out.append(cid)
    return out


def mentioned_ids(text: str) -> set[str]:
    return {m.upper() for m in MENTIONED_ID.findall(text)}
