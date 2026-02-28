## MODIFIED Requirements

### Requirement: Port location
IntentClassifier ABC and its data types (ConversationContext, ClassificationResult) SHALL be defined in `src/ports/intent.py`. No behavioral changes.

#### Scenario: Import path updated
- **WHEN** code imports IntentClassifier, ConversationContext, or ClassificationResult
- **THEN** the import SHALL be from `src.ports.intent`
