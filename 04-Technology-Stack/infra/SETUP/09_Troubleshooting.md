# 09 — Troubleshooting

> **Goal:** symptom → cause → exact fix for the failures you'll actually hit. Add new entries here whenever you debug something for ≥ 10 minutes.

---

## 1. Quickstart-time failures

| # | Symptom | Cause | Fix |
|---|---------|-------|-----|
| 1 | `make up` fails with `Bind for 0.0.0.0:5432 failed: port is already allocated` | A local Postgres is bound to 5432 on the host. | macOS: `brew services stop postgresql` (or `@14`/`@15` variant). Linux: `sudo systemctl stop postgresql`. WSL2: same. Then `make up`. As an alternative, change the host port in [`docker-compose.dev.yml`](../../docker-compose.dev.yml) to `"5433:5432"` and update `DATABASE_URL` to use port 5433. |
| 2 | `make migrate` fails with `ModuleNotFoundError: No module named 'psycopg2'` or `InvalidRequestError: ... uses asyncpg... but engine creation says psycopg2` | `DATABASE_URL` is `postgresql://...` — SQLAlchemy picked the sync driver. | Edit `.env` so it starts with `postgresql+asyncpg://` exactly. The default in [`.env.example`](../../.env.example) is correct; don't drop the `+asyncpg`. |
| 3 | App boots but every login returns 500 with no body | `JWT_SECRET` is empty or shorter than expected. | Set it via `python3 -c 'import secrets; print(secrets.token_hex(32))'` and paste into `.env`. Restart `make dev-backend`. |
| 4 | App boots but every request returns 500; logs show `pydantic_core._pydantic_core.ValidationError` for `Settings` | `.env` is missing `APP_SECRET_KEY` or `JWT_SECRET`, or `DATABASE_URL` doesn't parse as a Postgres DSN. | Compare your `.env` against [`.env.example`](../../.env.example). Both `APP_SECRET_KEY` and `JWT_SECRET` are required. |
| 5 | Frontend page loads but every API call fails with `TypeError: Failed to fetch` | The backend isn't running, OR `NEXT_PUBLIC_API_BASE_URL` is wrong. | `curl localhost:8000/health` should return `{"status":"ok"}`. Confirm `.env` has `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`. After changing `.env`, restart `make dev-frontend` — Next.js inlines `NEXT_PUBLIC_*` at build time. |
| 6 | Frontend logs `Access to fetch ... has been blocked by CORS` | `CORS_ORIGINS` in `.env` doesn't include the frontend origin. | Set `CORS_ORIGINS=http://localhost:3000`. Note: a *trailing slash* breaks the parse (`http://localhost:3000/` is a different origin). |
| 7 | After login, you're stuck on `/login` — refresh keeps redirecting back | Cookie was issued for `127.0.0.1` but you're accessing the page at `localhost`, or vice versa. | Pick one origin and stick to it. The default is `http://localhost:3000`. |

---

## 2. Backend errors at development time

| # | Symptom | Cause | Fix |
|---|---------|-------|-----|
| 8 | `ImportError: cannot import name 'PostgresDsn'` from pydantic | Your installed Pydantic is v1 (or a stub). | `cd backend && uv sync` to install Pydantic v2 from [`pyproject.toml`](../../backend/pyproject.toml). |
| 9 | `(trapped) error reading bcrypt version` warning, then `ValueError: password cannot be longer than 72 bytes` | passlib 1.7.4 reads `bcrypt.__about__.__version__`, which `bcrypt>=4.1` removed; passlib then runs a wrap-bug detection that probes a long password and crashes. | The bcrypt pin in [`pyproject.toml`](../../backend/pyproject.toml) is **`bcrypt>=4.0,<4.1`** explicitly. Run `cd backend && uv sync` to converge. The `core/security.py` helpers also truncate at 72 bytes defensively, so even if the pin slips this stops being a hard crash. |
| 9b | `ValueError: password cannot be longer than 72 bytes` outside of seed time | A user submitted a password whose UTF-8 encoding is > 72 bytes. | Already handled — `app/core/security.py.hash_password()` truncates on a UTF-8 boundary before bcrypt sees the string. If you wrote a custom auth path that bypasses it, route through that helper. |
| 10 | `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called` | A sync ORM access (e.g. lazy-loaded `relationship`) inside an async path. | Either declare `lazy="selectin"` on the relationship, eagerly `selectinload` in the query, or call `await db.refresh(obj, ["sme_profile"])`. The `User.sme_profile` relationship in [`app/models/user.py`](../../backend/app/models/user.py) already uses `selectin`. |
| 11 | `PendingRollbackError: This Session's transaction has been rolled back due to a previous exception during flush` | A query in the same request raised but you didn't roll back. | Either `await db.rollback()` inside the failure path before retrying, or restructure so the failing branch happens in its own service function (each request gets its own session via `get_db`). |
| 12 | Migration autogenerates a `drop_table` you don't recognise | A model's import is missing in [`backend/app/models/__init__.py`](../../backend/app/models/__init__.py); Alembic thinks the table is gone. | Re-import the model. Regenerate. Never let an unintended `drop_table` ship. |
| 13 | `slowapi` rate-limit fires immediately for a single request | The `@limiter.limit(...)` decorator is on a function whose first arg isn't `request: Request`. | Add `request: Request` (and a `# noqa: ARG001` if it isn't used inside the body). |
| 13b | Login keeps failing with `Invalid credentials` even though the seed ran and CORS is now fine | `bcrypt 4.1+` is still in your venv from before the F-57 pin landed. Pre-fix hashes were written by the broken passlib path and can't be verified now. | One command: `make doctor`. It surfaces the failing check (bcrypt version / round-trip / users-table). If bcrypt is too new: `cd backend && uv sync` then restart `make dev-backend`. If hashes are stale: `make reseed-users`. Other helpers: `make db-shell`, `make db-users`. |

