#!/usr/bin/env python3
"""Prepare and score WISDOM authoring-time application-fidelity cases.

The evaluator launches a model separately. This script is deterministic local
infrastructure: it never calls a model API, network service, CI system, or hook.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
from typing import Any, Sequence


RUNNER_PATH = Path(__file__).resolve()
ROOT = RUNNER_PATH.parents[1]
EVAL_ROOT = ROOT / "evaluations" / "application_fidelity"
CASES_PATH = EVAL_ROOT / "cases.json"
ORACLES_PATH = EVAL_ROOT / "oracles.py"
PREPARATION_NAME = ".wisdom-eval-preparation.json"
SUITE_SCHEMA = "wisdom.behavioral_eval_suite.v1"
PREPARATION_SCHEMA = "wisdom.behavioral_eval_preparation.v1"
SCORE_SCHEMA = "wisdom.behavioral_eval_score.v1"
SUITE_V2_SCHEMA = "wisdom.behavioral_eval_suite.v2"
PREPARATION_V2_SCHEMA = "wisdom.behavioral_eval_preparation.v2"
SCORE_V2_SCHEMA = "wisdom.behavioral_eval_score.v2"
SUITE_IDS = ("v1", "v2")
CASE_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class EvaluationError(RuntimeError):
    """The evaluation corpus, preparation, or score request is invalid."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _safe_relative(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise EvaluationError(f"{field} must be a nonempty relative path")
    if "\\" in value or "\x00" in value:
        raise EvaluationError(f"{field} must use portable forward slashes")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or (path.parts and ":" in path.parts[0])
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise EvaluationError(f"{field} escapes its declared root: {value}")
    return path.as_posix()


def _is_transient_python_artifact(relative: str, *, is_directory: bool = False) -> bool:
    path = PurePosixPath(relative)
    tree_parts = path.parts if is_directory else path.parts[:-1]
    return any(part.casefold() in {"__pycache__", ".pytest_cache"} for part in tree_parts) or (
        not is_directory and path.suffix.casefold() == ".pyc"
    )


def _string_list(case: dict[str, Any], field: str, *, minimum: int = 1) -> list[str]:
    value = case.get(field)
    if not isinstance(value, list) or len(value) < minimum:
        raise EvaluationError(f"case {case.get('id')}: {field} must contain at least {minimum} item(s)")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise EvaluationError(f"case {case.get('id')}: {field} entries must be nonempty strings")
    if len(value) != len(set(value)):
        raise EvaluationError(f"case {case.get('id')}: {field} entries must be unique")
    return value


def _suite_paths(suite_id: str) -> tuple[Path, Path]:
    if suite_id not in SUITE_IDS:
        raise EvaluationError(f"unknown evaluation suite: {suite_id}")
    if suite_id == "v1":
        return CASES_PATH, ORACLES_PATH
    return EVAL_ROOT / "cases.v2.json", EVAL_ROOT / "oracles_v2.py"


