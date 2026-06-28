# 1 — Setup & Verification: M1 Phase 2 Step 2a — Scrapy gazette spider

> **Companion to** [1.md](2026-05%20Step%202a%20—%20Scrapy%20gazette%20spider%20(M1%20Phase%202%20—%20Ingest%20+%20extraction,%20MVP%20slice).md) — the development plan for this slice.
> **Audience:** the developer setting up the environment locally and verifying that the spider works end-to-end. Covers automated CI tests + manual real-network smoke check + rollback.
> **What was built:** see [1.md](2026-05%20Step%202a%20—%20Scrapy%20gazette%20spider%20(M1%20Phase%202%20—%20Ingest%20+%20extraction,%20MVP%20slice).md) for the plan; [../14_M1_Tracking_Workflows.md](../14_M1_Tracking_Workflows.md) (admin pipeline-state tracking) for the user-facing workflow.

---

## Deployment context

Live deployments (Vercel):

| Surface | URL | Health check |
|---|---|---|
| Backend (FastAPI) | <https://enigmatrix-backend.vercel.app/> | `GET /health` → `{"status":"ok","service":"enigmatrix-api"}` |
| Frontend (Next.js) | <https://enigmatrix-frontend.vercel.app/> | open in browser |

Quick check:

```bash
curl https://enigmatrix-backend.vercel.app/health
# {"status":"ok","service":"enigmatrix-api"}
```

> **Important — Vercel does not run the spider.** Vercel is serverless. The FastAPI app deployed there handles HTTP requests (auth, regulation CRUD, survey flow) but **does not** run long-lived workers. The Scrapy spider added in this slice is a *process-style worker* — it runs locally during dev and will run on a dedicated host (Fly.io per [../07_M1_Deployment_Integration.md](../07_M1_Deployment_Integration.md)) in production. **For Step 2a, the spider runs only on your local machine against the production-DB-or-local-DB you choose to point it at.**

---

## Prerequisites

| Requirement | How to check |
|---|---|
| Python 3.11 or 3.12 | `python --version` |
| `uv` package manager | `uv --version` (or `pip install uv` to install) |
| Local Postgres 16 reachable (for the manual smoke check) | `psql --version`; `docker compose -f docker-compose.dev.yml up -d postgres` from the repo root brings one up |
| Internet access (for the manual smoke check that hits `documents.gov.lk`) | `curl -sI https://documents.gov.lk/` |

For the CI test (`pytest`) you don't need a local Postgres — the test uses `testcontainers[postgres]` which spins one up in Docker.

---

## Local setup

```bash
cd enigmatrix-backend

# 1. Pull the new dep (scrapy 2.11+).
uv sync

# 2. Copy the example env file (skip if you already have .env).
cp .env.example .env
# Edit DATABASE_URL, APP_SECRET_KEY, JWT_SECRET to local values.
# STORAGE_LOCAL_PATH defaults to ./storage — leave as-is unless you want a different directory.

# 3. Apply the new migration (adds m1_regulations.status / raw_pdf_path / gazette_number).
uv run alembic upgrade head
# Expected: "Running upgrade 202605210001 -> 202605220001, m1_regulations: status state machine + raw_pdf_path + gazette_number"
```

Confirm the migration shipped:

```bash
uv run alembic current
# Expected output ends with: 202605220001 (head)
```

---

## Verification — automated (CI tests)

The 4 integration tests run end-to-end against a disposable testcontainer Postgres + mocked HTTP — no real network, fully reproducible.

```bash
cd enigmatrix-backend
uv run pytest app/tests/integration/test_gazette_spider.py -v
```

Expected output:

```
app/tests/integration/test_gazette_spider.py::test_spider_parse_yields_gazette_item PASSED
app/tests/integration/test_gazette_spider.py::test_pdf_download_pipeline_writes_file PASSED
app/tests/integration/test_gazette_spider.py::test_insert_pipeline_creates_m1_regulations_row PASSED
app/tests/integration/test_gazette_spider.py::test_insert_pipeline_is_idempotent_on_duplicate PASSED

4 passed in N.NNs
```

What each test covers:

| Test | What it checks |
|---|---|
| `test_spider_parse_yields_gazette_item` | Spider parses the fixture HTML listing and yields one `GazetteItem` with `gazette_number='2486/22'`, `pdf_url`, `gazette_date='2026-04-15'`, `gazette_type='extraordinary'` |
| `test_pdf_download_pipeline_writes_file` | `PDFDownloadPipeline` writes the fixture PDF to `STORAGE_LOCAL_PATH/m1/raw/2486_22.pdf` + sets `raw_pdf_path` + SHA-256 on the item (mocked `crawler.engine.download`) |
| `test_insert_pipeline_creates_m1_regulations_row` | `M1RegulationsInsertPipeline` INSERTs one `m1_regulations` row with `status='ingested'`, `raw_pdf_path`, `gazette_number`, `regulation_short_code='GZT_2486_22'`, parsed `gazette_published_date` |
| `test_insert_pipeline_is_idempotent_on_duplicate` | Re-running on the same `gazette_number` raises `DropItem` (UNIQUE conflict) without leaking a second row |

**Troubleshooting:** if testcontainers fails to start Postgres, make sure Docker is running. The fixture-PDF test ignores the actual PDF content (`b'%PDF-'` magic-byte check only), so it works without PyMuPDF / Tesseract.

