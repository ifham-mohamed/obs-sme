# 03 — Architecture

> **Goal:** know enough about how the pieces fit together that the rest of the SETUP guides are obvious. Not a substitute for [`docs/research/07_System_Architecture.md`](../research/07_System_Architecture.md) (research-flavoured) or [`docs/BUILD_PLAN/BUILD_02_Folder_Structure.md`](../../infra/BUILD_PLAN/BUILD_02_Folder_Structure.md) (long-form folder spec) — links into both at the bottom.

---

## 1. Runtime topology (what's actually running)

```
                          ┌────────────────────────────────────────┐
                          │            Browser  (any OS)            │
                          │   localhost:3000  +  EN / SI / TA       │
                          └───────────────┬────────────────────────┘
                                          │   HTTP/JSON, HTTP-only cookies
                                          ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │                         Next.js 14 (App Router)                       │
   │   middleware.ts ── fast-path redirect if `access` cookie is missing   │
   │   server components in app/(app), app/(admin)                         │
   │     └─ requireUser() / requireRole("admin")  → calls /api/v1/users/me │
   │   client components — react-hook-form + zod + TanStack Query         │
   │   API client (lib/api/client.ts) sets Authorization: Bearer <jwt>     │
   └───────────────────────────────────┬──────────────────────────────────┘
                                       │   http://localhost:8000/api/v1
                                       ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │                          FastAPI 0.115  (uvicorn)                     │
   │   CORSMiddleware  →  SlowAPIMiddleware  →  router(/api/v1)            │
   │     v1.auth          — register / login / refresh    (rate-limited)   │
   │     v1.users         — me / list / create / patch /                   │
   │                        activate / deactivate / reset-password / del.  │
   │     v1.surveys       — submit / responses                             │
   │     v1.survey-flow   — start / answer  (legacy regulation-scoped flow) │
   │     v1.survey-sessions — start / next-question / answer / complete /  │
   │                          my-history / {id}  (session-based flow)       │
   │     v1.admin.survey-questions — question CRUD + M:N regulation linkage │
   │     v1.admin.survey-limits — singleton read/write (require_admin)      │
   │     v1.m1.regulations — list / get / create / patch / verify /        │
   │                         bulk-verify / archive / restore / duplicate   │
   │                         + /{id}/public  (SME-side regulation card)    │
   │     v1.m2            — questions / score                              │
   │     v1.m3            — risk-signals                                   │
   │     v1.admin/activity-log  — read-only audit-trail view (require_admin)│
   │     v1.qa / risk / verify   — 501 stubs (BUILDs 08/09/10)             │
   │   services layer (auth, survey, survey_question, survey_flow,         │
   │     m1_regulation, m2, m3, audit)  — business logic; every mutation   │
   │     writes an audit_log row via audit_service.record(...)             │
   │   models layer    (User, SMEProfile, SurveyResponse, AuditLog,        │
   │     SurveyQuestion, SurveyQuestionRegulation, M1Regulation,           │
   │     M1RegulationSector, M2KnowledgeScore, M3ComplianceHistory,        │
   │     M3BehaviouralSignals, RegulatoryDomain, Sector,                   │
   │     SurveySession, SurveyLimits)                                      │
   │   (content + identity models carry created_by/updated_by via          │
   │     AuthorshipMixin — denormalised acting-user email)                 │
   └─────────────┬─────────────────────────────────┬─────────────────────┘
                 │ asyncpg                          │ structlog → stdout
                 ▼                                  ▼
   ┌────────────────────────────┐   ┌──────────────────────────────┐
   │ PostgreSQL 16 (alpine)     │   │ stdout (dev) / JSON (prod)   │
   │   pgcrypto, uuid-ossp,     │   │   includes correlation_id     │
   │   pg_trgm, unaccent        │   └──────────────────────────────┘
   │   ≥ 13 tables (4 core +    │
   │   Session-5 M2/M3 +        │
   │   Session-6 m1_regulations │
   │   + Session-16/17 session  │
   │   + limits); see §5 ERD    │
   └────────────────────────────┘
                 ▲
                 │ (wired but unused in MVP)
   ┌────────────────────────────┐
   │ ChromaDB 0.5.5 :8001       │   activated when Module 2 (RAG) ships
   └────────────────────────────┘
```

---

## 2. Request lifecycle — "SME submits the awareness survey"

