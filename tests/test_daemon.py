"""
Daemon behaviour tests for poll_once().

Uses simulators only — no network, no credentials.
Covers: type-1 filtering, thread-based scanning, cache behaviour,
        cutoff pagination, error isolation, and cleaner-response polling.
"""

import sys
import os
from datetime import date, timedelta, datetime, timezone
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.ports import ActiveReservation
from src.adapters.simulator_intent import SimulatorIntentClassifier
from src.adapters.simulator_reservation_cache import InMemoryReservationCache
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
CUTOFF_DAYS = 7


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
def cache():
    return InMemoryReservationCache()


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
# Type-1 filtering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_only_guest_messages_type1_processed(smoobu, pipeline, cache):
    """poll_once must skip host messages (type=2)."""
    res = _make_reservation(1)
    smoobu.inject_active_reservation(res)
    # Host message only
    smoobu.inject_guest_message(1, "Host reply", "Bonjour, bienvenue !", type=2)

    memory = pipeline._cfg.memory
    await poll_once(pipeline, smoobu, cache, CUTOFF_DAYS)

    drafts = await memory.get_pending_drafts()
    assert drafts == [], "Host-only messages must not trigger pipeline"


@pytest.mark.asyncio
async def test_only_last_guest_message_processed(smoobu, pipeline, cache):
    """poll_once passes only the latest type=1 message to the pipeline."""
    res = _make_reservation(1)
    smoobu.inject_active_reservation(res)
    smoobu.inject_guest_message(1, "Early check-in?", "Puis-je arriver avant 15h, vers 12h ?")
    smoobu.inject_guest_message(1, "Another", "Puis-je partir tard, vers 13h ?")

    memory = pipeline._cfg.memory
    await poll_once(pipeline, smoobu, cache, CUTOFF_DAYS)

    drafts = await memory.get_pending_drafts()
    # Only the last message (late_checkout) processed
    intents = {d.intent for d in drafts}
    assert "late_checkout" in intents


@pytest.mark.asyncio
async def test_reservation_with_no_messages_skipped(smoobu, pipeline, cache):
    """poll_once skips reservations that have no messages."""
    res = _make_reservation(2)
    smoobu.inject_active_reservation(res)
    # No messages injected

    memory = pipeline._cfg.memory
    await poll_once(pipeline, smoobu, cache, CUTOFF_DAYS)

    drafts = await memory.get_pending_drafts()
    assert drafts == []


# ---------------------------------------------------------------------------
# Reservation cache behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_hit_avoids_get_reservation_call(smoobu, pipeline):
    """If info is cached, get_reservation() must not be called."""
    from src.adapters.ports import ReservationInfo

    res = _make_reservation(5)
    smoobu.inject_active_reservation(res)
    smoobu.inject_guest_message(5, "Late out", "Puis-je partir tard, vers 13h ?")

    # Pre-populate cache so get_reservation() on the gateway should not be needed
    cache = InMemoryReservationCache()
    cache.store(5, ReservationInfo(
        reservation_id=5,
        guest_name="Cached Guest",
        apartment_name="Cached Apt",
        arrival=res.arrival,
        departure=res.departure,
    ))

    get_reservation_calls = []
    original = smoobu.get_reservation

    def patched(rid):
        get_reservation_calls.append(rid)
        return original(rid)

    smoobu.get_reservation = patched  # type: ignore[method-assign]

    await poll_once(pipeline, smoobu, cache, CUTOFF_DAYS)

    assert 5 not in get_reservation_calls, "get_reservation() must not be called on cache hit"


@pytest.mark.asyncio
async def test_cache_miss_stores_fetched_reservation(smoobu, pipeline):
    """On cache miss, reservation info is fetched and stored in the cache."""
    res = _make_reservation(6)
    smoobu.inject_active_reservation(res)
    smoobu.inject_guest_message(6, "Late out", "Puis-je partir tard, vers 13h ?")

    cache = InMemoryReservationCache()
    await poll_once(pipeline, smoobu, cache, CUTOFF_DAYS)

    stored = cache.get(6)
    assert stored is not None, "Reservation info should be stored after cache miss"
    assert stored.reservation_id == 6


# ---------------------------------------------------------------------------
# Cutoff pagination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_threads_beyond_cutoff_not_processed(smoobu, pipeline, cache):
    """Reservations whose latest message is beyond the cutoff are skipped."""
    from src.adapters.ports import Thread, ThreadPage

    res = _make_reservation(7)
    smoobu.inject_active_reservation(res)

    # Override get_threads to return an old thread (10 days ago > 7-day cutoff)
    old_time = datetime.now(timezone.utc) - timedelta(days=10)

    def fake_get_threads(page_number=1):
        return ThreadPage(
            threads=[Thread(
                reservation_id=7,
                guest_name="Guest",
                apartment_name="Apt",
                latest_message_at=old_time,
            )],
            has_more=False,
        )

    smoobu.get_threads = fake_get_threads  # type: ignore[method-assign]
    smoobu.inject_guest_message(7, "Late out", "Puis-je partir tard, vers 13h ?")

    memory = pipeline._cfg.memory
    await poll_once(pipeline, smoobu, cache, CUTOFF_DAYS)

    drafts = await memory.get_pending_drafts()
    assert drafts == [], "Threads beyond cutoff must not be processed"


# ---------------------------------------------------------------------------
# Error isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_one_failing_reservation_does_not_abort_others(smoobu, pipeline, cache):
    """An exception for reservation A must not prevent reservation B from being processed."""
    good_res = _make_reservation(10)
    smoobu.inject_active_reservation(good_res)
    smoobu.inject_guest_message(10, "Late out", "Puis-je partir tard le dernier jour, vers 13h ?")

    broken_res = _make_reservation(11)
    smoobu.inject_active_reservation(broken_res)
    smoobu.inject_guest_message(11, "Late out", "Puis-je partir tard ?")

    original_get_messages = smoobu.get_messages

    def patched_get_messages(reservation_id: int):
        if reservation_id == 11:
            raise RuntimeError("Simulated Smoobu API failure")
        return original_get_messages(reservation_id)

    smoobu.get_messages = patched_get_messages  # type: ignore[method-assign]

    memory = pipeline._cfg.memory
    await poll_once(pipeline, smoobu, cache, CUTOFF_DAYS)

    drafts = await memory.get_pending_drafts()
    assert len(drafts) >= 1


# ---------------------------------------------------------------------------
# Cleaner response polling at end of cycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cleaner_responses_polled_each_cycle(smoobu, pipeline, cache, cleaner):
    """poll_once calls process_cleaner_responses() at end of cycle."""
    res = _make_reservation(20)
    smoobu.inject_active_reservation(res)
    smoobu.inject_guest_message(20, "Early", "Puis-je arriver avant 15h, vers 12h ?")

    memory = pipeline._cfg.memory

    # First cycle: guest message processed, drafts created
    await poll_once(pipeline, smoobu, cache, CUTOFF_DAYS)

    drafts_after_first = await memory.get_pending_drafts()
    request_id = drafts_after_first[0].request_id

    # Simulate cleaner reply and run another cycle
    cleaner.simulate_response(request_id, "Oui, pas de problème !")
    await poll_once(pipeline, smoobu, cache, CUTOFF_DAYS)

    all_drafts = await memory.get_pending_drafts()
    steps = [d.step for d in all_drafts]
    assert "guest_reply" in steps
