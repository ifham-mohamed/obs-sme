# Module 1 — Documentation Feature Checklist

> A task-oriented map of the consolidated **Module 1 documentation set** (`1 Module-1-Awareness-Gap/`). Each numbered parent document is the canonical one-file source for its area. Former companion sub-docs are represented below as linked subtasks that point into the relevant parent document sections.
>
> Reading order / "start here" is [[16_M1_Development_Roadmap]]; the annotated master map is [[00_INDEX]]. The raw code-feature ledger (F-01…F-242) lives in the vault `FEATURES.md`.

**Legend** — `[x]` shipped + verified · `[~]` code-complete / partial, pending an env/data/GPU gate · `[ ]` deferred or not started.

**How to read this checklist:** each numbered section has one **parent task** and several **subtasks**. The subtask links go to real headings inside the parent `.md` file. The last column explains why that subtask exists and where its output is used next.

---

## 00 · Index & Orientation — [[00_INDEX]]

**Parent task:** [x] Keep the Module 1 documentation navigable after consolidation.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[00_INDEX#Status|Status table]] | Track the current research, data, annotation, deployment, and monitoring state. Used by planning notes and review conversations to see what is live vs pending. |
| [x] | [[00_INDEX#Document Index|Document index]] | List the 16 numbered parent docs and their scope. Used as the primary entry point for the whole module. |
| [x] | [[00_INDEX#Consolidated Main Docs|Consolidated main docs]] | Map retired companion topics into their parent files. Used to prevent broken links and duplicate sub-docs. |
| [x] | [[00_INDEX#Pipeline at a Glance|Pipeline at a glance]] | Summarise stages A–G from ingestion to lag measurement. Used by roadmap, architecture, and implementation guides. |
| [x] | [[00_INDEX#Key Database Entities|Key database entities]] | Name the core `m1_*` tables and views. Used by data requirements, API, tracking UI, and findings notebooks. |
| [x] | [[00_INDEX#Research Questions|Research questions]] | Keep RQ1–RQ4 visible from the index. Used by research problem, findings extraction, and thesis reporting. |

## 01 · Research Problem — [[01_M1_Research_Problem]]

**Parent task:** [~] Prove the regulatory-awareness gap, define the research scope, and establish the success criteria.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[01_M1_Research_Problem#0. Where This Document Sits in the Pipeline|Pipeline position]] | Explain why the problem statement comes before data, model, and UI work. Used to justify the rest of M1. |
| [~] | [[01_M1_Research_Problem#1. Introduction|Introduction and motivation]] | Present the Sri Lankan SME regulatory-awareness problem and the evidence base. Feeds RQ framing and survey design. |
| [x] | [[01_M1_Research_Problem#2. Problem Statement|Problem statement]] | Define the exact failure M1 addresses: late discovery of gazetted changes. Used by scope, architecture, and evaluation. |
| [x] | [[01_M1_Research_Problem#3. Research Questions|Research questions]] | Formalise RQ1–RQ4. Used by model metrics, lag views, and findings notebooks. |
| [x] | [[01_M1_Research_Problem#4. Scope and Boundaries|Scope and boundaries]] | Separate in-scope SME-relevant regulations from out-of-scope legal advisory work. Used by taxonomy and UI expectations. |
| [x] | [[01_M1_Research_Problem#5. Success Metrics|Success metrics]] | Define F1, lag, response-count, and uptime targets. Used by training, monitoring, and roadmap DoDs. |
| [~] | [[01_M1_Research_Problem#8. Stage-by-Stage Regulatory Diffusion Timeline|Diffusion timeline]] | Model T0–T9 regulatory spread from gazette to enforcement. Used by propagation events and lag findings. |
| [~] | [[01_M1_Research_Problem#10. Risks and Threats to Validity|Risks and validity]] | Record evidence, OCR, survey, and taxonomy risks. Used by limitations, monitoring, and mitigation planning. |

## 02 · Data Requirements — [[02_M1_Data_Requirements]]

**Parent task:** [~] Define the data contract shared by scraping, preprocessing, classification, APIs, surveys, and findings.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [~] | [[02_M1_Data_Requirements#1. Data Sources|Data sources]] | Catalogue official gazette, portal, and secondary sources. Used by spiders, portal watchers, and source-health checks. |
| [~] | [[02_M1_Data_Requirements#1.4 Per-Source Operations Spec|Per-source operations]] | Define cadence, URL pattern, authentication, fallback, and failure handling per source. Used by `source_catalogue.py` and scheduler logic. |
| [x] | [[02_M1_Data_Requirements#2. Target Data Schema|Target schema]] | Specify all `m1_*` tables and views. Used by migrations, ORM models, Pydantic schemas, API responses, and notebooks. |
| [x] | [[02_M1_Data_Requirements#3. Schema Validation and Enforcement|Schema validation]] | Define SQL constraints, Pydantic validators, and nightly validation jobs. Used to keep pipeline data importable and analyzable. |
| [~] | [[02_M1_Data_Requirements#4. Volume Requirements|Volume requirements]] | Estimate corpus, production, and view sizes. Used by storage planning and deployment sizing. |
| [~] | [[02_M1_Data_Requirements#7. Data Governance, Retention and Privacy|Governance and retention]] | Define PDPA, retention windows, S3 lifecycle, audit archive, and erasure handling. Used by ops, survey data handling, and storage policy. |
| [~] | [[02_M1_Data_Requirements#8. Worked Examples Across All Tables|Worked examples]] | Populate VAT, EPF, and product-standard examples across all tables. Used by tests, demos, API examples, and research validation. |
| [~] | [[02_M1_Data_Requirements#10. Validation and Acceptance Criteria|Acceptance criteria]] | Define checks for schema, views, governance, and seed correctness. Used before marking data-layer tasks done. |

## 03 · Data Collection — [[03_M1_Data_Collection]]

**Parent task:** [~] Turn official gazette and secondary-source inputs into reliable per-notice text and propagation events.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[03_M1_Data_Collection#1. Web Scraping Framework Selection|Scraping framework]] | Select and justify Scrapy for official gazette ingestion. Feeds scraper implementation and scheduler setup. |
| [x] | [[03_M1_Data_Collection#2. PDF Text Extraction|PDF extraction chain]] | Classify PDFs and run PyMuPDF → pdfplumber → Tesseract fallback. Produces raw text for preprocessing and OCR metrics. |
| [x] | [[03_M1_Data_Collection#3. Gazette Segmentation|Gazette segmentation]] | Split multi-notice gazettes using regex, block-gap, and LLM fallback strategies. Produces per-notice records for classification. |
| [x] | [[03_M1_Data_Collection#3.6 The NOT_REGULATORY Pre-Filter|NOT_REGULATORY filter]] | Remove appointments, procurement, and other non-SME notices before expensive stages. Reduces noise for labeling and model training. |
| [~] | [[03_M1_Data_Collection#4. Secondary Source Watchers and Propagation Matching|Propagation matching]] | Match official regulations to IRD/EPF/eROC/RSS appearances. Produces `m1_propagation_events` for lag findings. |
| [~] | [[03_M1_Data_Collection#4.6 Manual Review Queue|Manual review queue]] | Route low-confidence propagation matches to expert/admin review. Feeds tracking workflow A2 and data-quality controls. |
| [x] | [[03_M1_Data_Collection#7. Error Handling and Retry Policy|Retry policy]] | Define Scrapy vs Celery failure ownership. Used by resilient ingestion and ops runbooks. |
| [~] | [[03_M1_Data_Collection#9. Validation and Acceptance Criteria|Acceptance criteria]] | Check extraction quality, segmentation quality, and propagation-match precision. Used before Phase 2 is considered stable. |

## 04 · Preprocessing Pipeline — [[04_M1_Preprocessing_Pipeline]]

**Parent task:** [x] Convert extracted text into normalized chunks and structured metadata for downstream classification.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[04_M1_Preprocessing_Pipeline#1. Preprocessing Challenges|Preprocessing challenges]] | Identify gazette noise and multilingual complexity. Used to choose cleaning order and tokenizer strategy. |
| [x] | [[04_M1_Preprocessing_Pipeline#2. Tokenization Framework Selection|Tokenizer selection]] | Choose HuggingFace XLM-R tokenizer. Used by chunking, classifier input construction, and multilingual training. |
| [x] | [[04_M1_Preprocessing_Pipeline#3.1 Step 1 — Noise Removal|Noise removal]] | Strip headers, footers, page numbers, publication boilerplate, and OCR artifacts. Produces cleaner text for metadata extraction. |
| [x] | [[04_M1_Preprocessing_Pipeline#3.2 Step 2 — Language Routing|Language routing]] | Route EN/SI/TA/mixed lines and connect to OCR/Wijesekara handling. Used by trilingual model and summarization paths. |
| [x] | [[04_M1_Preprocessing_Pipeline#3.3 Step 3 — Metadata Extraction|Metadata extraction]] | Extract gazette number, effective date, penalty ranges, principal act, and amendment type. Used by DB fields, API filters, and alerts. |
| [x] | [[04_M1_Preprocessing_Pipeline#3.4 Step 4 — Text Chunking|Text chunking]] | Emit section-aware 512-token windows with overlap. Produces `classification_chunk` and full chunk lists for summarization. |
| [x] | [[04_M1_Preprocessing_Pipeline#3.5 Step 5 — Final Preprocessing Output|Final output]] | Define the object handed to classification and persistence. Used by model inference and Celery task wiring. |

## 05 · Model Architecture — [[05_M1_Model_Architecture]]

**Parent task:** [ ] Define the sampling plan and model architecture for the M1 regulation classifier.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [ ] | [[05_M1_Model_Architecture#1. Sampling Strategy for Labeling|Sampling strategy]] | Build stratified, clustered, and active-learning batches. Produces balanced labeling data for annotation and training. |
| [ ] | [[05_M1_Model_Architecture#1.4 Worked Example — The First Two Batches|First batches example]] | Show how early labeling batches are composed. Used by `sample_for_labeling.py` and Label Studio imports. |
| [x] | [[05_M1_Model_Architecture#2. Classification Task Definition|Task definition]] | Freeze the 8-domain single-label task and 3-sector multi-label task. Used by annotation, schema enums, model heads, and API output. |
| [~] | [[05_M1_Model_Architecture#3. Architectural Approach Comparison|Architecture comparison]] | Compare scratch training, XLM-R + LoRA, zero-shot LLM, and rules. Justifies selected architecture and baselines. |
| [ ] | [[05_M1_Model_Architecture#4. Selected Architecture: XLM-R Dual-Head with LoRA|Selected architecture]] | Specify base model, LoRA config, memory budget, and dual-head design. Used by training and ONNX export. |
| [ ] | [[05_M1_Model_Architecture#4.3 LoRA Ablation Plan — `r` × `alpha`|LoRA ablation]] | Define `r × alpha` experiments. Used to choose final adapter settings before production training. |
| [ ] | [[05_M1_Model_Architecture#6. Inference Architecture (Production)|Inference architecture]] | Describe how the trained model serves category, sectors, and confidence. Used by deployment and API tasks. |
| [ ] | [[05_M1_Model_Architecture#8. Validation and Acceptance Criteria|Acceptance criteria]] | Define expected F1, memory, latency, and reproducibility checks. Used before the model is promoted. |

## 06 · Training & Evaluation — [[06_M1_Training_Evaluation]]

**Parent task:** [ ] Train, evaluate, version, and sanity-check the M1 classifier.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [ ] | [[06_M1_Training_Evaluation#1. Dataset Splits|Dataset splits]] | Use temporal train/val/test splits rather than random splits. Produces defensible held-out evaluation. |
| [ ] | [[06_M1_Training_Evaluation#1.3 Reproducibility and the Run Fingerprint|Run fingerprint]] | Hash dataset, environment, and split boundaries. Used by model registry and viva reproducibility claims. |
| [ ] | [[06_M1_Training_Evaluation#2. Class Imbalance and Data Augmentation|Class imbalance and augmentation]] | Apply back-translation, synonym substitution, and Sinhala paraphrase with a 5× cap. Used to improve minority-domain F1. |
| [ ] | [[06_M1_Training_Evaluation#3. Training Configuration|Training configuration]] | Define hyperparameters, differential learning rate, loop, and early stopping. Used by `training.py`. |
| [ ] | [[06_M1_Training_Evaluation#4. Evaluation Metrics|Evaluation metrics]] | Compute macro-F1, per-language F1, sector metrics, calibration, and confidence. Used by model acceptance and monitoring. |
| [ ] | [[06_M1_Training_Evaluation#7. Slice Analysis|Slice analysis]] | Evaluate by language, quarter, length, extraction method, confidence, and balance. Used to find hidden performance cliffs. |
| [ ] | [[06_M1_Training_Evaluation#8. Error Analysis|Error analysis]] | Categorise and inspect top wrong predictions. Feeds annotation guideline revisions and retraining tasks. |
| [ ] | [[06_M1_Training_Evaluation#9. Model Versioning Schema|Model versioning]] | Store model, dataset, and metric metadata. Used by deployment, rollback, and monitoring. |
| [ ] | [[06_M1_Training_Evaluation#10. Backfill and the Pre-Viva Checklist|Backfill and pre-viva checks]] | Reclassify historical gazettes and run final sanity checks. Used before thesis/demo reporting. |

## 07 · Deployment & Integration — [[07_M1_Deployment_Integration]]

**Parent task:** [ ] Serve the trained classifier through ONNX/Fly.io and integrate it into backend workflows.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [ ] | [[07_M1_Deployment_Integration#1. Deployment Platform Selection|Platform selection]] | Choose Fly.io and document trade-offs. Used by infra setup and cost planning. |
| [ ] | [[07_M1_Deployment_Integration#2. ONNX Export, Validation, and Quantization|ONNX export and quantization]] | Export PyTorch to ONNX, validate parity, and produce INT8 variant. Used by production inference. |
| [ ] | [[07_M1_Deployment_Integration#3. Inference Service|Inference service]] | Build ONNX Runtime session and Redis cache. Used by classification Celery task and manual endpoint. |
| [ ] | [[07_M1_Deployment_Integration#4. API Integration|API integration]] | Wire classification task and manual classification endpoint. Used by backend API and admin review. |
| [ ] | [[07_M1_Deployment_Integration#5. Deployment Pipeline and Operations|Deployment operations]] | Define `fly.toml`, machine sizing, model deploy, rollback, canary split, health checks, and cost alerts. Used by production operations. |
| [ ] | [[07_M1_Deployment_Integration#6. End-to-End Latency Budget|Latency budget]] | Allocate time across ingestion, extraction, inference, summarization, and alerting. Used by SLA monitoring. |
| [ ] | [[07_M1_Deployment_Integration#9. Validation and Acceptance Criteria|Acceptance criteria]] | Check ONNX parity, INT8 F1 loss, canary health, and service latency before go-live. |

## 08 · Full System Architecture — [[08_M1_Full_System_Architecture]]

**Parent task:** [~] Explain how all M1 layers, data stores, routes, tasks, findings, and failure handling work together.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[08_M1_Full_System_Architecture#1. Architecture Overview|Architecture overview]] | Define the six-layer system picture. Used by every implementation and review note. |
| [~] | [[08_M1_Full_System_Architecture#2. Database Layer|Database layer]] | Map tables and views to persisted state. Used by API, tasks, and research notebooks. |
| [~] | [[08_M1_Full_System_Architecture#3. Backend API Layer|Backend API layer]] | Summarise route groups and service ownership. Used by API reference and frontend integration. |
| [~] | [[08_M1_Full_System_Architecture#4. Frontend Routes|Frontend routes]] | Map admin and SME routes to workflows. Used by tracking workflow docs and UI planning. |
| [~] | [[08_M1_Full_System_Architecture#5. Celery Task Dependency Graph|Celery task graph]] | Show task dependencies from ingestion to alerting. Used by operations and failure diagnosis. |
| [~] | [[08_M1_Full_System_Architecture#10. Research Findings Extraction|Research findings extraction]] | Define F1–F6, SQL, tests, expected effects, and notebook inputs. Used by thesis results. |
| [~] | [[08_M1_Full_System_Architecture#13. Edge Cases and Failure Modes — Unified Runbook|Failure-mode runbook]] | List failure cases by pipeline stage with detection and resolution. Used by monitoring and support. |
| [~] | [[08_M1_Full_System_Architecture#14. Module 1 Definition of Done|Definition of Done]] | State what must be true before M1 is complete. Used by roadmap and release decisions. |

## 09 · Annotation Guidelines — [[09_M1_Annotation_Guidelines]]

**Parent task:** [~] Produce reliable gold labels and SME awareness-lag observations.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [~] | [[09_M1_Annotation_Guidelines#1. Annotation Tool Selection|Annotation tool selection]] | Select Label Studio and lock the UI config. Used by annotator onboarding and export format. |
| [~] | [[09_M1_Annotation_Guidelines#2. The 8-Domain Regulation Taxonomy — Criteria and Examples|8-domain taxonomy]] | Define mutually exclusive regulation categories with examples. Used by annotators, schema enums, model labels, and UI badges. |
| [~] | [[09_M1_Annotation_Guidelines#3. Contrastive Examples for Confusable Pairs|Contrastive examples]] | Explain confusing category boundaries. Used to improve IAA and reduce model label noise. |
| [x] | [[09_M1_Annotation_Guidelines#4. Sector Assignment Guidelines|Sector rules]] | Define grocery, food-service, and general-retail sector assignment. Used by sector head training and SME matching. |
| [ ] | [[09_M1_Annotation_Guidelines#5. Annotator Qualification and Calibration|Annotator calibration]] | Recruit roles, build calibration set, apply pass thresholds, and store results. Used before production labeling. |
| [ ] | [[09_M1_Annotation_Guidelines#6. Inter-Annotator Agreement|IAA protocol]] | Compute Cohen's κ, trigger review, resolve disagreements, and track drift. Produces trustworthy consensus labels. |
| [ ] | [[09_M1_Annotation_Guidelines#7. Annotation Workflow End-to-End|Annotation workflow]] | Define queue, dual annotation, IAA, expert review, and gold export paths. Used by BUILD_07 labeling operations. |
| [ ] | [[09_M1_Annotation_Guidelines#9. SME Awareness Survey Instrument|SME survey instrument]] | Define Q1–Q8, channel options, sector-tailored regulation selection, delivery, validation, and response tracking. Produces awareness-lag data. |
| [~] | [[09_M1_Annotation_Guidelines#11. Validation and Acceptance Criteria|Acceptance criteria]] | Check κ thresholds, label coverage, survey validity, and export shape. Used before training and findings extraction. |

## 10 · Sinhala / Tamil NLP — [[10_M1_Sinhala_Tamil_NLP]]

**Parent task:** [x] Keep English, Sinhala, Tamil, OCR, and legacy font handling inside one reliable multilingual path.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[10_M1_Sinhala_Tamil_NLP#1. Sri Lankan Language NLP Context|Language context]] | Explain Sinhala/Tamil morphology, token length, and script constraints. Used to justify multilingual model and chunking choices. |
| [x] | [[10_M1_Sinhala_Tamil_NLP#2. Language Detection and Routing|Language detection and routing]] | Use fastText plus per-line Unicode routing. Produces language tags for preprocessing, annotation routing, and model slices. |
| [x] | [[10_M1_Sinhala_Tamil_NLP#3. Multilingual Model Selection|Multilingual model selection]] | Choose XLM-R and explain alternatives. Used by architecture and training. |
| [x] | [[10_M1_Sinhala_Tamil_NLP#4. OCR for Scanned Gazettes|OCR handling]] | Configure Tesseract and quality checks for scanned gazettes. Used by extraction chain and CER monitoring. |
| [x] | [[10_M1_Sinhala_Tamil_NLP#5. Wijesekara Font Conversion|Wijesekara conversion]] | Detect legacy Sinhala font text and convert greedily to Unicode. Used by extraction and preprocessing. |
| [x] | [[10_M1_Sinhala_Tamil_NLP#6. Cross-Lingual Classification Strategy|Cross-lingual strategy]] | Keep EN/SI/TA inside one classifier and evaluation flow. Used by training and slice analysis. |
| [x] | [[10_M1_Sinhala_Tamil_NLP#8. Validation and Acceptance Criteria|Acceptance criteria]] | Check detection accuracy, conversion correctness, OCR quality, and per-language model targets. |

## 11 · API Reference — [[11_M1_API_Reference]]

**Parent task:** [~] Define the backend HTTP contract used by admin UI, SME UI, automation, and research tools.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [~] | [[11_M1_API_Reference#1. Authentication and Authorization|Authentication and authorization]] | Define JWT payload, token lifecycle, roles, permission matrix, errors, and request IDs. Used by every protected endpoint. |
| [x] | [[11_M1_API_Reference#2. Client Conventions|Client conventions]] | Define pagination, filters, IDs, errors, and request format. Used by frontend and integration examples. |
| [x] | [[11_M1_API_Reference#3. Regulation CRUD|Regulation CRUD]] | Specify list, create, detail, patch, and delete endpoints. Used by admin regulation management. |
| [~] | [[11_M1_API_Reference#4. Classification and Verification|Classification and verification]] | Define classify and verify endpoints. Used by model workflow and expert review ledger. |
| [~] | [[11_M1_API_Reference#5. Sector Management|Sector management]] | Define sector read/update endpoints. Used by admin corrections and SME matching. |
| [~] | [[11_M1_API_Reference#6. Propagation Events|Propagation events]] | Define propagation event reads/writes. Used by watchers, lag analytics, and admin review. |
| [x] | [[11_M1_API_Reference#7. SME Survey|SME survey]] | Define survey submission endpoint. Used by awareness-lag data capture. |
| [~] | [[11_M1_API_Reference#9. Lag Analytics|Lag analytics]] | Define lag analytics endpoint. Used by dashboards and findings notebooks. |
| [~] | [[11_M1_API_Reference#12. Model Version Management|Model version management]] | Define model listing and activation. Used by deployment, rollback, and ops. |

## 12 · Monitoring & Maintenance — [[12_M1_Monitoring_Maintenance]]

**Parent task:** [ ] Monitor pipeline health, classifier quality, infrastructure, retraining, and rollback.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [ ] | [[12_M1_Monitoring_Maintenance#1. SLA Targets|SLA targets]] | Define ingestion, extraction, alerting, uptime, and retraining targets. Used by dashboards and incident severity. |
| [ ] | [[12_M1_Monitoring_Maintenance#2. Data Pipeline Monitoring|Pipeline monitoring]] | Track ingestion health, scrape failures, source freshness, and validation jobs. Used by ops alerts. |
| [ ] | [[12_M1_Monitoring_Maintenance#3. Classifier Performance Monitoring|Classifier monitoring]] | Detect confidence drift, estimate F1, and trigger retraining. Used by model maintenance. |
| [ ] | [[12_M1_Monitoring_Maintenance#4. Infrastructure Monitoring|Infrastructure monitoring]] | Track FastAPI, Celery, Redis, alert routes, severity, runbooks, and Grafana. Used by production support. |
| [ ] | [[12_M1_Monitoring_Maintenance#5. Retraining, Deployment and Rollback|Retraining and rollback]] | Define trigger → label review → training → ONNX → canary → rollback → backfill. Used after model drift or taxonomy updates. |
| [ ] | [[12_M1_Monitoring_Maintenance#7. Materialized Views for Analytics|Materialized views]] | Keep analytics views refreshed and monitored. Used by lag dashboards and findings notebooks. |
| [ ] | [[12_M1_Monitoring_Maintenance#8. Maintenance Procedures|Maintenance procedures]] | Define failed extraction retry, model version operations, and DB maintenance. Used by operator runbooks. |
| [ ] | [[12_M1_Monitoring_Maintenance#10. Validation and Acceptance Criteria|Acceptance criteria]] | Check alerts, drift detection, retraining gates, rollback, and maintenance coverage. |

## 13 · Folder Structure & Implementation Flow — [[13_M1_Folder_Structure_and_Implementation_Flow]]

**Parent task:** [x] Define where Module 1 code, docs, tests, artifacts, and future modules belong.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[13_M1_Folder_Structure_and_Implementation_Flow#Purpose|Purpose]] | Explain why folder ownership matters. Used by contributors before adding code or docs. |
| [x] | [[13_M1_Folder_Structure_and_Implementation_Flow#Design principles|Design principles]] | Lock stage-based layout, schema separation, tests, reproducibility, and scalability rules. Used by code review. |
| [x] | [[13_M1_Folder_Structure_and_Implementation_Flow#M1 folder map|M1 folder map]] | Map ML, backend, scraper, research, storage, and docs folders. Used by folder reference and roadmap. |
| [x] | [[13_M1_Folder_Structure_and_Implementation_Flow#File-by-file role description|File role table]] | Define what each non-trivial file owns, exports, and is called by. Used by implementation planning. |
| [x] | [[13_M1_Folder_Structure_and_Implementation_Flow#Implementation flow — Stage A → G|Stage A–G implementation flow]] | Show what persists at each pipeline boundary. Used by Celery, DB, and API wiring. |
| [x] | [[13_M1_Folder_Structure_and_Implementation_Flow#5. Per-module template (M2 / M3 / M4)|Per-module template]] | Define how M2/M3/M4 should mirror M1 without importing M1-specific logic. Used by future module builds. |
| [x] | [[13_M1_Folder_Structure_and_Implementation_Flow#Upgradability & adaptability rules|Upgradability rules]] | Define model versioning, hot rollback, feature flags, rollout, and forward-only migrations. Used by ops and architecture. |

## 14 · Tracking Workflows (Frontend) — [[14_M1_Tracking_Workflows]]

**Parent task:** [~] Define the admin and SME surfaces that make the M1 pipeline visible and actionable.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[14_M1_Tracking_Workflows#1. The Two Personas and the 8+1 Surfaces|Personas and workflow map]] | Define admin and SME workflows plus the 8+1 surfaces. Used by frontend scope and UX planning. |
| [~] | [[14_M1_Tracking_Workflows#2. A1 — Admin Pipeline-State Tracking|A1 pipeline-state tracking]] | Show regulation stage status and triage daily pipeline health. Consumes `m1_regulations.status`. |
| [ ] | [[14_M1_Tracking_Workflows#3. A2 — Admin Review-Queue Triage|A2 review queue]] | Prioritise low-confidence and needs-review items. Consumes classifier confidence and propagation review flags. |
| [x] | [[14_M1_Tracking_Workflows#4. A3 — Admin Expert Verification|A3 expert verification]] | Record expert decisions, badges, bulk verify, and audit writes. Produces verified labels for trust and training. |
| [ ] | [[14_M1_Tracking_Workflows#5. A4 — Admin Lag Analytics and Propagation Tracker|A4 lag analytics]] | Inspect propagation lag and source/channel timing. Consumes analytical views and propagation events. |
| [~] | [[14_M1_Tracking_Workflows#6. S1 — SME Regulation Discovery|S1 SME discovery]] | Let SMEs find sector-relevant regulations. Consumes category, sector, summary, and verification state. |
| [x] | [[14_M1_Tracking_Workflows#7. S2 — SME Awareness Survey Participation|S2 awareness survey]] | Capture awareness, source channel, action, and open-text feedback. Produces survey rows for lag findings. |
| [~] | [[14_M1_Tracking_Workflows#8. S3 — SME Compliance and Action-Taken Tracking|S3 compliance tracking]] | Track whether SMEs acted after awareness. Feeds compliance outcomes and F6 analysis. |
| [ ] | [[14_M1_Tracking_Workflows#9. S4 — SME Deadline and Alert Delivery History|S4 deadline and alert history]] | Show deadlines and notification history. Consumes alert events and effective dates. |
| [x] | [[14_M1_Tracking_Workflows#10. X9 — Category × Sector: the Cross-Cutting Dimension|X9 category × sector rules]] | Lock badge names, URL state, sort order, accessibility, and convention locations across all surfaces. |

## 15 · Folder Reference (Per-Folder Build Guides) — [[15_M1_Folder_Reference]]

**Parent task:** [~] Translate M1 architecture into folder-level implementation work.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[15_M1_Folder_Reference#1. The Repo Tree and How to Use This Reference|Repo tree and usage]] | Explain real repo roots, section ownership, skeleton, conventions, and quick start. Used before editing folder guides. |
| [ ] | [[15_M1_Folder_Reference#2. `enigmatrix-ml/` — the ML Monorepo|ML monorepo guide]] | Break down data samplers, extraction, preprocessing, model, summarization, schemas, utils, and tests. Used by BUILD_07/BUILD_11. |
| [~] | [[15_M1_Folder_Reference#3. `enigmatrix-backend/app/` — the FastAPI + Celery Service|Backend guide]] | Break down API routes, services, tasks, models, schemas, migrations, seeds, and config. Used by backend implementation. |
| [ ] | [[15_M1_Folder_Reference#4. `enigmatrix-backend/scraper/` — the Scrapy Project|Scraper guide]] | Break down spider, pipelines, settings, source handling, and dependency edges. Used by ingestion work. |
| [ ] | [[15_M1_Folder_Reference#5. `research/` — the Analytical Surface|Research guide]] | Break down notebooks, figures, labeling data, calibration, gold labels, survey data, and preregistration. Used by findings work. |
| [~] | [[15_M1_Folder_Reference#6. `storage/` — the On-Disk Artifact Store|Storage guide]] | Define raw PDFs, OCR cache, inference cache, model artifacts, registry, and lifecycle. Used by ops and reproducibility. |
| [x] | [[15_M1_Folder_Reference#7. `enigmatrix-docs/m1/` — the Docs Set|Docs guide]] | Define numbering, consolidation rules, doc updates, and cross-reference hygiene. Used by future documentation edits. |
| [~] | [[15_M1_Folder_Reference#8. Cross-Folder Data Flow — One Gazette, Six Folders|Cross-folder flow]] | Trace one gazette across scraper, backend, ML, storage, research, and docs. Used to understand handoffs. |
| [~] | [[15_M1_Folder_Reference#9. Consolidated Tests and Acceptance Criteria|Consolidated acceptance]] | Collect folder-level tests and acceptance criteria. Used before marking implementation slices complete. |

## 16 · Development Roadmap — [[16_M1_Development_Roadmap]]

**Parent task:** [x] Sequence the day-to-day M1 build work from foundation through research findings.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[16_M1_Development_Roadmap#Where M1 stands today (2026-05-14)|Current state]] | Summarise what exists and what remains. Used before choosing the next implementation task. |
| [x] | [[16_M1_Development_Roadmap#Phase 1 — Foundation (✅ DONE)|Phase 1 foundation]] | Record completed admin CRUD, verification, schemas, and baseline screens. Used as the stable base. |
| [x] | [[16_M1_Development_Roadmap#Phase 2 — Ingest + extraction (BUILD_07 §A–B)|Phase 2 ingest and extraction]] | Sequence scraper, Celery, extraction, language routing, preprocessing, and persistence. Produces preprocessed regulations. |
| [ ] | [[16_M1_Development_Roadmap#Phase 3 — Annotation + classification (BUILD_07 §C–D + BUILD_11)|Phase 3 annotation and classification]] | Sequence Label Studio, sampling, 800 labels, LoRA training, evaluation, ONNX, and Fly deploy. Produces production classifier. |
| [ ] | [[16_M1_Development_Roadmap#Phase 4 — Schedulers, alerts, lag tracking (BUILD_12)|Phase 4 schedulers and alerts]] | Sequence watchers, batching, alert dispatch, nightly views, and drift checks. Produces automated lag pipeline. |
| [ ] | [[16_M1_Development_Roadmap#Phase 5 — Research findings + survey deployment|Phase 5 findings and survey]] | Sequence survey deployment, F1–F6 notebooks, retraining cadence, and rollback. Produces thesis-ready findings. |
| [~] | [[16_M1_Development_Roadmap#Tracking-workflow surfaces — when each ships|Tracking workflow schedule]] | Map A1–A4, S1–S4, and X9 to implementation phases. Used by frontend and roadmap planning. |
| [x] | [[16_M1_Development_Roadmap#How to use this roadmap|Roadmap usage rules]] | Define daily usage: pick phase, open docs, run DoDs, update status. Keeps implementation work ordered. |

---

### Consolidation Check

| Check | Status |
|---|---|
| Parent docs contain former companion concepts | [x] Represented as linked subtasks in this checklist |
| Root companion Markdown files | [x] Retired after merge |
| Checklist links | [x] Point to canonical parent docs and parent-doc headings |
| 09 annotation content | [x] Taxonomy examples, IAA protocol, annotation workflow, and SME survey instrument are all inside [[09_M1_Annotation_Guidelines]] |

### Status Roll-Up

| Group | Shipped `[x]` | Partial `[~]` | Deferred `[ ]` |
|---|---|---|---|
| Orientation & structure | 00, 13, 16 | 15 | — |
| Data, extraction, preprocessing, trilingual | 04, 10 | 02, 03 | — |
| Model, training, deployment, ops | — | — | 05, 06, 07, 12 |
| Research, annotation, architecture | — | 01, 08, 09 | — |
| API & tracking UI | — | 11, 14 | — |

*This checklist is intentionally more detailed than the index: it shows the parent task, the subtask breakdown, why each subtask exists, and which downstream stage consumes the output.*
