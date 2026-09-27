"""Select stale checks and write a source-bound recovery report."""

import hashlib
import json
from pathlib import Path


def recover(checks: dict[str, dict[str, object]], changed: list[str]) -> dict[str, list[str]]:
    invalidated = []
    for name, check in checks.items():
        if set(check["reads"]) & set(changed):
            invalidated.append(name)
            break
    return {"invalidated": sorted(invalidated), "retained": sorted(set(checks) - set(invalidated))}


def write_recovery(root: Path) -> dict[str, object]:
    checks_raw = (root / "checks.json").read_bytes()
    changes_raw = (root / "changes.json").read_bytes()
    report = recover(json.loads(checks_raw), json.loads(changes_raw))
    report.update(
        candidate_sha256=hashlib.sha256((root / "candidate.py").read_bytes()).hexdigest(),
        checks_sha256=hashlib.sha256(checks_raw).hexdigest(),
        changes_sha256=hashlib.sha256(changes_raw).hexdigest(),
    )
    output = root / "state" / "recovery.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    write_recovery(Path(__file__).resolve().parent)
