# Enigmatrix — API & Pages Reference

**Generated:** 2026-07-15 from `enigmatrix-backend/app/api/v1/` (26 routers, ~130 routes) and `enigmatrix-frontend/app/` (90+ pages). Base path: `/api/v1`. Auth = Bearer JWT (cookie). Roles: sme / admin / annotator.

## 1. Backend API by Router

### auth.py — `/auth`
`POST /register` · `POST /login` (rate-limited) · `POST /refresh`. Writes audit rows `auth.register`, `auth.login.success/failure`, `auth.refresh`. Service: `auth_service.py`.

### users.py — `/users`
`GET /me` · admin: `GET /`, `POST /`, `PATCH /{user_id}`, `POST /{user_id}/activate|deactivate|reset-password`, `DELETE /{user_id}`.

### m1_regulations.py — `/m1/regulations` (10 routes)
Public list + `GET /{id}/public`; admin CRUD (`POST`, `PATCH`, `DELETE` soft via `is_active`, `POST /{id}/restore`), `POST /{id}/verify`, `POST /bulk-verify`. Service: `m1_regulation_service.py` (archive/restore pattern); every mutation → `audit_service.record()`.

### m1_gazette_extraction.py — `/m1/gazette-extraction` (17 routes — the pipeline operations surface)
`POST /trigger` (scrape+extract, date-scoped; returns `overlaps` warn block) · `GET /status/{task_id}` · `GET /progress` · `GET /summary` · `GET /regulations/{id}/raw-pdf` · `GET /sources`, `GET /sources/{source_id}` · `GET /unknown` · `GET /pdf-records` · `GET /runs` (run history) · cancel/rollback/reconcile POSTs. Tasks: `run_scraper`, `extract_gazette`, `preprocess_gazette`; services: `m1_pipeline_service`, `m1_pdf_resolver`, `m1_sources_catalogue`, `m1_extraction_cancel`, `m1_extraction_run_status`.

### m1_extraction_ws.py
`WS /ws/extraction/{task_id}` — live sub-step progress (Celery emits via `m1_extraction_live_feed`).

### m1_completeness.py — `/m1/completeness`
`POST /verify` · `POST /verify/{task_id}` · `POST /refetch-missing` — verifies scraped coverage vs expected gazette index; EN→SI→TA fallback re-fetch.

### admin_m1_pipeline.py — `/admin/m1/pipeline`
`GET /overview` (funnel counts) · `GET /recent` · `GET /trace/{regulation_id}` (full per-regulation pipeline trace).

### m1_datasets.py — `/m1/datasets` (14 routes)
Dataset CRUD + restore; `GET /{id}/versions`, `GET .../versions/{vid}`; `POST /{id}/versions/upload` (Excel ground truth → `m1_xlsx_parser`); `POST .../seal` (freeze + SHA-256 + dispatch `validate_dataset_version`); `DELETE .../retire`. Services: `m1_dataset_service`, `m1_dataset_upload`, `m1_snapshot_service`.

### m1_extractions.py — `/m1/extractions` (8 routes)
Extraction-profile registry list/detail; `POST /run` (dispatch profile run → returns `overlap` block + auto v1→v2 routing); run status. Services: `m1_profile_service`, `m1_overlap_service`; ML: `m1/extraction/profiles/*`.

### m1_measurements.py — `/m1/measurements` (11 routes)
`POST /` run measurement (optional `date_from`/`date_to`/`source_id`) · `GET /candidate-versions` · list/detail/progress · `GET /{run_id}/worst` · `GET /{run_id}/calibration` · `GET /{run_id}/scores` · **`GET /{run_id}/report.md`** (accuracy report download). Engine: `enigmatrix-ml/m1/evaluation/**` via `run_measurement` task; aggregates service; report builder `m1_measurement_report.py`.

### m1_alerts.py — `/m1/alerts`
`GET /public` (no auth) · `GET /` (SME: sector-matched + public, unread count) · `POST /{alert_id}/read`. Service chain: `m1_alert_service` → `m1_alert_content` → `m1_alert_providers` (SendGrid/Twilio, graceful skip); dispatch task `alert_dispatch.py`.

