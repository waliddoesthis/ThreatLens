"""Parser tests for Sigma, CERT-FR and NVD — offline, using small fixtures."""

import zipfile

import feedparser

from threatlens.ingest import nvd
from threatlens.ingest.certfr import parse as parse_certfr
from threatlens.ingest.sigma import _from_dir, _from_zip, parse_files, rule_to_doc

RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>CERT-FR</title>
<item>
  <title>Multiples vulnérabilités dans Fortinet FortiOS</title>
  <link>https://www.cert.ssi.gouv.fr/avis/CERTFR-2026-AVI-0001/</link>
  <description>&lt;p&gt;De multiples vulnérabilités ont été découvertes.&lt;/p&gt;</description>
  <pubDate>Mon, 05 Jan 2026 10:00:00 +0000</pubDate>
</item>
</channel></rss>"""


def test_sigma_rule_to_doc_extracts_techniques():
    rule = {
        "title": "LSASS Memory Dump",
        "id": "abc-123",
        "level": "high",
        "tags": ["attack.credential-access", "attack.t1003.001"],
        "logsource": {"product": "windows", "category": "process_access"},
        "detection": {
            "selection": {"TargetImage|endswith": "\\lsass.exe"},
            "condition": "selection",
        },
    }
    doc = rule_to_doc(rule, "rules/windows/x.yml")
    assert doc.id == "sigma:abc-123"
    assert doc.metadata["techniques"] == ["T1003.001"]
    assert "lsass.exe" in doc.text and doc.url.endswith("rules/windows/x.yml")


def test_sigma_rule_without_id_is_skipped():
    assert rule_to_doc({"title": "no id"}, "rules/x.yml") is None
    assert rule_to_doc(["not", "a", "dict"], "rules/x.yml") is None


RULE_YML = b"""title: Test Rule
id: 11111111-2222-3333-4444-555555555555
tags: [attack.execution, attack.t1059.001]
logsource: {product: windows, category: process_creation}
detection: {selection: {Image|endswith: '\\powershell.exe'}, condition: selection}
"""


def test_sigma_reads_zip_and_git_checkout_identically(tmp_path):
    files = {
        "rules/windows/a.yml": RULE_YML,
        "rules/windows/broken.yml": b"title: [unclosed",
        "deprecated/old.yml": RULE_YML.replace(b"1111", b"9999"),
        "rules/README.md": b"not a rule",
    }
    zpath = tmp_path / "sigma-master.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for name, data in files.items():
            z.writestr(f"sigma-master/{name}", data)
    repo = tmp_path / "sigma"
    for name, data in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_bytes(data)

    from_zip = parse_files(_from_zip(zpath))
    from_dir = parse_files(_from_dir(repo))
    assert [d.id for d in from_zip] == ["sigma:11111111-2222-3333-4444-555555555555"]
    assert from_zip == from_dir
    assert from_zip[0].url.endswith("/rules/windows/a.yml")


def test_certfr_parse():
    docs = parse_certfr(feedparser.parse(RSS))
    assert [d.id for d in docs] == ["certfr:CERTFR-2026-AVI-0001"]
    assert "Fortinet" in docs[0].text and "<p>" not in docs[0].text


class _Resp:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._payload


def test_nvd_fetch_cve(monkeypatch):
    payload = {
        "vulnerabilities": [
            {
                "cve": {
                    "published": "2024-04-12",
                    "descriptions": [{"lang": "en", "value": "Command injection in PAN-OS."}],
                    "metrics": {
                        "cvssMetricV31": [
                            {"cvssData": {"baseScore": 10.0, "baseSeverity": "CRITICAL"}}
                        ]
                    },
                }
            }
        ]
    }
    monkeypatch.setattr(nvd.httpx, "get", lambda *a, **k: _Resp(payload))
    doc = nvd.fetch_cve("CVE-2024-3400")
    assert doc.id == "nvd:CVE-2024-3400"
    assert "10.0 (CRITICAL)" in doc.text and "PAN-OS" in doc.text


def test_nvd_unknown_cve(monkeypatch):
    monkeypatch.setattr(nvd.httpx, "get", lambda *a, **k: _Resp({"vulnerabilities": []}))
    assert nvd.fetch_cve("CVE-2099-0001") is None
