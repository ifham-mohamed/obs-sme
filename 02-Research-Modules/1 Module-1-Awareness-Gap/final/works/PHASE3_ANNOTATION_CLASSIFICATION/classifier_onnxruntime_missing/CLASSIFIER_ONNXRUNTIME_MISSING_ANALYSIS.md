# Phase 3 · Classification — `classify_gazette` crash-loop (onnxruntime missing): Analysis

> Group: `PHASE3_ANNOTATION_CLASSIFICATION / classifier_onnxruntime_missing`. Companion: [[CLASSIFIER_ONNXRUNTIME_MISSING_FIX_PLAN]].
> Symptom captured 2026-07-22 20:11 · `classify_gazette_task` failing repeatedly.

## Symptom

After the scraper fix let the pipeline progress into the classify stage, `classify_gazette_task` failed on every row with:

```
File ".../classifier_service.py", line 29, in _engine
    return GazetteInference(_ONNX_DIR)
File ".../enigmatrix-ml/m1/model/inference.py", line 21, in __init__
    import onnxruntime as ort
ModuleNotFoundError: No module named 'onnxruntime'
```

…immediately followed by a storm of:

```
RuntimeError: Event loop is closed
AttributeError: 'NoneType' object has no attribute 'send'
```

## Two problems (the second is a cascade of the first)

### Problem 1 — the classifier tries to run when it can't (primary)

`onnxruntime` is **not installed** in the worker environment (the ml package's optional `serving` extra was never `uv sync`-ed there). So the ONNX inference engine can't even import.

But the deeper flaw is in `classify_gazette._classify`: it called `classify_text(text)` **unconditionally**, never consulting the readiness signal that already exists — `classifier_service.classifier_status()`, which returns `no_model` (no artifact yet) / `load_error` (artifact present but the engine won't import) / `ready`. Phase 3 is, by design, **inert until a model is trained** ([[11_PHASE3_ANNOTATION_CLASSIFICATION_ANALYSIS]] §0 — "wired no-op"). The task was supposed to no-op in that state; instead it hit the import, set `last_error`, and **re-raised**.

### Problem 2 — raise → retry → "Event loop is closed" cascade (secondary)

`classify_gazette_task` is declared `autoretry_for=(Exception,)`, `max_retries=3`. So each raised `ModuleNotFoundError` triggered up to three retries, and the Celery entry point is `asyncio.run(_classify(...))` — a **fresh event loop per attempt**. The DB layer uses a **shared, module-level async engine** (`app.db.session.engine`); its asyncpg connection pool binds connections to the loop that created them. On the *next* `asyncio.run`, SQLAlchemy tried to health-check (ping) a pooled asyncpg connection created on the **previous, now-closed** loop → `RuntimeError: Event loop is closed`, and asyncpg's proactor write then blew up as `'NoneType' object has no attribute 'send'`.

Crucially, the sibling tasks (`extract_gazette`, `preprocess_gazette`, `run_scraper`) all **dispose the shared engine in a `finally`** for exactly this reason. `classify_gazette` was the one task that didn't — so it both *caused* the retries (problem 1) and *amplified* them into the loop-closed cascade (problem 2).

## Why the pipeline showed FAILURE with rows stuck

The chain reached `preprocessed`, then Stage-D failed hard on every row and retried, so the run's terminal Celery state was FAILURE and nothing advanced to `classified`. The DB writes you see in the log (`UPDATE m1_regulations SET last_error_at=…`) are the `except` block stamping the error before re-raising.

## Root cause, in one line

The classifier hard-failed (missing `onnxruntime`) **instead of no-opping while Phase 3 is untrained**, and because the failing task didn't dispose its async engine, the retries turned one clean "not ready" condition into an event-loop-closed storm.

## Not the cause

- Not the scraper (that's fixed and now succeeds — the log shows it reached classify).
- Not the DB (Postgres is up; the "event loop closed" errors are client-side asyncpg/loop reuse, not a server problem).
- Not a trained-model bug — there is no trained model yet; the correct behaviour is to skip, which is what the fix restores.
