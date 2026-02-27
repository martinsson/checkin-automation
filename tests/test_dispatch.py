"""
Tests for dispatch_reviewed_drafts().

Uses simulators and in-memory SQLite — no network, no credentials.
"""

import sys
import os
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.adapters.sqlite_memory import SqliteRequestMemory
from src.adapters.simulator_smoobu import SimulatorSmoobuGateway
from src.adapters.ports import ActiveReservation
from src.communication.console_notifier import ConsoleCleanerNotifier
from src.daemon import dispatch_reviewed_drafts


@pytest.fixture
def memory():
    return SqliteRequestMemory(":memory:")


@pytest.fixture
def smoobu():
    gw = SimulatorSmoobuGateway()
    arrival = (date.today() + timedelta(days=3)).isoformat()
    departure = (date.today() + timedelta(days=7)).isoformat()
    gw.inject_active_reservation(ActiveReservation(
        reservation_id=100, guest_name="Test Guest",
        arrival=arrival, departure=departure, apartment_id=1,
    ))
    return gw


@pytest.fixture
def cleaner():
    return ConsoleCleanerNotifier()


async def _seed_draft(memory, *, step="acknowledgment", intent="early_checkin"):
    """Create a request + draft and return the draft_id."""
    await memory.save_request(
        100, intent, "req-1", "Can I check in early?",
        guest_name="Test Guest", property_name="Le Matisse",
        original_time="17:00", requested_time="12:00",
        relevant_date=(date.today() + timedelta(days=3)).isoformat(),
    )
    return await memory.save_draft("req-1", 100, intent, step, "Bonjour, your request is noted.")


# ---------------------------------------------------------------------------
# Approved drafts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approved_acknowledgment_sent_via_smoobu(memory, smoobu, cleaner):
    """Approved guest-channel draft sends via smoobu.send_message with draft_body."""
    draft_id = await _seed_draft(memory, step="acknowledgment")
    await memory.review_draft(draft_id, "ok")

    await dispatch_reviewed_drafts(memory, smoobu, cleaner)

    assert len(smoobu.sent) == 1
    res_id, subject, body = smoobu.sent[0]
    assert res_id == 100
    assert body == "Bonjour, your request is noted."

    draft = await memory.get_draft(draft_id)
    assert draft.sent_at is not None


@pytest.mark.asyncio
async def test_approved_cleaner_query_sent_via_cleaner(memory, smoobu, cleaner):
    """Approved cleaner_query draft sends via cleaner.send_query."""
    draft_id = await _seed_draft(memory, step="cleaner_query")
    await memory.review_draft(draft_id, "ok")

    await dispatch_reviewed_drafts(memory, smoobu, cleaner, cleaner_name="TestCleaner")

    assert "req-1" in cleaner._sent
    query = cleaner._sent["req-1"]
    assert query.guest_name == "Test Guest"
    assert query.property_name == "Le Matisse"
    assert query.cleaner_name == "TestCleaner"

    draft = await memory.get_draft(draft_id)
    assert draft.sent_at is not None


# ---------------------------------------------------------------------------
# Rejected drafts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rejected_with_correction_sends_actual_message(memory, smoobu, cleaner):
    """Rejected draft with actual_message_sent sends the correction text."""
    draft_id = await _seed_draft(memory, step="acknowledgment")
    await memory.review_draft(draft_id, "nok", actual_message_sent="Custom corrected text")

    await dispatch_reviewed_drafts(memory, smoobu, cleaner)

    assert len(smoobu.sent) == 1
    assert smoobu.sent[0][2] == "Custom corrected text"  # (res_id, subject, body)


@pytest.mark.asyncio
async def test_rejected_without_correction_skips_but_marks_sent(memory, smoobu, cleaner):
    """Rejected draft without actual_message_sent skips sending but marks sent_at."""
    draft_id = await _seed_draft(memory, step="acknowledgment")
    await memory.review_draft(draft_id, "nok")

    await dispatch_reviewed_drafts(memory, smoobu, cleaner)

    assert len(smoobu.sent) == 0
    draft = await memory.get_draft(draft_id)
    assert draft.sent_at is not None


# ---------------------------------------------------------------------------
# Error isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_error_does_not_block_other_drafts(memory, smoobu, cleaner):
    """If one draft fails to send, others still dispatch."""
    # First draft — will fail
    await memory.save_request(
        100, "early_checkin", "req-fail", "msg",
        guest_name="G", property_name="P",
        original_time="17:00", requested_time="12:00",
        relevant_date="2026-03-01",
    )
    d1 = await memory.save_draft("req-fail", 100, "early_checkin", "acknowledgment", "Draft 1")
    await memory.review_draft(d1, "ok")

    # Second draft — should succeed
    await memory.save_request(
        100, "late_checkout", "req-good", "msg",
        guest_name="G", property_name="P",
        original_time="11:00", requested_time="13:00",
        relevant_date="2026-03-05",
    )
    d2 = await memory.save_draft("req-good", 100, "late_checkout", "acknowledgment", "Draft 2")
    await memory.review_draft(d2, "ok")

    # Make send_message fail on first call
    call_count = 0
    original = smoobu.send_message

    def failing_send(reservation_id, subject, body):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Simulated send failure")
        return original(reservation_id, subject, body)

    smoobu.send_message = failing_send  # type: ignore[method-assign]

    await dispatch_reviewed_drafts(memory, smoobu, cleaner)

    # First draft NOT marked sent (will retry next cycle)
    draft1 = await memory.get_draft(d1)
    assert draft1.sent_at is None

    # Second draft WAS sent
    draft2 = await memory.get_draft(d2)
    assert draft2.sent_at is not None


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_already_sent_draft_not_redispatched(memory, smoobu, cleaner):
    """Drafts with sent_at set are not re-dispatched."""
    draft_id = await _seed_draft(memory, step="acknowledgment")
    await memory.review_draft(draft_id, "ok")

    # First dispatch
    await dispatch_reviewed_drafts(memory, smoobu, cleaner)
    assert len(smoobu.sent) == 1

    # Second dispatch — should not send again
    await dispatch_reviewed_drafts(memory, smoobu, cleaner)
    assert len(smoobu.sent) == 1
