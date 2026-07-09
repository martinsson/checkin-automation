"""
Cleaner response domain logic — pure functions, no I/O.

rebuild_query_context(): Reconstruct a CleanerQuery from a stored request
plan_reply():            Plan what draft to save for a guest reply
"""

from dataclasses import dataclass

from src.ports.cleaner import CleanerQuery
from src.ports.memory import ProcessedRequest, RequestStatus


@dataclass
class ReplyPlan:
    request_id: str
    reservation_id: int
    intent: str
    draft_step: str   # always "guest_reply"
    draft_body: str
    new_status: RequestStatus


def rebuild_query_context(
    request: ProcessedRequest,
    cleaner_name: str,
) -> CleanerQuery:
    """Reconstruct a CleanerQuery from a stored ProcessedRequest. Pure."""
    return CleanerQuery(
        request_id=request.request_id,
        cleaner_name=cleaner_name,
        guest_name=request.guest_name,
        property_name=request.property_name,
        request_type=request.intent,
        original_time=request.original_time,
        requested_time=request.requested_time,
        date=request.relevant_date,
        message=request.guest_message,
    )


def plan_reply(
    reply_body: str,
    request: ProcessedRequest,
) -> ReplyPlan:
    """Plan the guest reply draft to save. Pure."""
    return ReplyPlan(
        request_id=request.request_id,
        reservation_id=request.reservation_id,
        intent=request.intent,
        draft_step="guest_reply",
        draft_body=reply_body,
        new_status=RequestStatus.pending_reply,
    )
