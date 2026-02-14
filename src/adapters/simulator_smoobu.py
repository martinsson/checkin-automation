from .ports import GuestMessage, SmoobuGateway


class SimulatorSmoobuGateway(SmoobuGateway):
    """
    In-memory fake for testing. No mocking framework needed.

    Test helpers:
        inject_guest_message() — simulate a guest sending a message
        sent                   — list of (reservation_id, subject, body) tuples
                                 recorded by send_message()
    """

    def __init__(self):
        self._messages: dict[int, list[GuestMessage]] = {}
        self.sent: list[tuple[int, str, str]] = []
        self._next_id = 1

    def inject_guest_message(
        self, reservation_id: int, subject: str, body: str
    ) -> None:
        """Test helper: simulate a guest sending a message."""
        msg = GuestMessage(
            message_id=self._next_id,
            subject=subject,
            body=body,
        )
        self._next_id += 1
        self._messages.setdefault(reservation_id, []).append(msg)

    def get_messages(self, reservation_id: int) -> list[GuestMessage]:
        return list(self._messages.get(reservation_id, []))

    def send_message(self, reservation_id: int, subject: str, body: str) -> None:
        self.sent.append((reservation_id, subject, body))
        # Also visible via get_messages so the conversation grows
        msg = GuestMessage(
            message_id=self._next_id,
            subject=subject,
            body=body,
        )
        self._next_id += 1
        self._messages.setdefault(reservation_id, []).append(msg)
