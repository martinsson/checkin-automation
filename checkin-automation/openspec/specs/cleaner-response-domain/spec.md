## ADDED Requirements

### Requirement: Pure rebuild_query_context reconstructs a CleanerQuery from a stored request
`rebuild_query_context()` SHALL be a pure, synchronous function that takes a `ProcessedRequest` and a cleaner name, and returns a `CleanerQuery`. No I/O.

#### Scenario: Query reconstructed from stored request
- **WHEN** `rebuild_query_context()` is called with a ProcessedRequest for early_checkin
- **THEN** the returned `CleanerQuery` SHALL have fields populated from the request record

### Requirement: Pure plan_reply function produces a reply draft command
`plan_reply()` SHALL be a pure, synchronous function that takes a reply body (str) and request metadata, and returns a command object describing the draft to save and the status to update. No I/O.

#### Scenario: Reply plan includes guest_reply draft and status update
- **WHEN** `plan_reply()` is called with a reply body and request metadata
- **THEN** it SHALL return a command to save a `"guest_reply"` draft and update status to `"pending_reply"`
