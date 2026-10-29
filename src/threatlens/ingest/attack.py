"""MITRE ATT&CK Enterprise (STIX 2.1) -> techniques + mitigations."""

import json

from threatlens.config import settings
from threatlens.ingest import download, processed_path
from threatlens.schema import Document, write_jsonl

URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"


def _attack_ref(obj: dict) -> tuple[str, str]:
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            return ref.get("external_id", ""), ref.get("url", "")
    return "", ""


def parse(bundle: dict) -> list[Document]:
    docs: list[Document] = []
    for obj in bundle.get("objects", []):
        if obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue
        typ = obj.get("type")
        if typ not in ("attack-pattern", "course-of-action"):
            continue
        ext_id, url = _attack_ref(obj)
        if not ext_id:
            continue
        name = obj.get("name", "")
        desc = obj.get("description", "")
        if typ == "attack-pattern":
            tactics = [p["phase_name"] for p in obj.get("kill_chain_phases", [])]
            platforms = obj.get("x_mitre_platforms", [])
            detection = obj.get("x_mitre_detection", "")
            text = (
                f"ATT&CK technique {ext_id}: {name}\n"
                f"Tactics: {', '.join(tactics)}\nPlatforms: {', '.join(platforms)}\n\n{desc}"
            )
            if detection:
                text += f"\n\nDetection: {detection}"
            meta = {
                "kind": "technique",
                "tactics": tactics,
                "platforms": platforms,
                "is_subtechnique": obj.get("x_mitre_is_subtechnique", False),
            }
        else:
            text = f"ATT&CK mitigation {ext_id}: {name}\n\n{desc}"
            meta = {"kind": "mitigation"}
        docs.append(
            Document(
                id=f"attack:{ext_id}",
                source="attack",
                title=f"{ext_id} {name}",
                text=text,
                url=url,
                metadata=meta,
            )
        )
    return docs


def ingest(force: bool = False) -> int:
    raw = download(URL, settings.raw_dir / "enterprise-attack.json", force=force)
    bundle = json.loads(raw.read_text(encoding="utf-8"))
    return write_jsonl(processed_path("attack"), parse(bundle))
