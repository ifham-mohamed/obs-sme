# 06 — Database & Migrations

> **Goal:** know what's in the dev database today, and how to evolve the schema without breaking it.
>
> **Prerequisite:** [`02_Quickstart.md`](02_Quickstart.md) — `make up && make migrate && make seed` succeeded at least once.

---

## 1. Two stores, two responsibilities

| Store | Holds | Status in MVP |
|-------|-------|--------------|
| **PostgreSQL 16** | The single source of truth: users, profiles, survey responses, audit log, the unified survey-question bank (M1/M2/M3), and the admin-managed regulation bank. | Active. Core 4 tables + M2/M3 schema (Session 5) + unified `survey_questions` and `m1_regulations*` (Session 6). |
| **ChromaDB 0.5.5** | Vector embeddings for the regulation corpus (Module 2 RAG). | Wired (compose service + env vars + client helper) but **unused** in the MVP. Activated by [`BUILD_08`](../BUILD_PLAN/BUILD_08_Module2_Knowledge.md). |

**Rule:** never duplicate authoritative data. Anything in ChromaDB or `ml/artifacts/` is a *derivative* — if it disappears, it must be reproducible from Postgres + the original source.

---

## 2. Connecting

### From the backend

[`backend/app/db/session.py`](../../backend/app/db/session.py) builds the async engine from `DATABASE_URL`. Default in [`.env.example`](../../.env.example):

```
DATABASE_URL=postgresql+asyncpg://enigmatrix:devpass@localhost:5432/enigmatrix
```

The `postgresql+asyncpg://` scheme is **required**. Plain `postgresql://` silently picks the sync driver and breaks every async session — see [`09_Troubleshooting.md`](09_Troubleshooting.md).

### From your shell (`psql`)

```bash
PGPASSWORD=devpass psql -h localhost -p 5432 -U enigmatrix -d enigmatrix
```

Some inspections you'll want often:

```sql
\dt                                              -- list tables
\d users                                         -- describe table
SELECT id, email, role FROM users ORDER BY created_at DESC LIMIT 10;
SELECT survey_instrument, COUNT(*) FROM survey_responses GROUP BY 1;
SELECT event_type, COUNT(*) FROM audit_log GROUP BY 1 ORDER BY 2 DESC;
```

---

## 3. The four MVP tables

DDL source → [`backend/alembic/versions/202605080001_initial_schema.py`](../../backend/alembic/versions/202605080001_initial_schema.py).
ORM source → [`backend/app/models/`](../../backend/app/models/).

### `users`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | `gen_random_uuid()` default. |
| `email` | text, **unique**, indexed | Login identity. |
| `password_hash` | text | bcrypt via [`core/security.py`](../../backend/app/core/security.py). |
| `role` | text | `'sme' \| 'admin' \| 'annotator'` — enforced in app, not as a DB CHECK (yet). |
| `preferred_language` | text | `'en' \| 'si' \| 'ta'`. |
| `is_active` | bool | Login refuses if `false`. |
| `created_at`, `updated_at` | timestamptz | `TimestampMixin`. |

### `sme_profiles`

| Column | Type | Notes |
|--------|------|-------|
| `sme_id` | UUID PK | Stable identifier independent of `users.id`. |
| `user_id` | UUID FK `users.id` ON DELETE CASCADE, **unique** | One-to-one. |
| `sector`, `sub_sector`, `region`, `primary_language` | text | Free-form for the MVP; will be referenced from sector / region tables in a later slice. |
| `employee_count_band` | text | `'1-10' \| '11-50' \| '51-200'`. |
| `annual_turnover_band` | text | Recommended values use the **April 2026** thresholds (e.g. `lt_36M`, `36M_100M`). Never re-introduce 60M. See [`docs/research/06_Data_Collection_and_Management.md`](../../shared/research/06_Data_Collection_and_Management.md). |
| `business_age_years` | int | 0–200. |
| `consent_given`, `consent_text_version` | bool, text | Future-proofing for ethics chapter. |
| `created_at`, `updated_at` | timestamptz | |

`auth_service.register()` always creates an `sme_profile` row, even when the registration form sent no profile fields — so `survey_responses.sme_id` always has a target.

### `survey_responses`

Long-form: **one row per (sme, instrument, question, submission)**. Multiple rows share the same `submitted_at` value when they came in via one transaction (which is how the admin list groups them).

