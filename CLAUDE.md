# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (dev extras for testing)
pip install -e ".[dev]"

# Run the dev server (requires a running Postgres — use Docker Compose instead)
uvicorn app.main:app --reload

# Run via Docker Compose (starts Postgres, runs migrations, starts API with hot-reload)
docker compose up

# Run all tests
pytest

# Run a single test
pytest tests/test_app.py::test_create_ticket

# Apply migrations
alembic upgrade head

# Generate a new migration (after changing a model)
alembic revision --autogenerate -m "describe change"
```

## Architecture

**Stack:** FastAPI + SQLAlchemy 2 (sync sessions) + Alembic + Postgres (psycopg3). Python 3.12.

**App layout:**

- `app/main.py` — `create_app()` factory; mounts routes and serves the Jinja2 home page at `/`.
- `app/config.py` — frozen dataclass `Settings` reads `APP_NAME` and `DATABASE_URL` from env.
- `app/database.py` — SQLAlchemy engine, `SessionLocal`, and the `get_db` FastAPI dependency. Sessions are **sync** even though the dependency is declared `async`.
- `app/routers/tickets.py` — all ticket endpoints registered via `register_ticket_routes(app)` rather than an `APIRouter`, so they appear directly on the root app.
- `app/models/` — `Ticket` (one-to-one with `TicketAnalysis`, cascade delete). `ticket.py` has a deferred import of `TicketAnalysis` at the bottom to avoid circular imports.
- `app/schemas/ticket.py` — Pydantic v2 schemas for request/response; `TicketRead` and `TicketAnalysisRead` use `from_attributes=True`.
- `app/services/mock_ai.py` — keyword-rule–based `analyze_ticket()` standing in for a real LLM; fully deterministic (no randomness, no I/O).
- `migrations/` — Alembic; `env.py` reads `DATABASE_URL` from `Settings`, not from `alembic.ini`.

**Key data flow for ticket analysis:**

`POST /api/tickets/{id}/analyze` → fetches `Ticket` from DB → calls `analyze_ticket(title, description)` (mock AI service) → upserts a single `TicketAnalysis` row (one-per-ticket constraint enforced by `unique=True` on `ticket_id`).

**Testing:** Tests use an in-memory SQLite database via `app.dependency_overrides[get_db]`. `asyncio.run()` drives async HTTP calls with `httpx.AsyncClient` + `ASGITransport`. No external services needed.

**Migration naming convention:** `YYYYMMDD_NNNN_<description>.py` (e.g. `20260618_0003_create_ticket_analyses.py`).
