"""
Adapter contract tests for CleanerNotifier — both console and email.

The same contract is verified against:
  - ConsoleCleanerNotifier  (always runs, no credentials needed)
  - EmailCleanerNotifier    (skipped if email credentials are not set)
"""

import asyncio
import os
import smtplib
from email.mime.text import MIMEText

import pytest

from src.communication.console_notifier import ConsoleCleanerNotifier
from src.communication.email_notifier import EmailCleanerNotifier

from tests.contracts.cleaner_notifier_contract import CleanerNotifierContract

# ---------------------------------------------------------------------------
# Console simulator — always runs
# ---------------------------------------------------------------------------


class TestConsoleCleanerContract(CleanerNotifierContract):

    def create_notifier(self):
        self._notifier = ConsoleCleanerNotifier()
        return self._notifier

    async def make_cleaner_reply(self, request_id, text):
        self._notifier.simulate_response(request_id, text)


# ---------------------------------------------------------------------------
# Real email — skipped without credentials
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


@pytest.mark.skipif(
    not CREDS_AVAILABLE,
    reason="Email credentials not set",
)
class TestEmailCleanerContract(CleanerNotifierContract):

    poll_max_seconds = 60
    poll_interval_seconds = 5
    pre_reply_delay = 5

    def create_notifier(self):
        return EmailCleanerNotifier(
            smtp_host=SMTP_HOST,
            smtp_port=SMTP_PORT,
            smtp_user=SYSTEM_USER,
            smtp_password=SYSTEM_PASSWORD,
            imap_host=IMAP_HOST,
            imap_port=IMAP_PORT,
            cleaner_email=CLEANER_EMAIL,
        )

    async def make_cleaner_reply(self, request_id, text):
        subject = f"Re: [REQ-{request_id}] Test Apartment — 2026-03-01"
        msg = MIMEText(text, _charset="utf-8")
        msg["Subject"] = subject
        msg["From"] = CLEANER_EMAIL
        msg["To"] = SYSTEM_USER

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(CLEANER_EMAIL, CLEANER_PASSWORD)
            server.send_message(msg)
