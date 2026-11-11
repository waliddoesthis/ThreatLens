"""Pinned versions of every data source, so a benchmark number can be reproduced later.

`DATA_PIN=pinned` (default) ingests exactly these versions. `DATA_PIN=latest` tracks upstream
(ATT&CK and Sigma default branches, the live KEV feed) for a fresh demo corpus. To move a pin:
change it here, re-run `make ingest index eval`, and log the new numbers in docs/DECISIONS.md.
"""

from threatlens.config import settings

ATTACK_TAG = "ATT&CK-v20.1"  # github.com/mitre/cti release tag
SIGMA_TAG = "r2026-07-01"  # github.com/SigmaHQ/sigma release tag
KEV_COMMIT = "2db0708eb3cd0aad3cecee8e072f34d8e011b3a6"  # github.com/cisagov/kev-data, 2026-11-10

# CERT-FR's RSS feed only keeps ~40 recent items. Advisories the benchmark relies on are fetched
# by reference so they do not roll off (eval/questions.jsonl, type "certfr").
CERTFR_PINNED = (
    "CERTFR-2026-AVI-1340",
    "CERTFR-2026-AVI-1428",
    "CERTFR-2026-AVI-1442",
    "CERTFR-2026-AVI-1444",
    "CERTFR-2026-ALE-013",
    "CERTFR-2025-CTI-010",
)


def pinned() -> bool:
    return settings.data_pin != "latest"


def ref(source: str) -> str:
    """Version label of a source for the ingest manifest."""
    if source == "certfr":
        return f"rss + {len(CERTFR_PINNED)} pinned advisories + local archive"
    if not pinned():
        return "latest"
    return {"attack": ATTACK_TAG, "sigma": SIGMA_TAG, "kev": KEV_COMMIT[:12]}[source]
