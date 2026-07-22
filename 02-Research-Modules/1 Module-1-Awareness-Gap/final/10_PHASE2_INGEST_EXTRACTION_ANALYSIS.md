# Module 1 — Phase 2 (Ingest + Extraction): Complete Analysis

> Single-file analysis of **Phase 2 — Ingest + Extraction (BUILD_07 §A–B)** *only*: scope, technologies actually used, what was built across every layer (Scrapy → Celery → ML extraction → preprocessing → DB → admin UI), how it was developed, the full data journey, and the approaches missed. Grounded in the live codebase (`C:\Reasearch\xyz`; backend now under `app/m1/`, ML under `enigmatrix-ml/m1/`) and the vault (`E:\Obsidian\sme` — `16_M1_Development_Roadmap.md §Phase 2`, `FEATURES.md` F-145→F-160, F-198).
>
> Generated 2026-07-18; **gap-closure status refreshed 2026-07-21 (Sessions 64–69)**. Phase 2 is marked **✅ complete** (shipped across Sessions 23–43 + 53–55). This document verifies that against the code and records the residual gaps, each now annotated with its closure status and the companion plan doc.

---

## 1. What Phase 2 is (scope + goal)

**Goal (roadmap):** new gazettes flow *automatically* from the government source → `m1_regulations.status='preprocessed'` with cleaned text + structured metadata, no human in the loop.

Phase 2 is the **automated ingestion pipeline** — the first place M1 stops being a manual CRUD app (Phase 1) and becomes a data machine. It is split into six steps:

| Step   | What it delivers                                                                            | Status         |
| ------ | ------------------------------------------------------------------------------------------- | -------------- |
| **2a** | Scrapy gazette spider → PDFs + `m1_regulations` rows at `status='ingested'`                 | 🟢 F-145 (S23) |
| **2b** | Celery task wiring (`gazette_scraper` → `extract_gazette`), Beat every 6h                   | 🟢             |
| **2c** | PDF-type classifier + chained extractor (PyMuPDF → pdfplumber → Tesseract)                  | 🟢             |
| **2d** | Language detection (fastText) + per-line routing + Wijesekara conversion                    | 🟢             |
| **2e** | Preprocessing chain — noise removal, metadata extraction, chunking (ml-package)             | 🟢 F-154 (S31) |
| **2f** | Wire preprocessing into Celery + DB persistence (`preprocessed` status, penalties junction) | 🟢 F-155 (S32) |

**Phase-2 DoD:** invoking the pipeline on a fresh source URL ends with an `m1_regulations` row at `status='preprocessed'`, all four metadata fields populated (`gazette_number` / `effective_date` / `penalty_range_lkr` / `principal_act_amended`), and `m1_regulation_penalties` rows for every penalty clause. **Met** as of 2026-05-17; later hardened by the multi-source ship (weekly/acts/bills spiders, F-198) and the admin extraction/observability portal (F-160).

---

## 2. Technologies actually used in Phase 2

Phase 2 is where the **ingestion + extraction stack wakes up** — but the ML *classifier* and *alerting* stacks are still dormant (Phase 3/4).

### Used in Phase 2

| Technology                                               | Layer       | Phase-2 role                                                                                                                                                                                                                           |
| -------------------------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Scrapy**                                               | Ingestion   | 4 spiders (gazette/EGZ, weekly, acts, bills) crawl `documents.gov.lk`                                                                                                                                                                  |
| **Celery + Redis + Beat**                                | Queue       | `gazette_scraper` (6h) → `extract_gazette` → `preprocess_gazette` chain; `run_scraper`, `reconcile_raw`, `run_extraction`; **`quality_probe` (monthly, Session 65)**                                                                   |
| **httpx**                                                | Integration | fetches each PDF **in-memory** from its `download_url` at extract time                                                                                                                                                                 |
| **PyMuPDF · pdfplumber · pypdfium2 · Tesseract · Surya** | Extraction  | multi-engine text + OCR, per-page routing                                                                                                                                                                                              |
| **fastText (`lid.176.bin`)**                             | NLP         | EN/SI/TA language detection (500-char window)                                                                                                                                                                                          |
| **Wijesekara maps**                                      | NLP         | legacy pre-2010 Sinhala font → Unicode conversion                                                                                                                                                                                      |
| **PostgreSQL**                                           | Storage     | `m1_regulations` status pipeline + `m1_gazette_items`, `m1_regulation_penalties`, `m1_sub_documents`, `m1_extraction_runs`/`_profiles`; **`m1_quality_probes` (Session 65)**                                                           |
| **Alembic**                                              | Backend     | `202605220001` (status enum) → penalties junction + `preprocessed` status + `cleaned_text`/`amendment_type`; **`202607210001`–`202607210004` (quality probes, metadata confidence, classification_chunk, extraction_method profiles)** |
| **FastAPI**                                              | Backend     | admin extraction: `POST /admin/m1/extraction/trigger`, `/status/{task_id}`, cancel; WebSocket feed; **`GET /admin/m1/pipeline/health`, `/metadata-review` (Sessions 66–67)**                                                           |
| **Next.js 14 + shadcn**                                  | Frontend    | pipeline observability portal, extraction runner, live progress (WebSocket + polling fallback)                                                                                                                                         |

