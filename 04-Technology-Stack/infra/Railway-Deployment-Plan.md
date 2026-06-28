---
title: Railway Deployment Plan — Backend + Worker + Beat (single service)
status: primary production target
created: 2026-05-19
context: Vercel cannot host the gazette pipeline. The frontend stays on
  Vercel; the FastAPI app + Celery worker + Celery Beat + Scrapy spider
  subprocess move to a single Railway service that shares a 10 GB
  Volume with the user's external managed Postgres and a Railway Redis
  plugin.
companion: Render-Migration-Plan.md (alternative reference)
---

# Railway Deployment Plan — Backend + Worker + Beat (single service)

> **Primary production target as of 2026-05-19.** Render plan kept as
> an alternative — switch if Railway pricing, quotas, or volume model
> become limiting.

## Why Railway

Vercel's serverless model can't host this backend:

- Scrapy spider subprocess runs 20–60 s per crawl (well past Vercel's 60 s pro / 10 s free function limit).
- Celery worker needs an always-on process; Vercel has none.
- Local-filesystem PDF storage (`storage/m1/raw/<source_id>/*.pdf`) is wiped between cold starts on Vercel.
- The combined import tree (Scrapy + Celery + PyMuPDF + pdfplumber + pytesseract + pdf2image + the `enigmatrix-ml` workspace member) exceeds Vercel's 250 MB unzipped function-size limit.

Railway gives us managed Redis + always-on container + 10 GB persistent volume in one project — every constraint above is lifted, and the deploy stays single-service (vs Render's two-service split).

## Target topology

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Vercel (frontend only)                                                 │
│  enigmatrix-frontend.vercel.app          NEXT_PUBLIC_API_BASE_URL →     │
└─────────────────────────────────────────────────────────────────────────┘
                                                          │
                                                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Railway project: enigmatrix-backend                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Service  enigmatrix-backend  (Dockerfile build)                 │   │
│  │  scripts/start_railway.sh runs:                                  │   │
│  │    1. alembic upgrade head                                       │   │
│  │    2. celery -A app.celery_config:celery_app worker  (background) │  │
│  │    3. celery -A app.celery_config:celery_app beat    (background) │  │
│  │    4. uvicorn app.main:app --port $PORT             (foreground) │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────┐   ┌──────────────────────────────────┐    │
│  │ Redis plugin             │   │ Volume  /data/storage  (10 GB)   │    │
│  │ CELERY_BROKER_URL ←      │   │ STORAGE_LOCAL_PATH ←             │    │
│  └──────────────────────────┘   └──────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                  │                                  │
                  ▼                                  ▼
       (external: user's managed Postgres — Neon / Supabase / Aiven / …)
```

The Volume holds `storage/m1/raw/<source_id>/*.pdf`. uvicorn, the Celery worker, and Beat are all in the same container so they share the volume — Railway Volumes attach to a single service.

## Pre-deploy code changes

All landed in the `Enigmatrixx/enigmatrix-backend` repo. Diff at a glance:

| File | Change |
|---|---|
| `pyproject.toml` | `[tool.uv.sources]` for `enigmatrix-ml` switched from `workspace = true` to a Git source (`ssh://git@github.com/Enigmatrixx/enigmatrix-ml.git`, branch `main`). |
| (xyz root) `pyproject.toml` | Added `[tool.uv.sources] enigmatrix-ml = { workspace = true }` so local dev still uses the editable workspace member; the backend's per-member Git source only applies when uv runs from outside xyz. |
| `Dockerfile` | Python 3.12-slim. Installs `tesseract-ocr` + `tesseract-ocr-sin` + `tesseract-ocr-tam` + `poppler-utils` + `git` system packages. CMD switches to `sh scripts/start_railway.sh`. |
| `scripts/start_railway.sh` (new) | Runs `alembic upgrade head`, then Celery worker + Beat in the background, then uvicorn in the foreground. SIGTERM cascades to children. |
| `railway.toml` (new) | Builder = Dockerfile, healthcheck `/health`, restart on failure (max 5). |
| `.dockerignore` | Trimmed: excludes `.git`, `storage/`, `app/tests/`, caches, IDE files. |

## Auth for the private `enigmatrix-ml` repo

The `enigmatrix-ml` repo is private. Railway needs read access at build time so `uv sync --frozen` can resolve the Git source. Two ways — pick one:

### Option A (recommended): GitHub PAT in `GITHUB_TOKEN`

1. Create a fine-scoped PAT on `github.com/Enigmatrixx/enigmatrix-ml` (Settings → Developer settings → Personal access tokens → Fine-grained) with **Repository access: Enigmatrixx/enigmatrix-ml** + **Contents: Read-only**.
2. Set on Railway service: `GITHUB_TOKEN=<pat>`.
3. Change `pyproject.toml` source to HTTPS-with-token form (Railway substitutes the env var at build time):

   ```toml
   [tool.uv.sources]
   enigmatrix-ml = { git = "https://${GITHUB_TOKEN}@github.com/Enigmatrixx/enigmatrix-ml.git", branch = "main" }
   ```

### Option B: GitHub deploy key in `RAILWAY_GIT_SSH_KEY`

1. Generate an ED25519 key: `ssh-keygen -t ed25519 -C "railway-enigmatrix-ml" -f ./railway_ml -N ""`.
2. Add the **public** key (`railway_ml.pub`) as a deploy key on `Enigmatrixx/enigmatrix-ml` (Settings → Deploy keys → Add deploy key, read-only).
3. Set on Railway service: `RAILWAY_GIT_SSH_KEY=<contents of ./railway_ml private key>`.
4. Keep the `ssh://git@github.com/...` source in `pyproject.toml` (already set).
5. Adjust Dockerfile to forward the SSH key into the `uv sync` step. The current Dockerfile uses `--mount=type=ssh`; on Railway, the SSH agent needs to be primed in the build environment.

## Railway dashboard setup

1. **Create project** → "Deploy from GitHub repo" → `Enigmatrixx/enigmatrix-backend` → branch `main`.
2. **Add Redis plugin**: Project → "+ New" → Database → Redis. Railway exposes the variable `REDIS_URL` on the project.
3. **Add Volume**: Service → Settings → Volumes → Add → mount path `/data/storage`, size `10 GB`.
4. **Set environment variables** (Service → Variables):

   | Key | Value |
   |---|---|
   | `APP_ENV` | `production` |
   | `APP_SECRET_KEY` | *generate locally with `python -c "import secrets;print(secrets.token_urlsafe(32))"`* |
   | `JWT_SECRET` | *same generator (different value)* |
   | `DATABASE_URL` | *your managed Postgres connection string* |
   | `DB_SSL` | `true` |
   | `STORAGE_LOCAL_PATH` | `/data/storage` |
   | `CORS_ORIGINS` | `["https://enigmatrix-frontend.vercel.app"]` |
   | `CORS_ORIGIN_REGEX` | `^https://enigmatrix-frontend(-[a-z0-9-]+)?\.vercel\.app$` |
   | `CELERY_BROKER_URL` | `${{Redis.REDIS_URL}}` (Railway variable reference; expands to the Redis URL of this project's plugin) |
   | `GITHUB_TOKEN` *or* `RAILWAY_GIT_SSH_KEY` | per the auth option chosen above |

5. **Deploy** (auto-triggered on first connect, or via "Deploy"). Tail the build log:
   - `apt-get install` for tesseract + poppler + git
   - `uv sync --frozen --no-dev` resolves `enigmatrix-ml` from the Git source (this is where auth errors show up if they exist)
   - `alembic upgrade head` runs and reports each revision
   - `Application startup complete` (uvicorn ready)
   - `celery@<host> ready` (worker connected to Redis)
   - `celery beat v… is starting` (scheduler running)

## Frontend env update (Vercel)

Vercel Dashboard → `enigmatrix-frontend` → Settings → Environment Variables:

| Key | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `https://<service>.up.railway.app` *(use the URL Railway assigns; visible in Service → Settings → Networking)* |

Redeploy the frontend.

## Verification

```bash
# 1. Health
curl https://<service>.up.railway.app/health
# Expected: {"status":"ok","env":"production"}

# 2. CORS preflight from the Vercel frontend origin
curl -I -X OPTIONS https://<service>.up.railway.app/api/v1/auth/login \
  -H "Origin: https://enigmatrix-frontend.vercel.app" \
  -H "Access-Control-Request-Method: POST"
# Expected: HTTP 200 with access-control-allow-origin matching the regex

# 3. Login
curl -X POST https://<service>.up.railway.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@…","password":"…"}'
# Expected: {"access":"<jwt>","refresh":"<jwt>"}

# 4. Volume sanity (after a successful extraction)
railway run -- ls -la /data/storage/m1/raw/EGZ/ | head
```

In the Sources hub UI:
- Tiles for EGZ / GZ / BILL / ACT render with non-zero counts (read from `/api/v1/admin/m1/extraction/sources`).
- Click Bills → "Start Bills extraction" with `2026-01-01 → 2026-01-31` scope. Watch the worker log in Railway:
  - `run_scraper: launching bills_spider …`
  - `extract_gazette: regulation … extracted via pymupdf (… chars)`
  - `preprocess_gazette: regulation … preprocessed (cleaned_text=…, sub_documents=…, primary_language=en)`
- Progress panel shows rows advancing `ingested → extracted → preprocessed`.

## Cost estimate

| Item | Plan | Monthly |
|---|---|---|
| Hobby plan (project) | Hobby | $5 flat (includes $5 of usage) |
| Service compute | usage-based | ~$5–15 depending on traffic |
| Redis plugin | usage-based | ~$3–5 |
| Volume (10 GB) | $0.25/GB-month | $2.50 |
| **Total** | | **≈ $15–30/mo** |

Render Starter alternative is ~$16.50/mo with the same workload split into two services. Pick on operational preference, not cost.

## Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `git@github.com: Permission denied (publickey)` during build | `enigmatrix-ml` SSH/HTTPS auth not set | Set `GITHUB_TOKEN` or `RAILWAY_GIT_SSH_KEY` and redeploy |
| OOMKilled on Celery worker | extract_gazette + preprocess concurrent runs blow past memory cap | Worker is already `--concurrency=2`; lower to 1 if needed, or bump the Railway instance tier |
| Volume "100% full" | Spider keeps downloading; PDFs accumulate | Increase volume size (Settings → Volumes → Resize) or implement object-storage migration (see follow-ups) |
| Broker connection drops | Redis plugin restarting | Celery auto-reconnects; persistent disconnects mean the Redis plugin needs scaling up |
| `alembic upgrade head` fails on boot | DATABASE_URL wrong / DB unreachable | Confirm `DB_SSL=true` and the URL uses `postgres://` (auto-normalised to `postgresql+asyncpg://`) |

## Open follow-ups

- **Object storage for PDFs (S3 / Cloudflare R2 / Backblaze B2)** — would let us split the web service from the worker (Railway Volumes attach to one service only, so combining is the workaround). Track in FEATURES.md.
- **gazettes.lk fallback via Playwright** — Railway supports Playwright easily (apt-get).
- **Sentry wiring** — `SENTRY_DSN` setting already exists; just unset until later.
- **Multi-language PDF ingest for Weekly Gazettes / Bills / Acts** — currently English only.

## Reference

- Backend code changes: see "Pre-deploy code changes" above; the diff landed in `Enigmatrixx/enigmatrix-backend` `main`.
- Alternative deploy target: [Render-Migration-Plan.md](./Render-Migration-Plan.md) — same architecture, two services + smaller bill, kept as a fallback.
- M1 pipeline architecture: [`02-Research-Modules/1 Module-1-Awareness-Gap/02_M1_Data_Requirements.md`](../../02-Research-Modules/1%20Module-1-Awareness-Gap/02_M1_Data_Requirements.md).
- Project Atlas: [`01-Project-Overview/Project-Atlas.md`](../../01-Project-Overview/Project-Atlas.md) — A-to-Z overview, status grid links here under §W.
