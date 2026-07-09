"""
Regression test: SqliteRequestMemory handles a DB created with the old schema
(missing guest_name, property_name, etc.) by migrating on startup.
"""

import sqlite3

import pytest

from src.adapters.sqlite_memory import SqliteRequestMemory

_OLD_SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_messages (
    message_id     INTEGER PRIMARY KEY,
    reservation_id INTEGER NOT NULL,
    seen_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER NOT NULL,
    intent      TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending_acknowledgment',
    created_at  TEXT NOT NULL,
    request_id  TEXT NOT NULL UNIQUE,
    guest_message TEXT NOT NULL
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

_OLD_REQUEST_INSERT = """
INSERT INTO requests (reservation_id, intent, status, created_at, request_id, guest_message)
VALUES (42, 'early_checkin', 'pending_acknowledgment', '2026-01-01T00:00:00+00:00',
        'req-old-123', 'Can we check in early?')
"""


@pytest.fixture
def old_schema_db(tmp_path):
    """A file-based DB seeded with the old schema and one request row."""
    db_path = str(tmp_path / "old.db")
    conn = sqlite3.connect(db_path)
    conn.executescript(_OLD_SCHEMA)
    conn.execute(_OLD_REQUEST_INSERT)
    conn.commit()
    conn.close()
    return db_path


@pytest.mark.asyncio
async def test_get_request_survives_old_schema(old_schema_db):
    """Opening an old-schema DB should not crash and should return the request."""
    mem = SqliteRequestMemory(old_schema_db)
    req = await mem.get_request("req-old-123")
    assert req is not None
    assert req.reservation_id == 42
    assert req.intent == "early_checkin"
    assert req.guest_message == "Can we check in early?"
    # Migrated columns default to empty string
    assert req.guest_name == ""
    assert req.property_name == ""


@pytest.mark.asyncio
async def test_save_request_after_migration(old_schema_db):
    """After migrating an old DB, new requests with all fields can be saved."""
    mem = SqliteRequestMemory(old_schema_db)
    await mem.save_request(
        reservation_id=99,
        intent="late_checkout",
        request_id="req-new-456",
        guest_message="Can we stay until noon?",
        guest_name="Alice",
        property_name="Studio A",
        original_time="11:00",
        requested_time="12:00",
        relevant_date="2026-03-10",
    )
    req = await mem.get_request("req-new-456")
    assert req is not None
    assert req.guest_name == "Alice"
    assert req.property_name == "Studio A"
