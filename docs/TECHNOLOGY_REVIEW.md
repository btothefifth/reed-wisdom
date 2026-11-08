# Technology implementation review: prose, context, and enforcement

Review baseline: 2026-11-07. This is an authoring report, not portable authority.
Reviewed source SHA-256: `b997973ab8c44fe052329c82e80eb4922f4abb9f608e0161b39a132fb59418f1`.

The review covers every rule, trigger, preference surface, dependency, proof
prompt, and reference placement in the technology library: 79 modules and 362
identified rules. It includes all 66 modules from the first draft plus 13 new
modules. It is a serial author review with primary-source checks and independent
mechanical delivery tests, not a separate reviewer or a model-effectiveness
experiment. The 26 pre-existing modules are retained and byte-checked; their
entire prose was not rewritten in this change.

The complete final wording is in [the generated inventory](TECHNOLOGY_MODULES.md).
[Adoption decisions](TECHNOLOGY_DECISIONS.md) retain uncertain defaults and
unresearched candidates.

## Findings and repairs

1. **The context limit was easy to misread.** The 42,000-byte field guards only
   the compiled kernel. Focused and substantial views are larger, and full mode
   reads the complete raw source. The inventory now reports every mode and
   profile's complete dependency-closed bytes. Tests compare those numbers with
   actual verified loader output. An advisory target must not remove rules.
2. **Proof caveats were duplicated and the examples could look mandatory.**
   Removed 66 repeated caveats (14,124 bytes) and put the scope rule in TECH-06,
   a dependency of every technology module. Prompts are selected for changed
   mechanisms and available evidence. Added technology_verification for choosing
   actual project checks without mandatory tools, hooks, CI, or per-rule forms.
   The later version-specific refinements add targeted rules and executable
   examples; their complete current delivery cost is measured below.
3. **Idiomatic Rust guidance needed a concrete public-API layer.** The existing
   types/ownership/error/runtime advice was useful, but did not cover conventional
   borrowed arguments, conversions, standard traits, public compatibility, or
   rustdoc sufficiently. Added rust_api and a base rule for matching, iteration,
   and semantically appropriate derives; avoided builder/generic/async mandates.
4. **Build and deployment targets were incomplete.** Added Vite and separate
   cloud architecture, identity, serverless, AWS, GCP, and Azure modules. TECH-02
   now includes a known deployment target while designing application code.
   Cloud does not select Kubernetes, and Vite does not select React/TypeScript
   or imply a production Node server.
5. **Node's modern execution and lifecycle boundaries needed precision.** Added
   native TypeScript execution limits, separate type analysis, explicit HTTP
   resource budgets, upgraded-connection shutdown, and runtime-specific tests.
6. **Docker and Kubernetes had good initial summaries but missed actionable
   detail.** Added build-cache/input/final-runtime checks and effective pod/RBAC/
   network-policy checks. Clarified CPU-limit tradeoffs and the fact that PDBs
   do not constrain a Deployment's own rolling-update strategy.
7. **Two broad rules needed narrower application.** React nested updates now
   explicitly copy the changed branch and ancestors. Migration immutability
   distinguishes retained/shared installations from explicitly disposable local
   state under project policy. The earlier POSIX pipefail correction remains.


8. **Selection and post-compaction recovery lacked durable tooling.** Added a
   bounded advisory stack inspector and immutable project/task-bound route
   checkpoints. Resume reloads the current source, expands current profiles,
   preserves earlier tags and companion bindings, rejects narrowing, and exposes
   drift. It also selects available recovery guidance automatically. New setup
   routers request fresh reading after context loss. No host
   hook, automatic classifier, or model-retention guarantee is implied.
9. **Application and retained proof needed one shared owner.** All technology
   profiles now include verification. TECH-07 binds advice to changed invariants
   and owners; TCHECK-05 invalidates only evidence with changed/unrecoverable
   dependencies. Conditional continuity rules retain user preferences, open
   failures, and the unfinished objective through recovery.
10. **Byte boundaries could corrupt text-tool delivery.** Segments now end at
    complete UTF-8 characters while preserving exact offsets, lengths, hashes,
    and reassembly. Invalid UTF-8 instructions are rejected. Delivery identity
    now binds current tools even for full-source fallback, preventing reuse of
    a receipt from a different segmentation implementation.

## Prose standard used in the review

Each rule should tell the agent what observable boundary matters, what action
to take, what mistake to avoid, and where project/version choices change the
recommendation. Keep one owner for shared preference and proof scope. Use
explicit conditions instead of unqualified always/never tool mandates, but keep
real semantic prohibitions direct. Keep the most likely contrast near the
instruction: transpilation versus type checking, timeout versus stopped work,
acknowledgment versus effect, or policy YAML versus enforcement.

The review did not force every rule into an eight-heading template or add a
worked example to every paragraph. That would make loading larger and can
obscure the governing distinction. Existing rule IDs, small paragraphs, scoped
proof prompts, and primary links are retained. A worked example is warranted
when task evidence shows that the compact instruction is insufficient.

