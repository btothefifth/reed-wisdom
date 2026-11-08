# T3 Code automatic-loading integration

The portable installer supports T3 Code through the underlying provider's
native instruction discovery. Follow the archive's
[installation instructions](wisdom-portable/README.md#automatic-loading-in-t3-code).
This file records the implementation boundary and evidence rather than adding
another source of WISDOM rules.

## Supported installation behavior

- Detect `t3` on `PATH`, or select `--t3` for a desktop installation without its
  CLI on `PATH`. Detection only checks command availability; it starts no server,
  provider, thread, or background process.
- Install the short source-specific router into the effective Codex
  `AGENTS.override.md`/`AGENTS.md`. Use the shared home from T3's provider
  settings, including for shadow accounts. A separate home needs separate setup.
- Offer Claude Code and OpenCode setup when their CLIs are detected **or** when
  their config directories are explicitly selected. The latter supports T3's
  custom binary paths. Explicit options take precedence over environment
  defaults: `CODEX_HOME`, `CLAUDE_CONFIG_DIR`, and `XDG_CONFIG_HOME` for OpenCode's
  global config directory.
- Preserve existing instruction content, line endings, Codex override precedence,
  per-target approval, backups, conflict preflight, and idempotence. A dry run or
  declined target remains unchanged. Existing equivalent user routers are kept.
- Report whether the selected files contain a current source-specific router
  after the installation decisions. A proposed router is reported missing until
  it is written. File presence does not claim provider discovery or compliance.

The source and Python tools must remain accessible at the installed path from
the actual provider environment. Repeat setup in remote, WSL, and container
environments. A worktree can use the same global router if it can access that
path. Project instructions, trust, permissions, provider flags, excluded files,
and instruction budgets still affect what the provider can read.

No T3 database, provider account, credential, general preference, orchestration
prompt, or hook is edited. Source-control writing-style custom instructions
govern source-control prose; they are not a general-purpose agent loader.
No undocumented `~/.t3/AGENTS.md` path is created. Other T3 providers have no
automatic installation claim here; Cursor editor User Rules do not establish
loading by its CLI through T3.

## Research baseline

Checked on 2026-11-07. The local command reports
`t3 v0.1.3-nightly.20261025.3682`; that identifies the available CLI, not a live
provider-loading trial. Current upstream documentation and implementation were
inspected at commit `a9e709f15f825cacac1b6d665fa1920c328d68b7`:

- [Installation and provider environments](https://github.com/pingdotgg/t3code/blob/a9e709f15f825cacac1b6d665fa1920c328d68b7/docs/user/install.md#providers):
  provider installation and configuration belong to the environment machine.
- [Codex account/home documentation](https://github.com/pingdotgg/t3code/blob/a9e709f15f825cacac1b6d665fa1920c328d68b7/docs/user/providers-codex.md#multiple-cli-logins)
  and [home materialization](https://github.com/pingdotgg/t3code/blob/a9e709f15f825cacac1b6d665fa1920c328d68b7/apps/server/src/provider/Drivers/CodexHomeLayout.ts):
  shared versus effective homes; instruction entries are shared into shadow homes.
  [Managed home selection](https://github.com/pingdotgg/t3code/blob/a9e709f15f825cacac1b6d665fa1920c328d68b7/apps/server/src/provider/CodexManagedHome.ts)
  uses the same layout owner.
- [Claude account documentation](https://github.com/pingdotgg/t3code/blob/a9e709f15f825cacac1b6d665fa1920c328d68b7/docs/user/providers-claude.md#separate-accounts-or-configurations)
  and [home resolution](https://github.com/pingdotgg/t3code/blob/a9e709f15f825cacac1b6d665fa1920c328d68b7/apps/server/src/provider/Drivers/ClaudeHome.ts):
  custom config directories use `CLAUDE_CONFIG_DIR`; `HOME` stays intact.
- Native instruction contracts: [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
  [Claude memory](https://code.claude.com/docs/en/memory), and
  [OpenCode rules](https://docs.opencode.ai/docs/rules/).
  [OpenCode custom configuration layers](https://docs.opencode.ai/docs/config/#custom-directory)
  must not be confused with its global instruction directory.

These sources establish the integration design. They do not prove that every
older or future T3/provider release loads the same instructions. No live
Claude/OpenCode session was launched during this implementation.

## Verification boundary and recovery

`tests/test_setup_wisdom.py` exercises T3 detection, explicit selection without
a CLI, effective Codex overrides, separate off-PATH provider directories,
partial approval, idempotence, environment defaults, explicit precedence, and
conflict rejection before writes. Existing installer tests cover preserved
content, backups, instruction limits, and concurrent-file-change rejection.

`test_extracted_t3_setup_installs_native_routers_without_provider_clis` in
`tests/test_build_wisdom_bundle.py` extracts the real archive into a path with
spaces. In a fresh process with isolated homes and an empty `PATH`, it runs the
actual setup entrypoint, verifies dry-run purity, supplies an interactive input
carrier, installs all three native routers, then repeats setup. It independently
reads the resulting files and verifies T3's unrelated preference file stayed
unchanged. This proves packaged installer behavior, not a model session.

The current complete repository suite passed on Linux with CPython 3.12.15
(422 passed, one Queue.shutdown version skip) and 3.14.4 (423 passed).
Installer/extraction cases passed within both complete runs. A disposable-copy
mutation removing explicit off-PATH OpenCode selection
made its owning regression fail at the intended routing assertion. The real
source stayed unchanged during that probe. The generated rule inventory and
rebuilt archive pass their drift checks. Hosted checks are reported by the
release workflow; fresh-session and compaction trials were not run locally.

## Local 1.20.1 installation

The authorized local release installation extracts the deterministic archive
to `/home/reed/.local/share/reed-wisdom/v1.20.1`, verifies all ten members, and
keeps their files read-only. Its source SHA-256 is
`2c0c01b249627fbdf496f0861eb0bf3835467e32f129fcde3450ac998b0df4ea`;
the archive SHA-256 is
`d49f85890baa878c4ee629b045e5f85e55b70ac10dcc89ba3d1321c83b629adb`.
The installed setup CLI migrated the exact sibling-version blocks in the local
Codex and OpenCode routers. It preserved each previous block in a
`.before-wisdom-aaa9dbd5647f498d.bak` backup beside the instruction file.
Provider settings and credentials were not edited; the active T3 Codex
provider's existing home is `/home/reed/.codex`.

The actual installed setup CLI reports both routers present. T3 supplied the
updated source-specific AGENTS instruction block in the active conversation
after installation. The installed loader then returned a verified Rust/Tokio
route; its 42,608 content bytes matched complete emission and two generation-bound
segments, with no unrelated Python asyncio guidance. All installed file names
and hashes remained unchanged. This proves the observed router delivery and
installed loading path; it does not prove model compliance or post-compaction
retention. Local installation receipts live outside the release tree at
`/home/reed/.local/share/reed-wisdom/installation-1.20.1.json`.

The earlier v1.20.0 tag remains immutable. Its release gate prevented archive
publication after Windows fixture encoding/newline failures and a Rust native
compilation timeout. Version 1.20.1 repairs the test surface: explicit UTF-8
source bytes, LF/CRLF byte-accounting cases, and compile-only borrowing checks
with the same E0505 negative oracle. The affected tests also pass locally with
UTF-8 mode disabled. Native linking is no longer claimed by the Rust capture
check; the timeout's underlying host cause was not established. The retained
v1.20.0 installation and its earlier backups provide local recovery evidence.

## Fresh-session follow-up

After installation, verify the actual provider session separately:

1. Start a fresh provider session or thread in the intended environment and
   project. Confirm the provider's instruction source includes the installed
   router; do not rely solely on a model's assertion.
2. Request a small representative task. Inspect its actual loader calls,
   verified source, selected technology tags, and complete rule-byte delivery.
   Mixed stacks need all applicable tags; the loader does not classify prose.
3. For ongoing work, save its project/task-bound route and keep the path,
   preferences, open failures, and next action in existing task state. After
   compaction or handoff, observe fresh resumption and all current rule bytes
   before dependent work. Recheck stack evidence and add new technologies.
4. Use an existing compiler/type/lint or behavioral check to verify a relevant
   principle in the actual result. Instruction delivery alone cannot prove it.

No universal T3 recovery callback is installed or assumed. The
[continuity guide](TECHNOLOGY_CONTINUITY.md) defines the portable recovery
procedure. A real host-compaction or comparative model-adherence trial remains
unperformed. Roll back an installer edit using its exact preserved backup after
checking for subsequent user changes; do not overwrite newer content blindly.
