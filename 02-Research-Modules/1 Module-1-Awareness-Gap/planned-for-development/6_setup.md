# 6_setup — Step 2f setup + verification guide

> Companion to [6.md](6.md) — user-actionable setup + verification for the Celery wiring + DB persistence layer.
> **Status:** ✅ Shipped Session 32 / F-155.

## 1. Deployment context

`enigmatrix-backend/app/tasks/m1/preprocess_gazette.py` runs on the Celery worker — the same one Step 2b stood up locally and Step 4a will host on Fly.io. It's the bridge between the ml workspace member (`m1.preprocessing`) and Postgres.

Live URLs unchanged:
- Backend health: <https://enigmatrix-backend.vercel.app/health>
- Worker hosting: local dev (this step); Fly.io machine when Step 4a lands.

Vercel does NOT run Celery workers (no long-lived processes). The persistence happens on whatever host runs the worker.

## 2. Prerequisites

Same as [5_setup.md](5_setup.md) §2 + working backend stack:

| Tool | Why | Install |
|---|---|---|
| Redis | Celery broker (from Step 2b) | `brew install redis` / `apt-get install redis-server` |
| Docker | Testcontainer Postgres for integration tests | Docker Desktop |
| `uv` | Backend package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

Verify:
```bash
which redis-server uv
docker info | grep -E "Server Version"   # Docker daemon running
```

## 3. Apply the migration

```bash
cd enigmatrix-backend
uv sync                                  # installs the new ml workspace dep + transitive
uv run alembic upgrade head              # forward — applies 202605240001
```

Round-trip verification:
```bash
uv run alembic downgrade -1              # backs out 202605240001
uv run alembic upgrade head              # forward again
```

Inspect the schema:
```bash
uv run python - <<'EOF'
from sqlalchemy import create_engine, text
from app.settings import get_settings
e = create_engine(get_settings().DATABASE_URL.replace("+asyncpg", ""))
with e.connect() as c:
    print("--- m1_regulations new columns ---")
    for row in c.execute(text("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name = 'm1_regulations'
          AND column_name IN ('cleaned_text', 'amendment_type')
    """)):
        print(row)
    print("--- m1_regulation_penalties table ---")
    for row in c.execute(text("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name = 'm1_regulation_penalties'
    """)):
        print(row)
    print("--- status CHECK constraint values ---")
    for row in c.execute(text("""
        SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c
        WHERE c.conname = 'ck_m1_regulations_status'
    """)):
        print(row)
EOF
```

Expected: `cleaned_text` + `amendment_type` columns present; `m1_regulation_penalties` has 10 columns including `penalty_id` UUID; CHECK constraint lists `'preprocessed'` among the values.

## 4. Run the integration tests

```bash
cd enigmatrix-backend
uv run pytest app/tests/integration/test_celery_preprocess_gazette.py -v
# 4 tests pass.

# Regression: Step 2b chain still green
uv run pytest app/tests/integration/test_celery_extract_gazette.py -v
# 2 tests pass.
```

Both rely on a testcontainer Postgres — Docker daemon must be running.

## 5. Manual end-to-end smoke (the full Phase 2 chain)

```bash
# Terminal 1: start Redis
redis-server

# Terminal 2: start Celery worker
cd enigmatrix-backend
uv run celery -A app.celery_config worker -l info

# Terminal 3: seed an 'ingested' row + trigger the chain
cd enigmatrix-backend
uv run python - <<'EOF'
import asyncio
from pathlib import Path
from app.db.session import SessionLocal
from app.models.regulation import M1Regulation

async def seed():
    async with SessionLocal() as s:
        row = M1Regulation(
            regulation_short_code="SMOKE_TEST_2486_22",
            document_type="extraordinary_gazette",
            document_number="2486/22",
            gazette_number="2486/22",
            title_en="Smoke test gazette",
            raw_pdf_path="m1/raw/sample.pdf",     # must exist under STORAGE_LOCAL_PATH
            status="ingested",
        )
        s.add(row)
        await s.commit()
        return str(row.regulation_id)

reg_id = asyncio.run(seed())
print(f"Seeded regulation_id={reg_id}")

# Trigger Stage B → which auto-chains Stage B+ (Step 2f preprocessing)
from app.tasks.m1 import extract_gazette
result = extract_gazette.delay(reg_id).get(timeout=120)
print(f"extract result: {result}")
EOF
```

