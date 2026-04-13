.PHONY: run test lint fmt clean

run:
	uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

test:
	pytest backend/tests/ -v --tb=short

lint:
	ruff check agents/ backend/ orchestrator/ schemas/ utils/

fmt:
	ruff format agents/ backend/ orchestrator/ schemas/ utils/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache
