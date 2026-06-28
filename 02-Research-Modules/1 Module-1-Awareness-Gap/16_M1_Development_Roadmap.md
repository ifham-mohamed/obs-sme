# 16 — M1 Development Roadmap

> Where to start, what to build next, in what order — with a link to the doc that explains each step.
> **Audience:** the developer (or team) starting M1 implementation work. Status-aware: every phase tells you what's done vs what's next.
> **See also:** [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) (the spec) · [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) (per-folder build guides).

---

## Where M1 stands today (2026-05-14)

| Surface | Status | Notes |
|---|---|---|
| Admin CRUD for regulations | ✅ Shipped | `/admin/regulations` list + detail + edit + flow canvas; verify button; bulk-verify |
| Audit log (Session 14) | ✅ Shipped | Singular `audit_log` table; passive HTTP middleware; record-level events |
| Unified survey flow (Session 15) | ✅ Shipped | `/surveys/regulation/[id]` runs M1→M2→M3 wizard; `m3_field_mapping` data-driven projection |
| Seed data | ✅ Shipped | 5 demo regulations (`VAT_2024_AMD`, `EPF_2024_RATE`, multi-pin adapter, etc.) |
| M1 docs base | ✅ Shipped | 53 files in `enigmatrix-docs/m1/` covering research + design |
| Ingest pipeline (Stage A–B+) | ✅ Shipped | Sessions 23/25/26/28/30/31/32 (F-145 → F-155). Phase 2 complete: spider → extract_gazette → preprocess_gazette_task chained; rows flow `ingested → extracted → preprocessed` with all metadata fields populated and multi-penalty junction filled. |
| ML training + classifier (Stage D) | 🔲 Deferred | BUILD_11 — no XLM-R fine-tune, no ONNX model |
| Summarisation (Stage E) | 🔲 Deferred | BUILD_07 — no MarianMT integration |
| Alert dispatch (Stage F) | 🔲 Deferred | BUILD_07 — no email/SMS pipeline |
| Schedulers + portal watchers | 🔲 Deferred | BUILD_12 — no Celery Beat, no IRD/EPF watchers |
| Lag-analytics UI (Stage G) | 🔲 Deferred | BUILD_13 — no admin dashboard |

The roadmap below sequences the deferred surfaces into 4 phases. The numbered steps inside each phase are dependency-ordered: step (b) needs step (a) done; you can't skip.

---

## Phase 1 — Foundation (✅ DONE)

Already shipped. You're inheriting:
- Admin CRUD (regulation manual entry / edit / verify / archive)
- Audit-log writes on every regulation mutation
- Unified survey engine (one session crosses M1/M2/M3 questions, branching per `next_question_rules`)
- 5 seeded demo regulations + the awareness Q1–Q8 instrument

**You don't need to rebuild any of this.** Skip to Phase 2.

---

## Phase 2 — Ingest + extraction (BUILD_07 §A–B)

**Goal:** new gazettes flow automatically from `gazette.lk` → `m1_regulations.status='extracted'` with cleaned text.

### Step 2a — Scrapy gazette spider

- **Read first:** [03_M1_Data_Collection.md §1 (Scrapy framework choice)](03_M1_Data_Collection.md) + [03_M1_1_PDF_Extraction_Chain.md](03_M1_1_PDF_Extraction_Chain.md).
- **Build:** `scraper/spiders/gazette_spider.py`. Targets `gazette.lk` + `documents.gov.lk`. Output = downloaded PDF + a queued Celery task.
- **DoD:** running `scrapy crawl gazette_spider` against a sample-day URL produces N PDF files in `storage/m1/raw/` + N new rows in `m1_regulations` (`status='ingested'`).
- **Do this next:** open [03_M1_Data_Collection.md §1.3](03_M1_Data_Collection.md) and copy the spider scaffold into `scraper/spiders/gazette_spider.py`.

### Step 2b — Celery task wiring

- **Read first:** [03_M1_Data_Collection.md §6.1 (Celery retry interaction)](03_M1_Data_Collection.md).
- **Build:** `backend/app/tasks/m1/gazette_scraper.py` (wraps the spider) + `backend/app/tasks/m1/extract_gazette.py` (Stage B). Celery Beat triggers every 6h.
- **DoD:** Celery picks up the gazette + extracts text via PyMuPDF/pdfplumber/Tesseract chain; row advances to `status='extracted'`.
- **Do this next:** define the Celery task signatures in `backend/app/tasks/m1/__init__.py`; wire `extract_gazette` to fire after `gazette_scraper`.

### Step 2c — PDF type classifier + extraction chain

