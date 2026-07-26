# M1 Pipeline — Stages, Statuses, Manual Stepping & Known System Issues

> Goal: document how a gazette moves through the pipeline (ingested → extracted → preprocessed → classified), how each stage maps onto the 39-column golden Excel format (`structured_v1_batches_1_2_3_4_5_6_7_8_official.xlsx`), the new **manual, one-stage-at-a-time** control that was added on 2026-07-26, and the two runtime issues currently surfaced in the Celery logs.

---

## 1. Stage → status → golden-Excel column map

A regulation row (`m1_regulations`) carries a `status` that advances through the pipeline. The known statuses (from `pipeline_service._KNOWN_STATUSES`) are:

```
ingested → extracted → preprocessed → classified → summarized → alerted → archived
                     ↘ extraction_failed
```

Which stage writes which golden column (canonical names match the field contract in `data/golden/field_contract_v1.yaml`):

| Stage | Trigger task | Sets on the row | Golden columns populated | Contract phase |
| --- | --- | --- | --- | --- |
| **Ingest** | scraper `run_gazette_spider` / `run_scraper`; legacy `reconcile_raw_pdfs` | registers `m1_gazette_items`, `raw_pdf_path`, `gazette_number`, `document_number`, `source_url`, `status='ingested'` | `gazette_number`, `document_number`, `raw_pdf_path`, `source_url`, `document_type` | extraction / provenance |
| **Extract** | `extract_gazette` | `raw_text`, `extraction_method`, `extracted_at`, `file_size_bytes`, `sha256`, `pdf_pages`, `language`, `status='extracted'` | `raw_text`, `extraction_method`, `extracted_at`, `title_en` (best-effort) | extraction (Tier A/B) |
| **Preprocess** | `preprocess_gazette_task` | `cleaned_text`, `classification_chunk`, `amendment_type`, `metadata_confidence`, `m1_sub_documents`, `m1_regulation_penalties`, `status='preprocessed'` | `cleaned_text`, `bill_published_date`, `effective_date`, `gazette_published_date`, `principal_act_amended`, `penalty_range_lkr` (metadata regexes) | extraction (dates/act) + Tier-D penalty |
| **Classify** | `classify_gazette_task` | `domain_code`, `change_category`, `severity_level`, `is_sme_relevant`, `classifier_confidence`, `classified_at`, `status='classified'` | `domain_code`, `change_category`, `severity_level`, `is_sme_relevant` | **annotation (Tier D — excluded from extraction EQS)** |

This is exactly why the field contract marks the classification columns Tier-D `annotation`: they are produced (or meant to be) by the Stage-D classifier, not by extraction. Scoring them as extraction accuracy would be wrong — and right now they are not being populated at all (see §3.2).

`metadata_confidence` from the log — `{"gazette_number": 0.95, "effective_date": 0.0, "penalty_range_lkr": 0.0, "principal_act_amended": 0.0}` — is the **extraction/metadata confidence channel**, distinct from `classifier_confidence` (Stage-D softmax) and from `sme_relevance_confidence` (human/expert). Keep the three separate, as the contract requires.

---

## 2. Manual stage stepping (new, 2026-07-26)

**Before:** every stage auto-chained. `reconcile/scraper → extract_gazette → preprocess_gazette_task → classify_gazette_task`, each stage dispatching the next with `apply_async`. Running an extraction ran the whole pipeline with no stop points.

**Now:** the operator can run one stage at a time and inspect between stages, or run the whole remainder with one click.

### 2.1 How it works
- The three chaining tasks gained an `auto_advance` parameter (default **True**, so every existing caller — reconcile, resume-on-startup, `run_extraction`, batch profiles — keeps auto-chaining exactly as before).
  - `extract_gazette(regulation_id, auto_advance=True)` — when `False`, it stops at `status='extracted'` instead of enqueuing preprocess.
  - `preprocess_gazette_task(regulation_id, auto_advance=True)` — when `False`, it stops at `status='preprocessed'` instead of enqueuing classify.
- Two new admin endpoints under `/api/v1/admin/m1/pipeline`:
  - `POST /regulations/{id}/advance` — runs **exactly the next stage** for that regulation (dispatched with `auto_advance=False`), then stops. `ingested→extract`, `extracted→preprocess`, `preprocessed→classify`. Returns `{from_status, dispatched_stage, next_status, task_id, mode:"single"}`; `409` if there is no next stage.
  - `POST /regulations/{id}/run-all` — runs the **remainder** of the chain in one go (dispatched with `auto_advance=True`). `mode:"all"`.
  - Both are `require_admin` and audited (`m1_regulation.pipeline.advance` / `.run_all`).

### 2.2 UI
On the regulation trace page (`/admin/m1/pipeline/trace/{regulationId}`) there is now a **Pipeline control** card (`StageStepper`): an animated 4-node rail (Ingested → Extracted → Preprocessed → Classified) with:
- **Advance · {NextStage}** — runs one stage and stops.
- **Run all steps** — auto-chains the rest.