| Column | Type | Notes |
|--------|------|-------|
| `response_id` | UUID PK | |
| `sme_id` | UUID FK `sme_profiles.sme_id` ON DELETE CASCADE | |
| `survey_instrument` | text, indexed | `'awareness'` for now (allow-list in [`schemas/survey.py`](../../backend/app/schemas/survey.py)). |
| `question_id` | text, indexed | Versioned: `'awareness.v1.q07'`. See OQ5 below. |
| `answer_text` | text \| null | Free-text, single-choice value, or comma-joined multi-select. |
| `answer_numeric` | numeric \| null | Likert + numeric questions. |
| `answer_date` | date \| null | Date questions. |
| `submitted_at` | timestamptz, indexed | `now()` default. |
| `linked_regulation_id` | UUID FK `m1_regulations.regulation_id` ON DELETE SET NULL \| null | **Session 6 addition (F-65).** Row-level override of the question-side `linked_regulation_id`. Lets a single answer record which specific regulation it was about. |

Session-5 added the M2/M3 denormalisation columns (`module_number`, `survey_section`, `correct_answer_norm`, `is_correct`, `is_partial`, `score_points`, `version_at_response`); see [`11_Survey_System.md`](11_Survey_System.md) §4.

**Constraint enforced in code, not in the DB:** exactly one of `answer_text`, `answer_numeric`, `answer_date` is non-null per row. See [`survey_service._validate_answer`](../../backend/app/services/survey_service.py).

### `audit_log`

Append-only log of state-changing events. Today only auth events emit rows; broader coverage is in [`BUILD_13`](../../frontend/BUILD_PLAN/BUILD_13_Admin_and_Annotation.md).

| Column | Type | Notes |
|--------|------|-------|
| `log_id` | bigserial PK | |
| `event_type` | text, indexed | Dotted: `auth.register`, `auth.login.success`, `auth.login.failure`, `auth.refresh`. |
| `table_name` | text \| null | Convention: name of the table the event concerns. |
| `record_id` | UUID \| null | Convention: PK of the affected row. |
| `user_name` | text \| null | Convention: actor email. |
| `event_data_json` | JSONB \| null | Free-form context. |
| `occurred_at` | timestamptz, indexed | |

The append-only invariant is a convention today; a Postgres trigger that *enforces* it ships with [`BUILD_13`](../../frontend/BUILD_PLAN/BUILD_13_Admin_and_Annotation.md).

### Session-6 tables — unified survey wizard + admin-managed regulations

DDL source → [`backend/alembic/versions/202605100001_unified_survey_questions.py`](../../backend/alembic/versions/202605100001_unified_survey_questions.py) and the follow-up [`202605100002_relax_survey_question_columns.py`](../../backend/alembic/versions/202605100002_relax_survey_question_columns.py). ORM source → [`backend/app/models/{survey_question,regulation}.py`](../../backend/app/models/).

#### `survey_questions` (renamed from `m2_questions` in Session 6)

The unified question bank for **all three survey modules** (M1 awareness, M2 knowledge, M3 vulnerability). The 40 existing M2 rows are preserved by the rename; awareness and vulnerability rows are added by the new seed scripts (F-66).

