"""Check rule ownership/routing and real loader invocation, not model behavior."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import compile_wisdom as compiler  # noqa: E402


@pytest.mark.parametrize("marker,section_id,route", (
    (b"At a bounded data boundary, admit every selected variable field", "storage_design", "storage"),
    (b"Eligibility retirement and byte/resource release are distinct events", "storage_design", "storage"),
    (b"Before implementing a consequential data or proof path", "performance", "implementation"),
    (b"Before consequential use of a new or changed executable helper", "test_harness", "implementation"),
    (b"Review must check the applicable WISDOM owners", "implementation", "implementation"),
    (b"Before copying policy or extracting a helper", "implementation", "implementation"),
    (b"For a new helper or operation API", "implementation", "implementation"),
    (b"Capture one validated immutable typed input generation", "performance", "implementation"),
    (b"Admission must account for actual blocking work", "async_lifecycle", "temporal"),
    (b"Preserve the original root code and fixed producer stage", "diagnostics", "diagnostics"),
))
def test_enforcement_has_one_owner_and_reaches_its_existing_route(marker, section_id, route):
    parsed = compiler.parse_source(ROOT / "WISDOM.md")
    assert marker not in parsed.kernel
    assert [section.section_id for section in parsed.sections if marker in section.body] == [section_id]
    selected = compiler.resolve_module_ids(parsed, mode="focused", tags=[route])
    assert any(section_id in parsed.module_by_id[module_id]["sections"] for module_id in selected)


def test_v114_preserves_fast_kernel_and_existing_rule_topology():
    parsed = compiler.parse_source(ROOT / "WISDOM.md")
    assert parsed.manifest["semantic_revision"] == 21
    assert len(parsed.manifest["modules"]) == 26
    assert len(parsed.manifest["allowed_tags"]) == 40
    assert hashlib.sha256(parsed.kernel[len(parsed.preamble):]).hexdigest() == (
        "22179848023a8a539524d7a97df795ef9d8a79f6517c78cb62fdcc83e6448528"
    )
    assert compiler.resolve_module_ids(parsed, mode="fast", tags=[]) == ()
    assert compiler.resolve_module_ids(parsed, mode="focused", tags=[]) == (
        "testing", "test_harness", "implementation_performance",
    )
    assert parsed.section_by_id["storage_design"].rule_ids == ("DATA-01",)
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "1.14.0"
    assert b"Product version: 1.14.0" in parsed.preamble


@pytest.mark.parametrize("profile", (
    "code_change", "performance_investigation", "research", "architecture", "protocol_change",
))
def test_consequential_cost_model_reaches_nonstorage_and_storage_profiles(profile):
    parsed = compiler.parse_source(ROOT / "WISDOM.md")
    mode, tags = compiler.resolve_task_profile(parsed, profile)
    selected = compiler.resolve_module_ids(parsed, mode=mode, tags=tags)
    content = b"".join(parsed.section_by_id[section_id].body
                       for module_id in selected
                       for section_id in parsed.module_by_id[module_id]["sections"])
    assert b"Before implementing a consequential data or proof path" in content


@pytest.mark.parametrize("section_id,predicates", (
    ("storage_design", (
        "before native hydration or parser construction allocates its body",
        "actual byte size", "aggregate allocation, including nullable joins",
        "Preserve the authoritative selection and generation between preflight and hydration",
        "bounded valid neighbor and permitted null remain accepted",
        "Keep the charge through every supported alias and active unwind until the last actual holder stops using the data or resource",
        "rather than refunding early or evicting active work",
    )),
    ("implementation", (
        "A material violation or missing required witness keeps acceptance blocked until repaired or the claim is narrowed to the proved scope",
        "Distinguish an inapplicable mechanism with its reason from a satisfied obligation with its evidence",
        "Until that caller is wired and independently witnessed, report it as prepared or unwired component evidence",
    )),
    ("performance", (
        "Before implementing a consequential data or proof path",
        "Label estimates as estimates",
        "Routine low-impact edits need no separate benchmark or artifact",
        "Measure the actual terminal path and these costs before claiming benefit",
        "Keep live authorization, cancellation, retirement, and final transactional compare-and-set separate",
    )),
    ("test_harness", (
        "interpreter and module globals, effective environment, resource root, dependency context, and public call",
        "A parser/AST check or command availability alone cannot prove that path",
        "source-safe smoke that reaches the real loader or dependency with effects disabled",
    )),
))
def test_action_critical_predicates_and_preserved_cases_remain_normative(section_id, predicates):
    body = compiler.parse_source(ROOT / "WISDOM.md").section_by_id[section_id].body.decode("utf-8")
    normalized = re.sub(r"\s+", " ", body)
    for predicate in predicates:
        assert predicate in normalized


def test_normal_module_driver_reaches_real_loader_from_isolated_context(tmp_path):
    loader = ROOT / "scripts" / "load_compiled_wisdom.py"
    source = ROOT / "WISDOM.md"
    driver = """import runpy, sys
loader, source = sys.argv[1:]
sys.argv = [loader, '--source', source, '--discover']
runpy.run_path(loader, run_name='__main__')
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", driver, str(loader), str(source)],
        cwd=tmp_path, capture_output=True, text=True, timeout=10,
    )
    assert completed.returncode == 0, completed.stderr
    receipt = json.loads(completed.stdout)
    assert receipt["status"] == "discovery"
    assert receipt["authority"] is False
    assert receipt["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert receipt["semantic_revision"] == 21
    assert list(tmp_path.iterdir()) == []


def test_ast_green_loader_with_missing_module_globals_fails_before_discovery(tmp_path):
    loader = ROOT / "scripts" / "load_compiled_wisdom.py"
    driver = """import ast, pathlib, sys
source = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')
ast.parse(source)
exec(compile(source, sys.argv[1], 'exec'), {})
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", driver, str(loader)],
        cwd=tmp_path, capture_output=True, text=True, timeout=10,
    )
    assert completed.returncode != 0
    assert "NameError" in completed.stderr and "__file__" in completed.stderr
    assert completed.stdout == ""
    assert list(tmp_path.iterdir()) == []
