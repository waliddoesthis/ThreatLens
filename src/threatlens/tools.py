"""Tools the agent can call. Each returns (text for the model, chunks used as evidence).

Every tool is a plain function over the index and the graph, so it can be unit-tested without
an LLM, and everything a tool returns is a real document the answer can cite. Facts that the
data states outright (is this CVE in KEV? which rules are tagged with this technique?) are
answered by lookup, not by generation.
"""

import json
from collections.abc import Callable

from threatlens.schema import Chunk, RetrievedChunk

ToolResult = tuple[str, list[RetrievedChunk]]
SNIPPET = 500  # characters of each search hit shown to the model; `lookup` returns the full text


def _retriever():
    from threatlens.retrieval.hybrid import get_retriever

    return get_retriever()


def _hit(c: Chunk, n: int = SNIPPET) -> str:
    text = (c.text if len(c.text) <= n else c.text[:n] + " …").replace(
        "</source>", "&lt;/source&gt;"
    )
    return f'<source id="{c.doc_id}" title="{c.title}">\n{text}\n</source>'


def search(query: str, source: str = "", k: int = 5) -> ToolResult:
    """Hybrid search (BM25 + dense, reranked). `source` restricts to one corpus."""
    from threatlens.pipeline import retrieve

    hits = retrieve(query, expand=False)
    if source:
        # the reranked top can hold no document of that source: fall back to the wider pool
        hits = [h for h in hits if h.chunk.source == source] or [
            h for h in _retriever().search(query, 30) if h.chunk.source == source
        ]
    hits = hits[:k]
    if not hits:
        return "No result.", []
    return "\n\n".join(_hit(h.chunk) for h in hits), hits


def lookup(id: str) -> ToolResult:
    """Full text of one document by exact id: CVE-…, T1059.001, M1043, CERTFR-…, a Sigma uuid,
    or a source-prefixed id such as sigma:<uuid>."""
    r = _retriever()
    ids = [id] if r.doc(id) else r.graph.ids_in(id)
    if not ids:
        return f"No document with id {id} in the corpus.", []
    c = r.doc(ids[0])
    return _hit(c, 4000), [RetrievedChunk(c, 1.0, "lookup")]


def kev_status(cve: str) -> ToolResult:
    """Is this CVE in CISA's Known Exploited Vulnerabilities catalog? Deterministic."""
    cve = cve.strip().upper()
    c = _retriever().doc(f"kev:{cve}")
    if c is None:
        return (
            json.dumps({"cve": cve, "in_kev": False})
            + "\nNot in the KEV snapshot of this corpus. That is not proof it is unexploited.",
            [],
        )
    m = c.metadata
    facts = {
        "cve": cve,
        "in_kev": True,
        "date_added": m.get("date_added"),
        "known_ransomware_use": m.get("ransomware"),
        "vendor": m.get("vendor"),
        "product": m.get("product"),
    }
    return json.dumps(facts) + "\n" + _hit(c, 1500), [RetrievedChunk(c, 1.0, "lookup")]


def related(technique_id: str, k: int = 5) -> ToolResult:
    """Sigma rules and ATT&CK mitigations linked to a technique id (graph edges, not search)."""
    r = _retriever()
    tid = technique_id.strip().upper().removeprefix("ATTACK:")
    rel = r.graph.related(tid)
    if not rel["sigma_rules"] and not rel["mitigations"]:
        return f"No linked Sigma rule or mitigation for {tid}.", []
    # high-severity rules first: with 40 rules on one technique the model needs a short list
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "informational": 4}
    rules = sorted(
        (r.doc(i) for i in rel["sigma_rules"]),
        key=lambda c: (order.get(c.metadata.get("level"), 5), c.title),
    )[:k]
    mits = [r.doc(i) for i in rel["mitigations"] if r.doc(i)][:k]
    lines = [
        f"{tid}: {len(rel['sigma_rules'])} Sigma rules, {len(rel['mitigations'])} mitigations."
    ]
    lines += [_hit(c, 400) for c in rules + mits]
    return "\n\n".join(lines), [RetrievedChunk(c, 1.0, "graph") for c in rules + mits]


def nvd(cve: str) -> ToolResult:
    """Live NVD record (description, CVSS) for a CVE that is not in the corpus."""
    from threatlens.ingest.nvd import fetch_cve

    try:
        doc = fetch_cve(cve.strip().upper())
    except Exception as e:
        return f"NVD lookup failed: {e}", []
    if doc is None:
        return f"NVD has no record for {cve}.", []
    c = Chunk(f"{doc.id}#0", doc.id, doc.source, doc.title, doc.text, doc.url, doc.metadata)
    return _hit(c, 2000), [RetrievedChunk(c, 1.0, "nvd")]


TOOLS: dict[str, Callable[..., ToolResult]] = {
    "search": search,
    "lookup": lookup,
    "kev_status": kev_status,
    "related": related,
    "nvd": nvd,
}


def _spec(name: str, description: str, props: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


_STR = {"type": "string"}
SPECS = [
    _spec(
        "search",
        "Search the corpus (MITRE ATT&CK, CISA KEV, Sigma rules, CERT-FR advisories). Use for "
        "any question or pasted alert / command line. Queries work best in English.",
        {
            "query": _STR,
            "source": {"type": "string", "enum": ["attack", "kev", "sigma", "certfr"]},
        },
        ["query"],
    ),
    _spec(
        "lookup",
        "Fetch one document by its exact id (CVE-2024-3400, T1059.001, M1043, CERTFR-…, "
        "sigma:<uuid>). Use when the question names an id or a search hit needs reading in full.",
        {"id": _STR},
        ["id"],
    ),
    _spec(
        "kev_status",
        "Check whether a CVE is in CISA's Known Exploited Vulnerabilities catalog.",
        {"cve": _STR},
        ["cve"],
    ),
    _spec(
        "related",
        "List the Sigma detection rules and ATT&CK mitigations linked to a technique id. Use "
        "after you know the technique, to answer how to detect or mitigate it.",
        {"technique_id": _STR},
        ["technique_id"],
    ),
    _spec(
        "nvd",
        "Fetch the live NVD record (description, CVSS) of a CVE that kev_status does not know.",
        {"cve": _STR},
        ["cve"],
    ),
]
