from datetime import datetime, timezone

from .ports import CleanerNotifier, CleanerQuery, CleanerResponse


class ConsoleCleanerNotifier(CleanerNotifier):
    """Adapter: print to console, buffer responses in memory. For dev/testing."""

    def __init__(self):
        self._pending: list[CleanerResponse] = []
        self._sent: dict[str, CleanerQuery] = {}

    async def send_query(self, query: CleanerQuery) -> str:
        tracking_id = f"console-{query.request_id}"
        self._sent[query.request_id] = query

        print(f"\n{'=' * 60}")
        print(f"  TO CLEANER: {query.cleaner_name}")
        print(f"  RE: {query.property_name} — {query.date}")
        print(f"  REQUEST ID: {query.request_id}")
        print(f"{'=' * 60}")
        print(query.message)
        print(f"{'=' * 60}\n")

        return tracking_id

    async def poll_responses(self) -> list[CleanerResponse]:
        responses = self._pending.copy()
        self._pending.clear()
        return responses

    def simulate_response(self, request_id: str, text: str):
        """Call from tests or a dev CLI to simulate a cleaner reply."""
        self._pending.append(
            CleanerResponse(
                request_id=request_id,
                raw_text=text,
                received_at=datetime.now(timezone.utc),
            )
        )
