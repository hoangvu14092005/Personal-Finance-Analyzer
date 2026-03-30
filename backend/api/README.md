# Backend API

FastAPI service for Personal Finance Analyzer.

## Run local

```bash
python -m uv sync
python -m uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Health check

- Endpoint: `GET /health`
- Expected response:

```json
{
  "status": "ok",
  "service": "api"
}
```

## Database migrations (Task 0.7)

Apply migration on the default local DB URL:

```bash
python -m uv run --project . alembic upgrade head
```

Create a new migration revision from SQLModel metadata:

```bash
python -m uv run --project . alembic revision --autogenerate -m "your message"
```

Seed default categories:

```bash
python -m uv run --project . python -m scripts.seed_categories
```

If host-to-Docker PostgreSQL auth is blocked locally, run migration from a temporary container in the same Docker network:

```bash
docker run --rm --network pfa-local-network -v "${PWD}:/workspace" -w /workspace/backend/api python:3.12-slim sh -lc "pip install --no-cache-dir alembic sqlmodel 'psycopg[binary]' >/tmp/pip.log 2>&1 && DATABASE_URL='postgresql+psycopg://pfa:pfa@postgres:5432/pfa' alembic upgrade head"
```

## Quality checks (Task 0.9)

Install dev dependencies:

```bash
python -m uv sync --all-groups
```

Run lint, typecheck, tests:

```bash
python -m uv run ruff check app tests
python -m uv run mypy app
python -m uv run pytest
```
