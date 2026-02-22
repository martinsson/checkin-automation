#!/usr/bin/env python3
"""
Quick DB status viewer.

Usage:
    python scripts/db_status.py               # last 10 seen messages
    python scripts/db_status.py --requests    # last 10 processed requests
    python scripts/db_status.py --drafts      # last 10 drafts
    python scripts/db_status.py --all         # everything
"""

import argparse
import os
import sqlite3
import textwrap

DB_PATH = os.getenv("DB_PATH", "data/checkin.db")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def col_exists(conn: sqlite3.Connection, table: str, col: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == col for r in rows)


def print_seen_messages(conn: sqlite3.Connection, n: int = 10) -> None:
    rows = conn.execute(
        "SELECT message_id, reservation_id, seen_at"
        " FROM seen_messages ORDER BY seen_at DESC LIMIT ?",
        (n,),
    ).fetchall()
    total = conn.execute("SELECT count(*) FROM seen_messages").fetchone()[0]

    print(f"\n── Seen messages (last {n} of {total}) ─────────────────────────────")
    if not rows:
        print("  (none)")
        return
    print(f"  {'message_id':<14} {'reservation_id':<16} seen_at")
    print(f"  {'-'*14} {'-'*16} {'-'*30}")
    for r in rows:
        print(f"  {r['message_id']:<14} {r['reservation_id']:<16} {r['seen_at']}")


def print_requests(conn: sqlite3.Connection, n: int = 10) -> None:
    has_guest_name = col_exists(conn, "requests", "guest_name")
    extra_cols = ", guest_name, property_name" if has_guest_name else ""

    rows = conn.execute(
        f"SELECT reservation_id, intent, status, created_at, guest_message{extra_cols}"
        f" FROM requests ORDER BY created_at DESC LIMIT ?",
        (n,),
    ).fetchall()
    total = conn.execute("SELECT count(*) FROM requests").fetchone()[0]

    print(f"\n── Processed requests (last {n} of {total}) ──────────────────────────")
    if not rows:
        print("  (none)")
        return
    for r in rows:
        guest_name = r["guest_name"] if has_guest_name else ""
        property_name = r["property_name"] if has_guest_name else ""
        label = f"{guest_name} @ {property_name}".strip(" @") if (guest_name or property_name) else ""
        print(f"\n  [{r['created_at'][:19]}]  reservation={r['reservation_id']}  intent={r['intent']}  status={r['status']}")
        if label:
            print(f"  Guest: {label}")
        snippet = r["guest_message"].replace("\n", " ")
        print(f"  Message: {textwrap.shorten(snippet, width=100)}")


def print_drafts(conn: sqlite3.Connection, n: int = 10) -> None:
    rows = conn.execute(
        "SELECT id, reservation_id, intent, step, verdict, draft_body, created_at"
        " FROM drafts ORDER BY created_at DESC LIMIT ?",
        (n,),
    ).fetchall()
    total = conn.execute("SELECT count(*) FROM drafts").fetchone()[0]
    pending = conn.execute("SELECT count(*) FROM drafts WHERE verdict='pending'").fetchone()[0]

    print(f"\n── Drafts (last {n} of {total}, {pending} pending) ──────────────────────")
    if not rows:
        print("  (none)")
        return
    for r in rows:
        verdict_marker = "⏳" if r["verdict"] == "pending" else ("✓" if r["verdict"] == "approved" else "✗")
        print(f"\n  #{r['id']} [{r['created_at'][:19]}]  reservation={r['reservation_id']}  "
              f"intent={r['intent']}  step={r['step']}  verdict={verdict_marker}{r['verdict']}")
        snippet = r["draft_body"].replace("\n", " ")
        print(f"  Draft: {textwrap.shorten(snippet, width=100)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect the checkin automation DB")
    parser.add_argument("--requests", action="store_true", help="Show processed requests")
    parser.add_argument("--drafts", action="store_true", help="Show drafts")
    parser.add_argument("--all", action="store_true", dest="all_", help="Show everything")
    parser.add_argument("-n", type=int, default=10, help="Number of rows (default: 10)")
    args = parser.parse_args()

    show_all = args.all_ or not (args.requests or args.drafts)

    print(f"DB: {DB_PATH}")
    conn = connect()

    if show_all or not (args.requests or args.drafts):
        print_seen_messages(conn, args.n)
    if args.requests or args.all_:
        print_requests(conn, args.n)
    if args.drafts or args.all_:
        print_drafts(conn, args.n)

    if not (args.requests or args.drafts or args.all_):
        # default: show a quick summary of all tables too
        print_requests(conn, args.n)
        print_drafts(conn, args.n)

    print()


if __name__ == "__main__":
    main()
