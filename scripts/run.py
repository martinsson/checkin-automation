"""
Local process runner for the checkin-automation pipeline.

Polls Smoobu every POLL_INTERVAL seconds using the thread-based activity index,
processes new guest messages through the pipeline, and polls for cleaner responses.

Usage:
    source .env && python scripts/run.py

Environment variables (all required unless noted):
    SMOOBU_API_KEY          - Smoobu API key
    ANTHROPIC_API_KEY       - Anthropic/Claude API key
    CLEANING_STAFF_CHANNEL  - "email" or "console" (default: console)
    POLL_INTERVAL           - seconds between polls (default: 60)
    THREADS_CUTOFF_DAYS     - how many days back to scan threads (default: 7)
    DB_PATH                 - SQLite database path (default: data/checkin.db)
    CLEANER_NAME            - name of the cleaning staff contact (default: Marie)

    # Email (only when CLEANING_STAFF_CHANNEL=email)
    EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_USER, EMAIL_PASSWORD
    EMAIL_IMAP_HOST, EMAIL_IMAP_PORT, CLEANER_EMAIL
"""

import asyncio
import logging
import os
import sys

# Make sure project root is on sys.path when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.claude_intent import ClaudeIntentClassifier
from src.adapters.claude_response import ClaudeGuestAcknowledger, ClaudeReplyComposer, ClaudeResponseParser
from src.adapters.smoobu_client import SmoobuClient
from src.adapters.sqlite_memory import SqliteRequestMemory
from src.adapters.sqlite_reservation_cache import SqliteReservationCache
from src.communication.factory import create_cleaner_notifier
from src.shell.main_cycle import poll_cycle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"ERROR: environment variable {name!r} is not set.", file=sys.stderr)
        sys.exit(1)
    return value


async def main() -> None:
    smoobu_api_key = _require_env("SMOOBU_API_KEY")
    api_key = _require_env("ANTHROPIC_API_KEY")
    poll_interval = int(os.environ.get("POLL_INTERVAL", "60"))
    threads_cutoff_days = int(os.environ.get("THREADS_CUTOFF_DAYS", "7"))

    db_path = os.environ.get("DB_PATH", "data/checkin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    cleaner_name = os.environ.get("CLEANER_NAME", "Virginie")

    smoobu = SmoobuClient(api_key=smoobu_api_key)
    memory = SqliteRequestMemory(db_path=db_path)
    cache = SqliteReservationCache(db_path=db_path)
    cleaner = create_cleaner_notifier()
    classifier = ClaudeIntentClassifier(api_key=api_key)
    acknowledger = ClaudeGuestAcknowledger(api_key=api_key)
    parser = ClaudeResponseParser(api_key=api_key)
    composer = ClaudeReplyComposer(api_key=api_key)

    log.info(
        "Daemon started — interval=%ds  threads_cutoff=%dd",
        poll_interval,
        threads_cutoff_days,
    )

    while True:
        await poll_cycle(
            smoobu=smoobu,
            memory=memory,
            cache=cache,
            classifier=classifier,
            acknowledger=acknowledger,
            parser=parser,
            composer=composer,
            cleaner=cleaner,
            cleaner_name=cleaner_name,
            threads_cutoff_days=threads_cutoff_days,
        )
        log.info("Sleeping %ds …", poll_interval)
        await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Daemon stopped.")
