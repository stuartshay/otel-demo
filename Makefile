# =============================================================================
# otel-demo Makefile
# =============================================================================

.PHONY: help setup install dev start stop restart reload clean lint format test docker-build docker-run docker-push all verify logs

# Default target
.DEFAULT_GOAL := help

# Variables
DOCKER_IMAGE := stuartshay/otel-demo
DOCKER_TAG := latest
PYTHON_VERSION := 3.12
VENV_DIR := venv
PID_FILE := .otel-demo.pid
LOG_FILE := logs/otel-demo.log

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(GREEN)otel-demo Makefile Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# =============================================================================
# Setup and Installation
# =============================================================================

setup: ## Run initial project setup (create venv, install dependencies)
	@echo "$(YELLOW)Running setup script...$(NC)"
	@bash setup.sh
	@echo "$(GREEN)✓ Setup complete$(NC)"

install: ## Install Python dependencies
	@echo "$(YELLOW)Installing dependencies...$(NC)"
	@test -d $(VENV_DIR) || python3 -m venv $(VENV_DIR)
	@. $(VENV_DIR)/bin/activate && pip install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

install-dev: ## Install development dependencies (including test tools)
	@echo "$(YELLOW)Installing development dependencies...$(NC)"
	@. $(VENV_DIR)/bin/activate && pip install -r requirements.txt
	@. $(VENV_DIR)/bin/activate && pip install pytest pytest-cov pytest-flask ruff mypy
	@echo "$(GREEN)✓ Development dependencies installed$(NC)"

clean: ## Clean build artifacts and cache
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -f $(PID_FILE)
	@echo "$(GREEN)✓ Cleaned$(NC)"

clean-all: clean ## Clean everything including venv
	@echo "$(YELLOW)Removing virtual environment...$(NC)"
	@rm -rf $(VENV_DIR)
	@echo "$(GREEN)✓ Deep clean complete$(NC)"

# =============================================================================
# Development Server
# =============================================================================

dev: start ## Alias for start (run in development mode)

start: ## Start development server (port 8080)
	@echo "$(YELLOW)Starting otel-demo server...$(NC)"
	@if [ -f $(PID_FILE) ]; then \
		echo "$(RED)✗ Server already running (PID: $$(cat $(PID_FILE)))$(NC)"; \
		exit 1; \
	fi
	@mkdir -p logs
	@echo "$(YELLOW)Loading environment variables from .env...$(NC)"
	@(set -a; . ./.env; set +a; \
	 . $(VENV_DIR)/bin/activate && \
	 python run.py > $(LOG_FILE) 2>&1 & echo $$! > $(PID_FILE))
	@sleep 2
	@if [ -f $(PID_FILE) ] && ps -p $$(cat $(PID_FILE)) > /dev/null 2>&1; then \
		echo "$(GREEN)✓ Server started (PID: $$(cat $(PID_FILE)))$(NC)"; \
		echo "$(GREEN)✓ API available at http://localhost:8080$(NC)"; \
		echo "$(GREEN)✓ Swagger UI at http://localhost:8080/apidocs$(NC)"; \
		echo "$(YELLOW)  Use 'make logs' to view output$(NC)"; \
		echo "$(YELLOW)  Use 'make stop' to stop the server$(NC)"; \
	else \
		echo "$(RED)✗ Server failed to start. Check $(LOG_FILE) for errors$(NC)"; \
		rm -f $(PID_FILE); \
		exit 1; \
	fi

start-fg: ## Start server in foreground (for debugging)
	@echo "$(YELLOW)Starting otel-demo server in foreground...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)Error: .env file not found. Please create .env before starting server.$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Loading environment variables from .env...$(NC)"
	@set -a; . ./.env; set +a; . $(VENV_DIR)/bin/activate && python run.py

