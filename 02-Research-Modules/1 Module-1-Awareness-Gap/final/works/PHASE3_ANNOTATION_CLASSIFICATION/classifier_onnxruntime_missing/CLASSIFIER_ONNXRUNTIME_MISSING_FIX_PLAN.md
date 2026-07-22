# Phase 3 · Classification — `classify_gazette` crash-loop: Fix + Plan

> Group: `PHASE3_ANNOTATION_CLASSIFICATION / classifier_onnxruntime_missing`. Companion: [[CLASSIFIER_ONNXRUNTIME_MISSING_ANALYSIS]].
> **Status: implemented (2026-07-22).** Code in `C:\Reasearch\xyz\enigmatrix-backend\app\m1\tasks\classify_gazette.py`.

## Two fixes — make it inert-safe, and stop the loop cascade

### Fix 1 — gate on `classifier_status()`; skip cleanly when not ready ✅

Before touching the ONNX engine, `_classify` now calls `classifier_service.classifier_status()`. If it isn't `"ready"` (`no_model` or `load_error`), the task **logs a warning, leaves the row at `preprocessed`, and returns a `skipped` result — it does not raise**. This matches the documented Phase-3 design (the classifier is a no-op until a trained artifact + runtime exist) and, because nothing raises, the `autoretry` never fires → the retry storm and its loop cascade can't start.

```python
status = classifier_status()
if status.get("status") != "ready":
    logger.warning("classify_gazette: classifier not ready (%s) — leaving %s at "
                   "'preprocessed', not classifying. %s",
                   status.get("status"), regulation_id, status.get("detail", ""))
    return {"status": "skipped", "reason": f"classifier_{status.get('status')}",
            "regulation_id": regulation_id}
```

Genuine transient errors during a *real* classification still raise and retry as before — only the "classifier unavailable" state is now a clean skip.

### Fix 2 — dispose the shared async engine in `finally` ✅

The whole body of `_classify` is now wrapped so that, on every exit (success, skip, or exception), it runs:

```python
finally:
    await _db_session.engine.dispose()
```

This is the exact rule the sibling tasks (`extract_gazette`, `preprocess_gazette`, `run_scraper`) already follow: each task runs under its own `asyncio.run()` loop, so the shared asyncpg pool must be disposed rather than left bound to a loop that's about to close. With this in place, even a legitimate retry can't produce `Event loop is closed` / `'NoneType' … send`.

## Files changed

| File | Change |
|---|---|
| `app/m1/tasks/classify_gazette.py` | readiness gate via `classifier_status()`; graceful `skipped` return; `try/finally` disposing `app.db.session.engine` |

No migration, no API change. `classifier_service.py` is unchanged — its `classifier_status()` already reports `no_model` / `load_error` / `ready` correctly; the task simply *uses* it now.

## What this does and doesn't do

- **Does:** stop the crash-loop and the event-loop cascade; let the pipeline finish cleanly with rows at `preprocessed`; keep Stage-D a true no-op while Phase 3 is untrained.
- **Doesn't:** magically classify anything. There is still no trained model. Rows stay `preprocessed` (not `classified`) until both of these exist:
  1. a trained ONNX artifact at `M1_MODEL_ONNX_DIR` (default `storage/models/m1/onnx/v1`) — see [[19_PHASE3_GAP_CLOSURE_PLAN]] Stages C–E, and
  2. the serving runtime in the worker env: **`cd enigmatrix-ml && uv sync --extra serving`** (installs `onnxruntime`).
  With both present, `classifier_status()` flips to `ready` and the same task classifies without any further change.

## Verification (deferred to user — sandbox lacks Postgres/Redis)

1. `cd enigmatrix-backend && python -m compileall app/m1/tasks/classify_gazette.py`.
2. `python -m app.m1.health` → `classifier` reports `no_model` or `load_error` (not `ready`) — confirms the state the gate now handles.
3. Re-run the pipeline for the same scope. Expected: **no `ModuleNotFoundError`, no `Event loop is closed` storm**; `classify_gazette_task` returns `{"status":"skipped","reason":"classifier_no_model"|"classifier_load_error"}`; the run's Celery state is SUCCESS; rows sit at `preprocessed`.
4. (Optional, to actually classify) install the serving extra + drop a model, then re-run → rows advance to `classified` with `classification_source='model'`.
5. `uv run pytest -q` (the classify task's existing tests still pass — behaviour for a *ready* classifier is unchanged).
6. `graphify update .`.

## Follow-ups

- The runtime health check already surfaces `classifier: no_model | load_error | ready` at worker boot / `GET /admin/m1/pipeline/health` / container start (Session 70). A small pipeline-portal banner reading that endpoint would make "classifier not installed/trained yet" visible in the UI instead of only in logs.
- Consider adding `onnxruntime` to the worker image's base install if classification is meant to run in this environment routinely — but keep it in the `serving` extra for API-only images (the ml package intentionally keeps it optional; see [[16_PHASE2_RUNTIME_DEPS_PLAN]] pattern).
- The engine-dispose-in-`finally` rule is now in all four async Celery tasks; worth a one-line lint/checklist item so future tasks don't reintroduce the cross-loop pool bug.
