"""
Contract + simulator-specific tests for the thread-based Smoobu methods.
"""

from datetime import date, timedelta

from src.adapters.ports import ActiveReservation
from src.adapters.simulator_smoobu import SimulatorSmoobuGateway
from tests.contracts.smoobu_gateway_contract import SmoobuGatewayContract


# ---------------------------------------------------------------------------
# Contract: run full gateway contract against the simulator
# ---------------------------------------------------------------------------


class TestSimulatorThreadsContract(SmoobuGatewayContract):

    def create_gateway(self):
        return SimulatorSmoobuGateway()

    def get_test_reservation_id(self):
        return 12345

    # Override: real gateway test needs a real reservation_id to get metadata.
    # Simulator returns None for unknown IDs, which satisfies the contract.
    def test_get_reservation_unknown_returns_none(self):
        gw = self.create_gateway()
        assert gw.get_reservation(99999) is None


# ---------------------------------------------------------------------------
# Simulator-specific tests
# ---------------------------------------------------------------------------


def _future_res(reservation_id: int, days_ahead: int = 3) -> ActiveReservation:
    arrival = (date.today() + timedelta(days=days_ahead)).isoformat()
    departure = (date.today() + timedelta(days=days_ahead + 4)).isoformat()
    return ActiveReservation(
        reservation_id=reservation_id,
        guest_name=f"Guest {reservation_id}",
        arrival=arrival,
        departure=departure,
        apartment_id=42,
    )


def test_get_threads_returns_injected_reservations():
    gw = SimulatorSmoobuGateway()
    gw.inject_active_reservation(_future_res(1))
    gw.inject_guest_message(1, "Early check-in?", "Puis-je arriver avant 15h ?")

    page = gw.get_threads(page_number=1)
    assert len(page.threads) == 1
    assert page.threads[0].reservation_id == 1


def test_get_threads_sorted_most_recent_first():
    gw = SimulatorSmoobuGateway()
    gw.inject_active_reservation(_future_res(1))
    gw.inject_active_reservation(_future_res(2))

    gw.inject_guest_message(1, "Msg", "First message")
    gw.inject_guest_message(2, "Msg", "Second message — more recent (higher message_id)")

    page = gw.get_threads(page_number=1)
    assert len(page.threads) == 2
    # Reservation 2 has a higher message_id → more recent → first
    assert page.threads[0].reservation_id == 2
    assert page.threads[1].reservation_id == 1


def test_get_threads_empty_when_no_messages():
    gw = SimulatorSmoobuGateway()
    gw.inject_active_reservation(_future_res(1))
    # No messages injected

    page = gw.get_threads(page_number=1)
    assert page.threads == []
    assert page.has_more is False


def test_get_reservation_returns_injected_metadata():
    gw = SimulatorSmoobuGateway()
    res = _future_res(99)
    gw.inject_active_reservation(res)

    info = gw.get_reservation(99)
    assert info is not None
    assert info.reservation_id == 99
    assert info.arrival == res.arrival
    assert info.departure == res.departure
    assert info.guest_name == res.guest_name


def test_get_messages_type_field_guest():
    gw = SimulatorSmoobuGateway()
    gw.inject_guest_message(1, "Hi", "Bonjour !", type=1)
    messages = gw.get_messages(1)
    assert messages[0].type == 1


def test_get_messages_type_field_host():
    gw = SimulatorSmoobuGateway()
    gw.inject_guest_message(1, "Reply", "Bonjour !", type=2)
    messages = gw.get_messages(1)
    assert messages[0].type == 2


def test_send_message_adds_type2():
    """send_message() should create a type=2 (host) message."""
    gw = SimulatorSmoobuGateway()
    gw.send_message(1, "Welcome", "Bienvenue !")
    messages = gw.get_messages(1)
    assert len(messages) == 1
    assert messages[0].type == 2
