# Phase 2 · Data Requirements — Schema Validation + Governance: Analysis

> Group: `PHASE2_INGEST_EXTRACTION / data_validation_governance`. Companion: [[PHASE2_DATA_VALIDATION_GOVERNANCE_PLAN]].
> Builds the two deferred data-contract docs [[02_M1_2_Database_Schema_Validation]] + [[02_M1_3_Data_Governance_Retention]] into code. **Status: implemented 2026-07-23 (verification deferred — sandbox VHDX down).**

## 1. What was deferred

The `02_M1_Data_Requirements` companions specified a three-layer validation system (SQL constraints → Pydantic → nightly job) and a data-governance/retention regime (PDPA, retention windows, S3 lifecycle, storage projection). Both were `🔲 Deferred` — the specs existed but no enforcing code did.

## 2. Key finding: the spec names don't match the live schema

The docs were written against an *idealized* schema and diverge from what actually shipped across Phase 2/3/4. Implementing the constraints verbatim would have produced CHECKs on non-existent columns and a migration that fails on `alembic upgrade`. The real mapping (grounded by reading `app/models/regulation.py`, `app/m1/models/propagation_event.py`, `app/models/audit_log.py`, `app/models/survey.py`, `app/models/sme_profile.py`):

| Doc assumes | Reality |
|---|---|
| single `confidence` | `classifier_confidence` + `sme_relevance_confidence` (both `Numeric(3,2)`) |
| `primary_language IN ('en','si','ta','mixed')` | `language IN ('sin','tam','eng','unknown')` |
| status set without `preprocessed` | real set has `preprocessed` between extracted and classified |
| `match_method` 4-value enum | `('exact_gazette','fuzzy_title')` |
| unique `(regulation_id, channel)` | already `uq_m1_prop_reg_source (regulation_id, source_id)` |
| `needs_review` column | none — review queue is a derived predicate |
| `m1_sme_awareness_responses`, `consent_acknowledged_at` | responses live in `survey_responses` (keyed `sme_id`, `answer_date`/`submitted_at`); consent is `sme_profiles.consent_given` + `consent_text_version` |

Every constraint and job below is written against the **real** columns.

## 3. Risk posture (sandbox down)

Bash is unavailable this session, so no migration/pytest/lint run was possible. Two mitigations shaped the design: (a) all CHECK constraints are added **`NOT VALID`** — enforced for new writes, but no full-table scan of legacy rows, so the migration cannot fail on existing data; (b) all retention jobs default to **dry-run** (`M1_RETENTION_DRY_RUN=True`) — they log would-change counts and mutate nothing until an operator opts in. Nothing shipped can destroy or reject existing data on first deploy.

## 4. What the three layers now catch

- **Layer 1 (DB):** enum/range/status membership + the "post-classification row must have a category" invariant, at write time, even for direct Celery/backfill inserts that bypass the API.
- **Layer 2 (Pydantic + `app/m1/validation.py`):** cross-field invariants before the DB round-trip — tightened `change_category` to the real 12-value enum, stage-date ordering (bill ≤ gazette ≤ effective), and a reusable `assert_regulation_row_valid()` the pipeline tasks can call to fail fast with a readable message instead of a raw `IntegrityError`.
- **Layer 3 (nightly job):** cross-row/distributional checks neither other layer can express — Sinhala share drift, legacy `classified`-without-category rows, out-of-range confidence, metadata-review backlog, absurd future effective dates, and lag-view queryability — persisted to `m1_pipeline_audits` and surfaced in the Activity Log on failure.

## 5. Governance regime

Retention windows from §2 became three Beat jobs (survey anonymisation, pipeline-audit pruning, audit-log archive *reporting*); §3's growth model became a pure-Python projection service; §4's lifecycle became a committed YAML. The audit-log archival is deliberately **report-only** because `audit_log` is INSERT-ONLY (Session 14) — moving rows out is an operator decision, not an automated delete.
