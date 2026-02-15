"""In-memory adapter for RequestMemory — for tests and local development."""

from datetime import datetime, timezone

from src.domain.memory import ProcessedRequest, RequestMemory


class InMemoryRequestMemory(RequestMemory):

    def __init__(self):
        self._records: list[ProcessedRequest] = []

    async def has_been_processed(self, reservation_id: int, intent: str) -> bool:
        return any(
            r.reservation_id == reservation_id and r.intent == intent
            for r in self._records
        )

    async def mark_processed(
        self,
        reservation_id: int,
        intent: str,
        result: str,
        request_id: str,
    ) -> None:
        self._records.append(
            ProcessedRequest(
                reservation_id=reservation_id,
                intent=intent,
                result=result,
                processed_at=datetime.now(timezone.utc),
                request_id=request_id,
            )
        )

    async def get_history(self, reservation_id: int) -> list[ProcessedRequest]:
        return [r for r in self._records if r.reservation_id == reservation_id]