stop: ## Stop development server
	@echo "$(YELLOW)Stopping otel-demo server...$(NC)"
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		if ps -p $$PID > /dev/null 2>&1; then \
			kill $$PID && echo "$(GREEN)✓ Server stopped (PID: $$PID)$(NC)"; \
		else \
			echo "$(YELLOW)Server not running (stale PID file)$(NC)"; \
		fi; \
		rm -f $(PID_FILE); \
	else \
		echo "$(YELLOW)No PID file found. Checking for running processes...$(NC)"; \
		pkill -f "python.*run.py" && echo "$(GREEN)✓ Stopped running server$(NC)" || echo "$(YELLOW)No server process found$(NC)"; \
	fi

restart: stop start ## Restart development server

reload: ## Reload server (restart development server)
	@echo "$(YELLOW)Reloading server (stop + start)...$(NC)"
	@$(MAKE) restart

status: ## Check server status
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		if ps -p $$PID > /dev/null 2>&1; then \
			echo "$(GREEN)✓ Server running (PID: $$PID)$(NC)"; \
			echo "  API: http://localhost:8080"; \
			echo "  Swagger: http://localhost:8080/apidocs"; \
			echo "  Health: http://localhost:8080/health"; \
		else \
			echo "$(RED)✗ Server not running (stale PID file)$(NC)"; \
		fi; \
	else \
		echo "$(YELLOW)Server not running$(NC)"; \
	fi

logs: ## Tail server logs
	@if [ -f $(LOG_FILE) ]; then \
		echo "$(YELLOW)Tailing logs (Ctrl+C to stop)...$(NC)"; \
		tail -f $(LOG_FILE); \
	else \
		echo "$(RED)✗ Log file not found: $(LOG_FILE)$(NC)"; \
		echo "$(YELLOW)  Start the server with 'make start' first$(NC)"; \
	fi

logs-view: ## View all server logs
	@if [ -f $(LOG_FILE) ]; then \
		less $(LOG_FILE); \
	else \
		echo "$(RED)✗ Log file not found: $(LOG_FILE)$(NC)"; \
	fi

# =============================================================================
# Code Quality
# =============================================================================

lint: ## Run ruff linter
	@echo "$(YELLOW)Running linter...$(NC)"
	@. $(VENV_DIR)/bin/activate && ruff check . || echo "$(YELLOW)Install ruff: pip install ruff$(NC)"
	@echo "$(GREEN)✓ Linting complete$(NC)"

lint-fix: ## Fix linting issues automatically
	@echo "$(YELLOW)Fixing lint issues...$(NC)"
	@. $(VENV_DIR)/bin/activate && ruff check --fix . || echo "$(YELLOW)Install ruff: pip install ruff$(NC)"
	@echo "$(GREEN)✓ Fixes applied$(NC)"

format: ## Format code with ruff
	@echo "$(YELLOW)Formatting code...$(NC)"
	@. $(VENV_DIR)/bin/activate && ruff format . || echo "$(YELLOW)Install ruff: pip install ruff$(NC)"
	@echo "$(GREEN)✓ Formatting complete$(NC)"

format-check: ## Check code formatting
	@echo "$(YELLOW)Checking formatting...$(NC)"
	@. $(VENV_DIR)/bin/activate && ruff format --check . || echo "$(YELLOW)Install ruff: pip install ruff$(NC)"

type-check: ## Run mypy type checking
	@echo "$(YELLOW)Running type check...$(NC)"
	@. $(VENV_DIR)/bin/activate && mypy app/ || echo "$(YELLOW)Install mypy: pip install mypy$(NC)"
	@echo "$(GREEN)✓ Type check complete$(NC)"

shellcheck: ## Check shell scripts
	@echo "$(YELLOW)Checking shell scripts...$(NC)"
	@shellcheck setup.sh start-dev.sh || echo "$(YELLOW)Install shellcheck: apt-get install shellcheck$(NC)"
	@echo "$(GREEN)✓ Shell scripts checked$(NC)"

# =============================================================================
# Testing
# =============================================================================

test: ## Run pytest tests
	@echo "$(YELLOW)Running tests...$(NC)"
	@. $(VENV_DIR)/bin/activate && pytest tests/ || echo "$(YELLOW)Install pytest: pip install pytest$(NC)"
	@echo "$(GREEN)✓ Tests complete$(NC)"

