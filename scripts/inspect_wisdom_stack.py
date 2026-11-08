#!/usr/bin/env python3
"""Suggest WISDOM technology tags from bounded local evidence; never select a route."""
from __future__ import annotations

import argparse
import hashlib
from importlib.machinery import SourceFileLoader
import importlib.util
import os
from pathlib import Path
import re
import sys
import tomllib
from typing import Sequence


class _SourceOnlyLoader(SourceFileLoader):
    """Load the exact sibling source without reading or writing bytecode caches."""

    def get_code(self, fullname):
        return self.source_to_code(self.get_data(self.path), self.path)


def _compiler():
    path = Path(__file__).resolve().with_name('compile_wisdom.py')
    name = '_wisdom_stack_compiler_' + hashlib.sha256(str(path).encode()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path, loader=_SourceOnlyLoader(name, str(path)))
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load sibling compiler')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


compiler = _compiler()
SCHEMA = 'wisdom.technology_candidates.v1'
SKIP = {'.git', '.hg', '.svn', 'node_modules', '.venv', 'venv', 'vendor', 'target',
        'dist', 'build', '.next', '.nuxt', '.svelte-kit', '.wisdom-cache', '__pycache__',
        '.pytest_cache', '.mypy_cache', '.terraform', 'coverage'}
MANIFESTS = {'package.json', 'pyproject.toml', 'Cargo.toml', 'go.mod', 'Gemfile',
             'pom.xml', 'build.gradle', 'build.gradle.kts', 'CMakeLists.txt'}
VERSION_FILES = {'.python-version': 'python', '.node-version': 'node', '.nvmrc': 'node',
                 '.ruby-version': 'ruby', '.java-version': 'java'}
METADATA = MANIFESTS | VERSION_FILES.keys() | {'rust-toolchain.toml', 'global.json'}
SUFFIX_TAG = {'.py': 'python', '.rs': 'rust', '.go': 'go', '.java': 'java',
              '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp', '.hpp': 'cpp',
              '.rb': 'ruby', '.js': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript',
              '.jsx': 'react', '.ts': 'typescript', '.tsx': 'typescript',
              '.mts': 'typescript', '.cts': 'typescript', '.sql': 'sql_relational', '.vue': 'vue',
              '.svelte': 'svelte', '.cs': 'csharp', '.kt': 'kotlin', '.kts': 'kotlin',
              '.tf': 'terraform', '.sh': 'shell_practices'}
PACKAGES = {
    'react': 'react', 'react-dom': 'react', 'next': 'nextjs', 'vite': 'vite',
    'vue': 'vue', 'svelte': 'svelte', '@sveltejs/kit': 'svelte',
    'django': 'django', 'fastapi': 'fastapi', 'tokio': 'rust_tokio',
    'rails': 'rails', 'pg': 'postgres', 'psycopg': 'postgres', 'psycopg2': 'postgres',
    'psycopg2-binary': 'postgres', 'asyncpg': 'postgres', 'tokio-postgres': 'postgres',
    'mysql2': 'mysql', 'mysqlclient': 'mysql', 'pymysql': 'mysql',
    'sqlite3': 'sqlite', 'better-sqlite3': 'sqlite', 'rusqlite': 'sqlite',
    'duckdb': 'duckdb', 'clickhouse-connect': 'clickhouse', '@clickhouse/client': 'clickhouse',
    'neo4j': 'graph', 'pymongo': 'mongodb', 'mongodb': 'mongodb', 'mongoose': 'mongodb',
    'redis': 'redis', 'ioredis': 'redis', 'cassandra-driver': 'wide_column',
    'elasticsearch': 'search', '@elastic/elasticsearch': 'search',
    'qdrant-client': 'vector', 'pgvector': 'vector', 'influxdb-client': 'timeseries',
    'kafka-python': 'kafka', 'confluent-kafka': 'kafka', 'kafkajs': 'kafka',
    'boto3': 'aws', 'botocore': 'aws', 'azure-identity': 'azure',
    'google-cloud-storage': 'gcp', 'google-cloud-pubsub': 'gcp',
    'pytest': 'python_testing', 'rspec': 'ruby_testing', 'minitest': 'ruby_testing',
    'pytest-asyncio': 'python_asyncio', '@testing-library/react': 'react_testing',
    '@testing-library/dom': 'web_testing', '@playwright/test': 'web_testing',
    'playwright': 'web_testing', '@testing-library/user-event': 'web_testing',
    '@vue/test-utils': 'web_testing', '@testing-library/vue': 'web_testing',
    '@testing-library/svelte': 'web_testing',
}
JS_SUFFIXES = {suffix for suffix, tag in SUFFIX_TAG.items()
               if tag in {'javascript', 'typescript', 'react', 'vue', 'svelte'}}