---

## 3. Frontend errors at development time

| # | Symptom | Cause | Fix |
|---|---------|-------|-----|
| 14 | `Module not found: Can't resolve '@/lib/...'` | Working directory is wrong, or `tsconfig.json` paths missing. | `cd frontend && pnpm dev`. The `@/*` alias is set in [`frontend/tsconfig.json`](../../frontend/tsconfig.json). |
| 15 | `Error: Cannot find module 'next-intl/plugin'` | `pnpm install` not run, or the lockfile is stale. | `cd frontend && pnpm install`. Delete `node_modules` + `pnpm-lock.yaml` and reinstall if it persists. |
| 16 | Sinhala / Tamil characters render as `□□□` | First-time `next/font` failed to download Noto fonts (corporate proxy or air-gapped network). | Either retry on an unrestricted network, or self-host the fonts: download Noto Sans Sinhala and Noto Sans Tamil into `frontend/public/fonts/`, then swap [`app/layout.tsx`](../../frontend/app/layout.tsx) from `next/font/google` to `next/font/local`. |
| 17 | Cookie not set after login (302 → /login → /dashboard → /login loop) | One of: `secure: true` was set in dev (block on HTTP); origin mismatch; `CORS_ORIGINS` wrong on the backend. | Confirm the request to `/api/auth/establish` returns 200 and the response includes `Set-Cookie:` for both `access` and `refresh`. The default in [`route.ts`](../../frontend/app/api/auth/establish/route.ts) flips `secure` based on `process.env.NODE_ENV`. |
| 18 | Hydration warning: "Server rendered HTML didn't match…" involving `class="dark"` on `<html>` | Theme provider mounting before SSR knows the user preference. | Confirm `<html suppressHydrationWarning>` is set in [`app/layout.tsx`](../../frontend/app/layout.tsx). It already is — don't remove it. |
| 19 | Survey submit returns 422 with `value_error.json` | The form sent `answer_numeric` as a string. | The renderer in [`question-renderer.tsx`](../../frontend/components/forms/question-renderer.tsx) uses `valueAsNumber` for numeric inputs; if you've added a custom renderer, do the same. |
| 20 | `pnpm install` is extremely slow on first run | First-time Tailwind/Radix install with cold pnpm cache. | One-off cost. If consistently slow, configure pnpm's store offline mirror or set `--registry=https://registry.npmjs.org`. |
| 21 | Playwright timeouts on `getByLabel(/email/i)` | A page-level translation changed the visible label. | Either pin the test to a fixed locale (set `NEXT_LOCALE=en` cookie before navigation) or update the locator. |
| 22 | `You cannot have two parallel pages that resolve to the same path` — every page returns 500 | Two route groups (e.g. `(app)` and `(admin)`) both have a `page.tsx` at the same inner path; route groups are stripped from the URL so both resolve to one path. **This is a recurring bug class.** | Move one of them to a unique sub-path. Two solved examples in this repo: (1) F-63 — `/admin/surveys/awareness` → `/admin/surveys/awareness/responses`. (2) F-82 — every `(admin)/*` page moved into `(admin)/admin/*` so URLs match the sidebar (`/admin/m2/questions`, `/admin/regulations`, etc.) and the SME `/regulations` hub stops colliding. **Rule of thumb:** if a route group needs a URL prefix that distinguishes it from peer groups, make the prefix a real segment inside the group (e.g. `(admin)/admin/...`) — don't rely on the group name. |
| 23 | `TypeError: Cannot destructure property 'control' of '(0 , …useFormContext)(...)' as it is null` on a survey page | A custom hook called `useFormContext()` from a component that runs *before* (or outside) its enclosing `<FormProvider>`. The context is null until the provider renders. | Don't reach for context — pass the form return value through. The fix shipped here: `useAutosave({ methods })` now takes the `useForm()` return explicitly and drops `useFormContext()` entirely. Apply the same pattern for any new survey-side hook (`useFooBar(args, methods)` not `useFooBar(args)` + context lookup). |
| 24 | Survey wizard "submits" but no DB row appears AND the progress counter stays at "Question 1 of N" / "0 / 12 · 0%". | react-hook-form treats `.` and `[]` in field names as object-path notation. If a question id contains a dot (e.g. `awareness.v1.q01`), `register("awareness.v1.q01")` writes the value at `values.awareness.v1.q01` (nested) — but `values["awareness.v1.q01"]` (flat) returns `undefined`. The submit serialiser sends `answer_text: null`; backend's `_validate_answer` rejects; the catch swallows the error. Same root cause produces (a) silent zero-row submit AND (b) progress counters / autosave drafts that never increment. | Sanitise field ids at every RHF boundary. Pattern: [`frontend/lib/surveys/safe-field-id.ts`](../../frontend/lib/surveys/safe-field-id.ts) (`toFieldId(code)` replaces `.` with `__DOT__`). Build a parallel `idMap` (safe → original) and translate back at submit time so the wire format stays canonical. Touched twice in the codebase: **F-89** ([`survey-wizard.tsx`](../../frontend/components/forms/survey-wizard.tsx) — unified `/surveys` page) and **F-99** ([`survey-form.tsx`](../../frontend/components/forms/survey-form.tsx) — per-instrument `/surveys/awareness` page). **Rule of thumb:** every place that does `register(q.id)` / `<Controller name={q.id}>` / `values[q.id]` needs the safe id. M2/M3 codes (no dots) are unchanged by `toFieldId`; awareness codes are the only sufferer in the seeded bank. |
| 25 | (a) Sidebar scrolls up out of view as the user scrolls a long admin page; (b) on a phone the sidebar is invisible AND there's no way to open it. | (a) The desktop `<aside>` was a flex sibling of the scrolling main column without `position: sticky`, so it sat at the top of a stretching flex row and slid off as the row grew. (b) The sidebar used `hidden md:flex` and the topbar's collapse toggle used `hidden md:inline-flex` — both gated by `md`, so below 768 px the user had no nav surface. | (a) Add `md:sticky md:top-0 md:h-screen md:self-start` to the aside. `self-start` is required because flex items default to `align-self: stretch`, which fights `sticky`. (b) Build a mobile drawer with a Radix Dialog (`@radix-ui/react-dialog`) styled as a left-edge slide-in panel. The hamburger trigger sits at the topbar's left edge with `md:hidden`. Reuse the existing nav content via an extracted `<SidebarContent>`. Wire an `onItemClick` callback through every `<NavLink>` so the drawer auto-closes on nav. F-91 fixed both bugs in one slice; pattern: see `components/layout/mobile-sidebar.tsx` and `components/ui/sheet.tsx`. |

