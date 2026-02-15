import requests

from .ports import GuestMessage, SmoobuGateway

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
            )
            for msg in data.get("messages", [])
        ]

    def send_message(self, reservation_id: int, subject: str, body: str) -> None:
        url = f"{BASE_URL}/reservations/{reservation_id}/messages/send-message-to-guest"
        resp = self.session.post(url, json={"subject": subject, "messageBody": body})
        resp.raise_for_status()