### NOT yet used in Phase 2 (later phases)

XLM-RoBERTa + LoRA + PyTorch + ONNX (classification = Phase 3), Label Studio + IAA (annotation = Phase 3), SendGrid/Twilio + feedparser (alerts/watchers = Phase 4), scikit-learn/scipy stats + materialized views `v_m1_*` (findings = Phase 4/5). Phase 2 stops at `preprocessed` — it produces the *input* the classifier will later consume, but runs no model.

---

## 3. Step-by-step: planned vs. built (with code files)

### 3a — Scrapy spider (🟢)
`enigmatrix-backend/scraper/`: `spiders/gazette_spider.py` (EGZ from `documents.gov.lk/view/egz/egz_{year}.html`), `weekly_gazette_spider.py`, `acts_spider.py`, `bills_spider.py`, shared `_base.py`; `items.py`; `settings.py`. Two-stage `pipelines.py`: **`M1GazetteItemPipeline`** (validates fields for URL-based extraction) → **`M1RegulationsInsertPipeline`** (INSERT one `m1_regulations` row `status='ingested'` + an `m1_gazette_items` row in one transaction, `DropItem` on UNIQUE `gazette_number` conflict, then `extract_gazette.delay(regulation_id)`). **Design evolution:** F-145 originally wrote PDFs to `STORAGE_LOCAL_PATH/m1/raw/<slug>.pdf`; the current code **does not persist PDFs to disk** (`raw_pdf_path` intentionally unset) and instead re-fetches them in-memory at extract time — see §6 gap #2.

### 3b — Celery wiring (🟢)
`app/m1/tasks/gazette_scraper.py` (`run_gazette_spider`, invokes `scrapy crawl` in a subprocess to dodge the Twisted-reactor singleton), `run_scraper.py`, `reconcile_raw.py` (legacy fallback), `migrate_raw_layout.py`. Registered in `celery_config.py` `include=[…]`; Beat `gazette-scraper-every-6h`. Task identities preserved as `app.tasks.m1.*` (see reorg doc).

### 3c — Classifier + extraction chain (🟢)
`extract_gazette` task (`app/m1/tasks/extract_gazette.py`): load `M1Regulation` (require `status='ingested'`) → httpx-fetch PDF bytes → **(Session 69) try `M1_DEFAULT_EXTRACTION_PROFILE` (`wijesekara_routing_v1`) via the ml registry first**, falling back to → `classify_pdf(bytes)` (char-density: `text_pdf` >200 cpp, `scanned` <30 cpp, else `hybrid`) → run the chosen extractor (`extract_pymupdf` → `extract_pdfplumber` → `extract_tesseract` fallback) → write `raw_text`, `extraction_method` (now records the profile name), `extracted_at` → flip `status='extracted'` (or `extraction_failed` + `last_error`). Algorithms live in `enigmatrix-ml/m1/extraction/` (`pdf_classifier.py`, `text_extractors.py`, `ocr.py`, `page_engines/{pymupdf,pdfplumber,pypdfium2,tesseract}_engine.py`, `surya_engine.py`); the backend mirror `app/extraction/` (`pdf_classifier.py`, `text_extractors.py`, `pdf_metadata.py`) is what the Celery task imports for in-process legacy use. Per-page routing is expressed as **extraction profiles** (`m1/extraction/profiles/{page_routing_v1,wijesekara_routing_v1,surya_fallback_v1,legacy_v1}.py`) dispatched by `run_extraction.py` (Slice 4). See §9.8.1 for the auto-chain wiring.

### 3d — Language detection + Wijesekara (🟢)
`m1/extraction/language_detection.py` (fastText `lid.176.bin` in `storage/models/m1/baseline/`, 500-char window), `wijesekara.py` + `font_aware_wijesekara.py` + `wijesekara_maps/` (legacy Sinhala → Unicode), applied inside `ocr.py` / the page engines.

### 3e + 3f — Preprocessing + persistence (🟢)
Algorithms: `enigmatrix-ml/m1/preprocessing/{cleaning.py, metadata_extractor.py, chunking.py}`. Wired by `preprocess_gazette` task (`app/m1/tasks/preprocess_gazette.py`, chained after `extract_gazette`): require `status='extracted'` → write `cleaned_text`, `gazette_number`, `effective_date`, `penalty_range_lkr`, `principal_act_amended`, `amendment_type` ('amendment'|'repeal'|'new_act'), **`classification_chunk` (Session 68), `metadata_confidence` JSONB + `needs_metadata_review` (Session 67)** → INSERT `m1_regulation_penalties` rows (multi-penalty) → `status='preprocessed'`. Idempotent (`return {"status":"skipped"}` off-path). Model: `app/m1/models/regulation_penalty.py` (`M1RegulationPenalty`).