test-cov: ## Run tests with coverage report
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	@. $(VENV_DIR)/bin/activate && pytest --cov=app --cov-report=term-missing tests/ || echo "$(YELLOW)Install pytest-cov: pip install pytest-cov$(NC)"

test-verbose: ## Run tests in verbose mode
	@. $(VENV_DIR)/bin/activate && pytest -v tests/

test-watch: ## Run tests in watch mode
	@. $(VENV_DIR)/bin/activate && pytest-watch tests/

# =============================================================================
# Database
# =============================================================================

db-test: ## Test database connection
	@echo "$(YELLOW)Testing database connection...$(NC)"
	@set -a; . ./.env; set +a; \
	. $(VENV_DIR)/bin/activate && \
	python -c "from app.services.database import DatabaseService; from app.config import Config; \
	config = Config.from_env(); db = DatabaseService(config); db.initialize(); \
	print('✓ Database connection successful') if db.health_check() else print('✗ Database connection failed')"

db-table-count: ## Show table count in database
	@echo "$(YELLOW)Querying database table count...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)Error: .env file not found. Please create .env with database credentials.$(NC)"; \
		exit 1; \
	fi
	@set -a; . ./.env; set +a; \
	. $(VENV_DIR)/bin/activate && \
	python -c "import psycopg2; \
	conn = psycopg2.connect(host='$${PGBOUNCER_HOST}', port='$${PGBOUNCER_PORT}', dbname='$${POSTGRES_DB}', user='$${POSTGRES_USER}', password='$${POSTGRES_PASSWORD}'); \
	cur = conn.cursor(); \
	cur.execute(\"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'\"); \
	count = cur.fetchone()[0]; \
	print(f'Total tables in $${POSTGRES_DB}: {count}')"

db-locations: ## Query location records from database
	@echo "$(YELLOW)Querying location records...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)Error: .env file not found. Please create .env with database credentials.$(NC)"; \
		exit 1; \
	fi
	@set -a; . ./.env; set +a; \
	. $(VENV_DIR)/bin/activate && \
	python -c "import psycopg2; \
	conn = psycopg2.connect(host='$${PGBOUNCER_HOST}', port='$${PGBOUNCER_PORT}', dbname='$${POSTGRES_DB}', user='$${POSTGRES_USER}', password='$${POSTGRES_PASSWORD}'); \
	cur = conn.cursor(); \
	cur.execute(\"SELECT COUNT(*) FROM locations\"); \
	count = cur.fetchone()[0]; \
	print(f'Total location records in $${POSTGRES_DB}: {count}')"

# =============================================================================
# Docker
# =============================================================================

docker-build: ## Build Docker image
	@echo "$(YELLOW)Building Docker image...$(NC)"
	@docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .
	@echo "$(GREEN)✓ Docker image built: $(DOCKER_IMAGE):$(DOCKER_TAG)$(NC)"

docker-run: ## Run Docker container locally (port 8080)
	@echo "$(YELLOW)Running Docker container...$(NC)"
	@echo "$(YELLOW)Loading environment from .env...$(NC)"
	@docker run -p 8080:8080 --name otel-demo --rm --env-file .env $(DOCKER_IMAGE):$(DOCKER_TAG)

docker-run-bg: ## Run Docker container in background
	@echo "$(YELLOW)Running Docker container in background...$(NC)"
	@docker run -d -p 8080:8080 --name otel-demo --env-file .env $(DOCKER_IMAGE):$(DOCKER_TAG)
	@echo "$(GREEN)✓ Container running$(NC)"
	@echo "  API: http://localhost:8080"
	@echo "  Use 'make docker-logs' to view output"

docker-stop: ## Stop Docker container
	@echo "$(YELLOW)Stopping Docker container...$(NC)"
	@docker stop otel-demo || true
	@echo "$(GREEN)✓ Container stopped$(NC)"

docker-logs: ## View Docker container logs
	@docker logs -f otel-demo

