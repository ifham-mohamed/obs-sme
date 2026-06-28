# 2 — Setup & Verification: Step 2b — Celery wiring + Stage-B extraction

> **Companion to** [2.md](2026-05%20Step%202b%20-%20Celery%20task%20wiring%20+%20Stage-B%20extraction%20(M1%20Phase%202).md) — the development plan for Step 2b.
> **Predecessor's setup:** [1_setup.md](1_setup.md) (run Step 2a's setup first; this guide assumes Step 2a is working — the parse-bug fix from Session 25 must be in place).
> **Audience:** the developer about to execute the Step 2b plan locally, plus the same dev verifying it end-to-end after the code lands.

This guide is *forward-looking* — Step 2b's code hasn't been written yet (Session 25 produced only the plan). When Session 26 (or whichever next session) executes [2.md](2026-05%20Step%202b%20-%20Celery%20task%20wiring%20+%20Stage-B%20extraction%20(M1%20Phase%202).md), follow this guide to set up the environment and verify the DoD.

---

## Deployment context

Live deployments (unchanged from Session 24):

| Surface | URL | Health check |
|---|---|---|
| Backend (FastAPI) | <https://enigmatrix-backend.vercel.app/> | `GET /health` → `{"status":"ok","service":"enigmatrix-api"}` |
| Frontend (Next.js) | <https://enigmatrix-frontend.vercel.app/> | open in browser |

> **Important — Vercel does not run Celery workers.** Same caveat as the spider in Step 2a, only more so: Celery needs a long-lived process (worker + Beat) plus a Redis broker. Vercel's serverless model can't host either. **For Step 2b development:** Redis + worker + Beat all run locally. **For production:** worker hosting lands on a Fly.io machine; see [../07_M1_Deployment_Integration.md §5](../07_M1_Deployment_Integration.md) for the deploy spec. Deployment configuration is **out of scope for Step 2b** — this slice ships the *code*; the production deploy is a follow-up.

---

## Prerequisites

