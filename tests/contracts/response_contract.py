"""
Contract tests for ResponseParser and ReplyComposer implementations.
"""

from abc import ABC, abstractmethod

import pytest

from src.communication.ports import CleanerQuery
from src.domain.response import ReplyComposer, ResponseParser


def _req(request_type: str = "early_checkin") -> CleanerQuery:
    return CleanerQuery(
        request_id="contract-001",
        cleaner_name="Marie",
        guest_name="Sophie",
        property_name="Le Matisse",
        request_type=request_type,
        original_time="15:00",
        requested_time="12:00",
        date="2026-04-01",
        message="Can you be done by noon?",
    )


# ---------------------------------------------------------------------------
# ResponseParser contract
# ---------------------------------------------------------------------------


class ResponseParserContract(ABC):

    @abstractmethod
    def create_parser(self) -> ResponseParser:
        ...

    @pytest.mark.asyncio
    async def test_yes_reply_parsed_as_yes(self):
        parser = self.create_parser()
        result = await parser.parse("Oui, pas de problème !", _req())
        assert result.answer == "yes"
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_no_reply_parsed_as_no(self):
        parser = self.create_parser()
        result = await parser.parse("Non, c'est impossible pour cette date.", _req())
        assert result.answer == "no"
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_result_has_required_fields(self):
        parser = self.create_parser()
        result = await parser.parse("Super, ça marche !", _req())
        assert result.answer in ("yes", "no", "conditional", "unclear")
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_time_extracted_when_mentioned(self):
        parser = self.create_parser()
        result = await parser.parse("Oui, mais pas avant 13h00.", _req())
        assert result.proposed_time is not None


# ---------------------------------------------------------------------------
# ReplyComposer contract
# ---------------------------------------------------------------------------


class ReplyComposerContract(ABC):

    @abstractmethod
    def create_composer(self) -> ReplyComposer:
        ...

    @pytest.mark.asyncio
    async def test_yes_produces_non_empty_reply(self):
        from src.domain.response import ParsedResponse

        composer = self.create_composer()
        parsed = ParsedResponse(
            answer="yes", conditions=None, proposed_time="12:00", confidence=0.9
        )
        reply = await composer.compose(parsed, _req())
        assert reply.body
        assert len(reply.body) > 20

    @pytest.mark.asyncio
    async def test_no_produces_non_empty_reply(self):
        from src.domain.response import ParsedResponse

        composer = self.create_composer()
        parsed = ParsedResponse(
            answer="no", conditions=None, proposed_time=None, confidence=0.9
        )
        reply = await composer.compose(parsed, _req())
        assert reply.body
        assert len(reply.body) > 20

    @pytest.mark.asyncio
    async def test_reply_has_confidence(self):
        from src.domain.response import ParsedResponse

        composer = self.create_composer()
        parsed = ParsedResponse(
            answer="yes", conditions=None, proposed_time="12:00", confidence=0.9
        )
        reply = await composer.compose(parsed, _req())
        assert 0.0 <= reply.confidence <= 1.0
