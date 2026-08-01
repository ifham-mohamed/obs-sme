# Phase 2 · Extraction — Preprocessing Starved Behind Extraction (0/N): Fix Plan

> Group: `PHASE2_INGEST_EXTRACTION / pipeline_stage_starvation`. Follows [[LANGUAGE_CHECK_CONSTRAINT_FIX_PLAN]] (rows now commit) — this is the next thing the operator saw.
> **Status: implemented (2026-07-23), verification deferred (sandbox VHDX down).** Not a crash — a throughput/ordering issue: preprocessing showed 0/228 for the whole extraction window. Fixed by prioritising downstream pipeline stages so they interleave with extraction.

## 1. Symptom (run page, task e70d9f7b…, scope 2026-03-01 → 03-31)

```
1 · Scraping     228 PDFs found          (Celery SUCCESS)
2 · Extracting    37 / 228
3 · Preprocessing  0 / 228
Run summary: In scope 228 · Raw chars 470K · Cleaned chars 0 · Penalties 0 · Sub-documents 0
Pipeline status: 37 extracted · 191 ingested
```
Extraction crept forward (~16 s/PDF) while **preprocessing stayed at 0** and cleaned-chars/penalties/sub-documents were all 0 — so it looked frozen even though it was making progress.

## 2. Root cause — FIFO starvation, not a bug

The worker processes one task at a time (single slot). Ingest enqueues **one `extract_gazette` per row** — 228 of them — up front. The extract→preprocess chain enqueues `preprocess_gazette_task` at the **tail** of the same FIFO queue. So the worker runs all 228 extracts first, and only then starts the 228 preprocesses. Result: for the whole ~hour extraction window, "Preprocessing" is pinned at 0/228. Nothing is broken — the counts are just serialised stage-by-stage instead of flowing per-document.

(The log confirms extraction itself is healthy post-fixes: `extract_gazette … extracted via wijesekara_routing_v1 (9466 chars)` → `COMMIT` → `Task … succeeded`.)

## 3. The fix (code) — prioritise downstream stages

Celery 5.3 + Redis supports priority queues (`priority_steps` default `[0,3,6,9]`, where **0 = highest** for the Redis transport). Enabling it lets a just-enqueued preprocess jump ahead of the pending extract backlog:

- **`app/celery_config.py`** — `broker_transport_options={"queue_order_strategy": "priority"}` + `task_default_priority=5`. Works with the existing `worker_prefetch_multiplier=1` (the worker reserves only the single highest-priority task available, so priority actually decides what runs next).
- **`extract_gazette`** — `preprocess_gazette_task.apply_async((regulation_id,), priority=0)` (highest).
- **`preprocess_gazette`** — `classify_gazette_task.apply_async((regulation_id,), priority=1)` (above the extract backlog, below preprocess).

Priority ladder: **preprocess (0) > classify (1) > extract (default 5)**. After each PDF extracts, its preprocess runs before the next extract → extract/preprocess/classify **interleave**, and the run page's per-stage tallies (which now update live — see [[EXTRACTION_RUN_PAGE_REALTIME_PLAN]]) climb together instead of 0 → all-at-once.

Safety: if priority somehow doesn't take effect on a given broker, tasks still run — just in the old FIFO order (no regression). No inversion risk: downstream is pinned to the documented highest end (0/1), upstream to the middle default (5).

## 4. The other half — throughput (recommended, not forced)

Priority fixes *interleaving/visibility* but the run is still **serial** (~16 s/PDF ⇒ ~60 min for 228). The lever is worker concurrency, now safe after the NullPool fix ([[CELERY_ASYNC_LOOP_DB_FIX_PLAN]] — each task gets its own connection/loop). Recommended (not baked into code, since the right pool is OS-specific): run the worker with concurrency, e.g.
- Linux: `celery -A app.celery_config worker --concurrency=4` (prefork).
- Windows: `celery -A app.celery_config worker --pool=threads --concurrency=4` (extraction is I/O-bound: HTTP fetch + Tesseract subprocess, so threads parallelise well; prefork on Windows is unreliable).
Left as ops guidance so it doesn't fight however the operator launches the worker.

## 5. Docs updated

- `enigmatrix-docs/m1/08_M1_Full_System_Architecture.md` — failure-mode row.
- `AI_WORK_LOG.md` — session entry.

## 6. Verification (deferred — sandbox VHDX down)

1. `python -m compileall app/celery_config.py app/m1/tasks/extract_gazette.py app/m1/tasks/preprocess_gazette.py`.
2. Restart the worker (priority config only applies to newly enqueued tasks). **Re-trigger a fresh run** — the in-flight backlog from the stuck run was enqueued pre-change and won't reorder.
3. Watch the run page: "Extracting" and "Preprocessing" should now climb roughly together (a few extracted ahead of preprocessed), not 0 until the end.
4. Optional: run the worker with `--concurrency=4` and confirm multiple PDFs extract concurrently (visible in the log + faster wall-clock).
5. `pytest` (eager mode ignores priority — suites unaffected); `graphify update .`.
