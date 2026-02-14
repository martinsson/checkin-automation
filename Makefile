test-adapter:
	set -a && source .env && set +a && pytest tests/ -v -s
