#!/usr/bin/env python3
"""Detect accidental text-format expansion in explicitly named Git files."""

from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Sequence


def _newline_styles(raw: bytes) -> list[str]:
    styles: list[str] = []
    if b"\r\n" in raw:
        styles.append("crlf")
    without_crlf = raw.replace(b"\r\n", b"")
    if b"\n" in without_crlf:
        styles.append("lf")
    if b"\r" in without_crlf:
        styles.append("cr")
    return styles


def _normalize_newlines(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _changed_lines(before: bytes, after: bytes, *, keep_ends: bool) -> int:
    left = before.splitlines(keepends=keep_ends)
    right = after.splitlines(keepends=keep_ends)
    matcher = difflib.SequenceMatcher(None, left, right, autojunk=False)
    return sum(
        max(left_end - left_start, right_end - right_start)
        for operation, left_start, left_end, right_start, right_end in matcher.get_opcodes()
        if operation != "equal"
    )


def _safe_relative_path(value: str) -> str:
    candidate = PurePosixPath(value.replace("\\", "/"))
    if candidate.is_absolute() or not candidate.parts or ".." in candidate.parts:
        raise ValueError(f"path must stay inside the repository: {value}")
    return candidate.as_posix()


def _git_blob(repo: Path, against: str, relative_path: str) -> bytes | None:
    completed = subprocess.run(
        ["git", "-C", str(repo), "show", f"{against}:{relative_path}"],
        check=False,
        capture_output=True,
    )
    if completed.returncode == 0:
        return completed.stdout
    missing = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{against}^{{commit}}"],
        check=False,
        capture_output=True,
    )
    if missing.returncode != 0:
        raise RuntimeError(f"cannot resolve comparison revision: {against}")
    return None


def inspect_path(
    repo: Path,
    relative_path: str,
    *,
    against: str,
    allow_line_ending_change: bool,
) -> dict[str, Any]:
    current_path = repo / Path(relative_path)
    if not current_path.is_file():
        raise RuntimeError(f"changed path is not a file: {relative_path}")
    current = current_path.read_bytes()
    base = _git_blob(repo, against, relative_path)
    issues: list[str] = []
    current_styles = _newline_styles(current)
    if len(current_styles) > 1:
        issues.append("mixed_current_line_endings")
    if current.startswith(b"\xef\xbb\xbf"):
        issues.append("utf8_bom_present")

    report: dict[str, Any] = {
        "path": relative_path,
        "base_present": base is not None,
        "base_bytes": len(base) if base is not None else None,
        "current_bytes": len(current),
        "base_newlines": _newline_styles(base) if base is not None else [],
        "current_newlines": current_styles,
        "raw_changed_lines": None,
        "normalized_changed_lines": None,
        "issues": issues,
    }
    if base is None:
        return report
    if b"\0" in base or b"\0" in current:
        report["status"] = "binary_skipped"
        return report
    try:
        base.decode("utf-8", errors="strict")
        current.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        report["status"] = "non_utf8_skipped"
        return report

    normalized_base = _normalize_newlines(base)
    normalized_current = _normalize_newlines(current)
    raw_changed = _changed_lines(base, current, keep_ends=True)
    normalized_changed = _changed_lines(
        normalized_base,
        normalized_current,
        keep_ends=False,
    )
    report["raw_changed_lines"] = raw_changed
    report["normalized_changed_lines"] = normalized_changed
    if not allow_line_ending_change:
        if base != current and normalized_base == normalized_current:
            issues.append("line_endings_changed_without_semantic_change")
        if raw_changed >= 100 and raw_changed >= max(10, normalized_changed * 5):
            issues.append("raw_diff_disproportionate_to_normalized_diff")
    report["status"] = "invalid" if issues else "ok"
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--against", default="HEAD")
    parser.add_argument("--path", action="append", required=True)
    parser.add_argument("--allow-line-ending-change", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        repo = args.repo.resolve()
        paths = [_safe_relative_path(item) for item in args.path]
        allowed = {
            _safe_relative_path(item) for item in args.allow_line_ending_change
        }
        unknown_allowed = sorted(allowed - set(paths))
        if unknown_allowed:
            raise ValueError(
                "allowed line-ending paths were not inspected: "
                + ", ".join(unknown_allowed)
            )
        reports = [
            inspect_path(
                repo,
                path,
                against=args.against,
                allow_line_ending_change=path in allowed,
            )
            for path in paths
        ]
        result = {
            "schema": "wisdom.changed_text_preflight.v1",
            "against": args.against,
            "valid": all(not report["issues"] for report in reports),
            "files": reports,
        }
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0 if result["valid"] else 1
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"changed-text preflight failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
