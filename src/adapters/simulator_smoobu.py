from datetime import datetime, timedelta, timezone

from .ports import ActiveReservation, GuestMessage, ReservationInfo, SmoobuGateway, Thread, ThreadPage


class SimulatorSmoobuGateway(SmoobuGateway):
    """
    In-memory fake for testing. No mocking framework needed.

    Test helpers:
        inject_guest_message()       — simulate a message on a reservation
        inject_active_reservation()  — register a reservation (also enables get_reservation())
        sent                         — list of (reservation_id, subject, body) tuples
                                       recorded by send_message()
    """

    def __init__(self):
        self._messages: dict[int, list[GuestMessage]] = {}
        self._reservations: list[ActiveReservation] = []
        self._reservation_info: dict[int, ReservationInfo] = {}
        self.sent: list[tuple[int, str, str]] = []
        self._next_id = 1

    def inject_active_reservation(self, reservation: ActiveReservation) -> None:
        """Test helper: register a reservation as active and cache its metadata."""
        self._reservations.append(reservation)
        self._reservation_info[reservation.reservation_id] = ReservationInfo(
            reservation_id=reservation.reservation_id,
            guest_name=reservation.guest_name,
            apartment_name=f"Apartment {reservation.apartment_id}",
            arrival=reservation.arrival,
            departure=reservation.departure,
        )

    def inject_guest_message(
        self,
        reservation_id: int,
        subject: str,
        body: str,
        type: int = 1,
    ) -> None:
        """Test helper: add a message to a reservation. type=1 guest, type=2 host."""
        msg = GuestMessage(
            message_id=self._next_id,
            subject=subject,
            body=body,
            type=type,
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
        # Also visible via get_messages; host outbox = type 2
        msg = GuestMessage(
            message_id=self._next_id,
            subject=subject,
            body=body,
            type=2,
        )
        self._next_id += 1
        self._messages.setdefault(reservation_id, []).append(msg)

    def get_threads(self, page_number: int = 1) -> ThreadPage:
        """Return threads derived from injected reservations.

        Sorted by most-recent message timestamp descending (via message_id order).
        Single page (has_more=False) — simulator doesn't paginate.
        """
        threads = []
        for reservation_id, messages in self._messages.items():
            if not messages:
                continue
            info = self._reservation_info.get(reservation_id)
            # Use message_id as monotonic proxy for recency — higher id = more recent.
            # Offset back from now so threads appear "recent" within any cutoff.
            latest_id = messages[-1].message_id
            latest_at = datetime.now(timezone.utc) - timedelta(seconds=1000 - latest_id)
            threads.append(Thread(
                reservation_id=reservation_id,
                guest_name=info.guest_name if info else "",
                apartment_name=info.apartment_name if info else "",
                latest_message_at=latest_at,
            ))

        # Most recent first
        threads.sort(key=lambda t: t.latest_message_at, reverse=True)
        return ThreadPage(threads=threads, has_more=False)

    def get_reservation(self, reservation_id: int) -> ReservationInfo | None:

        return self._reservation_info.get(reservation_id)
