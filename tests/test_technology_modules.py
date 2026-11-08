"""Verify conditional instruction delivery, not empirical model improvement."""

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
import load_compiled_wisdom as loader  # noqa: E402
import report_technology_modules as report  # noqa: E402


SOURCE = ROOT / "WISDOM.md"


@pytest.fixture(scope="module")
def parsed():
    return compiler.parse_source(SOURCE)


def test_library_is_large_but_not_a_baseline_or_phase_dependency(parsed):
    technologies = set(report.technology_module_ids(parsed))
    assert len(technologies) == 79
    assert sum(len(parsed.section_by_id[sid].rule_ids)
               for mid in technologies for sid in parsed.module_by_id[mid]["sections"]) == 362
    assert parsed.manifest["semantic_revision"] == 23
    assert len(parsed.manifest["modules"]) == 105
    assert len(parsed.manifest["allowed_tags"]) == 119
    for mode in ("fast", "focused", "substantial"):
        assert not technologies.intersection(compiler.resolve_module_ids(parsed, mode=mode))
    for phase in parsed.phase_by_id.values():
        assert not technologies.intersection(
            compiler.resolve_module_ids(parsed, mode="focused", tags=phase["tags"]))
    # The new shell guidance must not overload the incumbent shell mechanism tag.
    assert "shell_practices" not in compiler.resolve_module_ids(parsed, mode="fast", tags=["shell"])
    assert len(parsed.kernel) < 34_000 < parsed.manifest["kernel_max_bytes"]


@pytest.mark.parametrize("tag,expected", (
    ("python", {"technology_preferences", "python"}),
    ("python_asyncio", {"technology_preferences", "python", "python_asyncio"}),
    ("rust_tokio", {"technology_preferences", "rust", "rust_tokio"}),
    ("go_concurrency", {"technology_preferences", "go", "go_concurrency"}),
    ("java_testing", {"technology_preferences", "java", "java_testing"}),
    ("cpp_concurrency", {"technology_preferences", "cpp", "cpp_concurrency"}),
    ("rails_jobs", {"technology_preferences", "ruby", "rails", "rails_jobs"}),
    ("react", {"technology_preferences", "javascript", "web_ui", "react"}),
    ("react_effects", {"technology_preferences", "javascript", "web_ui", "react", "react_effects"}),
    ("nextjs", {"technology_preferences", "javascript", "web_ui", "react", "nextjs"}),
    ("postgres", {"architecture_authority", "storage_design", "technology_preferences", "sql_relational", "postgres"}),
    ("clickhouse", {"architecture_authority", "storage_design", "technology_preferences", "columnar", "clickhouse"}),
    ("wide_column", {"architecture_authority", "storage_design", "technology_preferences", "wide_column"}),
    ("kafka", {"technology_preferences", "distributed_jobs", "kafka"}),
    ("rust_api", {"technology_preferences", "rust", "rust_api"}),
    ("vite", {"technology_preferences", "javascript", "vite"}),
    ("node_testing", {"technology_preferences", "javascript", "node", "node_testing"}),
    ("aws", {"technology_preferences", "cloud_architecture", "cloud_identity", "aws"}),
    ("gcp", {"technology_preferences", "cloud_architecture", "cloud_identity", "gcp"}),
    ("azure", {"technology_preferences", "cloud_architecture", "cloud_identity", "azure"}),
    ("serverless", {"technology_preferences", "cloud_architecture", "serverless"}),
    ("docker_build", {"technology_preferences", "containers", "docker_build"}),
    ("kubernetes_security", {"technology_preferences", "kubernetes", "kubernetes_security"}),
    ("technology_verification", {"technology_preferences", "technology_verification"}),
    ("technology_continuity", {"technology_preferences", "technology_continuity"}),
))
def test_specific_tags_deliver_only_their_required_family(parsed, tag, expected):
    assert set(compiler.resolve_module_ids(parsed, mode="fast", tags=[tag])) == expected


def test_mixed_stack_is_union_and_keeps_unrelated_engines_out(parsed):
    tags = ["rails_jobs", "react_effects", "typescript", "postgres"]
    individual = set().union(*(
        set(compiler.resolve_module_ids(parsed, mode="fast", tags=[tag])) for tag in tags))
    combined = compiler.resolve_module_ids(parsed, mode="fast", tags=tags)
    assert set(combined) == individual
    assert len(combined) == len(set(combined))
    assert not {"rust", "python", "mysql", "clickhouse", "nextjs"}.intersection(combined)


