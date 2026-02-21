.PHONY: test test-integration run review review-ui fetch-threads deploy

# Database path (override with: make review DB_PATH=/path/to/checkin.db)
DB_PATH ?= data/checkin.db

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

# Integration tests — requires .env with SMOOBU_API_KEY, ANTHROPIC_API_KEY, etc.
test-integration:
	set -a && source .env && set +a && python -m pytest tests/ -v -s

# ---------------------------------------------------------------------------
# Run daemon (requires .env)
# Required: SMOOBU_API_KEY, ANTHROPIC_API_KEY
# Optional: POLL_INTERVAL (default 60s), THREADS_CUTOFF_DAYS (default 7),
#           CLEANING_STAFF_CHANNEL (default console), CLEANER_NAME (default Marie),
#           DB_PATH (default data/checkin.db)
# ---------------------------------------------------------------------------

run:
	set -a && source .env && set +a && python scripts/run.py

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
	set -a && source .env && set +a && \
	DB_PATH=$(DB_PATH) uvicorn src.web.app:app --reload --host 127.0.0.1 --port 8000

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

fetch-threads:
	set -a && source .env && set +a && python scripts/fetch_message_threads.py

# ---------------------------------------------------------------------------
# Deploy (Docker Compose)
# Builds images and (re)starts daemon + web services in the background.
# Requires docker and docker-compose on the host.
# ---------------------------------------------------------------------------

deploy:
	docker compose build
	docker compose up -d
	docker compose ps
