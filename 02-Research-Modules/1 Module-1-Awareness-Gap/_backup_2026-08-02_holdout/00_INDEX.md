# Module 1 — Regulatory Change Awareness Gap

> **Research Question:** Are regulatory changes reaching Sri Lankan SMEs in time to act — and what is the information lag between gazette publication and SME awareness?

> [!warning] Truth-ledger sync — 2026-08-02
> This index is the module's status ledger and is **current**. Two figures elsewhere in the doc set were stale and have now been corrected everywhere:
> the gold set is **1128 adjudicated rows → 1110 ML rows** (not 800), and the production classifier is **LinearSVC V6**, not XLM-R.
> A full copy of the submitted final report now lives in `final/report/` so every document can cite it directly.
>
> **Canonical record:** [[final/works/11_CLASSIFIER_FREEZE_AND_INTEGRATION|11_CLASSIFIER_FREEZE_AND_INTEGRATION]] · [[18_M1_Dataset_And_Model_Lineage]] · `final/works/evidence/M1_OPERATING_EVIDENCE_2026-08-02.json`
> **Submitted-report copy:** [[final/report/Enigmatrix_Consolidated_Final_Report_FULL|Enigmatrix_Consolidated_Final_Report_FULL]] (Part I = group report, Part II = Module 1 dissertation).

---

## Status

| Dimension                      | Target                             | Status                  |
| ------------------------------ | ---------------------------------- | ----------------------- |
| Category classifier F1 (macro) | ≥ 0.92                             | **PASSED** — V6 TF-IDF LinearSVC = **0.9472** (temporal test), frozen as primary |
| Sector assignment F1 (macro)   | ≥ 0.88                             | **No sector model in production** — the frozen classifier is category-only (`sectors: []`). A 1,103-row no-leak V7 working experiment ran and was rejected; the formal enriched V7 release was not built |
| Sector label coverage          | usable multi-label structure       | **Weak** — 73.2% of gold rows carry no sector, 84% of the rest carry all three; only 48 rows (4.3%) are partial |
| Labeled gazette documents      | ≥ 800                              | 1128 resolved v3 gold rows → 1110 after artifact exclusion; IAA gate passed |
| Propagation data points        | ≥ 800 (200 regulations × 4 stages) | Data collection         |
| SME awareness survey responses | ≥ 100 unique SMEs                  | Instrument, authenticated flow, and public `/portal/m1/survey` route exist; real field responses remain 0/100 |
| Ingestion latency              | ≤ 6 hours from gazette publication | Pipeline deployed       |
| Alert delivery latency         | ≤ 24 hours from publication        | Pipeline deployed       |
| System uptime                  | ≥ 99.9%                            | Monitoring active       |
| Expert verification coverage   | ≥ 30% of production regulations    | In progress             |
| Production classification run  | ≥ 1 end-to-end                     | **Completed** — the frozen model has classified live gazettes; retain the run evidence and complete the remaining quality review |

---

## Current Implementation Update

**As of the 2026-08-02 truth-ledger refresh — Phase 3 model selection and first live integration are closed.**

