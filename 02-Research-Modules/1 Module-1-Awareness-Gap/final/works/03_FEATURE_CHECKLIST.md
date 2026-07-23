# Module 1 — Documentation Feature Checklist

> A task-oriented map of the **whole M1 documentation set** (`1 Module-1-Awareness-Gap/`): every numbered doc (00–16) as a feature area linked to its parent file, with a one-line *why / what it does*, and each companion sub-doc as a sub-task carrying its own implementation status. Built by reading each file's Purpose + status badge.
>
> Reading order / "start here" is [[16_M1_Development_Roadmap]]; the annotated master map is [[00_INDEX]]. The raw code-feature ledger (F-01…F-242) lives in the vault `FEATURES.md`.

**Legend** — checkbox = implementation status of the feature the doc describes (the doc itself is written in all cases):
`[x]` shipped + verified · `[~]` code-complete / partial, pending an env/data/GPU gate · `[ ]` deferred or not started.

---

## 00 · Index & Orientation
- [x] [[00_INDEX]] — master map of the 61-file set: status table, per-doc contents, parent→companion table, pipeline stages A–G, DB entities, 4 research questions, tech choices. *Why: the single entry point that ties every M1 doc together.*

## 01 · Research Problem — [[01_M1_Research_Problem]]
*Why/what: frames the whole module — abstract, IRD/EPF awareness-gap statistics, the 4 formal research questions, scope, success metrics, and the T0–T9 regulatory-diffusion timeline (cabinet → enforcement).*
- [~] [[01_M1_1_Research_Motivation_Evidence]] — full evidence base behind the "34 % of SME penalties came from amendments gazetted > 90 days prior" claim: IRD/EPF citations + a 40-respondent pre-pilot scan.

## 02 · Data Requirements — [[02_M1_Data_Requirements]]
*Why/what: the data contract — 15-source catalogue, full schema for all 9 `m1_*` tables, 2 analytical views, and an end-to-end worked example.*
- [~] [[02_M1_1_Data_Sources_Catalogue]] — per-source ops spec **shipped 2026-07-23**: `source_catalogue.py` (cadence/auth/URL/failure/fallback + `due_after`/`in_backoff`) + nightly `source_health` report. Registry health contract already existed; spider-side Wayback/viewstate fallback still deferred.
- [x] [[02_M1_2_Database_Schema_Validation]] — three-layer validation **shipped 2026-07-23**: Layer-1 CHECK constraints (migration `202607230001`, `NOT VALID`), Layer-2 Pydantic + `app/m1/validation.py`, Layer-3 nightly `validate_pipeline` → `m1_pipeline_audits`. Names mapped to real schema; `VALIDATE CONSTRAINT` pending an operator run.
- [~] [[02_M1_3_Data_Governance_Retention]] — governance/retention **framework shipped 2026-07-23**: retention jobs + storage projection + S3 lifecycle YAML, Beat-scheduled, `M1_RETENTION_DRY_RUN` default on. PDPA data-export/erasure endpoints + `audit_log_archive` still deferred.
- [~] [[02_M1_4_Worked_Examples_All_Tables]] — idempotent seed **shipped 2026-07-23** (`seed_m1_worked_examples.py`) populating the 3 examples across the real tables (regulation→sectors→penalties→propagation→awareness) so the two views compute over real rows. Doc's non-existent tables (changes/court_cases) noted; view-assertion tests pending.

## 03 · Data Collection — [[03_M1_Data_Collection]]
*Why/what: the ingestion story — Scrapy scraper (4-way comparison), the PDF extraction chain, three segmentation strategies, the NOT_REGULATORY pre-filter, and 2-step secondary-source matching.*
- [x] [[03_M1_1_PDF_Extraction_Chain]] — `classify_pdf()` deep-dive (text/hybrid/scanned routing), full Tesseract config, and how to recalibrate thresholds for new gazette typesetting.
- [x] [[03_M1_2_Gazette_Segmentation]] — where each strategy (A heading-regex / B block-gap / C LLM-fallback) fails, plus boundary-detection troubleshooting; feeds per-notice classification.
- [~] [[03_M1_3_Secondary_Source_Integration]] — 3-tier matcher **shipped 2026-07-23** (`match_tiered`: exact → `multilingual-e5-base` embedding → difflib fallback), embedding tier opt-in (`M1_PROP_EMBEDDING_ENABLED`), `ck_m1_prop_match_method` widened (`202607230002`). De-dup/earliest-wins already existed; Tier-3 review-queue table + admin UI deferred.

