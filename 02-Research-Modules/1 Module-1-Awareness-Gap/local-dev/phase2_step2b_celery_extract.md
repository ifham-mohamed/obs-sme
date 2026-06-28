---
tags: [tracker, m1, local-dev, phase2, step-2b]
source: synthesised
layer: tracker
module: m1
---

# Phase 2 Step 2b — Celery + Stage-B PDF extraction (local dev)

> **Shipped:** Session 26 / F-148 (Celery infra + `extract_gazette` task + PyMuPDF/pdfplumber/Tesseract chain).
> **Spec**: [planned-for-development/2_setup.md](../planned-for-development/2_setup.md) · [03_M1_1_PDF_Extraction_Chain](../03_M1_1_PDF_Extraction_Chain.md) §2.

## 1 · What this step does

A row at `status='ingested'` (from Step 2a) gets picked up by the `extract_gazette` Celery task → runs the PyMuPDF / pdfplumber / Tesseract extraction chain → writes `raw_text` + `extraction_method` + `extracted_at` → flips `status='extracted'`.

## 2 · Prerequisites

- Step 2a passing locally ([phase2_step2a_scrapy_spider](phase2_step2a_scrapy_spider.md)).
- Migration `202605230001_m1_regulations_extraction_columns.py` applied (`raw_text`, `extraction_method`, `extracted_at` columns).
- Tesseract + sin + tam + poppler on the apt deps list (verify via `tesseract --list-langs`).
- Redis available (Docker or `redis-server`).

```bash
cd ~/repos/xyz
docker compose -f docker-compose.dev.yml up -d postgres redis
cd enigmatrix-backend && uv run alembic upgrade head
```

## 3 · Run the integration tests (Postgres + eager Celery)

```bash
cd ~/repos/xyz/enigmatrix-backend
uv run pytest app/tests/integration/test_celery_extract_gazette.py -v
```

Expected: **2 passed** (eager Celery — no broker needed):
- `test_extract_gazette_flips_status_and_writes_text` — `ingested` → `extracted` with `raw_text` non-empty.
- `test_extract_gazette_skips_non_ingested` — already-`extracted` rows are skipped (idempotent).

## 4 · End-to-end run with a real Celery worker

You'll need 3 terminals (all WSL):

### Terminal 1 — Redis (if not via Docker)

```bash
# Either:
docker compose -f ~/repos/xyz/docker-compose.dev.yml up -d redis
# Or native:
redis-server --daemonize yes
redis-cli ping   # expect PONG
```

### Terminal 2 — Celery worker

```bash
cd ~/repos/xyz/enigmatrix-backend
uv run celery -A app.celery_config worker -l info --concurrency=2

uv run celery -A app.celery_config worker -l info
```

Watch the log for `celery@<host> ready.`

### Terminal 3 — Trigger the task

```bash
cd ~/repos/xyz/enigmatrix-backend
uv run python
```

```python
# Inside the REPL:
from app.tasks.m1 import extract_gazette
# Grab a real regulation_id from the seeded data or your Step 2a run:
import asyncio
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.regulation import M1Regulation

async def first_ingested():
    async with SessionLocal() as s:
        row = (await s.execute(
            select(M1Regulation).where(M1Regulation.status == "ingested").limit(1)
        )).scalar_one_or_none()
        return str(row.regulation_id) if row else None

reg_id = asyncio.run(first_ingested())
print(f"Using regulation_id={reg_id}")

# Dispatch — eager_propagates=False here, so this runs on the Celery worker:
result = extract_gazette.delay(reg_id)
print(result.get(timeout=120))   # blocks until done
# {"status": "extracted", "regulation_id": "...", "method": "pymupdf", "chars": "12345"}
```

In Terminal 2 (worker), watch the log:

```
extract_gazette: regulation <uuid> extracted via pymupdf (12345 chars)
preprocess_gazette: failed to enqueue ...  # Step 2f chain — see note below
```

The "failed to enqueue" warning is expected unless you also have Step 2f's `preprocess_gazette_task` registered + the worker can route it. The Step 2b row still flips to `extracted` correctly.

## 5 · Verify the result

```sql
-- psql (Terminal 4):
docker compose -f ~/repos/xyz/docker-compose.dev.yml exec postgres psql -U enigmatrix -d enigmatrix_dev

SELECT regulation_id, status, extraction_method, length(raw_text) AS chars, extracted_at
FROM m1_regulations
WHERE regulation_id = '<paste-from-above>';
\q
```

Expected:
- `status` = `extracted`
- `extraction_method` ∈ `{pymupdf, pdfplumber, tesseract}`
- `length(raw_text)` > 100 (most likely thousands)
- `extracted_at` is now (UTC)

## 6 · Confirm the auto-chain to Step 2f works (if both are deployed)

If both Step 2b AND Step 2f have shipped (which is the current state):

- After the extract task succeeds, it enqueues `preprocess_gazette_task` via lazy `.delay()`.
- A second log line should appear: `preprocess_gazette: regulation <uuid> preprocessed (cleaned_text=N chars, penalties=M, sub_documents=K, primary_language=en)`.
- Final `status` should be `preprocessed`, not `extracted`.

If you DON'T see `status='preprocessed'`:
- Check the Celery worker log for the warning about failed enqueue.
- Confirm `app/celery_config.py` `include=[...]` lists `"app.tasks.m1.preprocess_gazette"`.

## 7 · Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Connection refused` on `redis://localhost:6379` | Redis container not up OR native redis-server not started | `docker compose -f ../docker-compose.dev.yml up -d redis` OR `redis-server --daemonize yes` |
| `tesseract not found` during Tesseract extraction | apt deps missing | `sudo apt install tesseract-ocr tesseract-ocr-sin tesseract-ocr-tam` |
| `FileNotFoundError: PDF not on disk` | row's `raw_pdf_path` doesn't exist | Run Step 2a first to populate `storage/m1/raw/` |
| Task hangs at `task_acks_late=True` | Postgres lost connection during the task | Restart Postgres + worker |
| Worker log: `Received task: app.tasks.m1.extract_gazette.extract_gazette ... not registered` | Worker started before code change | Stop worker (Ctrl+C) + restart |
| Row stuck at `status='extraction_failed'` after task | Tesseract OOM OR PDF corrupt | Check Tesseract logs; inspect the PDF manually with `pdftotext` |
| Task succeeds but row at `status='extracted'` (no preprocess) | Step 2f chain didn't fire | See §6 above |

## 8 · After verifying, standing cadence

```powershell
graphify update C:\Reasearch\xyz
graphify update C:\sme
```

## 9 · Cross-references

- [planned-for-development/2_setup.md](../planned-for-development/2_setup.md) — full Step 2b setup spec
- [phase2_step2a_scrapy_spider](phase2_step2a_scrapy_spider.md) — predecessor
- [phase2_step2c_extraction_chain](phase2_step2c_extraction_chain.md) — canonical extraction module location
- [phase2_step2f_celery_wiring](phase2_step2f_celery_wiring.md) — downstream auto-chain
- [03_M1_1_PDF_Extraction_Chain](../03_M1_1_PDF_Extraction_Chain.md) — chain rationale + thresholds