| Column | Type | Notes |
|--------|------|-------|
| `question_code` | text PK | e.g. `awareness.v1.q01`, `VAT_FACT_002`, `M3_HIST_001`. |
| `module_number` | int, NOT NULL, default 2 | `1` = awareness, `2` = knowledge, `3` = vulnerability. Drives the response-table routing and the wizard's accent class. Migration `202605180001` renamed this from `0` to `1` for awareness. |
| `domain_code` | text FK `regulatory_domains.domain_code` \| **NULL** | M2 only. F-73 relaxed this from NOT NULL so M1/M3 rows can insert. |
| `sector_code` | text FK `sectors.sector_code` \| null | M2 sector-tailored questions; NULL = universal. |
| `knowledge_type` | text \| **NULL** | M2 only (`factual` / `procedural` / `application` / `exception`). F-73 relaxed this. |
| `question_format` | text, NOT NULL | `mcq_single`, `multi`, `likert`, `numeric`, `date`, `short_text`, `ordered_steps`, `scenario_response`, `open`, `yes_no`. |
| `prompt_en`, `prompt_si`, `prompt_ta` | text | EN required; SI/TA optional. `needs_translation` flags pending. |
| `options_json` | JSONB \| null | Shape varies by `question_format` — see `flow-question-to-ui.ts` for the union. |
| `correct_answer_json` | JSONB \| null | M2 only. Relaxed in `202605100001` so M1/M3 leave it NULL. |
| `scoring_rubric_json` | JSONB \| null | M2 only. Partial-credit rules (e.g. `{"partial_credit": "first_and_last_only"}`). |
| `m3_field_mapping` | JSONB \| null | M3 only. Specifies which snapshot table and column this answer fans out to (e.g. `{"table": "compliance_history", "column": "missed_deadline_24mo"}`). The service falls back to `_M3_DEFAULT_MAPPINGS` when this is null. |
| `linked_regulation_id` | UUID FK `m1_regulations.regulation_id` ON DELETE SET NULL | When set, the wizard renders the regulation-context card before the question. |
| `next_question_rules` | JSONB, NOT NULL, default `[]` | List of `{when: {answer_eq \| answer_in \| answer_lt \| answer_gt: …}, goto_question_code: "…"}`. The flow engine applies the first matching rule; no match → linear fallback by `(instrument_section, sort_order)`. |
| `is_required` | bool, NOT NULL, default true | M3 has optional questions; M1/M2 default true. |
| `instrument_section` | text \| null | Free-form grouping (`history` / `behaviour` / `stress` for M3, domain code for M2). |
| `is_branching_root` | bool, NOT NULL, default false | `true` on the start-of-flow question(s) — `start_flow` looks for the first unanswered branching root. |
| `version`, `is_active`, `sort_order` | text / bool / int | Same semantics as the original `m2_questions`. |
| `created_at`, `updated_at` | timestamptz | |

#### `m1_regulations`

Admin-managed regulation bank. Five canonical rows seeded by `seed_regulations.py` (F-66): `VAT_THRESHOLD_2026`, `VAT_RATE_18PCT_2024`, `EPF_EMPLOYER_12PCT`, `ETF_EMPLOYER_3PCT`, `ROC_ANNUAL_RETURN_30D`. All start with `expert_verified = false` so the admin UI surfaces a "Needs verification" badge.

| Column | Type | Notes |
|--------|------|-------|
| `regulation_id` | UUID PK | `gen_random_uuid()` default. |
| `regulation_short_code` | text, **unique**, indexed | e.g. `VAT_THRESHOLD_2026`. Used by seed scripts and by humans. |
| `document_type` | text, NOT NULL | `bill`, `act`, `extraordinary_gazette`, `weekly_gazette`, `circular`, `order`, `notification`. |
| `document_number` | text \| null | E.g. gazette number. |
| `title_en`, `title_si`, `title_ta` | text | EN required. |
| `summary_en`, `summary_si`, `summary_ta` | text \| null | |
| `principal_act_amended` | text \| null | |
| `cabinet_approval_date`, `bill_published_date`, `gazette_published_date`, `effective_date` | date \| null | All indexed (`ix_m1_regulations_dates` covers the three publication dates). |
| `domain_code` | text FK `regulatory_domains.domain_code` \| null | Indexed. |
| `change_category` | text \| null | E.g. `threshold`, `rate_change`, `procedure`. |
| `severity_level` | smallint \| null | 1–5 likert (admin-edited). |
| `is_sme_relevant` | bool, NOT NULL, default true | |
| `penalty_range_lkr` | text \| null | Free-form (e.g. `LKR 25,000–500,000`). |
| `real_world_example_en`, `..._si`, `..._ta` | text \| null | Surfaced inside the SME-side regulation context card. |
| `source_url` | text \| null | |
| `expert_verified`, `expert_verified_by`, `expert_verified_at` | bool / text / timestamptz | Set by `POST /m1/regulations/{id}/verify`. Also flipped in batch by `POST /m1/regulations/bulk-verify` (Session 10 — F-97). |
| `sme_relevance_confidence` | numeric(3,2) \| null | For the future M1 ingest pipeline (BUILD_07). |
| `is_active` | bool, NOT NULL, default TRUE, indexed | **Session 10 addition (F-97).** Soft-archive flag. `DELETE /m1/regulations/{id}` flips this to FALSE; `POST /{id}/restore` flips back. The admin list filters out archived rows by default (opt-in via `?include_archived=true`); the SME public read 404s archived rows so the unified wizard's context cards stop appearing for archived regulations. Migration: [`202605110001_regulation_is_active.py`](../../backend/alembic/versions/202605110001_regulation_is_active.py). |
| `created_at`, `updated_at` | timestamptz | |