### Admin surface (F-160)
Backend: `app/m1/api/gazette_extraction.py` (`POST /admin/m1/extraction/trigger` with date-range scope + overlap guard, `GET /status/{task_id}`, `POST cancel` with rollback), `extractions.py`, `extraction_ws.py` (WebSocket live feed), `completeness.py`; **`admin_pipeline.py` (`GET /health`, `GET /metadata-review`, `POST /metadata-review/{id}/resolve`, Sessions 66–67).** Frontend: `(admin)/admin/m1/pipeline/{page,sources,steps,trace,extraction,recent}`, `(admin)/admin/m1/pdf-records`, `(admin)/admin/datasets/m1/extractions/{run,runs/[taskId]}`; components `components/m1/{extraction,pipeline}`, libs `lib/m1/{extraction,pipeline}`.

---

## 4. How it was developed (stages)

Sessions 23 → 43, then 53 → 55 (F-145 → F-198); hardening in Sessions 64 → 69 (gap closure):
1. **S23 / F-145** — Scrapy skeleton + `status` migration + first `ingested` rows (disk-stored PDFs).
2. **Celery wiring** — `gazette_scraper` → `extract_gazette`; Beat 6h.
3. **Extraction chain** — classifier + PyMuPDF/pdfplumber/Tesseract + Surya; profile registry (Slice 4).
4. **S31 / F-154** — preprocessing ml-package (cleaning/metadata/chunking).
5. **S32 / F-155** — preprocessing wired into Celery + DB (`preprocessed`, penalties junction).
6. **S37 / F-160** — admin pipeline observability portal (read-only) + WebSocket live feed.
7. **S53–55 / F-198** — multi-source ship (weekly/acts/bills spiders, `reconcile_raw`, `run_scraper`), URL-based in-memory extraction replaces disk storage.
8. **S64–69 (2026-07-21) — gap closure**: CI live-crawl canary (S64), monthly quality probe (S65), runtime-dependency health check + build gate (S66), metadata confidence + review queue (S67), chunk-contract freeze/align (S68), font-aware auto-chain (S69). See the six `PHASE2_*_PLAN.md` companion docs.

---

## 5. Verification present today

