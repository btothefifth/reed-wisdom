# Example project bootstrap for WISDOM v1.6.0

This is a template for a project's short `AGENTS.md` router, not an additional
WISDOM authority. Replace the example paths and frozen companion receipt before
using it. Keep the complete v1.6.0 archive under the governing project root,
for example at `vendor/wisdom/v1.6.0/`.

> Resolve the governing repository root first. Treat
> `<root>/vendor/wisdom/v1.6.0/WISDOM.md` as the sole portable WISDOM source.
> Run its own `scripts/load_compiled_wisdom.py --source
> <root>/vendor/wisdom/v1.6.0/WISDOM.md --discover` before routing. Choose the
> smallest discovered task profile, phase, or tag set that includes every
> applicable hard rule. When impact or mapping is uncertain, use
> `--unknown-impact` and read the full current source. Read every path in the
> verified load plan, or every generation-bound segment in order. A plan or
> cache receipt alone is not instruction content. Explicit user instructions
> and verified facts take precedence.

If the project has a separate rule source, bind it to the same load call with
the **frozen** byte length and SHA-256 recorded by the project owner:

```text
--companion-source <root>/AGENTS.rules.md
--expected-companion-bytes <frozen-decimal-byte-count>
--expected-companion-sha256 <frozen-64-character-lowercase-sha256>
```

Do not replace either value with a fresh hash computed from the file being
loaded: that would make a changed companion self-attesting. When a generated
WISDOM view is missing or stale, read the complete current WISDOM source. If
the companion is missing or its frozen receipt mismatches, stop and repair the
trusted companion binding before acting on project-specific rules. Do not copy
project-specific rules into portable `WISDOM.md`.
