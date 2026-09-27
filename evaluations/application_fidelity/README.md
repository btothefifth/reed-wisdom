# WISDOM application-fidelity evaluations

This directory is an authoring-time behavioral transfer kit for WISDOM. It is
not part of the operating kernel, does not add authority, and is not a required
user workflow. It lets an evaluator give the same high-level engineering task
to a model under three controlled instruction conditions and compare observable
work.

The kit requires only Python's standard library. It does not call a model API,
use the network, require CI, install hooks, or modify the repository under test.
The evaluator chooses and launches the model separately.

## Protocol

1. Prepare an isolated workspace:

   ```text
   python scripts/run_application_fidelity_eval.py prepare \
     --case acknowledged-not-reconciled --output <new-empty-path>
   ```

2. Run a fresh-session triad with the same model version and settings. Prepare a
   separate clean workspace for each arm:

   - **unassisted:** no WISDOM content;
   - **prior:** the exact routed view from the prior stable WISDOM release; and
   - **candidate:** the exact routed view from the candidate WISDOM release.

   Root each session only at its prepared directory and ask it to complete
   `TASK.md`. Do not expose this source repository, `cases.json`, or
   `oracles.py` to the model. Retain the exact routed bytes and source hash for
   each assisted arm.
3. Score the resulting workspace:

   ```text
   python scripts/run_application_fidelity_eval.py score \
     --case acknowledged-not-reconciled --workspace <prepared-path> \
     --allow-candidate-execution
   ```

4. Retain the raw model response, arm identity, model/version/settings, WISDOM
   source and routed-view hashes where applicable, workspace delta, and score
   vector. Compare all three arms case by case. The unassisted arm estimates the
   task/model baseline, the prior arm controls for existing WISDOM, and the
   candidate arm measures the proposed instructional change. Never reuse a
   conversation or mutated workspace across arms.

`self-check` proves that every seed contains its intended defect, every held-out
reference repair satisfies its oracle, and every declared go-red mutation
reaches and fails its named criterion:

```text
python scripts/run_application_fidelity_eval.py self-check
```

## Evidence boundary

The deterministic score covers final behavior, affected-consumer coverage,
current evidence, preserved behavior, and bounded workspace changes. It cannot
prove a model's private reasoning or the exact time at which it refreshed a
phase checklist. Transcript observations about process timing must be reported
separately as observer-coded evidence.

Scoring imports and executes model-written Python with the evaluator process's
operating-system authority. Preparation isolation keeps held-out evidence away
from a cooperative model; it is not a security sandbox, and a timeout does not
contain child processes. The CLI therefore refuses `score` unless the evaluator
passes `--allow-candidate-execution`. Run untrusted outputs only in a disposable
least-authority environment that has no secrets, external authority, or network
access. The kit measures cooperative model output and is not tamper-resistant;
adversarial candidate code could interfere with the interpreter or oracle.

The ordinary pytest file for this kit validates its schema, path containment,
preparation isolation, deterministic scoring, and oracle sensitivity. A green
pytest result proves the evaluation mechanism is internally consistent. It does
not prove that any model learned or applied WISDOM.

The cases are deliberately small and neutral. They test whether a model can
apply reusable engineering distinctions without relying on project-specific
names, services, repositories, accounts, or infrastructure.

## Explicit successor suite

The original `cases.json`, `oracles.py`, eight seed cases, and recorded v1.10
result remain the historical v1 suite. Commands without `--suite` still select
v1. The repository-only v2 suite is in `cases.v2.json` and `oracles_v2.py`:

```text
python scripts/run_application_fidelity_eval.py list --suite v2
python scripts/run_application_fidelity_eval.py prepare --suite v2 \
  --case recover-dependent-checks --output <new-empty-path>
python scripts/run_application_fidelity_eval.py score --suite v2 \
  --case recover-dependent-checks --workspace <prepared-path> \
  --allow-candidate-execution
python scripts/run_application_fidelity_eval.py self-check --suite v2
```

The cases cover six distinct behaviors:

| Case | Required behavior and preserved twin |
| --- | --- |
| `conditional-delivery` | Remote delivery waits for its required confirmation; local delivery does not wait for unrelated confirmation. |
| `uncertain-slot` | Timeout retains the current owner and occupancy; proven creation failure and observed completion free only the matching slot. |
| `recover-dependent-checks` | All checks reading changed inputs are invalidated; unrelated checks remain usable, and a durable report matches final implementation and input bytes. |
| `effective-source-and-outcomes` | An explicit clock remains effective after final setup; every enabled destination remains present in supplied order even when a public assertion expects an incomplete count. |
| `fixture-owner-triage` | A stale fixture is repaired at its owning test seam while the correct production expiry guard remains byte-identical. |
| `already-correct-normalizer` | Existing supported behavior passes with zero changed files; unnecessary edits and product artifacts fail. |