### Surveys & admin
- `survey_sessions.py` — `/survey-sessions`: start / my-history / detail / next-question / answer / complete.
- `admin_surveys.py` — survey CRUD + question attach/detach + ordering.
- `admin_survey_questions.py` (15) — question bank CRUD, verify, bulk-verify, restore, next-code, translations.
- `admin_survey_limits.py` — get/patch limits. `admin_translations.py` — translation management.
- `admin_audit.py` — `/admin/audit`: list, event-types, summary, detail.
- `dashboard.py` — `GET /dashboard/pending-regulations`.

### Modules 2–4
- `m2.py` — questions per sector, knowledge score, verify. `m3.py` — compliance-history, behavioural, risk-signals.
- `regulations.py` — public regulations list/detail. `qa.py /ask`, `risk.py /me`, `verify.py /claim` — M4/M3 stubs (501).

## 2. Celery Tasks (`app/tasks/m1/`)

| Task | Trigger | Purpose |
|---|---|---|
| run_scraper / gazette_scraper | Beat 6 h + manual | scrape gazettes into `m1_regulations` |
| extract_gazette | chained | PDF → text (classifier + engines + OCR) |
| preprocess_gazette | chained | clean/LID/Wijesekara/metadata/chunk → chains classify |
| classify_gazette | chained | ONNX XLM-R inference → category + confidence |
| run_extraction | API | profile-based extraction run → dataset version |
| run_measurement | API | accuracy measurement run |
| validate_dataset_version | post-seal | data-quality expectation suites |
| portal_watcher / rss_watcher | Beat 2 h | secondary-source propagation events |
| alert_dispatch | manual/wire-up pending | sector-matched alert send |
| analytics.refresh_lag_analytics | Beat 21:00 UTC | refresh lag views + drift check |
| retire_old_versions | Beat 20:30 UTC | dataset-version retention |
| retraining.run_retraining | Beat quarterly + drift | retrain → canary decide |
| reconcile_raw / migrate_raw_layout | manual | storage maintenance |

## 3. Frontend Pages (grouped)

**Auth:** `/login`, `/register` (split-panel).
**SME app:** `/dashboard` (streaming) · `/regulations` · `/surveys` (+ `/history`, `/module/[id]`, `/regulation/[id]`, `/unified`) · `/profile` · `/alerts` (public + sector feed; wiring pending) · `/qa`, `/risk`, `/verify` (coming-soon stubs).
**Admin — M1 pipeline:** `/admin/m1/pipeline` (funnel) · `/pipeline/extraction` (date-range trigger) · `/pipeline/recent` · `/pipeline/sources` + `/sources/[id]/extraction` · `/pipeline/steps[/stepId]` · `/pipeline/trace/[regulationId]` · `/admin/m1/pdf-records`.
**Admin — datasets & measurement:** `/admin/datasets` (hub) · `/admin/datasets/m1` (+ `/new`, `/[datasetId]`, `/upload`, `/versions/[versionId]`) · `/admin/datasets/m1/extractions/run` + `/runs/[taskId]` · `/admin/datasets/m1/measurements` (+ `/run`, `/[runId]`, `/[runId]/regulations/[regulationKey]`).
**Admin — platform:** `/admin/regulations` (+ new/edit/flow/authoring) · `/admin/questions` (+ new/edit) · `/admin/surveys` (+ [id], questions, awareness/responses, new) · `/admin/survey/regulations` · `/admin/m2/questions`, `/admin/m2/scores`, `/admin/m3/risk-signals` · `/admin/users` · `/admin/activity-log` · `/admin/translations` · `/admin/settings` · `/admin/models`, `/admin/training`, `/admin/annotation` (scaffolds).
**Knowledge portal:** `/knowledge` + build-status, build-tracker, changes, docs (+ m1 sections, platform-map), features[/featureId], findings[/module/slug], graph, ideas, master-context, modules[/module]/chapters[/slug], overview-docs, plans[/planId], prompts, sessions[/sessionId], team, tech-stack[/layer/slug], timeline.

**API clients** (`lib/api/*.ts`) mirror routers 1:1: `m1-gazette-extraction`, `m1-datasets`, `m1-extractions`, `m1-measurements`, `m1-alerts`, `m1-completeness`, `m1-pipeline`, plus auth/users/surveys/m2/m3/admin-*.

## 4. Contract-Drift Watchlist (from graph audit)
Zod ↔ SQL pairs with no enforced contract — check the counterpart when editing either side: `registerSchema` ↔ `users`/`sme_profiles` · `regulationCreateSchema` ↔ `m1_regulations` · `surveyQuestionCreateSchema` ↔ `survey_questions` · `adminCreateUserSchema` ↔ `users`.
