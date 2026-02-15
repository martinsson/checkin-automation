test:
	python -m pytest tests/ -v

test-integration:
	set -a && source .env && set +a && python -m pytest tests/ -v -s
