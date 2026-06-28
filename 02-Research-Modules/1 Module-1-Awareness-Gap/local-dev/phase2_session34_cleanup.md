---
tags: [tracker, m1, local-dev, phase2, session-34]
source: synthesised
layer: tracker
module: m1
---

# Phase 2 Session 34 cleanup — segmenter promotion + penalty enum widen + is_admin_set + m1_sub_documents (local dev)

> **Shipped:** Session 34 / F-157.
> **Spec**: [findings/2026-05-17-m1-phase2-cleanup-segmenter-penalty-subdocs](../findings/2026-05-17-m1-phase2-cleanup-segmenter-penalty-subdocs.md) · [02_M1_Data_Requirements §2.8 + §2.10](../02_M1_Data_Requirements.md) · [03_M1_2_Gazette_Segmentation](../03_M1_2_Gazette_Segmentation.md).

## 1 · What this step does

Closes 5 carry-forwards flagged at end of Session 33:

1. `m1.extraction.segmenter` promoted to standalone module — `NOTICE_BOUNDARY_RE` + `detect_sections` moved from `m1.preprocessing.chunking`; new `detect_sections_with_labels` classifies sections into 6 types (`part`/`schedule`/`section`/`notice`/`numbered_clause`/`preamble`).
2. `m1_regulation_penalties.penalty_type` CHECK enum widened 3 → 7 values to match the doc 02 §2.8 spec.
3. `is_admin_set BOOLEAN` flag added — admin-curated penalty rows survive re-extraction.
4. New `m1_sub_documents` junction table for per-section persistence (Stage E summariser consumer).
5. Doc 02 §5 mermaid diagram updated to show Stage B+ Preprocessing sub-node.

## 2 · Prerequisites

- Step 2f passing (all migrations through `202605240001` applied).
- Two new migrations from Session 34 to apply: `202605250001` (penalty enum widening + is_admin_set) and `202605260001` (m1_sub_documents).

## 3 · Apply both Session 34 migrations

```bash
cd ~/repos/xyz/enigmatrix-backend
uv run alembic upgrade head
# Expected: applies 202605250001 then 202605260001.
```

Round-trip check (exercises the enum-collapse rescue on downgrade):

```bash
uv run alembic downgrade -2   # backs out both Session-34 migrations
uv run alembic upgrade head   # re-applies
```

The double-downgrade verifies the careful state-collapse for both migrations:
- `202605250001` downgrade collapses extended-enum penalty rows (`license_revocation`, etc.) to `'fine'` before re-applying the narrower CHECK.
- `202605260001` downgrade drops the `m1_sub_documents` table.

## 4 · Run the ml regression (segmenter promotion + SectionInfo)

> **Always invoke through `uv run`.** Bare `pytest` / `python` resolve to
> the system Python (e.g. `/usr/bin/python3.14` on Ubuntu 24.04) which
> doesn't have the project deps (`pytesseract`, `fitz`/PyMuPDF,
> `fasttext-wheel`, `transformers`). `uv run` selects the workspace venv
> built by `uv sync`. `PYTHONPATH=$PWD` is no longer needed — `uv run`
> from `enigmatrix-ml/` resolves the `m1` package correctly.

```bash
cd ~/xyz/enigmatrix-ml
M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin uv run pytest tests/m1 -v
# Expected: 127 passed / 8 skipped (was 117/8 at end of Session 31 — net +10).
```

The 10 new tests are in `tests/m1/extraction/test_segmenter.py`:
- 5 NOTICE_BOUNDARY_RE pattern tests (numbered-clause positive, lowercase negative, PART, Schedule, Notice).
- 3 `detect_sections` tests (3-section doc, no-boundaries, empty).
- 6 `detect_sections_with_labels` tests (preamble + part + schedule + numbered_clause + notice + section types + offset-alignment + empty + no-boundaries).
- (5 tests moved out of `test_chunking.py` to here, then 5 new added — net +5; +5 from extended pattern coverage.)

## 5 · Run the backend integration tests (4 → 6 tests)

```bash
cd ~/repos/xyz/enigmatrix-backend
uv run pytest app/tests/integration/test_celery_preprocess_gazette.py -v
# Expected: 6 tests pass (4 from Session 32 + 2 new from Session 34).
```

The 2 new tests:
- `test_preprocess_gazette_preserves_admin_set_penalties` — seeds a row with `penalty_type='license_revocation'` (one of the 4 new widened enum values) and `is_admin_set=True`; runs the task; asserts the admin row survives + a parallel pipeline-set row is rebuilt fresh.
- `test_preprocess_gazette_persists_sub_documents` — seeds a row with `PART I` + `Schedule 1` markers; runs the task; asserts ≥ 2 `m1_sub_documents` rows with correct `section_type` classification + offset alignment.

## 6 · Segmenter CLI smoke

```bash
cd ~/repos/xyz/enigmatrix-ml
uv run python - <<'EOF'
from m1.extraction import detect_sections_with_labels

text = (
    "preamble before any boundary\n"
    "PART I\n"
    "first part body\n"
    "Schedule 1\n"
    "schedule body"
)
for s in detect_sections_with_labels(text):
    print(f"  [{s.sequence_idx}] type={s.section_type!r} label={s.section_label!r} "
          f"offsets=({s.char_offset_start},{s.char_offset_end}) text={s.text[:30]!r}")
EOF
```

Expected:

