## ADDED Requirements

### Requirement: Poll Smoobu at a configurable interval
The daemon SHALL call `poll_once()` in an infinite loop, sleeping for `POLL_INTERVAL` seconds between iterations. The default interval SHALL be 60 seconds when `POLL_INTERVAL` is not set.

#### Scenario: Default interval used when env var absent
- **WHEN** `POLL_INTERVAL` is not set in the environment
- **THEN** the daemon SHALL sleep 60 seconds between polls

#### Scenario: Custom interval respected
- **WHEN** `POLL_INTERVAL=30` is set
- **THEN** the daemon SHALL sleep 30 seconds between polls

### Requirement: Monitor active conversations via thread-based activity scan
The daemon SHALL use `GET /api/threads` as the activity index rather than scanning reservations by arrival date. The daemon SHALL paginate threads until it encounters a page where all threads have `latest_message_at` older than `THREADS_CUTOFF_DAYS` days ago (default: 7).

The `LOOKAHEAD_DAYS` environment variable is no longer used by the poll loop.

#### Scenario: Thread pagination stops at cutoff
- **WHEN** a page of threads contains entries all older than `THREADS_CUTOFF_DAYS` days
- **THEN** pagination SHALL stop and no further pages SHALL be fetched

#### Scenario: Active threads within cutoff are processed
- **WHEN** a thread has `latest_message_at` within the cutoff window
- **THEN** the daemon SHALL fetch messages for its reservation and process any new guest messages

#### Scenario: Reservations beyond cutoff not processed
- **WHEN** all threads on a page have `latest_message_at` older than the cutoff
- **THEN** those reservations SHALL NOT be processed in that cycle

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

### Requirement: Filter guest-only messages by type field
The daemon SHALL only pass messages with `type == 1` (guest inbox) to the pipeline. Messages with `type == 2` (host outbox) SHALL be ignored.

#### Scenario: Host messages not passed to pipeline
- **WHEN** `get_messages(reservation_id)` returns a mix of type=1 and type=2 messages
- **THEN** only type=1 messages SHALL be considered when selecting the latest message to process

#### Scenario: No guest messages skips reservation
- **WHEN** all messages for a reservation have `type == 2`
- **THEN** `pipeline.process_message()` SHALL NOT be called for that reservation

### Requirement: Reservation metadata fetched via gateway and cached
The daemon SHALL call `reservation_cache.get(reservation_id)`. If not found, it SHALL call `gateway.get_reservation(reservation_id)`, store the result in the cache, and use it to build `ConversationContext`.

#### Scenario: Cache hit avoids gateway call
- **WHEN** a reservation's metadata is already in the cache
- **THEN** `gateway.get_reservation()` SHALL NOT be called for that reservation in the same cycle

#### Scenario: Cache miss triggers gateway fetch and storage
- **WHEN** a reservation's metadata is not in the cache
- **THEN** `gateway.get_reservation()` SHALL be called once and the result stored

### Requirement: Required environment variable THREADS_CUTOFF_DAYS
The daemon SHALL read `THREADS_CUTOFF_DAYS` from the environment to configure the thread age cutoff. Default is 7.

#### Scenario: Default cutoff used when env var absent
- **WHEN** `THREADS_CUTOFF_DAYS` is not set
- **THEN** threads older than 7 days SHALL be excluded

#### Scenario: Custom cutoff respected
- **WHEN** `THREADS_CUTOFF_DAYS=14` is set
- **THEN** threads older than 14 days SHALL be excluded