def _load_oracles(suite_id: str = "v1") -> Any:
    _, oracle_path = _suite_paths(suite_id)
    module_name = f"wisdom_application_fidelity_oracles_{suite_id}"
    spec = importlib.util.spec_from_file_location(module_name, oracle_path)
    if spec is None or spec.loader is None:
        raise EvaluationError(f"cannot load held-out oracles from {oracle_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_suite(suite_id: str = "v1") -> tuple[dict[str, Any], dict[str, dict[str, Any]], Any]:
    cases_path, _ = _suite_paths(suite_id)
    expected_schema = SUITE_SCHEMA if suite_id == "v1" else SUITE_V2_SCHEMA
    try:
        suite = json.loads(cases_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"cannot read evaluation cases: {exc}") from exc
    if not isinstance(suite, dict) or suite.get("schema") != expected_schema:
        raise EvaluationError(f"evaluation suite must use schema {expected_schema}")
    cases_raw = suite.get("cases")
    if not isinstance(cases_raw, list) or not cases_raw:
        raise EvaluationError("evaluation suite must contain cases")
    oracles = _load_oracles(suite_id)
    cases: dict[str, dict[str, Any]] = {}
    for case in cases_raw:
        if not isinstance(case, dict):
            raise EvaluationError("each evaluation case must be an object")
        case_id = case.get("id")
        if not isinstance(case_id, str) or CASE_ID.fullmatch(case_id) is None:
            raise EvaluationError(f"invalid case id: {case_id!r}")
        if case_id in cases:
            raise EvaluationError(f"duplicate case id: {case_id}")
        _validate_case(case, oracles, suite_id=suite_id)
        cases[case_id] = case
    if set(cases) != set(oracles.ORACLES):
        raise EvaluationError(
            "case/oracle membership differs: "
            f"cases={sorted(cases)} oracles={sorted(oracles.ORACLES)}"
        )
    return suite, cases, oracles


def _validate_case(case: dict[str, Any], oracles: Any, *, suite_id: str = "v1") -> None:
    case_id = str(case["id"])
    for field in ("title", "task_profile"):
        if not isinstance(case.get(field), str) or not case[field].strip():
            raise EvaluationError(f"case {case_id}: {field} must be nonempty")
    for field in (
        "mechanisms",
        "expected_topology",
        "misleading_intermediate_evidence",
        "positive_witnesses",
        "negative_witnesses",
        "go_red_mutations",
        "critical_checks",
    ):
        _string_list(case, field)
    outcomes = case.get("outcomes")
    if not isinstance(outcomes, dict) or set(outcomes) != {"required", "forbidden", "preserved"}:
        raise EvaluationError(f"case {case_id}: outcomes must define required, forbidden, and preserved")
    for field in ("required", "forbidden", "preserved"):
        _string_list(outcomes, field)
    seed_root_text = _safe_relative(case.get("seed_root"), f"case {case_id} seed_root")
    expected_seed = f"seeds/{case_id}"
    if seed_root_text != expected_seed:
        raise EvaluationError(f"case {case_id}: seed_root must be {expected_seed}")
    seed_root = (EVAL_ROOT / Path(seed_root_text)).resolve()
    seeds_root = (EVAL_ROOT / "seeds").resolve()
    if seed_root.parent != seeds_root or not seed_root.is_dir():
        raise EvaluationError(f"case {case_id}: missing contained seed root")
    if any(path.is_symlink() for path in seed_root.rglob("*")):
        raise EvaluationError(f"case {case_id}: seed roots may not contain symlinks")
    task_file = _safe_relative(case.get("task_file"), f"case {case_id} task_file")
    if not (seed_root / task_file).is_file():
        raise EvaluationError(f"case {case_id}: task file is missing")
    allowed = [
        _safe_relative(path, f"case {case_id} allowed_mutation_paths")
        for path in _string_list(case, "allowed_mutation_paths", minimum=1 if suite_id == "v1" else 0)
    ]
    inventory = _inventory(seed_root, strict=suite_id == "v2")
    if any(path not in inventory for path in allowed):
        raise EvaluationError(f"case {case_id}: allowed mutation path is absent from seed")
    added: list[str] = []
    if suite_id == "v2":
        added = [
            _safe_relative(path, f"case {case_id} allowed_added_paths")
            for path in _string_list(case, "allowed_added_paths", minimum=0)
        ]
        all_allowed = allowed + added
        if allowed != case["allowed_mutation_paths"] or added != case["allowed_added_paths"]:
            raise EvaluationError(f"case {case_id}: mutation paths must be canonical")
        if len(all_allowed) != len(set(all_allowed)):
            raise EvaluationError(f"case {case_id}: mutation and addition paths overlap or repeat")
        if any(path in inventory or (seed_root / path).exists() for path in added):
            raise EvaluationError(f"case {case_id}: allowed addition already exists in seed")
        if any(parent != Path(".") and (seed_root / parent).exists() and not (seed_root / parent).is_dir() for path in added for parent in Path(path).parents):
            raise EvaluationError(f"case {case_id}: addition parent is not a directory")
        if any(path == PREPARATION_NAME or _is_transient_python_artifact(path) or _is_transient_python_artifact(path, is_directory=True) for path in all_allowed):
            raise EvaluationError(f"case {case_id}: reserved artifact path")
        if case.get("seed_condition") not in {"defective", "already_satisfies_contract"}:
            raise EvaluationError(f"case {case_id}: invalid seed_condition")
    maximum = case.get("max_changed_files")
    minimum = 1 if suite_id == "v1" else 0
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < minimum:
        raise EvaluationError(f"case {case_id}: invalid max_changed_files")
    if maximum > len(allowed) + len(added):
        raise EvaluationError(f"case {case_id}: max_changed_files exceeds allowed paths")
    oracle = oracles.ORACLES.get(case_id)
    if oracle is None:
        raise EvaluationError(f"case {case_id}: held-out oracle is missing")
    check_ids = [item.check_id for item in oracle.checks] + ["bounded-delta"]
    if len(check_ids) != len(set(check_ids)):
        raise EvaluationError(f"case {case_id}: duplicate oracle check id")
    if not set(case["critical_checks"]) <= set(check_ids):
        raise EvaluationError(f"case {case_id}: unknown critical check")
    mutation_ids = [item.mutation_id for item in oracle.mutations]
    if case["go_red_mutations"] != mutation_ids:
        raise EvaluationError(f"case {case_id}: mutation declaration/order differs from oracle")
    if any(item.target_check not in check_ids for item in oracle.mutations):
        raise EvaluationError(f"case {case_id}: mutation names an unknown target check")
    for relative in oracle.reference_files:
        _safe_relative(relative, f"case {case_id} reference path")
        if relative not in allowed + added:
            raise EvaluationError(f"case {case_id}: reference edits undeclared path {relative}")
    for mutation in oracle.mutations:
        mutation_path = _safe_relative(mutation.path, f"case {case_id} mutation path")
        if mutation_path not in inventory and mutation_path not in oracle.reference_files:
            raise EvaluationError(f"case {case_id}: mutation path is absent from seed and reference")


def _workspace_inventories(root: Path, *, strict: bool = False) -> tuple[dict[str, str], list[str]]:
    inventory: dict[str, str] = {}
    transient_python_artifacts: list[str] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink() or (strict and getattr(path, "is_junction", lambda: False)()):
            raise EvaluationError(f"workspace contains a symlink: {path.relative_to(root).as_posix()}")
        relative = path.relative_to(root).as_posix()
        is_directory = path.is_dir()
        if strict and _is_transient_python_artifact(relative, is_directory=is_directory):
            transient_python_artifacts.append(relative + "/" if is_directory else relative)
            continue
        if is_directory:
            if strict:
                inventory[relative + "/"] = hashlib.sha256(b"directory").hexdigest()
            continue
        if relative == PREPARATION_NAME or (not strict and ("__pycache__" in path.parts or path.suffix == ".pyc")):
            continue
        inventory[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return inventory, transient_python_artifacts


def _inventory(root: Path, *, strict: bool = False) -> dict[str, str]:
    return _workspace_inventories(root, strict=strict)[0]


def _case_digest(case: dict[str, Any]) -> str:
    return _digest(case)


def prepare_case(case_id: str, output: Path, *, suite_id: str = "v1") -> dict[str, Any]:
    suite, cases, oracles = load_suite(suite_id)
    if case_id not in cases:
        raise EvaluationError(f"unknown evaluation case: {case_id}")
    output = output.resolve()
    if output.exists():
        raise EvaluationError(f"prepare output must not already exist: {output}")
    seed = (EVAL_ROOT / cases[case_id]["seed_root"]).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(seed, output)
    manifest = {
        "schema": PREPARATION_SCHEMA if suite_id == "v1" else PREPARATION_V2_SCHEMA,
        "case_id": case_id,
        "case_sha256": _case_digest(cases[case_id]),
        "oracle_sha256": oracles.reference_digest(case_id),
        "seed_inventory": _inventory(seed, strict=suite_id == "v2"),
    }
    if suite_id == "v2":
        _, oracle_path = _suite_paths(suite_id)
        manifest.update(
            suite_id=suite_id,
            suite_sha256=_digest(suite),
            oracle_module_sha256=hashlib.sha256(oracle_path.read_bytes()).hexdigest(),
            runner_sha256=hashlib.sha256(RUNNER_PATH.read_bytes()).hexdigest(),
        )
    (output / PREPARATION_NAME).write_bytes(_canonical_bytes(manifest) + b"\n")
    return manifest


def _read_preparation(workspace: Path, case_id: str, case: dict[str, Any], oracles: Any, *, suite_id: str = "v1", suite: dict[str, Any] | None = None) -> dict[str, Any]:
    marker = workspace / PREPARATION_NAME
    try:
        manifest = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"missing or invalid preparation manifest: {exc}") from exc
    expected_schema = PREPARATION_SCHEMA if suite_id == "v1" else PREPARATION_V2_SCHEMA
    if not isinstance(manifest, dict) or manifest.get("schema") != expected_schema:
        raise EvaluationError("preparation manifest schema mismatch")
    expected = {
        "case_id": case_id,
        "case_sha256": _case_digest(case),
        "oracle_sha256": oracles.reference_digest(case_id),
    }
    if suite_id == "v2":
        _, oracle_path = _suite_paths(suite_id)
        expected.update(
            suite_id=suite_id,
            suite_sha256=_digest(suite),
            oracle_module_sha256=hashlib.sha256(oracle_path.read_bytes()).hexdigest(),
            runner_sha256=hashlib.sha256(RUNNER_PATH.read_bytes()).hexdigest(),
        )
    for field, value in expected.items():
        if manifest.get(field) != value:
            raise EvaluationError(f"preparation manifest {field} mismatch")
    seed_inventory = manifest.get("seed_inventory")
    if not isinstance(seed_inventory, dict) or any(
        not isinstance(path, str)
        or not isinstance(digest, str)
        or SHA256.fullmatch(digest) is None
        for path, digest in seed_inventory.items()
    ):
        raise EvaluationError("preparation seed inventory is invalid")
    authoritative_seed = _inventory((EVAL_ROOT / case["seed_root"]).resolve(), strict=suite_id == "v2")
    if seed_inventory != authoritative_seed:
        raise EvaluationError("preparation seed inventory mismatch")
    return manifest


def _delta_check(case: dict[str, Any], initial: dict[str, str], final: dict[str, str], *, suite_id: str = "v1") -> tuple[dict[str, object], dict[str, object]]:
    initial_paths = set(initial)
    final_paths = set(final)
    changed = sorted(path for path in initial_paths & final_paths if initial[path] != final[path])
    added = sorted(final_paths - initial_paths)
    deleted = sorted(initial_paths - final_paths)
    allowed = set(case["allowed_mutation_paths"])
    allowed_added = set(case["allowed_added_paths"]) if suite_id == "v2" else set()
    allowed_directories = {
        parent.as_posix() + "/"
        for path in allowed_added
        for parent in PurePosixPath(path).parents
        if parent != PurePosixPath(".")
    }
    unexpected = sorted(((set(changed) | set(deleted)) - allowed) | (set(added) - allowed_added - allowed_directories))
    added_files = [path for path in added if not path.endswith("/")]
    passed = (
        not deleted
        and not unexpected
        and len(changed) + len(added_files) <= case["max_changed_files"]
    )
    delta = {
        "changed": changed,
        "added": added,
        "deleted": deleted,
        "unexpected": unexpected,
        "max_changed_files": case["max_changed_files"],
    }
    check = {
        "id": "bounded-delta",
        "category": "bounded_efficiency",
        "passed": passed,
        "detail": "passed" if passed else json.dumps(delta, sort_keys=True),
    }
    return check, delta


def score_case(case_id: str, workspace: Path, *, suite_id: str = "v1") -> dict[str, Any]:
    suite, cases, oracles = load_suite(suite_id)
    if case_id not in cases:
        raise EvaluationError(f"unknown evaluation case: {case_id}")
    workspace = workspace.resolve()
    if not workspace.is_dir():
        raise EvaluationError(f"workspace is not a directory: {workspace}")
    manifest = _read_preparation(workspace, case_id, cases[case_id], oracles, suite_id=suite_id, suite=suite)
    checks = oracles.evaluate(case_id, workspace)
    final_inventory, transient_python_artifacts = _workspace_inventories(workspace, strict=suite_id == "v2")
    delta_check, delta = _delta_check(cases[case_id], manifest["seed_inventory"], final_inventory, suite_id=suite_id)
    checks.append(delta_check)
    check_by_id = {item["id"]: item for item in checks}
    critical_failures = [
        check_id
        for check_id in cases[case_id]["critical_checks"]
        if not bool(check_by_id[check_id]["passed"])
    ]
    result = {
        "schema": SCORE_SCHEMA if suite_id == "v1" else SCORE_V2_SCHEMA,
        "case_id": case_id,
        "case_sha256": manifest["case_sha256"],
        "oracle_sha256": manifest["oracle_sha256"],
        "passed": all(bool(item["passed"]) for item in checks),
        "critical_failures": critical_failures,
        "checks": checks,
        "delta": delta,
        "interpretation": (
            "This vector scores observable final behavior and evidence only; "
            "it does not prove private reasoning or behavioral transfer by itself."
        ),
    }
    if suite_id == "v2":
        result.update(
            suite_id=suite_id,
            suite_sha256=manifest["suite_sha256"],
            oracle_module_sha256=manifest["oracle_module_sha256"],
            runner_sha256=manifest["runner_sha256"],
            transient_python_artifacts={"informational_only": True, "paths": transient_python_artifacts},
        )
    return result


def self_check(*, suite_id: str = "v1") -> dict[str, Any]:
    _, cases, oracles = load_suite(suite_id)
    results: list[dict[str, Any]] = []
    all_passed = True
    with tempfile.TemporaryDirectory(prefix="wisdom-eval-self-check-") as temporary:
        base = Path(temporary)
        for case_id, case in cases.items():
            seed = EVAL_ROOT / case["seed_root"]
            seed_workspace = base / f"{case_id}-seed"
            shutil.copytree(seed, seed_workspace)
            seed_checks = oracles.evaluate(case_id, seed_workspace)
            seed_by_id = {item["id"]: item for item in seed_checks}
            seed_exposes_defect = any(
                not bool(seed_by_id[check_id]["passed"])
                for check_id in case["critical_checks"]
                if check_id != "bounded-delta"
            )

            reference = base / f"{case_id}-reference"
            shutil.copytree(seed, reference)
            oracles.materialize_reference(case_id, reference)
            reference_checks = oracles.evaluate(case_id, reference)
            reference_delta, _ = _delta_check(
                case,
                _inventory(seed, strict=suite_id == "v2"),
                _inventory(reference, strict=suite_id == "v2"),
                suite_id=suite_id,
            )
            reference_passed = all(bool(item["passed"]) for item in reference_checks) and bool(reference_delta["passed"])

            mutation_results: list[dict[str, object]] = []
            for mutation_id in case["go_red_mutations"]:
                mutated = base / f"{case_id}-mutation-{mutation_id}"
                shutil.copytree(reference, mutated)
                mutation = oracles.apply_mutation(case_id, mutation_id, mutated)
                mutated_checks = {
                    item["id"]: item for item in oracles.evaluate(case_id, mutated)
                }
                target_failed = not bool(mutated_checks[mutation.target_check]["passed"])
                mutation_results.append(
                    {
                        "id": mutation_id,
                        "target_check": mutation.target_check,
                        "target_failed": target_failed,
                    }
                )
            mutation_sensitive = all(bool(item["target_failed"]) for item in mutation_results)
            expected_defect = case.get("seed_condition", "defective") == "defective"
            case_passed = (seed_exposes_defect == expected_defect) and reference_passed and mutation_sensitive
            all_passed = all_passed and case_passed
            results.append(
                {
                    "case_id": case_id,
                    "passed": case_passed,
                    "seed_exposes_defect": seed_exposes_defect,
                    "reference_passed": reference_passed,
                    "mutations": mutation_results,
                }
            )
    return {
        "schema": f"wisdom.behavioral_eval_self_check.{suite_id}",
        "passed": all_passed,
        "cases": results,
        "claim_boundary": (
            "This proves corpus integrity and oracle sensitivity, not model behavioral transfer."
        ),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    listing = subparsers.add_parser("list", help="list available authoring evaluation cases")
    prepare = subparsers.add_parser("prepare", help="copy one seed into a new isolated workspace")
    prepare.add_argument("--case", required=True)
    prepare.add_argument("--output", required=True, type=Path)
    score = subparsers.add_parser("score", help="score one prepared workspace with held-out oracles")
    score.add_argument("--case", required=True)
    score.add_argument("--workspace", required=True, type=Path)
    score.add_argument(
        "--allow-candidate-execution",
        action="store_true",
        help=(
            "acknowledge that scoring executes model-written Python and must run "
            "inside a disposable least-authority environment"
        ),
    )
    checking = subparsers.add_parser("self-check", help="verify seeds, references, and go-red mutations")
    for command in (listing, prepare, score, checking):
        command.add_argument("--suite", choices=SUITE_IDS, default="v1")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "list":
            _, cases, _ = load_suite(args.suite)
            result: object = [
                {"id": case_id, "title": case["title"], "task_profile": case["task_profile"]}
                for case_id, case in cases.items()
            ]
            exit_code = 0
        elif args.command == "prepare":
            result = prepare_case(args.case, args.output, suite_id=args.suite)
            exit_code = 0
        elif args.command == "score":
            if not args.allow_candidate_execution:
                raise EvaluationError(
                    "score executes candidate code; rerun inside a disposable "
                    "least-authority environment with --allow-candidate-execution"
                )
            result = score_case(args.case, args.workspace, suite_id=args.suite)
            exit_code = 0 if result["passed"] else 3
        else:
            result = self_check(suite_id=args.suite)
            exit_code = 0 if result["passed"] else 2
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return exit_code
    except EvaluationError as exc:
        print(f"application-fidelity evaluation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
