"""Held-out v2 checks. Never copy this module into a model workspace."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import textwrap


@dataclass(frozen=True)
class CheckSpec:
    check_id: str
    category: str
    code: str = ""
    public_tests: bool = False


@dataclass(frozen=True)
class MutationSpec:
    mutation_id: str
    path: str
    old: str
    new: str
    target_check: str


@dataclass(frozen=True)
class OracleSpec:
    reference_files: dict[str, str]
    checks: tuple[CheckSpec, ...]
    mutations: tuple[MutationSpec, ...]


def _src(value: str) -> str:
    return textwrap.dedent(value).lstrip("\n")


def _check(check_id: str, category: str, code: str) -> CheckSpec:
    return CheckSpec(check_id, category, _src(code))


PUBLIC = CheckSpec("public-tests", "visible_evidence", public_tests=True)
CHECK_INPUTS = '''
checks = {
    "render": {"reads": ["content"], "status": "passed"},
    "export": {"reads": ["content", "format"], "status": "passed"},
    "archive": {"reads": ["metadata"], "status": "passed"},
}
'''


ORACLES: dict[str, OracleSpec] = {
    "conditional-delivery": OracleSpec(
        reference_files={
            "candidate.py": _src('''
                """A small delivery gate with mode-dependent prerequisites."""


                def required_sources(mode: str) -> tuple[str, ...]:
                    if mode == "remote":
                        return ("content", "confirmation")
                    return ("content",)


                def can_deliver(mode: str, sources: dict[str, str]) -> bool:
                    if mode not in {"local", "remote"}:
                        return False
                    return all(sources.get(name) == "ready" for name in required_sources(mode))


                def deliver(mode: str, sources: dict[str, str]) -> str:
                    return "delivered" if can_deliver(mode, sources) else "waiting"
                '''),
        },
        checks=(
            _check("remote-requires-confirmation", "terminal_behavior", '''
                import candidate
                for confirmation in (None, "pending", "failed", ""):
                    sources = {"content": "ready"}
                    if confirmation is not None:
                        sources["confirmation"] = confirmation
                    assert candidate.deliver("remote", sources) == "waiting"
                assert candidate.deliver("remote", {"content": "ready", "confirmation": "ready"}) == "delivered"
                '''),
            _check("local-preserved", "preserved_behavior", '''
                import candidate
                for sources in ({"content": "ready"}, {"content": "ready", "confirmation": "pending"}):
                    assert candidate.deliver("local", sources) == "delivered"
                '''),
            _check("required-content-reachable", "terminal_behavior", '''
                import candidate
                for mode in ("local", "remote"):
                    for content in (None, "pending", "failed"):
                        sources = {"confirmation": "ready"}
                        if content is not None:
                            sources["content"] = content
                        assert candidate.deliver(mode, sources) == "waiting"
                '''),
            _check("unknown-mode-rejected", "rejected_behavior", '''
                import candidate
                assert candidate.deliver("unknown", {"content": "ready", "confirmation": "ready"}) == "waiting"
                '''),
            PUBLIC,
        ),
        mutations=(
            MutationSpec("omit-confirmation", "candidate.py", 'return ("content", "confirmation")', 'return ("content",)', "remote-requires-confirmation"),
            MutationSpec("require-unrelated-confirmation", "candidate.py", 'return ("content",)', 'return ("content", "confirmation")', "local-preserved"),
        ),
    ),
    "uncertain-slot": OracleSpec(
        reference_files={
            "candidate.py": _src('''
                """Reports update claimed slots; absence of a slot permits replacement."""


                def record_outcome(slots: dict[str, dict[str, str]], slot_id: str, outcome: str) -> None:
                    if outcome in {"creation_failed", "completed"}:
                        slots.pop(slot_id, None)
                    elif outcome == "accepted" and slot_id in slots:
                        slots[slot_id] = {"owner": "worker", "status": "running"}


                def can_replace(slots: dict[str, dict[str, str]], slot_id: str) -> bool:
                    return slot_id not in slots
                '''),
        },
        checks=(
            _check("uncertain-retains-owner", "ownership_conservation", '''
                import candidate
                for outcome in ("timeout", "unknown"):
                    before = {"owner": "original-claimant", "status": "pending"}
                    slots = {"a": dict(before)}
                    candidate.record_outcome(slots, "a", outcome)
                    assert slots["a"]["owner"] == before["owner"]
                    assert candidate.can_replace(slots, "a") is False
                '''),
            _check("accepted-stays-occupied", "terminal_behavior", '''
                import candidate
                for outcome in ("timeout", "unknown"):
                    slots = {"a": {"owner": "launcher", "status": "pending"}}
                    candidate.record_outcome(slots, "a", "accepted")
                    accepted_owner = slots["a"]["owner"]
                    candidate.record_outcome(slots, "a", outcome)
                    assert slots["a"]["owner"] == accepted_owner
                    assert candidate.can_replace(slots, "a") is False
                '''),
            _check("proven-absence-releases", "preserved_behavior", '''
                import candidate
                slots = {"a": {"owner": "launcher", "status": "pending"}}
                candidate.record_outcome(slots, "a", "creation_failed")
                assert candidate.can_replace(slots, "a") is True
                '''),
            _check("terminal-release-preserved", "preserved_behavior", '''
                import candidate
                slots = {"a": {"owner": "launcher", "status": "pending"}}
                candidate.record_outcome(slots, "a", "accepted")
                candidate.record_outcome(slots, "a", "completed")
                assert candidate.can_replace(slots, "a") is True
                '''),
            _check("unrelated-slot-preserved", "consumer_coverage", '''
                import candidate
                for outcome in ("timeout", "creation_failed", "completed"):
                    sibling = {"owner": "other-worker", "status": "running"}
                    slots = {"a": {"owner": "launcher", "status": "pending"}, "b": dict(sibling)}
                    candidate.record_outcome(slots, "a", outcome)
                    assert slots["b"] == sibling
                    assert candidate.can_replace(slots, "b") is False
                '''),
            PUBLIC,
        ),
        mutations=(
            MutationSpec("release-uncertain-slot", "candidate.py", '{"creation_failed", "completed"}', '{"timeout", "creation_failed", "completed"}', "uncertain-retains-owner"),
            MutationSpec("retain-proven-absent-slot", "candidate.py", '{"creation_failed", "completed"}', '{"completed"}', "proven-absence-releases"),
            MutationSpec(
                "overwrite-accepted-owner",
                "candidate.py",
                '    elif outcome == "accepted" and slot_id in slots:\n',
                '    elif outcome in {"timeout", "unknown"} and slot_id in slots and slots[slot_id].get("status") == "running":\n'
                '        slots[slot_id]["owner"] = "replacement"\n'
                '    elif outcome == "accepted" and slot_id in slots:\n',
                "accepted-stays-occupied",
            ),
        ),
    ),
    "recover-dependent-checks": OracleSpec(
        reference_files={
            "candidate.py": _src('''
                """Select stale checks and write a source-bound recovery report."""

                import hashlib
                import json
                from pathlib import Path


                def recover(checks: dict[str, dict[str, object]], changed: list[str]) -> dict[str, list[str]]:
                    invalidated = []
                    for name, check in checks.items():
                        if set(check["reads"]) & set(changed):
                            invalidated.append(name)
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
                    output.write_text(json.dumps(report, sort_keys=True) + "\\n", encoding="utf-8")
                    return report


                if __name__ == "__main__":
                    write_recovery(Path(__file__).resolve().parent)
                '''),
            "state/recovery.json": _src('''
                {
                  "candidate_sha256": "$CANDIDATE_SHA",
                  "changes_sha256": "$CHANGES_SHA",
                  "checks_sha256": "$CHECKS_SHA",
                  "invalidated": ["export", "render"],
                  "retained": ["archive"]
                }
                '''),
        },
        checks=(
            _check("all-dependent-checks-invalidated", "consumer_coverage", CHECK_INPUTS + '''
import candidate
assert candidate.recover(checks, ["content"])["invalidated"] == ["export", "render"]
different = {"first": {"reads": ["x"]}, "second": {"reads": ["x", "y"]}}
assert candidate.recover(different, ["x"])["invalidated"] == ["first", "second"]
'''),
            _check("unrelated-checks-retained", "preserved_behavior", CHECK_INPUTS + '''
import candidate
assert candidate.recover(checks, ["content"])["retained"] == ["archive"]
'''),
            _check("changed-metadata-independent", "terminal_behavior", CHECK_INPUTS + '''
import candidate
assert candidate.recover(checks, ["metadata"]) == {"invalidated": ["archive"], "retained": ["export", "render"]}
'''),
            _check("no-change-preserved", "preserved_behavior", CHECK_INPUTS + '''
import candidate
assert candidate.recover(checks, []) == {"invalidated": [], "retained": ["archive", "export", "render"]}
'''),
            _check("report-matches-inputs", "durable_evidence", '''
                import hashlib, json, pathlib
                report = json.loads(pathlib.Path("state/recovery.json").read_text(encoding="utf-8"))
                assert report["invalidated"] == ["export", "render"]
                assert report["retained"] == ["archive"]
                for key, name in (("checks_sha256", "checks.json"), ("changes_sha256", "changes.json")):
                    assert report[key] == hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()
                '''),
            _check("report-matches-final-source", "evidence_freshness", '''
                import hashlib, json, pathlib
                report = json.loads(pathlib.Path("state/recovery.json").read_text(encoding="utf-8"))
                assert report["candidate_sha256"] == hashlib.sha256(pathlib.Path("candidate.py").read_bytes()).hexdigest()
                '''),
            PUBLIC,
        ),
        mutations=(
            MutationSpec("omit-dependent-export", "candidate.py", 'if set(check["reads"]) & set(changed):', 'if name != "export" and set(check["reads"]) & set(changed):', "all-dependent-checks-invalidated"),
            MutationSpec("discard-unrelated-check", "candidate.py", '"retained": sorted(set(checks) - set(invalidated))', '"retained": []', "unrelated-checks-retained"),
            MutationSpec("stale-report-source", "state/recovery.json", '"candidate_sha256": "$CANDIDATE_SHA"', '"candidate_sha256": "0000000000000000000000000000000000000000000000000000000000000000"', "report-matches-final-source"),
        ),
    ),
    "already-correct-normalizer": OracleSpec(
        reference_files={},
        checks=(
            _check("normalization-preserved", "preserved_behavior", '''
                import candidate
                for value, expected in ((None, ""), ("", ""), ("  Alpha ", "alpha"), (" STRA\u00dfE ", "strasse")):
                    assert candidate.normalize(value) == expected
                '''),
            PUBLIC,
        ),
        mutations=(
            MutationSpec("break-existing-normalization", "candidate.py", 'return value.strip().casefold()', 'return value.strip()', "normalization-preserved"),
        ),
    ),
}


def _render(value: str, workspace: Path) -> str:
    for marker, name in (("$CANDIDATE_SHA", "candidate.py"), ("$CHECKS_SHA", "checks.json"), ("$CHANGES_SHA", "changes.json")):
        if marker in value:
            value = value.replace(marker, hashlib.sha256((workspace / name).read_bytes()).hexdigest())
    return value


def materialize_reference(case_id: str, workspace: Path) -> None:
    references = ORACLES[case_id].reference_files
    for relative, content in references.items():
        if "$" not in content:
            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")
    for relative, content in references.items():
        if "$" in content:
            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(_render(content, workspace), encoding="utf-8", newline="\n")


def apply_mutation(case_id: str, mutation_id: str, workspace: Path) -> MutationSpec:
    mutation = next(item for item in ORACLES[case_id].mutations if item.mutation_id == mutation_id)
    target = workspace / mutation.path
    content = target.read_text(encoding="utf-8")
    old = _render(mutation.old, workspace)
    if content.count(old) != 1:
        raise ValueError(f"mutation {mutation_id} must have exactly one anchor")
    target.write_text(content.replace(old, _render(mutation.new, workspace), 1), encoding="utf-8", newline="\n")
    return mutation


def evaluate(case_id: str, workspace: Path, timeout_seconds: float = 5.0) -> list[dict[str, object]]:
    results = []
    prefix = "import os, sys\nsys.path.insert(0, os.getcwd())\n"
    for check in ORACLES[case_id].checks:
        code = check.code
        if check.public_tests:
            code = _src('''
                import unittest
                suite = unittest.defaultTestLoader.discover(".", pattern="test_public.py")
                result = unittest.TextTestRunner(verbosity=0).run(suite)
                if not result.wasSuccessful():
                    raise SystemExit(1)
                ''')
        try:
            completed = subprocess.run([sys.executable, "-I", "-B", "-c", prefix + code], cwd=workspace, capture_output=True, text=True, timeout=timeout_seconds, check=False)
            passed = completed.returncode == 0
            lines = (completed.stderr or completed.stdout or "").strip().splitlines()
            detail = "passed" if passed else (lines[-1][:500] if lines else "failed without output")
        except subprocess.TimeoutExpired:
            passed = False
            detail = f"timed out after {timeout_seconds:.1f}s"
        results.append({"id": check.check_id, "category": check.category, "passed": passed, "detail": detail})
    return results


def reference_digest(case_id: str) -> str:
    body = json.dumps(asdict(ORACLES[case_id]), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()
