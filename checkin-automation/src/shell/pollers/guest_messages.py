"""
Guest message poller — discovers new guest messages from Smoobu threads.

Infrastructure concern: compensates for the lack of webhooks.
Fetches threads, filters by cutoff, deduplicates, fetches messages,
and yields structured items for the handler.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from src.ports.intent import ConversationContext
from src.ports.smoobu import GuestMessage, ReservationInfo, SmoobuGateway
from src.ports.reservation_cache import ReservationCache

log = logging.getLogger(__name__)


@dataclass
class DiscoveredMessage:
    """A new guest message ready for handling."""
    reservation_id: int
    message: GuestMessage
    context: ConversationContext


def _get_reservation(
    reservation_id: int,
    smoobu: SmoobuGateway,
    cache: ReservationCache,
) -> ReservationInfo | None:
    """Cache-through reservation lookup."""
    info = cache.get(reservation_id)
    if info is not None:
        return info
    info = smoobu.get_reservation(reservation_id)
    if info is not None:
        cache.store(reservation_id, info)
    return info


def poll(
    smoobu: SmoobuGateway,
    cache: ReservationCache,
    threads_cutoff_days: int = 7,
) -> list[DiscoveredMessage]:
    """
    Discover new guest messages from Smoobu threads.

    Paginates threads, filters by cutoff, fetches messages for each
    reservation, and returns the latest guest message per reservation.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=threads_cutoff_days)

    # Collect unique reservation IDs from threads within cutoff
    reservation_ids: list[int] = []
    seen_ids: set[int] = set()
    threads_seen = 0
    page = 1
    while True:
        try:
            thread_page = smoobu.get_threads(page_number=page)
        except Exception as exc:
            log.error("Failed to fetch threads page %d: %s", page, exc)
            break

        if not thread_page.threads:
            break

        threads_seen += len(thread_page.threads)

        all_old = all(t.latest_message_at < cutoff for t in thread_page.threads)
        if all_old:
            log.debug("All threads on page %d older than cutoff — stopping pagination", page)
            break

        for thread in thread_page.threads:
            if thread.latest_message_at >= cutoff and thread.reservation_id not in seen_ids:
                reservation_ids.append(thread.reservation_id)
                seen_ids.add(thread.reservation_id)

        if not thread_page.has_more:
            break
        page += 1

    log.info(
        "Thread scan: %d thread(s) seen, %d unique reservation(s) within cutoff",
        threads_seen, len(reservation_ids),
    )

    results: list[DiscoveredMessage] = []
    for reservation_id in reservation_ids:
        try:
            info = _get_reservation(reservation_id, smoobu, cache)
            if info is None:
                log.warning("res=%d: could not fetch metadata — skipping", reservation_id)
                continue

            messages = smoobu.get_messages(reservation_id)
        except Exception as exc:
            log.error("Failed to fetch data for reservation %d: %s", reservation_id, exc)
            continue

        guest_messages = [m for m in messages if m.type == 1 and m.body.strip()]
        if not guest_messages:
            continue

        latest = guest_messages[-1]
        previous = [m.body for m in guest_messages[:-1]]

        context = ConversationContext(
            reservation_id=reservation_id,
            guest_name=info.guest_name,
            property_name=info.apartment_name,
            arrival_date=info.arrival,
            departure_date=info.departure,
            default_checkin_time="17:00",
            default_checkout_time="11:00",
            previous_messages=previous,
        )

        results.append(DiscoveredMessage(
            reservation_id=reservation_id,
            message=latest,
            context=context,
        ))

    return results
