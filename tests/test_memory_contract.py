"""
RequestMemory contract tests — run against SQLite with :memory:.
"""

from src.adapters.sqlite_memory import SqliteRequestMemory
from tests.contracts.request_memory_contract import RequestMemoryContract


class TestSqliteRequestMemory(RequestMemoryContract):

    def create_memory(self):
        return SqliteRequestMemory(":memory:")
