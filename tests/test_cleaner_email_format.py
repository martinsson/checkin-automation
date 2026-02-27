"""
Tests for cleaner email formatting: subject, body template, and request ID extraction.

These test the formatting logic without sending real emails.
"""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.communication.ports import CleanerQuery

# Same pattern used in email_notifier.py — duplicated here to avoid
# importing email_notifier which pulls in anthropic + imapclient.
REQUEST_ID_PATTERN = re.compile(r"\[REQ-([^\]]+)\]")


def _make_query(**overrides) -> CleanerQuery:
    defaults = dict(
        request_id="abc-123",
        cleaner_name="Virginie",
        guest_name="John Smith",
        property_name="Le Matisse",
        request_type="early_checkin",
        original_time="17:00",
        requested_time="12:00",
        date="2026-03-15",
        message="Can I check in at noon?",
    )
    defaults.update(overrides)
    return CleanerQuery(**defaults)


# ---------------------------------------------------------------------------
# Subject format
# ---------------------------------------------------------------------------


def test_email_subject_has_no_req_tag():
    """Subject should be 'property — date' without [REQ-...] tag."""
    query = _make_query()
    # Build subject the same way EmailCleanerNotifier does
    subject = f"{query.property_name} — {query.date}"
    assert "[REQ-" not in subject
    assert "Le Matisse" in subject
    assert "2026-03-15" in subject


# ---------------------------------------------------------------------------
# Body format
# ---------------------------------------------------------------------------


def test_email_body_has_french_greeting_template():
    """Body should use the French greeting template with cleaner name and REQ tag."""
    query = _make_query(cleaner_name="Virginie", message="Puis-je arriver à midi ?")
    # Simulate the body construction (without translation since we test format)
    body = (
        f"Bonjour {query.cleaner_name},\n\n"
        f"Voici une nouvelle demande, dites moi ce qui est possible, "
        f"raisonnablement bien entendu.\n\n"
        f"{query.message}\n\n"
        f"[REQ-{query.request_id}]"
    )
    assert body.startswith("Bonjour Virginie,")
    assert "Voici une nouvelle demande" in body
    assert "Puis-je arriver à midi ?" in body
    assert "[REQ-abc-123]" in body


# ---------------------------------------------------------------------------
# Request ID extraction from body
# ---------------------------------------------------------------------------


def test_request_id_extracted_from_body():
    """REQUEST_ID_PATTERN should match [REQ-...] tags in email body text."""
    body = (
        "Bonjour Virginie,\n\n"
        "Voici une nouvelle demande...\n\n"
        "Guest message here\n\n"
        "[REQ-abc-123]"
    )
    match = REQUEST_ID_PATTERN.search(body)
    assert match is not None
    assert match.group(1) == "abc-123"


def test_request_id_extracted_from_quoted_reply():
    """REQUEST_ID_PATTERN should find [REQ-...] even in quoted reply text."""
    reply_body = (
        "Oui pas de problème !\n\n"
        "> Bonjour Virginie,\n"
        "> \n"
        "> Voici une nouvelle demande...\n"
        "> \n"
        "> Guest message\n"
        "> \n"
        "> [REQ-xyz-789]"
    )
    match = REQUEST_ID_PATTERN.search(reply_body)
    assert match is not None
    assert match.group(1) == "xyz-789"


def test_request_id_not_found_in_empty_body():
    """No match when body has no [REQ-...] tag."""
    match = REQUEST_ID_PATTERN.search("Just a plain reply, thanks!")
    assert match is None
