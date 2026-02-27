## 1. Dependencies and Project Structure

- [x] 1.1 Add `fastapi`, `uvicorn[standard]`, `jinja2` to `requirements.txt`
- [x] 1.2 Create `src/web/__init__.py` to make it a package
- [x] 1.3 Create `src/web/templates/` directory with a `base.html` layout (mobile-friendly, minimal CSS)

## 2. Auth Module

- [x] 2.1 Create `src/web/auth.py` — reads `REVIEW_TOKEN` from env (exit with error if missing), validates cookie on requests, sets httponly cookie on successful login
- [x] 2.2 Add login route (`GET /login` renders form, `POST /login` validates token and redirects)

## 3. Draft Review Routes

- [x] 3.1 Create `src/web/routes.py` — draft list route (`GET /`) fetching pending drafts from `SqliteRequestMemory` and rendering `drafts.html`
- [x] 3.2 Add draft detail route (`GET /drafts/{id}`) rendering `draft_detail.html` with guest message and draft body
- [x] 3.3 Add approve route (`POST /drafts/{id}/approve`) calling `mem.review_draft(id, "ok")` and redirecting to `/`
- [x] 3.4 Add reject route (`POST /drafts/{id}/reject`) accepting optional `actual_message_sent` and `owner_comment` form fields, calling `mem.review_draft(id, "nok", ...)` and redirecting to `/`

## 4. FastAPI App Entry Point

- [x] 4.1 Create `src/web/app.py` — instantiates FastAPI, mounts routes, validates `REVIEW_TOKEN` at startup, configures `SqliteRequestMemory` from `DB_PATH` env var
- [x] 4.2 Create Jinja2 templates: `login.html`, `drafts.html` (list), `draft_detail.html` (detail + approve/reject form)

## 5. Docker Setup

- [x] 5.1 Create `Dockerfile` — `python:3.11-slim` base, copy source, `pip install -r requirements.txt`, no default `CMD` (overridden by Compose)
- [x] 5.2 Create `docker-compose.yml` — `daemon` service (`python scripts/run.py`), `web` service (`uvicorn src.web.app:app --host 0.0.0.0 --port 8000`), shared `data` volume mounted at `/data`, both services use `env_file: .env`, `restart: unless-stopped`
- [x] 5.3 Update `.env.example` with `REVIEW_TOKEN=` and `DB_PATH=/data/checkin.db`

## 6. Verification

- [x] 6.1 Run `docker compose build` and verify both services start without errors
- [x] 6.2 Smoke test: navigate to `http://localhost:8000`, log in with `REVIEW_TOKEN`, confirm draft list renders
- [x] 6.3 Approve and reject a draft via the UI; confirm verdict is persisted in SQLite
- [x] 6.4 Verify unauthenticated access to `/` redirects to `/login`
