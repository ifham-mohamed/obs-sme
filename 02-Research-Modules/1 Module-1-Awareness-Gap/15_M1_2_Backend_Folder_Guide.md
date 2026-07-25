# 15_M1_2 — Backend Folder Build Guide (`enigmatrix-backend/`)

> Companion to [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) — build guide for the backend slice of the M1 tree.
> **Repo note (2026-07-24):** the real folder is **`enigmatrix-backend/`**, and M1 code is a **self-contained package at `app/m1/`** (`api/`, `models/`, `schemas/`, `services/`, `tasks/`) — moved there from the flat `app/{services,models,...}` layout the old guide assumed. It is now **largely shipped**: Phase-2 ingest/extract/preprocess, the extraction dataset/measurement admin surface, alerts, drift, retraining, propagation matching, and pipeline validation all exist. Deferred: the live ONNX classify path (waits on the trained model) + some Stage-E summarisation.
> **Implementation status snapshot:** ✅ ~70 M1 files under `app/m1/` shipped (api/models/schemas/services/tasks) + Scrapy Stage A + seeds + audit + migrations · 🟡 classify/summarise tasks wired but pending the trained model · 🔲 MarianMT summarisation.

## Purpose

`enigmatrix-backend/` is the FastAPI + Celery service that fronts M1 — the admin + SME API, the extraction/measurement admin tooling, the Celery task layer that drives Stages A–F (calling `enigmatrix-ml/m1/` for the algorithms), and the Postgres schema. M1 lives in its own `app/m1/` package so it never tangles with M2/M3 code; cross-module concerns (auth, surveys, audit) stay in the top-level `app/` dirs.

## Files in this folder

### `app/m1/api/` — M1 REST + WebSocket routers (all ✅ shipped)

| File | Owns |
|---|---|
| `api/regulations.py` | Admin + SME regulation CRUD / list / detail |
| `api/admin_pipeline.py` | Pipeline-state admin surface (A1) |
| `api/extractions.py` + `api/extraction_ws.py` | Extraction runs + live WebSocket feed |
| `api/gazette_extraction.py` | Per-gazette extraction trigger + status |
| `api/datasets.py` | Golden/dataset upload + versioning |
| `api/measurements.py` + `api/completeness.py` | Baseline measurement + completeness reports |
| `api/alerts.py` | Alert history / dispatch surface |

> Cross-module routers stay in `app/api/v1/` (`regulations.py`, `verify.py`, `qa.py`, `risk.py`, `admin_*`, `survey_*`). Router assembly: `app/api/v1/router_slim.py` + `app/main.py`.

### `app/m1/services/` — business logic (✅ shipped; ~30 modules)

| Area | Modules |
|---|---|
| Regulation + sources | `regulation_service`, `source_catalogue` / `sources_catalogue`, `secondary_sources`, `embeddings` |
| Extraction ops | `pipeline_service`, `extraction_run_status`, `extraction_run_archive`, `extraction_cancel`, `extraction_live_feed`, `pdf_resolver`, `metadata_confidence`, `profile_service` |
| Datasets + measurement | `dataset_service`, `dataset_upload`, `xlsx_parser`, `measurement_report`, `measurement_aggregates`, `completeness_check`, `overlap_service`, `snapshot_service`, `storage_projection` |
| Classify + drift + alerts | `classifier_service`, `drift`, `alert_service`, `alert_content`, `alert_providers` |
| Propagation (Phase 4) | `propagation_matching`, `propagation_service` |

> Shared audit writes live at `app/services/` (`audit_service`) + the passive `app/middleware/` audit layer.

### `app/m1/tasks/` — Celery task tree (✅ shipped; classify/summarise pending the model)

| Stage | Tasks |
|---|---|
| A — Ingest | `run_scraper`, `gazette_scraper`, `reconcile_raw`, `migrate_raw_layout` |
| B/C — Extract + preprocess | `run_extraction`, `extract_gazette`, `preprocess_gazette`, `quality_probe`, `prune_extraction_runs` |
| D — Classify | `classify_gazette` (🟡 wired; live path waits on the trained ONNX model) |
| F — Alerts | `alert_dispatch` |
| Secondary (Phase 4) | `portal_watcher`, `rss_watcher`, `source_health` |
| Measurement + governance | `run_measurement`, `validate_dataset_version`, `validate_pipeline`, `analytics`, `retention`, `retire_old_versions` |
| Retraining | `retraining` |

