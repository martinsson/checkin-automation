## ADDED Requirements

### Requirement: Pure triage function decides whether to act on a guest message
`triage()` SHALL be a pure, synchronous function that accepts: `message_id`, `is_seen` (bool), `classification` (ClassificationResult or None), and `is_processed` (bool). It SHALL return one of: `Skip(reason)` or `Actionable(request_id, intent, ...)`. It SHALL have no side effects and no async calls.

#### Scenario: Already-seen message returns Skip
- **WHEN** `triage()` is called with `is_seen=True`
- **THEN** it SHALL return `Skip(reason="message already seen")`

#### Scenario: Intent "other" returns Skip
- **WHEN** `triage()` is called with a classification where `intent="other"`
- **THEN** it SHALL return `Skip(reason="ignored")`

#### Scenario: Already-processed request returns Skip
- **WHEN** `triage()` is called with `is_processed=True` and an actionable intent
- **THEN** it SHALL return `Skip(reason="already processed")`

#### Scenario: New actionable intent returns Actionable
- **WHEN** `triage()` is called with `is_seen=False`, `is_processed=False`, and `intent="early_checkin"`
- **THEN** it SHALL return an `Actionable` result containing the intent and extracted context fields

#### Scenario: No extracted time still returns Actionable
- **WHEN** `triage()` is called with a classification where `extracted_time` is None and `intent="early_checkin"`
- **THEN** it SHALL return an `Actionable` result with `extracted_time=None`
- **AND** it SHALL NOT return a Followup

### Requirement: Pure plan_drafts function produces draft commands
`plan_drafts()` SHALL be a pure, synchronous function that accepts an `Actionable` triage result and an acknowledgment body (str). It SHALL return a list of command objects describing what drafts to save and what status to set. It SHALL not call any ports or perform I/O.

#### Scenario: Actionable result produces acknowledgment and cleaner_query commands
- **WHEN** `plan_drafts()` is called with an `Actionable` result for `intent="early_checkin"` and an acknowledgment body
- **THEN** it SHALL return commands to save an `"acknowledgment"` draft, save a `"cleaner_query"` draft, and update status to `"pending_acknowledgment"`

### Requirement: Pure build_cleaner_query assembles a CleanerQuery from context
`build_cleaner_query()` SHALL be a pure, synchronous function that constructs a `CleanerQuery` dataclass from an `Actionable` result, conversation context, and cleaner name. No I/O.

#### Scenario: CleanerQuery built with correct fields
- **WHEN** `build_cleaner_query()` is called with an Actionable result for early_checkin
- **THEN** the returned `CleanerQuery` SHALL have `request_type="early_checkin"`, the guest name from context, and the extracted time from the classification

## REMOVED Requirements

### Requirement: Followup triage result
**Reason**: The followup path is removed. When the guest does not mention a specific time, the system creates a full request anyway and forwards the original message to the cleaner.
**Migration**: Remove `Followup` dataclass from `src/domain/guest_request.py`. Remove the `needs_followup` branch from `triage()`. `TriageResult` becomes `Skip | Actionable`. The handler no longer has a `followup_drafted` code path.
