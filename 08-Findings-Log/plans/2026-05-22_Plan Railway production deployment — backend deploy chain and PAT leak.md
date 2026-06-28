# Plan: Railway production deployment — backend deploy chain and PAT leak

## Context

This was the first push of `enigmatrix-backend` to production on Railway, following the `04-Technology-Stack/infra/Railway-Deployment-Plan.md` runbook. The frontend remains on Vercel; the FastAPI app + Celery worker + Beat + Scrapy spider subprocess + shared `/data/storage` volume all run in a single Railway service.

User logged into Chrome as `g.hub.fri@gmail.com`. The actual GitHub owner of the two repos (`enigmatrix-backend`, `enigmatrix-ml`) is **`ghubfri-bot`** — the Railway plan document still referenced `Enigmatrixx/enigmatrix-ml` and required correction.

Operator side-effects: created project `satisfied-prosperity` in Railway, added Redis plugin with its `redis-volume`, added 10 GB Volume mounted at `/data/storage` on the backend service, set 10 service env vars.

The deploy chain failed four times before succeeding on the fifth attempt. The final successful deploy printed the operator's GitHub PAT in plaintext in the build log and baked it into the container image's `/root/.gitconfig` — operator chose to defer PAT rotation rather than block on it.

## Goal

1. Get `enigmatrix-backend` running in production on Railway with the existing extraction pipeline (FastAPI + Celery worker + Beat) sharing the volume.
2. Make `uv sync --frozen --no-dev` resolve the private `enigmatrix-ml` Git dependency at both build time and runtime.
3. Confirm end-to-end: `/health` → 200, CORS preflight from Vercel → 200, admin login + extraction trigger → live extraction events in the worker log.

## Steps / tasks

1. ✅ **PAT issued** — Created a fine-grained PAT on `github.com` under `g.hub.fri@gmail.com`. Resource owner `ghubfri-bot`, repo `enigmatrix-ml`, permissions `Contents: Read-only`.
2. ✅ **Railway project verified** — `satisfied-prosperity` project, `production` env, `enigmatrix-backend` service connected to `ghubfri-bot/enigmatrix-backend` `main`, Redis plugin online (with its own `redis-volume`).
3. ✅ **10 GB volume mounted** — On the `enigmatrix-backend` service: Settings → Volumes → mount path `/data/storage`, size 10 GB.
4. ✅ **10 env vars set on the service** — `APP_ENV=production`, `APP_SECRET_KEY=<generated>`, `JWT_SECRET=<generated>`, `DATABASE_URL=<managed Postgres>`, `DB_SSL=true`, `STORAGE_LOCAL_PATH=/data/storage`, `CORS_ORIGINS=["https://enigmatrix-frontend.vercel.app"]`, `CORS_ORIGIN_REGEX=^https://enigmatrix-frontend(-[a-z0-9-]+)?\.vercel\.app$`, `CELERY_BROKER_URL=${{Redis.REDIS_URL}}` (Railway variable reference, not the literal Redis URL), `GITHUB_TOKEN=<PAT>`.
5. ✅ **Deploy failure #1 — workspace = true** — Build log showed `error: Failed to generate package metadata for enigmatrix-backend==0.1.0 @ editable+. Caused by: enigmatrix-ml references a workspace in tool.uv.sources (e.g., enigmatrix-ml = { workspace = true }), but is not a workspace member`. Cause: the `[tool.uv.sources]` block in `enigmatrix-backend/pyproject.toml` still had `enigmatrix-ml = { workspace = true }` (which only works from the xyz monorepo root). The Railway-Deployment-Plan said this was supposed to land but hadn't.
6. ✅ **First-attempt fix (incorrect)** — Edited `enigmatrix-backend/pyproject.toml` line 65 to `enigmatrix-ml = { git = "https://${GITHUB_TOKEN}@github.com/ghubfri-bot/enigmatrix-ml.git", branch = "main" }`. Two corrections from the original plan: `ssh://` → `https://${GITHUB_TOKEN}@`, and `Enigmatrixx` → `ghubfri-bot`. User pushed.
7. ✅ **Deploy failure #2 — push didn't land** — Same `workspace = true` error in the next Railway build. Cause: user ran `git push origin main` before staging the file — push pushed an empty commit. GitHub `main` still showed the old `ssh://git@github.com/Enigmatrixx/...` URL. Diagnosed by reading `github.com/ghubfri-bot/enigmatrix-backend/blob/main/pyproject.toml` content the operator pasted back.
8. ✅ **Lockfile regeneration + clean push** — Operator ran `git add pyproject.toml && uv lock && git add uv.lock && git commit -m "..." && git push origin main`. The previous `uv.lock` did not list `enigmatrix-ml` in `requires-dist` at all (the lockfile was stale from a workspace-only setup).
9. ✅ **Deploy failure #3 — Railway cache** — New build still showed `python:3.11-slim` (the local Dockerfile says `python:3.12-slim`), and every COPY/RUN layer was `cached 0ms`. The image digest was identical to the failing prior build. Railway was serving a stale snapshot. Diagnosis: compare commit SHA in Railway deployment header against `git log origin/main -1 --format=%H`; force redeploy via Deployments tab → Deploy.
10. ✅ **Deploy failure #4 — uv doesn't expand env vars in URLs** — Build now ran fresh with the Python 3.12 base image, BUT at runtime the start script's `uv run alembic upgrade head` triggered `uv sync` and crashed with `fatal: could not read Password for 'https://$%7BGITHUB_TOKEN%7D@github.com'`. The literal string `${GITHUB_TOKEN}` was URL-encoded by uv and passed as the username. uv does **not** expand environment variables inside `tool.uv.sources` URLs — known limitation.
11. ✅ **Final fix — git config insteadOf injection** — Three file edits:
    - `enigmatrix-backend/pyproject.toml`: URL changed to plain `https://github.com/ghubfri-bot/enigmatrix-ml.git` (no `${GITHUB_TOKEN}`).
    - `enigmatrix-backend/Dockerfile`: added `ARG GITHUB_TOKEN` and `RUN if [ -n "$GITHUB_TOKEN" ]; then git config --global url."https://x-access-token:${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"; fi` **before** the `COPY pyproject.toml uv.lock ./` + `RUN uv sync --frozen --no-dev` lines.
    - `enigmatrix-backend/scripts/start_railway.sh`: added the same `git config` injection at runtime startup (after `set -e`), because the start script's `uv run` may trigger a lazy `uv sync` that also needs git auth.
    - Regenerated `uv.lock`. Pushed.
