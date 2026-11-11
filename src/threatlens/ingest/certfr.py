"""CERT-FR advisories (avis / alertes) from the public RSS feed.

The RSS only holds ~40 recent items, so two things keep the corpus stable:
- advisories listed in `pins.CERTFR_PINNED` are fetched by reference (JSON endpoint for avis and
  alertes, the HTML page otherwise), a handful of requests per ingest;
- advisories ingested earlier stay in data/processed/certfr.jsonl after they leave the feed.
"""

import re
from html import unescape

import feedparser
import httpx

from threatlens.ingest import USER_AGENT, pins, processed_path
from threatlens.schema import Document, read_jsonl, write_jsonl

# CERT-FR moved from www.cert.ssi.gouv.fr (now a redirect) to cert.cyber.gouv.fr in 2026
URL = "https://cert.cyber.gouv.fr/feed/"
SITE = "https://www.cert.cyber.gouv.fr"
_TAGS = re.compile(r"<[^>]+>")
_SCRIPT = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
_MAIN = re.compile(r"<main\b.*?</main>", re.S | re.I)
_TITLE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
# CERTFR-2026-AVI-1340 -> /avis/, -ALE- -> /alerte/, ...
_SECTIONS = {"AVI": "avis", "ALE": "alerte", "CTI": "cti", "ACT": "actualite", "IOC": "ioc"}


def _plain(html: str) -> str:
    return re.sub(r"\s+", " ", unescape(_TAGS.sub(" ", _SCRIPT.sub(" ", html)))).strip()


def advisory_url(ref: str) -> str:
    return f"{SITE}/{_SECTIONS[ref.split('-')[2]]}/{ref}/"


def parse_advisory_json(ref: str, data: dict) -> Document:
    """One advisory from CERT-FR's `<url>/json/` endpoint."""
    title = data.get("title", ref)
    revisions = data.get("revisions") or [{}]
    lines = [
        f"CERT-FR {ref}: {title}",
        f"Published: {revisions[0].get('revision_date', '')[:10]}",
        "",
        _plain(data.get("summary", "")),
    ]
    risks = [r.get("description", "") for r in data.get("risks") or []]
    systems = [s.get("description", "") for s in data.get("affected_systems") or []]
    cves = [c.get("name", "") for c in data.get("cves") or []]
    if risks:
        lines.append("Risques : " + " ; ".join(risks))
    if systems:
        lines.append("Systèmes affectés : " + " ; ".join(systems[:20]))
    if cves:
        lines.append("CVE : " + ", ".join(cves[:40]))
    return Document(
        id=f"certfr:{ref}",
        source="certfr",
        title=title,
        text="\n".join(lines),
        url=advisory_url(ref),
        metadata={"published": revisions[0].get("revision_date"), "cves": cves, "pinned": True},
    )


def parse_advisory_html(ref: str, html: str) -> Document:
    """Fallback for document types without a JSON endpoint (CTI reports)."""
    m = _TITLE.search(html)
    title = _plain(m.group(1)).removesuffix("- CERT-FR").strip() if m else ref
    body = _MAIN.search(html)
    text = _plain(body.group(0) if body else html)[:6000]
    return Document(
        id=f"certfr:{ref}",
        source="certfr",
        title=title,
        text=f"CERT-FR {ref}: {title}\n\n{text}",
        url=advisory_url(ref),
        metadata={"pinned": True},
    )


def fetch_advisory(ref: str) -> Document:
    headers = {"User-Agent": USER_AGENT}
    url = advisory_url(ref)
    r = httpx.get(url + "json/", headers=headers, follow_redirects=True, timeout=60)
    if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
        return parse_advisory_json(ref, r.json())
    r = httpx.get(url, headers=headers, follow_redirects=True, timeout=60)
    r.raise_for_status()
    if ref not in r.text:  # the site answers 200 with an error page for unknown references
        raise RuntimeError(f"CERT-FR has no page for {ref}")
    return parse_advisory_html(ref, r.text)


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
    merged = {d.id: d for d in docs}
    for ref in pins.CERTFR_PINNED:
        if f"certfr:{ref}" in merged:
            continue
        try:
            doc = fetch_advisory(ref)
            merged[doc.id] = doc
        except Exception as e:  # one missing page must not lose the whole source
            print(f"[certfr] pinned advisory {ref} not fetched: {e}")
    # keep what an earlier ingest saw and the feed has since dropped
    path = processed_path("certfr")
    if path.exists():
        for old in read_jsonl(path):
            merged.setdefault(old.id, old)
    return write_jsonl(path, sorted(merged.values(), key=lambda d: d.id))
