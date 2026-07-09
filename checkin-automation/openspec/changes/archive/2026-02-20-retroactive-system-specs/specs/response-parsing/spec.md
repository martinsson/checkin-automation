## ADDED Requirements

### Requirement: Parse cleaner free-text reply into a structured answer
The `ResponseParser` port SHALL accept a raw text string from the cleaner and the original `CleanerQuery` and return a `ParsedResponse`. The `answer` field MUST be exactly one of `"yes"`, `"no"`, `"conditional"`, or `"unclear"`.

#### Scenario: Cleaner agrees unconditionally
- **WHEN** the cleaner's reply expresses unambiguous agreement (e.g. "Yes, no problem")
- **THEN** `ParsedResponse.answer` SHALL be `"yes"`
- **AND** `ParsedResponse.confidence` SHALL be ≥ 0.7

#### Scenario: Cleaner refuses
- **WHEN** the cleaner's reply expresses refusal (e.g. "No, we can't do that")
- **THEN** `ParsedResponse.answer` SHALL be `"no"`

#### Scenario: Cleaner agrees with conditions
- **WHEN** the cleaner's reply includes conditions (e.g. "Only if they arrive after 13:00")
- **THEN** `ParsedResponse.answer` SHALL be `"conditional"`
- **AND** `ParsedResponse.conditions` SHALL describe the condition as a non-empty string

#### Scenario: Cleaner reply is ambiguous
- **WHEN** the cleaner's reply cannot be clearly categorised
- **THEN** `ParsedResponse.answer` SHALL be `"unclear"`

### Requirement: Extract proposed time from cleaner reply when present
If the cleaner suggests a specific time, `ResponseParser` SHALL populate `proposed_time`.

#### Scenario: Cleaner proposes a time
- **WHEN** the cleaner's reply contains a time reference (e.g. "We can be done by 11:30")
- **THEN** `ParsedResponse.proposed_time` SHALL be the normalised time (e.g. `"11:30"`)

#### Scenario: No time in cleaner reply
- **WHEN** the cleaner's reply contains no time reference
- **THEN** `ParsedResponse.proposed_time` SHALL be `None`

### Requirement: Compose a polite guest reply from structured cleaner response
The `ReplyComposer` port SHALL accept a `ParsedResponse` and the original `CleanerQuery` and return a `ComposedReply` containing a complete, ready-to-send message body.

#### Scenario: Compose reply for positive answer
- **WHEN** `ParsedResponse.answer` is `"yes"`
- **THEN** `ComposedReply.body` SHALL confirm the request is granted in a friendly tone

#### Scenario: Compose reply for negative answer
- **WHEN** `ParsedResponse.answer` is `"no"`
- **THEN** `ComposedReply.body` SHALL apologise and explain the request cannot be accommodated

#### Scenario: Compose reply for conditional answer
- **WHEN** `ParsedResponse.answer` is `"conditional"`
- **THEN** `ComposedReply.body` SHALL communicate the conditions to the guest clearly

### Requirement: Compose guest acknowledgment immediately after intent detection
The `GuestAcknowledger` port SHALL accept a `ClassificationResult` and `ConversationContext` and return a `ComposedReply` that acknowledges the request and sets expectation that the owner is looking into it.

#### Scenario: Acknowledgment drafted for early check-in
- **WHEN** `ClassificationResult.intent` is `"early_checkin"`
- **THEN** `ComposedReply.body` SHALL reference the guest's early arrival request

#### Scenario: Acknowledgment drafted for late check-out
- **WHEN** `ClassificationResult.intent` is `"late_checkout"`
- **THEN** `ComposedReply.body` SHALL reference the guest's late departure request

### Requirement: All response adapters satisfy the same contract
Both Claude-backed and simulator implementations of `ResponseParser`, `ReplyComposer`, and `GuestAcknowledger` SHALL return correctly typed objects and pass the contract test suite scenarios.

#### Scenario: Simulator response parser returns valid ParsedResponse
- **WHEN** the simulator `ResponseParser.parse()` is called with any non-empty raw text
- **THEN** the result SHALL be a `ParsedResponse` with a valid `answer` and a `confidence` in `[0.0, 1.0]`