This is what happens when a logged-in SME clicks **Submit** on `/surveys/awareness`. Files are listed in the order they execute.

| Step | What happens | Where it happens |
|------|--------------|------------------|
| 1 | Browser triggers `<form onSubmit>` | [`frontend/components/forms/survey-form.tsx`](../../frontend/components/forms/survey-form.tsx) |
| 2 | `valuesToAnswers()` serialises 12 form values into `SurveyAnswer[]` | same file |
| 3 | `SurveysApi.submit("awareness", answers, accessToken)` | [`frontend/lib/api/surveys.ts`](../../frontend/lib/api/surveys.ts) |
| 4 | `api.post()` adds `Authorization: Bearer <jwt>` header, fetches `POST http://localhost:8000/api/v1/surveys/awareness/submit` | [`frontend/lib/api/client.ts`](../../frontend/lib/api/client.ts) |
| 5 | `CORSMiddleware` validates origin against `CORS_ORIGINS` | [`backend/app/main.py`](../../backend/app/main.py) |
| 6 | Router matches the path. `submit()` declared with `Depends(get_current_user)` | [`backend/app/api/v1/surveys.py`](../../backend/app/api/v1/surveys.py) |
| 7 | `get_current_user()` decodes the JWT, fetches the `User` row | [`backend/app/deps.py`](../../backend/app/deps.py) → [`backend/app/core/security.py`](../../backend/app/core/security.py) |
| 8 | `survey_service.submit()` validates the instrument, resolves `sme_id`, validates each answer has exactly one of {text, numeric, date} set | [`backend/app/services/survey_service.py`](../../backend/app/services/survey_service.py) |
| 9 | One `INSERT … RETURNING` per answer inside a single transaction; returns count + timestamp | same file (uses `db.add_all` + `await db.commit()`) |
| 10 | Pydantic `SurveySubmitOut` serialises the response | [`backend/app/schemas/survey.py`](../../backend/app/schemas/survey.py) |
| 11 | Frontend `router.push("/surveys/awareness/thank-you")` fires | [`frontend/components/forms/survey-form.tsx`](../../frontend/components/forms/survey-form.tsx) |
| 12 | Server-component `ThankYouPage` renders | [`frontend/app/(app)/surveys/awareness/thank-you/page.tsx`](../../frontend/app/(app)/surveys/awareness/thank-you/page.tsx) |

Every step that involves a token uses an HTTP-only cookie set on a *separate* round-trip (`/api/auth/establish`) — see [`07_Auth_and_Roles.md`](07_Auth_and_Roles.md).

> **Session-based flow (canonical path post-Session-16).** The per-instrument `/surveys/awareness` page is still live for testing. The canonical SME entry is `/surveys/module/[id]` (or `/surveys/unified`), which uses `SurveyLauncher` + `SurveyWizard`. This calls `POST /api/v1/survey-sessions/start` once, then loops `GET /{id}/next-question` → `POST /{id}/answer` until `POST /{id}/complete`. Each run creates a `survey_sessions` row; caps (10 per module, 20 unified) are enforced server-side. The old `GET/POST /api/v1/survey-flow/{start,answer}` endpoints are preserved for regulation-scoped flows at `/surveys/regulation/[id]`. See [`13_Unified_Survey_Configuration.md`](13_Unified_Survey_Configuration.md) for the full session loop and [`11_Survey_System.md`](11_Survey_System.md) §10–§11 for the branching rules.

---

## 3. Layered architecture (backend)

```
       app/api/v1/<resource>.py        ← thin: parse, authorize, call service
              │
              ▼
       app/services/<resource>_service.py   ← business logic, transactions
              │
              ▼
       app/models/<entity>.py          ← SQLAlchemy 2.0 ORM, no logic
              │
              ▼
       PostgreSQL  via  app/db/session.py  (async engine + SessionLocal)
```

Cross-cutting:

- [`app/deps.py`](../../backend/app/deps.py) — FastAPI dependencies (`get_db`, `get_current_user`, `require_admin`, `require_annotator`).
- [`app/core/security.py`](../../backend/app/core/security.py) — bcrypt + HS256 JWT helpers.
- [`app/core/rate_limit.py`](../../backend/app/core/rate_limit.py) — slowapi inbound limiter.
- [`app/exceptions.py`](../../backend/app/exceptions.py) — `DomainError` subclasses, registered as FastAPI exception handlers.
- [`app/logging_config.py`](../../backend/app/logging_config.py) — structlog with contextvars.
- [`app/schemas/<resource>.py`](../../backend/app/schemas/) — Pydantic request/response DTOs.

