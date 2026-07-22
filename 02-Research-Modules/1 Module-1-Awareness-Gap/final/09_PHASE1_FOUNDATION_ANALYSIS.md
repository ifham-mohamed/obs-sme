# Module 1 — Phase 1 (Foundation): Complete Analysis

> Single-file analysis of **Phase 1 — Foundation** *only*: what the phase is, which technologies it actually uses, what has been built (auth / RBAC / audit / admin regulation CRUD / survey engine / seeds), how it was developed, and what approaches were missed. Grounded in the live codebase (`C:\Reasearch\xyz`, backend now reorganized under `app/m1/`) and the vault (`E:\Obsidian\sme`, `FEATURES.md` F-01→F-40, `16_M1_Development_Roadmap.md`).
>
> Generated 2026-07-18; **reviewed 2026-07-21** (no Phase-1 code changed in the Session 64–71 gap-closure work — that work is Phase 2–4; cross-references and the audit-foundation note below were refreshed). Phase 1 is marked **✅ DONE** in the roadmap — this document verifies that against the code and records the residual gaps.

---

## 1. What Phase 1 is (scope, per the roadmap)

Per `16_M1_Development_Roadmap.md §"Phase 1 — Foundation (✅ DONE)"`, Phase 1 is the **platform every later module stands on** — it is deliberately *module-agnostic*. You inherit four things:

1. **Admin CRUD** — regulation manual entry / edit / verify / archive.
2. **Audit-log writes** on every regulation mutation.
3. **Unified survey engine** — one session crosses M1/M2/M3 questions, branching per `next_question_rules`.
4. **Seed data** — 5 demo regulations + the awareness instrument.

Underneath those four sits the thing the roadmap treats as assumed-present: **authentication + RBAC + the FastAPI/Next.js scaffold**. This is the "sign-in and shared shell" layer — in the reorg it was explicitly kept *shared* (not moved into `app/m1/`), because M2/M3/M4 depend on it too. So for this analysis, Phase 1 = **auth + platform scaffold + the four inherited capabilities above**.

The roadmap also tags two end-user workflows as shipped in Phase 1: **A3 — Expert verification** (admin) and **S2 — Awareness survey participation** (SME).

---

## 2. Technologies actually used in Phase 1

The full project stack spans ingestion, ML, and alerting — but **Phase 1 exercises only the web-application subset**. This distinction matters: most of the "heavy" stack is dormant until Phase 2+.

### Used in Phase 1

| Technology | Layer | Phase-1 role |
|---|---|---|
| **FastAPI** | Backend | REST API — `/auth/*`, `/users/*`, `/m1/regulations/*`, `/surveys/*` |
| **SQLAlchemy 2.0 async** | Backend | ORM (`User`, `SMEProfile`, `M1Regulation`, `AuditLog`, `SurveyQuestion/Session/Response`) |
| **Pydantic v2** | Backend | request/response schemas + `Settings` config |
| **Alembic** | Backend | `202605080001_initial_schema` + `202605090001_module23_schema` |
| **PostgreSQL** | Storage | structured tables (no materialized views yet — those arrive Phase 4) |
| **python-jose (HS256)** | Auth | JWT access + refresh encode/decode (`core/security.py`) |
| **passlib + bcrypt** | Auth | password hashing (`CryptContext(schemes=["bcrypt"])`) |
| **slowapi** | Auth | inbound rate-limit on `/auth/login` + `/auth/register` |
| **Next.js 14 (App Router, TS)** | Frontend | route groups `(auth)` / `(app)` / `(admin)`, server layouts |
| **shadcn/ui + Tailwind** | Frontend | login/register/regulation/survey UIs |
| **next-intl** | Frontend | EN/SI/TA trilingual shell |
| **pytest + httpx + testcontainers** | QA | `test_survey_flow.py` register→login→submit + 501-stub assertions |
| **Railway / Vercel / Aiven** | Deploy | production hosting of exactly this foundation |

### NOT yet used in Phase 1 (dormant until Phase 2–5)

