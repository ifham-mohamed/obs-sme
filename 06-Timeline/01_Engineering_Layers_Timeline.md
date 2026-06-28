# BUILD PLAN — Master Index

**Project:** SME Regulatory Intelligence Platform (Enigmatrix)
**Faculty of Information Technology | University of Moratuwa | 2026**

> This package is the **engineering/build companion** to the research guides (`00_INDEX.md` → `12_Module1_End_to_End_Workflow.md`).
> The research guides answer *"what is the science and why."*
> These build files answer *"how do we actually code, ship, deploy, and track it."*
>
> **Looking for run-instructions, not the spec?** See [`docs/SETUP/00_INDEX.md`](../SETUP/00_INDEX.md) — the onboarding/setup track for the MVP that ships today.

---

## How to Use This Package

1. **Read in order on first pass.** Files 01 → 06 set up the common foundation. Files 07 → 10 are per-module. Files 11 → 15 are cross-cutting (ML infra, deployment, observability). Files 16 → 17 are operational helpers (tracker + prompts).
2. **Use as a working checklist.** Every BUILD_01–15 file ends with an "Acceptance Criteria" block — when those tick, the section is done. (BUILD_00 — this index — and BUILD_16/17 are templates and do not carry acceptance criteria.)
3. **Pair with Claude.** Every BUILD_01–15 file ends with a **Claude Prompts** block — paste these into a fresh Claude chat to generate the actual code for that step. The full library is also collected in `BUILD_17_Claude_Prompts_Library.md`. (BUILD_00/16/17 are exceptions: this index has no prompts; BUILD_16 carries 2 status-generation prompts; BUILD_17 *is* the prompts library.)
4. **Track via `BUILD_16`.** Copy the templates into your repo's `/docs/progress/` folder and update weekly.

---

## File Map

### Layer 1 — Foundation (do these first, in order)

| # | File | What It Does |
|---|------|--------------|
| 01 | `BUILD_01_Project_Initialization.md` | Prerequisites, tooling, accounts, repo bootstrap, environment files |
| 02 | `BUILD_02_Folder_Structure.md` | Complete monorepo layout — every directory, every config file, naming conventions |
| 03 | `BUILD_03_Backend_API.md` | FastAPI scaffolding, settings, routers, dependency injection, error handling |
| 04 | `BUILD_04_Database_and_Storage.md` | PostgreSQL + Alembic migrations + ChromaDB + object storage layer |
| 05 | `BUILD_05_Frontend_App.md` | Next.js 14 (App Router) scaffold, layouts, i18n (EN/SI/TA), API client, design system |
| 06 | `BUILD_06_Auth_and_Users.md` | JWT auth, refresh tokens, role-based access, SME profile binding |

### Layer 2 — Per-Module Builds

| # | File | What It Does |
|---|------|--------------|
| 07 | `BUILD_07_Module1_Awareness.md` | Gazette scraper → PDF extractor → XLM-R classifier → alert engine |
| 08 | `BUILD_08_Module2_Knowledge.md` | Document chunker → ChromaDB → RAG pipeline → cited Q&A endpoint |
| 09 | `BUILD_09_Module3_Risk.md` | Feature engineering → XGBoost + LSTM → SHAP → risk dashboard |
| 10 | `BUILD_10_Module4_Misinformation.md` | Social scrapers → Label Studio → XLM-R verifier → claim-check UI |

### Layer 3 — Cross-Cutting Infrastructure

| # | File | What It Does |
|---|------|--------------|
| 11 | `BUILD_11_ML_Training_Pipeline.md` | Shared training framework: data loaders, MLflow tracking, model registry, retraining triggers |
| 12 | `BUILD_12_Data_Ingestion_and_Scheduling.md` | Scrapy + Playwright + APScheduler/Celery, watcher patterns, retry logic |
| 13 | `BUILD_13_Admin_and_Annotation.md` | Admin dashboards, Label Studio integration, dataset views, manual review queue |
| 14 | `BUILD_14_Deployment_Cloud.md` | Docker, compose, VM provisioning, nginx, HTTPS, backups, scaling path |
| 15 | `BUILD_15_Observability_Testing.md` | Structured logs, Sentry, Prometheus, pytest/Playwright, GitHub Actions CI/CD |

### Layer 4 — Operations

| # | File | What It Does |
|---|------|--------------|
| 16 | `BUILD_16_Progress_Tracker_Template.md` | Per-task tracker, weekly status, milestone checklist, risk log |
| 17 | `BUILD_17_Claude_Prompts_Library.md` | All Claude prompts from this package, organized by phase, copy-paste ready |

---

## Session 1–19 Delivery Status

> **As of Session 19 (2026-05-12)** — updated when a phase ships; forward-looking spec sections are unchanged.

