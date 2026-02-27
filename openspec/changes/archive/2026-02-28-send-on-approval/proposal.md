## Why

Approving or rejecting a draft in the review UI has no effect — no message is actually sent. The owner must manually copy the text and send it outside the system. This breaks the automation loop: the system drafts messages but can't deliver them, making the three-way conversation (guest → host → cleaner) entirely manual after the AI step.

## What Changes

- After each poll cycle, the daemon dispatches reviewed drafts:
  - `verdict="ok"` → send `draft_body`
  - `verdict="nok"` with `actual_message_sent` filled → send `actual_message_sent`
  - `verdict="nok"` without `actual_message_sent` → skip (owner chose not to send)
- Guest-facing drafts (`acknowledgment`, `followup`, `guest_reply`) are sent via `SmoobuGateway.send_message()`
- Cleaner drafts (`cleaner_query`) are sent via `CleanerNotifier.send_query()`
- After sending, the draft is marked as dispatched to prevent re-sending
- **BREAKING**: Modifies the pipeline-orchestration spec — the "nothing is sent directly" invariant is relaxed. The pipeline still creates drafts, but a new dispatch step sends them after owner review.

## Capabilities

### New Capabilities
- `draft-dispatch`: Picks up reviewed drafts and sends them via the appropriate channel. Tracks sent status to avoid double-sending.

### Modified Capabilities
- `pipeline-orchestration`: Relax the "nothing sent directly" requirement — the pipeline still drafts, but the dispatch step (outside the pipeline) sends after review.
- `request-memory`: Add `get_reviewed_unsent_drafts()` and `mark_draft_sent()` to track dispatch state.
- `daemon-runner`: Add draft dispatch step at the end of each poll cycle.

## Impact

- `src/domain/memory.py` — new abstract methods on `RequestMemory`
- `src/adapters/sqlite_memory.py` — new column `sent_at` on `drafts` table; migration for existing DBs
- `src/daemon.py` — new `dispatch_reviewed_drafts()` function called in `poll_once()`
- `src/communication/ports.py` — `CleanerQuery` construction from draft data
- `src/web/routes.py` — no change (review UI stays the same)
