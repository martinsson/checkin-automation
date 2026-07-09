"""
Cleaner response poller — discovers new responses from the cleaner.

Infrastructure concern: compensates for the lack of webhooks.
Wraps CleanerNotifier.poll_responses() in the symmetric poller pattern.
"""

import logging

from src.ports.cleaner import CleanerNotifier, CleanerResponse

log = logging.getLogger(__name__)


async def poll(notifier: CleanerNotifier) -> list[CleanerResponse]:
    """Poll for new cleaner responses and return them for handling."""
    responses = await notifier.poll_responses()
    if responses:
        log.info("Cleaner poller: %d new response(s)", len(responses))
    return responses