| Layer | Files | Status |
|-------|-------|--------|
| Foundation (BUILD_01–06) | Auth, FastAPI, Alembic, Next.js, RBAC, PostgreSQL | 🟢 **Complete** — all patterns implemented and running |
| Survey delivery layer | Session-based API (`survey_sessions` + `survey_limits`), all four module surveys (M1/M2/M3 full, M4 stub), admin question bank, branching flow canvas, regulation authoring wizard, M2 auto-scoring, M3 snapshot projection, admin settings | 🟢 **Complete** — shipped in Sessions 8–19 |
| Admin surface | Users CRUD, regulations CRUD, question bank, activity log, survey-responses view | 🟢 **Complete** |
| BUILD_07 — M1 ingest | Gazette scraper, PDF extractor, XLM-R classifier, alert engine | 🔲 **Pending** |
| BUILD_08 — M2 RAG | ChromaDB document chunker, `/api/v1/qa` RAG endpoint | 🔲 **Pending** |
| BUILD_09 — M3 risk ML | XGBoost/LightGBM risk model, MLflow, SHAP dashboard | 🔲 **Pending** |
| BUILD_10 — M4 misinformation | Social scrapers, M4 XLM-R verifier, claim-check UI | 🔲 **Pending** |
| BUILD_11 — ML training pipeline | Airflow/MLflow shared training infra | 🔲 **Pending** |
| BUILD_12 — Scheduling/ingest | APScheduler/Celery, portal watchers, retry logic | 🔲 **Pending** |
| BUILD_13 — Label Studio | Annotation bridge, manual review queue | 🔲 **Pending** |
| BUILD_14 — Cloud deploy | Docker, VM, nginx, HTTPS, backups | 🔲 **Pending** |
| BUILD_15 — Observability/CI | Sentry, Prometheus, pytest, GitHub Actions | 🔲 **Pending** |

The remaining work is ML/ingest-heavy. The survey data-collection platform is fully operational and can begin collecting real SME responses today.

---

## Build Order — A Recommended 14-Week Schedule

| Week | Phase | Files |
|------|-------|-------|
| 1 | Setup | 01, 02 |
| 2 | Backend + DB foundation | 03, 04 |
| 3 | Frontend foundation + Auth | 05, 06 |
| 4 | Data ingestion + scheduling | 12 |
| 5–7 | Module 1 build | 07 (with 11) |
| 7–9 | Module 2 build | 08 (with 11) |
| 9–11 | Module 3 build | 09 (with 11) |
| 11–13 | Module 4 build | 10 (with 11) |
| 13 | Admin + annotation polish | 13 |
| 13 | Cloud deployment + HTTPS | 14 |
| 14 | Observability + tests + CI/CD | 15 |
| Throughout | Tracking | 16 |
| Throughout | Prompts | 17 |

Modules 1–4 can run in parallel across team members **after** Layer 1 is finished.

---

## Conventions Used Throughout

- **`backend/`** = FastAPI Python service (port 8000)
- **`frontend/`** = Next.js TypeScript app (port 3000)
- **`ml/`** = Training scripts, notebooks, model artifacts (not bundled in API image)
- **`infra/`** = Dockerfiles, compose, nginx, deployment scripts
- **`docs/`** = This BUILD_PLAN/ + research guides + thesis chapters

Every code block tagged `# RUN` is a shell command; `# FILE: path` indicates the file path the snippet belongs in.

---

## Dependencies Between Files

```
        01 ─── 02
              │
       ┌──────┼──────┐
       │      │      │
       03     04     05
       │      │      │
       └──┬───┘      │
          │          │
          06 ────────┘
          │
        ┌─┴─────────────┐
        │               │
        11              12       (cross-cutting infra; consumed by 07–10)
        │               │
   ┌────┴───────┬───────┴───┬────────┐
   │            │           │        │
   07 ◄─── 12 ──┘     08────► 09     10 ◄── 12
   │            ▲     │                ▲    │
   │            │     │ (M1 corpus)    │    │
   │            │     └────────────────┘    │
   │            │              │             │
   │            └─────── 13 ───┴─────────────┘     (admin + annotation)
   │                     │
   └─► 14 ◄──────────────┴──── 15                  (deploy / observe)
       │                       │
       └──────► 16, 17 ◄───────┘                   (tracker + prompts)
```

Edges in plain English:
- 07 (M1 awareness) and 10 (M4 misinformation) both depend on 12 for portal/social ingest and on 11 for trainer infrastructure.
- 08 (M2 knowledge RAG) consumes the M1 regulation corpus produced by 07.
- 09 (M3 risk) consumes M1 categories *and* the M2 knowledge score (`GET /api/m2/sme/{id}/knowledge_score`).
- 10 (M4 misinformation verifier) consumes the M1 corpus as RAG ground truth.
- 13 (admin + annotation) attaches review queues to 07/08/09/10.
- 14/15 wrap everything for deployment + observability; 17 aggregates every Claude prompt from 01–16.

