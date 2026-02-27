## MODIFIED Requirements

### Requirement: Nothing is sent directly — all output goes through drafts
The pipeline SHALL never call `SmoobuGateway.send_message()` or `CleanerNotifier.send_query()` directly. All outbound messages SHALL be saved as drafts with `verdict="pending"` for owner review. **Sending happens in a separate dispatch step after review, outside the pipeline.**

#### Scenario: No direct send during process_message
- **WHEN** `process_message()` completes for any intent
- **THEN** `SmoobuGateway.send_message()` SHALL NOT have been called
- **AND** `CleanerNotifier.send_query()` SHALL NOT have been called

> Note: The dispatch step (`dispatch_reviewed_drafts`) runs outside the Pipeline class, in the daemon poll loop. The Pipeline remains a pure draft generator.
