.PHONY: install lint format typecheck test cov check migrate run seed precommit

install:  ## Install the package with dev + ai extras and pre-commit hooks
	pip install -e ".[dev,ai]"
	pre-commit install

lint:  ## Run ruff lint checks
	ruff check .

format:  ## Apply ruff formatting
	ruff format .

typecheck:  ## Run strict mypy type checking
	mypy app

test:  ## Run the test suite
	pytest

cov:  ## Run the test suite with a coverage report
	pytest --cov=app --cov-report=term-missing

check: lint typecheck test  ## Run everything CI enforces

migrate:  ## Apply database migrations
	alembic upgrade head

run:  ## Start the dev server with hot-reload
	uvicorn app.main:app --reload

seed:  ## Seed the database with demo tickets
	python scripts/seed.py

precommit:  ## Run all pre-commit hooks against every file
	pre-commit run --all-files
