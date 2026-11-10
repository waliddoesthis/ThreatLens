"""A small knowledge graph over the corpus, built from links the sources already publish.

Edges:
- Sigma rule -> ATT&CK technique   (the rule's `attack.tXXXX` tags)
- ATT&CK technique -> mitigation   (STIX `mitigates` relationships)
- any id -> document               (exact lookup of CVE / technique / rule / advisory ids)

No new data and no model: the graph is derived from chunk metadata when the index is loaded.
It lets the pipeline follow a link ("this command line matched three Sigma rules tagged
T1003.001") instead of relying on text similarity alone.
"""

import re
from collections import defaultdict

from threatlens.schema import Chunk

# ids a question can name outright; each maps to a doc id prefix
_ID_PATTERNS = [
    (re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.I), ("kev:{}", "nvd:{}")),
    (re.compile(r"\bT\d{4}(?:\.\d{3})?\b", re.I), ("attack:{}",)),
    (re.compile(r"\bM1\d{3}\b", re.I), ("attack:{}",)),
    (re.compile(r"\bCERTFR-\d{4}-[A-Z]{3}-\d+\b", re.I), ("certfr:{}",)),
]
_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)


class Graph:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.first_chunk: dict[str, int] = {}  # doc id -> index of its first chunk
        self.sigma_by_technique: dict[str, list[str]] = defaultdict(list)
        self.techniques_by_sigma: dict[str, list[str]] = {}
        self.mitigations_by_technique: dict[str, list[str]] = {}
        for i, c in enumerate(chunks):
            if c.doc_id in self.first_chunk:
                continue
            self.first_chunk[c.doc_id] = i
            if c.source == "sigma":
                techs = [t.upper() for t in c.metadata.get("techniques", [])]
                self.techniques_by_sigma[c.doc_id] = techs
                for t in techs:
                    self.sigma_by_technique[t].append(c.doc_id)
            elif c.source == "attack" and c.metadata.get("kind") == "technique":
                tid = c.doc_id.split(":", 1)[1]
                self.mitigations_by_technique[tid] = [
                    f"attack:{m}" for m in c.metadata.get("mitigations", [])
                ]

    def ids_in(self, text: str) -> list[str]:
        """Doc ids of the identifiers named in `text` that exist in the corpus, in order."""
        found: list[tuple[int, str]] = []
        for rx, templates in _ID_PATTERNS:
            for m in rx.finditer(text):
                for t in templates:
                    doc_id = t.format(m.group(0).upper())
                    if doc_id in self.first_chunk:
                        found.append((m.start(), doc_id))
                        break
        for m in _UUID.finditer(text):
            if f"sigma:{m.group(0).lower()}" in self.first_chunk:
                found.append((m.start(), f"sigma:{m.group(0).lower()}"))
        out: list[str] = []
        for _, doc_id in sorted(found):
            if doc_id not in out:
                out.append(doc_id)
        return out

    def technique_votes(self, ranked_doc_ids: list[str], k: int = 60) -> list[tuple[str, float]]:
        """ATT&CK techniques tagged by the Sigma rules in a ranked list, best supported first.

        Each rule votes for its techniques with weight 1/(k + rank), the same shape as RRF, so
        several rules agreeing near the top outweigh one rule far down. Only techniques that
        exist in the corpus are returned, as doc ids.
        """
        votes: dict[str, float] = defaultdict(float)
        for rank, doc_id in enumerate(ranked_doc_ids):
            for t in self.techniques_by_sigma.get(doc_id, []):
                if f"attack:{t}" in self.first_chunk:
                    votes[f"attack:{t}"] += 1.0 / (k + rank + 1)
        return sorted(votes.items(), key=lambda x: (-x[1], x[0]))

    def related(self, technique_id: str) -> dict[str, list[str]]:
        """Detections and mitigations linked to a technique id such as "T1003.001"."""
        tid = technique_id.upper().removeprefix("ATTACK:")
        return {
            "sigma_rules": list(self.sigma_by_technique.get(tid, [])),
            "mitigations": list(self.mitigations_by_technique.get(tid, [])),
        }