The status badge and rail advance automatically as the worker finishes (the trace query is invalidated on dispatch and polls every 15s).

### 2.3 Run-level (batch) manual stepping — IMPLEMENTED
The whole-run flow the operator asked for is now wired end to end:

**Critical: `resume_pipeline` must not undo ingest-only.** `resume_pipeline` (a crash-recovery sweep that runs on every worker boot and on schedule) re-enqueues the next stage for any row parked at `ingested`/`extracted`/`preprocessed`. That silently auto-extracted the manually-parked rows — the observed "Pipeline failed · 12/180 preprocessed" after an ingest-only crawl. Fix: rows ingested in manual mode now carry a persistent **`manual_hold=true`** flag (new `m1_regulations.manual_hold` column, migration `202607260002`), and `resume_pipeline` excludes held rows from its sweep. So ingest-only rows stay at `ingested` until the operator advances them; every other row keeps normal auto-recovery. **Apply the migration** (`uv run alembic upgrade head`) or the flag column won't exist.

**Ingest-only crawl.** The source extraction page (`/admin/m1/pipeline/sources/{source}/extraction`) now has an **"Ingest only — step stages manually"** checkbox next to the Start button (default **ON**), which sends `manual: true` and relabels the button to *Start … ingest*. The `/trigger` payload gained `manual: bool = False`. When `manual=True`:
- `run_scraper` launches the spider with `-a auto_extract=0`; the Scrapy item pipeline (`scraper/pipelines.py`) sees `spider.auto_extract` is falsy and **does not** dispatch `extract_gazette`, so every scraped row lands at `status='ingested'`.
- the `reconcile_raw_pdfs` auto-backfill (which itself auto-extracts) is **skipped**, so nothing sneaks the rows past ingest.
- Default (`manual=False`) is unchanged: scrape auto-extracts exactly as before.

