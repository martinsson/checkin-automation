# Plan: AI-Powered Request Processing Pipeline

## Guiding principle

> AI understands human language → structured data.
> Code implements business rules on that data.
> AI formulates the decision into a nice human notification.

Each step is independently testable with simulators.

---

## 1. Intent detection — "What is the guest asking for?"

### Port

```python
class IntentClassifier(ABC):
    @abstractmethod
    async def classify(self, message: str, context: ConversationContext) -> ClassificationResult:
        ...
```

### Data out

```python
@dataclass
class ClassificationResult:
    intent: Literal["early_checkin", "late_checkout", "other"]
    confidence: float            # 0.0–1.0
    extracted_time: str | None   # e.g. "12:00" — if the guest mentioned one
    needs_followup: bool         # True when AI is unsure or info is missing
    followup_question: str | None  # suggested question to ask guest
```

### How it works

- AI receives the raw guest message + conversation context (reservation dates, default check-in/out times).
- It returns structured data — the intent, confidence, and any extracted details.
- The system prompt defines classification rules. These can be iterated without changing code.

### Follow-up questions

When `needs_followup` is True, the system sends `followup_question` back to the guest via Smoobu and waits for the next message before re-classifying. Examples:
- "Could you let me know what time you'd like to check in?"
- "Just to confirm — you'd like a late checkout on March 5th?"

### Business rules (in code, not AI)

- If `confidence < threshold` → escalate to owner instead of acting.
- If `intent == "other"` → ignore (no action).
- Only proceed to cleaner query if intent is `early_checkin` or `late_checkout`.

### Adapters

| Adapter | Use |
|---------|-----|
| `ClaudeIntentClassifier` | Real — calls Claude API with a system prompt |
| `SimulatorIntentClassifier` | Test — returns pre-configured results based on keywords |

### Testing approach

- **Contract test**: Both adapters satisfy `IntentClassifier` contract.
- **Simulator**: Unit tests use deterministic keyword-based classification.
- **Real adapter**: Integration test with a few example messages (skipped without API key).

---

## 2. Cleaner response parsing & guest reply crafting

### Ports

```python
class ResponseParser(ABC):
    @abstractmethod
    async def parse(self, raw_text: str, original_request: CleanerQuery) -> ParsedResponse:
        ...

class ReplyComposer(ABC):
    @abstractmethod
    async def compose(self, parsed: ParsedResponse, context: ConversationContext) -> ComposedReply:
        ...
```

### Data

```python
@dataclass
class ParsedResponse:
    answer: Literal["yes", "no", "conditional", "unclear"]
    conditions: str | None       # e.g. "only if they arrive by 13:00"
    proposed_time: str | None    # e.g. "13:00"
    confidence: float

@dataclass
class ComposedReply:
    body: str                    # The message to send to the guest
    confidence: float            # How confident the AI is in the reply
```

### How it works

1. **Parse**: AI reads the cleaner's raw text and produces structured data.
2. **Business rules** (code): decide what to do with the parsed response.
3. **Compose**: AI formulates a friendly guest reply from the decision.

### Routing logic (code, not AI)

```
if parsed.confidence < threshold OR parsed.answer == "unclear":
    → send to owner: "Suggested response for {apartment} {booking_id}: {draft}"
    → do NOT auto-send to guest

if parsed.answer == "yes" OR parsed.answer == "conditional":
    → compose reply → send to guest via Smoobu

if parsed.answer == "no":
    → compose polite decline → send to guest via Smoobu
```

### Key safety rule

When in doubt, the system sends a **suggested response** to the owner rather than replying to the guest directly. The owner can approve, edit, or ignore.

### Adapters

| Adapter | Use |
|---------|-----|
| `ClaudeResponseParser` / `ClaudeReplyComposer` | Real — calls Claude API |
| `SimulatorResponseParser` / `SimulatorReplyComposer` | Test — keyword-based |

---

## 3. Request memory — avoid processing the same demand twice

### Port

```python
class RequestMemory(ABC):
    @abstractmethod
    async def has_been_processed(self, reservation_id: int, intent: str) -> bool:
        ...

    @abstractmethod
    async def mark_processed(self, reservation_id: int, intent: str, result: str) -> None:
        ...

    @abstractmethod
    async def get_history(self, reservation_id: int) -> list[ProcessedRequest]:
        ...
```

### Data

```python
@dataclass
class ProcessedRequest:
    reservation_id: int
    intent: str              # "early_checkin" or "late_checkout"
    result: str              # "approved", "declined", "pending_owner"
    processed_at: datetime
    request_id: str          # correlation ID
```

### Key rules

- A guest can request **both** early checkin AND late checkout — these are separate intents.
- A guest asking again for the same intent (e.g. "can I check in early?" twice) should NOT trigger a second cleaner query.
- If the guest changes the requested time for the same intent, that IS a new request.

### Adapters

| Adapter | Use |
|---------|-----|
| `SqliteRequestMemory` | Real — persistent storage |
| `InMemoryRequestMemory` | Test — dict-based |

### Contract test

Both adapters pass the same tests:
- `mark_processed` then `has_been_processed` returns True
- Different intents for same reservation are independent
- `get_history` returns chronological list

---

## 4. Overall pipeline wiring

### Data flow

```
Guest message (Smoobu)
    │
    ▼
[IntentClassifier]  →  ClassificationResult (structured data)
    │
    ▼
[Business rules]    →  Is this a repeat? (RequestMemory)
    │                   Is confidence high enough?
    │                   Does it need a follow-up question?
    │
    ▼
[CleanerNotifier]   →  Send query to cleaner
    │
    ▼
Cleaner replies
    │
    ▼
[ResponseParser]    →  ParsedResponse (structured data)
    │
    ▼
[Business rules]    →  Auto-reply? Or escalate to owner?
    │
    ├── confident ──→ [ReplyComposer] → send via Smoobu
    │
    └── unsure ────→ notify owner: "Suggested response for {apt} {booking}"
```

### Port summary

| Port | Responsibility | AI? |
|------|---------------|-----|
| `IntentClassifier` | Understand what the guest wants | Yes |
| `ResponseParser` | Understand what the cleaner said | Yes |
| `ReplyComposer` | Write a nice message to the guest | Yes |
| `RequestMemory` | Remember what's been processed | No |
| `SmoobuGateway` | Read/send guest messages | No |
| `CleanerNotifier` | Communicate with cleaning staff | No |

### Testing strategy

Every port has:
1. An **abstract contract test** (defines behavior)
2. A **simulator** (in-memory, deterministic, fast)
3. A **real adapter** (integration test, skipped without credentials)

The orchestrator is tested with all simulators — no network, no credentials, no AI API calls. Fast and deterministic.

---

## Suggested implementation order

1. `RequestMemory` port + in-memory simulator + contract tests
2. `IntentClassifier` port + simulator + contract tests
3. Wire intent classification into the pipeline (orchestrator)
4. `ResponseParser` port + simulator + contract tests
5. `ReplyComposer` port + simulator + contract tests
6. Wire response parsing + reply composition into the pipeline
7. Add real Claude API adapters for each AI port
8. Add owner notification port (Trello or simple email)
9. Add SQLite adapter for `RequestMemory`