JVM_SUFFIXES = {suffix for suffix, tag in SUFFIX_TAG.items() if tag in {'java', 'kotlin'}}
CPP_SUFFIXES = {suffix for suffix, tag in SUFFIX_TAG.items() if tag == 'cpp'} | {'.h', '.hh', '.hxx'}
IMPORTS = (
    (r'^\s*(?:from\s+asyncio\b|import\s+asyncio\b)', 'python_asyncio', {'.py'}),
    (r'^\s*(?:from\s+(?:pytest|unittest)\b|import\s+(?:pytest|unittest)\b)', 'python_testing', {'.py'}),
    (r'\b(?:use|extern crate)\s+tokio\b|#\[tokio::', 'rust_tokio', {'.rs'}),
    (r'#\[(?:test|tokio::test)\b', 'rust_testing', {'.rs'}),
    (r'''(?:from\s*|(?:require|import)\s*\(?\s*)['"]node:[\w]+''', 'node', JS_SUFFIXES),
    (r'''(?:from\s*|(?:require|import)\s*\(?\s*)['"]node:test['"]''', 'node_testing', JS_SUFFIXES),
    (r'''(?:from\s*|require\s*\()\s*['"]react(?:/[^'"]*)?['"]''', 'react', JS_SUFFIXES),
    (r'\b(?:useEffect|useLayoutEffect)\s*\(', 'react_effects', JS_SUFFIXES),
    (r'\b(?:goroutine|sync\.(?:Mutex|WaitGroup)|context\.WithCancel)\b|\bgo\s+(?:func\s*\(|[\w.]+\s*\()', 'go_concurrency', {'.go'}),
    (r'\b(?:StructuredTaskScope|Executors\.newVirtualThreadPerTaskExecutor|Thread\.ofVirtual)\b', 'java_concurrency', JVM_SUFFIXES),
    (r'\bimport\s+(?:static\s+)?org\.(?:junit|testng)\.', 'java_testing', JVM_SUFFIXES),
    (r'\bstd::(?:jthread|thread|mutex|atomic)\b', 'cpp_concurrency', CPP_SUFFIXES),
    (r'^\s*#\s*include\s*[<"](?:gtest/|catch2/|doctest/)', 'cpp_testing', CPP_SUFFIXES),
    (r'\b(?:RSpec\.describe|Minitest::Test)\b', 'ruby_testing', {'.rb'}),
    (r'^\s*apiVersion:\s*\S+[\s\S]*?^\s*kind:\s*(?:Deployment|StatefulSet|DaemonSet|Pod|Job|CronJob|Service|NetworkPolicy)\b', 'kubernetes', {'.yaml', '.yml'}),
    (r'^\s*provider\s+"aws"', 'aws', {'.tf'}),
    (r'^\s*provider\s+"google(?:-beta)?"', 'gcp', {'.tf'}),
    (r'^\s*provider\s+"azurerm"', 'azure', {'.tf'}),
)