---

## Verification — manual smoke check (real network → documents.gov.lk)

The CI test doesn't make real network calls. To verify the spider works against the live gazette listing:

```bash
cd enigmatrix-backend

# Make sure the migration has been applied (see Local setup §3).
uv run alembic current  # should show 202605220001

# Run the spider against the 2026 extraordinary-gazette listing.
uv run scrapy crawl gazette_spider
```

Expected behaviour:

- Spider walks `https://documents.gov.lk/view/egz/egz_2026.html` (the default `start_url`).
- For each `.pdf` anchor whose surrounding text contains a gazette-number pattern (`\d{4}/\d{1,3}`): downloads the PDF + inserts a row.
- Logs (INFO level) include `downloaded <gazette_number> → <path> (N bytes, sha256=...)` and `INSERTED m1_regulations row id=<uuid> gazette_number=<num> status=ingested`.
- After a `TODO: enqueue extract_gazette(<reg_id>) — Celery dispatch deferred to Step 2b` line per row.
- Typical run yields **1–5 new rows + 1–5 new PDFs** (depending on what's listed for the year).

Inspect the DB:

```bash
psql "$DATABASE_URL" -c "
  SELECT regulation_id, gazette_number, status, raw_pdf_path, gazette_published_date
  FROM m1_regulations
  WHERE status='ingested'
  ORDER BY created_at DESC
  LIMIT 10;
"
```

Inspect the downloaded PDFs:

```bash
ls -lh enigmatrix-backend/storage/m1/raw/
# Expected: <gazette_number>.pdf files (filename slug replaces / with _, e.g. 2486_22.pdf)
```

**Change the target year:**

```bash
uv run scrapy crawl gazette_spider -a start_url=https://documents.gov.lk/view/egz/egz_2025.html
```

**Idempotency check:** re-run the spider — no new rows should appear (the UNIQUE on `gazette_number` makes the insert pipeline drop duplicates with `DropItem`). The PDF download is also idempotent (skips if file already on disk).

---

## Rollback

If you need to undo the migration:

```bash
cd enigmatrix-backend
uv run alembic downgrade -1
# Expected: "Running downgrade 202605220001 -> 202605210001, m1_regulations: status state machine ..."

# Optional — clear downloaded PDFs:
rm -rf storage/m1/raw/
```

The downgrade is fully reversible: drops the 3 new columns (`status`, `raw_pdf_path`, `gazette_number`) + the 2 indexes + the CHECK constraint. Demo data isn't affected (those 5 rows had `gazette_number=NULL` and `status=` only existed *after* the migration).

---

## What's deferred to Step 2b

The spider is the MVP slice. Items intentionally **not** built this turn:

| Deferred | Why | Lands in |
|---|---|---|
| Celery dispatch of `extract_gazette` | Needs broker + `celery_config.py` + `tasks/m1/` scaffold; standalone Celery infra is its own slice | Step 2b |
| PDF text extraction (PyMuPDF → pdfplumber → Tesseract chain) | Drives `status: ingested → extracted` | Step 2b — see [../03_M1_1_PDF_Extraction_Chain.md](../03_M1_1_PDF_Extraction_Chain.md) |
| Language detection per line + Wijesekara conversion | Needed for SI/TA gazettes | Step 2c — see [../10_M1_1_Language_Detection_Routing.md](../10_M1_1_Language_Detection_Routing.md) and [../10_M1_2_OCR_Wijesekara_Conversion.md](../10_M1_2_OCR_Wijesekara_Conversion.md) |
| Worker hosting in production | Vercel can't run Scrapy or Celery | Step 2b deployment notes — [../07_M1_Deployment_Integration.md](../07_M1_Deployment_Integration.md) |

The next paired files will be `2.md` (Step 2b plan) + `2_setup.md` (Step 2b setup + verification).

---

## Cross-references

- **The plan that produced this code:** [1.md](2026-05%20Step%202a%20—%20Scrapy%20gazette%20spider%20(M1%20Phase%202%20—%20Ingest%20+%20extraction,%20MVP%20slice).md)
- **Tracker entries:** Session 23 / F-145 in [../../tracker/SESSIONS.md](../../tracker/SESSIONS.md), [CHANGES.md](../../tracker/CHANGES.md), [FEATURES.md](../../tracker/FEATURES.md); narrative in [../../../AI_WORK_LOG.md](../../../AI_WORK_LOG.md)
- **M1 development roadmap (Phase 2 Step 2a):** [../16_M1_Development_Roadmap.md](../16_M1_Development_Roadmap.md)
- **Backend canonical specs:** [../03_M1_Data_Collection.md §1 + §1.3](../03_M1_Data_Collection.md) (Scrapy framework + spider scaffold), [../03_M1_1_PDF_Extraction_Chain.md](../03_M1_1_PDF_Extraction_Chain.md), [../13_M1_Folder_Structure_and_Implementation_Flow.md](../13_M1_Folder_Structure_and_Implementation_Flow.md) (target folder tree)
- **Frontend admin tracking workflow** (for the regulations the spider produces): [../14_M1_1_Admin_Pipeline_State_Tracking.md](../14_M1_1_Admin_Pipeline_State_Tracking.md)