## 04 · Preprocessing Pipeline — [[04_M1_Preprocessing_Pipeline]]
*Why/what: turning raw extracted text into classifier input — noise removal, tokenizer choice (XLM-R), the 5-step pipeline, and chunking.*
- [x] [[04_M1_1_Gazette_Noise_Removal]] — 8 ordered noise classes with before/after snippets + a regex unit-test suite; two entry points (citation-faithful vs classifier-stripped).
- [x] [[04_M1_2_Metadata_Extraction_Patterns]] — production regex for gazette#, effective date, penalty range, principal act + multi-penalty `finditer` and amendment-vs-repeal disambiguation.
- [x] [[04_M1_3_Text_Chunking_Strategy]] — quantitative chunking comparison + the hybrid §-aware + sliding-window algorithm (`MAX_LEN=512`, `STRIDE=64`) with multilingual token implications.

## 05 · Model Architecture — [[05_M1_Model_Architecture]]
*Why/what: the classifier design — 3-step sampling, the 12-category + 10-sector task, a 4-way approach comparison (XLM-R + LoRA selected), and the dual-head architecture.*
- [ ] [[05_M1_1_Sampling_Strategy]] — stratified-by-year-language → k-means (k=20, silhouette-justified) → active-learning selection, with sparse-cell handling.
- [~] [[05_M1_2_Architecture_Comparison_Deep_Dive]] — train-from-scratch vs fine-tune-XLM-R vs zero-shot-GPT-4 vs rule-based, sourced with a 50-doc pilot and cost/failure analysis.
- [ ] [[05_M1_3_LoRA_Hyperparameter_Justification]] — the `r × alpha` ablation plan, `target_modules` trade-off, `bias="none"` precedent, and memory budget.

## 06 · Training & Evaluation — [[06_M1_Training_Evaluation]]
*Why/what: how the model is trained and judged — temporal (not random) split, 3-seed reproducibility, baselines, slice analysis, error taxonomy, versioning, and a 13-item pre-viva checklist.*
- [ ] [[06_M1_1_Data_Augmentation_Strategy]] — back-translation + paraphrase + synonym substitution with a diversity check and the 5× cap rationale + per-class F1 impact.
- [ ] [[06_M1_2_Slice_Analysis_Framework]] — per-language / per-quarter / per-length / per-extraction-method slice computation + visualization templates + "cliff"-pattern detection.

## 07 · Deployment & Integration — [[07_M1_Deployment_Integration]]
*Why/what: serving the model — 4-way platform comparison (Fly.io), ONNX Runtime CPU serving, INT8 quantization, Redis inference cache, and the latency budget.*
- [ ] [[07_M1_1_ONNX_Export_Quantization]] — `torch.onnx.export` config (opset 17, dynamic axes), the INT8 calibration pipeline, and float32-vs-INT8 accuracy validation.
- [ ] [[07_M1_2_Fly_io_Deployment_Operations]] — `fly.toml` deep-dive, machine sizing, volume layout (current + previous model), canary traffic-split, and cost alerting.

## 08 · Full System Architecture — [[08_M1_Full_System_Architecture]]
*Why/what: the whole picture — 6-layer architecture, all tables/routes, Celery task graph, end-to-end happy-path timeline, the 6 research findings, DoD, and M1→M2/M3/M4 links.*
- [~] [[08_M1_1_Research_Findings_Extraction]] — for each of F1–F6: data source, sample-size requirement, statistical test, SQL, expected effect sizes, and notebook scaffold.
- [~] [[08_M1_2_Edge_Cases_Failure_Modes]] — a 23-entry runbook extending the parent's 9 cases, each with a detection signal, resolution, and monitoring metric.

