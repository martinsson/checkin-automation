"""
Guest request domain logic — pure functions, no I/O.

triage():           Should we act on this message? → Skip | Followup | Actionable
plan_drafts():      What drafts to create? → list of commands
build_cleaner_query(): Assemble a CleanerQuery from context
"""

import uuid
from dataclasses import dataclass

from src.ports.cleaner import CleanerQuery
from src.ports.intent import ClassificationResult, ConversationContext


# --- Triage result types ---

@dataclass
class Skip:
    reason: str


@dataclass
class Followup:
    request_id: str
    intent: str
    question: str
    original_time: str
    requested_time: str
    relevant_date: str


@dataclass
class Actionable:
    request_id: str
    intent: str
    extracted_time: str
    original_time: str
    relevant_date: str


TriageResult = Skip | Followup | Actionable


# --- Draft command types ---

@dataclass
class SaveDraft:
    step: str   # "acknowledgment", "cleaner_query", "followup"
    body: str


@dataclass
class SaveRequest:
    reservation_id: int
    intent: str
    request_id: str
    guest_message: str
    guest_name: str
    property_name: str
    original_time: str
    requested_time: str
    relevant_date: str


@dataclass
class UpdateStatus:
    request_id: str
    status: str


@dataclass
class MarkMessageSeen:
    message_id: int
    reservation_id: int


@dataclass
class DraftPlan:
    save_request: SaveRequest
    drafts: list[SaveDraft]
    status_update: UpdateStatus


# --- Pure functions ---

def triage(
    message_id: int,
    is_seen: bool,
    classification: ClassificationResult | None,
    is_processed: bool,
) -> TriageResult:
    """
    Decide whether to act on a guest message.

    Pure function: takes booleans and a classification result,
    returns a decision. No I/O, no async.
    """
    if message_id and is_seen:
        return Skip(reason="message already seen")

    if classification is None:
        return Skip(reason="no classification")

    if classification.intent == "other":
        return Skip(reason="ignored")

    if is_processed:
        return Skip(reason=f"already processed intent={classification.intent}")

    request_id = str(uuid.uuid4())

    if classification.needs_followup and classification.followup_question:
        return Followup(
            request_id=request_id,
            intent=classification.intent,
            question=classification.followup_question,
            original_time="",
            requested_time=classification.extracted_time or "?",
            relevant_date="",
        )

    return Actionable(
        request_id=request_id,
        intent=classification.intent,
        extracted_time=classification.extracted_time or "?",
        original_time="",
        relevant_date="",
    )


def enrich_with_context(
    result: Followup | Actionable,
    context: ConversationContext,
) -> Followup | Actionable:
    """Fill in time/date fields from conversation context. Pure."""
    original_time = (
        context.default_checkin_time
        if result.intent == "early_checkin"
        else context.default_checkout_time
    )
    relevant_date = (
        context.arrival_date
        if result.intent == "early_checkin"
        else context.departure_date
    )
    result.original_time = original_time
    result.relevant_date = relevant_date
    return result


def plan_drafts(
    result: Actionable,
    reservation_id: int,
    message: str,
    context: ConversationContext,
    acknowledgment_body: str,
    cleaner_query_body: str,
) -> DraftPlan:
    """
    Plan what drafts to create for an actionable guest request.

    Pure function: returns a DraftPlan describing what to save.
    """
    save_request = SaveRequest(
        reservation_id=reservation_id,
        intent=result.intent,
        request_id=result.request_id,
        guest_message=message,
        guest_name=context.guest_name,
        property_name=context.property_name,
        original_time=result.original_time,
        requested_time=result.extracted_time,
        relevant_date=result.relevant_date,
    )

    drafts = [
        SaveDraft(step="acknowledgment", body=acknowledgment_body),
        SaveDraft(step="cleaner_query", body=cleaner_query_body),
    ]

    status_update = UpdateStatus(
        request_id=result.request_id,
        status="pending_acknowledgment",
    )

    return DraftPlan(
        save_request=save_request,
        drafts=drafts,
        status_update=status_update,
    )


def build_cleaner_query(
    result: Actionable,
    context: ConversationContext,
    cleaner_name: str,
    message: str,
) -> CleanerQuery:
    """Assemble a CleanerQuery from an Actionable result and context. Pure."""
    return CleanerQuery(
        request_id=result.request_id,
        cleaner_name=cleaner_name,
        guest_name=context.guest_name,
        property_name=context.property_name,
        request_type=result.intent,
        original_time=result.original_time,
        requested_time=result.extracted_time,
        date=result.relevant_date,
        message=message,
    )
