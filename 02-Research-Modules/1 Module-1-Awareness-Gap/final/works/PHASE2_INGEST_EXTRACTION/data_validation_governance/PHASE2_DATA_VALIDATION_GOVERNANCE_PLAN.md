# Phase 2 · Data Requirements — Schema Validation + Governance: Plan

> Group: `PHASE2_INGEST_EXTRACTION / data_validation_governance`. Companion: [[PHASE2_DATA_VALIDATION_GOVERNANCE_ANALYSIS]].
> **Status: implemented 2026-07-23.** Verification steps are deferred to the operator (sandbox VHDX down — no migrate/pytest/lint this session).

## 1. Files added / changed

**Layer 1 — SQL constraints + Layer-3 table**
- `alembic/versions/202607230001_m1_schema_validation_and_governance.py` (new) — `down_revision="202607220001"` (current head). Creates `m1_pipeline_audits` (`UNIQUE(check_name, run_date)`), then adds 11 CHECK constraints **`NOT VALID`** across `m1_regulations`, `m1_propagation_events`, `m1_regulation_sectors`.
- `app/m1/models/pipeline_audit.py` (new) — `M1PipelineAudit` ORM.

**Layer 2 — Pydantic + shared validator**
- `app/m1/validation.py` (new) — `assert_regulation_row_valid()` mirroring the Layer-1 rules for direct writers; enum frozensets.
- `app/schemas/regulation.py` (edit) — `change_category` tightened to the real `ChangeCategory` enum on Create+Update; `_validate_date_order` stage-date ordering validator.

**Layer 3 — nightly job**
- `app/m1/tasks/validate_pipeline.py` (new) — `run_nightly_checks` (6 checks) → upsert `m1_pipeline_audits`; audit row on failure.

**Governance / retention (02_M1_3)**
- `app/m1/tasks/retention.py` (new) — `anonymise_aged_survey_responses`, `prune_pipeline_audits`, `report_archivable_audit_logs`. Dry-run guarded.
- `app/m1/services/storage_projection.py` (new) — Y1/Y3/Y5/Y10 projection model.
- `infra/aws/s3_m1_lifecycle.yaml` (new) — Standard→Glacier→Deep Archive.

**Wiring**
- `app/celery_config.py` (edit) — `include` += `validate_pipeline`, `retention`; 4 new Beat entries (validate 02:00 daily; prune-audits 03:00 daily; anonymise-survey Sun 03:30; report-audit-logs Sun 03:45).
- `app/settings.py` (edit) — `M1_RETENTION_DRY_RUN` (True), `M1_SURVEY_RETENTION_YEARS` (5), `M1_PIPELINE_AUDIT_RETENTION_DAYS` (365), `M1_AUDIT_LOG_RETENTION_YEARS` (7).

## 2. Task-name convention (important)

This repo registers Celery tasks under explicit `app.tasks.m1.*` names even though modules live at `app.m1.tasks.*` (a reorg artefact). New tasks follow it: `@celery_app.task(name="app.tasks.m1.validate_pipeline.run_nightly_checks")` etc., and the Beat entries reference those exact names. Getting this wrong yields `Received unregistered task of type …` at runtime.

## 3. Design decisions

- **`NOT VALID` constraints** — enforce forward, never fail the migration on legacy rows. Operator runs `VALIDATE CONSTRAINT` after the nightly job's `classified_without_category` / `*_out_of_range` checks report zero offenders.
- **Dry-run retention** — a mis-tuned window (e.g. `M1_SURVEY_RETENTION_YEARS` set too low) cannot silently anonymise live data; the job logs the count first.
- **Audit-log = report-only** — respects the Session-14 INSERT-ONLY invariant; no automated deletes from `audit_log`.
- **Upsert Layer-3 rows** — `ON CONFLICT (check_name, run_date) DO UPDATE` keeps the job idempotent for same-day re-runs.

## 4. Verification (deferred to operator)

1. `python -m compileall app` (syntax) — covers the 5 new modules + edits.
2. `alembic upgrade head` → confirm `m1_pipeline_audits` exists and the 11 constraints are present (`\d+ m1_regulations`); `alembic downgrade -1` → `upgrade head` round-trips.
3. After a clean data pass: `ALTER TABLE m1_regulations VALIDATE CONSTRAINT ck_m1_reg_category_when_classified;` (repeat per constraint) — should succeed once the nightly job reports 0 offenders.
4. Trigger `run_nightly_checks` once → rows appear in `m1_pipeline_audits`; re-run same day → no duplicates (upsert).
5. `pytest tests/m1/` — add `test_schema_validation.py` (per-validator ± cases) and `test_schema_parity.py` (Layer-1 SQL vs `app/m1/validation.py`) per the doc's acceptance criteria.
6. Retention: with `M1_RETENTION_DRY_RUN=True`, tasks log counts and write nothing; flip off on staging and confirm survey anonymisation is idempotent.
7. `graphify update .`.

## 5. Follow-ups (not in this build)

PDPA `/sme/me/data-export` + `DELETE /sme/me` endpoints; `audit_log_archive` table + yearly partitioning + the operator archival job; `EXPLAIN ANALYZE` trace commit for the lag view; wiring `assert_regulation_row_valid()` into `classify_gazette`'s write path. Sources → 02_1 (catalogue/spiders) + 02_4 (worked examples) remain, per the chosen sequence.