---

## Inter-Module Data Contracts

These three contracts are the seams between module owners. **Lock them by end of week 3** — drift here breaks every downstream module.

| # | From → To | Endpoint / artifact | Payload |
|---|-----------|---------------------|---------|
| **C1** | M1 → M2 | ChromaDB collection `regulations_chunks_v1` (built by `ml/m2/build_kb.py` from `regulations.summary_*` columns) | text chunks (≤512 tokens, 64 overlap) + metadata `{regulation_id, gazette_date, predicted_category, language}` |
| **C2** | {M1, M2} → M3 | `GET /api/v1/m2/sme/{sme_id}/knowledge_score` + `GET /api/v1/m1/sme/{sme_id}/exposure` | `{score: float[0..100], percentile: float, instrument_breakdown: {...}, last_updated: iso8601}` and `{categories_seen: list[str], days_since_last_alert: int}` |
| **C3** | M1 → M4 | ChromaDB collection `regulations_chunks_v1` (shared with C1) + table `m4_claim_verifications.matched_regulation_id` | retrieval over the same KB; verdict service writes `matched_regulation_id`, `nli_label`, `confidence` |

---

## Library Version Policy

- Use **version *ranges*** (`>=X,<Y`) in `pyproject.toml` and `package.json`, not exact pins, except for the security-sensitive allowlist below.
- Exact pins are reserved for: `cryptography`, `python-jose`, `passlib`, `pydantic`, `sqlalchemy`, `chromadb`, plus anything explicitly called out in BUILD_03/04.
- The canonical *resolved* lock file (`uv.lock`, `poetry.lock`, `pnpm-lock.yaml`) is the immutable record per deployment — generated and committed in `BUILD_14_Deployment_Cloud.md`.
- All BUILD examples that include a version use ranges (e.g. `chromadb>=0.5,<0.6`). If you see an exact pin in a BUILD file, an inline comment explains why.

---

## April 2026 Budget — Threshold Truth

The 2026 Sri Lankan budget changed several thresholds that the question banks (Module 2/3) and any policy-aware UI text must reflect. **Single source of truth: `docs/research/module_2_and_3_data_architecture.md`.**

| Threshold | Pre-April 2026 | **From April 2026 (current)** |
|-----------|---------------|-------------------------------|
| VAT registration threshold | LKR 60M | **LKR 36M** |
| SSCL threshold | LKR 60M | **LKR 36M** |
| Standard VAT rate | 15% (post-Oct 2022) | **18%** |

`docs/research/06_Data_Collection_and_Management.md` was scrubbed (see commit log for that file) to align with these figures. If you find a stale threshold anywhere in `docs/`, file a tracker entry and fix it — drift is an examiner-flag-magnet.

---

## Open Questions (Project-Level Gaps Not Resolvable In Docs)

These are flagged here so they cannot be silently forgotten. None of them are blockers for engineering Layer 1, but all four must be resolved before thesis submission.

| # | Gap | Impact | Owner |
|---|-----|--------|-------|
| **OQ1** | Library *versions* not yet pinned across the stack | Reproducibility risk for thesis methodology | DevOps lead, BUILD_14 implementer |
| **OQ2** | Per-module training hyperparameters (LR, batch, epochs) not locked | Examiner will ask "what values did you actually use" | Each module owner, before training run |
| **OQ3** | Ethics committee approval reference missing | Required by Methodology chapter §4.X | Project lead |
| **OQ4** | NEDA / Chamber of Commerce survey-distribution partnership unconfirmed | Survey n-targets at risk for Modules 2/3/4 | Project lead, by week 5 |

---

## What Each Module Owner Reads

| Owner | Foundation | Module-Specific | Cross-Cutting |
|-------|-----------|-----------------|---------------|
| Module 1 (Awareness) | 01–06 | 07, research 09–12 | 11, 12 |
| Module 2 (Knowledge) | 01–06 | 08 | 11 |
| Module 3 (Risk) | 01–06 | 09 | 11 |
| Module 4 (Misinformation) | 01–06 | 10 | 11, 12, 13 |
| DevOps / Lead | 01–06 | — | 12, 13, 14, 15, 16 |

---

## Status Legend

Use these emojis in your tracker (file 16):

- 🔲 Not started
- 🟡 In progress
- 🟢 Done & tested
- 🔴 Blocked
- ⚪ Deferred

---

*— BUILD PLAN | Enigmatrix | 2026 —*
