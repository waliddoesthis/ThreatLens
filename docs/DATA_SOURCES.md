# Data sources

All public. Check each licence before redistributing data; the repo ships **code to download**, not the data.

| Source | What | URL | Format | Licence / terms |
|---|---|---|---|---|
| MITRE ATT&CK Enterprise | techniques, sub-techniques, mitigations, groups | https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json | STIX 2.1 JSON | ATT&CK Terms of Use (free, attribution) |
| CISA KEV | CVEs known to be exploited in the wild | https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json (mirror: github.com/cisagov/kev-data) | JSON | US Gov public domain |
| NVD | CVE descriptions, CVSS, CWE | https://services.nvd.nist.gov/rest/json/cves/2.0 | JSON API (rate-limited; API key recommended) | public, NVD terms |
| SigmaHQ | detection rules (YAML) | https://github.com/SigmaHQ/sigma (archive of `master`) | YAML | Detection Rule License (DRL) 1.1 |
| CERT-FR | French security advisories (avis, alertes) | https://cert.cyber.gouv.fr/feed/ (formerly www.cert.ssi.gouv.fr) | RSS | Licence Ouverte / Etalab |

## Pinned versions
`make ingest` fetches fixed versions so a benchmark number can be reproduced later; they live in `src/threatlens/ingest/pins.py`. `DATA_PIN=latest` tracks upstream instead (fresh demo corpus). Each ingest writes `data/processed/manifest.json` (version, document count, hash per source), and the index and the eval reports copy it.

| Source | Pinned to | With `DATA_PIN=latest` |
|---|---|---|
| MITRE ATT&CK | release tag `ATT&CK-v20.1` of github.com/mitre/cti | `master` |
| CISA KEV | commit `2db0708eb3cd` (2026-11-10) of github.com/cisagov/kev-data | live cisa.gov feed |
| SigmaHQ | release tag `r2026-07-01` | `master` |
| CERT-FR | RSS feed (rolling, ~40 items) + the advisories listed in `CERTFR_PINNED`, fetched by reference from `https://www.cert.cyber.gouv.fr/<avis\|alerte\|cti>/<ref>/` (`/json/` when it exists) + everything an earlier ingest already stored | same |

## Evaluation-only sources (never indexed)
| Source | What | URL | Licence |
|---|---|---|---|
| Atomic Red Team | command lines labelled with the ATT&CK technique they exercise; `eval/build_alert_questions.py` turns them into `eval/questions_alerts.jsonl` (built from commit `a0e3f9bc`, 2026-11-06) | https://github.com/redcanaryco/atomic-red-team | MIT |

Optional later: FIRST EPSS scores (https://api.first.org/data/v1/epss) for exploit probability; MITRE CAPEC; ANSSI guides.

## Record schema (data/processed/*.jsonl)
```json
{"id": "attack:T1059.001", "source": "attack", "title": "PowerShell",
 "text": "...", "url": "https://attack.mitre.org/techniques/T1059/001/",
 "metadata": {"tactics": ["execution"], "platforms": ["Windows"]}}
```
