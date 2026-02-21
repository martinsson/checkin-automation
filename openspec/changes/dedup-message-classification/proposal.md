## Why

On every poll cycle, `poll_once()` fetches the latest guest message for each reservation and
unconditionally passes it to `pipeline.process_message()`. The pipeline calls the Claude AI
classifier first, then checks `has_been_processed(reservation_id, intent)` to enforce idempotency.
This ordering means **every poll pays an AI API call** for messages that have already been classified
— even when nothing has changed since the last cycle.

In practice: a reservation with a processed early-check-in request will trigger an AI classification
call on every daemon cycle until the reservation ends, even though the result is always
"already_processed". This wastes money and adds latency with zero benefit.

## What Changes

- Add a `seen_messages` table to the SQLite schema to track which `message_id`s have already been
  classified (regardless of the classification result).
- Add `has_message_been_seen(message_id)` and `mark_message_seen(message_id, reservation_id)` to
  the `RequestMemory` port and its `SqliteRequestMemory` adapter.
- In `pipeline.process_message()`, accept a `message_id` parameter and short-circuit before the AI
  call if the message has already been seen.
- Update `daemon.poll_once()` to pass `message_id` (already present on `GuestMessage`) to the
  pipeline.

## Capabilities

### Modified Capabilities

- `request-memory`: Add two new methods — `has_message_been_seen(message_id: int) -> bool` and
  `mark_message_seen(message_id: int, reservation_id: int) -> None` — plus the backing SQLite table.
  The existing `has_been_processed(reservation_id, intent)` check is preserved; message-level dedup
  is an earlier, cheaper guard.
- `pipeline-orchestration`: `process_message()` now accepts `message_id: int` and checks
  `has_message_been_seen` before classification. If seen, returns `already_processed` immediately.
  After classification (any result, including "other"), calls `mark_message_seen`.
- `daemon-runner`: `poll_once()` passes `message_id=latest.message_id` to `pipeline.process_message()`.

## Impact

- No change to the owner-facing draft workflow or message content.
- Reduces Claude API calls to O(new messages) instead of O(all messages × poll cycles).
- Small schema migration: new `seen_messages` table in `data/checkin.db`. In-memory test instances
  create it automatically on construction (no migration needed for tests).
- Simulator adapter (`SimulatorRequestMemory`) must implement the two new methods.
