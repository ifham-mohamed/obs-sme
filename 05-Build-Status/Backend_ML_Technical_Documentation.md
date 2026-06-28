# Enigmatrix Backend + ML — Comprehensive Technical Documentation

**As of 2026-05-20 (latest migration: 202605290001)**

---

## 1. Database Schema

### Model Registry (`app/models/__init__.py`)

The following tables/models are registered and visible to Alembic autogenerate:

`AdminSurvey`, `AdminSurveyAssignment`, `AuditLog`, `M1ExtractionRun`, `M1GazetteItem`, `M1Regulation`, `M1RegulationPenalty`, `M1RegulationSector`, `M1SubDocument`, `M2KnowledgeScore`, `M2Question` (alias `SurveyQuestion`), `M3BehaviouralSignals`, `M3ComplianceHistory`, `RegulatoryDomain`, `Sector`, `SMEProfile`, `SurveyQuestion`, `SurveyQuestionRegulation`, `SurveyResponse`, `SurveySession`, `User`

---

### `users`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `email` | String | UNIQUE, indexed |
| `password_hash` | String | bcrypt |
| `role` | String | default `'sme'`; also `'admin'`, `'annotator'` |
| `preferred_language` | String | default `'en'` |
| `is_active` | Boolean | default `true` |
| `created_at`, `updated_at` | Timestamp | via `TimestampMixin` |

**Relationships:** `sme_profile` (one-to-one → `SMEProfile`)

---

### `m1_regulations`

Central table for the M1 regulatory pipeline. Every regulation, whether admin-created or spider-ingested, has a row here.

| Column | Type | Notes |
|---|---|---|
| `regulation_id` | UUID PK | |
| `regulation_short_code` | String | UNIQUE indexed slug, e.g. `GZT_2486_22` |
| `document_type` | String | `bill`, `act`, `extraordinary_gazette`, `weekly_gazette`, `circular`, `order`, `notification`, `unknown` |
| `document_number` | String | e.g. `31/2026`, `2486/15` |
| `title_en` / `title_si` / `title_ta` | String | Multilingual |
| `summary_en` / `summary_si` / `summary_ta` | String | Multilingual summaries |
| `principal_act_amended` | String | Act being amended |
| `cabinet_approval_date` | Date | |
| `bill_published_date` | Date | indexed |
| `gazette_published_date` | Date | indexed |
| `effective_date` | Date | indexed |
| `domain_code` | String | FK → `regulatory_domains.domain_code`, indexed |
| `change_category` | String | Literal enum of 11 values |
| `severity_level` | SmallInt | 1–5 |
| `is_sme_relevant` | Boolean | default `true` |
| `penalty_range_lkr` | String | e.g. `LKR 50,000 – 500,000` |
| `real_world_example_en/si/ta` | String | Multilingual examples |
| `source_url` | String | |
| `expert_verified` | Boolean | CA verification gate |
| `expert_verified_by` | String | |
| `expert_verified_at` | DateTime | |
| `sme_relevance_confidence` | Numeric(3,2) | Classifier confidence (nullable until BUILD_07) |
| `is_active` | Boolean | Soft-delete flag, indexed |
| **Pipeline state machine** | | |
| `status` | String(20) | `ingested` → `extracted` → `preprocessed` → (future: `classified`, `summarized`, `alerted`, `archived`) |
| `raw_pdf_path` | String(500) | Legacy disk path; NULL for new spider rows |
| `gazette_number` | String(50) | UNIQUE (NULLS allowed), indexed |
| `raw_text` | Text | Raw extracted text |
| `extraction_method` | String(20) | `pymupdf`, `pdfplumber`, or `tesseract` |
| `extracted_at` | DateTime | |
| `cleaned_text` | Text | Noise-removed text |
| `amendment_type` | String(20) | `amendment`, `repeal`, or `new_act` |
| `last_error` | Text | Sanitised failure message |
| `last_error_at` | DateTime | |
| `file_size_bytes` | BigInteger | |
| `sha256` | String(64) | indexed |
| `pdf_pages` | SmallInt | |
| `language` | String(10) | `sin`, `tam`, `eng`, `unknown` — indexed |
| `created_at`, `updated_at` | Timestamp | |

