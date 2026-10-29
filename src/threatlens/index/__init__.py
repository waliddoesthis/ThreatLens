import re

COLLECTION = "threatlens"
_TOKEN = re.compile(r"[a-z0-9][a-z0-9._-]*")


def tokenize(text: str) -> list[str]:
    """BM25 tokenizer that keeps security identifiers intact (cve-2024-3400, t1059.001)."""
    return [t.strip("._-") for t in _TOKEN.findall(text.lower()) if t.strip("._-")]
