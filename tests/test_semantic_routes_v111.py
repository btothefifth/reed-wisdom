"""Keep v1.11 teaching optional, source-bound, neutral, and proportionate."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import compile_wisdom as compiler  # noqa: E402
import load_compiled_wisdom as loader  # noqa: E402


SOURCE = ROOT / "WISDOM.md"
LESSONS = {
    "lesson_dependency": (
        "Teaching support: conditional dependency reachability",
        ["protocol_identity"],
        ["architecture_authority", "protocol_identity", "lesson_dependency"],
        {"DEP-01": "protocol_identity"},
    ),
    "lesson_acceptance": (
        "Teaching support: acceptance, ownership, and reconciliation",
        ["implementation_performance"],
        ["testing", "test_harness", "implementation_performance", "lesson_acceptance"],
        {"ACCEPT-01": "implementation"},
    ),
    "lesson_evidence_recovery": (
        "Teaching support: affected evidence and omission recovery",
        ["implementation_performance"],
        ["testing", "test_harness", "implementation_performance", "lesson_evidence_recovery"],
        {"CHANGE-01": "implementation", "SCOPE-01": "implementation", "IMPACT-01": "test_harness"},
    ),
}


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("`", "")).casefold()


def _teach(parsed: compiler.ParsedWisdom) -> str:
    start = parsed.section_by_id["start"].body.decode("utf-8").replace("\r\n", "\n")
    return start[start.index("**`TEACH-01`"):start.index("```text\nroute_wisdom")]


def _assert_phrases(text: str, phrases: tuple[str, ...]) -> None:
    normalized = _normalized(text)
    for phrase in phrases:
        assert _normalized(phrase) in normalized


def _independent_lesson_bytes(raw: bytes, heading: str) -> bytes:
    marker = b"## " + heading.encode("utf-8")
    start = raw.index(marker)
    assert raw[start - 1:start] == b"\n"
    next_heading = re.search(rb"(?m)^## ", raw[start + len(marker):])
    assert next_heading is not None
    end = start + len(marker) + next_heading.start()
    return raw[start:end]


def test_v111_preserves_single_rule_owners_and_existing_schemas() -> None:
    parsed = compiler.parse_source(SOURCE)
    assert parsed.manifest["semantic_revision"] == 19
    assert len(parsed.manifest["modules"]) == 26
    assert len(parsed.manifest["allowed_tags"]) == 40
    assert parsed.manifest["schema"] == "wisdom.portable_bootstrap.source.v1"
    assert loader.LOAD_PLAN_SCHEMA == "wisdom.compiled.load_plan.v2"
    owners = {
        rule: section.section_id
        for section in parsed.sections
        for rule in section.rule_ids
    }
    assert len(owners) == sum(len(section.rule_ids) for section in parsed.sections)
    assert owners["TEACH-01"] == "start"
    for lesson, (_, _, _, normative) in LESSONS.items():
        assert parsed.section_by_id[lesson].rule_ids == ()
        for rule, owner in normative.items():
            assert owners[rule] == owner


def test_teaching_selection_uses_current_evidence_and_remains_neutral() -> None:
    parsed = compiler.parse_source(SOURCE)
    teach = _teach(parsed)
    _assert_phrases(teach, (
        "Select the ordinary execution route first",
        "current task evidence shows a specific missing distinction",
        "A model name, vendor, size, self-description, workflow, or permanent capability label is not such evidence",
        "scoped to the task shape and evidence generation",
        "expire it when the task, tools, or demonstrated behavior changes",
        "Worker topology is independent of instruction depth",
    ))
    added = teach + "\n" + "\n".join(
        parsed.section_by_id[lesson].body.decode("utf-8") for lesson in LESSONS
    )
    assert re.search(r"\b(?:gpt[-\w]*|chatgpt|openai|anthropic|claude|reedout|astra|luna|sol)\b", added, re.I) is None
    assert re.search(r"\bworkflow[1-4]\b|\b[a-z]:[/\\]", added, re.I) is None


def test_solo_completeness_and_coordinated_workers_have_same_proof_boundary() -> None:
    _assert_phrases(_teach(compiler.parse_source(SOURCE)), (
        "One worker must be able to perform the complete route serially",
        "separating implementation, self-review, and validation as bounded passes",
        "independence from the oracle, source, or alternate derivation",
        "rather than pretending to be a separate reviewer",
        "Several workers of the same or different capabilities may divide roles",
        "one integration owner",
        "their number or diversity supplies no authority or proof by itself",
        "When delegation, hosted automation, continuous integration, network access, or a specialized tool is unavailable",
        "smallest local or serial mechanism that proves the same invariant",
        "state the remaining evidence limit honestly",
    ))


def test_support_levels_have_bounded_stop_and_reopen_conditions() -> None:
    _assert_phrases(_teach(compiler.parse_source(SOURCE)), (
        "core applies the owning normative rule",
        "contrast adds the nearest misleading intermediate fact or harmful inverse",
        "worked traces one structurally representative example through the real consumer and independent oracle",
        "recovery shows the earliest affected step to reopen after an omission while preserving unaffected evidence",
        "Choose the smallest level that can change behavior",
        "Stop added teaching when an intended case, its nearest contrast, and an unfamiliar structural sibling reach the correct consumer with preserved valid behavior",
        "when a mechanical control now supplies the capability",
        "Reopen it only for a materially different case or recurrence",
        "when delegation exists, CAPABILITY-01 governs any reassignment",
        "Do not answer recurrence by indefinitely expanding prose",
        "support moves a hard obligation into optional text",
        "treats a filled lesson as evidence",
        "adds ceremony to a fast direct-oracle task",
    ))


def test_lesson_envelope_does_not_impose_output_or_runtime_order() -> None:
    _assert_phrases(_teach(compiler.parse_source(SOURCE)), (
        "WHEN / UNDERSTAND / INSPECT / DO / REJECT / PROVE / RECOVER / STOP",
        "an authoring envelope, not a required output format, artifact, or execution order",
        "Omit an immaterial heading",
        "A known denial may REJECT before work",
        "an unreached dependency may STOP without inspection",
        "execution may stop while ownership remains until reconciliation",
        "Preserve state machines, truth tables, mathematics, or pseudocode",
    ))


def test_ordinary_routes_exclude_optional_lessons_and_keep_fast_oracle() -> None:
    parsed = compiler.parse_source(SOURCE)
    assert compiler.resolve_module_ids(parsed, mode="fast", tags=[]) == ()
    for profile in parsed.manifest["task_profiles"]:
        mode, tags = compiler.resolve_task_profile(parsed, profile["id"])
        assert not set(LESSONS).intersection(compiler.resolve_module_ids(parsed, mode=mode, tags=tags))
    for mode in ("fast", "focused", "substantial"):
        assert not set(LESSONS).intersection(compiler.resolve_module_ids(parsed, mode=mode, tags=[]))
    _assert_phrases(parsed.kernel.decode("utf-8"), (
        "when the request names an existing direct oracle, run it unchanged",
        "do not add or modify tests, documentation, or process artifacts",
        "a required action-relevant example is",
        "unrepresented by the existing direct oracle",
        "temporary non-mutating probe",
        "the absent coverage is itself the defect",
    ))
    for lesson in LESSONS:
        assert parsed.section_by_id[lesson].body not in parsed.kernel


@pytest.mark.parametrize("lesson", list(LESSONS))
def test_explicit_lesson_tag_delivers_exact_lesson_and_normative_closure(tmp_path: Path, lesson: str) -> None:
    heading, requires, expected, normative = LESSONS[lesson]
    parsed = compiler.parse_source(SOURCE)
    assert parsed.module_by_id[lesson]["requires"] == requires
    assert parsed.module_by_id[lesson]["tags"] == [lesson]
    cache = tmp_path / "cache"
    compiler.compile_and_install(SOURCE, cache)
    plan = loader.load_plan(SOURCE, cache, mode="fast", tags=[lesson])
    assert plan["status"] == "compiled"
    assert plan["module_ids"] == expected
    content = loader.read_plan_content(plan)
    expected_lesson = _independent_lesson_bytes(SOURCE.read_bytes(), heading)
    assert Path(plan["content_paths"][-1]).read_bytes() == expected_lesson
    assert content == parsed.kernel + b"".join(
        b"".join(parsed.section_by_id[section].body for section in parsed.module_by_id[module]["sections"])
        for module in expected
    )
    for rule in normative:
        assert ("**`" + rule + "`").encode("ascii") in content
    for excluded in set(LESSONS) - {lesson}:
        assert parsed.section_by_id[excluded].body not in content


@pytest.mark.parametrize("lesson", list(LESSONS))
def test_lesson_examples_preserve_their_failure_family(lesson: str) -> None:
    parsed = compiler.parse_source(SOURCE)
    text = parsed.section_by_id[lesson].body.decode("utf-8")
    assert set(re.findall(r"\*\*([A-Z]+):\*\*", text)) == {
        "WHEN", "UNDERSTAND", "INSPECT", "DO", "REJECT", "PROVE", "RECOVER", "STOP",
    }
    phrases = {
        "lesson_dependency": (
            "that rule remains the authority",
            "one case terminates before the dependency and succeeds while it is absent",
            "another reaches the dependency and fails closed when it is absent",
            "nearest valid reached case",
            "heading order describes the lesson, not the runtime",
        ),
        "lesson_acceptance": (
            "that rule remains the authority",
            "Silence, timeout, exception, or a missing result does not prove absence",
            "When batch or partial-acceptance semantics exist",
            "a singleton needs no invented sibling",
            "every submitted identity has one terminal disposition",
            "their agreement does not replace the authoritative consumer observation",
        ),
        "lesson_evidence_recovery": (
            "those rules remain the authority",
            "unaffected, invalidated, or unknown-impact",
            "When an independently unchanged dependency set exists",
            "when every receipt is affected",
            "Replace only invalidated receipts",
            "Neither topology changes the evidence required for completion",
        ),
    }
    _assert_phrases(text, phrases[lesson])


@pytest.mark.parametrize("reason", ["missing_cache", "unknown_impact", "stale_cache"])
def test_full_source_fallback_retains_complete_lesson_authority(tmp_path: Path, reason: str) -> None:
    source = tmp_path / "WISDOM.md"
    source.write_bytes(SOURCE.read_bytes())
    cache = tmp_path / "cache"
    if reason == "stale_cache":
        compiler.compile_and_install(source, cache)
        source.write_bytes(source.read_bytes() + b"\n")
    plan = loader.load_plan(source, cache, mode="fast", unknown_impact=reason == "unknown_impact")
    assert plan["status"] == "full_source_required"
    assert plan["authority"] is False
    assert plan["content_paths"] == [str(source.resolve())]
    assert plan["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert loader.read_plan_content(plan) == source.read_bytes()
    for heading, _, _, _ in LESSONS.values():
        assert heading.encode("utf-8") in loader.read_plan_content(plan)


def test_backlog_selects_teaching_and_keeps_only_two_potential_ideas() -> None:
    backlog = (ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
    selected, potential = backlog.split("# Potential backlog\n", 1)
    assert re.findall(r"^## (.+)$", selected, flags=re.MULTILINE) == ["Selected: v1.11 portable teaching support"]
    assert re.findall(r"^## (.+)$", potential, flags=re.MULTILINE) == [
        "Compact internal working state", "Omission recovery procedure",
    ]
    _assert_phrases(selected, (
        "one worker can execute every route",
        "no hard rule moves into optional lesson text",
        "no second worker, hosted service, or automation system becomes mandatory",
        "bounded fresh-session trials support only claims they observe",
    ))
    assert "do not create current" in potential.casefold()
