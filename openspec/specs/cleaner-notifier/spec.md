## ADDED Requirements

### Requirement: Send a structured query to cleaning staff
`CleanerNotifier.send_query(query: CleanerQuery)` SHALL deliver the query to the cleaner via the configured channel (email, console, or other) and return a tracking ID string.

#### Scenario: Query sent and tracking ID returned
- **WHEN** `send_query(query)` is called with a valid `CleanerQuery`
- **THEN** a non-empty tracking ID string SHALL be returned
- **AND** the cleaner SHALL receive the message content

#### Scenario: CleanerQuery carries all required fields
- **WHEN** a `CleanerQuery` is constructed
- **THEN** it SHALL contain `request_id`, `cleaner_name`, `guest_name`, `property_name`, `request_type`, `original_time`, `requested_time`, `date`, and `message`

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

### Requirement: Poll for new cleaner responses since last poll
`CleanerNotifier.poll_responses()` SHALL return all unprocessed `CleanerResponse` objects received since the last call. Each response SHALL carry the `request_id` that correlates it to the original query, the `raw_text` of the cleaner's reply, and `received_at` timestamp.

#### Scenario: Response returned for outstanding query
- **WHEN** a cleaner has replied and `poll_responses()` is called
- **THEN** a `CleanerResponse` SHALL be returned with `request_id` matching the original query

#### Scenario: No new responses
- **WHEN** no replies have been received since the last poll
- **THEN** `poll_responses()` SHALL return an empty list

#### Scenario: Responses not returned twice
- **WHEN** `poll_responses()` has already returned a response
- **THEN** subsequent calls SHALL NOT return the same response again

### Requirement: Console notifier prints to stdout for testing and development
`ConsoleCleanerNotifier` SHALL write the query content to stdout and accept responses via an in-process queue or pre-configured stubs. It SHALL satisfy the full `CleanerNotifier` contract.

#### Scenario: Console notifier send_query completes without error
- **WHEN** `send_query(query)` is called on the console notifier
- **THEN** the method SHALL return a non-empty string without raising an exception

#### Scenario: Console notifier poll_responses returns empty by default
- **WHEN** `poll_responses()` is called on the console notifier with no pre-loaded responses
- **THEN** an empty list SHALL be returned

### Requirement: Both email and console adapters satisfy the CleanerNotifier contract
All `CleanerNotifier` implementations SHALL return correctly typed objects and pass the contract test suite scenarios without raising unexpected exceptions.

#### Scenario: Contract test passes for any implementation
- **WHEN** the contract test fixture is run against any `CleanerNotifier` implementation
- **THEN** `send_query()` SHALL return a string and `poll_responses()` SHALL return a list of `CleanerResponse`
