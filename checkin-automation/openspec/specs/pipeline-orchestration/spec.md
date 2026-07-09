## MODIFIED Requirements

### Requirement: Classify intent before any other action
The guest request handler SHALL call `IntentClassifier.classify()` as the first substantive step. No memory write, draft creation, or notification SHALL occur before classification completes. The handler fetches dedup booleans from memory before calling `triage()`, but classification is the first AI call.

#### Scenario: Intent classification is first AI call
- **WHEN** a guest message is handled
- **THEN** `IntentClassifier.classify()` SHALL be called before any draft is saved

### Requirement: Pipeline is stateless between calls
The shell handlers SHALL hold no mutable state between calls. All state MUST live in the injected ports. Handlers are functions (or thin classes) that orchestrate I/O and delegate decisions to pure domain functions.

#### Scenario: Multiple reservations processed independently
- **WHEN** the guest request handler is called for two different `reservation_id` values in sequence
- **THEN** the result for each reservation SHALL be independent of the other

### Requirement: Nothing is sent directly — all output goes through drafts
The guest request handler and cleaner response handler SHALL never call `SmoobuGateway.send_message()` or `CleanerNotifier.send_query()` directly. All outbound messages SHALL be saved as drafts with `verdict="pending"` for owner review. Sending happens in the draft dispatch handler.

#### Scenario: No direct send during guest request handling
- **WHEN** a guest message is handled for any intent
- **THEN** `SmoobuGateway.send_message()` SHALL NOT have been called
- **AND** `CleanerNotifier.send_query()` SHALL NOT have been called

## REMOVED Requirements

### Requirement: Pipeline class wraps all orchestration
**Reason**: Replaced by separate shell handlers (`guest_request`, `cleaner_response`, `draft_dispatch`) that each handle one use case, with pure domain functions for decisions.
**Migration**: `Pipeline.process_message()` logic moves to `shell/handlers/guest_request.py` (I/O) + `domain/guest_request.py` (decisions). `Pipeline.process_cleaner_responses()` logic moves to `shell/handlers/cleaner_response.py` (I/O) + `domain/cleaner_response.py` (decisions). `PipelineConfig` is replaced by explicit dependency injection into each handler.

### Requirement: `process_message` accepts a `message_id` parameter
**Reason**: Absorbed into the triage function. The handler passes `message_id` and `is_seen` boolean to `triage()`.
**Migration**: Message-level dedup is still performed — the shell handler fetches `is_seen` from memory and passes it to `triage()`. The `message_id` parameter moves to the handler's interface.

### Requirement: Skip AI classification for already-seen messages
**Reason**: Absorbed into `triage()` as the `Skip(reason="message already seen")` branch.
**Migration**: Same behavior, now expressed as a pure function return value instead of an early return in a method.

### Requirement: Mark message as seen after classification
**Reason**: This I/O step moves to the shell handler. The domain function does not perform I/O.
**Migration**: The handler calls `memory.mark_message_seen()` after calling the classifier and before calling `triage()`.

### Requirement: Process cleaner responses and draft guest replies
**Reason**: Moves to `shell/handlers/cleaner_response.py` which orchestrates the I/O, and `domain/cleaner_response.py` which provides `rebuild_query_context()` and `plan_reply()`.
**Migration**: Same behavior, split across shell handler (I/O) and domain function (decisions).

### Requirement: Followup draft handling in guest request handler
**Reason**: The followup path is removed. The handler no longer creates followup drafts or returns `followup_drafted`.
**Migration**: Remove the `isinstance(result, Followup)` branch from `src/shell/handlers/guest_request.py`. The handler only handles `Skip` and `Actionable` results.