12. ✅ **Deploy success** — Build log: `Updated https://github.com/ghubfri-bot/enigmatrix-ml.git (cfb51ba323765a074e776b5053b294b26860fd77)` → `Built enigmatrix-ml @ git+https://github.com/ghubfri-bot/enigmatrix-ml.git@cfb51ba...` → `Installed 25 packages in 2.24s` → `INFO [alembic.runtime.migration]` → `Application startup complete` on port 8080 → `celery@d041fdf5158f ready` connected to `redis://default:**@redis.railway.internal:6379//` → `celery beat v5.6.3 (recovery) is starting` → `[1/1] Healthcheck succeeded!` → `INFO: 100.64.0.2:34232 - "GET /health HTTP/1.1" 200 OK`.
13. ✅ **End-to-end verified by live traffic** — Operator triggered a Bills extraction (scope `2025-01-01 → 2025-12-31`, task `a33612c1-54a4-4698-9536-797ab1016be0`). Worker logs showed `extract_gazette: regulation <uuid> extracted via pymupdf (22082 chars)` succeeding in ~5s per row; 10 PDFs in scope, 6 preprocessed, 4 extracted, 58 sub-documents detected. CORS-preflighted `OPTIONS /api/v1/admin/m1/extraction/progress` and `/summary` from the Vercel frontend returned 200 — confirming `NEXT_PUBLIC_API_BASE_URL` was correctly pointing at the Railway URL.

## Errors fixed (during deploy)

- `enigmatrix-ml references a workspace ... but is not a workspace member` — fixed by switching `[tool.uv.sources]` to a Git source.
- `Enigmatrixx/enigmatrix-ml` → `ghubfri-bot/enigmatrix-ml` — wrong owner in the deployment plan.
- `ssh://git@github.com/...` form + `GITHUB_TOKEN` was incompatible — switched to HTTPS form.
- `git push` without `git add` produced empty commits — diagnosed by comparing GitHub `main` content vs local file content.
- Railway used cached snapshot image (Python 3.11 vs current Dockerfile 3.12) — forced fresh build via Deploy button after commit SHA mismatch confirmed.
- Stale `uv.lock` (no `enigmatrix-ml` in `requires-dist`) — regenerated with `uv lock`.
- `uv` doesn't expand `${ENV_VAR}` inside `tool.uv.sources` URLs — switched to git's `insteadOf` URL rewrite (works at both build time via `ARG GITHUB_TOKEN` and runtime via env var inside `start_railway.sh`).
- PAT leaked in build log + image `.gitconfig` — flagged as a critical security issue; operator deferred rotation.

