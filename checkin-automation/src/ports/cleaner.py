from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CleanerQuery:
    """What we send to the cleaner."""

    request_id: str
    cleaner_name: str
    guest_name: str
    property_name: str
    request_type: str  # "early_checkin" or "late_checkout"
    original_time: str  # "15:00"
    requested_time: str  # "12:00"
    date: str  # "2026-02-20"
    message: str  # Human-readable question


@dataclass
class CleanerResponse:
    """What we get back from the cleaner."""

    request_id: str
    raw_text: str
    received_at: datetime


class CleanerNotifier(ABC):
    """
    Port: how we communicate with cleaning staff.

    The business logic depends ONLY on this interface.
    It doesn't know or care whether messages go via email,
    WhatsApp, Telegram, or carrier pigeon.
    """

    @abstractmethod
    async def send_query(self, query: CleanerQuery) -> str:
        """
        Send a question to the cleaner.
        Returns a tracking ID (email Message-ID, chat message ID, etc.)
        """
        ...

    @abstractmethod
    async def poll_responses(self) -> list[CleanerResponse]:
        """
        Check for new responses from cleaners.
        Returns all unprocessed responses since last poll.
        """
        ...
