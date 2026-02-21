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

    def test_get_messages_empty_reservation(self):
        gw = self.create_gateway()
        messages = gw.get_messages(reservation_id=999999999)
        assert isinstance(messages, list)
        assert messages == []

    def test_get_active_reservations_returns_list(self):
        gw = self.create_gateway()
        # Use a past date range — returns empty for both real and simulator
        result = gw.get_active_reservations(
            apartment_id=999999,
            arrival_from="2000-01-01",
            arrival_to="2000-01-02",
        )
        assert isinstance(result, list)

    def test_get_active_reservations_empty_for_out_of_range(self):
        gw = self.create_gateway()
        result = gw.get_active_reservations(
            apartment_id=999999,
            arrival_from="2000-01-01",
            arrival_to="2000-01-01",
        )
        assert result == []

    def test_get_threads_returns_thread_page(self):
        gw = self.create_gateway()
        page = gw.get_threads(page_number=1)
        assert isinstance(page.threads, list)
        assert isinstance(page.has_more, bool)

    def test_get_threads_sorted_by_recency(self):
        """Threads must be sorted most-recently-active first."""
        gw = self.create_gateway()
        page = gw.get_threads(page_number=1)
        if len(page.threads) < 2:
            return  # Not enough data to assert ordering
        timestamps = [t.latest_message_at for t in page.threads]
        assert timestamps == sorted(timestamps, reverse=True), (
            "Threads are not sorted by latest_message_at descending"
        )

    def test_get_threads_thread_fields_present(self):
        """Any returned thread must have required fields populated."""
        gw = self.create_gateway()
        page = gw.get_threads(page_number=1)
        for thread in page.threads:
            assert thread.reservation_id > 0, "Thread must have a reservation_id"
            assert thread.latest_message_at is not None

    def test_get_reservation_unknown_returns_none(self):
        gw = self.create_gateway()
        result = gw.get_reservation(reservation_id=999999999)
        assert result is None

    def test_get_messages_type_field_present(self):
        """Messages returned by get_messages must have a type field."""
        gw = self.create_gateway()
        reservation_id = self.get_test_reservation_id()
        gw.send_message(reservation_id, "Test", "Hello")
        messages = gw.get_messages(reservation_id)
        for msg in messages:
            assert hasattr(msg, "type"), "GuestMessage must have a type field"
            assert msg.type in (1, 2), f"type must be 1 or 2, got {msg.type}"
