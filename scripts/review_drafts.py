#!/usr/bin/env python3
"""
Owner review CLI — list, approve, and reject AI-generated drafts.

Usage (from project root):
    python scripts/review_drafts.py                  # list pending drafts
    python scripts/review_drafts.py ok 3             # approve draft #3
    python scripts/review_drafts.py nok 3            # reject draft #3 (interactive)
    python scripts/review_drafts.py show 3           # show full draft details
"""

import asyncio
import os
import sys
import textwrap

# Allow running as `python scripts/review_drafts.py` from project root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.adapters.sqlite_memory import SqliteRequestMemory

DB_PATH = "checkin.db"


def _wrap(text: str, width: int = 72, indent: str = "    ") -> str:
    return textwrap.fill(text, width=width, initial_indent=indent, subsequent_indent=indent)


async def list_pending(mem: SqliteRequestMemory) -> None:
    drafts = await mem.get_pending_drafts()
    if not drafts:
        print("No pending drafts.")
        return

    print(f"\n{'ID':>4}  {'Step':<16}  {'Intent':<16}  {'Res.ID':>6}  Preview")
    print("-" * 80)
    for d in drafts:
        preview = d.draft_body[:50].replace("\n", " ")
        print(f"{d.draft_id:>4}  {d.step:<16}  {d.intent:<16}  {d.reservation_id:>6}  {preview}...")
    print()


async def show_draft(mem: SqliteRequestMemory, draft_id: int) -> None:
    draft = await mem.get_draft(draft_id)
    if not draft:
        print(f"Draft #{draft_id} not found.")
        return

    req = await mem.get_request(draft.request_id)
    print(f"\n{'=' * 60}")
    print(f"  Draft #{draft.draft_id}  |  {draft.step}  |  {draft.intent}")
    print(f"  Request: {draft.request_id}")
    print(f"  Reservation: {draft.reservation_id}")
    if req:
        print(f"  Guest message: {req.guest_message[:80]}")
    print(f"  Status: {draft.verdict}")
    print(f"  Created: {draft.created_at}")
    if draft.reviewed_at:
        print(f"  Reviewed: {draft.reviewed_at}")
    print(f"{'=' * 60}")
    print(f"\n{draft.draft_body}\n")
    if draft.actual_message_sent:
        print(f"  Actually sent: {draft.actual_message_sent}")
    if draft.owner_comment:
        print(f"  Comment: {draft.owner_comment}")
    print()


async def approve(mem: SqliteRequestMemory, draft_id: int) -> None:
    draft = await mem.get_draft(draft_id)
    if not draft:
        print(f"Draft #{draft_id} not found.")
        return
    if draft.verdict != "pending":
        print(f"Draft #{draft_id} already reviewed ({draft.verdict}).")
        return

    await mem.review_draft(draft_id, "ok")
    print(f"Draft #{draft_id} approved.")


async def reject(mem: SqliteRequestMemory, draft_id: int) -> None:
    draft = await mem.get_draft(draft_id)
    if not draft:
        print(f"Draft #{draft_id} not found.")
        return
    if draft.verdict != "pending":
        print(f"Draft #{draft_id} already reviewed ({draft.verdict}).")
        return

    print(f"\nDraft #{draft_id} ({draft.step}):")
    print(_wrap(draft.draft_body))
    print()

    actual = input("What did you actually send? (leave empty to skip): ").strip() or None
    comment = input("Why did you change it? (leave empty to skip): ").strip() or None

    await mem.review_draft(draft_id, "nok", actual, comment)
    print(f"Draft #{draft_id} rejected.")


async def main() -> None:
    mem = SqliteRequestMemory(DB_PATH)

    if len(sys.argv) < 2:
        await list_pending(mem)
        return

    cmd = sys.argv[1]

    if cmd == "show" and len(sys.argv) >= 3:
        await show_draft(mem, int(sys.argv[2]))
    elif cmd == "ok" and len(sys.argv) >= 3:
        await approve(mem, int(sys.argv[2]))
    elif cmd == "nok" and len(sys.argv) >= 3:
        await reject(mem, int(sys.argv[2]))
    else:
        print(__doc__)


if __name__ == "__main__":
    asyncio.run(main())
