"""
Full pipeline tests using all simulators.

No network, no credentials, no LLM API calls.
Tests exercise the complete flow end-to-end via shell handlers.
Everything is draft-based — nothing is sent directly.
"""

import pytest

from src.adapters.sqlite_memory import SqliteRequestMemory
from src.simulators.intent import SimulatorIntentClassifier
from src.simulators.response import (
    SimulatorGuestAcknowledger,
    SimulatorReplyComposer,
    SimulatorResponseParser,
)
from src.simulators.cleaner import ConsoleCleanerNotifier
from src.simulators.smoobu import SimulatorSmoobuGateway
from src.ports.intent import ConversationContext
from src.ports.memory import RequestStatus
from src.shell.handlers import guest_request, cleaner_response, draft_dispatch


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


async def _handle(msg, memory, classifier, acknowledger, message_id):
    return await guest_request.handle(
        reservation_id=RESERVATION_ID,
        message=msg,
        context=_ctx(),
        message_id=message_id,
        memory=memory,
        classifier=classifier,
        acknowledger=acknowledger,
    )


# ---------------------------------------------------------------------------
# Intent classification and routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_other_intent_is_ignored(memory, classifier, acknowledger):
    result = await _handle(
        "Bonjour, quel est le code Wifi ?",
        memory, classifier, acknowledger, message_id=10,
    )
    assert result.action == "ignored"


