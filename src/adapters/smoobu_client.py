from datetime import datetime, timezone

import requests

from .ports import ActiveReservation, GuestMessage, ReservationInfo, SmoobuGateway, Thread, ThreadPage

BASE_URL = "https://login.smoobu.com/api"


class SmoobuClient(SmoobuGateway):
    """Adapter: real Smoobu HTTP client."""

    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Api-Key": api_key,
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
            }
        )

    def get_messages(self, reservation_id: int) -> list[GuestMessage]:
        url = f"{BASE_URL}/reservations/{reservation_id}/messages"
        resp = self.session.get(url)
        resp.raise_for_status()
        data = resp.json()

        return [
            GuestMessage(
                message_id=msg.get("id", 0),
                subject=msg.get("subject", ""),
                body=msg.get("message", ""),
                type=msg.get("type", 1),
            )
            for msg in data.get("messages", [])
        ]

    def send_message(self, reservation_id: int, subject: str, body: str) -> None:
        url = f"{BASE_URL}/reservations/{reservation_id}/messages/send-message-to-guest"
        resp = self.session.post(url, json={"subject": subject, "messageBody": body})
        resp.raise_for_status()

    def get_active_reservations(
        self,
        apartment_id: int,
        arrival_from: str,
        arrival_to: str,
    ) -> list[ActiveReservation]:
        reservations = []
        page = 1
        while True:
            resp = self.session.get(
                f"{BASE_URL}/reservations",
                params={
                    "apartmentId": apartment_id,
                    "pageSize": 100,
                    "page": page,
                    "arrivalFrom": arrival_from,
                    "arrivalTo": arrival_to,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            for b in data.get("bookings", []):
                reservations.append(
                    ActiveReservation(
                        reservation_id=b["id"],
                        guest_name=b.get("guest-name", ""),
                        arrival=b.get("arrival", ""),
                        departure=b.get("departure", ""),
                        apartment_id=b.get("apartment", {}).get("id", apartment_id),
                    )
                )
            if page >= data.get("page_count", 1):
                break
            page += 1
        return reservations

    def get_threads(self, page_number: int = 1) -> ThreadPage:
        resp = self.session.get(
            f"{BASE_URL}/threads",
            params={"page_number": page_number, "page_size": 25},
        )
        resp.raise_for_status()
        data = resp.json()

        threads = []
        for item in data.get("data", []):
            latest_raw = item.get("latest_message", {}).get("created_at", "")
            try:
                latest_at = datetime.fromisoformat(latest_raw.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                latest_at = datetime.now(timezone.utc)

            threads.append(Thread(
                reservation_id=item.get("booking", {}).get("id", 0),
                guest_name=item.get("booking", {}).get("guest_name", ""),
                apartment_name=item.get("apartment", {}).get("name", ""),
                latest_message_at=latest_at,
            ))

        total_pages = data.get("page_count", 1)
        return ThreadPage(threads=threads, has_more=page_number < total_pages)

    def get_reservation(self, reservation_id: int) -> ReservationInfo | None:
        resp = self.session.get(f"{BASE_URL}/reservations/{reservation_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        b = resp.json()
        return ReservationInfo(
            reservation_id=b["id"],
            guest_name=b.get("guest-name", ""),
            apartment_name=b.get("apartment", {}).get("name", ""),
            arrival=b.get("arrival", ""),
            departure=b.get("departure", ""),
        )