docker-push: ## Push Docker image to registry
	@echo "$(YELLOW)Pushing Docker image...$(NC)"
	@docker push $(DOCKER_IMAGE):$(DOCKER_TAG)
	@echo "$(GREEN)✓ Image pushed$(NC)"

docker-shell: ## Open shell in running Docker container
	@docker exec -it otel-demo /bin/bash

# =============================================================================
# Convenience Targets
# =============================================================================

all: clean install lint format test ## Clean, install, lint, format, and test

check: lint format-check type-check test ## Run all checks

pre-commit: lint format-check type-check ## Run pre-commit checks locally

pre-push: check ## Run pre-push checks

verify: ## Verify environment and dependencies
	@echo "$(YELLOW)Verifying environment...$(NC)"
	@echo "Python: $$(python3 --version)"
	@echo "pip: $$(pip3 --version)"
	@if [ -d $(VENV_DIR) ]; then \
		echo "$(GREEN)✓ Virtual environment exists$(NC)"; \
	else \
		echo "$(RED)✗ Virtual environment not found. Run 'make setup'$(NC)"; \
	fi
	@if [ -f .env ]; then \
		echo "$(GREEN)✓ .env file exists$(NC)"; \
		set -a; . ./.env; set +a; \
		if [ -z "$$POSTGRES_USER" ]; then \
			echo "$(RED)✗ POSTGRES_USER not set in .env$(NC)"; \
		else \
			echo "$(GREEN)✓ Database credentials configured$(NC)"; \
		fi; \
	else \
		echo "$(RED)✗ .env file not found$(NC)"; \
	fi
	@command -v docker >/dev/null 2>&1 && echo "Docker: $$(docker --version)" || echo "$(YELLOW)Docker: not installed$(NC)"
	@command -v shellcheck >/dev/null 2>&1 && echo "shellcheck: $$(shellcheck --version | grep version: | awk '{print $$2}')" || echo "$(YELLOW)shellcheck: not installed$(NC)"
	@echo "$(GREEN)✓ Environment verified$(NC)"

health: ## Check API health endpoint
	@echo "$(YELLOW)Checking API health...$(NC)"
	@curl -s http://localhost:8080/health | jq . || echo "$(RED)✗ API not responding$(NC)"

db-status: ## Check database endpoint
	@echo "$(YELLOW)Checking database status...$(NC)"
	@curl -s http://localhost:8080/db/status | jq . || echo "$(RED)✗ Database endpoint not responding$(NC)"

endpoints: ## List all available API endpoints
	@echo "$(YELLOW)Fetching API endpoints...$(NC)"
	@curl -s http://localhost:8080/apispec.json | jq '.paths | keys[]' || echo "$(RED)✗ API not responding$(NC)"

# =============================================================================
# Development Workflow
# =============================================================================

reset: clean-all setup ## Full reset (clean everything and reinstall)
	@echo "$(GREEN)✓ Project reset complete$(NC)"

rebuild: clean install ## Clean and reinstall dependencies

watch: start logs ## Start server and tail logs

quick-start: ## Quick start (install and run)
	@make -s install
	@make -s start

# =============================================================================
# Maintenance
# =============================================================================

update-deps: ## Update Python dependencies
	@echo "$(YELLOW)Updating dependencies...$(NC)"
	@. $(VENV_DIR)/bin/activate && pip install --upgrade pip
	@. $(VENV_DIR)/bin/activate && pip install --upgrade -r requirements.txt
	@echo "$(GREEN)✓ Dependencies updated$(NC)"

freeze: ## Freeze current dependencies to requirements.txt
	@echo "$(YELLOW)Freezing dependencies...$(NC)"
	@. $(VENV_DIR)/bin/activate && pip freeze > requirements.txt
	@echo "$(GREEN)✓ Dependencies frozen$(NC)"

requirements-check: ## Check for outdated dependencies
	@echo "$(YELLOW)Checking for outdated dependencies...$(NC)"
	@. $(VENV_DIR)/bin/activate && pip list --outdated