@pytest.mark.asyncio
async def test_early_checkin_creates_drafts(memory, classifier, acknowledger):
    result = await _handle(
        "Bonjour, serait-il possible d'accéder plus tôt à l'appartement, vers 12h ?",
        memory, classifier, acknowledger, message_id=20,
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
    assert req.status == RequestStatus.pending_ack


@pytest.mark.asyncio
async def test_same_intent_not_processed_twice(memory, classifier, acknowledger):
    msg = "J'aimerais arriver avant 15h, vers 12h si possible."
    await _handle(msg, memory, classifier, acknowledger, message_id=30)
    result2 = await _handle(msg, memory, classifier, acknowledger, message_id=31)
    assert result2.action == "already_processed"


@pytest.mark.asyncio
async def test_early_and_late_are_independent(memory, classifier, acknowledger):
    r1 = await _handle(
        "Puis-je arriver avant 15h, vers 12h ?",
        memory, classifier, acknowledger, message_id=40,
    )
    r2 = await _handle(
        "Puis-je partir tard le dernier jour, vers 13h ?",
        memory, classifier, acknowledger, message_id=41,
    )
    assert r1.action == "drafts_created"
    assert r2.action == "drafts_created"

    # 4 drafts total: 2 per request
    drafts = await memory.get_pending_drafts()
    assert len(drafts) == 4


@pytest.mark.asyncio
async def test_missing_time_still_creates_drafts(memory, classifier, acknowledger):
    """When no time is extracted, we still create ack + cleaner_query drafts."""
    result = await _handle(
        "Bonjour, serait-il possible d'accéder plus tôt à l'appartement ?",
        memory, classifier, acknowledger, message_id=50,
    )
    assert result.action == "drafts_created"

    drafts = await memory.get_pending_drafts()
    assert len(drafts) == 2
    steps = [d.step for d in drafts]
    assert "acknowledgment" in steps
    assert "cleaner_query" in steps


# ---------------------------------------------------------------------------
# Cleaner response processing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cleaner_yes_creates_reply_draft(memory, classifier, acknowledger, parser, composer, cleaner):
    result = await _handle(
        "Puis-je arriver avant 15h, vers 12h ?",
        memory, classifier, acknowledger, message_id=60,
    )

    # Simulate cleaner responding yes
    cleaner.simulate_response(result.request_id, "Oui, pas de problème !")

    responses = await cleaner.poll_responses()
    results = []
    for resp in responses:
        r = await cleaner_response.handle(
            resp, memory=memory, parser=parser, composer=composer,
        )
        results.append(r)

    assert len(results) == 1
    assert results[0].action == "reply_drafted"

    # Reply draft saved in memory (3 total: ack + cleaner_query + guest_reply)
    drafts = await memory.get_pending_drafts()
    assert len(drafts) == 3
    reply_draft = next(d for d in drafts if d.step == "guest_reply")
    assert len(reply_draft.draft_body) > 20


@pytest.mark.asyncio
async def test_cleaner_unclear_creates_reply_draft(memory, classifier, acknowledger, parser, composer, cleaner):
    result = await _handle(
        "Puis-je arriver avant 15h, vers 12h ?",
        memory, classifier, acknowledger, message_id=70,
    )

    cleaner.simulate_response(result.request_id, "Je verrai...")

    responses = await cleaner.poll_responses()
    results = []
    for resp in responses:
        r = await cleaner_response.handle(
            resp, memory=memory, parser=parser, composer=composer,
        )
        results.append(r)

    assert len(results) == 1
    assert results[0].action == "reply_drafted"


# ---------------------------------------------------------------------------
# Owner review workflow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_owner_can_approve_draft(memory, classifier, acknowledger):
    await _handle(
        "Puis-je arriver avant 15h, vers 12h ?",
        memory, classifier, acknowledger, message_id=80,
    )

    drafts = await memory.get_pending_drafts()
    ack_draft = next(d for d in drafts if d.step == "acknowledgment")

    await memory.review_draft(ack_draft.draft_id, "ok")

    remaining = await memory.get_pending_drafts()
    assert len(remaining) == 1
    assert remaining[0].step == "cleaner_query"


@pytest.mark.asyncio
async def test_owner_can_reject_with_correction(memory, classifier, acknowledger):
    await _handle(
        "Puis-je arriver avant 15h, vers 12h ?",
        memory, classifier, acknowledger, message_id=90,
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


# ---------------------------------------------------------------------------
# Message-level dedup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_same_message_id_not_classified_twice(memory, acknowledger):
    """Same message_id on two calls → second call skips AI and returns already_processed."""
    classify_calls = []

    class CountingClassifier(SimulatorIntentClassifier):
        async def classify(self, message, context):
            classify_calls.append(message)
            return await super().classify(message, context)

    counting = CountingClassifier()

    msg = "Puis-je arriver avant 15h, vers 12h ?"
    r1 = await _handle(msg, memory, counting, acknowledger, message_id=100)
    r2 = await _handle(msg, memory, counting, acknowledger, message_id=100)

    assert r1.action == "drafts_created"
    assert r2.action == "already_processed"
    assert r2.details == "message already seen"
    assert len(classify_calls) == 1  # classifier called only once


# ---------------------------------------------------------------------------
# Status transitions (task 6.4)
# ---------------------------------------------------------------------------


@pytest.fixture
def smoobu():
    return SimulatorSmoobuGateway()


@pytest.mark.asyncio
async def test_status_pending_ack_to_pending_cleaner(memory, classifier, acknowledger, smoobu, cleaner):
    """After both ack + cleaner_query are reviewed and dispatched, status → pending_cleaner."""
    result = await _handle(
        "Puis-je arriver avant 15h, vers 12h ?",
        memory, classifier, acknowledger, message_id=200,
    )
    req = await memory.get_request(result.request_id)
    assert req.status == RequestStatus.pending_ack

    # Review both drafts as ok
    drafts = await memory.get_pending_drafts()
    for d in drafts:
        await memory.review_draft(d.draft_id, "ok")

    # Dispatch reviewed drafts
    await draft_dispatch.run(memory=memory, smoobu=smoobu, cleaner=cleaner)

    req = await memory.get_request(result.request_id)
    assert req.status == RequestStatus.pending_cleaner


@pytest.mark.asyncio
async def test_status_pending_reply_to_done(memory, classifier, acknowledger, smoobu, cleaner, parser, composer):
    """After guest_reply is dispatched, status → done."""
    result = await _handle(
        "Puis-je arriver avant 15h, vers 12h ?",
        memory, classifier, acknowledger, message_id=210,
    )

    # Review + dispatch initial drafts
    drafts = await memory.get_pending_drafts()
    for d in drafts:
        await memory.review_draft(d.draft_id, "ok")
    await draft_dispatch.run(memory=memory, smoobu=smoobu, cleaner=cleaner)

    # Simulate cleaner reply → creates guest_reply draft
    cleaner.simulate_response(result.request_id, "Oui, pas de problème !")
    responses = await cleaner.poll_responses()
    for resp in responses:
        await cleaner_response.handle(resp, memory=memory, parser=parser, composer=composer)

    # Manually set status to pending_reply (as cleaner_response handler does)
    req = await memory.get_request(result.request_id)
    assert req.status == RequestStatus.pending_reply

    # Review + dispatch guest_reply
    pending = await memory.get_pending_drafts()
    reply_draft = next(d for d in pending if d.step == "guest_reply")
    await memory.review_draft(reply_draft.draft_id, "ok")
    await draft_dispatch.run(memory=memory, smoobu=smoobu, cleaner=cleaner)

    req = await memory.get_request(result.request_id)
    assert req.status == RequestStatus.done


# ---------------------------------------------------------------------------
# Delete request and seen message (task 6.5)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_seen_message(memory, classifier, acknowledger):
    """delete_seen_message clears the dedup flag so re-classification can happen."""
    msg = "Puis-je arriver avant 15h, vers 12h ?"
    await _handle(msg, memory, classifier, acknowledger, message_id=300)

    assert await memory.has_message_been_seen(300)
    await memory.delete_seen_message(300)
    assert not await memory.has_message_been_seen(300)


@pytest.mark.asyncio
async def test_delete_request_removes_request_and_drafts(memory, classifier, acknowledger):
    """delete_request removes the request row and all associated drafts."""
    result = await _handle(
        "Puis-je arriver avant 15h, vers 12h ?",
        memory, classifier, acknowledger, message_id=310,
    )
    request_id = result.request_id

    drafts_before = await memory.get_drafts_for_request(request_id)
    assert len(drafts_before) == 2

    await memory.delete_request(request_id)

    assert await memory.get_request(request_id) is None
    assert await memory.get_drafts_for_request(request_id) == []
