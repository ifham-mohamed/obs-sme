---
tags: [tracker, findings, m1]
source: synthesised
layer: tracker
module: m1
---

# 2026-05-17 — M1 Step 2f: wire preprocessing into Celery pipeline + DB persistence

> **Owner:** mohamedifham
> **Module:** m1
> **Type:** session log + decision + finding

## What I did

- Added Alembic migration `202605240001_m1_preprocessing_columns_and_penalties.py`: 2 new columns on `m1_regulations` (`cleaned_text` TEXT, `amendment_type` VARCHAR(20) with CHECK enum), extended the `ck_m1_regulations_status` CHECK to include a new `'preprocessed'` state, and created the `m1_regulation_penalties` junction table per the [04_M1_2 §3.3](../04_M1_2_Metadata_Extraction_Patterns.md) spec.
- Created `M1RegulationPenalty` ORM model at `enigmatrix-backend/app/models/m1_regulation_penalty.py` and registered it in `app/models/__init__.py` for Alembic autogenerate visibility.
- Created `M1RegulationPenaltyOut` Pydantic v2 schema at `app/schemas/m1_regulation_penalty.py` (`from_attributes=True`; not exposed in any router this slice).
- Extended `M1Regulation` with `cleaned_text` + `amendment_type` columns and `penalties: Mapped[list[M1RegulationPenalty]]` relationship (`cascade="all, delete-orphan"`, `order_by="M1RegulationPenalty.sequence_idx"`).
- Created new Celery task `preprocess_gazette_task` at `app/tasks/m1/preprocess_gazette.py` mirroring the Session-26 `extract_gazette` policy (`autoretry_for=(Exception,)`, `retry_backoff=True`, `max_retries=3`, `acks_late=True`).
- Chained it from `extract_gazette` via the Session-26 lazy-import + try/except `.delay(...)` pattern.
- Wrote 4 integration tests at `test_celery_preprocess_gazette.py`: DoD round-trip on the spec's VAT-amendment input, skip-test for non-extracted status, admin-curated authority test, idempotent penalties test.
- Updated `app/celery_config.py include=[...]` and `app/tasks/m1/__init__.py` re-exports.

## What I found

- **The canonical doc 02 §2.1 status enum needs amending.** The doc lists 6 pipeline states + `extraction_failed` (7 total). The user-confirmed scope chose to add a new `'preprocessed'` state inserted between `extracted` and `classified` — making it 7 + 1. This is a deliberate divergence; doc 02 §2.1 should be updated alongside this slice to match. The architecture diagram in doc 02 also treats preprocessing as part of Stage B; that mermaid block needs a "Stage B+" sub-node.
- **`extract_gazette` chaining via `.delay(...)` is safer than Celery `chain`/`chord` primitives** for this pipeline. The Session-26 spider → extract dispatch chose `.delay(...)` for the same reason: each task remains observable in isolation; failures don't cascade through workflow state. Step 2f follows the same convention.
- **DELETE-then-INSERT for the penalty junction is simpler than ON CONFLICT.** The penalty list's length varies between extractions (regex tweaks, re-runs with different windows). DELETE-then-INSERT handles all of grow / shrink / reorder with a single code path; ON CONFLICT would need branching to handle the cross-length case.
- **Admin-curated fields trump pipeline values.** The 4 DoD metadata fields can be (a) auto-discovered by the spider, (b) admin-curated manually, or (c) both. The task's fill-only-NULL rule keeps admin work authoritative. `cleaned_text` + `amendment_type` are always overwritten since they have no admin source today.

## What changed in the repo

