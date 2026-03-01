"""
Retry classification for a misclassified message.

Clears the "seen" flag so the next poll cycle re-classifies the message.
Optionally clears an existing request (and its drafts) if one was created.

Usage:
    python scripts/retry_classification.py --message-id 12345
    python scripts/retry_classification.py --message-id 12345 --clear-request
    python scripts/retry_classification.py --message-id 12345 --message "I want to check in at 12:00"

Environment variables:
    DB_PATH  — SQLite database path (default: data/checkin.db)
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.sqlite_memory import SqliteRequestMemory


async def main() -> None:
    parser = argparse.ArgumentParser(description="Retry classification for a message")
    parser.add_argument("--message-id", type=int, required=True, help="Message ID to retry")
    parser.add_argument("--message", type=str, help="Substitute message text for re-classification")
    parser.add_argument("--clear-request", action="store_true", help="Delete existing request + drafts")
    args = parser.parse_args()

    db_path = os.environ.get("DB_PATH", "data/checkin.db")
    memory = SqliteRequestMemory(db_path=db_path)

    # Check if message was seen
    is_seen = await memory.has_message_been_seen(args.message_id)
    if not is_seen:
        print(f"WARNING: message_id={args.message_id} was never seen — nothing to clear.")
        return

    # Look up reservation_id BEFORE clearing seen flag (needed for --clear-request)
    row = memory._conn.execute(
        "SELECT reservation_id FROM seen_messages WHERE message_id = ?",
        (args.message_id,),
    ).fetchone()
    reservation_id = row["reservation_id"] if row else None

    # Clear seen flag
    await memory.delete_seen_message(args.message_id)
    print(f"Cleared seen flag for message_id={args.message_id}")

    # Optionally store substitute message
    if args.message:
        print(f"NOTE: Substitute message provided: {args.message!r}")
        print("The poller will re-fetch the original message from Smoobu.")
        print("If you need a different message classified, edit it in Smoobu first.")

    # Optionally clear request and its drafts
    if args.clear_request:
        if reservation_id:
            requests = await memory.get_history(reservation_id)
            if requests:
                for req in requests:
                    await memory.delete_request(req.request_id)
                    print(f"Deleted request {req.request_id} (intent={req.intent}) and its drafts")
            else:
                print(f"No requests found for reservation_id={reservation_id}")
        else:
            print("Cannot determine reservation_id — unable to find associated requests.")
            print("Use DB_PATH to manually inspect and delete requests if needed.")


if __name__ == "__main__":
    asyncio.run(main())
