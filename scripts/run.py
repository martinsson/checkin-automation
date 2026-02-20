"""
Local process runner for the checkin-automation pipeline.

Polls Smoobu every POLL_INTERVAL seconds for new guest messages on active
reservations, processes them through the pipeline, and polls for cleaner
responses.

Usage:
    source .env && python scripts/run.py

Environment variables (all required unless noted):
    SMOOBU_API_KEY          - Smoobu API key
    ANTHROPIC_API_KEY       - Anthropic/Claude API key
    SMOOBU_APARTMENT_ID     - Smoobu apartment ID to monitor
    CLEANING_STAFF_CHANNEL  - "email" or "console" (default: console)
    POLL_INTERVAL           - seconds between polls (default: 60)
    LOOKAHEAD_DAYS          - how many days ahead to look for arrivals (default: 14)
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
from src.communication.factory import create_cleaner_notifier
from src.daemon import poll_once
from src.pipeline import Pipeline, PipelineConfig

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


def build_pipeline() -> Pipeline:
    api_key = _require_env("ANTHROPIC_API_KEY")
    db_path = os.environ.get("DB_PATH", "data/checkin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    cleaner_name = os.environ.get("CLEANER_NAME", "Marie")
    config = PipelineConfig(
        cleaner=create_cleaner_notifier(),
        classifier=ClaudeIntentClassifier(api_key=api_key),
        acknowledger=ClaudeGuestAcknowledger(api_key=api_key),
        parser=ClaudeResponseParser(api_key=api_key),
        composer=ClaudeReplyComposer(api_key=api_key),
        memory=SqliteRequestMemory(db_path=db_path),
        cleaner_name=cleaner_name,
    )
    return Pipeline(config)



async def main() -> None:
    apartment_id = int(_require_env("SMOOBU_APARTMENT_ID"))
    smoobu_api_key = _require_env("SMOOBU_API_KEY")
    poll_interval = int(os.environ.get("POLL_INTERVAL", "60"))
    lookahead_days = int(os.environ.get("LOOKAHEAD_DAYS", "14"))

    smoobu = SmoobuClient(api_key=smoobu_api_key)
    pipeline = build_pipeline()

    log.info(
        "Daemon started — apartment=%d  interval=%ds  lookahead=%dd",
        apartment_id,
        poll_interval,
        lookahead_days,
    )

    while True:
        await poll_once(pipeline, smoobu, apartment_id, lookahead_days)
        log.info("Sleeping %ds …", poll_interval)
        await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Daemon stopped.")