## 09 · Annotation Guidelines — [[09_M1_Annotation_Guidelines]]
*Why/what: how gold labels are made — Label Studio (4-way choice) + config XML, 12-category decision criteria, 10-sector rules, the IAA κ ≥ 0.75 protocol, and the SME survey.*
- [~] [[09_M1_1_Category_Taxonomy_Examples]] — 5–8 worked examples per category plus contrastive examples for confusable pairs (template + seeded-regulation based).
- [ ] [[09_M1_2_Annotation_Workflow_IAA_Protocol]] — the IAA computation, disagreement-resolution paths, calibration-test design, and per-annotator performance tracking.
- [ ] [[09_M1_3_SME_Survey_Instrument]] — the operational side of the Q1–Q8 survey: per-sector tailoring SQL, delivery mechanism, response-tracking schema, and validity rules.

## 10 · Sinhala / Tamil NLP — [[10_M1_Sinhala_Tamil_NLP]]
*Why/what: the trilingual core — SI/TA linguistic properties, language detection (fastText), multilingual model choice (XLM-R), Tesseract OCR, and Wijesekara font conversion.*
- [x] [[10_M1_1_Language_Detection_Routing]] — fastText `lid.176.bin` config, the 500-char window + 0.70 threshold, and the per-line Unicode-range router.
- [x] [[10_M1_2_OCR_Wijesekara_Conversion]] — full Tesseract config + the 87-entry Wijesekara→Unicode mapping, detection heuristic, and greedy longest-match converter.

## 11 · API Reference — [[11_M1_API_Reference]]
*Why/what: the complete HTTP surface — CRUD, classification, verification, sectors, propagation events, SME survey, public endpoint, analytics, backfill, and model-version management.*
- [~] [[11_M1_1_API_Authentication_Authorization]] — JWT payload structure, the role-permission matrix, token expiry/refresh, error codes, and request-id propagation.
- [~] [[11_M1_2_API_Integration_Examples]] — cURL + Python + Postman examples per endpoint group with common-error troubleshooting.

## 12 · Monitoring & Maintenance — [[12_M1_Monitoring_Maintenance]]
*Why/what: keeping it healthy — SLA targets, pipeline health checks, confidence-drift (KL-divergence), Prometheus metrics, queue monitoring, retraining triggers, and DB maintenance.*
- [ ] [[12_M1_1_Performance_Monitoring_Alerting]] — a confidence-drift worked example, SLA dashboard layout, escalation paths, and a per-severity runbook.
- [ ] [[12_M1_2_Retraining_Deployment_Rollback]] — the full retraining workflow, A/B testing strategy, auto-rollback trigger, and backfill orchestration.

## 13 · Folder Structure & Implementation Flow — [[13_M1_Folder_Structure_and_Implementation_Flow]]
- [x] Single doc, no companions — where every M1 file lives + how M2/M3/M4 mirror the layout; 5 design principles, the full folder map, the Stage A–G implementation flow, and upgradability/scalability rules. *Why: the structural spec the folder build guides (doc 15) elaborate.*