The 4 BUILD_07-only fields (`pdf_*_url`, scrape stage timestamps) from the architecture doc §A3.2 are deliberately omitted in this slice — they ship with the gazette ingest.

#### `m1_regulation_sectors`

M2M between `m1_regulations` and `sectors`. Lets one regulation tag multiple sectors with a per-sector `impact_level`.

| Column | Type | Notes |
|--------|------|-------|
| `regulation_id` | UUID FK `m1_regulations.regulation_id` ON DELETE CASCADE, PK | |
| `sector_code` | text FK `sectors.sector_code`, PK | |
| `impact_level` | smallint \| null | Optional per-sector severity override. |

The unified flow engine queries `survey_questions` filtered by sector + universal; the regulation–sector map is read by the admin UI (F-74) and by future targeting logic.

#### `m2_knowledge_scores` (Session 5 — cached aggregate)

DDL source → migration `202605090001`. One row per (SME, version) — recomputed eagerly on every M2 submit by `m2_service.recompute_knowledge_score()`. The M3 risk-signals endpoint reads this row directly via `GET /api/v1/m2/sme/{sme_id}/knowledge_score` (Contract C2).

| Column | Type | Notes |
|--------|------|-------|
| `score_id` | UUID PK | `gen_random_uuid()` default. |
| `sme_id` | UUID FK `sme_profiles.sme_id` ON DELETE CASCADE | |
| `version` | text | Default `"v1"`. Bumped when the scoring rubric changes incompatibly. |
| `overall_pct` | numeric(5,4) | 0.0–1.0 weighted average across all answered domains. |
| `overall_score_points` | numeric(7,2) | Sum of `score_points` for answered M2 questions. |
| `overall_max_points` | numeric(7,2) | Sum of `score_points` for the question bank (denominator). |
| `by_domain_json` | JSONB | Dict of `domain_code → {pct, n, correct}`. E.g. `{"VAT": {"pct": 0.83, "n": 6, "correct": 5}}`. |
| `instrument_breakdown_json` | JSONB | Dict of `knowledge_type → {pct, n, correct}`. E.g. `{"factual": {...}, "procedural": {...}}`. |
| `computed_at` | timestamptz | When the row was last written. |
| `last_updated` | timestamptz | Timestamp of the most-recent `survey_responses` row that fed this score. |

#### `m3_compliance_history` (Session 5 — append-only snapshots)

DDL source → migration `202605090001`. Append-only — new snapshot on every M3 compliance-history submit. The ML risk model (BUILD_09) will read the most-recent row per SME. Keyed by `(sme_id, snapshot_at)`.

| Column | Type | Notes |
|--------|------|-------|
| `history_id` | UUID PK | |
| `sme_id` | UUID FK `sme_profiles.sme_id` ON DELETE CASCADE | |
| `snapshot_at` | timestamptz | Server `NOW()` default — when the snapshot was written. |
| `missed_deadline_24mo` | bool \| null | Any missed filing deadline in the last 24 months? |
| `missed_count_band` | text \| null | `'1'`, `'2-3'`, `'4-6'`, `'7+'`, `'unknown'`. |
| `missed_kinds_json` | JSONB \| null | List of obligation types missed: `vat_return`, `vat_payment`, `epf`, `etf`, `income_tax_installment`, etc. |
| `penalty_received` | bool \| null | Any penalty received? |
| `penalty_total_band` | text \| null | Categorical band of total penalties paid. |
| `under_audit` | bool \| null | Currently under tax audit? |
| `back_taxes_paid` | bool \| null | Back taxes or arrears paid in last 24 months? |
| `self_compliance_confidence_1_5` | smallint \| null | Likert 1–5 SME self-rating. |
| Indexes | — | `(sme_id, snapshot_at)` for fast "most-recent" query. |

#### `m3_behavioural_signals` (Session 5 — append-only snapshots)

