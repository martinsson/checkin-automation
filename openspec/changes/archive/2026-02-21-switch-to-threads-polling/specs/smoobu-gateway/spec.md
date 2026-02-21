## ADDED Requirements

### Requirement: Retrieve a page of message threads
`SmoobuGateway.get_threads(page_number)` SHALL return a `ThreadPage` object containing a list of `Thread` items and a boolean `has_more` indicating whether further pages exist.

Each `Thread` SHALL have:
- `reservation_id: int`
- `guest_name: str`
- `apartment_name: str`
- `latest_message_at: datetime` (UTC)

#### Scenario: Threads returned sorted by recency
- **WHEN** `get_threads(page_number=1)` is called and multiple threads exist
- **THEN** threads SHALL be ordered from most-recently-active to least-recently-active
- **AND** each thread SHALL have a non-null `reservation_id` and `latest_message_at`

#### Scenario: No threads available
- **WHEN** no threads exist (empty inbox)
- **THEN** `get_threads(1)` SHALL return a `ThreadPage` with an empty list and `has_more=False`

#### Scenario: Pagination indicated by has_more
- **WHEN** there are more threads beyond the current page
- **THEN** `has_more` SHALL be `True`
- **AND** calling `get_threads(page_number + 1)` SHALL return the next page

### Requirement: Retrieve reservation metadata
`SmoobuGateway.get_reservation(reservation_id)` SHALL return a `ReservationInfo` object with:
- `reservation_id: int`
- `guest_name: str`
- `apartment_name: str`
- `arrival: str` (ISO date, `YYYY-MM-DD`)
- `departure: str` (ISO date, `YYYY-MM-DD`)

#### Scenario: Reservation found
- **WHEN** `get_reservation(reservation_id)` is called for an existing reservation
- **THEN** a `ReservationInfo` with non-null `arrival` and `departure` SHALL be returned

#### Scenario: Reservation not found
- **WHEN** `get_reservation(reservation_id)` is called for an unknown reservation ID
- **THEN** `None` SHALL be returned

### Requirement: GuestMessage includes sender type
`GuestMessage` SHALL include a `type` field: `1` for guest messages (inbox) and `2` for host messages (outbox).

#### Scenario: Guest messages have type 1
- **WHEN** `get_messages(reservation_id)` returns messages sent by the guest
- **THEN** each such message SHALL have `type == 1`

#### Scenario: Host messages have type 2
- **WHEN** `get_messages(reservation_id)` returns messages sent by the host
- **THEN** each such message SHALL have `type == 2`

### Requirement: Simulator supports thread-based access
`SimulatorSmoobuGateway` SHALL implement `get_threads()` and `get_reservation()`.

`get_threads()` SHALL return threads derived from injected reservations, ordered by most-recent guest message timestamp descending.

`get_reservation()` SHALL return `ReservationInfo` for reservations injected via `inject_active_reservation()`.

#### Scenario: Simulator get_threads returns injected reservations
- **WHEN** reservations are injected via `inject_active_reservation()` with messages
- **THEN** `get_threads(1)` SHALL include a thread for each injected reservation

#### Scenario: Simulator get_reservation returns metadata
- **WHEN** `get_reservation(reservation_id)` is called for an injected reservation
- **THEN** the returned `ReservationInfo` SHALL match the injected arrival and departure dates
