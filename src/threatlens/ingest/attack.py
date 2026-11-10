"""MITRE ATT&CK Enterprise (STIX 2.1) -> techniques + mitigations."""

import json
from urllib.parse import quote

from threatlens.config import settings
from threatlens.ingest import clean_stix_text, download, pins, processed_path
from threatlens.schema import Document, write_jsonl

_URL = "https://raw.githubusercontent.com/mitre/cti/{ref}/enterprise-attack/enterprise-attack.json"


def source_url() -> str:
    return _URL.format(ref=quote(pins.ATTACK_TAG) if pins.pinned() else "master")


def _attack_ref(obj: dict) -> tuple[str, str]:
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            return ref.get("external_id", ""), ref.get("url", "")
    return "", ""


def mitigations_by_technique(bundle: dict) -> dict[str, list[str]]:
    """Technique id -> mitigation ids, from STIX `mitigates` relationships.

    The relationship objects are the edges of ATT&CK's own graph; keeping them lets the pipeline
    answer "how do I mitigate T1003.001" by following a link instead of hoping retrieval finds it.
    """
    ext: dict[str, str] = {}
    for obj in bundle.get("objects", []):
        if obj.get("type") in ("attack-pattern", "course-of-action") and not (
            obj.get("revoked") or obj.get("x_mitre_deprecated")
        ):
            ext[obj.get("id", "")] = _attack_ref(obj)[0]
    out: dict[str, list[str]] = {}
    for obj in bundle.get("objects", []):
        if obj.get("type") != "relationship" or obj.get("relationship_type") != "mitigates":
            continue
        if obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue
        mit, tech = ext.get(obj.get("source_ref", "")), ext.get(obj.get("target_ref", ""))
        # ATT&CK also files old "T1xxx" course-of-action objects; only real mitigations are M ids
        if mit and tech and mit.startswith("M") and mit not in out.setdefault(tech, []):
            out[tech].append(mit)
    return {t: sorted(m) for t, m in out.items()}


def parse(bundle: dict) -> list[Document]:
    docs: list[Document] = []
    mitigations = mitigations_by_technique(bundle)
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
        desc = clean_stix_text(obj.get("description", ""))
        if typ == "attack-pattern":
            tactics = [p["phase_name"] for p in obj.get("kill_chain_phases", [])]
            platforms = obj.get("x_mitre_platforms", [])
            detection = clean_stix_text(obj.get("x_mitre_detection", ""))
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
                "mitigations": mitigations.get(ext_id, []),
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
    # one raw file per version, so switching the pin never reuses another version's download
    raw = download(
        source_url(), settings.raw_dir / f"enterprise-attack-{pins.ref('attack')}.json", force=force
    )
    bundle = json.loads(raw.read_text(encoding="utf-8"))
    return write_jsonl(processed_path("attack"), parse(bundle))
