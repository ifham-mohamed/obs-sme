# Plan: M1 extraction run history — server-side persistence and pool fix

## Context

Prior to this session, extraction run history was stored exclusively in browser `localStorage` (per-browser, max 20 entries, lost on cache clear, not visible across admin sessions). Session 54 (2026-05-22) replaced this with a durable server-side audit log: the `m1_extraction_runs` PostgreSQL table. localStorage is retained as a write-through cache for instant paint before the API responds.

The session also surfaced and fixed a SQLAlchemy `QueuePool` exhaustion error introduced by adding `db: AsyncSession` dependencies to previously-stateless endpoints, compounded by the audit middleware opening its own `SessionLocal()` on every request.

Tasks covered: #20 (backend model + migration), #21 (trigger persistence + status sync + GET /runs), #22 (frontend API + localStorage write-through), plus the QueuePool hotfix.

## Goal

1. Persist every extraction trigger as a row in `m1_extraction_runs` — durable, shared, unlimited, visible to every admin session.
2. Update `celery_status` in-place as the Celery task transitions through its lifecycle (PENDING → STARTED → SUCCESS / FAILURE / REVOKED).
3. Expose a paginated `GET /api/v1/admin/m1/extraction/runs` endpoint filterable by `source_id`.
4. Replace the frontend localStorage-only history with API-backed history (localStorage kept as write-through cache / fallback).
5. Fix the SQLAlchemy QueuePool exhaustion that resulted from the above changes.

## Steps / tasks

1. ✅ **Backend model** — Created `app/models/m1_extraction_run.py` (NEW): SQLAlchemy 2.0 ORM model for `m1_extraction_runs`. Columns: `run_id` (UUID PK), `task_id` (TEXT UNIQUE), `source_id`, `date_from`, `date_to`, `queued_at`, `queued_by_id` (FK → `users.id` ON DELETE SET NULL), `queued_by_email` (denormalised snapshot), `celery_status` (default PENDING), `result` (JSONB), `traceback`, `completed_at`, `rows_ingested/extracted/preprocessed/failed` (nullable INT), `created_at/updated_at` (TimestampMixin). Index: composite `(source_id, queued_at)` for most-common query pattern. Updated `app/models/__init__.py` to import and export `M1ExtractionRun`.
2. ✅ **Alembic migration** — Created `alembic/versions/202605210002_m1_extraction_runs.py` (NEW). `revision = "202605210002"`, `down_revision = "202605280001"` (the actual chain head — corrected from initial error of `"202605210001"`). Creates `m1_extraction_runs` with FK `users.id` (corrected from initial error of `users.user_id`). Four indexes: `task_id` (unique), `source_id`, `celery_status`, composite `(source_id, queued_at)`.
3. ✅ **Backend — trigger persistence** — Added `db: AsyncSession = Depends(get_db)` to `trigger_extraction` endpoint in `app/api/v1/m1_gazette_extraction.py`. After `run_scraper.delay()`, INSERTs `M1ExtractionRun` row with `queued_by_id=admin.id` (corrected from `admin.user_id`) and `queued_by_email`. DB error is non-fatal (logged, request still returns the task_id).
4. ✅ **Backend — status sync** — Added `db` dependency to `extraction_status` endpoint. Side-effect: UPDATEs `celery_status` + `completed_at` when status first becomes terminal (only if not already terminal to avoid redundant writes). Updated `cancel_extraction` to UPDATE `celery_status='REVOKED'` after rollback.
5. ✅ **Backend — GET /runs endpoint** — Added paginated `GET /api/v1/admin/m1/extraction/runs` endpoint. Filterable by `source_id`. `page_size` max 100. Ordered `queued_at DESC`. Response schema: `ExtractionRunsListOut` (items, total, page, page_size, server_time). Added `ExtractionRunOut` and `ExtractionRunsListOut` to `app/schemas/m1_pipeline.py`.
6. ✅ **Frontend — API types + client** — Added `ExtractionRunOut` and `ExtractionRunsListOut` interfaces to `lib/api/m1-gazette-extraction.ts`. Added `listRuns(token, {sourceId, page, pageSize})` method to `M1GazetteExtractionApi`. Added `toTriggerOut()` normalizer in the extraction page to convert `ExtractionRunOut → GazetteExtractionTriggerOut`.
7. ✅ **Frontend — write-through history** — Updated `app/(admin)/admin/m1/pipeline/sources/[sourceId]/extraction/page.tsx`: `runsQuery` (TanStack Query, `queryKey: ["m1-extraction-runs", sourceId]`) fetches from GET /runs. `history` useMemo: if `runsQuery.data?.items.length > 0`, uses API data; otherwise falls back to `localHistory` (localStorage). `trigger.onSuccess` invalidates `["m1-extraction-runs", sourceId]` cache key.
8. ✅ **QueuePool fix** — Increased `pool_size: 1 → 3` and `max_overflow: 2 → 5` in `app/db/session.py`. Root cause: `AuditMiddleware._write_passive_log` opens a fresh `SessionLocal()` on every API request (detached `asyncio.create_task`), and the trigger/status endpoints now each also hold a DB session. With pool_size=1/max_overflow=2 (cap=3), two overlapping requests generated ≥4 concurrent connection attempts → `QueuePool limit of size 1 overflow 2 reached, connection timed out`. New budget: pool_size=3 + max_overflow=5 = 8 uvicorn conns + ~2 Celery = ~10 total, within Aiven's ~20–25 connection limit.

