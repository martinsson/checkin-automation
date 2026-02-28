## Why

The two central modules (`pipeline.py` and `daemon.py`) mix infrastructure concerns (polling for new messages, dispatching drafts) with domain decisions (triage, draft planning, routing). The workflow — the most important concept in this codebase — is not visible in the code structure. Business logic is interleaved with I/O, making it hard to test decisions without simulators or async machinery.

## What Changes

- **BREAKING**: Replace `Pipeline` class and `daemon.py` with a functional-core / imperative-shell structure:
  - Pure domain functions (triage, draft planning, dispatch routing) in `src/domain/`
  - I/O orchestration (pollers, handlers) in `src/shell/`
- Consolidate all port ABCs + their data types into `src/ports/` (currently scattered across `src/adapters/ports.py`, `src/domain/`, `src/communication/ports.py`)
- Move simulator adapters from `src/adapters/` into `src/simulators/`
- Delete empty stub packages (`src/ai/`, `src/api/`, `src/business_logic/`, `src/integrations/`, `src/models/`, `src/utils/`) and empty deployment dirs
- Symmetric poller pattern for both guest messages (Smoobu threads) and cleaner responses (IMAP)

## Capabilities

### New Capabilities
- `guest-request-domain`: Pure functions for guest message triage (skip/followup/actionable) and draft planning (acknowledgment + cleaner query). No async, no I/O.
- `cleaner-response-domain`: Pure functions for cleaner response handling — rebuild query context, plan reply draft. No async, no I/O.
- `draft-dispatch-domain`: Pure function to route a reviewed draft to its dispatch action (send to guest, send to cleaner, skip silently).
- `message-polling`: Infrastructure pollers for discovering new guest messages (Smoobu threads) and new cleaner responses (IMAP/console), separated from message handling.

### Modified Capabilities
- `pipeline-orchestration`: Replaced by shell handlers that wire I/O to domain functions. The orchestration logic moves from a monolithic `Pipeline` class to `shell/handlers/` + `shell/main_cycle.py`.
- `daemon-runner`: `poll_once()` becomes `shell/main_cycle.py` — a thin sequencer calling pollers then handlers. `scripts/run.py` still owns the sleep loop.
- `draft-dispatch`: The dispatch routing logic (verdict + channel decisions) moves to a pure function in `domain/draft_dispatch.py`; the I/O execution stays in `shell/handlers/draft_dispatch.py`.
- `smoobu-gateway`: Port ABC + types move from `src/adapters/ports.py` to `src/ports/smoobu.py`. No behavior changes.
- `intent-classification`: Port ABC + types move from `src/domain/intent.py` to `src/ports/intent.py`. No behavior changes.
- `response-parsing`: Port ABCs + types move from `src/domain/response.py` to `src/ports/response.py`. No behavior changes.
- `request-memory`: Port ABC + types move from `src/domain/memory.py` to `src/ports/memory.py`. No behavior changes.
- `cleaner-notifier`: Port ABC + types move from `src/communication/ports.py` to `src/ports/cleaner.py`. No behavior changes.
- `reservation-cache`: Port ABC moves from `src/domain/reservation_cache.py` to `src/ports/reservation_cache.py`. No behavior changes.

## Impact

- **All imports change** — every file that imports from `src.pipeline`, `src.daemon`, `src.adapters.ports`, `src.domain.*`, or `src.communication.ports` needs updating.
- **Tests** need import path updates but no behavioral changes — the same contract tests and pipeline tests should pass with new paths.
- **`scripts/run.py`** wiring changes to use new shell entry point instead of `Pipeline` + `poll_once()`.
- **`src/web/`** imports from `src.ports.memory` instead of `src.domain.memory`.
- **Docker/deployment** unchanged — same entry points, same behavior.
