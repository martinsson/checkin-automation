"""Contract tests for any RequestMemory implementation."""

from abc import ABC, abstractmethod

import pytest

from src.domain.memory import RequestMemory


class RequestMemoryContract(ABC):

    @abstractmethod
    def create_memory(self) -> RequestMemory:
        ...

    # -- message-level dedup -------------------------------------------------

    @pytest.mark.asyncio
    async def test_message_not_seen_by_default(self):
        mem = self.create_memory()
        assert await mem.has_message_been_seen(999) is False

    @pytest.mark.asyncio
    async def test_mark_and_check_message_seen(self):
        mem = self.create_memory()
        await mem.mark_message_seen(42, 101)
        assert await mem.has_message_been_seen(42) is True

    @pytest.mark.asyncio
    async def test_mark_message_seen_is_idempotent(self):
        mem = self.create_memory()
        await mem.mark_message_seen(42, 101)
        await mem.mark_message_seen(42, 101)  # must not raise
        assert await mem.has_message_been_seen(42) is True

    # -- request tracking ----------------------------------------------------

    @pytest.mark.asyncio
    async def test_not_processed_by_default(self):
        mem = self.create_memory()
        assert await mem.has_been_processed(42, "early_checkin") is False

    @pytest.mark.asyncio
    async def test_save_then_check(self):
        mem = self.create_memory()
        await mem.save_request(42, "early_checkin", "req-1", "Can I check in early?")
        assert await mem.has_been_processed(42, "early_checkin") is True

    @pytest.mark.asyncio
    async def test_different_intents_are_independent(self):
        mem = self.create_memory()
        await mem.save_request(42, "early_checkin", "req-1", "msg")
        assert await mem.has_been_processed(42, "late_checkout") is False

    @pytest.mark.asyncio
    async def test_different_reservations_are_independent(self):
        mem = self.create_memory()
        await mem.save_request(42, "early_checkin", "req-1", "msg")
        assert await mem.has_been_processed(99, "early_checkin") is False

    @pytest.mark.asyncio
    async def test_get_history_returns_records(self):
        mem = self.create_memory()
        await mem.save_request(42, "early_checkin", "req-1", "msg1")
        await mem.save_request(42, "late_checkout", "req-2", "msg2")

        history = await mem.get_history(42)
        assert len(history) == 2
        intents = {r.intent for r in history}
        assert intents == {"early_checkin", "late_checkout"}

    @pytest.mark.asyncio
    async def test_get_history_empty_for_unknown_reservation(self):
        mem = self.create_memory()
        history = await mem.get_history(999)
        assert history == []

    @pytest.mark.asyncio
    async def test_get_request_by_id(self):
        mem = self.create_memory()
        await mem.save_request(42, "early_checkin", "req-1", "original msg")
        req = await mem.get_request("req-1")
        assert req is not None
        assert req.reservation_id == 42
        assert req.intent == "early_checkin"
        assert req.guest_message == "original msg"

    @pytest.mark.asyncio
    async def test_update_status(self):
        mem = self.create_memory()
        await mem.save_request(42, "early_checkin", "req-1", "msg")
        await mem.update_status("req-1", "pending_cleaner")
        req = await mem.get_request("req-1")
        assert req.status == "pending_cleaner"

    # -- draft management ----------------------------------------------------

    @pytest.mark.asyncio
    async def test_save_and_get_draft(self):
        mem = self.create_memory()
        await mem.save_request(42, "early_checkin", "req-1", "msg")
        draft_id = await mem.save_draft("req-1", 42, "early_checkin", "acknowledgment", "Bonjour...")

        draft = await mem.get_draft(draft_id)
        assert draft is not None
        assert draft.request_id == "req-1"
        assert draft.step == "acknowledgment"
        assert draft.draft_body == "Bonjour..."
        assert draft.verdict == "pending"

    @pytest.mark.asyncio
    async def test_pending_drafts(self):
        mem = self.create_memory()
        await mem.save_request(42, "early_checkin", "req-1", "msg")
        await mem.save_draft("req-1", 42, "early_checkin", "acknowledgment", "Draft 1")
        await mem.save_draft("req-1", 42, "early_checkin", "cleaner_query", "Draft 2")

        pending = await mem.get_pending_drafts()
        assert len(pending) == 2
        assert pending[0].step == "acknowledgment"
        assert pending[1].step == "cleaner_query"

    @pytest.mark.asyncio
    async def test_review_ok(self):
        mem = self.create_memory()
        await mem.save_request(42, "early_checkin", "req-1", "msg")
        draft_id = await mem.save_draft("req-1", 42, "early_checkin", "acknowledgment", "Draft text")

        await mem.review_draft(draft_id, "ok")

        draft = await mem.get_draft(draft_id)
        assert draft.verdict == "ok"
        assert draft.reviewed_at is not None
        # ok → no longer pending
        assert await mem.get_pending_drafts() == []

    @pytest.mark.asyncio
    async def test_review_nok_with_actual_message_and_comment(self):
        mem = self.create_memory()
        await mem.save_request(42, "early_checkin", "req-1", "msg")
        draft_id = await mem.save_draft("req-1", 42, "early_checkin", "acknowledgment", "AI draft")

        await mem.review_draft(
            draft_id, "nok",
            actual_message_sent="What I actually sent",
            owner_comment="Tone was too formal",
        )

        draft = await mem.get_draft(draft_id)
        assert draft.verdict == "nok"
        assert draft.actual_message_sent == "What I actually sent"
        assert draft.owner_comment == "Tone was too formal"
        assert draft.reviewed_at is not None
