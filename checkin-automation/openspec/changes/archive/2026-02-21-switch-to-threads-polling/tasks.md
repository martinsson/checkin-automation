## 1. Domain Models

- [x] 1.1 Add `type: int` field to `GuestMessage` in `src/adapters/ports.py` (default `1` for backward compat with existing simulator/tests)
- [x] 1.2 Add `Thread` dataclass to `src/adapters/ports.py`: `reservation_id`, `guest_name`, `apartment_name`, `latest_message_at: datetime`
- [x] 1.3 Add `ThreadPage` dataclass to `src/adapters/ports.py`: `threads: list[Thread]`, `has_more: bool`
- [x] 1.4 Add `ReservationInfo` dataclass to `src/adapters/ports.py`: `reservation_id`, `guest_name`, `apartment_name`, `arrival: str`, `departure: str`

## 2. SmoobuGateway Port

- [x] 2.1 Add abstract `get_threads(page_number: int) -> ThreadPage` to `SmoobuGateway` ABC in `src/adapters/ports.py`
- [x] 2.2 Add abstract `get_reservation(reservation_id: int) -> ReservationInfo | None` to `SmoobuGateway` ABC

## 3. ReservationCache Port and Adapters

- [x] 3.1 Create `src/domain/reservation_cache.py`: `ReservationCache` ABC with `store()` and `get()` abstract methods
- [x] 3.2 Create `src/adapters/sqlite_reservation_cache.py`: `SqliteReservationCache` implementing `ReservationCache` with `reservation_cache` table (auto-created on init)
- [x] 3.3 Create `InMemoryReservationCache` in `src/adapters/simulator_reservation_cache.py` using a plain dict

## 4. SmoobuGateway Adapter: Real Implementation

- [x] 4.1 Implement `get_threads(page_number)` in `SmoobuClient` (`src/adapters/smoobu_client.py`): call `GET /api/threads?page_number=N&page_size=25`, map response to `ThreadPage`
- [x] 4.2 Implement `get_reservation(reservation_id)` in `SmoobuClient`: call `GET /api/reservations/{id}`, map to `ReservationInfo` (or `None` on 404)
- [x] 4.3 Update `get_messages()` to populate the `type` field from the Smoobu message response

## 5. SmoobuGateway Simulator

- [x] 5.1 Implement `get_threads()` in `SimulatorSmoobuGateway`: derive threads from injected reservations, ordered by most-recent message timestamp descending
- [x] 5.2 Implement `get_reservation()` in `SimulatorSmoobuGateway`: return `ReservationInfo` for injected reservations
- [x] 5.3 Update `inject_active_reservation()` to record arrival/departure so `get_reservation()` can return them
- [x] 5.4 Update simulator `inject_guest_message()` to accept `type` field (default `1`); `send_message()` produces type=2

## 6. Contract Tests

- [x] 6.1 Add `test_get_threads_returns_thread_page` to `tests/contracts/smoobu_gateway_contract.py`
- [x] 6.2 Add `test_get_threads_sorted_by_recency` to the contract (asserts threads ordered most-recent first)
- [x] 6.3 Add `test_get_threads_thread_fields_present` to the contract (has_more pagination signal covered via simulator)
- [x] 6.4 Add `test_get_reservation_unknown_returns_none` to the contract
- [x] 6.5 Add `test_get_messages_type_field_present` to the contract (type=1 or 2 for all messages)
- [x] 6.6 Create `tests/contracts/reservation_cache_contract.py` with `test_store_and_get`, `test_unknown_returns_none`, `test_overwrite_updates_value`
- [x] 6.7 Create `tests/test_smoobu_simulator_threads.py` running the contract against `SimulatorSmoobuGateway`
- [x] 6.8 Create `tests/test_reservation_cache.py` running the cache contract against `InMemoryReservationCache` and `SqliteReservationCache`

## 7. Daemon poll_once Rewrite

- [x] 7.1 Rewrite `poll_once()` in `src/daemon.py` to use thread-based activity scan: paginate `get_threads()`, stop when all threads on page are older than `THREADS_CUTOFF_DAYS`, collect unique reservation IDs
- [x] 7.2 For each reservation ID: check reservation cache, fetch via `get_reservation()` if missing, build `ConversationContext`
- [x] 7.3 Filter messages by `type == 1`, skip reservation if no guest messages
- [x] 7.4 Pass latest guest message to `pipeline.process_message()` with `message_id`
- [x] 7.5 Add `THREADS_CUTOFF_DAYS` env var (default 7) to `scripts/run.py` → `poll_once()` config

## 8. Daemon Tests

- [x] 8.1 Update `tests/test_daemon.py`: use updated simulator with threads, verify only guest messages (type=1) are passed to pipeline
- [x] 8.2 Add test: pagination stops when all threads on page older than cutoff
- [x] 8.3 Add test: cache hit avoids `get_reservation()` call on second cycle
- [x] 8.4 Add test: reservation with only host messages (type=2) is skipped