**Completeness check.** After the crawl settles, run the existing verify/completeness step (`/api/v1/admin/m1/extraction/verify`) to confirm every gazette in the window was ingested before advancing. The **Re-fetch** action now honours ingest-only too: `refetch-missing` gained a `manual` flag (default follows the page's Ingest-only toggle) — in manual mode it creates the missing rows at `status='ingested'` with `manual_hold=true` and does **not** dispatch extraction, and the button reads **Ingest all (N)**. So filling completeness gaps no longer secretly runs the whole pipeline; the gap rows join the same manual batch-stepping flow.

**Batch stage buttons.** `POST /api/v1/admin/m1/pipeline/batch/{stage}` with body `{source_id, date_from, date_to}`, where `stage ∈ {extract, preprocess, classify, run-all}`. Each selects the in-window rows (joined on `m1_gazette_items.source_id` + `document_date`, since the scrape date exists at ingest while `gazette_published_date` is only parsed later) at the prerequisite status and dispatches that stage per row:
- `extract` → rows at `ingested`, dispatched with `auto_advance=False`
- `preprocess` → rows at `extracted`, `auto_advance=False`
- `classify` → rows at `preprocessed`
- `run-all` → rows at any of the three, dispatched with `auto_advance=True` (each row auto-chains the rest)

Returns `{stage, matched, dispatched, mode}`; admin-only and audited (`m1.pipeline.batch.*`).

**UI.** The extraction run page (`/admin/m1/pipeline/sources/{source}/extraction/runs/{taskId}`) now shows a **Batch pipeline control** card (`BatchStageControl`) with **Extract all / Preprocess all / Classify all** buttons — each badged with the live count of rows ready at that stage and disabled when zero — plus **Run all steps**. Clicking refetches the run summary so the per-stage tallies move as workers finish.

So the operator flow is exactly: run (manual) → all `ingested` → completeness check → **Extract all** → all `extracted` → **Preprocess all** → all `preprocessed` → **Classify all** (no-ops until a Phase-3 model exists, see §3.2), or **Run all steps** at any point.

---

## 3. Known system issues currently in the logs

### 3.1 fastText language model missing (CRITICAL, non-fatal)
```
EXTRACTION RUNTIME DEGRADED — fasttext_model: lid.176.bin not found —
ML-profile language routing will fall back
(searched: ['storage\models\m1\baseline\lid.176.bin', ...])
```
**Impact:** the ML extraction profile can't do fastText language identification, so language routing falls back to a heuristic. Extraction still works (`language='en'`/`'mixed'` is still set), but SI/TA routing is less reliable — relevant because SI/TA titles are Tier-C extraction fields.
**Fix:** download the 126 MB fastText model to `storage/models/m1/baseline/lid.176.bin` (`https://dl.fbaipublicfirst.../lid.176.bin`, official fastText LID). Until then the CRITICAL line is expected and safe to ignore.

### 3.2 Stage-D classifier has no model (skips classification)
```
classify_gazette: classifier not ready (no_model) — leaving {id} at 'preprocessed',
not classifying. no ONNX artifact in storage/models/m1/onnx/v1 —
classify_gazette will fail per-row until Phase-3 training drops one;
change_category is NOT being model-populated
```
**Impact:** rows stop at `status='preprocessed'`. `domain_code`, `change_category`, `severity_level`, `is_sme_relevant` are **not** being populated by the pipeline — they only exist in the golden Excel because they were expert-curated. This is consistent with the field contract (those columns are Tier-D annotation, excluded from extraction EQS). The **Classify** button will no-op until a Phase-3 model lands in `storage/models/m1/onnx/v1`.
**Fix:** train and drop the ONNX classifier (Phase-3), or leave classification deferred and rely on expert annotation.

### 3.3 `extraction_method` column too narrow — FIXED
`m1_dataset_rows.extraction_method` was `VARCHAR(20)`; method labels like `wijesekara_routing_v1` (21) overflowed on snapshot/upload. Widened to `VARCHAR(64)` (migration `202607260001`). Run `uv run alembic upgrade head`.

### 3.4 `reconcile_raw_pdfs` runs in LEGACY mode (informational)
```
reconcile_raw_pdfs: running in LEGACY mode — scanning disk for PDFs.
This task is deprecated. Prefer re-running the spider ...
```
Not an error — it registered 0 rows because ingestion now goes through the spider (`m1_gazette_items`, no disk write). Safe to ignore; eventually retire the task.

### 3.5 `wijesekara_applied=False`, `cid markers 0` (informational)
The Wijesekara legacy-font remap didn't need to fire (no `(cid:NN)` glyph corruption in these PDFs). Expected for native-text gazettes; the corrupted-Sinhala remap only triggers when cid markers are present.

---

## 3.6 Deploy note — restart the worker after these changes
Celery workers do **not** hot-reload (only the API's `uvicorn --reload` does). After any change to a Celery task signature or a model, you must:
1. `uv run alembic upgrade head` — apply schema changes (e.g. `manual_hold`).
2. Restart the Celery worker (and beat).

Symptom of skipping this: a scrape triggered from the reloaded API calls `run_scraper.delay(..., auto_extract=…)`, but a stale worker still has the old `run_scraper` signature and fails the task with `TypeError: unexpected keyword argument 'auto_extract'` — shown in the UI as **Pipeline failed · 0/0**, "Scraping: Waiting", before any scraping happens. The same applies to the Extract/Preprocess batch buttons (new `auto_advance` kwarg). Fix = apply migration + restart worker.

## 4. Files touched (2026-07-26)

| File | Change |
| --- | --- |
| `enigmatrix-backend/app/m1/tasks/extract_gazette.py` | `auto_advance` param gates the preprocess enqueue |
| `enigmatrix-backend/app/m1/tasks/preprocess_gazette.py` | `auto_advance` param gates the classify enqueue |
| `enigmatrix-backend/app/m1/api/admin_pipeline.py` | new `POST /regulations/{id}/advance` + `/run-all`; batch `POST /batch/{stage}` (extract/preprocess/classify/run-all over a source+window) |
| `enigmatrix-backend/app/m1/schemas/pipeline.py` | `GazetteExtractionTriggerIn.manual` flag (ingest-only) |
| `enigmatrix-backend/scraper/pipelines.py` | gate auto-extract on `spider.auto_extract`; set `manual_hold` at ingest |
| `enigmatrix-backend/app/models/regulation.py` + migration `202607260002` | new `manual_hold` column |
| `enigmatrix-backend/app/m1/tasks/resume_pipeline.py` | exclude `manual_hold` rows from the recovery sweep |
| `enigmatrix-backend/app/m1/tasks/run_scraper.py` | `auto_extract` param → `-a auto_extract=0` |
| `enigmatrix-backend/app/m1/api/gazette_extraction.py` | forward `manual` → `auto_extract`; skip reconcile auto-extract in manual mode |
| `enigmatrix-frontend/lib/api/m1-pipeline.ts` | `advanceStage` / `runAllStages` / `batchStage` clients + types |
| `enigmatrix-frontend/components/m1/pipeline/stage-stepper.tsx` | new animated per-regulation stepping control |
| `enigmatrix-frontend/components/m1/extraction/batch-stage-control.tsx` | new run-level batch stepping control |
| `enigmatrix-frontend/app/(admin)/admin/m1/pipeline/trace/[regulationId]/page.tsx` | mounts `StageStepper` |
| `enigmatrix-frontend/app/(admin)/admin/m1/pipeline/sources/[sourceId]/extraction/runs/[taskId]/page.tsx` | mounts `BatchStageControl` |
| `enigmatrix-frontend/lib/api/m1-gazette-extraction.ts` | `manual` field on `GazetteExtractionTriggerIn` |
| `enigmatrix-frontend/app/(admin)/admin/m1/pipeline/sources/[sourceId]/extraction/page.tsx` | "Ingest only" toggle on the run form |
| `enigmatrix-backend/app/m1/models/dataset.py` + migration `202607260001` | `extraction_method` VARCHAR 20→64 |

_Last updated: 2026-07-26._
