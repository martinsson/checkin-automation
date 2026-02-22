## Context

The daemon and draft-review workflow currently run on a local machine: `scripts/run.py` polls Smoobu, and `scripts/review_drafts.py` opens the SQLite file directly. This means the daemon stops when the laptop sleeps, and review requires filesystem access — no mobile access possible.

The target state is a two-service Docker Compose setup: a `daemon` service that runs the polling loop continuously, and a `web` service that exposes a mobile-friendly draft review UI over HTTP. Both share the same SQLite database via a named volume.

## Goals / Non-Goals

**Goals:**
- Daemon runs 24/7 independent of local machine uptime
- Draft review accessible from any device (mobile browser) via HTTPS
- Local development and production use the same `docker-compose.yml`
- SQLite data persists across container rebuilds and redeploys
- Simple token auth (one env var, no accounts)

**Non-Goals:**
- Multi-user access or role-based permissions
- Sending messages directly from the web UI (approve = save verdict to DB; actual send is still a future step)
- Real-time push notifications (polling the list page is sufficient for now)
- Replacing the existing CLI review script (it stays, still works locally)

## Decisions

### Single Dockerfile, two Compose services

Both `daemon` and `web` use the same Docker image, differentiated by their `command`. This avoids maintaining two Dockerfiles and ensures the same Python environment. The image is a `python:3.11-slim` base with all dependencies installed.

**Alternative considered:** Separate Dockerfiles per service. Rejected — they share the same codebase and dependencies; separate files just add drift risk.

### Separate Compose services (not asyncio background task in web process)

The daemon runs as its own Compose service (`python scripts/run.py`), not as an asyncio background task inside the FastAPI process.

**Rationale:** Clean separation of concerns. Crash isolation — a daemon error doesn't take down the review UI. Independent restart policies. Compose already manages process lifecycle, so we don't need to re-implement that in Python.

**Alternative considered:** Single FastAPI process with lifespan-managed background task. Simpler initially, but daemon crashes become invisible (the HTTP server stays up, no restarts) and mixing poll logic with web logic complicates future changes.

### FastAPI + Jinja2 server-side rendering

The web UI is server-side rendered HTML with minimal CSS. No JavaScript framework. FastAPI serves HTML responses via Jinja2 templates; approve/reject are plain HTML form POSTs.

**Rationale:** Mobile-first simplicity. Works without JavaScript. No build step. Jinja2 is a single pip install. The review workflow is simple enough that a SPA adds no value.

**Alternative considered:** React/Vue SPA + REST API. Rejected — overkill for a single-user review flow. Adds build tooling, more dependencies, and complexity with no benefit.

### Token auth via browser cookie

Auth is a single pre-shared token stored in `REVIEW_TOKEN` env var. The login page accepts the token, sets a `session` cookie (httponly, samesite=lax), and all subsequent requests validate the cookie. API access (future CLI use) accepts `Authorization: Bearer <token>` as an alternative.

**Rationale:** No user accounts needed (single owner). Cookie-based keeps the browser session alive without re-entering the token on every page. One env var, no database, no JWT library.

**Alternative considered:** HTTP Basic Auth via nginx. Simpler but worse UX on mobile (browser native dialog, no "remember me"). Also couples auth to infrastructure layer.

### SQLite on a named Docker volume

Both services mount the same named volume at `/data`. `DB_PATH` defaults to `/data/checkin.db` in the container environment. The volume is declared in `docker-compose.yml` and persists across `docker compose up/down` and image rebuilds.

**Rationale:** SQLite needs no extra infrastructure. A named volume is the standard Docker pattern for persistent data. Survives `docker compose down` (but not `docker compose down -v`).

**Alternative considered:** Bind mount to a host directory (e.g., `./data:/data`). Also fine, slightly more visible on disk. Named volume chosen for portability across dev machines and cloud hosts.

## Risks / Trade-offs

- **SQLite concurrent writes** → Daemon writes processed requests/drafts; web writes draft verdicts. SQLite WAL mode handles this safely for this low-concurrency workload. Risk is low.
- **No HTTPS out of the box** → docker-compose.yml exposes port 8000 only. For cloud deployment, a reverse proxy (nginx with certbot, or Fly.io's automatic TLS) must terminate TLS in front. Risk: token sent in plaintext if deployed without TLS. Mitigation: document that production MUST sit behind TLS.
- **Token in env var** → If the container env is exposed, the token leaks. Mitigation: keep `REVIEW_TOKEN` in `.env` (gitignored), use Docker secrets for production if needed.
- **No draft-send from UI** → Approve saves the verdict; the actual Smoobu send is still a manual step. This is intentional for the current validation phase but may feel incomplete.

## Migration Plan

1. Add `fastapi`, `uvicorn[standard]`, `jinja2` to `requirements.txt`
2. Create `Dockerfile` and `docker-compose.yml`
3. Create `src/web/` module with app, routes, auth, templates
4. Set `DB_PATH=/data/checkin.db` in container env; existing local path (`data/checkin.db`) still works for non-container use
5. Test locally: `docker compose up` → visit `http://localhost:8000`
6. Deploy to cloud: copy `docker-compose.yml` + `.env` to host, `docker compose up -d`

No data migration required. SQLite schema is unchanged.

## Open Questions

- Should the web UI also expose a `GET /api/drafts` JSON endpoint for future CLI use, or is the cookie-only HTML interface sufficient for now?
- Fly.io vs bare VPS — deferred; `docker-compose.yml` works on both. Cloud target is out of scope for this change.
