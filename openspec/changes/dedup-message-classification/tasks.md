## 1. Extend `RequestMemory` port

- [x] 1.1 Add `has_message_been_seen(message_id: int) -> bool` abstract method to
  `RequestMemory` in `src/domain/memory.py`.
- [x] 1.2 Add `mark_message_seen(message_id: int, reservation_id: int) -> None` abstract method
  to `RequestMemory` in `src/domain/memory.py`.

## 2. Update `SqliteRequestMemory` adapter

- [x] 2.1 Add `seen_messages` table to the schema in `src/adapters/sqlite_memory.py`:
  ```sql
  CREATE TABLE IF NOT EXISTS seen_messages (
      message_id   INTEGER PRIMARY KEY,
      reservation_id INTEGER NOT NULL,
      seen_at      TEXT NOT NULL
  )
  ```
- [x] 2.2 Implement `has_message_been_seen`: `SELECT 1 FROM seen_messages WHERE message_id = ?`.
- [x] 2.3 Implement `mark_message_seen`: `INSERT OR IGNORE INTO seen_messages ...` with current UTC
  timestamp.

## 3. Update `Pipeline.process_message()`

- [x] 3.1 Add `message_id: int` as a required parameter to `Pipeline.process_message()` in
  `src/pipeline.py`.
- [x] 3.2 At the top of `process_message()`, before the AI call, check
  `await self._cfg.memory.has_message_been_seen(message_id)`. If `True`, return
  `PipelineResult(action="already_processed", details="message_id already seen")` immediately.
- [x] 3.3 After `classifier.classify()` returns (for any result, including `"other"` and
  `"already_processed"`), call `await self._cfg.memory.mark_message_seen(message_id,
  reservation_id)` before returning. Place this call so it runs after classification but before
  any early return from the intent check.

## 4. Update `daemon.poll_once()`

- [x] 4.1 In `src/daemon.py`, pass `message_id=latest.message_id` to `pipeline.process_message()`.

## 5. Contract tests for the two new methods

- [x] 5.1 In `tests/contracts/request_memory_contract.py`, add:
  - `test_message_not_seen_by_default` — `has_message_been_seen(999)` returns `False`.
  - `test_mark_and_check_message_seen` — after `mark_message_seen(42, 101)`,
    `has_message_been_seen(42)` returns `True`.
  - `test_mark_message_seen_is_idempotent` — calling `mark_message_seen` twice with the same
    `message_id` does not raise and still returns `True` on check.

## 6. Update pipeline tests

- [x] 6.1 In `tests/test_pipeline.py`, update all calls to `pipeline.process_message()` to pass
  a `message_id` argument (e.g., `message_id=1`).
- [x] 6.2 Add a test `test_same_message_id_not_classified_twice`:
  - Process a message with `message_id=1` (should produce `drafts_created`).
  - Call `process_message` again with the same `message_id=1` (different body is fine).
  - Assert result is `already_processed` and the AI classifier was called only once.

## 7. Update daemon tests

- [x] 7.1 In `tests/test_daemon.py`, verify that the simulator `GuestMessage` objects have a
  non-zero `message_id` and that the pipeline receives it correctly.
  (Existing tests cover this: SimulatorSmoobuGateway assigns auto-incrementing IDs; existing
  multi-cycle test validates cleaner responses still process even when guest message is deduped.)

## 8. Delta spec

- [x] 8.1 Write `openspec/changes/dedup-message-classification/specs/request-memory.md` with the
  two new method requirements and their scenarios (already-seen returns False by default, mark +
  check returns True, idempotent mark).
- [x] 8.2 Write `openspec/changes/dedup-message-classification/specs/pipeline-orchestration.md`
  with the updated `process_message` flow: message-level dedup check before AI classification.