---

## 4. Database / migration errors

| # | Symptom | Cause | Fix |
|---|---------|-------|-----|
| 22 | `alembic upgrade head` says "Target database is not up to date" but `alembic current` shows the right rev | Two databases on the host (e.g. you switched ports). | Confirm `DATABASE_URL` in `.env` matches the database you're inspecting. Print it: `cd backend && uv run python -c "from app.settings import get_settings; print(get_settings().DATABASE_URL)"`. |
| 23 | `alembic revision --autogenerate` produces an empty migration | The new model isn't imported in [`backend/app/models/__init__.py`](../../backend/app/models/__init__.py). | Add it. |
| 24 | After dropping the `pg-data` Docker volume, `make migrate` fails: `extension "pgcrypto" does not exist` | The `init.sql` runs only on a *fresh* volume. Volume already existed. | `make reset-db`. |
| 25 | `psql: error: connection to server ... FATAL: password authentication failed` | You're hitting the right port but the `enigmatrix` user's password is different (e.g. you have a previous Postgres running). | `PGPASSWORD=devpass psql ...`. If a host Postgres is fighting on 5432, see issue #1. |
| 25b | `asyncpg.exceptions.InvalidAuthorizationSpecificationError: role "enigmatrix" does not exist` during `make migrate` | Your Postgres connection landed on a *different* server (almost always a host Homebrew Postgres listening on 5432) where the project's `enigmatrix` role was never seeded — or the Docker volume was created against different credentials. | (1) `lsof -nP -iTCP:5432 -sTCP:LISTEN` to see what's listening. (2) If it's Homebrew: `brew services stop postgresql@14`. (3) If the project's Docker volume is stale: `make reset-db`. (4) Verify with `docker exec -it enigmatrix-postgres psql -U enigmatrix -d enigmatrix -c '\du'` — the `enigmatrix` role must appear. (5) `make migrate` again. |
| 25c | Pydantic Settings: `error parsing value for field "CORS_ORIGINS"` → `JSONDecodeError: Expecting value: line 1 column 1` | `CORS_ORIGINS` in `.env` is a bare URL, but `pydantic-settings` JSON-decodes complex types like `list[AnyHttpUrl]`. | Use JSON-array form: `CORS_ORIGINS=["http://localhost:3000"]`. The `.env.example` ships in this shape; older copies of `.env` made before this fix will need a manual edit. |

