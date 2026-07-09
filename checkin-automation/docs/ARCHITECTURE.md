# Architecture — checkin-automation

> Slim, current overview of the app as it actually runs. For per-capability detail and
> change history, see [`../openspec/specs/`](../openspec/specs/). For the business intent
> and invariants, see [`../../CLAUDE.md`](../../CLAUDE.md).

## What it does

Polls Smoobu for guest messages, classifies intent with Claude, and orchestrates the
guest ↔ host ↔ cleaner loop. Every outgoing message is saved as a **draft** for the host to
review before sending (a temporary validation step). Door codes are **not** handled here —
that's in [Beds24 + igloohome + Make](../../integrations/door-codes.md).

## Shape: functional core / imperative shell

```
Smoobu (poll) ──► classify intent (Claude) ──► decide (pure Python) ──► draft (Claude)
                                                     │                       │
                                              idempotency + memory      saved as drafts
                                                                             │
                                              host reviews/sends ◄───────────┘
                                                     │
                                cleaner replies (email) ──► parse + draft guest response
```

- **`src/domain/`** — pure functions, no I/O (the functional core): `guest_request`,
  `cleaner_response`, `draft_dispatch`. All business decisions live here.
- **`src/ports/`** — abstract contracts (ABCs) for every external dependency: `smoobu`,
  `intent`, `response`, `cleaner`, `memory`, `reservation_cache`.
- **`src/adapters/`** — real implementations: `smoobu_client`, `claude_intent`,
  `claude_response`, `sqlite_memory`, `sqlite_reservation_cache`.
- **`src/simulators/`** — in-memory, deterministic doubles for each port (network-free tests).
- **`src/communication/`** — cleaner channel (email now, swappable via `factory`).
- **`src/shell/`** — the imperative shell that wires it together: `main_cycle`, `pollers/`
  (guest messages, cleaner responses), `handlers/`.
- **`src/prompts/`** — Claude prompt templates (loaded relative to the package).
- **`src/web/`** — FastAPI draft-review UI (`make review-ui`).

## Key invariants

- **Draft-first** — nothing is sent without a reviewed draft (temporary; see CLAUDE.md).
- **Idempotency** on `(reservation_id, intent)` — a message is never processed twice.
- **AI classifies, code decides, AI drafts** — business rules are plain Python.

## Runtime & testing

- Python 3.11+, async throughout. Claude (Haiku) for intent + drafting.
- SQLite at `data/checkin.db` (`:memory:` in tests). Entry point: `scripts/run.py` (`make run`).
- Every port has an **abstract contract test** + a **simulator** + a **real adapter**
  (integration test, skipped without credentials). The orchestrator is tested with all
  simulators — no network, no credentials, no AI calls. See `make test`.
