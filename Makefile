.DEFAULT_GOAL := help

.PHONY: help install format lint test test-all up down logs smoke compose-check clean

help:
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\n\n"} /^[a-zA-Z_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install the project and development dependencies
	uv sync --all-groups

format: ## Format Python source and tests
	uv run ruff format src tests
	uv run ruff check --fix src tests

lint: ## Run formatting, lint, and type checks
	uv run ruff format --check src tests
	uv run ruff check src tests
	uv run mypy src

test: ## Run fast unit and contract tests
	uv run pytest tests/unit tests/contract

test-all: ## Run all local test suites
	uv run pytest

up: ## Start required local services
	docker compose up -d --wait

down: ## Stop local services
	docker compose down

logs: ## Follow local service logs
	docker compose logs -f

smoke: ## Run the application smoke check
	uv run customer360 smoke

compose-check: ## Validate the Compose configuration
	docker compose config --quiet

clean: ## Remove disposable local Python artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage coverage.xml

