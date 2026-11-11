"""Build-time check for the demo image: every source made it into the index."""

import json
import sys

from threatlens.config import settings

meta = json.loads((settings.index_dir / "meta.json").read_text(encoding="utf-8"))
missing = [s for s in ("attack", "kev", "sigma", "certfr") if s not in meta.get("corpus", {})]
print(f"{meta['n_chunks']} chunks, corpus: {meta.get('corpus')}")
if missing or meta["n_chunks"] < 5000:
    sys.exit(f"incomplete index: missing {missing or 'chunks'}")
