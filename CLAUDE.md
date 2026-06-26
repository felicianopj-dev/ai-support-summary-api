# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (dev extras for testing/linting; add ai for the Gemini integration)
pip install -e ".[dev]"
pip install -e ".[dev,ai]"

# Run the dev server (requires a running Postgres — use Docker Compose instead)
uvicorn app.main:app --reload

# Run via Docker Compose (starts Postgres, runs migrations, starts API with hot-reload)
docker compose up

# Run all tests
pytest

# Run a single test
pytest tests/test_app.py::test_create_ticket

# Lint, format check, and type check (mirrors CI)
ruff check .
ruff format --check .
mypy app

# Apply migrations
alembic upgrade head

# Generate a new migration (after changing a model)
alembic revision --autogenerate -m "describe change"
```

## Architecture

**Stack:** FastAPI + SQLAlchemy 2 (sync sessions) + Alembic + Postgres (psycopg3). Python 3.12.

**App layout:**

- `app/main.py` — `create_app()` factory; includes the three routers and defines `/health`.
- `app/config.py` — frozen dataclass `Settings` reads `APP_NAME`, `DATABASE_URL`, and `GEMINI_API_KEY` from env.
- `app/database.py` — SQLAlchemy engine, `SessionLocal`, the `Base` declarative class, and the **sync** `get_db` FastAPI dependency.
- `app/routers/` — `tickets.py`, `insights.py`, and `pages.py`, each an `APIRouter`. `tickets.py` and `insights.py` use the `/api` prefix; `pages.py` serves the Jinja2 HTML pages. Re-exported as `tickets_router`, `insights_router`, `pages_router` from `app/routers/__init__.py`.
- `app/models/` — `Ticket` (one-to-one with `TicketAnalysis`, cascade delete). `ticket.py` has a deferred import of `TicketAnalysis` at the bottom to avoid circular imports.
- `app/schemas/ticket.py` — Pydantic v2 schemas for request/response. `Literal` aliases (`TicketStatus`, `AnalysisCategory`, `AnalysisPriority`, `AnalysisSentiment`) constrain the enum-like fields; `TicketRead`/`TicketAnalysisRead` use `from_attributes=True`.
- `app/services/` — `analyze_ticket()` (in `__init__.py`) dispatches at call time: if `GEMINI_API_KEY` is set it lazily imports and calls `gemini_ai.py`, otherwise it uses `mock_ai.py`. Both return the shared `AnalysisResult` dataclass from `base.py`.
  - `mock_ai.py` — keyword-rule–based, fully deterministic (no randomness, no I/O).
  - `gemini_ai.py` — calls Google Gemini (`gemini-2.0-flash`) via the `google-genai` SDK with a request timeout, validates the JSON output against the `Literal` enums with a Pydantic model, and **falls back to the mock on any failure** (network, timeout, malformed JSON, out-of-enum value).
- `migrations/` — Alembic; `env.py` reads `DATABASE_URL` from `Settings`, not from `alembic.ini`.

**Key data flow for ticket analysis:**

`POST /api/tickets/{id}/analyze` → fetches `Ticket` from DB → calls `analyze_ticket(title, description)` → upserts a single `TicketAnalysis` row (one-per-ticket constraint enforced by `unique=True` on `ticket_id`).

**Testing:** Tests use an in-memory SQLite database via `app.dependency_overrides[get_db]`. Async HTTP calls use `httpx.AsyncClient` + `ASGITransport`, driven by `pytest-asyncio` (`asyncio_mode = "auto"`). The Gemini path is exercised by monkeypatching the service; no external services or API keys are needed.

**Tooling:** Ruff (lint + format) and strict Mypy (with the pydantic plugin) are configured in `pyproject.toml` and enforced by GitHub Actions (`.github/workflows/ci.yml`) alongside the test suite. Migrations are excluded from Ruff.

**Migration naming convention:** `YYYYMMDD_NNNN_<description>.py` (e.g. `20260618_0003_create_ticket_analyses.py`).
