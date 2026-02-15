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
