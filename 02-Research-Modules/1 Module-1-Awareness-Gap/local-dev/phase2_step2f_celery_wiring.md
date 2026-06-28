---
tags: [tracker, m1, local-dev, phase2, step-2f]
source: synthesised
layer: tracker
module: m1
---

# Phase 2 Step 2f — Wire preprocessing into Celery pipeline + DB persistence (local dev)

> **Shipped:** Session 32 / F-155.
> **Spec**: [planned-for-development/6_setup.md](../planned-for-development/6_setup.md) · [04_M1_Preprocessing_Pipeline](../04_M1_Preprocessing_Pipeline.md) · [02_M1_Data_Requirements §2.1 + §2.8](../02_M1_Data_Requirements.md).

## 1 · What this step does

Closes the gap from Step 2e (which shipped the ml-package only). Adds:

- New Celery task `preprocess_gazette_task(reg_id)` chained automatically after `extract_gazette`.
- New `'preprocessed'` pipeline status (extends the canonical state machine).
- New `m1_regulation_penalties` junction table for multi-penalty data.
- New `cleaned_text` + `amendment_type` columns on `m1_regulations`.

After this step: a row flows `ingested → extracted → preprocessed` automatically.

## 2 · Prerequisites

- Steps 2a-2e passing.
- Migration `202605240001_m1_preprocessing_columns_and_penalties.py` applies cleanly.
- Redis running (Docker or native).
- `xlm-roberta-base` pre-warmed (§3 of [phase2_step2e_preprocessing](phase2_step2e_preprocessing.md)).
- `lid.176.bin` staged (§3 of [phase2_step2d_language_wijesekara](phase2_step2d_language_wijesekara.md)).

## 3 · Apply the migration

```bash
cd ~/repos/xyz/enigmatrix-backend
uv run alembic upgrade head
# Expected: 'Running upgrade 202605230001 -> 202605240001, m1_preprocessing_columns_and_penalties'
```

Round-trip check (proves the migration is reversible):

```bash
uv run alembic downgrade -1   # backs out 202605240001
uv run alembic upgrade head   # re-applies
```

The downgrade exercises the row-state-collapse rescue: any `status='preprocessed'` rows get reset to `'extracted'` before the CHECK constraint is narrowed back to the original 7 values.

## 4 · Run the integration tests

```bash
cd ~/repos/xyz/enigmatrix-backend
uv run pytest app/tests/integration/test_celery_preprocess_gazette.py -v
```

Expected (Session 32 baseline; Session 34 adds 2 more):
- **4 tests pass** (Session 32 / F-155):
  - `test_preprocess_gazette_flips_status_and_populates_metadata` — DoD round-trip on the VAT-amendment input.
  - `test_preprocess_gazette_skips_non_extracted` — non-`extracted` rows return `{"status": "skipped"}`.
  - `test_preprocess_gazette_respects_admin_curated_fields` — admin-set values survive.
  - `test_preprocess_gazette_idempotent_penalties` — same penalty count after re-run.
- **6 tests pass** (Session 34 / F-157 adds 2 more — see [phase2_session34_cleanup](phase2_session34_cleanup.md)).

Regression — Step 2b chain still green:

```bash
uv run pytest app/tests/integration/test_celery_extract_gazette.py -v   # 2 tests pass
```

## 5 · End-to-end manual smoke (full Phase 2 chain)

Three terminals — Redis + Celery worker + Python REPL.

### Terminal 1 — Redis + Postgres

```bash
cd ~/repos/xyz
docker compose -f docker-compose.dev.yml up -d postgres redis
```

### Terminal 2 — Celery worker

```bash
cd ~/repos/xyz/enigmatrix-backend
uv run celery -A app.celery_config worker -l info
```

Watch for: `celery@<host> ready.`

### Terminal 3 — Seed an `ingested` row + trigger

```bash
cd ~/repos/xyz/enigmatrix-backend
uv run python
```

