---
title: Render Migration Plan — Backend + Worker + Redis
status: planned
created: 2026-05-19
context: Vercel cannot host the gazette pipeline (Celery worker, Scrapy
  subprocess, persistent disk, long-running execution). This doc captures
  the migration path so login can stay on Vercel as a stateless API while
  the pipeline moves to a long-running host.
---

# Render Migration Plan — Backend + Worker + Redis

> **Status (2026-05-20):** Superseded by
> [Railway-Deployment-Plan.md](Railway-Deployment-Plan.md) as the chosen
> production target. This document is kept as an alternative reference
> — Render is still a valid host if Railway pricing, quotas, or volume
> model become limiting; the architecture (FastAPI + Celery worker +
> managed Redis + persistent disk) is identical, only the PaaS
> primitives differ (Render uses two services; Railway uses one).

## Why migrate

The current `https://enigmatrix-backend.vercel.app` deployment crashes with
`FUNCTION_INVOCATION_FAILED` and times out within Vercel's 10 s execution
limit. Even once env vars are set, the M1 gazette extraction pipeline
shipped in Sessions 26 / 32 / 42 / 45 cannot run on Vercel serverless:

| Subsystem                                                                                                          | Vercel constraint                                         | Verdict                           |
| ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------- | --------------------------------- |
| FastAPI request handling (login, regulation CRUD)                                                                  | 10 s cold-start limit (free)                              | works once env vars are correct   |
| Celery worker (`extract_gazette`, `preprocess_gazette`, `reconcile_raw_pdfs`, `run_scraper`, `migrate_raw_layout`) | Vercel has no persistent worker process                   | **does not work**                 |
| Scrapy spider (`run_scraper` → `subprocess.run("scrapy crawl …")`)                                                 | Spider runs 20–60 s; subprocess can't outlive the request | **does not work**                 |
| Redis broker                                                                                                       | Vercel has no managed Redis                               | **does not work** (need external) |
| Local file storage (`storage/m1/raw/<source_id>/*.pdf`)                                                            | Vercel FS is ephemeral per cold start                     | **does not work**                 |
| Scrapy + Celery + asyncpg + transformers imports                                                                   | Slow cold start, often exceeds 10 s                       | unreliable                        |

Render gives us managed Postgres + managed Redis + always-on web service +
always-on background worker + persistent disk — every constraint above is
lifted.

## Target topology

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Vercel (frontend only)                                                  │
│  enigmatrix-frontend.vercel.app          NEXT_PUBLIC_API_BASE_URL →      │
└──────────────────────────────────────────────────────────────────────────┘
                                                          │
                                                          ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Render                                                                   │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Web Service  enigmatrix-backend                                   │  │
