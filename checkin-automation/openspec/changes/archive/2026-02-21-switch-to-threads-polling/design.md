## Context

The daemon currently polls `GET /api/reservations` filtered by `arrivalFrom/arrivalTo` to find reservations to check. This window-based approach misses guests who have already checked in — their arrival date is in the past and they fall outside the window.

`GET /api/threads` is Smoobu's global inbox endpoint. It returns threads sorted by most-recent-activity (assumed descending — to be verified by the `get_threads` contract test). Each thread carries a `booking.id` (reservation ID), so we can use threads as an activity index: fetch threads until we hit a configurable age cutoff, then process per-reservation messages for each seen reservation ID.

## Goals / Non-Goals

**Goals:**
- Catch all active conversations regardless of check-in date
- Reduce API calls by using threads as a bounded activity index rather than scanning all reservations
- Cache reservation metadata to avoid repeated `GET /reservations/{id}` lookups
- Keep the existing `process_message()` pipeline and message-level dedup (`has_message_been_seen`) unchanged
- Lay the groundwork for a future webhook integration (same pipeline, same dedup, just a different trigger)

**Non-Goals:**
- Implement a webhook handler (future work)
- Remove `get_active_reservations` from the port (retain for backward compatibility)
- Change the draft-first review workflow

## Decisions

### Thread sort order assumption
We assume `GET /api/threads` returns threads sorted by most-recent-activity descending. The contract test (`test_get_threads_sorted_by_recency`) will assert this. If Smoobu returns threads in a different order, we will sort client-side by `latest_message.created_at` before pagination cutoff logic kicks in.

### Pagination cutoff strategy
Stop paginating threads when the page's `latest_message.created_at` is older than `THREADS_CUTOFF_DAYS` (default: 7 days). This bounds the API call count per cycle regardless of how many total threads exist.

### Per-reservation message fetch still required
The threads endpoint gives us only the latest message per thread, not all messages. We still need `GET /reservations/{id}/messages` to get the full message list and filter by `type=1` (guest). This is unchanged from the current approach.

### Reservation date caching
`GET /api/threads` does not include arrival/departure dates. We need those to build `ConversationContext`. Rather than calling `GET /reservations/{id}` on every cycle for every thread, we cache reservation metadata in a new SQLite table `reservation_cache` on first sight. The TTL is indefinite (reservation dates don't change).

### GuestMessage type field
The `type` field on `GuestMessage` is essential for filtering. `type=1` is guest (inbox), `type=2` is host (outbox). The daemon should only pass `type=1` messages to the pipeline. The field is added to the domain model so contract tests can assert on it.

### Daemon loop structure
```
poll_once():
  threads = paginate GET /api/threads (stop when oldest thread > cutoff)
  for each unique reservation_id in threads:
    reservation = cache.get(reservation_id) or fetch_and_cache()
    messages = gateway.get_messages(reservation_id)
    guest_messages = [m for m in messages if m.type == 1]
    if not guest_messages: continue
    last = guest_messages[-1]
    if memory.has_message_been_seen(last.message_id): continue
    context = build_context(reservation)
    pipeline.process_message(reservation_id, last.body, context, last.message_id)
  pipeline.process_cleaner_responses()
```

## Risks / Trade-offs

- **Sort order assumption**: If threads aren't sorted by recency, the cutoff logic may terminate early and miss active reservations. The contract test mitigates this; if it fails we add client-side sort.
- **Threads API rate limits**: Paginating threads on every cycle adds one extra Smoobu API call per page. With a 7-day cutoff and typical activity, this should be 1–2 extra calls per cycle.
- **Cache staleness**: Reservation dates stored in cache won't update if a guest extends their stay. For now this is acceptable — edge case, and the host can clear the cache if needed.
- **Only latest guest message processed per cycle**: Same behavior as before. Mid-stay conversations work because `message_id` dedup ensures only new messages trigger the pipeline.
