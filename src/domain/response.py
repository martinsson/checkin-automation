"""
ResponseParser and ReplyComposer ports.

ResponseParser: AI reads the cleaner's raw reply → structured data.
ReplyComposer:  AI formulates that structured data → a nice guest message.

Code (the pipeline) decides what to do between those two AI steps.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from src.communication.ports import CleanerQuery


@dataclass
class ParsedResponse:
    """Structured interpretation of a cleaner's free-text reply."""
    answer: Literal["yes", "no", "conditional", "unclear"]
    conditions: str | None      # e.g. "only if they arrive before 13:00"
    proposed_time: str | None   # e.g. "13:00" if the cleaner suggests a time
    confidence: float           # 0.0–1.0


@dataclass
class ComposedReply:
    """A ready-to-send message to the guest."""
    body: str
    confidence: float           # 0.0–1.0


class ResponseParser(ABC):
    """
    Port: parse the cleaner's raw text into structured data.
    """

    @abstractmethod
    async def parse(
        self, raw_text: str, original_request: CleanerQuery
    ) -> ParsedResponse:
        ...


class ReplyComposer(ABC):
    """
    Port: compose a polite guest reply from a parsed cleaner response.
    """

    @abstractmethod
    async def compose(
        self, parsed: ParsedResponse, original_request: CleanerQuery
    ) -> ComposedReply:
        ...