**Rule:** routers are thin. They parse, authorize, call a service. Never put SQL or ORM logic in a router. Never bypass the service layer to write to the DB from a router.

Long-form per-layer guide → [`docs/research/07_System_Architecture.md`](../research/07_System_Architecture.md) §3–§7.

---

## 4. Frontend layout

```
app/
├── layout.tsx                ← root: fonts (Inter + Noto Sinhala + Noto Tamil),
│                               theme + intl + query providers, <Toaster/>
├── globals.css               ← shadcn HSL token contract (light + dark)
├── page.tsx                  ← public landing
├── (auth)/                   ← unauth'd shell — login, register
├── (app)/                    ← auth'd shell  — Sidebar + Topbar + main
│   ├── layout.tsx            ← await requireUser()
│   ├── dashboard/page.tsx                    ← welcome banner + 4 stat cards
│   ├── surveys/page.tsx                      ← unified wizard (F-71)
│   ├── surveys/{awareness,knowledge,vulnerability}/{page,thank-you/page}.tsx
│   ├── regulations/page.tsx                  ← surveys hub (3 module cards)
│   ├── risk/page.tsx                         ← read-only risk view (F-52)
│   └── qa/page.tsx, verify/page.tsx          ← 2 "Coming soon" stubs (BUILDs 08/10)
├── (admin)/                  ← admin shell  — same Sidebar/Topbar; F-82 routing
│   ├── layout.tsx            ← await requireRole("admin")
│   └── admin/                ← real segment so URL matches sidebar
│       ├── surveys/awareness/responses/page.tsx        ← response list
│       ├── regulations/{page,new/page,[id]/edit/page}.tsx ← regulations CRUD
│       ├── m2/{questions,scores}/page.tsx              ← question bank + scores
│       ├── m3/risk-signals/page.tsx                    ← risk-signals view
│       └── users/page.tsx                              ← user CRUD (F-92)
└── api/auth/                 ← cookie-side route handlers (Node runtime)
    ├── establish/route.ts   ← writes access + refresh cookies
    ├── token/route.ts       ← reads access cookie (used by server cmps)
    └── logout/route.ts      ← clears both cookies
```

Reusable layers:

- [`components/ui/`](../../frontend/components/ui/) — **21 shadcn-pattern primitives** (button, input, label, card, badge, alert, skeleton, dropdown-menu, select, radio-group, checkbox, table, textarea, toaster + Tabs, Avatar, Breadcrumb, Tooltip from Sessions 7–8 + Sheet, Combobox, Dialog, ConfirmDialog from Session 10).
- [`components/layout/`](../../frontend/components/layout/) — `Sidebar`, `Topbar`, `ThemeToggle`, `LocaleSwitcher` + `MobileSidebar`, `AvatarMenu`, `PageHeader`, `BreadcrumbContext`, `SidebarStateProvider` (added in the Session-8/10 shell redesign).
- [`components/forms/`](../../frontend/components/forms/) — `SurveyForm` + `QuestionRenderer` (per-instrument page) + `SurveyWizard` (unified `/surveys` flow); plus `RegulationContextCard`, `RegulationForm`, `CreateUserDialog`, `EditUserDialog`, `ResetPasswordDialog`, `SurveyProgress`, `SurveyErrorSummary`, `useAutosave`. Renderers cover **10 question formats** (`mcq_single`, `multi`, `likert`, `numeric`, `date`, `short_text`, `ordered_steps`, `scenario_response`, `open`, `yes_no`).
- [`components/admin/`](../../frontend/components/admin/) — `RowActions` (3-dot row-actions menu reused on the Users + Regulations admin tables).
- [`lib/api/`](../../frontend/lib/api/) — typed clients: `auth`, `users`, `surveys`, `m2`, `m3`, `regulations`, `survey-flow`.
- [`lib/auth/`](../../frontend/lib/auth/) — `requireUser`, `requireRole`, `hasAtLeast`.
- [`lib/i18n/`](../../frontend/lib/i18n/) — locale config + EN/SI/TA message JSON (294 deep keys at parity post-Session-10).
- [`lib/surveys/`](../../frontend/lib/surveys/) — `awareness.ts` (legacy 12-question bank still imported by per-instrument pages), `m3-vulnerability.ts`, `safe-field-id.ts` (RHF dotted-id sanitiser, F-89/F-99), `flow-question-to-ui.ts` (FlowQuestion → UI Question adapter for the unified wizard), `types.ts`.
- [`lib/validators/`](../../frontend/lib/validators/) — zod schemas (`auth`, `regulation`, `user`).
- [`lib/types/index.ts`](../../frontend/lib/types/index.ts) — TypeScript mirrors of the backend Pydantic schemas.

