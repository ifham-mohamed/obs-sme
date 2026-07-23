# Module 1 — Phase 2 Gap #6: Metadata Confidence + Admin Review Queue

> Companion to [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/11_PHASE2_INGEST_EXTRACTION_ANALYSIS]] §6.6 and [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/12_PHASE2_GAP_CLOSURE_PLAN]] §6.6. **Status: implemented (Session 67, 2026-07-21).** Code in `C:\Reasearch\xyz\enigmatrix-backend`.

## Problem

`metadata_extractor.py` (ml package) is regex/pattern-tiered. Under gazette layout drift, a misfiring pattern produces a **silently missing or silently wrong** field — `effective_date` three years off, a "penalty range" with one number, an act name that never appears in the document. Nothing distinguished "extractor confident" from "extractor guessed", and no human ever saw the guesses.

## Key design decision: score in the backend, not (yet) in the ml package

The obvious fix — return `(value, confidence, pattern_id)` from `metadata_extractor.py` — changes the ml package's public contract, and the production image pins `enigmatrix-ml` by git rev (`ML_GIT_REF`), so an ml-side change needs a coordinated rev bump. Instead, Session 67 ships **backend-side sanity scoring** (`app/m1/services/metadata_confidence.py`), which:

- ships immediately, no ml release train;
- catches a class of errors the extractor *cannot* see about itself — a regex can match perfectly and still produce an implausible value; plausibility lives outside the pattern (e.g. date-vs-publication window);
- leaves a clean slot for the deeper ml-side pattern-tier confidence later (same JSONB, same threshold).

## Scoring rules (0.0–1.0; <0.7 = review material)

| Field | Checks |
|---|---|
| `gazette_number` | absent→0.0; matches `^\d{4}/\d{1,3}$`→0.95; malformed→0.4 |
| `effective_date` | absent→0.0; within [published−30d, published+365d]→0.9; parsed but implausible→0.3; no publication date to check against→0.6 |
| `penalty_range_lkr` | absent→0.0; ≥2 ordered numbers→0.9; one/unordered→0.5; **no digits in a "range"**→0.3 |
| `principal_act_amended` | absent→0.0; claim literally present in `cleaned_text`→0.9; contains "Act"→0.7; else→0.4 |

**Review rule (queue-flood guard):** `gazette_number` below threshold *including absent* always flags (it's the row's identity). The other three flag only when **present but below threshold** — many gazettes legitimately have no penalty clause or amended act, and flagging absence would bury real errors in noise. This asymmetry is the part most worth reviewing against real data.

## What was built

| Piece | Where |
|---|---|
| Scorer (pure function, unit-testable) | `app/m1/services/metadata_confidence.py` |
| Columns: `metadata_confidence` JSONB + `needs_metadata_review` bool | `app/models/regulation.py`, migration `202607210002` (partial index on flagged rows only) |
| Wiring: scored after the admin-override fill-in block, so **final** row values are scored, not raw extractor output | `app/m1/tasks/preprocess_gazette.py` |
| Queue: `GET /api/v1/admin/m1/pipeline/metadata-review` (paginated, active rows, newest first) | `app/m1/api/admin_pipeline.py` |
| Sign-off: `POST …/metadata-review/{id}/resolve` — clears flag + audit row `m1_regulation.metadata_review.resolved` (a data-quality control needs a sign-off trail) | same |

Workflow: probe queue → open regulation → fix fields via existing PATCH (already audited with old/new diff) → resolve. Idempotent with the pipeline: a re-preprocess re-scores and may legitimately re-flag.

## Verification (deferred to user)

1. `alembic upgrade head`; `python -m compileall app`.
2. Unit-test the scorer (pure function): implausible date → 0.3; one-number penalty → 0.5; act name not in text → 0.4; all-good row → no review.
3. Re-preprocess one known-bad row → appears in `GET /metadata-review` with per-field scores; PATCH a fix; POST resolve → gone from queue, audit row present.
4. `pytest` + `graphify update .`.

## Follow-ups

- **ml-side pattern-tier confidence** in `metadata_extractor.py` (return which tier matched; bump `ML_GIT_REF`) — merges into the same JSONB, replacing the 0.6 "can't check" cases with real signal.
- Frontend queue tab in the pipeline portal (API is ready; mirror the existing recent-runs table).
- Auto-clear the flag when an admin PATCHes a scored field (currently explicit resolve only — deliberate first, so sign-off stays conscious).
- Feed `needs_metadata_review` count into the monthly quality probe ([[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/15_PHASE2_QUALITY_MONITORING_PLAN]]) as a trend metric.
- Threshold (0.7) + date window (−30d/+365d) tuning after the first real queue fills.
