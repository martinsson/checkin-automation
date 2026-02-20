from .ports import ActiveReservation, GuestMessage, SmoobuGateway


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
        self._reservations: list[ActiveReservation] = []
        self.sent: list[tuple[int, str, str]] = []
        self._next_id = 1

    def inject_active_reservation(self, reservation: ActiveReservation) -> None:
        """Test helper: register a reservation as active."""
        self._reservations.append(reservation)

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

    def get_active_reservations(
        self,
        apartment_id: int,
        arrival_from: str,
        arrival_to: str,
    ) -> list[ActiveReservation]:
        return [
            r for r in self._reservations
            if r.apartment_id == apartment_id
            and arrival_from <= r.arrival <= arrival_to
        ]

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
