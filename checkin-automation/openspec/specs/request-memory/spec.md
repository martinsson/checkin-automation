## MODIFIED Requirements

### Requirement: Port location
RequestMemory ABC and its data types (ProcessedRequest, Draft, RequestStatus) SHALL be defined in `src/ports/memory.py`.

#### Scenario: Import path updated
- **WHEN** code imports RequestMemory, ProcessedRequest, Draft, or RequestStatus
- **THEN** the import SHALL be from `src.ports.memory`

## ADDED Requirements

### Requirement: RequestStatus enum defines all valid request states
A `RequestStatus` enum SHALL be defined in `src/ports/memory.py` with values: `pending_ack`, `pending_cleaner`, `pending_reply`, `done`. It SHALL be a `str` enum so values are stored as readable strings in SQLite.

#### Scenario: Enum values match expected lifecycle
- **WHEN** RequestStatus members are listed
- **THEN** they SHALL be exactly: `pending_ack`, `pending_cleaner`, `pending_reply`, `done`

### Requirement: ProcessedRequest.status uses RequestStatus enum
The `status` field on `ProcessedRequest` SHALL be typed as `RequestStatus` instead of `str`.

#### Scenario: Status field is typed
- **WHEN** a ProcessedRequest is loaded from the database
- **THEN** its `status` field SHALL be a `RequestStatus` enum member

### Requirement: delete_request removes a request and its drafts
`RequestMemory` SHALL provide a `delete_request(request_id)` method that removes the request and all associated drafts. Used by the retry script to clean up before re-classification.

#### Scenario: Delete request with drafts
- **WHEN** `delete_request("req-1")` is called and req-1 has 2 drafts
- **THEN** the request and both drafts SHALL be removed from storage
- **AND** `get_request("req-1")` SHALL return None

### Requirement: delete_seen_message clears message dedup entry
`RequestMemory` SHALL provide a `delete_seen_message(message_id)` method that removes the seen_messages entry for a given message_id. Used by the retry script.

#### Scenario: Clear seen flag
- **WHEN** `delete_seen_message(123)` is called
- **THEN** `is_message_seen(123)` SHALL return False
