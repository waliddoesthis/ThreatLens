import json
import re

COLLECTION = "threatlens"
_TOKEN = re.compile(r"[a-z0-9][a-z0-9._-]*")


def tokenize(text: str) -> list[str]:
    """BM25 tokenizer that keeps security identifiers intact (cve-2024-3400, t1059.001)."""
    return [t.strip("._-") for t in _TOKEN.findall(text.lower()) if t.strip("._-")]


# Embedding models are trained with different instruction prefixes; using the wrong one (or none)
# costs recall. Keys are matched against the lower-cased model name.
_PREFIXES = {
    "bge-m3": ("", ""),  # bge-m3 needs no instruction
    "bge-": ("Represent this sentence for searching relevant passages: ", ""),
    "e5": ("query: ", "passage: "),
}


def embedding_prefixes(model_name: str) -> tuple[str, str]:
    """(query_prefix, passage_prefix) for an embedding model; settings can override either."""
    from threatlens.config import settings

    q, p = next((v for k, v in _PREFIXES.items() if k in model_name.lower()), ("", ""))
    if settings.query_prefix != "auto":
        q = settings.query_prefix
    if settings.passage_prefix != "auto":
        p = settings.passage_prefix
    return q, p


def corpus_refs() -> dict[str, str]:
    """source -> version, from the ingest manifest (empty if the corpus predates it)."""
    from threatlens.config import settings

    path = settings.processed_dir / "manifest.json"
    if not path.exists():
        return {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return {name: f"{m['ref']} ({m['documents']} docs)" for name, m in manifest.items()}
