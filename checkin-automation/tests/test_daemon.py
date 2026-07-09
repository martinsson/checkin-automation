"""
Daemon behaviour tests for poll_cycle() and the guest message poller.

Uses simulators only — no network, no credentials.
Covers: type-1 filtering, thread-based scanning, cache behaviour,
        cutoff pagination, error isolation, and cleaner-response polling.
"""

import sys
import os
from datetime import date, timedelta, datetime, timezone
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ports.smoobu import ActiveReservation
from src.simulators.intent import SimulatorIntentClassifier
from src.simulators.reservation_cache import InMemoryReservationCache
from src.simulators.response import (
    SimulatorGuestAcknowledger,
    SimulatorReplyComposer,
    SimulatorResponseParser,
)
from src.simulators.smoobu import SimulatorSmoobuGateway
from src.adapters.sqlite_memory import SqliteRequestMemory
from src.simulators.cleaner import ConsoleCleanerNotifier

from src.shell.main_cycle import poll_cycle


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
def memory():
    return SqliteRequestMemory(":memory:")


@pytest.fixture
def classifier():
    return SimulatorIntentClassifier()


@pytest.fixture
def acknowledger():
    return SimulatorGuestAcknowledger()


@pytest.fixture
def parser():
    return SimulatorResponseParser()


@pytest.fixture
def composer():
    return SimulatorReplyComposer()


async def _poll(smoobu, memory, cache, classifier, acknowledger, parser, composer, cleaner,
                cutoff_days=CUTOFF_DAYS):
    await poll_cycle(
        smoobu=smoobu, memory=memory, cache=cache,
        classifier=classifier, acknowledger=acknowledger,
        parser=parser, composer=composer, cleaner=cleaner,
        cleaner_name="TestCleaner", threads_cutoff_days=cutoff_days,
    )


# ---------------------------------------------------------------------------
# Type-1 filtering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_only_guest_messages_type1_processed(smoobu, memory, cache, classifier, acknowledger, parser, composer, cleaner):
    """poll_cycle must skip host messages (type=2)."""
    res = _make_reservation(1)
    smoobu.inject_active_reservation(res)
    smoobu.inject_guest_message(1, "Host reply", "Bonjour, bienvenue !", type=2)

    await _poll(smoobu, memory, cache, classifier, acknowledger, parser, composer, cleaner)

    drafts = await memory.get_pending_drafts()
    assert drafts == [], "Host-only messages must not trigger pipeline"


@pytest.mark.asyncio
async def test_only_last_guest_message_processed(smoobu, memory, cache, classifier, acknowledger, parser, composer, cleaner):
    """poll_cycle passes only the latest type=1 message to the handler."""
    res = _make_reservation(1)
    smoobu.inject_active_reservation(res)
    smoobu.inject_guest_message(1, "Early check-in?", "Puis-je arriver avant 15h, vers 12h ?")
    smoobu.inject_guest_message(1, "Another", "Puis-je partir tard, vers 13h ?")

    await _poll(smoobu, memory, cache, classifier, acknowledger, parser, composer, cleaner)

    drafts = await memory.get_pending_drafts()
    intents = {d.intent for d in drafts}
    assert "late_checkout" in intents


@pytest.mark.asyncio
async def test_reservation_with_no_messages_skipped(smoobu, memory, cache, classifier, acknowledger, parser, composer, cleaner):
    """poll_cycle skips reservations that have no messages."""
    res = _make_reservation(2)
    smoobu.inject_active_reservation(res)

    await _poll(smoobu, memory, cache, classifier, acknowledger, parser, composer, cleaner)

    drafts = await memory.get_pending_drafts()
    assert drafts == []


# ---------------------------------------------------------------------------
# Reservation cache behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_hit_avoids_get_reservation_call(smoobu, memory, classifier, acknowledger, parser, composer, cleaner):
    """If info is cached, get_reservation() must not be called."""
    from src.ports.smoobu import ReservationInfo

    res = _make_reservation(5)
    smoobu.inject_active_reservation(res)
    smoobu.inject_guest_message(5, "Late out", "Puis-je partir tard, vers 13h ?")

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

    await _poll(smoobu, memory, cache, classifier, acknowledger, parser, composer, cleaner)

    assert 5 not in get_reservation_calls, "get_reservation() must not be called on cache hit"


@pytest.mark.asyncio
async def test_cache_miss_stores_fetched_reservation(smoobu, memory, classifier, acknowledger, parser, composer, cleaner):
    """On cache miss, reservation info is fetched and stored in the cache."""
    res = _make_reservation(6)
    smoobu.inject_active_reservation(res)
    smoobu.inject_guest_message(6, "Late out", "Puis-je partir tard, vers 13h ?")

    cache = InMemoryReservationCache()
    await _poll(smoobu, memory, cache, classifier, acknowledger, parser, composer, cleaner)

    stored = cache.get(6)
    assert stored is not None, "Reservation info should be stored after cache miss"
    assert stored.reservation_id == 6


# ---------------------------------------------------------------------------
# Cutoff pagination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_threads_beyond_cutoff_not_processed(smoobu, memory, cache, classifier, acknowledger, parser, composer, cleaner):
    """Reservations whose latest message is beyond the cutoff are skipped."""
    from src.ports.smoobu import Thread, ThreadPage

    res = _make_reservation(7)
    smoobu.inject_active_reservation(res)

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

    await _poll(smoobu, memory, cache, classifier, acknowledger, parser, composer, cleaner)

    drafts = await memory.get_pending_drafts()
    assert drafts == [], "Threads beyond cutoff must not be processed"


# ---------------------------------------------------------------------------
# Error isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_one_failing_reservation_does_not_abort_others(smoobu, memory, cache, classifier, acknowledger, parser, composer, cleaner):
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

    await _poll(smoobu, memory, cache, classifier, acknowledger, parser, composer, cleaner)

    drafts = await memory.get_pending_drafts()
    assert len(drafts) >= 1


# ---------------------------------------------------------------------------
# Cleaner response polling at end of cycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cleaner_responses_polled_each_cycle(smoobu, memory, cache, classifier, acknowledger, parser, composer, cleaner):
    """poll_cycle calls cleaner response handler at end of cycle."""
    res = _make_reservation(20)
    smoobu.inject_active_reservation(res)
    smoobu.inject_guest_message(20, "Early", "Puis-je arriver avant 15h, vers 12h ?")

    # First cycle: guest message processed, drafts created
    await _poll(smoobu, memory, cache, classifier, acknowledger, parser, composer, cleaner)

    drafts_after_first = await memory.get_pending_drafts()
    request_id = drafts_after_first[0].request_id

    # Simulate cleaner reply and run another cycle
    cleaner.simulate_response(request_id, "Oui, pas de problème !")
    await _poll(smoobu, memory, cache, classifier, acknowledger, parser, composer, cleaner)

    all_drafts = await memory.get_pending_drafts()
    steps = [d.step for d in all_drafts]
    assert "guest_reply" in steps
