## ADDED Requirements

### Requirement: Store reservation metadata by reservation ID
`ReservationCache.store(reservation_id, info)` SHALL persist a `ReservationInfo` object keyed by `reservation_id`. Subsequent calls to `get(reservation_id)` SHALL return the stored value.

#### Scenario: Stored metadata retrieved
- **WHEN** `store(reservation_id, info)` is called followed by `get(reservation_id)`
- **THEN** the returned `ReservationInfo` SHALL match the stored value

#### Scenario: Unknown reservation returns None
- **WHEN** `get(reservation_id)` is called for a reservation that was never stored
- **THEN** `None` SHALL be returned

### Requirement: SQLite-backed reservation cache
`SqliteReservationCache` SHALL implement `ReservationCache` using a SQLite table `reservation_cache` with columns:
- `reservation_id INTEGER PRIMARY KEY`
- `guest_name TEXT NOT NULL`
- `apartment_name TEXT NOT NULL`
- `arrival TEXT NOT NULL` (ISO date)
- `departure TEXT NOT NULL` (ISO date)
- `cached_at TEXT NOT NULL` (ISO datetime UTC)

The table SHALL be created automatically on first connection (CREATE TABLE IF NOT EXISTS).

#### Scenario: Cache persists across instances
- **WHEN** a `SqliteReservationCache` stores a reservation and is then closed and re-opened on the same file
- **THEN** `get(reservation_id)` on the new instance SHALL return the same metadata

#### Scenario: Table created automatically
- **WHEN** `SqliteReservationCache` is initialised on a new database
- **THEN** no manual schema migration is required — the table is created on init

### Requirement: In-memory cache for testing
`InMemoryReservationCache` SHALL implement `ReservationCache` using a plain dict. It SHALL be instantiated without arguments and require no database.

#### Scenario: In-memory store and retrieve
- **WHEN** `store(reservation_id, info)` is called on an in-memory cache
- **THEN** `get(reservation_id)` SHALL return the same `ReservationInfo`

#### Scenario: Isolation between instances
- **WHEN** two `InMemoryReservationCache` instances are created independently
- **THEN** data stored in one SHALL NOT appear in the other