Extending these is the subject of [`05_Frontend_Development.md`](05_Frontend_Development.md).

---

## 5. ERD — core tables

The four original MVP tables (Session 3) plus the Session-5 M2/M3 schema, the Session-6 unified `survey_questions` + admin-managed `m1_regulations`, the Session-10 `m1_regulations.is_active` soft-archive flag, the Session-12 `survey_question_regulations` M:N junction + `survey_questions.is_baseline`, the Session-14 `created_by`/`updated_by` authorship columns + `audit_log.record_key`, and the Session-15 `survey_questions.m3_field_mapping`.

```
   ┌──────────────┐ 1            1 ┌──────────────────┐
   │   users      │────────────────│  sme_profiles    │
   │──────────────│  user_id (FK)  │──────────────────│
   │ id  (PK)     │                │ sme_id (PK)      │
   │ email        │                │ user_id (FK,UQ)  │
   │ password_hash│                │ sector           │
   │ role         │                │ employee_count_  │
   │ pref_language│                │   band, region…  │
   │ is_active    │                │ consent_given    │
   │ created_by/  │                │ created_by/      │
   │  updated_by  │                │  updated_by      │
   │ timestamps   │                │ timestamps       │
   └──────────────┘                └─────────┬────────┘
                                              │ 1
                                              │ N
                                   ┌──────────▼─────────────────┐
                                   │   survey_responses          │
                                   │─────────────────────────────│
                                   │ response_id (PK)            │
                                   │ sme_id (FK → sme_profiles)  │
                                   │ survey_instrument           │  "awareness" | "knowledge" | "vulnerability"
                                   │ question_id                 │  "awareness.v1.qNN" or "knowledge.v1.VAT_FACT_001"
                                   │ answer_text/numeric/date    │  exactly one set
                                   │ module_number, domain_code, │  Session-5 denormalisation
                                   │ sector_code, version,       │
                                   │ is_correct, score_points,   │
                                   │ linked_regulation_id (FK)   │  Session-15 — now ALWAYS populated (scoped reg, else question's cached primary)
                                   │ meta (JSONB)                │  partial_credit_reason; from_question_code + from_rule (flow breadcrumb)
                                   │ submitted_at                │
                                   └─────────────────────────────┘

   ┌──────────────────────────────┐        ┌─────────────────────────────────┐
   │   survey_questions           │  N  N  │   m1_regulations                 │
   │──────────────────────────────│ ◀────▶ │─────────────────────────────────│
   │ question_code (PK)           │  (via  │ regulation_id (PK, UUID)         │
   │ module_number (1/2/3)        │  junc- │ regulation_short_code (UQ)       │
   │ domain_code, sector_code     │  tion  │ document_type, document_number   │
   │ knowledge_type,              │  below;│ title_en/si/ta, summary_en/si/ta │
   │ question_format              │  the   │ effective_date, gazette_date,    │
   │ prompt_en/si/ta              │  cached│ severity_level, penalty_range    │
   │ options_json,                │  primary│ expert_verified + by/at,        │
   │ correct_answer_json,         │  is the│ is_active   (Session-10 F-97)    │
   │ next_question_rules (JSONB), │  FK on │ created_by/updated_by            │
   │ m3_field_mapping (JSONB),    │  the q │ timestamps                       │
   │ linked_regulation_id (FK)    │  row)  └────────┬─────────────────────────┘
   │   ← cached PRIMARY pointer   │                 │ N
   │ is_baseline, is_required,    │                 │
   │ is_active, is_branching_root,│           ┌─────▼───────────────────┐
   │ version, created_by/         │           │ m1_regulation_sectors   │  M2M
   │  updated_by                  │           │─────────────────────────│
   └──────┬───────────────────────┘           │ regulation_id (FK, PK)  │
          │ N                                  │ sector_code   (FK, PK)  │
          │                                    │ impact_level            │
   ┌──────▼───────────────────────────┐        └─────────────────────────┘
   │ survey_question_regulations  M:N │
   │──────────────────────────────────│  Session 12 — replaces the 1:1 FK; the
   │ question_code (FK→sq, PK)        │  is_primary=true row is cached on
   │ regulation_id (FK→m1_reg, PK)   │  survey_questions.linked_regulation_id.
   │ weight smallint                  │
   │ is_primary bool  (≤1 per q)     │
   │ created_by/updated_by, timestamps│
   └──────────────────────────────────┘

   ┌─────────────────────────────────┐      ┌──────────────────────────────────┐
   │   m2_knowledge_scores            │      │   m3_compliance_history          │
   │─────────────────────────────────│      │──────────────────────────────────│
   │ score_id (PK), sme_id (FK)      │      │ snapshot_id (PK), sme_id (FK)    │
   │ overall_pct, overall_score_pts, │      │ missed_deadline_24mo, penalties, │
   │ by_domain (JSONB),              │      │ under_audit, back_taxes_paid …   │
   │ instrument_breakdown,           │      │ snapshot_at                      │
   │ computed_at, last_updated       │      └──────────────────────────────────┘
   └─────────────────────────────────┘      ┌──────────────────────────────────┐
   m3_* snapshots are written by              │   m3_behavioural_signals         │
   survey_service._project_m3_snapshots,      │ filing_method, books_method,     │
   driven by each M3 question's                │ accounting_software,             │
   m3_field_mapping (canonical M3_* codes      │ deadline_tracker, barriers …     │
   have built-in defaults).                    └──────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────┐
   │   audit_log (append-only, not FK'd to anything)          │
   │   log_id, event_type, table_name, record_id, record_key, │  Session 14 — record_key for string-keyed entities
   │   user_name, event_data_json, occurred_at                │  every mutation writes here via audit_service.record(...)
   └──────────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────┐
   │   survey_sessions (Session 16)                           │
   │   session_id (PK UUID), sme_id (FK → sme_profiles)      │
   │   survey_mode  TEXT  CHECK (per_module_m1 | per_module_m2│  five modes; each has a question cap
   │                              per_module_m3 | per_module_m4│
   │                              | unified)                  │
   │   status  TEXT  CHECK (in_progress | completed |         │
   │                         abandoned)                       │
   │   started_at, completed_at                               │
   │   questions_shown, questions_answered                    │
   │   recruitment_channel TEXT                               │
   └──────────────────────────────────────────────────────────┘
   survey_responses.session_id (FK → survey_sessions.session_id) added in same migration.

   ┌──────────────────────────────────────────────────────────┐
   │   survey_limits  (singleton — id=1 always)  Session 17   │
   │   id INT PRIMARY KEY DEFAULT 1                           │
   │   sme_limit INT DEFAULT 10                               │
   │   annotator_limit INT DEFAULT 0                          │
   │   admin_limit INT DEFAULT 0                              │
   │   updated_by TEXT, created_at, updated_at               │
   └──────────────────────────────────────────────────────────┘
   Read by survey_session_service on every POST /start; written by admin at /admin/settings.
```

