## Why

Request lifecycle is hard to follow: statuses are bare strings with no enum, `"done"` is never set, and the followup path creates orphaned requests. When automation fails (e.g. misclassification), there's no way to retry — the message is permanently marked as seen. This makes debugging and manual compensation impossible.

## What Changes

- **Remove followup classification path.** `needs_followup` is dropped. When no time is extracted, the system still creates the full request (ack + cleaner query), forwarding the guest's original message to the cleaner as-is.
- **Add explicit `RequestStatus` enum.** Replace bare strings with a Python enum: `pending_ack → pending_cleaner → pending_reply → done`. Transitions enforced in code. `done` is actually set when the guest reply is sent.
- **Add status transition: `pending_cleaner`.** After ack and cleaner query are both sent, request moves to `pending_cleaner` (currently it stays at `pending_acknowledgment` forever).
- **Set `done` on completion.** After guest_reply draft is sent, mark request as `done`.
- **Add CLI retry script for misclassification.** A script that clears the "seen" flag for a message_id so the pipeline re-classifies it on the next cycle. Optionally accepts a substitute message text.

## Capabilities

### New Capabilities
- `retry-classification`: CLI script to clear message dedup and re-trigger classification, optionally with a substitute message.

### Modified Capabilities
- `intent-classification`: Remove `needs_followup` and `followup_question` from ClassificationResult. Intent is always fully actionable.
- `guest-request-domain`: Remove `Followup` triage result. Triage returns only `Skip` or `Actionable`. No time → still actionable, use `"?"` as extracted_time.
- `request-memory`: Add `RequestStatus` enum. Add status transition to `pending_cleaner` and `done`. Enforce valid transitions.
- `pipeline-orchestration`: Update poll_cycle to set `pending_cleaner` after both ack+cleaner_query are dispatched. Set `done` after guest_reply is dispatched.
- `draft-dispatch-domain`: After dispatching, update request status based on which drafts were sent.

## Impact

- `src/ports/intent.py` — ClassificationResult loses two fields
- `src/domain/guest_request.py` — `Followup` type and branch removed from triage
- `src/ports/memory.py` — new `RequestStatus` enum, `ProcessedRequest.status` becomes typed
- `src/adapters/sqlite_memory.py` — status transitions enforced
- `src/domain/draft_dispatch.py` — returns status update commands alongside send commands
- `src/shell/handlers/draft_dispatch.py` — executes status transitions after sends
- `src/simulators/intent.py` — remove followup logic
- `scripts/retry_classification.py` — new CLI script
- Tests updated across the board
