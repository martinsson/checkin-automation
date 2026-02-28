"""
Guest request handler — imperative shell for processing a guest message.

Orchestrates I/O (memory, AI) and delegates decisions to domain functions.
"""

import logging
from dataclasses import dataclass
from typing import Literal

from src.domain.guest_request import (
    Actionable,
    Followup,
    Skip,
    build_cleaner_query,
    enrich_with_context,
    plan_drafts,
    triage,
)
from src.ports.intent import ConversationContext, IntentClassifier
from src.ports.memory import RequestMemory
from src.ports.response import GuestAcknowledger

log = logging.getLogger(__name__)


@dataclass
class HandleResult:
    action: Literal[
        "ignored",
        "already_processed",
        "followup_drafted",
        "drafts_created",
    ]
    details: str = ""
    request_id: str = ""


async def handle(
    reservation_id: int,
    message: str,
    context: ConversationContext,
    message_id: int,
    *,
    memory: RequestMemory,
    classifier: IntentClassifier,
    acknowledger: GuestAcknowledger,
    cleaner_name: str = "Marie",
) -> HandleResult:
    """
    Process a single guest message.

    Shell: fetches data from ports, calls domain triage(),
    then executes the plan.
    """
    log.debug("res=%d msg_id=%d message=%.60r", reservation_id, message_id, message)

    # Fetch dedup state from memory
    is_seen = False
    if message_id:
        is_seen = await memory.has_message_been_seen(message_id)

    # If not seen, classify (AI call)
    classification = None
    if not (message_id and is_seen):
        classification = await classifier.classify(message, context)

        # Mark seen after classification
        if message_id:
            await memory.mark_message_seen(message_id, reservation_id)

        log.info(
            "res=%d msg_id=%d classified → intent=%s conf=%.2f time=%s",
            reservation_id, message_id, classification.intent, classification.confidence,
            classification.extracted_time or "?",
        )

    # Check request-level dedup
    is_processed = False
    if classification and classification.intent != "other":
        is_processed = await memory.has_been_processed(reservation_id, classification.intent)

    # Domain decision: triage
    result = triage(message_id, is_seen, classification, is_processed)

    if isinstance(result, Skip):
        log.info("res=%d msg_id=%d skip: %s", reservation_id, message_id, result.reason)
        action = "already_processed" if "already" in result.reason else "ignored"
        return HandleResult(action=action, details=result.reason)

    # Enrich with context
    enrich_with_context(result, context)

    if isinstance(result, Followup):
        # Save request + followup draft
        await memory.save_request(
            reservation_id, result.intent, result.request_id, message,
            guest_name=context.guest_name, property_name=context.property_name,
            original_time=result.original_time, requested_time=result.requested_time,
            relevant_date=result.relevant_date,
        )
        followup_draft_id = await memory.save_draft(
            result.request_id, reservation_id, result.intent,
            "followup", result.question,
        )
        log.info("res=%d intent=%s followup draft=%d", reservation_id, result.intent, followup_draft_id)
        return HandleResult(action="followup_drafted", details=result.question, request_id=result.request_id)

    # Actionable: compose ack (AI), build cleaner query, plan drafts
    assert isinstance(result, Actionable)

    ack = await acknowledger.compose_acknowledgment(classification, context)  # type: ignore[arg-type]

    cleaner_query = build_cleaner_query(result, context, cleaner_name, message)
    plan = plan_drafts(result, reservation_id, message, context, ack.body, cleaner_query.message)

    # Execute plan: save request, save drafts, update status
    await memory.save_request(
        plan.save_request.reservation_id, plan.save_request.intent,
        plan.save_request.request_id, plan.save_request.guest_message,
        guest_name=plan.save_request.guest_name, property_name=plan.save_request.property_name,
        original_time=plan.save_request.original_time, requested_time=plan.save_request.requested_time,
        relevant_date=plan.save_request.relevant_date,
    )

    for draft_cmd in plan.drafts:
        await memory.save_draft(
            plan.save_request.request_id, reservation_id, plan.save_request.intent,
            draft_cmd.step, draft_cmd.body,
        )

    await memory.update_status(plan.status_update.request_id, plan.status_update.status)

    log.info("res=%d intent=%s drafts created", reservation_id, result.intent)
    return HandleResult(
        action="drafts_created",
        details="acknowledgment + cleaner_query drafted",
        request_id=result.request_id,
    )
