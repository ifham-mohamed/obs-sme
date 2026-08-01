# Phase 2 · Observability — Console Logging Rebuild: Analysis

> Group: `PHASE2_INGEST_EXTRACTION / observability_console`. What the four development consoles (api / worker / beat / web) were doing wrong, the four defects found underneath a complaint that sounded cosmetic, and what replaced them.
>
> Shipped 2026-07-28 (Session 101), with a same-session follow-up after the API console was found still flooded. Written up 2026-08-01 — this workstream had **no coverage anywhere in `works/`** until now.
>
> Evidence: `AI_WORK_LOG.md` Session 101 · `enigmatrix-backend/app/obs/` · `enigmatrix-docs` SETUP §10a · `.env.example`.

---

## 0. The one-paragraph truth

The complaint was "the terminals are unreadable — no colour, no status codes, per-transaction spam." The audit found that **one of the four causes was a real bug hiding behind a cosmetic symptom**: the API silently dropped every `INFO` log, so `logger.info(...)` in roughly 40 service and API modules printed nothing under uvicorn while the identical code printed fine under Celery. Same code, different behaviour per process, for the whole of development. The other three causes were genuine noise sources, the largest of which — SQLAlchemy `echo=` left on in development — printed every SELECT, every INSERT and its parameter tuple into *two* consoles. The fix is a new `app/obs/` package plus a routing change that gave ~180 existing stdlib call sites the new format with **zero edits**.

---

## 1. Why this belongs in Phase 2

It is infrastructure, not ingest — but it is the surface through which every Phase-2 pipeline run is observed. The extraction pipeline is a long-running, multi-stage, partially-failing batch process, and the console was the only place a human could see which gazette was in which stage. A console that prints 1,400 lines of framework narration per run is not a cosmetic problem for that workflow; it is the difference between noticing a stalled stage and not.

The related Phase-2 incident folders — `pipeline_stall_after_ingest/`, `pipeline_stage_starvation/`, `extraction_ws_heartbeat_disconnect/` — are all problems that were *found by reading logs*. This document explains why those logs became readable.

---

## 2. The four defects

### 2.1 `echo=(APP_ENV == "development")` in `db/session.py`

Every SELECT/INSERT and its parameter tuple printed in **both** the API and worker consoles for the entire development period. By volume this was the single largest noise source on the platform — the "every transaction" the complaint described.

Now behind `DB_ECHO=1`, off by default.

### 2.2 Two logging systems that never met

structlog was configured, and **5 files used it**. The other ~180 call sites use stdlib `logging.getLogger(__name__)` and were untouched by any structlog processor.

Fixed by routing stdlib records through the same chain via `ProcessorFormatter` + `ExtraAdder`. That is why this was scoped as **plumbing rather than a call-site rewrite**: all ~180 existing call sites get the new format with zero edits.

### 2.3 The API silently dropped INFO — the actual bug

The old `setup_logging` configured structlog and **never touched the stdlib root logger**, which defaults to `WARNING` with no handler under uvicorn. So `logger.info(...)` in ~40 service and API modules printed **nothing** in the API console — while the identical code printed fine under Celery, because Celery configures root itself.

This is the finding worth carrying forward: *a cosmetic complaint can be the visible edge of a correctness bug.* Anyone debugging an API-side pipeline problem before this fix was working with a console that had been silently discarding the log level most of the code writes at.

### 2.4 No request line at all

`AuditMiddleware` writes compliance rows to the database and prints nothing. The only per-request console output was uvicorn's access log — no colour, no duration, no actor, and no filtering of `/health` polling.

---

## 3. What replaced them

**New `app/obs/` package:**

| Module | Role |
|---|---|
| `console.py` | Aligned-column renderer; colour / TTY / Windows-VT handling |
| `context.py` | `req` / `run` / `stage` contextvars |
| `summary.py` | Shutdown error recap |
| `progress.py` | Stage rollups + the live status bar |
| `celery_hooks.py` | Worker lifecycle wiring |
| `demo.py` | `make console-demo` — renders every terminal without starting a service |

`logging_config.py` keeps its public surface (`log`, `setup_logging`), so `main.py`, `exceptions.py`, `audit_middleware.py` and `m4_service.py` import unchanged.

### 3.1 The status bar is fed through Redis on purpose

Under `--concurrency=8`, Celery prefork is eight **separate processes**. An in-process counter gives eight partial views, and eight children rewriting one terminal line shreds it.

So children publish their in-flight item to short-TTL Redis keys, and **one renderer thread — started from `worker_ready`, which fires in the parent — owns the line.** Redis is already the broker, so this adds no infrastructure. Every Redis call is swallowed, so a broker blip degrades progress reporting to nothing rather than touching the pipeline. The bar auto-disables when stderr is not a TTY, where escape sequences would corrupt a log file.

### 3.2 Progress hooks `publish_stage()`, not the three task files

Every stage boundary in the pipeline already calls through that one function with the human-readable gazette number. So extract / preprocess / classify all gained rollups, failure lines and status-bar labels from **a single instrumentation point**.

Nine per-item INFO lines in `extract_gazette` / `preprocess_gazette` were demoted to DEBUG — they are what the rollups replace. `LOG_LEVEL=DEBUG` brings them back.

---

## 4. Two semantics decisions worth recording

1. **A stage with *some* failures logs at WARNING with `status=OK` and a `failed=N` count.** `FAIL` is reserved for a stage that completed nothing. Marking a 225/228 run "FAIL" trains an operator to ignore the status column — which is a worse outcome than the noise this work removed.
2. **The shutdown summary groups on the message *template*, not the rendered message.** Eighteen gazette IDs hitting one problem collapse to one row with a count. Templates carrying no literal content (`"%s"`, `"%s done"`) fall back to the reason field — a fallback added during verification, when every progress failure was found collapsing into a single useless `%s` row.