│  │  FastAPI (uvicorn) — /api/v1/admin/m1/extraction/*                 │  │
│  │  $7/mo Starter (free has cold-start sleep; not OK for an API)      │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Background Worker  enigmatrix-celery-worker                       │  │
│  │  `celery -A app.celery_config:celery_app worker`                   │  │
│  │  Picks up extract / preprocess / reconcile / spider tasks          │  │
│  │  $7/mo Starter                                                     │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────┐    ┌──────────────────────────┐            │
│  │ Managed Postgres         │    │ Managed Redis (Key Value)│            │
│  │ (user already has one)   │    │ Render Redis ~free tier  │            │
│  │ DATABASE_URL             │    │ CELERY_BROKER_URL        │            │
│  └──────────────────────────┘    └──────────────────────────┘            │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Persistent Disk (mounted on the worker)                           │  │
│  │  /var/data/storage  →  STORAGE_LOCAL_PATH                          │  │
│  │  Holds storage/m1/raw/<source_id>/*.pdf                            │  │
│  │  Render Disk add-on (~$0.25/GB-month); 10 GB enough for ≈10 k PDFs │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

## render.yaml (Infrastructure-as-Code)

Drop this at the repo root of `enigmatrix-backend` and connect Render to
the GitHub repo. Render auto-provisions all four services on push to
`main`.

```yaml
services:
  - type: web
    name: enigmatrix-backend
    runtime: python
    plan: starter           # $7/mo; free has unacceptable cold-start sleep
    region: singapore       # closest to Colombo
    rootDir: .
    buildCommand: |
      pip install --upgrade pip uv
      uv pip install --system -r <(uv pip compile pyproject.toml)
    startCommand: |
      alembic upgrade head &&
      uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    autoDeploy: true
    envVars:
      - key: APP_ENV
        value: production
      - key: APP_SECRET_KEY
        generateValue: true
      - key: JWT_SECRET
        generateValue: true
      - key: DATABASE_URL
        sync: false                   # set manually from existing PG
      - key: DB_SSL
        value: "true"
      - key: STORAGE_LOCAL_PATH
        value: /var/data/storage
      - key: CORS_ORIGINS
        value: '["https://enigmatrix-frontend.vercel.app"]'
      - key: CORS_ORIGIN_REGEX
        value: '^https://enigmatrix-frontend(-[a-z0-9-]+)?\.vercel\.app$'
      - key: CELERY_BROKER_URL
        fromService:
          name: enigmatrix-redis
          type: redis
          property: connectionString
    disk:
      name: m1-storage
      mountPath: /var/data/storage
      sizeGB: 10

  - type: worker
    name: enigmatrix-celery-worker
    runtime: python
    plan: starter
    region: singapore
    rootDir: .
    buildCommand: |
      pip install --upgrade pip uv
      uv pip install --system -r <(uv pip compile pyproject.toml)
      # Tesseract + poppler for the OCR fallback in the extraction chain
      apt-get update && apt-get install -y tesseract-ocr poppler-utils
    startCommand: |
      celery -A app.celery_config:celery_app worker --loglevel=info --concurrency=2
    envVars:                          # share all of the web service's env
      - fromService:
          name: enigmatrix-backend
          type: web
          envVarKey: APP_SECRET_KEY
      - fromService:
          name: enigmatrix-backend
          type: web
          envVarKey: JWT_SECRET
      - fromService:
          name: enigmatrix-backend
          type: web
          envVarKey: DATABASE_URL
      - key: DB_SSL
        value: "true"
      - key: STORAGE_LOCAL_PATH
        value: /var/data/storage
      - key: CELERY_BROKER_URL
        fromService:
          name: enigmatrix-redis
          type: redis
          property: connectionString
    disk:
      name: m1-storage                # SAME disk as the web service
      mountPath: /var/data/storage
      sizeGB: 10

  - type: redis
    name: enigmatrix-redis
    plan: free                        # 25 MB; enough for Celery task queue
    region: singapore
    ipAllowList: []                   # only Render-internal traffic
```

## Step-by-step migration

1. **Create the Render services from `render.yaml`** (one PR adding the
   file to `enigmatrix-backend` root + connect Render to the repo).
   Render will create web / worker / redis on the first push.

2. **Set the unsynced secrets** in the Render dashboard:
   - `DATABASE_URL` on the web service (user's managed PG connection
     string). The worker inherits it via `fromService`.

3. **Run the Alembic migration once.** The `startCommand` runs
   `alembic upgrade head` on every web boot; first boot creates all M1
   tables in the managed Postgres.

4. **Verify**:
   - `curl https://enigmatrix-backend.onrender.com/health` → 200
   - `curl https://enigmatrix-backend.onrender.com/docs` → Swagger UI
   - Render dashboard → enigmatrix-celery-worker logs show
     `[tasks]` listing all six task names (extract_gazette,
     preprocess_gazette_task, reconcile_raw_pdfs, run_scraper,
     migrate_raw_layout, run_gazette_spider).

5. **Switch the frontend** in Vercel Project Settings → Environment
   Variables:
   - Replace `NEXT_PUBLIC_API_BASE_URL` = `https://enigmatrix-backend.onrender.com`
   - Redeploy.

6. **Decommission the Vercel backend project** (optional). Either
   delete it or leave it idle — it's no longer the upstream.

## One-off post-deploy task

After the web service boots for the first time, hit the storage
migration endpoint to move any legacy flat PDFs into source folders:

```bash
curl -X POST https://enigmatrix-backend.onrender.com/api/v1/admin/m1/extraction/migrate-raw-layout \
     -H "Authorization: Bearer <admin-jwt>"
```

(See [02_M1_Data_Requirements.md](../../02-Research-Modules/1%20Module-1-Awareness-Gap/02_M1_Data_Requirements.md)
for the partitioned `m1/raw/<source_id>/` layout.)

## Cost estimate

| Service | Plan | Monthly |
|---|---|---|
| Web (FastAPI) | Starter | $7 |
| Worker (Celery) | Starter | $7 |
| Redis | Free (25 MB) | $0 |
| Disk (10 GB) | Add-on | $2.50 |
| Postgres | (user-supplied managed PG) | — |
| **Total** | | **≈ $16.50** |

Add another $7 if you outgrow the free Redis (250 MB+ Starter tier).

## Open follow-ups

- **Sentry**: Render supports it via env var (`SENTRY_DSN` already in
  `settings.py`); set after deploy.
- **Worker scaling**: bump `--concurrency=2` once load grows past one
  extraction per second; can also add a second worker instance.
- **gazette.lk fallback**: Render makes Playwright easy (just another
  apt package), so the deferred gazette.lk integration is unblocked
  once we're here.
- **CDN for raw PDFs**: optional; for now the admin UI fetches PDFs
  directly through `/raw-pdf` which streams from disk.

## Reference

- Backend Vercel debug session: 2026-05-19 — confirmed
  `FUNCTION_INVOCATION_FAILED` and 10 s timeout on
  `https://enigmatrix-backend.vercel.app/`.
- M1 Phase 2 architecture: `02-Research-Modules/1 Module-1-Awareness-Gap/02_M1_Data_Requirements.md`.
- Celery + Scrapy task lineup that needs a long-running worker:
  `app/tasks/m1/` in `enigmatrix-backend`.
