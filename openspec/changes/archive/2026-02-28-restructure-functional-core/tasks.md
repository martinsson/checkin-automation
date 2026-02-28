## 1. Cleanup empty stubs

- [x] 1.1 Delete empty stub packages (`src/ai/`, `src/api/`, `src/business_logic/`, `src/integrations/`, `src/models/`, `src/utils/`) and empty deployment dirs (`deployment/nginx/`, `deployment/systemd/`)

## 2. Create `src/ports/` — consolidate all port ABCs and types

- [x] 2.1 Create `src/ports/smoobu.py` — move SmoobuGateway, GuestMessage, ActiveReservation, Thread, ThreadPage, ReservationInfo from `src/adapters/ports.py`
- [x] 2.2 Create `src/ports/intent.py` — move IntentClassifier, ConversationContext, ClassificationResult from `src/domain/intent.py`
- [x] 2.3 Create `src/ports/response.py` — move GuestAcknowledger, ResponseParser, ReplyComposer, ParsedResponse, ComposedReply from `src/domain/response.py`
- [x] 2.4 Create `src/ports/memory.py` — move RequestMemory, ProcessedRequest, Draft from `src/domain/memory.py`
- [x] 2.5 Create `src/ports/cleaner.py` — move CleanerNotifier, CleanerQuery, CleanerResponse from `src/communication/ports.py`
- [x] 2.6 Create `src/ports/reservation_cache.py` — move ReservationCache from `src/domain/reservation_cache.py`
- [x] 2.7 Update all imports across adapters, simulators, tests, web, and scripts to use `src.ports.*`
- [x] 2.8 Delete old port files (`src/adapters/ports.py`, `src/domain/intent.py`, `src/domain/response.py`, `src/domain/memory.py`, `src/domain/reservation_cache.py`, `src/communication/ports.py`) and empty `src/domain/`, `src/communication/` directories
- [x] 2.9 Run full test suite — all tests pass with new import paths

## 3. Move simulators to `src/simulators/`

- [x] 3.1 Move simulator files from `src/adapters/simulator_*.py` to `src/simulators/` (rename: `simulator_smoobu.py` → `smoobu.py`, `simulator_intent.py` → `intent.py`, `simulator_response.py` → `response.py`, `simulator_reservation_cache.py` → `reservation_cache.py`)
- [x] 3.2 Move `src/communication/console_notifier.py` to `src/simulators/cleaner.py`
- [x] 3.3 Update all test imports to use `src.simulators.*`
- [x] 3.4 Run full test suite — all tests pass

## 4. Create `src/domain/` — pure functional core

- [x] 4.1 Create `src/domain/guest_request.py` — implement `triage()` returning Skip/Followup/Actionable, `plan_drafts()` returning draft commands, `build_cleaner_query()`. All pure, synchronous, no I/O
- [x] 4.2 Create `src/domain/cleaner_response.py` — implement `rebuild_query_context()` and `plan_reply()`. All pure, synchronous
- [x] 4.3 Create `src/domain/draft_dispatch.py` — implement `plan_dispatch()` returning SendToGuest/SendToCleaner/SkipSilently. All pure, synchronous
- [x] 4.4 Write unit tests for domain functions — plain `assert`, no async, no mocks, no simulators needed

## 5. Create `src/shell/` — imperative shell

- [x] 5.1 Create `src/shell/pollers/guest_messages.py` — extract thread scanning, reservation fetching, message filtering, context building from `poll_once()`
- [x] 5.2 Create `src/shell/pollers/cleaner_responses.py` — wrap `CleanerNotifier.poll_responses()` in the symmetric poller pattern
- [x] 5.3 Create `src/shell/handlers/guest_request.py` — orchestrate: fetch dedup booleans → classify (AI) → triage (domain) → compose ack (AI) → plan_drafts (domain) → execute commands (memory writes)
- [x] 5.4 Create `src/shell/handlers/cleaner_response.py` — orchestrate: lookup request → rebuild query (domain) → parse (AI) → compose (AI) → plan_reply (domain) → execute commands
- [x] 5.5 Create `src/shell/handlers/draft_dispatch.py` — orchestrate: fetch drafts → plan_dispatch (domain) → execute send actions → mark sent
- [x] 5.6 Create `src/shell/main_cycle.py` with `poll_cycle()` — thin sequencer: call guest message poller → handler, cleaner response poller → handler, draft dispatch handler

## 6. Rewire entry points and delete old code

- [x] 6.1 Update `scripts/run.py` to use `shell/main_cycle.py` instead of `Pipeline` + `poll_once()`
- [x] 6.2 Update `src/web/` imports to use `src.ports.memory`
- [x] 6.3 Delete `src/pipeline.py` and `src/daemon.py`
- [x] 6.4 Run full test suite — all existing behavioral tests pass (with updated imports)

## 7. Update tests

- [x] 7.1 Update `test_pipeline.py` to test through the new shell handlers (same scenarios, new structure)
- [x] 7.2 Update `test_daemon.py` to test `poll_cycle()` and the guest message poller
- [x] 7.3 Update `test_dispatch.py` to test through `shell/handlers/draft_dispatch.py`
- [x] 7.4 Verify contract tests still pass unchanged (they test adapters, not orchestration)
- [x] 7.5 Run full test suite — green
