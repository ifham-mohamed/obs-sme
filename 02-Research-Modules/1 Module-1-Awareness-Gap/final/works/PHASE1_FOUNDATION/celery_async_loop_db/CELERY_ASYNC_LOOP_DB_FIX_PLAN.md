# Phase 1 · Foundation — Celery Async DB "Attached to a Different Loop" Crash: Fix Plan

> Group: `PHASE1_FOUNDATION / celery_async_loop_db`. Manifests in Phase-2 extraction but the root cause + fix live in the shared DB/Celery foundation.
> **Status: implemented (2026-07-23), verification deferred (sandbox VHDX down).** Root-cause fix (NullPool per worker) for the asyncpg cross-loop crash that put `extract_gazette` into an endless retry storm, plus a fast-fail default for the offline-HuggingFace noise in the same log.

## 1. Symptoms (from the worker log)

```
Exception terminating connection <AdaptedConnection asyncpg...>
RuntimeError: Task ... _terminate_graceful_close() ... got Future <Future pending> attached to a different loop
Future exception was never retrieved
  InternalClientError: got result for unknown protocol state 3
Task app.tasks.m1.extract_gazette.extract_gazette[...] retry: Retry in 2s:
  RuntimeError("... got Future ... attached to a different loop")
```
…and, separately, repeated:
```
Max retries exceeded with url: /xlm-roberta-base/resolve/main/tokenizer_config.json
  (NameResolutionError: Failed to resolve 'huggingface.co' ... getaddrinfo failed)
Retrying in 1s [Retry 1/5].
```

## 2. Root cause

**The async engine is a module-level QueuePool shared between two incompatible runtimes.** `app/db/session.py` builds one `create_async_engine(...)` with `pool_size=3, max_overflow=5`. FastAPI runs it under a single long-lived event loop (pooling is correct there). But every Celery task wraps its body in `asyncio.run(_..._async(...))` — a **fresh event loop per invocation**. A pooled async engine hands a task back an asyncpg connection that was opened on a *previous, now-closed* loop. asyncpg futures are loop-bound, so:

- reusing/closing that connection raises `got Future attached to a different loop` and `got result for unknown protocol state 3`;
- because each task has `autoretry_for=(Exception,)`, the failure retries forever instead of surfacing.

Every async task already carried an `await engine.dispose()` in its `finally` as a band-aid, but that can't fix it — with a shared pool the *next* task still gets a cross-loop connection, and `dispose()` running in a new loop is itself what raises during `_terminate_graceful_close`.

**The HuggingFace errors are a second, non-fatal issue:** on a host that can't resolve `huggingface.co`, a runtime tokenizer lookup burns 5×1 s retry back-offs. The classifier already no-ops when it isn't `ready` (`classify_gazette` guards on `classifier_status()`), so this is pure latency/noise, not a pipeline blocker — but it shares the same fix site.

## 3. The fix (code)

**`app/db/session.py`** — factored engine creation into `_make_engine(*, null_pool=False)` (unchanged QueuePool for web) and added `use_null_pool_engine()` which reassigns the module-level `engine`/`SessionLocal` to a `poolclass=NullPool` engine. Tasks reach these through the module namespace (`_db_session.SessionLocal` / `_db_session.engine`), so the swap is picked up with **zero task-code changes**. NullPool opens a fresh connection per session and drops it on close → every connection lives and dies inside one loop, so cross-loop reuse is impossible.

**`app/celery_config.py`** — new `@worker_process_init.connect` handler (fires in each prefork child after fork):
1. calls `use_null_pool_engine()` — the actual crash fix;
2. `os.environ.setdefault("HF_HUB_OFFLINE","1")` + `TRANSFORMERS_OFFLINE=1` — fail fast instead of 5×retry when offline; `setdefault` respects an explicit `=0` for operators who really want a runtime fetch. Set before any task imports transformers.

## 4. Why NullPool and not "just keep disposing"

`engine.dispose()` per task is O(open+close) per invocation *and* still leaves the window where a pooled connection crosses loops (the crash reproduced *with* the dispose in place). NullPool makes the "one connection per loop" invariant structural rather than best-effort. Cost: one connect per task — negligible next to a PDF fetch + OCR, and the connection budget actually *improves* (no idle pooled conns held per worker). The per-task `finally: dispose()` blocks are left in place: harmless with NullPool, and still useful when tasks run eagerly in tests (no `worker_process_init`, so the QueuePool engine is active).

## 5. Docs updated

- `enigmatrix-docs/m1/08_M1_2_Edge_Cases_Failure_Modes.md` — new failure mode entry.
- `AI_WORK_LOG.md` — session entry.

## 6. Verification (deferred — sandbox VHDX down)

1. `python -m compileall enigmatrix-backend/app/db/session.py enigmatrix-backend/app/celery_config.py`.
2. Boot a worker; confirm the log line `celery worker process init: NullPool DB engine + HF offline defaults applied` appears once per worker process.
3. Trigger a crawl over a multi-PDF range. Watch several `extract_gazette` tasks run back-to-back: **no** `attached to a different loop` / `unknown protocol state 3`, **no** retry storm; rows advance ingested→extracted→preprocessed. (This is also the real-time signal the run page now shows — see [[EXTRACTION_RUN_PAGE_REALTIME_PLAN]].)
4. Confirm the HF `getaddrinfo failed` warnings no longer 5×retry (classify no-ops fast while `no_model`).
5. Sanity: FastAPI still uses QueuePool (web path unchanged) — hit a couple of admin endpoints concurrently, no pool exhaustion.
6. `pytest` (task suites still pass under the eager/QueuePool path).
7. `graphify update .`.