Lookup tables `regulatory_domains` (9 rows: VAT, INCOME_TAX, …) and `sectors` (12 rows: universal, retail, …) are referenced via FK from several of the above; omitted here for brevity.

DDL sources → [`backend/alembic/versions/`](../../backend/alembic/versions/) — **11 Alembic versions** through `202605180001`: initial + Session-5 module23 + Session-6 unified + Session-10 regulation_is_active + Session-12 question_regulations_junction + is_baseline + Session-14 authorship + record_key + Session-15 m3_field_mapping + **Session-16 survey_sessions** + **Session-17 survey_limits** + **Session-19 module_number 0→1**.
ORM source → [`backend/app/models/`](../../backend/app/models/).
**Detail per column** → [`06_Database_and_Migrations.md`](06_Database_and_Migrations.md) §3 — that doc owns the column-level reference; the diagram above is just the relationship sketch.

---

## 6. Token + cookie model

```
   POST /api/v1/auth/login  (email + password)
        │
        ▼
   FastAPI returns { access_token, refresh_token, expires_in }
        │
        ▼
   Browser POST /api/auth/establish   (Next.js route handler)
        │
        ▼
   Set-Cookie: access  (httpOnly, sameSite=lax, ~15 min)
   Set-Cookie: refresh (httpOnly, sameSite=lax, 7 d)

   Subsequent server-component renders
        │
        ▼
   getAccessToken()  reads `access` cookie
        │
        ▼
   AuthApi.me(token)  →  GET /api/v1/users/me  with  Authorization: Bearer <jwt>
```

