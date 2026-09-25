"""Keep v1.4 proof-frontier rules on the existing test and release routes."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import compile_wisdom as compiler  # noqa: E402
import load_compiled_wisdom as loader  # noqa: E402


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


def test_v14_rules_use_existing_code_change_and_release_routes(tmp_path: Path) -> None:
    parsed = compiler.parse_source(SOURCE)
    artifact = compiler.build_artifacts(parsed)
    code_change_mode, code_change_tags = compiler.resolve_task_profile(
        parsed, "code_change"
    )
    bug_fix_mode, bug_fix_tags = compiler.resolve_task_profile(parsed, "bug_fix")
    code_change_modules = compiler.resolve_module_ids(
        parsed, mode=code_change_mode, tags=code_change_tags
    )
    bug_fix_modules = compiler.resolve_module_ids(
        parsed, mode=bug_fix_mode, tags=bug_fix_tags
    )

    code_change_ids = _rule_ids(parsed, code_change_modules)
    bug_fix_ids = _rule_ids(parsed, bug_fix_modules)
    routine_mode, routine_tags = compiler.resolve_task_profile(parsed, "routine")
    routine_ids = _rule_ids(
        parsed, compiler.resolve_module_ids(parsed, mode=routine_mode, tags=routine_tags)
    )
    assert "IMPACT-01" in parsed.section_by_id["test_harness"].rule_ids
    assert "PROMOTE-01" in parsed.section_by_id["delivery_status"].rule_ids
    assert "IMPACT-01" in code_change_ids & bug_fix_ids
    assert "PROMOTE-01" not in code_change_ids
    assert "IMPACT-01" not in routine_ids
    assert "PROMOTE-01" not in routine_ids
    assert code_change_modules == ("testing", "test_harness", "implementation_performance")

    cache = tmp_path / "compiled"
    compiler.compile_and_install(SOURCE, cache)
    release = loader.load_plan(
        SOURCE, cache, task_profile="code_change", phase="release"
    )
    assert release["status"] == "compiled"
    assert "delivery_status" in release["module_ids"]
    release_ids = _rule_ids(parsed, tuple(release["module_ids"]))
    assert "IMPACT-01" in release_ids
    assert "PROMOTE-01" in release_ids

    compiled_test_harness = artifact.payloads["modules/test_harness.md"].decode("utf-8")
    compiled_delivery = artifact.payloads["modules/delivery_status.md"].decode("utf-8")
    assert "**`IMPACT-01`" in compiled_test_harness
    assert "**`PROMOTE-01`" in compiled_delivery


@pytest.mark.parametrize(
    ("surface", "required_phrases"),
    [
        (
            "test_harness",
            (
                "unaffected,\ninvalidated, or unknown-impact",
                "remain at the cheapest red tier",
                "stop at any\nstate-contamination or trust boundary",
                "never rewrite expected output to match candidate behavior",
                "requires one candidate generation",
                "preserve unrelated receipts whose dependencies are unchanged",
                "one broad run reports multiple independent failures",
                "rerun the failed selectors and affected closure",
                "expensive rehearsal finds a cheaper-reproducible defect",
            ),
        ),
        (
            "delivery_status",
            (
                "cheaper\nproduction-faithful check",
                "Freeze the candidate identity for\nthe gate's lifetime.",
                "one same-generation aggregate",
                "reversible, authority-off\nstaging step",
            ),
        ),
    ],
)
def test_v14_rule_text_preserves_failure_repair_and_promotion_boundaries(
    surface: str, required_phrases: tuple[str, ...]
) -> None:
    parsed = compiler.parse_source(SOURCE)
    module_id = "test_harness" if surface == "test_harness" else "delivery_status"
    module_text = "\n".join(
        parsed.section_by_id[section_id].body.decode("utf-8")
        for section_id in parsed.module_by_id[module_id]["sections"]
    )

    for phrase in required_phrases:
        assert phrase in module_text


def test_v14_distinguishes_incremental_impact_from_retrospective_rule_audit() -> None:
    parsed = compiler.parse_source(SOURCE)
    all_rule_ids = [rule_id for section in parsed.sections for rule_id in section.rule_ids]

    assert all_rule_ids.count("IMPACT-01") == 1
    assert all_rule_ids.count("PROMOTE-01") == 1
    assert all_rule_ids.count("RETRO-01") == 1
    assert "IMPACT-01" in parsed.section_by_id["test_harness"].rule_ids
    assert "RETRO-01" in parsed.section_by_id["process_cost"].rule_ids
