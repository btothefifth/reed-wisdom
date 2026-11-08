# Technology loading and continuity through compaction

Authoring baseline: 2026-11-07. WISDOM.md remains the sole portable rule source.
This report explains the optional tools, application procedure, and evidence limits.

## What was and was not guaranteed

Before this refinement, explicit tags correctly selected dependency-closed,
source-verified content. Tests covered exact delivery, unrelated-module exclusions,
corruption fallback, and complete context accounting. Technology classification
still depended entirely on the agent. A plan or cache receipt did not prove that
content was read, retained through compaction, or applied correctly.

That distinction remains important. The new tools improve discovery and recovery;
they do not make a portable Markdown library control the host's memory. OpenAI's
[compaction documentation](https://developers.openai.com/api/docs/guides/compaction)
describes opaque continuation state, and the
[Codex command documentation](https://learn.chatgpt.com/docs/developer-commands)
describes replacing earlier turns with a concise summary. Neither establishes
verbatim preservation of an arbitrary earlier WISDOM tool result in every host.
No claim about T3's private compaction implementation follows from those pages.

## Discover the actual affected stack

The optional standard-library helper reads bounded local files and suggests tags:

```text
python scripts/inspect_wisdom_stack.py --project-root /work/app --path web/src
```

Repeat `--path` for disjoint affected paths. Paths are relative to the explicit
project root. A file or subdirectory includes its ancestor manifests, without
scanning unrelated sibling services. With no paths, inspection considers the
root within explicit bounds. The helper excludes common dependency/build/cache
trees, skips symlinks, and executes no manifests, scripts, package managers,
network calls, imports from the project, or deployment commands. Its defaults
are 600 considered files, 128 KiB per file, 4 MiB of examined file contents, and
6,000 directory entries. CLI flags expose those bounds.

Output includes candidate tags, individual path/reason evidence, examined-file
hashes and sizes, the WISDOM source hash, and issues such as missing paths,
unparsed manifests, unreadable files, changed files, symlinks, and exhausted
bounds. `partial` must not be interpreted as an empty or exhaustive stack.
`bounded_scan_complete` means completion within that enumerated scope and the
supported heuristics; it does not establish semantic completeness.

Review candidates against real callers. A dependency can be optional, unused,
test-only, or a build tool; an extension can identify generated or inactive code.
A Node engine declaration may describe Vite's build toolchain, not a deployed
Node server. Syntax hints are lexical, not a language parser or call graph.
Hints are limited to compatible source families so a Python file containing
Java/Rust/Go pattern strings does not suggest those runtimes. Embedded or
generated code targeting another family still requires explicit caller review.
The additive `version_evidence` array preserves declared constraints, editions,
and toolchain selectors with their path and field/directive. Parsed data fields
use JSON Pointer escaping; plain version files use an empty field. Opaque
references/selectors containing URL/path syntax or line breaks have `value: null`,
`value_status: opaque_selector`, and a SHA-256 of the declared value. This avoids
echoing reference credentials/query tokens; inspect the bound source when needed.
It is not a general secret scanner. Ordinary version constraints stay readable.
Supported
sources are package.json (engines and known dependencies), pyproject.toml
(requires-python, dependencies, extras, development groups, Poetry dependencies),
Cargo package/workspace/target metadata, go.mod, rust-toolchain.toml, global.json,
and .python-version/.node-version/.nvmrc/.ruby-version/.java-version. Ancestor
metadata is included, so a root manifest can still suggest an unrelated owner;
the caller review remains necessary. Group includes and inherited versions are
not resolved; ancestor declarations remain separate observations.

`version_interpretation` explicitly reports compatibility `not_evaluated`, runtime
`not_probed`, and lockfile resolution `not_parsed`. Constraints and selectors
can conflict; both remain visible, without inventing one effective project
version. Check the installed runtime, resolved lockfiles, and minimum supported
targets separately before choosing an API. A dependency's version is not its
parent language/framework version. Malformed declarations produce `partial`
instead of a clean applicability claim. `bytes_read` counts all actual read
bytes, including rejected content; `evidence_bytes` counts stable UTF-8 files
retained as evidence. Oversized files are skipped before content reading.

Test-library declarations and lexical hints can suggest the relevant testing
module, including React Testing Library, Playwright, pytest-asyncio, Rust test
attributes, Go test files, JUnit/TestNG, native C++ frameworks, and RSpec/Minitest.
These hints do not prove the tests execute or choose a runtime for a neutral
runner such as Vitest/Jest.

Add mechanisms, database engines, deployment targets, unsupported technologies,
and new-file intentions manually where the helper cannot identify them. A
known deployment target can apply before any provider manifest exists.

The candidate report is never automatically fed into `--tag`. Current user
preferences and controlling project conventions decide the approach; actual
runtime semantics still constrain it. The loader independently validates tags
against the current source and closes their dependencies.

Run `load_compiled_wisdom.py --discover` to inspect `modules[].routing_hints`.
These expose each available module's authored loading condition and engineering
preference fields, with section identity and heading, from the current source.
Use them to check mechanisms that lexical inspection can miss, including new
concurrency work, testing changes, and an intended deployment target. They are
navigation metadata: read the selected complete rule bytes before applying them.
Neither discovery API automatically selects a technology or overrides preferences.

## Save the selected route and retain the task state

For material work likely to outlast the current context, create a new checkpoint:

```text
python scripts/load_compiled_wisdom.py --prepare-cache --task-profile vite_ui --tag typescript --phase implement --project-root /work/app --task-id change-42 --save-route /work/app/.wisdom-context/change-42.route.1.json
```

This returns the ordinary verified plan and a `saved_route` path/hash. Read all
content paths or generation-bound delivery segments. Saving a route only
validates bytes on disk; it does not prove that the model read them.

Use an existing project-native plan/current-state record to retain:

- The objective, current task ID, project root, governing WISDOM path, and exact
  latest route-checkpoint path. Include a task-state pointer in any recovery
  handoff or compaction summary that the host exposes.
- Current user preferences and decisions with their source and supersession,
  supported stack/versions, affected paths/owners, and a known deployment target.
- Unresolved failures and uncertainty, completed evidence and its dependencies,
  the next action, and any still-applicable authority or recovery boundary.

These are public task facts and decisions, not private reasoning or secrets.
The checkpoint stores routing metadata, source/content hashes, expanded tags,
module identities, profile/phase lineage, the byte target, and any companion
binding. It does not store user preferences, task progress, test results,
external authority, or a replacement rule summary. Keep those in their existing
controlling owners. The checkpoint is a generated navigation view, not a fifth
independent source of project requirements.

Checkpoint paths must be inside the bound project and must be new. Publication
links complete temporary bytes without overwriting an existing generation;
a failed publication removes its owned temporary file. Use a new filename for
each update and advance the pointer in existing task state only after success.
Checkpoint publication requires hard-link support on its filesystem. If it is
unavailable, retain route fields in existing task state and reconstruct an
ordinary verified load; failure does not authorize a partial checkpoint.
A plain checksum detects accidental corruption; it is not authentication or
permission to trust arbitrary repository instructions. Use a canonical root and
explicit task identity; copied/moved workspaces need a fresh reviewed route.

## Recover before the first dependent action

After compaction, restart, or handoff, recover the current router and task state,
then plan current delivery from the saved route:

```text
python scripts/load_compiled_wisdom.py --resume-route /work/app/.wisdom-context/change-42.route.1.json --project-root /work/app --task-id change-42
```

The loader rejects malformed/oversized/duplicate-key/corrupt checkpoints and
mismatched project, task, or WISDOM paths. It resolves the current source and
current profile dependencies, preserves the previous expanded tags and phase
obligations, and retains the exact companion binding. Resumption also selects
`technology_continuity` when the current source provides it, so recovery guidance
does not depend on remembering an extra tag. A stale companion fails; it is not
silently omitted or self-approved with a freshly computed hash. Rebinding it
requires independently justified current project authority.

`continuity` in the returned plan reports source/content changes, any forced
full-source expansion, and the need to reload and recheck project evidence.
Read every current rule byte. Do not act merely because the checkpoint says
which modules were previously selected. Missing or stale caches use the normal
complete-source fallback; optional `--prepare-cache` rebuilds a compiled route
when allowed. It is unnecessary and rejected for full-source routes.

For bounded delivery, retain the **new plan's** delivery ID and segment size,
then read every declared index using those unchanged inputs:

```text
python scripts/load_compiled_wisdom.py --resume-route /work/app/.wisdom-context/change-42.route.1.json --project-root /work/app --task-id change-42 --emit-content-segment 0 --expected-delivery-id <new-plan-delivery-id>
```

Repeat for every segment. A source/tool/route change invalidates the old delivery
ID. Do not join segments from different generations. Segmentation bounds tool
responses; it does not reduce total context or prove host retention.
Each segment now ends at a complete UTF-8 character and is independently
decodable. Receipts retain exact offsets, lengths, and hashes; their concatenation
preserves every original byte. Delivery identity also binds the current tools
for full-source fallback, where compiled-build tool bindings are absent.
Invalid UTF-8 instruction content is rejected before emission.

Recheck current user instructions, affected callers/manifests, supported runtime,
and known deployment target. New code or a scope change may introduce tags that
the saved route could not know. The loader always marks this evidence recheck
as required; it does not claim a route file detects stack drift automatically.
If the checkpoint is missing or rejected, recover routing from current trusted
instructions and project evidence. Material unresolved applicability requires
the complete current source, not an empty route or an old remembered summary.

## Advance the task without forgetting earlier obligations

Add tags and a new phase/profile while retaining earlier expanded scope:

```text
python scripts/load_compiled_wisdom.py --resume-route /work/app/.wisdom-context/change-42.route.1.json --project-root /work/app --task-id change-42 --phase validate --tag node_testing --save-route /work/app/.wisdom-context/change-42.route.2.json
```

Resume can broaden a mode and add a profile; earlier tags remain. Every saved
profile and phase is reevaluated against the current source, including owners
from earlier checkpoint generations. A removed/unresolvable profile or phase,
a source change between route expansion and loading, or a closure that would
lose prior modules expands to the full current source. A saved
full-source route cannot silently become a smaller route. Explicit mode
narrowing is rejected. When a technology truly leaves scope, review its trigger
and create a fresh ordinary route; do not edit a checkpoint to suppress it.

New checkpoints use `wisdom.route_checkpoint.v2` to retain all accumulated
profile/phase identities. Version 1 remains readable and upgrades on the next
save, preserving its known profile, phase, and expanded tags. A version 1 record
cannot reconstruct earlier identities it never stored; review its prior task
state when that history matters. Duplicate, malformed, or contradictory lineage
is rejected even when its checksum is recomputed. Library callers must attach
the `continuity` returned by `resume_route_options` to the resulting plan before
saving it again; the CLI does this automatically.

Scope preservation is deliberately conservative, not a universal rule to retain
every old tag forever. Completed phases do not automatically retire rules that
still govern the result. A fresh reviewed route may remove obsolete tags while
preserving all still-applicable obligations. Checkpoints are task-specific:
do not reuse an old task's route as the default for a new task.

Apply each selected principle to the changed invariant and responsible owner,
then choose the cheapest useful existing check. Keep current user preferences
as design inputs. Revalidate results when their code/input/configuration/
environment dependencies changed or cannot be recovered; preserve unaffected
results and open failures. A stored source hash alone is not proof of an actual
test execution. All technology profiles now include the shared verification
module; the continuity module remains conditional on a recovery boundary.

## Host integration and evaluation boundary

New setup-generated routers explicitly request fresh rule loading after
compaction, restart, and handoff. The project-bootstrap template includes that
procedure. Existing equivalent user-authored global guidance is preserved;
this update does not silently rewrite global instructions or install hooks.

T3 Code installation uses those same provider-native routers. The
[T3 integration guide](T3_CODE.md) covers custom homes, shared/shadow accounts,
remote environments, packaged installer evidence, and fresh-session checks.
It does not add a T3 compaction callback.

Where the actual host exposes a supported recovery callback, an integrator can
recover the trusted task pointer, invoke the current loader, supply all verified
bytes in the active context, and record delivery completion before allowing
dependent work. The callback must preserve the host's ordinary instructions,
current user preferences, task isolation, source checks, and failures. Verify
its actual event/API and ordering; do not infer that every Codex, T3, Claude,
OpenCode, or Cursor host exposes the same callback. No such hook was installed
or host lifecycle control claimed by this portable update.

Tests start a fresh subprocess with a checkpoint and compare actual emitted
content with an independent prior verified view, including segmented delivery.
They cover corrupted and cross-task records, changed source/delivery identity,
phase/profile growth and narrowing, full-source fallback, immutable publication,
and stale companion rejection. Discovery tests cover scope, unsupported inputs,
bounds, nonexecution, and excluded paths. These tests establish deterministic
recovery behavior, not real model memory or instruction following.

For behavioral evaluation, extend the existing
[application-fidelity protocol](../evaluations/application_fidelity/README.md).
Use matched unassisted/prior/candidate runs with the same host, model/settings,
permissions, budgets, and recovery schedule. At a fixed milestone compact or
restart each arm under the same conditions; retain only its permitted router
and task state, with current user preferences and a known unresolved failure.
Test independent outcomes after recovery: stale React response prevention,
Vite's separate type check, Node upgraded-socket shutdown, Rust caller borrowing,
and effective cloud identity are useful distinct families. Include a simpler
valid user-preferred alternative and a scope change introducing another stack.
Score behavior, preserved scope/preferences, honest failure status, unnecessary
work, and total loading/execution cost. Do not grade rule-ID repetition.

No model-provider trial or real host compaction experiment was run here.
A correct loader plus a useful router improves recoverability; continuing
application remains something to verify through real outcomes.
