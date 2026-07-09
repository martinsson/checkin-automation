## Context

Currently, `Pipeline` is a class that takes all port dependencies via `PipelineConfig` and has two methods: `process_message()` (handles guest messages) and `process_cleaner_responses()` (handles cleaner replies). `daemon.py` contains `poll_once()` (thread scanning + message dispatch + cleaner polling + draft dispatch) and `dispatch_reviewed_drafts()`. Both mix I/O with business decisions.

The port ABCs are scattered: `SmoobuGateway` in `src/adapters/ports.py`, domain ports in `src/domain/`, cleaner ports in `src/communication/ports.py`. Six empty stub packages exist from an abandoned design.

## Goals / Non-Goals

**Goals:**
- Domain decision logic is pure Python functions (no async, no I/O, no port dependencies)
- I/O orchestration is separated into a shell layer that sequences calls
- Polling infrastructure (compensating for missing webhooks) is a first-class, symmetric pattern for both guest messages and cleaner responses
- Port ABCs and their types are consolidated in one place
- The codebase structure reveals the workflow at a glance

**Non-Goals:**
- Splitting `RequestMemory` into finer-grained ports (dedup vs drafts vs dispatch) — future work
- Changing any external behavior — same messages, same drafts, same dispatch
- Modifying the web UI beyond import path changes
- Changing the adapter implementations (SQLite, Claude, Smoobu, SMTP) beyond import paths
- Changing the test contract pattern — contracts stay abstract, adapters implement them

## Decisions

### 1. Functional core in `src/domain/`, imperative shell in `src/shell/`

The domain files contain pure functions that take data and return decision objects. The shell files orchestrate I/O (port calls, AI calls) and execute the decisions the domain returns.

**Why not keep the Pipeline class?** The class holds no state — it's just a bag of dependencies with two methods that share nothing. The functional-core approach makes the dependencies explicit per-call (the shell passes data in) and makes decisions testable without any port mocks.

**Why not a single `core.py`?** Guest request handling, cleaner response handling, and draft dispatch are independent use cases. Separate files match the "one file per use case" principle.

### 2. Domain functions return command objects, shell executes them

For example, `domain/draft_dispatch.py:plan_dispatch(draft, request)` returns `SendToGuest(...)`, `SendToCleaner(...)`, or `SkipSilently(...)`. The shell does `match action: ...` and calls the appropriate port.

**Why commands instead of just returning data?** Commands make the domain's intent explicit and testable: `assert isinstance(result, SendToGuest)`. They also decouple the decision from the execution — the shell can log, retry, or batch without the domain knowing.

### 3. Symmetric poller pattern in `src/shell/pollers/`

Both `guest_messages.py` and `cleaner_responses.py` follow the same shape: fetch raw data from an external source, filter/transform to find new items, yield items for handlers. This makes the "no webhook" infrastructure concern explicit and replaceable.

**Why not a shared Poller base class?** The two pollers have different I/O (Smoobu paginated threads vs IMAP inbox), different filtering (cutoff + dedup vs port-internal dedup), and different output types. A base class would be forced abstraction. The symmetry is in the pattern, not in shared code.

### 4. Ports consolidated in `src/ports/`

All ABCs + their co-located data types move to `src/ports/`. One file per port boundary: `smoobu.py`, `intent.py`, `response.py`, `memory.py`, `cleaner.py`, `reservation_cache.py`.

**Why not keep types separate from ABCs?** Each type is defined as part of its port's contract (e.g., `CleanerQuery` is the input type for `CleanerNotifier.send_query()`). Keeping them together means one import to get both the interface and its data shapes.

### 5. `shell/main_cycle.py` as the top-level orchestrator

Contains `poll_cycle()` — a thin async function that calls pollers, then handlers, then dispatch. `scripts/run.py` owns the sleep loop and wiring; `main_cycle.py` owns the single-cycle sequence.

### 6. Simulators move to `src/simulators/`

Currently mixed into `src/adapters/`. Separating them makes it clear what's production code vs test infrastructure.

## Risks / Trade-offs

**Every import path changes** → Mitigated by doing the move in a single pass and running the full test suite. No behavioral changes means tests validate correctness.

**`domain/guest_request.py` triage needs data from I/O (message seen? already processed?)** → The shell fetches these booleans and passes them as plain arguments to the pure `triage()` function. The domain never calls a port.

**AI calls are I/O that sits between domain decisions** → The shell makes the AI call, then passes the result to the domain function. This matches the existing "AI classifies, code decides" invariant. The domain function receives a `ClassificationResult`, not a classifier port.

**Two files named `guest_request.py` (domain + shell/handlers)** → Acceptable because they're in different packages with different roles. The domain one is pure functions, the handler one is async I/O orchestration. If confusing in practice, the handler could be renamed to `handle_guest_request.py`.
