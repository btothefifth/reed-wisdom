"""Verify canonical rule delivery and release consistency, not agent behavior."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import compile_wisdom as compiler  # noqa: E402


# Expected owners/routes are independent of the manifest under test. A moved,
# duplicated, or unselected rule must fail even if compilation remains valid.
RULE_OWNERS = (
    (b"Keep the existing owner/dependency map usable for change review", "recursive_contract", "architecture"),
    (b"Apply these architecture acceptance conditions in design and code review", "recursive_contract", "architecture"),
    (b"Before expanding a variant family, `SEM-01` implementation review must check", "implementation", "implementation"),
    (b"While writing code, implementation must consider known reuse", "implementation", "implementation"),
    (b"After writing code, the implementer must inspect affected code and real callers", "implementation", "implementation"),
    (b"The reviewer must challenge stale copies, actual caller adoption and required", "implementation", "implementation"),
    (b"Before adding a persistent shape for another fixture", "storage_design", "storage"),
    (b"An advertised current test mode must be executable", "test_harness", "testing"),
    (b"Current-source compatibility tests may consume historical fixtures", "test_harness", "testing"),
    (b"Committed generated artifacts must have one canonical authored input set", "delivery_status", "delivery"),
)


@pytest.mark.parametrize("marker,section_id,route", RULE_OWNERS)
def test_acceptance_rules_have_one_canonical_owner_and_existing_route(marker, section_id, route):
    parsed = compiler.parse_source(ROOT / "WISDOM.md")
    assert marker not in parsed.kernel
    assert [section.section_id for section in parsed.sections if marker in section.body] == [section_id]
    selected = compiler.resolve_module_ids(parsed, mode="focused", tags=[route])
    assert any(section_id in parsed.module_by_id[module_id]["sections"] for module_id in selected)


def test_current_release_version_is_consistent_without_freezing_old_rule_tests():
    version = (ROOT / "VERSION").read_text(encoding="ascii").strip()
    assert re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version)
    parsed = compiler.parse_source(ROOT / "WISDOM.md")
    assert f"Product version: {version}".encode("ascii") in parsed.preamble
    assert f"## {version} - " in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"/releases/download/v{version}/reed-wisdom.zip" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"vendor/wisdom/v{version}/" in (ROOT / "docs/wisdom-portable/EXAMPLE_PROJECT_BOOTSTRAP.md").read_text(encoding="utf-8")


def test_extracted_release_delivers_rules_through_real_loader(tmp_path):
    extracted = tmp_path / "extracted"
    with zipfile.ZipFile(ROOT / "WISDOM.zip") as archive:
        archive.extractall(extracted)
    source = extracted / "WISDOM.md"
    loader = extracted / "scripts/load_compiled_wisdom.py"
    cache = tmp_path / "cache"
    # Exercise the shipped entrypoint and tool/source provenance in a fresh
    # isolated working directory, not just compiler helper calls in this repo.
    subprocess.run(
        [sys.executable, "-I", "-B", str(loader), "--source", str(source),
         "--cache-root", str(cache), "--prepare-cache", "--mode", "fast"],
        check=True, capture_output=True, text=True, timeout=20, cwd=tmp_path,
    )
    for marker, section_id, route in RULE_OWNERS:
        loaded = subprocess.run(
            [sys.executable, "-I", "-B", str(loader), "--source", str(source),
             "--cache-root", str(cache), "--mode", "focused", "--tag", route],
            check=True, capture_output=True, text=True, timeout=20, cwd=tmp_path,
        )
        plan = json.loads(loaded.stdout)
        assert plan["status"] == "compiled"
        assert plan["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
        content = b"".join(Path(path).read_bytes() for path in plan["content_paths"])
        assert marker in content, (section_id, route)
        assert hashlib.sha256(content).hexdigest() == plan["delivery"]["content_sha256"]
    assert not list(extracted.rglob("__pycache__"))
    assert not list(extracted.rglob("*.pyc"))
