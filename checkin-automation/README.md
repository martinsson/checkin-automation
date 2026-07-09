# checkin-automation

Python service that polls Smoobu for guest messages, classifies intent with Claude, and
orchestrates the guest ↔ host ↔ cleaner loop. Every outgoing message is saved as a draft for
the host to review. Part of the [checking-automation hub](../README.md); the wider tool
stack is documented in [`../integrations/`](../integrations/).

## Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Credentials live centrally at the repo root in `../.env` (template: `../.env.example`,
catalogue: `../secrets/access-map.md`). The Makefile targets source `../.env` automatically.

## Commands

| Command | What it does |
|---------|--------------|
| `make test` | Unit + simulator tests — no credentials, no network, no AI calls. |
| `make test-integration` | Integration tests (needs `../.env` with real keys). |
| `make run` | Run the daemon: poll Smoobu and process guest messages. |
| `make review` / `make review-ui` | Review pending drafts (CLI / web UI). |
| `make fetch-threads` | Fetch message threads (utility). |
| `make deploy` | rsync + build + restart on the server. |

## Architecture

Functional core / imperative shell behind ports & adapters. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and the capability specs in
[`openspec/specs/`](openspec/specs/). Business intent and invariants are in
[`../CLAUDE.md`](../CLAUDE.md).