- **Read first:** [03_M1_1_PDF_Extraction_Chain.md](03_M1_1_PDF_Extraction_Chain.md) (covers the 3-tier `text_pdf | hybrid | scanned` decision + the chained PyMuPDF → pdfplumber → Tesseract fallback).
- **Build:** `ml/m1/extraction/pdf_classifier.py` + `text_extractors.py` + `ocr.py`. The `classify_pdf()` function uses character-density heuristics (text_pdf > 200 chars/page, scanned < 30 chars/page, hybrid between).
- **DoD:** 50-PDF hand-audit shows ≥ 95 % correct classification; OCR CER ≤ 10 % on Sinhala/Tamil samples.
- **Do this next:** copy the `classify_pdf()` skeleton from [03_M1_1 §1](03_M1_1_PDF_Extraction_Chain.md) and write the unit test against a fixture PDF first.

### Step 2d — Language detection + per-line routing

- **Read first:** [10_M1_1_Language_Detection_Routing.md](10_M1_1_Language_Detection_Routing.md) + [10_M1_2_OCR_Wijesekara_Conversion.md](10_M1_2_OCR_Wijesekara_Conversion.md).
- **Build:** `ml/m1/extraction/language_detection.py` (fastText `lid.176.bin` with 500-char window) + Wijesekara conversion in `ocr.py`.
- **DoD:** language detection accuracy ≥ 95 % on 100-doc hand-labeled set; pre-2010 Sinhala docs convert correctly.
- **Do this next:** download `lid.176.bin` to `storage/models/m1/baseline/` + wire the detector inline.

### Step 2e — Preprocessing chain (noise removal, metadata extraction, chunking)

- **Read first:** [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md) + sub-step companions [04_M1_1](04_M1_1_Gazette_Noise_Removal.md) · [04_M1_2](04_M1_2_Metadata_Extraction_Patterns.md) · [04_M1_3](04_M1_3_Text_Chunking_Strategy.md).
- **Build:** `ml/m1/preprocessing/cleaning.py` + `metadata_extractor.py` + `chunking.py`.
- **DoD:** every ingested gazette ends Phase 2 with: cleaned `raw_text`, extracted `gazette_number` / `effective_date` / `penalty_range_lkr` / `principal_act_amended`, and chunked text ready for Stage D.
- **Status:** ✅ Shipped Session 31 / F-154 (ml-package only; backend persistence + Celery wiring in Step 2f).

### Step 2f — Wire preprocessing into Celery pipeline + DB persistence

- **Read first:** [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md) + [04_M1_2_Metadata_Extraction_Patterns.md §3.3](04_M1_2_Metadata_Extraction_Patterns.md) (the `m1_regulation_penalties` junction).
- **Build:** Alembic migration adding `cleaned_text` + `amendment_type` columns; extending the status CHECK enum with `preprocessed`; `m1_regulation_penalties` junction table; `M1RegulationPenalty` ORM + Pydantic schema; new `preprocess_gazette_task` Celery task chained automatically from `extract_gazette`.
- **DoD:** end-to-end Celery chain takes a fresh PDF from spider through `status='preprocessed'` with all 4 DoD metadata fields populated and multi-penalty rows persisted.
- **Status:** ✅ Shipped Session 32 / F-155.

**Phase 2 DoD (overall):** invoking the pipeline on a fresh `gazette.lk` URL ends with `m1_regulations` row at `status='preprocessed'`, all 4 metadata fields populated (`gazette_number` / `effective_date` / `penalty_range_lkr` / `principal_act_amended`), and `m1_regulation_penalties` rows for every penalty clause. Status badges in 14_M1_1 ([Pipeline State Tracking](14_M1_1_Admin_Pipeline_State_Tracking.md)) flip from 🟡 to ✅ on this surface. **Phase 2 complete as of 2026-05-17.**

---

## Phase 3 — Annotation + classification (BUILD_07 §C–D + BUILD_11)

**Goal:** the model classifies new gazettes at macro-F1 ≥ 0.92 and serves predictions via ONNX from Fly.io.

### Step 3a — Label Studio setup + calibration test

- **Read first:** [09_M1_Annotation_Guidelines.md](09_M1_Annotation_Guidelines.md) + [09_M1_2_Annotation_Workflow_IAA_Protocol.md](09_M1_2_Annotation_Workflow_IAA_Protocol.md).
- **Build:** Label Studio project XML config + 20-doc calibration set in `research/data/calibration_set_v1.csv`.
- **DoD:** annotators recruited; ≥ 60 % pass the calibration test (κ ≥ 0.80 first attempt).
- **Do this next:** copy the XML config from [09 §1.2](09_M1_Annotation_Guidelines.md) into your Label Studio instance.

### Step 3b — Sample the first 300 labelling examples

