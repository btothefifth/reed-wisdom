# Changelog

All notable changes to WISDOM are recorded here. Releases follow Semantic
Versioning. The source manifest's `semantic_revision` is an independent
compiler-facing contract counter and does not replace the product version.

## 1.0.1 - 2026-09-13

- Reject Git option-shaped comparison revisions before invoking Git.
- Reject Windows drive paths and repository-escaping resolved paths.
- Fail when tracked UTF-8 text becomes binary, UTF-16, or invalid UTF-8.

## 1.0.0 - 2026-09-13

- Establish WISDOM as a standalone, versioned engineering operating kernel.
- Preserve deterministic compilation and byte-verified proportional loading.
- Add explicit cache preparation and bounded, generation-bound content delivery.
- Require failed cheap preflights to stop unnecessary downstream validation.
- Add accidental line-ending and disproportionate-diff detection guidance.
