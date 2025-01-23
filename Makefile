.PHONY: format lint dev-lint

GIT_ROOT ?= $(shell git rev-parse --show-toplevel)

format:
	poetry run black .

dev-lint:
	poetry run black .
	poetry run mypy .
	poetry run ruff check . --fix
#	isort .
#	pylint theoriq/. --max-line-length 120 --disable=R,C,I  --fail-under=9

lint:
	poetry run black . --check
	poetry run mypy .
	poetry run ruff check .
#	pylint theoriq/. --max-line-length 120 --disable=R,C,I,E0401,W1203,W0107 --fail-under=9
#	isort . --check-only

test: 
	poetry run pytest tests/agents/test_agent.py

unit-tests:
	poetry run pytest tests/unit
