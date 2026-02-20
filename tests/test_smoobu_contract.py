"""
Adapter contract tests for SmoobuGateway — both simulator and real.

The same contract is verified against:
  - SimulatorSmoobuGateway  (always runs, no credentials needed)
  - SmoobuClient            (skipped if SMOOBU_API_KEY is not set)
"""

import os

import pytest

from src.adapters.simulator_smoobu import SimulatorSmoobuGateway
from src.adapters.smoobu_client import SmoobuClient

from tests.contracts.smoobu_gateway_contract import SmoobuGatewayContract

# ---------------------------------------------------------------------------
# Simulator — always runs
# ---------------------------------------------------------------------------


class TestSimulatorSmoobuContract(SmoobuGatewayContract):

    def create_gateway(self):
        return SimulatorSmoobuGateway()

    def get_test_reservation_id(self):
        return 12345

    def test_injected_reservation_returned_within_range(self):
        from src.adapters.ports import ActiveReservation
        gw = SimulatorSmoobuGateway()
        gw.inject_active_reservation(ActiveReservation(
            reservation_id=1,
            guest_name="Alice",
            arrival="2026-06-01",
            departure="2026-06-05",
            apartment_id=42,
        ))
        result = gw.get_active_reservations(42, "2026-05-31", "2026-06-02")
        assert len(result) == 1
        assert result[0].guest_name == "Alice"

    def test_reservation_outside_range_not_returned(self):
        from src.adapters.ports import ActiveReservation
        gw = SimulatorSmoobuGateway()
        gw.inject_active_reservation(ActiveReservation(
            reservation_id=1,
            guest_name="Alice",
            arrival="2026-06-10",
            departure="2026-06-12",
            apartment_id=42,
        ))
        result = gw.get_active_reservations(42, "2026-06-01", "2026-06-05")
        assert result == []

    def test_reservation_wrong_apartment_not_returned(self):
        from src.adapters.ports import ActiveReservation
        gw = SimulatorSmoobuGateway()
        gw.inject_active_reservation(ActiveReservation(
            reservation_id=1,
            guest_name="Alice",
            arrival="2026-06-01",
            departure="2026-06-05",
            apartment_id=99,
        ))
        result = gw.get_active_reservations(42, "2026-05-31", "2026-06-02")
        assert result == []


# ---------------------------------------------------------------------------
# Real Smoobu API — skipped without credentials
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("SMOOBU_API_KEY", "")
BOOKING_ID = os.environ.get("TEST_BOOKING_ID", "")

CREDS_AVAILABLE = bool(API_KEY) and bool(BOOKING_ID)


@pytest.mark.skipif(
    not CREDS_AVAILABLE,
    reason="SMOOBU_API_KEY or TEST_BOOKING_ID not set",
)
class TestSmoobuClientContract(SmoobuGatewayContract):

    def create_gateway(self):
        return SmoobuClient(api_key=API_KEY)

    def get_test_reservation_id(self):
        return int(BOOKING_ID)
