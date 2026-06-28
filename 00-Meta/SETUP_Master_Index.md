# Setup & Developer Documentation — Master Index

**Project:** Enigmatrix — SME Regulatory Intelligence Platform
**Faculty of Information Technology · University of Moratuwa · 2026**

This is the **how-to-run-and-extend** track for the repo. It pulls together the prerequisites, quickstart, architecture, day-to-day developer commands, and contribution flow into one navigable set.

It deliberately sits beside — not inside — the two existing tracks:

| Track | What it answers |
|-------|----------------|
| [`docs/SETUP/`](.) | "How do I install, run, and extend the project?" *(you are here)* |
| [`docs/BUILD_PLAN/`](../BUILD_PLAN/BUILD_00_INDEX.md) | "What does each subsystem need to look like?" — engineering specs. |
| [`docs/research/`](../research/00_INDEX.md) | "What is the science and why?" — research methodology. |
| [`docs/tracker/`](../../tracker/README.md) | "What ships today vs what's next?" — live feature tracker. |

Everything in this folder describes the platform as it stands after **19 development sessions**: auth + all four SME module surveys (M1 Awareness, M2 Knowledge, M3 Vulnerability, M4 stub) + session-based survey architecture (`survey_sessions`, admin-configurable `survey_limits`) + admin question bank + visual branching flow canvas + regulation authoring wizard + activity log, all trilingual EN/SI/TA, light + dark themes. ML/ingest pipelines (gazette classifier, RAG, risk model, misinformation) are still deferred — see [`10_Next_Steps.md`](10_Next_Steps.md).

---

## Reading order — first-time contributor

If you have never seen this repo, walk these files top to bottom. Each one ends with a `**Prev** · **Next**` footer.

| # | File | Read for |
|---|------|---------|
| 01 | [`01_Prerequisites.md`](../../infra/SETUP/01_Prerequisites.md) | What to install on macOS / Linux / Windows-via-WSL2 before you do anything else. |
| 02 | [`02_Quickstart.md`](../../infra/SETUP/02_Quickstart.md) | The five-command path from clone to working `localhost:3000`. |
| 03 | [`03_Architecture.md`](03_Architecture.md) | How the pieces fit together (runtime topology, request lifecycle, ERD, file map). |
| 04 | [`04_Backend_Development.md`](../../backend/SETUP/04_Backend_Development.md) | How to add a new endpoint end-to-end. Backend conventions. |
| 05 | [`05_Frontend_Development.md`](../../frontend/SETUP/05_Frontend_Development.md) | How to add a new page. Theme tokens, i18n, shadcn primitives, RBAC layouts. |
| 06 | [`06_Database_and_Migrations.md`](../../backend/SETUP/06_Database_and_Migrations.md) | The four MVP tables, Alembic workflow, seed/inspect/reset commands. |
| 07 | [`07_Auth_and_Roles.md`](../../backend/SETUP/07_Auth_and_Roles.md) | Three roles, JWT lifecycle, cookies, audit log, role elevation. |
| 08 | [`08_Testing.md`](08_Testing.md) | Three test surfaces (unit, integration, E2E) and when to write each. |
| 09 | [`09_Troubleshooting.md`](../../infra/SETUP/09_Troubleshooting.md) | Symptom → cause → exact fix for the issues you'll hit first. |
| 10 | [`10_Next_Steps.md`](10_Next_Steps.md) | Roadmap. What to build next. Contribution flow against [`docs/tracker/`](../../tracker/README.md). |
| 11 | [`11_Survey_System.md`](../../backend/SETUP/11_Survey_System.md) | Cross-module linkage walkthrough — how M2 Knowledge, M3 Vulnerability, the question bank, scoring, conditional follow-ups, the M:N regulation junction, the visual flow canvas, and the session-based Phase 3 architecture fit together. |
| 12 | [`12_UI_Screens_and_Loading.md`](../../frontend/SETUP/12_UI_Screens_and_Loading.md) | Screen-by-screen map of the frontend (SME + admin), the reusable-component catalog, the design-system recap, and the loading-state strategy (`<Skeleton>` vs `<AnimatedLoadingSkeleton>` vs streaming `loading.tsx`). |
| 13 | [`13_Unified_Survey_Configuration.md`](../../frontend/SETUP/13_Unified_Survey_Configuration.md) | Session-based survey API reference — the 6 endpoints, five survey modes, `survey_sessions` + `survey_limits` schemas, `SurveyLauncher` / `SurveyWizard` frontend loop. |

---

## Just-want-to-run-it shortcut

Five commands, after [`01_Prerequisites.md`](../../infra/SETUP/01_Prerequisites.md) is satisfied:

```bash
git clone <repo-url> enigmatrix && cd enigmatrix
cp .env.example .env       # then fill JWT_SECRET + APP_SECRET_KEY
make up                    # docker compose: Postgres + ChromaDB
make migrate && make seed  # schema + admin/annotator/sample-SME accounts
make dev-backend           # terminal A — http://localhost:8000/docs
make dev-frontend          # terminal B — http://localhost:3000
```

Default seed credentials:

| Role | Email | Password |
|------|-------|----------|
| `admin` | `admin@enigmatrix.lk` | `admin12345` |
| `annotator` | `annotator@enigmatrix.lk` | `annotator12345` |
| `sme` | `sme@enigmatrix.lk` | `sme12345678` |

Smoke check: register a new SME at `/register`, complete the awareness survey at `/surveys/awareness`, log in as `admin@enigmatrix.lk`, view the response at `/admin/surveys/awareness/responses`. If anything fails, jump to [`09_Troubleshooting.md`](../../infra/SETUP/09_Troubleshooting.md).

---

