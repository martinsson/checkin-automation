"""
Integration test: full email round-trip with real Gmail accounts.

Nothing is mocked. The test:
1. System account sends a query email to the cleaner account
2. Cleaner account sends a reply (programmatically, via SMTP)
3. System account polls IMAP and finds the response
4. We verify the request_id correlation works

Required env vars (see .env.example):
    EMAIL_USER, EMAIL_PASSWORD        — system account
    CLEANER_EMAIL, CLEANER_EMAIL_PASSWORD — cleaner account
    EMAIL_SMTP_HOST, EMAIL_IMAP_HOST  — defaults to Gmail

Run locally:
    source .env && pytest tests/test_email_roundtrip.py -v -s

The test is skipped automatically if credentials are not set.
"""

import asyncio
import os
import smtplib
import time
import uuid
from email.mime.text import MIMEText

import pytest
import pytest_asyncio

from src.communication.email_notifier import EmailCleanerNotifier
from src.communication.ports import CleanerQuery

# ---------------------------------------------------------------------------
# Skip entire module if credentials are missing
# ---------------------------------------------------------------------------

SYSTEM_USER = os.environ.get("EMAIL_USER", "")
SYSTEM_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
CLEANER_EMAIL = os.environ.get("CLEANER_EMAIL", "")
CLEANER_PASSWORD = os.environ.get("CLEANER_EMAIL_PASSWORD", "")

SMTP_HOST = os.environ.get("EMAIL_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
IMAP_HOST = os.environ.get("EMAIL_IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.environ.get("EMAIL_IMAP_PORT", "993"))

CREDS_AVAILABLE = all([SYSTEM_USER, SYSTEM_PASSWORD, CLEANER_EMAIL, CLEANER_PASSWORD])

pytestmark = pytest.mark.skipif(
    not CREDS_AVAILABLE,
    reason="Email credentials not set — skipping integration test",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MAX_POLL_SECONDS = 60
POLL_INTERVAL_SECONDS = 5


def send_reply_as_cleaner(subject: str, body: str):
    """Use the cleaner's Gmail account to send a reply to the system account."""
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = f"Re: {subject}"
    msg["From"] = CLEANER_EMAIL
    msg["To"] = SYSTEM_USER

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(CLEANER_EMAIL, CLEANER_PASSWORD)
        server.send_message(msg)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def notifier():
    return EmailCleanerNotifier(
        smtp_host=SMTP_HOST,
        smtp_port=SMTP_PORT,
        smtp_user=SYSTEM_USER,
        smtp_password=SYSTEM_PASSWORD,
        imap_host=IMAP_HOST,
        imap_port=IMAP_PORT,
        cleaner_email=CLEANER_EMAIL,
    )


@pytest.fixture
def unique_request_id():
    """Each test run gets a unique ID so concurrent runs don't interfere."""
    return f"test-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_query_delivers_email(notifier, unique_request_id):
    """Verify that send_query actually delivers an email (no exception)."""
    query = CleanerQuery(
        request_id=unique_request_id,
        cleaner_name="Test Cleaner",
        guest_name="Test Guest",
        property_name="Test Apartment",
        request_type="early_checkin",
        original_time="15:00",
        requested_time="12:00",
        date="2026-03-01",
        message=f"Can you finish by 12:00 on March 1st? [test id: {unique_request_id}]",
    )

    tracking_id = await notifier.send_query(query)

    assert tracking_id  # got a Message-ID back
    assert "@" in tracking_id  # looks like a real Message-ID


@pytest.mark.asyncio
async def test_full_roundtrip(notifier, unique_request_id):
    """
    Full round-trip:
    1. System sends query to cleaner
    2. Cleaner replies
    3. System polls and finds the reply
    4. request_id matches
    """
    query = CleanerQuery(
        request_id=unique_request_id,
        cleaner_name="Test Cleaner",
        guest_name="Test Guest",
        property_name="Test Apartment",
        request_type="early_checkin",
        original_time="15:00",
        requested_time="12:00",
        date="2026-03-01",
        message=f"Can you finish by 12:00 on March 1st? [test id: {unique_request_id}]",
    )

    # Step 1: send the query
    await notifier.send_query(query)

    # Step 2: wait a moment for delivery, then reply as the cleaner
    await asyncio.sleep(5)
    subject = f"[REQ-{unique_request_id}] Test Apartment — 2026-03-01"
    send_reply_as_cleaner(subject, "Yes, that works for me!")

    # Step 3: poll until we get the response (with timeout)
    matched = None
    deadline = time.time() + MAX_POLL_SECONDS

    while time.time() < deadline:
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        responses = await notifier.poll_responses()

        for r in responses:
            if r.request_id == unique_request_id:
                matched = r
                break

        if matched:
            break

    # Step 4: verify
    assert matched is not None, (
        f"No response with request_id={unique_request_id!r} "
        f"found within {MAX_POLL_SECONDS}s"
    )
    assert "Yes" in matched.raw_text
    assert matched.request_id == unique_request_id