def test_framework_neutral_profiles_do_not_choose_unrequested_tools(parsed):
    for profile, excluded in (
        ("python_service", {"fastapi", "django"}),
        ("java_service", {"spring"}),
        ("react_ui", {"typescript", "nextjs"}),
        ("nextjs_application", {"typescript"}),
        ("vite_ui", {"react", "typescript", "node", "nextjs"}),
        ("node_service", {"typescript", "vite", "react"}),
    ):
        mode, tags = compiler.resolve_task_profile(parsed, profile)
        selected = set(compiler.resolve_module_ids(parsed, mode=mode, tags=tags))
        assert "ai_codegen" in selected
        assert not selected.intersection(excluded)


def test_every_technology_tag_closes_preferences_and_exact_rule_inventory(parsed):
    for module_id in report.technology_module_ids(parsed):
        selected = compiler.resolve_module_ids(parsed, mode="fast", tags=[module_id])
        assert "technology_preferences" in selected
        assert module_id in selected
        module = parsed.module_by_id[module_id]
        assert module["tags"] == [module_id]
        for sid in module["sections"]:
            body = parsed.section_by_id[sid].body
            definitions = re.findall(rb"(?m)^\*\*`([A-Z][A-Z0-9]+-[0-9]{2})`", body)
            assert [x.decode() for x in definitions] == list(parsed.section_by_id[sid].rule_ids)
            assert b"Load when:" in body
            assert b"Engineering preferences:" in body
            assert b"Representative proof:" in body
            assert b"Primary references (baseline checked 2026-11-07" in body
            assert b"Apply the shared technology preference contract." not in body


def test_cloud_profiles_do_not_select_a_provider_or_orchestrator(parsed):
    mode, tags = compiler.resolve_task_profile(parsed, "cloud_design")
    selected = set(compiler.resolve_module_ids(parsed, mode=mode, tags=tags))
    assert {"cloud_architecture", "cloud_identity", "technology_verification"} <= selected
    assert not {"aws", "gcp", "azure", "kubernetes", "containers", "serverless"}.intersection(selected)


def test_all_technology_profiles_include_verification_and_recovery_is_conditional(parsed):
    technologies = set(report.technology_module_ids(parsed))
    for profile in parsed.manifest['task_profiles']:
        if technologies.intersection(profile['tags']):
            selected = compiler.resolve_module_ids(parsed, mode=profile['mode'], tags=profile['tags'])
            assert 'technology_verification' in selected
            assert ('technology_continuity' in selected) == (profile['id'] == 'technology_resume')


def test_context_rows_match_actual_verified_delivery(parsed, tmp_path):
    compiler.compile_and_install(SOURCE, tmp_path / "cache")
    rows = report.context_rows(parsed)
    assert len(rows) == len(parsed.view_by_mode) + len(parsed.manifest["task_profiles"])
    for row in rows:
        kind, name = str(row["route"]).split(":", 1)
        options = {"mode": name} if kind == "mode" else {"task_profile": name}
        plan = loader.load_plan(SOURCE, tmp_path / "cache", **options)
        emitted = loader.read_plan_content(plan)
        assert row["selected_bytes"] == len(emitted)
        assert row["selected_bytes"] == plan["selected_context"]["selected_total_bytes"]


def test_context_target_never_silently_omits_required_cloud_guidance(tmp_path):
    cache = tmp_path / "cache"
    compiler.compile_and_install(SOURCE, cache)
    ordinary = loader.load_plan(SOURCE, cache, mode="focused", tags=["aws", "rust_api"])
    bounded = loader.load_plan(
        SOURCE, cache, mode="focused", tags=["aws", "rust_api"],
        selected_context_target_bytes=1)
    assert bounded["selected_context"]["target_status"]["kind"] == "over_target"
    assert bounded["module_ids"] == ordinary["module_ids"]
    assert loader.read_plan_content(bounded) == loader.read_plan_content(ordinary)


@pytest.fixture(scope="module")
def extracted_library(tmp_path_factory):
    root = tmp_path_factory.mktemp("technology-portable")
    with zipfile.ZipFile(ROOT / "WISDOM.zip") as archive:
        archive.extractall(root)
    return root