```python
import asyncio
from pathlib import Path
from app.db.session import SessionLocal
from app.models.regulation import M1Regulation

async def seed():
    async with SessionLocal() as s:
        row = M1Regulation(
            regulation_short_code="SMOKE_F157_2486_22",
            document_type="extraordinary_gazette",
            document_number="2486/22",
            gazette_number="2486/22",
            title_en="Smoke test gazette",
            raw_pdf_path="m1/raw/sample_gazette_2486_22.pdf",
            status="ingested",
        )
        s.add(row)
        await s.commit()
        return str(row.regulation_id)

reg_id = asyncio.run(seed())
print(f"Seeded regulation_id={reg_id}")

from app.tasks.m1 import extract_gazette
result = extract_gazette.delay(reg_id).get(timeout=120)
print(f"extract result: {result}")
```

The PDF at `enigmatrix-backend/storage/m1/raw/sample_gazette_2486_22.pdf` must exist (Session 23 fixture copied there during a prior Step 2a manual run).

In Terminal 2 (worker), watch for both log lines:

```
extract_gazette: regulation <uuid> extracted via pymupdf (X chars)
preprocess_gazette: regulation <uuid> preprocessed (cleaned_text=N chars, penalties=M, sub_documents=K, primary_language=en)
```

## 6 · Verify in SQL

```bash
docker compose -f ~/repos/xyz/docker-compose.dev.yml exec postgres psql -U enigmatrix -d enigmatrix_dev
```

```sql
SELECT regulation_short_code, status, gazette_number, effective_date,
       penalty_range_lkr, principal_act_amended, amendment_type,
       length(raw_text) AS raw_len, length(cleaned_text) AS clean_len
FROM m1_regulations WHERE regulation_short_code = 'SMOKE_F157_2486_22';
```

Expected:
- `status` = `preprocessed`
- 4 metadata fields populated (or NULL if extraction didn't find them; admin-set values would be preserved here).
- `amendment_type` set.
- `clean_len` > 0 (cleaned text persisted).

```sql
SELECT sequence_idx, penalty_type, min_lkr, max_lkr, imprisonment_months, is_admin_set
FROM m1_regulation_penalties
WHERE regulation_id = (SELECT regulation_id FROM m1_regulations
                       WHERE regulation_short_code = 'SMOKE_F157_2486_22')
ORDER BY sequence_idx;
```

Expected: ≥ 0 rows (depends on whether the test gazette has penalty regex matches). The `is_admin_set` column ships in Session 34; rows are all `false` here.

```sql
\q
```

## 7 · Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ProgrammingError: column "cleaned_text" does not exist` | Migration `202605240001` not applied | `uv run alembic upgrade head` |
| `IntegrityError: ck_m1_regulations_status` on row save | Trying to write a status value not in the enum | Status must be in `('ingested','extracted','preprocessed','classified','summarized','alerted','archived','extraction_failed')` |
| Task hangs on first invocation | xlm-roberta-base downloading (~1.1 GB to HF cache) | Pre-warm with `uv run python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('xlm-roberta-base')"` |
| `FileNotFoundError: fastText model not found` | lid.176.bin not staged for the worker | `cd ../enigmatrix-ml && uv run python scripts/download_lid_model.py --target storage/models/m1/baseline/lid.176.bin` |
| Row stays at `status='extracted'` indefinitely | Worker not running OR enqueue raised (check warning logs) | Restart Celery worker; check Redis is reachable |
| Row at `status='extraction_failed'` | Preprocessing raised exception → task caught it and flipped status | Check the worker log for the traceback |
| `m1_regulation_penalties` empty after task | Gazette text doesn't trigger penalty regex | Expected — not all gazettes have penalty clauses |

## 8 · After verifying

```powershell
graphify update C:\Reasearch\xyz
graphify update C:\sme
```

## 9 · Cross-references

- [planned-for-development/6_setup.md](../planned-for-development/6_setup.md) — Step 2f setup spec
- [phase2_step2e_preprocessing](phase2_step2e_preprocessing.md) — predecessor (ml-package orchestrator)
- [phase2_session34_cleanup](phase2_session34_cleanup.md) — Session 34 extensions (segmenter promotion + penalty enum widen + is_admin_set + m1_sub_documents)
- [02_M1_Data_Requirements §2.1 + §2.8](../02_M1_Data_Requirements.md) — schema
- [04_M1_Preprocessing_Pipeline](../04_M1_Preprocessing_Pipeline.md) — pipeline spec