## 14 · Tracking Workflows (frontend) — [[14_M1_Tracking_Workflows]]
*Why/what: the index of the 8 + 1 admin/SME tracking surfaces that expose the pipeline to users.*
- [~] [[14_M1_1_Admin_Pipeline_State_Tracking]] — **A1** Stage A→F status machine per regulation (status field + list surface it; no dedicated stage dashboard yet).
- [ ] [[14_M1_2_Admin_Review_Queue_Triage]] — **A2** needs-review queue for `confidence < 0.70` (backend flag exists; `?needs_review=true` filter is the workaround).
- [x] [[14_M1_3_Admin_Expert_Verification]] — **A3** verification ledger: Verify button + `<VerificationBadge>` + bulk-verify + audit writes.
- [ ] [[14_M1_4_Admin_Lag_Analytics]] — **A4** lag dashboard + propagation tracker (analytics endpoints exist; no UI consumes them).
- [~] [[14_M1_5_SME_Regulation_Discovery]] — **S1** regulation discovery (list + "pending" widget shipped; sector-applicability filter deferred).
- [x] [[14_M1_6_SME_Awareness_Survey]] — **S2** awareness survey participation (`/surveys/regulation/[id]`, `/surveys/awareness`, `/surveys/history`).
- [~] [[14_M1_7_SME_Compliance_Action_Tracking]] — **S3** action-taken status captured by survey Q7; no dedicated "My Regulations" tracker yet.
- [ ] [[14_M1_8_SME_Deadline_Alert_History]] — **S4** deadline countdown + alert-delivery history (backend writes events; no SME UI).
- [x] [[14_M1_9_Category_Sector_Workflows]] — **X9** cross-cutting reference for how the 12 categories × 10 sectors flow through every surface (schema + badge conventions shipped).

## 15 · Folder Reference (per-folder build guides) — [[15_M1_Folder_Reference]]
*Why/what: the parent index of six "how to build this folder" guides, each with a file table (owner / status / primary doc / how-to-build), start steps, dependencies, and acceptance.*
- [ ] [[15_M1_1_ML_Folder_Guide]] — `ml/` slice (~28 files, entirely deferred to BUILD_07 + BUILD_11).
- [~] [[15_M1_2_Backend_Folder_Guide]] — `backend/app/` slice (~6 shipped: admin CRUD + audit + model + middleware; ~3 partial; ~16 deferred).
- [ ] [[15_M1_3_Scraper_Folder_Guide]] — `scraper/` slice (5 files, deferred to BUILD_07).
- [ ] [[15_M1_4_Research_Folder_Guide]] — `research/` slice (~8 notebooks, scaffold post-BUILD_07/11).
- [~] [[15_M1_5_Storage_Folder_Guide]] — `storage/` conventions documented; directories populate as Phase 2/3 run.
- [x] [[15_M1_6_Docs_Folder_Guide]] — the docs folder itself (61 docs shipped).

## 16 · Development Roadmap — [[16_M1_Development_Roadmap]]
- [x] Single doc, no companions — the sequenced "start here" guide: 5 phases (Foundation ✅ / Ingest + extract / Annotation + classification / Schedulers + alerts / Research findings) with "do this next" call-outs, DoDs, and linked detail docs. *Why: the developer's daily start screen.*

---

### Status roll-up

| Group                                   | Shipped `[x]`                            | Partial `[~]`          | Deferred `[ ]`                     |
| --------------------------------------- | ---------------------------------------- | ---------------------- | ---------------------------------- |
| Extraction & preprocessing (03, 04, 10) | 03_1, 03_2, 04_1, 04_2, 04_3, 10_1, 10_2 | —                      | 03_3                               |
| Model & training (05, 06, 07)           | —                                        | 05_2                   | 05_1, 05_3, 06_1, 06_2, 07_1, 07_2 |
| Data & schema (02)                      | —                                        | —                      | 02_1, 02_2, 02_3, 02_4             |
| Research framing (01, 08, 09)           | —                                        | 01_1, 08_1, 08_2, 09_1 | 09_2, 09_3                         |
| API & ops (11, 12)                      | —                                        | 11_1, 11_2             | 12_1, 12_2                         |
| Frontend tracking (14)                  | 14_3, 14_6, 14_9                         | 14_1, 14_5, 14_7       | 14_2, 14_4, 14_8                   |
| Structure & build (13, 15, 16)          | 13, 15_6, 16                             | 15_2, 15_5             | 15_1, 15_3, 15_4                   |

*Shipped items concentrate in the ingest/extraction/trilingual layer (Phase 2) and the admin-CRUD + verification slice; the model, findings, and ops layers are documented-but-deferred pending gold labels, GPU training, and data flow.*
