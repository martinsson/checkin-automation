from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class GuestMessage:
    """A message from a Smoobu reservation conversation."""

    message_id: int
    subject: str
    body: str
    type: int = 1  # 1 = guest (inbox), 2 = host (outbox)


@dataclass
class ActiveReservation:
    """A reservation that is currently active or upcoming."""

    reservation_id: int
    guest_name: str
    arrival: str
    departure: str
    apartment_id: int


@dataclass
class Thread:
    """A conversation thread from the Smoobu global inbox."""

    reservation_id: int
    guest_name: str
    apartment_name: str
    latest_message_at: datetime


@dataclass
class ThreadPage:
    """A page of threads from GET /api/threads."""

    threads: list[Thread]
    has_more: bool


@dataclass
class ReservationInfo:
    """Reservation metadata used to build ConversationContext."""

    reservation_id: int
    guest_name: str
    apartment_name: str
    arrival: str   # ISO date YYYY-MM-DD
    departure: str  # ISO date YYYY-MM-DD


class SmoobuGateway(ABC):
    """
    Port: how we interact with Smoobu for guest messaging.

    The business logic depends ONLY on this interface.
    It doesn't know or care whether messages go through the real
    Smoobu API or an in-memory simulator.
    """

    @abstractmethod
    def get_messages(self, reservation_id: int) -> list[GuestMessage]:
        """Read all messages for a reservation."""
        ...

    @abstractmethod
    def send_message(self, reservation_id: int, subject: str, body: str) -> None:
        """Send a message to the guest on a reservation."""
        ...

    @abstractmethod
    def get_active_reservations(
        self,
        apartment_id: int,
        arrival_from: str,
        arrival_to: str,
    ) -> list[ActiveReservation]:
        """Return reservations arriving between arrival_from and arrival_to (YYYY-MM-DD)."""
        ...

    @abstractmethod
    def get_threads(self, page_number: int = 1) -> ThreadPage:
        """Return a page of threads sorted by most-recent-activity descending."""
        ...

    @abstractmethod
    def get_reservation(self, reservation_id: int) -> ReservationInfo | None:
        """Return reservation metadata, or None if not found."""
        ...
