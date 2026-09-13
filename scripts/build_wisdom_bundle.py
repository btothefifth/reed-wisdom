#!/usr/bin/env python3
"""Build or check the deterministic standalone WISDOM.zip archive."""

from __future__ import annotations

import argparse
import io
import re
import sys
import zipfile
from pathlib import Path
from typing import Mapping, Sequence


ARCHIVE_NAME = "WISDOM.zip"
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
BUNDLE_PATHS = {
    "CHANGELOG.md": Path("CHANGELOG.md"),
    "README.md": Path("docs/wisdom-portable/README.md"),
    "VERSION": Path("VERSION"),
    "WISDOM.md": Path("WISDOM.md"),
    "scripts/compile_wisdom.py": Path("scripts/compile_wisdom.py"),
    "scripts/check_changed_text.py": Path("scripts/check_changed_text.py"),
    "scripts/load_compiled_wisdom.py": Path("scripts/load_compiled_wisdom.py"),
}


class WisdomBundleError(RuntimeError):
    """The portable archive cannot be built or does not match its sources."""


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _portable_text(path: Path) -> bytes:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise WisdomBundleError(f"cannot read bundle source {path}: {exc}") from exc
    if raw.startswith(b"\xef\xbb\xbf"):
        raise WisdomBundleError(f"bundle source must be UTF-8 without BOM: {path}")
    without_crlf = raw.replace(b"\r\n", b"")
    if b"\r" in without_crlf:
        raise WisdomBundleError(f"bundle source contains a bare carriage return: {path}")
    try:
        raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise WisdomBundleError(f"bundle source is not strict UTF-8: {path}") from exc
    return raw.replace(b"\r\n", b"\n")


def read_payloads(root: Path) -> Mapping[str, bytes]:
    payloads: dict[str, bytes] = {}
    for archive_path, source_path in BUNDLE_PATHS.items():
        payloads[archive_path] = _portable_text(root / source_path)
    if not payloads["WISDOM.md"].startswith(b"# WISDOM:"):
        raise WisdomBundleError("WISDOM.md does not have the expected standalone heading")
    if b"WISDOM.md` is the sole authored authority" not in payloads["README.md"]:
        raise WisdomBundleError("portable README does not preserve WISDOM.md authority")
    version = payloads["VERSION"].decode("ascii").strip()
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None:
        raise WisdomBundleError("VERSION must contain one semantic version")
    if f"## {version} - ".encode("ascii") not in payloads["CHANGELOG.md"]:
        raise WisdomBundleError("CHANGELOG.md has no entry for VERSION")
    return payloads


def build_archive_bytes(root: Path) -> bytes:
    payloads = read_payloads(root)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for archive_path in sorted(payloads):
            info = zipfile.ZipInfo(archive_path, date_time=FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payloads[archive_path])
    return stream.getvalue()


def check_archive(archive_path: Path, expected: bytes) -> None:
    try:
        actual = archive_path.read_bytes()
    except OSError as exc:
        raise WisdomBundleError(f"cannot read {archive_path}: {exc}") from exc
    if actual != expected:
        raise WisdomBundleError(
            f"{archive_path.name} is stale; run scripts/build_wisdom_bundle.py"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if WISDOM.zip is stale")
    parser.add_argument("--output", type=Path, help="archive destination (default: repo WISDOM.zip)")
    args = parser.parse_args(argv)
    root = _repository_root()
    output = args.output.resolve() if args.output else root / ARCHIVE_NAME
    try:
        expected = build_archive_bytes(root)
        if args.check:
            check_archive(output, expected)
            print(f"current: {output}")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(expected)
            print(f"wrote: {output}")
    except WisdomBundleError as exc:
        print(f"wisdom bundle failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
