# Phase 2 · Extraction — `ck_m1_reg_language` Rejects Every Extracted Row: Fix Plan

> Group: `PHASE2_INGEST_EXTRACTION / language_check_constraint`. Sibling of the governance work ([[PHASE2_DATA_VALIDATION_GOVERNANCE_PLAN]]) whose migration introduced the bug. Surfaced right after [[CELERY_ASYNC_LOOP_DB_FIX_PLAN]] unblocked extraction.
> **Status: implemented (2026-07-23), verification deferred (sandbox VHDX down).** Corrective migration so `extract_gazette` can commit; the run that showed 0/0 forever will now advance.

## 1. Symptom

With the event-loop crash fixed, extraction ran — but every `extract_gazette` task failed its commit and retried:

```
Task ... extract_gazette[...] retry: Retry in 2s: IntegrityError(
  asyncpg.CheckViolationError: new row for relation "m1_regulations"
  violates check constraint "ck_m1_reg_language"
  DETAIL: Failing row contains (..., en, ...))
```

On the run page this looked "stuck": Scraping spun, **Extracting 0/0**, **Preprocessing 0/0**, Run summary all zeros — because no row ever left `status='ingested'`.

## 2. Root cause

Migration `202607230001_m1_schema_validation_and_governance` (Layer-1 CHECK constraints) added:

```sql
ck_m1_reg_language:  language IS NULL OR language IN ('sin','tam','eng','unknown')
```

Those are **ISO 639-2** three-letter codes. But the pipeline writes **ISO 639-1** two-letter codes: `app/extraction/pdf_metadata.py::detect_language` returns `'si' | 'ta' | 'en' | 'unknown'` (and its docstring says so explicitly; the ML worker's `language_detection.py` uses the same two-letter codes plus a `'mixed'` outcome). `extract_gazette` sets `row.language = metadata["language"]` → `'en'` for an English gazette → violates the constraint. The constraint added `NOT VALID`, so it enforced on new writes only — which is exactly the extract UPDATE — and `autoretry_for=(Exception,)` turned the deterministic failure into a retry loop.

This is the **same class of bug** already fixed once for a sibling constraint in `202607230002_widen_prop_match_method` (that governance migration shipped several enums narrower than the code) — the language one was just missed because no English gazette had been extracted until now.

## 3. The fix (code)

New migration **`202607230004_fix_m1_reg_language_check.py`** (revises the current head `202607230003`), mirroring the `202607230002` corrective pattern:

```sql
-- upgrade
ALTER TABLE m1_regulations DROP CONSTRAINT IF EXISTS ck_m1_reg_language;
ALTER TABLE m1_regulations ADD CONSTRAINT ck_m1_reg_language
  CHECK (language IS NULL OR language IN ('si','ta','en','mixed','unknown')) NOT VALID;
```

- Uses the two-letter codes the code actually emits.
- Includes `'mixed'` to future-proof against the ML worker's document-level detector, so this can't stall again if that path ever feeds `language`.
- `NOT VALID` (existing rows are a subset of the new set → a later `VALIDATE CONSTRAINT` passes instantly), consistent with the whole Layer-1 tier.
- `downgrade()` restores the old (incorrect) set for reversibility.

The source migration `202607230001` is left as-is (same convention as `202607230002` — corrective migrations rather than editing an applied one).

## 4. Why fix the constraint, not the code

The two-letter codes are the project standard everywhere else: `detect_language`, the ML detector, the API type (`language: 'si'|'ta'|'en'|'unknown'`), the frontend PDF-records language filter. The constraint from one governance migration is the sole outlier. Changing the pipeline to emit `'eng'` would ripple through the API + frontend filters and break existing rows. The constraint is the thing to correct.

## 5. Recovery for the already-stuck rows

The failed extracts rolled back, so those rows are still at `status='ingested'` (nothing lost). After `alembic upgrade head`:
- re-trigger extraction over the same scope (2026-02-01 → 2026-02-28 for the run in the log), or
- per row, `POST /admin/m1/extraction/regulations/{id}/re-extract`.

Each re-extract now commits `extracted` → auto-chains to preprocess → the run-page tallies climb.

## 6. Docs updated

- `enigmatrix-docs/m1/08_M1_Full_System_Architecture.md` — new failure-mode row.
- `AI_WORK_LOG.md` — session entry.

## 7. Verification (deferred — sandbox VHDX down)

1. `python -m compileall enigmatrix-backend/alembic/versions/202607230004_fix_m1_reg_language_check.py`.
2. `alembic upgrade head`; confirm `\d+ m1_regulations` shows `ck_m1_reg_language` with the two-letter set.
3. Re-trigger the EGZ run; confirm rows advance ingested→extracted→preprocessed and **no** `ck_m1_reg_language` violation in the worker log.
4. Optional hardening (follow-up, not in this change): `ALTER TABLE m1_regulations VALIDATE CONSTRAINT ck_m1_reg_language;` once back-classified rows are confirmed clean; and consider excluding deterministic `IntegrityError` from `extract_gazette`'s `autoretry_for` so a future constraint mismatch fails fast instead of retrying 3×.
5. `pytest`; `graphify update .`.
