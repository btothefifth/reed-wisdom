#!/usr/bin/env python3
"""Optional, consent-gated Codex setup for this exact WISDOM installation.

This tool reads only its WISDOM source, the effective global instruction file,
Codex config, and optional schema/model evidence. It never installs defaults.
"""

from __future__ import annotations

import argparse
import contextlib
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path
from typing import Callable


KEYS = (
    "model_context_window",
    "model_auto_compact_token_limit",
    "project_doc_max_bytes",
    "features.context_management",
    "features.code_mode.enabled",
    "agents.enabled",
    "agents.max_concurrent_threads_per_session",
)
ASSIGN_RE = re.compile(r"^\s*([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)\s*=\s*([0-9]+|true|false)\s*$")
SECTION_RE = re.compile(r"^\s*\[([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)\]\s*$")
_UNSET = object()


class SetupError(Exception):
    """A setup change cannot be proved safe."""


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_existing(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


def effective_agents(home: Path) -> tuple[Path, bytes | None]:
    override = home / "AGENTS.override.md"
    base = home / "AGENTS.md"
    override_raw = read_existing(override)
    base_raw = read_existing(base)
    if override_raw is not None and override_raw.strip():
        return override, override_raw
    if base_raw is not None and base_raw.strip():
        return base, base_raw
    # An empty override does not shadow a new, nonempty base file.
    return base, base_raw


def guidance(source: Path) -> bytes:
    resolved = source.resolve(strict=True)
    if resolved.name != "WISDOM.md" or not resolved.is_file():
        raise SetupError("source must be an existing WISDOM.md file")
    location = resolved.as_posix()
    if any(char in location for char in "`\r\n"):
        raise SetupError("source path cannot be represented safely")
    return (
        "## WISDOM operating kernel\n\n"
        f"For each task, load a verified view of `{location}` using this "
        "installation's loader when practical, then read and follow it proportionately. "
        "Explicit current instructions and verified facts take precedence. "
        "If a compiled view is unavailable or uncertain, read the full current source.\n"
    ).encode("utf-8")


def has_equivalent_guidance(raw: bytes, source: Path) -> bool:
    try:
        content = raw.decode("utf-8").replace("\\", "/").casefold()
    except UnicodeDecodeError as exc:
        raise SetupError("effective AGENTS file is not UTF-8") from exc
    location = source.resolve(strict=True).as_posix().casefold()
    for paragraph in re.split(r"\n\s*\n", content):
        if _positive_source_directive(paragraph, location):
            return True
    return False


def _positive_source_directive(paragraph: str, location: str) -> bool:
    if re.search(r"\b(former|obsolete|retired|deprecated|instead|migration|historical|archived)\b", paragraph):
        return False
    # Bare "read" often describes historical or migration context. Requiring
    # load/follow avoids treating a mention of this path as active guidance.
    pattern = r"\b(?:read\s+and\s+follow|load|follow)\b[^.!?]{0,120}" + re.escape(location)
    match = re.search(pattern, paragraph)
    return bool(match and not re.search(r"\b(?:do not|never|stop|avoid)\b", match.group()))


def proposed_agents(raw: bytes | None, source: Path) -> bytes | None:
    old = raw or b""
    if has_equivalent_guidance(old, source):
        return None
    try:
        existing = old.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SetupError("effective AGENTS file is not UTF-8") from exc
    normalized = existing.replace("\\", "/").casefold()
    if any(
        _positive_source_directive(paragraph, match.group())
        for paragraph in re.split(r"\n\s*\n", normalized)
        for match in re.finditer(r"(?:[a-z]:)?[^\s`'\"]*wisdom\.md", paragraph)
    ):
        raise SetupError("effective AGENTS file has different WISDOM guidance; manual review required")
    if b"\r\n" in old and b"\n" in old.replace(b"\r\n", b""):
        raise SetupError("effective AGENTS file has mixed line endings")
    sep = b"\r\n" if b"\r\n" in old else b"\n"
    addition = guidance(source).replace(b"\n", sep)
    prefix = sep * (2 if old and not old.endswith((b"\n", b"\r")) else 1) if old else b""
    return old + prefix + addition


def _value(config: dict, path: str):
    current = config
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _resolve_schema_ref(schema: dict, current: object) -> dict | None:
    seen: set[str] = set()
    for _ in range(8):
        if not isinstance(current, dict):
            return None
        ref = current.get("$ref")
        if ref is None:
            return current
        if not isinstance(ref, str) or not ref.startswith("#/") or ref in seen:
            return None
        seen.add(ref)
        current = schema
        for token in ref[2:].split("/"):
            if not isinstance(current, dict):
                return None
            current = current.get(token.replace("~1", "/").replace("~0", "~"))
    return None


def _schema_info(schema: dict | None, path: str) -> tuple[bool | None, dict | None]:
    if schema is None:
        return None, None
    current = schema
    parts = path.split(".")
    for index, part in enumerate(parts):
        current = _resolve_schema_ref(schema, current)
        if current is None:
            return None, None
        if "allOf" in current or "oneOf" in current:
            return None, None
        props = current.get("properties", {})
        if not isinstance(props, dict):
            return None, None
        if part not in props:
            return (False, None) if current.get("additionalProperties") is False else (None, None)
        current = props[part]
        if index < len(parts) - 1 and isinstance(current, dict) and "anyOf" in current:
            objects = [item for item in current["anyOf"] if isinstance(item, dict) and ("properties" in item or "$ref" in item)]
            if len(objects) == 1:
                current = objects[0]
            elif len(objects) > 1:
                return None, None
    return True, _resolve_schema_ref(schema, current)


def _schema_value_valid(leaf: dict | None, value: object) -> bool | None:
    """Validate only simple, explicit JSON-schema constraints; unknown stays unknown."""
    if not leaf or any(key in leaf for key in ("allOf", "oneOf", "anyOf", "not", "if")):
        return None
    types = leaf.get("type")
    if types is None:
        return None
    if isinstance(types, str):
        types = [types]
    if not isinstance(types, list) or not all(isinstance(item, str) for item in types):
        return None
    predicates = {
        "boolean": lambda x: type(x) is bool,
        "integer": lambda x: type(x) is int,
        "number": lambda x: type(x) in (int, float),
        "string": lambda x: isinstance(x, str),
        "object": lambda x: isinstance(x, dict),
        "array": lambda x: isinstance(x, list),
        "null": lambda x: x is None,
    }
    if any(item not in predicates for item in types):
        return None
    if not any(predicates[item](value) for item in types):
        return False
    supported = {
        "type", "const", "enum", "minimum", "maximum", "exclusiveMinimum",
        "exclusiveMaximum", "title", "description", "default", "examples",
        "$comment", "$id", "$schema", "deprecated", "readOnly", "writeOnly",
    }
    if any(key not in supported for key in leaf):
        return None
    if "const" in leaf and (type(value) is not type(leaf["const"]) or value != leaf["const"]):
        return False
    if "enum" in leaf:
        choices = leaf["enum"]
        if not isinstance(choices, list):
            return None
        if not any(type(value) is type(choice) and value == choice for choice in choices):
            return False
    if type(value) in (int, float):
        for constraint, operation in (
            ("minimum", lambda a, b: a >= b),
            ("maximum", lambda a, b: a <= b),
            ("exclusiveMinimum", lambda a, b: a > b),
            ("exclusiveMaximum", lambda a, b: a < b),
        ):
            bound = leaf.get(constraint)
            if bound is not None:
                if type(bound) not in (int, float):
                    return None
                if not operation(value, bound):
                    return False
    return True


def _model_limit(catalog: dict | None, model: str | None) -> int | None:
    if not catalog or not model:
        return None
    entries = catalog.get("models", catalog)
    if isinstance(entries, dict):
        entries = [dict(value, slug=key) for key, value in entries.items() if isinstance(value, dict)]
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if model not in (entry.get("slug"), entry.get("id"), entry.get("model")):
            continue
        limit = entry.get("context_window", entry.get("contextWindow"))
        return limit if type(limit) is int and limit > 0 else None
    return None


def _parse_json(path: Path | None, *, required: bool = False) -> dict | None:
    if path is None:
        return None
    if not path.is_file():
        if required:
            raise SetupError("explicit JSON evidence file is unavailable")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        if required:
            raise SetupError("explicit JSON evidence file is invalid") from None
        return None
    if not isinstance(value, dict):
        if required:
            raise SetupError("explicit JSON evidence must be an object")
        return None
    return value


def cli_version() -> str | None:
    binary = shutil.which("codex")
    if not binary:
        return None
    try:
        result = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = re.search(r"\bcodex-cli\s+([0-9][A-Za-z0-9.+-]*)", result.stdout)
    return match.group(1) if result.returncode == 0 and match else None


def _remove_scalar_line(raw: bytes, key: str) -> bytes:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SetupError("config.toml is not UTF-8") from exc
    lines = text.splitlines(keepends=True)
    section = ""
    matches: list[int] = []
    for index, line in enumerate(lines):
        body = line.rstrip("\r\n")
        section_match = SECTION_RE.fullmatch(body)
        if section_match:
            section = section_match.group(1)
            continue
        assign = ASSIGN_RE.fullmatch(body)
        if assign and ".".join(filter(None, (section, assign.group(1)))) == key:
            matches.append(index)
    if len(matches) != 1:
        raise SetupError(f"cannot safely isolate {key} as one simple scalar line")
    del lines[matches[0]]
    candidate = "".join(lines).encode("utf-8")
    try:
        parsed = tomllib.loads(candidate.decode("utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise SetupError(f"removing {key} would make TOML invalid") from exc
    if _value(parsed, key) is not None:
        raise SetupError(f"removing {key} did not clear its effective value")
    return candidate


def config_diagnostics(raw: bytes | None, schema: dict | None, catalog: dict | None) -> tuple[list[tuple[str, str]], dict[str, bytes]]:
    if raw is None:
        return [(key, "absent; no default proposed") for key in KEYS], {}
    try:
        config = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise SetupError("config.toml cannot be parsed safely") from exc
    model = config.get("model") if isinstance(config.get("model"), str) else None
    local_provider = config.get("model_provider")
    profile_selected = config.get("profile") is not None
    cap = _model_limit(catalog, model) if not profile_selected and local_provider in (None, "openai") else None
    findings: list[tuple[str, str]] = []
    proposals: dict[str, bytes] = {}
    for key in KEYS:
        value = _value(config, key)
        if value is None:
            findings.append((key, "absent; no default proposed"))
            continue
        known, leaf = _schema_info(schema, key)
        schema_valid = _schema_value_valid(leaf, value) if known is True else None
        if known is False:
            status = "unsupported by supplied schema; removal available"
        elif schema_valid is False:
            status = "conflicts with supplied schema value constraints; removal available"
        elif key in ("model_context_window", "model_auto_compact_token_limit") and cap is not None and type(value) is int and value > cap:
            status = f"conflicts with selected model's catalog window ({cap}); removal available"
        elif known is True and schema_valid is None:
            status = "schema-presence-only; value support remains unverified"
        elif known is True and key in ("project_doc_max_bytes", "features.context_management", "features.code_mode.enabled", "agents.enabled", "agents.max_concurrent_threads_per_session"):
            status = "schema-recognized; effective support or resource impact remains environment-dependent"
        elif known is True and cap is not None and type(value) is int and value <= cap:
            status = "valid against supplied schema and selected model catalog window; effective behavior requires fresh-session verification"
        elif known is True:
            status = "schema-recognized; model limit unverified"
        else:
            status = "environment-dependent; no supported remediation evidence"
        findings.append((key, status))
        if "removal available" in status:
            try:
                proposals[key] = _remove_scalar_line(raw, key)
            except SetupError:
                findings[-1] = (key, status.replace("; removal available", "; manual review required"))
    return findings, proposals


def _instruction_limit(config_raw: bytes | None) -> int:
    if config_raw is None:
        return 32768
    parsed = tomllib.loads(config_raw.decode("utf-8"))
    configured = parsed.get("project_doc_max_bytes")
    return configured if type(configured) is int and configured > 0 else 32768


@contextlib.contextmanager
def _setup_lock(home: Path):
    """Serialize cooperating installer writers; never reclaim another lock."""
    home.mkdir(parents=True, exist_ok=True)
    lock = home / ".setup-wisdom.lock"
    deadline = time.monotonic() + 2.0
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise SetupError("another setup writer holds the lock; retry later") from None
            time.sleep(0.05)
    try:
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink(missing_ok=True)


def _commit(path: Path, old: bytes | None, new: bytes) -> None:
    with _setup_lock(path.parent):
        if read_existing(path) != old:
            raise SetupError(f"{path.name} changed after preview; retry setup")
        if old is not None:
            backup = path.with_name(f"{path.name}.before-wisdom-{digest(old)[:16]}.bak")
            if backup.exists() and backup.read_bytes() != old:
                raise SetupError("existing backup name has different contents")
            if not backup.exists():
                _atomic_bytes(backup, old, mode=path.stat().st_mode)
        _atomic_bytes(path, new, mode=path.stat().st_mode if path.exists() else None, expected_target=old)
        if path.read_bytes() != new:
            raise SetupError(f"{path.name} verification failed")


def _atomic_bytes(path: Path, raw: bytes, *, mode: int | None, expected_target: bytes | None | object = _UNSET) -> None:
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if mode is not None:
            os.chmod(name, mode)
        # A second comparison narrows the uncooperative-writer race immediately
        # before replacement. Portable stdlib filesystems offer no atomic CAS.
        if expected_target is not _UNSET and read_existing(path) != expected_target:
            raise SetupError(f"{path.name} changed during write; retry setup")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _approve(input_func: Callable[[str], str], target: Path) -> bool:
    try:
        return input_func(f"Apply only this exact change to {target}? Type YES: ").strip() == "YES"
    except (EOFError, KeyboardInterrupt):
        return False


def run_setup(
    source: Path,
    home: Path,
    *,
    schema_path: Path | None = None,
    catalog_path: Path | None = None,
    interactive: bool = False,
    input_func: Callable[[str], str] = input,
    output: Callable[[str], None] = print,
    probe_cli: bool = True,
) -> None:
    source = source.resolve(strict=True)
    home = home.expanduser().resolve()
    agent_path, old_agents = effective_agents(home)
    new_agents = proposed_agents(old_agents, source)
    config_path = home / "config.toml"
    config_raw = read_existing(config_path)
    schema = _parse_json(schema_path, required=schema_path is not None)
    catalog = _parse_json(catalog_path, required=catalog_path is not None)
    findings, proposals = config_diagnostics(config_raw, schema, catalog)
    output(f"WISDOM source: {source}")
    output(f"Effective global instruction target: {agent_path}")
    if new_agents is None:
        output("AGENTS guidance: equivalent source-specific loading instruction already present.")
    elif len(new_agents) > _instruction_limit(config_raw):
        output("AGENTS guidance exceeds this config's instruction byte limit; no edit proposed. Review the effective limit and instruction chain manually.")
    else:
        output(f"AGENTS exact delta: before sha256={digest(old_agents or b'')}; after sha256={digest(new_agents)}")
        appended = new_agents[len(old_agents or b""):]
        output(f"Append exact UTF-8 bytes: {appended!r}")
        for line in appended.decode("utf-8").splitlines():
            output(f"+ {line}")
        if interactive and _approve(input_func, agent_path):
            _commit(agent_path, old_agents, new_agents)
            output("AGENTS guidance written and verified. Verify in a fresh Codex session.")
        else:
            output("AGENTS guidance skipped; no instruction-file write.")
    version = cli_version() if probe_cli else None
    output(f"Codex CLI version: {version or 'unavailable'}; local schema: {'available' if schema else 'unavailable'}; model catalog: {'available' if catalog else 'unavailable'}.")
    output("Diagnostics cover this CODEX_HOME config only; active CLI flags, profiles, project layers, and fresh-session behavior require separate verification.")
    expected_config = config_raw
    for key, status in findings:
        output(f"{key}: {status}")
        if key not in proposals:
            continue
        current = read_existing(config_path)
        if current is None or current != expected_config:
            raise SetupError("config.toml changed after diagnostics; retry setup")
        candidate = _remove_scalar_line(current, key)
        if candidate == current:
            continue
        output(f"Config exact delta for {key} in {config_path}: before sha256={digest(current)}; after sha256={digest(candidate)}")
        delta = list(difflib.unified_diff(current.decode("utf-8").splitlines(), candidate.decode("utf-8").splitlines(), n=0))
        for line in delta:
            if line.startswith("-") and not line.startswith("---"):
                output(line)
        if interactive and _approve(input_func, config_path):
            _commit(config_path, current, candidate)
            expected_config = candidate
            output(f"{key}: removed and verified. Verify effective config in a fresh Codex session.")
        else:
            output(f"{key}: skipped; no config write.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1] / "WISDOM.md")
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex"))
    parser.add_argument("--schema", type=Path, help="optional local installed Codex JSON schema")
    parser.add_argument("--model-catalog", type=Path, help="optional local installed model catalog JSON")
    parser.add_argument("--no-cli-probe", action="store_true")
    args = parser.parse_args(argv)
    try:
        run_setup(args.source, args.codex_home, schema_path=args.schema, catalog_path=args.model_catalog,
                  interactive=sys.stdin.isatty(), probe_cli=not args.no_cli_probe)
    except (OSError, SetupError) as exc:
        print(f"Setup stopped: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
