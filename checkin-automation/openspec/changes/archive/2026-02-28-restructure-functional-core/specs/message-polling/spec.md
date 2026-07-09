## ADDED Requirements

### Requirement: Guest message poller discovers new messages from Smoobu threads
The guest message poller SHALL paginate `SmoobuGateway.get_threads()`, filter by cutoff date, deduplicate reservation IDs, fetch messages and reservation metadata, and yield structured items containing (reservation_id, latest guest message, ConversationContext) for each reservation with new activity.

#### Scenario: Threads within cutoff are discovered
- **WHEN** the poller runs and threads exist with `latest_message_at` within the cutoff window
- **THEN** it SHALL yield items for those reservations

#### Scenario: Threads beyond cutoff are excluded
- **WHEN** all threads on a page have `latest_message_at` older than the cutoff
- **THEN** pagination SHALL stop and those reservations SHALL not be yielded

#### Scenario: Only latest guest message is included per reservation
- **WHEN** a reservation has multiple type=1 messages
- **THEN** the yielded item SHALL contain only the latest as the message, with earlier messages in `previous_messages`

#### Scenario: Reservation metadata is fetched with cache-through
- **WHEN** a reservation is discovered
- **THEN** the poller SHALL check the cache first, fetch from gateway on miss, and store in cache

### Requirement: Cleaner response poller discovers new responses
The cleaner response poller SHALL call `CleanerNotifier.poll_responses()` and yield each `CleanerResponse` for handling.

#### Scenario: New cleaner responses are yielded
- **WHEN** `poll_responses()` returns responses
- **THEN** the poller SHALL yield each response for handling

#### Scenario: No responses yields nothing
- **WHEN** `poll_responses()` returns an empty list
- **THEN** the poller SHALL yield nothing

### Requirement: Pollers are symmetric infrastructure
Both pollers SHALL follow the same pattern: fetch raw data from an external source, filter/transform, yield items for handlers. This compensates for the absence of webhooks. If a webhook becomes available, the poller can be replaced without changing the handler.

#### Scenario: Handler works without poller
- **WHEN** a handler receives a message item directly (e.g., from a webhook)
- **THEN** it SHALL process it identically to when the item came from a poller