These are authoring judgments. Official OpenAI guidance supports contextual
routing and trimming redundant instructions; it does not prove these specific
edits improve Sol, Luna, Astra, or any other model. See
[OpenAI's guidance on contextual instructions](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra).

## Recursive refinement passes

This continuation retained the 79-module boundary and refined 18 modules,
adding 13 rules to reach 362. It advanced semantic revision 22 to 23 within
the unreleased 1.20.0 candidate. The always-loaded kernel remains 32,606 bytes;
the complete source is 623,430 bytes. The table below records all current rules,
including the additions, rather than only the changed modules.

1. **Source-wide design pass.** Read all 79 technology modules and their
   preference/trigger/proof contracts. Recheck consequential modern API details
   against primary sources. Keep the existing ownership, user override, older
   target, database, and deployment alternatives. Select precise failure cases
   instead of adding a new framework or one example to every rule.
2. **Version and contradiction pass.** Revisit changed modules with their
   language/runtime/testing parents and the whole-library dependency frontier.
   Separate future Send from implementor Send, owned future cancellation from
   detached tasks, queue drain from discarded work, context binding from access
   control, and build success from lint/type/behavior proof. Correct inspector
   field locations, inherited declarations, malformed shapes, direct references,
   and development-group discovery. Preserve conflicting declarations rather
   than inventing a resolved version or excluding a user's supported target.
   Bind opaque reference values by hash instead of echoing possible URL credentials.
3. **Consumer and package pass.** Exercise every technology tag/profile through
   existing source-byte/closure checks and the real extracted CLI. Run authored
   examples with independent outcome assertions and intentional defects. Revisit
   the repaired inspector: rejected reads must consume its total budget, a short
   read must remain partial, and a fresh invocation must preserve the project/tool
   file frontier. Limit lexical hints to compatible source families while retaining
   actual JVM interoperability. Return the Rust example's future to an awaiting
   owner instead of discarding it in a demonstration helper. Recheck all unchanged
   module/section hashes, report freshness,
   baseline modes, recovery, and the deterministic archive. This serial pass
   supplies no separate-reviewer or model-compliance claim.

The inspector now emits path/field-bound `version_evidence` for supported
metadata and explicit `not_evaluated`/`not_probed`/`not_parsed` interpretation
states. It remains advisory and standard-library-only. See the
[precise field and supported-source contract](TECHNOLOGY_CONTINUITY.md#discover-the-actual-affected-stack).
Development groups follow the declaration shapes in the
[Python packaging specification](https://packaging.python.org/en/latest/specifications/dependency-groups/);
the inspector does not resolve group activation, includes, or dependency compatibility.

The 13 newly identified rules are listed here for review navigation; the
[inventory](TECHNOLOGY_MODULES.md) contains their complete wording from WISDOM.md:

| New rule | Concrete discipline | Version condition |
| --- | --- | --- |
| PY-06 | Compatible type syntax, deferred-annotation introspection, and no untrusted annotation evaluation | Type parameters/aliases 3.12+; annotation changes 3.14+ |
| PYASYNC-07 | Bounded admission, drain versus discard, and queue accounting versus durable success | Queue.shutdown 3.13+; older owned sentinel/cancellation paths retained |
| PYASYNC-08 | Initialize invariants before task creation; eagerness changes execution order | Eager factory 3.12+; create_task eager_start 3.14+ |
| RAPI-06 | Promise the future bounds generic callers need; verify dyn dispatch instead of adding Arc/unsafe/extra lifetime bounds | Native async trait/opaque return support 1.75+; actual dyn contract |
| RAPI-07 | Correct opaque lifetime capture without gratuitous cloning | Precise capture 1.82+; Rust 2024 edition 1.85+ |
| GOCON-06 | Correct WaitGroup.Go counting/spawn/panic contract; preserve error and cancellation ownership | 1.25+; Add-before-launch path on older targets |
| GOTEST-05 | Deterministic concurrent testing within a bubble's scope and correct benchmark iteration control | Stable synctest 1.25+; b.Loop 1.24+ |
| JCON-06 | Bounded request-context bindings, mutable-content safety, and explicit propagation limits | Finalized ScopedValue in JDK 25; earlier previews separately gated |
| NODE-07 | Per-request AsyncLocalStorage stores, scoped run, and tested callback propagation | Stable AsyncLocalStorage from 16.4; target runtime still checked |
| REACT-06 | Cached immutable external-store snapshots and consistent initial server/client state | useSyncExternalStore 18+ or a compatible established adapter |
| SQLITE-05 | Foreign-key setup before Python transaction policy, no accidental commits, and explicit close ownership | Python sqlite3 autocommit API 3.12+; actual SQLite library checked |
| PG-06 | Allowed/denied RLS operations as the application role, owner/bypass distinctions, and clean tenant pool reuse | Actual engine/policy contract; PostgreSQL 18 reference is a checked baseline |
| KOTLIN-05 | StateFlow current-state conflation, private mutable ownership, atomic safe-to-repeat updates, and explicit durable-event alternatives | Supported kotlinx.coroutines APIs, separately from Kotlin language version |

The other seven refined modules keep their existing rule IDs: Tokio cancellation,
React Effect/transition boundaries, Vue watcher cleanup, Next lint checks, Rails
strong parameters, C# ValueTask/WhenAll, and C++ compiler/library feature checks.
Their changes are recorded in the every-module table below.

Five compact examples live only in the authored WISDOM sections. The
[semantic tests](../tests/test_technology_semantics.py) extract those exact bytes:

| Authored example | Independent positive oracle | Deliberate defect and intended failing boundary |
| --- | --- | --- |
| Python queue drain, 3.13+ | Both accepted values are processed before return | Immediate shutdown discards them; the processed-values assertion fails |
| Python SQLite initialization, 3.12+ | A valid foreign key commits; an invalid one raises IntegrityError; the caller closes | Opening the transaction first makes PRAGMA ineffective; enforcement readback rejects initialization |
| Rust precise capture, 2024/1.85+ | An owned count stays usable after dropping the input | Removing use<> produces borrow error E0505 at the real caller |
| Rust async trait, 1.75+ | A generic consumer can require the returned future to be Send | Removing the public future bound produces E0277 despite the concrete implementation |
| Node request context, stable AsyncLocalStorage | Two overlapping async operations retain distinct IDs; caller context is empty | Replacing run with enterWith leaks context to the caller and fails its assertion |

These tests execute language/runtime contracts without installing packages or
toolchains. They do not grade generated model output or prove every design rule.
The Python 3.13+ example skips on 3.12 deliberately; the hosted matrix now
includes 3.14.4 so its version-specific path has an intended CI owner. Optional
native tests record missing/old-tool skip reasons and fail a broken discovered
tool instead of silently declaring it unavailable. Use pytest -rs to display skip
reasons; CI now includes that flag.

## Every-module review record

Each row covers every listed rule's final body as well as its trigger,
preferences, dependencies, proof prompt, and references. The test suite checks
that this record names every current technology module/rule and the current
source hash. That check establishes audit coverage and freshness, not semantic
correctness of the review.

| Module | Reviewed rule IDs | Review disposition |
| --- | --- | --- |
| `technology_preferences` | `TECH-01`, `TECH-02`, `TECH-03`, `TECH-04`, `TECH-05`, `TECH-06`, `TECH-07` | Centralized proof scope in TECH-06; kept user/project precedence and version checks; added known deployment targets to design selection and concrete owner/invariant application. |
| `ai_codegen` | `AIGEN-01`, `AIGEN-02`, `AIGEN-03`, `AIGEN-04`, `AIGEN-05` | Kept independent oracles, dependency verification, complete feature wiring, and scoped security checks; no current-model capability or efficacy claim. |
| `python` | `PY-01`, `PY-02`, `PY-03`, `PY-04`, `PY-05`, `PY-06` | Retained functions versus invariant-owning classes, built-install verification, runtime validation, safe defaults, and actual GIL/build distinctions. Added version-gated type syntax and deferred-annotation/introspection safety. |
| `python_asyncio` | `PYASYNC-01`, `PYASYNC-02`, `PYASYNC-03`, `PYASYNC-04`, `PYASYNC-05`, `PYASYNC-06`, `PYASYNC-07`, `PYASYNC-08` | Retained TaskGroup/gather distinction, cancellation propagation, blocking-thread ownership, loop scope, and controlled scheduling; no universal async mandate. Added queue drain versus discard semantics and eager-start ordering; an authored queue example has positive and deliberately broken runtime checks. |
| `python_testing` | `PYTEST-01`, `PYTEST-02`, `PYTEST-03`, `PYTEST-04` | Retained existing runner, narrow fixture lifetimes, consuming-namespace patching, installed imports, and plugin/loop compatibility. |
| `rust` | `RUST-01`, `RUST-02`, `RUST-03`, `RUST-04`, `RUST-05`, `RUST-06` | Added match/iterator/trait idioms with readable-loop exceptions; retained domain types, ownership, error, unsafe, edition, and MSRV boundaries. |
| `rust_tokio` | `TOKIO-01`, `TOKIO-02`, `TOKIO-03`, `TOKIO-04`, `TOKIO-05`, `TOKIO-06` | Retained runtime choice, supervised/bounded tasks, short standard-mutex exception, select cancellation safety, and non-abortable blocking-work ownership. Clarified losing an owned future versus a borrowed JoinHandle, detached tasks, abort/join, and retained cleanup ownership. |
| `rust_testing` | `RUSTTEST-01`, `RUSTTEST-02`, `RUSTTEST-03`, `RUSTTEST-04` | Retained public integration/doctest scope, parallel-test isolation, target/feature checks, and optional risk-specific tools; no blanket all-features command. |
| `go` | `GO-01`, `GO-02`, `GO-03`, `GO-04` | Retained consumer interfaces, useful zero values, error wrapping, slice aliasing, and language-version loop semantics; no interface-per-struct default. |
| `go_concurrency` | `GOCON-01`, `GOCON-02`, `GOCON-03`, `GOCON-04`, `GOCON-05`, `GOCON-06` | Retained bounded goroutines, context ownership, sender closure, compound synchronization, and exercised-schedule limits of race detection. Added Go 1.25 WaitGroup.Go accounting, panic/error limits, and the older Add-before-launch path. |
| `go_testing` | `GOTEST-01`, `GOTEST-02`, `GOTEST-03`, `GOTEST-04`, `GOTEST-05` | Retained native runner, isolated parallelism, owner-observed worker errors, meaningful fuzz invariants, and production-shaped benchmarks. Added stable Go 1.25 synctest versus the older experiment and Go 1.24 benchmark Loop, retaining scope and version limits. |
| `java` | `JAVA-01`, `JAVA-02`, `JAVA-03`, `JAVA-04`, `JAVA-05` | Retained records versus identity classes, shallow immutability, constructor dependencies, explicit null/error contracts, and configured release compatibility. |
| `java_concurrency` | `JCON-01`, `JCON-02`, `JCON-03`, `JCON-04`, `JCON-05`, `JCON-06` | Retained virtual-thread workload limits, downstream admission, actual-JDK preview checks, interruption, and JDK-specific pinning; no blanket synchronized rewrite. Added finalized JDK 25 ScopedValue, immutable binding versus mutable content, and executor propagation limits. |
| `java_testing` | `JTEST-01`, `JTEST-02`, `JTEST-03`, `JTEST-04` | Retained JUnit/runtime compatibility, focused framework tests, real database semantics, and observed worker failures; no forced major-version upgrade. |
| `cpp` | `CPP-01`, `CPP-02`, `CPP-03`, `CPP-04`, `CPP-05` | Retained RAII, unique/shared/borrowed distinctions, rule of zero, invariant classes, numeric/error policy, and compiler plus library/ABI compatibility. Strengthened the supported compiler/library feature-test or compile-probe gate. |
| `cpp_concurrency` | `CPPCON-01`, `CPPCON-02`, `CPPCON-03`, `CPPCON-04`, `CPPCON-05` | Retained joining ownership, cooperative stop, locks/atomics, coroutine capture/frame lifetime, bounded work, and destruction-order checks. |
| `cpp_testing` | `CPPTEST-01`, `CPPTEST-02`, `CPPTEST-03`, `CPPTEST-04` | Retained existing runner and targeted native boundaries; sanitizer configurations remain supported, separate where needed, and limited to exercised behavior. |
| `ruby` | `RUBY-01`, `RUBY-02`, `RUBY-03`, `RUBY-04` | Retained cohesive objects/modules, Data versus Struct/class, nested mutability, ensure/rescue behavior, and implementation/gem compatibility. |
| `ruby_concurrency` | `RUBYCON-01`, `RUBYCON-02`, `RUBYCON-03`, `RUBYCON-04` | Retained GVL/runtime distinctions, observed thread completion, scheduler-dependent fibers, and version/gem-gated Ractors; no generic parallelism promise. |
| `ruby_testing` | `RUBYTEST-01`, `RUBYTEST-02`, `RUBYTEST-03` | Retained chosen Minitest/RSpec style, isolated globals/fixtures, verified doubles, real adapters, and reproducible randomized order. |
| `rails` | `RAILS-01`, `RAILS-02`, `RAILS-03`, `RAILS-04`, `RAILS-05` | Retained conventional ownership, resource authorization, database constraints, query shape, commit/effect separation, and reload safety; no mandatory service objects. Added Rails 8 shape-aware params.expect and explicit attribute limits while preserving older require/permit. |
| `rails_jobs` | `RAILSJOB-01`, `RAILSJOB-02`, `RAILSJOB-03`, `RAILSJOB-04` | Retained executor/connection ownership, adapter-specific enqueue/commit semantics, durable retry identity, and pool budgets. |
| `rails_testing` | `RAILSTEST-01`, `RAILSTEST-02`, `RAILSTEST-03`, `RAILSTEST-04` | Retained request/model/job seams, real commit visibility, separate scheduling/effect assertions, and honest fixture/query behavior. |
| `javascript` | `JS-01`, `JS-02`, `JS-03`, `JS-04` | Retained runtime/module boundaries, shallow-alias risks, awaited promise ownership, Promise.all non-cancellation, and preserved failure causes. |
| `typescript` | `TS-01`, `TS-02`, `TS-03`, `TS-04` | Retained unknown-to-validated boundaries, discriminated states, project-controlled strictness, and readable schema-aligned types; no runtime guarantee from assertions. |
| `node` | `NODE-01`, `NODE-02`, `NODE-03`, `NODE-04`, `NODE-05`, `NODE-06`, `NODE-07` | Added native TypeScript limits and HTTP/security budgets; made HTTP shutdown, upgraded sockets, and background consumers explicit. Added per-request AsyncLocalStorage context and scoped run versus enterWith leakage; the authored example checks overlapping async callers. |
| `web_ui` | `UI-01`, `UI-02`, `UI-03`, `UI-04`, `UI-05` | Retained task-first design, complete interaction states, persistence/draft ownership, adaptive layout, and truthful rendered evidence; visual taste stays user-owned. |
| `web_accessibility` | `A11Y-01`, `A11Y-02`, `A11Y-03`, `A11Y-04`, `A11Y-05` | Retained semantic controls, keyboard/focus ownership, exposed state/errors, perceptual access, and limits of automated conformance claims. |
| `web_testing` | `WEBTEST-01`, `WEBTEST-02`, `WEBTEST-03`, `WEBTEST-04` | Retained semantic locators, observable waits, independent contexts, real critical flows, and reviewed failure/visual evidence. |
| `react` | `REACT-01`, `REACT-02`, `REACT-03`, `REACT-04`, `REACT-05`, `REACT-06` | Clarified copying the changed branch and ancestors; retained render purity, one state owner, stable keys, truthful hook dependencies, and selective optimization. Added React 18 external-store snapshots, stable subscriptions, and matching server/hydration state. |
| `react_effects` | `REFFECT-01`, `REFFECT-02`, `REFFECT-03`, `REFFECT-04`, `REFFECT-05` | Retained derivation/event/effect separation, symmetric cleanup, stale-result suppression, version-gated Effect Events, and limited transition/Suspense guarantees. Refined async Effect cleanup, React 19.2 Effect Event restrictions, post-await transition marking, and request-order limits. |
| `react_testing` | `REACTTEST-01`, `REACTTEST-02`, `REACTTEST-03`, `REACTTEST-04` | Retained DOM outcomes, rerender/unmount/request-order adversaries, realistic providers, and real-browser scope for hydration/focus/layout. |
| `nextjs` | `NEXT-01`, `NEXT-02`, `NEXT-03`, `NEXT-04`, `NEXT-05` | Retained actual router/runtime, narrow client graph, per-entrypoint authorization, explicit cache identity, and hydration/route checks; no remembered cache defaults. Added Next.js 16 lint removal and separate configured validation, without a forced upgrade. |
| `vue` | `VUE-01`, `VUE-02`, `VUE-03`, `VUE-04` | Retained project API style, version-sensitive destructuring/reactivity, computed versus watch, disposal, and public interaction checks. Added Vue 3.5 synchronous onWatcherCleanup registration before await with the supported callback alternative. |
| `svelte` | `SVELTE-01`, `SVELTE-02`, `SVELTE-03`, `SVELTE-04` | Retained compiler/mode compatibility, derivation versus effects, server-request isolation, and public/hydration evidence without forced syntax migration. |
| `django` | `DJANGO-01`, `DJANGO-02`, `DJANGO-03`, `DJANGO-04` | Retained domain/query ownership, installed-version async/transaction bridging, tenant scope, database constraints, and committed-behavior tests. |
| `fastapi` | `FASTAPI-01`, `FASTAPI-02`, `FASTAPI-03`, `FASTAPI-04` | Retained sync-helper versus async-loop distinction, request/response validation boundaries, lifespan cleanup, and honest BackgroundTasks durability limits. |
| `spring` | `SPRING-01`, `SPRING-02`, `SPRING-03`, `SPRING-04` | Retained constructor injection, actual proxy interception, context/thread ownership, and focused integration tests; annotations alone are not runtime proof. |
| `database_selection` | `DBSEL-01`, `DBSEL-02`, `DBSEL-03`, `DBSEL-04`, `DBSEL-05` | Retained family/product distinctions, workload invariants, operations/recovery cost, representative evidence, and overridable engine choices. |
| `sql_relational` | `SQL-01`, `SQL-02`, `SQL-03`, `SQL-04`, `SQL-05` | Retained value parameterization versus identifiers, database constraints, isolation by invariant, real access paths, and retry/migration compatibility. |
| `postgres` | `PG-01`, `PG-02`, `PG-03`, `PG-04`, `PG-05`, `PG-06` | Retained actual isolation, predicate-specific indexes, missing automatic referencing-FK indexes, concurrent-DDL recovery, and pool/maintenance costs. Added application-role RLS reads/writes, bypass/owner behavior, and tenant context across pool reuse. |
| `mysql` | `MYSQL-01`, `MYSQL-02`, `MYSQL-03`, `MYSQL-04` | Retained deployed modes/engine, InnoDB locking, bounded deadlock recovery, distinct uncertain/timeout outcomes, and exact-version DDL behavior. |
| `sqlite` | `SQLITE-01`, `SQLITE-02`, `SQLITE-03`, `SQLITE-04`, `SQLITE-05` | Retained one-writer semantics, per-connection constraints, WAL/file/backup lifecycle, and deliberate embedded-versus-server choice. Added Python 3.12 transaction initialization before foreign-key enforcement, no accidental commit toggles, and close ownership; an authored example proves the trap. |
| `columnar` | `COL-01`, `COL-02`, `COL-03`, `COL-04` | Retained scan/projection fit, pruning/layout, finite intermediate/spill budgets, and precise Arrow/Parquet conversion/lifetime semantics. |
| `clickhouse` | `CH-01`, `CH-02`, `CH-03`, `CH-04` | Retained non-unique primary ordering, deliberate inserts/acknowledgment, merge-dependent correctness, and version-specific mutation/backfill behavior. |
| `duckdb` | `DUCK-01`, `DUCK-02`, `DUCK-03`, `DUCK-04` | Retained actual process concurrency, limited memory/spill coverage, bounded result materialization, executed-plan scope, and output/temp lifecycle. |
| `timeseries` | `TSDB-01`, `TSDB-02`, `TSDB-03`, `TSDB-04`, `TSDB-05` | Retained clock/series identity, actual-engine cardinality, late/window/counter semantics, sufficient aggregate state, and retention/correction checks. |
| `graph` | `GRAPH-01`, `GRAPH-02`, `GRAPH-03`, `GRAPH-04` | Retained domain identity, constrained entry lookup, bounded traversal/multiplicity, executed-profile scope, and safe driver retries. |
| `mongodb` | `MONGO-01`, `MONGO-02`, `MONGO-03`, `MONGO-04` | Retained bounded documents, explicit schema/atomicity, query-driven indexes/shards, and driver/concern-specific retries and evolution. |
| `redis` | `REDIS-01`, `REDIS-02`, `REDIS-03`, `REDIS-04` | Retained authoritative cache identity, finite scans/memory, atomic command scope, and lock/pubsub durability limits; no universal lock algorithm endorsement. |
| `wide_column` | `WCOL-01`, `WCOL-02`, `WCOL-03`, `WCOL-04` | Retained query-driven partitions, hot-spot bounds, actual consistency/LWT/batch scope, and tombstone/repair/reconciliation behavior. |
| `search` | `SEARCH-01`, `SEARCH-02`, `SEARCH-03`, `SEARCH-04` | Retained source authority versus refresh, mappings/analyzers, authorization inside search, per-item bulk failures, and recoverable reindexing. |
| `vector` | `VECTOR-01`, `VECTOR-02`, `VECTOR-03`, `VECTOR-04` | Retained embedding generation identity, enforced permission boundaries, ANN/exact quality comparison, and owned refresh/deletion; no dedicated-store mandate. |
| `database_migrations` | `MIG-01`, `MIG-02`, `MIG-03`, `MIG-04` | Clarified disposable-local policy versus retained/shared history; retained compatibility windows, bounded resumable backfills, and actual restore/failure behavior. |
| `api_http` | `HTTP-01`, `HTTP-02`, `HTTP-03`, `HTTP-04` | Retained meaningful status/method semantics, bounded safe retries, operation authorization, and real consumer/wire compatibility. |
| `distributed_jobs` | `JOB-01`, `JOB-02`, `JOB-03`, `JOB-04` | Retained acceptance/effect distinctions, authoritative idempotency, conditional durable handoff, and capacity/recovery ownership. |
| `kafka` | `KAFKA-01`, `KAFKA-02`, `KAFKA-03`, `KAFKA-04` | Retained per-partition ordering/offset scope, duplicate-safe effects, limited exactly-once claims, and replay/schema failure behavior. |
| `containers` | `CTR-01`, `CTR-02`, `CTR-03`, `CTR-04` | Retained trusted/minimal runtime artifacts, secret-free layers, deliberate identity/state, and actual entrypoint/shutdown verification; detailed builds are separate. |
| `kubernetes` | `K8S-01`, `K8S-02`, `K8S-03`, `K8S-04` | Clarified scheduling versus CPU/OOM limits and PDB versus controller rollout policy; retained probes, graceful drain, capacity, and real service evidence. |
| `observability` | `OTEL-01`, `OTEL-02`, `OTEL-03`, `OTEL-04` | Retained user-outcome signals, bounded metric dimensions/exporters, privacy/context boundaries, and telemetry-failure limits. |
| `dependency_supply_chain` | `SUPPLY-01`, `SUPPLY-02`, `SUPPLY-03`, `SUPPLY-04` | Retained actual package/publisher/API provenance, artifact-specific lock policy, minimum install privilege, and consumer-level upgrade evidence. |
| `security_boundaries` | `SECAPP-01`, `SECAPP-02`, `SECAPP-03`, `SECAPP-04` | Retained enforcing actor/resource/tenant/action scope, structured input handling, protected secrets/TLS, and focused relevant adversaries. |
| `csharp` | `CSHARP-01`, `CSHARP-02`, `CSHARP-03`, `CSHARP-04` | Retained value/null contracts, task-based async, cancellation/disposal/scoped dependencies, and awaited tests with the chosen runner. Added single-consumption ValueTask/AsTask contracts and WhenAll non-cancellation. |
| `kotlin` | `KOTLIN-01`, `KOTLIN-02`, `KOTLIN-03`, `KOTLIN-04`, `KOTLIN-05` | Retained domain/nullability boundaries, structured scopes, cooperative cancellation/supervision, suitable dispatchers, and owned Flow/test-scheduler lifetimes. Added runCatching cancellation propagation, StateFlow equality conflation, atomic reevaluation-safe updates, and non-durable stream limits. |
| `terraform` | `TF-01`, `TF-02`, `TF-03`, `TF-04` | Retained state sensitivity, exact target-bound plans, supported identity moves/imports, coherent modules, and authorized apply boundaries. |
| `shell_practices` | `SHSAFE-01`, `SHSAFE-02`, `SHSAFE-03`, `SHSAFE-04` | Retained explicit dialect, argv/quoting, intentional statuses, and owned cleanup; preserved the corrected POSIX.1-2024 pipefail distinction. |
| `rust_api` | `RAPI-01`, `RAPI-02`, `RAPI-03`, `RAPI-04`, `RAPI-05`, `RAPI-06`, `RAPI-07` | Added borrowed caller contracts, From/TryFrom and naming, semantic standard traits, dyn compatibility, public crate commitments, and executable rustdoc. Added async-trait future Send and dyn boundaries plus edition-specific opaque capture; both authored examples have compiler counterexamples. |
| `vite` | `VITE-01`, `VITE-02`, `VITE-03`, `VITE-04`, `VITE-05` | Added production artifact versus preview, public build-time env, separate type checks, base/chunk/cache deployment behavior, and scoped development access. |
| `node_testing` | `NTEST-01`, `NTEST-02`, `NTEST-03`, `NTEST-04` | Added project-compatible runners, owned handles/fixtures, actual HTTP/stream/module/process boundaries, and deterministic lifecycle failure observation. |
| `cloud_architecture` | `CLOUD-01`, `CLOUD-02`, `CLOUD-03`, `CLOUD-04`, `CLOUD-05`, `CLOUD-06` | Added flow-level outcomes, replaceable compute/durable state, bounded scale/retries, actual failure domains, compatible promotion, and cost/recovery ownership. |
| `cloud_identity` | `CID-01`, `CID-02`, `CID-03`, `CID-04` | Added short-lived scoped identity, effective-policy allowed/denied checks, real network enforcement, rotation, and data-placement limits. |
| `serverless` | `FAAS-01`, `FAAS-02`, `FAAS-03`, `FAAS-04`, `FAAS-05` | Added actual trigger/plan lifecycle, duplicate/partial delivery, safe warm reuse, downstream-scale bounds, and platform-shaped restart evidence. |
| `aws` | `AWS-01`, `AWS-02`, `AWS-03`, `AWS-04` | Added account/role/region identity, effective permissions, service/tier failure scope, and SDK-generation/2026-opt-in retry limits without mandating a compute product. |
| `gcp` | `GCP-01`, `GCP-02`, `GCP-03`, `GCP-04` | Added project/runtime identity, service/job/worker distinctions, Cloud Run port/CPU/termination contracts, end-to-end networking, and actual service recovery scope. |
| `azure` | `AZ-01`, `AZ-02`, `AZ-03`, `AZ-04` | Added tenant/subscription/runtime identity, plan-specific hosting/storage, SDK/connection budgets, and real promotion/recovery behavior. |
| `docker_build` | `DBUILD-01`, `DBUILD-02`, `DBUILD-03`, `DBUILD-04` | Added small locked contexts/stages, cache versus freshness/secret inputs, final ABI/architecture dependencies, and supported executable image gates. |
| `kubernetes_security` | `KSEC-01`, `KSEC-02`, `KSEC-03`, `KSEC-04` | Added enforced pod privilege profiles, workload identity/RBAC, CNI-backed network policy, secret protection, and admitted-workload verification. |
| `technology_verification` | `TCHECK-01`, `TCHECK-02`, `TCHECK-03`, `TCHECK-04`, `TCHECK-05` | Added failure-derived existing commands, independent behavior checks, failure-sensitive gates, final evidence, and bounded durable enforcement without mandatory CI/hooks; invalidate only changed evidence dependencies. |

| `technology_continuity` | `TCONT-01`, `TCONT-02`, `TCONT-03`, `TCONT-04` | Added durable task/preferences/route recovery, complete fresh reading, additive scope and evidence preservation, and explicit host integration limits. |

## Measured context and whether to enlarge it

**Do not enlarge the portable default merely because a model accepts more
context.** Retain the existing 42,000-byte kernel guard. It is a maintenance
bound, not an empirically optimal prompt length and not a universal host limit.
The technology modules do not join baseline modes automatically. The following
measurements are on the reviewed source, with each dependency included once.

Token columns use **tiktoken 0.12.0, o200k_base**, measured locally in a temporary
environment. They are reproducible counts for that encoding only, not a claim
about this session's actual model tokenizer, native capacity, or hidden prompt.
The portable compiler/loader still require only Python's standard library; no
tokenizer is added to the product. Totals exclude project companions, system
messages, conversation, tool schemas/results, code, and output headroom.

| Route | Exact UTF-8 bytes | o200k_base tokens |
| --- | ---: | ---: |
| mode:fast | 32,606 | 6,348 |
| mode:focused | 98,191 | 18,671 |
| mode:substantial | 355,003 | 67,442 |
| mode:full | 623,430 | 125,177 |
| profile:rust_api_change | 118,845 | 22,892 |
| profile:vite_ui | 119,712 | 22,964 |
| profile:node_service | 118,824 | 22,779 |
| profile:cloud_design | 111,510 | 21,240 |
| profile:container_build | 110,122 | 21,013 |
| profile:kubernetes_workload | 110,728 | 21,090 |
| profile:technology_resume | 108,813 | 20,712 |

The local Codex configuration inspected for this task explicitly sets
`project_doc_max_bytes = 131072`, `model_context_window = 500000`, and
`model_auto_compact_token_limit = 250000`. These are configuration values, not
proof of a model's native limit or that every T3/host invocation uses them.
No host setting was changed. The current source exceeds that 128 KiB automatic
project-document budget; copying it into AGENTS.md would be the wrong delivery
method. Official Codex documentation describes a 32 KiB default for the combined
project instruction chain, which is a separate limit from model context.
[Official instruction-discovery documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

Keep AGENTS.md as a short router to verified content. For a specific task, use
the loader's selected_context accounting, add any companion and the actual host
prompt/tool/code/history costs, and reserve output/execution space using the
actual target tokenizer and observed host behavior. Recheck after compaction
or a material route/source change. A large tool response can truncate well
before the model window is full: use verified delivery segments when needed.
Segmenting does not reduce the total context required by the selected rules.

`--selected-context-target-bytes` is advisory. An over-target receipt exposes
the problem; it does not truncate or authorize omission. If the host cannot
receive all applicable rules, choose a smaller valid phase/route only when its
hard requirements are preserved, reduce unrelated context, use verified staged
reading with explicit continuity, or report the actual delivery limit. Do not
claim to have applied an unread prefix or a lossy summary as the full source.

The substantial baseline is already comparatively large. The useful next
optimization is evidence-backed pruning or finer conditional ownership in the
legacy core, not a larger ceiling. Such a revision must preserve the existing
independent route/byte tests and compare task outcomes before claiming benefit.
No universal percentage of a model window or new token maximum is justified by
this review.

The [loading and continuity guide](TECHNOLOGY_CONTINUITY.md) gives exact
commands, task-state fields, failure behavior, and a matched post-compaction
model-trial protocol. Deterministic recovery tests do not establish model memory.

## Practical enforcement

Instruction delivery, instruction following, and program correctness are three
different properties. The loader proves source/byte provenance and dependency
closure. A model can still miss a tag or ignore prose. Convert an applicable
requirement into a project-native check wherever a check can decide it, then
use independently justified behavior for what static tools cannot establish.

The following are examples to adapt to an existing project, not commands to
install or run universally:

| Changed boundary | Useful existing gate | What still needs behavior evidence |
| --- | --- | --- |
| Rust API/lifetime/features | Project rustfmt, cargo check/test, configured Clippy, supported target/MSRV, relevant doctests | External caller ergonomics, cancellation/cleanup, unsafe invariants, real feature consumers |
| Python async | Existing type/lint checks and pytest/unittest with the chosen async plugin | Sibling failure, cancellation, offloaded worker lifetime, real client/loop scope |
| Vite/TypeScript | Locked project build plus separate configured type and lint commands | Hosted base/deep route/lazy chunk, cache rollover, public-output secret absence |
| Node service | Existing runner and actual deployed loader/module setup | Slow consumer, disconnect, HTTP/upgraded-socket drain, child process exit |
| React/UI | Configured hook lint/type/component tests and selected browser checks | State identity, stale responses, focus, cleanup, hydration, complete interactions |
| Database change | Migration/schema checks and actual-engine integration | Racing writes, isolation/retry scope, committed visibility, interrupted backfill/restore |
| Docker build | Supported Buildx/build checks, locked inputs, image policy/scan/provenance | Final image identity/ABI/user, real startup/request/shutdown, secret-free layers |
| Kubernetes | Target API/schema and existing admission/security policy checks | Effective admitted pod, CNI enforcement, allowed/denied paths, rollout/drain/resource behavior |
| Cloud target | Existing IaC validation/plan and identity/policy checks | Real runtime principal, quota/retry budget, target service lifecycle, actual user flow and recovery |

Use the project's existing local or CI gate when it already protects the
boundary. Add a durable check when the requested scope authorizes it and it
catches a repeatable material defect. A pre-commit hook is convenience, not a
security boundary; hosted CI is optional; a server-side required check or
admission policy is stronger only for the exact action it actually gates.
Do not claim all design principles are mechanically enforceable, make every
warning fatal, or suppress a useful gate to get green output. Final evidence
should identify relevant command/target/version, result, and unavailable
integration scope in the existing change record.

For stronger evidence about WISDOM itself, extend the existing
[application-fidelity protocol](../evaluations/application_fidelity/README.md)
with held-out technology tasks and compare fresh unassisted/prior/candidate
arms under identical model, tools, permissions, and budgets. Useful families
include Vite client-secret/type-check confusion, Node shutdown with an upgraded
connection, Rust ownership/conversion API design, React stale-response cleanup,
and effective cloud/Kubernetes identity. Freeze independent outcome oracles,
include a valid simpler/user-preferred alternative, and measure correctness,
scope, instruction-loading cost, and unnecessary work. Do not grade whether the
agent repeated rule IDs or produced more prose.

No new model trial was run here. Existing small evaluation suites do not
establish the new technology modules' effectiveness. The candidate adds concrete
checks and better scoped instruction delivery, while comparative model behavior
remains an open measurement.

## Additional routing and application review

The final routing pass follows the actual discovery CLI, explicit selection,
dependency closure, checkpoint producer, recovery consumer, segmented delivery,
and extracted portable archive. Required behavior is to refresh every retained
profile and phase from current authored definitions across successive saves.
Forbidden behavior is to miss new obligations because an earlier owner's identity
was discarded or its expansion came from another source generation. Preserve
explicit preferences, prior tags/modules, narrow routes, full-source recovery,
immutable publication, task/project isolation, and exact companion binding.
This is the change contract for this pass; no new policy source is introduced.

The read-only loader also created a sibling compiler bytecode cache. Fresh
subprocess file-frontier checks failed for both discovery and ordinary loading
before repair. Its source-only import now consumes the exact sibling compiler
without reading or writing bytecode caches. The same checks require unchanged
file membership and hashes with bytecode writes enabled in the child interpreter.

Two existing defects were reproduced through the real CLI: after adding a second
profile/phase and saving again, expansion or removal of the original owner went
unnoticed. Four regression cases failed at the intended missing-module or missing
full-source-fallback assertion before repair. Version 2 checkpoints now carry all
known profile and phase identities. Each recovery expands their current definitions,
retains previous tags, and uses full source if an owner disappears. Source binding
also prevents using an expansion computed before a concurrent source update.
Version 1 remains readable; information omitted by an old record cannot be inferred.

Discovery previously exposed names and dependency closures without the authored
technology loading conditions. Its additive `routing_hints` now expose current
section identities, headings, loading conditions, and engineering preferences.
The data comes from WISDOM.md rather than a second catalog. This helps the agent
check applicability before selecting tags; it does not automatically classify a
task, override preferences, or replace complete rule loading and actual checks.

The focused proof surface is `tests/test_technology_continuity.py`: successive
CLI checkpoints with independently edited manifest owners, old-format upgrade,
rehashed invalid lineage, source change between expansion and loading, and a
fresh discovery subprocess after independently editing its authored condition.
Positive/preserved witnesses retain previous modules and exclude unrelated
Kubernetes guidance; removal requires exact current full-source bytes. Existing
checkpoint, companion, encoding, read-budget, and archive cases own their prior
failure families. Local temporary files are the operating boundary; subprocess
timeouts bound the harness, not a semantic expiry policy. No network, live host
compaction, model compliance, distributed scheduling, or deployment is exercised.
Complete-suite and portable-artifact results below qualify the final candidate.

## Validation and remaining limits

The complete suite passed on Linux with CPython 3.14.4: **422 passed** in 22.95s;
CPython 3.12.15: **421 passed, one version-gated skip** in 22.72s for Queue.shutdown.
The suite includes 44 technology-library checks, 69 continuity/discovery cases,
and five authored-example tests, plus compiler, setup, archive, route, and
existing evaluation-kit coverage. Fresh subprocesses and extracted archives
exercise actual byte emission, not only saved metadata. Intentional corrupt,
cross-task, source/profile drift, stale companion/delivery, invalid-encoding,
and multibyte-boundary cases reach the intended loader or discovery boundary.
Independent retained hashes still cover all 26 incumbent module definitions
and section bodies. Baseline mode/phase selections remain unchanged.

The generated rule report and deterministic archive pass their `--check`
commands. Changed-text preflight passes for all 35 touched text files, and
`git diff --check` passes. The hosted Python 3.12.10/3.14.4 Linux/Windows/macOS matrix
was not run from this checkout. Runtime tools still use only the standard
library. Existing source/load-plan/delivery schema identifiers are retained;
the loader adds optional route-checkpoint flags and extends delivery identity
with encoding and tool bindings. New route checkpoints use version 2 with
version 1 read compatibility; discovery adds authored applicability metadata.
No global instruction/configuration files or
host lifecycle hooks were changed.

T3 Code setup now uses provider-native instruction discovery, with explicit
off-PATH Claude/OpenCode targets, environment defaults, effective Codex override
handling, and installed-file reporting. Seven additional cases include a real
extracted-archive CLI installation in fresh processes. Removing explicit
off-PATH OpenCode selection in a disposable copy made its owning regression
fail at the intended routing assertion. See the [T3 integration evidence](T3_CODE.md)
for source references, shared/shadow and remote-home handling, and the distinction
between file installation and observed provider/model behavior.

The source-extracted examples ran on Rust 1.99.1 and Node 24.22.0, with Python
SQLite libraries 3.53.1 (Python 3.12) and 3.46.1 (Python 3.14). Both Rust compiler
counterexamples, queue discard, SQLite initialization order/failed-initialization
cleanup, and Node context leakage reach their intended predicates. Removing read
accounting in a disposable copy made the real inspector CLI admit later content
past a 16-byte budget; the final source rejects it. Fresh-process project/tool
file-frontier checks and ordinary version-value tests pass alongside opaque
reference non-echo checks. All 36 reviewed paths, including intended untracked
files, stayed byte-identical during both final complete runs. Only this evidence
report and the T3 report were updated afterward, with their affected checks rerun.

The Go executable is installed, but its snap-confine version probe failed because
cap_dac_override is unavailable. Go's new API recommendations were source-checked;
no Go runtime behavior was executed. The oldest Rust/Node version baselines come
from primary documentation; only the listed native versions ran locally. No
Java, Kotlin, C#, Rails, React/Vue/Next application, cloud, or cluster integration
was executed for these prose refinements. These are explicit evidence limits,
not a claim that each corresponding runtime is absent.

Primary references are a checked research baseline, not a live feed.
Preview/experimental status, SDK defaults, service plans, platform support,
and security policy must still match the actual project. No production cloud,
cluster, container workload, deployment, or provider account was changed. No
release was published, and no new comparative model-effectiveness trial was run.
