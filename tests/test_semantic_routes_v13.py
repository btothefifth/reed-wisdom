"""Independent task facts and old-rule coverage for the v1.3 route contract."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import compile_wisdom as compiler  # noqa: E402
import load_compiled_wisdom as loader  # noqa: E402


SOURCE = ROOT / "WISDOM.md"
V12_RULE_IDS = frozenset(
    """ROUTE-01 ROUTE-02 ROUTE-03 ROUTE-04 STAG-01 STAG-02 STAG-03
    STAG-04 STAG-05 LANG-01 RULE-01 DATA-01 PLANE-01 UPGRADE-01 TEST-01
    SEAL-01 NUM-01 STATE-01 NEG-01 ASYNC-01 ASYNC-02 SOURCE-01 SOURCE-02
    FENCE-01 EXT-01 FRAME-01 OPT-01 OPT-02 OPT-03 HASTE-01 HASTE-02
    ETA-01 CONT-01 RETRO-01 DIAG-01 DEPLOY-01 DELEGATE-01 ADOPT-01
    JUDG-01 JUDG-02 JUDG-03 ASK-01 CPATH-01 RESUME-01 STORE-01""".split()
)


def _declared_rule_ids(parsed: compiler.ParsedWisdom, modules: tuple[str, ...]) -> set[str]:
    kernel_ids = {
        rule_id
        for section in parsed.sections
        if section.section_id in parsed.manifest["kernel_sections"]
        for rule_id in section.rule_ids
    }
    return kernel_ids | {
        rule_id
        for module_id in modules
        for section_id in parsed.module_by_id[module_id]["sections"]
        for rule_id in parsed.section_by_id[section_id].rule_ids
    }


def _profile_modules(parsed: compiler.ParsedWisdom, profile_id: str) -> tuple[str, ...]:
    mode, tags = compiler.resolve_task_profile(parsed, profile_id)
    return compiler.resolve_module_ids(parsed, mode=mode, tags=tags)


def test_v12_hard_rule_ids_survive_nonoverlapping_v13_module_split() -> None:
    parsed = compiler.parse_source(SOURCE)
    declared = [rule_id for section in parsed.sections for rule_id in section.rule_ids]

    assert V12_RULE_IDS <= set(declared)
    assert len(declared) == len(set(declared))
    assert {"DEP-01", "SELECT-01", "ORACLE-01"} <= set(declared)
    assert {"SELECT-01", "ORACLE-01"} <= _declared_rule_ids(
        parsed, _profile_modules(parsed, "selector_gate")
    )

    # Every authored section has exactly one compiled owner, and substantial
    # keeps its prior hard-rule closure during phase adoption. The human-impact
    # lens remains an explicitly selected opt-in module as in v1.2.
    assert len(parsed.section_owner) == len(parsed.sections)
    assert parsed.section_by_id["decision_budget"].body.startswith(
        b"## Bound decision work by a monotonic budget"
    )
    assert parsed.section_by_id["runtime_identity"].body.startswith(
        b"## Verify runtime identity and resource ownership"
    )
    substantial = compiler.resolve_module_ids(parsed, mode="substantial", tags=())
    assert {"decision_budget", "runtime_identity"} <= set(substantial)
    stewardship = {f"STAG-0{index}" for index in range(1, 6)}
    assert V12_RULE_IDS - stewardship <= _declared_rule_ids(parsed, substantial)
    with_human_impact = compiler.resolve_module_ids(
        parsed, mode="substantial", tags=("human_impact",)
    )
    assert V12_RULE_IDS <= _declared_rule_ids(parsed, with_human_impact)


@pytest.mark.parametrize(
    ("task_fact", "profile", "required", "absent"),
    [
        ("small ordinary code edit", "code_change", {"SELECT-01", "ORACLE-01"}, {"EXT-01"}),
        ("reproduced existing defect", "bug_fix", {"SELECT-01", "ORACLE-01"}, {"EXT-01"}),
        ("carrier schema and compatibility changed", "protocol_change", {"PLANE-01", "UPGRADE-01", "EXT-01", "SOURCE-02"}, set()),
        ("current attempt may mutate a provider", "external_effect_change", {"EXT-01", "FENCE-01", "SOURCE-01"}, set()),
        ("immutable release must recover", "release_recovery", {"RESUME-01", "STORE-01", "FENCE-01"}, set()),
        ("measured non-storage resource regression", "performance_investigation", {"CPATH-01", "ORACLE-01"}, {"DATA-01", "EXT-01"}),
        ("later policy required only after an earlier stage", "dependency_gate", {"DEP-01"}, {"EXT-01"}),
        ("exact test manifest claims a complete gate", "selector_gate", {"SELECT-01"}, {"EXT-01"}),
        ("deadline and serialized byte limit", "budget_clock", {"ORACLE-01", "ASYNC-02"}, {"EXT-01"}),
    ],
)
def test_real_task_shapes_select_required_rules_without_accidental_effect_scope(
    task_fact: str,
    profile: str,
    required: set[str],
    absent: set[str],
) -> None:
    parsed = compiler.parse_source(SOURCE)
    modules = _profile_modules(parsed, profile)
    selected = _declared_rule_ids(parsed, modules)

    assert required <= selected, task_fact
    assert not (absent & selected), task_fact
    if profile == "code_change":
        assert modules == ("testing", "test_harness", "implementation_performance")
        artifact = compiler.build_artifacts(parsed)
        selected_bytes = len(parsed.kernel) + sum(
            len(artifact.payloads[f"modules/{module_id}.md"]) for module_id in modules
        )
        assert selected_bytes < len(parsed.raw) // 4


def test_profile_mapping_omission_goes_red_at_independent_rule_expectation(
    tmp_path: Path,
) -> None:
    original = compiler.parse_source(SOURCE)
    original_selected = _declared_rule_ids(
        original, _profile_modules(original, "budget_clock")
    )
    assert "ASYNC-02" in original_selected

    source = tmp_path / "WISDOM.md"
    raw = SOURCE.read_bytes()
    before = b'"id": "budget_clock", "mode": "focused", "tags": ["temporal", "testing"]'
    after = b'"id": "budget_clock", "mode": "focused", "tags": ["testing"]'
    assert raw.count(before) == 1
    source.write_bytes(raw.replace(before, after, 1))
    mutated = compiler.parse_source(source)
    changed_selected = _declared_rule_ids(
        mutated, _profile_modules(mutated, "budget_clock")
    )
    with pytest.raises(AssertionError):
        assert "ASYNC-02" in changed_selected


def test_storage_specific_research_adds_data_contract_without_widening_default() -> None:
    parsed = compiler.parse_source(SOURCE)
    research_mode, research_tags = compiler.resolve_task_profile(parsed, "research")
    baseline = compiler.resolve_module_ids(
        parsed, mode=research_mode, tags=research_tags
    )
    storage_specific = compiler.resolve_module_ids(
        parsed, mode=research_mode, tags=(*research_tags, "storage")
    )

    assert "DATA-01" not in _declared_rule_ids(parsed, baseline)
    assert "DATA-01" in _declared_rule_ids(parsed, storage_specific)
    assert set(baseline) < set(storage_specific)


def test_phase_transition_reloads_before_protected_release_action(tmp_path: Path) -> None:
    cache = tmp_path / "compiled"
    compiler.compile_and_install(SOURCE, cache)
    implementation = loader.load_plan(
        SOURCE, cache, task_profile="bug_fix", phase="implement"
    )
    release = loader.load_plan(SOURCE, cache, task_profile="bug_fix", phase="release")
    design = loader.load_plan(SOURCE, cache, task_profile="bug_fix", phase="design")
    observation = loader.load_plan(SOURCE, cache, task_profile="bug_fix", phase="observe")
    unknown = loader.load_plan(
        SOURCE, cache, task_profile="bug_fix", phase="unrecognized"
    )

    assert implementation["status"] == release["status"] == "compiled"
    assert "delivery_status" not in implementation["module_ids"]
    assert "delivery_status" in release["module_ids"]
    assert "decision_budget" in design["module_ids"]
    assert "runtime_identity" in observation["module_ids"]
    assert set(implementation["module_ids"]) <= set(release["module_ids"])
    assert b"## Publish, deploy, monitor, and roll back" in loader.read_plan_content(release)
    assert unknown["status"] == "full_source_required"
    assert loader.read_plan_content(unknown) == SOURCE.read_bytes()


def test_external_effect_rule_names_current_attempt_and_transport_layers() -> None:
    parsed = compiler.parse_source(SOURCE)
    effect = parsed.section_by_id["effect_harness"].body.decode("utf-8")
    assert re.search(r"one immutable current-attempt identity", effect)
    assert "preexisting provider object" in effect
    assert "zero current-attempt transport" in effect
    assert "terminal reconciliation" in effect


def test_reached_dependency_uses_real_loader_terminal_order_and_go_red_cutpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = tmp_path / "compiled"
    compiler.compile_and_install(SOURCE, cache)

    def later_dependency_was_consulted(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unreached phase metadata was consulted")

    # Independent oracle: the authored full-source fallback is terminal before
    # profile/phase parsing. Moving phase validation before it triggers this spy.
    with monkeypatch.context() as patch:
        patch.setattr(loader, "parse_source", later_dependency_was_consulted)
        earlier_unknown = loader.load_plan(
            SOURCE,
            cache,
            task_profile="unrecognized",
            phase="unrecognized",
            unknown_impact=True,
        )
        earlier_full = loader.load_plan(SOURCE, cache, mode="full", phase="unrecognized")

    reached_missing = loader.load_plan(
        SOURCE, cache, task_profile="routine", phase="unrecognized"
    )
    sibling_not_selected = loader.load_plan(SOURCE, cache, task_profile="routine")
    nearest_valid = loader.load_plan(
        SOURCE, cache, task_profile="routine", phase="implement"
    )

    assert (earlier_unknown["status"], earlier_unknown["reason"]) == (
        "full_source_required",
        "unknown_impact",
    )
    assert (earlier_full["status"], earlier_full["reason"]) == (
        "full_source_required",
        "full_mode",
    )
    assert (reached_missing["status"], reached_missing["reason"]) == (
        "full_source_required",
        "phase_unavailable:WisdomCompileError",
    )
    assert sibling_not_selected["status"] == nearest_valid["status"] == "compiled"
    assert sibling_not_selected["module_ids"] == []
    assert loader.read_plan_content(reached_missing) == SOURCE.read_bytes()
