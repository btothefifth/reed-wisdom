#!/usr/bin/env python3
"""Compile WISDOM.md into deterministic, non-authorizing exact-byte views."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SOURCE_SCHEMA = "wisdom.portable_bootstrap.source.v1"
COMPILED_SCHEMA = "wisdom.compiled.cache.v1"
CURRENT_SCHEMA = "wisdom.compiled.current.v1"
VIEW_SCHEMA = "wisdom.compiled.view.v1"
ANCHOR_SCHEMA = "wisdom.compiled.anchor_index.v1"
IDENTITY_SCHEMA = "wisdom.compiled.identity.v1"
COMPILE_RECEIPT_SCHEMA = "wisdom.compile.receipt.v1"

BEGIN_LINE = b"<!-- WISDOM-MANIFEST-BEGIN"
END_LINE = b"WISDOM-MANIFEST-END -->"
SAFE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
SOURCE_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")
RULE_ID_RE = re.compile(rb"\b[A-Z][A-Z0-9]+-[0-9]{2}\b")
HEADING_RE = re.compile(rb"(?m)^## ([^\r\n]+)\r?$")

SOURCE_KEYS = {
    "schema",
    "source_id",
    "semantic_revision",
    "encoding",
    "newline_policy",
    "kernel_max_bytes",
    "fallback",
    "allowed_tags",
    "kernel_sections",
    "kernel_tags",
    "task_profiles",
    "sections",
    "modules",
    "views",
}
SECTION_KEYS = {"id", "heading", "rule_ids"}
MODULE_KEYS = {"id", "sections", "tags", "requires"}
VIEW_KEYS = {"mode", "required_modules", "source_direct"}
TASK_PROFILE_KEYS = {"id", "mode", "tags"}
EXPECTED_MODES = ("fast", "focused", "substantial", "full")


class WisdomCompileError(RuntimeError):
    """A fail-closed source, compiler, cache, or provenance violation."""


@dataclass(frozen=True)
class SectionSlice:
    section_id: str
    heading: str
    body: bytes
    rule_ids: tuple[str, ...]
    ordinal: int


@dataclass(frozen=True)
class ParsedWisdom:
    source_path: Path
    raw: bytes
    source_sha256: str
    newline: bytes
    manifest: Mapping[str, Any]
    manifest_sha256: str
    preamble: bytes
    sections: tuple[SectionSlice, ...]
    section_by_id: Mapping[str, SectionSlice]
    module_by_id: Mapping[str, Mapping[str, Any]]
    module_order: tuple[str, ...]
    section_owner: Mapping[str, tuple[str, str]]
    view_by_mode: Mapping[str, Mapping[str, Any]]
    kernel: bytes


@dataclass(frozen=True)
class CompiledArtifacts:
    build_id: str
    identity: Mapping[str, Any]
    payloads: Mapping[str, bytes]
    output_receipts: tuple[Mapping[str, Any], ...]
    tree_sha256: str
    manifest_body: Mapping[str, Any]
    manifest_bytes: bytes
    manifest_sha256: str
    manifest_body_sha256: str
    current_bytes: bytes


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _strict_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise WisdomCompileError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise WisdomCompileError(f"non-JSON numeric constant: {value}")


def strict_json_loads(raw: bytes, *, label: str) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WisdomCompileError(f"invalid {label}: {exc}") from exc


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise WisdomCompileError(f"{label} keys mismatch; missing={missing}, extra={extra}")


def _require_list_of_unique_strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise WisdomCompileError(f"{label} must be a list of strings")
    if len(value) != len(set(value)):
        raise WisdomCompileError(f"{label} contains duplicates")
    return value


def _require_safe_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or SAFE_ID_RE.fullmatch(value) is None:
        raise WisdomCompileError(f"{label} is not a safe identifier")
    return value


def _filesystem_path(path: Path) -> Path:
    raw = os.path.abspath(os.fspath(path))
    if os.name != "nt" or raw.startswith("\\\\?\\"):
        return Path(raw)
    if raw.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + raw[2:])
    return Path("\\\\?\\" + raw)


def _stable_read(path: Path) -> bytes:
    filesystem_path = _filesystem_path(path)
    try:
        before = filesystem_path.stat()
        first = filesystem_path.read_bytes()
        middle = filesystem_path.stat()
        second = filesystem_path.read_bytes()
        after = filesystem_path.stat()
    except OSError as exc:
        raise WisdomCompileError(f"cannot read {path}: {exc}") from exc
    metadata = (
        before.st_size,
        before.st_mtime_ns,
        middle.st_size,
        middle.st_mtime_ns,
        after.st_size,
        after.st_mtime_ns,
    )
    if first != second or metadata[:2] != metadata[2:4] or metadata[2:4] != metadata[4:]:
        raise WisdomCompileError(f"source changed while reading: {path}")
    return first


def _newline_for(raw: bytes) -> bytes:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise WisdomCompileError("WISDOM.md must be UTF-8 without BOM")
    try:
        raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise WisdomCompileError(f"WISDOM.md is not strict UTF-8: {exc}") from exc
    without_crlf = raw.replace(b"\r\n", b"")
    if b"\r" in without_crlf:
        raise WisdomCompileError("WISDOM.md contains a bare carriage return")
    has_crlf = b"\r\n" in raw
    has_bare_lf = b"\n" in without_crlf
    if has_crlf and has_bare_lf:
        raise WisdomCompileError("WISDOM.md contains mixed newline styles")
    return b"\r\n" if has_crlf else b"\n"


def _validate_graph(modules: Sequence[Mapping[str, Any]], module_ids: set[str]) -> None:
    graph = {module["id"]: tuple(module["requires"]) for module in modules}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(module_id: str) -> None:
        if module_id in visiting:
            raise WisdomCompileError(f"module dependency cycle at {module_id}")
        if module_id in visited:
            return
        visiting.add(module_id)
        for dependency in graph[module_id]:
            if dependency not in module_ids:
                raise WisdomCompileError(
                    f"module {module_id} requires unknown module {dependency}"
                )
            visit(dependency)
        visiting.remove(module_id)
        visited.add(module_id)

    for module_id in graph:
        visit(module_id)


def parse_source(source_path: Path | str) -> ParsedWisdom:
    path = Path(source_path).resolve()
    raw = _stable_read(path)
    newline = _newline_for(raw)
    begin_line = BEGIN_LINE + newline
    end_line = END_LINE + newline
    if raw.count(BEGIN_LINE) != 1 or raw.count(END_LINE) != 1:
        raise WisdomCompileError("manifest sentinels must each occur exactly once")
    begin_at = raw.find(begin_line)
    if begin_at < 0:
        raise WisdomCompileError("manifest begin sentinel must occupy its own line")
    manifest_at = begin_at + len(begin_line)
    end_at = raw.find(end_line, manifest_at)
    if end_at < 0:
        raise WisdomCompileError("manifest end sentinel must occupy its own line")
    manifest_raw = raw[manifest_at:end_at]
    manifest = strict_json_loads(manifest_raw, label="embedded WISDOM manifest")
    if not isinstance(manifest, dict):
        raise WisdomCompileError("embedded WISDOM manifest must be an object")
    _require_exact_keys(manifest, SOURCE_KEYS, "source manifest")
    if manifest["schema"] != SOURCE_SCHEMA:
        raise WisdomCompileError(f"unsupported source schema: {manifest['schema']!r}")
    source_id = manifest["source_id"]
    if not isinstance(source_id, str) or SOURCE_ID_RE.fullmatch(source_id) is None:
        raise WisdomCompileError("source_id must contain only lowercase letters, digits, and hyphens")
    revision = manifest["semantic_revision"]
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise WisdomCompileError("semantic_revision must be a positive integer")
    if manifest["encoding"] != "utf-8" or manifest["newline_policy"] != "uniform-preserve":
        raise WisdomCompileError("unsupported source encoding or newline policy")
    kernel_max = manifest["kernel_max_bytes"]
    if isinstance(kernel_max, bool) or not isinstance(kernel_max, int) or kernel_max < 1:
        raise WisdomCompileError("kernel_max_bytes must be a positive integer")
    if manifest["fallback"] != "full_source":
        raise WisdomCompileError("fallback must be full_source")

    allowed_tags_list = _require_list_of_unique_strings(
        manifest["allowed_tags"], "allowed_tags"
    )
    for tag in allowed_tags_list:
        _require_safe_id(tag, f"tag {tag!r}")
    allowed_tags = set(allowed_tags_list)

    task_profiles = manifest["task_profiles"]
    if not isinstance(task_profiles, list) or not task_profiles:
        raise WisdomCompileError("task_profiles must be a nonempty list")
    profile_ids: set[str] = set()
    for index, profile in enumerate(task_profiles):
        if not isinstance(profile, dict):
            raise WisdomCompileError(f"task_profile[{index}] must be an object")
        _require_exact_keys(profile, TASK_PROFILE_KEYS, f"task_profile[{index}]")
        profile_id = _require_safe_id(profile["id"], f"task_profile[{index}].id")
        if profile_id in profile_ids:
            raise WisdomCompileError(f"duplicate task profile: {profile_id}")
        profile_ids.add(profile_id)
        if profile["mode"] not in EXPECTED_MODES:
            raise WisdomCompileError(f"task_profile[{profile_id}].mode is invalid")
        profile_tags = _require_list_of_unique_strings(
            profile["tags"], f"task_profile[{profile_id}].tags"
        )
        unknown_profile_tags = sorted(set(profile_tags) - allowed_tags)
        if unknown_profile_tags:
            raise WisdomCompileError(
                f"task_profile[{profile_id}] has unknown tags: {unknown_profile_tags}"
            )

    heading_matches = list(HEADING_RE.finditer(raw))
    if not heading_matches:
        raise WisdomCompileError("WISDOM.md has no level-two sections")
    after_manifest = end_at + len(end_line)
    if raw[after_manifest : heading_matches[0].start()].strip():
        raise WisdomCompileError("only whitespace may appear between manifest and first section")

    section_specs = manifest["sections"]
    if not isinstance(section_specs, list) or not section_specs:
        raise WisdomCompileError("sections must be a nonempty list")
    if len(section_specs) != len(heading_matches):
        raise WisdomCompileError("manifest section count does not match level-two headings")

    sections: list[SectionSlice] = []
    section_ids: set[str] = set()
    headings_seen: set[str] = set()
    declared_rule_owner: dict[str, str] = {}
    for ordinal, (spec, match) in enumerate(zip(section_specs, heading_matches)):
        if not isinstance(spec, dict):
            raise WisdomCompileError(f"section[{ordinal}] must be an object")
        _require_exact_keys(spec, SECTION_KEYS, f"section[{ordinal}]")
        section_id = _require_safe_id(spec["id"], f"section[{ordinal}].id")
        if section_id == "preamble" or section_id in section_ids:
            raise WisdomCompileError(f"duplicate or reserved section id: {section_id}")
        section_ids.add(section_id)
        heading = match.group(1).decode("utf-8")
        if spec["heading"] != heading:
            raise WisdomCompileError(
                f"section heading mismatch at {ordinal}: {spec['heading']!r} != {heading!r}"
            )
        if heading in headings_seen:
            raise WisdomCompileError(f"duplicate level-two heading: {heading}")
        headings_seen.add(heading)
        next_start = (
            heading_matches[ordinal + 1].start()
            if ordinal + 1 < len(heading_matches)
            else len(raw)
        )
        body = raw[match.start() : next_start]
        rule_ids = _require_list_of_unique_strings(
            spec["rule_ids"], f"section[{section_id}].rule_ids"
        )
        discovered_here = {
            item.decode("ascii") for item in RULE_ID_RE.findall(body)
        }
        for rule_id in rule_ids:
            if re.fullmatch(r"[A-Z][A-Z0-9]+-[0-9]{2}", rule_id) is None:
                raise WisdomCompileError(f"invalid rule id: {rule_id}")
            if rule_id in declared_rule_owner:
                raise WisdomCompileError(f"rule id declared more than once: {rule_id}")
            if rule_id not in discovered_here:
                raise WisdomCompileError(
                    f"rule {rule_id} is not present in owning section {section_id}"
                )
            declared_rule_owner[rule_id] = section_id
        sections.append(
            SectionSlice(
                section_id=section_id,
                heading=heading,
                body=body,
                rule_ids=tuple(rule_ids),
                ordinal=ordinal,
            )
        )

    discovered_rules = {
        item.decode("ascii")
        for section in sections
        for item in RULE_ID_RE.findall(section.body)
    }
    if discovered_rules != set(declared_rule_owner):
        raise WisdomCompileError(
            "rule inventory mismatch; "
            f"undeclared={sorted(discovered_rules - set(declared_rule_owner))}, "
            f"missing={sorted(set(declared_rule_owner) - discovered_rules)}"
        )

    section_by_id = {section.section_id: section for section in sections}
    kernel_sections = _require_list_of_unique_strings(
        manifest["kernel_sections"], "kernel_sections"
    )
    kernel_tags = _require_list_of_unique_strings(manifest["kernel_tags"], "kernel_tags")
    if any(tag not in allowed_tags for tag in kernel_tags):
        raise WisdomCompileError("kernel_tags contains an unknown tag")
    if not kernel_sections or kernel_sections[0] != "preamble":
        raise WisdomCompileError("kernel_sections must begin with preamble")
    if any(item != "preamble" and item not in section_by_id for item in kernel_sections):
        raise WisdomCompileError("kernel_sections references an unknown section")
    kernel_ordinals = [section_by_id[item].ordinal for item in kernel_sections[1:]]
    if kernel_ordinals != sorted(kernel_ordinals):
        raise WisdomCompileError("kernel sections must follow source order")

    modules = manifest["modules"]
    if not isinstance(modules, list) or not modules:
        raise WisdomCompileError("modules must be a nonempty list")
    module_by_id: dict[str, Mapping[str, Any]] = {}
    section_owner: dict[str, tuple[str, str]] = {
        section_id: ("kernel", "kernel")
        for section_id in kernel_sections
        if section_id != "preamble"
    }
    previous_module_last_ordinal = -1
    for index, module in enumerate(modules):
        if not isinstance(module, dict):
            raise WisdomCompileError(f"module[{index}] must be an object")
        _require_exact_keys(module, MODULE_KEYS, f"module[{index}]")
        module_id = _require_safe_id(module["id"], f"module[{index}].id")
        if module_id in module_by_id:
            raise WisdomCompileError(f"duplicate module id: {module_id}")
        module_sections = _require_list_of_unique_strings(
            module["sections"], f"module[{module_id}].sections"
        )
        if not module_sections or any(item not in section_by_id for item in module_sections):
            raise WisdomCompileError(f"module {module_id} has missing or unknown sections")
        ordinals = [section_by_id[item].ordinal for item in module_sections]
        if ordinals != sorted(ordinals):
            raise WisdomCompileError(f"module {module_id} sections are not source ordered")
        if ordinals[0] <= previous_module_last_ordinal:
            raise WisdomCompileError(
                "modules must occupy noninterleaved source section ranges"
            )
        previous_module_last_ordinal = ordinals[-1]
        for section_id in module_sections:
            if section_id in section_owner:
                raise WisdomCompileError(f"section has multiple output owners: {section_id}")
            section_owner[section_id] = ("module", module_id)
        tags = _require_list_of_unique_strings(
            module["tags"], f"module[{module_id}].tags"
        )
        if any(tag not in allowed_tags for tag in tags):
            raise WisdomCompileError(f"module {module_id} uses an unknown tag")
        _require_list_of_unique_strings(
            module["requires"], f"module[{module_id}].requires"
        )
        module_by_id[module_id] = module
    if set(section_owner) != section_ids:
        raise WisdomCompileError(
            f"sections without exactly one output owner: {sorted(section_ids - set(section_owner))}"
        )
    _validate_graph(modules, set(module_by_id))

    views = manifest["views"]
    if not isinstance(views, list) or len(views) != len(EXPECTED_MODES):
        raise WisdomCompileError("views must define fast, focused, substantial, and full")
    view_by_mode: dict[str, Mapping[str, Any]] = {}
    reachable_modules: set[str] = set()
    for index, view in enumerate(views):
        if not isinstance(view, dict):
            raise WisdomCompileError(f"view[{index}] must be an object")
        _require_exact_keys(view, VIEW_KEYS, f"view[{index}]")
        mode = view["mode"]
        if mode != EXPECTED_MODES[index]:
            raise WisdomCompileError("views must be uniquely ordered fast/focused/substantial/full")
        required = _require_list_of_unique_strings(
            view["required_modules"], f"view[{mode}].required_modules"
        )
        if any(module_id not in module_by_id for module_id in required):
            raise WisdomCompileError(f"view {mode} references an unknown module")
        if not isinstance(view["source_direct"], bool):
            raise WisdomCompileError(f"view {mode}.source_direct must be boolean")
        if view["source_direct"] != (mode == "full"):
            raise WisdomCompileError("only the full view may be source_direct")
        view_by_mode[mode] = view
        reachable_modules.update(required)
    for module in modules:
        if module["tags"]:
            reachable_modules.add(module["id"])
    if reachable_modules != set(module_by_id):
        raise WisdomCompileError(
            f"unreachable modules: {sorted(set(module_by_id) - reachable_modules)}"
        )
    covered_tags = set(kernel_tags)
    for module in modules:
        covered_tags.update(module["tags"])
    if covered_tags != allowed_tags:
        raise WisdomCompileError(
            "tag coverage mismatch; "
            f"uncovered={sorted(allowed_tags - covered_tags)}, "
            f"undeclared={sorted(covered_tags - allowed_tags)}"
        )

    preamble = raw[:begin_at]
    kernel_parts = [preamble]
    kernel_parts.extend(section_by_id[item].body for item in kernel_sections[1:])
    kernel = b"".join(kernel_parts)
    if len(kernel) > kernel_max:
        raise WisdomCompileError(
            f"compiled kernel is {len(kernel)} bytes, above {kernel_max} byte bound"
        )

    return ParsedWisdom(
        source_path=path,
        raw=raw,
        source_sha256=sha256_bytes(raw),
        newline=newline,
        manifest=manifest,
        manifest_sha256=sha256_bytes(canonical_json_bytes(manifest)),
        preamble=preamble,
        sections=tuple(sections),
        section_by_id=section_by_id,
        module_by_id=module_by_id,
        module_order=tuple(module["id"] for module in modules),
        section_owner=section_owner,
        view_by_mode=view_by_mode,
        kernel=kernel,
    )


def _tool_hashes() -> dict[str, str]:
    compiler_path = Path(__file__).resolve()
    loader_path = compiler_path.with_name("load_compiled_wisdom.py")
    try:
        return {
            "compiler_sha256": sha256_bytes(_stable_read(compiler_path)),
            "loader_sha256": sha256_bytes(_stable_read(loader_path)),
        }
    except OSError as exc:
        raise WisdomCompileError(f"cannot hash compiler/loader tools: {exc}") from exc


def _require_current_tool_hashes(artifacts: CompiledArtifacts) -> None:
    current = _tool_hashes()
    expected = {
        "compiler_sha256": artifacts.identity["compiler_sha256"],
        "loader_sha256": artifacts.identity["loader_sha256"],
    }
    if current != expected:
        raise WisdomCompileError("compiler or loader changed during cache publication")


def _module_bytes(parsed: ParsedWisdom, module_id: str) -> bytes:
    module = parsed.module_by_id[module_id]
    return b"".join(parsed.section_by_id[item].body for item in module["sections"])


def _payloads(parsed: ParsedWisdom) -> dict[str, bytes]:
    payloads: dict[str, bytes] = {"kernel.md": parsed.kernel}
    for module_id in parsed.module_order:
        payloads[f"modules/{module_id}.md"] = _module_bytes(parsed, module_id)
    for mode in EXPECTED_MODES:
        view = parsed.view_by_mode[mode]
        payloads[f"views/{mode}.json"] = canonical_json_bytes(
            {
                "schema": VIEW_SCHEMA,
                "source_id": parsed.manifest["source_id"],
                "source_sha256": parsed.source_sha256,
                "semantic_revision": parsed.manifest["semantic_revision"],
                "mode": mode,
                "required_modules": view["required_modules"],
                "source_direct": view["source_direct"],
            }
        ) + b"\n"

    headings: dict[str, Any] = {}
    rules: dict[str, Any] = {}
    for section in parsed.sections:
        owner_kind, owner_id = parsed.section_owner[section.section_id]
        record = {
            "section_id": section.section_id,
            "target_kind": owner_kind,
            "target_id": owner_id,
        }
        headings[section.heading] = record
        for rule_id in section.rule_ids:
            rules[rule_id] = record
    payloads["anchor-index.json"] = canonical_json_bytes(
        {
            "schema": ANCHOR_SCHEMA,
            "source_id": parsed.manifest["source_id"],
            "source_sha256": parsed.source_sha256,
            "headings": headings,
            "rules": rules,
        }
    ) + b"\n"
    return payloads


def _output_receipts(payloads: Mapping[str, bytes]) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        {
            "path": relative_path,
            "bytes": len(payloads[relative_path]),
            "sha256": sha256_bytes(payloads[relative_path]),
        }
        for relative_path in sorted(payloads)
    )


def _current_envelope(
    *,
    parsed: ParsedWisdom,
    build_id: str,
    tree_sha256: str,
    manifest_sha256: str,
    manifest_body_sha256: str,
    tool_hashes: Mapping[str, str],
) -> bytes:
    body = {
        "schema": CURRENT_SCHEMA,
        "source_id": parsed.manifest["source_id"],
        "source_sha256": parsed.source_sha256,
        "semantic_revision": parsed.manifest["semantic_revision"],
        "build_id": build_id,
        "tree_sha256": tree_sha256,
        "manifest_sha256": manifest_sha256,
        "manifest_body_sha256": manifest_body_sha256,
        **tool_hashes,
    }
    return canonical_json_bytes({"body": body, "body_sha256": sha256_bytes(canonical_json_bytes(body))}) + b"\n"


def build_artifacts(parsed: ParsedWisdom) -> CompiledArtifacts:
    tool_hashes = _tool_hashes()
    payloads = _payloads(parsed)
    output_receipts = _output_receipts(payloads)
    tree_sha256 = sha256_bytes(canonical_json_bytes(output_receipts))
    identity = {
        "schema": IDENTITY_SCHEMA,
        "source_id": parsed.manifest["source_id"],
        "source_sha256": parsed.source_sha256,
        "source_bytes": len(parsed.raw),
        "semantic_revision": parsed.manifest["semantic_revision"],
        "source_manifest_sha256": parsed.manifest_sha256,
        "tree_sha256": tree_sha256,
        **tool_hashes,
    }
    build_id = sha256_bytes(canonical_json_bytes(identity))
    section_receipts = [
        {
            "id": section.section_id,
            "heading": section.heading,
            "bytes": len(section.body),
            "sha256": sha256_bytes(section.body),
            "output_kind": parsed.section_owner[section.section_id][0],
            "output_id": parsed.section_owner[section.section_id][1],
            "rule_ids": list(section.rule_ids),
        }
        for section in parsed.sections
    ]
    manifest_body = {
        "schema": COMPILED_SCHEMA,
        "authority": False,
        "build_id": build_id,
        "identity": identity,
        "source_manifest": parsed.manifest,
        "sections": section_receipts,
        "outputs": output_receipts,
        "tree_sha256": tree_sha256,
    }
    manifest_body_bytes = canonical_json_bytes(manifest_body)
    manifest_body_sha256 = sha256_bytes(manifest_body_bytes)
    manifest_bytes = canonical_json_bytes(
        {"body": manifest_body, "body_sha256": manifest_body_sha256}
    ) + b"\n"
    manifest_sha256 = sha256_bytes(manifest_bytes)
    current_bytes = _current_envelope(
        parsed=parsed,
        build_id=build_id,
        tree_sha256=tree_sha256,
        manifest_sha256=manifest_sha256,
        manifest_body_sha256=manifest_body_sha256,
        tool_hashes=tool_hashes,
    )
    return CompiledArtifacts(
        build_id=build_id,
        identity=identity,
        payloads=payloads,
        output_receipts=output_receipts,
        tree_sha256=tree_sha256,
        manifest_body=manifest_body,
        manifest_bytes=manifest_bytes,
        manifest_sha256=manifest_sha256,
        manifest_body_sha256=manifest_body_sha256,
        current_bytes=current_bytes,
    )


def resolve_module_ids(
    parsed: ParsedWisdom,
    *,
    mode: str,
    tags: Iterable[str] = (),
) -> tuple[str, ...]:
    if mode not in parsed.view_by_mode:
        raise WisdomCompileError(f"unknown mode: {mode}")
    requested_tags = tuple(tags)
    allowed_tags = set(parsed.manifest["allowed_tags"])
    unknown_tags = sorted(set(requested_tags) - allowed_tags)
    if unknown_tags:
        raise WisdomCompileError(f"unknown tags: {unknown_tags}")
    if mode == "full":
        return ()
    selected = set(parsed.view_by_mode[mode]["required_modules"])
    for module_id, module in parsed.module_by_id.items():
        if set(module["tags"]).intersection(requested_tags):
            selected.add(module_id)
    frontier = list(selected)
    while frontier:
        module_id = frontier.pop()
        for dependency in parsed.module_by_id[module_id]["requires"]:
            if dependency not in selected:
                selected.add(dependency)
                frontier.append(dependency)
    return tuple(module_id for module_id in parsed.module_order if module_id in selected)


def resolve_task_profile(
    parsed: ParsedWisdom,
    profile_id: str,
) -> tuple[str, tuple[str, ...]]:
    for profile in parsed.manifest["task_profiles"]:
        if profile["id"] == profile_id:
            return profile["mode"], tuple(profile["tags"])
    raise WisdomCompileError(f"unknown task profile: {profile_id}")


def _write_new_file(path: Path, value: bytes) -> None:
    filesystem_path = _filesystem_path(path)
    filesystem_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        filesystem_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            filesystem_path.unlink()
        except OSError:
            pass
        raise


def validate_installed_build(
    build_dir: Path,
    parsed: ParsedWisdom,
    artifacts: CompiledArtifacts | None = None,
    *,
    require_named_directory: bool = True,
) -> CompiledArtifacts:
    expected = artifacts or build_artifacts(parsed)
    if require_named_directory and build_dir.name != expected.build_id:
        raise WisdomCompileError("installed directory does not match expected build id")
    filesystem_root = _filesystem_path(build_dir)
    expected_paths = set(expected.payloads) | {"manifest.json"}
    actual_paths = {
        path.relative_to(filesystem_root).as_posix()
        for path in filesystem_root.rglob("*")
        if path.is_file()
    }
    if actual_paths != expected_paths:
        raise WisdomCompileError(
            "installed file inventory mismatch; "
            f"missing={sorted(expected_paths - actual_paths)}, "
            f"extra={sorted(actual_paths - expected_paths)}"
        )
    for relative_path, expected_bytes in expected.payloads.items():
        actual = (filesystem_root / Path(relative_path)).read_bytes()
        if actual != expected_bytes:
            raise WisdomCompileError(f"installed output mismatch: {relative_path}")
    if (filesystem_root / "manifest.json").read_bytes() != expected.manifest_bytes:
        raise WisdomCompileError("installed manifest does not match current source and tools")
    return expected


def _atomic_replace(path: Path, value: bytes) -> None:
    filesystem_path = _filesystem_path(path)
    filesystem_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = filesystem_path.with_name(
        f".{filesystem_path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    try:
        _write_new_file(temporary, value)
        os.replace(temporary, filesystem_path)
    finally:
        if temporary.exists():
            temporary.unlink()


def compile_and_install(source_path: Path | str, cache_root: Path | str) -> Mapping[str, Any]:
    parsed = parse_source(source_path)
    artifacts = build_artifacts(parsed)
    root = Path(cache_root).resolve()
    source_root = root / parsed.manifest["source_id"]
    target = source_root / artifacts.build_id
    _filesystem_path(source_root).mkdir(parents=True, exist_ok=True)
    if _filesystem_path(target).exists():
        validate_installed_build(target, parsed, artifacts)
        disposition = "reused"
    else:
        stage = source_root / f".stage-{os.getpid()}-{uuid.uuid4().hex}"
        _filesystem_path(stage).mkdir()
        try:
            for relative_path, value in artifacts.payloads.items():
                _write_new_file(stage / Path(relative_path), value)
            _write_new_file(stage / "manifest.json", artifacts.manifest_bytes)
            validate_installed_build(
                stage,
                parsed,
                artifacts,
                require_named_directory=False,
            )
            if _stable_read(parsed.source_path) != parsed.raw:
                raise WisdomCompileError("WISDOM.md changed before build publication")
            _require_current_tool_hashes(artifacts)
            try:
                os.rename(_filesystem_path(stage), _filesystem_path(target))
            except FileExistsError:
                validate_installed_build(target, parsed, artifacts)
            disposition = "installed"
        finally:
            filesystem_stage = _filesystem_path(stage)
            if filesystem_stage.exists():
                shutil.rmtree(filesystem_stage)
    validate_installed_build(target, parsed, artifacts)
    if _stable_read(parsed.source_path) != parsed.raw:
        raise WisdomCompileError("WISDOM.md changed before CURRENT publication")
    _require_current_tool_hashes(artifacts)
    _atomic_replace(source_root / "CURRENT.json", artifacts.current_bytes)
    return {
        "schema": COMPILE_RECEIPT_SCHEMA,
        "status": disposition,
        "authority": False,
        "source_id": parsed.manifest["source_id"],
        "source_sha256": parsed.source_sha256,
        "semantic_revision": parsed.manifest["semantic_revision"],
        "build_id": artifacts.build_id,
        "tree_sha256": artifacts.tree_sha256,
        "kernel_bytes": len(parsed.kernel),
        "source_bytes": len(parsed.raw),
        "cache_pointer": str(source_root / "CURRENT.json"),
    }


def _default_source() -> Path:
    return Path(__file__).resolve().parents[1] / "WISDOM.md"


def _default_cache_root() -> Path:
    return Path.home() / ".codex" / "compiled" / "wisdom"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=_default_source())
    parser.add_argument("--cache-root", type=Path, default=_default_cache_root())
    args = parser.parse_args(argv)
    try:
        receipt = compile_and_install(args.source, args.cache_root)
    except WisdomCompileError as exc:
        print(f"wisdom compile failed: {exc}", file=sys.stderr)
        return 2
    print(canonical_json_bytes(receipt).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
