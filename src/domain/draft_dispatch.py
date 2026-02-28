"""
Draft dispatch domain logic — pure functions, no I/O.

plan_dispatch(): Given a reviewed draft, decide how to dispatch it.
"""

from dataclasses import dataclass

from src.ports.cleaner import CleanerQuery
from src.ports.memory import Draft, ProcessedRequest


# --- Dispatch action types ---

@dataclass
class SendToGuest:
    reservation_id: int
    body: str


@dataclass
class SendToCleaner:
    query: CleanerQuery


@dataclass
class SkipSilently:
    draft_id: int
    reason: str


DispatchAction = SendToGuest | SendToCleaner | SkipSilently

_GUEST_STEPS = {"acknowledgment", "followup", "guest_reply"}


def plan_dispatch(
    draft: Draft,
    request: ProcessedRequest | None,
    cleaner_name: str = "Marie",
) -> DispatchAction:
    """
    Decide how to dispatch a reviewed draft.

    Pure function: takes a Draft and optional request context,
    returns a dispatch action. No I/O, no async.
    """
    # Rejected without correction → skip
    if draft.verdict == "nok" and draft.actual_message_sent is None:
        return SkipSilently(
            draft_id=draft.draft_id,
            reason="rejected without correction",
        )

    # Determine the body to send
    body: str = (
        draft.draft_body
        if draft.verdict == "ok"
        else draft.actual_message_sent  # type: ignore[assignment]
    )

    # Route by step
    if draft.step in _GUEST_STEPS:
        return SendToGuest(
            reservation_id=draft.reservation_id,
            body=body,
        )

    if draft.step == "cleaner_query":
        if request is None:
            return SkipSilently(
                draft_id=draft.draft_id,
                reason=f"request {draft.request_id} not found",
            )
        query = CleanerQuery(
            request_id=draft.request_id,
            cleaner_name=cleaner_name,
            guest_name=request.guest_name,
            property_name=request.property_name,
            request_type=draft.intent,
            original_time=request.original_time,
            requested_time=request.requested_time,
            date=request.relevant_date,
            message=body,
        )
        return SendToCleaner(query=query)

    return SkipSilently(
        draft_id=draft.draft_id,
        reason=f"unknown step: {draft.step}",
    )
