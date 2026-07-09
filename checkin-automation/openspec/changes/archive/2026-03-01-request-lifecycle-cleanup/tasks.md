## 1. Add RequestStatus enum and update memory port

- [x] 1.1 Add `RequestStatus(str, Enum)` to `src/ports/memory.py` with values: `pending_ack`, `pending_cleaner`, `pending_reply`, `done`
- [x] 1.2 Change `ProcessedRequest.status` type from `str` to `RequestStatus`
- [x] 1.3 Add `delete_request(request_id)` and `delete_seen_message(message_id)` abstract methods to `RequestMemory`
- [x] 1.4 Implement `delete_request` and `delete_seen_message` in `SqliteRequestMemory`
- [x] 1.5 Update `SqliteRequestMemory` to return `RequestStatus` enum members when loading requests
- [x] 1.6 Add migration: rename `pending_acknowledgment` → `pending_ack` in existing DB rows

## 2. Remove followup from classification

- [x] 2.1 Remove `needs_followup` and `followup_question` from `ClassificationResult` in `src/ports/intent.py`
- [x] 2.2 Remove followup logic from `SimulatorIntentClassifier` in `src/simulators/intent.py`
- [x] 2.3 Remove followup logic from `ClaudeIntentClassifier` in `src/adapters/claude_intent.py` (prompt + response parsing)

## 3. Remove followup from domain and shell

- [x] 3.1 Remove `Followup` dataclass and `needs_followup` branch from `triage()` in `src/domain/guest_request.py`. `TriageResult = Skip | Actionable`
- [x] 3.2 Remove `isinstance(result, Followup)` branch from `src/shell/handlers/guest_request.py`
- [x] 3.3 Ensure `Actionable` is returned even when `extracted_time` is None

## 4. Status transitions in draft dispatch

- [x] 4.1 After dispatching drafts for a request, check if ack + cleaner_query are both sent → update status to `pending_cleaner`
- [x] 4.2 After dispatching guest_reply → update status to `done`
- [x] 4.3 Use `RequestStatus` enum values in all status string references across domain and shell files

## 5. CLI retry script

- [x] 5.1 Create `scripts/retry_classification.py` with `--message-id` (required), `--message` (optional substitute text), `--clear-request` (optional flag)
- [x] 5.2 Script clears `seen_messages` entry, optionally stores substitute message, optionally deletes request + drafts
- [x] 5.3 Script prints clear feedback about what was cleared/deleted

## 6. Update tests

- [x] 6.1 Update `tests/test_domain.py` — remove followup tests, add "no time still actionable" test
- [x] 6.2 Update `tests/test_pipeline.py` — remove `test_missing_time_drafts_followup`, update expectations
- [x] 6.3 Update `tests/test_daemon.py` if any tests rely on followup behavior
- [x] 6.4 Add tests for status transitions: `pending_ack` → `pending_cleaner` → `pending_reply` → `done`
- [x] 6.5 Add tests for `delete_request` and `delete_seen_message` in memory contract
- [x] 6.6 Run full test suite — green