Refresh rotation, logout, and role enforcement → [`07_Auth_and_Roles.md`](07_Auth_and_Roles.md).

---

## 7. Per-module status (post-Session-19)

The platform has grown across 19 sessions. All four module surveys are end-to-end on the SME side. The session-based architecture (`survey_sessions`, 6-endpoint API) shipped in Session 16 and is now the canonical path. Admin-managed limits (`survey_limits`) shipped in Session 17. `module_number` was renamed from 0 → 1 for Awareness in Session 19. Remaining deferred items are ML/ingest-only.

| `module_number` | Module | Scope | Status (Session 19) | BUILD file |
|---|---|---|---|---|
| **1** | M1 — Awareness survey | 12-Q baseline + sector profile; `instrument="awareness"` | 🟢 Session-based survey end-to-end; `/surveys/awareness` standalone + unified hub | BUILD_05 + BUILD_08 |
| **1** | M1 — Regulations (ingest) | Gazette ingest → NLP classifier → alerts | 🟡 Admin CRUD shipped (F-69, F-74, F-97); ingest pipeline deferred | [`BUILD_07`](../../backend/BUILD_PLAN/BUILD_07_Module1_Awareness.md) |
| **2** | M2 — Knowledge | Survey + auto-scoring + RAG over regulation corpus | 🟡 Survey + scoring + cross-module linkage shipped; RAG + Q-A endpoint deferred | [`BUILD_08`](../../backend/BUILD_PLAN/BUILD_08_Module2_Knowledge.md) |
| **3** | M3 — Risk / Vulnerability | Vulnerability survey + compliance-failure prediction | 🟡 Survey + snapshot projection shipped; ML risk model deferred | [`BUILD_09`](../../backend/BUILD_PLAN/BUILD_09_Module3_Risk.md) + [`BUILD_11`](../../ml/BUILD_PLAN/BUILD_11_ML_Training_Pipeline.md) |
| **4** | M4 — Misinformation | Multilingual claim verification | 🔲 Route stub + research scaffolding only; classifier deferred | [`BUILD_10`](../../backend/BUILD_PLAN/BUILD_10_Module4_Misinformation.md) |

The two remaining 501 stubs at `/api/v1/{qa,verify}` are placeholders so the router aggregator imports cleanly and the OpenAPI UI tells you where each one lives. `/api/v1/regulations` and `/api/v1/risk` are no longer 501s — they're real read endpoints (F-50, F-69), even though their ingest / ML pipelines are deferred.

For the column-level coverage breakdown (which F-IDs landed under which BUILD), see [`docs/tracker/BUILD_PLAN_COVERAGE.md`](../../tracker/BUILD_PLAN_COVERAGE.md).

---

## 8. Where to read further

- Architecture theory + 5-layer view → [`docs/research/07_System_Architecture.md`](../research/07_System_Architecture.md).
- Long-form folder layout (every directory, every file) → [`docs/BUILD_PLAN/BUILD_02_Folder_Structure.md`](../../infra/BUILD_PLAN/BUILD_02_Folder_Structure.md).
- Backend specifics → [`04_Backend_Development.md`](04_Backend_Development.md).
- Frontend specifics → [`05_Frontend_Development.md`](05_Frontend_Development.md).
- Survey-system internals (unified wizard, cross-module rules, scoring) → [`11_Survey_System.md`](11_Survey_System.md).
- BUILD-vs-delivered audit (per-BUILD F-ID attribution + open work) → [`docs/tracker/BUILD_PLAN_COVERAGE.md`](../../tracker/BUILD_PLAN_COVERAGE.md).
- SETUP-doc accuracy audit → [`docs/tracker/SETUP_COVERAGE.md`](../../tracker/SETUP_COVERAGE.md).

---

**Prev:** [`02_Quickstart.md`](02_Quickstart.md) &nbsp;·&nbsp; **Next:** [`04_Backend_Development.md`](04_Backend_Development.md)
