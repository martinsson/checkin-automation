from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GuestMessage:
    """A message from a Smoobu reservation conversation."""

    message_id: int
    subject: str
    body: str


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
