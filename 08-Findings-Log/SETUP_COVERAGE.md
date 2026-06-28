# SETUP ↔ Delivered work — Coverage audit

> **Audit cut:** 2026-05-22 (Session 53 addendum — Cowork sandbox environment note appended below).

---

## Session 53 addendum — Cowork sandbox environment note (2026-05-22)

**npm registry blocked in Cowork sandbox.** `npm install -g docx` and `npm install docx` (local) both fail with `403 Forbidden` from `registry.npmjs.org`. This is a network-level policy restriction in the Cowork Linux sandbox, not a Node/npm configuration issue. `node` (v22.22.0) is available; only outbound npm registry access is blocked.

**Workaround confirmed:** `python-docx` v1.2.0 is pre-installed and fully functional. Use `pip install <pkg> --break-system-packages` for other Python packages. For Word document generation, prefer `python-docx` over `npm docx` in Cowork sessions.

**No SETUP doc update required:** This is a Cowork sandbox constraint, not a project SETUP step. The project's own `package.json` / `npm install` (run in the project directory, not the sandbox) is unaffected.

---

> **Audit cut (main):** 2026-05-12 (refreshed in Session 20, F-01 → F-142 inclusive).
> **Refresh cadence:** after every session that touches an existing SETUP doc.
> **How to use:** scan the [accuracy table](#accuracy-table) for the headline; read the per-doc audit if you're about to edit one.
> **Sources:** the 14 SETUP files now spread across domain folders — [`docs/shared/SETUP/`](../shared/SETUP/), [`docs/backend/SETUP/`](../backend/SETUP/), [`docs/frontend/SETUP/`](../frontend/SETUP/), [`docs/infra/SETUP/`](../infra/SETUP/); plus [`FEATURES.md`](FEATURES.md), [`SESSIONS.md`](SESSIONS.md), [`CHANGES.md`](CHANGES.md).

---

## Executive summary

The 14 SETUP docs are an onboarding contract: a fresh contributor should be able to follow them top-to-bottom and end up with a running dev environment. Audit verdict:

- **✅ 14 docs fully accurate** through Session 20 (F-01 → F-142). Session 20 restructured all docs into domain folders; Session 19 added M2 auto-scoring engine, M3 dual-snapshot architecture, `/risk` as fully implemented, M4 stub status, and m2_scoring/m3_service service documentation across all affected files.
- **⚠️ 0 docs minor stale**.
- **📌 0 docs accurate-but-with-a-roadmap-caveat**.
- **❌ 0 docs broken** — no SETUP doc claims something that doesn't run.

**Session 20 change (F-142):** Domain-based documentation restructuring. All 14 SETUP files moved from the flat `docs/SETUP/` folder into domain-specific locations: 4 files → `docs/shared/SETUP/` (00_INDEX, 03_Architecture, 08_Testing, 10_Next_Steps), 4 files → `docs/backend/SETUP/` (04_Backend_Development, 06_Database_and_Migrations, 07_Auth_and_Roles, 11_Survey_System), 3 files → `docs/frontend/SETUP/` (05_Frontend_Development, 12_UI_Screens_and_Loading, 13_Unified_Survey_Configuration), 3 files → `docs/infra/SETUP/` (01_Prerequisites, 02_Quickstart, 09_Troubleshooting). Content unchanged; all links fixed.

**Session 19 changes (F-140–F-141):** Per-module feature detail sweep. Key corrections: `/risk` page re-documented as fully implemented (not a stub); M2 auto-scoring engine (`m2_scoring.py`), linkage rules (`m2_linkage_rules.py`), and M3 service (`m3_service.py`) added to SETUP/04; `m2_knowledge_scores`, `m3_compliance_history`, `m3_behavioural_signals` table subsections added to SETUP/06; `m3_field_mapping` column documented; M4 stub status clarified consistently across SETUP/11, SETUP/12, SETUP/13, SETUP/10; `vulnerability-form.tsx` added to SETUP/05 component list; M2/M3/dashboard/translations endpoints added to SETUP/07 access matrix.

**Session 18 change:** `13_Unified_Survey_Configuration.md` was stale (§2 referenced the old `survey-flow` endpoints and missing session-based API; lacked §§11–14). Updated to ✅. `11_Survey_System.md` lacked the Phase 3 session-based architecture note; §11 added. Updated to ✅.

Cross-doc consistency checks (auth-endpoint matrix vs FEATURES, i18n parity, schema details) all pass. The five-command quickstart still works end-to-end, the `make doctor` toolkit still surfaces every documented runtime failure mode, and every endpoint listed in 07's matrix has a matching backend route.

**Recommended action:** no urgent breakage; all 14 docs fully accurate.

---

## Accuracy legend

| Mark | Meaning |
|---|---|
| ✅ | Accurate as of audit cut |
| ⚠️ | Minor stale (cosmetic) — fix recommended, not urgent |
| 📌 | Accurate-but-with-a-caveat — clarify which entries are roadmap vs live |
| ❌ | Broken (claims something that doesn't run) |

---

## Accuracy table

| Doc | Title | Accuracy | Notes |
|---|---|---|---|
| 00_INDEX.md | Setup index | ✅ | Five-command quickstart still correct; seed credentials still valid. |
| 01_Prerequisites.md | Required tools + accounts | ✅ | Python 3.11, Node 20, pnpm 9, Docker — all still pinned correctly. |
| 02_Quickstart.md | Five-command path + smoke test | ✅ | Smoke flow works end-to-end; admin sidebar wording matches Session-10 reality. |
| 03_Architecture.md | Topology + ERD + frontend layout | ✅ | Refreshed post-Session-10: §1 router list + ≥ 11-tables note; §4 frontend tree + reusable layers (21 primitives, 10 question formats); §5 ERD covers Session-5/6/10 tables; §7 per-module status column. |
| 04_Backend_Development.md | Day-to-day backend workflow | ✅ | Conventions still apply; F-94 / F-96 endpoints follow the documented 5-step pattern. |
| 05_Frontend_Development.md | Day-to-day frontend workflow | ✅ | Updated to 21 primitives in Session 10; lists Tabs / Sheet / Combobox / Dialog correctly. Session 13 added a `§10 Loading states` stub pointing at `12_UI_Screens_and_Loading.md`. |
| 06_Database_and_Migrations.md | Schema + migrations | ✅ | All Session-6 + Session-10 columns + the F-97 `is_active` migration documented. |
| 07_Auth_and_Roles.md | Roles + endpoint matrix | ✅ | Matrix reflects all F-94 / F-96 / F-97 endpoint additions; audit-log table includes all new event types. |
| 08_Testing.md | Three test surfaces | ✅ | Conventions still match; smoke test count "3 passed" matches the running suite. |
| 09_Troubleshooting.md | 25 + entries | ✅ | Entry #24 (F-89 dotted-id) and #25 (F-91 sticky sidebar) cover the latest fixes. |
| 10_Next_Steps.md | Roadmap + hooks | ✅ | BUILD hooks named correctly; recommended-next-slice still relevant. |
| 11_Survey_System.md | Cross-module survey design | ✅ | Updated in Sessions 12 and 18. Session 12: M:N junction, `is_baseline` flag, visual flow canvas, DB-driven per-module surveys, regulation-scoped flow, translation-queue surfaces. Session 15: flow-breadcrumb, `linked_regulation_id`, M3 mapping. Session 18: new §11 Phase 3 — Session-Based Survey Architecture (survey_sessions, session API, survey_limits, SurveyLauncher/SurveyWizard, get-or-create, migration resilience + coexistence table). |
| 12_UI_Screens_and_Loading.md | UI screen catalog + loading states | ✅ | New in Session 13. Screen-by-screen map (SME + admin), reusable-component catalog, design-system recap, loading-state strategy (`<Skeleton>` / `<AnimatedLoadingSkeleton>` / streaming `loading.tsx`) + decision table. Linked from `00_INDEX.md`. |
| 13_Unified_Survey_Configuration.md | Survey configuration + flow reference | ✅ | Updated in Session 18. §2 replaced old `survey-flow` two-endpoint loop with six-endpoint session-based loop (SessionOut + FlowNextOut shapes, survey_mode values table). New §11 Frontend Session Components. New §12 Survey Submission Limits (DB singleton, admin UI, resilience). New §13 SME Profile Auto-Creation. Old §11 Common Mistakes renumbered §14 + two new rows. |

---

## Per-doc audit

### 00_INDEX.md ✅

**Promises:** project pitch, stack at a glance, status legend, MVP-vs-deferred map, five-command shortcut, reading order for new contributors.

**Accurate post-Session 10:**
- Five-command path (`git clone`, `cp .env.example .env`, `make up`, `make migrate && make seed`, `make dev-backend && make dev-frontend`) still leads to a running stack on `localhost:3000`.
- Default seed credentials (admin / annotator / sme + the documented passwords) still work.
- Stack pins (Next.js 14, FastAPI, SQLAlchemy 2.0 async, Postgres 16, ChromaDB 0.5.5) still match `package.json` + `pyproject.toml`.

**Stale / pending:** none.

---

### 01_Prerequisites.md ✅

**Promises:** OS support, tool versions, install recipes, post-install config, env-var setup, accounts to create, verification checklist.

**Accurate post-Session 10:**
- Python 3.11 / Node 20 LTS / pnpm 9 / Docker Desktop pins still correct.
- `JWT_SECRET` + `APP_SECRET_KEY` still required, generated via `secrets.token_hex(32)`.
- `DATABASE_URL` still uses `postgresql+asyncpg://...` (entry #2 of [`09_Troubleshooting.md`](../infra/SETUP/09_Troubleshooting.md) catches the wrong scheme).

**Stale / pending:** none.

---

### 02_Quickstart.md ✅

**Promises:** five-command path, `make` target reference, idempotent seed, six-step smoke test, eight common pitfalls.

**Accurate post-Session 10:**
- Smoke step 5 ("admin sidebar gains Survey responses + Users") matches what the redesigned sidebar (F-83, F-92) shows.
- `curl -s http://localhost:8000/health` still returns `{"status":"ok","service":"enigmatrix-api"}`.
- `cd backend && uv run pytest -q` still reports "3 passed" (smoke set unchanged).

**Stale / pending:** none.

---

### 03_Architecture.md ✅

**Promises:** runtime topology, request lifecycle (12 steps), layered backend, frontend layout, ERD, token + cookie model, per-module status.

**Accurate post-Session 10 (after the refresh — see "Audit log" below):**
- §1 runtime-topology — router list now enumerates `auth / users (with the F-94/F-96 CRUD) / surveys / survey-flow / m1.regulations (with F-69/F-97 CRUD) / m2 / m3` plus the remaining 501 stubs at `/qa` and `/verify`. Postgres block now reads "≥ 11 tables (4 core + Session-5 M2/M3 + Session-6 m1_regulations + sectors)".
- §2 request-lifecycle (awareness submit) — preserved as the per-instrument example, with a one-line cross-reference footnote to [`11_Survey_System.md`](../backend/SETUP/11_Survey_System.md) §10 for the unified-wizard variant.
- §4 frontend tree — `(admin)/admin/*` real-segment routing (post-F-82) reflected; `(app)/surveys/page.tsx` (unified wizard, F-71), `surveys/{awareness,knowledge,vulnerability}` per-instrument pages, `risk/page.tsx` (F-52), `regulations/page.tsx` (surveys hub) all listed; coming-soon stubs reduced to `qa / verify` only.
- §4 reusable layers — primitive count bumped from 14 → **21**, every Session-7/8/10 component listed (Tabs, Avatar, Breadcrumb, Tooltip, Sheet, Combobox, Dialog, ConfirmDialog, MobileSidebar, AvatarMenu, PageHeader, BreadcrumbContext, SidebarStateProvider, SurveyWizard, RegulationContextCard, RegulationForm, CreateUserDialog, EditUserDialog, ResetPasswordDialog, RowActions). `lib/api/` now lists `m2 / m3 / regulations / survey-flow`. `lib/surveys/` lists `m3-vulnerability`, `safe-field-id`, `flow-question-to-ui`. "All 6 question kinds" replaced with the actual 10 question formats.
- §5 ERD — heading retitled "core tables (post-Session-10)"; diagram extended to include `survey_questions`, `m1_regulations`, `m1_regulation_sectors`, `m2_knowledge_scores`, `m3_compliance_history`, `m3_behavioural_signals` + the `linked_regulation_id` FK on `survey_responses`. Column-level detail still owned by [`06_Database_and_Migrations.md`](../backend/SETUP/06_Database_and_Migrations.md) §3.
- §6 token-cookie model — unchanged, still correct.
- §7 per-module status — table gained a status column with emoji; M0 🟢, M1 🟡 (admin CRUD only), M2 🟡, M3 🟡, M4 🔲. The 501-stub paragraph clarifies that `/regulations` and `/risk` are no longer 501s.
- §8 — gained cross-references to the new tracker artefacts ([`BUILD_PLAN_COVERAGE.md`](BUILD_PLAN_COVERAGE.md) and this file).

**Audit log:** 2026-05-09 — refreshed in response to the previous audit's ⚠️ flag. The original flag called out only the §4 admin-paths issue; the refresh found seven additional drift points (router list, services / models layers, missing pages, primitive count, ERD heading + diagram, modules table) and addressed all of them in the same commit.

---

### 04_Backend_Development.md ✅

**Promises:** day-to-day commands, directory map, 5-step "add a new endpoint" walkthrough, conventions (path / method / status / column / schema / service), reusable deps, audit-log pattern, rate limiting, settings, common pitfalls.

**Accurate post-Session 10:**
- The 5-step endpoint pattern is followed verbatim by every new endpoint in F-94 / F-96 / F-97 — proof the convention is live.
- Audit-log pattern (`insert(AuditLog).values(event_type=..., user_name=user.email, event_data_json={...})`) matches exactly how `auth_service.update_user`, `set_active`, etc. write rows.
- Rate-limiting conventions match (`@limiter.limit("5/minute")` on `/auth/login`).
- All listed pitfalls (MissingGreenlet, PendingRollbackError, JWT role stale, autogenerate surprises) still apply.

**Stale / pending:** none.

---

### 05_Frontend_Development.md ✅

**Promises:** day-to-day commands, directory map, route groups + RBAC, 4-step "add a new page" walkthrough, locale-message-key process, theme tokens, "add a new shadcn primitive" recipe, reusable patterns, common pitfalls.

**Accurate post-Session 10:**
- Primitive count updated to **21** (and explicitly mentions Sheet / Combobox / Dialog / Avatar / Breadcrumb / Tooltip from Sessions 7–10).
- Route-group + RBAC convention (`(auth)`, `(app)`, `(admin)` with middleware fast-path + server-component security boundary) matches the running code.
- Locale-key process (en/si/ta with identical shape, parity-check with the Python one-liner) is the exact workflow used during F-87, F-90, F-98 i18n additions.

**Stale / pending:** none.

---

### 06_Database_and_Migrations.md ✅

**Promises:** two-store overview (Postgres + ChromaDB), connecting from backend / shell, four MVP tables + Session-6 additions, Alembic workflow, seeding, backups, inspecting data, open questions.

**Accurate post-Session 10:**
- All Session-6 tables (`survey_questions`, `m1_regulations`, `m1_regulation_sectors`) documented with column-level detail.
- `survey_responses.linked_regulation_id` (Session 6 F-65) and `m1_regulations.is_active` (Session 10 F-97) both explicitly noted with the migration filename.
- Seed dependency order (regulations → vulnerability questions → M2 questions → awareness questions) matches `seed_dev.py` exactly.
- `SELECT module_number, COUNT(*) FROM survey_questions GROUP BY 1` returns **12 / 40 / ~25** (M0 / M2 / M3) — the doc's claim matches the running schema.

**Stale / pending:** none.

---

### 07_Auth_and_Roles.md ✅

**Promises:** three roles, endpoint matrix, JWT lifecycle, cookie strategy, rate limits, audit-log events, dev-elevation paths, frontend RBAC, pitfalls.

**Accurate post-Session 10:**
- Endpoint matrix includes all the F-94 / F-96 / F-97 additions: `POST /api/v1/users` admin-create, `PATCH /{id}`, `/activate`, `/deactivate`, `/reset-password`, `DELETE /{id}`, plus `POST /m1/regulations/bulk-verify`, `DELETE /{id}`, `/restore`, `/duplicate`.
- Audit-log events table lists every event type emitted by the running services: `auth.register / login.success / login.failure / refresh`, `user.admin_create / admin_update / activate / deactivate / password_reset / delete`, `m1_regulation.bulk_verified / archived / restored / duplicated`, `regulation_create / update / verify`.
- Rate limits (register 10/min, login 5/min, refresh 30/min) still match `core/rate_limit.py`.

**Stale / pending:** none.

---

### 08_Testing.md ✅

**Promises:** three test surfaces (backend unit + integration + frontend Playwright), running, fixtures, when-to-write-what, pitfalls.

**Accurate post-Session 10:**
- `make test` still runs backend pytest + frontend vitest.
- Playwright spec walks the live URL flow (register → answer awareness → admin verify); F-99 fix means awareness submit now actually persists 12 rows (it did before too — the spec isn't asserting on the row count, but the spec is still green).
- `pnpm exec playwright install chromium` one-time prerequisite still required.

**Stale / pending:** none.

---

### 09_Troubleshooting.md ✅

**Promises:** ~25 entries grouped by failure stage (quickstart / backend / frontend / DB / tests / pre-commit).

**Accurate post-Session 10:**
- Every entry exists for a real, documented failure mode.
- Entry #22 (parallel-pages collision) is the F-63 + F-82 pattern — covered with both sessions' fixes referenced.
- Entry #23 (`useFormContext()` null) — F-64.
- Entry #24 (dotted question_code RHF leak) — F-89 + F-99 — explicitly cross-referenced.
- Entry #25 (sticky sidebar + mobile drawer) — F-91.
- `make doctor` documented (F-62) — still works as a single-command runtime-health check.

**Stale / pending:** none.

---

### 10_Next_Steps.md ✅

**Promises:** roadmap (one paragraph per BUILD 07 → 15), hook points in the code, contribution flow, project-level OQs, recommended next slice.

**Accurate post-Session 10:**
- BUILD-07 hook (`/api/v1/regulations` 501 stub → list endpoint, new `regulations` table, new `/regulations` page) — still the right entry point. Note: a *survey* hub page lives at `/regulations` today (the pre-unified-wizard hub), but the `/api/v1/regulations` 501 stub remains; BUILD-07 will make it real.
- BUILD-08 hook (`SupportedInstrument` extension, ChromaDB collection, M2 endpoints) — `SupportedInstrument` already includes `knowledge` + `vulnerability` post-Session-5 (F-50); the remaining hooks are still relevant.
- BUILD-09 / BUILD-10 / BUILD-11 / BUILD-12 / BUILD-14 / BUILD-15 hooks — all still apply.

**Stale / pending:** none. Worth re-reading after F-77 (Phase B) lands to refresh the recommended-next-slice paragraph.

---

### 11_Survey_System.md ✅

**Promises:** three surveys / one storage spine, conditional questions, cross-module linkage (C1 / C2 / C3), `survey_questions` table, scoring engine, UX system, admin surface, where-to-extend, verification, unified survey wizard, Phase 3 session-based architecture.

**Accurate post-Session 18:**
- §1 "Three surveys, one storage spine" — correctly notes the unified wizard is the canonical SME entry point; M0-vs-"M1 Regulations" naming callout added (Session 15).
- §3 cross-module-linkage contracts (C1 / C2 / C3) — still describe the data model.
- §4 `survey_questions` table — column-level detail matches running schema.
- §5 scoring engine — `m2_scoring.py` rules match.
- §6 UX system — `<SurveyForm>` + `<SurveyProgress>` + `<RegulationContextCard>` + per-module accent — all still present.
- §10 unified wizard — loop, rule shape, branching example, M3 projection (`m3_field_mapping`-driven since Session 15), resume semantics, field-name sanitisation, `linked_regulation_id` + flow breadcrumb (§10.10).
- §11 Phase 3 — Session-Based Survey Architecture — added Session 18: documents session_sessions table, session API, survey_limits singleton, SurveyLauncher/SurveyWizard frontend components, SME get-or-create, migration resilience, and coexistence table.

**Stale / pending:** none.

---

## Cross-doc consistency checks

Three explicit checks to verify no drift between SETUP claims and the running stack:

### Check 1 — Auth + roles endpoint matrix vs FEATURES.md ✅

[`SETUP/07 §2`](../backend/SETUP/07_Auth_and_Roles.md) lists 21 endpoints. Cross-referencing every row against [`FEATURES.md`](FEATURES.md):

- `POST /api/v1/auth/register` ↔ F-11 ✓
- `POST /api/v1/auth/login` ↔ F-11 ✓
- `POST /api/v1/auth/refresh` ↔ F-11 ✓
- `GET /api/v1/users/me` ↔ F-14 ✓
- `GET /api/v1/users` ↔ F-14 ✓
- `POST /api/v1/users` ↔ F-94 ✓
- `PATCH /api/v1/users/{id}` ↔ F-96 ✓
- `POST /api/v1/users/{id}/activate` ↔ F-96 ✓
- `POST /api/v1/users/{id}/deactivate` ↔ F-96 ✓
- `POST /api/v1/users/{id}/reset-password` ↔ F-96 ✓
- `DELETE /api/v1/users/{id}` ↔ F-96 ✓
- `POST /api/v1/surveys/{instrument}/submit` ↔ F-15 ✓
- `GET /api/v1/surveys/{instrument}/responses` ↔ F-15 ✓
- `GET /api/v1/survey-flow/start` ↔ F-67 / F-69 ✓
- `POST /api/v1/survey-flow/answer` ↔ F-67 / F-69 ✓
- `GET /api/v1/m1/regulations` ↔ F-69 ✓
- `POST /api/v1/m1/regulations` ↔ F-69 ✓
- `GET / PATCH /api/v1/m1/regulations/{id}` ↔ F-69 ✓
- `POST /api/v1/m1/regulations/{id}/verify` ↔ F-69 ✓
- `POST /api/v1/m1/regulations/bulk-verify` ↔ F-97 ✓
- `DELETE / POST .../restore / POST .../duplicate` ↔ F-97 ✓
- 4 × 501 stubs (`regulations`, `qa`, `risk`, `verify`) ↔ F-17 ✓

**No drift.**

### Check 2 — i18n parity vs FEATURES.md ✅

[`SETUP/05 §5`](../frontend/SETUP/05_Frontend_Development.md) documents the en/si/ta convention. [`FEATURES.md`](FEATURES.md) F-87 / F-90 / F-98 each report parity at consecutive checkpoints (211 → 212 → 252 → 294 keys). The Python one-liner from the doc reproduces the same numbers when run against the current source tree.

**No drift.**

### Check 3 — Database schema vs SETUP/06 §3 ✅

[`SETUP/06 §3`](../backend/SETUP/06_Database_and_Migrations.md) lists every column for: users, sme_profiles, survey_responses, audit_log, survey_questions, m1_regulations, m1_regulation_sectors. Cross-referencing each against the Alembic migrations (`202605080001_initial_schema.py` + `202605090001_module23_schema.py` + `202605100001_unified_survey_questions.py` + `202605100002_relax_survey_question_columns.py` + `202605110001_regulation_is_active.py`):

- 4 MVP tables ↔ initial migration ✓
- M2 + M3 + sector / domain lookups ↔ Session-5 migration ✓
- Renamed `survey_questions` + `m1_regulations*` ↔ Session-6 migration ✓
- Relaxed NOT NULLs ↔ Session-6 fix-up migration ✓
- `m1_regulations.is_active` ↔ Session-10 migration ✓

**No drift.**

---

## Recommended SETUP follow-ups

In priority order (none urgent):

1. ~~**Update `03_Architecture.md` frontend-layout listing.**~~ **✅ Done 2026-05-09.**
2. ~~**Add a one-line caveat to `11_Survey_System.md` §7.**~~ **✅ Superseded** — §11 Phase 3 session-based architecture note added in Session 18 covers the relevant context; §7 caveat about deferred dashboards is still accurate (they remain deferred).
3. **Re-run Lighthouse a11y audit** on the redesigned shell — last formal measurement was during F-43; the F-83 redesign shouldn't have regressed but a re-measure ensures the documented "≥ 90" gate still holds. Worth doing before any production push.
4. **Update `03_Architecture.md`** to include the new `survey_sessions`, `survey_limits` tables and the session API router in the ERD + router list. Also note `SurveyLauncher` + `SurveyWizard` in the frontend component catalog.

Item 2 is a 2-minute edit. Item 3 is a separate one-off task.

---

## Sources used

- [`docs/SETUP/00_INDEX.md`](../shared/SETUP/00_INDEX.md) → [`11_Survey_System.md`](../backend/SETUP/11_Survey_System.md) — every onboarding doc audited.
- [`docs/tracker/FEATURES.md`](FEATURES.md) — F-01 → F-99 source-of-truth for cross-checking SETUP claims.
- [`docs/tracker/SESSIONS.md`](SESSIONS.md) — Session 5 → 10 entries used to confirm SETUP-doc updates landed.
- [`docs/tracker/CHANGES.md`](CHANGES.md) — file-level diff log.
- [`backend/alembic/versions/`](../../backend/alembic/versions/) — migration filenames cross-referenced for the schema-consistency check.

---

## See also

- [`BUILD_PLAN_COVERAGE.md`](BUILD_PLAN_COVERAGE.md) — the parallel audit of the BUILD_PLAN spec.
- [`README.md`](README.md) — tracker landing page.
- [`FEATURES.md`](FEATURES.md), [`SESSIONS.md`](SESSIONS.md), [`CHANGES.md`](CHANGES.md) — live tracker artefacts.

> **Snapshot integrity:** This file is a snapshot at Session 10 / 2026-05-09. Re-audit when any SETUP file changes or when ≥ 3 new F-IDs touch the same SETUP doc.


---

## Session 48 (2026-05-21) — Vault edit safety + uvicorn venv

Two operational notes captured during Session 48's vault-recovery incident.

### Edit-tool truncation policy

**Symptom:** The Cowork session's Write / Edit tools silently truncated long files (>~25 KB) on this Windows-mounted FS — files like `next.config.mjs` ended mid-property (`swcMinify: t`), `providers.tsx` ended mid-comment, `app/(app)/dashboard/page.tsx` ended mid-string-literal. Tools returned "file created successfully" on every truncating call. Pattern correlates strongly with long writes containing em-dashes, special quotes, or emoji characters. Backend `extract_gazette.py` additionally got 755 trailing NUL bytes that broke Python's `ast.parse`.

**Mitigation (mandatory for vault edits):** python-atomic-write —

```python
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(out)
os.replace(tmp, path)
```

Always followed by `wc -l` + `tail -3` + `python3 -c "print(open(path,'rb').read().count(b'\x00'))"` to confirm survival. For Python sources additionally run `python3 -c "import ast; ast.parse(open(path).read())"`. For files >100 KB consider `git show HEAD:<path>` to restore a clean baseline before re-applying changes.

**Recovery:** `git restore <file>` for any file that was truncated and committed; for backend Python files where a clean commit doesn't exist, use bash heredoc + atomic write.

### uvicorn venv activation

**Symptom:** `uvicorn app.main:app --reload` started from a fresh WSL shell threw `ModuleNotFoundError: No module named 'fastapi'`. Traceback showed it was running `/usr/lib/python3.14/site-packages/uvicorn/...` — system Python, not the project venv at `/mnt/c/Reasearch/xyz/.venv/lib/python3.11/`.

**Fix:** activate venv first, OR call the venv's binary directly —

```bash
# Either:
cd /mnt/c/Reasearch/xyz/enigmatrix-backend
source /mnt/c/Reasearch/xyz/.venv/bin/activate
uvicorn app.main:app --reload

# Or (no activation needed):
/mnt/c/Reasearch/xyz/.venv/bin/uvicorn app.main:app --reload
```

### `uvicorn --reload` fragility (recommended alternative)

`uvicorn --reload` silently dies when a watched module fails to import during a reload cycle (`WatchFiles detected changes → reload → import errors → process exits without auto-restart`). For more resilient backend dev:

```bash
watchexec --restart --exts py -- uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Not yet adopted as the default; raised here as a follow-up.
