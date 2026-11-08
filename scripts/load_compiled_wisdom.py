#!/usr/bin/env python3
"""Load verified compiled WISDOM views or require the full current source."""

from __future__ import annotations

import argparse
import hashlib
from importlib.machinery import SourceFileLoader
import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping, Sequence


class _SourceOnlyLoader(SourceFileLoader):
    """Read the exact sibling source without consuming or creating bytecode."""

    def get_code(self, fullname):
        return self.source_to_code(self.get_data(self.path), self.path)


def _load_path_bound_compiler() -> ModuleType:
    compiler_path = Path(__file__).resolve().with_name("compile_wisdom.py")
    module_suffix = hashlib.sha256(str(compiler_path).casefold().encode("utf-8")).hexdigest()[:16]
    module_name = f"_wisdom_compile_{module_suffix}"
    spec = importlib.util.spec_from_file_location(
        module_name, compiler_path,
        loader=_SourceOnlyLoader(module_name, str(compiler_path)),
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load exact sibling compiler: {compiler_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module


_compiler = _load_path_bound_compiler()
CURRENT_SCHEMA = _compiler.CURRENT_SCHEMA
WisdomCompileError = _compiler.WisdomCompileError
_require_current_tool_hashes = _compiler._require_current_tool_hashes
_stable_read = _compiler._stable_read
_tool_hashes = _compiler._tool_hashes
build_artifacts = _compiler.build_artifacts
canonical_json_bytes = _compiler.canonical_json_bytes
parse_source = _compiler.parse_source
resolve_module_ids = _compiler.resolve_module_ids
resolve_task_profile = _compiler.resolve_task_profile
sha256_bytes = _compiler.sha256_bytes
strict_json_loads = _compiler.strict_json_loads
validate_installed_build = _compiler.validate_installed_build
compile_and_install = _compiler.compile_and_install


LOAD_PLAN_SCHEMA = "wisdom.compiled.load_plan.v2"
DISCOVERY_SCHEMA = "wisdom.compiled.discovery.v1"
DELIVERY_SCHEMA = "wisdom.compiled.segmented_delivery.v1"
ROUTE_CHECKPOINT_SCHEMA = "wisdom.route_checkpoint.v2"
LEGACY_ROUTE_CHECKPOINT_SCHEMA = "wisdom.route_checkpoint.v1"
MAX_CHECKPOINT_BYTES = 64 * 1024
DEFAULT_SEGMENT_BYTES = 32 * 1024
MIN_SEGMENT_BYTES = 4 * 1024
MAX_SEGMENT_BYTES = 256 * 1024


class WisdomPhaseError(WisdomCompileError):
    """A requested phase is absent from the current source routing contract."""


def _validated_companion_receipt(
    companion_source_path: Path | str | None,
    *,
    expected_sha256: str | None,
    expected_bytes: int | None,
) -> Mapping[str, Any] | None:
    supplied = (
        companion_source_path is not None,
        expected_sha256 is not None,
        expected_bytes is not None,
    )
    if not any(supplied):
        return None
    if not all(supplied):
        raise WisdomCompileError(
            "companion source path, byte count, and SHA-256 must be supplied together"
        )
    if (
        isinstance(expected_bytes, bool)
        or not isinstance(expected_bytes, int)
        or expected_bytes < 1
    ):
        raise WisdomCompileError("companion source byte count is invalid")
    normalized_sha256 = str(expected_sha256).strip().lower()
    if len(normalized_sha256) != 64 or any(
        char not in "0123456789abcdef" for char in normalized_sha256
    ):
        raise WisdomCompileError("companion source SHA-256 is invalid")
    companion_path = Path(companion_source_path).resolve()
    try:
        raw = _stable_read(companion_path)
    except WisdomCompileError as exc:
        raise WisdomCompileError("companion source is unavailable") from exc
    if len(raw) != expected_bytes or sha256_bytes(raw) != normalized_sha256:
        raise WisdomCompileError("companion source does not match its exact binding")
    return {
        "path": str(companion_path),
        "bytes": len(raw),
        "sha256": normalized_sha256,
    }


def _attach_companion(
    plan: Mapping[str, Any],
    companion_receipt: Mapping[str, Any] | None,
    *,
    phase: str | None = None,
    source_bytes: int | None = None,
    selected_context_target_bytes: int | None = None,
) -> Mapping[str, Any]:
    if selected_context_target_bytes is not None and (
        isinstance(selected_context_target_bytes, bool)
        or not isinstance(selected_context_target_bytes, int)
        or selected_context_target_bytes < 1
    ):
        raise WisdomCompileError("selected context target must be a positive byte count")
    attached = dict(plan)
    if companion_receipt is not None:
        attached["companion_source"] = dict(companion_receipt)
        attached["content_paths"] = [
            *list(attached["content_paths"]),
            companion_receipt["path"],
        ]
        attached["content_receipts"] = [
            *list(attached["content_receipts"]),
            dict(companion_receipt),
        ]
        attached["content_bytes"] = int(attached["content_bytes"]) + int(
            companion_receipt["bytes"]
        )
    receipts = attached["content_receipts"]
    wisdom_count = len(receipts) - (1 if companion_receipt is not None else 0)
    wisdom_bytes = sum(item["bytes"] for item in receipts[:wisdom_count])
    companion_bytes = 0 if companion_receipt is None else companion_receipt["bytes"]
    selected_total = wisdom_bytes + companion_bytes
    if attached["status"] == "compiled":
        kernel_bytes = receipts[0]["bytes"]
        module_bytes = wisdom_bytes - kernel_bytes
    else:
        kernel_bytes = 0
        module_bytes = 0
    if selected_context_target_bytes is None:
        target_status = {"kind": "unbounded", "excess_bytes": 0}
    elif selected_total > selected_context_target_bytes:
        target_status = {
            "kind": "over_target",
            "excess_bytes": selected_total - selected_context_target_bytes,
        }
    else:
        target_status = {"kind": "within_target", "excess_bytes": 0}
    attached["phase"] = phase
    attached["selected_context"] = {
        "phase": phase,
        "source_bytes": source_bytes if source_bytes is not None else wisdom_bytes,
        "kernel_bytes": kernel_bytes,
        "module_bytes": module_bytes,
        "companion_bytes": companion_bytes,
        "wisdom_selected_bytes": wisdom_bytes,
        "selected_total_bytes": selected_total,
        "target_bytes": selected_context_target_bytes,
        "target_status": target_status,
    }
    return attached


def _full_source_plan(
    source_path: Path,
    *,
    mode: str,
    tags: Iterable[str],
    reason: str,
    task_profile: str | None = None,
) -> Mapping[str, Any]:
    raw = _stable_read(source_path)
    content_path = str(source_path)
    return _attach_companion({
        "schema": LOAD_PLAN_SCHEMA,
        "status": "full_source_required",
        "authority": False,
        "mode": mode,
        "tags": sorted(set(tags)),
        "task_profile": task_profile,
        "reason": reason,
        "source_path": content_path,
        "source_sha256": sha256_bytes(raw),
        "tool_hashes": None,
        "build_id": None,
        "tree_sha256": None,
        "content_paths": [content_path],
        "content_receipts": [
            {
                "path": content_path,
                "bytes": len(raw),
                "sha256": sha256_bytes(raw),
            }
        ],
        "content_bytes": len(raw),
    }, None, source_bytes=len(raw))


def _validate_current_pointer(raw: bytes, expected: bytes) -> None:
    value = strict_json_loads(raw, label="CURRENT.json")
    if not isinstance(value, dict) or set(value) != {"body", "body_sha256"}:
        raise WisdomCompileError("CURRENT.json envelope is malformed")
    body = value["body"]
    if not isinstance(body, dict) or body.get("schema") != CURRENT_SCHEMA:
        raise WisdomCompileError("CURRENT.json schema is malformed")
    if value["body_sha256"] != sha256_bytes(canonical_json_bytes(body)):
        raise WisdomCompileError("CURRENT.json body hash is invalid")
    if raw != expected:
        raise WisdomCompileError("CURRENT.json does not bind current source and tools")


def _routing_hints(parsed: Any, module_id: str) -> list[dict[str, str]]:
    """Expose authored applicability metadata, never a substitute for rule bytes."""
    hints = []
    for section_id in parsed.module_by_id[module_id]["sections"]:
        section = parsed.section_by_id[section_id]
        # Only the introductory metadata precedes the first authored rule.
        intro = section.body.decode("utf-8").split("**`", 1)[0]
        paragraphs = intro.replace("\r\n", "\n").split("\n\n")
        hint = {"section_id": section_id, "heading": section.heading}
        for label, field in (("Load when:", "load_when"),
                             ("Engineering preferences:", "engineering_preferences")):
            for paragraph in paragraphs:
                if paragraph.startswith(label):
                    hint[field] = " ".join(paragraph[len(label):].split())
                    break
        if "load_when" in hint:
            hints.append(hint)
    return hints


def discover_capabilities(source_path: Path | str) -> Mapping[str, Any]:
    source = Path(source_path).resolve()
    try:
        parsed = parse_source(source)
        modes = []
        for mode, view in parsed.view_by_mode.items():
            modes.append(
                {
                    "mode": mode,
                    "source_direct": view["source_direct"],
                    "declared_modules": list(view["required_modules"]),
                    "resolved_modules": list(
                        resolve_module_ids(parsed, mode=mode, tags=())
                    ),
                }
            )
        kernel_tags = set(parsed.manifest["kernel_tags"])
        tags = []
        for tag in parsed.manifest["allowed_tags"]:
            direct_modules = [
                module_id
                for module_id in parsed.module_order
                if tag in parsed.module_by_id[module_id]["tags"]
            ]
            tags.append(
                {
                    "tag": tag,
                    "kernel_satisfied": tag in kernel_tags,
                    "direct_modules": direct_modules,
                    "resolved_modules": list(
                        resolve_module_ids(parsed, mode="fast", tags=(tag,))
                    ),
                }
            )
        modules = [
            {
                "id": module_id,
                "sections": list(parsed.module_by_id[module_id]["sections"]),
                "tags": list(parsed.module_by_id[module_id]["tags"]),
                "requires": list(parsed.module_by_id[module_id]["requires"]),
                "routing_hints": _routing_hints(parsed, module_id),
            }
            for module_id in parsed.module_order
        ]
        task_profiles = [
            {
                "id": profile["id"],
                "mode": profile["mode"],
                "tags": list(profile["tags"]),
                "resolved_modules": list(
                    resolve_module_ids(
                        parsed,
                        mode=profile["mode"],
                        tags=profile["tags"],
                    )
                ),
            }
            for profile in parsed.manifest["task_profiles"]
        ]
        phases = [
            {
                "id": phase_id,
                "tags": list(phase["tags"]),
                "resolved_modules": list(
                    resolve_module_ids(parsed, mode="fast", tags=phase["tags"])
                ),
            }
            for phase_id, phase in parsed.phase_by_id.items()
        ]
        return {
            "schema": DISCOVERY_SCHEMA,
            "status": "discovery",
            "authority": False,
            "source_id": parsed.manifest["source_id"],
            "source_sha256": parsed.source_sha256,
            "semantic_revision": parsed.manifest["semantic_revision"],
            "unknown_impact_action": "full_source_required",
            "modes": modes,
            "tags": tags,
            "modules": modules,
            "task_profiles": task_profiles,
            "phases": phases,
        }
    except (OSError, WisdomCompileError, KeyError, TypeError, ValueError) as exc:
        return _full_source_plan(
            source,
            mode="discovery",
            tags=(),
            reason=f"discovery_unavailable:{type(exc).__name__}",
        )


def load_plan(
    source_path: Path | str,
    cache_root: Path | str,
    *,
    mode: str | None = None,
    tags: Iterable[str] = (),
    task_profile: str | None = None,
    phase: str | None = None,
    selected_context_target_bytes: int | None = None,
    unknown_impact: bool = False,
    companion_source_path: Path | str | None = None,
    expected_companion_sha256: str | None = None,
    expected_companion_bytes: int | None = None,
    expected_source_sha256: str | None = None,
) -> Mapping[str, Any]:
    source = Path(source_path).resolve()
    explicit_mode = mode
    requested_mode = mode or "focused"
    requested_tags = tuple(sorted(set(tags)))
    if selected_context_target_bytes is not None and (
        isinstance(selected_context_target_bytes, bool)
        or not isinstance(selected_context_target_bytes, int)
        or selected_context_target_bytes < 1
    ):
        raise WisdomCompileError("selected context target must be a positive byte count")
    companion_receipt = _validated_companion_receipt(
        companion_source_path,
        expected_sha256=expected_companion_sha256,
        expected_bytes=expected_companion_bytes,
    )
    if unknown_impact:
        return _attach_companion(
            _full_source_plan(
                source,
                mode=requested_mode,
                tags=requested_tags,
                reason="unknown_impact",
                task_profile=task_profile,
            ),
            companion_receipt,
            phase=phase,
            selected_context_target_bytes=selected_context_target_bytes,
        )
    if mode == "full":
        return _attach_companion(
            _full_source_plan(
                source,
                mode=requested_mode,
                tags=requested_tags,
                reason="full_mode",
                task_profile=task_profile,
            ),
            companion_receipt,
            phase=phase,
            selected_context_target_bytes=selected_context_target_bytes,
        )
    try:
        parsed = parse_source(source)
        if expected_source_sha256 is not None and parsed.source_sha256 != expected_source_sha256:
            raise WisdomCompileError("source changed after route expansion; full source required")
        if phase is not None:
            if not isinstance(phase, str) or phase not in parsed.phase_by_id:
                raise WisdomPhaseError(f"unknown phase: {phase!r}")
            requested_tags = tuple(
                sorted(set((*requested_tags, *parsed.phase_by_id[phase]["tags"])))
            )
        if task_profile is not None:
            mode, profile_tags = resolve_task_profile(parsed, task_profile)
            if explicit_mode is not None and explicit_mode not in {mode, "full"}:
                raise WisdomCompileError(
                    "explicit mode conflicts with task profile; full source required"
                )
            requested_tags = tuple(sorted(set((*requested_tags, *profile_tags))))
        else:
            mode = requested_mode
        if mode == "full":
            return _attach_companion(
                _full_source_plan(
                    source,
                    mode="full",
                    tags=requested_tags,
                    reason="full_task_profile",
                    task_profile=task_profile,
                ),
                companion_receipt,
                phase=phase,
                selected_context_target_bytes=selected_context_target_bytes,
            )
        module_ids = resolve_module_ids(parsed, mode=mode, tags=requested_tags)
        artifacts = build_artifacts(parsed)
        source_root = Path(cache_root).resolve() / parsed.manifest["source_id"]
        current_path = source_root / "CURRENT.json"
        _validate_current_pointer(_stable_read(current_path), artifacts.current_bytes)
        build_dir = source_root / artifacts.build_id
        validate_installed_build(build_dir, parsed, artifacts)
        if _stable_read(source) != parsed.raw:
            raise WisdomCompileError("WISDOM.md changed after cache validation")
        _require_current_tool_hashes(artifacts)
        content_paths = [str(build_dir / "kernel.md")]
        content_paths.extend(str(build_dir / "modules" / f"{item}.md") for item in module_ids)
        receipt_by_path = {
            item["path"]: item for item in artifacts.output_receipts
        }
        relative_paths = ["kernel.md"]
        relative_paths.extend(f"modules/{item}.md" for item in module_ids)
        content_receipts = [
            {
                "path": content_path,
                "bytes": receipt_by_path[relative_path]["bytes"],
                "sha256": receipt_by_path[relative_path]["sha256"],
            }
            for content_path, relative_path in zip(content_paths, relative_paths)
        ]
        content_bytes = sum(item["bytes"] for item in content_receipts)
        return _attach_companion({
            "schema": LOAD_PLAN_SCHEMA,
            "status": "compiled",
            "authority": False,
            "mode": mode,
            "tags": list(requested_tags),
            "task_profile": task_profile,
            "reason": "verified_current_cache",
            "source_path": str(source),
            "source_sha256": parsed.source_sha256,
            "semantic_revision": parsed.manifest["semantic_revision"],
            "tool_hashes": {
                "compiler_sha256": artifacts.identity["compiler_sha256"],
                "loader_sha256": artifacts.identity["loader_sha256"],
            },
            "build_id": artifacts.build_id,
            "tree_sha256": artifacts.tree_sha256,
            "module_ids": list(module_ids),
            "content_paths": content_paths,
            "content_receipts": content_receipts,
            "content_bytes": content_bytes,
        }, companion_receipt,
            phase=phase,
            source_bytes=len(parsed.raw),
            selected_context_target_bytes=selected_context_target_bytes,
        )
    except (OSError, WisdomCompileError, KeyError, TypeError, ValueError) as exc:
        return _attach_companion(
            _full_source_plan(
                source,
                mode=requested_mode,
                tags=requested_tags,
                reason=(
                    "phase_unavailable:WisdomCompileError"
                    if isinstance(exc, WisdomPhaseError)
                    else
                    "task_profile_unavailable:WisdomCompileError"
                    if task_profile is not None and "task profile" in str(exc)
                    else f"compiled_cache_unavailable:{type(exc).__name__}"
                ),
                task_profile=task_profile,
            ),
            companion_receipt,
            phase=phase,
            selected_context_target_bytes=selected_context_target_bytes,
        )


def read_plan_content(plan: Mapping[str, Any]) -> bytes:
    if plan.get("schema") != LOAD_PLAN_SCHEMA:
        raise WisdomCompileError("load plan schema is not current")
    status = plan.get("status")
    if status not in {"compiled", "full_source_required"}:
        raise WisdomCompileError("load plan status cannot provide content")
    source_path = plan.get("source_path")
    source_sha256 = plan.get("source_sha256")
    if not isinstance(source_path, str) or not isinstance(source_sha256, str):
        raise WisdomCompileError("load plan source binding is malformed")
    source_before = _stable_read(Path(source_path))
    if sha256_bytes(source_before) != source_sha256:
        raise WisdomCompileError("WISDOM.md changed after load planning")

    expected_tool_hashes: Mapping[str, str] | None = None
    if status == "compiled":
        tool_hashes = plan.get("tool_hashes")
        if not isinstance(tool_hashes, dict) or set(tool_hashes) != {
            "compiler_sha256",
            "loader_sha256",
        }:
            raise WisdomCompileError("compiled load plan tool binding is malformed")
        if any(not isinstance(value, str) for value in tool_hashes.values()):
            raise WisdomCompileError("compiled load plan tool hash is malformed")
        expected_tool_hashes = tool_hashes
        if _tool_hashes() != expected_tool_hashes:
            raise WisdomCompileError("compiler or loader changed after load planning")
        parsed = parse_source(Path(source_path))
        if parsed.raw != source_before:
            raise WisdomCompileError("WISDOM.md changed while verifying route")
        route_mode = plan.get("mode")
        route_tags = plan.get("tags")
        if not isinstance(route_mode, str) or not isinstance(route_tags, list) or any(
            not isinstance(tag, str) for tag in route_tags
        ):
            raise WisdomCompileError("compiled load plan route is malformed")
        profile_id = plan.get("task_profile")
        if profile_id is not None:
            profile_mode, profile_tags = resolve_task_profile(parsed, profile_id)
            if route_mode != profile_mode or not set(profile_tags).issubset(route_tags):
                raise WisdomCompileError("compiled load plan task profile route is malformed")
        phase = plan.get("phase")
        if phase is not None:
            phase_meta = parsed.phase_by_id.get(phase) if isinstance(phase, str) else None
            if phase_meta is None or not set(phase_meta["tags"]).issubset(route_tags):
                raise WisdomCompileError("compiled load plan phase route is malformed")
        expected_modules = resolve_module_ids(parsed, mode=route_mode, tags=route_tags)
        if plan.get("module_ids") != list(expected_modules):
            raise WisdomCompileError("compiled load plan omits routed modules")
    elif plan.get("tool_hashes") is not None:
        raise WisdomCompileError("full-source load plan unexpectedly binds tools")

    companion_receipt = plan.get("companion_source")
    companion_before: bytes | None = None
    if companion_receipt is not None:
        if not isinstance(companion_receipt, dict):
            raise WisdomCompileError("load plan companion binding is malformed")
        companion_path = companion_receipt.get("path")
        if not isinstance(companion_path, str):
            raise WisdomCompileError("load plan companion path is malformed")
        companion_before = _stable_read(Path(companion_path))
        if (
            companion_receipt.get("bytes") != len(companion_before)
            or companion_receipt.get("sha256") != sha256_bytes(companion_before)
        ):
            raise WisdomCompileError("companion source changed after load planning")

    paths = plan.get("content_paths")
    receipts = plan.get("content_receipts")
    if not isinstance(paths, list) or not paths or not isinstance(receipts, list):
        raise WisdomCompileError("load plan has no verified content paths")
    if len(paths) != len(receipts):
        raise WisdomCompileError("load plan content receipts do not match paths")
    if status == "compiled":
        if not isinstance(paths[0], str):
            raise WisdomCompileError("compiled load plan kernel path is malformed")
        kernel_dir = Path(paths[0]).parent
        expected_paths = [str(kernel_dir / "kernel.md")]
        expected_paths.extend(
            str(kernel_dir / "modules" / f"{module_id}.md")
            for module_id in expected_modules
        )
        if isinstance(companion_receipt, dict):
            expected_paths.append(companion_receipt["path"])
        if paths != expected_paths:
            if isinstance(companion_receipt, dict) and companion_receipt["path"] not in paths:
                raise WisdomCompileError(
                    "load plan does not carry the exact companion content join"
                )
            raise WisdomCompileError("compiled load plan content path route is malformed")
        if kernel_dir.name != plan.get("build_id"):
            raise WisdomCompileError("compiled load plan build path is malformed")
    if isinstance(companion_receipt, dict):
        companion_path = companion_receipt["path"]
        if (
            paths.count(companion_path) != 1
            or paths[-1] != companion_path
            or receipts[-1] != companion_receipt
        ):
            raise WisdomCompileError(
                "load plan does not carry the exact companion content join"
            )
    expected_full_paths = [source_path]
    if isinstance(companion_receipt, dict):
        expected_full_paths.append(companion_receipt["path"])
    if status == "full_source_required" and paths != expected_full_paths:
        raise WisdomCompileError(
            "full-source load plan does not read only WISDOM.md and its bound companion"
        )
    content: list[bytes] = []
    for path, receipt in zip(paths, receipts):
        if not isinstance(receipt, dict) or receipt.get("path") != path:
            raise WisdomCompileError("load plan content receipt path mismatch")
        raw = _stable_read(Path(path))
        if receipt.get("bytes") != len(raw) or receipt.get("sha256") != sha256_bytes(raw):
            raise WisdomCompileError(f"load plan content changed after validation: {path}")
        content.append(raw)
    source_after = _stable_read(Path(source_path))
    if source_after != source_before:
        raise WisdomCompileError("WISDOM.md changed while reading planned content")
    if isinstance(companion_receipt, dict):
        companion_after = _stable_read(Path(companion_receipt["path"]))
        if companion_after != companion_before:
            raise WisdomCompileError("companion source changed while reading planned content")
    if expected_tool_hashes is not None and _tool_hashes() != expected_tool_hashes:
        raise WisdomCompileError("compiler or loader changed while reading planned content")
    joined = b"".join(content)
    if plan.get("content_bytes") != len(joined):
        raise WisdomCompileError("load plan content byte count is malformed")
    if status == "compiled":
        canonical = build_artifacts(parsed)
        if (
            plan.get("build_id") != canonical.build_id
            or plan.get("tree_sha256") != canonical.tree_sha256
            or plan.get("semantic_revision") != parsed.manifest["semantic_revision"]
        ):
            raise WisdomCompileError("compiled load plan is not the current source build")
        if kernel_dir.parent.name != parsed.manifest["source_id"]:
            raise WisdomCompileError("compiled load plan source cache path is malformed")
        _validate_current_pointer(
            _stable_read(kernel_dir.parent / "CURRENT.json"),
            canonical.current_bytes,
        )
        validate_installed_build(kernel_dir, parsed, canonical)
    context = plan.get("selected_context")
    companion_bytes = len(companion_before) if companion_before is not None else 0
    wisdom_bytes = len(joined) - companion_bytes
    if not isinstance(context, dict) or context.get("phase") != plan.get("phase"):
        raise WisdomCompileError("selected context phase binding is malformed")
    if (
        context.get("source_bytes") != len(source_before)
        or context.get("companion_bytes") != companion_bytes
        or context.get("wisdom_selected_bytes") != wisdom_bytes
        or context.get("selected_total_bytes") != len(joined)
    ):
        raise WisdomCompileError("selected context byte accounting is malformed")
    if status == "compiled":
        expected_kernel_bytes = receipts[0]["bytes"]
        expected_module_bytes = wisdom_bytes - expected_kernel_bytes
    else:
        expected_kernel_bytes = expected_module_bytes = 0
    if (
        context.get("kernel_bytes") != expected_kernel_bytes
        or context.get("module_bytes") != expected_module_bytes
    ):
        raise WisdomCompileError("selected context component accounting is malformed")
    target = context.get("target_bytes")
    if target is not None and (
        isinstance(target, bool) or not isinstance(target, int) or target < 1
    ):
        raise WisdomCompileError("selected context target is malformed")
    if target is None:
        expected_status = {"kind": "unbounded", "excess_bytes": 0}
    elif len(joined) > target:
        expected_status = {"kind": "over_target", "excess_bytes": len(joined) - target}
    else:
        expected_status = {"kind": "within_target", "excess_bytes": 0}
    if context.get("target_status") != expected_status:
        raise WisdomCompileError("selected context target status is malformed")
    try:
        joined.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise WisdomCompileError("planned instructions are not valid UTF-8") from exc
    return joined


def _validated_segment_bytes(value: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < MIN_SEGMENT_BYTES
        or value > MAX_SEGMENT_BYTES
    ):
        raise WisdomCompileError(
            f"segment byte bound must be between {MIN_SEGMENT_BYTES} and "
            f"{MAX_SEGMENT_BYTES}"
        )
    return value


def _segmented_delivery(
    plan: Mapping[str, Any],
    *,
    segment_bytes: int = DEFAULT_SEGMENT_BYTES,
) -> tuple[Mapping[str, Any], bytes]:
    size = _validated_segment_bytes(segment_bytes)
    delivery_tools = _tool_hashes()
    content = read_plan_content(plan)
    content_sha256 = sha256_bytes(content)
    identity = {
        "schema": DELIVERY_SCHEMA,
        "source_sha256": plan.get("source_sha256"),
        "status": plan.get("status"),
        "tool_hashes": plan.get("tool_hashes"),
        "build_id": plan.get("build_id"),
        "tree_sha256": plan.get("tree_sha256"),
        "companion_source": plan.get("companion_source"),
        "phase": plan.get("phase"),
        "selected_context": plan.get("selected_context"),
        "content_sha256": content_sha256,
        "content_bytes": len(content),
        "segment_bytes": size,
        "segment_encoding": "utf-8",
        "delivery_tool_hashes": delivery_tools,
    }
    delivery_id = sha256_bytes(canonical_json_bytes(identity))
    segments = []
    offset = 0
    while offset < len(content):
        end = min(offset + size, len(content))
        # End before an incomplete code point so every text-tool response decodes.
        while end < len(content) and content[end] & 0xC0 == 0x80:
            end -= 1
        segment = content[offset:end]
        segments.append(
            {
                "index": len(segments),
                "offset": offset,
                "bytes": len(segment),
                "sha256": sha256_bytes(segment),
            }
        )
        offset = end
    if not segments:
        raise WisdomCompileError("verified content is unexpectedly empty")
    if _tool_hashes() != delivery_tools:
        raise WisdomCompileError("delivery tools changed while segmenting instructions")
    return (
        {
            **identity,
            "delivery_id": delivery_id,
            "segment_count": len(segments),
            "segments": segments,
        },
        content,
    )


def segmented_delivery_plan(
    plan: Mapping[str, Any],
    *,
    segment_bytes: int = DEFAULT_SEGMENT_BYTES,
) -> Mapping[str, Any]:
    delivery, _ = _segmented_delivery(plan, segment_bytes=segment_bytes)
    return delivery


def read_delivery_segment(
    plan: Mapping[str, Any],
    index: int,
    *,
    expected_delivery_id: str,
    segment_bytes: int = DEFAULT_SEGMENT_BYTES,
) -> bytes:
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise WisdomCompileError("delivery segment index is invalid")
    normalized_expected = expected_delivery_id.strip().lower()
    if len(normalized_expected) != 64 or any(
        char not in "0123456789abcdef" for char in normalized_expected
    ):
        raise WisdomCompileError("expected delivery ID is invalid")
    delivery, content = _segmented_delivery(plan, segment_bytes=segment_bytes)
    if delivery["delivery_id"] != normalized_expected:
        raise WisdomCompileError("verified delivery generation does not match expectation")
    segments = delivery["segments"]
    if index >= len(segments):
        raise WisdomCompileError("delivery segment index is out of range")
    receipt = segments[index]
    start = receipt["offset"]
    segment = content[start : start + receipt["bytes"]]
    if sha256_bytes(segment) != receipt["sha256"]:
        raise WisdomCompileError("delivery segment does not match its receipt")
    return segment


def read_plan_content_or_current_source(plan: Mapping[str, Any]) -> bytes:
    """Read one verified plan, falling back to the newly current full source."""

    try:
        return read_plan_content(plan)
    except WisdomCompileError:
        source_path = plan.get("source_path")
        if not isinstance(source_path, str):
            raise
        mode = plan.get("mode")
        if not isinstance(mode, str):
            mode = "unknown"
        task_profile = plan.get("task_profile")
        if not isinstance(task_profile, str):
            task_profile = None
        tags = plan.get("tags")
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            tags = []
        fallback = _full_source_plan(
            Path(source_path).resolve(),
            mode=mode,
            tags=tags,
            reason="planned_content_invalidated",
            task_profile=task_profile,
        )
        companion_receipt = plan.get("companion_source")
        if companion_receipt is not None:
            if not isinstance(companion_receipt, dict):
                raise WisdomCompileError("load plan companion binding is malformed")
            companion_receipt = _validated_companion_receipt(
                companion_receipt.get("path"),
                expected_sha256=companion_receipt.get("sha256"),
                expected_bytes=companion_receipt.get("bytes"),
            )
        context = plan.get("selected_context")
        target = context.get("target_bytes") if isinstance(context, dict) else None
        fallback = _attach_companion(
            fallback,
            companion_receipt,
            phase=plan.get("phase"),
            selected_context_target_bytes=target,
        )
        return read_plan_content(fallback)


def _route_identity(project_root: Path | str, task_id: str) -> tuple[str, str]:
    root = Path(project_root).resolve(strict=True)
    if not root.is_dir():
        raise WisdomCompileError("route project root must be a directory")
    if not isinstance(task_id, str) or not 1 <= len(task_id) <= 128 or any(
        not (char.isascii() and (char.isalnum() or char in "._:-")) for char in task_id
    ):
        raise WisdomCompileError("route task ID must be 1-128 ASCII letters, digits, or ._:-")
    return str(root), task_id


def save_route_checkpoint(
    plan: Mapping[str, Any], destination: Path | str, *,
    project_root: Path | str, task_id: str,
) -> Mapping[str, Any]:
    """Publish an immutable navigation hint; never certify model retention."""
    root, task = _route_identity(project_root, task_id)
    content = read_plan_content(plan)
    previous = plan.get("continuity", {})
    profile = plan.get("task_profile") or previous.get("task_profile_hint")
    profiles = list(dict.fromkeys((*previous.get("task_profiles", ()), *filter(None, (profile,)))))
    phases = list(dict.fromkeys((*previous.get("phases", ()), *filter(None, (plan.get("phase"),)))))
    body = {
        "schema": ROUTE_CHECKPOINT_SCHEMA,
        "authority": False,
        "project_root": root,
        "task_id": task,
        "source_path": plan["source_path"],
        "source_sha256": plan["source_sha256"],
        "content_sha256": sha256_bytes(content),
        "module_ids": list(plan.get("module_ids", [])),
        "selection": {
            # A full-source fallback must not silently resume as a narrower route.
            "mode": "full" if plan["status"] == "full_source_required" else plan["mode"],
            "tags": list(plan["tags"]),
            "task_profile_hint": profile,
            "phase": plan.get("phase"),
            "task_profiles": profiles,
            "phases": phases,
            "selected_context_target_bytes": plan["selected_context"]["target_bytes"],
        },
        "companion_source": plan.get("companion_source"),
    }
    envelope = {"body": body, "body_sha256": sha256_bytes(canonical_json_bytes(body))}
    raw = canonical_json_bytes(envelope)
    if len(raw) > MAX_CHECKPOINT_BYTES:
        raise WisdomCompileError("route checkpoint exceeds its byte bound")
    output = Path(destination).absolute()
    if output.is_symlink() or output.exists():
        raise WisdomCompileError("route checkpoint already exists; use a new generation path")
    if not output.resolve().is_relative_to(Path(root)):
        raise WisdomCompileError("route checkpoint must stay inside its project root")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".wisdom-route-", delete=False) as stream:
            temporary = stream.name
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        # Publish complete bytes without replacing another task/generation.
        os.link(temporary, output)
    except OSError as exc:
        raise WisdomCompileError(f"cannot publish route checkpoint: {exc}") from exc
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
    return {"path": str(output.resolve()), "sha256": sha256_bytes(raw), "reload_required": True}


def read_route_checkpoint(
    checkpoint: Path | str, *, source_path: Path | str,
    project_root: Path | str, task_id: str,
) -> Mapping[str, Any]:
    root, task = _route_identity(project_root, task_id)
    path = Path(checkpoint)
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_CHECKPOINT_BYTES + 1)
        with path.open("rb") as stream:
            second = stream.read(MAX_CHECKPOINT_BYTES + 1)
    except OSError as exc:
        raise WisdomCompileError("route checkpoint is unavailable") from exc
    if len(raw) > MAX_CHECKPOINT_BYTES or raw != second:
        raise WisdomCompileError("route checkpoint is oversized or changed during reading")
    value = strict_json_loads(raw, label="route checkpoint")
    if not isinstance(value, dict) or set(value) != {"body", "body_sha256"}:
        raise WisdomCompileError("route checkpoint envelope is malformed")
    body = value["body"]
    expected = {"schema", "authority", "project_root", "task_id", "source_path",
                "source_sha256", "content_sha256", "module_ids", "selection", "companion_source"}
    if not isinstance(body, dict) or set(body) != expected or (
        body.get("schema") not in (ROUTE_CHECKPOINT_SCHEMA, LEGACY_ROUTE_CHECKPOINT_SCHEMA)
        or body.get("authority") is not False
        or value["body_sha256"] != sha256_bytes(canonical_json_bytes(body))
    ):
        raise WisdomCompileError("route checkpoint body or checksum is invalid")
    if body["project_root"] != root or body["task_id"] != task:
        raise WisdomCompileError("route checkpoint belongs to a different project or task")
    if body["source_path"] != str(Path(source_path).resolve()):
        raise WisdomCompileError("route checkpoint belongs to a different WISDOM source")
    for key in ("source_sha256", "content_sha256"):
        digest = body[key]
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise WisdomCompileError("route checkpoint digest is malformed")
    selection = body["selection"]
    selection_keys = {
        "mode", "tags", "task_profile_hint", "phase", "selected_context_target_bytes"
    }
    if body["schema"] == ROUTE_CHECKPOINT_SCHEMA:
        selection_keys.update(("task_profiles", "phases"))
    if not isinstance(selection, dict) or set(selection) != selection_keys or not isinstance(selection.get("mode"), str) or selection["mode"] not in {"fast", "focused", "substantial", "full"}:
        raise WisdomCompileError("route checkpoint selection is malformed")
    for items in (selection["tags"], body["module_ids"]):
        if not isinstance(items, list) or any(not isinstance(item, str) for item in items) or len(items) != len(set(items)):
            raise WisdomCompileError("route checkpoint tags/modules are malformed")
    for key in ("task_profile_hint", "phase"):
        if selection[key] is not None and not isinstance(selection[key], str):
            raise WisdomCompileError("route checkpoint profile/phase is malformed")
    if body["schema"] == ROUTE_CHECKPOINT_SCHEMA:
        for key, hint in (("task_profiles", "task_profile_hint"), ("phases", "phase")):
            owners = selection[key]
            if (not isinstance(owners, list)
                or any(not isinstance(owner, str) or not owner for owner in owners)
                or len(owners) != len(set(owners))
                or (selection[hint] is not None and selection[hint] not in owners)):
                raise WisdomCompileError("route checkpoint profile/phase lineage is malformed")
    target = selection["selected_context_target_bytes"]
    if target is not None and (type(target) is not int or target < 1):
        raise WisdomCompileError("route checkpoint context target is malformed")
    companion = body["companion_source"]
    if companion is not None and (not isinstance(companion, dict) or set(companion) != {"path", "bytes", "sha256"}):
        raise WisdomCompileError("route checkpoint companion is malformed")
    if companion is not None and (
        not isinstance(companion["path"], str) or not isinstance(companion["sha256"], str)
        or type(companion["bytes"]) is not int or companion["bytes"] < 1
    ):
        raise WisdomCompileError("route checkpoint companion binding is malformed")
    return {"body": body, "checkpoint_sha256": sha256_bytes(raw)}