DDL source → migration `202605090001`. Parallel append-only table for operational + behavioural answers. Same snapshot pattern as `m3_compliance_history`.

| Column | Type | Notes |
|--------|------|-------|
| `signals_id` | UUID PK | |
| `sme_id` | UUID FK `sme_profiles.sme_id` ON DELETE CASCADE | |
| `snapshot_at` | timestamptz | Server `NOW()` default. |
| `filing_method` | text \| null | `'self_efile'`, `'self_paper'`, `'accountant'`, `'agent'`, `'mixed'`. |
| `books_method` | text \| null | `'none'`, `'manual'`, `'excel'`, `'software'`, `'mixed'`. |
| `accounting_software` | text \| null | `'quickbooks'`, `'zoho'`, `'sage'`, `'tally'`, `'local'`, `'none'`. |
| `update_frequency` | text \| null | `'daily'`, `'weekly'`, `'monthly'`, `'quarterly'`, `'at_filing'`, `'none'`. |
| `deadline_tracker` | bool \| null | Uses any reminder/tracker tool? |
| `last_training_band` | text \| null | `'<6mo'`, `'6-12mo'`, `'1-2y'`, `'>2y'`, `'never'`. |
| `responsibility_owner` | text \| null | `'owner'`, `'finance_staff'`, `'shared'`, `'external'`, `'none'`. |
| `barriers_json` | JSONB \| null | Ranked list of compliance barriers: `[{"key":"time_constraints","rank":1}, ...]`. |
| `sector_specific_json` | JSONB \| null | Dict of sector-specific signals (e.g. `{"retail": {"daily_reconcile": true}}`). |
| `cash_flow_difficulty_1_5` | smallint \| null | Likert stress score. |
| `regulators_count_band` | text \| null | Number of regulators the SME interacts with: `'1'`, `'2'`, … `'5+'`. |
| Indexes | — | `(sme_id, snapshot_at)` for fast "most-recent" query. |

> **M4 note.** The `survey_sessions.survey_mode` CHECK constraint includes `'per_module_m4'`, and the session API will accept that mode. However, no `survey_questions` rows with `module_number=4` are seeded yet. Starting a `per_module_m4` session returns no questions and completes immediately. M4 data capture (claim verification table) is deferred to BUILD_10.

#### `survey_question_regulations` (Session 12 — M:N junction)

Replaces the 1:1 `linked_regulation_id` FK on `survey_questions` with a many-to-many junction. A unique partial index enforces at most one `is_primary = true` row per question; the cached `survey_questions.linked_regulation_id` column is kept for hot-path admin list hydration.

DDL source → [`backend/alembic/versions/202605120001_question_regulations_junction.py`](../../backend/alembic/versions/202605120001_question_regulations_junction.py).

| Column | Type | Notes |
|--------|------|-------|
| `question_code` | text FK `survey_questions.question_code` ON DELETE CASCADE, PK | |
| `regulation_id` | UUID FK `m1_regulations.regulation_id` ON DELETE CASCADE, PK | |
| `weight` | smallint | Default 1. Higher = more relevant to this regulation. |
| `is_primary` | bool | At most one `true` per question (unique partial index). When `true`, the question's `linked_regulation_id` cache is updated. |
| `created_by`, `updated_by` | text | Authorship (Session 14). |
| `created_at`, `updated_at` | timestamptz | |

### Session-16 tables — session-based survey architecture

DDL source → [`backend/alembic/versions/202605160001_survey_sessions.py`](../../backend/alembic/versions/202605160001_survey_sessions.py).

#### `survey_sessions`

Top-level grouping for one SME's run through a survey mode. A single SME can have multiple sessions (one per attempt). `survey_responses` rows are linked to their session via `session_id`.

| Column | Type | Notes |
|--------|------|-------|
| `session_id` | UUID PK | `gen_random_uuid()` default. |
| `sme_id` | UUID FK `sme_profiles.sme_id` | Which SME started the session. |
| `survey_mode` | text CHECK | `'per_module_m1'`, `'per_module_m2'`, `'per_module_m3'`, `'per_module_m4'`, `'unified'`. |
| `status` | text CHECK | `'in_progress'`, `'completed'`, `'abandoned'`. Default `'in_progress'`. |
| `started_at` | timestamptz | Default `NOW()`. |
| `completed_at` | timestamptz \| null | Set by `POST /survey-sessions/{id}/complete`. |
| `questions_shown` | int | Incremented on each `next-question` call. |
| `questions_answered` | int | Incremented on each `answer` call. Session ends when `questions_answered >= MODE_CAPS[survey_mode]`. |
| `recruitment_channel` | text \| null | How the SME was recruited (e.g. `'direct'`, `'email_campaign'`). |

