# 13 — M1 Folder Structure & Implementation Flow

> Where every M1 file lives, what it owns, when it lands, and how the same shape extends to M2/M3/M4.
> **Implementation status:** 🟡 Spec only — code lands with BUILD_07 (ingest), BUILD_11 (ML), BUILD_12 (schedulers).

---

## Purpose

The 12 numbered M1 docs describe **what** the gazette-classifier system does. This doc describes **where in the project tree** each piece lives once BUILD_07/11/12 ship. It also locks the per-module shape so M2 (Knowledge), M3 (Vulnerability), and M4 (Misinformation) can copy the layout without re-litigating decisions.

> Today (2026-05-14): the only M1 code that actually exists is the admin-CRUD slice — `backend/app/services/m1_regulation_service.py` + `backend/app/scripts/seed_regulations.py` + 5 demo regulations. Everything below is the **target** layout. Each sub-step doc carries a status badge so a reader can tell what's shipped vs deferred.

---

## Design principles

Five principles drive every layout decision below. When in doubt, fall back to these.

### 1. Organise by pipeline stage, not by file type

The pipeline has six stages (A–F, plus G for the research-findings extraction step). The folder tree under `ml/m1/` mirrors them one-for-one (`extraction/`, `preprocessing/`, `model/`, `summarization/`). This keeps related files together — a contributor working on Stage B reads `ml/m1/extraction/*.py` instead of hunting across `ml/loaders/`, `ml/utils/`, `ml/parsers/`.

### 2. Schema separation: Pydantic ↔ SQLAlchemy ↔ ORM

API contracts (Pydantic) and persistence (SQLAlchemy) live in distinct files inside `app/schemas/m1.py` and `app/models/m1_regulation.py`. ML-side type definitions (`ml/m1/schema/pydantic_models.py`) are *separate* from API-side schemas — they may overlap in shape but the lifecycle is different: API schemas validate HTTP boundaries, ML schemas validate file-on-disk artifacts (manifests, predictions, calibration outputs).

### 3. Tests mirror code

`tests/m1/` contains a subtree that 1:1 mirrors `ml/m1/`. If `ml/m1/extraction/pdf_classifier.py` exists, `tests/m1/extraction/test_pdf_classifier.py` exists. Same for `backend/tests/m1/` mirroring `backend/app/services/m1_*` and `backend/app/tasks/m1_*`. **Test files are first-class — no PR merges without them.**

### 4. Reproducibility: artifacts + git + data hash co-located

Every trained model artifact (`storage/models/m1/v1.0/`) carries a `model_registry.json` next to it that records: git commit SHA, training-dataset SHA-256, environment.yml, ONNX Runtime version, seed list, evaluation metrics per language. **Never overwrite a version — version-bump, archive the old.** The Fly volume keeps the last 2 versions hot for fast rollback.

### 5. Scalability: M2/M3/M4 mirror this exact tree

