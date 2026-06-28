# 15_M1_1 — `ml/` Folder Build Guide

> Companion to [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) — build guide for the `ml/` slice of doc 13's M1 tree.
> **Implementation status snapshot:** 🔲 ~28 deferred · 🟡 0 partial · ✅ 0 shipped (the entire `ml/` slice lands with BUILD_07 + BUILD_11).

## Purpose

`ml/` is the ML monorepo — everything that trains, evaluates, or runs the gazette classifier. It owns Stages B (extraction), C (preprocessing), D (classification + inference), and E (summarisation) from the pipeline. Cross-module helpers (embeddings, drift detection, reproducibility) live in `ml/shared/`. Each module is isolated: `ml/m1/` never imports from `ml/m2/` — shared code goes through `ml/shared/`.

## Files in this folder

### `ml/shared/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `shared/embeddings.py` | `multilingual-e5-base` wrapper | 🔲 | [03_M1_3 §3](03_M1_3_Secondary_Source_Integration.md) | Implement `embed(texts) -> np.ndarray`; cache the model singleton |
| `shared/drift.py` | KL-divergence + Population Stability Index helpers | 🔲 | [12_M1_Monitoring_Maintenance.md §3.1](12_M1_Monitoring_Maintenance.md) | Two pure functions: `kl_divergence(p, q)` + `psi(prod, ref)`; pip-only deps |
| `shared/reproducibility.py` | `hash_dataset()` + `pin_environment()` | 🔲 | [06_M1_Training_Evaluation.md §reproducibility hash](06_M1_Training_Evaluation.md) | SHA-256 over the labeled parquet + `pip freeze` snapshot |

### `ml/m1/data/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `data/sources.py` | 15-source registry (matches `m1_sources` table) | 🔲 | [02_M1_1_Data_Sources_Catalogue.md](02_M1_1_Data_Sources_Catalogue.md) | Hard-code the 15 sources as `dict[str, Source]`; the registry seeds the DB table |
| `data/loaders.py` | Async DB → labeled-set iterator | 🔲 | [05_M1_1_Sampling_Strategy.md](05_M1_1_Sampling_Strategy.md) | `async def load_labeled_set(split) -> AsyncIterator[Sample]`; uses `asyncpg` |
| `data/samplers.py` | Stratified + k-means + active-learning | 🔲 | [05_M1_1_Sampling_Strategy.md](05_M1_1_Sampling_Strategy.md) | Three functions: `stratified_sample`, `cluster_diverse_sample`, `active_learning_sample` |
| `data/augmentation.py` | Back-translation + paraphrase + Sinhala morph rules | 🔲 | [06_M1_1_Data_Augmentation_Strategy.md](06_M1_1_Data_Augmentation_Strategy.md) | Cap at 5× per source doc; diversity-validate via embedding cosine |

### `ml/m1/extraction/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `extraction/pdf_classifier.py` | `classify_pdf(path) -> 'text'|'hybrid'|'scanned'` | 🔲 | [03_M1_1_PDF_Extraction_Chain.md](03_M1_1_PDF_Extraction_Chain.md) | Thresholds `text > 200, scanned < 30` chars/page from env vars |
| `extraction/text_extractors.py` | PyMuPDF → pdfplumber → Tesseract chain | 🔲 | [03_M1_1_PDF_Extraction_Chain.md](03_M1_1_PDF_Extraction_Chain.md) | Fallback chain; each tier needs ≥ 100 chars to win |
| `extraction/ocr.py` | Tesseract 5.3.x + Wijesekara conversion | 🔲 | [10_M1_2_OCR_Wijesekara_Conversion.md](10_M1_2_OCR_Wijesekara_Conversion.md) | `--oem 1 --psm 6 --lang eng+sin+tam`; Wijesekara via greedy longest-match table |
| `extraction/language_detection.py` | fastText `lid.176.bin` (500-char window, top-3) | 🔲 | [10_M1_1_Language_Detection_Routing.md](10_M1_1_Language_Detection_Routing.md) | Load model once; `predict(text[:500], k=3)`; return top-1 or "mixed" |

