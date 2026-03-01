"""
Draft dispatch handler — imperative shell for sending reviewed drafts.

Fetches reviewed drafts, calls domain plan_dispatch() for routing,
then executes the send action.
"""

import logging
from collections import defaultdict

from src.domain.draft_dispatch import SendToCleaner, SendToGuest, SkipSilently, plan_dispatch
from src.ports.cleaner import CleanerNotifier
from src.ports.memory import RequestMemory, RequestStatus
from src.ports.smoobu import SmoobuGateway

log = logging.getLogger(__name__)

_INITIAL_STEPS = {"acknowledgment", "cleaner_query"}


async def run(
    *,
    memory: RequestMemory,
    smoobu: SmoobuGateway,
    cleaner: CleanerNotifier,
    cleaner_name: str = "Marie",
) -> None:
    """Send all reviewed-but-unsent drafts via the appropriate channel."""
    drafts = await memory.get_reviewed_unsent_drafts()
    # Track which requests had drafts dispatched this cycle
    dispatched_steps: dict[str, set[str]] = defaultdict(set)

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
            dispatched_steps[draft.request_id].add(draft.step)
            log.info("draft=%d: dispatched via %s for res=%d", draft.draft_id, draft.step, draft.reservation_id)
        except Exception as exc:
            log.error(
                "draft=%d res=%d: dispatch failed: %s",
                draft.draft_id, draft.reservation_id, exc,
            )

    # Advance request statuses based on what was dispatched
    for request_id, steps in dispatched_steps.items():
        request = await memory.get_request(request_id)
        if request is None:
            continue

        if "guest_reply" in steps and request.status == RequestStatus.pending_reply:
            await memory.update_status(request_id, RequestStatus.done)
            log.info("request=%s → done", request_id)
        elif steps & _INITIAL_STEPS and request.status == RequestStatus.pending_ack:
            # Check if ALL initial drafts are now sent
            all_drafts = await memory.get_drafts_for_request(request_id)
            initial_drafts = [d for d in all_drafts if d.step in _INITIAL_STEPS]
            if all(d.sent_at is not None for d in initial_drafts):
                await memory.update_status(request_id, RequestStatus.pending_cleaner)
                log.info("request=%s → pending_cleaner", request_id)
