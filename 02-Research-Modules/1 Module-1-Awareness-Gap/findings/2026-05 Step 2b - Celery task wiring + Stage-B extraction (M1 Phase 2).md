# 2 — Step 2b: Celery task wiring + Stage-B extraction (M1 Phase 2)

> **Pairs with** [2_setup.md](2_setup.md).
> **Predecessor:** [1.md](2026-05%20Step%202a%20—%20Scrapy%20gazette%20spider%20(M1%20Phase%202%20—%20Ingest%20+%20extraction,%20MVP%20slice).md) (the Scrapy spider that lands `m1_regulations` rows in `status='ingested'`).
> **Reference:** [../16_M1_Development_Roadmap.md](../16_M1_Development_Roadmap.md) Phase 2 Step 2b; [../03_M1_Data_Collection.md §6.1](../03_M1_Data_Collection.md) (Celery retry interaction); [../03_M1_1_PDF_Extraction_Chain.md](../03_M1_1_PDF_Extraction_Chain.md).

## Context

After Session 23 (Step 2a), `m1_regulations` rows land at `status='ingested'` with a `raw_pdf_path` pointing at the downloaded PDF. The pipeline's `M1RegulationsInsertPipeline` currently logs a `TODO: enqueue extract_gazette(<reg_id>)` line where Celery dispatch will go. **Step 2b closes that loop** — it adds the Celery infrastructure, the two Celery tasks (`gazette_scraper` wrapping the spider + `extract_gazette` running the PyMuPDF / pdfplumber / Tesseract chain), and flips rows from `ingested → extracted` with cleaned text in a new `raw_text` column.

**DoD:** `celery -A backend.app.celery_config worker --beat` running locally → Celery Beat fires the spider every 6 h → spider downloads new gazettes → `extract_gazette` task fires per row → row advances to `status='extracted'` with `raw_text` populated. End-to-end smoke check (run the task once manually + watch the DB) shipped with `2_setup.md`.

## Decisions

1. **Broker = Redis.** Standard for Celery on Python; cheap to run locally (`brew services start redis`) and free-tier on Upstash for the Fly.io production worker. RabbitMQ rejected — adds operational surface area we don't need at MVP scale.
2. **Worker host = local (dev) + Fly.io (prod).** Vercel cannot run Celery workers (no long-lived processes). The production worker lands on a Fly.io machine per [../07_M1_Deployment_Integration.md](../07_M1_Deployment_Integration.md); the dev loop runs locally. Worker hosting deployment is **out of scope for this slice** — Step 2b ships the *code*; the deploy spec is its own follow-up.
3. **Real extraction chain shipped this slice (not stubbed).** The roadmap's DoD says "row advances to status='extracted'" with cleaned text — that requires the real PyMuPDF → pdfplumber → Tesseract chain from [../03_M1_1_PDF_Extraction_Chain.md](../03_M1_1_PDF_Extraction_Chain.md). Tesseract OCR is a system dep; `2_setup.md` documents `brew install tesseract tesseract-lang`.
4. **Language detection + Wijesekara conversion deferred to Step 2c.** The extraction here just produces *cleaned text*; the per-line language routing + Sinhala glyph remapping land later. See [../10_M1_1_Language_Detection_Routing.md](../10_M1_1_Language_Detection_Routing.md) + [../10_M1_2_OCR_Wijesekara_Conversion.md](../10_M1_2_OCR_Wijesekara_Conversion.md).
5. **`raw_text` column added now**, since the DoD requires it. Migration `202605230001` adds `m1_regulations.raw_text` (TEXT nullable) + `extraction_method` (VARCHAR(20) nullable: `'pymupdf' | 'pdfplumber' | 'tesseract'`) + `extracted_at` timestamp.
6. **Celery retry pattern follows [03_M1_Data_Collection.md §6.1](../03_M1_Data_Collection.md).** Spider-side retries stay inside Scrapy; Celery only retries on infrastructure failures (DB lost, disk full). `autoretry_for=()` — no implicit retry; explicit `self.retry(exc=exc, countdown=60)` where appropriate.

## Hard constraints

- **One feature, one tracker entry** when Step 2b lands — Session 26 / F-148 (whichever number is next at that point).
- **Spider's `M1RegulationsInsertPipeline` updated to enqueue** `extract_gazette.delay(str(row.regulation_id))` *replacing* the TODO log line. That's a 2-line change.
- **No frontend code touched.** Backend + scraper only.
- **Test coverage**: 1 task-level integration test per Celery task (mocked broker via `task_always_eager=True`) + 1 end-to-end test that walks spider → both tasks → DB final state.

## Files (~18 touches when Step 2b executes)

### NEW — Celery infrastructure (4 files)

