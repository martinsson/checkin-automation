"""
ClaudeIntentClassifier — uses Claude API to classify guest messages.

System prompt is the source of truth for classification rules.
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

_SYSTEM_PROMPT = """
You are an assistant that classifies Airbnb guest messages for a property manager.

You must classify whether the guest is asking for:
- "early_checkin": arriving before the standard check-in time
- "late_checkout": leaving after the standard check-out time
- "other": anything else (ignore these)

Rules:
- The default check-in time and check-out time are provided in the context.
- A request is only early_checkin or late_checkout if the guest is specifically
  asking to deviate from those default times.
- If the message is about something else entirely (WiFi, parking, directions, etc.)
  classify as "other".
- If the message is ambiguous (e.g. "can I access the apartment earlier?" with no
  time mentioned), still classify correctly but set needs_followup=true and provide
  a followup_question in the guest's language.
- Extract the requested time if the guest mentions one (e.g. "13h", "1pm", "midi").

Respond ONLY with valid JSON matching this schema:
{
  "intent": "early_checkin" | "late_checkout" | "other",
  "confidence": <float 0.0–1.0>,
  "extracted_time": "<HH:MM>" | null,
  "needs_followup": <boolean>,
  "followup_question": "<question in the guest's language>" | null
}
""".strip()


class ClaudeIntentClassifier(IntentClassifier):
    """Intent classifier backed by Claude claude-haiku-4-5-20251001 (fast + cheap)."""

    def __init__(self, api_key: str | None = None, model: str = "claude-haiku-4-5-20251001"):
        self._client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self._model = model

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
            system=_SYSTEM_PROMPT,
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