## Errors fixed (during implementation)

- **Alembic multiple heads:** Initial `down_revision = "202605210001"` created a fork because `202605220001` already pointed there. Fix: changed to `down_revision = "202605280001"` (the actual tip of the migration chain: `202605210001 → 202605220001 → ... → 202605280001`).
- **FK column mismatch:** Migration and model initially referenced `users.user_id` but the actual PK on the `users` table is `id`. Error: `column "user_id" referenced in foreign key constraint does not exist`. Fix: changed FK to `users.id` in both the migration and model. Also fixed `admin.user_id` → `admin.id` in the trigger endpoint.
- **PowerShell line continuation:** User ran git commands with `\` (bash syntax) which produced `fatal: \: '\' is outside repository`. Fix: provided backtick `` ` `` syntax for PowerShell multi-line git commands.

## Technical notes

- `queued_by_email` is denormalised (snapshot at trigger time) so history rows remain meaningful after an admin user is deleted (the FK is ON DELETE SET NULL, making `queued_by_id` nullable while `queued_by_email` retains the name).
- `result` column is JSONB, capturing the full Celery task result dict on SUCCESS — useful for post-mortem inspection without replaying the task.
- `rows_ingested/extracted/preprocessed/failed` snapshot captured from the summary API the first time the task reaches a terminal status; NULL while still running.
- `pool_size=1/max_overflow=2` was originally chosen to fit within Aiven's ~20-connection budget with Celery --concurrency=2. The new `pool_size=3/max_overflow=5` (8 uvicorn + ~2 Celery = ~10 total) still fits comfortably.
- The audit middleware `_write_passive_log` uses a detached `asyncio.create_task` so it never adds latency to the response — but it does consume a pool connection per request. This is the primary driver of the increased pool pressure.

## Decisions taken

- **localStorage retained as write-through cache** — provides instant display before the API responds; removed from the primary data source role.
- **DB error non-fatal on trigger** — if the INSERT fails (e.g. DB unavailable), the extraction task still starts and the task_id is returned. The run row can be reconciled later via the status polling side-effect.
- **Status updates only on terminal state transitions** — avoids redundant UPDATE calls for every STARTED poll; checks `celery_status != terminal` before writing.
- **pool_size=3, max_overflow=5** chosen as minimum headroom for current concurrency patterns; can be raised if Celery workers are scaled beyond 2.

## Open questions

- Should `rows_ingested/extracted/preprocessed/failed` be populated continuously (during the run) rather than only at terminal state? Would require the status polling endpoint to call the summary API on every poll, adding load.
- Should the GET /runs endpoint expose `traceback` and `result` fields, or only the count snapshots?
- Should a Celery signal handler (task_success / task_failure) update the run row instead of relying on the HTTP status polling side-effect? This would guarantee terminal state is recorded even if no admin polls the status endpoint after completion.

## Acceptance criteria

- [x] `m1_extraction_runs` table created by migration `202605210002`.
- [x] Every `POST /trigger` call inserts a `M1ExtractionRun` row.
- [x] `GET /status/{task_id}` updates `celery_status` + `completed_at` when status is terminal.
- [x] `GET /api/v1/admin/m1/extraction/runs` returns paginated run history filterable by source_id.
- [x] Frontend history table shows API data when available; falls back to localStorage.
- [x] `QueuePool limit` error no longer occurs with concurrent admin requests.

## Linked trackers

- [CHANGES.md](../CHANGES.md) — F-189, F-190, F-191, F-192
- [FEATURES.md](../FEATURES.md) — F-189, F-190, F-191, F-192
- [SESSIONS.md](../SESSIONS.md) — Session 54
- [BUILD_PLAN_COVERAGE.md](../BUILD_PLAN_COVERAGE.md) — Session 54 add-on
- [RESEARCH_BUILD_TRACKER.md](../RESEARCH_BUILD_TRACKER.md) — Session 54 row
- [ENIGMATRIX_MASTER_CONTEXT.md](../ENIGMATRIX_MASTER_CONTEXT.md) — pool fix + m1_extraction_runs system-shape note
