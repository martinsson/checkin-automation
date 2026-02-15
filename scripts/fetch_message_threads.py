"""
Fetch all message threads for Le Matisse from Smoobu and save as a fixture.

Usage:
    source .env && python scripts/fetch_message_threads.py
"""

import json
import os

import requests

APARTMENT_ID = 3052591  # Le Matisse
OUTPUT_PATH = "tests/fixtures/matisse_message_threads.json"

session = requests.Session()
session.headers.update(
    {
        "Api-Key": os.environ["SMOOBU_API_KEY"],
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }
)

# Fetch all reservations (paginated)
bookings = []
page = 1
while True:
    resp = session.get(
        "https://login.smoobu.com/api/reservations",
        params={"apartmentId": APARTMENT_ID, "pageSize": 100, "page": page, "departureFrom": "2020-01-01"},
    )
    data = resp.json()
    bookings.extend(data.get("bookings", []))
    if page >= data.get("page_count", 1):
        break
    page += 1

print(f"Found {len(bookings)} reservations")

# Fetch messages for each reservation
threads = []
for b in bookings:
    bid = b["id"]
    reservation = session.get(f"https://login.smoobu.com/api/reservations/{bid}").json()
    messages = session.get(f"https://login.smoobu.com/api/reservations/{bid}/messages").json().get("messages", [])
    threads.append(
        {
            "reservation_id": bid,
            "guest_name": reservation.get("guest-name"),
            "arrival": reservation.get("arrival"),
            "departure": reservation.get("departure"),
            "channel": reservation.get("channel", {}).get("name"),
            "messages": messages,
        }
    )
    print(f"  {bid} ({reservation.get('guest-name')}): {len(messages)} messages")

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w") as f:
    json.dump(threads, f, indent=2, ensure_ascii=False)

print(f"\nSaved {len(threads)} threads to {OUTPUT_PATH}")