**Relationships:**
- `penalties` → `M1RegulationPenalty[]` (cascade delete)
- `sub_documents` → `M1SubDocument[]` (cascade delete)
- `gazette_item` → `M1GazetteItem` (one-to-one, cascade delete)

---

### `m1_gazette_items`

Introduced in migration `202605290001`. Replaces on-disk PDF storage. One row per gazette document discovered by the spider.

| Column | Type | Notes |
|---|---|---|
| `item_id` | UUID PK | |
| `regulation_id` | UUID | FK → `m1_regulations`, UNIQUE (one-to-one), CASCADE delete |
| `source_id` | String(10) | `EGZ`, `GZ`, `BILL`, `ACT` |
| `title` | Text | Anchor text from listing page |
| `source_url` | String(2048) | Listing page URL |
| `download_url` | String(2048) | NOT NULL — direct PDF URL |
| `document_number` | String(100) | e.g. `2486/22` |
| `document_date` | Date | Parsed from listing |
| `created_at`, `updated_at` | Timestamp | |

---

### `m1_extraction_runs`

Audit log for extraction trigger runs.

| Column | Type | Notes |
|---|---|---|
| `run_id` | UUID PK | |
| `task_id` | String | Celery task ID |
| `source_id` | String | `EGZ`, `GZ`, `BILL`, `ACT` |
| `date_from`, `date_to` | Date | Crawl scope |
| `queued_at` | DateTime | |
| `queued_by_id` | UUID | FK → `users` |
| `queued_by_email` | String | Denormalised |
| `celery_status` | String | PENDING/STARTED/SUCCESS/FAILURE/REVOKED |
| `completed_at` | DateTime | |
| `result` | JSONB | Task result payload |
| `traceback` | Text | Sanitised traceback |
| `rows_ingested`, `rows_extracted`, `rows_preprocessed`, `rows_failed` | Integer | Pipeline snapshot counts |

---

### `survey_sessions`

| Column | Type | Notes |
|---|---|---|
| `session_id` | UUID PK | |
| `sme_id` | UUID | FK → `sme_profiles.sme_id` |
| `survey_mode` | String | `per_module_m1/m2/m3/m4` or `unified` |
| `status` | String | `in_progress`, `completed`, `abandoned` |
| `started_at` | DateTime | |
| `completed_at` | DateTime | nullable |
| `questions_shown`, `questions_answered` | Integer | |
| `recruitment_channel`, `sector_code` | String | nullable |

---

### Other Models

- **`M1RegulationPenalty`** — per-penalty rows; fields: `sequence_idx`, `penalty_type`, `min_lkr`, `max_lkr`, `imprisonment_months`, `context`, `is_admin_set`
- **`M1SubDocument`** — gazette sections; fields: `sequence_idx`, `section_label`, `section_type`, `char_offset_start`, `char_offset_end`, `text`
- **`M2KnowledgeScore`** — per-SME knowledge scoring snapshots
- **`M3BehaviouralSignals`**, **`M3ComplianceHistory`** — M3 vulnerability module snapshots
- **`SurveyQuestion`** (`m2_questions`) — question bank across all modules
- **`SurveyQuestionRegulation`** — junction linking questions to regulations
- **`AdminSurvey`**, **`AdminSurveyAssignment`** — admin-configured surveys
- **`AuditLog`** — admin activity trail
- **`RegulatoryDomain`** — domain taxonomy (VAT, Employment, etc.)
- **`Sector`** — sector taxonomy
- **`SMEProfile`** — SME business profile linked to User

---

## 2. Backend API

All routes are prefixed `/api/v1/`. Router: `app/api/v1/router.py`.

### Auth (`/auth`)

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Register new user. Rate: 10/min. |
| POST | `/auth/login` | Email/password login → JWT pair. Rate: 5/min. |
| POST | `/auth/refresh` | Rotate refresh token. Rate: 30/min. |

### Users (`/users`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/users/me` | Any | Current user info + SME profile |
| GET | `/users` | Admin | List all users |
| POST | `/users` | Admin | Create user |
| PATCH | `/users/{user_id}` | Admin | Update user fields |
| POST | `/users/{user_id}/activate` | Admin | Set `is_active=true` |
| POST | `/users/{user_id}/deactivate` | Admin | Set `is_active=false` |
| POST | `/users/{user_id}/reset-password` | Admin | Force password reset |
| DELETE | `/users/{user_id}` | Admin | Soft-delete |