> Backend-side extraction helpers also live at `app/extraction/` (`pdf_classifier.py`, `text_extractors.py`, `pdf_metadata.py`); the heavier algorithms are in `enigmatrix-ml/m1/`.

### `app/m1/models/` + `app/m1/schemas/` (✅ shipped)

| Layer | Modules |
|---|---|
| `m1/models/` | `regulation_penalty`, `sub_document`, `gazette_item`, `dataset`, `propagation_event`, `propagation_review`, `alert`, `retraining_run`, `extraction_profile`, `extraction_run`, `measurement`, `quality_probe`, `pipeline_audit`, `source` |
| top-level `app/models/` | `regulation` (`M1Regulation`), `regulatory_domain`, `audit_log` |
| `m1/schemas/` | `regulation_penalty`, `sub_document`, `dataset`, `pipeline`, `measurement`, `extraction`, `alert` |

### Migrations, seeds, config

| Path | Owns | Status |
|---|---|---|
| `enigmatrix-backend/alembic/versions/*_m1_*.py` | Alembic migrations (e.g. `202607230001_m1_schema_validation_and_governance`, `202607210005_classification_source`) | ✅ Shipped |
| `app/scripts/seed_*.py` | `seed_lookups` (8 domains + 3 sectors), `seed_regulations`, `seed_m1_worked_examples`, `seed_m23_questions`, `seed_phase4`, `seed_demo_responses`, `seed_dev` | ✅ Shipped |
| `app/settings.py` | Pydantic settings / feature flags (env-driven) | ✅ Shipped |
| `app/middleware/` + `app/services/audit_service` | Passive HTTP audit logging | ✅ Shipped |

## How to start building

Most of this is **already built** — the sequence below is retained as the dependency order for the remaining work (live classify path + summarisation) and as an orientation for new contributors. The M1 package is at `app/m1/`; run the API with `make dev` / `uvicorn app.main:app` and Celery with the project's worker config.

1. **DB schema — ✅ shipped.** The `m1_*` migrations live under `enigmatrix-backend/alembic/versions/`; `alembic upgrade head` applies them. ORM under `app/m1/models/` + `app/models/regulation.py`. Seeds via `app/scripts/seed_lookups.py` (8 domains + 3 sectors) then `seed_regulations.py` / `seed_m1_worked_examples.py`.
2. **`config/feature_flags.py`.** Stub it with env-var-backed flags. Every Celery task entry-point reads from here. Build it before the tasks so they can gate themselves cleanly.
3. **`tasks/m1/__init__.py` + Celery routing.** Set up the task module + the queue names (`m1-extract`, `m1-classify`, `m1-summarise`, `m1-alert`) before any individual task; Celery Beat schedule lives in `backend/app/celery_config.py`.
4. **`tasks/m1/extract_gazette.py`.** First task — wraps Stage B from `ml/m1/extraction/`. Status transition `ingested → extracted`. Once this works, the rest of the chain follows the same pattern.
5. **`tasks/m1/classify_gazette.py` → `summarise_gazette.py` → `alert_dispatch.py`.** Chain order. Each fires on the previous's success.
6. **`tasks/m1/portal_watcher.py` + `rss_watcher.py`.** Phase 4 — independent of the main chain. Both write `m1_propagation_events`.
7. **`tasks/m1/analytics.py`.** Phase 4 — nightly batch; depends on all prior tasks having populated the rows it aggregates.
8. **API endpoint extensions.** As each Celery task lands, add the matching admin endpoint to `api/v1/m1_regulations.py` (e.g. `POST /regulations/{id}/classify` triggers `classify_gazette.delay(id)`).
9. **Scripts (`m1_backfill_classifications.py`, `m1_validate_pipeline.py`).** Last — they consume everything that came before.

## Dependencies

- **`enigmatrix-ml/m1/` modules** ([15_M1_1_ML_Folder_Guide.md](15_M1_1_ML_Folder_Guide.md)) — tasks import the extraction/preprocessing/model algorithms from the ML package. The boundary is strict: backend tasks own *orchestration*, not *algorithms*.
- **Postgres** — schema + connection pool; the `m1_*` tables are the persistent state machine.
- **Redis** — Celery broker + inference cache. Required for any Celery task to run.
- **`enigmatrix-backend/scraper/`** ([15_M1_3_Scraper_Folder_Guide.md](15_M1_3_Scraper_Folder_Guide.md)) — Stage A produces PDFs that Stage B consumes.
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
