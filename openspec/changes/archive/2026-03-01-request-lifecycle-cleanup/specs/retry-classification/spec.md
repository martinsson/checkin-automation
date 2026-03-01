## ADDED Requirements

### Requirement: CLI script clears message dedup for retry
`scripts/retry_classification.py` SHALL accept a `--message-id` argument (required) and clear the corresponding entry from `seen_messages` so the next poll cycle re-classifies the message.

#### Scenario: Clear seen flag for a message
- **WHEN** the script is run with `--message-id 12345`
- **THEN** the `seen_messages` entry for message_id `12345` SHALL be deleted
- **AND** the script SHALL print confirmation of what was cleared

### Requirement: CLI script optionally accepts substitute message text
The script SHALL accept an optional `--message` argument. When provided, the substitute text SHALL be stored so the next classification uses it instead of the original message.

#### Scenario: Retry with substitute message
- **WHEN** the script is run with `--message-id 12345 --message "I want to check in at 12:00"`
- **THEN** the seen_messages entry SHALL be cleared
- **AND** the substitute message SHALL be stored for use in next classification

### Requirement: CLI script optionally clears existing request
The script SHALL accept an optional `--clear-request` flag. When provided and a request was created from that message, the request and its drafts SHALL be deleted so the pipeline creates fresh ones.

#### Scenario: Retry with request cleanup
- **WHEN** the script is run with `--message-id 12345 --clear-request`
- **AND** a request exists that was created from message 12345
- **THEN** the request and all its drafts SHALL be deleted
- **AND** the seen_messages entry SHALL be cleared

### Requirement: CLI script warns if no seen entry found
The script SHALL warn the user if the given message_id has no seen_messages entry, indicating it was never processed.

#### Scenario: Message not found
- **WHEN** the script is run with `--message-id 99999` and no seen entry exists
- **THEN** the script SHALL print a warning that the message was never seen