**Question caps by mode** (enforced in `survey_session_service.cap_reached()`):

| `survey_mode` | Cap |
|---|---|
| `per_module_m1` | 10 |
| `per_module_m2` | 10 |
| `per_module_m3` | 10 |
| `per_module_m4` | 10 |
| `unified` | 20 |

#### `survey_limits` (Session 17 — singleton config)

DDL source → [`backend/alembic/versions/202605170001_survey_limits.py`](../../backend/alembic/versions/202605170001_survey_limits.py).

Singleton row (always `id = 1`) that holds admin-configurable per-role survey submission caps. Edited by admins at `/admin/settings`; read by `survey_limits_service.get_limits()` on every session start.

| Column | Type | Notes |
|--------|------|-------|
| `id` | int PK | Always `1` — singleton pattern. |
| `sme_limit` | int | Max completed sessions an SME may have. Default `10`. `0` = unlimited. |
| `annotator_limit` | int | Same for annotator role. Default `0` (unlimited). |
| `admin_limit` | int | Same for admin role. Default `0` (unlimited). |
| `updated_by` | text \| null | Email of admin who last changed the limits. |
| `created_at`, `updated_at` | timestamptz | |

> **Resilience note (F-138).** If the `survey_limits` table doesn't exist yet (e.g. migration not yet run), `get_limits()` catches `ProgrammingError` and returns the compiled-in defaults (`sme_limit=10`), so the app stays functional.

---

## 4. Alembic workflow

The configuration is in [`backend/alembic.ini`](../../backend/alembic.ini); the env script in [`backend/alembic/env.py`](../../backend/alembic/env.py) reads `DATABASE_URL` from `app.settings` and runs migrations through the same async engine the app uses.

### Anatomy of a model change

1. **Edit the ORM model** under [`backend/app/models/`](../../backend/app/models/).
2. If you added a new model file, **import it** in [`backend/app/models/__init__.py`](../../backend/app/models/__init__.py) — Alembic discovery walks the metadata, and unimported models are invisible.
3. **Generate the migration:**

   ```bash
   cd backend
   uv run alembic revision --autogenerate -m "add column X to users"
   ```

   The file lands in `backend/alembic/versions/YYYYMMDDHHMM_<slug>.py`.

4. **Review the generated file before committing.** Autogenerate is good but not perfect. Watch for:
   - `op.alter_column(..., server_default=...)` you didn't intend.
   - Unwanted `op.drop_table` for tables your branch never owned (a sign your `models/__init__.py` is missing an import).
   - `op.execute(...)` blocks that are empty (you can delete them).

5. **Apply locally:**

   ```bash
   uv run alembic upgrade head
   ```

6. **Roll back if needed:**

   ```bash
   uv run alembic downgrade -1
   ```

   Then edit the migration, rerun `upgrade`. Don't edit migrations that have already shipped to other developers' databases — write a new one instead.

### Migration naming

The `file_template` in [`alembic.ini`](../../backend/alembic.ini) generates `YYYYMMDDHHMM_<slug>.py`. The first migration is [`202605080001_initial_schema.py`](../../backend/alembic/versions/202605080001_initial_schema.py); follow the same `YYYYMMDDNNNN` pattern (NNNN is a same-day counter when you ship multiple in a day).

### When NOT to autogenerate

For destructive changes — dropping a column with data, renaming a table, splitting a column — write the migration by hand. Autogenerate doesn't preserve data.

### Migration history (all 11 versions)