@pytest.mark.parametrize("tags,required,forbidden", (
    (["python_asyncio", "python_testing"], [b"PYASYNC-04", b"PYTEST-04"], [b"TOKIO-01", b"REACT-01"]),
    (["rust_tokio"], [b"TOKIO-04", b"RUST-02"], [b"PYASYNC-01", b"JCON-01"]),
    (["react_effects", "web_accessibility"], [b"REFFECT-03", b"A11Y-02"], [b"NEXT-01", b"TS-01"]),
    (["clickhouse"], [b"CH-01", b"COL-01", b"DATA-01"], [b"PG-01", b"WCOL-01"]),
    (["vite"], [b"VITE-02", b"VITE-03", b"JS-01"], [b"NODE-01", b"REACT-01"]),
    (["aws", "docker_build"], [b"AWS-04", b"CLOUD-03", b"CID-01", b"DBUILD-02"], [b"GCP-01", b"AZ-01", b"KSEC-01"]),
))
def test_extracted_archive_cli_delivers_real_module_bytes(extracted_library, tmp_path, tags, required, forbidden):
    source = extracted_library / "WISDOM.md"
    command = [sys.executable, str(extracted_library / "scripts" / "load_compiled_wisdom.py"),
               "--source", str(source), "--cache-root", str(tmp_path / "cache"),
               "--prepare-cache", "--mode", "fast"]
    for tag in tags:
        command += ["--tag", tag]
    planned = subprocess.run(command, cwd=tmp_path, capture_output=True, check=True, timeout=30)
    plan = json.loads(planned.stdout)
    assert plan["status"] == "compiled"
    emitted = subprocess.run(command + ["--emit-content"], cwd=tmp_path,
                             capture_output=True, check=True, timeout=30).stdout
    assert all(rule in emitted for rule in required)
    assert all(rule not in emitted for rule in forbidden)
    current = compiler.parse_source(source)
    expected = current.kernel + b"".join(
        current.section_by_id[sid].body
        for mid in plan["module_ids"] for sid in current.module_by_id[mid]["sections"])
    assert emitted == expected
    assert hashlib.sha256(emitted).hexdigest() == plan["delivery"]["content_sha256"]


def test_selected_technology_cache_corruption_fails_closed(tmp_path):
    cache = tmp_path / "cache"
    compiler.compile_and_install(SOURCE, cache)
    plan = loader.load_plan(SOURCE, cache, mode="fast", tags=["react_effects"])
    target = next(Path(path) for path in plan["content_paths"] if Path(path).name == "react_effects.md")
    target.write_bytes(target.read_bytes().replace(b"REFFECT-03", b"REFFECT_03"))
    after = loader.load_plan(SOURCE, cache, mode="fast", tags=["react_effects"])
    assert after["status"] == "full_source_required"
    assert after["content_paths"] == [str(SOURCE)]


def test_report_is_current_and_source_edits_invalidate_it(tmp_path):
    assert (ROOT / "docs" / "TECHNOLOGY_MODULES.md").read_text(encoding="utf-8") == report.render_report(SOURCE)
    source = tmp_path / "WISDOM.md"
    source.write_bytes(SOURCE.read_bytes().replace(
        b"Prevent stale request wins", b"Prevent stale request results", 1))
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "report_technology_modules.py"),
         "--source", str(source), "--output", str(ROOT / "docs" / "TECHNOLOGY_MODULES.md"), "--check"],
        capture_output=True, timeout=30)
    assert result.returncode == 2
    assert b"technology report is stale" in result.stderr


def test_human_review_is_source_bound_and_covers_every_technology_rule(parsed):
    review = (ROOT / "docs" / "TECHNOLOGY_REVIEW.md").read_text(encoding="utf-8")
    assert f"Reviewed source SHA-256: `{parsed.source_sha256}`." in review
    rows = dict(re.findall(r"(?m)^\| `([a-z][a-z0-9_]*)` \| ([^\n]+) \|$", review))
    assert set(rows) == set(report.technology_module_ids(parsed))
    for module_id, row in rows.items():
        expected = tuple(
            rule_id for sid in parsed.module_by_id[module_id]["sections"]
            for rule_id in parsed.section_by_id[sid].rule_ids)
        assert tuple(re.findall(r"`([A-Z][A-Z0-9]+-[0-9]{2})`", row)) == expected


def test_reference_and_critical_preference_limits_are_explicit(parsed):
    root = parsed.section_by_id["technology_preferences"].body.decode()
    assert "explicit current user preferences first" in root
    assert "never silently raise the minimum runtime" in root
    assert "loader resolves explicit tags and dependencies" in parsed.preamble.decode()
    ai = " ".join(parsed.section_by_id["ai_codegen"].body.decode().split())
    assert "not a permanent capability rating" in ai
    assert "before claiming this module improves a named model" in ai
    postgres = " ".join(parsed.section_by_id["postgres"].body.decode().split())
    clickhouse = " ".join(parsed.section_by_id["clickhouse"].body.decode().split())
    assert "does not enforce row uniqueness" not in postgres
    assert "does not enforce row uniqueness" in clickhouse


