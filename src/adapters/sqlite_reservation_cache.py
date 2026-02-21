"""
SQLite adapter for ReservationCache.

Use ":memory:" for tests, a file path for production.
"""

import sqlite3
from datetime import datetime, timezone

from src.adapters.ports import ReservationInfo
from src.domain.reservation_cache import ReservationCache

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reservation_cache (
    reservation_id  INTEGER PRIMARY KEY,
    guest_name      TEXT NOT NULL,
    apartment_name  TEXT NOT NULL,
    arrival         TEXT NOT NULL,
    departure       TEXT NOT NULL,
    cached_at       TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteReservationCache(ReservationCache):

    def __init__(self, db_path: str = "checkin.db"):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    def get(self, reservation_id: int) -> ReservationInfo | None:
        row = self._conn.execute(
            "SELECT * FROM reservation_cache WHERE reservation_id = ?",
            (reservation_id,),
        ).fetchone()
        if not row:
            return None
        return ReservationInfo(
            reservation_id=row["reservation_id"],
            guest_name=row["guest_name"],
            apartment_name=row["apartment_name"],
            arrival=row["arrival"],
            departure=row["departure"],
        )

    def store(self, reservation_id: int, info: ReservationInfo) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO reservation_cache"
            " (reservation_id, guest_name, apartment_name, arrival, departure, cached_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (reservation_id, info.guest_name, info.apartment_name,
             info.arrival, info.departure, _now()),
        )
        self._conn.commit()
