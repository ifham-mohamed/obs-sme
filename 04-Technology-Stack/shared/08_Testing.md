# 08 — Testing

> **Goal:** know which test surface to write a new test in, and how to run each.
>
> **Reference:** [`backend/pyproject.toml`](../../backend/pyproject.toml), [`backend/app/tests/`](../../backend/app/tests/), [`frontend/playwright.config.ts`](../../frontend/playwright.config.ts), [`frontend/vitest.config.ts`](../../frontend/vitest.config.ts).

---

## 1. Three surfaces

| Surface | Where | What it verifies | When to add a test here |
|---------|-------|------------------|-------------------------|
| **Backend unit** | [`backend/app/tests/unit/`](../../backend/app/tests/unit/) | Pure helpers — no I/O. Today: bcrypt + JWT round-trip. | You've added a function in `app/core/`, `app/exceptions.py`, or any pure utility. |
| **Backend integration** | [`backend/app/tests/integration/`](../../backend/app/tests/integration/) | Real HTTP requests against an ASGI client wired to a disposable Postgres. Today: full register → login → submit → admin list flow + 501 stubs. | You've added or changed an endpoint, a service, or a model. **Default choice for new backend tests.** |
| **Frontend E2E** | [`frontend/tests/e2e/`](../../frontend/tests/e2e/) | Headless Chromium drives the real stack (frontend + backend + Postgres). Today: register → survey → admin spec. | You've added a UI flow that crosses pages or roles. |

The full test pyramid (CI, coverage gates, Vitest unit tests, k6 load tests) ships with [`BUILD_15_Observability_Testing.md`](../../infra/BUILD_PLAN/BUILD_15_Observability_Testing.md). The MVP's three surfaces are the minimum we keep green between now and then.

---

## 2. Running tests

### Backend

```bash
cd backend
uv run pytest -q                                           # everything
uv run pytest -q app/tests/unit/                           # just unit
uv run pytest -q app/tests/integration/                    # just integration
uv run pytest -v app/tests/integration/test_survey_flow.py # one file, verbose
uv run pytest -k "register"                                # by name fragment
uv run pytest --cov=app --cov-report=term-missing          # coverage
```

Or from the repo root: `make test`.

### Frontend (Playwright)

E2E tests need both servers running. Two options:

**Option A — bring stacks up by hand (recommended during development):**

```bash
# terminal A
make up && make migrate && make seed && make dev-backend
# terminal B
make dev-frontend
# terminal C
cd frontend
pnpm exec playwright install chromium    # one-time
pnpm e2e
```

**Option B — wrap it later in a single command:** add a pnpm script that uses `concurrently` or Playwright's `webServer` config. Not in MVP.

### Frontend (Vitest)

```bash
cd frontend
pnpm test               # interactive
pnpm test --run         # CI mode (single pass)
```

There are no Vitest unit tests yet — Vitest is wired so you can add component or hook tests when needed.

---

## 3. The integration-test fixture

[`backend/app/tests/conftest.py`](../../backend/app/tests/conftest.py) defines three fixtures:

| Fixture | Scope | What it does |
|---------|-------|--------------|
| `postgres_url` | session | Spins up a `postgres:16-alpine` container via `testcontainers`, returns its asyncpg URL. |
| `initialised_engine` | session | Connects to that container, creates the `pgcrypto` / `uuid-ossp` / `pg_trgm` extensions, and runs `Base.metadata.create_all` (no Alembic — faster). Yields the engine. |
| `client` | function | Patches `app.db.session.engine` and `app.db.session.SessionLocal` to point at the test engine, sets the env vars (`JWT_SECRET`, `APP_SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`), clears the `get_settings()` cache, builds a fresh app, and returns an `httpx.AsyncClient` bound to it via `ASGITransport`. |

This means each integration test starts against a **clean schema** — no pollution between tests, no manual DB setup. The cost is the first test in a session takes ~10s while testcontainers boots Postgres; subsequent tests in the same session reuse the container.

A new integration test looks like the existing `test_survey_flow.py`:

```python
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_my_endpoint(client: AsyncClient) -> None:
    r = await client.post("/api/v1/auth/register", json={...})
    assert r.status_code == 201
    ...
```

---

## 4. The Playwright spec

[`frontend/tests/e2e/auth_survey_admin.spec.ts`](../../frontend/tests/e2e/auth_survey_admin.spec.ts) drives the full UI flow:

1. Register a fresh SME (timestamp-suffixed email so reruns don't collide).
2. Fill all 12 awareness questions, submit, land at `/surveys/awareness/thank-you`.
3. Log in as the seeded admin (`admin@enigmatrix.lk`), navigate to `/admin/surveys/awareness/responses`, assert the new SME's email appears.

Failure modes the spec is sensitive to:

- The seed didn't run → admin login fails. Fix with `make seed`.
- The dev frontend isn't on `localhost:3000` → set `E2E_BASE_URL`.
- The dev backend rejects the register because port 8000 is in use → see [`09_Troubleshooting.md`](09_Troubleshooting.md).

---

## 5. When to write what

| Change | Test |
|--------|------|
| New helper in `app/core/security.py` | unit test in `tests/unit/` |
| New endpoint or service | integration test in `tests/integration/` (you can call the endpoint via the `client` fixture *and* assert DB state via `db_session`) |
| New page that lives behind an auth-guarded layout | extend the Playwright spec |
| New zod schema in `frontend/lib/validators/` | Vitest unit test (write the resolver, assert each failure case) |
| New SQL or model change | extend the integration test that exercises it; don't write a "model only" unit test — the model has no logic |

A useful heuristic: **prefer integration tests over unit tests** when the function under test touches the DB or another service. The testcontainer makes it fast enough that the maintenance burden of mocks isn't worth it.

---

## 6. Common test pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| `testcontainers.core.exceptions.ContainerStartException` | Docker daemon not running. | `docker info` to check; start Docker Desktop. |
| `pytest` hangs at "PostgresContainer …" | First-time image pull. | Wait, or `docker pull postgres:16-alpine` first. |
| Unit test fails with `pydantic_core._pydantic_core.ValidationError` for missing `JWT_SECRET` | Env vars not set in the unit-test fixture. | Use the `_env` fixture pattern from [`tests/unit/test_security.py`](../../backend/app/tests/unit/test_security.py): `monkeypatch.setenv(...)` + `get_settings.cache_clear()`. |
| Playwright test times out at the survey page | Form serialisation changed; old selector no longer matches. | Update the spec to match the current question kinds in `lib/surveys/awareness.ts`. |
| Test passes locally, fails in CI (which we don't have yet) | testcontainers default to `tcp://localhost`; CI may need `DOCKER_HOST` set. | Configure when [`BUILD_15`](../../infra/BUILD_PLAN/BUILD_15_Observability_Testing.md) ships CI. |

---

**Prev:** [`07_Auth_and_Roles.md`](07_Auth_and_Roles.md) &nbsp;·&nbsp; **Next:** [`09_Troubleshooting.md`](09_Troubleshooting.md)
