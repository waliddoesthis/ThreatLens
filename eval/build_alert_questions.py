"""Build alert-style benchmark questions from Atomic Red Team.

python eval/build_alert_questions.py <path to an atomic-red-team checkout>
  -> eval/questions_alerts.jsonl

Each Atomic test is a real command line labelled with the ATT&CK technique it exercises, which
gives alert questions with gold labels nobody on this project wrote. Atomic Red Team is used
for evaluation only and is never indexed, so the corpus cannot contain the answer verbatim.

Selection is deterministic (no sampling): Windows tests run from cmd or PowerShell, input
arguments replaced by their defaults, single-command tests only (the one line is the
behaviour, with no setup lines to mislabel), at most PER_TECHNIQUE tests per technique. Commands that name a technique id (paths like atomics\\T1218.005\\...) are dropped
because they would leak the label to BM25.
"""

import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).parent
OUT = HERE / "questions_alerts.jsonl"
PER_TECHNIQUE = 1
MIN_LEN, MAX_LEN = 25, 240
_ARG = re.compile(r"#\{([^}]+)\}")
_LEAK = re.compile(r"\bT\d{4}\b|atomic|PathToAtomicsFolder|ExternalPayloads", re.I)
TEMPLATES = {
    "command_prompt": [
        "Process creation: {cmd}",
        "EDR alert on a workstation, command line: {cmd}",
        "{cmd} was run from cmd.exe on a server. What is this?",
    ],
    "powershell": [
        "PowerShell script block log (event 4104): {cmd}",
        "Alert: powershell.exe executed: {cmd}",
        "{cmd} seen in PowerShell logs. What technique is this and how do I detect it?",
    ],
}


def command_line(test: dict) -> str | None:
    """A single-command test's command line with input arguments filled in, else None."""
    ex = test.get("executor") or {}
    if ex.get("name") not in TEMPLATES or "windows" not in (test.get("supported_platforms") or []):
        return None
    defaults = {
        k: str(v.get("default", "")) for k, v in (test.get("input_arguments") or {}).items()
    }
    lines = [ln.strip() for ln in str(ex.get("command", "")).splitlines()]
    lines = [ln for ln in lines if ln and not ln.startswith(("#", "REM ", "::", "echo "))]
    if len(lines) != 1:  # multi-line tests start with setup (TLS settings, variables, test files)
        return None
    cmd = _ARG.sub(lambda m: defaults.get(m.group(1), ""), lines[0])
    cmd = re.sub(r"\s+", " ", cmd).strip()
    if not MIN_LEN <= len(cmd) <= MAX_LEN or _LEAK.search(cmd):
        return None
    return cmd


def build(atomics: Path, known: set[str] | None = None) -> list[dict]:
    out: list[dict] = []
    for f in sorted(atomics.glob("T*/T*.yaml")):
        doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        gold = f"attack:{doc['attack_technique']}"
        if known is not None and gold not in known:
            continue
        kept = 0
        for test in doc.get("atomic_tests") or []:
            cmd = command_line(test)
            if cmd is None:
                continue
            templates = TEMPLATES[test["executor"]["name"]]
            out.append(
                {
                    "id": f"a{len(out) + 1:03d}",
                    "type": "alert_atomic",
                    "question": templates[len(out) % len(templates)].format(cmd=cmd),
                    "gold_ids": [gold],
                    "atomic_guid": test.get("auto_generated_guid", ""),
                }
            )
            kept += 1
            if kept >= PER_TECHNIQUE:
                break
    return out


def main() -> None:
    repo = Path(sys.argv[1])
    from threatlens.config import settings

    attack = settings.processed_dir / "attack.jsonl"
    known = None
    if attack.exists():
        with attack.open(encoding="utf-8") as f:
            known = {json.loads(line)["id"] for line in f}
    qs = build(repo / "atomics", known)
    with OUT.open("w", encoding="utf-8") as f:
        for q in qs:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    print(f"{len(qs)} alert questions -> {OUT}")


if __name__ == "__main__":
    main()
