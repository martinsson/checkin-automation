"""
IntentClassifier contract tests.

Runs the shared contract against:
  - SimulatorIntentClassifier  (always, no API key needed)
  - ClaudeIntentClassifier     (skipped without ANTHROPIC_API_KEY)
"""

import os

import pytest

from src.adapters.claude_intent import ClaudeIntentClassifier
from src.adapters.simulator_intent import SimulatorIntentClassifier
from tests.contracts.intent_classifier_contract import IntentClassifierContract


class TestSimulatorIntentClassifier(IntentClassifierContract):

    def create_classifier(self):
        return SimulatorIntentClassifier()


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
class TestClaudeIntentClassifier(IntentClassifierContract):

    def create_classifier(self):
        return ClaudeIntentClassifier()