## Technical notes

- **Service URL:** `https://enigmatrix-backend-production.up.railway.app`. Visible under Service → Settings → Networking.
- **Single-service topology:** uvicorn + Celery worker (`--concurrency=2`) + Celery Beat run under the same `start_railway.sh` process tree so all three share `/data/storage`. Railway Volumes attach to a single service.
- **CELERY_BROKER_URL = `${{Redis.REDIS_URL}}`** — Railway variable reference, not the literal value. This expands at runtime to the Redis plugin's current internal URL (`redis://default:**@redis.railway.internal:6379//`); if Redis is restarted with a new URL, the broker URL follows automatically. Pasting the literal would go stale.
- **GitHub PAT injection via insteadOf** — `git config --global url."https://x-access-token:${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"` runs once at image build time (using `ARG GITHUB_TOKEN`) and again at container startup (using env var). The username `x-access-token` is the canonical placeholder GitHub accepts for HTTPS Basic auth with a PAT as the password.
- **Why the PAT leaked:** Docker's `RUN if [ -n "$GITHUB_TOKEN" ]; then ...` command expands the env var **into the executed RUN command string**, which Railway then logs verbatim. Docker itself emitted `SecretsUsedInArgOrEnv: Do not use ARG or ENV instructions for sensitive data` in the same build. Proper fix is `RUN --mount=type=secret,id=github_token` (BuildKit secrets), tracked as a follow-up.
- **Auto-deploy on push** is enabled on the service; new commits to `ghubfri-bot/enigmatrix-backend` `main` trigger a fresh build within ~30s.

## Decisions taken

- **Option A (PAT) over Option B (deploy key)** — simpler to rotate, no SSH agent juggling in the Docker build.
- **`insteadOf` URL rewrite over Docker buildx secrets** — buildx-secret refactor was scoped as a follow-up rather than blocking the deploy.
- **PAT rotation deferred** — operator explicitly chose to ship with the leaked PAT visible in the build log + image `.gitconfig`. Known risk; tracked.
- **Force-true cancel rollback** scoped into Stage 1, not deploy.
- **No CI/CD added in this session** — Railway's auto-deploy is the only post-push automation. Follow-up to add GitHub Actions for lint/test pre-merge.

## Open questions

- Should the PAT-rotation + buildx-secret refactor happen as a single PR or staged?
- Should `CLOSESPIDER_TIMEOUT_NO_ITEM` and Celery `--max-tasks-per-child` be tuned for the production worker?
- Is there value in pinning the Python base image to a SHA digest (`FROM python:3.12-slim@sha256:...`) for reproducible builds?
- Should the `Railway-Deployment-Plan.md` document be updated to reflect the actual fix sequence (insteadOf trick, ghubfri-bot owner), so the next deploy can skip the four failures?

## Acceptance criteria

- [x] `enigmatrix-backend` service shows green Online in Railway dashboard.
- [x] Healthcheck on `/health` returns 200.
- [x] Frontend on Vercel reaches the backend (CORS preflight 200, admin endpoints 200).
- [x] Admin can trigger a Bills extraction and see live rows progress through `ingested → extracted → preprocessed` in the existing Sources hub UI.
- [x] Celery worker log shows `extract_gazette: ... succeeded` lines for at least one regulation.
- [ ] PAT rotated to a fresh token + Dockerfile switched to BuildKit secrets (deferred).

## Linked trackers

- [CHANGES.md](../CHANGES.md) — F-193
- [FEATURES.md](../FEATURES.md) — F-193
- [SESSIONS.md](../SESSIONS.md) — Session 55
- [ENIGMATRIX_MASTER_CONTEXT.md](../ENIGMATRIX_MASTER_CONTEXT.md) — production-deployment topology + PAT-injection pattern note
- Companion plan: [2026-05-22_Plan Cross-repo code quality audit — Stage 4](./2026-05-22_Plan%20Cross-repo%20code%20quality%20audit%20—%20Stage%204.md) — covers the PAT-leak remediation tasks
