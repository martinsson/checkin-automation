## MODIFIED Requirements

### Requirement: Pure plan_dispatch function routes a draft to a dispatch action
`plan_dispatch()` SHALL be a pure, synchronous function that takes a `Draft` and an optional `ProcessedRequest`, and returns one of: `SendToGuest(reservation_id, body)`, `SendToCleaner(query: CleanerQuery)`, or `SkipSilently(draft_id, reason)`. No I/O.

#### Scenario: Approved guest step returns SendToGuest
- **WHEN** `plan_dispatch()` is called with a draft where `verdict="ok"` and `step="acknowledgment"`
- **THEN** it SHALL return `SendToGuest` with the draft's `reservation_id` and `draft_body`

#### Scenario: Approved cleaner_query returns SendToCleaner
- **WHEN** `plan_dispatch()` is called with a draft where `verdict="ok"` and `step="cleaner_query"`
- **THEN** it SHALL return `SendToCleaner` with a `CleanerQuery` built from the draft and request

#### Scenario: Rejected with correction returns send with corrected body
- **WHEN** `plan_dispatch()` is called with a draft where `verdict="nok"` and `actual_message_sent` is not None
- **THEN** it SHALL return a send action using `actual_message_sent` as the body

#### Scenario: Rejected without correction returns SkipSilently
- **WHEN** `plan_dispatch()` is called with a draft where `verdict="nok"` and `actual_message_sent` is None
- **THEN** it SHALL return `SkipSilently` with the draft_id and a reason

## ADDED Requirements

### Requirement: Draft dispatch handler updates request status after sends
After dispatching all reviewed drafts for a request, the handler SHALL check whether to advance the request status.

#### Scenario: Both ack and cleaner_query sent advances to pending_cleaner
- **WHEN** the dispatch handler has sent both the `acknowledgment` and `cleaner_query` drafts for a request
- **AND** the request status is `pending_ack`
- **THEN** the request status SHALL be updated to `pending_cleaner`

#### Scenario: Guest reply sent advances to done
- **WHEN** the dispatch handler has sent the `guest_reply` draft for a request
- **AND** the request status is `pending_reply`
- **THEN** the request status SHALL be updated to `done`

#### Scenario: Partial dispatch does not advance status
- **WHEN** only the `acknowledgment` draft has been sent but not `cleaner_query`
- **THEN** the request status SHALL remain `pending_ack`