V2 preparation and score receipts bind the selected suite, case, complete oracle
module, semantic oracle specification, evaluator runner bytes, and exact product
seed inventory. `runner_sha256` identifies
`scripts/run_application_fidelity_eval.py` in both receipts. Scoring rejects
missing or changed runner bindings as well as mixed suite generations. A runner
change requires a fresh preparation; do not silently update an earlier marker
to make its generation appear current. Retain the original trial evidence when
reporting a later evaluation under changed scoring rules.

Existing-file changes and additions share one case-specific file budget. Added
product files require an exact `allowed_added_paths` entry; only ancestor
directories needed for those paths are permitted. Deletion is not permitted,
and ordinary empty directories remain subject to the exact scope contract.
The evaluator-owned preparation marker is excluded from the delta inventory;
its bound fields are independently checked before scoring.

V2 excludes standard transient Python artifacts from correctness and file-budget
inventory: `__pycache__` trees, `.pytest_cache` trees, and standalone `.pyc`
files. The score reports their exact relative paths separately in
`transient_python_artifacts`, with `informational_only: true`; directory paths
end in `/`. This field can report cleanup without making a worker's tool choice
part of task correctness. For example, `py_compile` writes bytecode even when
ordinary bytecode suppression is enabled. Cache paths cannot be declared as
product additions. Cache-like product filenames, undeclared durable state,
ordinary empty directories, deletions, stale generations, and case budgets
remain strict. These v2 rules do not change historical v1 scoring.

The no-op seed intentionally satisfies its contract already. `self-check`
requires that seed to pass unchanged, while every defective seed must expose a
failure. Both kinds require passing held-out reference output and failing
intentional mutations. Reference repairs demonstrate one solution, not the
required implementation layout or lesson wording. Oracles do not score lesson
headings, explanatory prose, or a model's private reasoning.

The durable report is a final-source/input witness. Its matching hash does not
prove that a model actually ran a particular command or performed a review at a
particular time; those observations require independently retained execution
and transcript evidence. The recorded
[`v1.11.0-gpt-6-luna-high.json`](results/v1.11.0-gpt-6-luna-high.json)
trial is one controlled solo-worker run: all three arms passed four cases. It
therefore supplies bounded non-regression and transfer evidence, not comparative
correctness improvement; its edit, token, and elapsed measurements also do not
show an efficiency gain for v1.11 on this small corpus. Green integrity tests or
`self-check` alone do not establish improved model behavior.

The v1.12 receipt
[`v1.12.0-gpt-6-luna-high.json`](results/v1.12.0-gpt-6-luna-high.json)
uses fresh isolated arms for the two new cases. Unassisted, v1.11, and v1.12
passed both and changed the same three files. The v1.12 arm used more reported
tokens and elapsed time, so this is bounded application and non-regression
evidence, not a correctness or efficiency advantage. The other four v2 cases
were integrity-tested against their references and go-red mutations but were
not rerun with models for this receipt.

## Workflow-neutral trials and evidence

The evaluator may run each fresh-session triad with a single worker, multiple
workers sharing one capability setting, or workers with different capability
settings. The kit neither launches workers nor requires a particular model,
vendor, orchestration workflow, or CI system. Hold the chosen worker topology,
role assignment, permissions, tools, environment, handoff conditions, and total
budget constant across the three arms. Record worker settings and every handoff;
include all worker effort in cost accounting. A comparison that adds a stronger
worker only to the candidate cannot attribute its gain to WISDOM.

For future behavioral evidence, retain exact instruction bytes and hashes,
prompt identity, per-check score vectors, final workspace inventory, raw
responses, failures, interventions, and unavailable measurements. Compare
terminal correctness, preserved behavior, honest unresolved state, and scope
before tool-call, token, or elapsed-cost differences. Include instruction loading,
all workers, retries, and unsuccessful runs in cost accounting. Prose length and
the number of named process steps are not behavioral success metrics.

Use development cases to qualify the harness and freeze thresholds before
opening confirmation variants. Do not coach a scored run or leak hidden scores.
Classify infrastructure invalidations with independent evidence, retain their
record, and rerun comparable arms consistently. Candidate failures and budget
exhaustion are scored outcomes. New confirmation variants and controlled
interruptions or handoffs are needed for broader or long-horizon claims; these
six small deterministic cases do not supply that evidence by themselves.
