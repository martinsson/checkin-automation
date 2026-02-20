"""
SQLite adapter for RequestMemory.

Use ":memory:" for tests, a file path for production.
"""

import sqlite3
from datetime import datetime, timezone

from src.domain.memory import Draft, ProcessedRequest, RequestMemory

_SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER NOT NULL,
    intent      TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending_acknowledgment',
    created_at  TEXT NOT NULL,
    request_id  TEXT NOT NULL UNIQUE,
    guest_message TEXT NOT NULL,
    guest_name  TEXT NOT NULL DEFAULT '',
    property_name TEXT NOT NULL DEFAULT '',
    original_time TEXT NOT NULL DEFAULT '',
    requested_time TEXT NOT NULL DEFAULT '',
    relevant_date TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS drafts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id  TEXT NOT NULL REFERENCES requests(request_id),
    reservation_id INTEGER NOT NULL,
    intent      TEXT NOT NULL,
    step        TEXT NOT NULL,
    draft_body  TEXT NOT NULL,
    verdict     TEXT NOT NULL DEFAULT 'pending',
    actual_message_sent TEXT,
    owner_comment TEXT,
    created_at  TEXT NOT NULL,
    reviewed_at TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


class SqliteRequestMemory(RequestMemory):

    def __init__(self, db_path: str = "checkin.db"):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    # -- request tracking ----------------------------------------------------

    async def has_been_processed(self, reservation_id: int, intent: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM requests WHERE reservation_id = ? AND intent = ?",
            (reservation_id, intent),
        ).fetchone()
        return row is not None

    async def save_request(
        self,
        reservation_id: int,
        intent: str,
        request_id: str,
        guest_message: str,
        guest_name: str = "",
        property_name: str = "",
        original_time: str = "",
        requested_time: str = "",
        relevant_date: str = "",
    ) -> None:
        self._conn.execute(
            "INSERT INTO requests"
            " (reservation_id, intent, request_id, guest_message, created_at,"
            "  guest_name, property_name, original_time, requested_time, relevant_date)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (reservation_id, intent, request_id, guest_message, _now(),
             guest_name, property_name, original_time, requested_time, relevant_date),
        )
        self._conn.commit()

    async def update_status(self, request_id: str, status: str) -> None:
        self._conn.execute(
            "UPDATE requests SET status = ? WHERE request_id = ?",
            (status, request_id),
        )
        self._conn.commit()

    async def get_request(self, request_id: str) -> ProcessedRequest | None:
        row = self._conn.execute(
            "SELECT * FROM requests WHERE request_id = ?", (request_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_request(row)

    async def get_history(self, reservation_id: int) -> list[ProcessedRequest]:
        rows = self._conn.execute(
            "SELECT * FROM requests WHERE reservation_id = ? ORDER BY created_at",
            (reservation_id,),
        ).fetchall()
        return [self._row_to_request(r) for r in rows]

    @staticmethod
    def _row_to_request(row) -> ProcessedRequest:
        return ProcessedRequest(
            reservation_id=row["reservation_id"],
            intent=row["intent"],
            status=row["status"],
            created_at=_parse_dt(row["created_at"]),
            request_id=row["request_id"],
            guest_message=row["guest_message"],
            guest_name=row["guest_name"],
            property_name=row["property_name"],
            original_time=row["original_time"],
            requested_time=row["requested_time"],
            relevant_date=row["relevant_date"],
        )

    # -- draft management ----------------------------------------------------

    async def save_draft(
        self,
        request_id: str,
        reservation_id: int,
        intent: str,
        step: str,
        draft_body: str,
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO drafts (request_id, reservation_id, intent, step, draft_body, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (request_id, reservation_id, intent, step, draft_body, _now()),
        )
        self._conn.commit()
        assert cur.lastrowid is not None
        return cur.lastrowid

    async def get_pending_drafts(self) -> list[Draft]:
        rows = self._conn.execute(
            "SELECT * FROM drafts WHERE verdict = 'pending' ORDER BY created_at"
        ).fetchall()
        return [self._row_to_draft(r) for r in rows]

    async def get_draft(self, draft_id: int) -> Draft | None:
        row = self._conn.execute(
            "SELECT * FROM drafts WHERE id = ?", (draft_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_draft(row)

    async def review_draft(
        self,
        draft_id: int,
        verdict: str,
        actual_message_sent: str | None = None,
        owner_comment: str | None = None,
    ) -> None:
        self._conn.execute(
            "UPDATE drafts SET verdict = ?, actual_message_sent = ?,"
            " owner_comment = ?, reviewed_at = ? WHERE id = ?",
            (verdict, actual_message_sent, owner_comment, _now(), draft_id),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_draft(row) -> Draft:
        return Draft(
            draft_id=row["id"],
            request_id=row["request_id"],
            reservation_id=row["reservation_id"],
            intent=row["intent"],
            step=row["step"],
            draft_body=row["draft_body"],
            verdict=row["verdict"],
            actual_message_sent=row["actual_message_sent"],
            owner_comment=row["owner_comment"],
            created_at=_parse_dt(row["created_at"]),
            reviewed_at=_parse_dt(row["reviewed_at"]) if row["reviewed_at"] else None,
        )
