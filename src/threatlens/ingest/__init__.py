"""Source-specific ingesters. Each exposes `ingest() -> int` writing data/processed/<source>.jsonl."""

from pathlib import Path

import httpx

from threatlens.config import settings

USER_AGENT = "ThreatLens/0.1 (portfolio research project)"


def download(url: str, dest: Path, *, force: bool = False) -> Path:
    """Download `url` to `dest` (cached unless force=True)."""
    if dest.exists() and not force:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream(
        "GET", url, headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=120
    ) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    return dest


def processed_path(source: str) -> Path:
    return settings.processed_dir / f"{source}.jsonl"
