"""
Core polling logic for the checking-automation daemon.

Extracted from scripts/run.py so it can be imported and tested
without pulling in Claude or email adapter dependencies.
"""

import logging
from datetime import datetime, timedelta, timezone

from src.adapters.ports import ReservationInfo, SmoobuGateway
from src.domain.intent import ConversationContext
from src.domain.reservation_cache import ReservationCache
from src.pipeline import Pipeline

log = logging.getLogger(__name__)


async def poll_once(
    pipeline: Pipeline,
    smoobu: SmoobuGateway,
    reservation_cache: ReservationCache,
    threads_cutoff_days: int = 7,
) -> None:
    """
    One poll cycle using threads as the activity index.

    1. Paginate GET /api/threads until all threads on a page are older than cutoff.
    2. For each unique reservation ID seen, fetch reservation metadata (cached).
    3. Fetch messages, filter type==1 (guest), process latest via pipeline.
    4. Poll for cleaner responses.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=threads_cutoff_days)

    # Collect unique reservation IDs from threads within the cutoff window
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

        # Stop paginating if all threads on this page are older than cutoff
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

    for reservation_id in reservation_ids:
        try:
            info = _get_reservation(reservation_id, smoobu, reservation_cache)
            if info is None:
                log.warning("res=%d: could not fetch metadata — skipping", reservation_id)
                continue

            messages = smoobu.get_messages(reservation_id)
        except Exception as exc:
            log.error("Failed to fetch data for reservation %d: %s", reservation_id, exc)
            continue

        # Filter to guest messages only (type=1)
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

        try:
            result = await pipeline.process_message(
                reservation_id=reservation_id,
                message=latest.body,
                context=context,
                message_id=latest.message_id,
            )
            if result.action not in ("ignored", "already_processed"):
                log.debug(
                    "res=%d action=%s: %s",
                    reservation_id,
                    result.action,
                    result.details[:60],
                )
        except Exception as exc:
            log.error("Pipeline error for reservation %d: %s", reservation_id, exc)

    # Poll for cleaner responses
    try:
        cleaner_results = await pipeline.process_cleaner_responses()
        for r in cleaner_results:
            log.info("Cleaner response processed → %s: %s", r.action, r.details[:60])
    except Exception as exc:
        log.error("Failed to process cleaner responses: %s", exc)


def _get_reservation(
    reservation_id: int,
    smoobu: SmoobuGateway,
    cache: ReservationCache,
) -> ReservationInfo | None:
    """Return reservation info from cache, fetching from gateway on cache miss."""
    info = cache.get(reservation_id)
    if info is not None:
        return info
    info = smoobu.get_reservation(reservation_id)
    if info is not None:
        cache.store(reservation_id, info)
    return info
