## ADDED Requirements

### Requirement: Poll Smoobu at a configurable interval
The daemon SHALL call `poll_once()` in an infinite loop, sleeping for `POLL_INTERVAL` seconds between iterations. The default interval SHALL be 60 seconds when `POLL_INTERVAL` is not set.

#### Scenario: Default interval used when env var absent
- **WHEN** `POLL_INTERVAL` is not set in the environment
- **THEN** the daemon SHALL sleep 60 seconds between polls

#### Scenario: Custom interval respected
- **WHEN** `POLL_INTERVAL=30` is set
- **THEN** the daemon SHALL sleep 30 seconds between polls

### Requirement: Monitor reservations arriving within a configurable look-ahead window
Each poll cycle SHALL query Smoobu for reservations with arrival dates between today and `today + LOOKAHEAD_DAYS`. The default look-ahead SHALL be 14 days when `LOOKAHEAD_DAYS` is not set.

#### Scenario: Default look-ahead used when env var absent
- **WHEN** `LOOKAHEAD_DAYS` is not set
- **THEN** the daemon SHALL request reservations for the next 14 days

#### Scenario: Reservations beyond the window not processed
- **WHEN** a reservation's arrival date is beyond `today + LOOKAHEAD_DAYS`
- **THEN** it SHALL NOT appear in the fetched reservation list

### Requirement: Process only the latest guest message per reservation per cycle
Within each poll cycle, for each reservation the daemon SHALL extract the last non-empty guest message and pass only that message to `pipeline.process_message()`. Earlier messages SHALL be passed as `previous_messages` in the `ConversationContext`.

#### Scenario: Only last message processed
- **WHEN** a reservation has three guest messages
- **THEN** only the third message SHALL be passed as the `message` argument
- **AND** the first two SHALL appear in `context.previous_messages`

#### Scenario: Reservation with no messages skipped
- **WHEN** `get_messages()` returns an empty list for a reservation
- **THEN** `pipeline.process_message()` SHALL NOT be called for that reservation

### Requirement: Cleaner response polling runs at the end of every poll cycle
After processing all reservation messages, the daemon SHALL call `pipeline.process_cleaner_responses()` once per cycle.

#### Scenario: Cleaner polling occurs after guest message processing
- **WHEN** a poll cycle completes guest message processing
- **THEN** `pipeline.process_cleaner_responses()` SHALL be called before sleeping

### Requirement: Errors per reservation are isolated and logged
An exception raised while fetching messages or running the pipeline for one reservation SHALL be caught, logged at `ERROR` level, and SHALL NOT abort processing of other reservations in the same cycle.

#### Scenario: One failing reservation does not abort cycle
- **WHEN** `get_messages()` raises an exception for reservation A
- **THEN** reservation B in the same cycle SHALL still be processed

#### Scenario: Pipeline error logged with reservation ID
- **WHEN** `pipeline.process_message()` raises an exception for a reservation
- **THEN** the error log message SHALL include the `reservation_id`

### Requirement: Required environment variables checked at startup
The daemon SHALL validate that `SMOOBU_API_KEY`, `SMOOBU_APARTMENT_ID`, and `ANTHROPIC_API_KEY` are set. If any are missing, the daemon SHALL print an error to stderr and exit with a non-zero status code before starting the poll loop.

#### Scenario: Missing required env var causes immediate exit
- **WHEN** `ANTHROPIC_API_KEY` is not set
- **THEN** the daemon SHALL print an error message referencing the missing variable
- **AND** SHALL exit before making any network calls

### Requirement: SQLite database directory created on startup
The daemon SHALL create the directory for `DB_PATH` if it does not exist, before initialising `SqliteRequestMemory`. The default path SHALL be `data/checkin.db`.

#### Scenario: Missing data directory created automatically
- **WHEN** the `data/` directory does not exist and `DB_PATH` uses the default
- **THEN** the daemon SHALL create the directory and succeed in opening the database
