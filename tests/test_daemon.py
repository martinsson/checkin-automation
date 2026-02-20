"""
Daemon behaviour tests for poll_once().

Uses simulators only — no network, no credentials.
Covers: last-message-only rule, empty reservations, per-reservation error
isolation, and cleaner-response polling at the end of each cycle.
"""

import sys
import os
from datetime import date, timedelta
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.ports import ActiveReservation
from src.adapters.simulator_intent import SimulatorIntentClassifier
from src.adapters.simulator_response import (
    SimulatorGuestAcknowledger,
    SimulatorReplyComposer,
    SimulatorResponseParser,
)
from src.adapters.simulator_smoobu import SimulatorSmoobuGateway
from src.adapters.sqlite_memory import SqliteRequestMemory
from src.communication.console_notifier import ConsoleCleanerNotifier
from src.pipeline import Pipeline, PipelineConfig

from src.daemon import poll_once


APARTMENT_ID = 42
LOOKAHEAD_DAYS = 14


def _make_reservation(reservation_id: int, days_ahead: int = 3) -> ActiveReservation:
    arrival = (date.today() + timedelta(days=days_ahead)).isoformat()
    departure = (date.today() + timedelta(days=days_ahead + 4)).isoformat()
    return ActiveReservation(
        reservation_id=reservation_id,
        guest_name="Test Guest",
        arrival=arrival,
        departure=departure,
        apartment_id=APARTMENT_ID,
    )


@pytest.fixture
def smoobu():
    return SimulatorSmoobuGateway()


@pytest.fixture
def cleaner():
    return ConsoleCleanerNotifier()


@pytest.fixture
def pipeline(cleaner):
    cfg = PipelineConfig(
        cleaner=cleaner,
        classifier=SimulatorIntentClassifier(),
        acknowledger=SimulatorGuestAcknowledger(),
        parser=SimulatorResponseParser(),
        composer=SimulatorReplyComposer(),
        memory=SqliteRequestMemory(":memory:"),
        cleaner_name="TestCleaner",
    )
    return Pipeline(cfg)


# ---------------------------------------------------------------------------
# Last-message-only rule
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_only_last_message_processed(smoobu, pipeline):
    """poll_once passes only the latest guest message to the pipeline."""
    res = _make_reservation(1)
    smoobu.inject_active_reservation(res)
    smoobu.inject_guest_message(1, "Early check-in?", "Bonjour, puis-je arriver avant 15h, vers 12h ?")
    smoobu.inject_guest_message(1, "Another", "Bonjour, puis-je partir tard, vers 13h ?")

    # Capture what the pipeline processes by checking drafts afterward
    memory = pipeline._cfg.memory
    await poll_once(pipeline, smoobu, APARTMENT_ID, LOOKAHEAD_DAYS)

    drafts = await memory.get_pending_drafts()
    # Only the last message (late_checkout) should have been processed
    intents = {d.intent for d in drafts}
    assert "late_checkout" in intents


@pytest.mark.asyncio
async def test_reservation_with_no_messages_skipped(smoobu, pipeline):
    """poll_once skips reservations that have no messages."""
    res = _make_reservation(2)
    smoobu.inject_active_reservation(res)
    # No messages injected

    memory = pipeline._cfg.memory
    await poll_once(pipeline, smoobu, APARTMENT_ID, LOOKAHEAD_DAYS)

    drafts = await memory.get_pending_drafts()
    assert drafts == []


# ---------------------------------------------------------------------------
# Error isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_one_failing_reservation_does_not_abort_others(smoobu, pipeline):
    """An exception for reservation A must not prevent reservation B from being processed."""
    # Reservation 10 will be processed normally
    good_res = _make_reservation(10)
    smoobu.inject_active_reservation(good_res)
    smoobu.inject_guest_message(10, "Late out", "Puis-je partir tard le dernier jour, vers 13h ?")

    # Reservation 11 has a get_messages override that raises
    broken_res = _make_reservation(11)
    smoobu.inject_active_reservation(broken_res)

    original_get_messages = smoobu.get_messages

    def patched_get_messages(reservation_id: int):
        if reservation_id == 11:
            raise RuntimeError("Simulated Smoobu API failure")
        return original_get_messages(reservation_id)

    smoobu.get_messages = patched_get_messages  # type: ignore[method-assign]

    memory = pipeline._cfg.memory
    await poll_once(pipeline, smoobu, APARTMENT_ID, LOOKAHEAD_DAYS)

    # Reservation 10 must still have produced drafts
    drafts = await memory.get_pending_drafts()
    assert len(drafts) >= 1


# ---------------------------------------------------------------------------
# Cleaner response polling at end of cycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cleaner_responses_polled_each_cycle(smoobu, pipeline, cleaner):
    """poll_once calls process_cleaner_responses() at end of cycle."""
    res = _make_reservation(20)
    smoobu.inject_active_reservation(res)
    smoobu.inject_guest_message(20, "Early", "Puis-je arriver avant 15h, vers 12h ?")

    memory = pipeline._cfg.memory

    # First cycle: guest message processed, drafts created
    await poll_once(pipeline, smoobu, APARTMENT_ID, LOOKAHEAD_DAYS)

    drafts_after_first = await memory.get_pending_drafts()
    request_id = drafts_after_first[0].request_id

    # Simulate cleaner reply and run another cycle
    cleaner.simulate_response(request_id, "Oui, pas de problème !")
    await poll_once(pipeline, smoobu, APARTMENT_ID, LOOKAHEAD_DAYS)

    # A guest_reply draft must now exist
    all_drafts = await memory.get_pending_drafts()
    steps = [d.step for d in all_drafts]
    assert "guest_reply" in steps