## Status legend (used in [`docs/tracker/FEATURES.md`](../../tracker/FEATURES.md))

| Char | Meaning |
|------|---------|
| 🔲 | Not started |
| 🟡 | In progress |
| 🟢 | Done & accepted |
| 🔴 | Blocked |
| ⚪ | Out of scope / dropped |

---

## Stack at a glance

| Layer | Choice | Pinned in |
|-------|--------|-----------|
| Backend language | Python 3.11 | [`backend/pyproject.toml`](../../backend/pyproject.toml) |
| Web framework | FastAPI ≥ 0.115 | [`backend/pyproject.toml`](../../backend/pyproject.toml) |
| ORM | SQLAlchemy 2.0 async + asyncpg | same |
| Migrations | Alembic ≥ 1.13 | [`backend/alembic.ini`](../../backend/alembic.ini) |
| Auth | bcrypt (`passlib[bcrypt]`) + HS256 JWT (`python-jose`) | [`backend/app/core/security.py`](../../backend/app/core/security.py) |
| Rate limiting (inbound) | `slowapi` | [`backend/app/core/rate_limit.py`](../../backend/app/core/rate_limit.py) |
| Logging | `structlog` + contextvars | [`backend/app/logging_config.py`](../../backend/app/logging_config.py) |
| Database | PostgreSQL 16 (alpine) | [`docker-compose.dev.yml`](../../docker-compose.dev.yml) |
| Vector DB | ChromaDB 0.5.5 (wired, unused in MVP) | same |
| Frontend framework | Next.js 14 (App Router) + React 18 + TypeScript 5.6 | [`frontend/package.json`](../../frontend/package.json) |
| Styling | Tailwind 3.4 + shadcn-style HSL token contract | [`frontend/tailwind.config.ts`](../../frontend/tailwind.config.ts) |
| Theming | `next-themes` (light / dark / system) | [`frontend/components/providers.tsx`](../../frontend/components/providers.tsx) |
| i18n | `next-intl` (en / si / ta) | [`frontend/i18n.ts`](../../frontend/i18n.ts) |
| Forms | `react-hook-form` + `zod` + `@hookform/resolvers` | [`frontend/lib/validators/auth.ts`](../../frontend/lib/validators/auth.ts) |
| Data fetching | TanStack Query 5 | [`frontend/components/providers.tsx`](../../frontend/components/providers.tsx) |
| Tests | pytest + `testcontainers[postgres]` (backend), Playwright + Vitest (frontend) | [`backend/pyproject.toml`](../../backend/pyproject.toml), [`frontend/package.json`](../../frontend/package.json) |

Full justification per choice → [`docs/research/04_Technology_Stack_Justification.md`](../research/04_Technology_Stack_Justification.md).

---

## What is and is not in this MVP slice

**In (as of Session 19):** auth (register / login / refresh / logout), three roles (sme/admin/annotator), SME profile capture at signup, all four SME module surveys (M1 Awareness / M2 Knowledge / M3 Vulnerability / M4 stub) DB-driven with session-based API, admin-configurable survey limits (`survey_limits`), admin question bank with branching rules editor + flow canvas + authoring wizard, regulation CRUD with M:N question linkage, unified survey hub (By Regulation / By Module tabs), activity log, M2 auto-scoring engine, M3 snapshot projection, audit log on every mutation, 11 Alembic migrations, light + dark theme, trilingual EN/SI/TA.

**Not in (deferred):**

| Subsystem | Lives in | First action |
|-----------|----------|--------------|
| Module 1 — gazette ingestion + NLP classifier | [`BUILD_07_Module1_Awareness.md`](../../backend/BUILD_PLAN/BUILD_07_Module1_Awareness.md) | implement `app/ingestion/gazette/lister.py` |
| Module 2 — RAG over regulation corpus | [`BUILD_08_Module2_Knowledge.md`](../../backend/BUILD_PLAN/BUILD_08_Module2_Knowledge.md) | wire ChromaDB + the `/api/v1/qa` endpoint |
| Module 3 — ML risk model | [`BUILD_09_Module3_Risk.md`](../../backend/BUILD_PLAN/BUILD_09_Module3_Risk.md) | feature-engineering script in `ml/m3/`; needs training data |
| Module 4 — misinformation classifier + verifier | [`BUILD_10_Module4_Misinformation.md`](../../backend/BUILD_PLAN/BUILD_10_Module4_Misinformation.md) | platform connectors under `app/modules/m4/sources/` |
| Shared ML training infra | [`BUILD_11_ML_Training_Pipeline.md`](../../ml/BUILD_PLAN/BUILD_11_ML_Training_Pipeline.md) | `ml/common/trainer.py` base class |
| Scrapers + scheduling | [`BUILD_12_Data_Ingestion_and_Scheduling.md`](../../backend/BUILD_PLAN/BUILD_12_Data_Ingestion_and_Scheduling.md) | source registry |
| Label Studio annotation bridge | [`BUILD_13_Admin_and_Annotation.md`](../../frontend/BUILD_PLAN/BUILD_13_Admin_and_Annotation.md) | Label Studio connector |
| Production deploy | [`BUILD_14_Deployment_Cloud.md`](../../infra/BUILD_PLAN/BUILD_14_Deployment_Cloud.md) | nginx + TLS + backups |
| Observability + CI | [`BUILD_15_Observability_Testing.md`](../../infra/BUILD_PLAN/BUILD_15_Observability_Testing.md) | Prometheus instrumentation |

The full roadmap is in [`10_Next_Steps.md`](10_Next_Steps.md).

---

**Prev:** [`README.md`](../../README.md) &nbsp;·&nbsp; **Next:** [`01_Prerequisites.md`](../../infra/SETUP/01_Prerequisites.md)
