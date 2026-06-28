# 15_M1_2 — `backend/` Folder Build Guide

> Companion to [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) — build guide for the `backend/app/` slice of doc 13's M1 tree.
> **Implementation status snapshot:** ✅ ~6 shipped (admin CRUD + audit + 1 model + middleware) · 🟡 ~3 partial · 🔲 ~16 deferred (Celery tasks + remaining models + migrations + scripts).

## Purpose

`backend/app/` is the FastAPI service that fronts M1 — the admin API, the SME survey endpoints, the Celery task layer that drives Stages A–F via `ml/m1/` calls, and the database schema. The admin-CRUD slice + audit log are already in production; the Celery task tree is the biggest deferred surface. Every `ml/m1/` module is called *from* a Celery task here.

## Files in this folder

### `backend/app/api/v1/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `api/v1/m1_regulations.py` | Admin + SME REST endpoints for M1 | ✅ Shipped (admin CRUD) | [11_M1_API_Reference.md](11_M1_API_Reference.md) + [11_M1_1_API_Authentication_Authorization.md](11_M1_1_API_Authentication_Authorization.md) | Already exists; extend with `/classify`, `/verify` (verify exists), `/propagation-events`, `/analytics/*` endpoints in BUILD_07/12 |

### `backend/app/services/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `services/m1_regulation_service.py` | Admin-slice business logic | ✅ Shipped | [11_M1_API_Reference.md](11_M1_API_Reference.md) | Already exists; extend with classify/verify bridge methods that enqueue Celery tasks |
| `services/shared/audit_service.py` | Singular `audit_log` writes (Session 14) | ✅ Shipped | — | Already exists; reused by every M1 mutation |

### `backend/app/tasks/m1/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `tasks/m1/gazette_scraper.py` | Stage A — wraps the Scrapy spider in a Celery task | 🔲 | [03_M1_Data_Collection.md §6.1](03_M1_Data_Collection.md) | `CrawlerRunner` + Celery retry-on-infra-failure-only |
| `tasks/m1/extract_gazette.py` | Stage B — calls `ml/m1/extraction/*` | 🔲 | [03_M1_1_PDF_Extraction_Chain.md](03_M1_1_PDF_Extraction_Chain.md) | Reads PDF path; advances `status='extracted'` on success |
| `tasks/m1/classify_gazette.py` | Stage D — calls `ml/m1/model/inference.py` | 🔲 | [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md) | Reads chunk 0; writes category + sectors + confidence; sets `needs_review` if conf < 0.70 |
| `tasks/m1/summarise_gazette.py` | Stage E — calls `ml/m1/summarization/marianmt.py` | 🔲 | [04_M1_3_Text_Chunking_Strategy.md](04_M1_3_Text_Chunking_Strategy.md) | Per-chunk summarise; concat per-language summaries |
| `tasks/m1/alert_dispatch.py` | Stage F — SendGrid + Twilio + chunked batching | 🔲 | [08_M1_Full_System_Architecture.md §8.1](08_M1_Full_System_Architecture.md) | Idempotency on `(regulation_id, sme_id, channel)`; respect SendGrid rate limit |
| `tasks/m1/portal_watcher.py` | Secondary sources (IRD/EPF/eROC) | 🔲 | [03_M1_3_Secondary_Source_Integration.md](03_M1_3_Secondary_Source_Integration.md) | `httpx` per source; INSERT ... ON CONFLICT DO NOTHING on `m1_propagation_events` |
| `tasks/m1/rss_watcher.py` | News RSS (5 outlets) | 🔲 | [03_M1_3_Secondary_Source_Integration.md](03_M1_3_Secondary_Source_Integration.md) | `feedparser` + embedding-similarity matching for Tier 2 |
| `tasks/m1/analytics.py` | Nightly view refresh + drift trigger + retraining trigger | 🔲 | [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md) + [12_M1_2_Retraining_Deployment_Rollback.md](12_M1_2_Retraining_Deployment_Rollback.md) | Celery Beat `0 2 * * *`; advisory-lock the view refresh |

### `backend/app/models/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `models/m1_regulation.py` | `m1_regulations` ORM model | 🟡 | [02_M1_Data_Requirements.md §2.1](02_M1_Data_Requirements.md) | Exists for the admin slice; the remaining 8 `m1_*` tables (sectors, events, sources, changes, examples, penalties, court cases, survey responses) land with BUILD_07 |

### `backend/app/schemas/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `schemas/m1.py` | Pydantic API request/response models | ✅ Shipped (admin slice) | [02_M1_2_Database_Schema_Validation.md](02_M1_2_Database_Schema_Validation.md) | Extend with classify/verify/propagation/survey schemas in BUILD_07 |

### `backend/app/config/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `config/feature_flags.py` | Per-stage on/off + model version | 🔲 | [13_M1_Folder_Structure §upgradability rules](13_M1_Folder_Structure_and_Implementation_Flow.md) | Env-var driven; pinned to `M1_INGESTION_ENABLED`, `M1_INFERENCE_ENABLED`, `M1_MODEL_VERSION`, `M1_MODEL_CANARY_PCT` |

### `backend/app/db/migrations/versions/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `*_m1_*.py` | Alembic migrations for the 9 `m1_*` tables | 🟡 | [02_M1_Data_Requirements.md §2](02_M1_Data_Requirements.md) + [02_M1_2_Database_Schema_Validation.md](02_M1_2_Database_Schema_Validation.md) | Migration per table + per index; `NOT VALID` constraint pattern for pre-populated tables |

