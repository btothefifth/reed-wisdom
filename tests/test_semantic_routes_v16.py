"""Keep v1.6 semantic-owner, repair, and proof-state rules routable."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import compile_wisdom as compiler  # noqa: E402


SOURCE = ROOT / "WISDOM.md"


def _route_rules(parsed: compiler.ParsedWisdom, task_profile: str) -> set[str]:
    mode, tags = compiler.resolve_task_profile(parsed, task_profile)
    modules = compiler.resolve_module_ids(parsed, mode=mode, tags=tags)
    kernel_ids = {
        rule_id
        for section in parsed.sections
        if section.section_id in parsed.manifest["kernel_sections"]
        for rule_id in section.rule_ids
    }
    module_ids = {
        rule_id
        for module_id in modules
        for section_id in parsed.module_by_id[module_id]["sections"]
        for rule_id in parsed.section_by_id[section_id].rule_ids
    }
    return kernel_ids | module_ids


def test_semantic_and_evidence_rules_reach_ordinary_code_changes() -> None:
    parsed = compiler.parse_source(SOURCE)

    assert parsed.manifest["semantic_revision"] == 15
    assert "SEM-01" in parsed.section_by_id["implementation"].rule_ids
    assert "EVIDENCE-01" in parsed.section_by_id["test_harness"].rule_ids
    code_rules = _route_rules(parsed, "code_change")
    assert {"SEM-01", "EVIDENCE-01", "SCOPE-01"} <= code_rules
    bug_rules = _route_rules(parsed, "bug_fix")
    assert {"SEM-01", "EVIDENCE-01", "SCOPE-01", "REPAIR-01"} <= bug_rules


def test_lifecycle_repair_rule_reaches_bug_fixes() -> None:
    parsed = compiler.parse_source(SOURCE)

    assert parsed.section_by_id["defect_family"].rule_ids == ("REPAIR-01",)
    bug_rules = _route_rules(parsed, "bug_fix")
    assert "REPAIR-01" in bug_rules
    assert "REPAIR-01" not in _route_rules(parsed, "routine")


def test_semantic_ownership_and_repair_frontier_are_explicit() -> None:
    parsed = compiler.parse_source(SOURCE)
    implementation = parsed.section_by_id["implementation"].body.decode("utf-8")
    defect = parsed.section_by_id["defect_family"].body.decode("utf-8")

    for phrase in (
        "canonical owner",
        "identities and lifecycle states it consumes and",
        "distinct\ntypes, constructors, or validated APIs",
        "One semantic fact has one canonical producer",
        "moving tangled\nlogic between files is not simplification",
    ):
        assert phrase in implementation

    for phrase in (
        "reachable callers and consumers",
        "persistence and rehydration",
        "error and cleanup paths",
        "duplicate, retry, cancellation, restart, reuse, and",
        "`IMPACT-01` independently derives which proof",
    ):
        assert phrase in defect


def test_proof_vector_and_consumer_backward_freshness_are_explicit() -> None:
    parsed = compiler.parse_source(SOURCE)
    test_harness = parsed.section_by_id["test_harness"].body.decode("utf-8")
    async_lifecycle = parsed.section_by_id["async_lifecycle"].body.decode("utf-8")

    for dimension in (
        "implemented",
        "reviewed",
        "focused-proof-green",
        "integration-proof-green",
        "native/lifecycle-proved",
        "immutable-candidate-proved",
        "deployed",
        "runtime-identity-proved",
        "authority-enabled",
        "behavior-observed",
        "reconciled",
    ):
        assert f"`{dimension}`" in test_harness
    assert "No dimension implies a later or neighboring dimension" in test_harness
    assert "Schedule freshness-bearing evidence backward from consumption." in async_lifecycle
    assert "retries or larger freshness windows\nare not the default repair" in async_lifecycle
