## MODIFIED Requirements

### Requirement: Port location
IntentClassifier ABC and its data types (ConversationContext, ClassificationResult) SHALL be defined in `src/ports/intent.py`. ClassificationResult SHALL NOT contain `needs_followup` or `followup_question` fields.

#### Scenario: Import path updated
- **WHEN** code imports IntentClassifier, ConversationContext, or ClassificationResult
- **THEN** the import SHALL be from `src.ports.intent`

#### Scenario: ClassificationResult has no followup fields
- **WHEN** a ClassificationResult is constructed
- **THEN** it SHALL have fields: `intent`, `confidence`, `extracted_time`
- **AND** it SHALL NOT have `needs_followup` or `followup_question`

## REMOVED Requirements

### Requirement: ClassificationResult includes followup fields
**Reason**: The followup path is removed. When no time is extracted, the system proceeds with the full request anyway, forwarding the guest's original message to the cleaner.
**Migration**: Remove `needs_followup: bool` and `followup_question: str | None` from ClassificationResult. All callers that checked `needs_followup` are updated to treat every classification as directly actionable.
