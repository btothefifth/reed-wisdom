# reed-wisdom

WISDOM is a portable engineering operating kernel for coding agents. It turns
high-level objectives into proportionate planning, implementation, testing,
delivery, and correction behavior while preserving user authority and evidence.

The complete authority is [`WISDOM.md`](WISDOM.md). The compiler and loader are
optional standard-library tools that create smaller byte-verified views; they
never add authority or replace the source.

**Current source:** 1.20.1, including the checked-in [WISDOM.zip](WISDOM.zip).
Download the pinned [v1.20.1 release archive](https://github.com/btothefifth/reed-wisdom/releases/download/v1.20.1/reed-wisdom.zip).

**Published downloads:** [latest `reed-wisdom.zip`](https://github.com/btothefifth/reed-wisdom/releases/latest/download/reed-wisdom.zip)
or the previous pinned [v1.19.1 archive](https://github.com/btothefifth/reed-wisdom/releases/download/v1.19.1/reed-wisdom.zip).

## Start

Download the release archive, extract it, and follow
[`docs/wisdom-portable/README.md`](docs/wisdom-portable/README.md). A capable
agent can begin with:

```text
python scripts/load_compiled_wisdom.py --source WISDOM.md --discover
python scripts/load_compiled_wisdom.py --source WISDOM.md --prepare-cache --mode focused
```

The second command prepares and verifies a local cache, then returns a load
plan. For content too large for one tool response, use the plan's delivery ID
and segment receipts as described in the portable README.

For automatic loading in **T3 Code**, run the optional setup helper on the
machine where its provider runs:

```text
python scripts/setup_wisdom.py --source WISDOM.md --t3
```

It uses the provider's native instruction files, including custom Codex,
Claude Code, and OpenCode directories. See the portable
[T3 installation instructions](docs/wisdom-portable/README.md#automatic-loading-in-t3-code)
and the [integration evidence and limits](docs/T3_CODE.md).

Before reviewing or staging explicitly touched Git text files, the bundled
preflight can detect mixed or accidental line-ending expansion:

```text
python scripts/check_changed_text.py --repo . --path path/to/changed-file
```

## Versioning

The current product version is in [`VERSION`](VERSION). Releases use Semantic
Versioning and immutable `vMAJOR.MINOR.PATCH` tags. `WISDOM.md` also carries a
`semantic_revision`; that counter changes when the source/compiler contract
changes and is intentionally separate from the product version.

The deterministic `WISDOM.zip` is rebuilt from the tracked portable inputs and
checked in with each release. Releases publish it as `reed-wisdom.zip`.
Pushing a matching version tag runs the platform/Python test matrix before a
release job uploads that archive as a draft and publishes it. Only that job
receives repository-content write permission. Existing releases are not overwritten.

## Development

Runtime tools use only the Python standard library. Tests require pytest:

```text
python -m pytest
python scripts/report_technology_modules.py --check
python scripts/build_wisdom_bundle.py --check
```

The 1.20.1 source adds 79 conditional technology modules and 362 identified
rules for language design, concurrency, testing, web frameworks, databases, and
common operations stacks. Read the complete [rule inventory](docs/TECHNOLOGY_MODULES.md)
and [adoption/uncertainty report](docs/TECHNOLOGY_DECISIONS.md).
The [implementation review](docs/TECHNOLOGY_REVIEW.md) covers Rust idioms,
Vite/Node, cloud deployment, Docker/Kubernetes, prose, context, and enforcement.
The [loading and continuity guide](docs/TECHNOLOGY_CONTINUITY.md) documents
bounded stack suggestions, task route checkpoints, and fresh rule loading after
compaction. These tools improve recovery; they cannot guarantee model retention.
The inspector preserves version declarations without inferring installed API
support. Five source-extracted examples have runtime/compiler checks and
intentional defect checks; the review records their exact scope and limits.
These are repository reports; the full portable rules and sources live in
`WISDOM.md`. User preferences and project conventions override technology
defaults. Existing task modes retain their selections: add discovered technology tags
or an optional stack profile only for the actual affected technologies.

Maintainers can use the repository-only
[application-fidelity evaluations](evaluations/application_fidelity/README.md)
to compare the same less-capable model unassisted, with a prior stable release,
and with a candidate release. The kit is release evidence, not a user
requirement, CI assumption, or part of the portable archive. Unselected ideas
remain in the [potential backlog](docs/BACKLOG.md).

WISDOM is model-, vendor-, workflow-, and topology-neutral. One instruction-
following worker can execute the complete method serially. Multiple workers of
the same or different capabilities are optional and remain subject to the same
authority, evidence, integration, and completion requirements. Hosted services,
delegation, continuous integration, and network access are never prerequisites
for ordinary use.

No license is granted by this repository unless a license file is added in a
later release.
