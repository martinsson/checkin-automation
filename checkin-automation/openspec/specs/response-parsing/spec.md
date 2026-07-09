## MODIFIED Requirements

### Requirement: Port location
GuestAcknowledger, ResponseParser, ReplyComposer ABCs and their data types (ParsedResponse, ComposedReply) SHALL be defined in `src/ports/response.py`. No behavioral changes.

#### Scenario: Import path updated
- **WHEN** code imports GuestAcknowledger, ResponseParser, ReplyComposer, ParsedResponse, or ComposedReply
- **THEN** the import SHALL be from `src.ports.response`
