"""Run all ingesters: python -m threatlens.ingest.run [--force] [--only attack kev ...]"""

import argparse

from threatlens.ingest import attack, certfr, kev, sigma

INGESTERS = {"attack": attack, "kev": kev, "sigma": sigma, "certfr": certfr}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="re-download raw files")
    p.add_argument("--only", nargs="*", choices=list(INGESTERS), default=list(INGESTERS))
    args = p.parse_args()
    for name in args.only:
        try:
            n = INGESTERS[name].ingest(force=args.force)
            print(f"[ok] {name:7s} {n:6d} documents")
        except Exception as e:  # keep going if one source is down
            print(f"[!!] {name:7s} failed: {e}")


if __name__ == "__main__":
    main()
