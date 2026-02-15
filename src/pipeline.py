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

from dataclasses import dataclass
from typing import Literal

from src.communication.ports import CleanerNotifier, CleanerQuery, CleanerResponse
from src.domain.intent import ConversationContext, IntentClassifier
from src.domain.memory import RequestMemory
from src.domain.response import GuestAcknowledger, ReplyComposer, ResponseParser

import uuid


@dataclass
class PipelineConfig:
    cleaner: CleanerNotifier
    classifier: IntentClassifier
    acknowledger: GuestAcknowledger
    parser: ResponseParser
    composer: ReplyComposer
    memory: RequestMemory


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
    ) -> PipelineResult:
        """Classify intent, generate drafts for owner review."""

        # Step 1: AI classifies intent
        result = await self._cfg.classifier.classify(message, context)

        if result.intent == "other":
            return PipelineResult(action="ignored", details=f"confidence={result.confidence:.2f}")

        # Step 2: check memory — don't process the same request twice
        if await self._cfg.memory.has_been_processed(reservation_id, result.intent):
            return PipelineResult(
                action="already_processed",
                details=f"intent={result.intent}",
            )

        request_id = str(uuid.uuid4())

        # Save the request in memory
        await self._cfg.memory.save_request(
            reservation_id, result.intent, request_id, message,
        )

        # If AI needs more info, draft a follow-up question
        if result.needs_followup and result.followup_question:
            await self._cfg.memory.save_draft(
                request_id, reservation_id, result.intent,
                "followup", result.followup_question,
            )
            return PipelineResult(
                action="followup_drafted",
                details=result.followup_question,
                request_id=request_id,
            )

        # Step 3: AI composes acknowledgment → saved as draft
        ack = await self._cfg.acknowledger.compose_acknowledgment(result, context)
        await self._cfg.memory.save_draft(
            request_id, reservation_id, result.intent,
            "acknowledgment", ack.body,
        )

        # Step 4: prepare cleaner query → saved as draft
        query = CleanerQuery(
            request_id=request_id,
            cleaner_name="Marie",               # TODO: look up from config
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
        await self._cfg.memory.save_draft(
            request_id, reservation_id, result.intent,
            "cleaner_query", query.message,
        )

        await self._cfg.memory.update_status(request_id, "pending_acknowledgment")

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

        # Build the query context for the AI to compose a reply
        stub_query = CleanerQuery(
            request_id=response.request_id,
            cleaner_name="Marie",
            guest_name="Guest",
            property_name="Le Matisse",
            request_type=req.intent if req else "early_checkin",
            original_time="15:00",
            requested_time="12:00",
            date="2026-01-01",
            message=req.guest_message if req else "(unknown)",
        )

        # AI parses cleaner's reply
        parsed = await self._cfg.parser.parse(response.raw_text, stub_query)

        # AI composes guest reply
        reply = await self._cfg.composer.compose(parsed, stub_query)

        # Save as draft for owner review
        reservation_id = req.reservation_id if req else 0
        intent = req.intent if req else "early_checkin"
        await self._cfg.memory.save_draft(
            response.request_id, reservation_id, intent,
            "guest_reply", reply.body,
        )

        if req:
            await self._cfg.memory.update_status(response.request_id, "pending_reply")

        return PipelineResult(
            action="reply_drafted",
            details=reply.body[:80],
            request_id=response.request_id,
        )
