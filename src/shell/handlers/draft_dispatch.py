"""
Draft dispatch handler — imperative shell for sending reviewed drafts.

Fetches reviewed drafts, calls domain plan_dispatch() for routing,
then executes the send action.
"""

import logging

from src.domain.draft_dispatch import SendToCleaner, SendToGuest, SkipSilently, plan_dispatch
from src.ports.cleaner import CleanerNotifier
from src.ports.memory import RequestMemory
from src.ports.smoobu import SmoobuGateway

log = logging.getLogger(__name__)


async def run(
    *,
    memory: RequestMemory,
    smoobu: SmoobuGateway,
    cleaner: CleanerNotifier,
    cleaner_name: str = "Marie",
) -> None:
    """Send all reviewed-but-unsent drafts via the appropriate channel."""
    drafts = await memory.get_reviewed_unsent_drafts()
    for draft in drafts:
        try:
            request = await memory.get_request(draft.request_id)
            action = plan_dispatch(draft, request, cleaner_name)

            if isinstance(action, SendToGuest):
                smoobu.send_message(action.reservation_id, "", action.body)
            elif isinstance(action, SendToCleaner):
                await cleaner.send_query(action.query)
            elif isinstance(action, SkipSilently):
                log.info("draft=%d: %s", draft.draft_id, action.reason)

            await memory.mark_draft_sent(draft.draft_id)
            log.info("draft=%d: dispatched via %s for res=%d", draft.draft_id, draft.step, draft.reservation_id)
        except Exception as exc:
            log.error(
                "draft=%d res=%d: dispatch failed: %s",
                draft.draft_id, draft.reservation_id, exc,
            )
