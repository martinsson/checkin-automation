## Context

The daemon polls Smoobu on a fixed interval. Each cycle it fetches messages for every active
reservation and passes the latest guest message to the pipeline. The pipeline's idempotency guard
(`has_been_processed`) prevents duplicate drafts but only fires *after* the AI classification call.
The message's `message_id` — already present on `GuestMessage` — is never stored or compared.

## Goals / Non-Goals

**Goals:**
- Skip AI classification for any `message_id` that was already classified in a previous poll cycle.
- Persist the seen-message record so dedup survives daemon restarts.
- Mark messages as seen for *all* classification outcomes, including `"other"` (which is currently
  discarded without any record).

**Non-Goals:**
- Does not change the idempotency semantics for `(reservation_id, intent)` — that guard remains and
  still prevents duplicate drafts if, e.g., the daemon is deployed fresh against an existing DB.
- Does not deduplicate at the `get_messages()` / gateway layer — the Smoobu call still happens every
  cycle (that is a separate, larger change).
- Does not handle multi-message bursts (where a guest sends several new messages in one poll window).
  We still only process the last guest message; this change just avoids re-processing it next cycle.

## Decisions

### D1 — Separate `seen_messages` table, not a column on `requests`

**Decision:** Add a dedicated `seen_messages(message_id, reservation_id, seen_at)` table.

**Rationale:** The `requests` table only stores records for non-"other" intents; messages classified
as "other" are never inserted there. Storing `message_id` on `requests` would leave "other"-intent
messages untracked and re-classified on every cycle. A separate table covers all outcomes uniformly.

**Alternatives considered:**
- Add `message_id` column to `requests` — rejected: doesn't cover "other" classifications.
- Track in-memory per daemon run — rejected: lost on restart, re-classifies on every cold start.

### D2 — Dedup guard in `pipeline.process_message()`, not in `daemon.poll_once()`

**Decision:** The `has_message_been_seen` check lives inside `Pipeline.process_message()`, not in
the daemon.

**Rationale:** The pipeline is the testable unit. Keeping the guard there means existing pipeline
tests catch regressions without needing a full daemon harness. The daemon is a thin orchestration
layer and should stay that way.

**Alternatives considered:**
- Check in `poll_once()` before calling the pipeline — rejected: moves business logic into the
  daemon, making it harder to test and violating the port/adapter pattern.

### D3 — `mark_message_seen` called after classification, regardless of result

**Decision:** After `classifier.classify()` returns (including `"other"`), call `mark_message_seen`
before returning.

**Rationale:** Any message that has been through the AI classifier should be marked as seen. If we
only marked non-"other" messages, we'd re-classify "other" messages every cycle.

**Exception:** If the message is already seen (early return), we do NOT call `mark_message_seen`
again — it's already recorded.

### D4 — `process_message()` signature change: `message_id` is a required parameter

**Decision:** Add `message_id: int` as a required parameter to `Pipeline.process_message()`.

**Rationale:** Making it required surfaces all call sites at compile time and forces callers to
provide the ID. The daemon already has it from `GuestMessage.message_id`. Tests must also pass it,
which is straightforward since the simulator assigns stable IDs.

## Open Questions

*(none — scope is narrow and decisions are clear)*