- **Read first:** [05_M1_1_Sampling_Strategy.md](05_M1_1_Sampling_Strategy.md).
- **Build:** `scripts/sample_for_labeling.py` (stratified-by-year-language + k-means topical diversity).
- **DoD:** `research/data/labeling/batch_01.csv` with 200 stratified + 40 k-means-diverse + 10 minority-class hand-picks.
- **Do this next:** run the sampler against the extracted gazettes from Phase 2, send batch_01 to Label Studio.

### Step 3c — Iterate to 800 labels with active learning

- **Read first:** [05_M1_Model_Architecture.md §1.3 (active-learning baseline)](05_M1_Model_Architecture.md).
- **Build:** AL baseline (TF-IDF + LR) + uncertainty-sampling acquisition function. Iterate batches 2–4 (200 docs each) over ~6 weeks.
- **DoD:** 800 labels in `gold_standard.csv` (≥ 50 per category); IAA on dual-annotated subset ≥ 0.75 κ.

### Step 3d — Train XLM-R + LoRA classifier

- **Read first:** [05_M1_Model_Architecture.md §3–4](05_M1_Model_Architecture.md) + [05_M1_3_LoRA_Hyperparameter_Justification.md](05_M1_3_LoRA_Hyperparameter_Justification.md) + [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) + augmentation companion [06_M1_1](06_M1_1_Data_Augmentation_Strategy.md).
- **Build:** `ml/m1/model/architecture.py` (GazetteClassifier dual head) + `training.py` (3-seed loop + AdamW + early-stop + FP16).
- **DoD:** 3-seed mean macro-F1 ≥ 0.92; per-language F1 hits EN ≥ 0.93, SI ≥ 0.88, TA ≥ 0.86; reproducibility hash written to `model_registry.json`.
- **Do this next:** start by hard-coding the small LoRA ablation (`r ∈ {8, 16, 32}`) from [05_M1_3](05_M1_3_LoRA_Hyperparameter_Justification.md) and run on the first 300 labels.

### Step 3e — Eval + slice analysis

- **Read first:** [06_M1_2_Slice_Analysis_Framework.md](06_M1_2_Slice_Analysis_Framework.md).
- **Build:** `ml/m1/model/evaluation.py` — per-language, per-quarter, per-text-length, per-extraction-method slices.
- **DoD:** no slice cliff > 8 pp below the macro-F1; confidence-bucket monotonicity verified.

### Step 3f — ONNX export + Fly.io deploy

- **Read first:** [07_M1_1_ONNX_Export_Quantization.md](07_M1_1_ONNX_Export_Quantization.md) + [07_M1_2_Fly_io_Deployment_Operations.md](07_M1_2_Fly_io_Deployment_Operations.md).
- **Build:** `ml/m1/model/export_onnx.py` + `quantize.py`; deploy to Fly with `M1_MODEL_VERSION=v1.0`.
- **DoD:** INT8 macro-F1 within 1.5 pp of FP32; latency p95 ≤ 2 s on `shared-cpu-1x`; rollback procedure tested.

**Phase 3 DoD (overall):** new gazettes from Phase 2 auto-classify; `m1_regulations.change_category` + `affected_sectors[]` + `confidence` populate via the Fly inference task. Status badges in [14_M1_2 (review queue)](14_M1_2_Admin_Review_Queue_Triage.md) flip from 🔲 to 🟡 (queue UI still deferred).

---

## Phase 4 — Schedulers, alerts, lag tracking (BUILD_12)

**Goal:** the pipeline runs autonomously on cron; alerts dispatch within 24 h; lag data accumulates in `m1_propagation_events`.

### Step 4a — Portal + RSS watchers

- **Read first:** [03_M1_3_Secondary_Source_Integration.md](03_M1_3_Secondary_Source_Integration.md) + [02_M1_1_Data_Sources_Catalogue.md](02_M1_1_Data_Sources_Catalogue.md).
- **Build:** `backend/app/tasks/m1/portal_watcher.py` + `rss_watcher.py`. 15-source registry from `m1_sources` table.
- **DoD:** every 2 h, watchers scan the 15 sources + write `m1_propagation_events` rows with proper match_method/match_confidence.

### Step 4b — Alert dispatch with batching

- **Read first:** [08_M1_Full_System_Architecture.md §8.1 (alert batching)](08_M1_Full_System_Architecture.md).
- **Build:** `backend/app/tasks/m1/alert_dispatch.py` (SendGrid + Twilio + chunked dispatch with rate-limit awareness).
- **DoD:** for a high-fan-out regulation (≥ 500 matched SMEs), alerts deliver within 1 h p99; idempotency on `(regulation_id, sme_id, channel)`.

### Step 4c — Nightly view refresh + drift detection

- **Read first:** [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md) + [12_M1_1_Performance_Monitoring_Alerting.md](12_M1_1_Performance_Monitoring_Alerting.md).
- **Build:** `backend/app/tasks/m1/analytics.py` — nightly REFRESH of `v_m1_regulation_lag_summary` + KL-divergence drift check.
- **DoD:** drift trigger fires correctly on synthetic drift; SLA dashboard data populates.

