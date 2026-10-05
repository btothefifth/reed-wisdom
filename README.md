# reed-wisdom

WISDOM is a portable engineering operating kernel for coding agents. It turns
high-level objectives into proportionate planning, implementation, testing,
delivery, and correction behavior while preserving user authority and evidence.

The complete authority is [`WISDOM.md`](WISDOM.md). The compiler and loader are
optional standard-library tools that create smaller byte-verified views; they
never add authority or replace the source.

**Download:** [latest `reed-wisdom.zip`](https://github.com/btothefifth/reed-wisdom/releases/latest/download/reed-wisdom.zip)
or the pinned [v1.13.0 archive](https://github.com/btothefifth/reed-wisdom/releases/download/v1.13.0/reed-wisdom.zip).

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

## Development

Runtime tools use only the Python standard library. Tests require pytest:

```text
python -m pytest
python scripts/build_wisdom_bundle.py --check
```

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
