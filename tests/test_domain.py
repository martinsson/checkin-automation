"""
Unit tests for pure domain functions.

No async, no mocks, no simulators — plain assert on pure functions.
"""

from datetime import datetime, timezone

from src.domain.guest_request import (
    Actionable,
    Followup,
    Skip,
    build_cleaner_query,
    enrich_with_context,
    plan_drafts,
    triage,
)
from src.domain.cleaner_response import plan_reply, rebuild_query_context
from src.domain.draft_dispatch import (
    SendToCleaner,
    SendToGuest,
    SkipSilently,
    plan_dispatch,
)
from src.ports.intent import ClassificationResult, ConversationContext
from src.ports.memory import Draft, ProcessedRequest


def _make_context(**overrides):
    defaults = dict(
        reservation_id=100,
        guest_name="Alice",
        property_name="Studio A",
        default_checkin_time="17:00",
        default_checkout_time="11:00",
        arrival_date="2026-03-05",
        departure_date="2026-03-07",
    )
    defaults.update(overrides)
    return ConversationContext(**defaults)


def _make_classification(**overrides):
    defaults = dict(
        intent="early_checkin",
        confidence=0.95,
        extracted_time="14:00",
        needs_followup=False,
        followup_question=None,
    )
    defaults.update(overrides)
    return ClassificationResult(**defaults)


def _make_draft(**overrides):
    defaults = dict(
        draft_id=1,
        request_id="req-1",
        reservation_id=100,
        intent="early_checkin",
        step="acknowledgment",
        draft_body="We got your request!",
        verdict="ok",
        actual_message_sent=None,
        owner_comment=None,
        created_at=datetime.now(timezone.utc),
        reviewed_at=datetime.now(timezone.utc),
        sent_at=None,
    )
    defaults.update(overrides)
    return Draft(**defaults)


def _make_request(**overrides):
    defaults = dict(
        reservation_id=100,
        intent="early_checkin",
        status="pending_acknowledgment",
        created_at=datetime.now(timezone.utc),
        request_id="req-1",
        guest_message="Can we check in at 14h?",
        guest_name="Alice",
        property_name="Studio A",
        original_time="17:00",
        requested_time="14:00",
        relevant_date="2026-03-05",
    )
    defaults.update(overrides)
    return ProcessedRequest(**defaults)


# === triage() ===

class TestTriage:
    def test_already_seen_message_returns_skip(self):
        result = triage(message_id=42, is_seen=True, classification=None, is_processed=False)
        assert isinstance(result, Skip)
        assert "already seen" in result.reason

    def test_no_classification_returns_skip(self):
        result = triage(message_id=42, is_seen=False, classification=None, is_processed=False)
        assert isinstance(result, Skip)

    def test_intent_other_returns_skip(self):
        cls = _make_classification(intent="other")
        result = triage(message_id=42, is_seen=False, classification=cls, is_processed=False)
        assert isinstance(result, Skip)
        assert "ignored" in result.reason

    def test_already_processed_returns_skip(self):
        cls = _make_classification(intent="early_checkin")
        result = triage(message_id=42, is_seen=False, classification=cls, is_processed=True)
        assert isinstance(result, Skip)
        assert "already processed" in result.reason

    def test_needs_followup_returns_followup(self):
        cls = _make_classification(needs_followup=True, followup_question="What time?")
        result = triage(message_id=42, is_seen=False, classification=cls, is_processed=False)
        assert isinstance(result, Followup)
        assert result.question == "What time?"

    def test_actionable_early_checkin(self):
        cls = _make_classification(intent="early_checkin", extracted_time="14:00")
        result = triage(message_id=42, is_seen=False, classification=cls, is_processed=False)
        assert isinstance(result, Actionable)
        assert result.intent == "early_checkin"
        assert result.extracted_time == "14:00"

    def test_zero_message_id_not_skipped_even_if_seen(self):
        result = triage(message_id=0, is_seen=True, classification=_make_classification(), is_processed=False)
        assert isinstance(result, Actionable)


# === enrich_with_context() ===