| Requirement | How to install / check |
|---|---|
| Step 2a working | `cd enigmatrix-backend && uv run pytest -k test_spider_parse_yields_gazette_item -v` → 1 passed. If failing, Session 25's parse-bug fix is missing — re-pull. |
| **Redis** running locally | `brew install redis && brew services start redis`, or `docker run -d -p 6379:6379 redis:7-alpine`. Verify with `redis-cli ping` → `PONG`. |
| **Tesseract** with `sin` + `tam` language packs | macOS: `brew install tesseract tesseract-lang`. Linux: `apt install tesseract-ocr tesseract-ocr-sin tesseract-ocr-tam`. Verify with `tesseract --list-langs` → output includes `eng`, `sin`, `tam`. |
| **poppler** (for `pdf2image`) | macOS: `brew install poppler`. Linux: `apt install poppler-utils`. |
| **Docker daemon** (for the testcontainer-based integration tests) | macOS: open Docker Desktop. Linux: `sudo systemctl start docker`. Verify: `docker info`. Without Docker, the 2 testcontainer-backed tests skip with `DockerException`. |
| Local Postgres | The `docker-compose.dev.yml` at the repo root brings one up: `docker compose -f docker-compose.dev.yml up -d postgres`. Or use the testcontainer one for tests. |
| Python deps via `uv` | `uv sync` (after pulling Step 2b's pyproject.toml change adding 5 new deps). |

---

## Local setup

```bash
cd enigmatrix-backend

# 1. Pull the new deps (celery[redis] + PyMuPDF + pdfplumber + pytesseract + pdf2image).
uv sync

# 2. Make sure the new env vars are in your .env (added in Step 2b):
#       CELERY_BROKER_URL=redis://localhost:6379/0
#       M1_PDF_TEXT_THRESHOLD=200
#       M1_PDF_SCANNED_THRESHOLD=30
# Copy from .env.example if you don't have them.

# 3. Apply the new migration (adds m1_regulations.raw_text / extraction_method / extracted_at).
uv run alembic upgrade head
# Expected end of output: "Running upgrade 202605220001 -> 202605230001, m1_regulations: extraction columns"
```

Confirm the migration shipped:

```bash
uv run alembic current
# Expected: 202605230001 (head)
```

---

## Start the worker + Beat

For Step 2b development you need **three terminal windows** (or a `tmux` setup):

```bash
# Terminal 1 — Redis (skip if `brew services` is already running it)
redis-server

# Terminal 2 — Celery worker
cd enigmatrix-backend
uv run celery -A app.celery_config worker --concurrency=2 --loglevel=info

# Terminal 3 — Celery Beat (the scheduler)
cd enigmatrix-backend
uv run celery -A app.celery_config beat --loglevel=info
```

Worker logs should show:

```
[tasks]
  . app.tasks.m1.extract_gazette
  . app.tasks.m1.gazette_scraper

celery@<host> ready.
```

Beat logs should show the 6 h schedule for `gazette_scraper`.

---

## Verification — automated (CI tests)

Step 2b's tests run in `task_always_eager=True` mode — Celery tasks execute synchronously in-process, no real broker / worker needed. **Most of these tests need Docker** (for the testcontainer Postgres); the 2 unit tests don't.

```bash
cd enigmatrix-backend

# Unit tests (no Docker required)
uv run pytest app/tests/unit/test_pdf_classifier.py app/tests/unit/test_text_extractors.py -v

# Integration tests (Docker required for testcontainer Postgres)
uv run pytest app/tests/integration/test_celery_extract_gazette.py \
              app/tests/integration/test_gazette_scraper_task.py -v
```

Expected per the plan:

| Test | What it asserts |
|---|---|
| `test_pdf_classifier` (unit) | `classify_pdf()` returns `text_pdf` / `hybrid` / `scanned` on fixture PDFs at varying char densities (150 / 180 / 200 / 220 / 250 chars/page). |
| `test_text_extractors` (unit) | `extract_pymupdf()` / `extract_pdfplumber()` / `extract_tesseract()` each return non-empty text on a fixture PDF + the right method label. |
| `test_celery_extract_gazette` (integration) | Eager-mode `extract_gazette(reg_id)` flips status `ingested → extracted` + writes `raw_text` + `extraction_method` + `extracted_at`. |
| `test_gazette_scraper_task` (integration) | Eager-mode `gazette_scraper.delay()` returns the spider's summary dict + triggers `extract_gazette` enqueue per ingested row. |

---

## Verification — manual smoke check (real Celery + real network)

The end-to-end flow: spider scrapes → enqueues `extract_gazette` → worker picks it up → row flips to `extracted`.

```bash
# 1. Start Redis + worker + Beat (3 terminals as above).

# 2. Trigger the spider as a Celery task (instead of `scrapy crawl`):
cd enigmatrix-backend
uv run python -c "from app.tasks.m1 import gazette_scraper; print(gazette_scraper.delay().id)"
# Prints a task UUID. The worker picks it up.

# 3. Watch the worker logs — you should see:
#    [INFO] gazette_scraper succeeded: {'crawled': N, 'duration_s': D}
#    Followed by N `extract_gazette` task starts:
#    [INFO] extract_gazette(<reg_id>) → method=pymupdf, chars=12345

# 4. Inspect the DB:
psql "$DATABASE_URL" -c "
  SELECT regulation_id, gazette_number, status, extraction_method,
         LENGTH(raw_text) AS text_len, extracted_at
  FROM m1_regulations
  WHERE status IN ('ingested', 'extracted')
  ORDER BY created_at DESC
  LIMIT 10;
"
```

**Expected:** N rows now have `status='extracted'`, `extraction_method` set, `raw_text` populated (typical: 5 k–30 k chars for a normal gazette), `extracted_at` recent.

**Beat verification:** wait 6 hours or temporarily change the Beat schedule to `*/2 * * * *` (every 2 min) for testing; restart Beat; watch the worker logs for periodic `gazette_scraper` invocations.

---

## Rollback

```bash
cd enigmatrix-backend

# 1. Stop worker + Beat (Ctrl-C in each terminal).

# 2. Roll back the migration:
uv run alembic downgrade -1
# Drops m1_regulations.raw_text / extraction_method / extracted_at.

# 3. (Optional) Reset rows to 'ingested' if you want to re-extract:
psql "$DATABASE_URL" -c "
  UPDATE m1_regulations SET status='ingested', extraction_method=NULL,
                            raw_text=NULL, extracted_at=NULL
  WHERE status='extracted';
"
```

The rollback is fully reversible. Note: rolling back the migration *while* the worker is still running will cause the next `extract_gazette` to fail because the `raw_text` column won't exist — stop the worker first.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `celery: command not found` | `uv sync` not run | `cd enigmatrix-backend && uv sync` |
| Worker shows `tasks: (empty)` | Tasks not registered | Confirm `app/celery_config.py` calls `celery_app.autodiscover_tasks(['app.tasks'])` |
| `redis.exceptions.ConnectionError` | Redis not running | `brew services start redis` or `docker run -d -p 6379:6379 redis:7-alpine` |
| `pytesseract.TesseractNotFoundError` | Tesseract not installed | `brew install tesseract tesseract-lang` |
| `pdf2image.exceptions.PDFInfoNotInstalledError` | Poppler missing | `brew install poppler` |
| Spider runs but 0 rows flip to `extracted` | `extract_gazette.delay(...)` not wired in `M1RegulationsInsertPipeline` | Step 2b plan §"Modified files" — confirm the TODO log was replaced |
| `raw_text` is empty | PDF was scanned-only; Tesseract OCR failed | Check `tesseract --list-langs` includes `sin` + `tam`; verify the fixture PDF isn't 0-byte |
| `documents.gov.lk` returns 0 items | Listing-page xpath / regex mismatch | Inspect the live page; broaden `_GAZETTE_NUMBER_RE` or the `parse()` xpath; Session 25's `ancestor::tr` fix targets `<table>` listings |

---

## What's deferred to Step 2c

- **Language detection per chunk.** `extract_gazette` produces a single `raw_text` blob; per-line language routing (EN / SI / TA / mixed) lands in Step 2c — spec at [../10_M1_1_Language_Detection_Routing.md](../10_M1_1_Language_Detection_Routing.md).
- **Wijesekara → Unicode conversion** for pre-2010 scanned Sinhala. Same step — [../10_M1_2_OCR_Wijesekara_Conversion.md](../10_M1_2_OCR_Wijesekara_Conversion.md).
- **Segmenter for multi-notice gazettes.** A single gazette PDF can contain N distinct notices; splitting them is [../03_M1_2_Gazette_Segmentation.md](../03_M1_2_Gazette_Segmentation.md). The MVP `extract_gazette` writes one `raw_text` blob per gazette; per-notice rows are a Step 2c/2d follow-up.
- **Production worker hosting on Fly.io.** Local-only for Step 2b. See [../07_M1_Deployment_Integration.md](../07_M1_Deployment_Integration.md).

The next paired files will be `3.md` + `3_setup.md` when Step 2c's plan lands.

---

## Cross-references

- **Plan that produces this code:** [2.md](2026-05%20Step%202b%20-%20Celery%20task%20wiring%20+%20Stage-B%20extraction%20(M1%20Phase%202).md)
- **Predecessor:** [1.md](2026-05%20Step%202a%20—%20Scrapy%20gazette%20spider%20(M1%20Phase%202%20—%20Ingest%20+%20extraction,%20MVP%20slice).md) + [1_setup.md](1_setup.md) (Step 2a — the spider)
- **Roadmap step:** [../16_M1_Development_Roadmap.md](../16_M1_Development_Roadmap.md) Phase 2 Step 2b
- **Detail docs:** [../03_M1_Data_Collection.md §6.1](../03_M1_Data_Collection.md) (Celery retry), [../03_M1_1_PDF_Extraction_Chain.md](../03_M1_1_PDF_Extraction_Chain.md) (PyMuPDF/pdfplumber/Tesseract chain)
- **Tracker entries** (when Step 2b executes): forthcoming Session-N / F-N rows in [../../tracker/SESSIONS.md](../../tracker/SESSIONS.md), [CHANGES.md](../../tracker/CHANGES.md), [FEATURES.md](../../tracker/FEATURES.md), and [../../../AI_WORK_LOG.md](../../../AI_WORK_LOG.md).
