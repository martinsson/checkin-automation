## MODIFIED Requirements

### Requirement: `process_message` accepts a `message_id` parameter
`Pipeline.process_message()` SHALL accept an optional `message_id: int` parameter (default `0`).
When a non-zero `message_id` is provided, the pipeline SHALL use it for message-level deduplication.

### Requirement: Skip AI classification for already-seen messages
**WHEN** `process_message` is called with a non-zero `message_id`
**AND** `RequestMemory.has_message_been_seen(message_id)` returns `True`
**THEN** the pipeline SHALL return `PipelineResult(action="already_processed",
details="message already seen")` immediately, without calling the AI classifier.

#### Scenario: Same message_id presented twice
- **GIVEN** `process_message` was previously called with `message_id=N` and completed successfully
- **WHEN** `process_message` is called again with the same `message_id=N`
- **THEN** result SHALL be `action="already_processed"` with `details="message already seen"`
- **AND** the AI classifier SHALL NOT be called

### Requirement: Mark message as seen after classification
**WHEN** `process_message` calls the AI classifier for a non-zero `message_id`
**THEN** the pipeline SHALL call `RequestMemory.mark_message_seen(message_id, reservation_id)`
immediately after classification, regardless of the classification result (including `"other"`).

This ensures that all classified messages — not just those with actionable intents — are recorded,
preventing re-classification of messages that were already determined to be irrelevant.

#### Scenario: Message classified as "other" is still marked seen
- **WHEN** `process_message` is called with a message that classifies as `intent="other"`
- **THEN** result SHALL be `action="ignored"`
- **AND** `has_message_been_seen(message_id)` SHALL return `True` after the call
