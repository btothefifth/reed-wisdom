from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_wisdom_bundle as bundle  # noqa: E402


EXPECTED_PATHS = [
    "CHANGELOG.md",
    "README.md",
    "VERSION",
    "WISDOM.md",
    "examples/PROJECT_BOOTSTRAP.md",
    "scripts/check_changed_text.py",
    "scripts/compile_wisdom.py",
    "scripts/inspect_wisdom_stack.py",
    "scripts/load_compiled_wisdom.py",
    "scripts/setup_wisdom.py",
]


def test_archive_is_reproducible_complete_and_current(tmp_path: Path) -> None:
    first = bundle.build_archive_bytes(REPO_ROOT)
    second = bundle.build_archive_bytes(REPO_ROOT)
    assert first == second
    assert first == (REPO_ROOT / "WISDOM.zip").read_bytes()

    archive_path = tmp_path / "WISDOM.zip"
    archive_path.write_bytes(first)
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == EXPECTED_PATHS
        assert all(info.date_time == bundle.FIXED_TIMESTAMP for info in archive.infolist())
        for bundled_path, expected in bundle.read_payloads(REPO_ROOT).items():
            assert archive.read(bundled_path) == expected


def test_archive_is_reproducible_across_lf_and_crlf_checkouts(tmp_path: Path) -> None:
    root = tmp_path / "source"
    for source_path in bundle.BUNDLE_PATHS.values():
        destination = root / source_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        portable = bundle._portable_text(REPO_ROOT / source_path)
        destination.write_bytes(portable.replace(b"\n", b"\r\n"))
    assert bundle.build_archive_bytes(root) == bundle.build_archive_bytes(REPO_ROOT)


def test_check_rejects_stale_archive_after_source_change(tmp_path: Path) -> None:
    root = tmp_path / "source"
    for source_path in bundle.BUNDLE_PATHS.values():
        destination = root / source_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((REPO_ROOT / source_path).read_bytes())
    archive_path = tmp_path / "WISDOM.zip"
    archive_path.write_bytes(bundle.build_archive_bytes(root))
    (root / "WISDOM.md").write_bytes((root / "WISDOM.md").read_bytes() + b"\n")

    with pytest.raises(bundle.WisdomBundleError, match="stale"):
        bundle.check_archive(archive_path, bundle.build_archive_bytes(root))


def test_bundle_rejects_version_without_matching_changelog_entry(tmp_path: Path) -> None:
    root = tmp_path / "source"
    for source_path in bundle.BUNDLE_PATHS.values():
        destination = root / source_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((REPO_ROOT / source_path).read_bytes())
    (root / "VERSION").write_text("9.9.9\n", encoding="ascii")

    with pytest.raises(bundle.WisdomBundleError, match="CHANGELOG"):
        bundle.build_archive_bytes(root)


def test_optional_tools_document_verified_runtime_without_overclaiming() -> None:
    readme = (REPO_ROOT / bundle.BUNDLE_PATHS["README.md"]).read_text(encoding="utf-8")
    normalized = " ".join(readme.split())
    assert "tested end to end with Python 3.12.15 and 3.14.4" in normalized
    assert "hosted matrix targets Python 3.12.10" in normalized
    assert "Compatibility with earlier Python versions has not been verified" in normalized
    assert "use only the Python standard library" in normalized
    assert "Python 3.7 or newer" not in normalized


