"""Integrity tests for the authoring-only application-fidelity evaluation kit.

These tests validate the corpus and its held-out oracles. They deliberately do
not claim that a model read, learned, or behaviorally transferred WISDOM.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
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
    assert arms["candidate"]["wisdom"]["source_sha256"] == _sha256(ROOT / "WISDOM.md")
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
