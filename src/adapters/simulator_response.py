"""
Simulator adapters for ResponseParser and ReplyComposer.

Deterministic keyword-based implementations for tests — no LLM calls.
"""

import re

from src.communication.ports import CleanerQuery
from src.domain.response import (
    ComposedReply,
    ParsedResponse,
    ReplyComposer,
    ResponseParser,
)

_YES_KEYWORDS = [
    r"\boui\b", r"\byes\b", r"\bpas de probl[eè]me\b", r"\bno problem\b",
    r"\bd'accord\b", r"\bok\b", r"\bparfait\b", r"\bsuper\b",
    r"\bc'est possible\b", r"\bpossible\b", r"\bça marche\b",
]
_NO_KEYWORDS = [
    r"\bnon\b", r"\bno\b", r"\bimpossible\b", r"\bne peut pas\b",
    r"\bcannot\b", r"\bcan't\b", r"\bdésolé\b", r"\bsorry\b",
    r"\bmalheureusement\b", r"\bunfortunately\b",
]
_TIME_PATTERN = re.compile(r"(\d{1,2})[h:](\d{0,2})", re.IGNORECASE)


def _match_any(text: str, patterns: list[str]) -> bool:
    lower = text.lower()
    return any(re.search(p, lower) for p in patterns)


def _extract_time(text: str) -> str | None:
    m = _TIME_PATTERN.search(text)
    if not m:
        return None
    return f"{int(m.group(1)):02d}:{int(m.group(2) or 0):02d}"


class SimulatorResponseParser(ResponseParser):

    async def parse(self, raw_text: str, original_request: CleanerQuery) -> ParsedResponse:
        is_yes = _match_any(raw_text, _YES_KEYWORDS)
        is_no = _match_any(raw_text, _NO_KEYWORDS)
        time = _extract_time(raw_text)

        if is_yes and not is_no:
            return ParsedResponse(
                answer="yes",
                conditions=None,
                proposed_time=time,
                confidence=0.85,
            )
        if is_no and not is_yes:
            return ParsedResponse(
                answer="no",
                conditions=None,
                proposed_time=None,
                confidence=0.85,
            )
        if is_yes and is_no:
            # e.g. "oui mais pas avant 13h" — conditional
            return ParsedResponse(
                answer="conditional",
                conditions=raw_text[:200],
                proposed_time=time,
                confidence=0.6,
            )
        return ParsedResponse(
            answer="unclear",
            conditions=raw_text[:200],
            proposed_time=None,
            confidence=0.3,
        )


class SimulatorReplyComposer(ReplyComposer):

    async def compose(
        self, parsed: ParsedResponse, original_request: CleanerQuery
    ) -> ComposedReply:
        req_type = original_request.request_type
        time = parsed.proposed_time or original_request.requested_time

        if parsed.answer == "yes":
            if req_type == "early_checkin":
                body = (
                    f"Bonjour {original_request.guest_name},\n\n"
                    f"Bonne nouvelle ! Un check-in anticipé à {time} est possible. "
                    f"Nous vous attendons avec plaisir.\n\n"
                    f"Cordialement"
                )
            else:
                body = (
                    f"Bonjour {original_request.guest_name},\n\n"
                    f"Bonne nouvelle ! Un départ tardif jusqu'à {time} est possible. "
                    f"Profitez bien !\n\n"
                    f"Cordialement"
                )
            return ComposedReply(body=body, confidence=0.9)

        if parsed.answer == "no":
            if req_type == "early_checkin":
                body = (
                    f"Bonjour {original_request.guest_name},\n\n"
                    f"Malheureusement, un check-in anticipé n'est pas possible "
                    f"pour votre séjour. L'heure d'arrivée standard est "
                    f"{original_request.original_time}.\n\n"
                    f"Cordialement"
                )
            else:
                body = (
                    f"Bonjour {original_request.guest_name},\n\n"
                    f"Malheureusement, un départ tardif n'est pas possible "
                    f"pour votre séjour. L'heure de départ standard est "
                    f"{original_request.original_time}.\n\n"
                    f"Cordialement"
                )
            return ComposedReply(body=body, confidence=0.9)

        # conditional or unclear — low confidence, will be escalated
        return ComposedReply(
            body=(
                f"Bonjour {original_request.guest_name},\n\n"
                f"Nous avons transmis votre demande et revenons vers vous "
                f"dès que possible.\n\nCordialement"
            ),
            confidence=0.4,
        )