Observe over the next ~30s (in the worker logs):
```
extract_gazette: regulation ... extracted via pymupdf (X chars)
preprocess_gazette: regulation ... preprocessed (cleaned_text=N chars, penalties=M, primary_language=en)
```

Verify in SQL:
```sql
SELECT regulation_short_code, status, gazette_number, effective_date,
       penalty_range_lkr, principal_act_amended, amendment_type,
       length(raw_text) AS raw_len, length(cleaned_text) AS clean_len
FROM m1_regulations WHERE regulation_short_code = 'SMOKE_TEST_2486_22';

SELECT sequence_idx, penalty_type, min_lkr, max_lkr, imprisonment_months
FROM m1_regulation_penalties WHERE regulation_id = '<reg_id>'
ORDER BY sequence_idx;
```

Expected: `status='preprocessed'`, all 4 metadata fields populated, `amendment_type` set, ≥ 0 penalty rows.

## 6. Rollback

```bash
cd enigmatrix-backend

# DB rollback:
uv run alembic downgrade -1

# Code rollback (drops Step 2f files; Step 2b chain reverts to no chaining):
git revert 73d47ab    # Step 2f commit on Enigmatrixx/enigmatrix-backend@main
```

After rollback: extract_gazette still works; rows stop at `status='extracted'`; cleaned_text + amendment_type columns gone; junction table dropped.

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ProgrammingError: column "cleaned_text" does not exist` | Migration not applied | `uv run alembic upgrade head` |
| Task hangs on first invocation | xlm-roberta-base downloading (~1.1 GB to HF cache) | Pre-warm: `uv run python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('xlm-roberta-base')"` |
| `FileNotFoundError: fastText model not found` | lid.176.bin not staged on the worker | `cd enigmatrix-ml && uv run python scripts/download_lid_model.py --target storage/models/m1/baseline/lid.176.bin` |
| Row stays at `extracted` indefinitely | Worker not running OR enqueue raised (check warning logs) | Restart Celery worker; check Redis is reachable |
| `m1_regulation_penalties` rows duplicate on re-run | Idempotency broken | Verify the task is using DELETE-then-INSERT (look for `delete(M1RegulationPenalty).where(...)` before the loop) |
| `IntegrityError: ck_m1_regulations_status` on rollback | A `preprocessed` row exists at downgrade time | The downgrade handles this — UPDATE collapses to `'extracted'` first. If you wrote the migration manually, confirm the UPDATE precedes the drop_constraint |

## 8. What's deferred

- **Doc 02 §2.1 enum amendment** to add `'preprocessed'` officially. Doc-only follow-up — Session 33 / F-156.
- **Architecture mermaid diagram update** in doc 02 — add a `Stage B+ Preprocessing` sub-node. Doc-only.
- **`is_admin_set` flag on `m1_regulation_penalties`** — for when an admin UI lets admins curate junction rows. The task would then skip rows where `is_admin_set=True` during the DELETE-then-INSERT pass.
- **Production Dockerfile pre-warm** of lid.176.bin + xlm-roberta-base. Add to the worker image build when Step 4a deploys to Fly.io.
- **`preprocessed_at` timestamp column** (analog to `extracted_at`). Currently the `TimestampMixin.updated_at` moves on the preprocessing commit; a future column block can land all the stage-timestamps together when stages C/E/F arrive.

## 9. Cross-references

- Plan: [6.md](6.md)
- Predecessor setup: [5_setup.md](5_setup.md) (Step 2e)
- Migration: `enigmatrix-backend/alembic/versions/202605240001_m1_preprocessing_columns_and_penalties.py`
- Spec docs needing parallel update (Session 33 / F-156): [../02_M1_Data_Requirements.md §2.1](../02_M1_Data_Requirements.md), [../16_M1_Development_Roadmap.md Phase 2 DoD](../16_M1_Development_Roadmap.md)
- Tracker: F-155 in `c:\sme\08-Findings-Log\FEATURES.md`; Session 32 in `SESSIONS.md`.