- The production classifier is **TF-IDF + `LinearSVC(class_weight="balanced")`**, frozen at `models/m1/linearsvc_v6_primary/`. Temporal-test macro-F1 **0.947220**, validation 0.924476, accuracy 0.958084 (160/167). This clears the ≥ 0.92 gate that the V3 baseline (0.9080) missed.
- **XLM-R + LoRA was trained in full and rejected.** Three runs; the best reached 0.969340 *training* macro-F1 and 0.902693 validation but only **0.743563** on the temporal test — a generalization failure, not an optimization one. No ONNX artifact was ever exported.
- The V6 dataset corrected four `EPF_ETF_CHANGE` mislabels, all in the **train** split, so the test split is byte-identical to V5 and every V5/V6 comparison remains valid. Split fixed at 777/166/167 since V4.
- The classifier is **wired into the backend** behind `M1_CLASSIFIER_BACKEND` (default `linearsvc`), and migration `202608010001` is applied to the live Supabase database (`classifier_decision_margin`, `classifier_model_name`).
- **`confidence` is now nullable.** LinearSVC emits an uncalibrated margin, not a probability. Margins may rank; they must never be displayed as percentages. The review threshold is configuration-dependent: the code default is unset and truthfully reports `mode='disabled'`, while `.env.example` opts into the validation-derived candidate `M1_CLASSIFIER_MIN_MARGIN=0.40`. Nine validation errors are too thin to call that operating point frozen.
- **Live integration has moved past the earlier blocker:** gazettes have been classified by the frozen model, `/admin/m1/pipeline/classifier-review` consumes the margin modes, and analytics now records margin/category-distribution drift, queue size, dominant-category concentration, and review correction yield. The 0.40 threshold remains provisional because no live review outcome has been completed.
- **The public survey route is built:** `/portal/m1/survey` carries EN/SI/TA recruitment copy, consent, safe login/register returns, and recruitment-channel attribution. The fieldwork count is still 0/100; software readiness is not participant evidence.
- **The first weighted V7 recovery diagnostic is complete:** seed 42, validation only, category macro-F1 `0.899862`, sector macro-F1 `0.884312`, partial-sector exact match `4/9`. It recovered from collapse but stopped before test/three-seed/export because the category gate and evidence gate were not met.

Full record: [[final/works/11_CLASSIFIER_FREEZE_AND_INTEGRATION|11_CLASSIFIER_FREEZE_AND_INTEGRATION]] · lineage: [17_M1_Repo_Structure_Map.md](17_M1_Repo_Structure_Map.md) and [18_M1_Dataset_And_Model_Lineage.md](18_M1_Dataset_And_Model_Lineage.md) · status ledger: [[final/works/03_FEATURE_CHECKLIST|03_FEATURE_CHECKLIST]].

### Earlier — as of 2026-07-31, Phase 3 had moved beyond planning:

- Calibration was completed for the annotators, with failed/conditional attempts retested before scale-up.
- Batches 02, 03, 04, and 05 were dual-annotated and reduced into `research\data\labeling\gold_standard.csv`.
- Current resolved gold set *at that date*: 800 rows, 800 unique regulation IDs, 40 manually adjudicated disagreement rows, category kappa 0.871534, mean sector kappa 0.863776, SME relevance kappa 0.723518. **Superseded** — Batches 06–07 took the gold set to 1128 rows (v3 category kappa 0.947215), and the ML branch froze at 1110 rows with the fixed 777 / 166 / 167 split.
- The row-count and category/sector IAA gates for starting model-preparation are now met.
- The accepted set was frozen as `gold_standard_v1_800.csv`; deterministic `--by key` split produced 560 train, 120 validation, and 120 test rows.
- TF-IDF baselines are complete: LogReg macro-F1 0.4980 and LinearSVC macro-F1 0.6167.
- CPU LoRA smoke completed with `xlm-roberta-base`, one seed, one epoch, and `gate_pass=false`; this is a pipeline proof only, not model-performance evidence.
- Rare-domain top-up Batches 06 and 07 increased the current gold set to 1128 rows. Current v3 IAA: category kappa 0.947215, mean sector kappa 0.965567, SME relevance kappa 0.914637.
- Current v3 TF-IDF baselines on the stratified split: LogReg macro-F1 0.8627 and LinearSVC macro-F1 0.9080.
- Remaining caution before final model claims: `EPF_ETF_CHANGE` is still sparse with 11 total examples, `PENALTY_ENFORCEMENT` has the weakest current per-class F1, and Batch 06/07 should be manually audited if strict independent annotation evidence is required.

---

## Document Index

