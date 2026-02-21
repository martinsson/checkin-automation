"""
Contract tests for ReservationCache implementations.

Runs against both InMemoryReservationCache and SqliteReservationCache.
"""

from src.adapters.simulator_reservation_cache import InMemoryReservationCache
from src.adapters.sqlite_reservation_cache import SqliteReservationCache
from tests.contracts.reservation_cache_contract import ReservationCacheContract


class TestInMemoryReservationCache(ReservationCacheContract):

    def create_cache(self):
        return InMemoryReservationCache()

    def test_isolation_between_instances(self):
        """Two in-memory instances must not share state."""
        from src.adapters.ports import ReservationInfo
        c1 = InMemoryReservationCache()
        c2 = InMemoryReservationCache()
        c1.store(1, ReservationInfo(1, "Alice", "Apt", "2026-01-01", "2026-01-05"))
        assert c2.get(1) is None


class TestSqliteReservationCache(ReservationCacheContract):

    def create_cache(self):
        return SqliteReservationCache(":memory:")

    def test_table_created_automatically(self):
        """No manual schema migration needed."""
        cache = SqliteReservationCache(":memory:")
        # If table creation failed, get() would raise — just call it
        result = cache.get(1)
        assert result is None