```
  [0] type='preamble' label=None offsets=(0,30) text='preamble before any boundary\n'
  [1] type='part' label='PART I' offsets=(30,53) text='PART I\nfirst part body\n'
  [2] type='schedule' label='Schedule 1' offsets=(53,77) text='Schedule 1\nschedule body'
```

## 7 · End-to-end manual smoke (full chain through Session 34)

After running the Step 2f manual smoke ([phase2_step2f_celery_wiring §5](phase2_step2f_celery_wiring.md)), verify the new tables populate:

```sql
docker compose -f ~/repos/xyz/docker-compose.dev.yml exec postgres psql -U enigmatrix -d enigmatrix_dev

-- Sub-documents written by the preprocess task
SELECT regulation_id, sequence_idx, section_type, section_label,
       length(text) AS section_chars
FROM m1_sub_documents
WHERE regulation_id = (SELECT regulation_id FROM m1_regulations
                       WHERE regulation_short_code = 'SMOKE_F157_2486_22')
ORDER BY sequence_idx;

-- Confirm is_admin_set defaults to FALSE for pipeline-extracted penalties
SELECT sequence_idx, penalty_type, is_admin_set
FROM m1_regulation_penalties
WHERE regulation_id = (SELECT regulation_id FROM m1_regulations
                       WHERE regulation_short_code = 'SMOKE_F157_2486_22')
ORDER BY sequence_idx;

-- Test the admin-curated preservation: manually INSERT an admin row + re-trigger
INSERT INTO m1_regulation_penalties
  (regulation_id, sequence_idx, penalty_type, min_lkr, max_lkr,
   imprisonment_months, context, is_admin_set, created_at, updated_at)
VALUES (
  (SELECT regulation_id FROM m1_regulations WHERE regulation_short_code = 'SMOKE_F157_2486_22'),
  0,
  'license_revocation',
  NULL, NULL, NULL,
  'Admin-curated: license revocation on 3rd offence',
  TRUE,
  now(), now()
)
ON CONFLICT (regulation_id, sequence_idx) DO NOTHING;

-- Flip status back so the task re-runs:
UPDATE m1_regulations SET status='extracted'
WHERE regulation_short_code = 'SMOKE_F157_2486_22';
\q
```

Then re-trigger `preprocess_gazette_task.delay(<reg_id>)` from the Python REPL. Re-query — admin row should survive, pipeline rows should renumber above its sequence_idx.

## 8 · Verify the segmenter type-classifier handles all 6 types

```bash
uv run python - <<'EOF'
from m1.extraction import detect_sections_with_labels

cases = {
    "PART": "preamble\nPART I\nbody",
    "Schedule": "preamble\nSchedule 1\nbody",
    "SECTION": "preamble\nSECTION 5\nbody",
    "Notice": "preamble\nNotice No. 12\nbody",
    "numbered_clause": "preamble\n1. The Act amends",
}

for label, text in cases.items():
    sections = detect_sections_with_labels(text)
    types = [s.section_type for s in sections]
    print(f"{label}: {types}")
EOF
```

Expected: each case produces `['preamble', <expected_type>]`.

## 9 · Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `IntegrityError: ck_m1_regulation_penalties_type` on penalty insert | Trying to write a value outside the 7-value enum | Valid values: `fine`, `imprisonment`, `both`, `license_revocation`, `business_closure`, `public_naming`, `asset_seizure` |
| `UniqueViolation: uq_m1_penalty_seq` on re-extraction | Admin row at sequence_idx=0 + pipeline trying to write 0 too | Expected — task is supposed to renumber pipeline rows above admin max. If you see this, the renumbering logic broke; check `app/tasks/m1/preprocess_gazette.py` |
| `m1_sub_documents` empty after task | Detector found no boundaries — single preamble section was dropped | Verify input text has `PART`/`Schedule`/`Notice`/numbered-clause markers; pure-text gazettes produce 1 preamble row |
| `IntegrityError: ck_m1_sub_documents_type` | section_type value not in CHECK enum | Valid: `part`, `schedule`, `section`, `notice`, `numbered_clause`, `preamble` |
| Circular import on `m1.extraction.segmenter` | Old code-side cache | Hard restart Python; `rm -rf __pycache__/`; verify `m1.extraction.types` has `SectionInfo` (moved from preprocessing in Session 34) |
| `ImportError: cannot import name 'SectionInfo' from 'm1.preprocessing.types'` | Module not refreshed | `m1.preprocessing.types` now re-exports from `m1.extraction.types`; should still work — check workspace re-sync |

## 10 · After verifying

```powershell
graphify update C:\Reasearch\xyz
graphify update C:\sme
```

## 11 · Cross-references

- [findings/2026-05-17-m1-phase2-cleanup-segmenter-penalty-subdocs](../findings/2026-05-17-m1-phase2-cleanup-segmenter-penalty-subdocs.md) — Session 34 finding entry
- [phase2_step2f_celery_wiring](phase2_step2f_celery_wiring.md) — predecessor (the wiring this cleanup extends)
- [02_M1_Data_Requirements §2.8 + §2.10](../02_M1_Data_Requirements.md) — m1_regulation_penalties + m1_sub_documents schemas
- [03_M1_2_Gazette_Segmentation](../03_M1_2_Gazette_Segmentation.md) — segmentation strategy spec
- Next milestone: **Phase 3 Step 3a** — Label Studio + 20-doc calibration test ([16_M1_Development_Roadmap](../16_M1_Development_Roadmap.md) §Phase-3).