### Survey Sessions (`/survey-sessions`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/survey-sessions/start` | SME | Create session; checks per-role survey limits |
| GET | `/survey-sessions/my-history` | SME | List all sessions for current SME |
| GET | `/survey-sessions/{id}` | SME | Session detail |
| GET | `/survey-sessions/{id}/next-question` | SME | First unanswered question with regulation context |
| POST | `/survey-sessions/{id}/answer` | SME | Submit answer, receive next question |
| POST | `/survey-sessions/{id}/complete` | SME | Manually mark completed |

### Module 2 — Knowledge (`/m2`)

| Method | Path | Description |
|---|---|---|
| GET | `/m2/questions/for-sector/{sector_code}` | Questions for SME's sector |
| GET | `/m2/sme/{sme_id}/knowledge_score` | Latest M2 score |
| POST | `/m2/questions/{question_code}/verify` | CA-verify a question (Admin) |

### Module 3 — Vulnerability (`/m3`)

| Method | Path | Description |
|---|---|---|
| POST | `/m3/compliance-history` | Submit compliance history snapshot |
| POST | `/m3/behavioural` | Submit behavioural signals snapshot |
| GET | `/m3/sme/{sme_id}/risk-signals` | Combined risk view: M2 score + M3 history + behavioural |

### Dashboard (`/dashboard`)

| Method | Path | Description |
|---|---|---|
| GET | `/dashboard/pending-regulations` | Active regulations the SME hasn't answered, scoped to sector |

### Admin M1 Extraction (`/admin/m1/extraction`)

| Method | Path | Description |
|---|---|---|
| POST | `/admin/m1/extraction/trigger` | Queue scoped crawl. Rate: 5/min. Returns `task_id`. |
| GET | `/admin/m1/extraction/status/{task_id}` | Poll Celery status; syncs terminal state to `m1_extraction_runs` |
| POST | `/admin/m1/extraction/cancel/{task_id}` | Revoke task + roll back DB rows + on-disk PDFs |
| GET | `/admin/m1/extraction/progress` | Per-row live feed for active run |
| GET | `/admin/m1/extraction/summary` | Aggregate stats for a run scope |
| GET | `/admin/m1/extraction/regulations/{id}/raw-pdf` | Stream raw PDF from disk (legacy path only) |
| POST | `/admin/m1/extraction/regulations/{id}/retry` | Reset `extraction_failed` → `ingested`; re-enqueue |
| POST | `/admin/m1/extraction/regulations/{id}/re-extract` | Force full re-extract |
| POST | `/admin/m1/extraction/regulations/{id}/re-preprocess` | Re-run preprocessing only |
| POST | `/admin/m1/extraction/reconcile` | Walk disk; insert DB rows for any PDF without one (legacy) |
| GET | `/admin/m1/extraction/sources` | All 4 M1 sources with per-source stats |
| GET | `/admin/m1/extraction/sources/{source_id}` | Single source metadata + stats |
| GET | `/admin/m1/extraction/unknown` | All `document_type='unknown'` rows (up to 200) |
| GET | `/admin/m1/extraction/pdf-records` | Paginated browse. Filters: source, status, language, date, search |
| POST | `/admin/m1/extraction/regulations/{id}/categorize` | Re-file unknown row |
| GET | `/admin/m1/extraction/runs` | Paginated history of all trigger runs |
| POST | `/admin/m1/extraction/migrate-raw-layout` | One-off: move legacy `m1/raw/*.pdf` → `m1/raw/EGZ/` |

### 501 Stubs (deferred)

- `GET /regulations`, `GET /regulations/{id}` — Module 1 awareness (BUILD_07)
- `GET /qa` — RAG QA (BUILD_08)
- `GET /risk` — ML risk model (BUILD_09)
- `GET /verify` — Module 4 verifier (deferred)

---

## 3. M1 Pipeline — Full Data Flow

