## ADDED Requirements

### Requirement: Retrieve all messages for a reservation
`SmoobuGateway.get_messages(reservation_id)` SHALL return a list of `GuestMessage` objects for the given reservation. The list SHALL be ordered as returned by Smoobu (chronological). An empty list SHALL be returned when no messages exist.

#### Scenario: Messages available for reservation
- **WHEN** `get_messages(reservation_id)` is called for a reservation with messages
- **THEN** each returned `GuestMessage` SHALL have non-null `message_id`, `subject`, and `body` fields

#### Scenario: No messages for reservation
- **WHEN** `get_messages(reservation_id)` is called for a reservation with no messages
- **THEN** an empty list SHALL be returned

### Requirement: Send a message to a guest on a reservation
`SmoobuGateway.send_message(reservation_id, subject, body)` SHALL deliver the message to the guest via the Smoobu platform. The method SHALL raise an exception if the send fails.

#### Scenario: Message sent to simulator
- **WHEN** `send_message(reservation_id, subject, body)` is called on the simulator
- **THEN** the message SHALL appear in subsequent calls to `get_messages(reservation_id)`

### Requirement: List active reservations within a date range
`SmoobuGateway.get_active_reservations(apartment_id, arrival_from, arrival_to)` SHALL return `ActiveReservation` objects for all reservations arriving within the specified date range (inclusive, ISO format `YYYY-MM-DD`).

#### Scenario: Reservations within range returned
- **WHEN** `get_active_reservations(apartment_id, arrival_from, arrival_to)` is called
- **THEN** each returned `ActiveReservation` SHALL have `reservation_id`, `guest_name`, `arrival`, `departure`, and `apartment_id` populated

#### Scenario: No reservations in range
- **WHEN** no reservations exist within the date range
- **THEN** an empty list SHALL be returned

### Requirement: Simulator maintains per-reservation message state
`SimulatorSmoobuGateway` SHALL store messages in memory per reservation. Messages added via `send_message()` or seeded via the constructor SHALL be retrievable via `get_messages()`.

#### Scenario: Simulator seeds initial messages
- **WHEN** the simulator is initialised with pre-seeded reservation data
- **THEN** `get_messages(reservation_id)` SHALL return those seeded messages

#### Scenario: Simulator tracks sent messages
- **WHEN** `send_message(reservation_id, subject, body)` is called on the simulator
- **THEN** the count of messages returned by `get_messages(reservation_id)` SHALL increase by one
