"""
Adapter contract for ReservationCache.

Any implementation (in-memory, SQLite, ...) must pass these tests.
"""

from abc import ABC, abstractmethod

from src.adapters.ports import ReservationInfo
from src.domain.reservation_cache import ReservationCache


class ReservationCacheContract(ABC):

    @abstractmethod
    def create_cache(self) -> ReservationCache:
        """Return a fresh cache instance."""
        ...

    def test_store_and_get(self):
        cache = self.create_cache()
        info = ReservationInfo(
            reservation_id=42,
            guest_name="Alice",
            apartment_name="Le Matisse",
            arrival="2026-04-01",
            departure="2026-04-05",
        )
        cache.store(42, info)
        result = cache.get(42)
        assert result is not None
        assert result.reservation_id == 42
        assert result.guest_name == "Alice"
        assert result.arrival == "2026-04-01"
        assert result.departure == "2026-04-05"

    def test_unknown_returns_none(self):
        cache = self.create_cache()
        assert cache.get(99999) is None

    def test_overwrite_updates_value(self):
        cache = self.create_cache()
        info1 = ReservationInfo(1, "Alice", "Apt A", "2026-01-01", "2026-01-05")
        info2 = ReservationInfo(1, "Bob", "Apt A", "2026-01-01", "2026-01-05")
        cache.store(1, info1)
        cache.store(1, info2)
        result = cache.get(1)
        assert result is not None
        assert result.guest_name == "Bob"
