"""
Adapter contract for SmoobuGateway.

Any implementation of SmoobuGateway (real HTTP client, in-memory simulator, ...)
must pass these tests.  Subclass this and provide create_gateway() and
get_test_reservation_id() to run the contract against your adapter.
"""

import uuid
from abc import ABC, abstractmethod

from src.adapters.ports import SmoobuGateway


class SmoobuGatewayContract(ABC):
    """Contract tests that every SmoobuGateway implementation must satisfy."""

    @abstractmethod
    def create_gateway(self) -> SmoobuGateway:
        """Return a fresh instance of the adapter under test."""
        ...

    @abstractmethod
    def get_test_reservation_id(self) -> int:
        """Return a reservation ID usable for testing."""
        ...

    def test_get_messages_returns_list(self):
        gw = self.create_gateway()
        reservation_id = self.get_test_reservation_id()
        messages = gw.get_messages(reservation_id)
        assert isinstance(messages, list)

    def test_send_then_read_contains_message(self):
        gw = self.create_gateway()
        reservation_id = self.get_test_reservation_id()
        tag = uuid.uuid4().hex[:8]

        gw.send_message(reservation_id, f"Contract test {tag}", f"Body {tag}")
        messages = gw.get_messages(reservation_id)

        found = any(tag in m.body for m in messages)
        assert found, (
            f"Sent message with tag {tag!r} not found in "
            f"{len(messages)} messages"
        )