```
Admin UI
  │
  ▼
POST /admin/m1/extraction/trigger
  ├─ Creates M1ExtractionRun row (status=PENDING)
  └─ run_scraper.delay(source_id, date_from, date_to)
       │
       ▼
  BaseDocumentsGovLkSpider.parse()
    - Fetches year-listing HTML from documents.gov.lk
    - Iterates every <a href="*.pdf"> anchor
    - Parses document_number + date from row context
    - Applies date-range scope filter; early-exit when past date_from
    - Yields RegulatoryDocumentItem per matching PDF link
       │
       ▼
  M1GazetteItemPipeline [priority 100]
    - Validates pdf_url + document_number present
       │
       ▼
  M1RegulationsInsertPipeline [priority 200]
    - INSERT m1_regulations row (status='ingested', raw_pdf_path=NULL)
    - flush() → get regulation_id PK
    - INSERT m1_gazette_items row (download_url, title, source_url, ...)
    - Both in same transaction; IntegrityError → DropItem (idempotent)
    - Dispatches extract_gazette.delay(regulation_id)
       │
       ▼
  extract_gazette [Celery task]
    1. Load M1Regulation; skip if status != 'ingested'
    2. Check gazette_item.download_url (new) OR raw_pdf_path (legacy)
    3a. New: httpx.AsyncClient.get(download_url, 60s timeout) → bytes
    3b. Legacy: read bytes from disk
    4. classify_pdf(bytes) → 'text_pdf' | 'hybrid' | 'scanned'
    5. Route: pymupdf | pdfplumber | tesseract
    6. compute_pdf_metadata(bytes, raw_text) → file_size, sha256, pages, language
    7. Write to DB; flip status ingested → extracted
    8. On failure: set status='extraction_failed', last_error, last_error_at
    9. Chain: preprocess_gazette_task.delay(regulation_id)
       │
       ▼
  preprocess_gazette_task [Celery task]
    1. Load regulation; require status='extracted'
    2. clean_gazette_text(raw_text) → cleaned_text [8-step pipeline]
    3. extract_metadata(cleaned_text) → gazette_number, effective_date,
       principal_act_amended, amendment_type, penalties, penalty_range_lkr
    4. detect_sections_with_labels(cleaned_text) → list[SectionInfo]
    5. Write: cleaned_text, amendment_type, penalty rows, sub_document rows
    6. Flip status extracted → preprocessed
```

**Future stages (not yet implemented):** `classified → summarized → alerted → archived`

---

## 4. Scrapy Spider Architecture

### Base class: `scraper/spiders/_base.py` — `BaseDocumentsGovLkSpider`

| Spider | `source_id` | `document_type` | Cadence |
|---|---|---|---|
| `gazette_spider` | `EGZ` | `extraordinary_gazette` | Daily |
| `weekly_gazette_spider` | `GZ` | `weekly_gazette` | Weekly |
| `bills_spider` | `BILL` | `bill` | Weekly |
| `acts_spider` | `ACT` | `act` | Weekly |

**Key design decisions:**
- **No-disk architecture**: PDFs never saved; spider stores only `download_url` in `m1_gazette_items`
- **Date-range scoping**: same calendar year per page; derives year and builds listing URL
- **Early exit**: listings are newest-first; spider calls `close_spider("scope_exhausted")` when row date < `date_from`
- **Custom settings**: `DOWNLOAD_DELAY=2`, `AUTOTHROTTLE_ENABLED=True`, `RETRY_TIMES=5`, `CLOSESPIDER_TIMEOUT_NO_ITEM=60`
- **Idempotency**: `IntegrityError` on `regulation_short_code` UNIQUE → DropItem; re-running same range is safe

---

## 5. ML Extraction Chain

All ML code lives in `enigmatrix-ml/m1/`. Standalone-installable package.

### 5a. PDF Classifier (`m1/extraction/pdf_classifier.py`)

Classifies PDF as `text_pdf`, `hybrid`, or `scanned` to route to correct extractor.

- Opens with PyMuPDF; computes mean chars/page over first 3 pages
- `mean >= 200` → `text_pdf`; `mean >= 30` → `hybrid`; `mean < 30` → `scanned`
- Thresholds env-overridable; calibration CLI available (`--calibrate <audit_dir>`)

### 5b. Text Extractors (`m1/extraction/text_extractors.py`)

- **`extract_pymupdf`** — fast path for text PDFs; preserves Sinhala/Tamil ligatures
- **`extract_pdfplumber`** — hybrid PDFs; `layout=True` for multi-column reflow + table extraction
- **`extract_with_chain`** — per-page routing: PyMuPDF first; if page < 100 chars, OCR fallback via Tesseract with language detection + Wijesekara conversion

