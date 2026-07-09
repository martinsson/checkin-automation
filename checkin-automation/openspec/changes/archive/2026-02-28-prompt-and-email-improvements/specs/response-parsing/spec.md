## MODIFIED Requirements

### Requirement: Compose a polite guest reply from structured cleaner response
The `ReplyComposer` port SHALL accept a `ParsedResponse` and the original `CleanerQuery` and return a `ComposedReply` containing a complete, ready-to-send message body.

#### Scenario: Tip mention is brief and optional
- **WHEN** `ParsedResponse.answer` is `"yes"` or `"conditional"`
- **THEN** `ComposedReply.body` MAY include a single brief sentence about tipping (e.g. "certains voyageurs laissent un petit pourboire, c'est tout à fait optionnel")
- **AND** the tip mention SHALL NOT exceed one sentence
- **AND** the tip mention SHALL NOT be the focus of the message
