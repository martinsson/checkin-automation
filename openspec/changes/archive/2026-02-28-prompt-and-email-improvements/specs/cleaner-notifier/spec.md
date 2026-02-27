## MODIFIED Requirements

### Requirement: Send a structured query to cleaning staff
`CleanerNotifier.send_query(query: CleanerQuery)` SHALL deliver the query to the cleaner via the configured channel (email, console, or other) and return a tracking ID string.

#### Scenario: Email body uses French greeting template
- **WHEN** `EmailCleanerNotifier.send_query(query)` is called
- **THEN** the email body SHALL be formatted as:
  ```
  Bonjour <cleaner_name>,

  Voici une nouvelle demande, dites moi ce qui est possible, raisonnablement bien entendu.

  <guest's message translated into French>

  [REQ-<request_id>]
  ```
- **AND** the subject SHALL be `<property_name> — <date>` without the `[REQ-...]` tag

#### Scenario: Request ID available in email body for reply correlation
- **WHEN** a cleaner replies to the email
- **THEN** `poll_responses()` SHALL extract the request ID from the `X-Request-ID` header, OR from the `[REQ-...]` tag in the quoted body, OR from the subject line (legacy fallback)

#### Scenario: Console notifier prints formatted output
- **WHEN** `ConsoleCleanerNotifier.send_query(query)` is called
- **THEN** it SHALL print the query content to stdout (format is adapter-specific, no template required)
