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
