# WISDOM portable bootstrap

This archive is a self-contained engineering operating bootstrap for an AI
agent. `WISDOM.md` is the sole authored authority. The bundled tools use only
the Python standard library to create and verify smaller exact-byte views; they do not
add rules and their output has no independent authority.

## File/Python-capable coding agents

Use the verified route when the agent can read files and run Python. Extract
the archive, read this README, and run these commands from the extracted
directory. Choose any writable cache directory; `.wisdom-cache` keeps it beside
the extracted files.

First discover the actual modes, tags, dependencies, and manifest-owned task
profiles:

```text
python scripts/load_compiled_wisdom.py --source WISDOM.md --discover
```

Prepare the current source and exact tool versions, then produce a verified
focused load plan:

```text
python scripts/load_compiled_wisdom.py --source WISDOM.md --cache-root .wisdom-cache --prepare-cache --mode focused
```

Cache preparation is explicit because it writes generated files. Omit
`--prepare-cache` when local writes are forbidden; the loader remains read-only
and returns the complete source fallback if no current cache exists. The
standalone compiler command remains available when preparation and loading must
be separate:

```text
python scripts/compile_wisdom.py --source WISDOM.md --cache-root .wisdom-cache
```

Select the smallest verified route that preserves every mechanism applicable to
the task. For a known request shape, prefer its discovered task profile; use
the explicit mode and discovered tags when no profile fits. For example:

```text
python scripts/load_compiled_wisdom.py --source WISDOM.md --cache-root .wisdom-cache --task-profile code_change
```

The loader prints a JSON plan. Read the files listed in `content_paths`, in
order. To write their verified content directly instead, add `--emit-content`.
Use `--tag TAG` one or more times only after discovery shows the relevant tags.
Apply the selected WISDOM view proportionally, then verify the current source
and produce the task's terminal deliverable.

```text
python scripts/load_compiled_wisdom.py --source WISDOM.md --cache-root .wisdom-cache --task-profile code_change --emit-content
```

When a selected view plus a project companion may exceed one response limit,
use bounded delivery. First retain the plan's `delivery.delivery_id`,
`delivery.segment_bytes`, and complete ordered segment receipts. Then emit each
zero-based segment with the same inputs and exact delivery ID:

```text
python scripts/load_compiled_wisdom.py --source WISDOM.md --cache-root .wisdom-cache --task-profile code_change --emit-content-segment 0 --expected-delivery-id <64-hex-id>
```

Read every declared segment once and in order. Each invocation revalidates the
whole generation; a changed source, tool, cache, companion, segment size, or
delivery ID is rejected. Concatenated segment bytes must match the plan's
complete content hash and byte count before the instruction delivery is called
complete.

Profiles are explicit aliases, not a natural-language classifier. If the task
does not fit a profile or a missed mechanism could change the outcome, use
`--discover` and then `--unknown-impact` so the loader returns the full current
source.

The tools have been tested end to end with Python 3.12.10. Compatibility with
earlier Python versions has not been verified.

## Chat-only or full-source fallback

If the agent cannot run Python, or if the task's impact is uncertain, give it
the complete `WISDOM.md` with this instruction:

> Read `WISDOM.md` as the operating bootstrap for this task. Apply its
> precedence, routing, evidence, authority, and stop/act rules proportionally.
> If anything needed for the task is uncertain, use the full file and retain
> every applicable higher-risk mechanism through the terminal deliverable.

No installation, generated files, repository, account, or Codex-specific setup
is required. `WISDOM.md` remains complete and usable by itself. Missing, stale,
changed, corrupt, or ambiguous compiled state returns a `full_source_required`
plan; read the current `WISDOM.md` in that case. Never treat a stale kernel,
generated module, cache pointer, or loader receipt as a replacement authority.

A project may bind one larger project-specific instruction source as an exact
companion without putting those rules into portable WISDOM. Supply its path,
independently recorded byte count, and SHA-256 together:

```text
python scripts/load_compiled_wisdom.py --source WISDOM.md --cache-root .wisdom-cache --mode focused --companion-source PROJECT-RULES.md --expected-companion-bytes 12345 --expected-companion-sha256 <64-lowercase-hex>
```

The loader appends the exact companion bytes after the selected WISDOM view and
rechecks them during content reading. It rejects a missing, truncated,
mismatched, or post-plan-changed companion. The companion remains a separate
project authority and is intentionally excluded from `WISDOM.zip`.

If a capable agent needs to request the full source explicitly:

```text
python scripts/load_compiled_wisdom.py --source WISDOM.md --cache-root .wisdom-cache --mode focused --unknown-impact
```

## Archive contents

- `VERSION` — product release version
- `CHANGELOG.md` — release history
- `WISDOM.md` — complete standalone authority
- `README.md` — this start guide
- `scripts/compile_wisdom.py` — deterministic optional compiler
- `scripts/load_compiled_wisdom.py` — provenance-checking optional loader
- `scripts/check_changed_text.py` — explicit-path Git text-integrity preflight

The archive contains no generated cache, runtime state, accounts, credentials,
or environment-specific paths.
