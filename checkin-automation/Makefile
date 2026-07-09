.PHONY: test test-integration run review review-ui fetch-threads deploy

# Database path (override with: make review DB_PATH=/path/to/checkin.db)
DB_PATH ?= data/checkin.db

# Hetzner server — configure 'hetzner' alias in ~/.ssh/config, or override:
#   make deploy SERVER=root@1.2.3.4
SERVER    ?= hetzner
REMOTE_DIR := /opt/checkin-automation

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

# Unit + simulator tests — no credentials needed, no external dependencies
IGNORE_TESTS := \
	--ignore=tests/test_cleaner_contract.py \
	--ignore=tests/test_intent_contract.py \
	--ignore=tests/test_intent_on_fixtures.py \
	--ignore=tests/test_response_contract.py

test:
	python -m pytest tests/ -v $(IGNORE_TESTS)

# Integration tests — requires ../.env with SMOOBU_API_KEY, ANTHROPIC_API_KEY, etc.
# Credentials live centrally at the repo root (see ../secrets/access-map.md).
test-integration:
	set -a && source ../.env && set +a && python -m pytest tests/ -v -s

# ---------------------------------------------------------------------------
# Run daemon locally (requires ../.env — central credentials at repo root)
# Required: SMOOBU_API_KEY, ANTHROPIC_API_KEY
# Optional: POLL_INTERVAL (default 60s), THREADS_CUTOFF_DAYS (default 7),
#           CLEANING_STAFF_CHANNEL (default console), CLEANER_NAME (default Marie),
#           DB_PATH (default data/checkin.db)
# ---------------------------------------------------------------------------

LOG_FILE ?= data/logs/daemon.log

run:
	mkdir -p data/logs
	set -a && source ../.env && set +a && venv/bin/python scripts/run.py 2>&1 | tee -a $(LOG_FILE)

# ---------------------------------------------------------------------------
# Review drafts
# CLI: make review              — list pending drafts
#      make review CMD="show 3" — show full draft #3
#      make review CMD="ok 3"   — approve draft #3
#      make review CMD="nok 3"  — reject draft #3
# ---------------------------------------------------------------------------

review:
	DB_PATH=$(DB_PATH) python scripts/review_drafts.py $(CMD)

# Web UI: make review-ui
# Requires: REVIEW_TOKEN env var (or in .env), DB_PATH
# Opens at http://localhost:8000
review-ui:
	set -a && source ../.env && set +a && \
	DB_PATH=$(DB_PATH) uvicorn src.web.app:app --reload --host 127.0.0.1 --port 8000

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

fetch-threads:
	set -a && source ../.env && set +a && python scripts/fetch_message_threads.py

# ---------------------------------------------------------------------------
# Build & Deploy to Hetzner
#
# Workflow:
#   make deploy   — rsync source to server, build there, restart services
#
# Both services use the same image (same Dockerfile, different command).
# Building on the server avoids transferring 400MB+ images over SSH; the
# server's layer cache makes rebuilds fast after the first one.
#
# Credentials live centrally at the repo root (../.env). The server keeps its own
# copy next to docker-compose.yml (docker-compose reads `.env` from its own dir).
#
# First-time server setup (manual, once):
#   ssh $(SERVER) 'mkdir -p $(REMOTE_DIR)'
#   scp ../.env $(SERVER):$(REMOTE_DIR)/.env
#
# The .env file is NEVER baked into the Docker image (.dockerignore excludes it).
# It lives only on the server and is read by docker-compose at container startup.
# To update secrets: scp ../.env $(SERVER):$(REMOTE_DIR)/.env && make deploy
# ---------------------------------------------------------------------------

deploy:
	@echo "→ Syncing source to $(SERVER):$(REMOTE_DIR)/"
	rsync -av --exclude='.env' --exclude='data/' --exclude='venv/' \
	    --exclude='__pycache__' --exclude='.git/' \
	    ./ $(SERVER):$(REMOTE_DIR)/
	@echo "→ Building images on server"
	ssh $(SERVER) 'cd $(REMOTE_DIR) && docker compose build'
	@echo "→ Restarting services"
	ssh $(SERVER) 'cd $(REMOTE_DIR) && docker compose up -d'
	@echo "→ Service status"
	ssh $(SERVER) 'cd $(REMOTE_DIR) && docker compose ps'
