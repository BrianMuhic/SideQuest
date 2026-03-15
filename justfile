# Development aliases
# Install just: apt install just OR brew install just OR cargo install just
# Run: just <recipe> or just help
# Documentation: https://just.systems/man/en/

# ==================== PROJECT SPECIFIC ==================== #
export APP_MODULE := "app"
export APP_DIR := "webapp"
export MIGRATIONS_DIR := "webapp/migrations"
# ========================================================== #

export PYTHONPATH := APP_DIR

# ==================== Application ==================== #

# Run the application
default: run

# Run the application
run: setup
    uv run python -m {{APP_MODULE}}

# Show all available commands (alias for just --list)
help:
    @just --list

# ==================== Code Quality ==================== #

# Run all normal checks on codebase
all: format lint test

# Format code (ruff + imports)
format: format-ruff format-imports

# Format code with ruff
format-ruff:
    uv run ruff format .

# Sort and organize imports
format-imports:
    uv run ruff check --select I --fix .

# Lint code with ruff (auto-fix)
lint:
    uv run ruff check --fix .

# Check type hints with ty
typehint:
    uv run ty check

# Check code complexity
complex:
    uv run complexipy


# ==================== Testing ==================== #

# Run tests with pytest
test:
    uv run pytest

# Run tests with coverage measurement
test-coverage:
    uv run coverage run -m pytest
    uv run coverage html
    @rm -f .coverage
    @echo "Coverage report: file://$(pwd)/htmlcov/index.html"


# ==================== Database ==================== #

# Create new migration with message (e.g., just db-migrate "add user table")
db-migrate message:
    uv run alembic revision --autogenerate -m "{{message}}"
    uv run ruff format {{MIGRATIONS_DIR}}/

# Apply all pending migrations
db-upgrade:
    uv run alembic upgrade head

# Rollback last migration
db-downgrade:
    uv run alembic downgrade -1


# ==================== Utilities ==================== #

# Upgrade all packages to latest versions
venv-upgrade:
    uv sync --upgrade

# Clean all generated files and caches
clean:
    rm -rf .venv .pytest_cache .ruff_cache htmlcov performance_report.html
    rm -rf {{APP_DIR}}/static/build {{APP_DIR}}/static/.webassets* 2>/dev/null
    -find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    -find . -name "*.pyc" -delete 2>/dev/null


# ==================== Setup ==================== #

# Run all setup tasks (only installs if not already installed)
setup: pre-commit-setup

# Setup pre-commit hooks
pre-commit-setup:
    @test -f .git/hooks/pre-commit || uv run pre-commit install -f

