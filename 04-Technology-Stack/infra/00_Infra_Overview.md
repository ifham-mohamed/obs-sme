# Infra Domain

Docker Compose · PostgreSQL 16 · ChromaDB 0.5.5 · Redis · nginx + Let's Encrypt · GitHub Actions CI/CD · Prometheus + Grafana

## Stack

| Component | Role |
|-----------|------|
| PostgreSQL 16 | Primary relational store — all survey data, users, regulations, scores |
| ChromaDB 0.5.5 | Vector store — reserved for M2 RAG pipeline (BUILD_08, not yet built) |
| Redis | Celery message broker (BUILD_12, not yet built) |
| Docker Compose | Local dev orchestration — backend + frontend + postgres + chromadb |
| nginx | Reverse proxy + TLS termination (production) |
| GitHub Actions | CI/CD pipeline — test + build + deploy (BUILD_15, not yet wired) |
| Prometheus + Grafana | Metrics + dashboards (BUILD_15, not yet wired) |

## Production deployment

| Surface | Host | Doc |
|---|---|---|
| Frontend | Vercel — `enigmatrix-frontend.vercel.app` | (deployed) |
| Backend + worker + beat | **Railway** (primary target) | [Railway-Deployment-Plan.md](Railway-Deployment-Plan.md) |
| Postgres | User-supplied managed PG (Neon / Supabase / Aiven / …) | — |
| Redis | Railway Redis plugin | (in Railway plan) |
| Persistent PDF storage | Railway Volume (10 GB at `/data/storage`) | (in Railway plan) |
| Alternative deploy target | Render (kept as fallback reference) | [Render-Migration-Plan.md](Render-Migration-Plan.md) |
| Slim Vercel build (auth/reads only, no pipeline) | Vercel — `enigmatrix-backend.vercel.app` | stopgap until Railway is live |

## Database migrations

11 Alembic versions through Session 19:

| Migration | What it adds |
|-----------|-------------|
| `202605080001` | Initial schema — users, sme_profiles, survey_responses, audit_log |
| `202605090001` | M2/M3 schema — regulatory_domains, sectors, m2_questions, m3_* tables |
| `202605100001` | m1_regulations, survey_questions rename, module_number column |
| `202605110001` | m1_regulations.is_active flag |
| `202605120001` | survey_question_regulations M:N junction |
| `202605140001` | created_by/updated_by + audit_log.record_key |
| `202605160001` | survey_sessions table + session_id/regulation_id/survey_mode on responses |
| `202605170001` | survey_limits singleton |
| `202605180001` | awareness module_number 0 → 1 |

## Files

### SETUP/
| File | Description |
|------|-------------|
| [01_Prerequisites.md](SETUP/01_Prerequisites.md) | Tool installation requirements — Python 3.11, Node 20, Docker, pnpm, psql, pre-commit |
| [02_Quickstart.md](SETUP/02_Quickstart.md) | Five-command startup: clone → env → `make up` → `make migrate` → `make seed` → dev servers |
| [09_Troubleshooting.md](SETUP/09_Troubleshooting.md) | 13 common failures with fixes — port binding, asyncpg, JWT_SECRET, CORS, bcrypt version |

### BUILD_PLAN/
| File | Description |
|------|-------------|
| [BUILD_01_Project_Initialization.md](BUILD_PLAN/BUILD_01_Project_Initialization.md) | Prerequisites, tooling checklist, VS Code extensions, env files, repo bootstrap |
| [BUILD_02_Folder_Structure.md](BUILD_PLAN/BUILD_02_Folder_Structure.md) | Monorepo layout spec: backend/, frontend/, ml/, infra/, docs/ with complete directory tree |
| [BUILD_04_Database_and_Storage.md](BUILD_PLAN/BUILD_04_Database_and_Storage.md) | Three stores spec (PostgreSQL = truth, ChromaDB = vectors, object storage = files) |
| [BUILD_14_Deployment_Cloud.md](BUILD_PLAN/BUILD_14_Deployment_Cloud.md) | Single-VM dockerized deployment spec: 4 vCPU/16 GB, blue/green releases, DR runbook |
| [BUILD_15_Observability_Testing.md](BUILD_PLAN/BUILD_15_Observability_Testing.md) | Logging (correlation IDs), Prometheus, OpenTelemetry, Grafana, four-layer test pyramid |
