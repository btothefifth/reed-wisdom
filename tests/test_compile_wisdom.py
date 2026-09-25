from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import compile_wisdom as compiler  # noqa: E402
import load_compiled_wisdom as loader  # noqa: E402


SOURCE = REPO_ROOT / "WISDOM.md"
COMPILER_SCRIPT = SCRIPTS / "compile_wisdom.py"
LOADER_SCRIPT = SCRIPTS / "load_compiled_wisdom.py"


def _copy_source(tmp_path: Path) -> Path:
    destination = tmp_path / "WISDOM.md"
    destination.write_bytes(SOURCE.read_bytes())
    return destination


def _write_companion(tmp_path: Path) -> tuple[Path, bytes]:
    raw = b"<INSTRUCTIONS>\nSynthetic project companion.\n</INSTRUCTIONS>\n"
    destination = tmp_path / "PROJECT-RULES.md"
    destination.write_bytes(raw)
    return destination, raw


def _compile(tmp_path: Path, source: Path | None = None) -> tuple[Path, dict[str, Any]]:
    selected_source = source or SOURCE
    cache = tmp_path / "cache"
    receipt = dict(compiler.compile_and_install(selected_source, cache))
    return cache, receipt


def _assert_full_source_only(plan: dict[str, Any], source: Path) -> None:
    assert plan["status"] == "full_source_required"
    assert plan["authority"] is False
    assert plan["source_path"] == str(source.resolve())
    assert plan["content_paths"] == [str(source.resolve())]
    assert plan["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert plan["tool_hashes"] is None
    assert plan["build_id"] is None
    assert plan["tree_sha256"] is None


def _replace_once(path: Path, old: bytes, new: bytes) -> None:
    raw = path.read_bytes()
    assert raw.count(old) == 1
    path.write_bytes(raw.replace(old, new, 1))


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _independent_source_slices(
    source: Path,
) -> tuple[bytes, dict[str, Any], bytes, dict[str, bytes]]:
    raw = source.read_bytes()
    newline = b"\r\n" if b"\r\n" in raw else b"\n"
    begin_line = b"<!-- WISDOM-MANIFEST-BEGIN" + newline
    end_line = b"WISDOM-MANIFEST-END -->" + newline
    begin_at = raw.index(begin_line)
    manifest_at = begin_at + len(begin_line)
    end_at = raw.index(end_line, manifest_at)
    manifest = json.loads(raw[manifest_at:end_at].decode("utf-8"))
    starts: list[tuple[str, int]] = []
    search_at = end_at + len(end_line)
    for section in manifest["sections"]:
        marker = b"## " + section["heading"].encode("utf-8")
        start = raw.index(marker, search_at)
        assert start == 0 or raw[start - 1 : start] == b"\n"
        starts.append((section["id"], start))
        search_at = start + len(marker)
    slices = {
        section_id: raw[start : starts[index + 1][1] if index + 1 < len(starts) else len(raw)]
        for index, (section_id, start) in enumerate(starts)
    }
    return raw, manifest, raw[:begin_at], slices


def test_real_source_compiles_to_exact_materially_smaller_views(tmp_path: Path) -> None:
    original = SOURCE.read_bytes()
    cache, receipt = _compile(tmp_path)
    raw, manifest, preamble, slices = _independent_source_slices(SOURCE)
    build = cache / receipt["source_id"] / receipt["build_id"]

    assert SOURCE.read_bytes() == original
    assert receipt["authority"] is False
    assert receipt["kernel_bytes"] <= manifest["kernel_max_bytes"]
    assert receipt["kernel_bytes"] < receipt["source_bytes"] * 0.15
    expected_kernel = preamble + b"".join(
        slices[section_id]
        for section_id in manifest["kernel_sections"]
        if section_id != "preamble"
    )
    assert (build / "kernel.md").read_bytes() == expected_kernel
    assert b"load_compiled_wisdom.py --discover" in expected_kernel
    assert receipt["source_bytes"] == len(raw)
    installed_manifest = json.loads(
        (build / "manifest.json").read_text(encoding="utf-8")
    )
    identity = installed_manifest["body"]["identity"]
    assert identity["tree_sha256"] == receipt["tree_sha256"]
    assert hashlib.sha256(_canonical(identity)).hexdigest() == receipt["build_id"]
    for module in manifest["modules"]:
        expected = b"".join(
            slices[section_id] for section_id in module["sections"]
        )
        assert (build / "modules" / f"{module['id']}.md").read_bytes() == expected


def test_compilation_is_deterministic_across_cache_roots(tmp_path: Path) -> None:
    first_cache, first = _compile(tmp_path / "first")
    second_cache, second = _compile(tmp_path / "second")
    parsed = compiler.parse_source(SOURCE)

    assert first["build_id"] == second["build_id"]
    assert first["tree_sha256"] == second["tree_sha256"]
    first_root = first_cache / parsed.manifest["source_id"]
    second_root = second_cache / parsed.manifest["source_id"]
    assert (first_root / "CURRENT.json").read_bytes() == (second_root / "CURRENT.json").read_bytes()
    for relative_path in sorted(
        path.relative_to(first_root / first["build_id"])
        for path in (first_root / first["build_id"]).rglob("*")
        if path.is_file()
    ):
        assert (first_root / first["build_id"] / relative_path).read_bytes() == (
            second_root / second["build_id"] / relative_path
        ).read_bytes()


@pytest.mark.parametrize(
    ("mode", "tags", "expected"),
    [
        ("fast", [], []),
        ("fast", ["shell"], [
            "architecture_authority", "protocol_identity", "effect_harness",
            "authority_carriers", "async_lifecycle", "source_fence",
            "conditional_operations", "runtime_identity",
        ]),
        ("fast", ["implementation"], [
            "testing", "test_harness", "implementation_performance",
        ]),
        ("fast", ["recovery"], [
            "defect_diagnostics", "architecture_authority", "protocol_identity",
            "authority_carriers", "async_lifecycle", "execution_efficiency",
        ]),
    ],
)
def test_loader_selects_mode_and_dependency_closed_tags(
    tmp_path: Path,
    mode: str,
    tags: list[str],
    expected: list[str],
) -> None:
    cache, _ = _compile(tmp_path)
    plan = dict(loader.load_plan(SOURCE, cache, mode=mode, tags=tags))

    assert plan["status"] == "compiled"
    assert plan["authority"] is False
    assert plan["module_ids"] == expected
    assert Path(plan["content_paths"][0]).name == "kernel.md"
    assert [Path(path).stem for path in plan["content_paths"][1:]] == expected


@pytest.mark.parametrize("profile", ["routine", "code_change", "architecture", "operations", "research"])
def test_task_profile_matches_explicit_mode_and_tags(tmp_path: Path, profile: str) -> None:
    cache, _ = _compile(tmp_path)
    discovery = dict(loader.discover_capabilities(SOURCE))
    selected = next(item for item in discovery["task_profiles"] if item["id"] == profile)
    profile_plan = dict(loader.load_plan(SOURCE, cache, task_profile=profile))
    explicit_plan = dict(
        loader.load_plan(
            SOURCE,
            cache,
            mode=selected["mode"],
            tags=selected["tags"],
        )
    )

    assert profile_plan["status"] == explicit_plan["status"] == "compiled"
    assert profile_plan["module_ids"] == explicit_plan["module_ids"]
    assert profile_plan["content_receipts"] == explicit_plan["content_receipts"]
    assert profile_plan["task_profile"] == profile


def test_unknown_task_profile_falls_back_to_full_source(tmp_path: Path) -> None:
    cache, _ = _compile(tmp_path)
    plan = dict(loader.load_plan(SOURCE, cache, task_profile="unknown_profile"))

    assert plan["status"] == "full_source_required"
    assert plan["reason"] == "task_profile_unavailable:WisdomCompileError"
    assert plan["task_profile"] == "unknown_profile"
    assert loader.read_plan_content(plan) == SOURCE.read_bytes()


def test_explicit_mode_conflict_with_task_profile_falls_back_without_narrowing(
    tmp_path: Path,
) -> None:
    cache, _ = _compile(tmp_path)
    plan = dict(
        loader.load_plan(
            SOURCE,
            cache,
            mode="substantial",
            task_profile="routine",
        )
    )

    assert plan["status"] == "full_source_required"
    assert plan["reason"] == "task_profile_unavailable:WisdomCompileError"
    assert plan["task_profile"] == "routine"
    assert plan["mode"] == "substantial"
    assert loader.read_plan_content(plan) == SOURCE.read_bytes()


def test_focused_implementation_baseline_cannot_omit_build_and_test_mechanics(
    tmp_path: Path,
) -> None:
    cache, _ = _compile(tmp_path)

    plan = dict(loader.load_plan(SOURCE, cache, mode="focused"))

    assert plan["status"] == "compiled"
    assert plan["module_ids"] == ["testing", "test_harness", "implementation_performance"]


def test_substantial_migration_baseline_cannot_omit_bmad_or_operations(
    tmp_path: Path,
) -> None:
    cache, _ = _compile(tmp_path)

    plan = dict(loader.load_plan(SOURCE, cache, mode="substantial"))

    assert plan["status"] == "compiled"
    assert plan["module_ids"] == [
        "bootstrap_contract",
        "defect_diagnostics",
        "architecture_authority",
        "storage_design",
        "protocol_identity",
        "effect_harness",
        "authority_carriers",
        "async_lifecycle",
        "source_fence",
        "testing",
        "test_harness",
        "implementation_performance",
        "decision_judgment",
        "decision_budget",
        "execution_efficiency",
        "delivery_status",
        "context_delegation",
        "conditional_operations",
        "runtime_identity",
        "correction_closure",
    ]


def test_discovery_exposes_modes_tags_dependencies_and_unknown_fallback() -> None:
    discovery = dict(loader.discover_capabilities(SOURCE))

    assert discovery["schema"] == loader.DISCOVERY_SCHEMA
    assert discovery["status"] == "discovery"
    assert discovery["authority"] is False
    assert discovery["unknown_impact_action"] == "full_source_required"
    mode_by_name = {item["mode"]: item for item in discovery["modes"]}
    assert mode_by_name["focused"]["resolved_modules"] == [
        "testing",
        "test_harness",
        "implementation_performance",
    ]
    assert "conditional_operations" in mode_by_name["substantial"]["resolved_modules"]
    tag_by_name = {item["tag"]: item for item in discovery["tags"]}
    assert tag_by_name["routing"] == {
        "tag": "routing",
        "kernel_satisfied": True,
        "direct_modules": [],
        "resolved_modules": [],
    }
    assert tag_by_name["implementation"]["resolved_modules"] == [
        "testing",
        "test_harness",
        "implementation_performance",
    ]
    assert tag_by_name["recovery"]["resolved_modules"] == [
        "defect_diagnostics",
        "architecture_authority",
        "protocol_identity",
        "authority_carriers",
        "async_lifecycle",
        "execution_efficiency",
    ]
    assert tag_by_name["shell"]["resolved_modules"] == [
        "architecture_authority",
        "protocol_identity",
        "effect_harness",
        "authority_carriers",
        "async_lifecycle",
        "source_fence",
        "conditional_operations",
        "runtime_identity",
    ]
    profile_by_name = {item["id"]: item for item in discovery["task_profiles"]}
    assert profile_by_name["routine"]["resolved_modules"] == []
    assert profile_by_name["code_change"]["resolved_modules"] == [
        "testing",
        "test_harness",
        "implementation_performance",
    ]


def test_isolated_discovery_cli_emits_machine_readable_receipt(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(LOADER_SCRIPT),
            "--source",
            str(SOURCE),
            "--discover",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    receipt = json.loads(completed.stdout)
    assert receipt["schema"] == loader.DISCOVERY_SCHEMA
    assert receipt["status"] == "discovery"
    assert receipt["unknown_impact_action"] == "full_source_required"


def test_isolated_task_profile_cli_emits_verified_profile_plan(tmp_path: Path) -> None:
    cache, _ = _compile(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(LOADER_SCRIPT),
            "--source",
            str(SOURCE),
            "--cache-root",
            str(cache),
            "--task-profile",
            "code_change",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    receipt = json.loads(completed.stdout)
    assert receipt["status"] == "compiled"
    assert receipt["task_profile"] == "code_change"
    assert receipt["module_ids"] == [
        "testing", "test_harness", "implementation_performance",
    ]


def test_isolated_compiled_load_cli_uses_exact_sibling_import(tmp_path: Path) -> None:
    cache = tmp_path / "isolated-cache"
    compiled = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(COMPILER_SCRIPT),
            "--source",
            str(SOURCE),
            "--cache-root",
            str(cache),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert compiled.returncode == 0, compiled.stderr

    loaded = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(LOADER_SCRIPT),
            "--source",
            str(SOURCE),
            "--cache-root",
            str(cache),
            "--mode",
            "focused",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert loaded.returncode == 0, loaded.stderr
    receipt = json.loads(loaded.stdout)
    assert receipt["status"] == "compiled"
    assert receipt["module_ids"] == [
        "testing", "test_harness", "implementation_performance",
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_key",
        "extra_section",
        "missing_rule",
        "invalid_dependency",
        "interleaved_modules",
        "kernel_bound",
    ],
)
def test_compiler_rejects_invalid_source_contract(tmp_path: Path, mutation: str) -> None:
    source = _copy_source(tmp_path)
    newline = b"\r\n" if b"\r\n" in source.read_bytes() else b"\n"
    if mutation == "duplicate_key":
        old = b'  "schema": "wisdom.portable_bootstrap.source.v1",' + newline
        _replace_once(source, old, old + old)
    elif mutation == "extra_section":
        source.write_bytes(source.read_bytes() + newline + b"## Undeclared section" + newline)
    elif mutation == "missing_rule":
        _replace_once(source, b'"ROUTE-01", ', b"")
    elif mutation == "invalid_dependency":
        old = (
            b'      "requires": []' + newline
            + b"    }," + newline
            + b"    {" + newline
            + b'      "id": "bootstrap_contract"'
        )
        new = old.replace(b'"requires": []', b'"requires": ["missing_module"]')
        _replace_once(source, old, new)
    elif mutation == "interleaved_modules":
        _replace_once(
            source,
            b'"sections": ["bootstrap_acceptance", "qualify_substantial"]',
            b'"sections": ["bootstrap_acceptance", "break_recurrence"]',
        )
        _replace_once(
            source,
            b'"sections": ["break_recurrence", "defect_family", "diagnostics"]',
            b'"sections": ["qualify_substantial", "defect_family", "diagnostics"]',
        )
    else:
        _replace_once(source, b'  "kernel_max_bytes": 42000,', b'  "kernel_max_bytes": 1,')

    if mutation == "interleaved_modules":
        with pytest.raises(compiler.WisdomCompileError, match="noninterleaved"):
            compiler.parse_source(source)
    else:
        with pytest.raises(compiler.WisdomCompileError):
            compiler.parse_source(source)


def test_missing_pointer_requires_full_current_source(tmp_path: Path) -> None:
    plan = dict(loader.load_plan(SOURCE, tmp_path / "empty", mode="fast"))
    _assert_full_source_only(plan, SOURCE)


def test_stale_source_requires_full_current_source(tmp_path: Path) -> None:
    source = _copy_source(tmp_path)
    cache, _ = _compile(tmp_path, source)
    _replace_once(source, b"Last updated: 2026-09-25", b"Last updated: 2026-09-25 ")

    plan = dict(loader.load_plan(source, cache, mode="fast"))
    _assert_full_source_only(plan, source)


def test_corrupt_output_requires_full_current_source(tmp_path: Path) -> None:
    cache, receipt = _compile(tmp_path)
    parsed = compiler.parse_source(SOURCE)
    kernel = cache / parsed.manifest["source_id"] / receipt["build_id"] / "kernel.md"
    kernel.write_bytes(kernel.read_bytes() + b"corrupt")

    plan = dict(loader.load_plan(SOURCE, cache, mode="fast"))
    _assert_full_source_only(plan, SOURCE)


def test_content_read_returns_exact_selected_bytes_when_current(tmp_path: Path) -> None:
    cache, _ = _compile(tmp_path)
    plan = dict(loader.load_plan(SOURCE, cache, mode="fast", tags=["recovery"]))

    expected = b"".join(Path(path).read_bytes() for path in plan["content_paths"])

    assert plan["schema"] == loader.LOAD_PLAN_SCHEMA
    assert loader.read_plan_content(plan) == expected


def test_content_read_rejects_output_changed_after_plan(tmp_path: Path) -> None:
    cache, receipt = _compile(tmp_path)
    plan = dict(loader.load_plan(SOURCE, cache, mode="fast"))
    parsed = compiler.parse_source(SOURCE)
    kernel = cache / parsed.manifest["source_id"] / receipt["build_id"] / "kernel.md"
    kernel.write_bytes(kernel.read_bytes() + b"late-corruption")

    with pytest.raises(loader.WisdomCompileError):
        loader.read_plan_content(plan)


def test_content_read_rejects_source_changed_after_plan(tmp_path: Path) -> None:
    source = _copy_source(tmp_path)
    cache, _ = _compile(tmp_path, source)
    plan = dict(loader.load_plan(source, cache, mode="fast"))
    _replace_once(source, b"Last updated: 2026-09-25", b"Last updated: 2026-09-25 ")

    with pytest.raises(loader.WisdomCompileError, match="changed after load planning"):
        loader.read_plan_content(plan)


def test_content_read_falls_back_to_newly_current_source_after_plan_drift(
    tmp_path: Path,
) -> None:
    source = _copy_source(tmp_path)
    cache, _ = _compile(tmp_path, source)
    plan = dict(loader.load_plan(source, cache, mode="fast"))
    _replace_once(source, b"Last updated: 2026-09-25", b"Last updated: 2026-09-25 ")

    assert loader.read_plan_content_or_current_source(plan) == source.read_bytes()


def test_content_read_rejects_tool_changed_after_plan(tmp_path: Path) -> None:
    tool_root = tmp_path / "tools"
    tool_root.mkdir()
    copied_compiler = tool_root / COMPILER_SCRIPT.name
    copied_loader = tool_root / LOADER_SCRIPT.name
    copied_source = tool_root / SOURCE.name
    copied_compiler.write_bytes(COMPILER_SCRIPT.read_bytes())
    copied_loader.write_bytes(LOADER_SCRIPT.read_bytes())
    copied_source.write_bytes(SOURCE.read_bytes())
    loader_module_name = "_test_path_bound_wisdom_loader"
    compiler_module_name = (
        "_wisdom_compile_"
        + hashlib.sha256(str(copied_compiler).casefold().encode("utf-8")).hexdigest()[:16]
    )
    spec = importlib.util.spec_from_file_location(loader_module_name, copied_loader)
    assert spec is not None and spec.loader is not None
    copied_loader_module = importlib.util.module_from_spec(spec)
    sys.modules[loader_module_name] = copied_loader_module
    try:
        spec.loader.exec_module(copied_loader_module)
        cache = tmp_path / "cache"
        copied_loader_module._compiler.compile_and_install(copied_source, cache)
        plan = dict(
            copied_loader_module.load_plan(copied_source, cache, mode="fast")
        )
        copied_loader.write_bytes(copied_loader.read_bytes() + b"# changed after plan\n")

        with pytest.raises(
            copied_loader_module.WisdomCompileError,
            match="changed after load planning",
        ):
            copied_loader_module.read_plan_content(plan)
    finally:
        sys.modules.pop(loader_module_name, None)
        sys.modules.pop(compiler_module_name, None)


def test_rehashed_corrupt_output_still_requires_full_source(tmp_path: Path) -> None:
    cache, receipt = _compile(tmp_path)
    parsed = compiler.parse_source(SOURCE)
    source_root = cache / parsed.manifest["source_id"]
    build = source_root / receipt["build_id"]
    kernel = build / "kernel.md"
    kernel.write_bytes(kernel.read_bytes() + b"forged")

    manifest_path = build / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    body = manifest["body"]
    for output in body["outputs"]:
        if output["path"] == "kernel.md":
            output["bytes"] = kernel.stat().st_size
            output["sha256"] = hashlib.sha256(kernel.read_bytes()).hexdigest()
    body["tree_sha256"] = hashlib.sha256(_canonical(body["outputs"])).hexdigest()
    manifest["body_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    manifest_bytes = _canonical(manifest) + b"\n"
    manifest_path.write_bytes(manifest_bytes)

    current_path = source_root / "CURRENT.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current["body"]["tree_sha256"] = body["tree_sha256"]
    current["body"]["manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    current["body"]["manifest_body_sha256"] = manifest["body_sha256"]
    current["body_sha256"] = hashlib.sha256(_canonical(current["body"])).hexdigest()
    current_path.write_bytes(_canonical(current) + b"\n")

    plan = dict(loader.load_plan(SOURCE, cache, mode="fast"))
    _assert_full_source_only(plan, SOURCE)


@pytest.mark.parametrize(
    ("mode", "tags", "unknown_impact"),
    [
        ("full", [], False),
        ("fast", ["not_a_known_tag"], False),
        ("fast", [], True),
        ("not_a_mode", [], False),
    ],
)
def test_ambiguous_or_direct_requests_require_full_current_source(
    tmp_path: Path,
    mode: str,
    tags: list[str],
    unknown_impact: bool,
) -> None:
    cache, _ = _compile(tmp_path)
    plan = dict(
        loader.load_plan(
            SOURCE,
            cache,
            mode=mode,
            tags=tags,
            unknown_impact=unknown_impact,
        )
    )
    _assert_full_source_only(plan, SOURCE)


def test_atomic_current_advances_without_removing_prior_build(tmp_path: Path) -> None:
    source = _copy_source(tmp_path)
    cache, first = _compile(tmp_path, source)
    parsed_first = compiler.parse_source(source)
    source_root = cache / parsed_first.manifest["source_id"]
    first_current = (source_root / "CURRENT.json").read_bytes()
    old_revision = parsed_first.manifest["semantic_revision"]
    new_revision = old_revision + 1
    _replace_once(
        source,
        f'  "semantic_revision": {old_revision},'.encode("ascii"),
        f'  "semantic_revision": {new_revision},'.encode("ascii"),
    )

    second = dict(compiler.compile_and_install(source, cache))

    assert second["build_id"] != first["build_id"]
    assert (source_root / first["build_id"]).is_dir()
    assert (source_root / second["build_id"]).is_dir()
    assert (source_root / "CURRENT.json").read_bytes() != first_current
    plan = dict(loader.load_plan(source, cache, mode="fast"))
    assert plan["status"] == "compiled"
    assert plan["build_id"] == second["build_id"]


def test_portable_source_visibly_explains_reconstruction_and_fallback() -> None:
    text = SOURCE.read_text(encoding="utf-8")

    assert "sole authored portable authority" in text
    assert "scripts/compile_wisdom.py" in text
    assert "scripts/load_compiled_wisdom.py" in text
    assert "load_compiled_wisdom.py --discover" in text
    assert "read the full current" in text
    assert "Never substitute a stale kernel" in text
    assert "CPATH-01" in text
    assert "RESUME-01" in text


def test_operational_semantics_revision_13_preserves_bounded_loading_topology(
    tmp_path: Path,
) -> None:
    parsed = compiler.parse_source(SOURCE)

    assert parsed.manifest["semantic_revision"] == 13
    assert parsed.section_by_id["bounded_operating_loop"].rule_ids == (
        "LANG-01",
        "RULE-01",
    )
    assert parsed.section_by_id["metacognition"].rule_ids == ("FRAME-01",)
    assert "OPT-02" in parsed.section_by_id["process_cost"].rule_ids
    assert parsed.section_by_id["storage_design"].rule_ids == ("DATA-01",)
    assert parsed.section_by_id["protocol_identity"].rule_ids == (
        "PLANE-01", "UPGRADE-01", "DEP-01",
    )
    assert len(parsed.manifest["allowed_tags"]) == 37
    assert len(parsed.manifest["modules"]) == 22
    assert "bounded_operating_loop" in parsed.manifest["kernel_sections"]
    assert "metacognition" in parsed.module_by_id["decision_judgment"]["sections"]
    assert "process_cost" in parsed.module_by_id["decision_judgment"]["sections"]

    cache, receipt = _compile(tmp_path)
    assert receipt["kernel_bytes"] < 42_000

    fast_plan = dict(loader.load_plan(SOURCE, cache, mode="fast"))
    fast_content = loader.read_plan_content(fast_plan)
    assert b"LANG-01" in fast_content
    assert b"RULE-01" in fast_content
    assert b"actor and objective" in fast_content
    assert b"nearest negative contrast" in fast_content
    assert b"structurally different sibling" in fast_content
    assert b"action-relevant unknown or boundary" in fast_content
    assert b"independent oracle for each" in fast_content
    assert b"same canonical consumer" in fast_content
    assert b"deliberate predicate mutation goes red" in fast_content
    assert b"FRAME-01" not in fast_content
    assert b"DATA-01" not in fast_content
    assert b"PLANE-01" not in fast_content

    focused_plan = dict(loader.load_plan(SOURCE, cache, mode="focused"))
    focused_content = loader.read_plan_content(focused_plan)
    assert b"repository-owned nonmutating checks" in focused_content
    assert b"loaded source origin" in focused_content
    assert b"cache as a producer-carrier-consumer contract" in focused_content
    assert b"future_path_comparison" not in focused_content
    assert b"DATA-01" not in focused_content
    assert parsed.section_by_id["protocol_identity"].body not in focused_content

    storage_plan = dict(loader.load_plan(SOURCE, cache, mode="focused", tags=["storage"]))
    storage_content = loader.read_plan_content(storage_plan)
    assert b"DATA-01" in storage_content
    assert b"workloads and effective capabilities" in storage_content
    assert b"minimum supported hardware plus one growth step" in storage_content
    assert b"writer occupancy alongside foreground wait and terminal latency" in storage_content
    assert b"not invisible intermediate commits" in storage_content
    assert b"bounded dimensions, retention, and overhead" in storage_content

    substantial_plan = dict(loader.load_plan(SOURCE, cache, mode="substantial"))
    substantial_content = loader.read_plan_content(substantial_plan)
    assert b"LANG-01" in substantial_content
    assert b"RULE-01" in substantial_content
    assert b"FRAME-01" in substantial_content
    assert b"temporary-process retirement" in substantial_content
    assert b"pass_count: 1 | 2" in substantial_content
    assert b"stop_reason: decision_stable" in substantial_content
    assert b"independently existing completed carrier" in substantial_content
    assert b"evidenced by current carriers" in substantial_content
    assert b"actually shared exogenous inputs" in substantial_content
    assert b"endogenous per-lifecycle" in substantial_content
    assert b"current controlling authored contract" in substantial_content
    assert b"deployed behavior cannot override" in substantial_content
    assert b"future_path_comparison" in substantial_content
    assert b"Exclude sunk" in substantial_content
    assert b"authorized replacement proves" in substantial_content
    assert b"DATA-01" in substantial_content
    assert b"PLANE-01" in substantial_content
    assert b"ASYNC-01" in substantial_content
    assert b"FENCE-01" in substantial_content

    full_plan = dict(loader.load_plan(SOURCE, cache, mode="full"))
    _assert_full_source_only(full_plan, SOURCE)
    assert loader.read_plan_content(full_plan) == SOURCE.read_bytes()

def test_loader_appends_exact_bound_project_companion(tmp_path: Path) -> None:
    cache, _ = _compile(tmp_path)
    companion, detail = _write_companion(tmp_path)
    plan = dict(
        loader.load_plan(
            SOURCE,
            cache,
            mode="focused",
            companion_source_path=companion,
            expected_companion_sha256=hashlib.sha256(detail).hexdigest(),
            expected_companion_bytes=len(detail),
        )
    )

    assert plan["status"] == "compiled"
    assert plan["companion_source"] == {
        "path": str(companion.resolve()),
        "bytes": len(detail),
        "sha256": hashlib.sha256(detail).hexdigest(),
    }
    assert plan["content_paths"][-1] == str(companion.resolve())
    assert loader.read_plan_content(plan).endswith(detail)


@pytest.mark.parametrize("mutation", ["missing", "truncated"])
def test_loader_rejects_missing_or_truncated_project_companion(
    tmp_path: Path,
    mutation: str,
) -> None:
    detail, expected = _write_companion(tmp_path)
    if mutation == "missing":
        detail.unlink()
    else:
        detail.write_bytes(expected[:-1])

    with pytest.raises(loader.WisdomCompileError, match="companion source"):
        loader.load_plan(
            SOURCE,
            tmp_path / "cache",
            mode="focused",
            companion_source_path=detail,
            expected_companion_sha256=hashlib.sha256(expected).hexdigest(),
            expected_companion_bytes=len(expected),
        )


def test_loader_rejects_project_companion_changed_after_plan(tmp_path: Path) -> None:
    source = _copy_source(tmp_path)
    detail, expected = _write_companion(tmp_path)
    cache, _ = _compile(tmp_path, source)
    plan = dict(
        loader.load_plan(
            source,
            cache,
            mode="focused",
            companion_source_path=detail,
            expected_companion_sha256=hashlib.sha256(expected).hexdigest(),
            expected_companion_bytes=len(expected),
        )
    )
    detail.write_bytes(expected[:-1])

    with pytest.raises(loader.WisdomCompileError, match="companion source"):
        loader.read_plan_content_or_current_source(plan)


def test_loader_rejects_forged_plan_that_omits_bound_companion_content(
    tmp_path: Path,
) -> None:
    cache, _ = _compile(tmp_path)
    companion, detail = _write_companion(tmp_path)
    plan = dict(
        loader.load_plan(
            SOURCE,
            cache,
            mode="focused",
            companion_source_path=companion,
            expected_companion_sha256=hashlib.sha256(detail).hexdigest(),
            expected_companion_bytes=len(detail),
        )
    )
    plan["content_paths"] = list(plan["content_paths"][:-1])
    plan["content_receipts"] = list(plan["content_receipts"][:-1])
    plan["content_bytes"] -= len(detail)

    with pytest.raises(loader.WisdomCompileError, match="exact companion content join"):
        loader.read_plan_content(plan)
    assert loader.read_plan_content_or_current_source(plan).endswith(detail)


def test_full_source_fallback_retains_exact_project_companion(tmp_path: Path) -> None:
    companion, detail = _write_companion(tmp_path)
    plan = dict(
        loader.load_plan(
            SOURCE,
            tmp_path / "missing-cache",
            mode="focused",
            companion_source_path=companion,
            expected_companion_sha256=hashlib.sha256(detail).hexdigest(),
            expected_companion_bytes=len(detail),
        )
    )

    assert plan["status"] == "full_source_required"
    assert plan["content_paths"] == [
        str(SOURCE.resolve()),
        str(companion.resolve()),
    ]
    assert loader.read_plan_content(plan) == SOURCE.read_bytes() + detail


def test_cli_explicitly_prepares_empty_cache_and_default_load_is_read_only(
    tmp_path: Path,
) -> None:
    read_only_cache = tmp_path / "read-only-cache"
    read_only = subprocess.run(
        [
            sys.executable,
            str(LOADER_SCRIPT),
            "--source",
            str(SOURCE),
            "--cache-root",
            str(read_only_cache),
            "--mode",
            "focused",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    read_only_plan = json.loads(read_only.stdout)
    assert read_only_plan["status"] == "full_source_required"
    assert not read_only_cache.exists()

    prepared_cache = tmp_path / "prepared-cache"
    prepared = subprocess.run(
        [
            sys.executable,
            str(LOADER_SCRIPT),
            "--source",
            str(SOURCE),
            "--cache-root",
            str(prepared_cache),
            "--prepare-cache",
            "--mode",
            "focused",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    prepared_plan = json.loads(prepared.stdout)
    assert prepared_plan["status"] == "compiled"
    assert prepared_plan["reason"] == "verified_current_cache"
    assert prepared_plan["delivery"]["segment_count"] >= 1
    assert (prepared_cache / "portable-wisdom" / "CURRENT.json").is_file()


def test_segmented_delivery_reassembles_one_exact_generation(tmp_path: Path) -> None:
    cache, _ = _compile(tmp_path)
    companion, detail = _write_companion(tmp_path)
    plan = dict(
        loader.load_plan(
            SOURCE,
            cache,
            mode="substantial",
            companion_source_path=companion,
            expected_companion_sha256=hashlib.sha256(detail).hexdigest(),
            expected_companion_bytes=len(detail),
        )
    )
    delivery = loader.segmented_delivery_plan(plan, segment_bytes=4096)

    assert delivery["schema"] == loader.DELIVERY_SCHEMA
    assert delivery["segment_count"] == len(delivery["segments"])
    assert [item["index"] for item in delivery["segments"]] == list(
        range(delivery["segment_count"])
    )
    assembled = b"".join(
        loader.read_delivery_segment(
            plan,
            item["index"],
            expected_delivery_id=delivery["delivery_id"],
            segment_bytes=4096,
        )
        for item in delivery["segments"]
    )
    expected = loader.read_plan_content(plan)
    assert assembled == expected
    assert hashlib.sha256(assembled).hexdigest() == delivery["content_sha256"]
    assert len(assembled) == delivery["content_bytes"]


def test_segmented_delivery_rejects_mixed_generation_and_invalid_index(
    tmp_path: Path,
) -> None:
    cache, _ = _compile(tmp_path)
    plan = dict(loader.load_plan(SOURCE, cache, mode="focused"))
    delivery = loader.segmented_delivery_plan(plan, segment_bytes=4096)

    with pytest.raises(loader.WisdomCompileError, match="does not match"):
        loader.read_delivery_segment(
            plan,
            0,
            expected_delivery_id="0" * 64,
            segment_bytes=4096,
        )
    with pytest.raises(loader.WisdomCompileError, match="out of range"):
        loader.read_delivery_segment(
            plan,
            delivery["segment_count"],
            expected_delivery_id=delivery["delivery_id"],
            segment_bytes=4096,
        )


def test_cli_emits_one_generation_bound_segment(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    planned = subprocess.run(
        [
            sys.executable,
            str(LOADER_SCRIPT),
            "--source",
            str(SOURCE),
            "--cache-root",
            str(cache),
            "--prepare-cache",
            "--mode",
            "focused",
            "--segment-bytes",
            "4096",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    plan = json.loads(planned.stdout)
    delivery = plan["delivery"]
    emitted = subprocess.run(
        [
            sys.executable,
            str(LOADER_SCRIPT),
            "--source",
            str(SOURCE),
            "--cache-root",
            str(cache),
            "--mode",
            "focused",
            "--segment-bytes",
            "4096",
            "--emit-content-segment",
            "0",
            "--expected-delivery-id",
            delivery["delivery_id"],
        ],
        check=True,
        capture_output=True,
    )
    first = delivery["segments"][0]
    assert len(emitted.stdout) == first["bytes"]
    assert hashlib.sha256(emitted.stdout).hexdigest() == first["sha256"]


def test_selected_context_counts_companion_and_preserves_oversized_mandatory_rule(
    tmp_path: Path,
) -> None:
    source = _copy_source(tmp_path)
    raw, manifest, _, slices = _independent_source_slices(source)
    focused = next(view for view in manifest["views"] if view["mode"] == "focused")
    mandatory_module = next(
        module for module in manifest["modules"]
        if module["id"] == focused["required_modules"][0]
    )
    section_body = slices[mandatory_module["sections"][0]]
    oversized_marker = b"OVERSIZED_MANDATORY_RULE_BODY " + b"x" * 50_000
    assert raw.count(section_body) == 1
    source.write_bytes(raw.replace(section_body, section_body + oversized_marker + b"\n", 1))
    cache, _ = _compile(tmp_path, source)
    companion, companion_raw = _write_companion(tmp_path)
    target = 100
    plan = loader.load_plan(
        source,
        cache,
        mode="focused",
        companion_source_path=companion,
        expected_companion_bytes=len(companion_raw),
        expected_companion_sha256=hashlib.sha256(companion_raw).hexdigest(),
        selected_context_target_bytes=target,
    )
    content = loader.read_plan_content(plan)
    context = plan["selected_context"]
    assert oversized_marker in content
    assert content.endswith(companion_raw)
    assert context["source_bytes"] == len(source.read_bytes())
    assert context["kernel_bytes"] == plan["content_receipts"][0]["bytes"]
    assert context["module_bytes"] == sum(
        item["bytes"] for item in plan["content_receipts"][1:-1]
    )
    assert context["companion_bytes"] == len(companion_raw)
    assert context["wisdom_selected_bytes"] + len(companion_raw) == len(content)
    assert context["selected_total_bytes"] == plan["content_bytes"] == len(content)
    assert context["target_status"] == {
        "kind": "over_target",
        "excess_bytes": len(content) - target,
    }


def test_unknown_phase_keeps_full_source_and_accounts_for_target(tmp_path: Path) -> None:
    cache, _ = _compile(tmp_path)
    companion, companion_raw = _write_companion(tmp_path)
    plan = loader.load_plan(
        SOURCE,
        cache,
        task_profile="routine",
        phase="unrecognized_phase",
        companion_source_path=companion,
        expected_companion_bytes=len(companion_raw),
        expected_companion_sha256=hashlib.sha256(companion_raw).hexdigest(),
        selected_context_target_bytes=1,
    )
    assert plan["status"] == "full_source_required"
    assert plan["reason"] == "phase_unavailable:WisdomCompileError"
    assert loader.read_plan_content(plan) == SOURCE.read_bytes() + companion_raw
    context = plan["selected_context"]
    assert context["phase"] == "unrecognized_phase"
    assert context["source_bytes"] == context["wisdom_selected_bytes"] == len(SOURCE.read_bytes())
    assert context["kernel_bytes"] == context["module_bytes"] == 0
    assert context["companion_bytes"] == len(companion_raw)
    assert context["target_status"]["kind"] == "over_target"


def test_older_manifest_without_phases_keeps_legacy_route(tmp_path: Path) -> None:
    source = _copy_source(tmp_path)
    raw = source.read_bytes()
    newline = b"\r\n" if b"\r\n" in raw else b"\n"
    manifest_start = raw.index(b"<!-- WISDOM-MANIFEST-BEGIN" + newline) + len(
        b"<!-- WISDOM-MANIFEST-BEGIN" + newline
    )
    manifest_end = raw.index(b"WISDOM-MANIFEST-END -->" + newline, manifest_start)
    manifest = json.loads(raw[manifest_start:manifest_end].decode("utf-8"))
    assert manifest.pop("phases")
    source.write_bytes(
        raw[:manifest_start] + _canonical(manifest) + newline + raw[manifest_end:]
    )
    cache, _ = _compile(tmp_path, source)
    legacy = loader.load_plan(source, cache, task_profile="routine")
    assert legacy["status"] == "compiled"
    assert legacy["phase"] is None
    assert loader.read_plan_content(legacy)
    phase_plan = loader.load_plan(source, cache, task_profile="routine", phase="validate")
    assert phase_plan["status"] == "full_source_required"
    assert loader.read_plan_content(phase_plan) == source.read_bytes()


def test_profile_declaring_full_mode_never_routes_to_compiled_kernel(tmp_path: Path) -> None:
    source = _copy_source(tmp_path)
    raw = source.read_bytes()
    newline = b"\r\n" if b"\r\n" in raw else b"\n"
    manifest_start = raw.index(b"<!-- WISDOM-MANIFEST-BEGIN" + newline) + len(
        b"<!-- WISDOM-MANIFEST-BEGIN" + newline
    )
    manifest_end = raw.index(b"WISDOM-MANIFEST-END -->" + newline, manifest_start)
    manifest = json.loads(raw[manifest_start:manifest_end].decode("utf-8"))
    routine = next(item for item in manifest["task_profiles"] if item["id"] == "routine")
    routine["mode"] = "full"
    source.write_bytes(
        raw[:manifest_start] + _canonical(manifest) + newline + raw[manifest_end:]
    )
    cache, _ = _compile(tmp_path, source)
    plan = loader.load_plan(source, cache, task_profile="routine")
    assert plan["status"] == "full_source_required"
    assert plan["reason"] == "full_task_profile"
    assert loader.read_plan_content(plan) == source.read_bytes()


def test_phase_transition_requires_fresh_route_and_keeps_exact_source_bytes(
    tmp_path: Path,
) -> None:
    cache, _ = _compile(tmp_path)
    discovery = loader.discover_capabilities(SOURCE)
    phases = {item["id"]: item for item in discovery["phases"]}
    assert set(phases) == {"design", "implement", "validate", "release", "observe"}
    plans = {
        phase: loader.load_plan(SOURCE, cache, task_profile="routine", phase=phase)
        for phase in ("design", "validate", "release")
    }
    for phase, plan in plans.items():
        assert plan["status"] == "compiled"
        assert plan["phase"] == plan["selected_context"]["phase"] == phase
        assert plan["module_ids"] == phases[phase]["resolved_modules"]
        assert loader.read_plan_content(plan) == b"".join(
            Path(path).read_bytes() for path in plan["content_paths"]
        )
    assert b"FRAME-01" in loader.read_plan_content(plans["design"])
    assert b"FRAME-01" not in loader.read_plan_content(plans["validate"])
    assert "test_harness" in plans["validate"]["module_ids"]
    assert "delivery_status" in plans["release"]["module_ids"]
    assert plans["design"]["content_paths"] != plans["validate"]["content_paths"]


def test_selected_context_receipt_rejects_false_target_status(tmp_path: Path) -> None:
    cache, _ = _compile(tmp_path)
    plan = dict(loader.load_plan(SOURCE, cache, mode="fast"))
    context = dict(plan["selected_context"])
    context["target_status"] = {"kind": "within_target", "excess_bytes": 0}
    plan["selected_context"] = context
    with pytest.raises(loader.WisdomCompileError, match="target status"):
        loader.read_plan_content(plan)


def test_compiled_plan_cannot_relabel_old_phase_or_drop_routed_module(
    tmp_path: Path,
) -> None:
    cache, _ = _compile(tmp_path)
    plan = dict(loader.load_plan(SOURCE, cache, task_profile="routine", phase="design"))
    mislabeled = dict(plan)
    mislabeled["phase"] = "release"
    mislabeled_context = dict(plan["selected_context"])
    mislabeled_context["phase"] = "release"
    mislabeled["selected_context"] = mislabeled_context
    with pytest.raises(loader.WisdomCompileError, match="phase route"):
        loader.read_plan_content(mislabeled)

    omitted = dict(plan)
    omitted["content_paths"] = list(plan["content_paths"][:-1])
    omitted["content_receipts"] = list(plan["content_receipts"][:-1])
    omitted["content_bytes"] -= plan["content_receipts"][-1]["bytes"]
    with pytest.raises(loader.WisdomCompileError, match="content path route"):
        loader.read_plan_content(omitted)


def test_reader_rejects_rehashed_cache_and_plan_that_omit_source_rule(
    tmp_path: Path,
) -> None:
    cache, _ = _compile(tmp_path)
    plan = dict(loader.load_plan(SOURCE, cache, mode="substantial"))
    build = Path(plan["content_paths"][0]).parent
    module = build / "modules" / "protocol_identity.md"
    original = module.read_bytes()
    assert b"DEP-01" in original
    forged = original.replace(b"DEP-01", b"DEP_01")
    assert forged != original
    module.write_bytes(forged)

    manifest_path = build / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    body = manifest["body"]
    output = next(
        item for item in body["outputs"]
        if item["path"] == "modules/protocol_identity.md"
    )
    output["bytes"] = len(forged)
    output["sha256"] = hashlib.sha256(forged).hexdigest()
    body["tree_sha256"] = hashlib.sha256(_canonical(body["outputs"])).hexdigest()
    manifest["body_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    manifest_bytes = _canonical(manifest) + b"\n"
    manifest_path.write_bytes(manifest_bytes)

    current_path = build.parent / "CURRENT.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current["body"]["tree_sha256"] = body["tree_sha256"]
    current["body"]["manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    current["body"]["manifest_body_sha256"] = manifest["body_sha256"]
    current["body_sha256"] = hashlib.sha256(_canonical(current["body"])).hexdigest()
    current_path.write_bytes(_canonical(current) + b"\n")

    receipts = [dict(item) for item in plan["content_receipts"]]
    forged_receipt = next(item for item in receipts if item["path"] == str(module))
    forged_receipt["bytes"] = len(forged)
    forged_receipt["sha256"] = hashlib.sha256(forged).hexdigest()
    plan["content_receipts"] = receipts
    plan["tree_sha256"] = body["tree_sha256"]
    with pytest.raises(loader.WisdomCompileError, match="current source build"):
        loader.read_plan_content(plan)
