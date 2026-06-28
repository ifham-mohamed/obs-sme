# 02 — Quickstart

> **Goal:** clone → run → register → submit a survey → see it as admin, in under 15 minutes.
>
> **Prerequisite:** [`01_Prerequisites.md`](01_Prerequisites.md) complete; every verification command passed.

---

## The five commands

```bash
git clone <repo-url> enigmatrix && cd enigmatrix
cp .env.example .env       # then edit .env to fill JWT_SECRET + APP_SECRET_KEY
make up                    # docker compose: Postgres :5432 + ChromaDB :8001
make migrate && make seed  # Alembic schema + dev users
# terminal A
make dev-backend           # FastAPI on http://localhost:8000
# terminal B
make dev-frontend          # Next.js on http://localhost:3000
```

If you are scripting the first run, generate the two secrets first:

```bash
{ printf 'JWT_SECRET=%s\n'        "$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  printf 'APP_SECRET_KEY=%s\n'    "$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
} >> .env
```

The `Makefile` targets are defined here — these aren't aliases the docs invented:

| Target | What it runs |
|--------|--------------|
| `make up` | `docker compose -f docker-compose.dev.yml up -d postgres chromadb` |
| `make down` | `docker compose -f docker-compose.dev.yml down` |
| `make migrate` | `cd backend && uv run alembic upgrade head` |
| `make seed` | `cd backend && uv run python -m app.scripts.seed_dev` |
| `make dev-backend` | `cd backend && uv run uvicorn app.main:app --reload --port 8000` |
| `make dev-frontend` | `cd frontend && pnpm dev` |
| `make test` | backend pytest + frontend vitest |
| `make lint` | ruff (backend) + eslint (frontend) |

Source: [`Makefile`](../../Makefile).

---

## What `make seed` creates

[`backend/app/scripts/seed_dev.py`](../../backend/app/scripts/seed_dev.py) is **idempotent** — re-run it as often as you want.

| Role | Email | Password |
|------|-------|----------|
| `admin` | `admin@enigmatrix.lk` | `admin12345` |
| `annotator` | `annotator@enigmatrix.lk` | `annotator12345` |
| `sme` | `sme@enigmatrix.lk` | `sme12345678` |

The seeded SME has a profile with sector `retail`, region `Western`, primary language `si`. To clear the dev DB and reseed → see [`06_Database_and_Migrations.md`](06_Database_and_Migrations.md).

---

## End-to-end smoke test (you should be able to do all of these)

After both `make dev-backend` and `make dev-frontend` are running:

### 1. Backend health

```bash
curl -s http://localhost:8000/health
# {"status":"ok","service":"enigmatrix-api"}
```

Then open **http://localhost:8000/docs** — the FastAPI OpenAPI UI lists every router (`auth`, `users`, `surveys`, plus the four 501-stub module routers). Every shipped endpoint should be visible.

### 2. Frontend landing

Open **http://localhost:3000**. You should see the landing page in your default locale, with two CTAs (Sign up / Sign in). The topbar has a theme toggle (light / dark / system) and a locale switcher (EN / SI / TA). Toggle each and confirm the page re-renders.

### 3. Register an SME

Click **Sign up**. Fill the form:

- Email: anything not already taken (e.g. `sme.test+1@example.com`)
- Password: ≥ 8 characters
- Sector / region / employee band: any values
- Preferred language: pick one

Submit. You should land at `/dashboard` with "Welcome, <email>" and a CTA to take the awareness survey.

### 4. Complete the awareness survey

Click **Awareness survey**. Twelve questions appear, six different question kinds (single choice, multi-select, Likert 1–5, date, numeric, short-text). Fill them in, click **Submit**. You should land at `/surveys/awareness/thank-you`.

### 5. Sign in as admin and view the response

Click the logout icon in the topbar. Sign in as `admin@enigmatrix.lk` / `admin12345`. The sidebar gains an **Admin** section with **Survey responses** and **Users**. Click **Survey responses** → you should see exactly one row with the SME email you registered, the sector, the region, the submitted-at timestamp, and the answer count (12).

### 6. Run the test suites

```bash
# Terminal C
cd backend && uv run pytest -q
# 3 passed (the integration test + the two security unit tests)

# Frontend E2E (requires both dev servers running)
cd frontend && pnpm exec playwright install chromium    # one-time
pnpm e2e
```

If any of those six steps fails, jump to [`09_Troubleshooting.md`](09_Troubleshooting.md) — the failure modes are catalogued there.

---

## Common quickstart pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| `make up` fails with "port 5432 already in use" | A local Postgres is running on the host. | `brew services stop postgresql` (macOS) or `sudo systemctl stop postgresql` (Linux), then `make up`. |
| `make migrate` fails with `InvalidRequestError: psycopg2 not installed` | `DATABASE_URL` is `postgresql://...` instead of `postgresql+asyncpg://...`. | Edit `.env` to use the asyncpg scheme. |
| Backend boots but every login returns 500 | `JWT_SECRET` is empty. | Set it in `.env` (see [`01_Prerequisites.md`](01_Prerequisites.md) → Environment variables). |
| Frontend loads but every API call CORS-rejects | `CORS_ORIGINS` doesn't include `http://localhost:3000`. | Edit `.env`, restart `make dev-backend`. |
| Sinhala / Tamil characters render as boxes | First-time `next/font` download failed (corporate proxy). | Either retry on a clean network or follow the offline-fonts workaround in [`09_Troubleshooting.md`](09_Troubleshooting.md). |
| Cookie not set after login (302 loop) | Browser blocking insecure HTTP cookies. | Confirm you're on `http://localhost:3000` (not `127.0.0.1`); `secure: false` in dev is set automatically. |

The full failure → fix table is in [`09_Troubleshooting.md`](09_Troubleshooting.md).

---

## What to read next

- New to the architecture? → [`03_Architecture.md`](03_Architecture.md).
- Want to add a backend endpoint? → [`04_Backend_Development.md`](04_Backend_Development.md).
- Want to add a frontend page? → [`05_Frontend_Development.md`](05_Frontend_Development.md).
- Want to understand the auth model? → [`07_Auth_and_Roles.md`](07_Auth_and_Roles.md).
- Looking for the next slice to build? → [`10_Next_Steps.md`](10_Next_Steps.md).

---

**Prev:** [`01_Prerequisites.md`](01_Prerequisites.md) &nbsp;·&nbsp; **Next:** [`03_Architecture.md`](03_Architecture.md)
