"""Keep the v1.10 application discipline routed, ordered, and proportionate."""

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


def _route_rules(parsed: compiler.ParsedWisdom, profile_id: str) -> set[str]:
    mode, tags = compiler.resolve_task_profile(parsed, profile_id)
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
    implementation = _section(parsed, "implementation")
    start = implementation.index("**`CHANGE-01`")
    end = implementation.index("**`ACCEPT-01`", start)
    return implementation[start:end]


def test_v110_reuses_existing_rules_and_routes() -> None:
    parsed = compiler.parse_source(SOURCE)
    assert parsed.manifest["semantic_revision"] == 18
    assert len(parsed.manifest["modules"]) == 23
    assert parsed.section_by_id["implementation"].rule_ids.count("CHANGE-01") == 1
    assert parsed.section_by_id["implementation"].rule_ids.count("SEM-01") == 1

    for profile in (
        "code_change",
        "bug_fix",
        "delegated_code_change",
        "delegated_bug_fix",
        "delegated_review",
    ):
        assert {"CHANGE-01", "SEM-01"} <= _route_rules(parsed, profile)
    assert "CHANGE-01" not in _route_rules(parsed, "routine")


def test_fast_route_runs_named_direct_oracle_without_extra_artifacts() -> None:
    router = _normalized(_section(compiler.parse_source(SOURCE), "start"))
    for phrase in (
        "when the request names an existing direct oracle, run it unchanged",
        "do not add or modify tests, documentation, or process artifacts",
        "unless that oracle cannot distinguish the required behavior",
        "reroute to focused if repairing the proof seam becomes material",
    ):
        assert _normalized(phrase) in router


def test_material_change_loop_is_complete_and_ordered() -> None:
    change = _normalized(_change_rule(compiler.parse_source(SOURCE)))
    stages = ["frame:", "trace:", "join:", "implement:", "disprove:", "close:"]
    positions = [change.index(stage) for stage in stages]
    assert positions == sorted(positions)
    for phrase in (
        "required, forbidden, and preserved behavior",
        "producer, carrier, state, consumer, recovery, and sibling paths",
        "state, owner, deadline, acceptance event, evidence, and failure disposition",
        "smallest complete owning seam",
        "first consequential consumer",
        "invalidate evidence affected by later edits",
        "not another artifact or review stage",
    ):
        assert _normalized(phrase) in change


def test_application_gate_names_every_red_condition() -> None:
    change = _normalized(_change_rule(compiler.parse_source(SOURCE)))
    for phrase in (
        "consequential consumer has no evidence-backed disposition",
        "evidence belongs to another source, input, boundary, or ownership generation",
        "receipt proves only admission, acknowledgment, start, return, or publication",
        "witness exits before the named production predicate or consumer boundary",
        "intended or preserved witness or its applicable negative twin is missing",
        "ownership, accepted work, or external effect remains uncertain",
        "final behavior-bearing edit occurred after the supporting evidence",
        "unresolved obligation can still change the claimed outcome",
        "distinct from a retained go-red mutation",
    ):
        assert _normalized(phrase) in change


def test_contrast_pairs_reject_intermediate_completion_claims() -> None:
    change = _normalized(_change_rule(compiler.parse_source(SOURCE)))
    for phrase in (
        "request or transport success",
        "current authoritative terminal observation",
        "receipt or admission",
        "exact same-generation acceptance event observed at that consumer",
        "scheduled or expected child start",
        "exact child identity plus an independently observed creation result",
        "observed child creation",
        "independently observed acceptance by the new owner",
        "boundary-reach evidence plus the real consumer result",
        "rerun of the invalidated frontier against the final source",
        "positive preserved-behavior twin at the same consumer",
        "bounded consumer inventory with evidence-backed dispositions",
        "independent current observation of the claimed terminal state",
    ):
        assert _normalized(phrase) in change


def test_phase_refresh_reuses_existing_contract_and_evidence() -> None:
    implementation = _normalized(_section(compiler.parse_source(SOURCE), "implementation"))
    for phrase in (
        "derived view of existing contract and evidence",
        "never a fifth semantic artifact",
        "an unknown material answer keeps the application gate red",
        "before editing",
        "what must remain possible",
        "which boundary owns the behavior",
        "before validation",
        "which exact predicate must the witness reach",
        "which independent oracle decides the result",
        "before completion or transfer",
        "does its evidence match the final generation",
        "did any later edit invalidate proof",
        "return to the earliest affected loop step",
    ):
        assert _normalized(phrase) in implementation


def test_behavioral_drill_is_maintainer_evidence_without_user_infrastructure() -> None:
    bootstrap = _normalized(_section(compiler.parse_source(SOURCE), "bootstrap_acceptance"))
    for phrase in (
        "matched application-fidelity drill",
        "three fresh isolated sessions",
        "unassisted run no wisdom",
        "stable run the prior stable routed wisdom view",
        "candidate run the exact current routed view",
        "same less-capable target model, settings, tools, workspace seed and environment, budget, and high-level prompt",
        "using a separate clean copy for each arm",
        "do not leak the scoring rubric or expert procedure into any task prompt",
        "correctness and false-completion prevention dominate efficiency",
        "bootstrap-maintainer release drills",
        "not user ci, project ceremony, or a dependency of ordinary wisdom operation",
    ):
        assert _normalized(phrase) in bootstrap


def test_backlog_contains_exactly_three_unselected_potential_ideas() -> None:
    backlog = (ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
    assert "not part of WISDOM v1.10" in backlog
    assert "do not create current obligations" in backlog
    assert re.findall(r"^## (.+)$", backlog, flags=re.MULTILINE) == [
        "Compact internal working state",
        "Omission recovery procedure",
        "Standard lesson structure",
    ]


def test_v110_language_remains_project_independent() -> None:
    changed_guidance = (_change_rule(compiler.parse_source(SOURCE)) + "\n" + (
        ROOT / "docs" / "BACKLOG.md"
    ).read_text(encoding="utf-8")).casefold()
    for forbidden in ("personal project", "chatgpt.com/s/", "project-specific workflow"):
        assert forbidden not in changed_guidance
    assert re.search(r"\b[a-z]:[/\\]", changed_guidance) is None
