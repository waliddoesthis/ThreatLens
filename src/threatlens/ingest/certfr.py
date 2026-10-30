"""CERT-FR advisories (avis / alertes) from the public RSS feed.

The RSS only holds recent items. For a bigger corpus, a later step can crawl
https://cert.cyber.gouv.fr/avis/ pages politely (rate-limit, respect robots.txt).
"""

import re

import feedparser
import httpx

from threatlens.ingest import USER_AGENT, processed_path
from threatlens.schema import Document, write_jsonl

# CERT-FR moved from www.cert.ssi.gouv.fr (now a redirect) to cert.cyber.gouv.fr in 2026
URL = "https://cert.cyber.gouv.fr/feed/"
_TAGS = re.compile(r"<[^>]+>")


def parse(feed) -> list[Document]:
    docs = []
    for e in feed.entries:
        link = e.get("link", "")
        ref = link.rstrip("/").rsplit("/", 1)[-1] or e.get("id", "")
        summary = _TAGS.sub(" ", e.get("summary", "")).strip()
        text = (
            f"CERT-FR {ref}: {e.get('title', '')}\nPublished: {e.get('published', '')}\n\n{summary}"
        )
        docs.append(
            Document(
                id=f"certfr:{ref}",
                source="certfr",
                title=e.get("title", ref),
                text=text,
                url=link,
                metadata={"published": e.get("published")},
            )
        )
    return docs


def ingest(force: bool = False) -> int:
    # fetch with httpx (honours proxies, raises on HTTP errors) instead of feedparser's own fetcher
    r = httpx.get(URL, headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=60)
    r.raise_for_status()
    docs = parse(feedparser.parse(r.content))
    if not docs:
        raise RuntimeError("CERT-FR feed returned no entries")
    return write_jsonl(processed_path("certfr"), docs)
