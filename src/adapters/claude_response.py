"""
Claude-powered adapters for GuestAcknowledger, ResponseParser, and ReplyComposer.

Prompts are loaded from src/prompts/*.txt.
"""

import json
import os

import anthropic

from src.communication.ports import CleanerQuery
from src.domain.intent import ClassificationResult, ConversationContext
from src.domain.response import (
    ComposedReply,
    GuestAcknowledger,
    ParsedResponse,
    ReplyComposer,
    ResponseParser,
)
from src.prompts import load_prompt


class ClaudeGuestAcknowledger(GuestAcknowledger):

    def __init__(self, api_key: str | None = None, model: str = "claude-haiku-4-5-20251001"):
        self._client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self._model = model
        self._system_prompt = load_prompt("guest_acknowledgment")

    async def compose_acknowledgment(
        self,
        classification: ClassificationResult,
        context: ConversationContext,
    ) -> ComposedReply:
        user_content = (
            f"Guest name: {context.guest_name}\n"
            f"Property: {context.property_name}\n"
            f"Request type: {classification.intent}\n"
            f"Requested time: {classification.extracted_time or 'not specified'}\n"
            f"Arrival: {context.arrival_date}  Departure: {context.departure_date}\n"
            f"Default check-in: {context.default_checkin_time}  "
            f"Default check-out: {context.default_checkout_time}\n"
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=512,
            system=self._system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)

        return ComposedReply(
            body=data["body"],
            confidence=float(data.get("confidence", 0.5)),
        )


class ClaudeResponseParser(ResponseParser):

    def __init__(self, api_key: str | None = None, model: str = "claude-haiku-4-5-20251001"):
        self._client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self._model = model
        self._system_prompt = load_prompt("response_parser")

    async def parse(self, raw_text: str, original_request: CleanerQuery) -> ParsedResponse:
        user_content = (
            f"Request type: {original_request.request_type}\n"
            f"Property: {original_request.property_name}\n"
            f"Requested time: {original_request.requested_time} "
            f"(standard: {original_request.original_time})\n"
            f"Date: {original_request.date}\n\n"
            f"Cleaner's reply:\n{raw_text}"
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=256,
            system=self._system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)

        return ParsedResponse(
            answer=data["answer"],
            conditions=data.get("conditions"),
            proposed_time=data.get("proposed_time"),
            confidence=float(data.get("confidence", 0.5)),
        )


class ClaudeReplyComposer(ReplyComposer):

    def __init__(self, api_key: str | None = None, model: str = "claude-haiku-4-5-20251001"):
        self._client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self._model = model
        self._system_prompt = load_prompt("reply_composer")

    async def compose(
        self, parsed: ParsedResponse, original_request: CleanerQuery
    ) -> ComposedReply:
        user_content = (
            f"Request type: {original_request.request_type}\n"
            f"Guest name: {original_request.guest_name}\n"
            f"Property: {original_request.property_name}\n"
            f"Date: {original_request.date}\n"
            f"Requested time: {original_request.requested_time} "
            f"(standard: {original_request.original_time})\n\n"
            f"Cleaner's decision:\n"
            f"  answer: {parsed.answer}\n"
            f"  conditions: {parsed.conditions}\n"
            f"  proposed_time: {parsed.proposed_time}\n"
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=512,
            system=self._system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)

        return ComposedReply(
            body=data["body"],
            confidence=float(data.get("confidence", 0.5)),
        )
