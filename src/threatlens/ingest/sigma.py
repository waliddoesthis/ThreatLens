"""SigmaHQ detection rules (YAML) from the GitHub master archive.

Falls back to a shallow `git clone` when the archive download is refused (some proxies
allow git but not codeload.github.com).
"""

import shutil
import subprocess
import zipfile
from collections.abc import Iterator
from pathlib import Path

import httpx
import yaml

from threatlens.config import settings
from threatlens.ingest import download, processed_path
from threatlens.schema import Document, write_jsonl

URL = "https://github.com/SigmaHQ/sigma/archive/refs/heads/master.zip"
GIT_URL = "https://github.com/SigmaHQ/sigma"


def rule_to_doc(rule: dict, path: str) -> Document | None:
    if not isinstance(rule, dict) or "title" not in rule or "id" not in rule:
        return None
    tags = rule.get("tags", []) or []
    techniques = [
        t.split(".", 1)[1].upper() for t in tags if t.startswith("attack.t") and t[8:9].isdigit()
    ]
    logsource = rule.get("logsource", {}) or {}
    detection = yaml.safe_dump(rule.get("detection", {}), sort_keys=False, allow_unicode=True)
    text = (
        f"Sigma rule: {rule['title']}\nLevel: {rule.get('level', '')}  "
        f"Status: {rule.get('status', '')}\n"
        f"Log source: {', '.join(f'{k}={v}' for k, v in logsource.items())}\n"
        f"ATT&CK: {', '.join(techniques)}\n\n{rule.get('description', '')}\n\n"
        f"Detection logic:\n{detection}"
    )
    return Document(
        id=f"sigma:{rule['id']}",
        source="sigma",
        title=rule["title"],
        text=text,
        url=f"https://github.com/SigmaHQ/sigma/blob/master/{path}",
        metadata={"techniques": techniques, "level": rule.get("level"), "logsource": logsource},
    )


def _from_zip(path: Path) -> Iterator[tuple[str, bytes]]:
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            # sigma-master/rules/**.yml -> rules/**.yml
            parts = name.split("/", 1)
            if len(parts) == 2:
                yield parts[1], z.read(name)


def _from_dir(root: Path) -> Iterator[tuple[str, bytes]]:
    for f in sorted((root / "rules").rglob("*.yml")):
        yield f.relative_to(root).as_posix(), f.read_bytes()


def _fetch(force: bool) -> Iterator[tuple[str, bytes]]:
    try:
        return _from_zip(download(URL, settings.raw_dir / "sigma-master.zip", force=force))
    except httpx.HTTPError as e:
        print(f"[sigma] archive download failed ({e}); falling back to git clone")
    repo = settings.raw_dir / "sigma"
    if force or not (repo / "rules").is_dir():
        shutil.rmtree(repo, ignore_errors=True)
        subprocess.run(["git", "clone", "-q", "--depth", "1", GIT_URL, str(repo)], check=True)
    return _from_dir(repo)


def parse_files(files: Iterator[tuple[str, bytes]]) -> list[Document]:
    docs = []
    for path, data in files:
        # keep only the main rule set: rules/**.yml
        if not path.startswith("rules/") or not path.endswith(".yml"):
            continue
        try:
            rule = yaml.safe_load(data)
        except yaml.YAMLError:
            continue
        doc = rule_to_doc(rule, path)
        if doc:
            docs.append(doc)
    return docs


def ingest(force: bool = False) -> int:
    return write_jsonl(processed_path("sigma"), parse_files(_fetch(force)))
