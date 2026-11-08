"""Exercise real routing recovery and bounded discovery, not model-memory claims."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import compile_wisdom as compiler
import inspect_wisdom_stack as inspector
import load_compiled_wisdom as loader

SOURCE = ROOT / 'WISDOM.md'


def test_discovery_cli_exposes_current_authored_applicability_without_selecting_it(tmp_path):
    source = tmp_path / 'WISDOM.md'
    original = SOURCE.read_bytes()
    old = b'Changes affect Python source, public types, package layout, or packaging.'
    current = b'Changes affect Python source or the independently selected packaging owner.'
    assert original.count(old) == 1
    source.write_bytes(original.replace(old, current))
    result = json.loads(subprocess.run([
        sys.executable, str(ROOT / 'scripts/load_compiled_wisdom.py'),
        '--source', str(source), '--discover'], check=True,
        capture_output=True, timeout=10).stdout)
    assert result['source_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    modules = {row['id']: row for row in result['modules']}
    assert modules['python']['routing_hints'] == [{
        'section_id': 'python', 'heading': 'Python design and packaging',
        'load_when': current.decode(),
        'engineering_preferences': 'Package manager, formatter, type checker, supported Python versions, and class-versus-function conventions.'}]
    profiles = {row['id']: row for row in result['task_profiles']}
    assert 'python' not in profiles['routine']['resolved_modules']
    assert 'rust' not in profiles['python_service']['resolved_modules']
    assert not (tmp_path / 'cache').exists()


@pytest.mark.parametrize('arguments', [['--discover'], ['--mode', 'fast']])
def test_loader_read_only_cli_preserves_its_tool_frontier(tmp_path, arguments):
    tools = tmp_path / 'tools'
    tools.mkdir()
    for name in ('load_compiled_wisdom.py', 'compile_wisdom.py'):
        shutil.copyfile(ROOT / 'scripts' / name, tools / name)
    source = tmp_path / 'WISDOM.md'
    source.write_bytes(SOURCE.read_bytes())

    def frontier():
        return {path.relative_to(tmp_path).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in tmp_path.rglob('*') if path.is_file()}

    before = frontier()
    result = subprocess.run([
        sys.executable, '-I', str(tools / 'load_compiled_wisdom.py'),
        '--source', str(source), '--cache-root', str(tmp_path / 'absent-cache'),
        *arguments], check=True, capture_output=True, timeout=10, cwd=tmp_path)
    assert json.loads(result.stdout)['status'] in {'discovery', 'full_source_required'}
    assert frontier() == before
    assert not (tools / '__pycache__').exists()
    assert not (tmp_path / 'absent-cache').exists()


def test_inspector_cli_preserves_project_and_tool_files_in_a_fresh_process(tmp_path):
    tools = tmp_path / 'tools'
    tools.mkdir()
    for name in ('inspect_wisdom_stack.py', 'compile_wisdom.py'):
        shutil.copyfile(ROOT / 'scripts' / name, tools / name)
    project = tmp_path / 'project'
    project.mkdir()
    (project / 'app.py').write_text('import asyncio\n')

    def frontier():
        return {path.relative_to(tmp_path).as_posix(): path.read_bytes()
                for path in tmp_path.rglob('*') if path.is_file()}

    before = frontier()
    result = subprocess.run([sys.executable, str(tools / 'inspect_wisdom_stack.py'),
                             '--source', str(SOURCE), '--project-root', str(project)],
                            check=True, capture_output=True, timeout=10, cwd=project)
    assert 'python_asyncio' in json.loads(result.stdout)['candidate_tags']
    assert frontier() == before
    assert not (tools / '__pycache__').exists()


def test_stack_versions_keep_scope_constraints_and_conflicts_without_execution(tmp_path):
    (tmp_path / '.node-version').write_text('22\n')
    web = tmp_path / 'web'
    web.mkdir()
    (web / 'package.json').write_text(json.dumps({
        'engines': {'node': '>=24'},
        'dependencies': {'react': '^19.2.0'},
        'devDependencies': {'@testing-library/react': '^16', '@playwright/test': '^1.56'},
        'scripts': {'preinstall': 'touch MUST_NOT_EXIST'},
    }))
    (web / 'main.tsx').write_text('export const value = 1;')
    sibling = tmp_path / 'unrelated'
    sibling.mkdir()
    (sibling / '.node-version').write_text('26')
    result = inspector.inspect_project(SOURCE, tmp_path, ['web/main.tsx'])
    assert {'react', 'react_testing', 'web_testing', 'node', 'typescript'} <= set(result['candidate_tags'])
    assert result['version_interpretation'] == {
        'compatibility': 'not_evaluated', 'runtime': 'not_probed', 'lockfile_resolution': 'not_parsed'}
    node = [row for row in result['version_evidence'] if row['technology'] == 'node']
    assert {(row['path'], row['value'], row['kind']) for row in node} == {
        ('.node-version', '22', 'toolchain_selector'),
        ('web/package.json', '>=24', 'declared_constraint')}
    assert all(row['path'] in {item['path'] for item in result['evidence_files']}
               for row in result['version_evidence'])
    assert any(row['field'] == '/devDependencies/@testing-library~1react'
               for row in result['version_evidence'])
    assert not (tmp_path / 'MUST_NOT_EXIST').exists()


def test_stack_versions_cover_python_cargo_workspace_and_go_without_resolving_them(tmp_path):
    (tmp_path / 'pyproject.toml').write_text('''[project]
requires-python = ">=3.12,<3.15"
dependencies = ["fastapi>=0.115"]
[project.optional-dependencies]
test = ["pytest-asyncio>=1.2"]
''')
    (tmp_path / 'Cargo.toml').write_text('''[workspace]
members = ["member"]
[workspace.package]
rust-version = "1.85"
edition = "2024"
[workspace.dependencies]
rt = { package = "tokio", version = "1.48" }
''')
    member = tmp_path / 'member'
    member.mkdir()
    (member / 'Cargo.toml').write_text('''[package]
name = "member"
version = "0.1.0"
rust-version.workspace = true
edition.workspace = true
[target.'cfg(unix)'.dependencies]
tokio = "1.47"
''')
    (tmp_path / 'rust-toolchain.toml').write_text('[toolchain]\nchannel = "stable"\n')
    (tmp_path / 'go.mod').write_text('module example.org/test\ngo 1.25.0\ntoolchain go1.26.1\n')
    (tmp_path / 'work.go').write_text('package main\nfunc work() {}\nfunc main() { go work() }\n')
    result = inspector.inspect_project(SOURCE, tmp_path)
    assert result['status'] == 'bounded_scan_complete'
    assert {'python_asyncio', 'python_testing', 'fastapi', 'rust_tokio', 'go_concurrency'} <= set(result['candidate_tags'])
    rows = result['version_evidence']
    assert any(row['field'] == '/workspace/package/rust-version' and row['value'] == '1.85' for row in rows)
    assert any(row['kind'] == 'edition' and row['value'] == '2024' for row in rows)
    assert {row['value'] for row in rows if row['technology'] == 'rust_tokio'} == {'1.48', '1.47'}
    assert any(row['field'] == '/workspace/dependencies/rt/version' and row['value'] == '1.48' for row in rows)
    assert {row['value'] for row in rows if row['technology'] == 'go'} == {'1.25.0', 'go1.26.1'}
    assert not any(row['path'] == 'member/Cargo.toml' and row['technology'] == 'rust' for row in rows)
    scoped = inspector.inspect_project(SOURCE, tmp_path, ['member/Cargo.toml'])
    assert any(row['value'] == '1.85' for row in scoped['version_evidence'])
    # Root manifests remain advisory ancestor evidence; unrelated source stays out.
    assert 'go_concurrency' not in scoped['candidate_tags']
    assert 'work.go' not in {row['path'] for row in scoped['evidence_files']}


@pytest.mark.parametrize('filename,content', [
    ('package.json', '{"dependencies": {"react": 19}, "engines": {"node": []}}'),
    ('package.json', '[' * 1500 + '0' + ']' * 1500),
    ('pyproject.toml', '[project]\ndependencies = "pytest>=8"'),
    ('pyproject.toml', '[project]\noptional-dependencies = ["pytest"]'),
    ('Cargo.toml', '[package]\nrust-version = 85'),
    ('global.json', '{"sdk": []}'),
    ('.python-version', '\n'),
    ('package.json', '{"dependencies": {"unknown-library": 42}}'),
    ('pyproject.toml', '[dependency-groups]\ntest = [{invalid = "pytest"}]'),
])
def test_unusable_version_or_dependency_declarations_are_partial(tmp_path, filename, content):
    (tmp_path / filename).write_text(content)
    result = inspector.inspect_project(SOURCE, tmp_path)
    assert result['status'] == 'partial'
    assert result['issues']
    assert result['version_evidence'] == []
    assert result['version_interpretation']['runtime'] == 'not_probed'


def test_stack_inspects_development_group_declarations_without_resolving_includes(tmp_path):
    (tmp_path / 'pyproject.toml').write_text('''[dependency-groups]
test = ["pytest>=8", {include-group = "async"}]
async = ["pytest-asyncio>=1.2"]
''')
    result = inspector.inspect_project(SOURCE, tmp_path)
    assert result['status'] == 'bounded_scan_complete'
    assert {'python_testing', 'python_asyncio'} <= set(result['candidate_tags'])
    assert {row['value'] for row in result['version_evidence']} == {'pytest>=8', 'pytest-asyncio>=1.2'}
    assert {row['field'] for row in result['version_evidence']} == {
        '/dependency-groups/test/0', '/dependency-groups/async/0'}


def test_poetry_version_fields_identify_the_actual_scalar(tmp_path):
    (tmp_path / 'pyproject.toml').write_text('''[tool.poetry.dependencies]
python = {version = "^3.12"}
fastapi = {version = "^0.115"}
''')
    result = inspector.inspect_project(SOURCE, tmp_path)
    assert result['status'] == 'bounded_scan_complete'
    assert {(row['field'], row['value']) for row in result['version_evidence']} == {
        ('/tool/poetry/dependencies/python/version', '^3.12'),
        ('/tool/poetry/dependencies/fastapi/version', '^0.115')}


def test_python_direct_reference_and_normalized_names_remain_advisory(tmp_path):
    (tmp_path / 'pyproject.toml').write_text('''[project]
dependencies = ["fastapi@git+https://example.invalid/framework@revision", "pytest.Asyncio>=1.2"]
''')
    result = inspector.inspect_project(SOURCE, tmp_path)
    assert {'fastapi', 'python_asyncio', 'python_testing'} <= set(result['candidate_tags'])
    assert {row['technology'] for row in result['version_evidence']} == {'fastapi', 'python_asyncio'}
    assert result['version_interpretation']['compatibility'] == 'not_evaluated'


@pytest.mark.parametrize('filename,content,selector', [
    ('package.json', '{"dependencies":{"react":"git+https://example.invalid/react?token=sample-token"}}',
     'git+https://example.invalid/react?token=sample-token'),
    ('pyproject.toml', '[project]\ndependencies = ["fastapi@git+https://user:sample-token@example.invalid/fw"]',
     'fastapi@git+https://user:sample-token@example.invalid/fw'),
    ('.node-version', 'lts/*', 'lts/*'),
])
def test_opaque_version_selectors_are_hash_bound_without_echoing_references(tmp_path, filename, content, selector):
    (tmp_path / filename).write_text(content)
    result = inspector.inspect_project(SOURCE, tmp_path)
    assert result['status'] == 'bounded_scan_complete'
    row, = result['version_evidence']
    assert row['value'] is None and row['value_status'] == 'opaque_selector'
    assert row['value_sha256'] == hashlib.sha256(selector.encode()).hexdigest()
    assert selector not in json.dumps(result)
    assert 'sample-token' not in json.dumps(result)


@pytest.mark.parametrize('filename,content,expected', [
    ('check.rs', '#[tokio::test]\nasync fn check() {}', {'rust_testing', 'rust_tokio'}),
    ('check_test.go', 'package check', {'go_testing'}),
    ('Check.java', 'import org.junit.jupiter.api.Test;', {'java_testing'}),
    ('check.cpp', '#include <gtest/gtest.h>', {'cpp_testing'}),
    ('check.rb', 'RSpec.describe "check" do\nend', {'ruby_testing'}),
    ('check.mjs', "import { AsyncLocalStorage } from 'node:async_hooks';", {'node'}),
    ('dynamic.mjs', "const { test } = await import('node:test');", {'node', 'node_testing'}),
    ('check.py', 'from pytest import fixture', {'python_testing'}),
])
def test_stack_suggests_test_and_runtime_owners_from_lexical_evidence(tmp_path, filename, content, expected):
    (tmp_path / filename).write_text(content)
    result = inspector.inspect_project(SOURCE, tmp_path)
    assert expected <= set(result['candidate_tags'])
    assert result['authority'] is False
    assert result['version_interpretation']['runtime'] == 'not_probed'


def test_cross_language_pattern_strings_do_not_suggest_unrelated_runtimes(tmp_path):
    (tmp_path / 'patterns.py').write_text('''java = "StructuredTaskScope"
ruby = "Minitest::Test"
go = "sync.WaitGroup"
rust = "#[tokio::test]"
javascript = "import { test } from 'node:test'"
''')
    result = inspector.inspect_project(SOURCE, tmp_path)
    assert result['candidate_tags'] == ['python']
    # JVM code can intentionally call Java concurrency APIs from Kotlin.
    (tmp_path / 'worker.kt').write_text('val factory = Thread.ofVirtual()')
    mixed = inspector.inspect_project(SOURCE, tmp_path)
    assert {'kotlin', 'java_concurrency'} <= set(mixed['candidate_tags'])


def test_rejected_non_utf8_files_consume_the_total_read_budget(tmp_path):
    (tmp_path / 'a.py').write_bytes(b'\xff' * 8)
    (tmp_path / 'b.py').write_bytes(b'\xff' * 8)
    (tmp_path / 'c.py').write_text('import asyncio\n')
    result = inspector.inspect_project(SOURCE, tmp_path, max_file_bytes=32, max_total_bytes=16)
    assert result['bytes_read'] == 16
    assert result['evidence_bytes'] == 0
    assert result['evidence_files'] == []
    assert 'python_asyncio' not in result['candidate_tags']
    assert {'path': 'c.py', 'reason': 'byte_limit'} in result['issues']
    assert result['status'] == 'partial'


@pytest.mark.parametrize('small_evidence', [b'import asyncio\n', b'import asyncio\r\n'])
def test_oversized_files_are_skipped_before_reading_without_starving_small_evidence(tmp_path, small_evidence):
    (tmp_path / 'a.py').write_bytes(b'x' * 33)
    (tmp_path / 'b.py').write_bytes(small_evidence)
    result = inspector.inspect_project(SOURCE, tmp_path, max_file_bytes=32, max_total_bytes=32)
    assert result['bytes_read'] == len(small_evidence)
    assert result['evidence_bytes'] == result['bytes_read']
    assert 'python_asyncio' in result['candidate_tags']
    assert {'path': 'a.py', 'reason': 'byte_limit'} in result['issues']


def test_short_read_is_partial_not_a_hash_of_complete_source(tmp_path, monkeypatch):
    path = tmp_path / 'app.py'
    path.write_text('import asyncio\n')
    original = Path.open

    class ShortReader:
        def __enter__(self):
            self.stream = original(path, 'rb', buffering=0)
            return self

        def __exit__(self, *exc):
            self.stream.close()

        def fileno(self):
            return self.stream.fileno()

        def read(self, size):
            return self.stream.read(1)

    def opened(self, *args, **kwargs):
        return ShortReader() if self == path else original(self, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', opened)
    result = inspector.inspect_project(SOURCE, tmp_path)
    assert result['status'] == 'partial'
    assert result['bytes_read'] == 1
    assert result['evidence_files'] == []
    assert result['candidate_tags'] == []
    assert result['issues'] == [{'path': 'app.py', 'reason': 'incomplete_file_read'}]


@pytest.fixture
def route(tmp_path):
    project = tmp_path / 'project'
    project.mkdir()
    source = tmp_path / 'WISDOM.md'
    source.write_bytes(SOURCE.read_bytes())
    cache = tmp_path / 'cache'
    compiler.compile_and_install(source, cache)
    plan = loader.load_plan(source, cache, task_profile='vite_ui', phase='implement',
                            tags=['typescript', 'technology_continuity'])
    checkpoint = project / 'route.1.json'
    loader.save_route_checkpoint(plan, checkpoint, project_root=project, task_id='change-42')
    return project, source, cache, plan, checkpoint


def restore(route, **extra):
    project, source, cache, _, checkpoint = route
    saved = loader.read_route_checkpoint(checkpoint, source_path=source, project_root=project, task_id='change-42')
    options, continuity = loader.resume_route_options(saved, source_path=source, **extra)
    plan = dict(loader.load_plan(source, cache, **options))
    plan['continuity'] = continuity
    return plan


def test_resume_in_fresh_cli_reloads_complete_bytes_after_losing_prior_context(route):
    project, source, cache, old, checkpoint = route
    command = [sys.executable, str(ROOT / 'scripts/load_compiled_wisdom.py'),
               '--source', str(source), '--cache-root', str(cache),
               '--resume-route', str(checkpoint), '--project-root', str(project), '--task-id', 'change-42']
    planned = json.loads(subprocess.run(command, check=True, capture_output=True).stdout)
    assert planned['module_ids'] == old['module_ids']
    assert planned['continuity']['reload_required'] is True
    assert planned['continuity']['source_changed'] is False
    assert planned['continuity']['content_changed'] is False
    assert 'retained' not in planned['continuity']
    content = subprocess.run(command + ['--emit-content'], check=True, capture_output=True).stdout
    assert content == loader.read_plan_content(old)
    # Recover via independently checked delivery segments, not a receipt as prose.
    assembled = b''.join(subprocess.run(
        command + ['--emit-content-segment', str(segment['index']), '--expected-delivery-id', planned['delivery']['delivery_id']],
        check=True, capture_output=True).stdout for segment in planned['delivery']['segments'])
    assert assembled == content


def test_phase_and_profile_growth_preserve_old_obligations(route):
    old = route[3]
    resumed = restore(route, phase='validate', task_profile='cloud_design', tags=['aws'])
    assert set(old['tags']) <= set(resumed['tags'])
    assert set(old['module_ids']) <= set(resumed['module_ids'])
    assert {'aws', 'cloud_architecture', 'cloud_identity', 'vite', 'typescript'} <= set(resumed['module_ids'])
    assert resumed['phase'] == 'validate'
    with pytest.raises(loader.WisdomCompileError, match='cannot narrow'):
        restore(route, mode='fast')
    assert restore(route, mode='substantial')['mode'] == 'substantial'


@pytest.mark.parametrize('owner', ['profile', 'phase'])
@pytest.mark.parametrize('change', ['expand', 'remove'])
def test_successive_cli_checkpoints_refresh_every_historical_route_owner(route, owner, change):
    project, source, cache, _, checkpoint = route
    command = [sys.executable, str(ROOT / 'scripts/load_compiled_wisdom.py'),
               '--source', str(source), '--cache-root', str(cache),
               '--project-root', str(project), '--task-id', 'change-42']
    second_path = project / 'route.2.json'
    second = json.loads(subprocess.run(command + [
        '--resume-route', str(checkpoint), '--task-profile', 'cloud_design',
        '--phase', 'validate', '--save-route', str(second_path)],
        check=True, capture_output=True, timeout=10).stdout)

    raw = source.read_bytes().decode('utf-8')
    start = raw.index('{', raw.index('<!-- WISDOM-MANIFEST-BEGIN'))
    end = raw.index('WISDOM-MANIFEST-END -->', start)
    manifest = json.loads(raw[start:end])
    rows = manifest['task_profiles'] if owner == 'profile' else manifest['phases']
    old_id = 'vite_ui' if owner == 'profile' else 'implement'
    row = next(item for item in rows if item['id'] == old_id)
    if change == 'expand':
        row['tags'].append('node')
    else:
        row['id'] = 'renamed_' + old_id
    source.write_bytes((raw[:start] + json.dumps(manifest, indent=2) + '\n' + raw[end:]).encode('utf-8'))
    compiler.compile_and_install(source, cache)

    resumed_command = command + ['--resume-route', str(second_path)]
    resumed = json.loads(subprocess.run(resumed_command, check=True,
                                       capture_output=True, timeout=10).stdout)
    content = subprocess.run(resumed_command + ['--emit-content'], check=True,
                             capture_output=True, timeout=10).stdout
    if change == 'remove':
        assert resumed['status'] == 'full_source_required'
        assert content == source.read_bytes()
    else:
        assert resumed['status'] == 'compiled'
        assert set(second['module_ids']) <= set(resumed['module_ids'])
        assert 'node' in resumed['module_ids']
        assert b'NODE-01' in content
        assert 'kubernetes' not in resumed['module_ids']


def test_legacy_checkpoint_cli_upgrades_known_lineage_without_losing_scope(route):
    project, source, cache, old, checkpoint = route
    envelope = json.loads(checkpoint.read_bytes())
    envelope['body']['schema'] = 'wisdom.route_checkpoint.v1'
    for key in ('task_profiles', 'phases'):
        del envelope['body']['selection'][key]
    envelope['body_sha256'] = hashlib.sha256(
        compiler.canonical_json_bytes(envelope['body'])).hexdigest()
    legacy = project / 'legacy.json'
    legacy.write_bytes(compiler.canonical_json_bytes(envelope))
    upgraded = project / 'upgraded.json'
    result = json.loads(subprocess.run([
        sys.executable, str(ROOT / 'scripts/load_compiled_wisdom.py'),
        '--source', str(source), '--cache-root', str(cache),
        '--resume-route', str(legacy), '--save-route', str(upgraded),
        '--project-root', str(project), '--task-id', 'change-42'],
        check=True, capture_output=True, timeout=10).stdout)
    assert result['module_ids'] == old['module_ids']
    assert result['continuity']['content_changed'] is False
    saved = json.loads(upgraded.read_bytes())['body']
    assert saved['schema'] == 'wisdom.route_checkpoint.v2'
    assert saved['selection']['task_profiles'] == ['vite_ui']
    assert saved['selection']['phases'] == ['implement']
    assert legacy.read_bytes() == compiler.canonical_json_bytes(envelope)


@pytest.mark.parametrize('corruption', ['duplicate_profile', 'missing_phase_hint',
                                       'non_string_owner', 'unknown_schema'])
def test_rehashed_invalid_route_lineage_is_rejected(route, corruption):
    project, source, _, _, checkpoint = route
    envelope = json.loads(checkpoint.read_bytes())
    selection = envelope['body']['selection']
    if corruption == 'duplicate_profile':
        selection['task_profiles'] *= 2
    elif corruption == 'missing_phase_hint':
        selection['phases'] = []
    elif corruption == 'non_string_owner':
        selection['phases'] = [{}]
    else:
        envelope['body']['schema'] = []
    envelope['body_sha256'] = hashlib.sha256(
        compiler.canonical_json_bytes(envelope['body'])).hexdigest()
    checkpoint.write_bytes(compiler.canonical_json_bytes(envelope))
    with pytest.raises(loader.WisdomCompileError):
        loader.read_route_checkpoint(checkpoint, source_path=source,
                                     project_root=project, task_id='change-42')


def test_resume_automatically_loads_applicable_recovery_discipline(route):
    project, source, cache, _, _ = route
    ordinary = loader.load_plan(source, cache, mode='fast', tags=['vite'])
    path = project / 'ordinary-route.json'
    loader.save_route_checkpoint(ordinary, path, project_root=project, task_id='ordinary')
    checkpoint = loader.read_route_checkpoint(path, source_path=source,
                                               project_root=project, task_id='ordinary')
    options, _ = loader.resume_route_options(checkpoint, source_path=source)
    resumed = loader.load_plan(source, cache, **options)
    assert set(ordinary['module_ids']) <= set(resumed['module_ids'])
    assert 'technology_continuity' in resumed['module_ids']
    assert b'TCONT-02' in loader.read_plan_content(resumed)


def test_changed_source_is_freshly_loaded_and_stale_delivery_is_rejected(route):
    project, source, cache, old, checkpoint = route
    old_delivery = loader.segmented_delivery_plan(old)
    source.write_bytes(source.read_bytes().replace(b'Separate development from the deployed artifact',
                                                 b'Separate development from the final deployed artifact'))
    compiler.compile_and_install(source, cache)
    fresh = restore(route)
    assert fresh['source_sha256'] != old['source_sha256']
    assert b'final deployed artifact' in loader.read_plan_content(fresh)
    with pytest.raises(loader.WisdomCompileError, match='generation'):
        loader.read_delivery_segment(fresh, 0, expected_delivery_id=old_delivery['delivery_id'])


def test_source_change_between_route_expansion_and_loading_requires_full_source(route):
    project, source, cache, _, checkpoint = route
    saved = loader.read_route_checkpoint(checkpoint, source_path=source,
                                         project_root=project, task_id='change-42')
    options, _ = loader.resume_route_options(saved, source_path=source)
    raw = source.read_bytes().decode('utf-8')
    start = raw.index('{', raw.index('<!-- WISDOM-MANIFEST-BEGIN'))
    end = raw.index('WISDOM-MANIFEST-END -->', start)
    manifest = json.loads(raw[start:end])
    next(row for row in manifest['task_profiles'] if row['id'] == 'vite_ui')['tags'].append('node')
    source.write_bytes((raw[:start] + json.dumps(manifest, indent=2) + '\n' + raw[end:]).encode('utf-8'))
    compiler.compile_and_install(source, cache)
    # Cache is current; only the independently changed route definition is stale.
    assert loader.load_plan(source, cache, task_profile='vite_ui')['status'] == 'compiled'
    resumed = loader.load_plan(source, cache, **options)
    assert resumed['status'] == 'full_source_required'
    assert loader.read_plan_content(resumed) == source.read_bytes()


@pytest.mark.parametrize('change', ['expand', 'narrow', 'remove'])
def test_current_profile_changes_do_not_drop_saved_scope(route, change):
    _, source, cache, old, _ = route
    raw = source.read_bytes().decode('utf-8')
    start = raw.index('{', raw.index('<!-- WISDOM-MANIFEST-BEGIN'))
    end = raw.index('WISDOM-MANIFEST-END -->', start)
    manifest = json.loads(raw[start:end])
    profile = next(row for row in manifest['task_profiles'] if row['id'] == 'vite_ui')
    if change == 'expand':
        profile['tags'].append('node')
    elif change == 'narrow':
        profile['tags'].remove('web_accessibility')
    else:
        profile['id'] = 'renamed_vite_profile'
    source.write_bytes((raw[:start] + json.dumps(manifest, indent=2) + '\n' + raw[end:]).encode('utf-8'))
    compiler.compile_and_install(source, cache)
    resumed = restore(route)
    if change == 'remove':
        assert resumed['status'] == 'full_source_required'
        assert loader.read_plan_content(resumed) == source.read_bytes()
    else:
        assert set(old['module_ids']) <= set(resumed['module_ids'])
        if change == 'expand':
            assert 'node' in resumed['module_ids']


@pytest.mark.parametrize('wrong', ['task', 'project', 'source'])
def test_checkpoint_cannot_be_applied_to_another_task_project_or_installation(route, tmp_path, wrong):
    project, source, _, _, checkpoint = route
    other = tmp_path / 'other'
    other.mkdir()
    with pytest.raises(loader.WisdomCompileError, match='different'):
        loader.read_route_checkpoint(checkpoint, source_path=other if wrong == 'source' else source,
                                     project_root=other if wrong == 'project' else project,
                                     task_id='other-task' if wrong == 'task' else 'change-42')


@pytest.mark.parametrize('corruption', ['truncated', 'checksum', 'duplicate', 'oversized', 'companion_shape'])
def test_corrupted_checkpoints_fail_before_route_loading(route, corruption):
    project, source, _, _, checkpoint = route
    data = json.loads(checkpoint.read_bytes())
    if corruption == 'truncated':
        raw = checkpoint.read_bytes()[:100]
    elif corruption == 'checksum':
        data['body']['selection']['tags'] = []
        raw = json.dumps(data).encode()
    elif corruption == 'duplicate':
        raw = checkpoint.read_bytes().replace(b'"authority":false', b'"authority":false,"authority":false')
    elif corruption == 'oversized':
        raw = b' ' * (loader.MAX_CHECKPOINT_BYTES + 1)
    else:
        data['body']['companion_source'] = {'path': 42, 'bytes': False, 'sha256': []}
        data['body_sha256'] = loader.sha256_bytes(loader.canonical_json_bytes(data['body']))
        raw = json.dumps(data).encode()
    checkpoint.write_bytes(raw)
    with pytest.raises(loader.WisdomCompileError):
        loader.read_route_checkpoint(checkpoint, source_path=source, project_root=project, task_id='change-42')


def test_publication_never_overwrites_another_generation_or_escapes_project(route, tmp_path):
    project, _, _, plan, checkpoint = route
    before = checkpoint.read_bytes()
    with pytest.raises(loader.WisdomCompileError, match='already exists'):
        loader.save_route_checkpoint(plan, checkpoint, project_root=project, task_id='change-42')
    assert checkpoint.read_bytes() == before
    with pytest.raises(loader.WisdomCompileError, match='inside'):
        loader.save_route_checkpoint(plan, tmp_path / 'outside.json', project_root=project, task_id='change-42')
    next_path = project / 'route.2.json'
    loader.save_route_checkpoint(restore(route, tags=['node']), next_path, project_root=project, task_id='change-42')
    assert checkpoint.read_bytes() == before
    assert not list(project.glob('.wisdom-route-*'))


def test_missing_cache_and_full_source_fallback_never_resume_as_a_narrower_view(route):
    project, source, cache, _, _ = route
    fallback = loader.load_plan(source, cache / 'absent', mode='fast', tags=['vite'])
    checkpoint = project / 'full.json'
    loader.save_route_checkpoint(fallback, checkpoint, project_root=project, task_id='change-42')
    saved = loader.read_route_checkpoint(checkpoint, source_path=source, project_root=project, task_id='change-42')
    options, _ = loader.resume_route_options(saved, source_path=source)
    assert options['mode'] == 'full'
    resumed = loader.load_plan(source, cache, **options)
    assert loader.read_plan_content(resumed) == source.read_bytes()


def test_resume_retains_and_revalidates_exact_companion(route):
    project, source, cache, _, _ = route
    companion = project / 'PLAN.md'
    companion.write_text('Use existing test tools.\n')
    plan = loader.load_plan(source, cache, mode='fast', tags=['rust_api'],
                            companion_source_path=companion,
                            expected_companion_bytes=companion.stat().st_size,
                            expected_companion_sha256=hashlib.sha256(companion.read_bytes()).hexdigest())
    path = project / 'companion-route.json'
    loader.save_route_checkpoint(plan, path, project_root=project, task_id='library')
    saved = loader.read_route_checkpoint(path, source_path=source, project_root=project, task_id='library')
    options, _ = loader.resume_route_options(saved, source_path=source)
    assert loader.read_plan_content(loader.load_plan(source, cache, **options)).endswith(companion.read_bytes())
    companion.write_text('Changed decision.\n')
    with pytest.raises(loader.WisdomCompileError, match='exact binding'):
        loader.load_plan(source, cache, **options)


def test_every_segment_decodes_and_reassembles_at_a_multibyte_boundary(tmp_path):
    source = tmp_path / 'WISDOM.md'
    # Full-source fallback permits this tiny valid UTF-8 source without a manifest.
    raw = b'x' * 4095 + '\U0001f9a6\u00e9\u4e2d'.encode() * 1000
    source.write_bytes(raw)
    plan = loader.load_plan(source, tmp_path / 'cache', mode='full')
    delivery = loader.segmented_delivery_plan(plan, segment_bytes=4096)
    pieces = [loader.read_delivery_segment(plan, row['index'],
                expected_delivery_id=delivery['delivery_id'], segment_bytes=4096)
              for row in delivery['segments']]
    assert delivery['segment_encoding'] == 'utf-8'
    assert delivery['segments'][0]['bytes'] == 4095
    assert all(0 < len(piece) <= 4096 for piece in pieces)
    assert ''.join(piece.decode('utf-8', errors='strict') for piece in pieces).encode() == raw
    assert b''.join(pieces) == raw


def test_invalid_utf8_cannot_be_emitted_as_instructions(tmp_path):
    source = tmp_path / 'WISDOM.md'
    source.write_bytes(b'corrupt instructions\xff')
    plan = loader.load_plan(source, tmp_path / 'cache', mode='full')
    with pytest.raises(loader.WisdomCompileError, match='valid UTF-8'):
        loader.read_plan_content(plan)


def test_full_source_delivery_also_binds_the_segmentation_tools(tmp_path, monkeypatch):
    source = tmp_path / 'WISDOM.md'
    source.write_text('Current source instructions.\n')
    plan = loader.load_plan(source, tmp_path / 'cache', mode='full')
    original = loader.segmented_delivery_plan(plan)
    tools = dict(original['delivery_tool_hashes'])
    tools['loader_sha256'] = 'f' * 64
    monkeypatch.setattr(loader, '_tool_hashes', lambda: tools)
    with pytest.raises(loader.WisdomCompileError, match='generation'):
        loader.read_delivery_segment(plan, 0, expected_delivery_id=original['delivery_id'])


def write(root, path, text):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    return target


def test_inspection_suggests_real_mixed_stack_without_executing_project_scripts(tmp_path):
    write(tmp_path, 'package.json', json.dumps({'dependencies': {'react': '*'}, 'devDependencies': {'vite': '*'},
        'scripts': {'preinstall': 'touch EXECUTED'}}))
    write(tmp_path, 'src/main.tsx', "import React from 'react';\nuseEffect(() => {}, []);\n")
    write(tmp_path, 'Dockerfile', 'FROM scratch\n')
    result = inspector.inspect_project(SOURCE, tmp_path)
    assert {'react', 'react_effects', 'vite', 'typescript', 'docker_build'} <= set(result['candidate_tags'])
    assert not {'node', 'nextjs', 'aws', 'kubernetes'}.intersection(result['candidate_tags'])
    assert result['authority'] is False
    assert not (tmp_path / 'EXECUTED').exists()
    assert result['review_required']
    before = next(row for row in result['evidence_files'] if row['path'] == 'src/main.tsx')
    write(tmp_path, 'src/main.tsx', 'export const value = 1;\n')
    changed = inspector.inspect_project(SOURCE, tmp_path)
    after = next(row for row in changed['evidence_files'] if row['path'] == before['path'])
    assert before['sha256'] != after['sha256']
    assert 'react_effects' not in changed['candidate_tags']


def test_affected_paths_find_ancestor_manifests_but_not_sibling_service(tmp_path):
    write(tmp_path, 'web/package.json', '{"devDependencies":{"vite":"*"}}')
    write(tmp_path, 'web/src/main.ts', 'export const value = 1;\n')
    write(tmp_path, 'backend/pyproject.toml', '[project]\nname="api"\ndependencies=["fastapi", "psycopg[binary]"]\n')
    result = inspector.inspect_project(SOURCE, tmp_path, ['web/src/main.ts'])
    assert set(result['candidate_tags']) == {'vite', 'typescript'}
    assert all(not row['path'].startswith('backend/') for row in result['evidence'])


def test_inspector_reports_limits_malformed_manifests_and_missing_paths(tmp_path):
    write(tmp_path, 'pyproject.toml', 'invalid = [')
    write(tmp_path, 'long.py', 'x' * 100)
    result = inspector.inspect_project(SOURCE, tmp_path, ['missing.py', '.'], max_file_bytes=50)
    reasons = {item['reason'] for item in result['issues']}
    assert {'manifest_unparsed', 'byte_limit', 'path_missing_or_not_regular'} <= reasons
    assert result['status'] == 'partial'
    assert 'never establishes complete applicability' in result['review_required'][-1]
    assert inspector.inspect_project(SOURCE, tmp_path, max_files=1)['status'] == 'partial'


def test_inspector_skips_dependency_trees_and_symlinks_and_rejects_escape(tmp_path):
    write(tmp_path, 'node_modules/next/server.js', 'export const x = 1;')
    write(tmp_path, 'src/main.py', 'import asyncio\n')
    try:
        (tmp_path / 'linked.py').symlink_to(tmp_path / 'src/main.py')
    except OSError:
        pytest.skip('symlink creation unavailable')
    result = inspector.inspect_project(SOURCE, tmp_path)
    assert set(result['candidate_tags']) == {'python', 'python_asyncio'}
    assert any(row['reason'] == 'symlink_skipped' for row in result['issues'])
    for path in ('../outside', 'linked.py'):
        with pytest.raises(ValueError):
            inspector.inspect_project(SOURCE, tmp_path, [path])


def test_extracted_archive_inspects_saves_and_recovers_without_repository_imports(tmp_path):
    installed = tmp_path / 'installed'
    with zipfile.ZipFile(ROOT / 'WISDOM.zip') as archive:
        archive.extractall(installed)
    project = tmp_path / 'app'
    project.mkdir()
    write(project, 'package.json', '{"devDependencies":{"vite":"^7.0.0"}}')
    write(project, 'src/main.ts', 'export const value = 1;\n')
    scan = subprocess.run([sys.executable, str(installed / 'scripts/inspect_wisdom_stack.py'),
                           '--project-root', str(project), '--path', 'src/main.ts'],
                          cwd=project, check=True, capture_output=True)
    inspected = json.loads(scan.stdout)
    assert set(inspected['candidate_tags']) == {'vite', 'typescript'}
    assert inspected['version_evidence'] == [
        {'technology': 'vite', 'path': 'package.json', 'field': '/devDependencies/vite',
         'value': '^7.0.0', 'kind': 'declared_constraint'}]
    assert inspected['version_interpretation']['runtime'] == 'not_probed'
    checkpoint = project / 'route.json'
    base = [sys.executable, str(installed / 'scripts/load_compiled_wisdom.py'),
            '--cache-root', str(tmp_path / 'cache'), '--project-root', str(project), '--task-id', 'portable']
    prepared = subprocess.run(base + ['--prepare-cache', '--task-profile', 'vite_ui', '--tag', 'typescript',
                                      '--save-route', str(checkpoint)],
                              cwd=project, check=True, capture_output=True)
    plan = json.loads(prepared.stdout)
    saved = json.loads(checkpoint.read_bytes())['body']
    assert saved['schema'] == 'wisdom.route_checkpoint.v2'
    assert saved['selection']['task_profiles'] == ['vite_ui']
    discovery = json.loads(subprocess.run([
        sys.executable, str(installed / 'scripts/load_compiled_wisdom.py'), '--discover'],
        cwd=project, check=True, capture_output=True, timeout=10).stdout)
    vite = next(row for row in discovery['modules'] if row['id'] == 'vite')
    assert vite['routing_hints'][0]['heading'] == 'Vite builds, environment boundaries, and deployment'
    assert vite['routing_hints'][0]['load_when']
    resumed = json.loads(subprocess.run(base + ['--resume-route', str(checkpoint)],
                                       cwd=project, check=True, capture_output=True).stdout)
    assert set(plan['module_ids']) <= set(resumed['module_ids'])
    content = subprocess.run(base + ['--resume-route', str(checkpoint), '--emit-content'],
                             cwd=project, check=True, capture_output=True).stdout
    assert b'VITE-03' in content and b'TS-01' in content
    assert hashlib.sha256(content).hexdigest() == resumed['delivery']['content_sha256']