# Independently retained v1.19.1 module definitions and exact section bytes.
# The implementation hash includes upstream's private-overlay isolation clarification.
INCUMBENT_MODULE_SHA256 = {
    'agency_ethics': 'a605532eeb54af97157e6d3714f028ed1b3be02e9f6ef5445c58fc8f0cfd4bf1',
    'bootstrap_contract': '99e3265aaff970806756f81dee6c5c4ea124aa6c6a568bf8523ccdfadaf3a9c4',
    'defect_diagnostics': '0f8e46bfc9e86c8ff16e265ec3337a9d79cb9537059c37dd8dbd31bd1e2d8f70',
    'architecture_authority': '1d4a42f0c7c8c0922eec5557176d38de78fafe86a9ac576bbea0eaec9b90675e',
    'storage_design': '4af4de997736f9d7945ca1e93aaba3599f4dc3e1e6d95dcff139e3239b206b0d',
    'protocol_identity': 'b1f47e98992d5e60ce07cdea73bc5dc86c4a20ea49a53dfe6d33ace89d6cbc66',
    'effect_harness': '4322e4a1d2e0257e15f97856843367c7a1cadd933df127984d13f07c7b945ab5',
    'authority_carriers': 'd2fceacfc30538ea4fe35c021b3f53163f0aa3ddd5edc08f93760af1e36fd7c8',
    'async_lifecycle': 'c2b1aa9cef07633d1588d09919988144378cdc822cc4b022b0fc9e89badb0ebd',
    'source_fence': '00696cb5d9448166798697f19d8108aa530de5bc4565867ef3ab4c32eeb8c88b',
    'testing': 'dcab1bc4051c9982f2058c5d674f145546f3177905d95b9322a981041c447e60',
    'test_harness': '64366c1903dfba244b60819f53bd0dc590c2c3be032fbffe1af1c03ef940c78b',
    'implementation_performance': '73f28f3829e971919e203756d2ea424f8f5769bdb7a3f1d95fd9f0a11413e3a1',
    'decision_judgment': 'e90b55a3012594065b0782cdcdc640d6b4b18171a1c5d1163ce2f226114cb000',
    'decision_budget': '5c5905f8aa341ab7fc8c6ec40537e53d2115a81d6ae5400bbf7cc5c3b5f65dbd',
    'execution_efficiency': '58944ff5cfc3f05081cc441e3e569917d375edb5087efd0b7c6d1a6707eee6ca',
    'delivery_status': 'd5f42ebe21ac6cb5de777cb6fcbe2f38e1360d870b4b7483e643be84143b25cd',
    'delegation_contract': 'dd89b53fc6fe097e366bc9a45e526c79d5d3333296bbaaafc0bed13c02c3357f',
    'context_delegation': 'e341bda0638d3e35cff64a1619a7b654d59a359e5035349adc2f335e5713f27b',
    'conditional_operations': '130347d00a37e55b40343ab1b41d220a26ae92e13933f9ba0416d659620f8fc6',
    'runtime_identity': '756b7ad18ca96c94f74ca4a5001c1634983f31dbde0017f8c839dea2cb0d7961',
    'correction_closure': 'a8e46d3b1f33af530a7c882682c39440f804767b684b4d4a5d076b1884304621',
    'lesson_dependency': 'fdd9b3a4bb990de922fa0852c9c95fdd2eab08eeb8aa5183c58a2fdad55ec7ae',
    'lesson_acceptance': 'f88d4ef31e13b184c8a4a9282e2bb29ab4aba8e118f2ffb8f3bb41c38a423cdf',
    'lesson_evidence_recovery': 'b119c7e7ec14c31dbb7267a9a0a4dd3dd485c89ddaa0bf860653c0703fc83e5f',
    'sources': '5e94faed54a0f46524037f88a9493703c93f442c3ae2eb939c899e75da73e3f5',
}


def test_incumbent_modules_remain_byte_exact(parsed):
    for module_id, expected in INCUMBENT_MODULE_SHA256.items():
        module = parsed.module_by_id[module_id]
        payload = compiler.canonical_json_bytes(module) + b"".join(
            parsed.section_by_id[sid].body for sid in module["sections"])
        assert hashlib.sha256(payload).hexdigest() == expected, module_id
