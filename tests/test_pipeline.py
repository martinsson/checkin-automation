"""
Full pipeline tests using all simulators.

No network, no credentials, no LLM API calls.
The test exercises the complete flow end-to-end.
Everything is draft-based — nothing is sent directly.
"""

import pytest

from src.adapters.sqlite_memory import SqliteRequestMemory
from src.adapters.simulator_intent import SimulatorIntentClassifier
from src.adapters.simulator_response import (
    SimulatorGuestAcknowledger,
    SimulatorReplyComposer,
    SimulatorResponseParser,
)
from src.communication.console_notifier import ConsoleCleanerNotifier
from src.domain.intent import ConversationContext
from src.pipeline import Pipeline, PipelineConfig


RESERVATION_ID = 42


def _ctx():
    return ConversationContext(
        reservation_id=RESERVATION_ID,
        guest_name="Sophie Martin",
        property_name="Le Matisse",
        default_checkin_time="15:00",
        default_checkout_time="11:00",
        arrival_date="2026-04-01",
        departure_date="2026-04-05",
    )


@pytest.fixture
def cleaner():
    return ConsoleCleanerNotifier()


@pytest.fixture
def memory():
    return SqliteRequestMemory(":memory:")


@pytest.fixture
def pipeline(cleaner, memory):
    cfg = PipelineConfig(
        cleaner=cleaner,
        classifier=SimulatorIntentClassifier(),
        acknowledger=SimulatorGuestAcknowledger(),
        parser=SimulatorResponseParser(),
        composer=SimulatorReplyComposer(),
        memory=memory,
    )
    return Pipeline(cfg)


# ---------------------------------------------------------------------------
# Intent classification and routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_other_intent_is_ignored(pipeline):
    result = await pipeline.process_message(
        RESERVATION_ID,
        "Bonjour, quel est le code Wifi ?",
        _ctx(),
    )
    assert result.action == "ignored"


@pytest.mark.asyncio
async def test_early_checkin_creates_drafts(pipeline, memory):
    result = await pipeline.process_message(
        RESERVATION_ID,
        "Bonjour, serait-il possible d'accéder plus tôt à l'appartement, vers 12h ?",
        _ctx(),
    )
    assert result.action == "drafts_created"
    assert result.request_id

    # Two drafts saved: acknowledgment + cleaner_query
    drafts = await memory.get_pending_drafts()
    assert len(drafts) == 2
    steps = [d.step for d in drafts]
    assert "acknowledgment" in steps
    assert "cleaner_query" in steps

    # Acknowledgment draft body is non-empty
    ack_draft = next(d for d in drafts if d.step == "acknowledgment")
    assert len(ack_draft.draft_body) > 30

    # Request is tracked in memory
    req = await memory.get_request(result.request_id)
    assert req is not None
    assert req.status == "pending_acknowledgment"


@pytest.mark.asyncio
async def test_same_intent_not_processed_twice(pipeline):
    msg = "J'aimerais arriver avant 15h, vers 12h si possible."
    await pipeline.process_message(RESERVATION_ID, msg, _ctx())
    result2 = await pipeline.process_message(RESERVATION_ID, msg, _ctx())
    assert result2.action == "already_processed"


@pytest.mark.asyncio
async def test_early_and_late_are_independent(pipeline, memory):
    r1 = await pipeline.process_message(
        RESERVATION_ID,
        "Puis-je arriver avant 15h, vers 12h ?",
        _ctx(),
    )
    r2 = await pipeline.process_message(
        RESERVATION_ID,
        "Puis-je partir tard le dernier jour, vers 13h ?",
        _ctx(),
    )
    assert r1.action == "drafts_created"
    assert r2.action == "drafts_created"

    # 4 drafts total: 2 per request
    drafts = await memory.get_pending_drafts()
    assert len(drafts) == 4


@pytest.mark.asyncio
async def test_missing_time_drafts_followup(pipeline, memory):
    result = await pipeline.process_message(
        RESERVATION_ID,
        "Bonjour, serait-il possible d'accéder plus tôt à l'appartement ?",
        _ctx(),
    )
    assert result.action == "followup_drafted"

    # A follow-up draft was saved
    drafts = await memory.get_pending_drafts()
    assert len(drafts) == 1
    assert drafts[0].step == "followup"
    assert "heure" in drafts[0].draft_body.lower() or "?" in drafts[0].draft_body


# ---------------------------------------------------------------------------
# Cleaner response processing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cleaner_yes_creates_reply_draft(pipeline, memory, cleaner):
    # First, trigger the pipeline to create drafts
    result = await pipeline.process_message(
        RESERVATION_ID,
        "Puis-je arriver avant 15h, vers 12h ?",
        _ctx(),
    )

    # Simulate cleaner responding yes
    cleaner.simulate_response(result.request_id, "Oui, pas de problème !")

    results = await pipeline.process_cleaner_responses()
    assert len(results) == 1
    assert results[0].action == "reply_drafted"

    # Reply draft saved in memory (3 total: ack + cleaner_query + guest_reply)
    drafts = await memory.get_pending_drafts()
    assert len(drafts) == 3
    reply_draft = next(d for d in drafts if d.step == "guest_reply")
    assert len(reply_draft.draft_body) > 20


@pytest.mark.asyncio
async def test_cleaner_unclear_creates_reply_draft(pipeline, memory, cleaner):
    result = await pipeline.process_message(
        RESERVATION_ID,
        "Puis-je arriver avant 15h, vers 12h ?",
        _ctx(),
    )

    cleaner.simulate_response(result.request_id, "Je verrai...")

    results = await pipeline.process_cleaner_responses()
    assert len(results) == 1
    # Even unclear responses get a draft — the owner decides what to do
    assert results[0].action == "reply_drafted"


# ---------------------------------------------------------------------------
# Owner review workflow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_owner_can_approve_draft(pipeline, memory):
    result = await pipeline.process_message(
        RESERVATION_ID,
        "Puis-je arriver avant 15h, vers 12h ?",
        _ctx(),
    )

    drafts = await memory.get_pending_drafts()
    ack_draft = next(d for d in drafts if d.step == "acknowledgment")

    await memory.review_draft(ack_draft.draft_id, "ok")

    # Only 1 pending draft left (cleaner_query)
    remaining = await memory.get_pending_drafts()
    assert len(remaining) == 1
    assert remaining[0].step == "cleaner_query"


@pytest.mark.asyncio
async def test_owner_can_reject_with_correction(pipeline, memory):
    result = await pipeline.process_message(
        RESERVATION_ID,
        "Puis-je arriver avant 15h, vers 12h ?",
        _ctx(),
    )

    drafts = await memory.get_pending_drafts()
    ack_draft = next(d for d in drafts if d.step == "acknowledgment")

    await memory.review_draft(
        ack_draft.draft_id,
        "nok",
        actual_message_sent="My own version of the message",
        owner_comment="Too formal for this guest",
    )

    reviewed = await memory.get_draft(ack_draft.draft_id)
    assert reviewed.verdict == "nok"
    assert reviewed.actual_message_sent == "My own version of the message"
    assert reviewed.owner_comment == "Too formal for this guest"
