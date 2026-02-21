# Project: checking-automation

## Business Intent

The core purpose of this system is two things:

1. **Always respond to guest messages in near-real-time.** A guest who sends a message at midnight about an early check-in should get an acknowledgment quickly, not when the host wakes up. The system must never let a message sit unhandled.

2. **Automate the three-way conversation between guest, host, and cleaner.** When a guest asks for something that requires the cleaner's input (early check-in, late checkout), the system orchestrates the full loop: acknowledge the guest, ask the cleaner, relay the answer back to the guest — all without the host having to manage the thread manually.

The host is not removed from the loop — every outgoing message is drafted and reviewed before sending. But the host's job changes from "manage every message" to "approve drafts and handle exceptions." The goal is to make hosting feel effortless for routine requests.

## Key Invariants

- **Draft-first as validation.** Every outgoing message is saved as a draft before sending. This is a temporary mechanism — the owner reviews drafts to validate that the AI is producing good output. Once confidence in the AI is established, this step is expected to be automated away.
- **Idempotency.** A guest message that has already been processed for a given intent is never processed again, no matter how many poll cycles see it.
- **AI classifies, code decides, AI drafts.** Intent classification and message composition use Claude. Business rules (idempotency, routing, escalation) are plain Python.

## Architecture

```
Guest message (Smoobu)
    → AI classifies intent
    → Code checks idempotency + memory
    → AI drafts acknowledgment + cleaner query (saved as drafts)
    → Owner reviews and sends
    → Cleaner replies
    → AI parses reply + drafts guest response (saved as draft)
    → Owner reviews and sends
```

## External API References

- **Smoobu API docs:** https://docs.smoobu.com/#introduction
- **Smoobu base URL:** `https://login.smoobu.com/api`
  - `GET  /reservations` — list reservations (filter: `arrivalFrom`, `arrivalTo`, `apartmentId`)
  - `GET  /reservations/{id}/messages` — fetch message thread
  - `POST /reservations/{id}/messages/send-message-to-guest` — send to guest

## Tech Stack

- Python 3.11+, async/await throughout
- Claude API (Haiku for intent/response, via `anthropic` SDK)
- SQLite for persistence (`data/checkin.db`), in-memory (`:memory:`) for tests
- Port/adapter architecture — every external dependency behind an ABC
- pytest + pytest-asyncio, simulator adapters for network-free tests
