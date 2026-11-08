# Technology guidance: adoption, uncertainty, and research limits

This is the implementation report for the technology library introduced in
1.20.0 and released in 1.20.1, researched on 2026-11-07. It records decisions and open candidates; it does not add portable
rules. [WISDOM.md](../WISDOM.md) is the authority, and the generated
[rule inventory](TECHNOLOGY_MODULES.md) reports every added principle verbatim.
The [follow-up implementation review](TECHNOLOGY_REVIEW.md) covers the full
technology-rule audit, deployment additions, measured context, and enforcement.

The update adds 79 modules and 362 individually owned rules. All 26 incumbent
module definitions and their section bodies remain unchanged from upstream
1.19.1, including its private-overlay isolation clarification. The manifest
advances from semantic revision 21 to 23 without a compiler-schema change.
Technology sections are separate generated module files in a compiled cache;
the standalone WISDOM source still contains the entire library. Ordinary fast,
focused, substantial, and phase routes do not load the technology library unless
an explicit applicable tag or stack profile selects it. The preamble adds a
small technology-routing instruction, including user preference precedence.

The [recursive refinement record](TECHNOLOGY_REVIEW.md#recursive-refinement-passes)
covers the later 18-module pass, 13 additional rules, version evidence, and five
source-extracted semantic examples with deliberate defects. It records the
current runtime proof limits separately from source research and delivery.

## What was added for each requested language

The inventory contains the full text, sources, proof prompts, and preference
surfaces for all of these rules. These summaries are navigation, not substitutes
for the rules.

| Language / framework | Modules and rule families | Main mechanisms |
| --- | --- | --- |
| Python | `python` (PY), `python_asyncio` (PYASYNC), `python_testing` (PYTEST) | Packaging and installed imports; cohesive functions/classes; annotations versus runtime validation; dataclass defaults; cleanup; GIL/free-threading assumptions; TaskGroup versus gather; cancellation and ExceptionGroup; blocking offload; surviving worker threads; event-loop lifetimes; pytest/unittest and isolated fixtures |
| Rust | `rust` (RUST), `rust_api` (RAPI), `rust_tokio` (TOKIO), `rust_testing` (RUSTTEST) | Domain types; ownership and borrowing; conventional traits/conversions; public surface and compatibility; rustdoc; match/iterators; clone/Arc tradeoffs; Result/Option; unsafe invariants; MSRV/edition/features; task supervision; mutex selection; select cancellation safety; blocking offload; graceful shutdown; public integration tests and appropriate analysis tools |
| Go | `go` (GO), `go_concurrency` (GOCON), `go_testing` (GOTEST) | Cohesive packages and consumer interfaces; error wrapping; slices and aliases; language-version loop capture; context propagation; channel closure; bounded errgroup; goroutine termination; shared-state synchronization; race detection; table tests, cleanup, fuzzing, and meaningful benchmarks |
| Java | `java` (JAVA), `java_concurrency` (JCON), `java_testing` (JTEST) | Records versus identity classes; shallow immutability; composition; errors and AutoCloseable; release targets; virtual-thread workload fit; downstream admission; structured-concurrency preview checks; interruption; JDK-specific pinning; JUnit compatibility; real database and proxy tests |
| C++ | `cpp` (CPP), `cpp_concurrency` (CPPCON), `cpp_testing` (CPPTEST) | RAII; unique/shared/borrowed ownership; rule of zero; invariant-owning classes; views and iterator lifetimes; error and numeric policy; compiler/library compatibility; joining threads; cooperative stopping; locks/atomics; coroutine captures and suspension; separate sanitizer configurations; optimized benchmarks |
| Ruby | `ruby` (RUBY), `ruby_concurrency` (RUBYCON), `ruby_testing` (RUBYTEST) | Cohesive objects/modules; Data/Struct and nested mutability; ensure/rescue; gem/runtime identity; CRuby versus other implementations; GVL limits; thread completion; scheduler-dependent fibers; Ractor API/shareability; Minitest/RSpec and isolation |
| Rails | `rails` (RAILS), `rails_jobs` (RAILSJOB), `rails_testing` (RAILSTEST) | Conventional ownership and autoloading; resource authorization and strong parameters; DB constraints; N+1 prevention; transaction/effect separation; executor wrapping; enqueue/commit semantics; durable job identity; connection-pool budgets; committed multi-connection tests; scheduling versus actual effects |

Additional language/framework modules cover JavaScript, TypeScript, Node.js,
React, React effects, React tests, Next.js, Vite, Vue, Svelte, Django, FastAPI,
Spring, C#, and Kotlin. Node testing has its own conditional module.
Cross-cutting modules cover UI, accessibility, browser testing,
HTTP APIs, jobs, Kafka, containers, Kubernetes, observability, supply chains,
application security, Terraform, shell scripts, and practical technology checks.
Cloud modules cover application architecture, workload identity/networking,
serverless execution, and separate AWS, Google Cloud, and Azure targets.
Docker build and Kubernetes security submodules deepen the existing deployment
guidance without selecting an orchestrator or provider for the user.

Database modules cover selection, relational SQL, PostgreSQL, MySQL, SQLite,
columnar analytics, ClickHouse, DuckDB, time series, graphs, MongoDB, Redis,
wide-column stores, search, vectors, and migrations. They distinguish data
models and engine semantics rather than treating every store as interchangeable.

## Choices intentionally left conditional

These are the additions I was unsure should become defaults. Each is either
included with a trigger and escape condition, or deferred as a universal rule.
No question here blocks use of the added library.

| Candidate | Disposition and reason | Evidence that would justify a stronger project preference |
| --- | --- | --- |
| Automatically load every detected technology | Not adopted. Bounded file and dependency evidence can be optional, generated, or inactive. The helper suggests candidates; the agent verifies affected callers and omissions. | A verified task scope, actual execution paths, supported versions, and current user preferences. |
| Assume compaction retains every discipline | Rejected. A route checkpoint permits fresh verified reloading, while model memory and application remain separate. | A supported host recovery integration plus independent post-recovery outcome evidence. |
| Install recovery hooks in every agent host | Deferred as a universal implementation. Hosts expose different lifecycle contracts; no global files or hooks are silently changed. | Verified callback ordering and delivery tests for the actual host, within authorized setup scope. |
| Use async for every service | Not added. Async increases lifecycle complexity and is not automatically faster; synchronous bounded work remains valid. | A workload dominated by scalable concurrent waiting, compatible libraries, and measured service behavior. |
| Always use asyncio | Conditional. The module explains asyncio semantics when selected; AnyIO, Trio, and synchronous implementations remain valid choices. | Project runtime and dependency contracts plus cancellation/shutdown tests. |
| Require TaskGroup everywhere | Conditional on Python 3.11+ and sibling-cancellation semantics. Gather and independently owned tasks can have different intended contracts. | Related child work whose failure policy matches TaskGroup. |
| Free-threaded Python as the CPU default | Not added. Interpreter build, extensions, deployment, and measured contention matter. | A verified compatible runtime and dependencies with representative parallel benchmarks. |
| Mandate a Python type checker, formatter, package manager, or validation library | Not added. New dependencies and migrations need project benefit. | Existing project policy or a specific boundary an available tool can protect. |
| Require src layout for every Python repository | Conditional for new distributable packages. Scripts and established layouts need no forced reorganization. | Evidence that checkout imports hide packaging defects or that distribution isolation matters. |
| Use Tokio for every Rust crate | Conditional on application/runtime and ecosystem fit. Library code can remain runtime-neutral. | Existing Tokio integrations or required runtime features and a clear embedding model. |
| Always use async mutexes in Rust | Rejected as a blanket rule. A short synchronous critical section can use a standard mutex; an async resource may suit a task owner. | Actual contention, suspension, Send/lifetime requirements, and throughput/latency measurements. |
| Require Rust 2024, boxed errors, Miri, or Loom | Conditional. Edition/MSRV, library error APIs, unsafe scope, and synchronization models differ. | Supported toolchains and a concrete invariant or consumer need. |
| Generic or builder-based Rust APIs everywhere | Not added. Borrowing and standard conversions follow real caller ownership; generics, dynamic dispatch, and builders need a concrete ergonomic or invariant benefit. | External call sites demonstrating the needed substitution or configuration complexity. |
| Require channels for all Go concurrency | Not added. Mutexes can express shared invariants more clearly; channels suit ownership transfer and coordination. | A named state owner or communication/lifecycle contract. |
| Add errgroup everywhere | Conditional for related fallible tasks and accepted dependencies. Pure joins or unrelated supervised tasks differ. | Shared cancellation/error policy and a bounded admission design. |
| Always apply the old Go loop-variable workaround | Not added. Go 1.22 language semantics changed per-iteration declarations; reassignment and older language versions still differ. | The actual go.mod language version and the specific captured variable declaration. |
| Use Java virtual threads everywhere | Conditional for supported blocking-I/O workloads. They do not accelerate CPU computation or remove downstream limits. | JDK/dependency compatibility, resource admission, and measured waiting-heavy workload. |
| Make StructuredTaskScope the Java default | Not added as an unconditional API. The checked JDK 25 reference labels it preview; signatures/status must be checked for the actual JDK. | Explicit project acceptance of that JDK preview and runtime/build flags, or a later verified stable API. |
| Replace synchronized everywhere for virtual threads | Rejected. Monitor-related pinning changed in JDK 24; rewriting synchronization from old advice can add errors. | Actual runtime-specific remaining pinning or contention demonstrated by profiling. |
| Mandate records, sealed types, or an interface per Java class | Conditional value/variant tools; interface-per-class is not a default. | Real value semantics, a closed domain, substitution, or compatibility need. |
| Raise every C++ repository to C++20/23/26 | Not added. Compiler, standard-library, platform, and ABI support are project constraints. | Authorized migration with an exercised compatibility matrix. |
| Require coroutines or lock-free code in C++ | Not added. Coroutines need a runtime/lifetime contract; lock-free designs need a concrete benefit and memory-model argument. | A measured requirement plus supported libraries, modeled invariants, and targeted tooling. |
| Require exceptions or prohibit exceptions in C++ | Not added. Existing error/ABI/platform policy controls. | Project constraints and a coherent caller-visible failure model. |
| Use Ruby Ractors for every parallel operation | Conditional and version-sensitive. API, sharing, extensions, gems, and deployment support vary. | Compatibility proof and a workload that benefits over threads/processes. |
| Mandate RBS/Sorbet or Minitest/RSpec | Not added. Existing tool choices remain authoritative. | A project-owned adoption/migration decision. |
| Require a Rails service object per action | Not added. Extract a workflow only when it owns a real multi-component invariant or removes duplication. | Actual complexity, transaction ownership, or a reusable application operation. |
| Assume every Active Job enqueue is transaction-safe and durable | Rejected. Adapter, version, database placement, settings, and crash boundaries determine the guarantee. | A tested commit-to-queue protocol, or a durable outbox when atomic handoff is required. |
| Make TypeScript or strictness migrations mandatory | Not added. TypeScript guidance applies only when present; stricter settings are preferred for suitable new code, with deliberate migration scope. | Existing TypeScript policy and a manageable affected consumer frontier. |
| Treat native Node TypeScript execution or Vite builds as type checking | Rejected. Execution/transpilation and type analysis have different contracts. | A separate configured type-check command for an actual TypeScript project. |
| Require Vite, node:test, or a particular Node framework | Not added. Vite and runner guidance applies only to the chosen stack; existing framework and test preferences control. | An actual build/runtime requirement and an authorized adoption decision. |
| Require Redux, Zustand, React Query, or another state library | Not added. Local state, framework loaders, and existing caches can be sufficient. | Actual shared-state/cache requirements with clear identity and invalidation. |
| Use React memoization everywhere | Not added. Measured/evident costs, compiler behavior, and dependency stability determine usefulness. | A representative render/performance problem. |
| Require new React action or Effect Event APIs | Conditional on installed React and actual semantics. They are not dependency-lint escape hatches or durable job frameworks. | Version support and a matching action/synchronization need. |
| Mandate a particular visual style | Not added. Existing design direction and user preferences control; the module asks for coherent task-oriented design and working states. | A user-provided design reference or product design system. |
| Treat WCAG checks as an automatic conformance certificate | Rejected. Automated tools test a subset; the target and relevant human/assistive checks still matter. | A defined conformance scope with appropriate evidence. |
| Migrate every Vue/Svelte application to new syntax | Not added. Existing Options/legacy components remain valid; new syntax must match the installed compiler and component mode. | An authorized migration with public interaction and hydration checks. |
| Use PostgreSQL for everything | Not added. It is often versatile, but SQLite, analytical, graph, document, and other systems can better fit actual constraints. | Required query/transaction/operations evidence and incumbent limitations. |
| Use an ORM, repository pattern, UUID flavor, or schema naming style universally | Not added. These are engineering preferences; integrity and query semantics remain the invariant. | Established project policy and measurable caller/migration benefit. |
| Serializable isolation for all SQL transactions | Not added. Correctness requirements and measured contention choose constraints, CAS, locks, or isolation. | An invariant not adequately protected at the current isolation level. |
| Normalize everything or denormalize everything | Not added. Relational invariants and query-driven distributed/analytical layouts have different tradeoffs. | Real write/read, consistency, and correction requirements. |
| Require keyset pagination everywhere | Conditional for suitable large/changing ordered queries. Offset can be appropriate for small bounded results and page-number UX. | A stable total ordering and demonstrated offset cost or consistency problem. |
| Partition every database table | Not added. Partitioning adds query, uniqueness, maintenance, and migration constraints. | Actual retention, pruning, growth, or maintenance requirements with representative plans. |
| Universal low-cardinality tag rule for time-series engines | Not added. InfluxDB 3 differs from older TSM systems; engine metadata/query costs still need measurement. | The actual engine/version, identity needs, and a resource budget. |
| Redis locks/Redlock as general distributed correctness | Not adopted universally. Expiry, failover, timing, and downstream fencing require an explicit failure model. | A proved bounded guarantee adequate for the specific operation. |
| Kafka exactly-once as an external-effect guarantee | Rejected. Broker transactions do not automatically coordinate arbitrary external effects. | Atomic output/offset coordination or authoritative idempotency at the external owner. |
| Dedicated graph/vector/search store by default | Not added. Existing-engine capabilities may suffice; a second store creates synchronization and operations obligations. | A representative query/quality/latency advantage and owned rebuild/deletion/recovery. |
| Outbox, microservices, CQRS, or event sourcing for every application | Not added. Outbox is conditional on a required atomic durable handoff; broader patterns need concrete domain and operational benefit. | A cross-owner consistency or scaling requirement that simpler ownership cannot satisfy. |
| Require Docker/Kubernetes/Terraform/OpenTelemetry | Not added. Modules activate only when those technologies or mechanisms are actually involved. | The project's deployment and observability requirements. |
| Use Kubernetes or multiple regions for every cloud deployment | Not added. Availability, recovery, locality, operations, and cost requirements choose topology. | A failure-domain or platform need that the simpler deployment cannot meet. |
| Rebuild per environment versus promote one browser bundle | Conditional. Vite environment substitution is build-time unless the application implements runtime configuration; identical-artifact promotion is preferred only where compatible. | A verified configuration boundary and deployment policy. |
| Always set equal requests/limits or cap every Kubernetes CPU | Not added. Scheduling, OOM, throttling, QoS, autoscaling, and platform policy determine resource settings. | Representative resource measurements and the actual cluster's admission/runtime behavior. |
| Smallest possible container base as the universal choice | Not added. ABI, libraries, certificates, debugging, patching, and operational needs matter alongside image size. | A verified final-runtime dependency inventory and measured startup/operational benefit. |
| Adopt every new cloud SDK default or preview | Not added. The checked AWS retry documentation explicitly separates opt-in 2026 behavior; actual SDK/configuration remains authoritative. | Verified supported SDK behavior and a bounded retry/capacity test. |
| Always pin immutable image digests | Conditional under the project's reproducibility and patch/update policy. Unmaintained pins can preserve vulnerabilities. | A controlled update mechanism and provenance requirements. |
| Treat pipefail as universally non-POSIX or available in every sh | Rejected. POSIX.1-2024 specifies it; older target interpreters may still lack it. | The required standard edition and exercised interpreter support. |
| More tests, coverage percentage, or mandatory mutation tooling | Not added as a universal target. Tests protect named behavior; proof prompts are scoped to affected mechanisms. | A demonstrated missing failure family and an independent oracle the tool can exercise. |

## AI failure evidence and scope

The generic agent module targets five mechanisms: invented dependencies/APIs,
incomplete feature wiring, tests changed to fit the candidate, insecure generated
boundaries, and unsupported claims about model capability. Technology modules
then add domain-specific failure hypotheses and representative checks.

Two empirical primary sources motivated part of this work:

- [Spracklen et al., package hallucinations](https://arxiv.org/abs/2406.10279),
  submitted in 2024 and revised in 2025, studied Python/JavaScript package
  hallucinations across 16 models. It supports verifying package identity; its
  measured rates are not estimates for today's Sol or every language.
- [Pearce et al., historical Copilot security](https://arxiv.org/abs/2108.09293),
  from 2021, studied generated code in selected security-sensitive scenarios.
  It supports examining generated security boundaries, not a contemporary
  failure percentage for current OpenAI models.

[OpenAI's Codex prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)
and [frontend instructions](https://developers.openai.com/api/docs/guides/frontend-prompt)
provide practical context for completion and UI quality. They are vendor
guidance, not controlled evidence that a particular React defect is frequent in
Sol. React effect/state/identity rules come from React's own documentation.
I found no controlled Sol-specific React failure study in the research used here.
The library therefore stays model-neutral and does not repeat unverified
model rankings or invent a current training cutoff.

These failure mechanisms are synthesis, not claims that every model always
makes every mistake. The existing application-fidelity evaluation framework
remains the appropriate place to measure whether these instructions improve a
specific model. No model-provider run or empirical effectiveness claim was made
as part of this implementation.

## Research verification and remaining limits

Each module carries primary references and a 2026-11-07 research baseline.
The research used official language/runtime/framework/database documentation,
standards, maintainer documentation, and the two original studies above.
References were opened/fetched; a source audit caught and repaired a JUnit 404,
a Java URL that redirected to a generic index, and a DuckDB redirect stub.
MySQL pages were readable through web retrieval despite direct HTTP denial;
the shell module uses the readable POSIX standard rather than retaining the
blocked Bash page as checked evidence.
A final semantics check caught and corrected the outdated blanket claim that
pipefail is non-POSIX: Issue 8 specifies it, while older interpreter baselines
still require a support check.
A Kotlin cancellation page returned an empty body; the checked coroutine
exception/supervision reference supplies that module's failure semantics.

Some references intentionally pin an older supported baseline, including JDK
25, Django 5.2, MySQL 8.4, DuckDB 1.5, and JUnit 6.1.3. Others use a moving
current/stable URL. The Ruby Ractor development reference is explicitly marked
as such. None establishes the user's installed version or grants permission to
upgrade it. Future editions, preview status, extension compatibility, and
provider defaults must be rechecked for the target project. Network access is
needed to refresh those facts, not to load the checked-in modules.

Source/compiler/report tests verify selection, ownership, byte delivery,
negative routes, and packaging. They cannot prove a model follows the prose,
replace application-specific tests, or certify every referenced future release.
The representative proof paragraphs are prompts to select relevant evidence,
not a requirement to build 79 new test suites for ordinary work.

## Initial implementation validation

The final follow-up results are recorded in the
[implementation review](TECHNOLOGY_REVIEW.md). The checks cover positive and
negative technology routes, mixed
stacks, framework-neutral profiles, exact delivery through a freshly extracted
portable archive, corruption fallback, and stale-report rejection. Independently
retained hashes verify all 26 incumbent module definitions and section bodies.

The generated rule report and deterministic archive have dedicated `--check`
commands. The changed-text preflight and `git diff --check` cover text integrity.
The inventory measures every route's context; the fast kernel does not acquire
all technology modules. The existing CI
matrix targets Python 3.12.10 and 3.14.4 on Linux, Windows, and macOS; those hosted
runs were outside the initial local implementation pass, which published no
release. The subsequent 1.20.1 matrix, installation, publication, and public
download verification are recorded in [the T3 integration report](T3_CODE.md).
No model-effectiveness evaluation was run.

## Coverage deferred rather than guessed

The latest refinements also leave specific modern choices conditional. No
rule mandates Node's newer experimental context-scope helpers over stable run,
React Activity/Compiler/RSC cache APIs for every UI, or free-threaded Python as
the default runtime. They need an actual workload, compatible versions and
dependencies, and a check that decides the benefit. The inspector does not
resolve lockfiles, Maven/Gradle's executable configuration, arbitrary engine
versions, or cross-language compatibility; it reports supported declarations
and explicit interpretation limits instead of granting API support.

The library is broad, not exhaustive. These candidates need separate primary
research and concrete triggers before becoming portable defaults:

- C and embedded/real-time systems, including ISR rules, allocation policies,
  atomics, hardware access, and safety-critical requirements.
- Swift/SwiftUI actor isolation and strict concurrency; Android lifecycle and
  Compose; Flutter/Dart isolates; React Native platform boundaries.
- PHP/Laravel, Elixir/OTP, Scala effect systems, R, Julia, and scientific runtime
  interoperability. Their lifecycle and testing models deserve their own modules.
- Angular's versioned signals, change detection, server rendering, and testing
  ecosystem; Web Components, browser extensions, and service-worker/offline sync.
- Spark, dbt, Iceberg/Delta/DuckLake, streaming watermarks, data orchestration,
  distributed SQL, DynamoDB, and cloud-specific warehouse cost models.
- Additional cloud products and service-specific rollout/migration tools,
  beyond the shared identity, serverless, and provider modules added here;
  CMake target conventions and native dependency managers.
- ML/GPU pipelines, model-serving concurrency, device-memory ownership,
  scientific numerical error budgets, and data/model evaluation leakage.

Add one of these when its actual technology is selected and the research can
support a small coherent module. Avoid creating a name-only module with generic
advice or a mandatory tool choice merely to increase the count.
