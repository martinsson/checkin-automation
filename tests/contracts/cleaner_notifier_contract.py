"""
Adapter contract for CleanerNotifier.

Any implementation of CleanerNotifier (email, console, WhatsApp, ...)
must pass these tests.  Subclass this and provide the abstract methods
to run the contract against your adapter.
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod

import pytest

from src.communication.ports import CleanerNotifier, CleanerQuery


class CleanerNotifierContract(ABC):
    """Contract tests that every CleanerNotifier implementation must satisfy."""

    # Subclasses override these for slow channels (e.g. email).
    poll_max_seconds: int = 1
    poll_interval_seconds: float = 0
    pre_reply_delay: float = 0

    @abstractmethod
    def create_notifier(self) -> CleanerNotifier:
        """Return a fresh instance of the adapter under test."""
        ...

    @abstractmethod
    async def make_cleaner_reply(self, request_id: str, text: str) -> None:
        """Simulate the cleaner replying.

        For the console adapter this calls simulate_response().
        For the email adapter this sends a real email from the cleaner account.
        """
        ...

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _make_query(request_id: str) -> CleanerQuery:
        return CleanerQuery(
            request_id=request_id,
            cleaner_name="Test Cleaner",
            guest_name="Test Guest",
            property_name="Test Apartment",
            request_type="early_checkin",
            original_time="15:00",
            requested_time="12:00",
            date="2026-03-01",
            message=f"Can you finish by 12:00 on March 1st? [id: {request_id}]",
        )

    async def _poll_until_found(
        self, notifier: CleanerNotifier, request_id: str
    ) -> "CleanerQuery | None":
        """Poll for a response matching *request_id*, respecting class timing."""
        from src.communication.ports import CleanerResponse

        deadline = time.time() + self.poll_max_seconds
        while True:
            responses = await notifier.poll_responses()
            for r in responses:
                if r.request_id == request_id:
                    return r
            if time.time() >= deadline:
                return None
            await asyncio.sleep(self.poll_interval_seconds)

    # -- contract tests ------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_query_returns_tracking_id(self):
        notifier = self.create_notifier()
        query = self._make_query(f"contract-{uuid.uuid4().hex[:8]}")
        tracking_id = await notifier.send_query(query)
        assert tracking_id  # non-empty string

    @pytest.mark.asyncio
    async def test_roundtrip_send_reply_poll(self):
        notifier = self.create_notifier()
        request_id = f"contract-{uuid.uuid4().hex[:8]}"
        query = self._make_query(request_id)

        await notifier.send_query(query)

        if self.pre_reply_delay:
            await asyncio.sleep(self.pre_reply_delay)

        await self.make_cleaner_reply(request_id, "Yes, no problem!")

        matched = await self._poll_until_found(notifier, request_id)
        assert matched is not None, (
            f"No response with request_id={request_id!r} found "
            f"within {self.poll_max_seconds}s"
        )
        assert matched.request_id == request_id
        assert "Yes" in matched.raw_text