### `ml/m1/preprocessing/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `preprocessing/cleaning.py` | 8 noise classes + NFKD | 🔲 | [04_M1_1_Gazette_Noise_Removal.md](04_M1_1_Gazette_Noise_Removal.md) | Fixed-order regex chain; idempotent — `clean(clean(x)) == clean(x)` |
| `preprocessing/metadata_extractor.py` | Gazette#, effective date, multi-penalty, principal act | 🔲 | [04_M1_2_Metadata_Extraction_Patterns.md](04_M1_2_Metadata_Extraction_Patterns.md) | `re.finditer` for multi-penalty; output stored in `m1_regulation_penalties` |
| `preprocessing/chunking.py` | §-aware → 512-token sliding window (stride 64) | 🔲 | [04_M1_3_Text_Chunking_Strategy.md](04_M1_3_Text_Chunking_Strategy.md) | Detect sections via `NOTICE_BOUNDARY_RE`; emit `Chunk[]`; classifier consumes `[0]` |
| `preprocessing/tokenization.py` | XLM-R SentencePiece wrapper | 🔲 | [05_M1_Model_Architecture.md §4.2](05_M1_Model_Architecture.md) | Wrap `AutoTokenizer.from_pretrained('facebook/xlm-roberta-base')` |

### `ml/m1/model/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `model/architecture.py` | `GazetteClassifier` (XLM-R + LoRA + dual head) | 🔲 | [05_M1_Model_Architecture.md §4](05_M1_Model_Architecture.md) | `nn.Module` with PEFT LoRA wrap + 2 classification heads |
| `model/training.py` | 3-seed loop, AdamW, FP16, early-stop | 🔲 | [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) | Differential LRs (LoRA 2e-4, heads 2e-5); 10-epoch cap |
| `model/evaluation.py` | macro-F1, ECE, slice analyses | 🔲 | [06_M1_2_Slice_Analysis_Framework.md](06_M1_2_Slice_Analysis_Framework.md) | 4 standard slices + 2 extended; outputs `EvaluationReport` |
| `model/inference.py` | ONNX Runtime session + Redis cache | 🔲 | [07_M1_1_ONNX_Export_Quantization.md](07_M1_1_ONNX_Export_Quantization.md) | Cache key = `SHA256(text + gazette# + date + model_version)` |
| `model/calibration.py` | Temperature scaling | 🔲 | [12_M1_1_Performance_Monitoring_Alerting.md](12_M1_1_Performance_Monitoring_Alerting.md) | Fit `T` on val set; apply at inference |

### `ml/m1/summarization/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `summarization/marianmt.py` | MarianMT EN→SI/TA + EN→EN summary | 🔲 | [04_M1_3_Text_Chunking_Strategy.md](04_M1_3_Text_Chunking_Strategy.md) | Per-chunk summarise; concat to ≤ 600 chars total |

### `ml/m1/schema/` + `ml/m1/utils/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `schema/pydantic_models.py` | `PreprocessedGazette`, `PredictionOut`, etc. | 🔲 | [04_M1_Preprocessing_Pipeline.md §3.5](04_M1_Preprocessing_Pipeline.md) | Mirror the dataclass shape from doc 04; immutable + JSON-serializable |
| `schema/manifest.py` | Dataset `manifest.yaml` schema | 🔲 | [06_M1_Training_Evaluation.md §reproducibility hash](06_M1_Training_Evaluation.md) | Validates `model_registry.json` shape |
| `utils/constants.py` | 12 category codes, 10 sector codes | 🔲 | [09_M1_Annotation_Guidelines.md §2 + §3](09_M1_Annotation_Guidelines.md) | Two `Literal`-style enums; single source of truth |
| `utils/logging.py` | Structured JSON logging | 🔲 | — | `structlog` config; per-task `request_id` propagation |
| `utils/validation.py` | Data-quality assertions | 🔲 | [02_M1_2_Database_Schema_Validation.md](02_M1_2_Database_Schema_Validation.md) | Functions consumed by Pydantic validators + nightly health checks |

