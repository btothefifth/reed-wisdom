"""Execute authored examples and targeted defects; never download a toolchain.

These prove selected language semantics, not model compliance or all library rules.
The test oracles come from the referenced language/runtime contracts.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import compile_wisdom as compiler


@pytest.fixture(scope='module')
def authored():
    return compiler.parse_source(ROOT / 'WISDOM.md')


def example(authored, section, name, language):
    body = authored.section_by_id[section].body.decode()
    matches = re.findall(r'<!-- wisdom-example: ' + re.escape(name) + r' -->\n```'
                         + re.escape(language) + r'\n(.*?)\n```', body, re.S)
    assert len(matches) == 1, f'missing or duplicated authored example: {name}'
    return matches[0] + '\n'


def run_python(tmp_path, source, harness):
    path = tmp_path / 'example.py'
    path.write_text(source + '\n' + harness)
    return subprocess.run([sys.executable, '-I', str(path)], capture_output=True,
                          text=True, timeout=10)


@pytest.mark.skipif(sys.version_info < (3, 13), reason='Queue.shutdown requires Python 3.13+')
def test_authored_queue_drains_and_immediate_shutdown_goes_red(authored, tmp_path):
    source = example(authored, 'python_asyncio', 'python_queue_drain', 'python')
    harness = '''assert asyncio.run(drain_values()) == [1, 2], "accepted values were discarded"
print("queue:ok")
'''
    good = run_python(tmp_path, source, harness)
    assert good.returncode == 0, good.stderr
    assert good.stdout == 'queue:ok\n'
    assert source.count('queue.shutdown()') == 1
    bad = run_python(tmp_path, source.replace('queue.shutdown()', 'queue.shutdown(immediate=True)'), harness)
    assert bad.returncode != 0
    assert 'AssertionError: accepted values were discarded' in bad.stderr


def test_authored_sqlite_initialization_enforces_integrity_and_wrong_order_goes_red(authored, tmp_path):
    source = example(authored, 'sqlite', 'python_sqlite_initialization', 'python')
    harness = '''connection = open_connection(":memory:")
try:
    assert connection.autocommit is False
    connection.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
    connection.execute("CREATE TABLE child (parent_id INTEGER REFERENCES parent(id))")
    connection.execute("INSERT INTO parent VALUES (1)")
    with connection:
        connection.execute("INSERT INTO child VALUES (1)")
    try:
        connection.execute("INSERT INTO child VALUES (999)")
    except sqlite3.IntegrityError:
        connection.rollback()
    else:
        raise AssertionError("foreign-key violation accepted")
    assert connection.execute("SELECT parent_id FROM child").fetchall() == [(1,)]
    # The transaction context did not close the connection; its caller still owns it.
finally:
    connection.close()
try:
    connection.execute("SELECT 1")
except sqlite3.ProgrammingError:
    pass
else:
    raise AssertionError("connection was not closed")
print("sqlite:ok")
'''
    good = run_python(tmp_path, source, harness)
    assert good.returncode == 0, good.stderr
    assert good.stdout == 'sqlite:ok\n'
    assert source.count('database, autocommit=True') == 1
    failed_initialization = '''created = []
connect = sqlite3.connect
def observed_connect(*args, **kwargs):
    connection = connect(*args, **kwargs)
    created.append(connection)
    return connection
sqlite3.connect = observed_connect
try:
    open_connection(":memory:")
except RuntimeError:
    try:
        created[0].execute("SELECT 1")
    except sqlite3.ProgrammingError:
        pass
    else:
        raise AssertionError("initialization leaked its connection")
    raise
else:
    raise AssertionError("invalid initialization was accepted")
'''
    wrong_order = source.replace('database, autocommit=True', 'database, autocommit=False')
    bad = run_python(tmp_path, wrong_order, failed_initialization)
    assert bad.returncode != 0
    assert 'RuntimeError: foreign-key enforcement unavailable' in bad.stderr
    assert 'AssertionError' not in bad.stderr
    leaked = run_python(tmp_path, wrong_order.replace('connection.close()', 'pass'), failed_initialization)
    assert leaked.returncode != 0
    assert 'AssertionError: initialization leaked its connection' in leaked.stderr


def native_tool(name, minimum):
    path = shutil.which(name)
    if path is None:
        pytest.skip(f'{name} is not installed; no toolchain downloaded')
    probe = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=10)
    assert probe.returncode == 0, f'{path} version probe failed: {probe.stderr}'
    match = re.search(r'\b(?:v)?(\d+)\.(\d+)\.(\d+)', probe.stdout)
    assert match, f'unrecognized {name} version: {probe.stdout}'
    if tuple(map(int, match.groups())) < minimum:
        pytest.skip(f'{path}: {probe.stdout.strip()} is below required {minimum}')
    return path


def test_authored_rust_capture_compiles_and_overcapture_goes_red(authored, tmp_path):
    rustc = native_tool('rustc', (1, 85, 0))
    source = example(authored, 'rust_api', 'rust_precise_capture', 'rust')
    path = tmp_path / 'capture.rs'
    output = tmp_path / ('capture.exe' if sys.platform == 'win32' else 'capture')
    command = [rustc, '--edition=2024', '--error-format=json', str(path), '-o', str(output)]
    path.write_text(source)
    good = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert good.returncode == 0, good.stderr
    ran = subprocess.run([str(output)], capture_output=True, text=True, timeout=10)
    assert ran.returncode == 0, ran.stderr
    assert source.count(' + use<>') == 1
    path.write_text(source.replace(' + use<>', ''))
    bad = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert bad.returncode != 0
    errors = [json.loads(line) for line in bad.stderr.splitlines() if line.startswith('{')]
    assert any(item.get('code') and item['code']['code'] == 'E0505' for item in errors), bad.stderr


def test_authored_rust_generic_caller_needs_the_public_future_bound(authored, tmp_path):
    rustc = native_tool('rustc', (1, 75, 0))
    source = example(authored, 'rust_api', 'rust_async_trait_send', 'rust')
    path = tmp_path / 'future.rs'
    command = [rustc, '--edition=2021', '--crate-type=lib', '--emit=metadata', '--error-format=json',
               str(path), '-o', str(tmp_path / 'future.rmeta')]
    path.write_text(source)
    good = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert good.returncode == 0, good.stderr
    signature = 'fn run(&self) -> impl Future<Output = ()> + Send;'
    assert source.count(signature) == 1
    path.write_text(source.replace(signature, 'fn run(&self) -> impl Future<Output = ()>;'))
    bad = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert bad.returncode != 0
    errors = [json.loads(line) for line in bad.stderr.splitlines() if line.startswith('{')]
    assert any(item.get('code') and item['code']['code'] == 'E0277' for item in errors), bad.stderr


def test_authored_node_context_isolated_and_enter_with_leak_goes_red(authored, tmp_path):
    node = native_tool('node', (16, 4, 0))
    source = example(authored, 'node', 'node_request_context', 'javascript')
    harness = '''import assert from 'node:assert/strict';
let releaseFirst, releaseSecond;
const firstGate = new Promise(resolve => { releaseFirst = resolve; });
const secondGate = new Promise(resolve => { releaseSecond = resolve; });
const first = withRequest('first', async () => {
    await firstGate;
    return requests.getStore().requestId;
});
const second = withRequest('second', async () => {
    await secondGate;
    return requests.getStore().requestId;
});
releaseSecond();
assert.equal(await second, 'second');
releaseFirst();
assert.equal(await first, 'first');
assert.equal(requests.getStore(), undefined, 'request context leaked to the caller');
console.log('node:ok');
'''
    path = tmp_path / 'context.mjs'
    path.write_text(source + harness)
    good = subprocess.run([node, str(path)], capture_output=True, text=True, timeout=10)
    assert good.returncode == 0, good.stderr
    assert good.stdout == 'node:ok\n'
    call = 'return requests.run(Object.freeze({ requestId }), work);'
    assert source.count(call) == 1
    path.write_text(source.replace(call, 'requests.enterWith(Object.freeze({ requestId })); return work();') + harness)
    bad = subprocess.run([node, str(path)], capture_output=True, text=True, timeout=10)
    assert bad.returncode != 0
    assert 'request context leaked to the caller' in bad.stderr
