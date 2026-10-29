"""NVD CVE lookup (on demand — the full NVD is too big for the MVP index)."""

import httpx

from threatlens.config import settings
from threatlens.ingest import USER_AGENT
from threatlens.schema import Document

API = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def fetch_cve(cve_id: str) -> Document | None:
    headers = {"User-Agent": USER_AGENT}
    if settings.nvd_api_key:
        headers["apiKey"] = settings.nvd_api_key
    r = httpx.get(API, params={"cveId": cve_id}, headers=headers, timeout=30)
    r.raise_for_status()
    vulns = r.json().get("vulnerabilities", [])
    if not vulns:
        return None
    cve = vulns[0]["cve"]
    desc = next((d["value"] for d in cve.get("descriptions", []) if d["lang"] == "en"), "")
    cvss = ""
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        if key in cve.get("metrics", {}):
            m = cve["metrics"][key][0]["cvssData"]
            cvss = f"{m.get('baseScore')} ({m.get('baseSeverity', '')}) {m.get('vectorString', '')}"
            break
    text = f"{cve_id} (NVD)\nPublished: {cve.get('published', '')}\nCVSS: {cvss}\n\n{desc}"
    return Document(
        id=f"nvd:{cve_id}",
        source="nvd",
        title=cve_id,
        text=text,
        url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
        metadata={"cvss": cvss},
    )
