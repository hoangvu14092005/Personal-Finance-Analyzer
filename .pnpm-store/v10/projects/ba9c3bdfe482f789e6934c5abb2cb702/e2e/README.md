# E2E Tests (Phase 3.11)

Playwright tests for the OCR review + manual entry + history flows.

## Prerequisites

The tests require the **backend API** running with a clean database. Worker is *not*
required because OCR responses are mocked via `page.route()` in `receipt-review.spec.ts`.

### 1. Start infrastructure

```powershell
# From repo root.
docker compose -f infra/docker/docker-compose.yml up -d postgres redis
```

### 2. Migrate + seed categories

```powershell
# From backend/api.
$env:DATABASE_URL = "postgresql+psycopg://pfa_user:pfa_pass@localhost:5432/pfa"
python -m uv run alembic upgrade head
python -m uv run python -m scripts.seed_categories
```

### 3. Start backend API

```powershell
# From backend/api.
python -m uv run uvicorn app.main:app --port 8000
```

The Playwright config (`../playwright.config.ts`) auto-starts Next.js dev server on
port `3100` via the `webServer` block. You do **not** need to run `pnpm dev` separately.

## Run

```powershell
# From frontend/web.
pnpm e2e               # headless
pnpm e2e:ui            # interactive UI mode
npx playwright test --headed  # see browser
npx playwright test e2e/manual-entry.spec.ts  # single file
```

## Test suites

| Spec | Phase | Coverage |
| --- | --- | --- |
| `auth.spec.ts` | 1.x smoke | Register → Login → Dashboard nav |
| `manual-entry.spec.ts` | 3.6 | Manual transaction entry happy path + required-amount validation |
| `receipt-review.spec.ts` | 3.4 | OCR review form: pre-fill, low-confidence banner, draft 404 fallback (uses route mock) |
| `transactions-history.spec.ts` | 3.10 | List filter by merchant, reset, delete with confirm dialog |

## Notes

- Each test creates a unique user (`uniqueEmail()`) to isolate state across runs without DB cleanup.
- The `webServer` block in `playwright.config.ts` reuses an existing dev server when not in CI.
- For CI: set `CI=1` to enable retries + force fresh server start; expose backend via service container.
- Categories must be seeded once per database — re-running `seed_categories.py` is idempotent.
