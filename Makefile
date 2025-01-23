.PHONY: format lint dev-lint

GIT_ROOT ?= $(shell git rev-parse --show-toplevel)

format:
	black .

dev-lint:
	black .
	mypy .
	ruff check . --fix
#	isort .
#	pylint theoriq/. --max-line-length 120 --disable=R,C,I  --fail-under=9

lint:
	black . --check
	mypy .
	ruff check .
#	pylint theoriq/. --max-line-length 120 --disable=R,C,I,E0401,W1203,W0107 --fail-under=9
#	isort . --check-only

test: 
	python -m pytest tests/agents/test_agent.py

unit-tests:
	python -m pytest tests/unit
