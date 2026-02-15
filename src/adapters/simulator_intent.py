"""
SimulatorIntentClassifier — deterministic keyword-based classifier for tests.

No LLM calls, no network. Recognises the most common French and English
phrases used in real Airbnb message threads.
"""

import re

from src.domain.intent import (
    ClassificationResult,
    ConversationContext,
    IntentClassifier,
)

# French + English keywords that signal each intent
_EARLY_CHECKIN_KEYWORDS = [
    r"\btôt\b", r"\btot\b", r"\bavant\b",
    r"\bearly\s+check.?in\b", r"\bcheck.?in\s+early\b",
    r"\bearlier\s+check.?in\b", r"\bcheck.?in\s+earlier\b",
    r"\bplus\s+tôt\b", r"\baccéder\s+plus\s+tôt\b",
    r"\barriver\s+(?:plus\s+)?tôt\b", r"\barriver\s+avant\b",
    r"\bdéposer\s+(?:nos|mes|les)\s+affaires\b",
    r"\bahead\s+of\s+time\b",
    r"\bearlier\b",
]

_LATE_CHECKOUT_KEYWORDS = [
    r"\blate\s+check.?out\b", r"\bcheck.?out\s+(?:a\s+bit\s+)?later\b",
    r"\bcheck.?out\s+tard\b",
    r"\bquitter\s+(?:plus\s+)?tard\b",
    r"\brester\s+(?:\w+\s+){0,3}tard\b", r"\bpartir\s+(?:\w+\s+){0,3}tard\b",
    r"\blate\s+departure\b",
    r"\blib[eé]rer\b",
    r"\bne\s+lib[eé]rer\b",
]

# Simple time patterns like "12h", "12:00", "midi", "noon"
_TIME_PATTERN = re.compile(
    r"(\d{1,2})[h:](\d{0,2})|(\bmidi\b)|(\bnoon\b)|(\bminuit\b)", re.IGNORECASE
)


def _match_any(text: str, patterns: list[str]) -> bool:
    lower = text.lower()
    return any(re.search(p, lower) for p in patterns)


def _extract_time(text: str) -> str | None:
    m = _TIME_PATTERN.search(text)
    if not m:
        return None
    if m.group(3) or m.group(4):  # midi / noon
        return "12:00"
    if m.group(5):                 # minuit
        return "00:00"
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    return f"{hour:02d}:{minute:02d}"


class SimulatorIntentClassifier(IntentClassifier):
    """
    Keyword-based intent classifier for tests.
    Returns high confidence when a keyword matches, low confidence otherwise.
    """

    async def classify(
        self, message: str, context: ConversationContext
    ) -> ClassificationResult:
        is_early = _match_any(message, _EARLY_CHECKIN_KEYWORDS)
        is_late = _match_any(message, _LATE_CHECKOUT_KEYWORDS)
        time = _extract_time(message)

        if is_early and not is_late:
            return ClassificationResult(
                intent="early_checkin",
                confidence=0.85,
                extracted_time=time,
                needs_followup=time is None,
                followup_question=(
                    "À quelle heure souhaitez-vous arriver ?"
                    if time is None
                    else None
                ),
            )

        if is_late and not is_early:
            return ClassificationResult(
                intent="late_checkout",
                confidence=0.85,
                extracted_time=time,
                needs_followup=time is None,
                followup_question=(
                    "À quelle heure souhaitez-vous quitter l'appartement ?"
                    if time is None
                    else None
                ),
            )

        return ClassificationResult(
            intent="other",
            confidence=0.9 if not (is_early or is_late) else 0.4,
            extracted_time=None,
            needs_followup=False,
            followup_question=None,
        )
