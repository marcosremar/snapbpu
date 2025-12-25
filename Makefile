# =============================================================================
# DumontCloud - Makefile
# =============================================================================
#
# Comandos principais:
#   make test          - Executa todos os testes (mock -> gpu)
#   make test-mock     - Apenas testes com mocks (rápido)
#   make test-gpu      - Testes de GPU real (shared paralelo, lifecycle sequencial)
#   make test-quick    - Mocks + smoke tests
#
# =============================================================================

.PHONY: help test test-mock test-gpu test-quick test-smoke test-full \
        test-shared test-lifecycle lint format clean install dev

# Default target
.DEFAULT_GOAL := help

# Colors
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

# Configuration
MOCK_WORKERS ?= 10
SHARED_WORKERS ?= 4
# LIFECYCLE_WORKERS = 1 to avoid Vast.ai rate limiting (429)
LIFECYCLE_WORKERS ?= 1
PYTEST_OPTS ?=

# =============================================================================
# Help
# =============================================================================

help: ## Show this help
	@echo ""
	@echo "$(CYAN)DumontCloud - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# =============================================================================
# Testing - Layered Execution
# =============================================================================

test: ## Run all tests (mock -> gpu) in layers
	@./scripts/run_tests.sh

test-mock: ## Run mock tests only (fast, no cost)
	@echo "$(CYAN)=== MOCK TESTS ($(MOCK_WORKERS) workers) ===$(NC)"
	pytest tests/backend/api/ -v --tb=short -m "not real" \
		--ignore=tests/backend/api/test_gpu_real.py \
		-n $(MOCK_WORKERS) --timeout=30 $(PYTEST_OPTS)

test-gpu: ## Run all GPU tests (shared parallel, lifecycle sequential)
	@echo "$(YELLOW)=== GPU REAL TESTS ===$(NC)"
	@echo "$(YELLOW)WARNING: This uses REAL Vast.ai credits!$(NC)"
	@echo ""
	@$(MAKE) test-shared
	@echo ""
	@$(MAKE) test-lifecycle

test-shared: ## Run shared GPU tests (parallel, 1 machine for all)
	@echo "$(CYAN)=== SHARED GPU TESTS ($(SHARED_WORKERS) workers, 1 shared machine) ===$(NC)"
	pytest tests/backend/api/test_gpu_real.py -v --tb=short \
		-m "uses_shared_machine" -n $(SHARED_WORKERS) --timeout=600 $(PYTEST_OPTS)

test-lifecycle: ## Run lifecycle GPU tests (SEQUENTIAL to avoid rate limit)
	@echo "$(CYAN)=== LIFECYCLE GPU TESTS (sequential to avoid rate limit) ===$(NC)"
	pytest tests/backend/api/test_gpu_real.py -v --tb=short \
		-m "creates_machine" -n $(LIFECYCLE_WORKERS) --timeout=600 $(PYTEST_OPTS)

test-smoke: ## Run smoke tests only (critical paths)
	@echo "$(CYAN)=== SMOKE TESTS ===$(NC)"
	pytest tests/backend/api/ -v --tb=short -m "smoke or critical" \
		-n $(MOCK_WORKERS) --timeout=30 $(PYTEST_OPTS)

test-quick: ## Run mock + smoke tests (fast validation)
	@echo "$(CYAN)=== QUICK TESTS ===$(NC)"
	@$(MAKE) test-mock
	@echo ""
	@echo "$(GREEN)Quick tests completed!$(NC)"

test-full: ## Run all tests with HTML report
	@./scripts/run_tests.sh full

test-api: ## Run all API tests (mock + real)
	@echo "$(CYAN)=== ALL API TESTS ===$(NC)"
	pytest tests/backend/api/ -v --tb=short -n $(MOCK_WORKERS) \
		--timeout=600 $(PYTEST_OPTS)

test-serverless: ## Run serverless tests only (sequential)
	@echo "$(CYAN)=== SERVERLESS TESTS ===$(NC)"
	pytest tests/backend/api/ -v --tb=short -m "serverless" \
		-n $(LIFECYCLE_WORKERS) --timeout=600 $(PYTEST_OPTS)

test-failover: ## Run failover tests only (sequential)
	@echo "$(CYAN)=== FAILOVER TESTS ===$(NC)"
	pytest tests/backend/api/ -v --tb=short -m "failover" \
		-n $(LIFECYCLE_WORKERS) --timeout=600 $(PYTEST_OPTS)

test-coldstart: ## Run coldstart tests only (sequential)
	@echo "$(CYAN)=== COLDSTART TESTS ===$(NC)"
	pytest tests/backend/api/test_coldstart_failover.py -v --tb=short \
		-n $(LIFECYCLE_WORKERS) --timeout=600 $(PYTEST_OPTS)

test-e2e: ## Run E2E complete tests (sequential)
	@echo "$(CYAN)=== E2E TESTS ===$(NC)"
	pytest tests/backend/api/test_e2e_complete.py -v --tb=short \
		-n $(LIFECYCLE_WORKERS) --timeout=600 $(PYTEST_OPTS)

test-advanced: ## Run advanced features tests (sequential)
	@echo "$(CYAN)=== ADVANCED FEATURES TESTS ===$(NC)"
	pytest tests/backend/api/test_advanced_features_real.py -v --tb=short \
		-n $(LIFECYCLE_WORKERS) --timeout=600 $(PYTEST_OPTS)

# =============================================================================
# Test with specific patterns
# =============================================================================

test-k: ## Run tests matching pattern: make test-k PATTERN=serverless
ifndef PATTERN
	$(error PATTERN is required. Usage: make test-k PATTERN=serverless)
endif
	pytest tests/backend/api/ -v --tb=short -k "$(PATTERN)" \
		-n $(MOCK_WORKERS) --timeout=600 $(PYTEST_OPTS)

test-file: ## Run specific test file: make test-file FILE=test_foo.py
ifndef FILE
	$(error FILE is required. Usage: make test-file FILE=test_foo.py)
endif
	pytest tests/backend/api/$(FILE) -v --tb=short \
		-n $(LIFECYCLE_WORKERS) --timeout=600 $(PYTEST_OPTS)

# =============================================================================
# Test utilities
# =============================================================================

test-lf: ## Re-run last failed tests
	pytest tests/backend/api/ -v --tb=short --lf $(PYTEST_OPTS)

test-ff: ## Run failed tests first, then rest
	pytest tests/backend/api/ -v --tb=short --ff \
		-n $(MOCK_WORKERS) $(PYTEST_OPTS)

test-cov: ## Run tests with coverage report
	pytest tests/backend/api/ -v --tb=short \
		--cov=src --cov-report=html --cov-report=term \
		-n $(MOCK_WORKERS) --timeout=600 $(PYTEST_OPTS)
	@echo "$(GREEN)Coverage report: htmlcov/index.html$(NC)"

test-watch: ## Run tests in watch mode (requires pytest-watch)
	ptw tests/backend/api/ -- -v --tb=short -m "not real" \
		-n $(MOCK_WORKERS) --timeout=30

# =============================================================================
# Development
# =============================================================================

install: ## Install dependencies
	pip install -e ".[dev]"

dev: ## Setup development environment
	pip install -e ".[dev]"
	pre-commit install

lint: ## Run linters
	ruff check src tests
	mypy src

format: ## Format code
	ruff format src tests
	ruff check --fix src tests

clean: ## Clean cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage htmlcov reports 2>/dev/null || true
	@echo "$(GREEN)Cleaned!$(NC)"

# =============================================================================
# Server
# =============================================================================

run: ## Run development server
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Run production server
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
