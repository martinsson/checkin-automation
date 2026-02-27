## ADDED Requirements

### Requirement: Track which message IDs have already been classified
`RequestMemory.has_message_been_seen(message_id: int)` SHALL return `True` if the given
`message_id` was previously recorded via `mark_message_seen`, and `False` otherwise.

#### Scenario: Unknown message is not seen by default
- **WHEN** no call to `mark_message_seen` has been made for a given `message_id`
- **THEN** `has_message_been_seen(message_id)` SHALL return `False`

#### Scenario: Message marked and then checked
- **WHEN** `mark_message_seen(message_id, reservation_id)` is called
- **THEN** `has_message_been_seen(message_id)` SHALL return `True`

#### Scenario: `mark_message_seen` is idempotent
- **WHEN** `mark_message_seen(message_id, reservation_id)` is called two or more times with the
  same `message_id`
- **THEN** no exception SHALL be raised
- **AND** `has_message_been_seen(message_id)` SHALL return `True`

### Requirement: `seen_messages` table persists records in SQLite
The `SqliteRequestMemory` adapter SHALL persist seen-message records in a `seen_messages` table
with columns `message_id` (INTEGER PRIMARY KEY), `reservation_id` (INTEGER NOT NULL), and
`seen_at` (TEXT NOT NULL, UTC ISO-8601 timestamp). The table SHALL be created automatically on
construction alongside the existing `requests` and `drafts` tables.
