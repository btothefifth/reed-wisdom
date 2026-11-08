# WISDOM portable bootstrap

This archive is a self-contained engineering operating bootstrap for an AI
agent. `WISDOM.md` is the sole authored authority. The bundled tools use only
the Python standard library to create and verify smaller exact-byte views;
they do not add rules and their output has no independent authority.

## Optional coding-agent setup

After extraction, users of Codex, OpenCode, Claude Code, Cursor, or T3 Code may run the
bundled setup helper:

```text
python scripts/setup_wisdom.py --source WISDOM.md
```

It checks the effective global `AGENTS.md`/`AGENTS.override.md` guidance and
the `config.toml` in that `CODEX_HOME`. When the `opencode` CLI is on `PATH`, it
also offers a WISDOM-specific edit to OpenCode's global
`~/.config/opencode/AGENTS.md`. When the `claude` CLI is on `PATH`, it offers a
separate edit to Claude Code's user-wide `~/.claude/CLAUDE.md`, shared by its
CLI and desktop app. Each instruction-file target has its own exact preview
and separate explicit consent; declining or running without interactive input
leaves that target unchanged. Use `--opencode-config-home` or
`--claude-config-home` when those config directories are elsewhere; these explicit
options also offer setup when the provider executable is outside `PATH`.
Detected providers default to `$CLAUDE_CONFIG_DIR` and
`$XDG_CONFIG_HOME/opencode` when set, otherwise to the locations above.
`--codex-home` overrides `$CODEX_HOME` or its default `~/.codex`.

When `cursor-agent` or `cursor` is on `PATH`, the helper prints the exact
WISDOM instruction and directs you to add it manually under Cursor Settings >
Rules. Cursor documents User Rules as global plain text settings, but does not
document a supported global rule-file path for the helper to edit. The helper
does not modify Cursor settings or OpenCode's `opencode.json`, model settings,
or workflows.

Codex model-context numbers and experimental feature flags are
environment-dependent suggestions, not portable defaults; unsupported or
uncertain settings are reported rather than silently applied. Existing user
content remains authoritative unless the user approves a specific edit.
For model and feature remediation, `--schema` and `--model-catalog` accept
local JSON evidence. Without that evidence, the helper reports uncertainty
and proposes no numeric or feature defaults. It does not resolve project
instructions, CLI flags, selected profiles, project config layers, or live
model capabilities. After an approved edit, verify the effective guidance and
settings in a fresh Codex session.

This helper is optional. File/Python-capable agents can use the complete WISDOM
source without installation or configuration changes.

## Automatic loading in T3 Code

T3 Code runs coding providers on the selected environment's machine. Install
WISDOM there and use the provider's native instruction file; the desktop or
mobile client's configuration is insufficient for an agent running elsewhere.
The helper detects `t3` on `PATH`. Use `--t3` to show its integration checks
when the desktop app's CLI is unavailable:

```text
python scripts/setup_wisdom.py --source WISDOM.md --t3
```

Match the setup target to **Settings > Providers** for that environment:

| T3 provider | WISDOM router location | Setup option |
| --- | --- | --- |
| Codex | Effective `AGENTS.override.md` or `AGENTS.md` in its shared `CODEX_HOME` | `--codex-home /absolute/shared/codex-home` |
| Claude Code | `CLAUDE.md` in its actual `CLAUDE_CONFIG_DIR` | `--claude-config-home /absolute/claude-config` |
| OpenCode | `AGENTS.md` in its global config directory | `--opencode-config-home /absolute/global/opencode-config` |

For example, install for a custom T3 Codex home with:

```text
python scripts/setup_wisdom.py --source WISDOM.md --t3 --codex-home /absolute/shared/codex-home
```

Repeat for separate provider homes. For a Codex shadow account, use its shared
home; T3 prepares the shared instruction entries in the shadow home when the
provider starts. Do not copy credentials or populate shadow homes yourself.
Claude account directories remain separate. For OpenCode, a custom
`OPENCODE_CONFIG_DIR` is an additional configuration layer; it does not by itself
establish that directory as the global instruction-file location. Match the
global directory actually read by the installed provider.

Keep the archive at its installed absolute path. The provider must be able to
read the source and run its loader, including from project worktrees. Repeat
installation inside each applicable WSL distro, SSH host, or container; host
paths do not automatically exist inside them. A provider's permissions or
project rules can affect loading and access.

The helper reports `router present` only after reading the installed target.
That is a file check. Verify provider discovery in a fresh provider session or
thread: ask the agent to identify its instruction source and load WISDOM, then
inspect the actual loader calls, selected tags, and complete content delivery.
Existing threads may retain their prior instructions. The installed router
automatically requests per-task loading; the agent still has to execute the
loader and select applicable technologies. Setup does not pre-load every rule.

