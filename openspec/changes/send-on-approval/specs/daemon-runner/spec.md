## ADDED Requirements

### Requirement: Dispatch reviewed drafts at the end of each poll cycle
After `pipeline.process_cleaner_responses()`, the daemon SHALL call `dispatch_reviewed_drafts()` to send any drafts that have been reviewed by the owner but not yet sent.

#### Scenario: Dispatch runs after cleaner response polling
- **WHEN** a poll cycle completes guest message processing and cleaner response polling
- **THEN** `dispatch_reviewed_drafts()` SHALL be called before the daemon sleeps

#### Scenario: Dispatch needs SmoobuGateway and CleanerNotifier
- **WHEN** `dispatch_reviewed_drafts()` is called
- **THEN** it SHALL have access to `RequestMemory`, `SmoobuGateway`, and `CleanerNotifier` to send via the appropriate channel
