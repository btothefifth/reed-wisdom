"""Keep the v1.9 boundary contract joined across implementation and proof."""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import compile_wisdom as compiler  # noqa: E402


SOURCE = ROOT / "WISDOM.md"


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("_", " ").replace("`", "")).casefold()


def _section(parsed: compiler.ParsedWisdom, section_id: str) -> str:
    return parsed.section_by_id[section_id].body.decode("utf-8")


def _route(parsed: compiler.ParsedWisdom, profile_id: str) -> tuple[set[str], set[str]]:
    mode, tags = compiler.resolve_task_profile(parsed, profile_id)
    modules = set(compiler.resolve_module_ids(parsed, mode=mode, tags=tags))
    rules = {
        rule_id
        for section in parsed.sections
        if section.section_id in parsed.manifest["kernel_sections"]
        for rule_id in section.rule_ids
    } | {
        rule_id
        for module_id in modules
        for section_id in parsed.module_by_id[module_id]["sections"]
        for rule_id in parsed.section_by_id[section_id].rule_ids
    }
    return modules, rules


def test_boundary_contract_reaches_ordinary_and_delegated_material_routes() -> None:
    parsed = compiler.parse_source(SOURCE)
    assert parsed.manifest["semantic_revision"] == 17
    assert len(parsed.manifest["modules"]) == 23

    for profile in (
        "code_change",
        "bug_fix",
        "delegated_code_change",
        "delegated_bug_fix",
        "delegated_review",
    ):
        modules, rules = _route(parsed, profile)
        assert {"CHANGE-01", "ACCEPT-01", "ORACLE-01"} <= rules
        if profile in ("code_change", "bug_fix"):
            assert "effect_harness" not in modules
            assert "delegation_contract" not in modules
            assert "context_delegation" not in modules

    _, routine_rules = _route(parsed, "routine")
    assert "CHANGE-01" not in routine_rules


def test_change_contract_joins_each_boundary_under_one_identity() -> None:
    parsed = compiler.parse_source(SOURCE)
    implementation = _section(parsed, "implementation")
    start = implementation.index("**`CHANGE-01`")
    end = implementation.index("**`ACCEPT-01`", start)
    change = _normalized(implementation[start:end])

    for phrase in (
        "boundary contracts",
        "boundary id and generation",
        "entry state, attempted event, and permitted terminal states",
        "current owner, transfer event, accepting owner",
        "admission, durable-completion, or observation boundary",
        "actual accepted-work or effect event and independent observation",
        "pre-acceptance, accepted, uncertain, absent-child",
        "boundary ref",
        "same operation and generation",
        "reject contradictory or mixed-generation joins",
        "earlier event",
        "never implies a later transfer",
        "receipt existence, expected child creation, or fixture readiness",
        "does not prove timely acceptance, successful child creation",
        "reachability of the intended production boundary, or completion",
        "immediately before and after each material boundary-contract cutpoint",
    ):
        assert _normalized(phrase) in change


def test_acceptance_contract_owns_pre_child_failures_and_uncertain_creation() -> None:
    text = _normalized(_section(compiler.parse_source(SOURCE), "implementation"))
    for phrase in (
        "bind it to the applicable CHANGE-01 boundary-contract identity and generation",
        "acquiring ownership before a child operation exists",
        "release responsibility with the claimant",
        "independently evidenced ownership transfer",
        "establish cleanup immediately after acquisition",
        "preparation, serialization, creation, and transfer failures",
        "cleanup must not wait for that nonexistent child",
        "creation or effect uncertainty retains the current owner until reconciliation",
        "ownership claimed, child created, work or effect accepted",
        "serialization failure after claim but before creation",
        "successful transfer without premature claimant release",
    ):
        assert _normalized(phrase) in text


def test_acknowledged_effect_remains_unresolved_at_consequential_consumer() -> None:
    text = _normalized(_section(compiler.parse_source(SOURCE), "implementation"))
    for phrase in (
        "acknowledged request or transport success proves only acknowledgment",
        "it is not reconciled state",
        "declared authoritative consumer observes current terminal state",
        "carry the effect as unresolved into every consequential consumer",
        "whose decision depends on its completion or absence",
        "may advance only behavior valid while the effect remains unresolved",
        "must not infer absence",
        "permit a conflicting or replacement effect",
        "producer receipt through the real carrier",
        "first consumer capable of acting",
        "acknowledgment-before-observation negative witness",
        "current-terminal-observation positive witness",
        "after that consumer acts is too late",
    ):
        assert _normalized(phrase) in text


def test_deadline_contract_distinguishes_phase_completion_and_observation() -> None:
    text = _normalized(_section(compiler.parse_source(SOURCE), "test_harness"))
    for phrase in (
        "same boundary-contract identity and generation",
        "phase or action scope",
        "whether it bounds admission, durable completion, or observation",
        "resume policy",
        "resumed verification uses its own bounded execution budget",
        "grants no renewed mutation authority",
        "actual protected linearization, durability, publication, or consumer boundary",
        "begins before but completes after expiry",
        "late API return alone does not prove that the durable commit was late",
        "expired mutation deadline with still-eligible read-only verification",
        "timely commit observed only later",
    ):
        assert _normalized(phrase) in text


def test_existing_fixture_and_evidence_owners_remain_the_enforcement_points() -> None:
    parsed = compiler.parse_source(SOURCE)
    harness = _normalized(_section(parsed, "test_harness"))
    for phrase in (
        "pin or inject every contextual policy input",
        "clock, session, regime, feature mode, and authority mode",
        "assert the intended production predicate is reached",
        "repair the fixture, not the production guard",
        "no dimension implies a later or neighboring dimension",
    ):
        assert _normalized(phrase) in harness