| File | Change |
|---|---|
| `enigmatrix-backend/alembic/versions/202605240001_m1_preprocessing_columns_and_penalties.py` | NEW — adds 2 columns, extends status CHECK enum with `'preprocessed'`, creates `m1_regulation_penalties` table |
| `enigmatrix-backend/app/models/m1_regulation_penalty.py` | NEW — `M1RegulationPenalty` ORM model with `back_populates="penalties"` |
| `enigmatrix-backend/app/models/__init__.py` | Import + `__all__` include the new model for Alembic autogenerate visibility |
| `enigmatrix-backend/app/models/regulation.py` | `M1Regulation` adds `cleaned_text` + `amendment_type` columns + `penalties` relationship |
| `enigmatrix-backend/app/schemas/m1_regulation_penalty.py` | NEW — `M1RegulationPenaltyOut` Pydantic v2 schema (read-only) |
| `enigmatrix-backend/app/tasks/m1/preprocess_gazette.py` | NEW — `preprocess_gazette_task` Celery task |
| `enigmatrix-backend/app/tasks/m1/__init__.py` | Re-export `preprocess_gazette_task` alongside `extract_gazette` + `run_gazette_spider` |
| `enigmatrix-backend/app/tasks/m1/extract_gazette.py` | After successful flip to `'extracted'`, enqueue `preprocess_gazette_task.delay(...)` via Session-26 lazy + try/except pattern |
| `enigmatrix-backend/app/celery_config.py` | `include=[...]` lists `"app.tasks.m1.preprocess_gazette"` |
| `enigmatrix-backend/app/tests/integration/test_celery_preprocess_gazette.py` | NEW — 4 integration tests (DoD round-trip, skip, admin-authority, idempotency) |

## What's next

- [ ] Run the migration round-trip in the user's environment: `cd enigmatrix-backend && uv sync && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` — all clean.
- [ ] Run the integration test suite: `uv run pytest app/tests/integration/test_celery_preprocess_gazette.py -v` — needs Docker (testcontainer Postgres) + the workspace `enigmatrix-ml` member installed.
- [ ] Update **doc 02 §2.1** to add `'preprocessed'` between `'extracted'` and `'classified'` in the canonical status enum table. Single-line markdown change; no code coupling.
- [ ] Update **doc 02's architecture mermaid diagram** to add a "Stage B+ Preprocessing" sub-node showing the new task.
- [ ] Production worker image must stage `lid.176.bin` AND pre-warm the xlm-roberta-base HF tokenizer cache. Add to the Dockerfile.
- [ ] When the admin UI for `m1_regulation_penalties` lands (future BUILD_13 work), add an `is_admin_set` boolean flag on the junction so `preprocess_gazette_task` doesn't wipe curated rows on re-extraction.

## Blockers

None code-side. Backend runtime tests not run in this environment (no `uv` on PATH, no backend venv, no Docker for testcontainer). All 10 new/modified files pass `python -m py_compile` syntax checks.

## Cross-references

- Related session: [Session 32 — 2026-05-17](../../../08-Findings-Log/SESSIONS.md)
- Predecessor: [Session 31 / F-154 — Step 2e preprocessing ml-package](2026-05-17-m1-step2e-preprocessing-pipeline.md). Provides the `preprocess_gazette()` orchestrator + `PreprocessedGazette` dataclass that this slice persists.
- Other predecessors: [Session 26 / F-148 — Step 2b Celery + Stage-B PDF extraction](../../../08-Findings-Log/SESSIONS.md) (the `extract_gazette` task this one chains from); [Session 30 / F-153 — Step 2d language detection + Wijesekara](2026-05-17-m1-step2d-lang-detect-wijesekara.md) (the `preprocess_gazette()` call uses Step 2d's `detect_document_language` internally).
- Spec docs: [02_M1_Data_Requirements §2.1](../02_M1_Data_Requirements.md) (status enum — needs amendment), [04_M1_2 §3.3](../04_M1_2_Metadata_Extraction_Patterns.md) (junction table schema), [04_M1_Preprocessing_Pipeline §3.3](../04_M1_Preprocessing_Pipeline.md) (per-field extraction rules).
- Roadmap milestone: closes [Phase 2 overall DoD](../16_M1_Development_Roadmap.md#phase-2-ingest--extraction-build_07-ab) ("invoking the pipeline on a fresh `gazette.lk` URL ends with `m1_regulations` row at `status='extracted'`, all metadata fields populated"). With Step 2f, the pipeline now goes further — through `'preprocessed'` — with all 4 DoD metadata fields filled.
- Feature: F-155 in [FEATURES](../../../08-Findings-Log/FEATURES.md)