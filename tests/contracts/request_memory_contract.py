"""Contract tests for any RequestMemory implementation."""

from abc import ABC, abstractmethod

import pytest

from src.domain.memory import RequestMemory


class RequestMemoryContract(ABC):

    @abstractmethod
    def create_memory(self) -> RequestMemory:
        ...

    @pytest.mark.asyncio
    async def test_not_processed_by_default(self):
        mem = self.create_memory()
        assert await mem.has_been_processed(42, "early_checkin") is False

    @pytest.mark.asyncio
    async def test_mark_then_check(self):
        mem = self.create_memory()
        await mem.mark_processed(42, "early_checkin", "approved", "req-1")
        assert await mem.has_been_processed(42, "early_checkin") is True

    @pytest.mark.asyncio
    async def test_different_intents_are_independent(self):
        mem = self.create_memory()
        await mem.mark_processed(42, "early_checkin", "approved", "req-1")
        assert await mem.has_been_processed(42, "late_checkout") is False

    @pytest.mark.asyncio
    async def test_different_reservations_are_independent(self):
        mem = self.create_memory()
        await mem.mark_processed(42, "early_checkin", "approved", "req-1")
        assert await mem.has_been_processed(99, "early_checkin") is False

    @pytest.mark.asyncio
    async def test_get_history_returns_records(self):
        mem = self.create_memory()
        await mem.mark_processed(42, "early_checkin", "approved", "req-1")
        await mem.mark_processed(42, "late_checkout", "declined", "req-2")

        history = await mem.get_history(42)
        assert len(history) == 2
        intents = {r.intent for r in history}
        assert intents == {"early_checkin", "late_checkout"}

    @pytest.mark.asyncio
    async def test_get_history_empty_for_unknown_reservation(self):
        mem = self.create_memory()
        history = await mem.get_history(999)
        assert history == []
