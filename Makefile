test:
	python -m pytest tests/ -v

test-integration:
	set -a && source .env && set +a && python -m pytest tests/ -v -s

review:
	python scripts/review_drafts.py

fetch-threads:
	set -a && source .env && set +a && python scripts/fetch_message_threads.py

run:
	set -a && source .env && set +a && python scripts/run.py
