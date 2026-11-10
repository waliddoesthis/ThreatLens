"""Run all ingesters: python -m threatlens.ingest.run [--force] [--only attack kev ...]"""

import argparse
import hashlib
import json
from datetime import UTC, datetime

from threatlens.config import settings
from threatlens.ingest import attack, certfr, kev, pins, processed_path, sigma

INGESTERS = {"attack": attack, "kev": kev, "sigma": sigma, "certfr": certfr}


def write_manifest(counts: dict[str, int]) -> dict:
    """data/processed/manifest.json: which version of each source this corpus was built from.

    Sources not ingested in this run keep their previous entry. The index build and the eval
    reports copy it, so every number can be traced to a corpus.
    """
    path = settings.processed_dir / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for name, n in counts.items():
        manifest[name] = {
            "ref": pins.ref(name),
            "documents": n,
            "sha256": hashlib.sha256(processed_path(name).read_bytes()).hexdigest()[:16],
            "ingested_at": datetime.now(UTC).strftime("%Y-%m-%d"),
        }
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="re-download raw files")
    p.add_argument("--only", nargs="*", choices=list(INGESTERS), default=list(INGESTERS))
    args = p.parse_args()
    counts: dict[str, int] = {}
    for name in args.only:
        try:
            n = INGESTERS[name].ingest(force=args.force)
            counts[name] = n
            print(f"[ok] {name:7s} {n:6d} documents  ({pins.ref(name)})")
        except Exception as e:  # keep going if one source is down
            print(f"[!!] {name:7s} failed: {e}")
    write_manifest(counts)


if __name__ == "__main__":
    main()