def resume_route_options(
    checkpoint: Mapping[str, Any], *, source_path: Path | str,
    mode: str | None = None, tags: Iterable[str] = (),
    task_profile: str | None = None, phase: str | None = None,
    selected_context_target_bytes: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Restore scope, refreshing every historical profile and phase from source."""
    body = checkpoint["body"]
    saved = body["selection"]
    levels = {"fast": 0, "focused": 1, "substantial": 2, "full": 3}
    chosen = saved["mode"]
    if mode is not None:
        if mode not in levels or levels[mode] < levels[chosen]:
            raise WisdomCompileError("resumption cannot narrow a saved mode; establish a fresh reviewed route")
        chosen = mode
    selected = set(saved["tags"]) | set(tags)
    profile_hint = task_profile or saved["task_profile_hint"]
    profiles = list(saved.get("task_profiles", filter(None, (saved["task_profile_hint"],))))
    phases = list(saved.get("phases", filter(None, (saved["phase"],))))
    if task_profile is not None and task_profile not in profiles:
        profiles.append(task_profile)
    if phase is not None and phase not in phases:
        phases.append(phase)
    force_full = False
    route_source_sha256 = None
    try:
        parsed = parse_source(Path(source_path).resolve())
        route_source_sha256 = parsed.source_sha256
        if "technology_continuity" in parsed.manifest["allowed_tags"]:
            selected.add("technology_continuity")
        # Expanded tags alone cannot refresh obligations after a source update.
        for profile in profiles:
            profile_mode, profile_tags = resolve_task_profile(parsed, profile)
            chosen = max((chosen, profile_mode), key=levels.__getitem__)
            selected.update(profile_tags)
        for phase_id in phases:
            selected.update(parsed.phase_by_id[phase_id]["tags"])
        if not set(body["module_ids"]).issubset(resolve_module_ids(parsed, mode=chosen, tags=selected)):
            force_full = True
    except (OSError, WisdomCompileError, KeyError, TypeError, ValueError):
        force_full = True
    companion = body["companion_source"]
    options = {
        "mode": "full" if force_full else chosen,
        "tags": sorted(selected),
        # Profiles were expanded above; preserving their old tags prevents narrowing.
        "task_profile": None,
        "phase": phase if phase is not None else saved["phase"],
        "selected_context_target_bytes": selected_context_target_bytes if selected_context_target_bytes is not None else saved["selected_context_target_bytes"],
        "companion_source_path": companion["path"] if companion else None,
        "expected_companion_sha256": companion["sha256"] if companion else None,
        "expected_companion_bytes": companion["bytes"] if companion else None,
        "expected_source_sha256": route_source_sha256,
    }
    continuity = {
        "checkpoint_sha256": checkpoint["checkpoint_sha256"],
        "previous_source_sha256": body["source_sha256"],
        "previous_content_sha256": body["content_sha256"],
        "task_profile_hint": profile_hint,
        "task_profiles": profiles,
        "phases": phases,
        "route_expanded_to_full": force_full,
        "reload_required": True,
        "project_evidence_recheck_required": True,
    }
    return options, continuity


def _default_source() -> Path:
    return Path(__file__).resolve().parents[1] / "WISDOM.md"


def _default_cache_root() -> Path:
    return Path.home() / ".codex" / "compiled" / "wisdom"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=_default_source())
    parser.add_argument("--cache-root", type=Path, default=_default_cache_root())
    parser.add_argument("--mode")
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--task-profile")
    parser.add_argument("--phase")
    parser.add_argument("--selected-context-target-bytes", type=int)
    parser.add_argument("--unknown-impact", action="store_true")
    parser.add_argument("--companion-source", type=Path)
    parser.add_argument("--expected-companion-sha256")
    parser.add_argument("--expected-companion-bytes", type=int)
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--save-route", type=Path, help="publish a new immutable task route checkpoint")
    parser.add_argument("--resume-route", type=Path, help="reload current rules from a saved task route")
    parser.add_argument("--project-root", type=Path, help="explicit project binding for route checkpoints")
    parser.add_argument("--task-id", help="explicit task binding for route checkpoints")
    parser.add_argument(
        "--prepare-cache",
        action="store_true",
        help="compile the current source into the selected cache before loading",
    )
    parser.add_argument("--emit-content", action="store_true")
    parser.add_argument("--emit-content-segment", type=int, metavar="INDEX")
    parser.add_argument("--expected-delivery-id")
    parser.add_argument(
        "--segment-bytes",
        type=int,
        default=DEFAULT_SEGMENT_BYTES,
        help=f"bounded delivery segment size ({MIN_SEGMENT_BYTES}-{MAX_SEGMENT_BYTES})",
    )
    args = parser.parse_args(argv)
    try:
        _validated_segment_bytes(args.segment_bytes)
        route_requested = args.save_route is not None or args.resume_route is not None
        if route_requested and (args.project_root is None or args.task_id is None):
            raise WisdomCompileError("route checkpoints require --project-root and --task-id")
        if not route_requested and (args.project_root is not None or args.task_id is not None):
            raise WisdomCompileError("project/task bindings require --save-route or --resume-route")
        if args.save_route is not None and (args.emit_content or args.emit_content_segment is not None):
            raise WisdomCompileError("save a route with a non-content plan, then read its complete delivery")
        if args.emit_content and args.emit_content_segment is not None:
            raise WisdomCompileError(
                "--emit-content and --emit-content-segment are mutually exclusive"
            )
        if args.discover:
            if (
                args.emit_content
                or args.emit_content_segment is not None
                or args.expected_delivery_id is not None
                or args.prepare_cache
                or route_requested
            ):
                raise WisdomCompileError(
                    "--discover cannot be combined with preparation or content emission"
                )
            plan = discover_capabilities(args.source)
        else:
            options = {
                "mode": args.mode, "tags": args.tag, "task_profile": args.task_profile,
                "phase": args.phase, "selected_context_target_bytes": args.selected_context_target_bytes,
                "companion_source_path": args.companion_source,
                "expected_companion_sha256": args.expected_companion_sha256,
                "expected_companion_bytes": args.expected_companion_bytes,
            }
            continuity = None
            if args.resume_route is not None:
                checkpoint = read_route_checkpoint(
                    args.resume_route, source_path=args.source,
                    project_root=args.project_root, task_id=args.task_id,
                )
                options, continuity = resume_route_options(
                    checkpoint, source_path=args.source, mode=args.mode, tags=args.tag,
                    task_profile=args.task_profile, phase=args.phase,
                    selected_context_target_bytes=args.selected_context_target_bytes,
                )
                if any(value is not None for value in (
                    args.companion_source, args.expected_companion_sha256, args.expected_companion_bytes
                )):
                    options.update(
                        companion_source_path=args.companion_source,
                        expected_companion_sha256=args.expected_companion_sha256,
                        expected_companion_bytes=args.expected_companion_bytes,
                    )
            if args.prepare_cache:
                if args.unknown_impact or options["mode"] == "full":
                    raise WisdomCompileError(
                        "cache preparation is not used for full-source loading"
                    )
                compile_and_install(args.source, args.cache_root)
            plan = load_plan(
                args.source,
                args.cache_root,
                unknown_impact=args.unknown_impact,
                **options,
            )
            if continuity is not None:
                plan = dict(plan)
                continuity["source_changed"] = plan["source_sha256"] != continuity["previous_source_sha256"]
                continuity["content_changed"] = sha256_bytes(read_plan_content(plan)) != continuity["previous_content_sha256"]
                plan["continuity"] = continuity
        if args.discover:
            print(canonical_json_bytes(plan).decode("utf-8"))
        elif args.emit_content:
            sys.stdout.buffer.write(read_plan_content_or_current_source(plan))
        elif args.emit_content_segment is not None:
            if args.expected_delivery_id is None:
                raise WisdomCompileError(
                    "--emit-content-segment requires --expected-delivery-id"
                )
            sys.stdout.buffer.write(
                read_delivery_segment(
                    plan,
                    args.emit_content_segment,
                    expected_delivery_id=args.expected_delivery_id,
                    segment_bytes=args.segment_bytes,
                )
            )
        else:
            if args.expected_delivery_id is not None:
                raise WisdomCompileError(
                    "--expected-delivery-id requires --emit-content-segment"
                )
            planned = dict(plan)
            planned["delivery"] = segmented_delivery_plan(
                plan,
                segment_bytes=args.segment_bytes,
            )
            if args.save_route is not None:
                planned["saved_route"] = save_route_checkpoint(
                    plan, args.save_route, project_root=args.project_root, task_id=args.task_id,
                )
            print(canonical_json_bytes(planned).decode("utf-8"))
    except (WisdomCompileError, OSError) as exc:
        print(f"wisdom load failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