class TestEnrichWithContext:
    def test_early_checkin_uses_arrival(self):
        result = Actionable(request_id="r", intent="early_checkin", extracted_time="14:00", original_time="", relevant_date="")
        ctx = _make_context()
        enrich_with_context(result, ctx)
        assert result.original_time == "17:00"
        assert result.relevant_date == "2026-03-05"

    def test_late_checkout_uses_departure(self):
        result = Actionable(request_id="r", intent="late_checkout", extracted_time="13:00", original_time="", relevant_date="")
        ctx = _make_context()
        enrich_with_context(result, ctx)
        assert result.original_time == "11:00"
        assert result.relevant_date == "2026-03-07"


# === plan_drafts() ===

class TestPlanDrafts:
    def test_creates_ack_and_cleaner_query(self):
        result = Actionable(request_id="r1", intent="early_checkin", extracted_time="14:00", original_time="17:00", relevant_date="2026-03-05")
        ctx = _make_context()
        plan = plan_drafts(result, 100, "Can I check in early?", ctx, "We'll check!", "Query for cleaner")
        assert plan.save_request.intent == "early_checkin"
        assert len(plan.drafts) == 2
        assert plan.drafts[0].step == "acknowledgment"
        assert plan.drafts[1].step == "cleaner_query"
        assert plan.status_update.status == "pending_acknowledgment"


# === build_cleaner_query() ===

class TestBuildCleanerQuery:
    def test_builds_correct_query(self):
        result = Actionable(request_id="r1", intent="early_checkin", extracted_time="14:00", original_time="17:00", relevant_date="2026-03-05")
        ctx = _make_context()
        query = build_cleaner_query(result, ctx, "Marie", "Can I check in at 14h?")
        assert query.request_type == "early_checkin"
        assert query.guest_name == "Alice"
        assert query.cleaner_name == "Marie"
        assert query.requested_time == "14:00"


# === cleaner_response domain ===

class TestCleanerResponseDomain:
    def test_rebuild_query_context(self):
        req = _make_request()
        query = rebuild_query_context(req, "Marie")
        assert query.request_id == "req-1"
        assert query.guest_name == "Alice"
        assert query.request_type == "early_checkin"

    def test_plan_reply(self):
        req = _make_request()
        plan = plan_reply("Great news, you can check in at 14h!", req)
        assert plan.draft_step == "guest_reply"
        assert plan.new_status == "pending_reply"
        assert plan.reservation_id == 100


# === draft_dispatch domain ===

class TestDraftDispatch:
    def test_approved_guest_step_sends_to_guest(self):
        draft = _make_draft(verdict="ok", step="acknowledgment")
        action = plan_dispatch(draft, _make_request())
        assert isinstance(action, SendToGuest)
        assert action.body == "We got your request!"

    def test_approved_cleaner_query_sends_to_cleaner(self):
        draft = _make_draft(verdict="ok", step="cleaner_query")
        action = plan_dispatch(draft, _make_request())
        assert isinstance(action, SendToCleaner)
        assert action.query.guest_name == "Alice"

    def test_rejected_with_correction_sends_correction(self):
        draft = _make_draft(verdict="nok", actual_message_sent="Fixed text", step="acknowledgment")
        action = plan_dispatch(draft, _make_request())
        assert isinstance(action, SendToGuest)
        assert action.body == "Fixed text"

    def test_rejected_without_correction_skips(self):
        draft = _make_draft(verdict="nok", actual_message_sent=None)
        action = plan_dispatch(draft, _make_request())
        assert isinstance(action, SkipSilently)

    def test_cleaner_query_without_request_skips(self):
        draft = _make_draft(verdict="ok", step="cleaner_query")
        action = plan_dispatch(draft, None)
        assert isinstance(action, SkipSilently)

    def test_guest_reply_sends_to_guest(self):
        draft = _make_draft(verdict="ok", step="guest_reply", draft_body="You can check in at 14h!")
        action = plan_dispatch(draft, _make_request())
        assert isinstance(action, SendToGuest)
        assert action.body == "You can check in at 14h!"
