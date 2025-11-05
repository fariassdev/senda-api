# ============================================================================
# VIRTUAL ENVIRONMENT (UV)
# ============================================================================
# This project uses UV for dependency management and virtual environments
# All Python commands should be run through 'uv run' to use the managed venv
# ============================================================================

# Virtual Environment Management
ve:
	uv venv
	uv sync --all-groups

ve-sync:
	uv sync --all-groups

# Pre-commit Hooks
install-hooks:
	uv sync --group dev
	uv run pre-commit install

run-hooks:
	uv run pre-commit run --all-files

# Development Server
runserver:
	uv run uvicorn senda.app:app --host 0.0.0.0 --port 8081

runserver-dev:
	uv run --env-file .env.dev uvicorn senda.app:app --host 0.0.0.0 --port 8081 --reload

# Testing
test:
	uv run --env-file .env.test pytest -v ./tests

test-cov:
	uv run --env-file .env.test pytest --cov=./senda ./tests

test-watch:
	uv run --env-file .env.test pytest -v ./tests --watch

# Database Migrations
migration:
	uv run alembic -c senda/infrastructure/alembic.ini revision --autogenerate -m "$(message)"

migrate:
	uv run alembic -c senda/infrastructure/alembic.ini upgrade head

migrate-down:
	uv run alembic -c senda/infrastructure/alembic.ini downgrade -1

migrate-history:
	uv run alembic -c senda/infrastructure/alembic.ini history

# Code Quality (using Ruff - replaces flake8, black, isort, pyupgrade)
lint:
	uv run ruff check senda tests

lint-fix:
	uv run ruff check --fix senda tests

format:
	uv run ruff format --check senda tests

format-fix:
	uv run ruff format senda tests

types:
	uv run mypy --namespace-packages -p "senda" --config-file setup.cfg

check:
	uv run ruff check senda tests
	uv run ruff format --check senda tests
	uv run mypy --namespace-packages -p "senda" --config-file setup.cfg

fix:
	uv run ruff check --fix senda tests
	uv run ruff format senda tests

# Docker Commands
docker-build:
	docker-compose up -d --build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-restart:
	docker-compose stop
	docker-compose up -d

docker-logs:
	docker-compose logs --tail=100 -f

# Development Helpers
shell:
	uv run python -c "from senda.core.container import Container; container = Container(); print('Senda container loaded. Access via: container')"

db-reset:
	uv run alembic -c senda/infrastructure/alembic.ini downgrade base
	uv run alembic -c senda/infrastructure/alembic.ini upgrade head

clean:
	rm -r .mypy_cache
	rm -r .pytest_cache
	rm -r .ruff_cache
	rm -r .venv
	rm -r dist
	rm -r build
	rm -f .coverage

# Quick Start (run all setup steps)
setup:
	@echo "Setting up Senda development environment..."
	@echo "1. Creating virtual environment with UV..."
	uv venv
	@echo "2. Installing dependencies..."
	uv sync --all-groups
	@echo "3. Installing pre-commit hooks..."
	uv run pre-commit install
	@echo "4. Running migrations..."
	uv run alembic -c senda/infrastructure/alembic.ini upgrade head
	@echo "✅ Senda setup complete! Run 'make runserver-dev' to start."

# Help
help:
	@echo "Senda Development Commands:"
	@echo ""
	@echo "  Virtual Environment:"
	@echo "    ve            - Create virtual environment and install dependencies"
	@echo "    ve-sync       - Sync dependencies"
	@echo ""
	@echo "  Pre-commit Hooks:"
	@echo "    install-hooks - Install pre-commit hooks"
	@echo "    run-hooks     - Run all hooks manually"
	@echo ""
	@echo "  Server:"
	@echo "    runserver      - Run Senda API server (port 8081)"
	@echo "    runserver-dev  - Run with auto-reload"
	@echo ""
	@echo "  Testing:"
	@echo "    test          - Run tests"
	@echo "    test-cov      - Run tests with coverage"
	@echo ""
	@echo "  Database:"
	@echo "    migration     - Create new migration (message='description')"
	@echo "    migrate       - Apply migrations"
	@echo "    migrate-down  - Rollback one migration"
	@echo "    db-reset      - Reset database to clean state"
	@echo ""
	@echo "  Code Quality (Ruff):"
	@echo "    lint          - Check code with ruff (linting)"
	@echo "    lint-fix      - Auto-fix linting issues"
	@echo "    format        - Check formatting"
	@echo "    format-fix    - Auto-fix formatting"
	@echo "    types         - Type check with mypy"
	@echo "    check         - Run all checks (lint + format + types)"
	@echo "    fix           - Auto-fix all issues (lint + format)"
	@echo ""
	@echo "  Docker:"
	@echo "    docker-build  - Build and start containers"
	@echo "    docker-up     - Start containers"
	@echo "    docker-down   - Stop containers"
	@echo "    docker-logs   - View logs"
	@echo ""
	@echo "  Setup:"
	@echo "    setup         - Complete setup (deps + migrations)"
	@echo "    help          - Show this help"
	@echo ""
	@echo "  📚 For detailed documentation, see: SENDA_DEV_GUIDE.md"
	@echo "  🚀 Quick start: make verify && make runserver-dev"
