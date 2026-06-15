# AI Support Summary API

Minimal FastAPI backend for an AI-assisted support summary application. AI
features are intentionally not implemented yet.

## Stack

- Python 3.12
- FastAPI and Jinja2
- SQLAlchemy 2 and Alembic
- PostgreSQL 16
- Docker Compose
- Pytest
- Bootstrap 5 via CDN

## Run with Docker

Requirements: Docker with Compose support.

```bash
docker compose up --build
```

The API is available at:

- Home page: <http://localhost:8000/>
- Health check: <http://localhost:8000/health>
- OpenAPI docs: <http://localhost:8000/docs>

Stop the services with:

```bash
docker compose down
```

To also remove the PostgreSQL data volume:

```bash
docker compose down -v
```

## Run locally

Requirements: Python 3.12 and a running PostgreSQL instance.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
set -a
source .env
set +a
alembic upgrade head
uvicorn app.main:app --reload
```

Environment variables are read from the process environment. The commands
above export the values from `.env`; the application also has local defaults
matching `.env.example`.

## Tests

Tests do not require a database connection.

```bash
pytest
```

## Database migrations

Create a migration after adding or changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```
