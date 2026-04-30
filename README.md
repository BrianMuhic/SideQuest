# SideQuest

A Flask web app that suggests road trip stops and detours based on a route and user preferences. Uses OpenStreetMap data via Nominatim (geocoding), OSRM (routing), and the Overpass API (points of interest).

---

## User Flow

1. **Register / Login** - optional, for saving preferences and routes
2. **Build Route** - enter start and destination, preview on map
3. **Set Preferences** - choose stop categories and allowed detour time
4. **Find Stops** - view suggested stops along the route ranked by proximity
5. **Export Route** - save or export to Google Maps, Apple Maps

---

## Setup

**Requirements:** Python 3.12, [uv](https://docs.astral.sh/uv/), [just](https://just.systems/), MariaDB/MySQL

```bash
# Start a local database (requires Docker or Podman)
just db-container

# Run migrations
just db-upgrade

# Start the server
just run
```

Static assets (SCSS → CSS, JS bundling) are compiled automatically on startup.

**Optional: Run services locally (recommended for development)**

```bash
# Local routing engine (faster, no rate limits)
just osrm-container

# Local POI database (no rate limits on Overpass queries)
just overpass-container
```

These run OSRM and Overpass locally via Docker. First run downloads Virginia OSM data and may take several minutes to initialize.

**Common commands:**

| Command | Description |
|---|---|
| `just run` | Start the app |
| `just format` | Format code (ruff) |
| `just lint` | Lint and auto-fix |
| `just test` | Run tests |
| `just db-migrate "message"` | Create a new migration |
| `just db-upgrade` | Apply pending migrations |
| `just clean` | Remove build artifacts and caches |

---

## Architecture

```
webapp/
├── account/          # Auth module: login, registration, session management
├── osm/              # Route planning module: geocoding, routing, stop discovery
├── core/
│   ├── app/          # App factory, blueprints, error handlers, extensions
│   ├── db/           # SQLAlchemy engine, base models, utils, @use_db decorator
│   ├── models/       # Shared models (e.g. EmailLog)
│   ├── service/      # Logger, emailer
│   ├── ui/           # BaseForm, WTForms filters and validators
│   └── util/         # request_params, date, formatting, traceback helpers
├── static/
│   ├── js/           # app.js, map.js, route.js, stops.js, auth.js, utils.js
│   └── scss/         # main.scss + partials (_variables, _layout, _panels, etc.)
├── blueprints.py     # Central blueprint registry
├── config.py         # Pydantic settings (loads from .env)
└── app.py            # Entry point
```

Each feature lives in its own module (`account/`, `osm/`, etc.) with a consistent internal structure:

| File | Responsibility |
|---|---|
| `routes.py` | HTTP layer only - parse request, call service, return response |
| `service.py` | Business logic, external API calls, logging |
| `forms.py` | WTForms input validation and export |
| `models/` | SQLAlchemy models |

---

## External APIs

| API | Used For |
|---|---|
| Nominatim (`nominatim.openstreetmap.org`) | Geocoding - location name → lat/lon |
| OSRM (`router.project-osrm.org`) | Routing - driving route between two points |
| Overpass (`overpass-api.de`) | POI discovery - stops near route coordinates |
| Wikimedia Commons | Stop photos via `wikimedia_commons` OSM tags |
| Google Places API (`places.googleapis.com`) | Stop photos (optional, requires API key) |
| OSRM Table API (`router.project-osrm.org`) | Detour time calculation - driving time matrix for all stops in one call |

---

## Environment Variables (Optional)

| Variable | Description |
|---|---|
| `GOOGLE_PLACES_API_KEY` | Enables Google Photos on stop cards |
| `OVERPASS_URL` | Override Overpass endpoint (default: public API) |
| `OSRM_URL` | Override OSRM endpoint (default: public demo server) |

## Style Guide

### Backend

#### Routes (`routes.py`)

Routes are HTTP plumbing only. They should:
- Extract parameters using `core.util.request_params`
- Call one or more service functions
- Return a response

They should **not** contain business logic, API calls, or log statements.

```python
@bp.post("/api/find-stops")
def find_stops() -> ResponseReturnValue:
    start_location = require_json("start_location", str)
    end_location = require_json("end_location", str)
    stop_categories = get_json("stop_categories", list, [])

    stops, route_geojson = service.find_stops(start_location, end_location, stop_categories, 0)
    return _api_response({"stops": stops, "route_geojson": route_geojson})
```

#### Service (`service.py`)

All business logic, external API calls, and logging live here. Public functions are called by routes; private helpers (prefixed `_`) are internal.

```python
# Public - called from routes.py
def find_stops(start: str, categories: list[str]) -> tuple[list[dict], dict | None]:
    log.i(f"Find stops: {start!r}, categories={categories}")
    ...

# Private - internal helper
def _geocode(location: str) -> dict | None:
    ...
```

#### Request Parameters

Always use `core.util.request_params` to extract request data - never access `request.args` or `request.get_json()` directly in routes.

```python
from core.util.request_params import require_json, get_json, get_param, require_param

# JSON body (POST)
name = require_json("name", str)           # raises 400 if missing
value = get_json("value", int, 0)          # returns default if missing

# Query string (GET)
query = require_param("q", str)            # raises 400 if missing
page = get_param("page", int, 1)           # returns default if missing
```

#### Error Handling

Raise werkzeug exceptions directly - the central error handler in `core/app/errors.py` catches them and returns JSON for API requests, HTML for page requests.

```python
from werkzeug.exceptions import BadRequest, NotFound, Forbidden

raise BadRequest("Start location is required.")
raise NotFound("Could not find that destination.")
```

Do not manually build error responses in routes.

#### Logging

Use `log = get_logger()` at the module level. Log in service, not routes.

| Level | When to use |
|---|---|
| `log.d` | High-frequency flow events (autocomplete, debug info) |
| `log.i` | Important actions - request received, result returned |
| `log.w` | Handled failures - geocoding miss, external API error |
| `log.e` | Unrecoverable errors that need attention |

```python
log.i(f"Find stops: {start!r} -> {end!r}, categories={categories}")
log.w(f"Geocoding failed for {location!r}")
```

#### Database

Use the `@use_db` decorator for routes or service functions that need a database session. The session is scoped to the request.

```python
from core.db.engine import use_db
from sqlalchemy.orm import Session

@bp.post("/login")
@use_db
def login(db: Session) -> ResponseReturnValue:
    ...
```

#### Auth Decorators

Import from `account.service`:

```python
from account.service import login_required, admin_required, guest_required

@bp.get("/dashboard")
@login_required
def dashboard(): ...
```

---

### Frontend

#### SCSS

All styles live in `static/scss/`. Add new partials as `_name.scss` and import them in `main.scss`.

| File | Contains |
|---|---|
| `_variables.scss` | Colors, spacing, typography constants |
| `_layout.scss` | Page structure, global reset, responsive |
| `_buttons.scss` | Button variants and states |
| `_forms.scss` | Inputs, labels, validation |
| `_panels.scss` | Panel system, stop cards, loading hints |
| `_route_detail.scss` | Itinerary list, leg connectors, markers |
| `_auth.scss` | Auth widget - toggle icon + dropdown |

Use variables from `_variables.scss` - do not hardcode colors or font sizes.

**Loading states** - any element with `.loading-hint` automatically gets a spinning icon via `::before`. No markup needed:

```html
<p id="my-loading" class="loading-hint" hidden>Processing…</p>
```

```js
$('#my-loading').removeAttr('hidden');   // show with spinner
$('#my-loading').attr('hidden', true);   // hide
```

#### JavaScript

Source files in `static/js/`, bundled into `build/core.min.js`.

| File | Responsibility |
|---|---|
| `app.js` | SPA orchestrator - panel flow, shared state, event wiring |
| `map.js` | Leaflet map wrapper (`osmMap()`) |
| `route.js` | Route display, route preview API |
| `stops.js` | Stop markers, selection state |
| `auth.js` | Login/register UI |
| `utils.js` | CSRF setup, `postJson()`, `ajaxFailure()`, shared helpers |

Keep API calls in the relevant module (`route.js` for route endpoints, `stops.js` for stop endpoints). Shared state lives in `app.js` and is passed down as needed.

#### API Responses

All `osm` API endpoints return JSON with consistent structure via `_api_response()`:

```js
// Success
{ "stops": [...], "route_geojson": {...} }

// Error (from werkzeug exception)
{ "error": "Human-readable message" }
```

Cache-Control is managed server-side - GET endpoints that return deterministic data (route preview, location suggestions) are cached for 1 hour. POST endpoints are not cached.