Celery + Redis + Beat, Scrapy, PyMuPDF/pdfplumber/pypdfium2/Tesseract/Surya, fastText + Wijesekara, XLM-RoBERTa + LoRA + PyTorch, ONNX Runtime, scikit-learn/scipy, httpx watchers, feedparser, SendGrid/Twilio, Label Studio, Jupyter/pandas. None of these are on the Phase-1 execution path — if you are evaluating "what did Phase 1 require," it is a standard authenticated CRUD web app, not the ML pipeline.

---

## 3. Feature-by-feature: planned vs. built

Legend: 🟢 built & verified · 🟡 built, thin · 🔲 deferred by design.

### 3.1 Authentication & session (sign-in) — 🟢

**Backend.** `core/security.py` implements bcrypt hashing + HS256 JWT with separate **access** (15 min) and **refresh** (7 day) tokens (`JWT_ACCESS_EXPIRE_MINUTES` / `JWT_REFRESH_EXPIRE_DAYS` in `settings.py`). `services/auth_service.py` exposes `register`, `login`, `refresh`, plus admin user-management (`admin_create_user`, `update_user`, `set_active`, `reset_password`, `delete_user`). Router `api/v1/auth.py` = `POST /auth/register`, `/auth/login`, `/auth/refresh`. Schemas enforce `password: Field(min_length=8)`. (F-10, F-11, F-13, F-16.)

**Frontend.** `(auth)/login` + `(auth)/register` pages (zod + react-hook-form + shadcn). Login posts to the backend, then calls a Next.js route handler (`/api/auth/establish`) that sets **HTTP-only cookies** (`access`, `refresh`); `/api/auth/logout` clears them. `middleware.ts` does a **presence-only** fast-path check on protected prefixes (`/dashboard /surveys /regulations /qa /verify /risk /admin`) and redirects unauthenticated users to `/login`. (F-25, F-28, F-30, F-31.)

**Guardrails already present:** last-active-admin cannot be deleted/deactivated (`_count_active_admins`); auth events are audited (`auth.register`, `auth.login.success/failure`, `auth.refresh`); login/register are rate-limited.

### 3.2 RBAC & authorization — 🟢

Three roles on `users.role` (server_default `sme`): **sme / annotator / admin**. Dependency guards in `deps.py`: `get_current_user` (decodes access token), `require_admin` (403 unless `admin`), `require_annotator` (admin *or* annotator), `get_current_sme`. Frontend mirrors this: `(app)` layout calls `requireUser()`, `(admin)` layout calls `requireRole('admin')` server-side (`lib/auth/{session,roles}.ts`). Verified by an integration test asserting SME → 403 on an admin endpoint (F-12, F-26, F-31).

### 3.3 Audit logging — 🟢 (notably strong)

`AuditLog` (`audit_log` table) captures far more than the roadmap requires: `event_type`, `table_name`, `record_id`/`record_key`, `user_name`, **`old_value`/`new_value` JSONB diffs**, plus full HTTP context (`http_method`, `endpoint_path`, `ip_address`, `user_agent`, `status_code`, `success`). `services/audit_service.record()` is called by every mutating service (auth + regulation CRUD). `list_events()` backs the admin Activity-Log view. This is production-grade and already exceeds Phase-1 scope (F-08, F-16). **Foundation leverage (Session 64–71):** the later data-quality controls reuse this exact table with zero new frontend — the metadata-review resolve (`m1_regulation.metadata_review.resolved`), the classifier-review override (`m1_regulation.classifier_review.override`), the source-registry edits, and the monthly quality-probe degradation alert (`m1.quality_probe.degraded`, actor `system:quality_probe`) all write `audit_log` rows that surface immediately in the Activity Log. The Phase-1 audit spine is what makes those controls shippable as backend-only slices.

### 3.4 Admin regulation CRUD + expert-verification gate — 🟢

`app/m1/api/regulations.py` (behind `require_admin`) + `app/m1/services/regulation_service.py` implement the **full lifecycle**, richer than the roadmap's "entry/edit/verify/archive":

- `GET ""` (paginated list, `include_archived`), `POST ""` (create), `GET/PATCH /{id}`, `POST /{id}/verify`, `GET /{id}/public` (SME read).
- Session-10 (F-97) extras: `POST /bulk-verify`, `DELETE /{id}` (archive), `POST /{id}/restore`, `POST /{id}/duplicate`.

