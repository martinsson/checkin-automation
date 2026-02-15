"""
RequestMemory port — tracks which requests have already been processed
so the same guest demand is never handled twice.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProcessedRequest:
    reservation_id: int
    intent: str          # "early_checkin" or "late_checkout"
    result: str          # "approved", "declined", "pending_owner", "pending_cleaner"
    processed_at: datetime
    request_id: str      # correlation ID


class RequestMemory(ABC):
    """
    Port: remember which guest requests have been processed.

    A guest can make both an early-checkin AND a late-checkout request —
    those are tracked independently (different intent values).
    If the same guest sends the same intent again, has_been_processed
    returns True and the orchestrator skips it.
    """

    @abstractmethod
    async def has_been_processed(self, reservation_id: int, intent: str) -> bool:
        """True if this intent was already handled for this reservation."""
        ...

    @abstractmethod
    async def mark_processed(
        self,
        reservation_id: int,
        intent: str,
        result: str,
        request_id: str,
    ) -> None:
        """Record that an intent has been processed."""
        ...

    @abstractmethod
    async def get_history(self, reservation_id: int) -> list[ProcessedRequest]:
        """Return all processed requests for a reservation, oldest first."""
        ...
