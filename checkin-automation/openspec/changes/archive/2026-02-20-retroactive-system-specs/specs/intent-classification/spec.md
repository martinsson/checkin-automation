## ADDED Requirements

### Requirement: Classify guest message into a structured intent
The `IntentClassifier` port SHALL accept a guest message string and a `ConversationContext` and return a `ClassificationResult`. The result MUST contain exactly one of `"early_checkin"`, `"late_checkout"`, or `"other"` as the `intent` field.

#### Scenario: Early check-in request detected
- **WHEN** the guest message expresses a desire to arrive before the default check-in time
- **THEN** `ClassificationResult.intent` SHALL be `"early_checkin"`
- **AND** `ClassificationResult.confidence` SHALL be ≥ 0.5

#### Scenario: Late check-out request detected
- **WHEN** the guest message expresses a desire to depart after the default check-out time
- **THEN** `ClassificationResult.intent` SHALL be `"late_checkout"`
- **AND** `ClassificationResult.confidence` SHALL be ≥ 0.5

#### Scenario: Unrelated message
- **WHEN** the guest message is not about check-in or check-out timing
- **THEN** `ClassificationResult.intent` SHALL be `"other"`

### Requirement: Extract requested time when present
If the guest mentions a specific time, the classifier SHALL populate `extracted_time` with that time in `HH:MM` 24-hour format.

#### Scenario: Guest states a time
- **WHEN** the guest message contains a time reference (e.g. "12h", "noon", "13:00")
- **THEN** `ClassificationResult.extracted_time` SHALL be the normalised time string (e.g. `"12:00"`)

#### Scenario: No time mentioned
- **WHEN** the guest message contains no time reference
- **THEN** `ClassificationResult.extracted_time` SHALL be `None`

### Requirement: Signal when a follow-up question is needed
When the classifier cannot determine a specific time or intent with sufficient information, it SHALL set `needs_followup=True` and populate `followup_question` with a ready-to-send question in the guest's implied language.

#### Scenario: Intent unclear, follow-up required
- **WHEN** the classifier sets `needs_followup=True`
- **THEN** `ClassificationResult.followup_question` SHALL be a non-empty string
- **AND** the pipeline SHALL save it as a `"followup"` draft instead of an acknowledgment

#### Scenario: Intent clear, no follow-up needed
- **WHEN** the classifier can determine intent without additional information
- **THEN** `ClassificationResult.needs_followup` SHALL be `False`
- **AND** `ClassificationResult.followup_question` SHALL be `None`

### Requirement: ConversationContext provides all classification inputs
The `ConversationContext` dataclass SHALL carry all fields required for classification without additional lookups.

#### Scenario: Context fields available to classifier
- **WHEN** `classify()` is called
- **THEN** the classifier SHALL have access to `reservation_id`, `guest_name`, `property_name`, `default_checkin_time`, `default_checkout_time`, `arrival_date`, `departure_date`, and `previous_messages`

### Requirement: Both real and simulator adapters satisfy the same contract
All `IntentClassifier` implementations (Claude-backed and simulator) SHALL produce `ClassificationResult` instances that satisfy the type contract and the scenario expectations defined in the contract test suite.

#### Scenario: Simulator detects early check-in keywords
- **WHEN** the message contains French or English early check-in keywords (e.g. "tôt", "early", "plus tôt")
- **THEN** the simulator SHALL return `intent="early_checkin"`

#### Scenario: Simulator detects late check-out keywords
- **WHEN** the message contains French or English late check-out keywords (e.g. "tard", "late checkout", "plus tard")
- **THEN** the simulator SHALL return `intent="late_checkout"`
