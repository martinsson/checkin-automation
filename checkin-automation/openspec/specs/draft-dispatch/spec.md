## MODIFIED Requirements

### Requirement: Dispatch approved drafts via SmoobuGateway
The draft dispatch handler (`shell/handlers/draft_dispatch.py`) SHALL call `domain/draft_dispatch.py:plan_dispatch()` for each reviewed draft to get the dispatch action, then execute it. For `SendToGuest` actions, it SHALL call `SmoobuGateway.send_message()`.

#### Scenario: Approved acknowledgment sent to guest
- **WHEN** `plan_dispatch()` returns `SendToGuest` for a draft with `step="acknowledgment"`
- **THEN** `SmoobuGateway.send_message()` SHALL be called with the action's reservation_id and body
- **AND** the draft's `sent_at` SHALL be set

### Requirement: Dispatch approved cleaner_query drafts via CleanerNotifier
For `SendToCleaner` actions from `plan_dispatch()`, the handler SHALL call `CleanerNotifier.send_query()` with the query from the action.

#### Scenario: Approved cleaner query sent to cleaner
- **WHEN** `plan_dispatch()` returns `SendToCleaner` for a draft with `step="cleaner_query"`
- **THEN** `CleanerNotifier.send_query()` SHALL be called with the action's `CleanerQuery`
- **AND** the draft's `sent_at` SHALL be set

### Requirement: Dispatch rejected drafts when actual_message_sent is provided
For rejected drafts with corrections, `plan_dispatch()` SHALL return a send action using the corrected body. The handler executes it the same as any other send action.

#### Scenario: Rejected draft with correction sent to guest
- **WHEN** `plan_dispatch()` returns `SendToGuest` for a rejected draft with correction
- **THEN** `SmoobuGateway.send_message()` SHALL be called with the corrected body

#### Scenario: Rejected without correction is skipped
- **WHEN** `plan_dispatch()` returns `SkipSilently`
- **THEN** no message SHALL be sent
- **AND** `sent_at` SHALL be set to prevent re-processing
