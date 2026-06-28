---
tags: [tracker, findings, m1]
source: synthesised
layer: tracker
module: m1
---

# 2026-05-17 — M1 admin gazette extraction trigger (scoped year + month range) + Celery integration-test loop fix

> **Owner:** mohamedifham
> **Module:** m1
> **Type:** feature + decision + finding
> **Features:** [F-161](../../../08-Findings-Log/FEATURES.md#session-38), F-162
> **Session:** [Session 38](../../../08-Findings-Log/SESSIONS.md#2026-05-17--session-38-admin-scoped-gazette-extraction-trigger-fe--be--celery-integration-test-loop-fix-f-161-f-162)

## What I did

- Shipped a scoped Scrapy crawl trigger at `POST /api/v1/admin/m1/extraction/trigger` (admin-only). Admin picks a year (2010 → today) and a month range; backend queues `run_gazette_spider.delay(year, month_start, month_end)` and returns the Celery `task_id`. Frontend polls `GET /status/{task_id}` every 5 s until terminal.
- Frontend page lives at `/admin/m1/pipeline/extraction` (sidebar entry under the existing M1 Pipeline group, icon `DownloadCloud`). Three autocomplete `Combobox` dropdowns drive the form. On `SUCCESS` the page shows a "View recent runs →" link to the existing `/admin/m1/pipeline/recent` view (F-160 portal) — no new "results" surface needed.
- Extended `GazetteSpider.__init__` with three optional kwargs. Scrapy passes `-a` flags as strings, so the spider coerces to `int`. When `year` is set without `start_url`, builds the canonical `https://documents.gov.lk/view/egz/egz_<year>.html` URL automatically. The existing test-fixture `start_url` override still works untouched.
- Filtering happens at the spider's `parse()`, not at the download pipeline. `_in_scope(gazette_date)` skips rows whose date falls outside the bounded month range BEFORE `yield GazetteItem(...)` — so `PDFDownloadPipeline` never fires for them. Saves bandwidth + keeps the bulletproof `gazette_number` UNIQUE de-dupe behaviour.
- Added defence-in-depth scope validation via `_validate_scope()` in `app/tasks/m1/gazette_scraper.py`. It rejects year < 2010, year > today, month outside 1–12, or `month_start > month_end`. The API surfaces it as HTTP 400; the Celery task surfaces the same `ValueError` so a direct `run_gazette_spider.delay(...)` from a Python REPL also fails loudly.
- Fixed a long-latent Celery eager-mode + pytest-asyncio integration-test bug. `pyproject.toml` configures `asyncio_default_test_loop_scope = "session"`, so under `@pytest.mark.asyncio` there's already a loop running when the test calls `task.delay(...).get()`. Celery eager-mode then runs the task body inline in the test's loop → the task's own `asyncio.run()` crashes with `RuntimeError: asyncio.run() cannot be called from a running event loop`. New `_run_eager_task(task, *args, timeout)` helper fixes it test-side only.
- Added per-test data isolation via `TRUNCATE m1_regulation_penalties, m1_sub_documents, m1_regulations RESTART IDENTITY CASCADE` inside `patched_session` (preprocess test only). Previously: test 1 inserted gazette `2369/14` from the VAT-amendment fixture, tests 4–5 reused the same fixture → `ix_m1_regulations_gazette_number` UNIQUE collision.

## What I found

- **Production task code does NOT need to change.** `asyncio.run()` is correct for a real Celery worker — the worker thread has no running loop. The fix lives entirely in the test harness. Specifically:
  ```python
  async def _run_eager_task(task, *args, timeout: float = 120):
      from app.db import session as session_mod
      await session_mod.engine.dispose()  # clear test-loop-bound pool
      return await asyncio.to_thread(
          lambda: task.delay(*args).get(timeout=timeout)
      )
  ```
  The thread offload mirrors a real Celery worker; the pool dispose forces the task's `asyncio.run()` loop to mint fresh asyncpg connections rather than inheriting test-loop-bound ones (which would crash with `Future attached to a different loop`).
- **The cascade of three layered errors.** Each fix revealed the next:
  1. `asyncio.run()` inside running loop → fixed by `asyncio.to_thread`.
  2. `Future attached to a different loop` → fixed by `engine.dispose()` before handoff.
  3. `duplicate key value violates ix_m1_regulations_gazette_number` → fixed by per-test `TRUNCATE`.
  Solving one without the next two is a partial fix that keeps tests red.
- **The `accessToken` ↔ `access` token-key drift.** Six other M1 portal pages copy-pasted the same `useEffect` that reads `d.accessToken` from `/api/auth/token` — but the route returns `{ access }`, not `{ accessToken }`. The bug doesn't manifest as a crash because `useQuery` is gated by `enabled: !!token` and silently keeps the pages in skeleton state when token stays `null`. The new extraction page's "Start extraction" button surfaced it (because the button is gated by `!token` directly). Only the new page fixed in this lap.
- **Celery's `AsyncResult.status` returns `'PENDING'` for unknown task IDs (not 404).** The status endpoint accepts any string; the FE renders the "Queued" tone until the task transitions. Acceptable trade-off vs. inventing a job-tracker DB table.
- **Beat-scheduled invocation still works unchanged.** The new task parameters are all optional. When `run_gazette_spider.delay()` is called with no args (the Beat path), `_validate_scope(None, None, None)` is a no-op, no `-a` flags get appended, the spider's `start_urls` defaults stay as-is. Only the admin-trigger path uses the new scope.

## What changed in the repo

| File | Change |
|---|---|
| `enigmatrix-backend/app/api/v1/m1_gazette_extraction.py` | NEW — 2 endpoints under `Depends(require_admin)`: `POST /trigger` + `GET /status/{task_id}`. |
| `enigmatrix-backend/app/api/v1/router.py` | Registered new router at `prefix="/admin/m1/extraction"`, tag `"admin-m1-extraction"`. |
| `enigmatrix-backend/app/schemas/m1_pipeline.py` | Added `GazetteExtractionTriggerIn`, `GazetteExtractionTriggerOut`, `GazetteExtractionStatusOut`. |
| `enigmatrix-backend/app/tasks/m1/gazette_scraper.py` | `run_gazette_spider(year, month_start, month_end)` signature; new `_validate_scope()`. |
| `enigmatrix-backend/scraper/spiders/gazette_spider.py` | `__init__` accepts year/month_start/month_end; `_in_scope()` filter inside `parse()`. |
| `enigmatrix-backend/app/tests/unit/test_gazette_scraper_task.py` | +3 tests: scope-as-flags, inverted range rejected, pre-2010 year rejected. |
| `enigmatrix-backend/app/tests/integration/test_gazette_spider.py` | +2 tests: year arg builds canonical URL, month-range filter drops out-of-scope rows. |
| `enigmatrix-backend/app/tests/integration/test_celery_extract_gazette.py` | Added `_run_eager_task` helper, replaced 2 `.delay().get()` calls. |
| `enigmatrix-backend/app/tests/integration/test_celery_preprocess_gazette.py` | Added `_run_eager_task` helper, replaced 7 `.delay().get()` calls, added `TRUNCATE` to `patched_session`. |
| `enigmatrix-frontend/app/(admin)/admin/m1/pipeline/extraction/page.tsx` | NEW — admin form with three `Combobox` inputs + status polling. |
| `enigmatrix-frontend/lib/api/m1-gazette-extraction.ts` | NEW — typed client wrapper. |
| `enigmatrix-frontend/components/layout/sidebar.tsx` | Added `DownloadCloud` icon import + entry to `ADMIN_M1_PIPELINE_ITEMS`. |
| `enigmatrix-frontend/lib/i18n/messages/{en,si,ta}.json` | Added `nav.adminM1Extraction = "Gazette Extraction"`. |

## Tests

- `cd enigmatrix-backend && uv run pytest app/tests/unit/test_gazette_scraper_task.py app/tests/integration/test_gazette_spider.py -v` → **11 passed**.
- `cd enigmatrix-backend && uv run pytest app/tests/integration/test_celery_extract_gazette.py app/tests/integration/test_celery_preprocess_gazette.py -v` → **8 passed** (was: 8 erroring before F-162).
- Combined: `uv run pytest app/tests/unit/test_gazette_scraper_task.py app/tests/integration/test_gazette_spider.py app/tests/integration/test_celery_extract_gazette.py app/tests/integration/test_celery_preprocess_gazette.py -v` → **19 passed** in ~93 s.
- Frontend type-check: `cd enigmatrix-frontend && npx tsc --noEmit` → clean (only pre-existing `trace-timeline.tsx::sky` color-key error remains, unrelated).

## Decisions

- **Filter at `parse()` not at the pipeline.** Out-of-month rows dropped BEFORE `yield`, so `PDFDownloadPipeline` never fires for them.
- **Validation in both layers (API + task).** API → HTTP 400; task → `ValueError`. Direct REPL invocations also get protected.
- **No `extraction_jobs` DB table this lap.** Celery's already-configured Redis result-backend (`app/celery_config.py:22`) supports `AsyncResult(task_id).status`. The F-160 portal at `/admin/m1/pipeline/recent` covers post-trigger row observability.
- **Autocomplete `Combobox` over plain shadcn `Select`.** Typing "Aug" jumps to August faster than scrolling 12 entries; same for years (17 entries from 2010 → 2026).
- **F-161 vs F-162 split.** Test-loop fix is small but structurally distinct (DX infrastructure, reused by future Celery integration tests). Kept as its own F-### for tracker readability.

## Risks / open follow-ups

- **`accessToken → access` sweep across 6 other M1 portal pages.** Latent — currently degrades to skeleton state, not crashes. One-line each.
- **No backend integration test for the new `/admin/m1/extraction/{trigger,status}` endpoints.** Trigger logic unit-tested at the Celery-task layer; FastAPI surface only smoke-verified manually.
- **Beat-scheduled invocation still defaults to `egz_2026.html`.** Becomes stale in 2027 unless someone updates `start_urls` or drops the Beat schedule (admins can trigger on-demand now anyway).
- **No real-network smoke check ran in this lap.** Inline HTML fixture exercises the scope-filter; user runs the manual end-to-end smoke per the new `phase2_admin_gazette_extraction.md` local-dev doc.

## Cross-references

- Spec: M1 Phase 2 admin tooling extension (no dedicated BUILD doc — this is a UI-only layer over the shipped Phase 2 pipeline).
- Predecessors: [F-145 (spider)](../../../08-Findings-Log/FEATURES.md#session-23), [F-148 (Celery extract)](../../../08-Findings-Log/FEATURES.md#session-26), [F-155 (preprocess wiring)](../../../08-Findings-Log/FEATURES.md#session-32), [F-160 (M1 Pipeline portal)](../../../08-Findings-Log/FEATURES.md#session-37).
- Runtime doc: [`local-dev/phase2_admin_gazette_extraction.md`](../local-dev/phase2_admin_gazette_extraction.md).
- Session entry: [Session 38](../../../08-Findings-Log/SESSIONS.md).