Adding M2 means copying `ml/m1/` to `ml/m2/`, copying `app/tasks/m1_*` to `app/tasks/m2_*`, etc. Cross-module shared utilities go in `ml/shared/` (NOT inside any module folder) and `app/services/shared/`. This is enforced by convention — see [§5 Per-module template](#5-per-module-template-m2-m3-m4) below.

---

## M1 folder map

> **See also:** for per-folder *build instructions* (what every file owns + how to start building it + dependencies + acceptance) see [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) and its 6 sub-folder guides ([ml/](15_M1_1_ML_Folder_Guide.md) · [backend/](15_M1_2_Backend_Folder_Guide.md) · [scraper/](15_M1_3_Scraper_Folder_Guide.md) · [research/](15_M1_4_Research_Folder_Guide.md) · [storage/](15_M1_5_Storage_Folder_Guide.md) · [docs/](15_M1_6_Docs_Folder_Guide.md)). For the *sequenced order* in which to build these folders see the [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md). This doc remains the *spec* (what every file owns); those docs are the *how to ship it*.

This is the full tree once BUILD_07 + BUILD_11 + BUILD_12 have all shipped. Folders marked 🟡 are partially implemented today (admin-CRUD only); 🔲 are wholly deferred; ✅ are shipped.

```
xyz/                                          # repo root
├── ml/                                        # 🔲 ML monorepo slice (training + inference)
│   ├── shared/                                # cross-module helpers (e.g. embeddings, drift)
│   │   ├── __init__.py
│   │   ├── embeddings.py                      # intfloat/multilingual-e5-base wrapper
│   │   ├── drift.py                           # KL-divergence + PSI helpers
│   │   └── reproducibility.py                 # hash_dataset(), pin_environment()
│   │
│   ├── m1/                                    # Module 1 — gazette classifier
│   │   ├── __init__.py
│   │   ├── config.py                          # M1 hyperparameters, paths, feature flags
│   │   │
│   │   ├── data/                              # Stage 0 — data setup (sampling, augmentation)
│   │   │   ├── __init__.py
│   │   │   ├── sources.py                     # 15-source registry → matches m1_sources table
│   │   │   ├── loaders.py                     # AsyncSession DB loaders for labeled set
│   │   │   ├── samplers.py                    # stratified + k-means + active-learning
│   │   │   └── augmentation.py                # back-translation + paraphrase + SI morph
│   │   │
│   │   ├── extraction/                        # Stage B — PDF → text
│   │   │   ├── __init__.py
│   │   │   ├── pdf_classifier.py              # classify_pdf() → text|hybrid|scanned
│   │   │   ├── text_extractors.py             # PyMuPDF + pdfplumber + Tesseract chain
│   │   │   ├── ocr.py                         # Tesseract 5.3.x config + Wijesekara converter
│   │   │   └── language_detection.py          # fastText lid.176.bin wrapper
│   │   │
│   │   ├── preprocessing/                     # Stage C — text → clean tokens
│   │   │   ├── __init__.py
│   │   │   ├── cleaning.py                    # 8 noise-class removal
│   │   │   ├── metadata_extractor.py          # gazette#, effective_date, penalty, principal_act regex
│   │   │   ├── chunking.py                    # §-aware → sliding-window hybrid
│   │   │   └── tokenization.py                # XLM-R SentencePiece wrapper
│   │   │
│   │   ├── model/                             # Stage D — classification
│   │   │   ├── __init__.py
│   │   │   ├── architecture.py                # GazetteClassifier (XLM-R + LoRA + dual head)
│   │   │   ├── training.py                    # 3-seed loop, AdamW, early-stopping
│   │   │   ├── evaluation.py                  # macro-F1, slice analyses, ECE
│   │   │   ├── inference.py                   # ONNX Runtime + Redis cache
│   │   │   └── calibration.py                 # temperature scaling for confidence outputs
│   │   │
│   │   ├── summarization/                     # Stage E — text → EN/SI/TA summaries
│   │   │   ├── __init__.py
│   │   │   └── marianmt.py                    # Helsinki-NLP MarianMT wrapper
│   │   │
│   │   ├── schema/                            # ML-internal type definitions
│   │   │   ├── __init__.py
│   │   │   ├── pydantic_models.py             # PreprocessedGazette, PredictionOut, etc.
│   │   │   └── manifest.py                    # dataset manifest.yaml schema
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── constants.py                   # 12 category codes, 10 sector codes
│   │       ├── logging.py                     # structured JSON logging
│   │       └── validation.py                  # data-quality assertions
│   │
│   └── tests/                                 # ML-side tests
│       ├── m1/
│       │   ├── data/test_samplers.py
│       │   ├── extraction/test_pdf_classifier.py
│       │   ├── extraction/test_text_extractors.py
│       │   ├── preprocessing/test_cleaning.py
│       │   ├── preprocessing/test_chunking.py
│       │   ├── model/test_inference.py
│       │   └── fixtures/
│       │       ├── sample_gazettes/           # anonymised demo PDFs
│       │       └── gold_labels.csv            # IAA-validated test labels
│       └── shared/test_embeddings.py
│
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   └── m1_regulations.py              # ✅ admin CRUD shipped; classify/verify/propagation deferred
│   │   ├── services/
│   │   │   ├── m1_regulation_service.py       # ✅ admin slice; ⚙️ inference-bridge deferred
│   │   │   └── shared/
│   │   │       └── audit_service.py           # ✅ singular audit_log (Session 14)
│   │   ├── tasks/                             # 🔲 Celery — all M1 tasks deferred
│   │   │   ├── m1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── gazette_scraper.py         # Stage A
│   │   │   │   ├── extract_gazette.py         # Stage B
│   │   │   │   ├── classify_gazette.py        # Stage D
│   │   │   │   ├── summarise_gazette.py       # Stage E
│   │   │   │   ├── alert_dispatch.py          # Stage F
│   │   │   │   ├── portal_watcher.py          # secondary sources (IRD/EPF/eROC)
│   │   │   │   ├── rss_watcher.py             # news RSS
│   │   │   │   └── analytics.py               # nightly view refresh, retraining triggers
│   │   ├── models/
│   │   │   └── m1_regulation.py               # ✅ 5 demo rows; 🟡 the 9 m1_* tables — only m1_regulations exists
│   │   ├── schemas/
│   │   │   └── m1.py                          # ✅ admin schemas
│   │   ├── config/
│   │   │   └── feature_flags.py               # 🔲 per-stage on/off toggles
│   │   ├── db/migrations/versions/
│   │   │   └── *_m1_*.py                      # 🟡 m1_regulations only
│   │   ├── scripts/
│   │   │   ├── seed_regulations.py            # ✅ 5 demo rows
│   │   │   ├── m1_backfill_classifications.py # 🔲 BUILD_07
│   │   │   └── m1_validate_pipeline.py        # 🔲 ongoing health checks
│   │   └── middleware/
│   │       └── audit_middleware.py            # ✅ Session 14 (passive HTTP logging)
│   └── tests/m1/                              # backend-side integration tests
│       ├── test_m1_regulation_service.py      # ✅ admin slice
│       └── ...                                # 🔲 task + inference tests
│
├── scraper/                                   # 🔲 Scrapy spider lives outside ml/ + backend/
│   ├── __init__.py
│   ├── settings.py
│   ├── pipelines.py                           # PDF→storage pipeline
│   └── spiders/
│       ├── gazette_spider.py                  # gazette.lk + documents.gov.lk
│       └── portal_spiders.py                  # IRD/EPF/eROC/Customs watchers
│
├── research/                                  # 🟡 notebooks scaffolded, no real data yet
│   ├── notebooks/
│   │   ├── findings_lag_analysis.ipynb        # F1–F3
│   │   ├── findings_classifier_evaluation.ipynb
│   │   ├── findings_alert_effectiveness.ipynb # F6 DiD
│   │   └── findings_secondary_diffusion.ipynb # F4 channel effectiveness
│   ├── figures/                               # rendered output (committed; small PNGs)
│   └── data/
│       ├── labeling/                          # Label Studio export CSVs
│       │   ├── batch_01.csv … batch_NN.csv
│       │   └── gold_standard.csv
│       └── test_split.parquet                 # held-out test set hash-pinned in registry
│
├── storage/                                   # local + Fly persistent volume artifacts
│   ├── m1/
│   │   ├── raw/                               # downloaded PDFs (gitignored, S3 cold archive >2y)
│   │   ├── ocr_cache/                         # Tesseract outputs (idempotent, gitignored)
│   │   └── inference_cache/                   # Redis dump (operational, gitignored)
│   └── models/
│       └── m1/
│           ├── v1.0/
│           │   ├── gazette_classifier.onnx
│           │   ├── gazette_classifier_int8.onnx
│           │   ├── adapter_model.bin          # raw LoRA weights (for retraining)
│           │   ├── tokenizer/
│           │   ├── model_registry.json        # git SHA, data SHA, env.yml, metrics
│           │   └── metrics.json               # per-language F1, confusion matrix, ECE
│           ├── v0.9/                          # previous version (rollback target)
│           └── baseline/
│               ├── tfidf_lr_model.pkl
│               └── vocabulary.pkl
│
└── enigmatrix-docs/m1/                        # this folder — docs only
    ├── 01_M1_*.md … 12_M1_*.md
    ├── 13_M1_Folder_Structure_and_Implementation_Flow.md
    └── NN_M1_N_*.md                           # 29 sub-step companions
```

---

## File-by-file role description

For each non-trivial file: **owns** (what state/logic), **exports** (the public surface), **called by** (upstream consumer).

| File | Owns | Exports | Called by |
|---|---|---|---|
| `ml/m1/data/sources.py` | 15-source registry (URLs, scrape frequency, fallback) | `SOURCE_REGISTRY: dict[str, Source]` | `scraper/spiders/*`, `backend/app/tasks/m1/portal_watcher.py` |
| `ml/m1/data/loaders.py` | DB → labeled-set loader (async) | `load_labeled_set(split: "train"|"val"|"test") -> Iterator[Sample]` | `ml/m1/model/training.py` |
| `ml/m1/data/samplers.py` | Stratified + k-means + active-learning | `sample_for_labeling(year_lang_strat, k=20, al_top=50)` | `scripts/sample_for_labeling.py` |
| `ml/m1/extraction/pdf_classifier.py` | `classify_pdf(path) -> Literal["text", "hybrid", "scanned"]` | threshold-tunable function | `backend/app/tasks/m1/extract_gazette.py` |
| `ml/m1/extraction/text_extractors.py` | PyMuPDF→pdfplumber→Tesseract fallback chain | `extract_text(path, pdf_type) -> ExtractedText` | same |
| `ml/m1/extraction/ocr.py` | Tesseract 5.3.x runner + Wijesekara conversion | `run_ocr(image_path, langs="eng+sin+tam")`, `wijesekara_to_unicode(s)` | `text_extractors.py` |
| `ml/m1/extraction/language_detection.py` | fastText `lid.176.bin` (top-3 confidence) | `detect_language(text, k=3, window=500)` | `preprocessing/cleaning.py` |
| `ml/m1/preprocessing/cleaning.py` | 8 noise classes + Unicode normalisation | `clean(text, lang) -> str` | same task |
| `ml/m1/preprocessing/metadata_extractor.py` | Gazette#, effective date, penalty range, principal act regex | `extract_metadata(text) -> GazetteMetadata` | same task |
| `ml/m1/preprocessing/chunking.py` | §-aware → sliding-window hybrid (window=512, stride=64) | `chunk(text, lang) -> list[Chunk]` | `model/inference.py` |
| `ml/m1/model/architecture.py` | `GazetteClassifier` (XLM-R + LoRA + dual head) | `class GazetteClassifier(nn.Module)` | training + inference |
| `ml/m1/model/training.py` | 3-seed loop, AdamW, early-stop, FP16 | `train(config: TrainingConfig) -> ModelArtifact` | `scripts/train_model.py` |
| `ml/m1/model/evaluation.py` | macro-F1, ECE, slice analyses, confusion matrix | `evaluate(model, test_set) -> EvaluationReport` | training + monitoring |
| `ml/m1/model/inference.py` | ONNX Runtime session + Redis cache (SHA-256 key) | `class GazetteInferencer; predict(text) -> Prediction` | `backend/app/tasks/m1/classify_gazette.py` |
| `ml/m1/model/calibration.py` | Temperature scaling | `calibrate(model, val_set) -> float` | training |
| `ml/m1/summarization/marianmt.py` | MarianMT EN→SI/TA, EN→EN summarisation | `summarise(text, target_lang) -> str` | `backend/app/tasks/m1/summarise_gazette.py` |
| `ml/shared/embeddings.py` | `multilingual-e5-base` wrapper | `embed(texts) -> np.ndarray` | secondary-source matching, drift detection |
| `ml/shared/drift.py` | KL-divergence + Population Stability Index | `kl_divergence(p, q)`, `psi(prod_dist, ref_dist)` | `backend/app/tasks/m1/analytics.py` |
| `backend/app/tasks/m1/extract_gazette.py` | Celery task wrapping Stage B | `@app.task extract_gazette(gazette_id)` | scraper after download |
| `backend/app/tasks/m1/classify_gazette.py` | Celery task wrapping Stage D | `@app.task classify_gazette(gazette_id)` | `extract_gazette` chord |
| `backend/app/tasks/m1/analytics.py` | Nightly view refresh + retraining-trigger check | Celery Beat: `0 2 * * *` | scheduler |
| `backend/app/config/feature_flags.py` | Per-stage on/off toggles (env-var driven) | `FLAGS.M1_INFERENCE_ENABLED`, `FLAGS.M1_AUTO_RETRAIN` | every task entrypoint |
| `scraper/spiders/gazette_spider.py` | Scrapy spider for `gazette.lk` + `documents.gov.lk` | Scrapy CLI entrypoint | cron / Celery Beat |
| `storage/models/m1/v*/model_registry.json` | Reproducibility manifest | static JSON read by inference + monitoring | inference, drift detection |

---

## Implementation flow — Stage A → G

Each stage names its folder owner, what gets persisted at the stage boundary, and the Celery task chain link.

| Stage | Owner folder | Persists | Celery task | Trigger | Idempotent? |
|---|---|---|---|---|---|
| **A — Ingestion** | `scraper/` | PDF bytes → `storage/m1/raw/<gazette_no>.pdf` + `m1_regulations` row (`status=fetched`) | `scraper.spiders.gazette_spider` (Scrapy CLI) → posts to `extract_gazette` | Celery Beat `0 */6 * * *` (every 6h) | Yes — gazette# is unique key |
| **B — Extraction** | `ml/m1/extraction/` | Plain text → `m1_regulations.full_text`, `language` enum, `extraction_method` enum, status=`extracted` | `app.tasks.m1.extract_gazette` | After A completes | Yes — re-run overwrites |
| **C — Preprocessing** | `ml/m1/preprocessing/` | Cleaned chunks → in-memory (passed to D); metadata → `m1_regulation_metadata` row | (in same task as D, no boundary persist) | Inline before D | Yes |
| **D — Classification** | `ml/m1/model/` | Category, sectors[], confidence → `m1_regulations.category`, `m1_regulation_sectors`, status=`classified` | `app.tasks.m1.classify_gazette` | After B completes | Yes — model version stored alongside |
| **E — Summarisation** | `ml/m1/summarization/` | 3 summaries (EN/SI/TA) → `m1_regulations.summary_en/si/ta`, status=`summarised` | `app.tasks.m1.summarise_gazette` | After D completes | Yes |
| **F — Alerting** | `backend/app/tasks/m1/alert_dispatch.py` | `m1_propagation_events` rows + outbound email/SMS via SendGrid | `app.tasks.m1.alert_dispatch` | After E completes | **No** — outbound side-effect; needs idempotency key per (regulation, channel, sme) |
| **G — Lag Measurement** | `research/notebooks/` + `backend/app/tasks/m1/analytics.py` | Nightly refresh of `v_m1_regulation_lag_summary` + `v_m1_channel_effectiveness` | Celery Beat `0 2 * * *` | Async to A–F | Yes — view refresh is idempotent |

**Disk vs DB vs memory boundaries (read this if you're wondering where state lives):**
- *Disk:* raw PDFs (`storage/m1/raw/`), OCR cache, ONNX models, dataset parquet files. Everything in `storage/` is gitignored except model `model_registry.json` (which is small, version-controlled).
- *DB:* every regulation has a persistent state machine via `m1_regulations.status` (fetched → extracted → classified → summarised → alerted). Stages B–E each advance the status atomically inside their Celery task transaction.
- *Memory:* preprocessing → inference is a single Celery worker process, no persistence between C and D (saves DB round-trip; cost is no resumability mid-task — re-run the whole classify task on failure).
- *Redis:* inference cache keyed `SHA256(text + gazette_no + published_date)` to avoid cross-gazette contamination. TTL 30 days.

---

## 5. Per-module template (M2 / M3 / M4)

Adding a new module = mechanical copy of M1's tree. The exact recipe:

1. **Create the ML folder:** `cp -r ml/m1/ ml/m2/`. Rename module-prefix constants in `ml/m2/utils/constants.py` (`M1_CATEGORIES` → `M2_CATEGORIES`).
2. **Create the backend task folder:** `cp -r backend/app/tasks/m1/ backend/app/tasks/m2/` and rename Celery task names (must be globally unique — `m1.classify_gazette` → `m2.classify_knowledge_unit`).
3. **Create the service:** `backend/app/services/m2_<name>_service.py`. Re-use `services/shared/audit_service.py` for audit; **do not duplicate audit logic per module.**
4. **Create the DB models + migrations:** `backend/app/models/m2_*.py` + Alembic migration `<timestamp>_create_m2_tables.py`. Module-table names start with `m2_` to keep the namespace clean.
5. **Create the docs:** `cp -r enigmatrix-docs/m1/ enigmatrix-docs/m2/` and adapt the 12 numbered docs + this folder-structure doc. The sub-step companions are module-specific; M2's set will be different from M1's (different stages, different tech choices) but the *skeleton* (Purpose → Detailed process → Tech choices → Worked example → Failure modes → Validation → Cross-refs) is identical.
6. **Cross-module utilities:** put shared embedding code, drift detectors, and rate-limiting helpers in `ml/shared/` (NOT `ml/m2/utils/`). Same for `backend/app/services/shared/`.

> **The cardinal rule:** if M2 needs to *import* anything from `ml/m1/`, that thing belongs in `ml/shared/`. No M2 file imports from `ml/m1/`; no M1 file imports from `ml/m2/`. Module isolation is enforced by convention — a future linter rule will check this.

---

## Upgradability & adaptability rules

- **Version everything.** Model artifacts live under `storage/models/m1/v<MAJOR>.<MINOR>/`. Never overwrite. `v1.0` → `v1.1` is non-breaking (same inputs/outputs, better F1); `v1.0` → `v2.0` is breaking (e.g. category taxonomy changed). The inference service reads the version from `app/config/feature_flags.py:M1_MODEL_VERSION`; rollback = change the env var + restart Fly machine (no rebuild).
- **Keep 2 versions hot.** Fly persistent volume always carries the current + previous version. If a deployed v1.1 fails post-deploy health checks (production F1 drops > 5 pp in the first 24h after canary rollout), `flyctl deploy --env M1_MODEL_VERSION=v1.0` rolls back in < 60 s.
- **Feature flags per stage.** `app/config/feature_flags.py` declares one flag per pipeline stage (`M1_INGESTION_ENABLED`, `M1_INFERENCE_ENABLED`, `M1_AUTO_RETRAIN`, `M1_ALERT_DISPATCH`). Stages can be turned off independently for maintenance or incident response.
- **Progressive rollout.** New model versions go through canary (10% of incoming gazettes) → 50% → 100% over 3 days. Traffic split is a Postgres-backed hash on `gazette_id % 100`, evaluated in the inference task. Per-version production F1 is reported daily; rollback is automatic if canary F1 < (current F1 − 5 pp).
- **Schema migrations are forward-only.** Alembic migrations never `DROP` — they only `ADD` (columns, tables, indexes). Renames go through add-new → backfill → flip-readers → drop-old (4 migrations spread over 2 weeks). This protects the rollback path.

---

## Scalability characteristics

How each stage scales horizontally. Numbers are targets; real capacity confirmed after BUILD_07/11/12 land.

| Stage | Bottleneck | Horizontal scale handle | Capacity at 1× | Capacity at N× |
|---|---|---|---|---|
| **A — Ingestion** | gazette.lk rate limits + Scrapy throughput | parallel spider instances (1 per source) | ~30 gazettes/day (today) | ~300/day at 10× (rate-limit ceiling) |
| **B — Extraction** | Tesseract OCR CPU | Celery worker count (`m1-extract` queue) | ~8 OCR ops/min/worker | linear up to 8 workers (PG conn-pool ceiling) |
| **C — Preprocessing** | trivial (regex + tokenisation) | combined with D in same worker | n/a | n/a |
| **D — Classification** | ONNX Runtime CPU inference | Fly machine count + batching | ~30 inferences/min at batch=8 | linear up to 4 Fly machines |
| **E — Summarisation** | MarianMT (heavier than D) | Celery worker count (`m1-summarise` queue) | ~6 summaries/min/worker | linear up to 4 workers |
| **F — Alerting** | SendGrid rate limits | batched dispatch + retry queue | 100 emails/sec (Pro tier) | tier upgrade |
| **G — Lag Measurement** | Postgres view refresh | nightly batch (no horizontal scale needed) | views refresh in < 30 s at 10 k regulations | scale to 100 k regulations with materialised-view indexes |

**Cost model** (steady state, BUILD_07/11/12 fully shipped, 30 gazettes/day):
- Fly inference: 1× `shared-cpu-1x` @ 1 GB → ~$3/mo. Upgrade path: `shared-cpu-2x` @ 2 GB → ~$12/mo when batched inference saturates.
- Celery workers: 2× `shared-cpu-1x` @ 512 MB → ~$3/mo total.
- Postgres: Supabase free tier (500 MB) → upgrade to Pro ($25/mo) once `m1_*` tables exceed 200 MB (≈ 18 months at current ingestion rate).
- Redis: Upstash free tier (10 k commands/day) → upgrade to Pro ($10/mo) when inference cache hit-rate < 20 %.
- ChromaDB: deferred until BUILD_08 lands the RAG retrieval layer.

---

## Cross-references

**Back to numbered M1 docs:** every numbered doc has a "See also: folder structure" callout pointing here. The mapping:

| Doc | What this folder-spec answers for that doc |
|---|---|
| [01_M1_Research_Problem.md](01_M1_Research_Problem.md) | Where the lag-measurement code lives (Stage G owners) |
| [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) | Which folder owns each of the 9 `m1_*` tables (`backend/app/models/`) and where ingestion writes them (`backend/app/tasks/m1/`) |
| [03_M1_Data_Collection.md](03_M1_Data_Collection.md) | `scraper/`, `ml/m1/extraction/`, status-machine boundaries |
| [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md) | `ml/m1/preprocessing/` ownership + chunking output shape |
| [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) | `ml/m1/model/architecture.py`, `data/samplers.py`, calibration |
| [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) | `ml/m1/model/training.py` + `evaluation.py`; where `model_registry.json` writes |
| [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md) | Fly volume layout, rollback path, inference Celery task |
| [08_M1_Full_System_Architecture.md](08_M1_Full_System_Architecture.md) | The whole tree above is the system architecture view |
| [09_M1_Annotation_Guidelines.md](09_M1_Annotation_Guidelines.md) | `research/data/labeling/` (Label Studio exports) + `tests/m1/fixtures/gold_labels.csv` |
| [10_M1_Sinhala_Tamil_NLP.md](10_M1_Sinhala_Tamil_NLP.md) | `ml/m1/extraction/ocr.py` (Wijesekara), `extraction/language_detection.py` |
| [11_M1_API_Reference.md](11_M1_API_Reference.md) | `backend/app/api/v1/m1_regulations.py` + `services/m1_regulation_service.py` |
| [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md) | `ml/shared/drift.py`, `backend/app/tasks/m1/analytics.py`, `storage/models/m1/v*/model_registry.json` |

**Forward to BUILD phase docs:**
- `enigmatrix-docs/backend/BUILD_PLAN/BUILD_07_Module1_Awareness.md` — when stages A, B, D, E, F, G land.
- `enigmatrix-docs/ml/BUILD_PLAN/BUILD_11_ML_Training_Pipeline.md` — when `ml/m1/data/`, `ml/m1/model/training.py`, `storage/models/m1/`, and `model_registry.json` land.
- `enigmatrix-docs/backend/BUILD_PLAN/BUILD_12_Data_Ingestion_and_Scheduling.md` — when `backend/app/tasks/m1/portal_watcher.py`, `rss_watcher.py`, and Celery Beat config land.