| Migration ID | What it adds |
|---|---|
| `202605080001` | Initial schema: `users`, `sme_profiles`, `survey_responses`, `audit_log` |
| `202605090001` | M2/M3 schema: `regulatory_domains`, `sectors`, `m2_questions`, `m3_compliance_history`, `m3_behavioural_signals` |
| `202605100001` | `m1_regulations` + sector junction; rename `m2_questions` → `survey_questions`; add `module_number`, `linked_regulation_id`, `next_question_rules` |
| `202605110001` | Add `is_active` soft-archive flag to `m1_regulations` |
| `202605120001` | `survey_question_regulations` M:N junction; add `is_baseline` to `survey_questions` |
| `202605140001` | Add `created_by`/`updated_by` authorship columns; add `record_key` to `audit_log` |
| `202605160001` | Add `survey_sessions` table; add `session_id`, `regulation_id`, `survey_mode` to `survey_responses` |
| `202605170001` | Add `survey_limits` singleton config table |
| `202605180001` | Rename awareness `module_number` from `0` → `1`; update `survey_responses` server default |

### Pattern: rename-then-extend, with a follow-up to relax legacy constraints

Session 6 generalised `m2_questions` → `survey_questions` to host all three modules. The canonical sequence:

1. **`202605100001_unified_survey_questions.py`** — `op.rename_table("m2_questions", "survey_questions")` preserves the existing rows; the same migration adds the new columns (`module_number`, `linked_regulation_id`, `next_question_rules`, …) and renames the inherited indexes (`ix_m2_questions_*` → `ix_survey_questions_*`). This avoids the "drop and recreate" data-loss trap that `--autogenerate` would otherwise propose for a table rename.
2. **`202605100002_relax_survey_question_columns.py`** — drops `NOT NULL` from columns that were specific to the old purpose (here: `domain_code`, `knowledge_type` — both M2-only concepts that don't apply to M1/M3 rows). Worth shipping as a *separate* migration because it's the kind of constraint a future contributor will want to revert independently, and because it's the natural fix-up when the first seed run catches a leftover NOT NULL.

Use the same shape any time a generalising migration leaves a column whose `NOT NULL` no longer matches the new domain.

---

## 5. Seeding the dev DB

`make seed` runs [`backend/app/scripts/seed_dev.py`](../../backend/app/scripts/seed_dev.py). It is **idempotent** — every insert is gated by an existence check, so re-running adds nothing.

### Seed order (Session 22 update)

`seed_dev.py` calls the following entry points in dependency order. Each one is independently idempotent and safe to call out-of-band, but the order matters because later steps reference rows the earlier ones create:

1. `_ensure_user(...)` — admin / annotator / SME accounts.
2. **(NEW — Session 22)** [`seed_lookups.py`](../../backend/app/scripts/seed_lookups.py) — 9 `regulatory_domains` + 12 `sectors`. Must run before `seed_regulations` because `m1_regulations.domain_code` and `m1_regulation_sectors.sector_code` both FK here. Idempotent via `ON CONFLICT DO NOTHING`. (Previously these rows were seeded inside `seed_m23_questions.main()`, which ran later in the chain — defensive split, no behavioural change for already-populated DBs.)
3. [`seed_regulations.py`](../../backend/app/scripts/seed_regulations.py) — 5 canonical `m1_regulations` rows. Must run before `seed_m23_questions` because M2 questions FK back to a regulation. Marked `expert_verified = false` so the admin UI shows the "Needs verification" badge.
4. [`seed_vulnerability_questions.py`](../../backend/app/scripts/seed_vulnerability_questions.py) — M3 rows (history / behaviour / stress / sector-specific). Must run before `seed_awareness_questions` because awareness `next_question_rules` reference M3 codes (`M3_HIST_004`, `M3_VAT_NOAWARE_PENALTY`).
5. [`seed_m23_questions.py`](../../backend/app/scripts/seed_m23_questions.py) — the 40 canonical M2 rows. Updated for the new fields and applies the `CROSS_MODULE_LINKAGE` constant (`VAT_FACT_002 → M3_HIST_004`, `VAT_FACT_001 → M3_VAT_NOAWARE_PENALTY`) so a wrong M2 answer routes the wizard into the matching M3 follow-up. Still seeds the same `DOMAINS` / `SECTORS` constants as a belt-and-braces safety net; `on_conflict_do_nothing` makes re-seeding harmless now that `seed_lookups` runs first.
6. [`seed_awareness_questions.py`](../../backend/app/scripts/seed_awareness_questions.py) — 12 M1 rows verbatim from the original `frontend/lib/surveys/awareness.ts` bank, with Q4 (April 2026 VAT threshold) and Q5 (VAT 18% rate) carrying `next_question_rules` that fire on `answer_in ["no", "unsure"]`. Q1 marked `is_branching_root = true`.
7. **(NEW — Session 22)** [`seed_demo_responses.py`](../../backend/app/scripts/seed_demo_responses.py) — 6 demo SMEs (`demo.<sector>@enigmatrix.lk` / `demo12345678` across retail, manufacturing, it, tourism, construction, food_beverage), each walked through M1+M2+M3 with scored answers + one `M3ComplianceHistory` + one `M3BehaviouralSignals` snapshot. Populates `survey_responses`, `m2_knowledge_scores`, `m3_compliance_history`, `m3_behavioural_signals` so `/admin/m2/scores`, `/admin/m3/risk-signals`, and `/admin/surveys/awareness/responses` render non-empty without manually walking the SME wizard. Idempotent: skips any SME that already has `survey_responses` rows; deterministic via `random.Random(hash(email))` so screenshots are stable. Per-SME `skill ∈ [0.35, 0.85]` + `compliance_profile ∈ {strong, average, weak}` produce a 34–86 % M2 distribution with correlated compliance flags.

After a clean migrate + seed: `SELECT module_number, COUNT(*) FROM survey_questions GROUP BY 1` should report 12 / 40 / ~25 for modules 0 / 2 / 3; and `SELECT COUNT(*) FROM survey_responses` should report 336 (12 awareness × 6 demo SMEs + 44 M2 × 6 demo SMEs).

To extend the seed (e.g. add a sample admin in your sector):

```python
# FILE: backend/app/scripts/seed_dev.py — inside main()
await _ensure_user(db, email="qa@enigmatrix.lk", password="qa12345678", role="admin")
```

Then `make seed` again.

To **drop and rebuild** the whole dev database:

```bash
make reset-db
```

Or, if you want to keep the Docker volume but wipe all DB objects:

```bash
make clean-db
```

---

## 6. Backups (dev)

Even in development, take an occasional snapshot before destructive migrations:

```bash
docker exec enigmatrix-postgres pg_dump -U enigmatrix enigmatrix \
  | gzip > "backups/enigmatrix_$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
```

Restore:

```bash
gunzip -c backups/enigmatrix_<ts>.sql.gz \
  | docker exec -i enigmatrix-postgres psql -U enigmatrix enigmatrix
```

Production backup automation lives in [`BUILD_14_Deployment_Cloud.md`](../../infra/BUILD_PLAN/BUILD_14_Deployment_Cloud.md).

---

## 7. Inspecting data

A few one-liners worth bookmarking:

```sql
-- All submissions grouped by SME, latest first
SELECT u.email, sp.sector, sr.submitted_at, COUNT(*) AS answers
FROM survey_responses sr
JOIN sme_profiles sp ON sp.sme_id = sr.sme_id
JOIN users u ON u.id = sp.user_id
GROUP BY u.email, sp.sector, sr.submitted_at
ORDER BY sr.submitted_at DESC;

-- Audit trail for one user
SELECT occurred_at, event_type, event_data_json
FROM audit_log WHERE user_name = 'sme1@example.com'
ORDER BY occurred_at;

-- Per-question completion rates for the awareness instrument
SELECT question_id, COUNT(*) AS n
FROM survey_responses WHERE survey_instrument = 'awareness'
GROUP BY question_id ORDER BY question_id;
```

---

## 8. Open questions about the schema

- **OQ5 — question_id versioning.** When the awareness question bank evolves, do we keep `survey_responses.question_id` stable (`awareness.v1.qNN`) and write `awareness.v2.qNN` for new bank versions, or rewrite history? **Provisional answer:** append-only, version the `question_id`. Confirm before adding the second instrument (knowledge / vulnerability).
- **DB-level role enforcement.** `users.role` accepts any text today; the application enforces the three valid values. A Postgres CHECK constraint plus an enum type would harden this — non-blocking, but a clean follow-up.
- **`survey_responses.answer_text` for multi-select.** Today it's stored as a comma-joined string. JSONB array would be cleaner; the migration cost is small but breaks every SQL query that relies on the current shape. Defer until the second instrument forces the issue.

---

**Prev:** [`05_Frontend_Development.md`](05_Frontend_Development.md) &nbsp;·&nbsp; **Next:** [`07_Auth_and_Roles.md`](07_Auth_and_Roles.md)
