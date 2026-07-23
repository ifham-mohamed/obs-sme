# Module 1 — Activity Log / Audit Coverage: Complete Analysis

> Cross-cutting analysis of **what the application logs to the Activity Log** (`audit_log` table → `/api/v1/admin/activity-log`) across every phase. Scope: which **state-changing actions** (POST/PUT/PATCH/DELETE + Celery/ML pipeline writes + SME survey actions) are captured, which relied only on the passive net, and the deliberate exclusion of GET reads. Grounded in the live codebase (`C:\Reasearch\xyz\enigmatrix-backend`: `middleware/audit_middleware.py`, `services/audit_service.py`, `models/audit_log.py`, every `api/v1/*` + `m1/api/*` router, `m1/tasks/*`).
>
> Generated 2026-07-22. Companion plan: [[24_ACTIVITY_LOG_GAP_CLOSURE_PLAN]]. Policy set this session: **the Activity Log records main actions only — mutations, not GET reads** (one sanctioned exception: sensitive-PII reads).

---

## 0. The one-paragraph truth

The app has **two logging layers into one table** (`audit_log`): (1) a **passive middleware** (`AuditMiddleware`) that writes an `http.request` catch-all row after every request, and (2) **explicit business events** (`audit_service.record(...)`) written by the service layer for named actions (`m1_regulation.create`, `survey_question.updated`, `auth.login.success`, …). Before this session the passive layer logged **every** request including GETs (reads inflated the log and buried the real actions). As of **Session 73 (2026-07-22)** the passive layer records **only POST/PUT/PATCH/DELETE**; GET/HEAD/OPTIONS are excluded. Sensitive-PII reads stay logged as a **deliberate exception** via `audit_service.record_read` (`user.pii.read` / `sme.pii.read`). Net effect: the Activity Log is now an *actions* log, and every state change is covered — explicitly where a named event exists, by the passive net otherwise.

---

## 1. The two write paths (how a row gets into `audit_log`)

| Path | Written by | Event type(s) | Commit | Covers |
|---|---|---|---|---|
| **Passive net** | `AuditMiddleware.dispatch` | `http.request` | own session, fire-and-forget after response | every un-instrumented mutation (POST/PUT/PATCH/DELETE) to `/api/…`, incl. errors (`success = status < 400`) |
| **Explicit business event** | `audit_service.record(...)` in a service/router | `<resource>.<action>` (e.g. `m1_regulation.verify`) | rides the caller's transaction (atomic with the mutation) | named, high-value actions with structured `old_value`/`new_value`/`data` |
| **PII read exception** | `audit_service.record_read(...)` | `*.pii.read` | commits itself (no surrounding write txn) | sensitive-data GET reads only (compliance access trail) |

`audit_log` columns: `event_type`, `table_name`, `record_id`/`record_key`, `user_name`, `old_value`/`new_value` (JSONB diffs), `http_method`, `endpoint_path`, `ip_address`, `user_agent`, `status_code`, `success`, `event_data_json`, `occurred_at`. The admin reader (`list_events` / `summary` / `distinct_event_types`) powers the Activity Log UI + dashboard.

---

## 2. Policy (set this session)