- `app/tests/integration/test_gazette_spider.py` — spider parse + async pipeline INSERT (testcontainer Postgres). Avoids `CrawlerProcess` (Twisted reactor) → historically **live crawl was a manual smoke test, not CI**; now covered by the twice-weekly canary (§6 gap #3).
- `app/tests/live/test_live_crawl_canary.py` — **(Session 64)** selector canary over all 4 spiders + subprocess `scrapy crawl` E2E smoke; marked `live_crawl`+`slow`, scheduled Mon+Thu, deliberately out of PR CI.
- `test_celery_extract_gazette.py`, `test_celery_preprocess_gazette.py` — task-level chain.
- `test_run_extraction_with_profile.py` — profile dispatcher.
- `enigmatrix-ml/tests/m1/preprocessing/test_chunk_contract.py` — **(Session 68)** chunk-contract field-shape freeze + head-window ≡ 512-truncation equivalence (fake-tokenizer layer everywhere; real XLM-R layer gated on tokenizer cache).
- Roadmap DoD audits: PDF-type classification ≥95 % (50-PDF hand audit); OCR CER ≤10 % on SI/TA; language detection ≥95 % (100-doc set) — historically **point-in-time audits**; now shadowed continuously by the monthly `quality_probe` proxy metrics (§6 gap #4). True CER re-measurement stays a quarterly manual audit by design.

---

## 6. Gaps & missed approaches (the analytical part)

1. **`gazette.lk` is not fully wired.** The roadmap names `gazette.lk` as a primary source, but it is an ASP.NET **viewstate** site kept only in `allowed_domains` as a Step-2c hardening target; real crawling runs against `documents.gov.lk` only. The second official source is effectively deferred. → 📋 **Planned** (do last): `FormRequest` viewstate postbacks, feature-flagged out of Beat until the canary is green for two runs — see [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_GAP_CLOSURE_PLAN]] §6.1.
2. **PDFs are no longer stored — re-extraction depends on source-URL availability.** Moving to in-memory httpx fetch saved storage but introduced **link-rot risk**: if `download_url` dies, a row can't be re-extracted. `reconcile_raw_pdfs` is kept as a legacy bridge but is slated for retirement. → 📋 **Planned** (urgent-half backfill): write-through raw-PDF archive to S3/MinIO (`M1_PDF_ARCHIVE_*`, `raw_pdf_object_key`), archive→URL→fail re-extraction order — see [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_GAP_CLOSURE_PLAN]] §6.2.
3. **Twisted-reactor constraint means no CI coverage of a live crawl.** Tests deliberately avoid `CrawlerProcess`; a real network regression (site markup change) would only surface in the manual smoke test or in production. → ✅ **Closed (Session 64, 2026-07-21):** live-markup canary + subprocess crawl smoke on a twice-weekly schedule — see [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_GAP_CLOSURE_PLAN]] §6.3 (`app/tests/live/`, `.github/workflows/crawl-canary.yml`).
4. **Extraction-quality DoDs are audited once, not monitored.** Classification accuracy / OCR CER / language-detection accuracy were hand-audited at ship time; there is no continuous drift metric on extraction quality (the confidence-drift job that exists targets the *classifier*, Phase 3+, not the extractor). → ✅ **Closed (Session 65, 2026-07-21):** monthly `quality_probe` Beat task — DB-derived proxy metrics (failed/empty/CID/Wijesekara/OCR-share/unknown-lang/metadata-completeness/`profile_share`) into new `m1_quality_probes`, floors + 2σ drift alerts into the admin Activity Log — see [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_QUALITY_MONITORING_PLAN]]. True CER re-measurement remains a quarterly manual audit by design.
5. **Heavy/optional dependencies.** Surya (`surya_engine.py`) and Tesseract add large system deps; ensure the production image actually ships them, else the OCR fallback silently degrades. `lid.176.bin` must be present — a deploy-time step that is easy to miss and has no startup assertion. → ✅ **Closed (Session 66, 2026-07-21):** `app/m1/health.py` runtime check (`check_extraction_runtime`) surfaced at worker boot, `/admin/m1/pipeline/health`, and container start; `lid.176.bin` now baked into the image (`M1_LID_MODEL_PATH=/opt/models/…`) and a `--strict` health gate fails the Docker build if the runtime is incomplete — see [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_RUNTIME_DEPS_PLAN]]. Also closes §9.8.5.
6. **Metadata extraction is regex/pattern-based** (`metadata_extractor.py`) — brittle across gazette layout drift; a malformed date or penalty string yields a missing field rather than a flagged error. → ✅ **Closed (Session 67, 2026-07-21):** backend-side per-field sanity scoring (`metadata_confidence.py`, deliberately independent of the ml package so it ships without an ML_GIT_REF bump) → `metadata_confidence` JSONB + `needs_metadata_review` flag written by `preprocess_gazette` → admin queue + audited resolve at `/admin/m1/pipeline/metadata-review` — see [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_METADATA_CONFIDENCE_PLAN]]. ml-side pattern-tier confidence remains the planned deepening.
7. **Chunking output isn't consumed yet.** `chunking.py` prepares text "ready for Stage D," but nothing downstream reads it until Phase 3 — worth confirming the chunk contract matches what the classifier will expect, before Phase 3 locks in. → ✅ **Closed (Session 68, 2026-07-21):** the audit found the contract had already forked — live Stage-D truncated full `cleaned_text` while the ml chain computed (and the backend discarded) the section-aware EN-bucket `classification_chunk`. Contract frozen by test (`test_chunk_contract.py`), aligned by persisting `classification_chunk` (migration `202607210003`) and making `classify_gazette` consume it — see [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_CHUNK_CONTRACT_PLAN]], incl. the training-skew A/B check to run before trusting mixed-language outputs.

Residual open items are 1, 2, and the font-level/Tamil sub-gaps of §9.8; items 1 and 2 are the ones to address before relying on the pipeline unattended in production. **Gap-closure tracker:** see [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_GAP_CLOSURE_PLAN]] for priority order and per-gap plans.

---

## 7. Traceability (capability → code → doc → F-id)

| Capability | Code path(s) | Doc | F-id |
|---|---|---|---|
| Gazette spider(s) | `scraper/spiders/*`, `scraper/pipelines.py`, `items.py` | `03_M1_Data_Collection §1` | F-145, F-198 |
| Celery scrape task + Beat | `app/m1/tasks/{gazette_scraper,run_scraper,reconcile_raw}.py`, `celery_config.py` | `03_M1 §6.1` | F-146 |
| PDF classify + extract | `app/m1/tasks/extract_gazette.py`, `app/extraction/*`, `enigmatrix-ml/m1/extraction/*` | `03_M1_1_PDF_Extraction_Chain` | F-147–F-150 |
| Language detect + Wijesekara | `m1/extraction/{language_detection,wijesekara,font_aware_wijesekara,ocr}.py` | `10_M1_1`, `10_M1_2` | F-151–F-153 |
| Preprocess (clean/meta/chunk) | `m1/preprocessing/*`, `app/m1/tasks/preprocess_gazette.py` | `04_M1_Preprocessing_Pipeline` | F-154, F-155 |
| Penalties junction | `app/m1/models/regulation_penalty.py` | `04_M1_2 §3.3` | F-155 |
| Extraction profiles + runner | `m1/extraction/profiles/*`, `app/m1/tasks/run_extraction.py` | Slice 4 plan | — |
| Admin extraction + observability | `app/m1/api/{gazette_extraction,extractions,extraction_ws,completeness}.py`; `(admin)/admin/m1/pipeline/*` | `14_M1_1` | F-160 |
| Live-crawl canary | `app/tests/live/test_live_crawl_canary.py`, `.github/workflows/crawl-canary.yml` | [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_GAP_CLOSURE_PLAN]] §6.3 | S64 |
| Extraction-quality probe | `app/m1/tasks/quality_probe.py`, `app/m1/models/quality_probe.py`, `202607210001` | [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_QUALITY_MONITORING_PLAN]] | S65 |
| Runtime health check + build gate | `app/m1/health.py`, `Dockerfile`, `scripts/start_railway.sh` | [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_RUNTIME_DEPS_PLAN]] | S66 |
| Metadata confidence + review queue | `app/m1/services/metadata_confidence.py`, `admin_pipeline.py`, `202607210002` | [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_METADATA_CONFIDENCE_PLAN]] | S67 |
| Chunk contract freeze + align | `enigmatrix-ml/.../chunk_schema.py`, `test_chunk_contract.py`, `202607210003` | [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_CHUNK_CONTRACT_PLAN]] | S68 |
| Font-aware auto-chain | `app/m1/tasks/extract_gazette.py` (profile-first), `202607210004` | [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_TRILINGUAL_AUTOCHAIN_PLAN]] | S69 |

