"""
Core polling logic for the checking-automation daemon.

Extracted from scripts/run.py so it can be imported and tested
without pulling in Claude or email adapter dependencies.
"""

import logging
from datetime import date, timedelta

from src.adapters.ports import SmoobuGateway
from src.domain.intent import ConversationContext
from src.pipeline import Pipeline

log = logging.getLogger(__name__)


async def poll_once(
    pipeline: Pipeline,
    smoobu: SmoobuGateway,
    apartment_id: int,
    lookahead_days: int,
) -> None:
    today = date.today()
    arrival_from = today.isoformat()
    arrival_to = (today + timedelta(days=lookahead_days)).isoformat()

    log.info("Fetching active reservations %s → %s", arrival_from, arrival_to)
    try:
        reservations = smoobu.get_active_reservations(
            apartment_id=apartment_id,
            arrival_from=arrival_from,
            arrival_to=arrival_to,
        )
    except Exception as exc:
        log.error("Failed to fetch reservations: %s", exc)
        return

    log.info("Found %d reservation(s)", len(reservations))

    for res in reservations:
        try:
            messages = smoobu.get_messages(res.reservation_id)
        except Exception as exc:
            log.error("Failed to fetch messages for reservation %d: %s", res.reservation_id, exc)
            continue

        # Only process the last guest message to avoid re-processing history
        guest_messages = [m for m in messages if m.body.strip()]
        if not guest_messages:
            continue

        latest = guest_messages[-1]
        previous = [m.body for m in guest_messages[:-1]]

        context = ConversationContext(
            reservation_id=res.reservation_id,
            guest_name=res.guest_name,
            property_name=f"Apartment {res.apartment_id}",
            arrival_date=res.arrival,
            departure_date=res.departure,
            default_checkin_time="17:00",
            default_checkout_time="11:00",
            previous_messages=previous,
        )

        try:
            result = await pipeline.process_message(
                reservation_id=res.reservation_id,
                message=latest.body,
                context=context,
            )
            if result.action not in ("ignored", "already_processed"):
                log.info(
                    "Reservation %d → %s: %s",
                    res.reservation_id,
                    result.action,
                    result.details[:60],
                )
        except Exception as exc:
            log.error("Pipeline error for reservation %d: %s", res.reservation_id, exc)

    # Poll for cleaner responses
    try:
        cleaner_results = await pipeline.process_cleaner_responses()
        for r in cleaner_results:
            log.info("Cleaner response processed → %s: %s", r.action, r.details[:60])
    except Exception as exc:
        log.error("Failed to process cleaner responses: %s", exc)