---

## 5. The follow-up — the API console was still flooded

Three further defects, found from pasted output after the first fix:

### 5.1 The `echo=` fix had landed on only one of two engines

`db/session.py` builds a NullPool engine (Celery) and a QueuePool engine (uvicorn) with the same `echo=(APP_ENV == "development")` line **at different indentation** — so a string replace matched one and silently left the other. The worker went quiet; the API — the process actually serving the polled admin endpoints — did not. Both now call `_echo_enabled()`.

**The lesson is about the edit, not the code:** an identical line at two indentation levels is a replace that reports success and does half the job.

### 5.2 A log level alone could never have held

`create_async_engine(echo=True)` calls `setLevel(INFO)` on `sqlalchemy.engine.Engine` **and attaches its own raw-format handler** at engine-creation time — which happens on `app.db.session` import, either side of `setup_logging` depending on import order and the reloader. That is why both an unformatted `… INFO sqlalchemy.engine.Engine SELECT …` line **and** a formatted copy appeared for every statement.

Fixed with `_SQLEchoFilter` on our handler (order-independent: nothing reaches the console even if echo is re-enabled) plus `handlers.clear()` on the SQLAlchemy loggers. `sqlalchemy` at WARNING+ still passes — **a pool exhaustion must not be hidden by a noise fix.**

### 5.3 The renderer had no ceilings

`ExtraAdder` passed stdlib record attributes through, so every line carried `message=<the entire message again>` and `asctime=…`; and a multi-line SQL statement broke the columns for itself and everything after it.

Now: `_STDLIB_RECORD_KEYS` excluded, all values collapsed to one line, per-value cap of 80 characters with a `…+N` marker, per-line context cap of 200. **"One event is one line" is now structurally enforced rather than assumed.**

### 5.4 Poll collapsing

With the SQL gone, the next-loudest thing was the admin page polling `/extraction/{progress,summary}` once a second — a line per second, forever.

A repeat **successful GET** to an already-seen path is counted rather than printed; one summary line per 30-second window carries the count, the average and the peak (`polls=x47 peak=2.3s`), raised to WARNING when any sample exceeded 1s so degradation under polling stays visible. Mutations and 4xx/5xx are **never** collapsed — this hides healthy repetition and nothing else.

The bound `req` id is cleared before a collapsed line is emitted: an id identifying one request is misleading on a line standing for 47.

Measured: **76 polling requests → 4 lines.** Knobs: `API_POLL_COLLAPSE=0`, `API_POLL_WINDOW_S`.

---

## 6. Everything else that was silenced

| Source | Change | Reason |
|---|---|---|
| Scrapy `LOG_LEVEL` | INFO → WARNING | It runs as a worker subprocess, so its per-request lines and stats table landed in the worker terminal |
| Celery `worker_hijack_root_logger` | off | Was overriding the unified configuration |
| Celery `worker_redirect_stdouts` | off | Captured prints into the log stream |
| `uvicorn.access` | disabled | Replaced by `RequestLogMiddleware` |
| Makefiles, `start_railway.sh` | `--no-access-log`, `--loglevel=warning` | Same format from every entry point |
| Frontend `lib/logger.ts` | Mirrors the format in the Next terminal | Failures and >1s calls only; sends `X-Request-ID` so one action greps across all four consoles |

---

## 7. Verification performed

| Check | Result |
|---|---|
| Middleware through a real Starlette app | status→level mapping, `/health` + OPTIONS filtered, client request id echoed |
| Renderer, colour and `NO_COLOR` modes | correct |
| Exception blocks | rendered |
| ML formatter standalone **and** its no-op path when the worker already configured root | both correct |
| Celery hooks under a mocked celery | correct |
| Redis absent / Redis raising | degrades to no progress reporting; pipeline untouched |
| Existing tests referencing changed logging | none |
| Poll collapsing, measured | 76 requests → 4 lines |

---

## 8. Gaps and follow-ups

1. **This is development-console work, not production observability.** There is still no metrics backend, no log aggregation and no alerting on log patterns. [[12_M1_Monitoring_Maintenance]] describes Prometheus metrics and SLA targets that remain unimplemented — do not read this workstream as closing that one.
2. **The status bar is TTY-only.** In a deployed environment progress reporting silently degrades to nothing. Acceptable for now, but a deployed pipeline run has no equivalent of the live "which gazette / which stage" indicator.
3. **`DB_ECHO=1` is the only way back to statement-level SQL** and it is all-or-nothing. Debugging one slow endpoint means re-enabling the firehose for every process.
4. **Poll collapsing is time-window based**, so a genuinely stuck poll loop looks the same as a healthy one until the 1s WARNING threshold trips. Watch this if the admin page ever polls a heavier endpoint.
5. **No test covers the unified format end-to-end.** Verification was by exercise and reading, not by assertion — so a future refactor of `console.py` has no failing test to stop it.

---

## 9. Cross-references

- **Phase-2 analysis:** `../PHASE2_INGEST_EXTRACTION_ANALYSIS.md`
- **Phase-2 gap-closure plan:** `../PHASE2_GAP_CLOSURE_PLAN.md`
- **Incidents found by reading these logs:** `../pipeline_stall_after_ingest/` · `../pipeline_stage_starvation/` · `../extraction_ws_heartbeat_disconnect/`
- **Quality probes and monitoring plan:** `../PHASE2_QUALITY_MONITORING_PLAN.md`
- **Production monitoring design (not delivered by this work):** [[12_M1_Monitoring_Maintenance]]
- **Setup and console usage:** [[07_SETUP_AND_USER_MANUAL]] · `make console-demo`
