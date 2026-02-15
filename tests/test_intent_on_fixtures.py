"""
Golden tests: classify real message threads from Le Matisse.

These tests run the IntentClassifier against messages we know the ground truth for.
They serve as regression tests — if the classifier starts mis-classifying known
messages, these tests fail.

Two layers:
  - SimulatorIntentClassifier: always runs, tests keyword matching
  - ClaudeIntentClassifier:    runs when ANTHROPIC_API_KEY is set

Edge cases (e.g. "arriverons tard" = late arrival, NOT late checkout) are
explicitly tested against the Claude classifier only, since the keyword-based
simulator intentionally keeps it simple.
"""

import os

import pytest

from src.adapters.claude_intent import ClaudeIntentClassifier
from src.adapters.simulator_intent import SimulatorIntentClassifier
from src.domain.intent import ConversationContext

HAS_API_KEY = bool(os.environ.get("ANTHROPIC_API_KEY"))


def _ctx(**kw) -> ConversationContext:
    defaults = dict(
        reservation_id=0,
        guest_name="Guest",
        property_name="Le Matisse",
        default_checkin_time="15:00",
        default_checkout_time="11:00",
        arrival_date="2026-04-01",
        departure_date="2026-04-05",
    )
    defaults.update(kw)
    return ConversationContext(**defaults)


# ---------------------------------------------------------------------------
# Messages with clear ground truth (both simulator and Claude should agree)
# ---------------------------------------------------------------------------

CLEAR_EARLY_CHECKIN = [
    # From reservation 120007226
    "Bonsoir, je voudrais savoir s'il serait possible d'accéder plus tôt à l'appartement, car nous avons une cérémonie à 17 h et nous aimerions déposer nos affaires.",
    # From reservation 120491866
    "Est-ce possible d'arriver un peu plus tôt ? Si oui votre heure sera la nôtre.",
    # From reservation 121135736 (English)
    "Hi, thanks for the info. Would early check in be an option? Thanks. Happy New Year.",
    # From reservation 125738476 — "ahead of time" keyword
    "Hi guys. We are here early. Are we able to go in ahead of time please?",
]

# Messages where keyword matching is insufficient — Claude-only tests
SEMANTIC_EARLY_CHECKIN = [
    # "We are here early" without "check-in" or "ahead of time" keyword
    # (simulator may miss this variant, Claude understands the situation)
    "We arrived a couple hours early, any chance we can get in?",
]

CLEAR_LATE_CHECKOUT = [
    # From reservation 123177576
    "Bonsoir, une petite question: serait-il éventuellement possible de ne libérer l'appartement samedi prochain qu'en début d'après-midi? Bonne soirée",
    # From reservation 123068726
    "Nous voulions savoir s'il serait éventuellement possible de partir un peu plus tard demain. Nous avons un train assez tard, vers 20h.",
]

CLEAR_OTHER = [
    # Unrelated intro message
    "Bonjour, nous allons à Grenoble pour découvrir la ville et revoir de vieux amis.",
    # Party rules confirmation
    "Oui, il n'y a aucun problème, nous ne voulons pas faire la fête.",
    # Wifi / facilities question
    "Bonjour, quel est le code Wifi s'il vous plaît ?",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("message", CLEAR_EARLY_CHECKIN)
async def test_simulator_classifies_early_checkin(message):
    clf = SimulatorIntentClassifier()
    result = await clf.classify(message, _ctx())
    assert result.intent == "early_checkin", (
        f"Expected early_checkin, got {result.intent!r} for: {message[:80]}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("message", CLEAR_LATE_CHECKOUT)
async def test_simulator_classifies_late_checkout(message):
    clf = SimulatorIntentClassifier()
    result = await clf.classify(message, _ctx())
    assert result.intent == "late_checkout", (
        f"Expected late_checkout, got {result.intent!r} for: {message[:80]}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("message", CLEAR_OTHER)
async def test_simulator_classifies_other(message):
    clf = SimulatorIntentClassifier()
    result = await clf.classify(message, _ctx())
    assert result.intent == "other", (
        f"Expected other, got {result.intent!r} for: {message[:80]}"
    )


# ---------------------------------------------------------------------------
# Claude golden tests — require API key
# ---------------------------------------------------------------------------

CLAUDE_GOLDEN = [
    # (message, expected_intent)
    *[(m, "early_checkin") for m in CLEAR_EARLY_CHECKIN],
    *[(m, "early_checkin") for m in SEMANTIC_EARLY_CHECKIN],
    *[(m, "late_checkout") for m in CLEAR_LATE_CHECKOUT],
    *[(m, "other") for m in CLEAR_OTHER],
    # Edge case: "arriverons tard" means late arrival time, NOT late checkout
    (
        "D'accord, super, merci beaucoup. Nous arriverons tard le mercredi soir car nous venons de Lille.",
        "other",
    ),
    # Edge case: asking if check-in time applies with a code (not a timing request)
    (
        "Bonjour, merci pour votre message, malheureusement je n'arrive pas à voir le code… Si je souhaite arriver avant 17h y a t il un coût supplémentaire ?",
        "early_checkin",
    ),
    # Time given as "16h" — standard time is 15h, so 16h is AFTER, not a request
    (
        "Bonsoir. Nous arriverons un peu plus tôt (vers 16h). L'appartement sera-t-il accessible avec les codes d'accès ?",
        "early_checkin",
    ),
]


@pytest.mark.skipif(not HAS_API_KEY, reason="ANTHROPIC_API_KEY not set")
@pytest.mark.asyncio
@pytest.mark.parametrize("message,expected", CLAUDE_GOLDEN)
async def test_claude_classifies_fixture_message(message, expected):
    clf = ClaudeIntentClassifier()
    result = await clf.classify(message, _ctx())
    assert result.intent == expected, (
        f"Expected {expected!r}, got {result.intent!r} "
        f"(confidence={result.confidence:.2f}) for:\n{message[:120]}"
    )