**Phase 4 DoD (overall):** the pipeline runs end-to-end without human intervention; lag data flows to the views. SME-side [14_M1_8 (deadline + alerts)](14_M1_8_SME_Deadline_Alert_History.md) status flips from 🔲 to 🟡 (UI deferred to BUILD_13).

---

## Phase 5 — Research findings + survey deployment

**Goal:** F1–F6 findings are computed end-to-end; SME survey is in production; thesis chapter is data-ready.

### Step 5a — SME survey deployment

- **Read first:** [09_M1_3_SME_Survey_Instrument.md](09_M1_3_SME_Survey_Instrument.md).
- **Build:** survey portal embed at `/portal/m1/survey` (the page exists; wire up to the 9-regulation selection SQL); partner outreach (NEDA, Chamber).
- **DoD:** ≥ 100 unique SME respondents with all 9 regulations answered (10/sector minimum).

### Step 5b — F1–F6 findings extraction

- **Read first:** [08_M1_1_Research_Findings_Extraction.md](08_M1_1_Research_Findings_Extraction.md).
- **Build:** the four `research/notebooks/findings_*.ipynb` files. Each runs end-to-end against the production replica.
- **DoD:** every finding (F1–F6) has its median + bootstrap CI + statistical test result; pre-registration honoured.

### Step 5c — Retraining cadence + auto-rollback

- **Read first:** [12_M1_2_Retraining_Deployment_Rollback.md](12_M1_2_Retraining_Deployment_Rollback.md).
- **Build:** retraining script (`scripts/retrain.py`) + canary rollout helper. Wire to a `m1_retraining_runs` table.
- **DoD:** quarterly retraining dry-run completes end-to-end on staging; auto-rollback fires correctly on synthetic F1 drop.

**Phase 5 DoD (overall):** thesis-ready dataset. The platform is the research vehicle and produces the empirical contribution simultaneously.

---

## Tracking-workflow surfaces — when each ships

These cross-reference [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) — which UI surfaces become real at which phase. The detail docs (14_M1_1..9) describe the *intended* workflow; this table tells you *when* it becomes available.

| Surface | Audience | Ships in | Doc |
|---|---|---|---|
| A1 — Pipeline-state tracking | Admin | Phase 2 (data) + BUILD_13 (UI) | [14_M1_1](14_M1_1_Admin_Pipeline_State_Tracking.md) |
| A2 — Review queue triage | Admin | Phase 3 (data) + BUILD_13 (UI) | [14_M1_2](14_M1_2_Admin_Review_Queue_Triage.md) |
| A3 — Expert verification | Admin | ✅ Already shipped (Phase 1) | [14_M1_3](14_M1_3_Admin_Expert_Verification.md) |
| A4 — Lag analytics dashboard | Admin | Phase 4 (data) + BUILD_13 (UI) | [14_M1_4](14_M1_4_Admin_Lag_Analytics.md) |
| S1 — Regulation discovery (sector filter) | SME | Phase 4 (data) + BUILD_13 (UI) | [14_M1_5](14_M1_5_SME_Regulation_Discovery.md) |
| S2 — Awareness survey participation | SME | ✅ Already shipped (Phase 1) | [14_M1_6](14_M1_6_SME_Awareness_Survey.md) |
| S3 — Compliance / action-taken tracker | SME | Phase 5 (data) + BUILD_13 (UI) | [14_M1_7](14_M1_7_SME_Compliance_Action_Tracking.md) |
| S4 — Deadline + alert history | SME | Phase 4 (data) + BUILD_13 (UI) | [14_M1_8](14_M1_8_SME_Deadline_Alert_History.md) |
| X9 — Category × Sector workflows | Both | Reference doc — applies at every phase | [14_M1_9](14_M1_9_Category_Sector_Workflows.md) |

---

## How to use this roadmap

- **Today, after onboarding:** start with **Step 2a** above. The Scrapy spider is your first concrete piece of code.
- **Each step ends with "Do this next."** Open the linked detail doc, copy the scaffold or read the spec, and start there.
- **Each phase ends with a DoD.** Track yourself against it.
- **If a step's linked doc is missing/incomplete:** open the relevant BUILD_07/11/12 doc in `enigmatrix-docs/backend/BUILD_PLAN/` or `enigmatrix-docs/ml/BUILD_PLAN/` and flesh out the spec first.
- **For per-folder build context** (what every file in `ml/m1/` owns + how to start): see [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md).

## Cross-references

- Folder spec: [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md)
- Per-folder build guides: [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)
- Tracking workflows: [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md)
- Module 1 doc index: [README.md](README.md)