def test_clean_extraction_compiles_and_loads_verified_focused_view(tmp_path: Path) -> None:
    archive_path = tmp_path / "WISDOM.zip"
    archive_path.write_bytes(bundle.build_archive_bytes(REPO_ROOT))
    extracted = tmp_path / "extracted"
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(extracted)

    compiler = extracted / "scripts" / "compile_wisdom.py"
    loader = extracted / "scripts" / "load_compiled_wisdom.py"
    setup = extracted / "scripts" / "setup_wisdom.py"
    source = extracted / "WISDOM.md"
    cache = tmp_path / "cache"
    setup_help = subprocess.run(
        [sys.executable, str(setup), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--source" in setup_help.stdout
    discovery = subprocess.run(
        [sys.executable, str(loader), "--source", str(source), "--discover"],
        check=True,
        capture_output=True,
        text=True,
    )
    discovery_receipt = json.loads(discovery.stdout)
    assert discovery_receipt["status"] == "discovery"
    assert discovery_receipt["unknown_impact_action"] == "full_source_required"

    subprocess.run(
        [sys.executable, str(compiler), "--source", str(source), "--cache-root", str(cache)],
        check=True,
        capture_output=True,
        text=True,
    )
    loaded = subprocess.run(
        [
            sys.executable,
            str(loader),
            "--source",
            str(source),
            "--cache-root",
            str(cache),
            "--mode",
            "focused",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    plan = json.loads(loaded.stdout)
    assert plan["status"] == "compiled"
    assert plan["reason"] == "verified_current_cache"
    assert plan["module_ids"] == [
        "testing",
        "test_harness",
        "implementation_performance",
    ]
    assert plan["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert all(Path(path).is_file() for path in plan["content_paths"])


def test_extracted_t3_setup_installs_native_routers_without_provider_clis(tmp_path: Path) -> None:
    extracted = tmp_path / "portable install"
    archive_path = tmp_path / "WISDOM.zip"
    archive_path.write_bytes(bundle.build_archive_bytes(REPO_ROOT))
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(extracted)
    private_home = tmp_path / "user"
    private_home.mkdir()
    codex_home = private_home / "codex-account"
    claude_home = private_home / "claude-account"
    oc_home = private_home / "xdg" / "opencode"
    t3_state = private_home / "t3-state"
    t3_state.mkdir()
    preferences = t3_state / "preferences.json"
    preferences.write_bytes(b'{"sourceControlWritingStyle":{"customInstructions":"keep"}}\n')
    env = dict(os.environ)
    env.update(HOME=str(private_home), USERPROFILE=str(private_home), PATH="",
               CODEX_HOME=str(codex_home), CLAUDE_CONFIG_DIR=str(claude_home),
               XDG_CONFIG_HOME=str(oc_home.parent), T3CODE_HOME=str(t3_state))
    args = [str(extracted / "scripts" / "setup_wisdom.py"), "--t3", "--no-cli-probe",
            "--claude-config-home", str(claude_home), "--opencode-config-home", str(oc_home)]
    dry = subprocess.run([sys.executable, *args], env=env, input="YES\n" * 3,
                         capture_output=True, text=True, check=True, cwd=tmp_path)
    assert "T3 Code / Codex: router missing" in dry.stdout
    assert not codex_home.exists() and not claude_home.exists() and not oc_home.exists()
    # Only emulate an interactive stdin. The extracted CLI, path defaults,
    # conflict checks, consent decisions and filesystem writer remain real.
    driver = """import io, runpy, sys
class TerminalInput(io.StringIO):
    def isatty(self): return True
sys.stdin = TerminalInput('YES\\n' * 3)
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
"""
    installed = subprocess.run([sys.executable, "-c", driver, *args], env=env,
                               capture_output=True, text=True, check=True, cwd=tmp_path)
    assert "T3 Code / Codex: router present" in installed.stdout
    assert "T3 Code / Claude Code: router present" in installed.stdout
    assert "T3 Code / OpenCode: router present" in installed.stdout
    source = (extracted / "WISDOM.md").resolve().as_posix().encode()
    for target in [codex_home / "AGENTS.md", claude_home / "CLAUDE.md", oc_home / "AGENTS.md"]:
        assert source in target.read_bytes()
        assert b"load a verified view" in target.read_bytes()
        assert b"After compaction, restart, or handoff" in target.read_bytes()
    repeated = subprocess.run([sys.executable, *args], env=env, input="",
                              capture_output=True, text=True, check=True, cwd=tmp_path)
    assert repeated.stdout.count("router present at") == 3
    assert not list(private_home.rglob("*.bak"))
    assert preferences.read_bytes() == b'{"sourceControlWritingStyle":{"customInstructions":"keep"}}\n'
    assert list(t3_state.iterdir()) == [preferences]