---

## 8. Data flow — how data travels through the stages (Phase 2)

Unlike Phase 1 (human-entered), Phase 2's input is a **government website + PDF files**, and most of the journey is server-to-server (no browser in the hot path). Two entry points: the **scheduled** crawl (Beat) and the **admin-triggered** scoped run.

### 8.0 Inputs / data sources

| Input | Where it enters | Becomes |
|---|---|---|
| `documents.gov.lk` EGZ/GZ/BILL/ACT year listings | Scrapy spider `start_urls` | discovered PDF `download_url` + metadata |
| The gazette **PDF file** (bytes) | fetched in-memory via httpx at extract time | `raw_text` on the `m1_regulations` row |
| Admin date-range + source scope | `(admin)/admin/m1/pipeline/…/extraction` form | a scoped Celery run (`m1_extraction_runs`) |
| `gazette.lk` | *not wired* (viewstate hardening target) | — |

### 8.1 Scheduled ingestion (no frontend — Beat-driven)

```
Celery Beat (every 6h)
  → app/m1/tasks/gazette_scraper.run_gazette_spider   (subprocess: scrapy crawl gazette_spider)
    → scraper/spiders/gazette_spider.py  crawls documents.gov.lk → yields items (items.py)
      → scraper/pipelines.py:
          M1GazetteItemPipeline      (validate fields)
          M1RegulationsInsertPipeline → INSERT m1_regulations (status='ingested')
                                        + INSERT m1_gazette_items          [DB]
                                        → extract_gazette.delay(regulation_id)   [→ Redis queue]
```

### 8.2 Extraction (Celery worker, server-side)

```
extract_gazette(regulation_id)                         app/m1/tasks/extract_gazette.py
  → SELECT m1_regulations WHERE id=? AND status='ingested'
  → httpx GET download_url → PDF bytes (in memory)
  → IF M1_DEFAULT_EXTRACTION_PROFILE set (default wijesekara_routing_v1):        [Session 69]
        bytes → NamedTemporaryFile → PROFILE_REGISTRY[name]().extract()
        (per-span font-aware SI conversion; records cid_before/after, wijesekara_applied)
        on ANY failure → warning + fall through to the legacy block below
  → app/extraction/pdf_classifier.classify_pdf(bytes)  → text_pdf | hybrid | scanned   [legacy fallback]
  → extractor: extract_pymupdf → extract_pdfplumber → extract_tesseract   (ML engines)
       (language_detection + Wijesekara applied per page inside ocr.py)
  → UPDATE m1_regulations SET raw_text, extraction_method (profile name or engine), extracted_at, status='extracted'
  → live progress emitted → app/m1/services/extraction_live_feed → WebSocket (extraction_ws)
  → chains → preprocess_gazette.delay(regulation_id)
        (on error: status='extraction_failed', last_error set)
```

### 8.3 Preprocessing (Celery worker → DB)

```
preprocess_gazette(regulation_id)                      app/m1/tasks/preprocess_gazette.py
  → require status='extracted' (else skip, idempotent)
  → ml preprocessing: cleaning.py → clean text
                      metadata_extractor.py → gazette_number, effective_date,
                                              penalty_range_lkr, principal_act_amended, amendment_type
                      chunking.py → chunks + classification_chunk (EN-bucket section head)
  → metadata_confidence.score(final row values) → metadata_confidence JSONB + needs_metadata_review  [Session 67]
  → UPDATE m1_regulations SET cleaned_text, <4 metadata fields>, amendment_type,
                              classification_chunk, metadata_confidence, needs_metadata_review, status='preprocessed'
  → INSERT m1_regulation_penalties (one row per penalty clause)          [DB]
```

### 8.4 Admin-triggered scoped run + live monitoring (frontend in the loop)