def inspect_project(source: Path, root: Path, paths: Sequence[str] = (), *,
                    max_files: int = 600, max_file_bytes: int = 128 * 1024,
                    max_total_bytes: int = 4 * 1024 * 1024, max_entries: int = 6000) -> dict:
    if any(type(x) is not int or x < 1 for x in (max_files, max_file_bytes, max_total_bytes, max_entries)):
        raise ValueError('inspection bounds must be positive integers')
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('project root must be a directory')
    parsed = compiler.parse_source(source)
    allowed = set(parsed.manifest['allowed_tags'])
    evidence: set[tuple[str, str, str]] = set()
    versions: set[tuple[str, str, str, str, str]] = set()
    issues: set[tuple[str, str]] = set()
    files: set[Path] = set()
    entries_seen = 0
    selection = list(paths) or ['.']

    def issue(path: Path, reason: str):
        issues.add((path.relative_to(root).as_posix(), reason))

    def add(tag: str, path: Path, reason: str):
        if tag in allowed:
            evidence.add((tag, path.relative_to(root).as_posix(), reason))

    def version(technology: str, path: Path, field: str, value, kind: str = 'declared_constraint'):
        if not isinstance(value, str) or not value.strip():
            issue(path, 'version_declaration_unparsed')
            return
        versions.add((technology, path.relative_to(root).as_posix(), field, value, kind))

    def dependency(name: str, value, path: Path, field: str):
        if not isinstance(value, str) or not value.strip():
            issue(path, 'version_declaration_unparsed')
            return
        technology = PACKAGES.get(name.lower().replace('_', '-'))
        if technology:
            version(technology, path, field, value)

    def table(value) -> dict:
        if not isinstance(value, dict):
            raise ValueError('manifest object required')
        return value

    def string_list(value) -> list[str]:
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError('manifest string array required')
        return value

    def field_path(*parts: str) -> str:
        return '/' + '/'.join(part.replace('~', '~0').replace('/', '~1') for part in parts)

    def safe_path(value: str) -> Path:
        candidate = Path(value)
        if candidate.is_absolute() or '..' in candidate.parts:
            raise ValueError('inspection paths must be relative and stay inside the project')
        current = root
        for part in candidate.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError('explicit inspection paths must not traverse symlinks')
        return current

    def enqueue(path: Path):
        if len(files) >= max_files and path not in files:
            issue(path, 'file_limit')
            return
        files.add(path)

    for value in selection:
        selected = safe_path(value)
        parent = selected if selected.is_dir() else selected.parent
        # Ancestor manifests explain ownership; unrelated sibling projects stay out.
        while parent.is_relative_to(root):
            for name in sorted(METADATA):
                manifest = parent / name
                if manifest.is_symlink():
                    issue(manifest, 'symlink_skipped')
                elif manifest.is_file():
                    enqueue(manifest)
            if parent == root:
                break
            parent = parent.parent
        if selected.is_file():
            enqueue(selected)
        elif selected.is_dir():
            pending = [selected]
            while pending and entries_seen < max_entries and len(files) < max_files:
                directory = pending.pop()
                children = []
                try:
                    with os.scandir(directory) as stream:
                        for entry in stream:
                            entries_seen += 1
                            if entries_seen > max_entries:
                                issue(directory, 'entry_limit')
                                break
                            children.append(entry)
                    for entry in sorted(children, key=lambda item: item.name, reverse=True):
                        path = Path(entry.path)
                        if entry.is_symlink():
                            issue(path, 'symlink_skipped')
                        elif entry.is_dir(follow_symlinks=False):
                            if entry.name not in SKIP:
                                pending.append(path)
                        elif entry.is_file(follow_symlinks=False) and (
                            path.suffix in SUFFIX_TAG or path.name in METADATA
                            or path.suffix in {'.yaml', '.yml', '.csproj', '.xml'}
                            or path.name.startswith(('Dockerfile', 'vite.config.', 'requirements'))
                        ):
                            enqueue(path)
                except OSError:
                    issue(directory, 'directory_unreadable')
            if pending:
                issue(selected, 'scan_limit')
        else:
            issue(selected, 'path_missing_or_not_regular')

    total = 0
    evidence_files = []
    for path in sorted(files):
        try:
            if path.is_symlink() or not path.is_file():
                issue(path, 'file_changed_or_not_regular')
                continue
            with path.open('rb', buffering=0) as stream:
                before = os.fstat(stream.fileno())
                remaining = max_total_bytes - total
                if before.st_size > max_file_bytes or before.st_size > remaining or remaining == 0:
                    issue(path, 'byte_limit')
                    continue
                raw = stream.read(min(max_file_bytes + 1, remaining))
                # Charge every read, including malformed, changed, and rejected files.
                total += len(raw)
                after = os.fstat(stream.fileno())
            current = path.stat()
            if any((item.st_ino, item.st_size, item.st_mtime_ns) !=
                   (before.st_ino, before.st_size, before.st_mtime_ns) for item in (after, current)):
                issue(path, 'file_changed_during_scan')
                continue
            if len(raw) != before.st_size:
                issue(path, 'incomplete_file_read')
                continue
            if len(raw) > max_file_bytes:
                issue(path, 'byte_limit')
                continue
            text = raw.decode('utf-8')
            evidence_files.append({'path': path.relative_to(root).as_posix(),
                                   'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        except (OSError, UnicodeDecodeError):
            issue(path, 'unreadable_or_non_utf8')
            continue
        suffix = path.suffix
        if suffix in SUFFIX_TAG:
            add(SUFFIX_TAG[suffix], path, 'source_extension_requires_caller_review')
        if path.name.endswith('_test.go'):
            add('go_testing', path, 'go_test_source_requires_caller_review')
        if path.name.startswith('Dockerfile'):
            add('docker_build', path, 'dockerfile_requires_target_review')
        if path.name.startswith('vite.config.'):
            add('vite', path, 'vite_configuration')
        packages = []
        try:
            if path.name == 'package.json':
                data = table(compiler.strict_json_loads(raw, label='package manifest'))
                for group in ('dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies'):
                    values = table(data.get(group, {}))
                    packages.extend(values)
                    for name, value in values.items():
                        dependency(name, value, path, field_path(group, name))
                engines = table(data.get('engines', {}))
                if 'node' in engines:
                    add('node', path, 'declared_node_engine_may_only_serve_build_tools')
                    version('node', path, '/engines/node', engines['node'])
            elif path.name in {'pyproject.toml', 'Cargo.toml', 'rust-toolchain.toml'}:
                data = tomllib.loads(text)
                if path.name == 'pyproject.toml':
                    add('python', path, 'python_project_manifest')
                    project = table(data.get('project', {}))
                    if 'requires-python' in project:
                        version('python', path, '/project/requires-python', project['requires-python'])
                    groups = {'/project/dependencies': string_list(project.get('dependencies', []))}
                    for name, group in table(project.get('optional-dependencies', {})).items():
                        groups[field_path('project', 'optional-dependencies', name)] = string_list(group)
                    for name, group in table(data.get('dependency-groups', {})).items():
                        if not isinstance(group, list):
                            raise ValueError('dependency group array required')
                        # Inspect declarations in every group, without resolving includes
                        # or implying that any group is active in the changed caller.
                        groups[field_path('dependency-groups', name)] = group
                        for requirement in group:
                            if not isinstance(requirement, str) and not (isinstance(requirement, dict)
                                      and set(requirement) == {'include-group'}
                                      and isinstance(requirement['include-group'], str)):
                                issue(path, 'manifest_dependency_unparsed')
                    for field, group in groups.items():
                        for index, requirement in enumerate(group):
                            if not isinstance(requirement, str):
                                continue
                            name = re.split(r'[\s\[<>=!~;@]', requirement.strip(), maxsplit=1)[0]
                            name = re.sub(r'[-_.]+', '-', name).lower()
                            packages.append(name)
                            dependency(name, requirement, path, field + '/' + str(index))
                    poetry = table(table(table(data.get('tool', {})).get('poetry', {})).get('dependencies', {}))
                    packages.extend(name for name in poetry if name != 'python')
                    for name, config in poetry.items():
                        field = field_path('tool', 'poetry', 'dependencies', name)
                        value = config.get('version') if isinstance(config, dict) else config
                        if name == 'python':
                            version('python', path, field + '/version' if isinstance(config, dict) else field, value)
                        elif value is not None:
                            dependency(name, value, path, field + '/version' if isinstance(config, dict) else field)
                elif path.name == 'Cargo.toml':
                    add('rust', path, 'cargo_manifest_including_possible_workspace')
                    workspace = table(data.get('workspace', {}))
                    for prefix, package in ((('package',), table(data.get('package', {}))),
                                            (('workspace', 'package'), table(workspace.get('package', {})))):
                        for name, kind in (('rust-version', 'declared_constraint'), ('edition', 'edition')):
                            value = package.get(name)
                            if isinstance(value, dict) and value.get('workspace') is True:
                                continue  # The ancestor workspace declaration is separate evidence.
                            if name in package:
                                version('rust', path, field_path(*prefix, name), value, kind)
                    scopes = [((), data), (('workspace',), workspace)]
                    scopes.extend((('target', name), table(config))
                                  for name, config in table(data.get('target', {})).items())
                    for prefix, scope in scopes:
                        for group in ('dependencies', 'dev-dependencies', 'build-dependencies'):
                            for name, config in table(scope.get(group, {})).items():
                                actual = config.get('package', name) if isinstance(config, dict) else name
                                packages.append(actual)
                                value = config.get('version') if isinstance(config, dict) else config
                                if value is not None and isinstance(actual, str):
                                    field = field_path(*prefix, group, name)
                                    dependency(actual, value, path, field + '/version' if isinstance(config, dict) else field)
                else:
                    add('rust', path, 'rust_toolchain_selector_requires_caller_review')
                    toolchain = table(data.get('toolchain', {}))
                    if 'channel' in toolchain:
                        version('rust', path, '/toolchain/channel', toolchain['channel'], 'toolchain_selector')
            elif path.name in VERSION_FILES:
                technology = VERSION_FILES[path.name]
                add(technology, path, 'toolchain_selector_requires_caller_review')
                version(technology, path, '', text.strip(), 'toolchain_selector')
            elif path.name == 'global.json':
                data = table(compiler.strict_json_loads(raw, label='.NET SDK manifest'))
                sdk = table(data.get('sdk', {}))
                if 'version' in sdk:
                    add('csharp', path, 'dotnet_sdk_may_also_serve_other_languages')
                    version('dotnet_sdk', path, '/sdk/version', sdk['version'], 'toolchain_selector')
            elif path.name == 'Gemfile' or path.name.startswith('requirements'):
                packages.extend(re.findall(r'''^\s*(?:gem\s+['"])?([A-Za-z0-9_.-]+)''', text, re.M))
                add('ruby' if path.name == 'Gemfile' else 'python', path, 'dependency_manifest')
            elif path.name == 'go.mod':
                add('go', path, 'go_module_manifest')
                for match in re.finditer(r'^\s*(go|toolchain)\s+(\S+)', text, re.M):
                    kind = 'declared_constraint' if match[1] == 'go' else 'toolchain_selector'
                    version('go', path, match[1], match[2], kind)
            elif path.name in {'pom.xml', 'build.gradle', 'build.gradle.kts'}:
                add('java', path, 'jvm_build_requires_source_language_review')
                if 'org.springframework' in text:
                    add('spring', path, 'declared_spring_dependency')
            elif path.name == 'CMakeLists.txt':
                # CMake also builds C, Fortran, etc.; require a declared C++ language.
                if re.search(r'\b(?:CXX|cxx_std_[0-9]+)\b', text):
                    add('cpp', path, 'declared_cmake_cxx_target')
        except (ValueError, TypeError, AttributeError, RecursionError, compiler.WisdomCompileError):
            issue(path, 'manifest_unparsed')
        for package in packages:
            if not isinstance(package, str):
                issue(path, 'manifest_dependency_unparsed')
                continue
            name = re.split(r'[\s\[<>=!~;]', package, maxsplit=1)[0].lower().replace('_', '-')
            if name in PACKAGES:
                add(PACKAGES[name], path, 'declared_dependency:' + name)
                if name == 'pytest-asyncio':
                    add('python_testing', path, 'declared_async_test_dependency')
            elif name.startswith('@aws-sdk/'):
                add('aws', path, 'declared_aws_sdk')
            elif name.startswith('@azure/'):
                add('azure', path, 'declared_azure_sdk')
            elif name.startswith('@google-cloud/'):
                add('gcp', path, 'declared_google_cloud_sdk')
        for pattern, tag, suffixes in IMPORTS:
            if suffix in suffixes and re.search(pattern, text, re.M):
                add(tag, path, 'syntax_hint_requires_execution_path_review')
    candidates = sorted({tag for tag, _, _ in evidence})
    version_rows = []
    for technology, path, field, value, kind in sorted(versions):
        row: dict[str, str | None] = {
            'technology': technology, 'path': path, 'field': field, 'value': value, 'kind': kind}
        # Dependency URLs may carry credentials/query tokens. Keep their source
        # binding, without copying an opaque reference into task-state reports.
        if any(character in value for character in ('/', ':', '@', '?', '%', '\n', '\r')):
            row.update(value=None, value_status='opaque_selector',
                       value_sha256=hashlib.sha256(value.encode('utf-8')).hexdigest())
        version_rows.append(row)
    return {
        'schema': SCHEMA, 'authority': False, 'status': 'partial' if issues else 'bounded_scan_complete',
        'source_sha256': parsed.source_sha256, 'project_root': str(root), 'scope': selection,
        'candidate_tags': candidates,
        'evidence': [{'tag': tag, 'path': path, 'reason': reason} for tag, path, reason in sorted(evidence)],
        'limits': {'max_files': max_files, 'max_file_bytes': max_file_bytes,
                   'max_total_bytes': max_total_bytes, 'max_entries': max_entries},
        'files_considered': len(files), 'bytes_read': total,
        'evidence_bytes': sum(item['bytes'] for item in evidence_files),
        'evidence_files': evidence_files,
        'version_evidence': version_rows,
        'version_interpretation': {'compatibility': 'not_evaluated', 'runtime': 'not_probed',
                                   'lockfile_resolution': 'not_parsed'},
        'issues': [{'path': path, 'reason': reason} for path, reason in sorted(issues)],
        'review_required': ['Confirm affected production/test callers and supported versions.',
                            'Version evidence preserves declarations, selectors, and editions; it does not prove installed APIs or reconcile constraints.',
                            'Discard inactive, optional, generated, or unrelated candidates.',
                            'Add mechanisms, deployment targets, or unrecognized technologies manually.',
                            'Apply current user preferences; then choose explicit loader tags.',
                            'A bounded scan, including an empty result, never establishes complete applicability.'],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1] / 'WISDOM.md')
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--path', action='append', default=[])
    parser.add_argument('--max-files', type=int, default=600)
    parser.add_argument('--max-file-bytes', type=int, default=128 * 1024)
    parser.add_argument('--max-total-bytes', type=int, default=4 * 1024 * 1024)
    parser.add_argument('--max-entries', type=int, default=6000)
    args = parser.parse_args(argv)
    try:
        result = inspect_project(args.source, args.project_root, args.path, max_files=args.max_files,
                                 max_file_bytes=args.max_file_bytes, max_total_bytes=args.max_total_bytes,
                                 max_entries=args.max_entries)
        print(compiler.canonical_json_bytes(result).decode())
    except (OSError, ValueError, compiler.WisdomCompileError) as exc:
        parser.exit(2, f'WISDOM stack inspection failed: {exc}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
