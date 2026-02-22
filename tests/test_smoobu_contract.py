"""
Adapter contract tests for SmoobuGateway.

The same contract (SmoobuGatewayContract) is run against every implementation:
  - SimulatorSmoobuGateway  (always runs, no credentials needed)
  - SmoobuClient            (skipped when SMOOBU_API_KEY is not set)

Each subclass provides create_gateway() returning a ready-to-use instance.
The simulator is pre-seeded so every contract test passes without skips.
"""

import os
from datetime import date, timedelta

import pytest

from src.adapters.ports import ActiveReservation
from src.adapters.simulator_smoobu import SimulatorSmoobuGateway
from src.adapters.smoobu_client import SmoobuClient
from tests.contracts.smoobu_gateway_contract import SmoobuGatewayContract


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


# ---------------------------------------------------------------------------
# Simulator — always runs
# ---------------------------------------------------------------------------

class TestSimulatorSmoobuContract(SmoobuGatewayContract):
    """
    Pre-seed two reservations with messages so every contract test passes.
    Reservation 101 is the primary test target; 102 ensures ordering tests
    have at least two threads to compare.
    """

    def create_gateway(self):
        gw = SimulatorSmoobuGateway()
        gw.inject_active_reservation(_future_res(101, days_ahead=2))
        gw.inject_active_reservation(_future_res(102, days_ahead=3))
        gw.inject_guest_message(101, "Hi", "Can we check in early?")
        gw.inject_guest_message(102, "Hi", "What time is check-out?")
        return gw

    def get_test_reservation_id(self):
        return 101

    def test_injected_reservation_returned_within_range(self):
        gw = self.create_gateway()
        result = gw.get_active_reservations(42, date.today().isoformat(),
                                            (date.today() + timedelta(days=10)).isoformat())
        assert any(r.reservation_id == 101 for r in result)

    def test_reservation_outside_range_not_returned(self):
        gw = SimulatorSmoobuGateway()
        gw.inject_active_reservation(_future_res(1, days_ahead=10))
        result = gw.get_active_reservations(42, date.today().isoformat(),
                                            (date.today() + timedelta(days=5)).isoformat())
        assert result == []

    def test_reservation_wrong_apartment_not_returned(self):
        gw = SimulatorSmoobuGateway()
        gw.inject_active_reservation(ActiveReservation(
            reservation_id=1, guest_name="Alice",
            arrival=date.today().isoformat(),
            departure=(date.today() + timedelta(days=3)).isoformat(),
            apartment_id=99,
        ))
        result = gw.get_active_reservations(42, date.today().isoformat(),
                                            (date.today() + timedelta(days=5)).isoformat())
        assert result == []


# ---------------------------------------------------------------------------
# Real Smoobu API — skipped without credentials
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("SMOOBU_API_KEY", "")
BOOKING_ID = os.environ.get("TEST_BOOKING_ID", "")
CREDS_AVAILABLE = bool(API_KEY) and bool(BOOKING_ID)


@pytest.mark.skipif(not CREDS_AVAILABLE, reason="SMOOBU_API_KEY or TEST_BOOKING_ID not set")
class TestSmoobuClientContract(SmoobuGatewayContract):

    def create_gateway(self):
        return SmoobuClient(api_key=API_KEY)

    def get_test_reservation_id(self):
        return int(BOOKING_ID)
