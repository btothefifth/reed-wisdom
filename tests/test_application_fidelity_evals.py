"""Integrity tests for the authoring-only application-fidelity evaluation kit.

These tests validate the corpus and its held-out oracles. They deliberately do
not claim that a model read, learned, or behaviorally transferred WISDOM.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_application_fidelity_eval as evaluation  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_suite_has_seven_material_cases_and_one_fast_control() -> None:
    suite, cases, oracles = evaluation.load_suite()

    assert suite["schema"] == evaluation.SUITE_SCHEMA
    assert len(cases) == 8
    assert {case["task_profile"] for case in cases.values()} >= {"bug_fix", "routine"}
    assert [case_id for case_id, case in cases.items() if case["task_profile"] == "routine"] == [
        "fast-local-control"
    ]
    assert set(cases) == set(oracles.ORACLES)
    assert all(case["outcomes"]["required"] for case in cases.values())
    assert all(case["outcomes"]["forbidden"] for case in cases.values())
    assert all(case["outcomes"]["preserved"] for case in cases.values())


def test_protocol_uses_fresh_session_triads_without_model_infrastructure() -> None:
    readme = " ".join(
        (evaluation.EVAL_ROOT / "README.md").read_text(encoding="utf-8").casefold().split()
    )

    for phrase in (
        "fresh-session triad",
        "unassisted",
        "prior",
        "candidate",
        "same model version and settings",
        "separate clean workspace",
    ):
        assert phrase in readme
    assert "does not call a model api" in readme
    assert "never reuse a conversation or mutated workspace across arms" in readme
    assert "preparation isolation" in readme
    assert "not a security sandbox" in readme
    assert "disposable least-authority environment" in readme
    assert "not tamper-resistant" in readme


def test_v110_behavioral_receipt_is_source_bound_and_bounded() -> None:
    receipt_path = (
        evaluation.EVAL_ROOT / "results" / "v1.10.0-gpt-6-luna-high.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    arms = {arm["id"]: arm for arm in receipt["arms"]}

    assert receipt["schema"] == "wisdom.behavioral_eval_run.v1"
    assert receipt["release"] == "1.10.0"
    assert receipt["suite"]["cases_sha256"] == _sha256(evaluation.CASES_PATH)
    assert receipt["suite"]["oracles_sha256"] == _sha256(evaluation.ORACLES_PATH)
    # Historical release evidence stays bound to its original source generation.
    assert arms["candidate"]["wisdom"]["source_sha256"] == (
        "3c056a2c7cb3a5159af99c43ea8d9f929aaefb9b1e1873801603ed0cb050336a"
    )
    assert arms["candidate"]["passed_cases"] == 8
    assert arms["candidate"]["failed_cases"] == []
    assert arms["prior"]["failed_cases"] == [
        {
            "id": "fast-local-control",
            "critical_failures": ["bounded-delta"],
            "unexpected_changed_paths": ["test_public.py"],
        }
    ]
    assert receipt["claim_boundary"]["not_supported"]


def test_v112_behavioral_receipt_is_historical_source_bound_and_bounded() -> None:
    receipt_path = evaluation.EVAL_ROOT / "results" / "v1.12.0-gpt-6-luna-high.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    arms = {arm["id"]: arm for arm in receipt["arms"]}
    suite, _, _ = evaluation.load_suite("v2")

    assert receipt["schema"] == "wisdom.behavioral_eval_run.v2"
    assert receipt["release"] == "1.12.0"
    assert receipt["suite"]["suite_sha256"] == evaluation._digest(suite)
    cases_path, oracles_path = evaluation._suite_paths("v2")
    assert receipt["suite"]["cases_file_sha256"] == _sha256(cases_path)
    assert receipt["suite"]["oracles_sha256"] == _sha256(oracles_path)
    assert receipt["suite"]["runner_sha256"] == _sha256(evaluation.RUNNER_PATH)
    # Historical evidence retains its independently verified immutable v1.12 source.
    assert arms["candidate"]["wisdom"]["source_sha256"] == (
        "df786b013b91cfa88b8b1d8ca5e88499a5682af93a4525ba14f8bbee468085b1"
    )
    assert receipt["suite"]["selected_cases"] == [
        "effective-source-and-outcomes",
        "fixture-owner-triage",
    ]
    assert all(arm["passed_cases"] == 2 and arm["failed_cases"] == [] for arm in arms.values())
    assert arms["candidate"]["tokens_used"] > arms["prior"]["tokens_used"]
    assert receipt["claim_boundary"]["not_supported"]


def test_score_cli_requires_explicit_candidate_execution_acknowledgement(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workspace = tmp_path / "prepared"
    evaluation.prepare_case("fast-local-control", workspace)

    result = evaluation.main(
        ["score", "--case", "fast-local-control", "--workspace", str(workspace)]
    )

    assert result == 2
    assert "score executes candidate code" in capsys.readouterr().err


def test_visible_tasks_remain_high_level_and_hide_evaluator_analysis() -> None:
    _, cases, _ = evaluation.load_suite()
    evaluator_terms = (
        "wisdom",
        "topology",
        "oracle",
        "go-red",
        "go red",
        "boundary",
        "producer",
        "consumer",
        "failure matrix",
        "phase capsule",
        "rubric",
        "positive witness",
        "negative witness",
        "proportionate",
        "reversible",
    )

    for case in cases.values():
        task_path = evaluation.EVAL_ROOT / case["seed_root"] / case["task_file"]
        task = task_path.read_text(encoding="utf-8").casefold()
        assert task.startswith("# task\n")
        assert all(term not in task for term in evaluator_terms), (case["id"], task)
        assert len(task.split()) <= 80


def test_prepare_is_deterministic_and_keeps_oracles_outside_workspace(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_manifest = evaluation.prepare_case("acknowledged-not-reconciled", first)
    second_manifest = evaluation.prepare_case("acknowledged-not-reconciled", second)

    assert first_manifest == second_manifest
    assert evaluation._inventory(first) == evaluation._inventory(second)
    assert (first / "TASK.md").is_file()
    assert not (first / "oracles.py").exists()
    assert not (first / "evaluations").exists()
    marker = json.loads((first / evaluation.PREPARATION_NAME).read_text(encoding="utf-8"))
    assert marker == first_manifest
    assert "runner_sha256" not in marker


def test_prepare_requires_a_new_path(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(evaluation.EvaluationError, match="must not already exist"):
        evaluation.prepare_case("fast-local-control", existing)


def test_self_check_proves_seed_reference_and_mutation_sensitivity() -> None:
    result = evaluation.self_check()

    assert result["passed"] is True
    assert len(result["cases"]) == 8
    for case in result["cases"]:
        assert case["passed"] is True
        assert case["seed_exposes_defect"] is True
        assert case["reference_passed"] is True
        assert case["mutations"]
        assert all(mutation["target_failed"] for mutation in case["mutations"])
    assert "not model behavioral transfer" in result["claim_boundary"]


@pytest.mark.parametrize(
    "case_id",
    [
        "acknowledged-not-reconciled",
        "claim-before-child",
        "fixture-reaches-boundary",
        "stale-receipt-after-edit",
        "sibling-consumer-omitted",
        "harmful-suppression",
        "intermediate-event-completion",
        "fast-local-control",
    ],
)
def test_held_out_reference_scores_green_without_overclaiming(
    tmp_path: Path, case_id: str
) -> None:
    workspace = tmp_path / case_id
    evaluation.prepare_case(case_id, workspace)
    oracles = evaluation._load_oracles()
    oracles.materialize_reference(case_id, workspace)

    score = evaluation.score_case(case_id, workspace)

    assert score["schema"] == evaluation.SCORE_SCHEMA
    assert score["passed"] is True
    assert score["critical_failures"] == []
    assert all(check["passed"] for check in score["checks"])
    assert "does not prove private reasoning" in score["interpretation"]
    assert "runner_sha256" not in score
    assert "transient_python_artifacts" not in score


def test_seed_score_exposes_critical_failure(tmp_path: Path) -> None:
    workspace = tmp_path / "seed"
    evaluation.prepare_case("intermediate-event-completion", workspace)

    score = evaluation.score_case("intermediate-event-completion", workspace)

    assert score["passed"] is False
    assert {"failure-not-complete", "timeout-not-complete"} <= set(
        score["critical_failures"]
    )


def test_acknowledgement_oracle_accepts_equivalent_nonterminal_state_names(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "equivalent-state"
    evaluation.prepare_case("acknowledged-not-reconciled", workspace)
    candidate = (workspace / "candidate.py").read_text(encoding="utf-8")
    candidate = candidate.replace(
        'state["cancel_state"] = "cancelled"\n        state["occupied"] = False',
        'state["cancel_state"] = "requested"',
        1,
    )
    candidate = candidate.replace(
        'if remote_state == "cancelled":\n        state["cancel_state"] = "requested"',
        'if remote_state == "cancelled":\n        state["cancel_state"] = "cancelled"\n        state["occupied"] = False',
        1,
    )
    (workspace / "candidate.py").write_text(candidate, encoding="utf-8", newline="\n")

    score = evaluation.score_case("acknowledged-not-reconciled", workspace)

    assert score["passed"] is True


def test_score_rejects_tampered_preparation_generation(tmp_path: Path) -> None:
    workspace = tmp_path / "tampered"
    evaluation.prepare_case("fast-local-control", workspace)
    marker_path = workspace / evaluation.PREPARATION_NAME
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["case_sha256"] = "0" * 64
    marker_path.write_text(json.dumps(marker), encoding="utf-8")

    with pytest.raises(evaluation.EvaluationError, match="case_sha256 mismatch"):
        evaluation.score_case("fast-local-control", workspace)


def test_score_rejects_tampered_seed_inventory(tmp_path: Path) -> None:
    workspace = tmp_path / "tampered-inventory"
    evaluation.prepare_case("fast-local-control", workspace)
    marker_path = workspace / evaluation.PREPARATION_NAME
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker["seed_inventory"]["candidate.py"] = "0" * 64
    marker_path.write_text(json.dumps(marker), encoding="utf-8")

    with pytest.raises(evaluation.EvaluationError, match="seed inventory mismatch"):
        evaluation.score_case("fast-local-control", workspace)


def test_fast_control_flags_unbounded_or_unrelated_delta(tmp_path: Path) -> None:
    workspace = tmp_path / "fast"
    evaluation.prepare_case("fast-local-control", workspace)
    oracles = evaluation._load_oracles()
    oracles.materialize_reference("fast-local-control", workspace)
    (workspace / "PROCESS.md").write_text("unnecessary artifact\n", encoding="utf-8")

    score = evaluation.score_case("fast-local-control", workspace)
    checks = {item["id"]: item for item in score["checks"]}

    assert checks["bounded-delta"]["passed"] is False
    assert score["passed"] is False
    assert score["critical_failures"] == ["bounded-delta"]
    assert score["delta"]["added"] == ["PROCESS.md"]


@pytest.mark.parametrize(
    "unsafe", ["../escape", "/absolute", "C:/windows-drive", "nested\\windows", "bad\x00path"]
)
def test_portable_paths_reject_escape_and_platform_specific_forms(unsafe: str) -> None:
    with pytest.raises(evaluation.EvaluationError):
        evaluation._safe_relative(unsafe, "test path")


V2_CASES = (
    "conditional-delivery",
    "uncertain-slot",
    "recover-dependent-checks",
    "effective-source-and-outcomes",
    "fixture-owner-triage",
    "already-correct-normalizer",
)


def test_v2_is_explicit_and_preserves_the_v1_corpus_and_historical_receipt() -> None:
    suite, cases, _ = evaluation.load_suite("v2")
    assert suite["schema"] == evaluation.SUITE_V2_SCHEMA
    assert tuple(cases) == V2_CASES
    assert len(evaluation.load_suite()[1]) == 8
    assert _sha256(evaluation.CASES_PATH) == "31d235c81a465cdbd3d910db70b300419f9214d5db3de37490923b605c23a39a"
    assert _sha256(evaluation.ORACLES_PATH) == "4d42c465a24b3a498d42b14f7ade86974acd391e5bd4a6e7bc8c16ff7a8b4ff6"
    assert _sha256(evaluation.EVAL_ROOT / "results" / "v1.10.0-gpt-6-luna-high.json") == "a45176c60791bd4bf3dbc035b691a9de740c99ac329d045f5fcdad39f4e5d1ad"


@pytest.mark.parametrize("case_id", V2_CASES)
def test_v2_reference_reaches_terminal_and_preserved_behavior(tmp_path: Path, case_id: str) -> None:
    workspace = tmp_path / case_id
    manifest = evaluation.prepare_case(case_id, workspace, suite_id="v2")
    evaluation._load_oracles("v2").materialize_reference(case_id, workspace)
    score = evaluation.score_case(case_id, workspace, suite_id="v2")
    assert manifest["schema"] == evaluation.PREPARATION_V2_SCHEMA
    assert score["schema"] == evaluation.SCORE_V2_SCHEMA
    assert score["suite_id"] == "v2"
    assert score["suite_sha256"] == manifest["suite_sha256"]
    assert score["runner_sha256"] == manifest["runner_sha256"] == _sha256(evaluation.RUNNER_PATH)
    assert score["passed"] is True
    assert score["critical_failures"] == []
    assert "oracles_v2.py" not in evaluation._inventory(workspace)


def test_v2_self_check_distinguishes_defective_seeds_and_correct_noop() -> None:
    result = evaluation.self_check(suite_id="v2")
    assert result["schema"] == "wisdom.behavioral_eval_self_check.v2"
    assert result["passed"] is True
    by_id = {case["case_id"]: case for case in result["cases"]}
    assert by_id["already-correct-normalizer"]["seed_exposes_defect"] is False
    assert all(by_id[case_id]["seed_exposes_defect"] is True for case_id in V2_CASES[:-1])
    assert all(mutation["target_failed"] for case in result["cases"] for mutation in case["mutations"])


def test_v2_noop_passes_with_no_change_and_rejects_unnecessary_work(tmp_path: Path) -> None:
    workspace = tmp_path / "noop"
    evaluation.prepare_case("already-correct-normalizer", workspace, suite_id="v2")
    assert evaluation.score_case("already-correct-normalizer", workspace, suite_id="v2")["passed"] is True
    source = workspace / "candidate.py"
    source.write_text(source.read_text(encoding="utf-8") + "\n# unnecessary edit\n", encoding="utf-8")
    score = evaluation.score_case("already-correct-normalizer", workspace, suite_id="v2")
    assert score["critical_failures"] == ["bounded-delta"]


@pytest.mark.parametrize("extra", ["PROCESS.md", "state/extra.json", "__pycache__", ".pytest_cache", "__pycache__.json", ".pytest_cache.txt", "notes.pyc.json"])
def test_v2_exact_addition_contract_rejects_undeclared_product_files(tmp_path: Path, extra: str) -> None:
    workspace = tmp_path / "recovery"
    evaluation.prepare_case("recover-dependent-checks", workspace, suite_id="v2")
    evaluation._load_oracles("v2").materialize_reference("recover-dependent-checks", workspace)
    target = workspace / extra
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("unrequested\n", encoding="utf-8")
    score = evaluation.score_case("recover-dependent-checks", workspace, suite_id="v2")
    assert score["critical_failures"] == ["bounded-delta"]
    assert extra in score["delta"]["unexpected"]


def test_v2_process_artifacts_are_reported_without_failing_correctness_or_budget(tmp_path: Path) -> None:
    workspace = tmp_path / "noop-with-caches"
    evaluation.prepare_case("already-correct-normalizer", workspace, suite_id="v2")
    # py_compile creates bytecode even with both ordinary suppression settings.
    subprocess.run(
        [sys.executable, "-B", "-m", "py_compile", "candidate.py"],
        cwd=workspace,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        check=True,
        capture_output=True,
        timeout=10,
    )
    pytest_cache = workspace / ".pytest_cache" / "v" / "cache"
    pytest_cache.mkdir(parents=True)
    (pytest_cache / "nodeids").write_text("[]\n", encoding="utf-8")
    (workspace / "notes.pyc").write_bytes(b"transient bytecode")
    score = evaluation.score_case("already-correct-normalizer", workspace, suite_id="v2")
    assert score["passed"] is True
    assert score["critical_failures"] == []
    assert score["delta"] == {"changed": [], "added": [], "deleted": [], "unexpected": [], "max_changed_files": 0}
    artifacts = score["transient_python_artifacts"]
    assert artifacts["informational_only"] is True
    assert {"__pycache__/", ".pytest_cache/", ".pytest_cache/v/", ".pytest_cache/v/cache/", ".pytest_cache/v/cache/nodeids", "notes.pyc"} <= set(artifacts["paths"])
    assert any(path.startswith("__pycache__/") and path.endswith(".pyc") for path in artifacts["paths"])
    assert artifacts["paths"] == sorted(artifacts["paths"])
    assert evaluation._inventory(workspace, strict=True) == evaluation._inventory(
        evaluation.EVAL_ROOT / "seeds" / "already-correct-normalizer", strict=True
    )


@pytest.mark.parametrize("directory", ["PROCESS", "notes.pyc", "__pycache__-product", ".pytest_cache-product"])
def test_v2_noop_rejects_ordinary_empty_directories(tmp_path: Path, directory: str) -> None:
    workspace = tmp_path / "noop"
    evaluation.prepare_case("already-correct-normalizer", workspace, suite_id="v2")
    (workspace / directory).mkdir()
    score = evaluation.score_case("already-correct-normalizer", workspace, suite_id="v2")
    assert score["critical_failures"] == ["bounded-delta"]
    assert score["delta"]["unexpected"] == [directory + "/"]


def test_v2_transient_artifacts_do_not_hide_product_deletion(tmp_path: Path) -> None:
    workspace = tmp_path / "deleted-task"
    evaluation.prepare_case("already-correct-normalizer", workspace, suite_id="v2")
    (workspace / "TASK.md").unlink()
    (workspace / "__pycache__").mkdir()
    (workspace / "__pycache__" / "cache.pyc").write_bytes(b"cache")
    score = evaluation.score_case("already-correct-normalizer", workspace, suite_id="v2")
    assert score["critical_failures"] == ["bounded-delta"]
    assert score["delta"]["deleted"] == ["TASK.md"]
    assert score["transient_python_artifacts"]["paths"] == ["__pycache__/", "__pycache__/cache.pyc"]


def test_v2_declared_addition_counts_against_the_file_budget() -> None:
    _, cases, _ = evaluation.load_suite("v2")
    case = dict(cases["recover-dependent-checks"], max_changed_files=1)
    check, _ = evaluation._delta_check(case, {"candidate.py": "old"}, {"candidate.py": "new", "state/": "directory", "state/recovery.json": "report"}, suite_id="v2")
    assert check["passed"] is False


@pytest.mark.parametrize("field", ["suite_sha256", "oracle_module_sha256", "runner_sha256", "case_sha256", "oracle_sha256"])
def test_v2_rejects_mixed_or_tampered_preparation_generation(tmp_path: Path, field: str) -> None:
    workspace = tmp_path / "mixed"
    evaluation.prepare_case("conditional-delivery", workspace, suite_id="v2")
    marker_path = workspace / evaluation.PREPARATION_NAME
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    marker[field] = "0" * 64
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    with pytest.raises(evaluation.EvaluationError, match=field + " mismatch"):
        evaluation.score_case("conditional-delivery", workspace, suite_id="v2")


def test_v2_rejects_runner_byte_drift_after_preparation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = tmp_path / "run_application_fidelity_eval.py"
    runner.write_bytes(evaluation.RUNNER_PATH.read_bytes())
    monkeypatch.setattr(evaluation, "RUNNER_PATH", runner)
    workspace = tmp_path / "prepared"
    manifest = evaluation.prepare_case("already-correct-normalizer", workspace, suite_id="v2")
    assert manifest["runner_sha256"] == _sha256(runner)
    runner.write_bytes(runner.read_bytes() + b"\n# changed evaluator generation\n")
    with pytest.raises(evaluation.EvaluationError, match="runner_sha256 mismatch"):
        evaluation.score_case("already-correct-normalizer", workspace, suite_id="v2")


def test_v2_schema_rejects_broad_or_contradictory_addition_contracts() -> None:
    _, cases, oracles = evaluation.load_suite("v2")
    original = cases["recover-dependent-checks"]
    for added in (["../escape"], ["candidate.py"], ["state/recovery.json", "state/recovery.json"], ["candidate.py/report.json"], ["state/./recovery.json"], [evaluation.PREPARATION_NAME], ["__pycache__"], [".pytest_cache"], ["__pycache__/report.pyc"], [".pytest_cache/report.json"], ["nested/.pytest_cache/report.json"], ["report.pyc"]):
        malformed = dict(original, allowed_added_paths=added)
        with pytest.raises(evaluation.EvaluationError):
            evaluation._validate_case(malformed, oracles, suite_id="v2")
    with pytest.raises(evaluation.EvaluationError, match="invalid seed_condition"):
        evaluation._validate_case(dict(original, seed_condition="probably_ok"), oracles, suite_id="v2")
    with pytest.raises(evaluation.EvaluationError, match="unknown evaluation suite"):
        evaluation.load_suite("../v2")


def test_v2_cli_requires_selection_and_explicit_execution_acknowledgement(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    workspace = tmp_path / "noop"
    assert evaluation.main(["prepare", "--suite", "v2", "--case", "already-correct-normalizer", "--output", str(workspace)]) == 0
    capsys.readouterr()
    assert evaluation.main(["score", "--suite", "v2", "--case", "already-correct-normalizer", "--workspace", str(workspace)]) == 2
    assert "score executes candidate code" in capsys.readouterr().err
    assert evaluation.main(["score", "--suite", "v2", "--case", "already-correct-normalizer", "--workspace", str(workspace), "--allow-candidate-execution"]) == 0


def test_v2_tasks_and_oracles_are_neutral_and_do_not_score_lesson_prose() -> None:
    _, cases, oracles = evaluation.load_suite("v2")
    forbidden = ("wisdom", "oracle", "go-red", "rubric", "topology", "producer", "consumer", "workflow1", "gpt-", "openai")
    for case in cases.values():
        task = (evaluation.EVAL_ROOT / case["seed_root"] / "TASK.md").read_text(encoding="utf-8").casefold()
        assert task.startswith("# task\n")
        assert len(task.split()) <= 80
        assert all(term not in task for term in forbidden)
        for check in oracles.ORACLES[case["id"]].checks:
            assert "TASK.md" not in check.code
            assert "UNDERSTAND" not in check.code


def test_v2_blank_failure_output_remains_a_typed_score(tmp_path: Path) -> None:
    workspace = tmp_path / "blank-failure"
    evaluation.prepare_case("conditional-delivery", workspace, suite_id="v2")
    (workspace / "candidate.py").write_text("print()\nraise SystemExit(1)\n", encoding="utf-8")
    score = evaluation.score_case("conditional-delivery", workspace, suite_id="v2")
    assert score["passed"] is False
    assert score["checks"][0]["detail"] == "failed without output"


def test_v2_self_check_rejects_a_reference_outside_its_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    suite, cases, oracles = evaluation.load_suite("v2")
    constrained = {"conditional-delivery": dict(cases["conditional-delivery"], max_changed_files=0)}
    monkeypatch.setattr(evaluation, "load_suite", lambda suite_id="v1": (suite, constrained, oracles))
    result = evaluation.self_check(suite_id="v2")
    assert result["passed"] is False
    assert result["cases"][0]["reference_passed"] is False


def test_v2_uncertain_owner_oracle_accepts_equivalent_status_reporting(tmp_path: Path) -> None:
    workspace = tmp_path / "equivalent-status"
    evaluation.prepare_case("uncertain-slot", workspace, suite_id="v2")
    evaluation._load_oracles("v2").materialize_reference("uncertain-slot", workspace)
    source = workspace / "candidate.py"
    content = source.read_text(encoding="utf-8")
    content = content.replace(
        '    if outcome in {"creation_failed", "completed"}:',
        '    if outcome in {"timeout", "unknown"} and slot_id in slots:\n'
        '        slots[slot_id]["status"] = "unresolved"\n'
        '    if outcome in {"creation_failed", "completed"}:',
        1,
    )
    source.write_text(content, encoding="utf-8", newline="\n")
    score = evaluation.score_case("uncertain-slot", workspace, suite_id="v2")
    assert score["passed"] is True
