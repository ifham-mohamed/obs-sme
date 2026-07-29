# 15 — M1 Folder Reference (per-folder build guides)

> Pick the folder you're working in; open the matching sub-folder guide; read what every file owns + why + how to build. Each guide cross-links into the deeper m1 doc that explains the spec.
> **See also:** [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) (the spec — *what* every file owns) · [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md) (sequenced *when* to build each step).
> **Audience:** the developer implementing M1. Status-aware: every guide marks files ✅ / 🟡 / 🔲 to match doc 13.

---

## Why this doc exists

Doc 13 specifies *every* file in the future M1 codebase. The 53 m1 docs explain the *why* + the *spec* for each major piece. But a new contributor opening doc 13's tree has no entry point for "I'm going to start by writing `ml/m1/extraction/pdf_classifier.py` — show me how." This reference closes that gap. Each sub-folder guide collects every file in that folder into one table — owner, status, primary doc, 1-liner on how to build — plus a "How to start building" section that sequences the work inside that folder.

The real repo roots (2026-07-24) — the guides use the short names `ml/`, `backend/`, `scraper/`, but the actual folders are the `enigmatrix-*` ones; the scraper lives under the backend:

```
xyz/
├── enigmatrix-ml/        → 15_M1_Folder_Reference.md   (extraction, preprocessing, evaluation, model, data/samplers)
├── enigmatrix-backend/   → 15_M1_Folder_Reference.md   (also hosts the Scrapy scraper → 15_M1_3)
├── research/             → 15_M1_Folder_Reference.md   (labelling data + notebooks)
├── mydata/               → live Label Studio instance (see 15_M1_4 + PHASE3_ANNOTATION_RUNBOOK.md)
├── data/                 → Phase-2 extraction golden set + eval (data/golden, data/eval)
├── scripts/              → sample_for_labeling.py, score_calibration.py, run_baseline_measurement.py, …
├── storage/             → 15_M1_Folder_Reference.md   (model artifacts, e.g. storage/models/m1/baseline/lid.176.bin)
└── enigmatrix-docs/      → 15_M1_Folder_Reference.md
```

---

## Index

| Guide | Folder it covers | File count (approx) | Status snapshot |
|---|---|---|---|
| [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) | `enigmatrix-ml/` (extraction, preprocessing, evaluation, model, `data/samplers`, tests) | ~100 files | ✅ Extraction + preprocessing + evaluation + model + sampler shipped; augmentation/summarisation deferred |
| [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) | `enigmatrix-backend/app/` (API routes, services, Celery tasks, models, schemas, migrations, scripts, middleware) | ~40 files | 🟡 Admin-CRUD + audit-log + Phase-2 ingest/extract pipeline shipped; alerts/schedulers deferred |
| [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) | Scrapy project (under `enigmatrix-backend/`) — settings, pipelines, spiders | ~5 files | ✅ Phase-2 spiders shipped (gazette + weekly + acts + bills) |
| [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) | `research/` (labeling data + config + calibration + runbook; notebooks/figures) | ~10 files | 🟡 Labelling surface shipped (config, calibration, batch_01, runbook); notebooks deferred |
| [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) | `storage/` (raw PDFs, OCR cache, inference cache, model artifacts) | ~5 directories | 🟡 Conventions documented; `storage/models/m1/baseline/lid.176.bin` present |
| [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) | `enigmatrix-docs/m1/` (the docs set) | 61 files | ✅ Shipped — the docs themselves |

---

## How each guide is structured

All 6 sub-folder guides follow the same locked skeleton (mirrors the precedent from the previous m1 companion passes):

1. **Purpose.** What the folder owns in the M1 pipeline; what stage(s) it serves.
2. **Files in this folder.** Table per file: owner / status / primary doc link / 1-liner on how to build.
3. **How to start building.** Concrete sequenced first-tasks per file. References the linked detail doc for the *why* + the spec — this section only sequences the work.
4. **Dependencies.** Which other folders / files must exist before this one builds; cross-links to other 15_M1_X guides.
5. **Tests & acceptance criteria.** Per file or per folder: unit / integration / acceptance metric. Usually the existing doc's "Validation" section quoted + cross-linked.
6. **Cross-references.** Doc 13 (folder map) + Roadmap (16_M1_*) + relevant detail docs + BUILD phase.

The skeleton is identical across the 6 guides so a developer learns once + skips between folders.

---

## How to start (the 30-second start-here)

1. **Don't know where to begin?** Open [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md). The roadmap is phase-by-phase; it tells you the first concrete task.
2. **Already know which folder you're building in?** Open the matching guide above. Find the file you're touching in the "Files in this folder" table. Click the primary-doc link for the spec.
3. **Need the bigger picture?** Open [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) for the full tree + stage-A-to-G implementation flow.
4. **Need to add a new module (M2/M3/M4)?** [13_M1_Folder_Structure §5 (per-module template)](13_M1_Folder_Structure_and_Implementation_Flow.md) tells you how to clone M1's tree.

## Conventions used in the guides