The `M1Regulation` model is **trilingual** (`title/summary/real_world_example _en/_si/_ta`), carries the **expert-verification gate** (`expert_verified`, `_by`, `_at` — workflow A3), classification fields (`domain_code`, `change_category`, `severity_level 1–5`, `is_sme_relevant`, `penalty_range_lkr`), and a `status` pipeline column that Phase 1 seeds/authors at the manual end while leaving the `ingested→extracted→…` progression for Phase 2. Frontend authoring UI: `(admin)/admin/regulations/{page,new,[id]/authoring}`.

### 3.5 Unified survey engine + branching + auto-scoring — 🟢

One `SurveySession` spans M1/M2/M3. `survey_question_service.py` resolves the next question from each row's **`next_question_rules`** (`start_flow`, `_next_in_section`, `_resolve_rule`, `_answer_matches`, scope helpers `_sector_visible` / `_in_regulation_scope` / `_skip_answered`). `survey_session_service.py` handles `create_session`, `record_answer`, `complete_session`, submission caps (`cap_reached`). **Auto-scoring is intentionally M2-only** (`_score_m2`; returns `None` for M1/M3 — awareness/vulnerability answers are descriptive, not right/wrong). Regulation-scoped flows fall back to a global branching root when a regulation has no in-scope root. (F-15, F-33, F-35–F-37.)

### 3.6 Seed data — 🟢

`seed_dev.py` (idempotent) creates **admin / annotator / sample SME** (`admin@enigmatrix.lk` etc.). `seed_regulations.py` loads the 5 demo regulations. `seed_awareness_questions.py` loads the awareness instrument. **Note on "Q1–Q8":** the roadmap's "awareness Q1–Q8" refers to the *per-regulation conditional* awareness pattern; the standalone survey bank is **12 baseline questions** (`is_baseline=True`) covering all six question kinds (single / multi / likert / date / numeric / short_text). Both facts are true — don't let the "8 vs 12" wording read as a contradiction. (F-18, F-33.)

### 3.7 Frontend foundation — 🟢

Next.js 14 App Router with `(auth)`/`(app)`/`(admin)` route groups, `lib/api/client.ts` (`ApiError` + bearer plumbing), cookie route handlers, guarded layouts + middleware fast-path, trilingual shell, and "Coming soon" stubs for `/regulations /qa /verify /risk` that name the `BUILD_NN` reference where the real feature lands (F-19, F-25, F-31, F-39).

---

## 4. How it was developed (stages)

Phase 1 was built bottom-up across the early BUILD plans and feature IDs:

1. **Scaffold & infra** — `BUILD_02` (monorepo), `BUILD_04 §2` (docker-compose + `infra/postgres/init.sql`). F-01→F-04.
2. **Backend spine** — `BUILD_03` (FastAPI app, settings, deps) + `BUILD_04` (SQLAlchemy async, models, Alembic). F-05→F-09.
3. **Auth & RBAC** — `BUILD_06` (bcrypt+JWT, auth service/router, RBAC deps, rate-limit, auth audit). F-10→F-16.
4. **Domain surface** — users router, surveys router, 501 module stubs, `seed_dev`. F-14→F-18.
5. **Frontend** — `BUILD_05`/`BUILD_06` (Next.js, API client, session/roles, login/register, cookie handlers, guarded layouts, awareness bank, survey pages, admin list, coming-soon stubs) + the register→login→submit integration test. F-19→F-40.

Regulation CRUD then hardened through Session 10 (F-97: archive/restore/duplicate/bulk-verify) and the expert-verification gate.

---

## 5. Verification present today

- `test_security.py` — access/refresh JWT round-trip.
- Integration `test_survey_flow.py` — full register/login/submit/admin-list + asserts the 501 stubs.
- RBAC integration test — SME → 403 on admin route.
- `python -m compileall app` clean; models registered in metadata; `alembic upgrade head` succeeds on a fresh DB.

---

## 6. Gaps & missed approaches (the analytical part)

Phase 1 is functionally complete, but several **foundation-level hardening approaches were skipped** — cheap to note now, increasingly expensive later:

> **Session 72 update (2026-07-21)** — the code-addressable foundation gaps are now closed; see [[PHASE1_GAP_CLOSURE_PLAN]] for the full per-gap plan + verification. Two items below (#1, #7) turned out to be **already fixed in code** — this list had gone stale.
>
> | # | Gap | Status |
> |---|---|---|
> | 1 | Refresh rotation / revocation / logout-all | ✅ already in code (`refresh_tokens`, rotation + reuse-detection, `/auth/logout-all`, `token_version`) |
> | 2 | Self-service password reset | ✅ implemented — hashed single-use tokens, `/auth/forgot-password` + `/auth/reset-password`, mail-optional stub (migration `202607210007`) |
> | 5 | Weak password policy | ✅ implemented — `core/password_policy.py`: length≥10, 3-of-4 classes, denylist, email-part guard, optional HIBP |
> | 6 | Edge JWT presence-only | ✅ implemented — `middleware.ts` now checks `exp` + clears stale cookies |
> | 7 | Reads not audited | ✅ already in code — `audit_service.record_read` on the PII list (single-record PII reads still open) |
> | 10 | `next_question_rules` untyped | ✅ implemented — structural write-time validator (`schemas/survey_rules.py`), complements the semantic soft-warns |
> | 11 | Auth paths thinly tested | ✅ policy + rule-validator unit tests; fixed a stale refresh-token test; integration cases specced |
> | 3 | Email verification | 📋 deferred (needs mail infra; reuses #2's provider) |
> | 4 | MFA / lockout | 📋 not scoped |
> | 8 / 9 | Hand-entered summaries / M1-M3 unscored | 📋 by design |
>
> The numbered items below are the *original* gap descriptions, kept for context.

**Auth / session security**
1. **No refresh-token rotation or server-side revocation.** Tokens are stateless HS256; `logout` only clears the browser cookie — a leaked/refresh token stays valid until natural expiry. No jti blocklist, no rotation-on-refresh, no "log out all sessions."
2. **No self-service password reset / forgot-password.** Only *admin*-initiated `POST /users/{id}/reset-password` exists. A real SME who forgets their password has no path.
3. **No email verification on register** — `register` activates immediately; email ownership is unproven.
4. **No MFA/2FA**, and no account-lockout/backoff after repeated failed logins (only coarse slowapi rate-limiting).
5. **Weak password policy** — `min_length=8` only; no complexity, no breached-password (HIBP) check. Seed uses `admin12345`; ensure it's rotated before any real deployment.
6. **Edge-path JWT check is presence-only** in `middleware.ts` (by design, real check is server-side) — acceptable, but means a malformed/expired cookie still passes the edge and relies entirely on the layout check.

**Audit / data**
7. **Mutations are audited; reads are not.** Fine for now, but sensitive-record reads (SME PII) have no trail. (Note: Session 64–71 added *system-event* audit rows — quality-probe degradation, review-queue resolves/overrides — but ordinary SME-PII reads still have no trail; the gap stands.)
8. **Regulation summaries are hand-entered** in Phase 1 — the auto-summarize path is deferred (Phase 4/5), so demo data quality depends on the author.

**Survey engine**
9. **M1/M3 answers are unscored by design** — correct, but there is no analytics/aggregation over awareness responses yet (that's Phase 5 findings). Worth stating explicitly so it's not mistaken for a bug.
10. **`next_question_rules` branching is powerful but untyped** (JSON on the row) — a malformed rule is only caught at runtime by `_normalise_m3_mapping_or_raise`. A schema/validator + admin-time lint would prevent bad branches reaching production.

**Testing**
11. Auth **failure/expiry paths are thinly tested** — expired-access, refresh-rotation, and last-admin-guard cases would benefit from explicit unit tests.

None of these block Phase 2. **As of Session 72 (2026-07-21), items #2/#5/#6/#10/#11 are closed and #1/#7 were already covered in code**, so the platform is materially safer for real SME users. Remaining before a public launch: email verification (#3), MFA/lockout (#4), and rotating the seed passwords. See [[PHASE1_GAP_CLOSURE_PLAN]].

---

## 7. Traceability (feature → code → doc → feature-id)

| Capability | Backend path | Frontend path | Doc | F-id |
|---|---|---|---|---|
| JWT + bcrypt | `core/security.py` | — | `BUILD_06 §2` | F-10 |
| Auth service + router | `services/auth_service.py`, `api/v1/auth.py` | `(auth)/login`, `/register` | `BUILD_06 §3–5` | F-11, F-28 |
| RBAC deps | `deps.py` | `lib/auth/{session,roles}.ts`, guarded layouts | `BUILD_06 §6` | F-12, F-26, F-31 |
| Cookie session | — | `/api/auth/{establish,token,logout}`, `middleware.ts` | `BUILD_06 §8` | F-30, F-31 |
| Audit log | `services/audit_service.py`, `models/audit_log.py` | `/admin/activity-log` | `BUILD_06 §10` | F-08, F-16 |
| Regulation CRUD + verify | `app/m1/api/regulations.py`, `app/m1/services/regulation_service.py`, `models/regulation.py` | `(admin)/admin/regulations/*` | `14_M1_3` | F-97 |
| Survey engine | `services/survey_{service,session_service,question_service}.py`, `models/survey*.py` | `(app)/surveys/*` | `14_M1_6` | F-15, F-33–F-37 |
| Seeds | `scripts/seed_{dev,regulations,awareness_questions}.py` | — | `BUILD_04 §8` | F-18 |


---

## 8. Data flow — how data travels through the stages (Phase 1)

This section traces each Phase-1 feature end-to-end: **input → frontend page → API client → backend route → service → database → response → UI**. In Phase 1 the *inputs are human-entered or seeded* — there is no file ingestion yet (gazette-PDF input begins in Phase 2).

### 8.0 Inputs / data sources in Phase 1

| Input | Where it enters | Becomes |
|---|---|---|
| Admin form (regulation authoring) | `(admin)/admin/regulations/new` | rows in `m1_regulations` (+ `m1_regulation_sectors`) |
| SME survey answers | `(app)/surveys/awareness` | rows in `survey_sessions` + `survey_responses` |
| Login/register credentials | `(auth)/login`, `(auth)/register` | rows in `users`, JWTs, `audit_log` |
| Seed scripts (code-defined, not uploaded files) | `scripts/seed_{dev,regulations,awareness_questions}.py` | demo `users`, 5 `m1_regulations`, 12 `survey_questions` |

**No PDF / gazette file input in Phase 1** — that path (`storage/m1/raw/*.pdf` → Scrapy → Celery) is Phase 2.

### 8.1 The transport layer (how every request navigates)

All browser→server traffic follows one spine:

```
React page/component
  → lib/api/<feature>.ts        (typed wrapper, e.g. AuthApi.login)
    → lib/api/client.ts          (fetch to NEXT_PUBLIC_API_BASE_URL, adds Authorization: Bearer <access>)
      → FastAPI  /api/v1/...      (deps: get_current_user / require_admin / require_annotator)
        → app/.../services/*.py   (business logic)
          → PostgreSQL (SQLAlchemy 2.0 async)   + audit_service.record() → audit_log
        ← Pydantic response schema
      ← JSON
    ← typed object / ApiError
  → UI state update / redirect
```

Two request styles coexist: **Server Components** read the `access` cookie and fetch during render (guarded layouts, admin lists); **Client Components** obtain the token from `/api/auth/token` and call the same API client. The `access`/`refresh` tokens live in **HTTP-only cookies**, minted by the backend and written by the Next.js `/api/auth/establish` route handler.

### 8.2 Sign-in / registration flow

```
[user types email+password on /login]
  → AuthApi.login()  → api.post("/api/v1/auth/login")            (client → backend, no token yet)
    → api/v1/auth.py:login → services/auth_service.login
        → SELECT users WHERE email=?  → bcrypt verify (core/security.py)
        → mint access(15m)+refresh(7d) JWT (HS256)
        → audit_service.record("auth.login.success|failure") → audit_log
      ← TokenPair {access_token, refresh_token}
  → browser POSTs tokens to /api/auth/establish  (Next route handler)
      → sets HTTP-only cookies access + refresh; decodes role from JWT
  → redirect to `next` (/dashboard or /admin)
      → (app)/(admin) server layout calls requireUser()/requireRole()
          → reads cookie → GET /api/v1/users/me → resolves User → allow | redirect
```

Every later authenticated call re-uses the `access` cookie → `Authorization: Bearer` → `deps.get_current_user` (decode) → role guard. Logout = `/api/auth/logout` clears the cookies (token remains valid until expiry — see gap #1).

### 8.3 Admin regulation CRUD flow (feature: `/admin/regulations`)

```
[admin fills authoring form at /admin/regulations/new]
  → regulations client → api.post("/api/v1/m1/regulations", body, token)
    → app/m1/api/regulations.py:create_regulation   [Depends(require_admin)]
        → app/m1/services/regulation_service.create_regulation
            → INSERT m1_regulations (trilingual fields, status='ingested', expert_verified=false)
            → INSERT m1_regulation_sectors (sector links)
            → audit_service.record("m1_regulation.create", new_value=JSONB) → audit_log
      ← RegulationAdminOut
  → table at /admin/regulations refreshes (regulations-client.tsx)

Verify   : POST /{id}/verify  → expert_verified=true, _by, _at         + audit
Edit     : PATCH /{id}        → diff old→new                            + audit(old_value,new_value)
Archive  : DELETE /{id}       → is_active=false (soft delete)           + audit
Restore  : POST /{id}/restore → is_active=true                          + audit
Bulk     : POST /bulk-verify  → many rows in one call                   + audit
SME read : GET /{id}/public   → RegulationPublicOut (verified rows only)
```

So a single regulation navigates **admin form → `m1_regulations` row → verification gate → SME-visible public projection**, with an `audit_log` row written at every mutation (mutation-side only; reads are not audited — gap #7).

### 8.4 Survey participation flow (feature: `/surveys/awareness`)

```
[SME opens /surveys/awareness]
  → create session → survey_session_service.create_session → INSERT survey_sessions
  → survey_question_service.start_flow → first in-scope branching-root question
       (question chosen from survey_questions.next_question_rules; scope = sector × regulation)
  loop per answer:
    → record_answer → _score_m2 (M2 only; None for M1/M3)
        → INSERT survey_responses (session_id, question, answer_text, is_correct?)
    → next question resolved from next_question_rules
  → complete_session → survey_sessions.completed_at set
  → redirect /surveys/awareness/thank-you

[admin] /admin/surveys/awareness → GET responses → reads survey_responses (grouped by sme, submitted_at)
```

The awareness answers land in `survey_responses` **unscored by design** (awareness is descriptive, not right/wrong); only M2 knowledge answers get `is_correct`. Aggregation/analytics over these responses is Phase 5, not Phase 1.

### 8.5 Where each stage lives (quick map)

| Stage | Sign-in | Regulation CRUD | Survey |
|---|---|---|---|
| Frontend page/feature | `(auth)/login`,`/register` | `(admin)/admin/regulations/*` | `(app)/surveys/awareness/*` |
| API client | `lib/api/auth.ts` | `lib/api/*regulations*` | `lib/api/*surveys*` |
| Backend route | `api/v1/auth.py` | `app/m1/api/regulations.py` | `api/v1/survey_sessions.py` |
| Service | `services/auth_service.py` | `app/m1/services/regulation_service.py` | `services/survey_{session,question}_service.py` |
| DB tables | `users`, `audit_log` | `m1_regulations`,`m1_regulation_sectors`,`audit_log` | `survey_sessions`,`survey_responses`,`survey_questions` |
| Back to UI | cookies + redirect | `RegulationAdminOut`/`Public` | next-question / thank-you |

---

*Scope note: this document covers Phase 1 only. Phase 2 (ingest + extraction) → `PHASE2_INGEST_EXTRACTION_ANALYSIS.md`; Phase 3 (annotation + XLM-R/LoRA classification) → `PHASE3_ANNOTATION_CLASSIFICATION_ANALYSIS.md`; Phase 4 (schedulers + alerts + lag) → `PHASE4_SCHEDULERS_ALERTS_ANALYSIS.md`; Phase 5 (research findings) → `PHASE5_RESEARCH_FINDINGS_ANALYSIS.md`. The Scrapy/Celery pipeline, the PDF/OCR chain, and the XLM-R classifier are out of scope here.*
