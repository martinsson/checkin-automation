## ADDED Requirements

### Requirement: Track requests by (reservation_id, intent) to prevent duplicates
`RequestMemory.has_been_processed(reservation_id, intent)` SHALL return `True` if any request record exists for that `(reservation_id, intent)` pair, regardless of its current status.

#### Scenario: First request for an intent
- **WHEN** no request exists for `(reservation_id, intent)`
- **THEN** `has_been_processed()` SHALL return `False`

#### Scenario: Subsequent message for the same intent
- **WHEN** a request already exists for `(reservation_id, intent)` (any status)
- **THEN** `has_been_processed()` SHALL return `True`

#### Scenario: Same reservation, different intent
- **WHEN** a request exists for `(reservation_id, "early_checkin")` but not for `(reservation_id, "late_checkout")`
- **THEN** `has_been_processed(reservation_id, "late_checkout")` SHALL return `False`

### Requirement: Save request with a correlation ID
`RequestMemory.save_request()` SHALL persist a `ProcessedRequest` record with the provided `request_id` (UUID), initial status `"pending_acknowledgment"`, and the original guest message.

#### Scenario: Request saved and retrievable
- **WHEN** `save_request(reservation_id, intent, request_id, guest_message)` is called
- **THEN** `get_request(request_id)` SHALL return a `ProcessedRequest` with matching fields

### Requirement: Update request status through a defined lifecycle
`RequestMemory.update_status()` SHALL update the status of a request. Valid statuses are `"pending_acknowledgment"`, `"pending_cleaner"`, `"pending_reply"`, and `"done"`.

#### Scenario: Status update persisted
- **WHEN** `update_status(request_id, "pending_reply")` is called
- **THEN** `get_request(request_id).status` SHALL return `"pending_reply"`

### Requirement: Save drafts for owner review
`RequestMemory.save_draft()` SHALL persist a draft with `verdict="pending"` and return an integer `draft_id`. Valid `step` values are `"acknowledgment"`, `"cleaner_query"`, `"followup"`, and `"guest_reply"`.

#### Scenario: Draft saved and retrievable by ID
- **WHEN** `save_draft(request_id, reservation_id, intent, step, draft_body)` is called
- **THEN** `get_draft(draft_id)` SHALL return a `Draft` with `verdict="pending"` and the provided `draft_body`

#### Scenario: Pending drafts listed in order
- **WHEN** multiple drafts with `verdict="pending"` exist
- **THEN** `get_pending_drafts()` SHALL return all of them, oldest first

### Requirement: Record owner verdict and feedback on drafts
`RequestMemory.review_draft()` SHALL set `verdict` to `"ok"` or `"nok"`, record `actual_message_sent`, `owner_comment`, and set `reviewed_at` to the current timestamp.

#### Scenario: Owner approves draft as-is
- **WHEN** `review_draft(draft_id, verdict="ok")` is called
- **THEN** `get_draft(draft_id).verdict` SHALL be `"ok"`
- **AND** `get_draft(draft_id).reviewed_at` SHALL be non-null

#### Scenario: Owner rejects and provides alternative
- **WHEN** `review_draft(draft_id, verdict="nok", actual_message_sent="...", owner_comment="...")` is called
- **THEN** `get_draft(draft_id).actual_message_sent` and `.owner_comment` SHALL reflect the provided values

### Requirement: History retrieval returns all requests for a reservation
`get_history(reservation_id)` SHALL return all `ProcessedRequest` records for the given reservation in chronological order (oldest first).

#### Scenario: Multiple intents for one reservation
- **WHEN** both `"early_checkin"` and `"late_checkout"` requests exist for the same reservation
- **THEN** `get_history(reservation_id)` SHALL return both records

### Requirement: SQLite implementation uses in-memory DB for tests
The `SqliteRequestMemory` adapter SHALL accept `":memory:"` as `db_path`, creating a fresh in-memory database per instance with no disk I/O.

#### Scenario: In-memory database initialised on construction
- **WHEN** `SqliteRequestMemory(db_path=":memory:")` is constructed
- **THEN** all required tables SHALL exist and `get_pending_drafts()` SHALL return an empty list