- **Status badges** (per file, in each table): ✅ Shipped (works in production today) · 🟡 Partial (exists but incomplete) · 🔲 Deferred (file doesn't exist yet; will land in a future BUILD).
- **Owner column** describes *what state or behaviour* the file controls — one line, no jargon.
- **"How to build" column** is ≤ 1 sentence. Anything longer means the underlying detail doc is the right place — the guide just sequences + links, doesn't duplicate.
- **Primary doc column** links to ONE doc per file (the canonical reference). Secondary references go in the "Cross-references" section at the bottom of each guide.

## Cross-references

- [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) — the folder-map spec
- [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md) — sequenced "start here" guide
- [README.md](README.md) — full m1 doc index (61 files)
- [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) — frontend tracking workflow surfaces (the *what users do*, this folder spec is the *what code lives where*)


# 15_M1_1 — `enigmatrix-ml/` Folder Build Guide

> Companion to [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) — build guide for the ML slice of the M1 tree.
> **Repo note (2026-07-24):** the real folder is **`enigmatrix-ml/`** (not `ml/`). Much of it is now **shipped**, not deferred: the full `m1/extraction/` chain (PDF classify → PyMuPDF/pdfplumber/pypdfium2/Tesseract/Surya page engines → Wijesekara + font-aware conversion → segmenter → language detection), `m1/preprocessing/` (cleaning, metadata, chunking), the `m1/evaluation/` extraction-metrics package, `m1/model/` (labels, architecture, `train_xlmr`, eval, baselines, `export_onnx`, inference, promotion), and `m1/data/samplers.py`. The idealised names below (`shared/`, `model/training.py`, `model/calibration.py`) map to real files noted inline.
> **Implementation status snapshot:** ✅ extraction + preprocessing + evaluation + model scaffolds + sampler shipped · 🟡 model training/ONNX being validated · 🔲 `data/sources.py` / `data/loaders.py` / `data/augmentation.py` / `summarization/` deferred.

## Purpose

`enigmatrix-ml/` is the ML monorepo — everything that trains, evaluates, or runs the gazette classifier, plus the Phase-2 extraction chain and the Phase-2 extraction-quality **evaluation** package. It owns Stages B (extraction), C (preprocessing), D (classification + inference), and E (summarisation). Each module is isolated: `m1/` never imports sibling-module code — shared helpers stay local. **Labelling entry point:** `m1/data/samplers.py` (called by `xyz/scripts/sample_for_labeling.py`).

## Files in this folder

### `ml/shared/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `shared/embeddings.py` | `multilingual-e5-base` wrapper | 🔲 | [03_M1_3 §3](03_M1_Data_Collection.md) | Implement `embed(texts) -> np.ndarray`; cache the model singleton |
| `shared/drift.py` | KL-divergence + Population Stability Index helpers | 🔲 | [12_M1_Monitoring_Maintenance.md §3.1](12_M1_Monitoring_Maintenance.md) | Two pure functions: `kl_divergence(p, q)` + `psi(prod, ref)`; pip-only deps |
| `shared/reproducibility.py` | `hash_dataset()` + `pin_environment()` | 🔲 | [06_M1_Training_Evaluation.md §reproducibility hash](06_M1_Training_Evaluation.md) | SHA-256 over the labeled parquet + `pip freeze` snapshot |

### `enigmatrix-ml/m1/data/` — the labelling sampler (Phase 3b)

| File | Owns | Status | Primary doc | Notes |
|---|---|---|---|---|
| `data/samplers.py` | Stratified + k-means-diversity + minority-class sampling for annotation batches | ✅ **Shipped** | [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) | Public API: `stratified_sample(df, small_cell_threshold, target_per_cell)`, `kmeans_diversity_sample(df, exclude_ids, n, k)`, `find_minority_candidates(df, exclude_ids, min_per_category)`, `sample_for_labeling(df, n_strat, n_kmeans, n_handpick, k, random_state)`. Constants: `TARGET_PER_CELL=20`, `OPTIMAL_K=20`. Carries `CATEGORIES_8` in sync with `model/labels.py`. Called by `xyz/scripts/sample_for_labeling.py`. |
| `data/sources.py` | 15-source registry (matches `m1_sources` table) | 🔲 Deferred | [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) | Hard-code the 15 sources as `dict[str, Source]`; the registry seeds the DB table |
| `data/loaders.py` | Async DB → labeled-set iterator | 🔲 Deferred | [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) | `async def load_labeled_set(split) -> AsyncIterator[Sample]` (in practice `scripts/sample_for_labeling.py::_load_from_db` currently fills this role) |
| `data/augmentation.py` | Back-translation + paraphrase + Sinhala morph rules | 🔲 Deferred | [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) | Cap at 5× per source doc; diversity-validate via embedding cosine |

> **Labelling data + Label Studio** live under `xyz/research/data/` and `xyz/mydata/`, not in `enigmatrix-ml/` — see [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) and `research/data/PHASE3_ANNOTATION_RUNBOOK.md`. The `model/labels.py` module here is the single source of truth for the 8 domains + 3 sectors that the Label Studio config mirrors.

### `enigmatrix-ml/m1/evaluation/` — Phase-2 extraction-quality metrics (shipped, not in the original tree)

| File | Owns | Status | Notes |
|---|---|---|---|
| `evaluation/field_metrics.py`, `completeness.py`, `aggregates.py`, `strata.py`, `raw_text.py`, `date_scope.py`, `xlsx_reader.py`, `metrics/{strings,semantic,dates,categorical,numeric,text_summary}.py` | Scores legacy-extraction output against the `data/golden/` ground-truth (the `structured_v1.xlsx` 21-field set); produces `data/eval/baseline_v0.json` | ✅ Shipped | Driven by `xyz/scripts/run_baseline_measurement.py`; see [15_M1_4](15_M1_Folder_Reference.md) + `data/golden/README.md`. This package did not exist in doc 13's original tree. |

### `ml/m1/extraction/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `extraction/pdf_classifier.py` | `classify_pdf(path) -> 'text'|'hybrid'|'scanned'` | 🔲 | [03_M1_Data_Collection.md](03_M1_Data_Collection.md) | Thresholds `text > 200, scanned < 30` chars/page from env vars |
| `extraction/text_extractors.py` | PyMuPDF → pdfplumber → Tesseract chain | 🔲 | [03_M1_Data_Collection.md](03_M1_Data_Collection.md) | Fallback chain; each tier needs ≥ 100 chars to win |
| `extraction/ocr.py` | Tesseract 5.3.x + Wijesekara conversion | 🔲 | [10_M1_Sinhala_Tamil_NLP.md](10_M1_Sinhala_Tamil_NLP.md) | `--oem 1 --psm 6 --lang eng+sin+tam`; Wijesekara via greedy longest-match table |
| `extraction/language_detection.py` | fastText `lid.176.bin` (500-char window, top-3) | 🔲 | [10_M1_Sinhala_Tamil_NLP.md](10_M1_Sinhala_Tamil_NLP.md) | Load model once; `predict(text[:500], k=3)`; return top-1 or "mixed" |

### `ml/m1/preprocessing/`

| File                                  | Owns                                                   | Status | Primary doc                                                                        | How to build (1-liner)                                                              |
| ------------------------------------- | ------------------------------------------------------ | ------ | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `preprocessing/cleaning.py`           | 8 noise classes + NFKD                                 | 🔲     | [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md)               | Fixed-order regex chain; idempotent — `clean(clean(x)) == clean(x)`                 |
| `preprocessing/metadata_extractor.py` | Gazette#, effective date, multi-penalty, principal act | 🔲     | [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md) | `re.finditer` for multi-penalty; output stored in `m1_regulation_penalties`         |
| `preprocessing/chunking.py`           | §-aware → 512-token sliding window (stride 64)         | 🔲     | [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md)             | Detect sections via `NOTICE_BOUNDARY_RE`; emit `Chunk[]`; classifier consumes `[0]` |
| `preprocessing/tokenization.py`       | XLM-R SentencePiece wrapper                            | 🔲     | [05_M1_Model_Architecture.md §4.2](05_M1_Model_Architecture.md)                    | Wrap `AutoTokenizer.from_pretrained('facebook/xlm-roberta-base')`                   |

### `ml/m1/model/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `model/architecture.py` | `GazetteClassifier` (XLM-R + LoRA + dual head) | 🔲 | [05_M1_Model_Architecture.md §4](05_M1_Model_Architecture.md) | `nn.Module` with PEFT LoRA wrap + 2 classification heads |
| `model/training.py` | 3-seed loop, AdamW, FP16, early-stop | 🔲 | [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) | Differential LRs (LoRA 2e-4, heads 2e-5); 10-epoch cap |
| `model/evaluation.py` | macro-F1, ECE, slice analyses | 🔲 | [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) | 4 standard slices + 2 extended; outputs `EvaluationReport` |
| `model/inference.py` | ONNX Runtime session + Redis cache | 🔲 | [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md) | Cache key = `SHA256(text + gazette# + date + model_version)` |
| `model/calibration.py` | Temperature scaling | 🔲 | [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md) | Fit `T` on val set; apply at inference |

### `ml/m1/summarization/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `summarization/marianmt.py` | MarianMT EN→SI/TA + EN→EN summary | 🔲 | [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md) | Per-chunk summarise; concat to ≤ 600 chars total |

### `ml/m1/schema/` + `ml/m1/utils/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `schema/pydantic_models.py` | `PreprocessedGazette`, `PredictionOut`, etc. | 🔲 | [04_M1_Preprocessing_Pipeline.md §3.5](04_M1_Preprocessing_Pipeline.md) | Mirror the dataclass shape from doc 04; immutable + JSON-serializable |
| `schema/manifest.py` | Dataset `manifest.yaml` schema | 🔲 | [06_M1_Training_Evaluation.md §reproducibility hash](06_M1_Training_Evaluation.md) | Validates `model_registry.json` shape |
| `utils/constants.py` | 8 domain codes, 3 sector codes | 🔲 | [09_M1_Annotation_Guidelines.md §2 + §3](09_M1_Annotation_Guidelines.md) | Two `Literal`-style enums; single source of truth |
| `utils/logging.py` | Structured JSON logging | 🔲 | — | `structlog` config; per-task `request_id` propagation |
| `utils/validation.py` | Data-quality assertions | 🔲 | [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) | Functions consumed by Pydantic validators + nightly health checks |

### `ml/tests/m1/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `tests/m1/extraction/test_pdf_classifier.py` | Fixture PDFs × the 3-tier classifier | 🔲 | [03_M1_1 §validation](03_M1_Data_Collection.md) | 50-doc audit set; ≥ 95% correct classification |
| `tests/m1/preprocessing/test_cleaning.py` | Per-noise-class round-trip tests | 🔲 | [04_M1_1 §validation](04_M1_Preprocessing_Pipeline.md) | 8 noise classes × 2 cases each = 16 unit tests minimum |
| `tests/m1/model/test_inference.py` | ONNX output ≈ PyTorch output (1e-4) | 🔲 | [07_M1_1 §validation](07_M1_Deployment_Integration.md) | Smoke test on a 50-doc held-out set |
| `tests/m1/fixtures/sample_gazettes/` | Anonymised demo PDFs for tests | 🔲 | — | Use the 5 seeded demo regulations as fixture PDFs |

## How to start building

Follow the roadmap's [Phase 2 + Phase 3 ordering](16_M1_Development_Roadmap.md). The fastest entry point in `ml/`:

1. **Set up the package skeleton.** `ml/__init__.py`, `ml/m1/__init__.py`, etc. — empty `__init__.py` files; the imports already work.
2. **Start with `ml/m1/extraction/pdf_classifier.py`.** It has zero dependencies on other `ml/` files; the only external deps are `pymupdf` + the `M1_PDF_TEXT_THRESHOLD` / `M1_PDF_SCANNED_THRESHOLD` env vars. Tests live at `tests/m1/extraction/test_pdf_classifier.py` — TDD pattern.
3. **Then `text_extractors.py` + `ocr.py`.** These complete Stage B; without them the Celery `extract_gazette` task can't advance a row past `status='ingested'`.
4. **Then `preprocessing/cleaning.py` + `metadata_extractor.py` + `chunking.py`.** Stage C — feeds Stage D's classifier input.
5. **Labeling loop — `data/samplers.py` is ✅ shipped.** It powers Phase 3b via `xyz/scripts/sample_for_labeling.py`. Remaining `data/` work is `sources.py` + `loaders.py` (DB registry + labeled-set iterator) + `augmentation.py` (Phase 3d training-data augmentation). Operate the labelling loop from `research/data/PHASE3_ANNOTATION_RUNBOOK.md`.
6. **Then `model/*` files** in order: architecture → training → evaluation → inference. Each depends on the previous.
7. **Finally `summarization/marianmt.py`.** Independent of the classifier; can be built in parallel with `model/*` once Stage D has output to summarise.

Cross-module helpers (`ml/shared/`) build alongside whatever needs them — embeddings first (used by secondary-source matching in Phase 4), then drift (Phase 4 monitoring), then reproducibility (Phase 3).

## Dependencies

- **`backend/` Celery task layer** ([15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)) — every `ml/m1/` module is called *from* a Celery task in `backend/app/tasks/m1/`. The boundary is one-way: `ml/m1/` never imports from `backend/`.
- **`scraper/` Stage A** ([15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)) — provides the PDFs that `ml/m1/extraction/` consumes.
- **`storage/` artifacts** ([15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)) — raw PDFs, OCR cache, model files; `ml/m1/` reads + writes here.
- **Postgres** — `data/loaders.py` reads the labeled set; the training script reads the DB directly. No ORM dependency — uses `asyncpg` or `psycopg` raw.

## Tests & acceptance criteria

- **Coverage target.** Every public function in `ml/m1/` has ≥ 1 unit test; integration tests cover Stage B → C → D end-to-end on fixture PDFs.
- **Per-stage acceptance.** Stage B: extraction success rate ≥ 95 % on the audit set; OCR CER ≤ 10 % on Sinhala/Tamil. Stage D: macro-F1 ≥ 0.92 with 3-seed stability < 0.02 std. ONNX export: max-abs-diff vs PyTorch < 1e-4.
- **Validation docs.** Per-file specs reference the "Validation & acceptance criteria" section of the linked detail doc.

## Cross-references

- Folder map spec: [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md)
- Roadmap: [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md)
- Phase docs: BUILD_07 (Stage A–F backend), BUILD_11 (ML training)
- Sibling folders: [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md), [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md), [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)


# 15_M1_2 — Backend Folder Build Guide (`enigmatrix-backend/`)

> Companion to [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) — build guide for the backend slice of the M1 tree.
> **Repo note (2026-07-24):** the real folder is **`enigmatrix-backend/`**, and M1 code is a **self-contained package at `app/m1/`** (`api/`, `models/`, `schemas/`, `services/`, `tasks/`) — moved there from the flat `app/{services,models,...}` layout the old guide assumed. It is now **largely shipped**: Phase-2 ingest/extract/preprocess, the extraction dataset/measurement admin surface, alerts, drift, retraining, propagation matching, and pipeline validation all exist. Deferred: the live ONNX classify path (waits on the trained model) + some Stage-E summarisation.
> **Implementation status snapshot:** ✅ ~70 M1 files under `app/m1/` shipped (api/models/schemas/services/tasks) + Scrapy Stage A + seeds + audit + migrations · 🟡 classify/summarise tasks wired but pending the trained model · 🔲 MarianMT summarisation.

## Purpose

`enigmatrix-backend/` is the FastAPI + Celery service that fronts M1 — the admin + SME API, the extraction/measurement admin tooling, the Celery task layer that drives Stages A–F (calling `enigmatrix-ml/m1/` for the algorithms), and the Postgres schema. M1 lives in its own `app/m1/` package so it never tangles with M2/M3 code; cross-module concerns (auth, surveys, audit) stay in the top-level `app/` dirs.

## Files in this folder

### `app/m1/api/` — M1 REST + WebSocket routers (all ✅ shipped)

| File | Owns |
|---|---|
| `api/regulations.py` | Admin + SME regulation CRUD / list / detail |
| `api/admin_pipeline.py` | Pipeline-state admin surface (A1) |
| `api/extractions.py` + `api/extraction_ws.py` | Extraction runs + live WebSocket feed |
| `api/gazette_extraction.py` | Per-gazette extraction trigger + status |
| `api/datasets.py` | Golden/dataset upload + versioning |
| `api/measurements.py` + `api/completeness.py` | Baseline measurement + completeness reports |
| `api/alerts.py` | Alert history / dispatch surface |

> Cross-module routers stay in `app/api/v1/` (`regulations.py`, `verify.py`, `qa.py`, `risk.py`, `admin_*`, `survey_*`). Router assembly: `app/api/v1/router_slim.py` + `app/main.py`.

### `app/m1/services/` — business logic (✅ shipped; ~30 modules)

| Area | Modules |
|---|---|
| Regulation + sources | `regulation_service`, `source_catalogue` / `sources_catalogue`, `secondary_sources`, `embeddings` |
| Extraction ops | `pipeline_service`, `extraction_run_status`, `extraction_run_archive`, `extraction_cancel`, `extraction_live_feed`, `pdf_resolver`, `metadata_confidence`, `profile_service` |
| Datasets + measurement | `dataset_service`, `dataset_upload`, `xlsx_parser`, `measurement_report`, `measurement_aggregates`, `completeness_check`, `overlap_service`, `snapshot_service`, `storage_projection` |
| Classify + drift + alerts | `classifier_service`, `drift`, `alert_service`, `alert_content`, `alert_providers` |
| Propagation (Phase 4) | `propagation_matching`, `propagation_service` |

> Shared audit writes live at `app/services/` (`audit_service`) + the passive `app/middleware/` audit layer.

### `app/m1/tasks/` — Celery task tree (✅ shipped; classify/summarise pending the model)

| Stage | Tasks |
|---|---|
| A — Ingest | `run_scraper`, `gazette_scraper`, `reconcile_raw`, `migrate_raw_layout` |
| B/C — Extract + preprocess | `run_extraction`, `extract_gazette`, `preprocess_gazette`, `quality_probe`, `prune_extraction_runs` |
| D — Classify | `classify_gazette` (🟡 wired; live path waits on the trained ONNX model) |
| F — Alerts | `alert_dispatch` |
| Secondary (Phase 4) | `portal_watcher`, `rss_watcher`, `source_health` |
| Measurement + governance | `run_measurement`, `validate_dataset_version`, `validate_pipeline`, `analytics`, `retention`, `retire_old_versions` |
| Retraining | `retraining` |

> Backend-side extraction helpers also live at `app/extraction/` (`pdf_classifier.py`, `text_extractors.py`, `pdf_metadata.py`); the heavier algorithms are in `enigmatrix-ml/m1/`.

### `app/m1/models/` + `app/m1/schemas/` (✅ shipped)

| Layer | Modules |
|---|---|
| `m1/models/` | `regulation_penalty`, `sub_document`, `gazette_item`, `dataset`, `propagation_event`, `propagation_review`, `alert`, `retraining_run`, `extraction_profile`, `extraction_run`, `measurement`, `quality_probe`, `pipeline_audit`, `source` |
| top-level `app/models/` | `regulation` (`M1Regulation`), `regulatory_domain`, `audit_log` |
| `m1/schemas/` | `regulation_penalty`, `sub_document`, `dataset`, `pipeline`, `measurement`, `extraction`, `alert` |

### Migrations, seeds, config

| Path | Owns | Status |
|---|---|---|
| `enigmatrix-backend/alembic/versions/*_m1_*.py` | Alembic migrations (e.g. `202607230001_m1_schema_validation_and_governance`, `202607210005_classification_source`) | ✅ Shipped |
| `app/scripts/seed_*.py` | `seed_lookups` (8 domains + 3 sectors), `seed_regulations`, `seed_m1_worked_examples`, `seed_m23_questions`, `seed_phase4`, `seed_demo_responses`, `seed_dev` | ✅ Shipped |
| `app/settings.py` | Pydantic settings / feature flags (env-driven) | ✅ Shipped |
| `app/middleware/` + `app/services/audit_service` | Passive HTTP audit logging | ✅ Shipped |

## How to start building

Most of this is **already built** — the sequence below is retained as the dependency order for the remaining work (live classify path + summarisation) and as an orientation for new contributors. The M1 package is at `app/m1/`; run the API with `make dev` / `uvicorn app.main:app` and Celery with the project's worker config.

1. **DB schema — ✅ shipped.** The `m1_*` migrations live under `enigmatrix-backend/alembic/versions/`; `alembic upgrade head` applies them. ORM under `app/m1/models/` + `app/models/regulation.py`. Seeds via `app/scripts/seed_lookups.py` (8 domains + 3 sectors) then `seed_regulations.py` / `seed_m1_worked_examples.py`.
2. **`config/feature_flags.py`.** Stub it with env-var-backed flags. Every Celery task entry-point reads from here. Build it before the tasks so they can gate themselves cleanly.
3. **`tasks/m1/__init__.py` + Celery routing.** Set up the task module + the queue names (`m1-extract`, `m1-classify`, `m1-summarise`, `m1-alert`) before any individual task; Celery Beat schedule lives in `backend/app/celery_config.py`.
4. **`tasks/m1/extract_gazette.py`.** First task — wraps Stage B from `ml/m1/extraction/`. Status transition `ingested → extracted`. Once this works, the rest of the chain follows the same pattern.
5. **`tasks/m1/classify_gazette.py` → `summarise_gazette.py` → `alert_dispatch.py`.** Chain order. Each fires on the previous's success.
6. **`tasks/m1/portal_watcher.py` + `rss_watcher.py`.** Phase 4 — independent of the main chain. Both write `m1_propagation_events`.
7. **`tasks/m1/analytics.py`.** Phase 4 — nightly batch; depends on all prior tasks having populated the rows it aggregates.
8. **API endpoint extensions.** As each Celery task lands, add the matching admin endpoint to `api/v1/m1_regulations.py` (e.g. `POST /regulations/{id}/classify` triggers `classify_gazette.delay(id)`).
9. **Scripts (`m1_backfill_classifications.py`, `m1_validate_pipeline.py`).** Last — they consume everything that came before.

## Dependencies

- **`enigmatrix-ml/m1/` modules** ([15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)) — tasks import the extraction/preprocessing/model algorithms from the ML package. The boundary is strict: backend tasks own *orchestration*, not *algorithms*.
- **Postgres** — schema + connection pool; the `m1_*` tables are the persistent state machine.
- **Redis** — Celery broker + inference cache. Required for any Celery task to run.
- **`enigmatrix-backend/scraper/`** ([15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)) — Stage A produces PDFs that Stage B consumes.
- **`storage/`** ([15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)) — raw PDFs, OCR cache, ONNX models. Tasks read + write here.

## Tests & acceptance criteria

- **Schema migrations.** `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` succeeds on a fresh DB. Every migration is reversible.
- **Celery task tests.** Each task in `tests/m1/test_*.py` runs against a fixture row + asserts the post-state. Tasks must be idempotent (re-running advances state correctly without duplicates).
- **API integration.** `tests/m1/integration/` covers every endpoint with each role's expected status code (per the permission matrix in [11_M1_1](11_M1_API_Reference.md)).
- **Audit-log invariants.** Every state-changing API call writes one `audit_log` row; tests assert the row count delta.
- **Pre-deploy gate.** `make test` + `alembic upgrade head` both pass before any task is enabled in production (`M1_*_ENABLED=true`).

## Cross-references

- Folder map spec: [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md)
- Roadmap: [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md) (Phases 2 + 4 are heaviest here)
- API spec: [11_M1_API_Reference.md](11_M1_API_Reference.md) + [11_M1_1](11_M1_API_Reference.md) + [11_M1_2](11_M1_API_Reference.md)
- Schema spec: [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) + [02_M1_2](02_M1_Data_Requirements.md)
- Monitoring: [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md) + [12_M1_1](12_M1_Monitoring_Maintenance.md)
- Sibling folders: [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md), [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md), [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)


# 15_M1_3 — Scraper Folder Build Guide (`enigmatrix-backend/scraper/`)

> Companion to [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) — build guide for the Scrapy slice of the M1 tree.
> **Repo note (2026-07-24):** the Scrapy project is **shipped** and lives at **`enigmatrix-backend/scraper/`** (project root `enigmatrix-backend/scrapy.cfg`), *not* a top-level `scraper/`. Secondary-source watchers were **not** built as Scrapy spiders — they're Celery tasks under `enigmatrix-backend/app/m1/tasks/` (`portal_watcher.py`, `rss_watcher.py`) backed by `services/secondary_sources.py`.
> **Implementation status snapshot:** ✅ Shipped — Stage A spiders (gazette + weekly + acts + bills) + settings + pipelines. Phase-2 ingest is live.

## Purpose

The Scrapy project owns **Stage A** (Ingestion) — discovers new gazettes/acts/bills on `gazette.lk` + `documents.gov.lk`, downloads PDFs, deduplicates against the DB, and hands off to Stage B. It sits *inside* `enigmatrix-backend/` (shares the backend venv + DB session) and is driven in production by the `run_scraper` / `gazette_scraper` Celery tasks.

## Files in this folder

| File | Owns | Status | Primary doc | Notes |
|---|---|---|---|---|
| `scraper/settings.py` | Scrapy global config — autothrottle, retry, user-agent, ROBOTSTXT_OBEY | ✅ Shipped | [03_M1_Data_Collection.md §1.3](03_M1_Data_Collection.md) | `DOWNLOAD_DELAY` + AUTOTHROTTLE + retry codes |
| `scraper/pipelines.py` | PDF → `storage/m1/raw/` write pipeline + dedup + row insert | ✅ Shipped | [03_M1_Data_Collection.md §1.2](03_M1_Data_Collection.md) | SHA-256 the bytes; skip duplicate `gazette_number` |
| `scraper/spiders/_base.py` | Shared base spider (common parsing/item shape) | ✅ Shipped | [03_M1_Data_Collection.md](03_M1_Data_Collection.md) | The 4 concrete spiders subclass this |
| `scraper/spiders/gazette_spider.py` | Extraordinary-gazette spider (`gazette.lk` / `documents.gov.lk`) | ✅ Shipped | [03_M1_Data_Collection.md §1.2 + §1.3](03_M1_Data_Collection.md) | Yields `{url, gazette_number, gazette_date, pdf_url}` |
| `scraper/spiders/weekly_gazette_spider.py` | Weekly-gazette spider | ✅ Shipped | [03_M1_Data_Collection.md](03_M1_Data_Collection.md) | Weekly issue cadence |
| `scraper/spiders/acts_spider.py` | Acts spider | ✅ Shipped | [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) | Parliament acts |
| `scraper/spiders/bills_spider.py` | Bills spider | ✅ Shipped | [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) | Draft bills |
| _Secondary sources_ (IRD/EPF/eROC/SLSI/CBSL + news RSS) | Not Scrapy spiders — Celery tasks | ✅ Shipped elsewhere | [03_M1_Data_Collection.md](03_M1_Data_Collection.md) | `app/m1/tasks/portal_watcher.py` + `rss_watcher.py` + `services/secondary_sources.py` — see [15_M1_2](15_M1_Folder_Reference.md) |

## How to start building

This folder is **already built** (Phase 2, roadmap [Step 2a](16_M1_Development_Roadmap.md)). The notes below are how to *run + extend* it; the build history is retained for context.

> **Run it (local dev):** from `enigmatrix-backend/` (where `scrapy.cfg` lives): `scrapy list` shows `gazette_spider`, `weekly_gazette_spider`, `acts_spider`, `bills_spider`. `scrapy crawl gazette_spider -s CLOSESPIDER_ITEMCOUNT=5` fetches 5 issues into `storage/m1/raw/` + inserts `status='ingested'` rows. Production runs the same spiders inside the `run_scraper` / `gazette_scraper` Celery tasks.

1. **Project is scaffolded.** `enigmatrix-backend/scrapy.cfg` + `scraper/settings.py` are in place; there is no `items.py`/`middlewares.py` (ad-hoc item dicts + default middlewares).
2. **Write `scraper/settings.py`.** Copy the `custom_settings` dict from [03_M1_Data_Collection.md §1.3](03_M1_Data_Collection.md). Critical settings: `DOWNLOAD_DELAY=2` + `AUTOTHROTTLE_ENABLED=True` + `RETRY_HTTP_CODES=[500, 503, 429]` + `USER_AGENT='EnigmatrixResearchBot/1.0 (+https://enigmatrix.lk/bot)'`.
3. **Write `scraper/pipelines.py`.** `FilesPipeline` subclass that:
   - downloads each PDF into `storage/m1/raw/{gazette_number}.pdf`
   - SHA-256 hashes the bytes (stored in `m1_regulations.pdf_hash`)
   - skips if the `gazette_number` already exists in the DB
4. **Write `scraper/spiders/gazette_spider.py`.** Two `start_urls` (gazette.lk + documents.gov.lk). Parse the pagination + emit per-issue items. Use `scrapy crawl gazette_spider` against a fixture date first to validate; only enable in Celery once stable.
5. **Test locally.** `scrapy crawl gazette_spider --limit 5` produces 5 PDFs in `storage/m1/raw/` + 5 rows in `m1_regulations` (`status='ingested'`).
6. **Secondary sources are NOT Scrapy spiders.** IRD/EPF/ETF/eROC/SLSI/CBSL + news RSS diffusion tracking is handled by `app/m1/tasks/portal_watcher.py` + `rss_watcher.py` (+ `services/secondary_sources.py` + `propagation_matching.py`), which write `m1_propagation_events`. See [15_M1_2](15_M1_Folder_Reference.md).

The Scrapy CLI works standalone for local testing. Production runs the spiders *inside* the `run_scraper` / `gazette_scraper` Celery tasks (see [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)) — the cooperative retry boundary between Scrapy and Celery is documented in [03_M1_Data_Collection.md §6.1](03_M1_Data_Collection.md). Integration test: `enigmatrix-backend/app/tests/integration/test_gazette_spider.py`.

## Dependencies

- **`storage/m1/raw/`** ([15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)) — destination for downloaded PDFs. Must be writable.
- **Postgres `m1_regulations` table** — dedup check + new-row insert. ORM in `enigmatrix-backend/app/m1/models/` ([15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)).
- **`enigmatrix-backend/app/m1/tasks/run_scraper.py` + `gazette_scraper.py`** ([15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)) — the Celery wrappers that trigger Scrapy on a schedule. Scrapy CLI handles local dev; the wrappers handle production.
- **Wayback Machine + admin URL override table** — fallback when a source URL changes (see [02_M1_1 §source-specific fallbacks](02_M1_Data_Requirements.md)).

## Tests & acceptance criteria

- **Discovery completeness.** Quarterly audit: hand-identify 50 known gazettes from `gazette.lk` → confirm Scrapy picks all 50 up; ≥ 98 % recall.
- **Download integrity.** SHA-256 hash check on every download; 0 % corruption.
- **De-duplication.** Running the spider twice on the same date produces zero duplicate rows in `m1_regulations` (enforced by the `UNIQUE` constraint on `gazette_number`).
- **Rate-limit politeness.** Honour `DOWNLOAD_DELAY=2` + `AUTOTHROTTLE_TARGET_CONCURRENCY=2`. Monitor 429 rate from each source; alert if > 1 % of requests get 429.
- **Spider health.** `m1_sources.last_check_status` tracks consecutive-failure count per source; alert if any source fails ≥ 3 consecutive checks.

## Cross-references

- Folder map spec: [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md)
- Roadmap: [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md) §Phase 2a
- Detail docs: [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md), [03_M1_Data_Collection.md](03_M1_Data_Collection.md), [03_M1_Data_Collection.md](03_M1_Data_Collection.md)
- Phase doc: BUILD_07 §Stage A (ingestion)
- Sibling folders: [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md), [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)


# 15_M1_4 — `research/` Folder Build Guide

> Companion to [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) — build guide for the `research/` slice of the M1 tree.
> **Repo note (2026-07-24):** the annotation surface is **live**. The labeling config, the 20-doc calibration set, `batch_01.csv` + provenance, and the Phase-3 runbook all exist under `research/data/`; a working Label Studio instance is initialised at `xyz/mydata/`. The Jupyter findings notebooks (F1–F6) are still to scaffold.
> **Implementation status snapshot:** ✅ 5 shipped (labeling config, calibration set, batch_01 + provenance, Phase-3 runbook) · 🟡 1 partial (pre-pilot data) · 🔲 ~6 deferred (findings notebooks + figures + `gold_standard.csv` + `test_split.parquet`).

## Purpose

`research/` is the analytical surface — Jupyter notebooks that produce the F1–F6 thesis findings, the labelled dataset that the classifier trains on, the figures the thesis ships. Unlike `ml/` (production code), this is the *researcher's surface*: it reads from production replicas, doesn't write back. Lives outside `backend/` + `ml/` because the lifecycle is different — notebooks are exploratory; they don't need to deploy.

## Files in this folder

### `research/notebooks/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `notebooks/findings_lag_analysis.ipynb` | F1–F5 lag distributions + statistical tests | 🔲 | [08_M1_Full_System_Architecture.md](08_M1_Full_System_Architecture.md) | Read replicas; median + bootstrap 95% CI + Mann-Whitney U / Kruskal-Wallis tests |
| `notebooks/findings_classifier_evaluation.ipynb` | Full classifier eval suite (slice analyses + confusion matrix) | 🔲 | [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) + [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) | Load `test_split.parquet` + ONNX model; reproduce eval per language / quarter / length |
| `notebooks/findings_alert_effectiveness.ipynb` | F6 — DiD analysis on subscribed vs non-subscribed SMEs | 🔲 | [08_M1_Full_System_Architecture.md §F6](08_M1_Full_System_Architecture.md) | DiD regression with sector + district fixed effects; parallel-trends robustness check |
| `notebooks/findings_secondary_diffusion.ipynb` | F4 — channel effectiveness ranking | 🔲 | [02_M1_Data_Requirements.md §3.3 (`v_m1_channel_effectiveness`)](02_M1_Data_Requirements.md) | Query the view; sort by median lag; produce the channel-effectiveness heatmap |

### `research/figures/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `figures/lag_distribution.png` | F1–F3 box plots + CDFs | 🔲 | [08_M1_1 §F1–F3](08_M1_Full_System_Architecture.md) | Generated by `findings_lag_analysis.ipynb` — commit the PNG |
| `figures/confusion_matrix.png` | 8×8 domain confusion matrix | 🔲 | [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) | Generated by `findings_classifier_evaluation.ipynb` |
| `figures/alert_effectiveness_timeseries.png` | F6 DiD pre/post intervention plot | 🔲 | [08_M1_1 §F6](08_M1_Full_System_Architecture.md) | Generated by `findings_alert_effectiveness.ipynb` |
| `figures/secondary_diffusion_heatmap.png` | F4 channel × sector lag heatmap | 🔲 | [08_M1_1 §F4](08_M1_Full_System_Architecture.md) | Generated by `findings_secondary_diffusion.ipynb` |

### `research/data/` — the annotation surface (mostly shipped)

> **Full operational runbook:** [`research/data/PHASE3_ANNOTATION_RUNBOOK.md`](../../../../Reasearch/xyz/research/data/PHASE3_ANNOTATION_RUNBOOK.md) — the step-by-step for sampling → Label Studio → calibration → IAA → export. The tables below are the file inventory; the runbook is the *how*.

| File | Owns | Status | Primary doc | How it's built |
|---|---|---|---|---|
| `data/label_studio_config.xml` | Labeling interface — 8-domain single-label + 3-sector multi-label + SME-relevance + confidence + notes | ✅ Shipped | [09_M1_Annotation_Guidelines.md §1.2](09_M1_Annotation_Guidelines.md) | Paste into Label Studio → Labeling Interface → Code; kept in sync with `enigmatrix-ml/m1/model/labels.py` |
| `data/calibration_set_v1.csv` | 20-doc calibration test with **locked** expert reference labels (`expert_change_category`, `expert_affected_sectors`) | ✅ Shipped | [09_M1_2 §Step 1](09_M1_Annotation_Guidelines.md) | Hand-picked by domain expert; `cal_001`–`cal_020`; spans 8 domains + EN/SI/TA + edge cases |
| `data/labeling/batch_01.csv` | First 200-doc annotation batch (150 stratified + 40 k-means + 10 hand-pick) | ✅ Shipped | [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) | Emitted by `scripts/sample_for_labeling.py` → imported into Label Studio |
| `data/labeling/batch_01_provenance.json` | Sampling provenance (seed, corpus size, language/year/type breakdowns) | ✅ Shipped | [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) | Auto-written alongside each `batch_NN.csv` |
| `data/PHASE3_ANNOTATION_RUNBOOK.md` | Operational runbook for the whole labelling loop | ✅ Shipped | [09_M1_2](09_M1_Annotation_Guidelines.md) | Living doc; describes data vs mydata, LS setup, calibration, IAA, export |
| `data/labeling/gold_standard.csv` | Final consensus labels (κ ≥ 0.75) | 🔲 Deferred | [09_M1_2 §Step 3](09_M1_Annotation_Guidelines.md) | Concat of all batches' resolved annotations; ≥ 800 rows, ≥ 50 per domain — needs the not-yet-built export/IAA reducer |
| `data/test_split.parquet` | Held-out test set (hash-pinned in `model_registry.json`) | 🔲 Deferred | [06_M1_Training_Evaluation.md §1.2](06_M1_Training_Evaluation.md) | Temporal split with 30-day minimum window; SHA-256 stored in registry |
| `data/prepilot_2025-09.csv` | 40-respondent informal SME scan (EN-only Google Forms export) | 🟡 Partial (already collected) | [01_M1_Research_Problem.md](01_M1_Research_Problem.md) | Already collected; redact PII before commit |

> **Where the live Label Studio instance lives:** `xyz/mydata/` (`label_studio.sqlite3` + `media/upload/1` = Batch project, `/2` = Calibration project + `.env`). Start it with `LABEL_STUDIO_BASE_DATA_DIR=C:\Reasearch\xyz\mydata`. This is **not** `research/data/` — `research/data/` holds the import *sources*; `mydata/` is Label Studio's own store of tasks + submitted annotations.
>
> **Supporting scripts (in `xyz/scripts/`):** `sample_for_labeling.py` (emits batches — ✅), `score_calibration.py` (scores a calibration export vs expert labels, Cohen's κ + per-sector κ — ✅). Still to build: an `annotations_to_dataframe.py` / `resolve_iaa.py` reducer that turns a Label Studio export into `gold_standard.csv`.

## How to start building

`research/` builds *behind* `ml/` + `backend/` — the notebooks need real data from the production replicas, and the labelling data comes out of Phase 3 of the roadmap.

> **Labelling (Phase 3a/3b) is already stood up** — steps 1–4 below are largely done. Follow [`PHASE3_ANNOTATION_RUNBOOK.md`](../../../../Reasearch/xyz/research/data/PHASE3_ANNOTATION_RUNBOOK.md) to operate it; the remaining research work is `gold_standard.csv` + the notebooks.

1. **Labeling interface — ✅ done.** `data/label_studio_config.xml` carries the 8-domain / 3-sector interface. Paste it into a Label Studio project's Code tab. Keep it in sync with `enigmatrix-ml/m1/model/labels.py`.
2. **Calibration set — ✅ done (Phase 3a).** The 20 expert-labelled docs are in `data/calibration_set_v1.csv`. Candidates label them in the "M1 Calibration Test v1" project; score with `scripts/score_calibration.py` (gate κ ≥ 0.80). See runbook §5–6.
3. **First labelling batch — ✅ done (Phase 3b).** `data/labeling/batch_01.csv` (200 docs) + `batch_01_provenance.json` are committed. Regenerate / add batches with `uv run python scripts/sample_for_labeling.py --batch N`. Versioned, append-only — the sampler refuses to overwrite an existing batch.
4. **Dual-annotate + IAA (Phase 3c) — in progress.** Two annotators per task; export Label Studio JSON; compute κ (reuse `score_calibration.py`'s helpers); resolve per 09 §4.3–4.4. Output → `data/labeling/gold_standard.csv` (≥ 800 rows, ≥ 50/domain). **Next script to build:** the export→`gold_standard.csv` reducer.
5. **`test_split.parquet` (Phase 3d).** Once the 800-label set exists, produce + SHA-256-hash-pin the held-out temporal split; the hash goes into `model_registry.json`.
6. **Notebook environment + scaffolds (Phase 5).** `requirements-research.txt` (`jupyterlab`, `pandas`, `scipy`, `matplotlib`, `pyarrow`) + a `.env.research` pointing at the read-only Postgres replica + ONNX model URL. Then scaffold `findings_classifier_evaluation.ipynb` first (Phase 3 output feeds it), then `findings_secondary_diffusion.ipynb`, then `findings_lag_analysis.ipynb` + `findings_alert_effectiveness.ipynb` (need SME survey data).
7. **Figures.** Each notebook writes to `figures/*.png` — commit the PNGs (small) so thesis reviewers can see the chart without re-running.
8. **Pre-registration.** Before unblinding the data, write `research/preregistration.md` listing the hypotheses + tests (the pattern is in [08_M1_1 §Validation](08_M1_Full_System_Architecture.md)).

The notebooks are the **thesis artifact** — they must re-run end-to-end against the production replica without errors. CI runs `nbconvert --execute` on each to catch drift.

## Dependencies

- **Postgres replica** — every notebook reads from a read-only replica. The notebooks must NOT write back (enforced by the replica's permissions).
- **`storage/models/m1/v*/`** ([15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)) — `findings_classifier_evaluation.ipynb` loads the ONNX model from here.
- **Label Studio** ([09_M1_Annotation_Guidelines.md](09_M1_Annotation_Guidelines.md)) — external tool; instance initialised at `xyz/mydata/`; `data/labeling/*.csv` is the import format, JSON export is the annotation output.
- **`enigmatrix-ml/m1/data/samplers.py`** ([15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)) — the sampler (`stratified_sample` + `kmeans_diversity_sample` + `find_minority_candidates` + `sample_for_labeling`) that `scripts/sample_for_labeling.py` calls to produce the batch CSVs.
- **SME survey backend** ([backend tasks/services](15_M1_Folder_Reference.md)) — populates `m1_sme_awareness_responses`, which `findings_lag_analysis.ipynb` reads.

## Tests & acceptance criteria

- **Notebook reproducibility.** Each notebook re-runs end-to-end against the production replica without errors. CI runs `jupyter nbconvert --execute` on every PR that touches `research/notebooks/`.
- **Figures byte-identical.** PNG outputs are deterministic — same data → same figure. CI snapshot test.
- **Statistical tests pre-registered.** Every finding (F1–F6) has a pre-registered test in `research/preregistration.md`; the notebook implements that exact test. Post-hoc deviations get a methodology footnote.
- **Sample-size disclaimers.** Any finding with N < 30 per slice is reported with "low confidence — N=X" in both notebook + thesis.
- **Per-finding DoD.** F1: median portal lag with 95% CI on ≥ 200 regulations. F2: same for news. F3: median SME lag urban vs rural with Mann-Whitney p-value, n ≥ 100. F4: channel ranking with ≥ 10 SMEs per sector. F5: Kruskal-Wallis on 3 language groups, n ≥ 30 each. F6: DiD with parallel-trends check.

## Cross-references

- Folder map spec: [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md)
- Roadmap: [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md) §Phase 3 (labelling) + §Phase 5 (notebooks)
- Findings methodology: [08_M1_Full_System_Architecture.md](08_M1_Full_System_Architecture.md)
- Annotation: [09_M1_Annotation_Guidelines.md](09_M1_Annotation_Guidelines.md) + [09_M1_2](09_M1_Annotation_Guidelines.md) + [09_M1_3](09_M1_Annotation_Guidelines.md)
- Evidence base: [01_M1_Research_Problem.md](01_M1_Research_Problem.md)
- Sibling folders: [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md), [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md), [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)


# 15_M1_5 — `storage/` Folder Build Guide

> Companion to [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) — build guide for the `storage/` slice of the M1 tree.
> **Repo note (2026-07-24):** `storage/` is mostly conventions still. What's actually present today is the fastText language-ID model at **`storage/models/m1/baseline/lid.176.bin`** (used by `enigmatrix-ml/m1/extraction/language_detection.py`, fetched via `enigmatrix-ml/scripts/download_lid_model.py`). Raw-PDF / OCR-cache dirs populate at runtime; the trained ONNX classifier lands once Phase-3 labelling → training completes.
> **Implementation status snapshot:** 🟡 Conventions documented; `models/m1/baseline/lid.176.bin` present; raw/OCR/inference caches + `models/m1/v*/` populate as Phase 2/3 run.

## Purpose

`storage/` is the on-disk artifact store — raw PDFs the scraper downloads, OCR caches, the inference cache mirror, and the versioned ONNX model files. Everything here is *operational state*: gitignored except for the `model_registry.json` manifests (small + version-controlled for reproducibility). On Fly.io, the production mount is a persistent volume; locally, it's the repo `storage/` directory.

## Files in this folder

### `storage/m1/`

| Path | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `m1/raw/` | Downloaded gazette PDFs, keyed by `gazette_number` | 🔲 | [03_M1_Data_Collection.md](03_M1_Data_Collection.md) + [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) | `scraper/pipelines.py` writes here; S3 lifecycle moves > 2y to Glacier |
| `m1/ocr_cache/` | Tesseract output keyed by `SHA-256(image_bytes)` | 🔲 | [03_M1_Data_Collection.md](03_M1_Data_Collection.md) | Idempotent — re-running OCR returns cached result; TTL 30 days |
| `m1/inference_cache/` | Redis dump (operational; not authoritative) | 🔲 | [07_M1_Deployment_Integration.md §3.2](07_M1_Deployment_Integration.md) | Local backup of the Redis cache for cold-start warming |

### `storage/models/m1/`

| Path | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `models/m1/v1.0/gazette_classifier.onnx` | Production FP32 ONNX model | 🔲 | [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md) | Produced by `ml/m1/model/export_onnx.py` |
| `models/m1/v1.0/gazette_classifier_int8.onnx` | INT8-quantized variant (2× speedup) | 🔲 | [07_M1_1 §INT8](07_M1_Deployment_Integration.md) | Produced by `quantize_onnx.py`; F1 within 1.5pp of FP32 |
| `models/m1/v1.0/adapter_model.bin` | LoRA adapter weights (for retraining) | 🔲 | [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) | PEFT's `save_pretrained()` output (~10MB; never overwrite) |
| `models/m1/v1.0/tokenizer/` | XLM-R SentencePiece tokenizer (frozen) | 🔲 | [05_M1_Model_Architecture.md §4.2](05_M1_Model_Architecture.md) | Copied from `facebook/xlm-roberta-base` at training time |
| `models/m1/v1.0/model_registry.json` | Reproducibility fingerprint | 🔲 | [06_M1_Training_Evaluation.md §reproducibility hash](06_M1_Training_Evaluation.md) | **Committed to git** (small JSON); contains git SHA + data SHA-256 + env.yml hash + per-language F1 |
| `models/m1/v1.0/metrics.json` | Per-language F1 + confusion matrix + ECE | 🔲 | [06_M1_Training_Evaluation.md §4](06_M1_Training_Evaluation.md) | **Committed to git**; consumed by monitoring dashboard |
| `models/m1/v0.9/` | Previous version (rollback target) | 🔲 | [07_M1_Deployment_Integration.md §rollback](07_M1_Deployment_Integration.md) | Always kept on the Fly volume for ~60s rollback |
| `models/m1/baseline/lid.176.bin` | fastText language-ID model (EN/SI/TA routing) | ✅ **Present** | [10_M1_Sinhala_Tamil_NLP.md](10_M1_Sinhala_Tamil_NLP.md) | Fetched by `enigmatrix-ml/scripts/download_lid_model.py`; read by `enigmatrix-ml/m1/extraction/language_detection.py` |
| `models/m1/baseline/tfidf_lr_model.pkl` | Production-baseline TF-IDF + LR | 🔲 | [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) | Trained on the full labelled set; used for ablation only |
| `models/m1/baseline/vocabulary.pkl` | Baseline's vocabulary | 🔲 | Same | Companion to `tfidf_lr_model.pkl`; pickle for reproducibility |

## How to start building

This folder is **mostly conventions** — directories appear as Phase 2 + Phase 3 run. The build work is *setting up the conventions* + *enforcing them in CI*.

1. **Create the directory tree.** `mkdir -p storage/m1/{raw,ocr_cache,inference_cache} storage/models/m1/{baseline,v1.0}`. Add `.gitkeep` files so empty dirs are tracked.
2. **`.gitignore` setup.** Add `storage/m1/raw/`, `storage/m1/ocr_cache/`, `storage/m1/inference_cache/`, `storage/models/m1/v*/*.onnx`, `storage/models/m1/v*/adapter_model.bin`, `storage/models/m1/v*/tokenizer/` to gitignore. The only things that ARE tracked: `model_registry.json` + `metrics.json` files (small, reproducibility-critical).
3. **S3 lifecycle config.** Per [02_M1_3 §Step 4](02_M1_Data_Requirements.md), commit `infra/aws/s3_m1_lifecycle.yaml`. AWS CLI applies the rules; CI asserts byte-equality with the committed YAML.
4. **Fly volume.** `fly volumes create ml_models --size 3 --region sin` once Phase 3 ships the first ONNX. Volume mounted at `/app/storage/models/` per [07_M1_2 §fly.toml](07_M1_Deployment_Integration.md).
5. **Model versioning convention.** When Phase 3's training pipeline lands, every `model_registry.json` must include: `model_version` (semver), `trained_at` (ISO), `git_commit_sha`, `dataset.labeled_set_sha256`, `dataset.split_boundaries`, `environment.python` + `torch` + `transformers` + `peft` + `onnxruntime` versions, `training.seeds` + `final_macro_f1_mean` + `final_macro_f1_std`, `metrics_per_language`. See [06_M1_Training_Evaluation.md §reproducibility hash](06_M1_Training_Evaluation.md) for the full schema.
6. **Backup + retention.** `storage/m1/raw/` PDFs > 2y old auto-migrate to Glacier (S3 lifecycle). Local repo dev: just rely on the lifecycle; don't try to delete locally.

The two committed files per model version (`model_registry.json` + `metrics.json`) are the *only* things from this folder that ship in the docs/PR review. Everything else is operational.

## Dependencies

- **`enigmatrix-backend/scraper/pipelines.py`** ([15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)) — writes to `storage/m1/raw/`.
- **`enigmatrix-ml/m1/extraction/ocr.py`** ([15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)) — reads/writes `storage/m1/ocr_cache/`.
- **`enigmatrix-ml/m1/model/inference.py`** ([15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)) — reads `storage/models/m1/v<X>/*.onnx`.
- **`enigmatrix-ml/m1/model/train_xlmr.py`** + `export_onnx.py` ([15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)) — writes the entire `storage/models/m1/v<X>/` tree.
- **AWS S3** — Glacier lifecycle for raw PDFs > 2 years old.
- **Fly.io persistent volume** — mounts production model files at `/app/storage/models/`.

## Tests & acceptance criteria

- **Gitignore correctness.** `git status` after a clean checkout + Phase 2 run shows ZERO untracked files under `storage/m1/raw/` etc. (they're gitignored). CI test: spider produces PDFs locally; `git status --porcelain storage/` is empty.
- **`model_registry.json` validity.** Every committed `model_registry.json` matches `ml/m1/schema/manifest.py`'s Pydantic schema. CI test on every PR.
- **No model files committed by accident.** CI fails any PR that adds `*.onnx`, `adapter_model.bin`, or files under `tokenizer/` to git. Pre-commit hook enforces.
- **S3 lifecycle in sync.** `aws s3api get-bucket-lifecycle-configuration --bucket enigmatrix-m1-pdfs` byte-matches `infra/aws/s3_m1_lifecycle.yaml`. Drift detection in monitoring.
- **Rollback works.** Quarterly drill: flip `M1_MODEL_VERSION=v<previous>` on staging → confirm previous model serves traffic correctly → `< 60s` end-to-end.

## Cross-references

- Folder map spec: [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md)
- Roadmap: [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md) §Phase 3 (model artifacts ship) + §Phase 2 (PDFs land)
- Reproducibility: [06_M1_Training_Evaluation.md §reproducibility hash](06_M1_Training_Evaluation.md)
- ONNX export: [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md)
- Fly deployment: [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md)
- Retention + S3 lifecycle: [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md)
- Sibling folders: [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md), [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)


# 15_M1_6 — `enigmatrix-docs/m1/` Folder Build Guide

> Companion to [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) — build guide for the docs folder itself.
> **Two locations (2026-07-24):** the canonical docs live in **`enigmatrix-docs/m1/`** in the repo; they are also authored/mirrored in the **Obsidian research vault** at `E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\` (which additionally holds `findings/`, `local-dev/`, `planned-for-development/`, and `final/works/` that aren't in the repo copy). Keep the numbered `NN_M1_*.md` set in sync between the two. Operational runbooks that pair with code (e.g. the Phase-3 annotation runbook) live next to the code under `research/data/`, **not** here.
> **Implementation status snapshot:** ✅ Shipped — the full numbered doc set (01–16 mains + sub-step companions + 14 tracking + 15 folder guides + README). Counts drift as docs are added; treat the numbers below as approximate.

## Purpose

`enigmatrix-docs/m1/` is the canonical knowledge base for Module 1 — research framing, technical specs, sub-step deep-dives, tracking workflows, folder + dev guides. It's the only folder in this guide series that's *fully shipped today*. The guide exists so a contributor adding a new M1 doc knows the conventions: numbering, skeleton, badges, cross-link patterns. It is also the entry point for "where in the docs do I write X?" — naming + placement decisions.

## Files in this folder

Doc 13's tree summary line for this folder is `enigmatrix-docs/m1/ ├── 01_M1_*.md … 12_M1_*.md ├── 13_M1_Folder_Structure_and_Implementation_Flow.md └── NN_M1_N_*.md (29 sub-step companions)`. As of this pass, 14, 15, and 16 also exist. The doc series is:

| Series | What it covers | Count | Skeleton |
|---|---|---|---|
| `01_M1_*` through `12_M1_*` | Main research + design docs (research problem, data, collection, preprocessing, model, training, deployment, system arch, annotation, multilingual, API, monitoring) | 12 | Long-form prose with section headings; each is a self-contained chapter |
| `NN_M1_M_*.md` (backend sub-step companions) | Sub-step deep-dives under each of `01..12` | 29 | Locked 7-section skeleton: Purpose → Detailed process → Tech choices → Worked example → Failure modes → Validation → Cross-references |
| `13_M1_Folder_Structure_*` | The folder spec (what every file owns) | 1 | Custom shape — folder map + per-file role table + implementation flow |
| `14_M1_Tracking_Workflows.md` + `14_M1_N_*.md` | Frontend tracking workflows (parent + 9 companions) | 10 | Parent is an index; sub-step companions use the locked 7-section skeleton |
| `15_M1_Folder_Reference.md` + `15_M1_N_*.md` | Per-folder build guides (this series — parent + 6 companions) | 7 | Locked sub-folder skeleton: Purpose → Files table → How to start → Dependencies → Tests → Cross-refs |
| `16_M1_Development_Roadmap.md` | Sequenced "start here" guide | 1 | Phase-based; each phase has steps with "Do this next" call-outs |
| `README.md` | Index of everything above | 1 | Document Index table + Sub-Step Companions table + cross-refs |

**~60+ files in `enigmatrix-docs/m1/`** (main docs + sub-step companions + tracking + folder guides + README), plus the repo also carries a `planned-for-devlopment/` scratch folder. The Obsidian vault mirror carries the same numbered set plus research-only folders. Exact counts drift — the `README.md` index is the source of truth, not this number.

## How to add a new doc

The conventions are deliberate — a new doc should slot into one of these patterns:

### 1. Extending an existing main doc (`01..12`)

If the new content is a sub-step deep-dive that belongs under a parent (e.g. expanding `04_M1_Preprocessing_Pipeline.md` with a new chunking variant), add a sub-step companion: `04_M1_4_<Title>.md`. Use the locked 7-section skeleton. Update the parent doc's "Sub-step companions" header line to link to the new file. Update `README.md` Sub-Step Companions table.

### 2. New top-level main doc (rare)

If the new content is a *new* major topic that doesn't fit under 01–16, take the next available number (17, 18, ...) and pick a skeleton (long-form chapter or new sub-step parent). Add a row to `README.md` Document Index. Cross-link from related existing docs.

### 3. New folder build guide

If a new top-level project folder is added (e.g. an `infra/` folder lands), create `15_M1_<N>_<Folder>_Folder_Guide.md` using the locked sub-folder skeleton. Update `15_M1_Folder_Reference.md` Index table. Update `README.md`.

### 4. Conventions to obey

- **Naming.** `NN_M1_<TitleSnakeCase>.md` for main docs; `NN_M1_M_<TitleSnakeCase>.md` for sub-step companions. `NN` zero-padded to 2 digits (`01`, `02`, …, `16`); sub-step suffix is just `1..9` (not zero-padded).
- **Status badges.** Every sub-step companion + folder guide opens with `> **Implementation status:** ✅ Shipped | 🟡 Partial | 🔲 Deferred` in the header. Honest — never `✅` for code that doesn't exist.
- **Cross-refs.** Every doc has a "Cross-references" section at the bottom. Link to the parent + roadmap + relevant detail docs.
- **Worked examples.** Use the seeded demo regulations (`VAT_2024_AMD`, `EPF_2024_RATE`, multi-pin adapter from [02_M1_4](02_M1_Data_Requirements.md)). No PII; no real SME names.
- **EN-only.** Doc body content is English. Trilingual labels go in `frontend/messages/{en,si,ta}.json`; doc body translation is deferred indefinitely.

## When to update which doc

| Trigger | Update |
|---|---|
| New M1 source code lands | The relevant `15_M1_N_*` folder guide's "Files in this folder" table — flip status badge from 🔲 to ✅ |
| Schema migration adds a column | [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) §2 (the table the column belongs to) + [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) constraint list |
| New regulation category added | [09_M1_Annotation_Guidelines.md §2](09_M1_Annotation_Guidelines.md) + [09_M1_Annotation_Guidelines.md](09_M1_Annotation_Guidelines.md) + `frontend/messages/*.json` |
| Classifier hyperparameter change | [05_M1_Model_Architecture.md §4.2](05_M1_Model_Architecture.md) + [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) |
| Retraining run completes | `storage/models/m1/v<X>/model_registry.json` + the F1 table in [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) |
| New tracking surface (frontend) | [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) parent table + new `14_M1_N_*` companion |
| Build phase ships | [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md) — flip the phase DoD checkmark |

## How to start building

1. **Decide which series.** Use the table at the top — main doc, sub-step companion, folder guide, or roadmap?
2. **Pick a number.** Look at `README.md` Document Index for the next available; for sub-step companions, the next available sub-number under the relevant parent.
3. **Copy the skeleton from a sibling.** Don't invent. `15_M1_Folder_Reference.md` is a good model for any new folder guide; `04_M1_Preprocessing_Pipeline.md` is a good model for any new sub-step companion.
4. **Open `README.md` LAST.** Add your file to both the Document Index + the Sub-Step Companions table (if applicable). Bump the file-count line.
5. **Run the cross-ref check.** From `enigmatrix-docs/m1/`: the Python script from the previous turn's verification — assert no broken `.md` links.

## Dependencies

This folder is the *destination* of every other folder's work — every code change should produce a documentation update. There are no upstream dependencies in code, only in *content* (the detail docs build on each other; the cross-ref graph is the spec).

## Tests & acceptance criteria

- **Cross-ref integrity.** Every markdown link to a `.md` target resolves. CI runs the Python URL-only checker against `enigmatrix-docs/m1/*.md` on every PR.
- **Skeleton conformance.** Every sub-step companion + folder guide carries all 7/6 required sections (per the locked skeletons). CI grep.
- **Status-badge honesty.** Spot-check 3 random docs per quarter — does the badge match reality? Any `✅` claim that doesn't map to shipped code is a bug.
- **README index completeness.** Every file in the folder appears in `README.md`. CI test: `ls *.md | wc -l` matches the row count in README's table.
- **No accidental code drift.** This folder is docs-only. CI test: any PR touching only `enigmatrix-docs/m1/` should have zero changes outside that folder.

## Cross-references

- Folder map spec: [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md)
- Parent reference: [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)
- Roadmap: [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md)
- Per-module template (how to clone for M2/M3/M4): [13_M1_Folder_Structure §5](13_M1_Folder_Structure_and_Implementation_Flow.md)
- M1 doc index: [README.md](README.md)
- Tracking workflows pattern: [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) (an example of a parent + companions series)
- Sibling folders: [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) … [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)
