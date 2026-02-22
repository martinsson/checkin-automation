## Why

The system currently runs only on a local machine, meaning polling stops when the laptop sleeps and draft review requires direct filesystem access. Moving to a cloud-hosted container lets the daemon run continuously and makes draft review accessible from any device — including mobile — via a lightweight web UI.

## What Changes

- Add a `Dockerfile` (single image used by both services)
- Add `docker-compose.yml` with two services (`daemon`, `web`) sharing a SQLite volume
- Add `src/web/` — FastAPI app serving a mobile-friendly draft review UI
  - Server-side rendered (Jinja2 templates), no JS framework
  - Token-based auth: env var `REVIEW_TOKEN` → browser cookie after login
  - Endpoints: list drafts, view draft, approve, reject
- `DB_PATH` defaults to `/data/checkin.db` when running in container
- `scripts/run.py` continues to be the daemon entrypoint (no changes required)

## Capabilities

### New Capabilities
- `draft-review-api`: HTTP interface for listing, viewing, approving, and rejecting AI-generated drafts — replaces direct SQLite access with a web UI accessible from any device

### Modified Capabilities
<!-- No existing specs change requirements — daemon-runner, request-memory, etc. are unchanged in behaviour -->

## Impact

- New Python dependency: `fastapi`, `uvicorn`, `jinja2`
- New files: `Dockerfile`, `docker-compose.yml`, `src/web/app.py`, `src/web/routes.py`, `src/web/auth.py`, `src/web/templates/`
- `DB_PATH` env var must resolve to a path inside the shared Docker volume (`/data/checkin.db`) when running in containers
- No changes to existing adapters, pipeline, or daemon logic
