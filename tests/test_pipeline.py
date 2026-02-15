"""
Full pipeline tests using all simulators.

No network, no credentials, no LLM API calls.
The test exercises the complete flow end-to-end.
"""

import pytest

from src.adapters.memory_simulator import InMemoryRequestMemory
from src.adapters.simulator_intent import SimulatorIntentClassifier
from src.adapters.simulator_response import (
    SimulatorGuestAcknowledger,
    SimulatorReplyComposer,
    SimulatorResponseParser,
)
from src.adapters.simulator_smoobu import SimulatorSmoobuGateway
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
def smoobu():
    return SimulatorSmoobuGateway()


@pytest.fixture
def cleaner():
    return ConsoleCleanerNotifier()


@pytest.fixture
def memory():
    return InMemoryRequestMemory()


@pytest.fixture
def pipeline(smoobu, cleaner, memory):
    cfg = PipelineConfig(
        smoobu=smoobu,
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
async def test_early_checkin_triggers_cleaner_query(pipeline, cleaner, smoobu):
    result = await pipeline.process_message(
        RESERVATION_ID,
        "Bonjour, serait-il possible d'accéder plus tôt à l'appartement, vers 12h ?",
        _ctx(),
    )
    assert result.action == "cleaner_queried"
    # Cleaner notifier received the query
    responses = await cleaner.poll_responses()
    assert responses == []  # no reply yet
    # An acknowledgment was sent to the guest via Smoobu
    messages = smoobu.get_messages(RESERVATION_ID)
    assert len(messages) == 1
    ack_body = messages[0].body.lower()
    assert "possible" in ack_body or "demande" in ack_body


@pytest.mark.asyncio
async def test_same_intent_not_processed_twice(pipeline):
    msg = "J'aimerais arriver avant 15h, vers 12h si possible."
    await pipeline.process_message(RESERVATION_ID, msg, _ctx())
    result2 = await pipeline.process_message(RESERVATION_ID, msg, _ctx())
    assert result2.action == "already_processed"


@pytest.mark.asyncio
async def test_early_and_late_are_independent(pipeline):
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
    assert r1.action == "cleaner_queried"
    assert r2.action == "cleaner_queried"


@pytest.mark.asyncio
async def test_missing_time_triggers_followup(pipeline, smoobu):
    result = await pipeline.process_message(
        RESERVATION_ID,
        "Bonjour, serait-il possible d'accéder plus tôt à l'appartement ?",
        _ctx(),
    )
    assert result.action == "followup_sent"
    # A follow-up question was sent to the guest via Smoobu
    messages = smoobu.get_messages(RESERVATION_ID)
    assert len(messages) == 1
    assert "heure" in messages[0].body.lower() or "?" in messages[0].body


# ---------------------------------------------------------------------------
# Cleaner response processing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_yes_cleaner_response_replied_to_guest(pipeline, cleaner):
    # First, trigger the cleaner query
    await pipeline.process_message(
        RESERVATION_ID,
        "Puis-je arriver avant 15h, vers 12h ?",
        _ctx(),
    )

    # Cleaner replies yes
    cleaner.simulate_response("any-id", "Oui, pas de problème !")

    results = await pipeline.process_cleaner_responses()
    assert len(results) == 1
    assert results[0].action == "replied_to_guest"


@pytest.mark.asyncio
async def test_unclear_cleaner_response_escalated(pipeline, cleaner):
    await pipeline.process_message(
        RESERVATION_ID,
        "Puis-je arriver avant 15h, vers 12h ?",
        _ctx(),
    )

    cleaner.simulate_response("any-id", "Je verrai...")

    results = await pipeline.process_cleaner_responses()
    assert len(results) == 1
    assert results[0].action == "escalated_to_owner"
