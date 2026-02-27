## ADDED Requirements

### Requirement: Dispatch approved drafts via SmoobuGateway
When a draft has `verdict="ok"` and `sent_at IS NULL` and `step IN ("acknowledgment", "followup", "guest_reply")`, the dispatch step SHALL call `SmoobuGateway.send_message(reservation_id, subject, draft_body)`.

#### Scenario: Approved acknowledgment sent to guest
- **WHEN** a draft with `step="acknowledgment"` and `verdict="ok"` exists
- **THEN** `SmoobuGateway.send_message()` SHALL be called with the draft's `reservation_id` and `draft_body`
- **AND** the draft's `sent_at` SHALL be set to the current timestamp

#### Scenario: Approved guest_reply sent to guest
- **WHEN** a draft with `step="guest_reply"` and `verdict="ok"` exists
- **THEN** `SmoobuGateway.send_message()` SHALL be called with the draft's `reservation_id` and `draft_body`

### Requirement: Dispatch approved cleaner_query drafts via CleanerNotifier
When a draft has `verdict="ok"` and `sent_at IS NULL` and `step="cleaner_query"`, the dispatch step SHALL construct a `CleanerQuery` from the draft and its associated request, and call `CleanerNotifier.send_query(query)`.

#### Scenario: Approved cleaner query sent to cleaner
- **WHEN** a draft with `step="cleaner_query"` and `verdict="ok"` exists
- **THEN** `CleanerNotifier.send_query()` SHALL be called with a `CleanerQuery` populated from the draft's associated request
- **AND** the draft's `sent_at` SHALL be set to the current timestamp

### Requirement: Dispatch rejected drafts when actual_message_sent is provided
When a draft has `verdict="nok"` and `sent_at IS NULL` and `actual_message_sent IS NOT NULL`, the dispatch step SHALL send `actual_message_sent` instead of `draft_body`, using the same channel routing by step.

#### Scenario: Rejected draft with correction sent to guest
- **WHEN** a draft with `step="acknowledgment"`, `verdict="nok"`, and `actual_message_sent="Custom text"` exists
- **THEN** `SmoobuGateway.send_message()` SHALL be called with `"Custom text"` as the body

#### Scenario: Rejected draft without correction is skipped
- **WHEN** a draft with `verdict="nok"` and `actual_message_sent IS NULL` exists
- **THEN** no message SHALL be sent
- **AND** `sent_at` SHALL be set (to prevent re-processing)

### Requirement: Each draft is dispatched exactly once
After a draft is dispatched (or skipped), `sent_at` SHALL be set to the current timestamp. Subsequent dispatch cycles SHALL NOT process drafts where `sent_at IS NOT NULL`.

#### Scenario: Already-sent draft not re-dispatched
- **WHEN** a draft has `sent_at` set to a non-null value
- **THEN** the dispatch step SHALL NOT call any send method for that draft

### Requirement: Dispatch errors are logged but do not block other drafts
If sending a draft fails (exception from SmoobuGateway or CleanerNotifier), the error SHALL be logged at ERROR level with the draft_id and reservation_id. The failing draft's `sent_at` SHALL NOT be set, so it will be retried on the next cycle. Other drafts in the same cycle SHALL still be processed.

#### Scenario: One failing draft does not block others
- **WHEN** dispatch of draft A raises an exception
- **THEN** draft B in the same cycle SHALL still be dispatched
- **AND** draft A SHALL remain with `sent_at IS NULL` for retry
