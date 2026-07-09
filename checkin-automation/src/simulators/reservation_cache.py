"""
In-memory ReservationCache for testing — no database required.
"""

from src.ports.smoobu import ReservationInfo
from src.ports.reservation_cache import ReservationCache


class InMemoryReservationCache(ReservationCache):

    def __init__(self):
        self._store: dict[int, ReservationInfo] = {}

    def get(self, reservation_id: int) -> ReservationInfo | None:
        return self._store.get(reservation_id)

    def store(self, reservation_id: int, info: ReservationInfo) -> None:
        self._store[reservation_id] = info
