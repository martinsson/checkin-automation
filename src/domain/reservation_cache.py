"""
ReservationCache port — stores reservation metadata to avoid repeated API calls.
"""

from abc import ABC, abstractmethod

from src.adapters.ports import ReservationInfo


class ReservationCache(ABC):
    """
    Port: cache reservation metadata keyed by reservation_id.

    The daemon fetches reservation info on first sight and stores it here,
    avoiding repeated GET /reservations/{id} calls on every poll cycle.
    """

    @abstractmethod
    def get(self, reservation_id: int) -> ReservationInfo | None:
        """Return cached info, or None if not stored."""
        ...

    @abstractmethod
    def store(self, reservation_id: int, info: ReservationInfo) -> None:
        """Persist reservation metadata."""
        ...
