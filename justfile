# Development aliases
# Install just: apt install just OR brew install just OR cargo install just
# Run: just <recipe> or just help
# Documentation: https://just.systems/man/en/

# ==================== Environment ==================== #
set ignore-comments := true
export UV_PROJECT_ENVIRONMENT := "venv"

app_module := "app"
app_dir := "webapp"


# ==================== Application ==================== #

# Run the application
default: run

# Run the application
run: setup
    PYTHONPATH={{app_dir}} uv run python -m {{app_module}}

# Show all available commands (alias for just --list)
help:
    @just --list


# ==================== Code Quality ==================== #

# Run all normal checks on codebase
all: format lint typehint complexity

# Format code with ruff
format:
    uv run ruff format .

# Lint code with ruff (auto-fix)
lint:
    uv run ruff check --select I --fix .
    uv run ruff check --fix .

# Check type hints with pyrefly
typehint:
    uv run pyrefly check

# Check code complexity
complexity:
    uv run complexipy


# ==================== Testing ==================== #

# Run tests with pytest (parallel)
test:
    uv run pytest

# Run tests with coverage measurement
test-coverage:
    uv run coverage run -m pytest
    uv run coverage html
    @rm .coverage
    @echo "Coverage report: file://$(pwd)/htmlcov/index.html"


# ==================== Database ==================== #

# Create new migration with message (e.g., just db-migrate "add user table")
db-migrate message:
    uv run alembic revision --autogenerate -m "{{message}}"
    uv run ruff format {{app_dir}}/migrations/

# Check if a alembic migration is needed
db-check:
    uv run alembic check

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
@clean:
    rm -rf venv .venv .*cache htmlcov
    rm -rf {{app_dir}}/static/build {{app_dir}}/static/.webassets*
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -name "*.pyc" -delete


# ==================== Containers ==================== #

# Run MariaDB via container
db-container:
    #!/bin/sh
    set -e
    if command -v podman &>/dev/null; then 
        export CMD="podman"
    elif command -v docker &>/dev/null; then
        export CMD="docker"
    else
        echo "Cannot find podman or docker"
        exit 1
    fi
    mkdir -p ./local/mysql
    $CMD run --detach --name mariadb -v ./local/mysql:/var/lib/mysql:Z -p 3306:3306 -e MARIADB_ALLOW_EMPTY_ROOT_PASSWORD=1 mariadb:latest
    echo "MariaDB server started (user='root', password='', port=3306)"
    echo "To stop the server, run '$CMD rm -f mariadb'"
    echo "To ensure the database is on the most recent version, run 'just db-upgrade'"


# Run OSRM routing engine via container (Virginia data)
osrm-container:
    #!/bin/sh
    set -e
    if command -v podman &>/dev/null; then
        export CMD="podman"
    elif command -v docker &>/dev/null; then
        export CMD="docker"
    else
        echo "Cannot find podman or docker"
        exit 1
    fi
    mkdir -p ./local/osrm
    if [ ! -f ./local/virginia-latest.osm.pbf ]; then
        echo "Downloading Virginia OSM data..."
        curl -L -o ./local/virginia-latest.osm.pbf https://download.geofabrik.de/north-america/us/virginia-latest.osm.pbf
    fi
    if [ ! -f ./local/osrm/virginia-latest.osrm ]; then
        echo "Extracting..."
        $CMD run -t -v "${PWD}/local/osrm:/data" -v "${PWD}/local/virginia-latest.osm.pbf:/data/virginia-latest.osm.pbf:ro" osrm/osrm-backend osrm-extract -p /opt/car.lua /data/virginia-latest.osm.pbf
        echo "Partitioning..."
        $CMD run -t -v "${PWD}/local/osrm:/data" osrm/osrm-backend osrm-partition /data/virginia-latest.osrm
        echo "Customizing..."
        $CMD run -t -v "${PWD}/local/osrm:/data" osrm/osrm-backend osrm-customize /data/virginia-latest.osrm
    fi
    $CMD run --detach --name osrm -p 5001:5000 -v "${PWD}/local/osrm:/data" osrm/osrm-backend osrm-routed --algorithm mld /data/virginia-latest.osrm
    echo "OSRM server started on port 5001"
    echo "To stop the server, run '$CMD rm -f osrm'"
    echo "Remember to set OSRM_URL=\"http://127.0.0.1:5001/route/v1/driving\" in your .env"


# Run Overpass API via container (Virginia data)
overpass-container:
    #!/bin/sh
    set -e
    if command -v podman &>/dev/null; then
        export CMD="podman"
    elif command -v docker &>/dev/null; then
        export CMD="docker"
    else
        echo "Cannot find podman or docker"
        exit 1
    fi
    mkdir -p ./local/overpass
    if [ ! -f ./local/virginia-latest.osm.pbf ]; then
        echo "Downloading Virginia OSM data..."
        curl -L -o ./local/virginia-latest.osm.pbf \
            https://download.geofabrik.de/north-america/us/virginia-latest.osm.pbf
    fi
    if [ ! -f ./local/planet.osm.bz2 ]; then
        echo "Converting OSM data to bz2 (one-time, takes a few minutes)..."
        $CMD run --rm \
            --entrypoint /bin/sh \
            -v "${PWD}/local:/data" \
            wiktorn/overpass-api \
            -c "osmium cat -o /data/planet.osm.bz2 /data/virginia-latest.osm.pbf"
    fi
    if [ ! -f ./local/overpass/osm_base_version ]; then
        echo "Initializing Overpass database (this may take several minutes)..."
        $CMD run --rm -i \
            -e OVERPASS_MODE=init \
            -e OVERPASS_PLANET_URL=file:///osm/planet.osm.bz2 \
            -e OVERPASS_RULES_LOAD=100 \
            -e OVERPASS_STOP_AFTER_INIT=true \
            -v "${PWD}/local/overpass:/db" \
            -v "${PWD}/local/planet.osm.bz2:/osm/planet.osm.bz2:ro" \
            wiktorn/overpass-api
    fi
    $CMD run --detach --name overpass -v "${PWD}/local/overpass:/db" -p 5002:80 wiktorn/overpass-api
    echo "Overpass API started on port 5002"
    echo "To stop the server, run '$CMD rm -f overpass'"
    echo "Remember to set OVERPASS_URL=\"http://127.0.0.1:5002/api/interpreter\" in your .env"


# ==================== Setup ==================== #

# Run all setup tasks (only installs if not already installed)
setup: pre-commit-setup

# Setup pre-commit hooks
pre-commit-setup:
    @test -f .git/hooks/pre-commit || uv run pre-commit install -f

