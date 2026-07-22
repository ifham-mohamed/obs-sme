# Phase 2 · Ingest — Pipeline Stalls After Ingest: Fix Plan

> Group: `PHASE2_INGEST_EXTRACTION / pipeline_stall_after_ingest`. Companion: [[PIPELINE_STALL_AFTER_INGEST_ANALYSIS]].
> **Status: implemented (2026-07-23).** One-line root-cause fix + a guardrail so this class of bug can never silently stall the pipeline again.

## 1. The fix (code)

**File:** `enigmatrix-backend/scraper/pipelines.py` — `M1RegulationsInsertPipeline._insert_rows`, dispatch block.

- **Correct the import path:** `from app.tasks.m1 import extract_gazette` → **`from app.m1.tasks import extract_gazette`**. This is the canonical post-reorg task package (`app/m1/tasks/__init__.py` re-exports the `extract_gazette` Celery task).
- **Split the `try` and narrow the except so failures can't hide:**
  - The **import** now has its own `try/except ImportError` that logs `.exception(...)` and **re-raises**. A broken dispatch path is a code bug — it must fail loudly, not degrade to a warning.
  - The **`.delay()` enqueue** keeps its own `except Exception` → `warning` (this is the legitimate "broker down in dev/tests" path, where leaving the row at `ingested` for a later reconcile is correct behaviour).

```python
try:
    from app.m1.tasks import extract_gazette
except ImportError:
    spider.logger.exception("extract_gazette import failed — pipeline dispatch is broken; "
                            "regulation_id=%s left at 'ingested'", regulation_row.regulation_id)
    raise
try:
    extract_gazette.delay(str(regulation_row.regulation_id))
    spider.logger.info("enqueued extract_gazette(%s)", regulation_row.regulation_id)
except Exception as dispatch_exc:  # broker-down path only
    spider.logger.warning("could not enqueue extract_gazette(%s): %s — row stays 'ingested'",
                          regulation_row.regulation_id, dispatch_exc)
```

## 2. Why this is the right shape

The original broad `except Exception` conflated two very different failures: a **transient** broker outage (recoverable, warn-and-continue) and a **permanent** import error (a bug, must surface). Separating them means the transient path still degrades gracefully, while any future stale import / packaging break trips the scrape immediately instead of quietly producing 261 orphaned `ingested` rows.

## 3. One-time unstick for the already-stuck rows

The fix only affects **new** ingests. The 261 rows already at `status='ingested'` won't re-dispatch on a fresh crawl (they're dropped as duplicates before the dispatch block). Kick them once, any of:

- **Admin portal → pipeline → Trigger extraction** over the affected source/date scope (re-enqueues extraction for in-scope `ingested` rows).
- **Per row:** `POST /admin/m1/…/regulations/{id}/re-extract` (or `/retry` for `extraction_failed`).
- **Bulk one-off** (psql / shell): enqueue `extract_gazette.delay(str(id))` for every `SELECT regulation_id FROM m1_regulations WHERE status='ingested'`.

Each kicked row runs extract → auto-chains to preprocess, so they land at `preprocessed` on their own.

## 4. Verification (deferred to user — sandbox VHDX still down)

1. `python -m compileall enigmatrix-backend/scraper/pipelines.py` (syntax).
2. Grep guard — no stale paths remain: `rg "from app\.tasks\.m1 import" enigmatrix-backend/` returns only `_m1_migrate.py` (the rewrite script's own regex/comments).
3. Run the pipeline on a small scope. Worker log should now show `enqueued extract_gazette(<id>)` after each `INSERTED regulation … status=ingested`, then stage 2/3 advance. Confirm at least one row reaches `status='preprocessed'`.
4. Unstick the existing 261 per §3 and confirm they drain out of `ingested`.
5. `graphify update .`.
