## Tasks

### Domain model
- [x] Add `sent_at: datetime | None = None` field to `Draft` dataclass in `src/domain/memory.py`
- [x] Add `get_reviewed_unsent_drafts()` abstract method to `RequestMemory` port
- [x] Add `mark_draft_sent(draft_id)` abstract method to `RequestMemory` port

### SQLite adapter
- [x] Add `sent_at` column migration to `_MIGRATIONS` in `src/adapters/sqlite_memory.py`
- [x] Implement `get_reviewed_unsent_drafts()` in `SqliteRequestMemory` — query drafts where `verdict IN ('ok','nok') AND sent_at IS NULL`, ordered by `created_at`
- [x] Implement `mark_draft_sent(draft_id)` in `SqliteRequestMemory` — set `sent_at` to current UTC timestamp
- [x] Update `_row_to_draft()` to populate `sent_at` from the row

### Contract tests
- [x] Add `test_get_reviewed_unsent_drafts` to `RequestMemoryContract` — create drafts with mixed verdicts and sent_at states, assert only reviewed unsent ones returned
- [x] Add `test_mark_draft_sent` to `RequestMemoryContract` — mark a draft sent, assert it no longer appears in `get_reviewed_unsent_drafts()`
- [x] Add `test_new_draft_has_sent_at_none` to `RequestMemoryContract`

### Dispatch function
- [x] Create `dispatch_reviewed_drafts()` async function in `src/daemon.py` taking `memory`, `smoobu`, `cleaner` as arguments
- [x] Implement guest-channel routing: for `step in (acknowledgment, followup, guest_reply)`, call `smoobu.send_message(reservation_id, "", body)` where body is `draft_body` (ok) or `actual_message_sent` (nok)
- [x] Implement cleaner-channel routing: for `step == cleaner_query`, construct `CleanerQuery` from request data and call `cleaner.send_query(query)`
- [x] Skip nok drafts where `actual_message_sent` is None — still mark `sent_at` to prevent re-processing
- [x] Call `memory.mark_draft_sent(draft_id)` after successful send
- [x] Wrap each draft dispatch in try/except: log error with draft_id and reservation_id, do not set `sent_at` on failure, continue to next draft

### Daemon integration
- [x] Wire `dispatch_reviewed_drafts()` call into `poll_once()` — after `process_cleaner_responses()`, before sleep
- [x] Pass `CleanerNotifier` instance to `poll_once()` (or to the new dispatch function) in `scripts/run.py`

### Dispatch tests
- [x] Test approved acknowledgment draft sends via smoobu.send_message with draft_body
- [x] Test approved cleaner_query draft sends via cleaner.send_query with CleanerQuery
- [x] Test rejected draft with actual_message_sent sends the correction text
- [x] Test rejected draft without actual_message_sent skips sending but marks sent_at
- [x] Test dispatch error on one draft does not block other drafts
- [x] Test already-sent draft (sent_at set) is not re-dispatched