1. **Log main actions, not reads.** The passive net now filters on `request.method in {POST, PUT, PATCH, DELETE}`. GET/HEAD/OPTIONS produce **no** `http.request` row.
2. **One exception — sensitive-PII reads.** `record_read` still logs `user.pii.read` (admin lists the user table) and `sme.pii.read` (M2/M3 read an SME's answers). These are an intentional compliance access-trail, kept per the Phase-1 gap #7 decision, and are independent of the middleware.
3. **Every mutation is covered.** A mutation either has an explicit business event (preferred — richer) or falls through to the passive `http.request` net (guaranteed floor). Nothing that changes state is silent.
4. **Automated (Celery/ML) mutations** aren't HTTP, so the middleware never sees them; they log **selectively** as system events (see §5) — summarised per run, never per-row (volume).

---

## 3. Coverage by phase — human-triggered HTTP mutations

Legend: 🟢 explicit business event · 🟡 passive net only (works, but no named event) · 🔒 PII-read exception (GET, logged on purpose).

### Phase 1 — Foundation (auth / users / surveys / regulations CRUD)

| Action | Route | Coverage |
|---|---|---|
| Register / login (success+failure) / refresh / logout / logout-all | `POST /auth/*` | 🟢 `auth.register`, `auth.login.success|failure`, `auth.refresh`, `auth.logout`, `auth.logout_all` |
| Forgot / reset password (Session 72) | `POST /auth/forgot-password`, `/reset-password` | 🟢 `auth.password_reset.requested|completed` |
| Admin create / update / activate / deactivate / reset-pw / delete user | `POST/PATCH/DELETE /users/*` | 🟢 `user.admin_create`, `user.admin_update`, `user.activate|deactivate`, `user.password_reset`, `user.delete` |
| Admin lists users (PII) | `GET /users` | 🔒 `user.pii.read` |
| Regulation create / update / verify / bulk-verify / archive / restore / duplicate | `POST/PATCH/DELETE /m1/regulations/*` | 🟢 `m1_regulation.*` |
| Survey question create / update / archive / restore / duplicate / verify / bulk-verify / link / unlink / set-primary | `admin_survey_questions/*` | 🟢 `survey_question.*` |
| Admin survey create / update / archive / add-remove-question / reorder | `admin_surveys/*` | 🟢 `admin_survey.*` |
| Survey limits patch | `PATCH /admin/survey-limits` | 🟡 passive net |
| **SME survey — start / complete** | `POST /survey-sessions/start`, `/{id}/complete` | 🟢 **`survey.session.started|completed` (added Session 73)** |
| SME survey — answer | `POST /survey-sessions/{id}/answer` | 🟡 passive net (per-answer is too granular for a named event; the completed-session event summarises the run) |

### Phase 2 — Ingest + Extraction (admin pipeline / datasets / extraction)

| Action | Route | Coverage |
|---|---|---|
| Trigger / cancel extraction | `POST /admin/m1/extraction/trigger`, `/cancel/{task_id}` | 🟢 via `gazette_extraction` + `run_extraction` events |
| Retry / re-extract / re-preprocess / categorize / reconcile / migrate-raw | `POST /admin/m1/extraction/regulations/{id}/*`, `/reconcile`, `/migrate-raw-layout` | 🟡 mixed — service-logged where it writes; passive net otherwise |
| Extraction profile activate / deactivate | `POST /…/extraction-profiles/{id}/activate|deactivate` | 🟢 `m1_extraction_profile.*` (profile_service) |
| Run extraction / snapshot-range | `POST /…/extractions/run`, `/snapshot-range` | 🟢 `run_extraction` events |
| Dataset create / update / archive / restore / upload / seal / retire / promote | `POST/PATCH/DELETE /m1/datasets/*` | 🟢 `m1_dataset.*` (dataset_service / dataset_upload / snapshot_service) |
| Measurement run | `POST /m1/measurements/run` | 🟢 `run_measurement` events |
| Completeness verify / refetch-missing | `POST /…/completeness/verify`, `/refetch-missing` | 🟡 passive net |
| Pipeline health / metadata-review / classifier-review / sources | `GET …/health`, `/metadata-review`, `/sources`; `POST …/resolve`, `/override`; `PUT/PATCH /sources/{id}` | GET → not logged; 🟢 `m1_regulation.metadata_review.resolved`, `m1_regulation.classifier_review.override`, source upsert/patch audited |

### Phase 3 — Annotation + Classification

| Action | Route / trigger | Coverage |
|---|---|---|
| Classifier-review override | `POST /admin/m1/pipeline/classifier-review/{id}/override` | 🟢 `m1_regulation.classifier_review.override` |
| Classify gazette (auto) | Celery `classify_gazette` | system — see §5 (per-row status change; not individually audited) |

### Phase 4 — Schedulers + Alerts

| Action | Route / trigger | Coverage |
|---|---|---|
| SME marks alert read | `POST /m1/alerts/{id}/read` | 🟡 passive net |
| Watcher source upsert / patch | `PUT/PATCH /admin/m1/pipeline/sources/{id}` | 🟢 audited (admin_pipeline) |
| Portal/RSS watchers, alert dispatch, lag refresh | Celery (Beat) | system — see §5 |

### Phase 5 — Findings + Retraining

| Action | Trigger | Coverage |
|---|---|---|
| Retraining run + canary decision | Celery `run_retraining` | ledgered in `m1_retraining_runs` (dedicated table); a summary system event is a follow-up (see plan) |

### M2 / M3 instruments

| Action | Route | Coverage |
|---|---|---|
| M2 verify question (ground-truth) | `POST /m2/questions/{code}/verify` | 🟡 passive net |
| M3 submit compliance-history / behavioural | `POST /m3/compliance-history`, `/behavioural` | 🟡 passive net |
| M2 / M3 read an SME's answers (PII) | `GET /m2/…`, `/m3/…` | 🔒 `sme.pii.read` |

---

## 4. GET reads — now excluded (what stopped being logged)

Before Session 73 every `GET /api/v1/…` produced an `http.request` row: regulation lists, survey question lists, pipeline dashboards, alert feeds, dataset browsing, measurement reports, activity-log reads themselves (already skipped). These were **noise** — they buried the actual actions and inflated `audit_log`. They are now dropped at the middleware. The only reads that remain logged are the two `*.pii.read` exceptions (§2.2).

---

## 5. Automated (Celery / ML) mutations — a different class

The ~17 Beat/queue tasks (`extract_gazette`, `preprocess_gazette`, `classify_gazette`, `portal_watcher`, `rss_watcher`, `alert_dispatch`, `analytics`, `quality_probe`, `retraining`, `run_extraction`, `run_measurement`, dataset validate/retire, scrapers, reconcile) change DB state **without an HTTP request**, so the middleware never sees them. Logging every per-gazette status transition would flood the Activity Log. Current + intended approach: **summarise per run**, not per row.

| Task | Today | Intended |
|---|---|---|
| `quality_probe` | 🟢 `m1.quality_probe.degraded` on breach | keep |
| admin-triggered `run_extraction` / `run_measurement` | 🟢 run-level events | keep |
| `retraining` | ledgered in `m1_retraining_runs` | + one `m1.retraining.decided` summary event |
| `extract/preprocess/classify` (Beat) | 🟡 per-row status only (no audit) | optional per-run rollup (`m1.ingest_run.summary`) — see plan |
| `alert_dispatch` | 🟡 per-alert `m1_alerts.status` | optional `m1.alerts.dispatched` batch summary |
| watchers | 🟡 per-source health columns | optional `m1.watcher.run` summary on state change |

These are **follow-ups**, tracked in [[24_ACTIVITY_LOG_GAP_CLOSURE_PLAN]] §4 — the Beat cadence + per-run summarisation keeps the log readable.

---

## 6. What changed this session (2026-07-22, "Session 73")

1. **`AuditMiddleware`** now records only `POST/PUT/PATCH/DELETE` (`_MUTATING_METHODS`); GET/HEAD/OPTIONS excluded. Docstring rewritten to state the policy + the PII-read exception.
2. **`survey_session_service`** gained explicit `survey.session.started` (in `create_session`, after a flush for the id) and `survey.session.completed` (in `complete_session`) — the flagship SME action is now a named event, not just a passive row.
3. The PII-read exception (`record_read`) is **unchanged and retained** by design.

See [[24_ACTIVITY_LOG_GAP_CLOSURE_PLAN]] for the event-type taxonomy, the remaining per-feature explicit-event backlog, and the verification steps.

---

*Scope note: this is a cross-cutting concern spanning Phases 1–5; it is filed under `final/works/` alongside the numbered phase analyses. Related: [[09_PHASE1_FOUNDATION_ANALYSIS]] §3.3 (the audit foundation), [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/10_PHASE1_GAP_CLOSURE_PLAN]] (gap #7 read-audit), and every phase's admin surface.*