---

## 5. Tests

| # | Symptom | Cause | Fix |
|---|---------|-------|-----|
| 26 | `testcontainers.core.exceptions.ContainerStartException: Couldn't connect to Docker` | Docker daemon not running. | macOS / Windows: open Docker Desktop. Linux: `sudo systemctl start docker`. WSL2: confirm Docker Desktop's WSL integration is on. |
| 27 | `pytest` first run hangs ~30s | First-time pull of `postgres:16-alpine`. | Wait. To pre-pull: `docker pull postgres:16-alpine`. |
| 28 | Unit test for `core/security` fails with `ValidationError` for missing settings | The unit test forgot to set env vars before importing `app.settings`. | Follow the `_env` fixture pattern in [`tests/unit/test_security.py`](../../backend/app/tests/unit/test_security.py): `monkeypatch.setenv(...)` + `get_settings.cache_clear()`. |
| 29 | Playwright `pnpm e2e` immediately fails with "Executable doesn't exist" | Browsers not installed. | `cd frontend && pnpm exec playwright install chromium`. |
| 30 | Playwright passes locally but flakes on dropdown selections | Dropdown menu animation race. | Add `await page.waitForLoadState('networkidle')` after a navigation, or use `page.locator('...').click({ force: true })` sparingly. |

---

## 6. pre-commit / linting

| # | Symptom | Cause | Fix |
|---|---------|-------|-----|
| 31 | `pre-commit` hook fails on the Sinhala/Tamil JSON saying "EOF expected" | The file ends without a final newline. | The `end-of-file-fixer` hook adds it; just `git add -u && git commit` again. |
| 32 | `ruff` complaints in test files about hardcoded passwords (S105/S106) | The MVP `pyproject.toml` already exempts `app/tests/**`; you may have added a test elsewhere. | Move the test under `app/tests/` or add `# noqa: S106`. |
| 33 | Prettier rewrites your TS files on every commit, swapping single → double quotes | Different `.prettierrc` than the repo. | The repo's `.prettierrc` mandates double quotes (`"singleQuote": false`). Adopt it. |

---

## 7. When you really can't figure it out

1. Re-read [`02_Quickstart.md`](02_Quickstart.md) end to end. 80% of issues stem from a missed step.
2. Run with verbose logging:
   ```bash
   APP_ENV=development uv run uvicorn app.main:app --log-level debug --port 8000
   ```
3. Inspect the audit log:
   ```sql
   SELECT * FROM audit_log ORDER BY occurred_at DESC LIMIT 50;
   ```
4. Open an entry in [`docs/tracker/SESSIONS.md`](../../tracker/SESSIONS.md) describing the failure under "Blockers". Future-you (or another contributor) will pick it up cold.

---

**Prev:** [`08_Testing.md`](08_Testing.md) &nbsp;·&nbsp; **Next:** [`10_Next_Steps.md`](10_Next_Steps.md)
