"""CISA Known Exploited Vulnerabilities catalog."""

import json

import httpx

from threatlens.config import settings
from threatlens.ingest import download, processed_path
from threatlens.schema import Document, write_jsonl

URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
# Official CISA mirror on GitHub, used if cisa.gov refuses the request
MIRROR = (
    "https://raw.githubusercontent.com/cisagov/kev-data/main/known_exploited_vulnerabilities.json"
)


def parse(catalog: dict) -> list[Document]:
    docs = []
    for v in catalog.get("vulnerabilities", []):
        cve = v["cveID"]
        text = (
            f"{cve} — {v.get('vulnerabilityName', '')}\n"
            f"Vendor/product: {v.get('vendorProject', '')} {v.get('product', '')}\n"
            f"KNOWN EXPLOITED IN THE WILD (CISA KEV), added {v.get('dateAdded', '')}.\n"
            f"Known ransomware use: {v.get('knownRansomwareCampaignUse', 'Unknown')}\n"
            f"CWE: {', '.join(v.get('cwes', []) or [])}\n\n"
            f"{v.get('shortDescription', '')}\n\nRequired action: {v.get('requiredAction', '')}"
        )
        docs.append(
            Document(
                id=f"kev:{cve}",
                source="kev",
                title=f"{cve} {v.get('vulnerabilityName', '')}",
                text=text,
                url=f"https://nvd.nist.gov/vuln/detail/{cve}",
                metadata={
                    "cve": cve,
                    "vendor": v.get("vendorProject"),
                    "product": v.get("product"),
                    "date_added": v.get("dateAdded"),
                    "ransomware": v.get("knownRansomwareCampaignUse"),
                },
            )
        )
    return docs


def ingest(force: bool = False) -> int:
    dest = settings.raw_dir / "kev.json"
    try:
        raw = download(URL, dest, force=force)
    except httpx.HTTPError as e:
        print(f"[kev] cisa.gov failed ({e}); using GitHub mirror")
        raw = download(MIRROR, dest, force=True)
    return write_jsonl(processed_path("kev"), parse(json.loads(raw.read_text(encoding="utf-8"))))