| Path | Purpose |
|---|---|
| `enigmatrix-backend/app/celery_config.py` | Celery app instance. `Celery("enigmatrix-m1", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_BROKER_URL)`. `task_always_eager=False` (overridden to `True` in tests). `CELERYBEAT_SCHEDULE` registers `gazette_scraper` on a 6 h cron. Auto-discovers tasks from `app.tasks`. |
| `enigmatrix-backend/app/tasks/__init__.py` | Package marker + re-export of the celery app (`from app.celery_config import celery_app`). |
| `enigmatrix-backend/app/tasks/m1/__init__.py` | Package marker + re-exports `gazette_scraper`, `extract_gazette` so other modules can `from app.tasks.m1 import extract_gazette`. |
| `enigmatrix-backend/app/tasks/m1/gazette_scraper.py` | Celery task `gazette_scraper` — wraps the Scrapy spider in a `CrawlerRunner` per [03_M1_Data_Collection.md §1.2](../03_M1_Data_Collection.md). Returns `{"crawled": n, "duration_s": d}`. Celery Beat fires it on `0 */6 * * *`. |
| `enigmatrix-backend/app/tasks/m1/extract_gazette.py` | Celery task `extract_gazette(regulation_id)` — loads the row → reads `raw_pdf_path` → runs `classify_pdf()` → dispatches to PyMuPDF / pdfplumber / Tesseract extractor → writes `raw_text` + `extraction_method` + `extracted_at` → flips `status` to `'extracted'`. On failure: status → `'extraction_failed'`. The full extraction-chain logic + threshold sensitivity is in [../03_M1_1_PDF_Extraction_Chain.md](../03_M1_1_PDF_Extraction_Chain.md). |

### NEW — Extraction helpers (3 files)

| Path | Purpose |
|---|---|
| `enigmatrix-backend/app/extraction/__init__.py` | Package marker. Lives in `app/extraction/` (not `ml/m1/extraction/`) for now to stay inside the backend repo; the `ml/` split is a future reorg per doc 13. |
| `enigmatrix-backend/app/extraction/pdf_classifier.py` | `classify_pdf(path: str) -> dict` returning `{"type": "text_pdf" | "hybrid" | "scanned", "method": ...}`. Thresholds from env vars `M1_PDF_TEXT_THRESHOLD` (default 200) + `M1_PDF_SCANNED_THRESHOLD` (default 30). Spec: [../03_M1_1_PDF_Extraction_Chain.md](../03_M1_1_PDF_Extraction_Chain.md). |
| `enigmatrix-backend/app/extraction/text_extractors.py` | Three callables: `extract_pymupdf(path)`, `extract_pdfplumber(path)`, `extract_tesseract(path)`. Each returns `(text, method)`. `extract_gazette` calls the chain in order, picking the first non-empty result. |

### NEW — Alembic migration (1 file)

| Path | Purpose |
|---|---|
| `enigmatrix-backend/alembic/versions/202605230001_m1_regulations_extraction_columns.py` | Adds 3 columns: `raw_text TEXT` (nullable), `extraction_method VARCHAR(20)` (nullable; CHECK in `('pymupdf', 'pdfplumber', 'tesseract')`), `extracted_at TIMESTAMPTZ` (nullable). `down_revision = "202605220001"`. Down: drop the 3 columns + CHECK. |

### MODIFIED — Existing files (4 files)

| Path | Change |
|---|---|
| `enigmatrix-backend/pyproject.toml` | Add 5 deps: `celery[redis]>=5.3,<6`, `PyMuPDF>=1.24,<2`, `pdfplumber>=0.11,<1`, `pytesseract>=0.3.13,<1`, `pdf2image>=1.17,<2`. Bumps the working dep count from 17 → 22. |
| `enigmatrix-backend/.env.example` | Append 3 vars: `CELERY_BROKER_URL=redis://localhost:6379/0`, `M1_PDF_TEXT_THRESHOLD=200`, `M1_PDF_SCANNED_THRESHOLD=30`. |
| `enigmatrix-backend/app/settings.py` | Add the 3 new env-var fields to the `Settings` Pydantic model. |
| `enigmatrix-backend/scraper/pipelines.py` | In `M1RegulationsInsertPipeline._insert_row`, replace the `TODO` log line with `from app.tasks.m1 import extract_gazette; extract_gazette.delay(str(row.regulation_id))`. Two lines change; logic semantics now match the DoD. |
| `enigmatrix-backend/app/models/regulation.py` | Add 3 `Mapped[]` columns matching the migration: `raw_text`, `extraction_method`, `extracted_at`. |

### NEW — Tests (4 files)