```
[admin] /admin/m1/pipeline/.../extraction  (date-range + source scope)
  → lib/m1/pipeline client → POST /api/v1/admin/m1/extraction/trigger   [require_admin]
    → app/m1/api/gazette_extraction.trigger_extraction
        → overlap guard (find_overlapping_extraction_runs)
        → enqueue scraper/extraction task; persist m1_extraction_runs row
      ← {task_id}
  → UI polls GET /status/{task_id}  AND/OR subscribes WebSocket (extraction_ws)
      → live per-PDF sub-step progress (extracting_text, …) from extraction_live_feed
  → observability: /admin/m1/pipeline/{sources,steps,trace/[regulationId],health,metadata-review}
       read the m1_regulations status + m1_extraction_runs history and render the funnel/flow
  Cancel: POST /cancel → cancel_and_rollback (revokes task, rolls back that run's writes)
```

### 8.5 Where each stage lives (quick map)

| Stage | Component | Code |
|---|---|---|
| Discover + download | Scrapy spiders + pipeline | `scraper/spiders/*`, `scraper/pipelines.py` |
| Queue | Celery + Redis + Beat | `celery_config.py`, `app/m1/tasks/*` |
| Fetch PDF | httpx (in-memory) | `extract_gazette.py` |
| Extract text/OCR | profile-first (font-aware) then PyMuPDF/pdfplumber/Tesseract/Surya + fastText + Wijesekara | `app/extraction/*`, `enigmatrix-ml/m1/extraction/*` |
| Preprocess | cleaning + metadata + chunking + confidence | `enigmatrix-ml/m1/preprocessing/*`, `preprocess_gazette.py`, `metadata_confidence.py` |
| Persist | Postgres pipeline tables | `m1_regulations`, `m1_gazette_items`, `m1_regulation_penalties`, `m1_extraction_runs`, `m1_quality_probes` |
| Monitor quality | monthly Beat probe | `app/m1/tasks/quality_probe.py`, `m1_quality_probes` |
| Assert runtime | health check | `app/m1/health.py`, `GET /admin/m1/pipeline/health` |
| Trigger + watch | FastAPI admin + Next.js portal + WebSocket | `app/m1/api/gazette_extraction.py`, `(admin)/admin/m1/pipeline/*` |


---

## 9. Deep-dive: trilingual (EN/SI/TA) extraction — the garbled-text problem & the font-aware upgrade

This is the part the earlier draft under-covered: **English extracted cleanly from the start, but Sinhala/Tamil came out as garbled/mojibake text** in the first pass — and Phase 2 was later *expanded* with font-type detection to fix it. Below is the actual mechanism, verified against the code, plus what is / isn't wired.

### 9.1 Why English worked but Sinhala/Tamil garbled

Pre-2010 Sri Lankan gazettes are typeset in **legacy "Wijesekara" fonts** — non-Unicode fonts where each Sinhala glyph is stored under a **Latin/ASCII code point**. `page.get_text()` therefore returns ASCII-looking rubbish (e.g. CID markers / Latin salad) for Sinhala, even though the PDF *looks* correct on screen. English (already ASCII/Unicode) extracts fine; Sinhala (and legacy-font Tamil) does not. So the first-pass extractor "worked" for EN and produced **encoded/undecoded garbage** for SI/TA — exactly the symptom described.

### 9.2 The two-stage evolution (first pass → font-aware upgrade)

| | Stage 1 — first pass (Sessions 23–32) | Stage 2 — Phase-2 Upgrade Plan, **Slice 7** (2026-05-23) |
|---|---|---|
| Where | auto-chain `extract_gazette` → backend `app/extraction/*` | ML profile path `enigmatrix-ml/m1/extraction/profiles/*` via `run_extraction_with_profile` |
| Sinhala | single **canonical** Wijesekara map, run **once over the whole document** (loses per-span font signal) | **per-span, font-specific** conversion *before* page assembly |
| Font awareness | none — one map for all fonts | **detects the font**, picks a per-font override map |
| Outcome | EN clean; SI often still garbled (wrong map for the font) | CID markers `4800 → 0` on a real doc (`2468/44`), per the slice-7 dashboard metric |

So the "upgrade" is **Slice 7 — new extraction profiles** (`page_routing_v1`, `wijesekara_routing_v1`, `surya_fallback_v1`, `legacy_v1`), dispatched by `app/m1/tasks/run_extraction.py`. **As of Session 69 the `wijesekara_routing_v1` profile is also the default for the auto-chain** (§9.8.1).

### 9.3 The routing / threshold decision (the "if fewer than N chars, which steps; if scanned, which approach")

**Two-level classification** — a document label *and* a per-page label (because a text-heavy cover page can mask a scanned body):

- **Document level** — `enigmatrix-ml/m1/extraction/pdf_classifier.py`: mean chars/page over the first 3 pages →
  - `>= 200` (`M1_PDF_TEXT_THRESHOLD`) → **`text_pdf`**
  - `>= 30` (`M1_PDF_SCANNED_THRESHOLD`) → **`hybrid`**
  - `< 30` → **`scanned`**
  Thresholds are env-tunable and have a quarterly recalibration routine (`_threshold_calibration`, candidate pairs e.g. `(180,30)`,`(200,30)`).