All accept `bytes | Path` (PdfSource type alias).

### 5c. OCR (`m1/extraction/ocr.py`)

- Rasterises all pages at 300 DPI via `pdf2image`; bytes input written to temp file, deleted after
- Runs Tesseract `--oem 1 --psm 6 --lang eng+sin+tam` per page
- Per-page 60s timeout via `ThreadPoolExecutor`

### 5d. Language Detection (`m1/extraction/language_detection.py`)

**Layer 1 — fastText `lid.176.bin`:** predicts over first 500 chars; returns primary language if confidence ≥ 0.70 and label ∈ {en, si, ta}; else `'mixed'`

**Layer 2 — Per-line Unicode-range router:** Sinhala: U+0D80–U+0DFF, Tamil: U+0B80–U+0BFF; line classified as X if >50% non-whitespace chars belong to that script

### 5e. Wijesekara Converter (`m1/extraction/wijesekara.py`)

Handles pre-Unicode Wijesekara-encoded Sinhala from Tesseract OCR on government documents.

- `is_wijesekara_encoded(text)` — heuristic: Wijesekara indicator chars ratio > 0.40 AND ≥ 50 ASCII-alpha chars
- `convert_wijesekara(text)` — greedy longest-match (4→3→2→1 chars) from `wijesekara_map.yaml`; `@lru_cache`

### 5f. Segmenter (`m1/extraction/segmenter.py`)

Detects gazette section boundaries.

- Matches: `PART I/II`, `Schedule I/1`, `SECTION 5`, `Notice No. 5`, `1. The Sri Lanka ...`
- `detect_sections_with_labels(text)` → `list[SectionInfo]` with `section_label`, `section_type` (part/schedule/section/notice/numbered_clause/preamble), char offsets
- Consumed by `preprocess_gazette_task` to populate `m1_sub_documents`

### 5g. Preprocessing — Cleaning (`m1/preprocessing/cleaning.py`)

8-step noise removal pipeline:

| Step | What it removes |
|---|---|
| 1 | NFKD unicode normalization |
| 2 | Dehyphenation of line-break splits |
| 3 | Repeated gazette headers |
| 4 | Page numbers (`- 3 -`, Roman numerals) |
| 5 | Horizontal rules (`______`, `=======`) |
| 6 | Signature blocks (for classification input only) |
| 7 | 3+ blank lines → 2 |
| 8 | Multiple spaces/tabs → single space |

`clean_gazette_text(text)` — steps 1–5, 7, 8 (preserves signatures)
`clean_for_classification(text)` — all 8 steps (used for XLM-R input)

### 5h. Preprocessing — Chunking (`m1/preprocessing/chunking.py`)

Section-aware + sliding-window chunking for XLM-R input.

- `MAX_LEN=512`, `STRIDE=64`, `_MIN_SECTION_TOKENS=100`
- Uses `detect_sections` → merges micro-sections < 100 tokens → tokenizes with XLM-R SentencePiece
- Sections ≤ 512 tokens → one chunk; longer → sliding window; drops trailing windows < 50 tokens

### 5i. Preprocessing — Metadata Extractor (`m1/preprocessing/metadata_extractor.py`)

Regex-based extraction from cleaned text:

| Field | Method |
|---|---|
| `gazette_number` | `No. XXXX/N` regex |
| `effective_date` | `with effect from`, `w.e.f.`, `comes into operation on` + dateparser |
| `principal_act_amended` | `amend[s/ment to] the <Act Name, No. X of YYYY>` |
| `amendment_type` | Verb-count heuristic: repeal/amend/new_act |
| `penalties` | Two-pass: fines (`Rs./LKR`) + imprisonment; merged when within 30 chars |
| `penalty_range_lkr` | Derived: `"LKR {min} – {max}"` from all fine/both penalties |

---

## 6. Celery Tasks

| Task | Trigger | Max Retries | What it does |
|---|---|---|---|
| `extract_gazette` | Spider pipeline / retry endpoint | 3 | Fetch PDF in-memory → classify → extract text → metadata → DB write → chain preprocess |
| `preprocess_gazette_task` | Chained by extract_gazette | 3 | Clean text → extract metadata → detect sections → write to DB |
| `run_scraper` | POST /trigger | 2 | Launch Scrapy spider in-process for source_id + date range |
| `reconcile_raw_pdfs` | POST /trigger (auto) / POST /reconcile | 2 | **LEGACY** — walk disk, insert DB rows for PDFs without rows |

