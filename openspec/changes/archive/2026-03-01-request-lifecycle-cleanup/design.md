## Context

Request lifecycle is tracked via bare strings (`"pending_acknowledgment"`, `"pending_reply"`) with no enum and no enforcement. The `"done"` state is never set. The `needs_followup` classification path creates orphaned requests that never progress. When the AI misclassifies a message, there's no way to retry — the message is permanently marked as seen.

## Goals / Non-Goals

**Goals:**
- Explicit `RequestStatus` enum with enforced transitions
- Every request reaches `done` when complete
- Remove followup path — always create full request even without extracted time
- CLI retry mechanism for misclassified messages

**Non-Goals:**
- Web UI for manual compensation (CLI/SQL is enough for now)
- Handling cleaner parser failures (out of scope)
- Handling cleaner query generation failures (out of scope)

## Decisions

### Decision 1: RequestStatus as a Python `str` enum

**Choice:** `class RequestStatus(str, Enum)` with values: `pending_ack`, `pending_cleaner`, `pending_reply`, `done`.

**Why str enum:** SQLite stores the string value directly — readable in the DB without a lookup table, and backward compatible with existing string-based queries.

**Alternatives considered:**
- Plain int enum: less readable in DB
- Keep bare strings: status quo, no guardrails

### Decision 2: Status transitions driven by draft dispatch

**Choice:** When `draft_dispatch` sends a draft, it also updates the request status based on what was sent. The domain function `plan_dispatch()` returns both a send action AND a status update command.

Transition rules:
- After **acknowledgment** + **cleaner_query** are both sent → `pending_cleaner`
- After **guest_reply** is sent → `done`

**Why in dispatch:** This is the only place that knows something was actually sent. The handler already iterates over reviewed drafts — adding a status check is natural.

**How "both sent" works:** After dispatching each draft, check if all drafts for that request with step in (`acknowledgment`, `cleaner_query`) have `sent_at` set. If yes → `pending_cleaner`.

### Decision 3: Remove followup entirely from classification

**Choice:** Remove `needs_followup` and `followup_question` from `ClassificationResult`. Remove `Followup` from triage results. When no time is extracted, `extracted_time` is `None` and the request proceeds normally — the cleaner query forwards the guest's original message.

**Why:** The followup path creates orphaned requests (guest replies → new message → new request, old one is abandoned). Removing it simplifies the state machine and the cleaner can handle ambiguity better than a back-and-forth with the guest.

### Decision 4: CLI retry via clearing message dedup

**Choice:** A script `scripts/retry_classification.py` that:
1. Takes a `message_id` (required)
2. Optionally takes a substitute message text
3. Clears the `seen_messages` entry for that `message_id`
4. Optionally clears the `(reservation_id, intent)` dedup if a request was already created from that message
5. Next poll cycle picks it up and re-classifies

**Why not re-run classification directly:** The poller already handles the full flow (build context, classify, triage, create drafts). Re-running it is simpler than duplicating that logic in a script.

**Alternative considered:** Direct "inject request" script — more powerful but more complex, and doesn't help validate the AI classification itself.

### Decision 5: No DB migration needed

**Choice:** Existing `status` column is TEXT. The enum values are valid strings. Old values (`pending_acknowledgment`) are replaced by `pending_ack` via a one-time UPDATE in the migration. The `seen_messages` table already exists.

## Risks / Trade-offs

- **[Risk] Existing requests with old status strings** → Mitigation: add a migration step that maps `pending_acknowledgment` → `pending_ack`. Run once at startup or as a script.
- **[Risk] Removing followup may produce worse cleaner queries** → Mitigation: the cleaner query includes the guest's original message verbatim, so the cleaner sees exactly what was asked. If needed, the acknowledger prompt can say "we're looking into your request" without mentioning a specific time.
- **[Risk] Retry script could create duplicate requests** → Mitigation: script must also clear the `(reservation_id, intent)` request if one was incorrectly created, or warn the user if a request exists.