- **Per-page** — `page_engines/classifier.py`: a page with **text spans < 10 AND image-area-ratio > 0.5** → `scanned`; otherwise `text`/`hybrid`. So each page is routed independently.

**Extractor per route:**
- `text_pdf` / text pages → **PyMuPDF** `get_text` (alternates: `pdfplumber`, `pypdfium2` engines).
- `scanned` pages → **Tesseract OCR** (`ocr.py`): `--psm 6 --lang eng+sin+tam`, **dpi=300** (200 loses Sinhala diacritics), via `pdf2image`. After OCR, `is_wijesekara_encoded(text)` gates a `convert_wijesekara` pass.
- **Surya OCR** (`surya_engine.py`, profile `surya_fallback_v1`) is the intended higher-accuracy fallback for hard scanned SI/TA — but it is currently a **stub deferred to Phase 3** (`run_surya_on_page` raises "deferred", gated on GPU). Since Session 66 the health check reports it as `surya: stub` so nobody assumes the fallback exists in prod. ⚠️

### 9.4 Language detection (which language → which routing)

`language_detection.py`, two layers (per `10_M1_1_Language_Detection_Routing.md`):
- **Layer 1 (document)** — fastText `lid.176.bin` (~127 MB), first **500 chars** (`M1_LID_WINDOW_CHARS`), confidence ≥ **0.70** (`M1_LID_MIN_CONFIDENCE`) → primary `en|si|ta|mixed`.
- **Layer 2 (per-line)** — Unicode-range router: Sinhala `U+0D80–0DFF`, Tamil `U+0B80–0BFF`, English Latin. This is what lets a mixed EN/SI gazette line route correctly.

Model resolution: `M1_LID_MODEL_PATH` env → else `storage/models/m1/baseline/lid.176.bin`; lazy-loaded on first call. **As of Session 66 the model is baked into the image at `/opt/models/` with `M1_LID_MODEL_PATH` set and a build-time size assertion — the old "easy-to-miss deploy copy" no longer exists.**

### 9.5 Font detection with several options (the font-aware piece)

`font_aware_wijesekara.py` (Slice 7.B):
- **`LEGACY_FONT_PREFIXES`** — 12 known legacy families: `FM`, `DL-`, `Iskoola Pota Wij`, `Bindumathi`, `Abhaya`, `Mihintale`, `Tikiri`, `Malithi`, `Bamini`, `Kaputa`, `Amalee`, `Thibus`. (Empirical list; unknown fonts surfaced by slice-7.3 instrumentation are meant to be added and shipped as `wijesekara_routing_v1.1`.)
- **`is_legacy_font(font_name)`** → is this span's font a legacy one?
- **`convert_with_font_table(text, font_name)`** → picks the per-font override map (small per-font YAML in `wijesekara_maps/`, layered on the canonical ~120-entry map), then runs the **greedy 4→3→2→1 longest-match** substitution.
- **Gate:** `is_wijesekara_encoded(text)` (≥ **0.40** indicator-char ratio, `WIJESEKARA_THRESHOLD`) decides whether to convert at all — Unicode-clean spans are bypassed so good text isn't corrupted.

In `wijesekara_routing_v1.py` the flow is per-span: read each PyMuPDF span's `font`; `if is_legacy_font(font): text = convert_with_font_table(text, font)` — **before** the page is assembled, preserving the font signal Stage 1 lost.

### 9.6 Implementation status (verified)

| Capability | Status | Where |
|---|---|---|
| Doc-level char-threshold classifier (200/30) | ✅ | `pdf_classifier.py` |
| Per-page text/hybrid/scanned routing | ✅ | `page_engines/classifier.py` |
| PyMuPDF / pdfplumber / pypdfium2 text engines | ✅ | `page_engines/*` |
| Tesseract OCR `eng+sin+tam` @300dpi | ✅ | `ocr.py` |
| fastText + per-line Unicode language routing | ✅ | `language_detection.py` |
| Canonical Wijesekara (heuristic + greedy sub) | ✅ | `wijesekara.py` |
| **Font-type detection (12 families) + per-font maps** | ✅ | `font_aware_wijesekara.py`, `wijesekara_maps/` |
| Per-span font-aware conversion profile | ✅ | `profiles/wijesekara_routing_v1.py` |
| **Font-aware profile wired into the auto-chain** | ✅ **(Session 69)** | `extract_gazette.py` (profile-first + legacy fallback) |
| Surya OCR fallback | ⚠️ **stub, deferred to Phase 3** (visible as `surya: stub` in health) | `surya_engine.py`, `profiles/surya_fallback_v1.py` |

**Resolved divergence:** the font-aware Sinhala fix originally lived only in the **ML profile path** (`run_extraction_with_profile`), while the **default automatic pipeline** applied no Wijesekara/font-aware conversion — so a newly scraped gazette landed with SI/TA garbled until a manual profile re-extraction. **Session 69 made `wijesekara_routing_v1` the auto-chain default** (`M1_DEFAULT_EXTRACTION_PROFILE`), with a hard fallback to the legacy chain so the auto-path can never be *less* reliable than before. Backfill of pre-Session-69 garbled rows is an operator step (§9.8.1).

