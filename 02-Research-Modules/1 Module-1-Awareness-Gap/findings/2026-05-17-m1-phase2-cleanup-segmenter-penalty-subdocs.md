---
tags: [tracker, findings, m1]
source: synthesised
layer: tracker
module: m1
---

# 2026-05-17 — M1 Phase 2 cleanup: segmenter promotion + penalty enum widening + is_admin_set + m1_sub_documents

> **Owner:** mohamedifham
> **Module:** m1
> **Type:** decision + session log + finding

## What I did

- Closed all 5 deferred Phase 2 carry-forwards from Session 33's "Deferred" list in a single lap.
- Promoted the segmenter to a standalone `m1.extraction.segmenter` module — moved `NOTICE_BOUNDARY_RE` + `detect_sections` from `m1.preprocessing.chunking` and added new `detect_sections_with_labels(text) -> list[SectionInfo]` that classifies sections into 6 types (`part`/`schedule`/`section`/`notice`/`numbered_clause`/`preamble`).
- Widened `m1_regulation_penalties.penalty_type` CHECK enum from 3 to 7 values via migration `202605250001`, matching the canonical doc 02 §2.8 spec.
- Added `is_admin_set BOOLEAN NOT NULL DEFAULT FALSE` column on `m1_regulation_penalties` so admin-curated rows survive `preprocess_gazette_task` re-extractions. Partial index `WHERE is_admin_set=TRUE` keeps the admin-curated query fast.
- Created `m1_sub_documents` junction table via migration `202605260001` per doc 02 §2.10. New `M1SubDocument` ORM, `M1SubDocumentOut` Pydantic schema, `M1Regulation.sub_documents` relationship.
- Extended `PreprocessedGazette.sections: list[SectionInfo]` and wired the orchestrator to populate it. `preprocess_gazette_task` now persists sub-documents via DELETE-then-INSERT.
- Updated doc 02 §5 mermaid to show the Stage B+ Preprocessing sub-node with all three writes (UPDATE m1_regulations + INSERT m1_regulation_penalties + INSERT m1_sub_documents).
- Flipped `03_M1_2_Gazette_Segmentation.md` (vault + code) from `⚠️ Partial` to `✅ Shipped Session 34 / F-157`.

## What I found

- **`SectionInfo` must live in `m1.extraction.types`, NOT `m1.preprocessing.types`.** Initial design placed it next to `PreprocessedGazette` since that's where it's consumed; this caused a circular import:
  ```
  segmenter.py
    → imports SectionInfo from preprocessing.types
      → triggers preprocessing.__init__.py
        → imports chunking.py
          → imports segmenter.py (still loading!) → ImportError
  ```
  Moving SectionInfo to `extraction.types` and re-exporting from `preprocessing.types` breaks the cycle and is also more logically correct (segmentation output owned by extraction module).
- **Pipeline penalty rows must re-number above admin-set rows.** The DELETE-then-INSERT idempotency couldn't reuse `sequence_idx=0,1,2,...` because admin rows might already occupy those values + the UNIQUE `(regulation_id, sequence_idx)` constraint would fail. Solution: read `max(sequence_idx WHERE is_admin_set=TRUE) + 1` and start pipeline-row sequence from there. Keeps both row classes addressable without conflict.
- **`m1_sub_documents` doesn't need `is_admin_set` today** — admins don't curate segmentation boundaries, the detector is fully pipeline-driven. The flag becomes useful when an admin UI for segmentation override appears (BUILD_13 territory).
- **`section_type='preamble'` distinguishes two cases.** A document with NO detected boundaries gets a single preamble row spanning the whole text; a document WITH boundaries where the head also has content gets a preamble row plus the labelled sections. Both code paths produce valid `m1_sub_documents` rows and the CHECK enum accommodates both via the `'preamble'` value.
- **127 ml tests pass — net +10 from this lap.** 14 new in `test_segmenter.py`, 5 moved out of `test_chunking.py`. Backend integration test suite has 2 new tests (admin-set preservation + sub-documents persistence) but couldn't run them locally (no Docker testcontainer Postgres in this env).

## What changed in the repo

