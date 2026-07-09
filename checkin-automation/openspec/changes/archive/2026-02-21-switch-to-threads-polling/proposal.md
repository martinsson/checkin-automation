## Why

The current daemon polls Smoobu using `arrivalFrom=today` / `arrivalTo=today+N`, which misses guests who are already checked in (their arrival date is in the past). If a guest sends a late-checkout request mid-stay, the system never sees it.

`GET /api/threads` provides a global inbox sorted by most-recent activity across all reservations. It gives us the active reservation IDs in one call, which we can then use to fetch per-reservation messages and filter for guest messages (`type=1`). This is strictly superior: it catches all active conversations regardless of check-in date.

As a bonus, the thread-based approach maps directly to a future webhook integration — a webhook payload would identify a reservation ID, and the same `process_message()` pipeline could handle it without structural changes.

## What Changes

- **Daemon poll loop**: Replace the arrival-window scan with a thread-based scan. Poll `GET /api/threads`, paginate until threads older than a configurable cutoff (e.g. 7 days), fetch messages per reservation, filter type==1, deduplicate via existing `message_id` guard.
- **SmoobuGateway port**: Add `get_threads(page)` and `get_reservation(reservation_id)` methods.
- **GuestMessage**: Add `type` field (1=guest inbox, 2=host outbox) so the daemon can filter for guest messages only.
- **Reservation date cache**: Avoid repeated `GET /reservations/{id}` calls by storing arrival/departure on first sight in SQLite.

## Capabilities

### New Capabilities

- `reservation-cache`: Store and retrieve reservation metadata (arrival date, departure date, guest name, property name) keyed by reservation ID to avoid repeated API calls.

### Modified Capabilities

- `smoobu-gateway`: Add `get_threads(page_number)` returning a page of threads (reservation ID, guest name, apartment name, latest message timestamp). Add `get_reservation(reservation_id)` returning reservation metadata. Add `type` field to `GuestMessage`.
- `daemon-runner`: Replace arrival-window polling with thread-based activity scan. Use thread recency to bound pagination. Cache reservation dates on first sight.

## Impact

- Guests currently staying (arrived before today) will now have their messages processed — previously they were invisible to the system.
- The poll loop becomes simpler: one global threads endpoint instead of computing date windows.
- One new SQLite table (`reservation_cache`) for date caching.
- `get_active_reservations` on `SmoobuGateway` is no longer used by the daemon; it may be retained for backward compatibility or removed.
- The contract test for `get_threads()` will assert sort order (most-recent-activity descending) — if Smoobu returns threads in a different order, we will need to sort client-side.