### `backend/app/scripts/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `scripts/seed_regulations.py` | 5 demo regulations | ✅ Shipped | [02_M1_4_Worked_Examples_All_Tables.md](02_M1_4_Worked_Examples_All_Tables.md) | Already exists; extend with more worked-example regulations in BUILD_07 |
| `scripts/m1_backfill_classifications.py` | Re-classify the last 30 days | 🔲 | [12_M1_2_Retraining_Deployment_Rollback.md §Day 5](12_M1_2_Retraining_Deployment_Rollback.md) | Rate-limited (10/min); writes both old + new prediction for ablation |
| `scripts/m1_validate_pipeline.py` | Nightly data-quality checks | 🔲 | [02_M1_2_Database_Schema_Validation.md §Layer 3](02_M1_2_Database_Schema_Validation.md) | 13 checks; appends rows to `m1_pipeline_audits` |

### `backend/app/middleware/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `middleware/audit_middleware.py` | Passive HTTP-level audit logging (Session 14) | ✅ Shipped | — | Already exists; no M1-specific change needed |

## How to start building

The backend has the most "spans-the-roadmap-phases" surface area. Sequence:

1. **DB schema first (Phase 2 prerequisite).** Add the 8 deferred `m1_*` table migrations under `db/migrations/versions/`. Run `alembic upgrade head` after each. Update `models/m1_*` ORM files in lockstep. The schema is the contract for everything that follows.
2. **`config/feature_flags.py`.** Stub it with env-var-backed flags. Every Celery task entry-point reads from here. Build it before the tasks so they can gate themselves cleanly.
3. **`tasks/m1/__init__.py` + Celery routing.** Set up the task module + the queue names (`m1-extract`, `m1-classify`, `m1-summarise`, `m1-alert`) before any individual task; Celery Beat schedule lives in `backend/app/celery_config.py`.
4. **`tasks/m1/extract_gazette.py`.** First task — wraps Stage B from `ml/m1/extraction/`. Status transition `ingested → extracted`. Once this works, the rest of the chain follows the same pattern.
5. **`tasks/m1/classify_gazette.py` → `summarise_gazette.py` → `alert_dispatch.py`.** Chain order. Each fires on the previous's success.
6. **`tasks/m1/portal_watcher.py` + `rss_watcher.py`.** Phase 4 — independent of the main chain. Both write `m1_propagation_events`.
7. **`tasks/m1/analytics.py`.** Phase 4 — nightly batch; depends on all prior tasks having populated the rows it aggregates.
8. **API endpoint extensions.** As each Celery task lands, add the matching admin endpoint to `api/v1/m1_regulations.py` (e.g. `POST /regulations/{id}/classify` triggers `classify_gazette.delay(id)`).
9. **Scripts (`m1_backfill_classifications.py`, `m1_validate_pipeline.py`).** Last — they consume everything that came before.

## Dependencies

- **`ml/m1/` modules** ([15_M1_1_ML_Folder_Guide.md](15_M1_1_ML_Folder_Guide.md)) — every task imports `from ml.m1.extraction import ...`. The boundary is strict: backend tasks own *orchestration*, not *algorithms*.
- **Postgres** — schema + connection pool. The 9 `m1_*` tables are the persistent state machine.
- **Redis** — Celery broker + inference cache + session blacklist. Required for any Celery task to run.
- **`scraper/`** ([15_M1_3_Scraper_Folder_Guide.md](15_M1_3_Scraper_Folder_Guide.md)) — Stage A produces PDFs that Stage B (this folder) consumes.
- **`storage/`** ([15_M1_5_Storage_Folder_Guide.md](15_M1_5_Storage_Folder_Guide.md)) — raw PDFs, OCR cache, ONNX models. Tasks read + write here.

## Tests & acceptance criteria

- **Schema migrations.** `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` succeeds on a fresh DB. Every migration is reversible.
- **Celery task tests.** Each task in `tests/m1/test_*.py` runs against a fixture row + asserts the post-state. Tasks must be idempotent (re-running advances state correctly without duplicates).
- **API integration.** `tests/m1/integration/` covers every endpoint with each role's expected status code (per the permission matrix in [11_M1_1](11_M1_1_API_Authentication_Authorization.md)).
- **Audit-log invariants.** Every state-changing API call writes one `audit_log` row; tests assert the row count delta.
- **Pre-deploy gate.** `make test` + `alembic upgrade head` both pass before any task is enabled in production (`M1_*_ENABLED=true`).

## Cross-references

- Folder map spec: [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md)
- Roadmap: [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md) (Phases 2 + 4 are heaviest here)
- API spec: [11_M1_API_Reference.md](11_M1_API_Reference.md) + [11_M1_1](11_M1_1_API_Authentication_Authorization.md) + [11_M1_2](11_M1_2_API_Integration_Examples.md)
- Schema spec: [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) + [02_M1_2](02_M1_2_Database_Schema_Validation.md)
- Monitoring: [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md) + [12_M1_1](12_M1_1_Performance_Monitoring_Alerting.md)
- Sibling folders: [15_M1_1_ML_Folder_Guide.md](15_M1_1_ML_Folder_Guide.md), [15_M1_3_Scraper_Folder_Guide.md](15_M1_3_Scraper_Folder_Guide.md), [15_M1_5_Storage_Folder_Guide.md](15_M1_5_Storage_Folder_Guide.md)
