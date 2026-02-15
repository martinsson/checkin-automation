"""
ClaudeIntentClassifier — uses Claude API to classify guest messages.

System prompt is loaded from src/prompts/intent_classifier.txt.
The prompt returns JSON that maps directly to ClassificationResult.
"""

import json
import os

import anthropic

from src.domain.intent import (
    ClassificationResult,
    ConversationContext,
    IntentClassifier,
)
from src.prompts import load_prompt


class ClaudeIntentClassifier(IntentClassifier):
    """Intent classifier backed by Claude claude-haiku-4-5-20251001 (fast + cheap)."""

    def __init__(self, api_key: str | None = None, model: str = "claude-haiku-4-5-20251001"):
        self._client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self._model = model
        self._system_prompt = load_prompt("intent_classifier")

    async def classify(
        self, message: str, context: ConversationContext
    ) -> ClassificationResult:
        user_content = (
            f"Property: {context.property_name}\n"
            f"Guest: {context.guest_name}\n"
            f"Arrival: {context.arrival_date}  Departure: {context.departure_date}\n"
            f"Default check-in: {context.default_checkin_time}  "
            f"Default check-out: {context.default_checkout_time}\n"
        )
        if context.previous_messages:
            user_content += "\nPrevious messages (for context):\n"
            for m in context.previous_messages[-3:]:
                user_content += f"  - {m}\n"
        user_content += f"\nLatest guest message:\n{message}"

        response = self._client.messages.create(
            model=self._model,
            max_tokens=256,
            system=self._system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )

        raw = response.content[0].text.strip()
        # Strip markdown code fences if the model wraps the JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)

        return ClassificationResult(
            intent=data["intent"],
            confidence=float(data.get("confidence", 0.5)),
            extracted_time=data.get("extracted_time"),
            needs_followup=bool(data.get("needs_followup", False)),
            followup_question=data.get("followup_question"),
        )
