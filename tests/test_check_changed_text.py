from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_changed_text.py"


def _repo(tmp_path: Path, content: bytes) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "WISDOM Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "wisdom-test@example.invalid"],
        cwd=repo,
        check=True,
    )
    (repo / "sample.txt").write_bytes(content)
    subprocess.run(["git", "add", "sample.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=repo, check=True)
    return repo


def _run(repo: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            str(repo),
            "--path",
            "sample.txt",
            *extra,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_semantic_edit_with_mass_line_ending_churn_is_rejected(tmp_path: Path) -> None:
    original = b"".join(f"line {index}\r\n".encode() for index in range(180))
    repo = _repo(tmp_path, original)
    changed = b"".join(
        ("changed\n" if index == 20 else f"line {index}\n").encode()
        for index in range(180)
    )
    (repo / "sample.txt").write_bytes(changed)

    completed = _run(repo)

    assert completed.returncode == 1
    assert "raw_diff_disproportionate_to_normalized_diff" in completed.stdout


def test_real_large_edit_with_stable_line_endings_is_accepted(tmp_path: Path) -> None:
    original = b"".join(f"before {index}\n".encode() for index in range(180))
    repo = _repo(tmp_path, original)
    changed = b"".join(f"after {index}\n".encode() for index in range(180))
    (repo / "sample.txt").write_bytes(changed)

    completed = _run(repo)

    assert completed.returncode == 0, completed.stdout


def test_intentional_line_ending_conversion_requires_exact_allowance(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path, b"alpha\r\nbeta\r\n")
    (repo / "sample.txt").write_bytes(b"alpha\nbeta\n")

    rejected = _run(repo)
    allowed = _run(repo, "--allow-line-ending-change", "sample.txt")

    assert rejected.returncode == 1
    assert "line_endings_changed_without_semantic_change" in rejected.stdout
    assert allowed.returncode == 0, allowed.stdout


def test_mixed_current_line_endings_are_rejected(tmp_path: Path) -> None:
    repo = _repo(tmp_path, b"alpha\nbeta\n")
    (repo / "sample.txt").write_bytes(b"alpha\r\nbeta\n")

    completed = _run(repo)

    assert completed.returncode == 1
    assert "mixed_current_line_endings" in completed.stdout


def test_tracked_utf8_text_becoming_utf16_is_rejected(tmp_path: Path) -> None:
    repo = _repo(tmp_path, b"alpha\nbeta\n")
    (repo / "sample.txt").write_text("alpha\nbeta\n", encoding="utf-16")

    completed = _run(repo)

    assert completed.returncode == 1
    assert "tracked_utf8_text_became_binary_or_non_utf8" in completed.stdout


def test_option_shaped_revision_is_rejected_before_git(tmp_path: Path) -> None:
    repo = _repo(tmp_path, b"alpha\nbeta\n")

    completed = _run(repo, "--against=--quiet")

    assert completed.returncode == 2
    assert "comparison revision is invalid" in completed.stderr


def test_windows_drive_path_is_rejected(tmp_path: Path) -> None:
    repo = _repo(tmp_path, b"alpha\nbeta\n")
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            str(repo),
            "--path",
            r"C:\Windows\win.ini",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "path must stay inside the repository" in completed.stderr
