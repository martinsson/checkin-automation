## MODIFIED Requirements

### Requirement: Monitor reservations arriving within a configurable look-ahead window
**Reason for modification**: The arrival-window scan is replaced by thread-based activity scanning. The look-ahead concept no longer applies to the primary poll loop.

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

## ADDED Requirements

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
