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


def test_clean_stix_text_drops_citations_and_links():
    from threatlens.ingest import clean_stix_text

    raw = (
        "Adversaries may abuse [PowerShell](https://attack.mitre.org/techniques/T1059/001) "
        "commands.(Citation: TechNet PowerShell) It is common. (Citation: A)(Citation: B)"
    )
    assert clean_stix_text(raw) == "Adversaries may abuse PowerShell commands. It is common."


def test_pins_select_versioned_urls(monkeypatch):
    from threatlens.config import settings
    from threatlens.ingest import attack, pins

    monkeypatch.setattr(settings, "data_pin", "pinned")
    assert pins.ref("attack") == pins.ATTACK_TAG
    assert "/ATT%26CK-v" in attack.source_url()  # the "&" in the tag must be URL-encoded
    monkeypatch.setattr(settings, "data_pin", "latest")
    assert pins.ref("sigma") == "latest" and "/master/" in attack.source_url()


def test_certfr_pinned_advisory_parsers():
    from threatlens.ingest.certfr import advisory_url, parse_advisory_html, parse_advisory_json

    doc = parse_advisory_json(
        "CERTFR-2026-ALE-013",
        {
            "title": "Vulnérabilité dans Ivanti",
            "summary": "<b>Mise à jour</b> : exploitation active.",
            "revisions": [{"revision_date": "2026-10-14T00:00:00"}],
            "risks": [{"description": "Exécution de code arbitraire à distance"}],
            "cves": [{"name": "CVE-2026-0001"}],
        },
    )
    assert doc.id == "certfr:CERTFR-2026-ALE-013" and doc.url.endswith(
        "/alerte/CERTFR-2026-ALE-013/"
    )
    assert "Mise à jour : exploitation active." in doc.text and "<b>" not in doc.text
    assert "CVE-2026-0001" in doc.text and "Published: 2026-10-14" in doc.text

    html = "<html><title>Rapport Apple - CERT-FR</title><main><script>x()</script><p>Pegasus</p></main></html>"
    doc = parse_advisory_html("CERTFR-2025-CTI-010", html)
    assert doc.title == "Rapport Apple" and doc.text.endswith("Pegasus")
    assert advisory_url("CERTFR-2025-CTI-010").endswith("/cti/CERTFR-2025-CTI-010/")


def test_certfr_ingest_keeps_archived_and_pinned(monkeypatch, tmp_path):
    from threatlens.config import settings
    from threatlens.ingest import certfr, pins
    from threatlens.schema import Document, read_jsonl, write_jsonl

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    old = Document("certfr:CERTFR-2025-AVI-0009", "certfr", "old", "rolled off the feed", "u")
    write_jsonl(settings.processed_dir / "certfr.jsonl", [old])
    monkeypatch.setattr(pins, "CERTFR_PINNED", ("CERTFR-2026-AVI-1340",))
    monkeypatch.setattr(
        certfr, "fetch_advisory", lambda ref: Document(f"certfr:{ref}", "certfr", "p", "p", "u")
    )

    class Resp:
        content = RSS.encode()

        def raise_for_status(self):
            pass

    monkeypatch.setattr(certfr.httpx, "get", lambda *a, **k: Resp())

    assert certfr.ingest() == 3
    ids = [d.id for d in read_jsonl(settings.processed_dir / "certfr.jsonl")]
    assert ids == [
        "certfr:CERTFR-2025-AVI-0009",
        "certfr:CERTFR-2026-AVI-0001",
        "certfr:CERTFR-2026-AVI-1340",
    ]
