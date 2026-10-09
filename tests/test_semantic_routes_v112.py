"""Keep the v1.12 semantic validation target concrete and proportional."""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import compile_wisdom as compiler  # noqa: E402


SOURCE = ROOT / "WISDOM.md"


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("`", "")).casefold()


def _section(parsed: compiler.ParsedWisdom, section_id: str) -> str:
    return parsed.section_by_id[section_id].body.decode("utf-8")


def _assert_phrases(text: str, phrases: tuple[str, ...]) -> None:
    normalized = _normalized(text)
    for phrase in phrases:
        assert _normalized(phrase) in normalized


def test_v112_preserves_route_schema() -> None:
    parsed = compiler.parse_source(SOURCE)
    assert parsed.manifest["semantic_revision"] == 21
    assert len(parsed.manifest["modules"]) == 26
    assert len(parsed.manifest["allowed_tags"]) == 40
    assert parsed.manifest["schema"] == "wisdom.portable_bootstrap.source.v1"


def test_material_validation_names_the_final_semantic_target() -> None:
    implementation = _section(compiler.parse_source(SOURCE), "implementation")
    _assert_phrases(implementation, (
        "final effective producer or surviving state is used by this invocation after setup and overrides",
        "exact predicate must the witness reach and which acting consumer uses it",
        "complete contract-valid outcome set",
        "what justifies any exact value, count, order, or refusal",
        "which intermediate facts could mislead",
        "which independent oracle decides the result",
        "semantic_validation_target",
        "final_installed_producer",
        "acting_consumer",
        "valid_outcome_set",
        "exactness_basis",
        "misleading_intermediates",
        "oracle",
    ))


def test_exact_expectations_require_contract_complete_outcomes() -> None:
    tests = _section(compiler.parse_source(SOURCE), "tests")
    _assert_phrases(tests, (
        "Before asserting an exact value, count, order, member set, or refusal",
        "complete bounded set of outcomes that the owning contract permits at the acting consumer",
        "justify why every included and excluded possibility has that disposition",
        "assert the stable property, invariant, or bounded typed result set",
        "Fixture construction, one observed run, preserved assertions, unchanged source bytes, or a matching snapshot",
        "neither completeness nor semantic correctness by itself",
    ))


def test_exactness_challenge_repairs_evidence_before_production() -> None:
    implementation = _section(compiler.parse_source(SOURCE), "implementation")
    _assert_phrases(implementation, (
        "another contract-valid outcome when one exists",
        "applicable later overwrite, reorder, or authority transition when that mechanism can change consumption",
        "Do not invent an alternate outcome or transition for a deterministic singleton whose contract excludes it",
        "classify and repair the earliest fixture, oracle, setup, or contract defect before changing production behavior",
        "reuse the existing positive, preserved, negative, and go-red witnesses",
        "does not add a review stage",
    ))


def test_semantic_target_is_derived_and_fast_work_stays_direct() -> None:
    parsed = compiler.parse_source(SOURCE)
    implementation = _section(parsed, "implementation")
    _assert_phrases(implementation, (
        "existing contract or test-evidence record",
        "This is a derived view, not another required artifact or serialized form",
        "references in the existing record are sufficient",
        "A simple direct-oracle case needs only the ordinary assertion and caller trace",
    ))
    assert b"semantic_validation_target" not in parsed.kernel
    assert compiler.resolve_module_ids(parsed, mode="fast", tags=[]) == ()
    assert compiler.resolve_module_ids(parsed, mode="focused", tags=[]) == (
        "testing", "test_harness", "implementation_performance",
    )


def test_fixture_or_oracle_failures_are_classified_before_product_changes() -> None:
    parsed = compiler.parse_source(SOURCE)
    harness = _section(parsed, "test_harness")
    _assert_phrases(harness, (
        "Before changing production to resolve a failing behavioral assertion",
        "production defect, fixture or reachability defect, expectation or oracle defect, infrastructure failure, or unresolved",
        "Repair an invalid fixture or oracle at its owning seam",
        "do not broaden expected behavior merely to accommodate the candidate",
    ))
    _assert_phrases(harness, (
        "When the contract is unchanged and the expectation faithfully represents it",
        "When independent evidence instead demonstrates an expectation or oracle defect",
        "repair that evidence owner without changing production behavior",
        "Never rewrite expected output to match candidate behavior",
    ))


def test_v112_guidance_remains_project_model_and_workflow_neutral() -> None:
    parsed = compiler.parse_source(SOURCE)
    guidance = (_section(parsed, "tests") + "\n" + _section(parsed, "implementation")).casefold()
    assert re.search(r"\b(?:reedout|chatgpt|openai|anthropic|claude|astra|luna|sol)\b", guidance) is None
    assert re.search(r"\bworkflow[1-9]\b|\b[a-z]:[/\\]", guidance, re.I) is None


def test_backlog_selects_v112_and_preserves_potential_ideas() -> None:
    backlog = (ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
    selected, potential = backlog.split("# Potential backlog\n", 1)
    assert re.findall(r"^## (.+)$", selected, flags=re.MULTILINE) == [
        "Selected: v1.12 semantic validation target",
    ]
    assert re.findall(r"^## (.+)$", potential, flags=re.MULTILINE) == [
        "Compact internal working state", "Omission recovery procedure",
    ]
    _assert_phrases(selected, (
        "final effective producer",
        "complete valid outcome set",
        "alternate valid outcome",
        "no project-specific example",
        "simple direct-oracle work gains no ceremony",
        "public tag, release asset, main branch, and installed bytes agree",
    ))
