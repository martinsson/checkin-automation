## ADDED Requirements

### Requirement: Classify intent before any other action
`Pipeline.process_message()` SHALL call `IntentClassifier.classify()` as the first step. No memory lookup, draft creation, or notification SHALL occur before classification completes.

#### Scenario: Intent classification is first
- **WHEN** `process_message(reservation_id, message, context)` is called
- **THEN** `IntentClassifier.classify()` SHALL be called before any memory or notifier operation

### Requirement: Ignore messages with intent "other"
When classification returns `intent="other"`, the pipeline SHALL return `PipelineResult(action="ignored")` immediately without touching memory, drafts, or the cleaner channel.

#### Scenario: Non-actionable message ignored
- **WHEN** the classifier returns `intent="other"`
- **THEN** `process_message()` SHALL return `action="ignored"`
- **AND** no draft SHALL be created

### Requirement: Skip already-processed (reservation_id, intent) pairs
After classification, the pipeline SHALL call `RequestMemory.has_been_processed(reservation_id, intent)`. If it returns `True`, the pipeline SHALL return `PipelineResult(action="already_processed")` without creating new drafts.

#### Scenario: Duplicate message skipped
- **WHEN** `has_been_processed()` returns `True` for the classified intent
- **THEN** `process_message()` SHALL return `action="already_processed"`
- **AND** no new draft SHALL be saved

### Requirement: Create acknowledgment and cleaner-query drafts for actionable intents
When intent is `"early_checkin"` or `"late_checkout"` and the request has not been processed before, the pipeline SHALL:
1. Save a request record to memory
2. Save an `"acknowledgment"` draft
3. Save a `"cleaner_query"` draft
4. Update request status to `"pending_acknowledgment"`

#### Scenario: Two drafts created for new early check-in request
- **WHEN** `process_message()` is called with a new early check-in intent
- **THEN** `process_message()` SHALL return `action="drafts_created"`
- **AND** exactly one `"acknowledgment"` draft and one `"cleaner_query"` draft SHALL be saved to memory

#### Scenario: Two drafts created for new late check-out request
- **WHEN** `process_message()` is called with a new late check-out intent
- **THEN** `process_message()` SHALL return `action="drafts_created"`

### Requirement: Draft a follow-up question when the classifier requests it
When `ClassificationResult.needs_followup=True`, the pipeline SHALL save the `followup_question` as a `"followup"` draft instead of creating acknowledgment and cleaner-query drafts.

#### Scenario: Follow-up drafted instead of acknowledgment
- **WHEN** the classifier returns `needs_followup=True` with a non-empty `followup_question`
- **THEN** `process_message()` SHALL return `action="followup_drafted"`
- **AND** exactly one `"followup"` draft SHALL be saved
- **AND** no `"cleaner_query"` draft SHALL be saved

### Requirement: Process cleaner responses and draft guest replies
`Pipeline.process_cleaner_responses()` SHALL poll the `CleanerNotifier`, parse each response through `ResponseParser`, compose a guest reply via `ReplyComposer`, save it as a `"guest_reply"` draft, and return `PipelineResult(action="reply_drafted")` per response.

#### Scenario: Cleaner response processed to guest reply draft
- **WHEN** `process_cleaner_responses()` is called and the notifier returns one response
- **THEN** one `"guest_reply"` draft SHALL be saved to memory
- **AND** the result list SHALL contain one `PipelineResult` with `action="reply_drafted"`

#### Scenario: No cleaner responses
- **WHEN** `poll_responses()` returns an empty list
- **THEN** `process_cleaner_responses()` SHALL return an empty list

### Requirement: Pipeline is stateless between calls
The `Pipeline` class SHALL hold no mutable state between calls to `process_message()` or `process_cleaner_responses()`. All state MUST live in the injected ports.

#### Scenario: Multiple reservations processed independently
- **WHEN** `process_message()` is called for two different `reservation_id` values in sequence
- **THEN** the result for each reservation SHALL be independent of the other

### Requirement: Nothing is sent directly — all output goes through drafts
The pipeline SHALL never call `SmoobuGateway.send_message()` or `CleanerNotifier.send_query()` directly. All outbound messages SHALL be saved as drafts with `verdict="pending"` for owner review.

#### Scenario: No direct send during process_message
- **WHEN** `process_message()` completes for any intent
- **THEN** `SmoobuGateway.send_message()` SHALL NOT have been called
- **AND** `CleanerNotifier.send_query()` SHALL NOT have been called
