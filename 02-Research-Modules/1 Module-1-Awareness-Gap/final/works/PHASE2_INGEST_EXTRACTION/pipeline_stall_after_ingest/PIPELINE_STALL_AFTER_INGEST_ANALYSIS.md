# Phase 2 · Ingest — Pipeline Stalls After Ingest: Analysis

> Group: `PHASE2_INGEST_EXTRACTION / pipeline_stall_after_ingest`. Companion: [[PIPELINE_STALL_AFTER_INGEST_FIX_PLAN]].
> **Status: root cause found + fixed (2026-07-23).** Related: [[SCRAPER_STALE_MODEL_IMPORT_ANALYSIS]] (same class of bug — a stale post-reorg import), [[SCRAPER_CRAWL_EXIT1_ANALYSIS]].

## 1. Symptom

Running the gazette pipeline, the admin portal shows:

```
1 · Scraping … 261 PDFs found  (Spider → gazette items)   ✅
2 · Extraction …                                          — never advances
3 · Preprocessing …                                       — never advances
```

The scrape "succeeds" — 261 `m1_regulations` rows land at `status='ingested'` with their `m1_gazette_items` — but nothing ever moves to `extracted` / `preprocessed`. The pipeline is stuck at stage 1.

## 2. Root cause

The scraper's DB-insert pipeline dispatches the Stage-B extractor per row. In `enigmatrix-backend/scraper/pipelines.py`, `M1RegulationsInsertPipeline._insert_rows` did:

```python
try:
    from app.tasks.m1 import extract_gazette   # ← stale path
    extract_gazette.delay(str(regulation_row.regulation_id))
    ...
except Exception as dispatch_exc:               # ← too broad
    spider.logger.warning("could not enqueue … — row stays 'ingested'", …)
```

Two faults compounding:

1. **Stale import path.** The M1 module reorg (`08_M1_MODULE_REORG_PLAN`) moved the task package from `app.tasks.m1` → **`app.m1.tasks`**. The `_m1_migrate.py` rewrite even carries a regex for exactly `from app.tasks.m1 import ` → `from app.m1.tasks import `, but **this one line was missed** (it lives inside a `try` block). `app.tasks.m1` no longer exists, so the import raises `ModuleNotFoundError` on every single item. Every other caller in the codebase already uses the correct `from app.m1.tasks import extract_gazette` (`reconcile_raw.py`, `gazette_extraction.py`, `completeness.py`) — the scraper pipeline was the lone straggler.

2. **The broad `except Exception` swallowed it.** The handler was written for the legitimate "broker is down in dev/tests" case and downgrades any failure to a `warning`, leaving the row at `ingested`. So a hard, always-fatal `ModuleNotFoundError` was silently absorbed as if it were a transient broker hiccup — the pipeline reported success while never enqueuing a single extraction.

Net: `.delay()` was **never reached**. Zero `extract_gazette` tasks were ever queued from a scrape. The rows sit at `ingested` forever, and because the auto-chain `extract → preprocess` starts inside `extract_gazette`, preprocessing never runs either.

## 3. Why "261 found" but 0 extracted, and why a re-run doesn't self-heal

`M1RegulationsInsertPipeline` drops duplicates (UNIQUE `regulation_short_code`) with `DropItem` **before** the dispatch block. So on a second crawl the 261 already-ingested rows are dropped as duplicates and never reach dispatch again. The stuck rows therefore do **not** get re-queued by simply re-running the spider — they need a one-time re-dispatch (see the plan §3).

## 4. Blast radius

- Every automatic scrape since the reorg produced `ingested` rows that never extracted. The only extractions that ran were ones triggered **manually** through the admin endpoints (`/re-extract`, `/retry`, reconcile), which import the task correctly.
- No data loss — `download_url` is stored on each `m1_gazette_items` row, so the PDFs are re-fetchable in-memory at extract time. Nothing needs re-scraping; the stuck rows only need extraction kicked.

## 5. Verification signal

Before: worker log shows the scrape finishing with `INSERTED regulation … status=ingested` lines but **no** `enqueued extract_gazette(…)` lines. After the fix: each insert is followed by `enqueued extract_gazette(<id>)`, and the worker picks them up (`extracted` → auto-chain → `preprocessed`).
