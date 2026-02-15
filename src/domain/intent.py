"""
IntentClassifier port — understands what the guest is asking for.

AI is used here: the classifier reads a guest message and returns
structured data.  Business rules then operate on that data.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ConversationContext:
    """Everything the classifier needs to understand a guest message."""
    reservation_id: int
    guest_name: str
    property_name: str
    default_checkin_time: str     # e.g. "15:00"
    default_checkout_time: str    # e.g. "11:00"
    arrival_date: str             # ISO: "2026-03-05"
    departure_date: str           # ISO: "2026-03-07"
    previous_messages: list[str] = field(default_factory=list)


@dataclass
class ClassificationResult:
    """Structured output of intent classification — no raw text, only data."""
    intent: Literal["early_checkin", "late_checkout", "other"]
    confidence: float                # 0.0–1.0
    extracted_time: str | None       # e.g. "12:00" if guest mentioned one
    needs_followup: bool             # True when more info is needed
    followup_question: str | None    # question to send back to guest


class IntentClassifier(ABC):
    """
    Port: classify a guest message into a structured intent.

    Implementations may use an LLM (ClaudeIntentClassifier) or
    deterministic keyword matching (SimulatorIntentClassifier).
    Both must satisfy the same contract.
    """

    @abstractmethod
    async def classify(
        self, message: str, context: ConversationContext
    ) -> ClassificationResult:
        """Classify a single guest message given the reservation context."""
        ...
