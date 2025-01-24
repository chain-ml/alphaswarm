# Define all phony targets
.PHONY: help format lint dev-lint tests unit-tests all-tests

# Default git root path
GIT_ROOT ?= $(shell git rev-parse --show-toplevel)

# Default target, shows help
help:
	@echo "Available commands:"
	@echo "  format            - Format code using black and isort"
	@echo "  dev-lint          - Run all linters in fix mode (for development)"
	@echo "  lint              - Run all linters in check mode (for CI)"
	@echo "  integration-tests - Run all integration tests"
	@echo "  unit-tests        - Run all unit tests"
	@echo "  all-tests         - Run all tests"

# Code formatting and linting
format:
	poetry run black .
	poetry run isort .

dev-lint: format
	poetry run mypy . || true
	poetry run ruff check . --fix || true
#	poetry pylint alphaswarm/. --max-line-length 120 --disable=R,C,I  --fail-under=9

lint:
	poetry run black . --check
	poetry run isort . --check-only
	poetry run mypy .
	poetry run ruff check .
#	poetry pylint alphaswarm/. --max-line-length 120 --disable=R,C,I,E0401,W1203,W0107 --fail-under=9

# Testing
integration-tests:
	poetry run pytest tests/integration

unit-tests:
	poetry run pytest tests/unit

all-tests: unit-tests integration-tests