| File | Change |
|---|---|
| `enigmatrix-ml/m1/extraction/segmenter.py` | NEW — promoted from inline-in-chunking.py; adds `detect_sections_with_labels` |
| `enigmatrix-ml/m1/extraction/types.py` | Adds `SectionInfo` dataclass + `SectionType` Literal (moved from preprocessing.types to break circular import) |
| `enigmatrix-ml/m1/extraction/__init__.py` | Re-exports segmenter public surface |
| `enigmatrix-ml/m1/preprocessing/chunking.py` | NOTICE_BOUNDARY_RE + detect_sections moved out; now imports + re-exports from segmenter |
| `enigmatrix-ml/m1/preprocessing/types.py` | SectionInfo re-exported for backward compat; `PreprocessedGazette.sections` field added; `PenaltyType` Literal widened 3 → 7 |
| `enigmatrix-ml/m1/preprocessing/__init__.py` | Orchestrator populates `pp.sections` via `detect_sections_with_labels(cleaned)` |
| `enigmatrix-ml/tests/m1/extraction/test_segmenter.py` | NEW — 14 tests (5 pattern + 3 detect_sections + 6 detect_sections_with_labels) |
| `enigmatrix-ml/tests/m1/preprocessing/test_chunking.py` | 5 moved tests dropped |
| `enigmatrix-backend/alembic/versions/202605250001_m1_penalties_enum_widen_and_admin_set.py` | NEW — penalty enum widen + is_admin_set column + partial index |
| `enigmatrix-backend/alembic/versions/202605260001_m1_sub_documents.py` | NEW — m1_sub_documents table + CHECK on section_type + UNIQUE + index |
| `enigmatrix-backend/app/models/m1_regulation_penalty.py` | PenaltyType Literal widened 3 → 7; is_admin_set column added |
| `enigmatrix-backend/app/models/m1_sub_document.py` | NEW — M1SubDocument ORM |
| `enigmatrix-backend/app/models/regulation.py` | `sub_documents` relationship added on M1Regulation |
| `enigmatrix-backend/app/models/__init__.py` | M1SubDocument registered for Alembic autogenerate |
| `enigmatrix-backend/app/schemas/m1_regulation_penalty.py` | PenaltyTypeOut widened 3 → 7; is_admin_set field added |
| `enigmatrix-backend/app/schemas/m1_sub_document.py` | NEW — M1SubDocumentOut Pydantic schema |
| `enigmatrix-backend/app/tasks/m1/preprocess_gazette.py` | Penalty DELETE filtered by is_admin_set=FALSE + sequence_idx renumbering; new sub-documents DELETE-then-INSERT |
| `enigmatrix-backend/app/tests/integration/test_celery_preprocess_gazette.py` | 2 new tests — admin-set preservation + sub-docs persistence |
| `02_M1_Data_Requirements.md` (vault + code) | §5 mermaid gains Stage B+; §2.8 status flipped + Shipped-subset DDL updated for 7-value enum + is_admin_set; new §2.10 m1_sub_documents schema; existing §2.10 renumbered to §2.11 |
| `03_M1_2_Gazette_Segmentation.md` (vault + code) | Status flipped ⚠️ Partial → ✅ Shipped Session 34 / F-157 |

## What's next

- [ ] User runs the migration round-trip locally: `cd enigmatrix-backend && uv run alembic upgrade head && uv run alembic downgrade -2 && uv run alembic upgrade head`.
- [ ] User runs the backend integration tests: `uv run pytest app/tests/integration/test_celery_preprocess_gazette.py -v` → 6 tests pass (4 existing + 2 new).
- [ ] Admin UI for penalty curation (BUILD_13) — when it lands, it'll write `is_admin_set=TRUE` rows that survive every preprocessing run.
- [ ] Stage E summariser (Phase 4) consumes `m1_sub_documents` to summarise per-section.
- [ ] Boundary-detection F1 benchmark on the 50-doc hand-annotated corpus per doc 03_M1_2 §validation (target F1 ≥ 0.85). Harness shipped; data follows the standard fixture-gated pattern.

## Blockers

None code-side. Backend runtime tests gated on `uv` + Docker testcontainer Postgres, neither present in this Claude Code environment.

## Cross-references

- Related session: [Session 34 — 2026-05-17](../../../08-Findings-Log/SESSIONS.md)
- Predecessor: [Session 33 / F-156 — doc catch-up](../../../08-Findings-Log/SESSIONS.md) — flagged the 5 carry-forwards this lap closes.
- Spec docs: [02_M1_Data_Requirements §2.8 + §2.10 + §5 mermaid](../02_M1_Data_Requirements.md), [03_M1_2_Gazette_Segmentation](../03_M1_2_Gazette_Segmentation.md), [04_M1_2_Metadata_Extraction_Patterns §3.3](../04_M1_2_Metadata_Extraction_Patterns.md).
- Feature: F-157 in [FEATURES](../../../08-Findings-Log/FEATURES.md)