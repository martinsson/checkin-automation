"""
RequestMemory contract tests.

Runs the shared contract against every RequestMemory implementation.
"""

from src.adapters.memory_simulator import InMemoryRequestMemory
from tests.contracts.request_memory_contract import RequestMemoryContract


class TestInMemoryRequestMemory(RequestMemoryContract):

    def create_memory(self):
        return InMemoryRequestMemory()
