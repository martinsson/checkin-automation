## Context

The checking-automation system manages early check-in and late check-out requests for Airbnb properties. It was built before OpenSpec was introduced, so no formal design documents exist. This document captures the architectural decisions that were made during implementation, serving as the authoritative record for future contributors.

**Current state:** A working MVP. A daemon polls Smoobu for guest messages, runs them through a pipeline of AI + business-logic steps, and saves every outgoing message as a draft for owner review before sending.

**Stakeholders:** Property owner (reviews drafts), cleaning staff (answers availability queries), guests (receive polished replies).

**Constraints:**
- Nothing is ever sent directly — the owner must approve every draft
- No server infrastructure available at MVP stage — runs as a local Python script
- Must work without network calls during tests

## Goals / Non-Goals

**Goals:**
- Document the port/adapter architecture so new adapters can be added without touching business logic
- Record the draft-review invariant as a normative requirement
- Capture the AI→data→code→AI processing principle
- Define the idempotency contract (same request never processed twice per intent)

**Non-Goals:**
- This document does not describe UI, webhooks, or how drafts are sent to guests (that is the owner's manual action)
- Does not cover Trello, RemoteLock, or multi-language support (planned phases 2–4)
- Does not specify prompt engineering details for Claude adapters

## Decisions

### D1 — Port-based adapter architecture

**Decision:** Every external dependency (Smoobu, cleaner channel, Claude AI, SQLite) is hidden behind an abstract `ABC` port. The pipeline depends only on the ports.

**Rationale:** Allows swapping any adapter without touching business logic. Critical for testing — simulator adapters replace real ones and the pipeline cannot tell the difference.

**Alternatives considered:**
- Direct API calls inline in the pipeline — rejected because it makes testing require network access and makes adapter swapping impossible
- Dependency injection framework — rejected as over-engineering for this scale

### D2 — Draft-first, owner-last

**Decision:** Every message the system wants to send (acknowledgment to guest, query to cleaner, reply to guest) is persisted as a `Draft` with `verdict="pending"` before any message leaves the system. The owner reviews and acts manually.

**Rationale:** AI drafts can be wrong or off-tone. Owner review catches errors. `verdict="nok"` entries become training data for improving prompts. This is a safety property, not a feature.

**Alternatives considered:**
- Auto-send when confidence > threshold — rejected because a single bad message to a guest can damage a rental's rating

### D3 — Idempotency keyed on (reservation_id, intent)

**Decision:** `has_been_processed(reservation_id, intent)` returns `True` if any request for that intent exists, regardless of status. The pipeline skips processing if it returns `True`.

**Rationale:** The daemon polls on a timer and re-reads all messages every cycle. Without idempotency, it would create duplicate drafts on every poll.

**Alternatives considered:**
- Keying on message_id — rejected because Smoobu message IDs are not stable; the guest may send follow-up messages about the same intent

### D4 — Async/await throughout

**Decision:** All port methods and pipeline methods are `async`. The daemon uses `asyncio.run()`.

**Rationale:** Future polling loops, email IMAP checks, and Claude API calls all benefit from non-blocking I/O. Starting async now avoids painful refactors later.

**Alternatives considered:**
- Sync with threading — rejected as harder to reason about correctness

### D5 — SQLite for persistence

**Decision:** The default `RequestMemory` implementation uses SQLite via raw `sqlite3` (no ORM). Database path is configurable via `DB_PATH`.

**Rationale:** No external database server required. File-based. Easy to inspect and backup. Tests use `:memory:` so no disk I/O.

**Alternatives considered:**
- PostgreSQL — rejected as too heavy for a single-property MVP
- JSON files — rejected as lacking ACID guarantees

### D6 — Simulator adapters as first-class citizens

**Decision:** Every port has a deterministic simulator (e.g., `SimulatorIntentClassifier`, `SimulatorSmoobuGateway`). Simulators use keyword matching, not randomness.

**Rationale:** Tests must be fast, deterministic, and network-free. Simulators satisfy the same contracts as real adapters, validated by contract test files (`test_*_contract.py`).

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Owner never reviews drafts → backlog grows silently | Future: add age-based alerting or Trello escalation |
| Simulator keyword matching diverges from Claude behaviour | Contract tests run both against the same scenarios; acceptance criteria require both to pass |
| SQLite is single-writer | Acceptable at MVP scale; single daemon process is the only writer |
| `process_message()` only reads the last guest message | Reduces re-processing risk but means mid-conversation intent changes are ignored until next cycle |
| Cleaner response correlation via `request_id` embedded in email | Email body must contain the `request_id` token; cleaner must not strip it |

## Open Questions

- **Cleaner name is hardcoded** (`"Marie"` in pipeline.py:118) — needs to come from config or reservation metadata
- **Stub query in `_handle_cleaner_response`** uses hardcoded guest name / property / times — needs to pull actual values from the stored request
- **No timeout or escalation** if cleaner never replies — planned for phase 2