### `ml/tests/m1/`

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `tests/m1/extraction/test_pdf_classifier.py` | Fixture PDFs × the 3-tier classifier | 🔲 | [03_M1_1 §validation](03_M1_1_PDF_Extraction_Chain.md) | 50-doc audit set; ≥ 95% correct classification |
| `tests/m1/preprocessing/test_cleaning.py` | Per-noise-class round-trip tests | 🔲 | [04_M1_1 §validation](04_M1_1_Gazette_Noise_Removal.md) | 8 noise classes × 2 cases each = 16 unit tests minimum |
| `tests/m1/model/test_inference.py` | ONNX output ≈ PyTorch output (1e-4) | 🔲 | [07_M1_1 §validation](07_M1_1_ONNX_Export_Quantization.md) | Smoke test on a 50-doc held-out set |
| `tests/m1/fixtures/sample_gazettes/` | Anonymised demo PDFs for tests | 🔲 | — | Use the 5 seeded demo regulations as fixture PDFs |

## How to start building

Follow the roadmap's [Phase 2 + Phase 3 ordering](16_M1_Development_Roadmap.md). The fastest entry point in `ml/`:

1. **Set up the package skeleton.** `ml/__init__.py`, `ml/m1/__init__.py`, etc. — empty `__init__.py` files; the imports already work.
2. **Start with `ml/m1/extraction/pdf_classifier.py`.** It has zero dependencies on other `ml/` files; the only external deps are `pymupdf` + the `M1_PDF_TEXT_THRESHOLD` / `M1_PDF_SCANNED_THRESHOLD` env vars. Tests live at `tests/m1/extraction/test_pdf_classifier.py` — TDD pattern.
3. **Then `text_extractors.py` + `ocr.py`.** These complete Stage B; without them the Celery `extract_gazette` task can't advance a row past `status='ingested'`.
4. **Then `preprocessing/cleaning.py` + `metadata_extractor.py` + `chunking.py`.** Stage C — feeds Stage D's classifier input.
5. **Then `data/sources.py` + `data/loaders.py` + `data/samplers.py`.** These enable the labeling loop (Phase 3 of the roadmap).
6. **Then `model/*` files** in order: architecture → training → evaluation → inference. Each depends on the previous.
7. **Finally `summarization/marianmt.py`.** Independent of the classifier; can be built in parallel with `model/*` once Stage D has output to summarise.

Cross-module helpers (`ml/shared/`) build alongside whatever needs them — embeddings first (used by secondary-source matching in Phase 4), then drift (Phase 4 monitoring), then reproducibility (Phase 3).

## Dependencies

- **`backend/` Celery task layer** ([15_M1_2_Backend_Folder_Guide.md](15_M1_2_Backend_Folder_Guide.md)) — every `ml/m1/` module is called *from* a Celery task in `backend/app/tasks/m1/`. The boundary is one-way: `ml/m1/` never imports from `backend/`.
- **`scraper/` Stage A** ([15_M1_3_Scraper_Folder_Guide.md](15_M1_3_Scraper_Folder_Guide.md)) — provides the PDFs that `ml/m1/extraction/` consumes.
- **`storage/` artifacts** ([15_M1_5_Storage_Folder_Guide.md](15_M1_5_Storage_Folder_Guide.md)) — raw PDFs, OCR cache, model files; `ml/m1/` reads + writes here.
- **Postgres** — `data/loaders.py` reads the labeled set; the training script reads the DB directly. No ORM dependency — uses `asyncpg` or `psycopg` raw.

## Tests & acceptance criteria

- **Coverage target.** Every public function in `ml/m1/` has ≥ 1 unit test; integration tests cover Stage B → C → D end-to-end on fixture PDFs.
- **Per-stage acceptance.** Stage B: extraction success rate ≥ 95 % on the audit set; OCR CER ≤ 10 % on Sinhala/Tamil. Stage D: macro-F1 ≥ 0.92 with 3-seed stability < 0.02 std. ONNX export: max-abs-diff vs PyTorch < 1e-4.
- **Validation docs.** Per-file specs reference the "Validation & acceptance criteria" section of the linked detail doc.

## Cross-references

- Folder map spec: [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md)
- Roadmap: [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md)
- Phase docs: BUILD_07 (Stage A–F backend), BUILD_11 (ML training)
- Sibling folders: [15_M1_2_Backend_Folder_Guide.md](15_M1_2_Backend_Folder_Guide.md), [15_M1_3_Scraper_Folder_Guide.md](15_M1_3_Scraper_Folder_Guide.md), [15_M1_5_Storage_Folder_Guide.md](15_M1_5_Storage_Folder_Guide.md)
