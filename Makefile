.DEFAULT_GOAL := help

.PHONY: help install format lint test test-all up up-ai up-apps down logs smoke compose-check clean

help:
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\n\n"} /^[a-zA-Z_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install the project and development dependencies
	uv sync --all-groups

format: ## Format Python source and tests
	uv run ruff format src tests apps
	uv run ruff check --fix src tests apps

lint: ## Run formatting, lint, and type checks
	uv run ruff format --check src tests apps
	uv run ruff check src tests apps
	uv run mypy src

test: ## Run fast unit, contract, and local integration tests
	uv run pytest tests/unit tests/contract tests/integration

test-all: ## Run all local test suites
	uv run pytest

up: ## Start required local services
	docker compose up -d --wait

up-ai: ## Start PostgreSQL, OpenSearch, and Ollama
	docker compose --profile ai up -d --wait

up-apps: ## Start PostgreSQL, API, and Streamlit
	docker compose --profile apps up -d --build --wait

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
