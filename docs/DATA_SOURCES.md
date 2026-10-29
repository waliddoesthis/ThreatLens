# Data sources

All public. Check each licence before redistributing data; the repo ships **code to download**, not the data.

| Source | What | URL | Format | Licence / terms |
|---|---|---|---|---|
| MITRE ATT&CK Enterprise | techniques, sub-techniques, mitigations, groups | https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json | STIX 2.1 JSON | ATT&CK Terms of Use (free, attribution) |
| CISA KEV | CVEs known to be exploited in the wild | https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json (mirror: github.com/cisagov/kev-data) | JSON | US Gov public domain |
| NVD | CVE descriptions, CVSS, CWE | https://services.nvd.nist.gov/rest/json/cves/2.0 | JSON API (rate-limited; API key recommended) | public, NVD terms |
| SigmaHQ | detection rules (YAML) | https://github.com/SigmaHQ/sigma (archive of `master`) | YAML | Detection Rule License (DRL) 1.1 |
| CERT-FR | French security advisories (avis, alertes) | https://www.cert.ssi.gouv.fr/feed/ | RSS | Licence Ouverte / Etalab |

Optional later: FIRST EPSS scores (https://api.first.org/data/v1/epss) for exploit probability; MITRE CAPEC; ANSSI guides.

## Record schema (data/processed/*.jsonl)
```json
{"id": "attack:T1059.001", "source": "attack", "title": "PowerShell",
 "text": "...", "url": "https://attack.mitre.org/techniques/T1059/001/",
 "metadata": {"tactics": ["execution"], "platforms": ["Windows"]}}
```
