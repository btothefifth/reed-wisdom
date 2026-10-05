"""Keep the v1.8 portable change contract routed and checkable."""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import compile_wisdom as compiler  # noqa: E402


SOURCE = ROOT / "WISDOM.md"


def _route_rules(parsed: compiler.ParsedWisdom, task_profile: str) -> set[str]:
    mode, tags = compiler.resolve_task_profile(parsed, task_profile)
    modules = compiler.resolve_module_ids(parsed, mode=mode, tags=tags)
    return {
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


def _change_rule(parsed: compiler.ParsedWisdom) -> str:
    implementation = parsed.section_by_id["implementation"].body.decode("utf-8")
    start = implementation.index("**`CHANGE-01`")
    end = implementation.index("**`ACCEPT-01`", start)
    return implementation[start:end]


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("_", " ").replace("`", "")).casefold()


def test_change_contract_routes_to_material_work_but_not_routine_fast() -> None:
    parsed = compiler.parse_source(SOURCE)
    assert parsed.manifest["semantic_revision"] == 21
    assert parsed.section_by_id["implementation"].rule_ids.count("CHANGE-01") == 1

    for profile in (
        "code_change",
        "bug_fix",
        "delegated_code_change",
        "delegated_bug_fix",
        "delegated_review",
        "protocol_change",
        "external_effect_change",
    ):
        assert "CHANGE-01" in _route_rules(parsed, profile)
    assert "CHANGE-01" not in _route_rules(parsed, "routine")


def test_change_contract_has_generalized_topology_claims_and_receipt_states() -> None:
    parsed = compiler.parse_source(SOURCE)
    rule = _normalized(_change_rule(parsed))
    for phrase in (
        "identity and generation",
        "required: behavior",
        "forbidden: behavior",
        "preserved: adjacent valid behavior",
        "inputs and sources",
        "transformations and decisions",
        "state and representations",
        "boundaries and effects",
        "consumers and observers",
        "alternate and recovery paths",
        "peer or sibling paths",
        "independent oracle",
        "positive witness",
        "negative witness",
        "selector or procedure",
        "result and receipt status",
        "remaining unknown",
        "actual paths examined",
        "topology dispositions",
        "unreachable with evidence",
        "not applicable with reason",
    ):
        assert _normalized(phrase) in rule


def test_change_contract_keeps_dimensions_conditional_and_proof_executed() -> None:
    rule = _normalized(_change_rule(compiler.parse_source(SOURCE)))
    for phrase in (
        "only when their mechanism exists",
        "each present dimension",
        "absent material dimensions a reasoned not-applicable disposition",
        "harmful-suppression twin when valid behavior can be suppressed",
        "otherwise use the nearest forbidden or wrong-result contrast",
        "planned witness is a proof obligation",
        "acceptance consumes source-bound result receipts",
        "pure local transformation may have no persistence",
        "fast work remains exempt",
    ):
        assert _normalized(phrase) in rule


def test_handoff_reuses_same_contract_and_reviewer_checks_reachable_system() -> None:
    parsed = compiler.parse_source(SOURCE)
    delegation = parsed.section_by_id["delegation_contract"].body.decode("utf-8")
    normalized = _normalized(delegation)
    for phrase in (
        "change contract: exact CHANGE-01 identity and generation",
        "fast-route or research-only not-applicable reason",
        "same generation-bound CHANGE-01 contract",
        "actual callers, data structures, state transitions, and consumers",
        "rather than reviewing only the patch",
    ):
        assert _normalized(phrase) in normalized


def test_change_contract_is_portable_and_has_no_local_paths_or_review_links() -> None:
    rule = _change_rule(compiler.parse_source(SOURCE)).casefold()
    assert "chatgpt.com/" not in rule
    assert "personal project" not in rule
    assert re.search(r"\b[a-z]:[/\\]", rule) is None
