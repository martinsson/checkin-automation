## Context

The pipeline creates drafts (acknowledgment, cleaner_query, followup, guest_reply) but nothing sends them after the owner reviews. The owner approves via the web UI, then must manually copy the text and send it through Smoobu or email. This defeats the automation goal.

The draft review flow already sets `verdict` and optionally `actual_message_sent`. We need a dispatch step that reads reviewed drafts and sends them through the right channel.

## Goals / Non-Goals

**Goals:**
- Reviewed drafts are automatically sent via the correct channel
- Each draft is sent exactly once (idempotent dispatch)
- The dispatch step runs in the existing daemon poll loop — no new processes

**Non-Goals:**
- Real-time sending (webhook on approval) — polling each cycle is fast enough
- Changing the review UI — approve/reject flow stays the same
- Auto-approving drafts — owner always reviews first

## Decisions

### Decision 1: Dispatch lives in the daemon poll loop, not in the web UI

The web UI sets the verdict. The daemon's next poll cycle picks up reviewed drafts and sends them. This keeps the web UI stateless (no need for SmoobuGateway or CleanerNotifier wiring in the web layer) and reuses the daemon's existing adapter instances.

Alternative: send immediately in the web POST handler. Rejected because the web process doesn't have access to the SmoobuGateway or CleanerNotifier, and adding them would break the clean separation.

### Decision 2: New `sent_at` column on drafts, not a separate table

Track dispatch state with a nullable `sent_at` timestamp on the existing `drafts` table. A draft is dispatchable when `verdict IN ('ok', 'nok')` AND `sent_at IS NULL`. After sending, set `sent_at` to now.

Alternative: separate `dispatch_queue` table. Rejected — adds complexity for no benefit; the drafts table already has all the data.

### Decision 3: Route by draft step, not by intent

- `step IN ('acknowledgment', 'followup', 'guest_reply')` → `SmoobuGateway.send_message(reservation_id, subject, body)`
- `step = 'cleaner_query'` → `CleanerNotifier.send_query(CleanerQuery(...))`

This is simpler than routing by intent and maps directly to the existing channel split.

### Decision 4: Determine message body from verdict

- `verdict = 'ok'` → send `draft_body`
- `verdict = 'nok'` AND `actual_message_sent IS NOT NULL` → send `actual_message_sent`
- `verdict = 'nok'` AND `actual_message_sent IS NULL` → skip (owner chose not to send)

### Decision 5: `dispatch_reviewed_drafts()` is a standalone async function

Like `poll_once()`, it takes the ports it needs as arguments (memory, smoobu, cleaner). Called at the end of each poll cycle, after `process_cleaner_responses()`.

## Risks / Trade-offs

- [Risk] Daemon crashes after sending but before marking `sent_at` → message sent twice on restart → Mitigation: SmoobuGateway.send_message is append-only (duplicate guest messages are visible but not harmful); CleanerNotifier email dedup via Message-ID
- [Risk] SQLite migration needed for `sent_at` column on existing DBs → Mitigation: same ALTER TABLE pattern as the existing migrations in SqliteRequestMemory
- [Risk] CleanerQuery construction from draft data requires looking up the request → Mitigation: draft already carries `request_id`, use `memory.get_request()` to hydrate
