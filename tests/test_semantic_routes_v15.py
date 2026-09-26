"""Keep WISDOM review-scope rules on the normal implementation route."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import compile_wisdom as compiler  # noqa: E402


SOURCE = ROOT / "WISDOM.md"


def _rule_ids(parsed: compiler.ParsedWisdom, module_ids: tuple[str, ...]) -> set[str]:
    kernel_ids = {
        rule_id
        for section in parsed.sections
        if section.section_id in parsed.manifest["kernel_sections"]
        for rule_id in section.rule_ids
    }
    module_rule_ids = {
        rule_id
        for module_id in module_ids
        for section_id in parsed.module_by_id[module_id]["sections"]
        for rule_id in parsed.section_by_id[section_id].rule_ids
    }
    return kernel_ids | module_rule_ids


def test_scope_rule_is_compiled_for_code_changes_and_bug_fixes() -> None:
    parsed = compiler.parse_source(SOURCE)
    artifact = compiler.build_artifacts(parsed)

    code_mode, code_tags = compiler.resolve_task_profile(parsed, "code_change")
    bug_mode, bug_tags = compiler.resolve_task_profile(parsed, "bug_fix")
    routine_mode, routine_tags = compiler.resolve_task_profile(parsed, "routine")
    code_modules = compiler.resolve_module_ids(parsed, mode=code_mode, tags=code_tags)
    bug_modules = compiler.resolve_module_ids(parsed, mode=bug_mode, tags=bug_tags)
    routine_modules = compiler.resolve_module_ids(
        parsed, mode=routine_mode, tags=routine_tags
    )

    assert parsed.manifest["semantic_revision"] == 14
    assert "SCOPE-01" in parsed.section_by_id["implementation"].rule_ids
    assert "SCOPE-01" in _rule_ids(parsed, code_modules)
    assert "SCOPE-01" in _rule_ids(parsed, bug_modules)
    assert "SCOPE-01" not in _rule_ids(parsed, routine_modules)
    assert "**`SCOPE-01`" in artifact.payloads[
        "modules/implementation_performance.md"
    ].decode("utf-8")


def test_scope_rule_keeps_review_ownership_and_expansion_boundaries_explicit() -> None:
    parsed = compiler.parse_source(SOURCE)
    implementation = parsed.section_by_id["implementation"].body.decode("utf-8")
    delegation = parsed.section_by_id["context_delegation"].body.decode("utf-8")

    for phrase in (
        "owned delta",
        "semantic frontier",
        "integration delta",
        "repository frontier",
        "does not inherit unrelated pre-existing branch changes or sibling",
        "independently reviews the implementer's owned delta and semantic frontier",
        "independently reviews the integration delta and cross-lane interactions",
        "Scope limits responsibility, not observation.",
        "mechanically enumerate\nthe affected consumers",
        "the full repository is the\nonly defensible boundary",
        "`IMPACT-01` proof-frontier recomputation",
    ):
        assert phrase in implementation

    for field in (
        "assignment_baseline:",
        "owned_delta:",
        "semantic_frontier:",
        "review_obligation:",
        "integration_baseline:",
        "exclusions:",
        "escalation_triggers:",
    ):
        assert field in delegation


def test_scope_rule_decision_table_covers_workers_integrators_and_unknown_impact() -> None:
    parsed = compiler.parse_source(SOURCE)
    implementation = parsed.section_by_id["implementation"].body.decode("utf-8")

    for phrase in (
        "Worker on a multi-lane feature",
        "Root integrating multiple lanes",
        "Shared or global primitive change",
        "Unknown impact",
        "Routine implementation with unrelated unchanged files",
        "Do not re-review unrelated repository areas",
    ):
        assert phrase in implementation