### 9.7 Data traversal — the font-aware extraction path

```
[admin] /admin/m1/pipeline/.../extraction  OR  /admin/datasets/m1/extractions/run
        (choose extraction profile, e.g. wijesekara_routing_v1, + scope)
  → lib/m1/{pipeline,extraction} → POST /api/v1/admin/m1/extraction/...   [require_admin]
    → app/m1/api/... → run_extraction_with_profile.delay(version_id, profile_name, scope)   [Redis]
      → app/m1/tasks/run_extraction.py → load_profile(profile_name)      [profile_service]
        → for each PDF:
            pdf_classifier.classify_pdf  → text_pdf | hybrid | scanned
            per page: page_engines/classifier.classify_page
              text page  → PyMuPDF spans → for each span:
                              font = span.font
                              if is_legacy_font(font): convert_with_font_table(text, font)   ← SI fix
              scanned page → Tesseract (eng+sin+tam, 300dpi) → is_wijesekara_encoded? → convert_wijesekara
            language_detection.detect_document_language → en|si|ta|mixed
        → persist extracted text + per-field metrics (cid_marker_count_before/after, wijesekara_applied)
          into the dataset version + m1_extraction_runs
  → UI: components/m1/measurement-dashboard + measurement-comparison render the quality deltas
        (e.g. "CID count 4800 → 0"), field heatmaps, worst-N lists

The same per-span path now also runs inside the Beat-driven auto-chain (Session 69), via the
ml PROFILE_REGISTRY directly, on every newly scraped gazette.
```

So for the trilingual path the browser's role is **choosing the profile and reading the quality dashboard**; the font detection + conversion happen server-side in the ML profile, and the *evidence* it worked (CID drop, Wijesekara-applied flag) flows back to the admin measurement UI — and, for auto-chain runs, to the Celery task result and the monthly probe's `profile_share`.

### 9.8 Gaps specific to trilingual extraction

1. **Auto-chain isn't font-aware** (see §9.6) — historically the highest-impact gap: routine ingestion garbled SI/TA until a profile re-extraction ran. → ✅ **Closed (Session 69, 2026-07-21):** `M1_DEFAULT_EXTRACTION_PROFILE=wijesekara_routing_v1` — `extract_gazette` runs the profile first (ml registry direct, temp-file bridge), falls back to the legacy chain on any failure (never less reliable than before), records the profile in `extraction_method` (migration `202607210004`), logs CID before/after, and the monthly probe watches `profile_share` for silent fallback — see [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_TRILINGUAL_AUTOCHAIN_PLAN]]. Backfill of pre-existing garbled SI rows deferred to operator (plan §Backfill).
2. **Surya is a stub** — the better scanned-SI/TA engine is deferred to Phase 3, so hard scans rely on Tesseract CER alone. Now at least **visible** (`surya: stub` in the health check since Session 66). → 📋 Phase-3 activation plan in [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_TRILINGUAL_AUTOCHAIN_PLAN]] §9.8.2.
3. **Unknown fonts silently fall back** to the canonical map (may still garble); depends on the slice-7.3 instrumentation actually being watched to grow the 12-font list. → ⚙️ **Partially covered (Session 69):** the quality probe's `profile_share` catches chain-level silent fallback; font-level instrumentation (`unknown_suspect_fonts` in `error_signals`, probe aggregation) planned in [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_TRILINGUAL_AUTOCHAIN_PLAN]] §9.8.3 (needs ML_GIT_REF bump).
4. **Legacy *Tamil* fonts aren't covered** — the Wijesekara machinery is Sinhala-specific; Tamil relies on Unicode + Tesseract `tam`. If any Tamil gazettes use legacy Tamil encodings, that stratum is uncovered. → 📋 **Audit-first plan** in [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_TRILINGUAL_AUTOCHAIN_PLAN]] §9.8.4: indicator query + 20-doc sample decides whether Tamil maps get built or the gap closes as "not present in corpus".
5. **`lid.176.bin` is a required, unasserted artifact** — missing model silently degrades language routing. → ✅ **Closed (Session 66)** — baked into the image + asserted at build/boot/API; see [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/PHASE2_RUNTIME_DEPS_PLAN]].

---

*Scope note: this document covers Phase 2 only. Phase 1 (foundation) is in `PHASE1_FOUNDATION_ANALYSIS.md`; Phase 3 (annotation + XLM-R/LoRA classification) is in `PHASE3_ANNOTATION_CLASSIFICATION_ANALYSIS.md`; Phase 4 (schedulers + alerts) in `PHASE4_SCHEDULERS_ALERTS_ANALYSIS.md`. Phase 2 ends at `status='preprocessed'` — it produces the classifier's input but runs no model. Gap-closure companions: `PHASE2_GAP_CLOSURE_PLAN.md` + the five per-gap plan docs.*
