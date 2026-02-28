"""
Cleaner response handler — imperative shell for processing cleaner replies.

Orchestrates I/O (memory, AI) and delegates decisions to domain functions.
"""

import logging
from dataclasses import dataclass
from typing import Literal

from src.domain.cleaner_response import plan_reply, rebuild_query_context
from src.ports.cleaner import CleanerResponse
from src.ports.memory import RequestMemory
from src.ports.response import ReplyComposer, ResponseParser

log = logging.getLogger(__name__)


@dataclass
class HandleResult:
    action: Literal["reply_drafted"]
    details: str = ""
    request_id: str = ""


async def handle(
    response: CleanerResponse,
    *,
    memory: RequestMemory,
    parser: ResponseParser,
    composer: ReplyComposer,
    cleaner_name: str = "Marie",
) -> HandleResult:
    """
    Process a single cleaner response.

    Shell: looks up context from memory, calls AI to parse/compose,
    delegates planning to domain, executes the plan.
    """
    # Look up original request
    request = await memory.get_request(response.request_id)

    # Rebuild query context (pure)
    if request:
        query = rebuild_query_context(request, cleaner_name)
    else:
        # Fallback — shouldn't happen but handle gracefully
        from src.ports.cleaner import CleanerQuery
        query = CleanerQuery(
            request_id=response.request_id,
            cleaner_name=cleaner_name,
            guest_name="", property_name="",
            request_type="early_checkin",
            original_time="", requested_time="",
            date="", message="(unknown)",
        )

    # AI: parse cleaner's reply
    parsed = await parser.parse(response.raw_text, query)
    log.info("cleaner response req=%s parsed → %s", response.request_id, parsed.answer)

    # AI: compose guest reply
    reply = await composer.compose(parsed, query)

    # Domain: plan what to save
    if request:
        plan = plan_reply(reply.body, request)
        reply_draft_id = await memory.save_draft(
            plan.request_id, plan.reservation_id, plan.intent,
            plan.draft_step, plan.draft_body,
        )
        await memory.update_status(plan.request_id, plan.new_status)
    else:
        reply_draft_id = await memory.save_draft(
            response.request_id, 0, "early_checkin",
            "guest_reply", reply.body,
        )

    log.info("cleaner response req=%s guest reply draft=%d", response.request_id, reply_draft_id)
    return HandleResult(
        action="reply_drafted",
        details=reply.body[:80],
        request_id=response.request_id,
    )
