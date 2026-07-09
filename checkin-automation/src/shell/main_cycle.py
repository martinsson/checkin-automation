"""
Main poll cycle — thin sequencer that composes pollers and handlers.

Replaces the old poll_once() function. The sleep loop lives in scripts/run.py.
"""

import logging

from src.ports.cleaner import CleanerNotifier
from src.ports.intent import IntentClassifier
from src.ports.memory import RequestMemory
from src.ports.reservation_cache import ReservationCache
from src.ports.response import GuestAcknowledger, ReplyComposer, ResponseParser
from src.ports.smoobu import SmoobuGateway

from src.shell.pollers import guest_messages, cleaner_responses
from src.shell.handlers import guest_request, cleaner_response, draft_dispatch

log = logging.getLogger(__name__)


async def poll_cycle(
    *,
    smoobu: SmoobuGateway,
    memory: RequestMemory,
    cache: ReservationCache,
    classifier: IntentClassifier,
    acknowledger: GuestAcknowledger,
    parser: ResponseParser,
    composer: ReplyComposer,
    cleaner: CleanerNotifier,
    cleaner_name: str = "Marie",
    threads_cutoff_days: int = 7,
) -> None:
    """
    One full poll cycle: discover → handle → dispatch.

    1. Poll for new guest messages, handle each one
    2. Poll for new cleaner responses, handle each one
    3. Dispatch reviewed drafts
    """
    # 1. Guest messages
    discovered = guest_messages.poll(smoobu, cache, threads_cutoff_days)
    for item in discovered:
        try:
            result = await guest_request.handle(
                reservation_id=item.reservation_id,
                message=item.message.body,
                context=item.context,
                message_id=item.message.message_id,
                memory=memory,
                classifier=classifier,
                acknowledger=acknowledger,
                cleaner_name=cleaner_name,
            )
            if result.action not in ("ignored", "already_processed"):
                log.debug("res=%d action=%s: %s", item.reservation_id, result.action, result.details[:60])
        except Exception as exc:
            log.error("Handler error for reservation %d: %s", item.reservation_id, exc)

    # 2. Cleaner responses
    try:
        responses = await cleaner_responses.poll(cleaner)
        for response in responses:
            try:
                result = await cleaner_response.handle(
                    response,
                    memory=memory,
                    parser=parser,
                    composer=composer,
                    cleaner_name=cleaner_name,
                )
                log.info("Cleaner response processed → %s: %s", result.action, result.details[:60])
            except Exception as exc:
                log.error("Cleaner response handler error for req=%s: %s", response.request_id, exc)
    except Exception as exc:
        log.error("Failed to poll cleaner responses: %s", exc)

    # 3. Dispatch reviewed drafts
    try:
        await draft_dispatch.run(
            memory=memory,
            smoobu=smoobu,
            cleaner=cleaner,
            cleaner_name=cleaner_name,
        )
    except Exception as exc:
        log.error("Failed to dispatch reviewed drafts: %s", exc)
