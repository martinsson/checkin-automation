## ADDED Requirements

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
