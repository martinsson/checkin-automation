"""
Simulator adapters for GuestAcknowledger, ResponseParser, and ReplyComposer.

Deterministic keyword/template-based implementations for tests — no LLM calls.
"""

import re

from src.communication.ports import CleanerQuery
from src.domain.intent import ClassificationResult, ConversationContext
from src.domain.response import (
    ComposedReply,
    GuestAcknowledger,
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


class SimulatorGuestAcknowledger(GuestAcknowledger):

    async def compose_acknowledgment(
        self,
        classification: ClassificationResult,
        context: ConversationContext,
    ) -> ComposedReply:
        if classification.intent == "early_checkin":
            req_label = "un check-in anticipé"
        else:
            req_label = "un départ tardif"

        body = (
            f"Bonjour {context.guest_name},\n\n"
            f"Nous avons bien reçu votre demande pour {req_label}. "
            f"Nous allons faire tout notre possible pour y répondre favorablement. "
            f"Notre équipe de ménage est formidable pour réorganiser son planning "
            f"et faire des trajets supplémentaires afin d'optimiser son emploi du temps — "
            f"si c'est faisable, elle le fera !\n\n"
            f"Cependant, les changements le jour même peuvent être délicats car "
            f"l'équipe a besoin de suffisamment de temps pour préparer notre "
            f"appartement ainsi que d'autres logements dans le même créneau.\n\n"
            f"Nous vous tenons au courant dès que possible.\n\n"
            f"Cordialement"
        )
        return ComposedReply(body=body, confidence=0.9)


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
                    f"Il n'y a aucun frais supplémentaire pour cela. "
                    f"Certains voyageurs laissent un petit pourboire à l'équipe de "
                    f"ménage qui rend cela possible — c'est absolument pas obligatoire, "
                    f"juste un geste si vous le souhaitez.\n\n"
                    f"Cordialement"
                )
            else:
                body = (
                    f"Bonjour {original_request.guest_name},\n\n"
                    f"Bonne nouvelle ! Un départ tardif jusqu'à {time} est possible. "
                    f"Il n'y a aucun frais supplémentaire pour cela. "
                    f"Certains voyageurs laissent un petit pourboire à l'équipe de "
                    f"ménage qui rend cela possible — c'est absolument pas obligatoire, "
                    f"juste un geste si vous le souhaitez.\n\n"
                    f"Cordialement"
                )
            return ComposedReply(body=body, confidence=0.9)

        if parsed.answer == "no":
            if req_type == "early_checkin":
                body = (
                    f"Bonjour {original_request.guest_name},\n\n"
                    f"Malheureusement, un check-in anticipé n'est pas possible "
                    f"pour votre séjour. Nous avons fait de notre mieux, mais les "
                    f"changements le jour même sont parfois impossibles car l'équipe "
                    f"de ménage a besoin de suffisamment de temps pour préparer "
                    f"plusieurs appartements. "
                    f"L'heure d'arrivée standard est {original_request.original_time}.\n\n"
                    f"Cordialement"
                )
            else:
                body = (
                    f"Bonjour {original_request.guest_name},\n\n"
                    f"Malheureusement, un départ tardif n'est pas possible "
                    f"pour votre séjour. Nous avons fait de notre mieux, mais les "
                    f"changements le jour même sont parfois impossibles car l'équipe "
                    f"de ménage a besoin de suffisamment de temps pour préparer "
                    f"plusieurs appartements. "
                    f"L'heure de départ standard est {original_request.original_time}.\n\n"
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