| Path | Purpose |
|---|---|
| `enigmatrix-backend/app/tests/integration/test_celery_extract_gazette.py` | `task_always_eager=True` mode. Seeds a `m1_regulations` row + a sample PDF on disk. Calls `extract_gazette(regulation_id)`. Asserts: `status='extracted'`, `raw_text` non-empty, `extraction_method='pymupdf'`, `extracted_at` populated. |
| `enigmatrix-backend/app/tests/unit/test_pdf_classifier.py` | Threshold table: feed PDFs of varying char counts; assert correct classification (`text_pdf` / `hybrid` / `scanned`). |
| `enigmatrix-backend/app/tests/unit/test_text_extractors.py` | Each extractor on a fixture PDF: assert returns non-empty string + correct method label. |
| `enigmatrix-backend/app/tests/integration/test_gazette_scraper_task.py` | Spider Celery task in eager mode: assert it returns `{"crawled": n, "duration_s": d}` and triggers the spider's normal pipeline path. |

### NEW — Paired tracker (4 files when this lands)

When Step 2b is executed: a new Session entry (Session 26 / F-148 or whichever number is next) in AI_WORK_LOG, SESSIONS, CHANGES, FEATURES — same pattern as Sessions 23 / 24 / 25.

### Total

**~18 file touches when Step 2b executes** (4 Celery infra + 3 extraction helpers + 1 migration + 4 modified + 4 new tests + 4 tracker = 20 new + 5 modified). Substantial but well-bounded.

## Execution order (when Step 2b runs)

1. **Update `pyproject.toml` + `.env.example` + `settings.py`** for the 5 new deps + 3 env vars.
2. **`uv sync`** to pull the deps (user runs this).
3. **Write the Alembic migration `202605230001`** + add the matching `Mapped[]` columns to the model.
4. **`uv run alembic upgrade head`** (user runs).
5. **Write `app/extraction/`** (classifier + extractors).
6. **Write `app/celery_config.py`** + `app/tasks/__init__.py` + `app/tasks/m1/__init__.py`.
7. **Write `app/tasks/m1/gazette_scraper.py`** (Celery wrapper around the spider).
8. **Write `app/tasks/m1/extract_gazette.py`** (the heart of Stage B).
9. **Update `scraper/pipelines.py`** — replace the TODO log line with `extract_gazette.delay(reg_id)`.
10. **Write the 4 tests.**
11. **Verification + tracker updates.**

## Verification (when Step 2b runs)

1. **Migration round-trip.** `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` clean.
2. **All 4 new tests pass** (Celery in `task_always_eager` mode + the 2 unit tests for the extraction helpers).
3. **End-to-end smoke check** documented in `2_setup.md` — start Redis, start Celery worker + Beat, run the spider against the fixture or real network, watch `m1_regulations.status` flip `ingested → extracted` with `raw_text` populated.
4. **No drift outside the planned files.** `git diff --stat` shows changes only in `enigmatrix-backend/`.

## Risks / open items

- **System Tesseract dep on macOS.** `brew install tesseract tesseract-lang` is mandatory; `2_setup.md` calls this out. Linux uses `apt install tesseract-ocr tesseract-ocr-sin tesseract-ocr-tam`.
- **PyMuPDF wheels for Apple Silicon.** Recent versions ship wheels; `uv sync` handles it. If wheel install fails, fallback is `pip install --no-binary :all:` (slow but works).
- **Celery + asyncio bridge.** The pipelines use `async def process_item` (Session 23). When the pipeline calls `extract_gazette.delay(...)`, the dispatch is synchronous Celery API — fine to call from async context (Celery client is sync but non-blocking for the message send). Documented.
- **Worker concurrency.** Default Celery prefork = `CPU_COUNT`. For local dev, `--concurrency=2` is plenty. Production tuning is in doc 13 (Fly.io machine sizing).
- **6-hour Beat schedule** matches the spider's per-source scrape frequency in [02_M1_1_Data_Sources_Catalogue.md](../02_M1_1_Data_Sources_Catalogue.md). Override via Celery Beat config if needed.
- **Tesseract data race.** Multiple workers running `pytesseract` against the same temp dir can collide. Solution: `tempfile.TemporaryDirectory()` per task invocation.

## Cross-references

- **Predecessor:** [1.md](2026-05%20Step%202a%20—%20Scrapy%20gazette%20spider%20(M1%20Phase%202%20—%20Ingest%20+%20extraction,%20MVP%20slice).md) + [1_setup.md](1_setup.md) (Step 2a — the spider).
- **Setup guide for this:** [2_setup.md](2_setup.md).
- **Roadmap step:** [../16_M1_Development_Roadmap.md](../16_M1_Development_Roadmap.md) Phase 2 Step 2b.
- **Detail docs:** [../03_M1_Data_Collection.md §6.1](../03_M1_Data_Collection.md), [../03_M1_1_PDF_Extraction_Chain.md](../03_M1_1_PDF_Extraction_Chain.md), [../03_M1_2_Gazette_Segmentation.md](../03_M1_2_Gazette_Segmentation.md) (segmentation is Step 2c).
- **What comes after:** Step 2c (language detection + per-line routing) + Step 2d (preprocessing for classification).
