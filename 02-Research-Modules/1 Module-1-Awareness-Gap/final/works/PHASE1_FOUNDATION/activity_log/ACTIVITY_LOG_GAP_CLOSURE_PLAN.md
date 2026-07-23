# Module 1 — Activity Log Gap-Closure Plan (mutations-only audit)

> Companion to [[23_ACTIVITY_LOG_ANALYSIS]]. Records the design, what was implemented in **Session 73 (2026-07-22)**, the event-type taxonomy, the remaining per-feature explicit-event backlog, and how to verify. Code in `C:\Reasearch\xyz\enigmatrix-backend` (+ frontend is unaffected — the Activity Log is a backend concern).

## Goal

The Activity Log must capture the **main actions** of the whole application — everything that changes state, from every feature and pipeline — and **exclude GET reads**. Where GET logging already existed, remove it. Keep the log readable (no per-row automation floods) and preserve one deliberate exception: sensitive-PII reads.

## Status summary

| Item | What | Status |
|---|---|---|
| A | Passive middleware logs GETs too | ✅ closed — restricted to POST/PUT/PATCH/DELETE |
| B | GET-read logging policy | ✅ decided — excluded, except the two `*.pii.read` compliance rows (kept) |
| C | Flagship SME action (survey) had no named event | ✅ closed — `survey.session.started|completed` |
| D | Un-instrumented HTTP mutations | ✅ covered by the passive net (floor); 📋 explicit events backlog below |
| E | Automated (Celery/ML) mutations | 📋 per-run summary events (backlog §4) |
| F | Event-type taxonomy inconsistent over time | 📋 documented convention below; migrate stragglers opportunistically |

---

## A — Middleware: log mutations only ✅ IMPLEMENTED

**Design.** The passive net is the *floor* guaranteeing no state change is silent; it should not carry reads. `AuditMiddleware.dispatch` now gates on `request.method in _MUTATING_METHODS = {POST, PUT, PATCH, DELETE}` **and** the existing path filter. GET/HEAD/OPTIONS produce no `http.request` row. Everything else (own-session, fire-and-forget, error-swallowing, `success = status < 400`, actor-from-bearer) is unchanged.

**Why not remove the middleware entirely?** Because it is the safety net: any mutation endpoint a developer forgets to instrument still lands a row. Removing it would make "un-instrumented mutation" == "silent mutation". Keeping it, scoped to mutations, is strictly safer than either extreme.

**File.** `app/middleware/audit_middleware.py` (registered in `main.py`).

## B — GET reads excluded, with one sanctioned exception ✅ DECIDED

All GET logging is dropped **except** sensitive-PII reads, which remain via `audit_service.record_read` and are *not* routed through the middleware:

- `user.pii.read` — admin lists the users table (`GET /users`).
- `sme.pii.read` — M2/M3 read an SME's answers (`GET /m2/…`, `/m3/…`).

These are a compliance access-trail (who looked at whose PII), retained per the Phase-1 gap #7 decision. They end in `.read` by convention so the Activity Log UI can filter/segregate them from actions. **No other reads are logged.** (This is the "keep as a special exception" answer — the read-audit stays, only the blanket GET logging goes.)

## C — Flagship SME action now a named event ✅ IMPLEMENTED

Survey participation is *the* main SME action of Module 1, yet the session lifecycle produced only passive `http.request` rows. Added, in `survey_session_service`:

- `survey.session.started` — in `create_session` (after a `flush()` to populate `session_id`), `data={survey_mode, recruitment_channel}`.
- `survey.session.completed` — in `complete_session`, `data={survey_mode, questions_answered}`.

Both ride the function's existing commit (atomic). **Per-answer** submission is deliberately left to the passive net — one row per answer would flood the log, and the completed-session event already summarises the run (`questions_answered`). Actor is the SME id string (SME endpoints resolve a `SMEProfile`, not a `User`).

**File.** `app/services/survey_session_service.py`.

---

## D — Explicit-event backlog for HTTP mutations (📋 — passive net covers them today)

Each of these currently lands a passive `http.request` row (so it **is** logged); promoting it to a named business event adds structured context and a filterable action type. Priority order:

1. **M3 self-reports** — `m3.compliance_history.submitted`, `m3.behavioural.submitted` (`app/api/v1/m3.py` submit handlers). SME-facing, research-relevant.
2. **Completeness ops** — `m1.completeness.verify`, `m1.completeness.refetch` (`app/m1/api/completeness.py`). Operator actions that change coverage.
3. **Gazette re-processing ops** — `m1_regulation.retry|re_extract|re_preprocess|categorize`, `m1.reconcile`, `m1.migrate_raw` (`app/m1/api/gazette_extraction.py`) where the service doesn't already log.
4. **M2 ground-truth verify** — `m2_question.verify` (`app/api/v1/m2.py`).
5. **Survey limits** — `admin.survey_limits.updated` (`app/api/v1/admin_survey_limits.py`).
6. **Alert read** — `m1_alert.read` (`app/m1/api/alerts.py`) — low value; the passive net is arguably enough (leave last, or never).

Pattern for each: call `await audit_service.record(db, event_type=…, actor=<user|sme>, table_name=…, record_id=…, data={…})` inside the service (rides the existing commit) or after the router's service call (`record` + `db.commit()`), and — for edits — pass `old_value`/`new_value` built with `app.utils.serialise.model_to_audit_dict`.

## E — Automated (Celery/ML) mutation summaries (📋 — keep the log readable)

Beat/queue tasks change state without HTTP; log them **per run**, not per row:

1. `m1.retraining.decided` — one row per `run_retraining` with `{trigger, action, prod_f1, candidate_f1, promoted}` (data already in `m1_retraining_runs`; mirror it into `audit_log` for the unified Activity Log).
2. `m1.ingest_run.summary` — a rollup at the end of a Beat scrape→extract→preprocess wave: counts of ingested/extracted/preprocessed/failed. Not per gazette.
3. `m1.alerts.dispatched` — one row per `dispatch_regulation_alerts` with `{email_sent, sms_sent, skipped, failed}`.
4. `m1.watcher.run` — per watcher pass, only when source health changes (new failure / recovery), reusing the `consecutive_failures` signal.

Guardrail: **never** audit a per-gazette status transition — that's what the pipeline tables (`m1_regulations.status`, `m1_extraction_runs`) are for; the Activity Log is for human-legible actions + run summaries.

## F — Event-type naming taxonomy (📋 — convention, migrate stragglers opportunistically)

`<resource>.<action>` lowercase, dot-separated; sub-scoped with a second dot where useful:

- Resource = the primary table/aggregate: `auth`, `user`, `m1_regulation`, `survey_question`, `admin_survey`, `m1_dataset`, `m1_extraction_profile`, `survey_session`, `m1_alert`, `m3`, `m2_question`, `m1` (pipeline/system).
- Action = the verb: `create`, `update`, `verify`, `archive`, `restore`, `duplicate`, `delete`, `activate`, `deactivate`, `override`, `resolve`, `started`, `completed`, `submitted`, `read`.
- Reads end in `.read` (the only GET-sourced events). System/automation events use the `m1.<subject>.<verb>` shape (`m1.quality_probe.degraded`, `m1.retraining.decided`).

Existing events already follow this closely; new events (this session + the backlog) conform. No migration of historical rows is needed — `distinct_event_types` simply surfaces both.

---

## Verification (deferred to user — sandbox lacks Postgres/Redis)

1. `cd enigmatrix-backend && python -m compileall app` (imports/syntax).
2. Middleware: hit a `GET /api/v1/m1/regulations` → **no** new `http.request` row in `audit_log`; hit a `POST`/`PATCH`/`DELETE` on any endpoint → exactly one `http.request` row (if un-instrumented) or a business-event row (if instrumented). `HEAD`/`OPTIONS` → none.
3. PII exception intact: `GET /users` as admin → a `user.pii.read` row still appears.
4. Survey events: start a survey (`POST /survey-sessions/start`) → `survey.session.started`; finish it → `survey.session.completed`; both carry `data`.
5. Activity-log reader unaffected: `/api/v1/admin/activity-log` still lists + filters; `distinct_event_types` shows the new types; `summary` action-breakdown no longer dominated by GET `http.request`.
6. `uv run pytest -q` (the auth/survey integration tests still pass — they assert business behaviour, not audit rows).
7. `graphify update .`.

## Follow-ups

- Work the §D backlog (M3 + completeness first).
- Add the §E per-run summary events when the pipeline runs autonomously (ties to [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/21_PHASE4_GAP_CLOSURE_PLAN]] activation + [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/19_PHASE3_GAP_CLOSURE_PLAN]] Stage E).
- Optional: a partial index on `audit_log(event_type)` and a `pg_trgm` GIN index on `event_data_json::text` once the table grows (the reader's free-text `q` is a seq-scan today).
- Frontend Activity Log: add an "actions only / include PII reads" toggle now that reads are a clean, separate class.
