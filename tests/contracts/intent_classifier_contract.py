"""
Contract tests for any IntentClassifier implementation.

The contract defines the behavioral guarantees:
- A clear early checkin message is classified as early_checkin
- A clear late checkout message is classified as late_checkout
- An unrelated message is classified as other
- The result always has the required fields
"""

from abc import ABC, abstractmethod

import pytest

from src.domain.intent import ConversationContext, IntentClassifier


def _ctx() -> ConversationContext:
    return ConversationContext(
        reservation_id=42,
        guest_name="Test Guest",
        property_name="Le Matisse",
        default_checkin_time="15:00",
        default_checkout_time="11:00",
        arrival_date="2026-04-01",
        departure_date="2026-04-05",
    )


class IntentClassifierContract(ABC):

    @abstractmethod
    def create_classifier(self) -> IntentClassifier:
        ...

    @pytest.mark.asyncio
    async def test_early_checkin_classified_correctly(self):
        clf = self.create_classifier()
        result = await clf.classify(
            "Bonjour, serait-il possible d'accéder plus tôt à l'appartement ?",
            _ctx(),
        )
        assert result.intent == "early_checkin"
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_late_checkout_classified_correctly(self):
        clf = self.create_classifier()
        result = await clf.classify(
            "Hi, could we check out later, say around 1pm?",
            _ctx(),
        )
        assert result.intent == "late_checkout"
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_unrelated_message_classified_as_other(self):
        clf = self.create_classifier()
        result = await clf.classify(
            "Bonjour, quel est le code Wifi ?",
            _ctx(),
        )
        assert result.intent == "other"

    @pytest.mark.asyncio
    async def test_result_has_required_fields(self):
        clf = self.create_classifier()
        result = await clf.classify("Can I check in early?", _ctx())
        assert result.intent in ("early_checkin", "late_checkout", "other")
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.needs_followup, bool)
        # followup_question must be set when needs_followup is True
        if result.needs_followup:
            assert result.followup_question is not None

    @pytest.mark.asyncio
    async def test_time_extracted_when_mentioned(self):
        clf = self.create_classifier()
        result = await clf.classify(
            "Can I check in earlier, around 12:00?", _ctx()
        )
        assert result.intent == "early_checkin"
        assert result.extracted_time is not None
