"""
Integration test: Smoobu API read/send round-trip.

Nothing is mocked. The test:
1. Reads existing messages for a test booking
2. Sends a new message to the test booking
3. Reads messages again and verifies the new one appears

Required env vars (see .env.example):
    SMOOBU_API_KEY   — Smoobu API key
    TEST_BOOKING_ID  — a reservation ID to test against

Run locally:
    source .env && pytest tests/test_smoobu_roundtrip.py -v -s
"""

import os
import uuid

import pytest

from src.adapters.smoobu_client import SmoobuClient

# ---------------------------------------------------------------------------
# Skip if credentials are missing
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("SMOOBU_API_KEY", "")
BOOKING_ID = os.environ.get("TEST_BOOKING_ID", "")

CREDS_AVAILABLE = bool(API_KEY) and bool(BOOKING_ID)

pytestmark = pytest.mark.skipif(
    not CREDS_AVAILABLE,
    reason="SMOOBU_API_KEY or TEST_BOOKING_ID not set — skipping integration test",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    return SmoobuClient(api_key=API_KEY)


@pytest.fixture
def reservation_id():
    return int(BOOKING_ID)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_read_messages(client, reservation_id):
    """Verify we can read messages from a reservation."""
    messages = client.get_messages(reservation_id)

    # The test booking should have at least zero messages (no crash)
    assert isinstance(messages, list)


def test_send_then_read(client, reservation_id):
    """Send a message, then read messages and verify it appears."""
    tag = uuid.uuid4().hex[:8]
    subject = f"Integration test {tag}"
    body = f"Automated test message — please ignore. ID: {tag}"

    # Step 1: send
    client.send_message(reservation_id, subject, body)

    # Step 2: read back
    messages = client.get_messages(reservation_id)

    # Step 3: verify the message we just sent is in the list
    found = any(tag in msg.body for msg in messages)
    assert found, (
        f"Sent message with tag {tag!r} not found in {len(messages)} messages. "
        f"Last 3 messages: {[m.body[:80] for m in messages[-3:]]}"
    )
