# BUILD_PLAN ↔ Delivered work — Coverage audit

> **Audit cut:** 2026-05-22 (updated after Session 56, F-01 → F-199 inclusive).
> **Refresh cadence:** after every session, or every 5 new F-IDs — whichever comes first.

## Session 56 add-on — M1 raw PDF bulk extraction + classification (F-199, data-population workstream)

Cowork-mode data-population workstream. **Not** a code-build workstream — does **not** touch `enigmatrix-backend`, `enigmatrix-frontend`, or `enigmatrix-ml` source. Operates entirely inside the Cowork sandbox using `pdfplumber` (+ `pdftotext` poppler-utils fallback) and a regex/heuristic statute classifier (`outputs/build_csv.py`).

**Mapping to BUILD spec:** This work is **upstream input data** for the BUILD_07 import job (M1 gazette ingest pipeline). The 7 batch CSVs + 2 tracker addenda deliver pre-classified `m1_regulations`-shape rows that a future BUILD_07 import task could load directly, bypassing the Celery pipeline entirely. Useful as a seed-data backstop while the production Celery pipeline matures.

- **F-199** — Full 800-PDF corpus extraction + classification across batches 5–11, with `m1_extraction_tracker_v11_addendum.csv` (203 rows) + `m1_extraction_tracker_v12_addendum.csv` (145 rows) marking 100% coverage of `C:\sme\03-Data-Sources\m1\raw\pdf\`. Classifier extended in `outputs/build_csv.py` for Pradeshiya Sabha Act 15/1987, Sri Lanka Electricity (Amendment) Act 36/2024, Sri Lanka Export Development Act 40/1979, Companies Act 07/2007, doubled-Tamil Land Acquisition Act Ch 460, Armed Services Long Service Medal pattern broadening, and `PREFIX_FALLBACK` extended for gazette prefixes 2483–2486.

**Open BUILD-spec gaps surfaced:**
- BUILD_07 doesn't describe an "import-from-pre-classified-CSV" code path — the classifier in `outputs/build_csv.py` is a parallel Cowork-only system. If the production pipeline ever needs to ingest the deliverables, a BUILD_07 import task spec would be required.
- BUILD_07 doesn't describe gazette-prefix → ISO-date weekly bucketing (`PREFIX_FALLBACK`). The production pipeline relies on PDF body date parsing; the Cowork classifier needs a manual map. This divergence should be documented.

## Session 55 add-on — Railway production deployment + Stages 1-4 (F-193–F-198)

Five workstreams in one long Cowork session, delivering the first production deployment of `enigmatrix-backend` plus four feature stages on top of it.

**Stage 0 — Railway production deployment (F-193).** Directly executes the `04-Technology-Stack/infra/Railway-Deployment-Plan.md` runbook with three corrections discovered during the deploy: (1) repo owner is `ghubfri-bot` not `Enigmatrixx` as the plan said; (2) the `[tool.uv.sources]` Git source must use plain HTTPS (no `${GITHUB_TOKEN}` substitution — uv doesn't expand env vars in those URLs); (3) `GITHUB_TOKEN` injection must use git's `insteadOf` URL-rewrite at BOTH build time (via `ARG GITHUB_TOKEN`) and runtime (via env var in `start_railway.sh`). The Railway-Deployment-Plan should be updated to reflect these corrections so the next deploy can skip the four pre-success failures.

**Stage 1 — Cancel + rollback (F-194 backend, F-195 frontend).** Directly extends **BUILD_07** (M1 gazette ingest pipeline). Adds the first operator-facing destructive action on the M1 admin surface — every prior recovery action (`/retry`, `/re-extract`, `/re-preprocess`, `/categorize`) operated on a single row. Cancel is the first scope-wide rollback. Pre-dates the `m1_extraction_runs` table (F-189 from Session 54) so it uses scope+queued_at params instead of a `run_id` lookup — could be migrated later.

**Stage 2 — Per-PDF metadata schema (F-196).** Extends **BUILD_07** Step 2b (PDF extraction). The four new columns (`file_size_bytes`, `sha256`, `pdf_pages`, `language`) close the operator's "I want to see PDF metadata" gap surfaced after the first production extraction runs. The Unicode-codepoint `detect_language` heuristic is an intentional divergence from ml's heavier fasttext implementation — image-size cost wins over accuracy delta for the three Sri Lankan languages.

**Stage 3 — PDF Records browse page (F-197).** Extends **BUILD_07** admin surface. Adds the first browse-all M1 view (every prior admin view is scoped to a single trigger run). New `GET /pdf-records` endpoint + new admin page. Consumes Stage 2's metadata fields. UX choices distilled from invoked `design:ux-copy`/`design:user-research`/`design:design-system` skills (concrete next-step empty-state copy, pagination over infinite-scroll, lean row shape, draft-vs-applied filter state for search).

**Stage 4 — Cross-repo code-quality audit (F-198).** Audit dimension, not a BUILD spec item. Six parallel agents produced 60+ findings; three HIGH inline fixes applied (`ForbiddenError` import, `.gitignore` Cowork block, `ExtractionRowStatus` trim — last reverted); five MEDIUM follow-ups deferred as discrete tasks #18-22.

- **F-193** — Railway production deployment (5 build failures, final fix via git `insteadOf`; PAT leaked in build log, rotation pending #12).
- **F-194** — `POST /api/v1/admin/m1/extraction/cancel/{task_id}` endpoint + rollback service (`app/services/m1_extraction_cancel.py` NEW).
- **F-195** — Cancel button + ConfirmDialog + inline result panel on extraction status card.
- **F-196** — Migration `202605280001`: `file_size_bytes`, `sha256`, `pdf_pages`, `language` columns + indexes + `app/extraction/pdf_metadata.py` helper.
- **F-197** — `GET /api/v1/admin/m1/extraction/pdf-records` + new `/admin/m1/pdf-records` admin page + sidebar nav + i18n keys.
- **F-198** — Stage 4 cross-repo audit + 3 HIGH inline fixes + 5 MEDIUM follow-ups (#18-22).

**Open BUILD-spec gaps surfaced (not in scope for Session 55):**
- BUILD_07 doesn't yet describe the `m1_extraction_runs` table or the `/runs` endpoint added in Session 54 (F-189-F-191) — should be documented.
- BUILD_07 doesn't yet describe the `cancel` + `pdf-records` endpoints added in Session 55 — should be documented.
- No BUILD spec governs deployment topology (single-service container with shared volume, Redis plugin pattern, `${{Redis.REDIS_URL}}` variable reference). Could become a `BUILD_17_Deployment_Topology.md` if a second deploy target is added (Render fallback per `Render-Migration-Plan.md`).

**Errors fixed in this session (not plan items):**
- `enigmatrix-backend/pyproject.toml` workspace=true vs Git-source confusion (Stage 0).
- uv doesn't expand `${GITHUB_TOKEN}` in `tool.uv.sources` URLs (Stage 0).
- Railway cached snapshot image after new commit (Stage 0).
- `app/deps.py:44` ForbiddenError NameError (Stage 4 — H2 fix).
- `.gitignore` missing Cowork-artifacts patterns in all 4 repos (Stage 4 — H3 fix).
- ConfirmDialog Edit stray `}` (Stage 1).

## Session 54 add-on — M1 extraction UX improvements + run history persistence + pool fix (F-185–F-192)

Two workstreams delivering operational improvements to the M1 gazette extraction admin surface, plus an infrastructure hotfix.

**Workstream A — Extraction page UX (F-185–F-188).** No BUILD spec directly mandates these four UX improvements, but they all support the operational-readiness criteria implicit in **BUILD_07** (M1 gazette ingest pipeline). The sticky sidebar fix (F-185) is a layout correctness regression fix. The resume/restart card (F-186) addresses the operational gap where a mid-pipeline failure left rows stranded at the `extracted` status with no recovery path short of manual DB intervention. The full history table (F-187) replaces a cosmetic 5-item pill strip with a functional run log. Auto-scroll (F-188) is a minor navigation UX improvement.

**Workstream B — Server-side run history (F-189–F-192).** Directly extends **BUILD_07** by replacing ephemeral per-browser localStorage history with a durable, shared, server-side audit log (`m1_extraction_runs` table). This closes the gap where extraction history was invisible to other admin sessions and lost on browser cache clear. The `GET /runs` endpoint also enables future features (e.g. scheduled-run monitoring, bulk status audits). The QueuePool fix (F-192) is an infrastructure hotfix required by the new `db` dependencies introduced in this workstream.

- **F-185** — Sticky sidebar layout fix (layout.tsx `lg:items-start` + nav `max-h + overflow-y-auto`).
- **F-186** — Resume/restart card for mid-pipeline failure recovery (`resume-extraction-card.tsx` NEW).
- **F-187** — Full extraction history table replacing 5-item pill strip (`extraction-history-table.tsx` NEW; `MAX_HISTORY` 5→20).
- **F-188** — Auto-scroll to progress panel on history row click (`progressRef` + `scrollIntoView`).
- **F-189** — `m1_extraction_runs` SQLAlchemy model + Alembic migration `202605210002` (FK `users.id`, 4 indexes).
- **F-190** — Backend: trigger INSERT, status UPDATE on terminal, cancel UPDATE REVOKED, `GET /runs` endpoint, new schemas.
- **F-191** — Frontend: `listRuns()` API method, `runsQuery` TanStack Query, `toTriggerOut()` normalizer, API-primary history with localStorage fallback.
- **F-192** — `app/db/session.py` pool fix: `pool_size 1→3`, `max_overflow 2→5` (QueuePool exhaustion hotfix).

**Errors fixed in this session (not plan items):**
- Alembic multiple-heads fork — corrected `down_revision` from `"202605210001"` to `"202605280001"`.
- FK column mismatch — `users.user_id` → `users.id` in migration, model, and trigger endpoint.
- PowerShell line continuation — `\` → backtick for multi-line git commands.

**Open BUILD_07 items surfaced (no change from Session 53):** Recent Runs backend 503, post-failure step state, Reconcile confirmation, Start Extraction feedback, server path in error messages.

---

## Session 53 add-on — M1 pipeline admin UX audit (F-184)

Admin-interface audit sprint covering F-184. No BUILD spec directly covers admin UX auditing — this is an above-spec quality and operational-readiness activity. The work maps to **BUILD_07** (M1 gazette ingest pipeline), specifically the admin monitoring and observability surface that serves as the operational interface for the pipeline built under BUILD_07.

- **F-184** — Hands-on UX/UI audit of `/admin/m1/pipeline` and all sub-pages. 14 findings (1 Critical, 4 High, 6 Medium, 3 Low) plus 7 positive observations. Word document deliverable produced. Critical finding F-06: `/admin/m1/pipeline/recent` returns HTTP 503 on every RSC fetch — this is a BUILD_07 backend gap that must be fixed before the pipeline admin surface is considered operational.

**New BUILD_07 open items surfaced:**
- Recent Runs page backend endpoint returning 503 (F-06 — Critical).
- Post-failure step state shows "pending" instead of "skipped" (F-07 — High) — pipeline state-machine logic gap.
- "Reconcile all raw folders" has no confirmation or reversibility safeguard (F-09 — High) — operational safety gap.
- Start Extraction buttons give no feedback (F-10 — High) — extraction job submission UX gap.
- Server path (including typo `Reasearch`) exposed in extraction error messages (F-12 — High) — security/professionalism gap.

**Open BUILD items unaffected by this session:** BUILD_10 (M4 misinformation), BUILD_11 (ML training), BUILD_12 (scheduling), BUILD_14 (cloud deployment) — all unchanged.

---

## Session 52 add-on — UI component suite + theme toggle refactor

Frontend-only polish sprint covering F-179–F-183. No BUILD spec directly covers UI animation primitives or canvas-based text effects — these are above-spec quality improvements. The work maps loosely to **BUILD_05 §2** (frontend foundation + theme tokens) which called for a light/dark toggle and responsive UI.

- **F-179–F-180** — `AnimatedList` component + applied to 6 list/card pages and 13 table files. Addresses an implicit acceptance criterion in BUILD_05 that list pages be responsive and usable on mobile.
- **F-181–F-182** — `FuzzyText` canvas component + applied to 404, ComingSoon, platform-map stats, research-log metrics. Not in any BUILD spec; brand identity polish.
- **F-183** — Theme toggle dropdown → single-click toggle button with View Transitions API circular reveal. Directly improves the BUILD_05 `next-themes` feature (F-22); the circular reveal is above spec.

**Open BUILD items unaffected by this session:** BUILD_07 (gazette ingest), BUILD_10 (M4 misinformation), BUILD_11 (ML training), BUILD_12 (scheduling), BUILD_14 (cloud deployment) — all unchanged.

---
## Session 12 add-on — Universal regulation-anchored survey system

Not strictly a BUILD-spec item (BUILD_08 + BUILD_09 + BUILD_13 each cover slivers of this work) but the largest single delta since Session 11. Delivered F-IDs: F-106 → F-118.

- **Backend** — M:N junction `survey_question_regulations` (replacing the 1:1 cached column with a proper many-to-many while keeping `linked_regulation_id` as a primary cache); `is_baseline` flag for regulation-agnostic baseline questions; branching validators with soft-warn forward-ref/cycle/archived-target detection; regulation-scoped flow (`?regulation_id=…`); per-instrument question fetch endpoint; translation queue admin endpoints; dashboard pending-regulations endpoint; backend i18n fallback helper.
- **Frontend admin** — visual flow canvas at `/admin/regulations/[id]/flow` (CSS grid M0/M2/M3 columns + slim drawer for follow-up creation + validation banner); `/admin/translations` queue page with inline SI/TA edit + bulk-mark.
- **Frontend SME** — DB-driven awareness/knowledge/vulnerability pages (kill the hardcoded TS banks); two-tab `/surveys` hub with per-regulation cards alongside the classic per-instrument cards; regulation-scoped flow at `/surveys/regulation/[id]`; dashboard widget for pending regulations.

**Open follow-ups:** OQ12 hard redirect, OQ32 partial-credit rubric UI, M3-projection data-driven mapping, ReactFlow upgrade-path for the canvas, drawer rule-upsert race (ETag), full SI/TA translations for the new UI strings.

---
> **How to use:** scan the [coverage table](#coverage-table) for the headline; drill into a specific BUILD section if you care about its sub-items.
> **Sources:** [`FEATURES.md`](FEATURES.md), [`SESSIONS.md`](SESSIONS.md), [`CHANGES.md`](CHANGES.md), and the per-BUILD specs under [`docs/BUILD_PLAN/`](../BUILD_PLAN/).

---

## Executive summary

Of the 14 substantive BUILD specs (BUILD_01 → BUILD_15 — `BUILD_00` is an index, `BUILD_16` is a tracker template, `BUILD_17` is a prompt library):

- **🟢 Fully delivered (6):** BUILD_01 (project init), BUILD_02 (folder structure), BUILD_03 (backend API skeleton), BUILD_04 (database core), BUILD_05 (frontend foundation), BUILD_06 (auth + users).
- **🟡 Partially delivered (3):** BUILD_08 (M2 knowledge — survey + scoring + cross-module shipped, RAG deferred), BUILD_09 (M3 risk — survey + storage + projection shipped, ML model deferred), BUILD_13 (admin console — regulations + users CRUD + audit shipped, annotation bridge deferred).
- **🔲 Deferred / not started (5):** BUILD_07 (M1 awareness ingest), BUILD_10 (M4 misinformation runtime — research scaffolding only), BUILD_11 (ML training pipeline), BUILD_12 (data ingestion + scheduling), BUILD_14 (cloud deployment).
- **🟡 Partially delivered (1):** BUILD_15 (observability + testing — three smoke-test surfaces shipped, full pyramid + metrics deferred).

**Thesis-friendly framing:** The MVP foundation (auth + storage + frontend) plus the **M0 → M2 → M3 unified survey flow** plus the admin CRUD surface for regulations and users have shipped end-to-end and are runnable today via `make up && make migrate && make seed && make dev`. The remaining work — gazette ingest (M1), misinformation classifier (M4), ML training pipeline, ingestion scheduling, cloud deployment, and the full observability stack — is scheduled as separate BUILD slices and is intentionally absent from the present codebase. Every "missing" item below has a named BUILD doc plus a roadmap entry, not a gap.

**Breadth vs depth:** the project went deeper on the survey + admin slice (Session 6 unified the three instruments into a single DB-driven flow with cross-module branching — a deviation from BUILD_08's spec that's documented in SESSIONS.md Session 6 "Decisions") and shallower on M1/M4 ingest. Both choices were deliberate.

---

## Status legend

| Char | Meaning |
|------|---------|
| 🔲 | Not started |
| 🟡 | In progress |
| 🟢 | Done & accepted |
| 🔴 | Blocked |
| ⚪ | Out of scope / dropped |

(Verbatim from [`BUILD_00`](../shared/BUILD_PLAN/BUILD_00_INDEX.md). The `FEATURES.md` rows use the same legend.)

---

## Coverage table

| BUILD | Title | Status | Delivered F-IDs | Open work / deferred |
|---|---|---|---|---|
| BUILD-00 | Index + module map | n/a (index, not a deliverable) | — | — |
| BUILD-01 | Project Initialization | 🟢 | F-03 | OQ1 (library pinning) deferred — see BUILD-00 OQs |
| BUILD-02 | Monorepo Folder Structure | 🟢 | F-01, F-02 | None |
| BUILD-03 | Backend API (FastAPI) | 🟢 | F-05, F-06, F-08, F-11, F-12, F-13, F-14, F-15, F-16, F-17 | None — 4 module endpoints stay 501 stubs by design until BUILDs 07 / 08 / 09 / 10 ship |
| BUILD-04 | Database & Storage | 🟢 | F-02, F-07, F-09, F-18, F-44, F-65, F-66, F-73, F-97 (migration) | ChromaDB wired but unused (BUILD_08 §7); object storage not yet provisioned (deferred to BUILD_07/14) |
| BUILD-05 | Frontend (Next.js 14) | 🟢 | F-19 → F-39, F-43, F-51 → F-55, F-71, F-78, F-83 → F-88, F-92, F-93, F-94, F-98 | None for the MVP slice; M1/M4 pages stay coming-soon stubs |
| BUILD-06 | Auth & Users | 🟢 | F-10, F-11, F-12, F-13, F-16, F-26, F-28 → F-32, F-57, F-58, F-94, F-96 | OQ6 (server-side `confirmPassword`) deferred; password-reset email flow + revoke-on-logout deferred to BUILD_14 |
| BUILD-07 | Module 1: Awareness | 🔲 | — | All deliverables (gazette lister/downloader/extractor/classifier, watchers, alert engine) deferred. SME-side awareness *survey* shipped under BUILD_08/05 (F-33–F-36, F-65–F-72) but that's distinct from M1 *ingest*. |
| BUILD-08 | Module 2: Knowledge & RAG | 🟡 | F-44 → F-50, F-65 → F-72, F-77 (Phase B planned) | RAG knowledge base + ChromaDB ingest + Q-A endpoint with citations all deferred. The *knowledge survey + scoring + cross-module linkage* portion shipped fully. |
| BUILD-09 | Module 3: Risk Prediction | 🟡 | F-44, F-49, F-50, F-70 (M3 projection) | XGBoost/LSTM training, SHAP explanations, drift monitoring all deferred. Risk-signals storage + read endpoint shipped. |
| BUILD-10 | Module 4: Misinformation | 🔲 (research-only) | F-90 (data-collection scaffolding docs only) | All runtime deliverables (connectors, cleaning, classifier, RAG verifier, public claim-check, `m4_*` tables) deferred. Research methodology + Perplexity prompt + source registry shipped under F-90. |
| BUILD-11 | ML Training Pipeline | 🔲 | — | Single training harness, MLflow + Optuna, gate decorators, registry promotion CLI all deferred. Required by BUILD_07/08/09/10. |
| BUILD-12 | Data Ingestion & Scheduling | 🔲 | — | Scrapy spiders, Playwright workers, social watchers, APScheduler/Celery all deferred. Source registry partially exists in research/ (F-90) but not as runtime code. |
| BUILD-13 | Admin Console & Annotation | 🟡 | F-37, F-38, F-53, F-67, F-68, F-69, F-71, F-74, F-79, F-80, F-81, F-86, F-91 → F-98, F-126, F-127, F-134 → F-137 | Label Studio bridge + bulk CSV import + Postgres immutability trigger deferred. Audit-log browsing UI shipped (F-126/F-127). Admin-configurable survey limits (`survey_limits` singleton, `/admin/settings`) shipped in F-134–F-137. |
| BUILD-14 | Deployment Cloud | 🔲 | — | Docker-compose prod topology, nginx + TLS, blue/green CI/CD, nightly backups, DR runbook all deferred. |
| BUILD-15 | Observability & Testing | 🟡 | F-40, F-41, F-42, F-56, F-60, F-62 | Three smoke surfaces shipped (backend integration + unit + Playwright E2E) plus runtime hardening + the `make doctor` toolkit. Full pyramid (≥ 70 % coverage gates, k6 load, Prometheus + OpenTelemetry, Grafana dashboards) deferred. |
| BUILD-16 | Progress Tracker Template | n/a (template) | — | The tracker files this audit consumes (FEATURES / SESSIONS / CHANGES) instantiate this template. |
| BUILD-17 | Claude Prompts Library | n/a (prompt library) | — | Prompts referenced as needed; no deliverable. |

**Headcount:** 139 F-IDs delivered (F-01 → F-139); zero blocked; zero dropped.

---

## Per-BUILD details

### BUILD-01 — Project Initialization 🟢

**Acceptance criteria from the spec:**
- Required tools installed at the right versions (Python 3.11, Node 20, Docker, pnpm, pre-commit).
- `git clone + make up` succeeds on a fresh machine.
- `GET /health` returns 200 once the backend is up.
- `.gitignore`, `.env.example`, `Makefile`, pre-commit config all in repo root.

**What landed:**
- **F-03** — `.gitignore`, `.env.example`, `Makefile`, root `README.md`, pre-commit config wired.

**What's missing:** Nothing in scope. The thesis-grade open question **OQ1 (library pinning)** is tracked in BUILD_00 and `FEATURES.md` "Open questions" but isn't a BUILD-01 acceptance criterion.

**Notes:** `make doctor`, `make db-shell`, `make db-users`, `make reseed-users` (F-62) extend the `Makefile` beyond the BUILD-01 spec — useful additions that came out of Session-5 runtime hardening.

---

### BUILD-02 — Monorepo Folder Structure 🟢

**Acceptance criteria:**
- `tree -L 2` matches BUILD_02 §1 layout (`backend/`, `frontend/`, `ml/`, `infra/`, `docs/`).
- All sub-directories with `.gitkeep` where empty.
- Per-folder README stubs.

**What landed:**
- **F-01** — Monorepo scaffold with all the directories per spec.
- **F-02** — Dev infrastructure (`docker-compose.dev.yml`, `infra/postgres/init.sql`).

**What's missing:** `ml/` directory is bootstrapped but currently empty (BUILDs 11/07/10 will populate it). Acceptable for the MVP slice.

---

### BUILD-03 — Backend API (FastAPI) 🟢

**Acceptance criteria:**
- `GET /health` returns 200 + DB ping.
- `/docs` (Swagger UI) renders.
- Logs emit JSON / pretty per env.
- Invalid JWT → 401.
- All v1 endpoints (auth, users, m1–m4, admin, surveys) exist as at least 501 stubs.

**What landed:**
- **F-05** — FastAPI app skeleton (`main.py`, `settings.py`, `logging_config.py`, `exceptions.py`, `deps.py`).
- **F-06** — Pydantic v2 settings with `DATABASE_URL` (asyncpg) + `JWT_SECRET` + `CORS_ORIGINS`.
- **F-08** — ORM models for the four MVP tables.
- **F-11** — Auth router (register / login / refresh).
- **F-12** — RBAC dependencies (`get_current_user`, `require_admin`, `require_annotator`).
- **F-13** — slowapi rate limit on `/auth/login` + `/auth/register`.
- **F-14** — Users router (`/users/me` + admin list).
- **F-15** — Surveys router (`/surveys/{instrument}/submit` + admin list).
- **F-16** — Audit-log writes on auth events.
- **F-17** — Module 501 stubs for `/regulations`, `/qa`, `/risk`, `/verify`.

**What's missing:** Nothing for the MVP. The `/qa`, `/verify`, `/risk` 501 stubs and `/regulations` 501 stub stay 501 by design until BUILDs 07 / 08 / 09 / 10 ship — that's expected behaviour, not a gap.

---

### BUILD-04 — Database & Storage 🟢

**Acceptance criteria:**
- `make up && make migrate && make seed` succeeds end-to-end.
- All tables in the research-doc schema present.
- `pg_trgm` + `uuid-ossp` extensions loaded.
- ChromaDB callable via the helper.
- 1 MB file round-trips through object storage.

**What landed:**
- **F-02** — Compose file + `init.sql` with extensions.
- **F-07** — SQLAlchemy 2.0 async session + `DeclarativeBase` + `TimestampMixin`.
- **F-09** — Initial migration `202605080001_initial_schema.py` (4 tables).
- **F-18** — `seed_dev.py` for admin / annotator / SME accounts.
- **F-44** — Session-5 schema additions: `regulatory_domains`, `sectors`, `m2_questions`, `m2_knowledge_scores`, `m3_compliance_history`, `m3_behavioural_signals` + 7 columns on `survey_responses`.
- **F-65** — Session-6 generalisation: `m2_questions` → `survey_questions` rename + `m1_regulations` + `m1_regulation_sectors` + `survey_responses.linked_regulation_id`.
- **F-66** — Idempotent seed scripts (regulations, awareness, M2/M3 questions).
- **F-73** — Follow-up migration `202605100002` to relax NOT NULL on `survey_questions.domain_code` + `knowledge_type` after Session-6.
- **F-97** — Session-10 migration `202605110001` adds `m1_regulations.is_active` for soft-archive.

**What's missing:** Object storage layer (S3 or MinIO) **not provisioned**. ChromaDB **runs** in Docker compose but no collections created (deferred until BUILD_08 RAG ships). Both deferrals are intentional and documented.

**Notes:** Two migrations beyond the BUILD-04 spec — `202605090001` (M2/M3 schema) and `202605110001` (regulations `is_active`) — are recorded in [`SETUP/06_Database_and_Migrations.md`](../backend/SETUP/06_Database_and_Migrations.md) §3.

---

### BUILD-05 — Frontend (Next.js 14) 🟢

**Acceptance criteria:**
- `pnpm dev` serves on :3000.
- All three locales (EN/SI/TA) render with correct fonts.
- Auth-guarded layout redirects unauthenticated.
- Dark mode toggle works.
- Lighthouse a11y ≥ 90.
- All 16 page stubs exist.

**What landed:**
- **F-19 → F-27** — Next.js 14 + Tailwind + shadcn primitives + theme + i18n + API client + RBAC helpers + TanStack Query provider.
- **F-28 → F-32** — Auth flow: login + register + cookie route handlers + `(app)` and `(admin)` layouts + middleware + topbar.
- **F-33 → F-39** — Awareness survey end-to-end + admin response list + 501-stub coming-soon pages.
- **F-43** — `docs/SETUP/` track shipped with 12 onboarding docs.
- **F-51 → F-55** — Conditional questions, six SME pages, three admin pages, per-module accent CSS, sidebar nav, EN/SI/TA i18n parity.
- **F-71** — Unified `/surveys` wizard (Session 6).
- **F-78, F-83 → F-88** — Sidebar redesign, dashboard stat cards, filter rail, polished tables (Sessions 7–8).
- **F-92, F-93, F-94, F-98** — `/admin/users` redesign + Combobox primitive + Create/Edit/Delete dialogs (Sessions 9–10).

**What's missing:** Lighthouse a11y formally measured **once** during F-43 work; no re-measurement after the recent shell redesign. Recommended re-audit before any production push.

**Notes:** UI primitive count grew from 14 (BUILD-05 spec) to **24** post-Session-10 (added Tabs, Sheet, Combobox, Dialog, Avatar, Breadcrumb, Tooltip, ConfirmDialog, RowActions, plus a few helpers). Documented in [`SETUP/05_Frontend_Development.md`](../frontend/SETUP/05_Frontend_Development.md) §7.

---

### BUILD-06 — Auth & Users 🟢

**Acceptance criteria:**
- Register + login + refresh round-trip works.
- Invalid JWT → 401; SME → admin endpoint → 403.
- Rate limit on `/auth/login`.
- Audit trail row per auth event.

**What landed:**
- **F-10** — `core/security.py` (bcrypt + HS256 access/refresh).
- **F-11** — Auth service + schemas + router.
- **F-12** — RBAC dependencies.
- **F-13** — Inbound rate limit (slowapi).
- **F-16** — Audit-log writes (register / login.success / login.failure / refresh).
- **F-26** — `lib/auth/{session,roles}.ts` — server-side `requireUser()` / `requireRole()`.
- **F-28 → F-32** — Frontend auth flow.
- **F-57, F-58** — bcrypt pin + UTF-8 truncation hardening.
- **F-94** — `POST /api/v1/users` admin-driven create (extends the spec).
- **F-96** — Full admin user CRUD: PATCH / activate / deactivate / reset-password / DELETE — last-active-admin guard included.

**What's missing:** Email-link password reset flow (deferred to a later slice once SMTP infra lands). User-facing self-service password change. Account lockout per email. Revoke-on-logout (deferred to BUILD_14 when Redis ships).

**Notes:** F-94 + F-96 went **beyond** the BUILD-06 spec — the spec only lists register/login/refresh + role checks. The CRUD surface is documented in [`SETUP/07_Auth_and_Roles.md`](../backend/SETUP/07_Auth_and_Roles.md) §2.

---

### BUILD-07 — Module 1: Awareness 🔲

**Acceptance criteria from the spec:**
- Gazette lister + downloader + PDF extractor (PyMuPDF → pdfplumber → OCR fallback).
- Text-hash dedup.
- Classifier loads from `model_versions`.
- Secondary watchers (news, IRD portal) wired.
- Alert engine fires on classified updates.

**What landed:** Nothing in the runtime sense. The SME-side **awareness *survey*** (12 hardcoded questions, then DB-driven post-Session-6) shipped under BUILDs 05 and 08 (F-33, F-65, F-66) — but that's the *user-facing* awareness measurement, not the *gazette ingest pipeline* that BUILD-07 specs.

**What's missing (file-and-endpoint specific):**
- `backend/app/ingestion/gazette/{lister,downloader,extractor,segmenter}.py` — none exist.
- `backend/app/services/module1/{classifier,summarizer,lag_analyzer,alert_engine}.py` — none exist.
- `backend/app/ingestion/{news_watcher,portal_watcher}.py` — none exist.
- `regulations` table row count: only the 5 admin-seeded rows (Session 6, F-66); zero auto-ingested gazette rows.

**Notes:** Admins enter regulations manually via the Session-7 `/admin/regulations` form (F-74) until BUILD-07 ships the auto-ingest. Documented in [`SETUP/11_Survey_System.md`](../backend/SETUP/11_Survey_System.md) §10 and the [`research/module_1_and_4_data_architecture.md`](../backend/research/module_1_and_4_data_architecture.md) §A3.

---

### BUILD-08 — Module 2: Knowledge & RAG 🟡

**Acceptance criteria:**
- 3 instruments (Awareness, Compliance Knowledge, Vulnerability) with surveys end-to-end.
- Scoring engine covers 6 question kinds.
- RAG over `regulations_chunks_v1` ChromaDB collection with citations.
- `GET /api/v1/m2/sme/{sme_id}/knowledge_score` returns score + breakdown + percentile.
- 40 M2 + 15 M0 + 20 M3 questions seeded.

**What landed (survey + scoring + linkage half):**
- **F-44** — `m2_questions` + `m2_knowledge_scores` schema (Session 5).
- **F-45** — 40 canonical M2 questions seeded (verbatim from `research/module_2_and_3_data_architecture.md` PART A).
- **F-46** — Cross-module-linkage rules (`m2_linkage_rules.py`).
- **F-47** — Scoring engine for mcq / scenario / numeric / ordered_steps / open + partial credit.
- **F-48** — `m2_service.questions_for_sme` + scoring on submit + `recompute_knowledge_score` cache.
- **F-49** — M3 service: history + behavioural + combined risk-signals view.
- **F-50** — `/api/v1/m2/*` + `/api/v1/m3/*` routers.
- **F-65 → F-72** — Session-6 unified `survey_questions` table + flow engine + `next_question_rules` + frontend wizard.

**What's missing (BUILD-08 §7, the RAG half):**
- `regulations_chunks_v1` ChromaDB collection — not created.
- `ml/m2/build_kb.py` — does not exist.
- `ml/m2/eval_ragas.py` — does not exist.
- `app/services/m2_rag.py` — does not exist.
- `/api/v1/qa/ask` — currently a 501 stub (per F-17).

**Notes:** Sessions 6–10 went **deeper** on the survey half — the unified flow engine + admin regulations CRUD are extensions, not regressions. RAG ships in a separate BUILD_08 §7 slice once gazette ingest (BUILD_07) provides corpus content.

---

### BUILD-09 — Module 3: Risk Prediction 🟡

**Acceptance criteria:**
- 6 `m3_*` tables populated.
- Features computable without leakage.
- ROC-AUC ≥ 0.75 + precision-at-10 % ≥ 0.60.
- SHAP explains top-5 features.
- `GET /api/v1/risk/me` returns risk band + SHAP.

**What landed (storage + projection half):**
- **F-44** — `m3_compliance_history` + `m3_behavioural_signals` schema.
- **F-49** — Risk-signals view (combined M2 score + M3 history + behaviour).
- **F-50** — `/api/v1/m3/*` router + `SupportedInstrument` extension.
- **F-70** — M3 projection on `survey_service.submit` (when `module_number=3` answers come in via the unified wizard).

**What's missing (the ML half):**
- `ml/m3/{features,synth,train_xgb,train_lstm,explain,eval}.py` — none exist.
- `m3_features` + `m3_predictions` tables — not in any migration.
- `app/services/m3/predict.py` — does not exist.
- `/api/v1/risk/me` — still a 501 stub (per F-17).

**Notes:** The vulnerability *survey* shipped (Session 6, F-65 → F-72); the *ML-driven risk score* is the deferred half, scheduled with BUILD_11 (training pipeline) which is also deferred.

---

### BUILD-10 — Module 4: Misinformation 🔲 (research scaffolding only)

**Acceptance criteria:**
- 6 `m4_*` tables.
- Connectors for Facebook / Twitter / Reddit / YouTube / TikTok / WhatsApp / FactCheck.lk.
- Label Studio bridge.
- Classifier loaded from registry.
- RAG verifier returns verdict + supporting regulations.
- Public `/verify/claim` endpoint + UI.
- ≥ 500 consensus posts, κ ≥ 0.70, F1 ≥ 0.75.

**What landed:**
- **F-90** — Research-only scaffolding: `docs/research/module_4_data_collection.md` (methodology), `docs/research/module_4_perplexity_prompt.md` (research prompt), `docs/research/module_4_sri_lankan_sources.md` (registry skeleton). All annotation workforce / volume / language balance / ethics decisions documented. No runtime code.

**What's missing (everything that runs):**
- `m4_raw_posts`, `m4_cleaned_posts`, `m4_labeled_posts`, `m4_linguistic_features`, `m4_claim_verifications`, `m4_topics` — none exist in any migration.
- `app/modules/m4/{language,pii,classify,verify,spread,sources/*.py}` — none exist.
- `backend/app/integrations/label_studio.py` — does not exist.
- `frontend/app/verify/page.tsx` — currently a coming-soon stub (per F-39).
- `/api/v1/verify/claim` — 501 stub (per F-17).

**Notes:** F-90 is deliberately a **research deliverable**, not runtime work. A research lead can paste the Perplexity prompt to populate the source registry; runtime ingest waits for BUILD-10 + BUILD-12 to land together.

---

### BUILD-11 — ML Training Pipeline 🔲

**Acceptance criteria:**
- Dataset manifest versioned with SHA-256.
- MLflow runs tagged consistently.
- Gate decorators block models that don't meet eval thresholds.
- `ml/registry/promote.py` CLI promotes staging → production.

**What landed:** Nothing.

**What's missing (file-specific):**
- `ml/datasets/manifest.yaml` — does not exist.
- `ml/common/{trainer,gates,registry,mlflow_utils}.py` — none exist.
- Per-module `train_*.py` + `eval.py` — none exist.
- `ml/registry/promote.py` — does not exist.

**Notes:** BUILD-11 is a **prerequisite** for the M3 risk-score classifier and the M4 misinformation classifier. Until it ships, both modules are storage-only.

---

### BUILD-12 — Data Ingestion & Scheduling 🔲

**Acceptance criteria:**
- Source registry covers 20+ sources with ToS notes + cron cadence.
- Spiders + workers parse each source.
- Rate limiter + dedup work.
- Scheduled tasks trigger on cron (APScheduler dev / Celery prod).

**What landed:** Nothing as runtime code. The **Sri-Lankan source registry skeleton** (F-90) is documentation-only.

**What's missing:**
- `backend/app/ingest/registry.py` — does not exist.
- `backend/app/ingest/scrapers/*.py` — none exist.
- `backend/app/ingest/workers/*.py` — none exist.
- `backend/app/ingest/scheduler.py` — does not exist.
- `backend/app/tasks/*.py` (Celery) — does not exist.

**Notes:** Required by BUILD-07 (gazette ingest) and BUILD-10 (social ingest); both deferred together is consistent.

---

### BUILD-13 — Admin Console & Annotation 🟡

**Acceptance criteria:**
- 5 admin pages (regulations, posts, predictions, questions, audit).
- Role guards enforce access.
- Every mutation writes an `audit_log` row.
- Label Studio bidirectional sync.
- Bulk CSV import for questions + examples.

**What landed (admin console half):**
- **F-37, F-38** — Admin response list + user list (read-only).
- **F-53** — `/admin/m2/questions` + `/admin/m2/scores` + `/admin/m3/risk-signals` (read + verify-action).
- **F-67, F-68, F-69** — Survey-flow + regulation services + routers.
- **F-71** — Unified wizard with admin-managed regulation cards.
- **F-74, F-79, F-80, F-81** — Regulations admin CRUD: list + new + edit + verify.
- **F-86, F-91 → F-98** — Sticky sidebar + mobile drawer + `/admin/users` redesign + full CRUD (users + regulations: edit / activate / deactivate / reset-password / delete / archive / restore / duplicate / bulk-verify).

**What's missing:**
- **Label Studio bridge** — `backend/app/integrations/label_studio.py` does not exist (deferred until BUILD-10 needs it).
- **Bulk CSV import** for questions + examples — not built.
- **Audit-log browsing UI** — every mutation writes a row, but there's no `/admin/audit` page yet.
- **Postgres trigger enforcing append-only** on `audit_log` — invariant is convention-only.

**Notes:** The admin surface for *regulations* and *users* is **complete and polished** post-Session-10; remaining BUILD-13 work is annotation-side (Label Studio + bulk CSV), which is M4-driven.

---

### BUILD-14 — Deployment Cloud 🔲

**Acceptance criteria:**
- `docker-compose.yml` (prod, blue/green) + nginx.conf with Let's Encrypt + 3 Dockerfiles + GHCR-pushing CI/CD + nightly backup.

**What landed:** Nothing.

**What's missing (file-specific):**
- `docker-compose.yml` (prod, distinct from `docker-compose.dev.yml`) — does not exist.
- `infra/docker/{backend,frontend,ml}.Dockerfile` — none exist.
- `infra/nginx/nginx.conf` — does not exist.
- `.github/workflows/deploy.yml` — does not exist.
- `infra/deploy/{provision,deploy,backup}.sh` — none exist.

**Notes:** Required for any production push. The dev compose at the repo root (`docker-compose.dev.yml`) is **dev-only** and not production-suitable.

---

### BUILD-15 — Observability & Testing 🟡

**Acceptance criteria:**
- `GET /metrics` exposes module counters + latency histograms.
- Logs include `correlation_id` + `service` + `module`.
- Test coverage ≥ 70 % backend, ≥ 80 % frontend.
- E2E for happy path; load test scripts present.

**What landed (smoke surface):**
- **F-40** — Backend integration test (httpx + Postgres testcontainers).
- **F-41** — Backend unit test for `core/security` (bcrypt + JWT round-trip).
- **F-42** — Playwright E2E `auth_survey_admin.spec.ts`.
- **F-56** — Backend unit + integration tests for M2 scoring + M2/M3 flow + Playwright extension.
- **F-60, F-62** — Troubleshooting docs + `make doctor` diagnostic toolkit (catches ~30 + runtime failure modes).

**What's missing:**
- `core/metrics.py` (Prometheus counters / histograms) — does not exist.
- `core/middleware.py` (correlation-id) — does not exist.
- `GET /metrics` — not exposed.
- OpenTelemetry tracing — not wired.
- Grafana dashboards — not built.
- k6 load test scripts — not built.
- Coverage gates in CI — no CI yet (no `.github/workflows/test.yml`).
- Vitest unit-test coverage on the frontend — minimal (only Playwright E2E).

**Notes:** Pragmatic state — runtime code has **no metrics endpoint**, but development-time diagnostics (logs, troubleshooting, `make doctor`) are robust. Production observability waits for BUILD-14 deployment.

---

## Open BUILD-level questions

From [`BUILD_00_INDEX.md`](../shared/BUILD_PLAN/BUILD_00_INDEX.md) and [`FEATURES.md`](FEATURES.md) "Open questions":

| OQ | Topic | Status post-Session-10 |
|---|---|---|
| OQ1 | Library version pinning | Still open. Pinned where it bit us (`bcrypt>=4.0,<4.1` per F-57); blanket pin deferred until thesis-reproducibility review. |
| OQ2 | Per-module hyperparameters (LR, batch, epochs) | Still open. Deferred until BUILD-11 ships and a model trains. |
| OQ3 | Ethics committee approval reference | Still open. NEDA-partnership-dependent. |
| OQ4 | NEDA partnership confirmation | Still open. Pursued out-of-band; not a code blocker. |
| OQ5 | `survey_responses.question_id` versioning policy | **RESOLVED** — append-only, version-prefixed (`awareness.v1.qNN`). Confirmed in Session 6 + survives the Session-9 dotted-id fix (F-89 / F-99). |
| OQ6 | Server-side `confirmPassword` validation | Still open. Frontend-zod-only; revisit when password policy tightens. |
| OQ7 | Translate SETUP into Sinhala / Tamil | **RESOLVED — no.** Engineering docs stay English; UI is trilingual. |
| OQ8 | Regulation cards from RAG vs curated `summary` | Still open until BUILD-08 §7 RAG ships. |
| OQ9 | Eager vs lazy `m2_knowledge_scores` recompute | **RESOLVED — eager.** One cache row per submit (F-48). |
| OQ10 | Resume-from-mid-survey policy | **RESOLVED — replay `survey_responses`** (F-67). |
| OQ11 | M3 unified-flow projection | **RESOLVED — write to `survey_responses` canonically + project to M3 tables on the way out** (F-70). |
| OQ12 | `/admin/m2/questions` URL after generalisation | Open — provisional redirect to `/admin/questions?module=2` once F-77 Phase B lands. |
| OQ13 → OQ28 | Slice-specific decisions | Mostly resolved during the sessions that introduced them; see [`SESSIONS.md`](SESSIONS.md) "Decisions" subsections. |

---

## Recommended next slices

In ROI order, smallest blast radius first:

1. **Resolve F-77 Phase B — generalised `/admin/questions` UI + backend admin survey-questions endpoint.** Backend prerequisite is small (`GET / POST / PATCH /api/v1/admin/survey-questions` with a `module_number` filter); frontend reuses the existing Combobox + filter rail patterns. Closes the admin half of the survey system.
2. **Resolve F-75 + F-76 — backend tests for the unified flow + admin regulations + a Playwrig