| # | File | Contents |
|---|---|---|
| 1 | [01_M1_Research_Problem.md](01_M1_Research_Problem.md) | Abstract, IRD/EPF awareness gap statistics, 4 formal research questions, scope boundaries, success metrics, T0-T9 regulatory diffusion timeline (cabinet → enforcement), two research outputs (alert system + lag dataset), 7-row implementation risk register, manual vs automated pipeline Mermaid |
| 2 | [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) | Primary/secondary data sources, 15-source catalogue (with URL patterns), full schema for all 9 `m1_*` DB tables, `m1_sources` registry, `m1_regulation_changes` (clause-level), `m1_real_world_examples` (JSONB flow), `m1_regulation_penalties`, `m1_court_cases`, 2 analytical views (`v_m1_regulation_lag_summary`, `v_m1_channel_effectiveness`), multi-pin adapter worked example (all tables populated) |
| 3 | [03_M1_Data_Collection.md](03_M1_Data_Collection.md) | Scrapy scraper (4-way comparison), PyMuPDF/pdfplumber/Tesseract chain, PDF type classification (`classify_pdf()`), 3 segmentation strategies (A: heading regex / B: block-gap heuristic / C: LLM fallback), NOT_REGULATORY pre-filter (6 patterns), 2-step secondary-source matching (exact + embedding ≥ 0.78), 7-checkpoint validation table, 6-pitfall table |
| 4 | [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md) | Gazette noise types, 4-way tokenizer comparison (HuggingFace XLM-R selected), 5-step pipeline with code, chunking strategies, Sinhala/Tamil token implications, Mermaid |
| 5 | [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) | 3-step sampling strategy (stratified random → cluster k-means k=20 → active learning), 8-domain + 3-sector task definition, 4-way approach comparison (XLM-R LoRA selected), within-BERT comparison, LoRA config, dual-head architecture, combined loss function |
| 6 | [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) | Temporal split (NOT random — sorted by gazette_published_date), 3-seed reproducibility (seeds 42/1/2), class imbalance + augmentation, AdamW + early stopping, 3-baseline comparison (TF-IDF+LR / TF-IDF+SVM / zero-shot LLM), slice analysis (per-language/year-quarter/text-length/extraction-method), error analysis (4-type taxonomy + `error_analysis_topwrong.csv`), model versioning SQL schema, backfill script, 13-item pre-viva checklist |
| 7 | [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md) | 4-way platform comparison (Fly.io selected), ONNX Runtime CPU serving, INT8 quantization, Redis inference cache, Celery task integration, latency budget table, deployment Mermaid |
| 8 | [08_M1_Full_System_Architecture.md](08_M1_Full_System_Architecture.md) | 6-layer architecture overview, all DB tables, all API route groups, all frontend routes, Celery task graph, full end-to-end Mermaid, T+0:00→T+0:15 happy path timeline, 6-finding research findings table, 4-notebook research structure, 7-checkpoint validation methodology, 9-case edge cases/failure modes table, 10-item definition of done checklist, inter-module connections (M1→M2/M3/M4) |
| 9 | [09_M1_Annotation_Guidelines.md](09_M1_Annotation_Guidelines.md) | 4-way annotation tool comparison (Label Studio selected), Label Studio config XML, full 8-domain decision criteria, 3-sector assignment guidelines, IAA protocol (Cohen's κ ≥ 0.75), annotator qualifications, annotation workflow Mermaid, SME awareness survey instrument (Q1-Q8, 18 channel options, sector-tailored SQL selection) |
| 10 | [10_M1_Sinhala_Tamil_NLP.md](10_M1_Sinhala_Tamil_NLP.md) | Sinhala/Tamil linguistic properties, token-length comparison (EN vs SI vs TA), 4-way language detection comparison (fastText selected), 4-way multilingual model comparison (XLM-R selected), Tesseract OCR for scanned gazettes, Wijesekara font conversion, **§10 NLLB-200 EN→SI/TA translation pipeline (pull-based Colab GPU worker, shipped 2026-07-31)** |
| 11 | [11_M1_API_Reference.md](11_M1_API_Reference.md) | Full API reference — CRUD, classification, verification, sectors, propagation events, SME survey, public endpoint, analytics, backfill endpoint (`POST .../backfill`), model version management (`GET/POST .../models`), channel effectiveness analytics (`GET .../analytics/channel-effectiveness`), error codes, cURL examples |
| 12 | [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md) | SLA targets table, pipeline health checks, confidence distribution drift (KL divergence), estimated production F1, Prometheus metrics, Celery queue monitoring, retraining triggers, DB maintenance, monitoring Mermaid |
| 13 | [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) | Where every M1 file lives + how M2/M3/M4 mirror the layout; 5 design principles; full folder map; Stage A–G implementation flow; per-module template; upgradability + scalability rules |
| 14 | [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) | **M1 frontend tracking workflows** — consolidated index of the 8+1 admin/SME surfaces: pipeline-state, review queue, verification, lag analytics, discovery, awareness survey, compliance tracking, deadline/alert history, and the category × sector reference. |
| 15 | [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) | **Per-folder build guides** — consolidated build reference for ml/, backend/, scraper/, research/, storage/, and docs/, with file tables, start steps, dependencies, and acceptance checks. |
| 16 | [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md) | **Sequenced "start here" guide** — 5 phases (Foundation ✅ / Ingest + extract / Annotation + classification / Schedulers + alerts / Research findings) with concrete next-action call-outs + DoDs + linked detail docs. The developer's daily start screen. |
| 17 | [17_M1_Repo_Structure_Map.md](17_M1_Repo_Structure_Map.md) | **The workspace as measured** (against doc 13's designed tree) — top-level inventory with sizes, the root tidy of 2026-08-01, `documentation/` layout, why `scripts/` was deliberately left flat (26 files reference those paths), the vault-vs-repo doc fork and which copy is canonical, and where new files go. |
| 18 | [18_M1_Dataset_And_Model_Lineage.md](18_M1_Dataset_And_Model_Lineage.md) | **V4 → V5 → V6 dataset lineage and every model trained on them** — per-version label changes, class distribution, per-split SHA256, the five-model comparison table, why the transformer lost, the frozen LinearSVC artifact and its hashes, the confidence contract, and four standing constraints. |
| 19 | [19_M1_Regulation_Summarization.md](19_M1_Regulation_Summarization.md) | **Stage-E summarisation method** — the input contract (raw text + the 6 Stage-C metadata fields + classifier context), a measured diagnostic showing the extractors return a *wrong* gazette number on 31.1% of test rows, a 5-way approach comparison (decisive-constraint table + scored matrix + one real gazette walked through every approach), and the selected **field-grounded constrained generation** design with four faithfulness invariants, a reference-free evaluation protocol, and the novelty claim it supports. |
| 20 | [20_M1_Multitask_Classifier_Upgrade.md](20_M1_Multitask_Classifier_Upgrade.md) | **V7 multitask upgrade** — one shared XLM-R encoder emitting regulation domain (8-way softmax), affected SME sectors (3 sigmoids) and SME relevance **derived** from the sector output so the two can never contradict. Contains the 1,110-row source audit, the executed 1,103-row no-leak working dataset, parser/trainer fixes, smoke and 3-seed rejected run, plus the still-unbuilt formal enriched V7 package. Weighted-loss recovery and fresh evaluation data are required before any promotion work. |

---

## Consolidated Main Docs

The former sub-step companion files have been merged into their matching parent documents. Each parent now contains the full chain of why the step exists, how it works, what it outputs, and how that output is used by the next Module 1 stage.

| Parent | Merged coverage now inside the parent |
|---|---|
| [01_M1_Research_Problem.md](01_M1_Research_Problem.md) | Research motivation evidence, pre-pilot scan, evidence limitations |
| [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) | Data source catalogue, schema validation, governance/retention, worked examples |
| [03_M1_Data_Collection.md](03_M1_Data_Collection.md) | PDF extraction, gazette segmentation, secondary-source integration |
| [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md) | Noise removal, metadata extraction, text chunking strategy |
| [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) | Sampling strategy, architecture comparison, LoRA hyperparameters |
| [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) | Data augmentation and slice-analysis framework |
| [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md) | ONNX export/quantization and Fly.io operations |
| [08_M1_Full_System_Architecture.md](08_M1_Full_System_Architecture.md) | Research findings extraction and failure-mode runbook |
| [09_M1_Annotation_Guidelines.md](09_M1_Annotation_Guidelines.md) | Category taxonomy examples, annotation workflow/IAA protocol, SME survey instrument |
| [10_M1_Sinhala_Tamil_NLP.md](10_M1_Sinhala_Tamil_NLP.md) | Language detection/routing and OCR/Wijesekara conversion |
| [11_M1_API_Reference.md](11_M1_API_Reference.md) | API authentication/authorization and integration examples |
| [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md) | Performance monitoring/alerting and retraining/rollback |
| [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) | Single structural specification |
| [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) | All admin/SME tracking workflows and category/sector workflow rules |
| [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) | ML, backend, scraper, research, storage, and docs folder guides |
| [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md) | Single sequenced roadmap |
| [17_M1_Repo_Structure_Map.md](17_M1_Repo_Structure_Map.md) | Measured workspace/repository inventory; companion to doc 13's design |
| [18_M1_Dataset_And_Model_Lineage.md](18_M1_Dataset_And_Model_Lineage.md) | Dataset versions, model comparison, frozen artifact hashes, confidence contract |
| [19_M1_Regulation_Summarization.md](19_M1_Regulation_Summarization.md) | Stage-E summarisation: input contract, approach comparison, faithfulness invariants, evaluation |
| [20_M1_Multitask_Classifier_Upgrade.md](20_M1_Multitask_Classifier_Upgrade.md) | V7 multitask: domain + sectors + derived relevance, V6 audit, gates, steps 41–53 |

**File counts:** 20 numbered main docs + this README = **21 canonical Markdown files** at the Module 1 root. Historical implementation notes remain in `final/`, `findings/`, `local-dev/`, and `planned-for-development/`, but root companion files have been retired.

---

## Frontend Tracking Workflows

The frontend-side UI workflows for this module live in this same folder as [`14_M1_Tracking_Workflows.md`](14_M1_Tracking_Workflows.md). That one file now carries the former pipeline-state triage, needs-review queue, expert verification, lag analytics, regulation discovery, awareness survey, compliance tracker, deadline/alert history, and category × sector workflow details. The screen-by-screen reference for those routes lives in [`04-Technology-Stack/frontend/SETUP/12_UI_Screens_and_Loading.md`](../../04-Technology-Stack/frontend/SETUP/12_UI_Screens_and_Loading.md).

The frontend route table that maps these workflows to real frontend files is reconciled in [08_M1_Full_System_Architecture.md §4](08_M1_Full_System_Architecture.md) (earlier placeholder component names like `RegulationsListPage` have been replaced with real file paths).

---

## Pipeline at a Glance

| Stage | Name               | What Happens                                                                        |
| ----- | ------------------ | ----------------------------------------------------------------------------------- |
| A     | Ingestion          | Scrapy scrapes `gazette.lk` + `documents.gov.lk` every 6 hours; PDFs stored locally |
| B     | Extraction         | PyMuPDF → pdfplumber → Tesseract OCR; fastText language detection                   |
| C     | Classification     | **TF-IDF + LinearSVC** on the 8-domain taxonomy, frozen 2026-08-01 (test macro-F1 0.9472). Category only — no sector head, and `confidence` is `null` by design. The XLM-R dual-head path exists but was never promoted. See [18_M1_Dataset_And_Model_Lineage.md](18_M1_Dataset_And_Model_Lineage.md) |
| D     | Secondary Tracking | Watchers on IRD, EPF, ETF, eROC portals; 5 news RSS feeds (every 2h)                |
| E     | Summarisation      | **Backend slice shipped and live-backfilled.** The deterministic 80-English audit passed 80/80; four false sentence-count reviews were repaired, leaving 7 genuine low-margin reviews. Human faithfulness review, review UI, and full coverage remain open. See [19_M1_Regulation_Summarization.md](19_M1_Regulation_Summarization.md) |
| E2    | Translation        | NLLB-200 pull worker shipped, but the SI/TA numeric audit passed only 10/152 checks. 144 replacement jobs are queued; worker/tunnel recovery and re-audit remain open. See [10_M1_Sinhala_Tamil_NLP.md §10](10_M1_Sinhala_Tamil_NLP.md) |
| F     | Alerting           | Celery + Redis → sector-matched SME notifications (email/SMS/dashboard)             |
| G     | Lag Measurement    | Propagation timestamps + SME survey → research findings (RQ3, RQ4)                  |

---

## Key Database Entities

| Table | Purpose |
|---|---|
| `m1_regulations` | Central regulation record — all pipeline stages write here |
| `m1_regulation_sectors` | M2M: regulation ↔ sector codes |
| `m1_propagation_events` | One row per (regulation × channel) with `first_seen_at` timestamp |
| `m1_sme_awareness_responses` | Survey answers: awareness date, source channel, action taken |
| `m1_sources` | Source registry — 15 rows covering all official portals and news channels |
| `m1_regulation_changes` | Clause-level diff: old_value → new_value per clause reference |
| `m1_real_world_examples` | SME impact scenario with operational_flow_steps JSONB |
| `m1_regulation_penalties` | Violation type, penalty range (LKR), imprisonment cap |
| `m1_court_cases` | Precedent cases — case_number, court, fine_imposed_lkr, outcome |
| `v_m1_regulation_lag_summary` | View: 5 lag columns + SME count + median lag per regulation |
| `v_m1_channel_effectiveness` | View: median lag ranked by channel (ASC) — produces Finding F4 |

---

## Research Questions

| # | Question | Success Criterion |
|---|---|---|
| RQ1 | Can NLP classify Sri Lankan gazettes into SME-relevant categories with F1 ≥ 0.92? | Macro F1 ≥ 0.92 on held-out test set |
| RQ2 | Can multilingual models handle EN/SI/TA gazette text without per-language pipelines? | F1 within 5% across all three languages |
| RQ3 | What is the median information lag between gazette publication and SME awareness? | Dataset of ≥ 200 regulations × ≥ 4 stages |
| RQ4 | Which dissemination channels deliver regulatory information fastest? | Ranked channel table with median lag in days |

---

## Key Technology Choices

| Component            | Choice                                   | Alternative Considered              |
| -------------------- | ---------------------------------------- | ----------------------------------- |
| Gazette scraper      | Scrapy                                   | BeautifulSoup, Playwright, Selenium |
| PDF extractor        | PyMuPDF → pdfplumber → Tesseract (chain) | Apache Tika, PaddleOCR              |
| Language detection   | fastText `lid.176.bin`                   | langdetect, langid, cld3            |
| Tokenizer            | HuggingFace XLM-R SentencePiece          | spaCy, NLTK, IndicNLP               |
| Classification model | `facebook/xlm-roberta-base` + LoRA       | mBERT, IndicBERT, GPT-4 zero-shot   |
| Serving format       | ONNX Runtime (CPU)                       | Raw PyTorch, TorchServe             |
| Deployment platform  | Fly.io (sin region)                      | Render, Railway, AWS SageMaker      |
| Annotation tool      | Label Studio                             | Prodigy, Doccano, custom            |

---

## Backend Source Files

> **Implementation status as of 2026-05-14:** The admin-CRUD slice (manual regulation entry + expert verification) is shipped. Everything else is 🔲 **Deferred — lands with BUILD_07 (ingest pipeline), BUILD_11 (ML training/inference), BUILD_12 (schedulers + monitoring)**. The list below is the *target* layout — see [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) for the full tree.

- ✅ `backend/app/api/v1/m1_regulations.py` — Admin CRUD endpoint definitions
- ✅ `backend/app/services/m1_regulation_service.py` — Admin-slice business logic
- ✅ `backend/app/schemas/m1.py` — Pydantic request/response schemas
- 🟡 `backend/app/models/m1_regulation.py` — SQLAlchemy ORM (5 demo rows seeded; the 9-table schema lands with BUILD_07)
- 🔲 `backend/app/tasks/m1/gazette_scraper.py` — Scraping Celery tasks (BUILD_07)
- 🔲 `backend/app/tasks/m1/classify_gazette.py` — Classification Celery task (BUILD_07)
- 🔲 `ml/m1/model/inference.py` — ONNX inference engine (BUILD_07/11)
- 🔲 `scraper/spiders/gazette_spider.py` — Scrapy spider (BUILD_07)
- 🔲 `research/notebooks/findings_lag_analysis.ipynb` — F1–F3 (BUILD_07)
- 🔲 `research/notebooks/findings_classifier_evaluation.ipynb` — Model evaluation suite (BUILD_11)
- 🔲 `research/notebooks/findings_alert_effectiveness.ipynb` — F6 DiD analysis (BUILD_07)
- 🔲 `research/notebooks/findings_secondary_diffusion.ipynb` — F4 channel effectiveness (BUILD_07)

---

## Related Files

The following older M1 documents (outside the `m1/` directory) served as the source for the deeper content merged into this documentation set. They are retained as BUILD/implementation context and should not be edited:

| File | Role |
|---|---|
| `backend/research/09_Module1_Architecture_Overview.md` | Two-outputs framing, 12-week implementation plan, risk register |
| `backend/research/10_Module1_Gazette_PDF_Extraction_Pipeline.md` | `classify_pdf()` code, segmentation A/B/C, NOT_REGULATORY filter, validation/pitfalls tables |
| `ml/research/11_Module1_NLP_Classifier_Training.md` | Sampling strategy, temporal split, baseline code, slice analysis, error taxonomy, versioning schema, backfill script, 13-item checklist |
| `backend/research/12_Module1_End_to_End_Workflow.md` | Happy path timeline, secondary-source matching, 9-failure-modes table, definition-of-done, research findings table, 4 notebooks structure, inter-module connections |
| `backend/BUILD_PLAN/BUILD_07_Module1_Awareness.md` | Stage-wise acceptance criteria, cross-module linkage (M1→M2→M3 chain), code paths |
| `backend/research/module_1_and_4_data_architecture.md` | T0-T9 diffusion timeline, 15-source catalogue, 5 additional DB tables, 2 analytical views, multi-pin adapter worked example, survey instrument Q1-Q8 |

---

## ∞ Final-report reconciliation (2026-08-02)

*Added by the 2026-08-02 consolidation pass. Maps this document onto the submitted final report and records where the two disagree.*

**Where this document appears in the report:** the whole report — Part I is the four-member group draft, Part II is the Module 1 dissertation.

### The report is one revision behind this ledger

| Claim | Submitted report says | Truth ledger (2026-08-02) |
|---|---|---|
| Production model | XLM-R + LoRA, dual head, ONNX INT8 | **TF-IDF + LinearSVC V6**, frozen |
| XLM-R status | the production architecture | **trained and rejected** — temporal test 0.743563 |
| Headline score | test macro-F1 0.6415, `gate_pass: false` | **0.947220** temporal test, gate passed |
| Confidence | calibrated probability, gate 0.55 | uncalibrated **margin**; `confidence: null`; threshold 0.40 provisional |
| Sector output | 3-label sigmoid head, served | **no sector model in production** — `sectors: []` |
| Gold dataset | 800 rows | **1128 gold → 1110 ML rows**, fixed split 777 / 166 / 167 |
| ONNX artifact | exported and serving | **never exported** |

**How to read this.** The report is the *earlier* artefact. Where the two disagree, this vault is authoritative and the report is a record of what was believed at submission time. The report's XLM-R material is preserved as design rationale, not as a description of what serves.

### Operating evidence backing this ledger

From `final/works/evidence/M1_OPERATING_EVIDENCE_2026-08-02.json` (generated 2026-08-01T19:30:15Z):

| Signal | Value |
|---|---:|
| Classifier backend | `linearsvc` |
| Regulations classified | 898 |
| Rows carrying a margin | 898 |
| Margin min / p10 / p50 / p90 / max | 0.008653 / 1.12149 / 1.809804 / 2.081984 / 2.245461 |
| Configured review threshold | 0.40 |
| Rows below threshold (active queue) | 18 |
| Threshold decision | `provisional_no_review_outcomes` |
| Stage-E English summary pass rate | 80 / 80 = 100% |
| Stage-E numeric-locale pass rate | 10 / 152 = **6.58%** |
| Stage-E rows requiring review | 7 |
| SME survey sessions / completed | 0 / 0 against a target of 100 |

Two of those are the honest weak points: **numeric-locale checking passes 6.58%**, and **SME recruitment stands at zero against a target of 100**. Neither is visible in the submitted report.
