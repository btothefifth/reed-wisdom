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
