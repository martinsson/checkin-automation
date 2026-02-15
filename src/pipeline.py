"""
Main processing pipeline.

Wires together all ports following the plan principle:
  AI → data → code → AI

Flow:
  1. AI: classify guest intent → ClassificationResult
  2. Code: check memory, decide whether to proceed
  3. Code: ask cleaner (CleanerNotifier)
  4. AI: parse cleaner response → ParsedResponse
  5. Code: decide auto-reply vs escalate to owner
  6. AI: compose guest reply → ComposedReply
  7. Code: send via Smoobu or notify owner
"""

from dataclasses import dataclass
from typing import Literal

from src.adapters.ports import SmoobuGateway
from src.communication.ports import CleanerNotifier, CleanerQuery, CleanerResponse
from src.domain.intent import ConversationContext, IntentClassifier
from src.domain.memory import RequestMemory
from src.domain.response import ReplyComposer, ResponseParser

import uuid


# Threshold below which we escalate to the owner instead of acting.
CONFIDENCE_THRESHOLD = 0.6


@dataclass
class PipelineConfig:
    smoobu: SmoobuGateway
    cleaner: CleanerNotifier
    classifier: IntentClassifier
    parser: ResponseParser
    composer: ReplyComposer
    memory: RequestMemory
    owner_contact: str = "owner"     # placeholder for owner notification


@dataclass
class PipelineResult:
    action: Literal[
        "ignored",           # intent == "other"
        "already_processed", # memory says we handled this before
        "followup_sent",     # asked guest a clarifying question
        "cleaner_queried",   # sent query to cleaner, waiting for reply
        "replied_to_guest",  # auto-replied to guest
        "escalated_to_owner",# sent suggested response to owner
    ]
    details: str = ""


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
        """Step 1–3: classify, check memory, query cleaner."""

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

        # If AI needs more info, ask the guest a follow-up question
        if result.needs_followup and result.followup_question:
            self._cfg.smoobu.send_message(
                reservation_id,
                subject="",
                body=result.followup_question,
            )
            return PipelineResult(action="followup_sent", details=result.followup_question)

        # Step 3: forward to cleaner
        request_id = str(uuid.uuid4())
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
        await self._cfg.cleaner.send_query(query)

        await self._cfg.memory.mark_processed(
            reservation_id, result.intent, "pending_cleaner", request_id
        )

        return PipelineResult(action="cleaner_queried", details=f"request_id={request_id}")

    async def process_cleaner_responses(self) -> list[PipelineResult]:
        """Steps 4–7: parse cleaner responses and act on them."""
        responses = await self._cfg.cleaner.poll_responses()
        results = []
        for response in responses:
            r = await self._handle_cleaner_response(response)
            results.append(r)
        return results

    async def _handle_cleaner_response(
        self, response: CleanerResponse
    ) -> PipelineResult:
        # We need the original query to compose the reply.
        # For now, store it on the response (the cleaner notifier embeds it).
        # In a full implementation, we'd look it up from persistent storage.
        # For the simulator we use a stub query derived from the response.
        stub_query = CleanerQuery(
            request_id=response.request_id,
            cleaner_name="Marie",
            guest_name="Guest",
            property_name="Le Matisse",
            request_type="early_checkin",
            original_time="15:00",
            requested_time="12:00",
            date="2026-01-01",
            message="(original message not stored yet)",
        )

        # Step 4: AI parses cleaner's reply
        parsed = await self._cfg.parser.parse(response.raw_text, stub_query)

        # Step 5: decide — auto-reply or escalate?
        if parsed.confidence < CONFIDENCE_THRESHOLD or parsed.answer == "unclear":
            # Escalate to owner with a suggested response draft
            draft = await self._cfg.composer.compose(parsed, stub_query)
            owner_msg = (
                f"[Suggested response for {stub_query.property_name} "
                f"/ booking {stub_query.request_id}]\n\n"
                f"{draft.body}\n\n"
                f"(confidence: {parsed.confidence:.0%} — please review before sending)"
            )
            # TODO: send via owner notification port; for now log to console
            print(f"\nEscalated to owner:\n{owner_msg}\n")
            return PipelineResult(action="escalated_to_owner", details=owner_msg[:80])

        # Step 6: AI composes guest reply
        reply = await self._cfg.composer.compose(parsed, stub_query)

        # Step 7: send to guest via Smoobu
        # NOTE: we'd need the reservation_id — in the full implementation
        # this comes from persistent storage keyed by request_id.
        # For now we log the reply (the pipeline test verifies the calls).
        print(f"\nAuto-reply to guest:\n{reply.body}\n")
        return PipelineResult(action="replied_to_guest", details=reply.body[:80])