For long tasks, save the task-bound route described below. After compaction or
handoff, recover that route and read all current rule bytes before continuing.
This integration installs no T3 compaction hook and cannot guarantee adherence.
Other T3 providers require their own verified instruction route. Cursor's
editor User Rules are not evidence of loading by T3's Cursor CLI provider.
The helper does not write `~/.t3/AGENTS.md` or use source-control writing-style
preferences as general agent instructions.

This integration follows [T3's provider installation guidance](https://github.com/pingdotgg/t3code/blob/main/docs/user/install.md#providers),
[Codex home/account guidance](https://github.com/pingdotgg/t3code/blob/main/docs/user/providers-codex.md),
and [Claude configuration guidance](https://github.com/pingdotgg/t3code/blob/main/docs/user/providers-claude.md).
Native instruction contracts are documented by [Codex](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
[Claude Code](https://code.claude.com/docs/en/memory), and
[OpenCode](https://docs.opencode.ai/docs/rules/). Recheck them when upgrading.

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

The ordinary implementation route includes SEM-01 enforcement for policy
reuse, closed dispatch, cohesive ownership, and request lifecycle boundaries.
Add the discovered architecture, storage, or delivery tags when design/owner maps,
persistent schema evolution, or generated distribution artifacts are affected;
these rules stay with their existing owners rather than adding a separate
architecture workflow.

Material acquisition, schema, large-query/replay and data growth work selects
the existing storage route automatically, even when phrased as collection or
analysis. For example, add `--tag storage` to the implementation profile before
designing a historical-input pipeline. The model plans with compact verified
results; deterministic tools compute the large-data results within explicit
intermediate-state and lifecycle budgets. Read-only access and disk spill do
not remove resource, privacy or recovery obligations. A routine bounded edit
does not require a new engine, benchmark, artifact or workflow.

When discovery advertises phases, add the current phase to select its required
rules and re-route before each later phase's protected action. An unknown phase
requires the full source. Optional selected-context accounting reports the
combined WISDOM and companion bytes and flags an over-target result without
discarding rules:

```text
python scripts/load_compiled_wisdom.py --source WISDOM.md --cache-root .wisdom-cache --task-profile bug_fix --phase validate --selected-context-target-bytes 131072
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
Segments end at complete UTF-8 characters and may be slightly shorter than the
requested byte bound. Use their declared offsets/lengths. Delivery identity binds
the current tools even for full-source fallback; invalid UTF-8 is rejected.

Profiles are explicit aliases, not a natural-language classifier. If the task
does not fit a profile or a missed mechanism could change the outcome, use
`--discover` and then `--unknown-impact` so the loader returns the full current
source.

## Conditional technology modules

The technology library covers language design, concurrency, and testing for
Python, Rust, Go, Java, C++, Ruby, and Rails, plus JavaScript/TypeScript, React,
Next.js, Vue, Svelte, Node, Django, FastAPI, Spring, C#, and Kotlin. Database
modules distinguish SQL/relational, PostgreSQL, MySQL, SQLite, columnar,
ClickHouse, DuckDB, time-series, graph, document, Redis, wide-column, search,
vector, and migration concerns. Additional tags cover UI/accessibility, HTTP,
jobs, Kafka, containers, Kubernetes, observability, dependencies, security,
Terraform, and shell practices.

Additional submodules cover Rust API idioms, Vite build/deployment boundaries,
Node runtime testing, Docker builds, and Kubernetes security. When a cloud
deployment target is known, include its constraints during application design:
`cloud_architecture`, applicable `cloud_identity` or `serverless`, and only the
actual `aws`, `gcp`, or `azure` target. A cloud target does not select an
orchestrator automatically.

Run discovery, inspect the actual project versions and affected callers, then
select explicit tags. For a Python concurrency edit:

```text
python scripts/load_compiled_wisdom.py --source WISDOM.md --cache-root .wisdom-cache --prepare-cache --task-profile code_change --tag python_asyncio --tag python_testing --tag ai_codegen --emit-content
```

For a React UI task, the optional `react_ui` profile loads component, effect,
test, UI, and accessibility guidance; add `--tag typescript` only when the
project actually uses TypeScript. For an existing database query, select the
real engine, such as `--tag postgres` or `--tag clickhouse`. Use the
`database_selection` tag when choosing an engine and `database_migrations`
when schema/data evolution is affected. Normal task modes and phases do not
implicitly select every language or database.

Dependencies load shared preference and parent-language guidance. Concurrency
and test modules remain separately selectable; an ordinary `python` tag does
not automatically load asyncio, and a `react` tag does not mandate Next.js or
TypeScript. The loader does not scan the project or classify natural language.
Its technology tags are the agent's explicit selection after inspection.
Discovery also exposes `modules[].routing_hints`: current authored loading
conditions and preference fields for checking applicability before selection.
These are navigation metadata; read the selected complete rule bytes.
The optional `scripts/inspect_wisdom_stack.py --project-root <root> --path <relative-path>`
suggests candidate tags from bounded local files and ancestor manifests. It
executes no project code. Review path/reason evidence, file hashes, scan limits,
and omissions; suggestions never automatically select a loader route.
Version evidence preserves declared runtime/dependency constraints, editions,
and toolchain selectors from supported local metadata. It does not resolve
lockfiles, reconcile conflicts, or probe installed runtimes. A declared range
is not permission to use every API from its newest possible version.
Opaque reference values are hash-bound rather than echoed with possible URL credentials.
Framework-neutral service profiles do not choose FastAPI or Spring; add those
tags only when the application uses them. Stack profiles are conveniences,
not package installation requests or universal architecture recommendations.

Use `technology_verification` to translate applicable guidance into the existing
compiler, type, lint, policy, and behavior checks. Choose checks for the changed
failure mechanism; do not run every representative proof or add competing tools.

Explicit current user preferences and controlling project conventions override
technology defaults. Verify minimum supported versions before adopting modern
syntax or APIs, and keep preview/experimental features conditional. References
in each module record a research baseline, not a live update feed. The whole
library remains available in the accompanying `WISDOM.md` without network
access or generated caches; apply only guidance whose trigger is relevant.

The manifest's `kernel_max_bytes` is a compiler guard on the always-read kernel,
not a model context window or a maximum for selected modules. Inspect the plan's
`selected_context` for the complete route plus any companion. The optional
`--selected-context-target-bytes` reports an advisory target; it never truncates
rules. Segmented delivery bounds tool responses, not the combined model context.
Keep automatic project instructions as a short loader router and reserve model
context for the task, repository evidence, and execution. Increase a host's
instruction-file limit only for demonstrated delivery truncation after checking
the actual host configuration; do not expand WISDOM merely to fill a larger
model window.

## Recovering discipline after compaction

The loader verifies selected bytes; it cannot guarantee that a host retains
them through compaction. New setup-generated routers and the example bootstrap
explicitly require fresh reading after compaction, restart, or handoff. Existing
equivalent user guidance is preserved, and no host recovery hook is installed.

For material long work, keep the current objective, user preferences and their
sources, stack/versions, open failures, evidence dependencies, and next action
in existing task state. Save a generated task route alongside it:

```text
python scripts/load_compiled_wisdom.py --prepare-cache --task-profile vite_ui --tag typescript --project-root <project-root> --task-id change-42 --save-route <project-root>/.wisdom-context/change-42.route.1.json
```

Record the exact checkpoint path in the existing task-state pointer. Checkpoints
are immutable new paths inside the bound project; use a new generation filename
after updating a route. They carry routing metadata and source/content hashes,
not preferences, task progress, secret values, or replacement rule summaries.

After context loss, recover task state and request a new plan:

```text
python scripts/load_compiled_wisdom.py --resume-route <project-root>/.wisdom-context/change-42.route.1.json --project-root <project-root> --task-id change-42
```

Read all returned content paths or segments using the new delivery ID. Wrong
project/task/source bindings and corrupted checkpoints are rejected. Current
profiles and historical phases are re-resolved, earlier expanded tags remain, stale companions fail,
and recovery guidance is added automatically when the current source provides it.
A full-source route cannot silently narrow. A new phase adds obligations;
it does not discard applicable earlier ones. To retire obsolete scope, establish
a fresh reviewed route. Recheck current project evidence for new technologies
and preferences; a saved route cannot discover future stack changes.

Version 2 checkpoints preserve accumulated profile/phase identities across
successive saves. Version 1 remains readable and upgrades on saving; review
existing task state for earlier identities that the old format never stored.
Lost owners or source changes between expansion and loading require full source.

Use `technology_continuity` when recovery applies. If the route is absent or
invalid, reconstruct it from current instructions and evidence; use the full
current source for material unresolved applicability. Neither a checkpoint,
summary, source hash, nor successful previous turn proves ongoing compliance.

The current tools and archive have been tested end to end with Python 3.12.15
and 3.14.4. The hosted matrix targets Python 3.12.10 and 3.14.4; it was not run locally.
Compatibility with earlier Python versions has not been verified.

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
- `scripts/setup_wisdom.py` — optional consent-based provider setup, including T3 Code routes
- `examples/PROJECT_BOOTSTRAP.md` — project-router template

The archive contains no generated cache, runtime state, accounts, credentials,
or environment-specific paths.
Fill the example's paths and any frozen companion receipt before using it.
