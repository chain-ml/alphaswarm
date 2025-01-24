.PHONY: format lint dev-lint

GIT_ROOT ?= $(shell git rev-parse --show-toplevel)

format:
	poetry run black .

dev-lint:
	poetry run black .
	poetry run mypy . || true
	poetry run ruff check . --fix || true
	poetry run isort .
#	pylint theoriq/. --max-line-length 120 --disable=R,C,I  --fail-under=9

lint:
	poetry run black . --check
	poetry run mypy .
	poetry run ruff check .
	poetry run isort . --check-only
#	pylint theoriq/. --max-line-length 120 --disable=R,C,I,E0401,W1203,W0107 --fail-under=9

test: 
	poetry run pytest tests/agents/test_agent.py

unit-tests:
	poetry run pytest tests/unit
