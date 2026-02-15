"""
Claude-powered adapters for ResponseParser and ReplyComposer.
"""

import json
import os

import anthropic

from src.communication.ports import CleanerQuery
from src.domain.response import (
    ComposedReply,
    ParsedResponse,
    ReplyComposer,
    ResponseParser,
)

_PARSER_SYSTEM = """
You are an assistant that parses replies from Airbnb cleaning staff.

Given the cleaner's raw reply and the original request context, extract:
- answer: "yes", "no", "conditional", or "unclear"
  * "yes": cleaner clearly agrees
  * "no": cleaner clearly refuses
  * "conditional": cleaner agrees but with conditions or a different time
  * "unclear": cannot determine from the text
- conditions: any conditions the cleaner mentioned (or null)
- proposed_time: if the cleaner suggests a specific time (HH:MM format, or null)
- confidence: your confidence in the parsing (0.0–1.0)

Respond ONLY with valid JSON matching this schema:
{
  "answer": "yes" | "no" | "conditional" | "unclear",
  "conditions": "<string>" | null,
  "proposed_time": "<HH:MM>" | null,
  "confidence": <float>
}
""".strip()

_COMPOSER_SYSTEM = """
You are an assistant that composes polite Airbnb host replies to guests.

You are given structured information about a cleaner's decision and the
original guest request. Write a warm, professional reply to the guest
in the same language they used (detect from the guest name and context —
default to French for French-speaking guests).

Rules:
- Be warm and concise (2–4 sentences)
- Do NOT mention the cleaner or internal operations
- If approved: confirm the new time clearly
- If declined: apologise briefly and give the standard time
- If conditional: explain the condition clearly

Respond ONLY with valid JSON:
{
  "body": "<the message to send to the guest>",
  "confidence": <float 0.0–1.0>
}
""".strip()


class ClaudeResponseParser(ResponseParser):

    def __init__(self, api_key: str | None = None, model: str = "claude-haiku-4-5-20251001"):
        self._client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self._model = model

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
            system=_PARSER_SYSTEM,
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
            system=_COMPOSER_SYSTEM,
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
