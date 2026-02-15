"""
ResponseParser and ReplyComposer contract tests.

Runs the shared contracts against:
  - Simulator adapters  (always, no API key needed)
  - Claude adapters     (skipped without ANTHROPIC_API_KEY)
"""

import os

import pytest

from src.adapters.claude_response import ClaudeReplyComposer, ClaudeResponseParser
from src.adapters.simulator_response import SimulatorReplyComposer, SimulatorResponseParser
from tests.contracts.response_contract import ReplyComposerContract, ResponseParserContract

HAS_API_KEY = bool(os.environ.get("ANTHROPIC_API_KEY"))


# ---------------------------------------------------------------------------
# Simulator adapters — always run
# ---------------------------------------------------------------------------


class TestSimulatorResponseParser(ResponseParserContract):

    def create_parser(self):
        return SimulatorResponseParser()


class TestSimulatorReplyComposer(ReplyComposerContract):

    def create_composer(self):
        return SimulatorReplyComposer()


# ---------------------------------------------------------------------------
# Claude adapters — skipped without API key
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not HAS_API_KEY, reason="ANTHROPIC_API_KEY not set")
class TestClaudeResponseParser(ResponseParserContract):

    def create_parser(self):
        return ClaudeResponseParser()


@pytest.mark.skipif(not HAS_API_KEY, reason="ANTHROPIC_API_KEY not set")
class TestClaudeReplyComposer(ReplyComposerContract):

    def create_composer(self):
        return ClaudeReplyComposer()
