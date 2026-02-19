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

    # Email (only when CLEANING_STAFF_CHANNEL=email)
    EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_USER, EMAIL_PASSWORD
    EMAIL_IMAP_HOST, EMAIL_IMAP_PORT, CLEANER_EMAIL
"""

import asyncio
import logging
import os
import sys
from datetime import date, timedelta

# Make sure project root is on sys.path when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.claude_intent import ClaudeIntentClassifier
from src.adapters.claude_response import ClaudeGuestAcknowledger, ClaudeReplyComposer, ClaudeResponseParser
from src.adapters.smoobu_client import SmoobuClient
from src.adapters.sqlite_memory import SqliteRequestMemory
from src.communication.factory import create_cleaner_notifier
from src.domain.intent import ConversationContext
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

    config = PipelineConfig(
        cleaner=create_cleaner_notifier(),
        classifier=ClaudeIntentClassifier(api_key=api_key),
        acknowledger=ClaudeGuestAcknowledger(api_key=api_key),
        parser=ClaudeResponseParser(api_key=api_key),
        composer=ClaudeReplyComposer(api_key=api_key),
        memory=SqliteRequestMemory(db_path=db_path),
    )
    return Pipeline(config)


async def poll_once(pipeline: Pipeline, smoobu: SmoobuClient, apartment_id: int, lookahead_days: int) -> None:
    today = date.today()
    arrival_from = today.isoformat()
    arrival_to = (today + timedelta(days=lookahead_days)).isoformat()

    log.info("Fetching active reservations %s → %s", arrival_from, arrival_to)
    try:
        reservations = smoobu.get_active_reservations(
            apartment_id=apartment_id,
            arrival_from=arrival_from,
            arrival_to=arrival_to,
        )
    except Exception as exc:
        log.error("Failed to fetch reservations: %s", exc)
        return

    log.info("Found %d reservation(s)", len(reservations))

    for res in reservations:
        try:
            messages = smoobu.get_messages(res.reservation_id)
        except Exception as exc:
            log.error("Failed to fetch messages for reservation %d: %s", res.reservation_id, exc)
            continue

        # Only process the last guest message to avoid re-processing history
        guest_messages = [m for m in messages if m.body.strip()]
        if not guest_messages:
            continue

        latest = guest_messages[-1]
        previous = [m.body for m in guest_messages[:-1]]

        context = ConversationContext(
            reservation_id=res.reservation_id,
            guest_name=res.guest_name,
            property_name=f"Apartment {res.apartment_id}",
            arrival_date=res.arrival,
            departure_date=res.departure,
            default_checkin_time="17:00",
            default_checkout_time="11:00",
            previous_messages=previous,
        )

        try:
            result = await pipeline.process_message(
                reservation_id=res.reservation_id,
                message=latest.body,
                context=context,
            )
            if result.action != "ignored" and result.action != "already_processed":
                log.info(
                    "Reservation %d → %s: %s",
                    res.reservation_id,
                    result.action,
                    result.details[:60],
                )
        except Exception as exc:
            log.error("Pipeline error for reservation %d: %s", res.reservation_id, exc)

    # Poll for cleaner responses
    try:
        cleaner_results = await pipeline.process_cleaner_responses()
        for r in cleaner_results:
            log.info("Cleaner response processed → %s: %s", r.action, r.details[:60])
    except Exception as exc:
        log.error("Failed to process cleaner responses: %s", exc)


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
