"""
Roundtrip test: full message flow using simulators only.

No network, no credentials, no mocking framework. Uses:
- SimulatorSmoobuGateway  (in-memory fake for Smoobu)
- ConsoleCleanerNotifier  (in-memory fake for cleaner communication)

The test proves the orchestration wiring works:
1. Guest sends a message (injected into SimulatorSmoobuGateway)
2. Orchestrator reads it, forwards to cleaner
3. Cleaner replies (injected via ConsoleCleanerNotifier.simulate_response)
4. Orchestrator polls the response, sends reply to guest
5. We verify the reply appeared in SimulatorSmoobuGateway
"""

import pytest

from src.adapters.simulator_smoobu import SimulatorSmoobuGateway
from src.communication.console_notifier import ConsoleCleanerNotifier
from src.communication.ports import CleanerQuery


RESERVATION_ID = 99999
REQUEST_ID = "test-req-001"


# ---------------------------------------------------------------------------
# Minimal orchestrator — just enough to wire the two ports together.
# This will be replaced by the real processor in Phase 0, but the test
# shape stays the same.
# ---------------------------------------------------------------------------


class MessageForwarder:
    """
    Phase 0 walking-skeleton orchestrator.

    Reads a guest message from Smoobu, forwards it to the cleaner.
    Reads the cleaner's response, sends it back to the guest via Smoobu.
    """

    def __init__(
        self,
        smoobu: SimulatorSmoobuGateway,
        cleaner: ConsoleCleanerNotifier,
    ):
        self.smoobu = smoobu
        self.cleaner = cleaner

    async def forward_guest_to_cleaner(self, reservation_id: int) -> str | None:
        """Read latest guest message and send it to the cleaner."""
        messages = self.smoobu.get_messages(reservation_id)
        if not messages:
            return None

        latest = messages[-1]
        query = CleanerQuery(
            request_id=REQUEST_ID,
            cleaner_name="Marie",
            guest_name="Test Guest",
            property_name="Test Apartment",
            request_type="early_checkin",
            original_time="15:00",
            requested_time="12:00",
            date="2026-03-01",
            message=latest.body,
        )
        await self.cleaner.send_query(query)
        return REQUEST_ID

    async def forward_cleaner_to_guest(self, reservation_id: int) -> bool:
        """Poll cleaner responses and send reply to guest."""
        responses = await self.cleaner.poll_responses()
        if not responses:
            return False

        for response in responses:
            self.smoobu.send_message(
                reservation_id,
                subject="Re: Guest request",
                body=response.raw_text,
            )
        return True


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def smoobu():
    return SimulatorSmoobuGateway()


@pytest.fixture
def cleaner():
    return ConsoleCleanerNotifier()


@pytest.fixture
def forwarder(smoobu, cleaner):
    return MessageForwarder(smoobu=smoobu, cleaner=cleaner)


@pytest.mark.asyncio
async def test_guest_message_forwarded_to_cleaner(smoobu, cleaner, forwarder):
    """Guest message is read from Smoobu and forwarded to cleaner."""
    smoobu.inject_guest_message(
        RESERVATION_ID,
        subject="Check-in request",
        body="Can I check in at 12pm instead of 3pm?",
    )

    request_id = await forwarder.forward_guest_to_cleaner(RESERVATION_ID)

    assert request_id == REQUEST_ID
    # The cleaner notifier printed the message (console) and has no pending
    # responses yet — that's correct, the cleaner hasn't replied.
    responses = await cleaner.poll_responses()
    assert responses == []


@pytest.mark.asyncio
async def test_cleaner_response_forwarded_to_guest(smoobu, cleaner, forwarder):
    """Cleaner response is polled and sent back to guest via Smoobu."""
    cleaner.simulate_response(REQUEST_ID, "Yes, no problem!")

    forwarded = await forwarder.forward_cleaner_to_guest(RESERVATION_ID)

    assert forwarded is True
    assert len(smoobu.sent) == 1
    reservation_id, subject, body = smoobu.sent[0]
    assert reservation_id == RESERVATION_ID
    assert "Yes, no problem!" in body


@pytest.mark.asyncio
async def test_full_roundtrip(smoobu, cleaner, forwarder):
    """
    Full round-trip:
    1. Guest sends message
    2. Forwarded to cleaner
    3. Cleaner replies
    4. Reply sent back to guest
    """
    # Step 1: guest sends a message
    smoobu.inject_guest_message(
        RESERVATION_ID,
        subject="Early check-in",
        body="Can I check in at noon?",
    )

    # Step 2: orchestrator forwards to cleaner
    request_id = await forwarder.forward_guest_to_cleaner(RESERVATION_ID)
    assert request_id is not None

    # Step 3: cleaner replies
    cleaner.simulate_response(request_id, "Sure, that works!")

    # Step 4: orchestrator forwards reply to guest
    forwarded = await forwarder.forward_cleaner_to_guest(RESERVATION_ID)
    assert forwarded is True

    # Verify: the reply is now visible in Smoobu
    all_messages = smoobu.get_messages(RESERVATION_ID)
    assert len(all_messages) == 2  # original guest message + our reply
    assert "Sure, that works!" in all_messages[-1].body

    # Verify: exactly one outgoing message was sent
    assert len(smoobu.sent) == 1