All tasks: `acks_late=True`, `autoretry_for=(Exception,)`, `retry_backoff=True`, `engine.dispose()` in finally.

---

## 7. Alembic Migration Chain

21 migrations from `202605080001` → `202605290001`:

| Migration | What it adds |
|---|---|
| 202605080001 | Initial schema (users, sme_profiles, regulations, domains, sectors) |
| 202605090001 | Module 2/3 schema |
| 202605100001 | m1_regulations + survey_questions |
| 202605110001 | regulation is_active flag |
| 202605120001 | question_regulations junction |
| 202605140001 | authorship + audit record_key |
| 202605160001 | survey_sessions |
| 202605170001 | survey limits per role |
| 202605180001 | rename awareness module_number |
| 202605190001 | audit_log request fields |
| 202605220001 | m1_regulations status columns (pipeline state machine) |
| 202605230001 | m1_regulations extraction columns (raw_text, method, extracted_at) |
| ... | (intermediate: penalties, sub_documents, last_error, extraction_runs) |
| 202605270001 | last_error + last_error_at columns |
| 202605280001 | Per-PDF metadata (file_size_bytes, sha256, pdf_pages, language) |
| 202605290001 | **m1_gazette_items table** (no-disk architecture) |

---

## 8. What is Complete vs In-Progress

### Complete

- User model + JWT auth (register/login/refresh)
- Admin user management (CRUD, activate/deactivate, reset-password)
- Survey sessions (start, answer, next-question, complete, history) with multilingual regulation context
- Survey limits per role
- M2 knowledge questions + scoring
- M3 compliance history + behavioural signals
- Dashboard pending-regulations widget
- M1 regulations model (full schema with pipeline state machine)
- Scrapy base spider + 4 concrete spiders (EGZ, GZ, BILL, ACT)
- **No-disk spider architecture (Phase 2b)**: `M1GazetteItem` table, `M1GazetteItemPipeline`, `M1RegulationsInsertPipeline`
- `extract_gazette` Celery task with in-memory PDF fetch via httpx + legacy disk fallback
- PDF classifier (text_pdf/hybrid/scanned) with calibration CLI
- PyMuPDF, pdfplumber, Tesseract extractors (all accept `bytes | Path`)
- Per-page hybrid chain with OCR fallback + language routing + Wijesekara handling
- fastText language detection (document + per-line Unicode-range router)
- Wijesekara → Unicode converter (greedy longest-match from YAML map)
- `preprocess_gazette_task` with 8-step cleaning pipeline
- Metadata extractor (gazette_number, effective_date, principal_act, amendment_type, penalties)
- Section segmenter (`detect_sections_with_labels`) with type classification
- XLM-R chunking (section-aware + sliding window)
- `m1_regulation_penalty` + `m1_sub_document` child tables
- `m1_extraction_runs` audit table
- Per-PDF metadata columns (file_size_bytes, sha256, pdf_pages, language)
- Last-error columns for failure surfacing
- Admin extraction API (all 17 endpoints)
- Admin M1 pipeline observability portal
- Error sanitiser (strips server paths from user-facing errors)

### In-Progress / Deferred

| Area | Notes |
|---|---|
| Module 1 awareness endpoints (`/regulations`) | 501 stub — BUILD_07 |
| NLP classifier for `domain_code`, `change_category`, `is_sme_relevant` | Deferred BUILD_07 |
| Summariser (Stage E) — per-section text summarization | BUILD_07 Phase 4 |
| Alerting — notify SMEs when relevant regulations land | BUILD_07 Phase 5 |
| RAG / QA (`/qa` endpoint) | 501 stub — BUILD_08 |
| ML risk model training for M3 | BUILD_09 |
| Module 4 verifier (`/verify`) | Deferred |
| Pipeline stages `classified`, `summarized`, `alerted`, `archived` | Columns exist; no tasks write these yet |
| `m1_extraction_runs` snapshot counts (rows_ingested etc.) | Columns exist; not yet populated |
| Admin-editable `m1_sources` table | Currently code-only catalogue |
| `reconcile_raw_pdfs` full retirement | Kept for legacy disk PDFs |
