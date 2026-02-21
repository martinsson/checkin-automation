"""
Main processing pipeline.

Wires together all ports following the plan principle:
  AI → data → code → AI

Nothing is sent directly — every outgoing message is saved as a draft
in the RequestMemory for the owner to review, approve, or reject.

Flow:
  1. AI: classify guest intent → ClassificationResult
  2. Code: check memory, decide whether to proceed
  3. AI: compose acknowledgment + cleaner query → saved as drafts
  --- owner reviews and sends manually ---
  4. AI: parse cleaner response → ParsedResponse
  5. AI: compose guest reply → saved as draft
  --- owner reviews and sends manually ---
"""

import logging
from dataclasses import dataclass
from typing import Literal

from src.communication.ports import CleanerNotifier, CleanerQuery, CleanerResponse
from src.domain.intent import ConversationContext, IntentClassifier
from src.domain.memory import RequestMemory
from src.domain.response import GuestAcknowledger, ReplyComposer, ResponseParser

import uuid

log = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    cleaner: CleanerNotifier
    classifier: IntentClassifier
    acknowledger: GuestAcknowledger
    parser: ResponseParser
    composer: ReplyComposer
    memory: RequestMemory
    cleaner_name: str = "Marie"


@dataclass
class PipelineResult:
    action: Literal[
        "ignored",           # intent == "other"
        "already_processed", # memory says we handled this before
        "followup_drafted",  # follow-up question saved as draft
        "drafts_created",    # acknowledgment + cleaner query saved as drafts
        "reply_drafted",     # guest reply saved as draft after cleaner response
    ]
    details: str = ""
    request_id: str = ""


class Pipeline:
    """
    Stateless pipeline step: process one guest message.

    Call process_message() when a new guest message arrives.
    Call process_cleaner_responses() on a schedule to handle replies.
    """

    def __init__(self, config: PipelineConfig):
        self._cfg = config

    async def process_message(
        self,
        reservation_id: int,
        message: str,
        context: ConversationContext,
        message_id: int = 0,
    ) -> PipelineResult:
        """Classify intent, generate drafts for owner review."""

        log.debug("res=%d msg_id=%d message=%.60r", reservation_id, message_id, message)

        # Guard: skip AI call if this exact message was already classified
        if message_id and await self._cfg.memory.has_message_been_seen(message_id):
            log.info("res=%d msg_id=%d skip: message already seen", reservation_id, message_id)
            return PipelineResult(action="already_processed", details="message already seen")

        # Step 1: AI classifies intent
        result = await self._cfg.classifier.classify(message, context)

        # Mark seen now so re-runs of the same message_id are skipped
        if message_id:
            await self._cfg.memory.mark_message_seen(message_id, reservation_id)

        log.info(
            "res=%d msg_id=%d classified → intent=%s conf=%.2f time=%s",
            reservation_id, message_id, result.intent, result.confidence,
            result.extracted_time or "?",
        )

        if result.intent == "other":
            return PipelineResult(action="ignored", details=f"confidence={result.confidence:.2f}")

        # Step 2: check memory — don't process the same request twice
        if await self._cfg.memory.has_been_processed(reservation_id, result.intent):
            log.info("res=%d intent=%s skip: already processed", reservation_id, result.intent)
            return PipelineResult(
                action="already_processed",
                details=f"intent={result.intent}",
            )

        request_id = str(uuid.uuid4())

        original_time = (
            context.default_checkin_time
            if result.intent == "early_checkin"
            else context.default_checkout_time
        )
        relevant_date = (
            context.arrival_date
            if result.intent == "early_checkin"
            else context.departure_date
        )

        # Save the request in memory
        await self._cfg.memory.save_request(
            reservation_id, result.intent, request_id, message,
            guest_name=context.guest_name,
            property_name=context.property_name,
            original_time=original_time,
            requested_time=result.extracted_time or "?",
            relevant_date=relevant_date,
        )

        # If AI needs more info, draft a follow-up question
        if result.needs_followup and result.followup_question:
            followup_draft_id = await self._cfg.memory.save_draft(
                request_id, reservation_id, result.intent,
                "followup", result.followup_question,
            )
            log.info(
                "res=%d intent=%s followup draft=%d: %.60s",
                reservation_id, result.intent, followup_draft_id, result.followup_question,
            )
            return PipelineResult(
                action="followup_drafted",
                details=result.followup_question,
                request_id=request_id,
            )

        # Step 3: AI composes acknowledgment → saved as draft
        ack = await self._cfg.acknowledger.compose_acknowledgment(result, context)
        ack_draft_id = await self._cfg.memory.save_draft(
            request_id, reservation_id, result.intent,
            "acknowledgment", ack.body,
        )

        # Step 4: prepare cleaner query → saved as draft
        query = CleanerQuery(
            request_id=request_id,
            cleaner_name=self._cfg.cleaner_name,
            guest_name=context.guest_name,
            property_name=context.property_name,
            request_type=result.intent,
            original_time=(
                context.default_checkin_time
                if result.intent == "early_checkin"
                else context.default_checkout_time
            ),
            requested_time=result.extracted_time or "?",
            date=(
                context.arrival_date
                if result.intent == "early_checkin"
                else context.departure_date
            ),
            message=message,
        )
        query_draft_id = await self._cfg.memory.save_draft(
            request_id, reservation_id, result.intent,
            "cleaner_query", query.message,
        )

        await self._cfg.memory.update_status(request_id, "pending_acknowledgment")

        log.info(
            "res=%d intent=%s drafts created: ack=%d cleaner_query=%d",
            reservation_id, result.intent, ack_draft_id, query_draft_id,
        )
        return PipelineResult(
            action="drafts_created",
            details=f"acknowledgment + cleaner_query drafted",
            request_id=request_id,
        )

    async def process_cleaner_responses(self) -> list[PipelineResult]:
        """Parse cleaner responses and save guest reply drafts."""
        responses = await self._cfg.cleaner.poll_responses()
        results = []
        for response in responses:
            r = await self._handle_cleaner_response(response)
            results.append(r)
        return results

    async def _handle_cleaner_response(
        self, response: CleanerResponse
    ) -> PipelineResult:
        # Look up the original request from memory
        req = await self._cfg.memory.get_request(response.request_id)

        # Reconstruct the CleanerQuery from the stored request
        stub_query = CleanerQuery(
            request_id=response.request_id,
            cleaner_name=self._cfg.cleaner_name,
            guest_name=req.guest_name if req else "",
            property_name=req.property_name if req else "",
            request_type=req.intent if req else "early_checkin",
            original_time=req.original_time if req else "",
            requested_time=req.requested_time if req else "",
            date=req.relevant_date if req else "",
            message=req.guest_message if req else "(unknown)",
        )

        # AI parses cleaner's reply
        parsed = await self._cfg.parser.parse(response.raw_text, stub_query)

        log.info("cleaner response req=%s parsed → %s", response.request_id, parsed.answer)

        # AI composes guest reply
        reply = await self._cfg.composer.compose(parsed, stub_query)

        # Save as draft for owner review
        reservation_id = req.reservation_id if req else 0
        intent = req.intent if req else "early_checkin"
        reply_draft_id = await self._cfg.memory.save_draft(
            response.request_id, reservation_id, intent,
            "guest_reply", reply.body,
        )

        log.info(
            "cleaner response req=%s guest reply draft=%d: %.60s",
            response.request_id, reply_draft_id, reply.body,
        )

        if req:
            await self._cfg.memory.update_status(response.request_id, "pending_reply")

        return PipelineResult(
            action="reply_drafted",
            details=reply.body[:80],
            request_id=response.request_id,
        )
