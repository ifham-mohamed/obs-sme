# Module 1 — Documentation Feature Checklist

> A task-oriented map of the consolidated **Module 1 documentation set** (`1 Module-1-Awareness-Gap/`). Each numbered parent document is the canonical one-file source for its area. Former companion sub-docs are represented below as linked subtasks that point into the relevant parent document sections.
>
> Reading order / "start here" is [[16_M1_Development_Roadmap]]; the annotated master map is [[00_INDEX]]. The raw code-feature ledger (F-01…F-242) lives in the vault `FEATURES.md`.

**Legend** — `[x]` shipped + verified · `[~]` code-complete / partial, pending an env/data/GPU gate · `[ ]` deferred or not started.

**How to read this checklist:** each numbered section has one **parent task** and several **subtasks**. The subtask links go to real headings inside the parent `.md` file. The last column explains why that subtask exists and where its output is used next.

**Every `[~]` names its blocking gate.** A partial status with no stated gate is unfinished bookkeeping, not a status — it reads as "in progress" forever. Where a row is `[~]` or `[ ]` and the gate is not obvious from the row itself, §Blocking-Gate Ledger near the end of this file gives the gate and the artifact that would close it. If you mark something `[~]`, add its gate there in the same edit.

---

## 2026-08-01 Documentation Gap-Closure Pass

A second pass on the same day, auditing all 19 module-root documents and all 77 files in `final/works/` against the repository's actual state. It found work that had shipped with no `works/` coverage at all, and a checklist that stopped at document 16.

| Gap found | Closed by |
|---|---|
| The classifier freeze had no program-level `works/` document — it existed only in a session record and in vault docs 17/18 | **Created** [[11_CLASSIFIER_FREEZE_AND_INTEGRATION]] |
| The NLLB translation pipeline (shipped 2026-07-31) had **no `works/` document of its own** — mentioned in passing in five files, specified nowhere here | **Created** [[12_TRILINGUAL_TRANSLATION_PIPELINE]] |
| Phase 5 was the only phase with an `_ANALYSIS` and **no `_GAP_CLOSURE_PLAN`** | **Created** `PHASE5_RESEARCH_FINDINGS/PHASE5_GAP_CLOSURE_PLAN.md` |
| Phase 3 had a training *readiness plan* but no record of what the training actually produced or why XLM-R lost | **Created** `PHASE3_ANNOTATION_CLASSIFICATION/classifier_model_training/CLASSIFIER_MODEL_SELECTION_ANALYSIS.md` |
| The 2026-07-28 observability/console rebuild had **zero coverage anywhere in `works/`** | **Created** `PHASE2_INGEST_EXTRACTION/observability_console/OBSERVABILITY_CONSOLE_ANALYSIS.md` |
| This checklist had no sections for documents **17** and **18**, which have existed since 2026-08-01 | Sections 17 and 18 added below |
| 136 wikilink cells contained an **unescaped `\|`** inside a Markdown table, splitting each row into a spurious extra column in Obsidian; 7 section headers had been padded to 5 columns to compensate | All escaped to `\|`; headers normalised to 3 columns |
| Sections 05/06/07/11/12 still described the XLM-R dual-head as the production model and ONNX/Fly.io as the serving path | Rows corrected below with the frozen-model outcome |
| No single place listed which `[~]` rows were blocked on what | §Blocking-Gate Ledger added |

Nothing was deleted. Docs 05, 06 and 11 are **annotated, not rewritten** — the reasoning that led to XLM-R was sound, and deleting it would falsify the research narrative. Each now states its own outcome.

---

## 2026-08-01 Implementation Update

This update records the V6 dataset correction, the model bake-off that ended Phase 3 model selection, the inference integration, the Stage-E summary implementation slice, and the workspace/documentation reorganization.

| Area | Current state | Evidence / next use |
|---|---|---|
| V6 dataset correction | Completed and frozen | `datasets/m1_regulations_v6_1110_clean_fixedsplit` — four Presidential duties/functions gazettes carrying incidental ETF mentions (`official-pdf-2226-17`, `-2235-59`, `-2248-35`, `-2412-08`) were relabelled `EPF_ETF_CHANGE` → `SECTOR_SPECIFIC`. All four are in **train**, so the test split is unchanged from V5 and V5/V6 model comparisons stay valid. Split held at 777/166/167; cross-split leakage zero. Per-split SHA256 recorded in `dataset_manifest_v6.json`. See [[18_M1_Dataset_And_Model_Lineage]]. |
| **Primary classifier — frozen** | **Completed — gate passed** | TF-IDF word uni/bi-grams (`max_features=50000, min_df=2`) + `LinearSVC(class_weight="balanced")` on V6: validation macro-F1 **0.924476**, temporal-test macro-F1 **0.947220**, accuracy 0.958084, 160/167 correct. This clears the 0.92 gate that the V3 stratified baseline (0.9080) missed. Artifact `models/m1/linearsvc_v6_primary/linearsvc_pipeline.joblib`, SHA256 `1D7F8475…23CFA`. |
| XLM-R LoRA — category-only | Completed / **rejected** | Three runs. Unweighted collapsed to the majority class (~0.094 macro-F1 = the majority baseline). Balanced V5 (seed 42, 16 ep) reached val 0.596014 / test 0.685348 with **zero** `EPF_ETF_CHANGE` predictions. The V6 underfit-fix run (head LR 1e-3, LoRA LR 2e-4, √-balanced clipped weights, α=0.5 minority sampling, grad-clip 1.0) reached **training** macro-F1 0.969340 and val 0.902693 but **test 0.743563** — underfitting solved, temporal generalization not. Transformer tuning stopped. |
| Model selection evidence | Completed | Head-to-head on the 167-row temporal test: both correct 150, SVC-only correct 10, XLM-R-only correct 3, both wrong 4. The single EPF/ETF test record was classified correctly by LinearSVC and missed by XLM-R (0.803 on `LABOUR_LAW`). Failure tables in the end-to-end record §Step 31. |
| Local reproducibility | Completed | Bundle downloaded to Windows and re-scored: macro-F1 `0.9472199858964565` byte-identical to the Kaggle result; model and test-data SHA256 both verified. Record: `models/m1/linearsvc_v6_primary/local_windows_verification.json`. |
| Inference integration | **Wired** / migration not yet applied to a database | `LinearSVCGazetteInference` added to `m1/model/inference.py` alongside the untouched ONNX `GazetteInference`; both exported from `m1.model`. Tests: 6 targeted + 3 export + 7 chunk-contract; non-slow M1 model suite **26 passed, 2 deselected**. `classifier_service` now selects the backend from `M1_CLASSIFIER_BACKEND` (default `linearsvc`) with cwd/workspace-root path resolution; `classify_gazette` persists the margin and model name; the review-queue endpoint switches signal by backend and reports `mode`. Migration `202608010001` is **applied** — `alembic upgrade head` run against Supabase on 2026-08-01, live schema verified: `classifier_decision_margin numeric(10,6)`, `classifier_model_name varchar(64)`, CHECK `>= 0`, partial index, `alembic_version = 202608010001`. |
| Review-queue threshold | Derived, shipped **unset** | Decision margins on the V6 **validation** split separate cleanly: median 1.5954 for correct predictions against 0.3896 for errors. Candidate `M1_CLASSIFIER_MIN_MARGIN=0.40` flags 6.6% of rows and catches 55.6% of errors at 45.5% flag precision. Ships unset because 9 errors in 166 rows is too thin to freeze an operating point; with nothing configured the queue reports `mode='disabled'` rather than looking like a clean bill of health. Full sweep: `documentation/m1/analysis/MARGIN_THRESHOLD_ANALYSIS.md`. |
| scikit-learn version pin | **Pinned** / environment not yet rebuilt | The frozen pipeline was fitted under scikit-learn **1.5.2**; the workspace `.venv` has **1.8.0** and emits `InconsistentVersionWarning` on unpickle. Validation accuracy still reproduced exactly (0.9457831325301205), so this artifact is unaffected in practice. `enigmatrix-ml/pyproject.toml` now pins `scikit-learn>=1.5.2,<1.6` in **both** the `serving` and `training` extras (a model trained under one line must be loadable by the other), and `serving` now declares `joblib` explicitly. The existing `.venv` still holds 1.8.0 — run `uv sync --extra serving` before trusting a deploy. |
| Confidence contract | Decided | LinearSVC margins are **not** calibrated probabilities. The adapter returns `confidence: null` with `confidence_type: "not_available_uncalibrated_linearsvc"` plus `decision_score`, `decision_margin`, `second_category`, `class_scores`. These may drive ranking and review-queue priority but **must not be displayed as percentages**. Any calibrated probability needs a separately trained and evaluated calibration layer. |
| Sector prediction | Unchanged / deferred | The frozen primary model has no sector head — it returns `sectors: []`. Sector output still belongs to the ONNX dual-head model. Decide whether to retrain a sector head or keep the split-model arrangement. |
| **Stage-E constrained summaries** | **Backend slice shipped** / evaluation pending | Commit `ee36ce7` adds `app/m1/services/summary_service.py`, `app/m1/tasks/summarise_gazette.py`, migration `202608010002_m1_summary_metadata.py`, and backfill scripts `scripts/generate_regulation_summaries.py` + `scripts/enqueue_missing_m1_translations.py`. The first slice is intentionally non-LLM: `summary_source="anchor_bound_slots"`, `summary_model_version="m1_anchor_bound_summary_v1"`, short English summaries only from source-anchored slots, with `summary_status`, `summary_quality_flags`, and `summary_source_sha256` stored for review. Focused tests: **13 passed**. |
| Summary backfill and translation evidence | **Partially completed on live DB** | Read-only DB verification after the first write run: `generated=380`, `review_required=11`, `pending=751`; pipeline status now includes `summarized=380`. Summary translation queue was drained for generated summaries: `done/si=388`, `done/ta=388`, and `generated summaries missing SI/TA = 0`. Treat SI/TA as machine-generated draft translations pending human review. |
| End-to-end research record | Completed | `documentation/m1/records/ENIGMATRIX_M1_COMPLETE_END_TO_END_RECORD_2026-07-31_2313_IST.md` — 5,642 lines / 299,967 B, regenerable via `scripts/build_enigmatrix_m1_complete_record.py`. Contains the full chronology, every epoch, all failures and recoveries, live artifact hashes, live git state, and 13 source appendices. |
| Workspace reorganization | Completed | Root planning docs moved into `documentation/{plans,manuals,_archive}` via `git mv`; generated records and audits consolidated under `documentation/m1/`. `scripts/` deliberately left flat — 26 files reference those paths. Map: [[17_M1_Repo_Structure_Map]] and `C:\Reasearch\xyz\STRUCTURE.md`. |
| Vault `works/` reorganization | Completed | `PROGRAM_READINESS/log and works/` → `LOG_AND_WORKS/`; the byte-identical duplicate `M1_PROGRAM_READINESS_MASTER_INDEX.md` demoted to `_archive/duplicates/`; `_REORGANIZE_works.ps1` → `_tooling/`. Rules now written down in `00_WORKS_ORGANIZATION_INDEX.md`. |
| **Documentation drift — action required** | **Open** | `enigmatrix-docs/m1/` in the repo is a second copy of this doc series and has gone stale: of 36 shared filenames, **34 diverged and the vault is newer in 31**. `15_M1_Folder_Reference.md` is 5.9 KB there against 101.6 KB here; `14_M1_Tracking_Workflows.md` 7.7 KB against 109.9 KB. The vault is now declared canonical. The repo mirror needs a one-way refresh **from** the vault. Evidence: `documentation/m1/structure_audit/DOCS_SYNC_REPORT.md`. |
| Repository commit state | **Open** | `enigmatrix-ml` (branch `module-1`) has 6 modified files and 3 untracked paths — including `?? datasets/`, which means the legacy V1–V3 dataset generations are untracked. Decide gitignore-vs-commit before the next push. |

Artifacts frozen in this pass:

```text
C:\Reasearch\xyz\datasets\m1_regulations_v6_1110_clean_fixedsplit\{train,val,test}.parquet
C:\Reasearch\xyz\models\m1\linearsvc_v6_primary\linearsvc_pipeline.joblib
C:\Reasearch\xyz\models\m1\linearsvc_v6_primary\{model_registry,labels,SHA256SUMS}.json
C:\Reasearch\xyz\models\m1\linearsvc_v6_primary\local_windows_verification.json
C:\Reasearch\xyz\documentation\m1\records\ENIGMATRIX_M1_COMPLETE_END_TO_END_RECORD_2026-07-31_2313_IST.md
```

Documents created in this pass:

```text
17_M1_Repo_Structure_Map.md
18_M1_Dataset_And_Model_Lineage.md
20_M1_Multitask_Classifier_Upgrade.md
final/works/00_WORKS_ORGANIZATION_INDEX.md
C:\Reasearch\xyz\STRUCTURE.md

# added in the same-day documentation gap-closure pass:
final/works/11_CLASSIFIER_FREEZE_AND_INTEGRATION.md
final/works/12_TRILINGUAL_TRANSLATION_PIPELINE.md
final/works/PHASE5_RESEARCH_FINDINGS/PHASE5_GAP_CLOSURE_PLAN.md
final/works/PHASE3_ANNOTATION_CLASSIFICATION/classifier_model_training/CLASSIFIER_MODEL_SELECTION_ANALYSIS.md
final/works/PHASE2_INGEST_EXTRACTION/observability_console/OBSERVABILITY_CONSOLE_ANALYSIS.md
```

Relevant parent-document mapping:

| Work completed | Parent docs to update/use next | Status note |
|---|---|---|
| V6 correction, model bake-off, frozen LinearSVC, local reproduction | [[05_M1_Model_Architecture]], [[06_M1_Training_Evaluation]], [[15_M1_Folder_Reference]], [[18_M1_Dataset_And_Model_Lineage]] | Phase-3 model selection is **closed**: the primary classifier is lexical, not neural. Docs 05/06 still describe the XLM-R dual-head as the intended production model and need that corrected. |
| Inference adapter, exports, confidence contract | [[07_M1_Deployment_Integration]], [[11_M1_API_Reference]], [[12_M1_Monitoring_Maintenance]] | The response contract changed: `confidence` can now be `null`. API docs must state this before any consumer renders it. |
| Workspace + vault reorganization, doc canonicity | [[13_M1_Folder_Structure_and_Implementation_Flow]], [[15_M1_Folder_Reference]], [[17_M1_Repo_Structure_Map]] | Doc 13 describes the designed tree; doc 17 now records the measured one. |
| Stale 12-category / neural architecture references | [[05_M1_Model_Architecture]], [[08_M1_Full_System_Architecture]] | The frozen V6 dataset has **8** categories. Any surviving 12-category description is stale and should be corrected in the same pass. |

---

## 2026-07-30 Implementation Update

This update records the work completed during the latest Phase 3 labeling and documentation pass.

| Area | Current state | Evidence / next use |
|---|---|---|
| Extraction accuracy measurement | Code-complete / needs real production run evidence | Dataset registry, Excel upload, sealed versions, DB snapshot service, measurement run engine, score tables, Markdown report export, data-quality suites, and thesis artifact scripts exist. See `PROGRAM_READINESS/M1_EXTRACTION_ACCURACY_AND_DATASET_MANAGEMENT_MANUAL.md`. Capture real run IDs and screenshots before claiming final viva evidence. |
| Label Studio calibration | Completed | Ifham passed; Reezma and Ilham passed after retest. Calibration output is used as annotator qualification evidence before production labeling. |
| Batches 02-05 IAA + resolution | Completed and clean | 800 tasks, 1600 annotations, 800 gold rows, 40 manual resolutions, category kappa 0.871534, mean sector kappa 0.863776, SME relevance kappa 0.723518. The temporary 1601-annotation Batch 05 export problem was fixed; all batches now have exactly 2 annotations per task. |
| Batch 05 active-learning batch | Completed | `batch_05.csv` and `batch_05_annotations_full.json` were reduced into the gold set; the 3 Batch 05 disagreement rows were explicitly resolved in `manual_resolutions.csv`. |
| Frozen v1 gold dataset | Completed | `gold_standard_v1_800.csv`, `iaa_report_v1_800.json`, and `iaa_report_summary_v1_800.csv` were copied as immutable v1 evidence files at 2026-07-30 11:59. |
| Training split | Completed with limitation | `m1.model.data --by key` created `train.parquet` 560 rows, `val.parquet` 120 rows, and `test.parquet` 120 rows in `enigmatrix-ml/datasets/m1_regulations`. This is deterministic by key, not a true temporal split, because the current gold file does not contain a reliable `gazette_published_date`. |
| TF-IDF baselines | Completed | `tfidf_logreg` test macro-F1 = 0.4980; `tfidf_linsvc` test macro-F1 = 0.6167. Report: `storage/models/m1/baselines_v1/baselines.json`. |
| CPU LoRA smoke test | Completed / not promotable | The first CPU attempt on the full `datasets/m1_regulations` split downloaded the model but wrote no registry, so it is not counted. The valid smoke ran `xlm-roberta-base` for 1 seed and 1 epoch on `datasets/m1_regulations_smoke` (train 16, val 8, test 8). It wrote `storage/models/m1/xlmr_lora_smoke/model_registry.json` and `model.pt`; `gate_pass=false`, val macro-F1 = 0.1111, test macro-F1 = 0.0. This proves the training loop runs, not model quality. See `PROGRAM_READINESS/M1_TRAINING_PREPARATION_AND_SMOKE_TEST_RUNBOOK.md`. |
| Full LoRA training | Pending GPU | CUDA check returned `cuda=False`, CPU only. Full 3-seed LoRA training/evaluation/export should run on a CUDA machine after the rare-domain strategy is accepted. |
| Rare-domain coverage | Still weak | Current gold counts are dominated by `SECTOR_SPECIFIC` (671/800); `EPF_ETF_CHANGE` has 0 rows, and product/business/penalty/import domains remain under target. The remaining sampled pool has few/no candidates for several rare domains. |
| Trilingual regulation summary | **Superseded by 2026-08-01 implementation** | At this 2026-07-30 checkpoint the summarizer was pending. It is now replaced by the Stage-E backend slice above: `summary_en` generation, summary provenance metadata, backfill scripts, and NLLB queueing for `summary_si`/`summary_ta` are built. Remaining gate is not code existence; it is human quality review and full coverage of remaining pipeline rows. |
| Batch 06 rare-domain top-up | Completed / review caveat | `collect_rare_domain_topup.py` generated 200 official rare-domain candidates and `batch_06_annotations_full.json` was reduced into the gold set. Batch 06 agreement passed strongly: category kappa 0.980485, mean sector kappa 0.995844, SME relevance kappa 0.974012. Annotation was assisted/direct, so manually audit if strict independent evidence is required. |
| Batch 07 PDF rare-domain top-up | Completed / review caveat | `collect_pdf_rare_topup.py` generated 128 PDF-backed official candidates and `batch_07_annotations_full.json` was reduced into the gold set. Batch 07 agreement passed strongly: category kappa 0.989611, mean sector kappa 0.992982, SME relevance kappa 0.977977. Annotation was assisted/direct, so manually audit if strict independent evidence is required. |
| Frozen v3 gold dataset | Completed | `gold_standard_v3_1128.csv`, `iaa_report_v3_1128.json`, `iaa_report_summary_v3_1128.csv`, and `disagreements_v3_1128.csv` preserve the 1128-row gold state. Overall IAA: category kappa 0.947215, mean sector kappa 0.965567, SME relevance kappa 0.914637. |
| V3 stratified baseline | Completed / close to gate | `datasets/m1_regulations_v3_1128_stratified` contains 790 train, 169 validation, and 169 test rows. `baselines_v3_1128_stratified` reports LogReg macro-F1 0.862652 and LinearSVC macro-F1 0.908012. This is close to the 0.92 target but not a final pass. |

Final gold-standard artifact set:

```text
C:\Reasearch\xyz\research\data\labeling\gold_standard.csv
C:\Reasearch\xyz\research\data\labeling\iaa_report.json
C:\Reasearch\xyz\research\data\labeling\iaa_report_summary.csv
C:\Reasearch\xyz\research\data\labeling\disagreements.csv
C:\Reasearch\xyz\research\data\labeling\manual_resolutions.csv
C:\Reasearch\xyz\research\data\labeling\gold_standard_v1_800.csv
C:\Reasearch\xyz\research\data\labeling\iaa_report_v1_800.json
C:\Reasearch\xyz\research\data\labeling\iaa_report_summary_v1_800.csv
C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations\train.parquet
C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations\val.parquet
C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations\test.parquet
C:\Reasearch\xyz\storage\models\m1\baselines_v1\baselines.json
C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model_registry.json
```

Program-readiness manuals created/updated for this work:

```text
PROGRAM_READINESS/M1_PHASE3_ANNOTATION_AND_ACTIVE_LEARNING_USER_MANUAL.md
PROGRAM_READINESS/M1_TRAINING_PREPARATION_AND_SMOKE_TEST_RUNBOOK.md
PROGRAM_READINESS/M1_EXTRACTION_ACCURACY_AND_DATASET_MANAGEMENT_MANUAL.md
PROGRAM_READINESS/M1_SUMMARIZATION_TRANSLATION_READINESS_PLAN.md
PROGRAM_READINESS/M1_PROGRAM_READINESS_MASTER_INDEX.md
PROGRAM_READINESS/M1_RARE_DOMAIN_TOPUP_AND_V3_BASELINE_MANUAL.md
```

Relevant parent-document mapping:

| Work completed or reviewed | Parent docs to update/use next | Status note |
|---|---|---|
| Label Studio calibration, Batch 02-05 annotation, IAA, manual resolution, gold export, split, baseline, CPU smoke | `05_M1_Model_Architecture.md`, `06_M1_Training_Evaluation.md`, `09_M1_Annotation_Guidelines.md`, `14_M1_Tracking_Workflows.md`, `16_M1_Development_Roadmap.md` | Completed through the 800-row gold gate, deterministic key split, TF-IDF baselines, and CPU LoRA smoke. Full LoRA still requires GPU and rare-domain limitation handling. |
| Rare-domain top-up, Batches 06-07, v3 gold, v3 stratified baseline | `03_M1_Data_Collection.md`, `05_M1_Model_Architecture.md`, `06_M1_Training_Evaluation.md`, `09_M1_Annotation_Guidelines.md`, `15_M1_Folder_Reference.md`, `16_M1_Development_Roadmap.md` | Completed through the 1128-row v3 gold gate. LinearSVC now reaches 0.9080 macro-F1, close to the target but still not a final pass. |
| Extraction accuracy measurement, Excel upload, sealed dataset versions, DB snapshots, measurement dashboard/report | `02_M1_Data_Requirements.md`, `03_M1_Data_Collection.md`, `08_M1_Full_System_Architecture.md`, `11_M1_API_Reference.md`, `12_M1_Monitoring_Maintenance.md`, `14_M1_Tracking_Workflows.md` | Code paths exist; collect one real production measurement run and screenshots. |
| Trilingual title/summary storage and NLLB readiness | `02_M1_Data_Requirements.md`, `04_M1_Preprocessing_Pipeline.md`, `07_M1_Deployment_Integration.md`, `10_M1_Sinhala_Tamil_NLP.md`, `11_M1_API_Reference.md`, `14_M1_Tracking_Workflows.md`, [[19_M1_Regulation_Summarization]] | Storage/translation queue exists; summary generator and NLLB summary backfill scripts now exist. Next use: show `summary_status`, `summary_quality_flags`, SI/TA draft status, and manual review/edit evidence in the admin/SME surfaces. |

## 00 · Index & Orientation — [[00_INDEX]]

**Parent task:** [x] Keep the Module 1 documentation navigable after consolidation.

| Status | Linked subtask | Task breakdown and downstream use |
| --- | --- | --- |
| [x]    | [[00_INDEX#Status\|Status table]]                    | Track the current research, data, annotation, deployment, and monitoring state. Used by planning notes and review conversations to see what is live vs pending. |
| [~]    | [[00_INDEX#Document Index\|Document index]]                  | List the numbered parent docs and their scope. Used as the primary entry point for the whole module. **Gate:** the table lists 16 rows and the series now runs to **18** — docs 17 and 18 need adding, and the "16 numbered main docs + this README = 17 canonical files" count corrected to 18 + 1 = 19. |
| [x]    | [[00_INDEX#Consolidated Main Docs\|Consolidated main docs]]          | Map retired companion topics into their parent files. Used to prevent broken links and duplicate sub-docs.                                                      |
| [x]    | [[00_INDEX#Pipeline at a Glance\|Pipeline at a glance]]            | Summarise stages A–G from ingestion to lag measurement. Used by roadmap, architecture, and implementation guides.                                               |
| [x]    | [[00_INDEX#Key Database Entities\|Key database entities]]           | Name the core `m1_*` tables and views. Used by data requirements, API, tracking UI, and findings notebooks.                                                     |
| [x]    | [[00_INDEX#Research Questions\|Research questions]]              | Keep RQ1–RQ4 visible from the index. Used by research problem, findings extraction, and thesis reporting.                                                       |

## 01 · Research Problem — [[01_M1_Research_Problem]]

**Parent task:** [~] Prove the regulatory-awareness gap, define the research scope, and establish the success criteria.

| Status | Linked subtask | Task breakdown and downstream use |
| --- | --- | --- |
| [x]    | [[01_M1_Research_Problem#0. Where This Document Sits in the Pipeline\|Pipeline position]]               | Explain why the problem statement comes before data, model, and UI work. Used to justify the rest of M1.                |
| [~]    | [[01_M1_Research_Problem#1. Introduction\|Introduction and motivation]]     | Present the Sri Lankan SME regulatory-awareness problem and the evidence base. Feeds RQ framing and survey design.      |
| [x]    | [[01_M1_Research_Problem#2. Problem Statement\|Problem statement]]               | Define the exact failure M1 addresses: late discovery of gazetted changes. Used by scope, architecture, and evaluation. |
| [x]    | [[01_M1_Research_Problem#3. Research Questions\|Research questions]]              | Formalise RQ1–RQ4. Used by model metrics, lag views, and findings notebooks.                                            |
| [x]    | [[01_M1_Research_Problem#4. Scope and Boundaries\|Scope and boundaries]]            | Separate in-scope SME-relevant regulations from out-of-scope legal advisory work. Used by taxonomy and UI expectations. |
| [x]    | [[01_M1_Research_Problem#5. Success Metrics\|Success metrics]]                 | Define F1, lag, response-count, and uptime targets. Used by training, monitoring, and roadmap DoDs.                     |
| [~]    | [[01_M1_Research_Problem#8. Stage-by-Stage Regulatory Diffusion Timeline\|Diffusion timeline]]              | Model T0–T9 regulatory spread from gazette to enforcement. Used by propagation events and lag findings.                 |
| [~]    | [[01_M1_Research_Problem#10. Risks and Threats to Validity\|Risks and validity]]              | Record evidence, OCR, survey, and taxonomy risks. Used by limitations, monitoring, and mitigation planning.             |

## 02 · Data Requirements — [[02_M1_Data_Requirements]]

**Parent task:** [~] Define the data contract shared by scraping, preprocessing, classification, APIs, surveys, and findings.

| Status | Linked subtask | Task breakdown and downstream use |
| --- | --- | --- |
| [~]    | [[02_M1_Data_Requirements#1. Data Sources\|Data sources]]                    | Catalogue official gazette, portal, and secondary sources. Used by spiders, portal watchers, and source-health checks.                     |
| [~]    | [[02_M1_Data_Requirements#1.4 Per-Source Operations Spec\|Per-source operations]]           | Define cadence, URL pattern, authentication, fallback, and failure handling per source. Used by `source_catalogue.py` and scheduler logic. |
| [x]    | [[02_M1_Data_Requirements#2. Target Data Schema\|Target schema]]                   | Specify all `m1_*` tables and views. Used by migrations, ORM models, Pydantic schemas, API responses, and notebooks.                       |
| [x]    | [[02_M1_Data_Requirements#3. Schema Validation and Enforcement\|Schema validation]]               | Define SQL constraints, Pydantic validators, and nightly validation jobs. Used to keep pipeline data importable and analyzable.            |
| [~]    | [[02_M1_Data_Requirements#4. Volume Requirements\|Volume requirements]]             | Estimate corpus, production, and view sizes. Used by storage planning and deployment sizing.                                               |
| [~]    | [[02_M1_Data_Requirements#7. Data Governance, Retention and Privacy\|Governance and retention]]        | Define PDPA, retention windows, S3 lifecycle, audit archive, and erasure handling. Used by ops, survey data handling, and storage policy.  |
| [~]    | [[02_M1_Data_Requirements#8. Worked Examples Across All Tables\|Worked examples]]                 | Populate VAT, EPF, and product-standard examples across all tables. Used by tests, demos, API examples, and research validation.           |
| [~]    | [[02_M1_Data_Requirements#10. Validation and Acceptance Criteria\|Acceptance criteria]]             | Define checks for schema, views, governance, and seed correctness. Used before marking data-layer tasks done.                              |

## 03 · Data Collection — [[03_M1_Data_Collection]]

**Parent task:** [~] Turn official gazette and secondary-source inputs into reliable per-notice text and propagation events.

| Status | Linked subtask | Task breakdown and downstream use |
| --- | --- | --- |
| [x]    | [[03_M1_Data_Collection#1. Web Scraping Framework Selection\|Scraping framework]]              | Select and justify Scrapy for official gazette ingestion. Feeds scraper implementation and scheduler setup.                         |
| [x]    | [[03_M1_Data_Collection#2. PDF Text Extraction\|PDF extraction chain]]            | Classify PDFs and run PyMuPDF → pdfplumber → Tesseract fallback. Produces raw text for preprocessing and OCR metrics.               |
| [x]    | [[03_M1_Data_Collection#3. Gazette Segmentation\|Gazette segmentation]]            | Split multi-notice gazettes using regex, block-gap, and LLM fallback strategies. Produces per-notice records for classification.    |
| [x]    | [[03_M1_Data_Collection#3.6 The NOT_REGULATORY Pre-Filter\|NOT_REGULATORY filter]]           | Remove appointments, procurement, and other non-SME notices before expensive stages. Reduces noise for labeling and model training. |
| [~]    | [[03_M1_Data_Collection#4. Secondary Source Watchers and Propagation Matching\|Propagation matching]]            | Match official regulations to IRD/EPF/eROC/RSS appearances. Produces `m1_propagation_events` for lag findings.                      |
| [~]    | [[03_M1_Data_Collection#4.6 Manual Review Queue\|Manual review queue]]             | Route low-confidence propagation matches to expert/admin review. Feeds tracking workflow A2 and data-quality controls.              |
| [x]    | [[03_M1_Data_Collection#7. Error Handling and Retry Policy\|Retry policy]]                    | Define Scrapy vs Celery failure ownership. Used by resilient ingestion and ops runbooks.                                            |
| [~]    | [[03_M1_Data_Collection#9. Validation and Acceptance Criteria\|Acceptance criteria]]             | Check extraction quality, segmentation quality, and propagation-match precision. Used before Phase 2 is considered stable.          |

## 04 · Preprocessing Pipeline — [[04_M1_Preprocessing_Pipeline]]

**Parent task:** [x] Convert extracted text into normalized chunks and structured metadata for downstream classification.

| Status | Linked subtask | Task breakdown and downstream use |
| --- | --- | --- |
| [x]    | [[04_M1_Preprocessing_Pipeline#1. Preprocessing Challenges\|Preprocessing challenges]]        | Identify gazette noise and multilingual complexity. Used to choose cleaning order and tokenizer strategy.                              |
| [x]    | [[04_M1_Preprocessing_Pipeline#2. Tokenization Framework Selection\|Tokenizer selection]]             | Choose HuggingFace XLM-R tokenizer. Used by chunking, classifier input construction, and multilingual training.                        |
| [x]    | [[04_M1_Preprocessing_Pipeline#3.1 Step 1 — Noise Removal\|Noise removal]]                   | Strip headers, footers, page numbers, publication boilerplate, and OCR artifacts. Produces cleaner text for metadata extraction.       |
| [x]    | [[04_M1_Preprocessing_Pipeline#3.2 Step 2 — Language Routing\|Language routing]]                | Route EN/SI/TA/mixed lines and connect to OCR/Wijesekara handling. Used by trilingual model and summarization paths.                   |
| [x]    | [[04_M1_Preprocessing_Pipeline#3.3 Step 3 — Metadata Extraction\|Metadata extraction]]             | Extract gazette number, effective date, penalty ranges, principal act, and amendment type. Used by DB fields, API filters, and alerts. |
| [x]    | [[04_M1_Preprocessing_Pipeline#3.4 Step 4 — Text Chunking\|Text chunking]]                   | Emit section-aware 512-token windows with overlap. Produces `classification_chunk` and full chunk lists for summarization.             |
| [x]    | [[04_M1_Preprocessing_Pipeline#3.5 Step 5 — Final Preprocessing Output\|Final output]]                    | Define the object handed to classification and persistence. Used by model inference and Celery task wiring.                            |

## 05 · Model Architecture — [[05_M1_Model_Architecture]]

**Parent task:** [x] Define the sampling plan, active-learning batch flow, and model architecture for the M1 regulation classifier. **Closed 2026-08-01 with an outcome the document did not predict:** the selected architecture was XLM-R dual-head + LoRA; the architecture that reached production is TF-IDF + LinearSVC. The comparison work is complete and the decision is made — see [[11_CLASSIFIER_FREEZE_AND_INTEGRATION]] and `PHASE3_ANNOTATION_CLASSIFICATION/classifier_model_training/CLASSIFIER_MODEL_SELECTION_ANALYSIS.md`.

| Status | Linked subtask | Task breakdown and downstream use |
| --- | --- | --- |
| [x]    | [[05_M1_Model_Architecture#1. Sampling Strategy for Labeling\|Sampling strategy]]               | Built stratified, k-means, minority-targeted, active-learning, and rare-domain top-up batches through Batch 07. Produces Label Studio imports, PDF-backed candidate pools, and provenance files. |
| [x]    | [[05_M1_Model_Architecture#1.4 Worked Example — The First Two Batches\|First batches example]]           | Batches 02-07 are now concrete examples with CSV/XLSX exports, provenance JSON, full Label Studio JSON, and IAA outputs. |
| [x]    | [[05_M1_Model_Architecture#2. Classification Task Definition\|Task definition]]                 | Freeze the 8-domain single-label task and 3-sector multi-label task. Used by annotation, schema enums, model heads, and API output. |
| [x]    | [[05_M1_Model_Architecture#3. Architectural Approach Comparison\|Architecture comparison]] | Compare scratch training, XLM-R + LoRA, zero-shot LLM, and rules. **Resolved empirically, not on paper:** three XLM-R LoRA runs against TF-IDF baselines on the V6 temporal split. Head-to-head on the 167-row test — both correct 150, LinearSVC-only 10, XLM-R-only 3, both wrong 4. |
| [x]    | [[05_M1_Model_Architecture#4. Selected Architecture: XLM-R Dual-Head with LoRA\|Selected architecture]] | Specify base model, LoRA config, memory budget, and dual-head design. **Superseded — never promoted.** Best XLM-R test macro-F1 0.743563 against LinearSVC 0.947220; §4 now carries an outcome callout. No ONNX artifact was ever exported. Retained as the design rationale, not as a description of production. |
| [x]    | [[05_M1_Model_Architecture#4.3 LoRA Ablation Plan — `r` × `alpha`\|LoRA ablation]] | Define `r × alpha` experiments. **Moot and deliberately not run** — ablating a configuration that loses by ~0.20 macro-F1 cannot change the selection. Recorded as a decision so it is not re-opened later as an oversight. |
| [x]    | [[05_M1_Model_Architecture#6. Inference Architecture (Production)\|Inference architecture]] | Describe how the trained model serves category, sectors, and confidence. **Shipped, but not as designed:** `LinearSVCGazetteInference` in-process, chosen by `M1_CLASSIFIER_BACKEND`. Returns `confidence: null` + `decision_margin`; **category only — `sectors: []`**. See [[11_CLASSIFIER_FREEZE_AND_INTEGRATION]] §5, §7. |
| [x]    | [[05_M1_Model_Architecture#8. Validation and Acceptance Criteria\|Acceptance criteria]] | Define expected F1, memory, latency, and reproducibility checks. **Passed — by the lexical model:** test macro-F1 0.947220 ≥ 0.92 gate; reproduced byte-identically on a second machine (`0.9472199858964565`); artifact SHA256 `1D7F8475…23CFA`. Latency and memory are trivially met by a joblib pipeline. |

## 06 · Training & Evaluation — [[06_M1_Training_Evaluation]]

**Parent task:** [~] Prepare the classifier training set and evaluation gate. **The gate is now passed** — V6 fixed temporal split, frozen LinearSVC at 0.947220 test macro-F1, reproduced locally. **Gate on the remaining `[~]`/`[ ]` rows:** slice analysis, error analysis and the versioning/backfill chain were all written for a transformer run that never shipped and have not been redone against the frozen model.

| Status | Linked subtask | Task breakdown and downstream use |
| --- | --- | --- |
| [x]    | [[06_M1_Training_Evaluation#1. Dataset Splits\|Dataset splits]] | **Resolved.** The `--by key` 560/120/120 split is superseded by the V6 **temporal** split 777/166/167, fixed since V4 and byte-identical between V5 and V6 so label corrections cannot be confused with split effects. Cross-split leakage zero. Lineage: [[18_M1_Dataset_And_Model_Lineage]]. |
| [x]    | [[06_M1_Training_Evaluation#1.3 Reproducibility and the Run Fingerprint\|Run fingerprint]] | **Complete for the frozen model.** Per-split SHA256 in `dataset_manifest_v6.json`; pipeline SHA256 `1D7F8475…23CFA`; bundle hash; `local_windows_verification.json` records an exact off-machine reproduction. Environment pinned at `scikit-learn>=1.5.2,<1.6` after the artifact was found fitted under 1.5.2 in a 1.8.0 workspace. |
| [~]    | [[06_M1_Training_Evaluation#2. Class Imbalance and Data Augmentation\|Class imbalance and augmentation]] | Handled in the frozen model by `class_weight="balanced"`, not by augmentation. **Gate: `EPF_ETF_CHANGE` at 4 train / 1 test rows.** Its 1.000 test F1 is a one-sample estimate. Only a targeted collection round closes this — resampling on four examples manufactures confidence. `PENALTY_ENFORCEMENT` at 0.857 is the weakest class with a real sample. |
| [x]    | [[06_M1_Training_Evaluation#3. Training Configuration\|Training configuration]] | **Captured for the model that shipped:** `TfidfVectorizer(max_features=50000, ngram_range=(1,2), min_df=2)` → `LinearSVC(class_weight="balanced")`. The three XLM-R configurations that were run and rejected are recorded in `PHASE3_ANNOTATION_CLASSIFICATION/classifier_model_training/CLASSIFIER_MODEL_SELECTION_ANALYSIS.md` §2. |
| [x]    | [[06_M1_Training_Evaluation#4. Evaluation Metrics\|Evaluation metrics]] | **Final numbers recorded.** V6 temporal test: LinearSVC macro-F1 **0.947220**, accuracy 0.958084 (160/167); LogReg reference 0.882481; best XLM-R 0.743563. Per-class F1 recorded for all 8 categories. The earlier 0.4980 / 0.6167 figures were the v1 `--by key` split and are superseded. |
| [ ]    | [[06_M1_Training_Evaluation#7. Slice Analysis\|Slice analysis]] | Evaluate by language, quarter, length, extraction method, confidence, and balance. **Gate: not run against the frozen model, and the confidence slice is impossible as specified** — LinearSVC emits margins, not calibrated probabilities. Re-specify that slice on `decision_margin` or drop it. |
| [~]    | [[06_M1_Training_Evaluation#8. Error Analysis\|Error analysis]] | Categorise and inspect top wrong predictions. **Partially done:** the 7 test errors and the 9 validation errors are enumerated, and two validation errors (`GZT_2487_01` margin 1.2670, `GZT_2479_56` 1.4632) are recorded as **confidently wrong** — unreachable by any margin threshold. **Gate:** no `error_analysis_topwrong.csv` produced and no taxonomy applied. |
| [~]    | [[06_M1_Training_Evaluation#9. Model Versioning Schema\|Model versioning]] | Store model, dataset, and metric metadata. **Artifact side done** — `model_registry.json`, `labels.json`, `SHA256SUMS.json` beside the frozen pipeline, and `classifier_model_name` now persisted per classified row. **Gate:** the DB-side model-version table and activation endpoint described here are still unwired to the LinearSVC backend. |
| [ ]    | [[06_M1_Training_Evaluation#10. Backfill and the Pre-Viva Checklist\|Backfill and pre-viva checks]] | Reclassify historical gazettes and run final sanity checks. **Gate: no production classification run has happened yet.** The model is wired and the migration applied, but no gazette has been classified by the frozen model in the live system — so there is nothing to backfill *from* and no production evidence to show. This is the single highest-value open item. |

## 07 · Deployment & Integration — [[07_M1_Deployment_Integration]]

**Parent task:** [~] Serve the trained classifier and integrate it into backend workflows. **The serving path changed shape:** the frozen model is an in-process joblib pipeline, not an ONNX artifact on Fly.io. Backend integration is done and the migration is applied; the ONNX/Fly.io half of this document now describes a path that was not taken. **Gate: no production classification run has occurred yet.**

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [ ] | [[07_M1_Deployment_Integration#1. Deployment Platform Selection\|Platform selection]] | Choose Fly.io and document trade-offs. Used by infra setup and cost planning. |
| [ ] | [[07_M1_Deployment_Integration#2. ONNX Export, Validation, and Quantization\|ONNX export and quantization]] | Export PyTorch to ONNX, validate parity, and produce INT8 variant. **Not performed and not currently needed** — no transformer artifact met the gate to export. The ONNX code path survives, reachable via `M1_CLASSIFIER_BACKEND=onnx`, unpromoted. Revisit only if a transformer is retried after the corpus grows. |
| [x] | [[07_M1_Deployment_Integration#3. Inference Service\|Inference service]] | **Shipped as a two-backend service.** `classifier_service` selects on `M1_CLASSIFIER_BACKEND` (default `linearsvc`), resolving the model directory against cwd then workspace root. Redis inference cache not used — a joblib predict is cheaper than the round-trip. Tests: 26 passed, 2 deselected. |
| [~] | [[07_M1_Deployment_Integration#4. API Integration\|API integration]] | Wire classification task and manual classification endpoint. **Backend done:** `classify_gazette` persists `decision_margin` + `model_name`; review-queue endpoint switches signal by backend and reports `mode`. **Gate: no consumer.** No UI renders `classifier_confidence` or reads `classifier-review` yet, so the `null`-confidence contract is untested against a real client. |
| [ ] | [[07_M1_Deployment_Integration#5. Deployment Pipeline and Operations\|Deployment operations]] | Define `fly.toml`, machine sizing, model deploy, rollback, canary split, health checks, and cost alerts. Used by production operations. |
| [ ] | [[07_M1_Deployment_Integration#6. End-to-End Latency Budget\|Latency budget]] | Allocate time across ingestion, extraction, inference, summarization, and alerting. Used by SLA monitoring. |
| [~] | [[07_M1_Deployment_Integration#9. Validation and Acceptance Criteria\|Acceptance criteria]] | Check parity, F1 loss, canary health, and service latency before go-live. **Reproduction parity proven** (identical macro-F1 off-machine, hashes verified). **Gates remaining:** `uv sync --extra serving` (the `.venv` still holds scikit-learn 1.8.0 against a 1.5.x pin), and one real end-to-end classification run. |

## 08 · Full System Architecture — [[08_M1_Full_System_Architecture]]

**Parent task:** [~] Explain how all M1 layers, data stores, routes, tasks, findings, and failure handling work together.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[08_M1_Full_System_Architecture#1. Architecture Overview\|Architecture overview]] | Define the six-layer system picture. Used by every implementation and review note. |
| [~] | [[08_M1_Full_System_Architecture#2. Database Layer\|Database layer]] | Map tables and views to persisted state. Used by API, tasks, and research notebooks. |
| [~] | [[08_M1_Full_System_Architecture#3. Backend API Layer\|Backend API layer]] | Summarise route groups and service ownership. Used by API reference and frontend integration. |
| [~] | [[08_M1_Full_System_Architecture#4. Frontend Routes\|Frontend routes]] | Map admin and SME routes to workflows. Used by tracking workflow docs and UI planning. |
| [~] | [[08_M1_Full_System_Architecture#5. Celery Task Dependency Graph\|Celery task graph]] | Show task dependencies from ingestion to alerting. Used by operations and failure diagnosis. |
| [~] | [[08_M1_Full_System_Architecture#10. Research Findings Extraction\|Research findings extraction]] | Define F1–F6, SQL, tests, expected effects, and notebook inputs. Used by thesis results. |
| [~] | [[08_M1_Full_System_Architecture#13. Edge Cases and Failure Modes — Unified Runbook\|Failure-mode runbook]] | List failure cases by pipeline stage with detection and resolution. Used by monitoring and support. |
| [~] | [[08_M1_Full_System_Architecture#14. Module 1 Definition of Done\|Definition of Done]] | State what must be true before M1 is complete. Used by roadmap and release decisions. |

## 09 · Annotation Guidelines — [[09_M1_Annotation_Guidelines]]

**Parent task:** [~] Produce reliable gold labels and SME awareness-lag observations.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [~] | [[09_M1_Annotation_Guidelines#1. Annotation Tool Selection\|Annotation tool selection]] | Select Label Studio and lock the UI config. Used by annotator onboarding and export format. |
| [~] | [[09_M1_Annotation_Guidelines#2. The 8-Domain Regulation Taxonomy — Criteria and Examples\|8-domain taxonomy]] | Define mutually exclusive regulation categories with examples. Used by annotators, schema enums, model labels, and UI badges. |
| [~] | [[09_M1_Annotation_Guidelines#3. Contrastive Examples for Confusable Pairs\|Contrastive examples]] | Explain confusing category boundaries. Used to improve IAA and reduce model label noise. |
| [x] | [[09_M1_Annotation_Guidelines#4. Sector Assignment Guidelines\|Sector rules]] | Define grocery, food-service, and general-retail sector assignment. Used by sector head training and SME matching. |
| [x] | [[09_M1_Annotation_Guidelines#5. Annotator Qualification and Calibration\|Annotator calibration]] | Calibration set, scoring script, first attempts, retests, and pass/fail decisions are complete. Used as evidence that production annotators were qualified before batch labeling. |
| [x] | [[09_M1_Annotation_Guidelines#6. Inter-Annotator Agreement\|IAA protocol]] | `resolve_iaa.py` computes category, sector, and SME-relevance agreement, emits disagreements, and applies `manual_resolutions.csv`. Batches 02-07 pass the category gate with v3 category kappa 0.947215. |
| [x] | [[09_M1_Annotation_Guidelines#7. Annotation Workflow End-to-End\|Annotation workflow]] | End-to-end flow is working through export, IAA, disagreement review, manual resolution, and gold export for Batches 02-07. Batch 06/07 annotation method should be disclosed as assisted/direct unless manually audited. |
| [ ] | [[09_M1_Annotation_Guidelines#9. SME Awareness Survey Instrument\|SME survey instrument]] | Define Q1–Q8, channel options, sector-tailored regulation selection, delivery, validation, and response tracking. Produces awareness-lag data. |
| [~] | [[09_M1_Annotation_Guidelines#11. Validation and Acceptance Criteria\|Acceptance criteria]] | Category and sector kappa gates pass for Batches 02-07, and the 1128-row v3 target state is frozen. `EPF_ETF_CHANGE` remains sparse and Batch 06/07 should be manually audited for stricter evidence. |

## 10 · Sinhala / Tamil NLP — [[10_M1_Sinhala_Tamil_NLP]]

**Parent task:** [x] Keep English, Sinhala, Tamil, OCR, and legacy font handling inside one reliable multilingual path.

| Status | Linked subtask                                                                                                 | Task breakdown and downstream use                                                                                                                                                                                                                                                                                                                       |
| ------ | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [x]    | [[10_M1_Sinhala_Tamil_NLP#1. Sri Lankan Language NLP Context\|Language context]]                               | Explain Sinhala/Tamil morphology, token length, and script constraints. Used to justify multilingual model and chunking choices.                                                                                                                                                                                                                        |
| [x]    | [[10_M1_Sinhala_Tamil_NLP#2. Language Detection and Routing\|Language detection and routing]]                  | Use fastText plus per-line Unicode routing. Produces language tags for preprocessing, annotation routing, and model slices.                                                                                                                                                                                                                             |
| [x]    | [[10_M1_Sinhala_Tamil_NLP#3. Multilingual Model Selection\|Multilingual model selection]]                      | Choose XLM-R and explain alternatives. Used by architecture and training.                                                                                                                                                                                                                                                                               |
| [x]    | [[10_M1_Sinhala_Tamil_NLP#4. OCR for Scanned Gazettes\|OCR handling]]                                          | Configure Tesseract and quality checks for scanned gazettes. Used by extraction chain and CER monitoring.                                                                                                                                                                                                                                               |
| [x]    | [[10_M1_Sinhala_Tamil_NLP#5. Wijesekara Font Conversion\|Wijesekara conversion]]                               | Detect legacy Sinhala font text and convert greedily to Unicode. Used by extraction and preprocessing.                                                                                                                                                                                                                                                  |
| [x]    | [[10_M1_Sinhala_Tamil_NLP#6. Cross-Lingual Classification Strategy\|Cross-lingual strategy]]                   | Keep EN/SI/TA inside one classifier and evaluation flow. Used by training and slice analysis.                                                                                                                                                                                                                                                           |
| [x]    | [[10_M1_Sinhala_Tamil_NLP#10. Machine Translation Pipeline (NLLB-200, EN → SI/TA)\|NLLB translation pipeline]] | **Shipped 2026-07-31.** Pull-based Colab worker leasing `m1_translation_jobs`; `UNIQUE (regulation_id, field, target_lang)` idempotency; `source_sha256` drift detection; FLORES-200 codes served by the backend so the worker cannot guess; MT never overwrites a human value. Full write-up: [[12_TRILINGUAL_TRANSLATION_PIPELINE]].                  |
| [~]    | [[10_M1_Sinhala_Tamil_NLP#8. Validation and Acceptance Criteria\|Acceptance criteria]]                         | Check detection accuracy, conversion correctness, OCR quality, and per-language model targets. **Gate: translation quality is entirely unmeasured** — no BLEU/chrF reference set exists. Per-job `model_name`/`device`/`latency_ms` are stored so a sampled human evaluation can be attributed later. Treat SI/TA as draft-until-reviewed in any claim. |

## 11 · API Reference — [[11_M1_API_Reference]]

**Parent task:** [~] Define the backend HTTP contract used by admin UI, SME UI, automation, and research tools.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [~] | [[11_M1_API_Reference#1. Authentication and Authorization\|Authentication and authorization]] | Define JWT payload, token lifecycle, roles, permission matrix, errors, and request IDs. Used by every protected endpoint. |
| [x] | [[11_M1_API_Reference#2. Client Conventions\|Client conventions]] | Define pagination, filters, IDs, errors, and request format. Used by frontend and integration examples. |
| [x] | [[11_M1_API_Reference#3. Regulation CRUD\|Regulation CRUD]] | Specify list, create, detail, patch, and delete endpoints. Used by admin regulation management. |
| [~] | [[11_M1_API_Reference#4. Classification and Verification\|Classification and verification]] | Define classify and verify endpoints. **Contract changed 2026-08-01: `confidence` can now be `null`.** The response carries `confidence_type: "not_available_uncalibrated_linearsvc"` plus `decision_score`, `decision_margin`, `second_category`, `class_scores`. Margins may drive ranking but **must not be rendered as percentages**. Doc 11 annotated; **gate:** no client has been built against the new shape. |
| [~] | [[11_M1_API_Reference#5. Sector Management\|Sector management]] | Define sector read/update endpoints. Used by admin corrections and SME matching. |
| [~] | [[11_M1_API_Reference#6. Propagation Events\|Propagation events]] | Define propagation event reads/writes. Used by watchers, lag analytics, and admin review. |
| [x] | [[11_M1_API_Reference#7. SME Survey\|SME survey]] | Define survey submission endpoint. Used by awareness-lag data capture. |
| [~] | [[11_M1_API_Reference#9. Lag Analytics\|Lag analytics]] | Define lag analytics endpoint. Used by dashboards and findings notebooks. |
| [~] | [[11_M1_API_Reference#12. Model Version Management\|Model version management]] | Define model listing and activation. **Gate:** backend selection is an environment variable (`M1_CLASSIFIER_BACKEND`), not an API-driven activation. The listing/activation endpoints described here were designed for the ONNX registry and are unwired to the frozen pipeline. |

## 12 · Monitoring & Maintenance — [[12_M1_Monitoring_Maintenance]]

**Parent task:** [ ] Monitor pipeline health, classifier quality, infrastructure, retraining, and rollback.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [ ] | [[12_M1_Monitoring_Maintenance#1. SLA Targets\|SLA targets]] | Define ingestion, extraction, alerting, uptime, and retraining targets. Used by dashboards and incident severity. |
| [ ] | [[12_M1_Monitoring_Maintenance#2. Data Pipeline Monitoring\|Pipeline monitoring]] | Track ingestion health, scrape failures, source freshness, and validation jobs. Used by ops alerts. |
| [ ] | [[12_M1_Monitoring_Maintenance#3. Classifier Performance Monitoring\|Classifier monitoring]] | Detect confidence drift, estimate F1, and trigger retraining. **Blocked by a design conflict, not by effort:** the KL-divergence drift check reads `classifier_confidence`, which the LinearSVC backend leaves NULL by design — so the branch no-ops silently forever. Decide between drift over `classifier_decision_margin`, drift over the predicted-category distribution, or an explicit "dormant" declaration. See `PHASE5_RESEARCH_FINDINGS/PHASE5_GAP_CLOSURE_PLAN.md` §5c-A. |
| [ ] | [[12_M1_Monitoring_Maintenance#4. Infrastructure Monitoring\|Infrastructure monitoring]] | Track FastAPI, Celery, Redis, alert routes, severity, runbooks, and Grafana. Used by production support. |
| [ ] | [[12_M1_Monitoring_Maintenance#5. Retraining, Deployment and Rollback\|Retraining and rollback]] | Define trigger → label review → training → ONNX → canary → rollback → backfill. **`promotion.decide()` is complete, pure and Beat-wired; `retrain.py` targets `m1.model.train_xlmr`, which is no longer the production model line.** Retarget at the LinearSVC refit (minutes on CPU — which makes a genuine quarterly retrain achievable for the first time) or scope it out explicitly. |
| [ ] | [[12_M1_Monitoring_Maintenance#7. Materialized Views for Analytics\|Materialized views]] | Keep analytics views refreshed and monitored. Used by lag dashboards and findings notebooks. |
| [ ] | [[12_M1_Monitoring_Maintenance#8. Maintenance Procedures\|Maintenance procedures]] | Define failed extraction retry, model version operations, and DB maintenance. Used by operator runbooks. |
| [ ] | [[12_M1_Monitoring_Maintenance#10. Validation and Acceptance Criteria\|Acceptance criteria]] | Check alerts, drift detection, retraining gates, rollback, and maintenance coverage. |

## 13 · Folder Structure & Implementation Flow — [[13_M1_Folder_Structure_and_Implementation_Flow]]

**Parent task:** [x] Define where Module 1 code, docs, tests, artifacts, and future modules belong.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[13_M1_Folder_Structure_and_Implementation_Flow#Purpose\|Purpose]] | Explain why folder ownership matters. Used by contributors before adding code or docs. |
| [x] | [[13_M1_Folder_Structure_and_Implementation_Flow#Design principles\|Design principles]] | Lock stage-based layout, schema separation, tests, reproducibility, and scalability rules. Used by code review. |
| [x] | [[13_M1_Folder_Structure_and_Implementation_Flow#M1 folder map\|M1 folder map]] | Map ML, backend, scraper, research, storage, and docs folders. Used by folder reference and roadmap. |
| [x] | [[13_M1_Folder_Structure_and_Implementation_Flow#File-by-file role description\|File role table]] | Define what each non-trivial file owns, exports, and is called by. Used by implementation planning. |
| [x] | [[13_M1_Folder_Structure_and_Implementation_Flow#Implementation flow — Stage A → G\|Stage A–G implementation flow]] | Show what persists at each pipeline boundary. Used by Celery, DB, and API wiring. |
| [x] | [[13_M1_Folder_Structure_and_Implementation_Flow#5. Per-module template (M2 / M3 / M4)\|Per-module template]] | Define how M2/M3/M4 should mirror M1 without importing M1-specific logic. Used by future module builds. |
| [x] | [[13_M1_Folder_Structure_and_Implementation_Flow#Upgradability & adaptability rules\|Upgradability rules]] | Define model versioning, hot rollback, feature flags, rollout, and forward-only migrations. Used by ops and architecture. |

## 14 · Tracking Workflows (Frontend) — [[14_M1_Tracking_Workflows]]

**Parent task:** [~] Define the admin and SME surfaces that make the M1 pipeline visible and actionable.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[14_M1_Tracking_Workflows#1. The Two Personas and the 8+1 Surfaces\|Personas and workflow map]] | Define admin and SME workflows plus the 8+1 surfaces. Used by frontend scope and UX planning. |
| [~] | [[14_M1_Tracking_Workflows#2. A1 — Admin Pipeline-State Tracking\|A1 pipeline-state tracking]] | Show regulation stage status and triage daily pipeline health. Consumes `m1_regulations.status`. |
| [ ] | [[14_M1_Tracking_Workflows#3. A2 — Admin Review-Queue Triage\|A2 review queue]] | Prioritise low-confidence and needs-review items. **Backend ready, UI absent — and the UI has three new obligations:** handle `mode='disabled'`, show the margin as a **rank** not a percentage, and tolerate `classifier_confidence: null`. The endpoint reports which signal it used precisely so an unconfigured queue cannot look like a clean bill of health. |
| [x] | [[14_M1_Tracking_Workflows#4. A3 — Admin Expert Verification\|A3 expert verification]] | Record expert decisions, badges, bulk verify, and audit writes. Produces verified labels for trust and training. |
| [ ] | [[14_M1_Tracking_Workflows#5. A4 — Admin Lag Analytics and Propagation Tracker\|A4 lag analytics]] | Inspect propagation lag and source/channel timing. Consumes analytical views and propagation events. |
| [~] | [[14_M1_Tracking_Workflows#6. S1 — SME Regulation Discovery\|S1 SME discovery]] | Let SMEs find sector-relevant regulations. Consumes category, sector, summary, and verification state. |
| [x] | [[14_M1_Tracking_Workflows#7. S2 — SME Awareness Survey Participation\|S2 awareness survey]] | Capture awareness, source channel, action, and open-text feedback. Produces survey rows for lag findings. |
| [~] | [[14_M1_Tracking_Workflows#8. S3 — SME Compliance and Action-Taken Tracking\|S3 compliance tracking]] | Track whether SMEs acted after awareness. Feeds compliance outcomes and F6 analysis. |
| [ ] | [[14_M1_Tracking_Workflows#9. S4 — SME Deadline and Alert Delivery History\|S4 deadline and alert history]] | Show deadlines and notification history. Consumes alert events and effective dates. |
| [x] | [[14_M1_Tracking_Workflows#10. X9 — Category × Sector: the Cross-Cutting Dimension\|X9 category × sector rules]] | Lock badge names, URL state, sort order, accessibility, and convention locations across all surfaces. |

## 15 · Folder Reference (Per-Folder Build Guides) — [[15_M1_Folder_Reference]]

**Parent task:** [~] Translate M1 architecture into folder-level implementation work.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[15_M1_Folder_Reference#1. The Repo Tree and How to Use This Reference\|Repo tree and usage]] | Explain real repo roots, section ownership, skeleton, conventions, and quick start. Used before editing folder guides. |
| [~] | [[15_M1_Folder_Reference#2. `enigmatrix-ml/` — the ML Monorepo\|ML monorepo guide]] | Samplers, preprocessing, evaluation scaffolds, and NLLB title-translation helper are documented by use. Production summarization and LoRA artifact generation remain pending. |
| [~] | [[15_M1_Folder_Reference#3. `enigmatrix-backend/app/` — the FastAPI + Celery Service\|Backend guide]] | Break down API routes, services, tasks, models, schemas, migrations, seeds, and config. Used by backend implementation. |
| [ ] | [[15_M1_Folder_Reference#4. `enigmatrix-backend/scraper/` — the Scrapy Project\|Scraper guide]] | Break down spider, pipelines, settings, source handling, and dependency edges. Used by ingestion work. |
| [x] | [[15_M1_Folder_Reference#5. `research/` — the Analytical Surface\|Research guide]] | Calibration exports, labeling batches, gold-standard outputs, IAA reports, and manual resolutions are now present through the 1128-row Batch 02-07 v3 gold set. |
| [~] | [[15_M1_Folder_Reference#6. `storage/` — the On-Disk Artifact Store\|Storage guide]] | Define raw PDFs, OCR cache, inference cache, model artifacts, registry, and lifecycle. Used by ops and reproducibility. |
| [x] | [[15_M1_Folder_Reference#7. `enigmatrix-docs/m1/` — the Docs Set\|Docs guide]] | Define numbering, consolidation rules, doc updates, and cross-reference hygiene. Used by future documentation edits. |
| [~] | [[15_M1_Folder_Reference#8. Cross-Folder Data Flow — One Gazette, Six Folders\|Cross-folder flow]] | Trace one gazette across scraper, backend, ML, storage, research, and docs. Used to understand handoffs. |
| [~] | [[15_M1_Folder_Reference#9. Consolidated Tests and Acceptance Criteria\|Consolidated acceptance]] | Collect folder-level tests and acceptance criteria. Used before marking implementation slices complete. |

## 16 · Development Roadmap — [[16_M1_Development_Roadmap]]

**Parent task:** [x] Sequence the day-to-day M1 build work from foundation through research findings.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[16_M1_Development_Roadmap#Where M1 stands today (2026-05-14; Phase 3 refreshed 2026-07-30)\|Current state]] | Summarise what exists and what remains. Used before choosing the next implementation task. |
| [x] | [[16_M1_Development_Roadmap#Phase 1 — Foundation (✅ DONE)\|Phase 1 foundation]] | Record completed admin CRUD, verification, schemas, and baseline screens. Used as the stable base. |
| [x] | [[16_M1_Development_Roadmap#Phase 2 — Ingest + extraction (BUILD_07 §A–B)\|Phase 2 ingest and extraction]] | Sequence scraper, Celery, extraction, language routing, preprocessing, and persistence. Produces preprocessed regulations. |
| [~] | [[16_M1_Development_Roadmap#Phase 3 — Annotation + classification (BUILD_07 §C–D + BUILD_11)\|Phase 3 annotation and classification]] | **Model selection is closed** — LinearSVC frozen at 0.947220, XLM-R rejected after three runs, migration applied, inference wired. **Remaining, in order:** one real production classification run; the triage UI; the `M1_CLASSIFIER_MIN_MARGIN` capacity decision; audit Batch 06/07 if strict independent-annotation evidence is required; collect genuine `EPF_ETF_CHANGE` documents. |
| [ ] | [[16_M1_Development_Roadmap#Phase 4 — Schedulers, alerts, lag tracking (BUILD_12)\|Phase 4 schedulers and alerts]] | Sequence watchers, batching, alert dispatch, nightly views, and drift checks. Produces automated lag pipeline. |
| [~] | [[16_M1_Development_Roadmap#Phase 5 — Research findings + survey deployment\|Phase 5 findings and survey]] | Sequence survey deployment, F1–F6 notebooks, retraining cadence, and rollback. **Two items are unblocked today** — the `promotion.decide()` rollback unit test, and writing F6 against the frozen model. **The critical path is fieldwork:** `/portal/m1/survey` does not exist and there are 0 of ≥100 respondents. Plan: `PHASE5_RESEARCH_FINDINGS/PHASE5_GAP_CLOSURE_PLAN.md`. |
| [~] | [[16_M1_Development_Roadmap#Tracking-workflow surfaces — when each ships\|Tracking workflow schedule]] | Map A1–A4, S1–S4, and X9 to implementation phases. Used by frontend and roadmap planning. |
| [x] | [[16_M1_Development_Roadmap#How to use this roadmap\|Roadmap usage rules]] | Define daily usage: pick phase, open docs, run DoDs, update status. Keeps implementation work ordered. |

## 17 · Repo Structure Map — [[17_M1_Repo_Structure_Map]]

**Parent task:** [x] Record the *measured* shape of the workspace and repository, as distinct from the designed shape in doc 13.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[17_M1_Repo_Structure_Map#1. Why this document exists\|Why it exists]] | Separate the tree as designed (doc 13) from the tree as measured. Used before adding any file, so new work lands where the audit says it belongs. |
| [x] | [[17_M1_Repo_Structure_Map#2. Top-level inventory (measured)\|Measured inventory]] | Size every top-level directory. The finding that carries: `storage/` 7.7 GB, `.venv/` 1.4 GB, `graphify-out/` 225 MB — **the research work that matters is under 50 MB**, so a whole-workspace backup is ~95% noise. |
| [x] | [[17_M1_Repo_Structure_Map#3. Root files after the 2026-08-01 tidy\|Root files]] | Record which root planning documents moved into `documentation/{plans,manuals,_archive}` via `git mv`, so `log --follow` survives. |
| [x] | [[17_M1_Repo_Structure_Map#4. `documentation/` — the new shape\|documentation/ layout]] | Define `records/` (generated, never hand-edited), `analysis/`, `structure_audit/`. Used by anything that generates evidence. |
| [x] | [[17_M1_Repo_Structure_Map#5. Why `scripts/` was **not** reorganized\|scripts/ left flat]] | **A documented path is a contract.** 26 files reference scripts by their current path — docs, runbooks, `AI_WORK_LOG.md`, a test, and the frozen record's own appendices. Tidiness was not worth invalidating 26 documented commands. |
| [~] | [[17_M1_Repo_Structure_Map#6. The two copies of this documentation set\|Doc-set fork]] | The vault is canonical; `enigmatrix-docs/m1/` is refreshed *from* it, never merged back. 33 files refreshed on 2026-08-01. **Gate: this is a manual one-way sync with no automation and no drift check** — it will fork again. |
| [x] | [[17_M1_Repo_Structure_Map#7. Where things go\|Placement rules]] | State where a new dataset, model, script, record or plan belongs. Used before creating any artifact. |
| [x] | [[17_M1_Repo_Structure_Map#8. Cross-references\|Cross-references]] | Link the measured map to doc 13, doc 15, `STRUCTURE.md` and the audit outputs. |

## 18 · Dataset & Model Lineage — [[18_M1_Dataset_And_Model_Lineage]]

**Parent task:** [x] Trace every classification dataset from raw gold standard to frozen production model, with hashes.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[18_M1_Dataset_And_Model_Lineage#1. Lineage at a glance\|Lineage chain]] | V4 → V5 → V6 with the change at each step. Two invariants make every comparison valid: **the split never moved** (777/166/167 from V4 onward) and **nothing was deleted from the gold history**. |
| [x] | [[18_M1_Dataset_And_Model_Lineage#2. Version-by-version\|Version detail]] | Per-version row counts, label-change tables and per-split SHA256. Used by anyone reproducing a reported number. |
| [x] | [[18_M1_Dataset_And_Model_Lineage#3. Models trained on these datasets\|Model table]] | Five models, their datasets, val/test macro-F1 and verdict. The evidence base for "why the transformer lost". |
| [x] | [[18_M1_Dataset_And_Model_Lineage#Frozen primary artifact\|Frozen artifact]] | Pipeline SHA256, bundle SHA256, exact configuration, per-class test F1, and the byte-identical off-machine reproduction. |
| [x] | [[18_M1_Dataset_And_Model_Lineage#4. The confidence contract\|Confidence contract]] | `confidence: null` + `confidence_type` + margins. **The most-likely-to-be-misused output in the module** — stated as a contract, not a note. |
| [~] | [[18_M1_Dataset_And_Model_Lineage#5. Standing constraints\|Standing constraints]] | Four constraints that outlive this session: the V6 test split is spent for tuning; `EPF_ETF_CHANGE` needs documents not resampling; `datasets/` and `models/` paths are contracts; re-derive rather than hand-edit. **Gate: constraint 2 is open and only a collection round closes it.** |

## 19 · Regulation Summarization (Stage E) — [[19_M1_Regulation_Summarization]]

**Parent task:** [~] Turn a gazette's raw text and extracted fields into a short, correct, SME-readable English summary that can be safely translated. **First backend slice is built and live-tested** — `summary_service.py`, `summarise_gazette` task, summary metadata migration, dry-run/write backfill script, translation-enqueue script, and NLLB summary queueing now exist. The implementation is deliberately conservative: no LLM, no free-form OCR summarisation, and no write unless source literals pass the grounding gate. Remaining gates are human review, full-row coverage, and final evaluation.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[19_M1_Regulation_Summarization#2. The Input Contract\|Input contract]] | Pin exactly what Stage C and Stage D hand over: `PreprocessedGazette`'s 6 metadata fields + `section_chunks`, plus category/sectors/relevance. **Gate already recorded:** `classifier_confidence` is NULL on the production backend, so no summariser may gate on a confidence threshold. |
| [x] | [[19_M1_Regulation_Summarization#3. The Measurement That Decided The Design\|Extraction diagnostic]] | **Measured on all 167 V6 test rows.** `gazette_number` 20.4% correct / **31.1% wrong** / 48.5% absent; `effective_date` 0 of 11 rows that state one; the wrong value is literally in the text in **52 of 52** cases; `metadata_confidence` scores the wrong gazette 0.95 with `needs_review=False`. This is the evidence base for the whole design. |
| [x] | [[19_M1_Regulation_Summarization#4. Approach Comparison\|Approach comparison]] | Five approaches — extractive, template, fine-tuned seq2seq, zero-shot LLM, field-grounded constrained — with a decisive-constraint table, a scored matrix carrying its own honesty caveat, and `GZT_2487_02` walked through all five. Used to justify the selection to an examiner. |
| [x] | [[19_M1_Regulation_Summarization#5. Selected Design — Field-Grounded Constrained Generation\|Selected design]] | Slot contract (`value + source_span + anchor + verified`), four invariants F1–F4, deterministic verifier, optional gated rewrite, GPU on Colab/Kaggle reusing the translation lease pattern. |
| [x] | [[19_M1_Regulation_Summarization#6. The Novelty Claim\|Novelty claim]] | States what is claimable (anchor binding as a *necessary* condition, established empirically; omission as a first-class output; faithfulness with zero reference summaries) **and what is not** (constrained generation, slot-filling, faithfulness metrics, every third-party model). Used in the thesis and the viva. |
| [x] | [[19_M1_Regulation_Summarization#10. Implementation Plan\|Stage-E backend slice]] | Implemented in `enigmatrix-backend`: `summary_service.py`, `summarise_gazette.py`, migration `202608010002`, `generate_regulation_summaries.py`, `enqueue_missing_m1_translations.py`, and `test_m1_summary_service.py`. Summary statuses are `pending/generated/review_required/manual/skipped`; quality flags preserve why a row was generated or refused. |
| [~] | [[19_M1_Regulation_Summarization#10. Implementation Plan\|Rate/amount extraction]] | Minimal source-figure extraction is built: money/percentage literals such as `Rs. 50.00 per kg` can appear as grounded `source_figure` slots if present in source text. **Gate:** this is not yet a dedicated structured rate/levy/threshold slot family with schedule-row anchors, so do not claim full rate extraction. |
| [~] | [[19_M1_Regulation_Summarization#10. Implementation Plan\|gazette_number and effective_date fixes]] | Summary-side mitigation is built: gazette identity comes from ingest/document metadata; effective dates are emitted only when one of the accepted date forms is literally present in source text. **Gate:** upstream metadata extraction still needs repair; this prevents summary hallucination but does not fix the extractor's original 31% gazette-number error. |
| [~] | [[19_M1_Regulation_Summarization#5.3 The verifier\|Verifier]] | First deterministic verifier is built and unit-tested: source-literal grounding, maximum length/sentence count, non-SME action-word guard, source hash, and named hard flags. **Gate:** the broader planned verifier still needs evaluated sector-containment/OCR-damage checks and a human-reviewed error set. |
| [ ] | [[19_M1_Regulation_Summarization#7. Evaluation Without Reference Summaries\|Evaluation protocol]] | Reference-free by necessity — no human-written summaries exist. Literal grounding = 1.00 and relevance violations = 0 are **gates**; omission/rejection rates are diagnostics. 80-document human eval with harm reported as a raw count, plus the E vs E′ verifier ablation. |
| [~] | [[19_M1_Regulation_Summarization#11. Validation and Acceptance Criteria\|Acceptance criteria]] | Operational provenance and translation queueing are met for the first slice: 380 generated summaries, 11 review-required rows, 388 SI and 388 TA summary translations done, 0 generated summaries missing SI/TA. **Gate:** human quality review, trilingual numeric-preservation audit, and full-row coverage are still open. |

## 20 · Multitask Classifier Upgrade (V7) — [[20_M1_Multitask_Classifier_Upgrade]]

**Parent task:** [~] Specify the additive V7 classifier line that can emit category, affected study sectors, and derived SME relevance without modifying the frozen `linearsvc_v6_primary`. **Step 41 audit is complete; implementation is not started.** This is deliberately separate from the frozen primary classifier: V7 may be promoted later, rejected, or used only as a sector head beside LinearSVC.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[20_M1_Multitask_Classifier_Upgrade#1. Step 41 — the V6 audit, and what it changed\|Step 41 V6 audit]] | Read-only audit over V6 parquets and v3 gold found the missing `is_sme_relevant` export column, verified 1110/1110 gold join coverage, found one deliberate relevance/sector mismatch, and measured the near-degenerate sector distribution. |
| [x] | [[20_M1_Multitask_Classifier_Upgrade#1.4 The finding that most changes the plan — the sector task is nearly degenerate\|Sector degeneracy finding]] | 812/1110 rows carry no sector, 250/1110 carry all three, and only 48/1110 carry a genuine partial sector combination. This changes the gates: sector macro-F1 alone is gameable by a relevance detector. |
| [x] | [[20_M1_Multitask_Classifier_Upgrade#1.5 Measured class weights — use these, do not assume balance\|Measured class weights]] | V6 train split gives sector `pos_weight` values 2.944 / 2.905 / 3.415 and derived relevance `pos_weight=2.809`. Used to correct docs 05/06 and avoid the earlier false "balanced sector head" claim. |
| [ ] | [[20_M1_Multitask_Classifier_Upgrade#2. Step 42 — the V7 dataset\|V7 dataset]] | Build `m1_regulations_v7_1110_multitask_fixedsplit` from frozen V6, preserving keys/splits/categories and adding recovered/derived relevance plus sector vectors. Must write `dataset_manifest_v7.json`. |
| [ ] | [[20_M1_Multitask_Classifier_Upgrade#3. Steps 43–44 — label contract and architecture\|Label contract and architecture]] | Add frozen category/sector orders, encode/decode helpers, consistency checks, batch contract, three-head architecture, `pos_weight` losses, and category-only sampler. |
| [ ] | [[20_M1_Multitask_Classifier_Upgrade#4. Steps 45–49 — training protocol\|Training protocol]] | Train/evaluate the V7 multitask line without tuning on the spent V6 test split. Keep frozen LinearSVC untouched. |
| [ ] | [[20_M1_Multitask_Classifier_Upgrade#6. Step 50 — evaluation and promotion\|Evaluation and promotion]] | Add the extra gates that prevent degenerate sector promotion: partial-sector exact-set reporting, individual sector floor, derived relevance consistency, and a legitimate hybrid outcome if category does not beat LinearSVC. |
| [ ] | [[20_M1_Multitask_Classifier_Upgrade#7. Steps 51–53 — export, inference, freeze\|Export, inference, freeze]] | Build export/inference/registry only after promotion decision. Served `is_sme_relevant` is derived from sectors, never taken from the auxiliary relevance head. |

## 20 · Multitask Classifier Upgrade (V7) — [[20_M1_Multitask_Classifier_Upgrade]]

**Parent task:** [~] Upgrade Stage D from a category-only classifier to one shared encoder emitting domain + sectors + derived relevance, **without modifying the frozen `linearsvc_v6_primary`**. Step 41 (audit) is complete and changed three things in the plan; steps 42–53 are not started.

| Status | Linked subtask | Task breakdown and downstream use |
|---|---|---|
| [x] | [[20_M1_Multitask_Classifier_Upgrade#1. Step 41 — the V6 audit, and what it changed\|Step 41 audit]] | **Run against the real parquets, not planned.** V6 columns are `key · text · category · sectors · language · date` — **`is_sme_relevant` is absent** and must be recovered from `gold_standard_v3_1128.csv` (join coverage 1110/1110; V6 sectors match gold on 1110/1110). Integrity otherwise clean: 0 duplicate keys, 0 cross-split overlap, 0 empty text, 0 unknown labels. Artifacts in `documentation/m1/analysis/`. |
| [x] | [[20_M1_Multitask_Classifier_Upgrade#1.3 The one derivation-rule violation is not a data error\|Derivation rule]] | `is_sme_relevant == bool(affected_sectors)` holds **1109/1110**. The exception `GZT_2492_10` is a *reasoned* annotation — both annotators agreed at confidence 1.0 that an export-proceeds rule affects SMEs outside the three study sectors. Deriving relevance therefore **narrows** the field to "affects a studied sector"; that must appear in the limitations, not be flipped silently. |
| [x] | [[20_M1_Multitask_Classifier_Upgrade#1.4 The finding that most changes the plan — the sector task is nearly degenerate\|Sector label shape]] | **The finding that most changes the plan.** 812 rows (73.2%) carry no sector; 250 (22.5%) carry all three; only 48 (4.3%) are partial. `general+grocery` has **0 training rows**; `food_service` alone has **0 val and 0 test rows**. Consequence: the ≥0.88 sector gate is gameable, and per-sector thresholds are unsupportable. |
| [x] | [[20_M1_Multitask_Classifier_Upgrade#1.5 Measured class weights — use these, do not assume balance\|Measured class weights]] | `pos_weight` from train: grocery 2.944 · food 2.905 · general 3.415 · relevance 2.809. Doc 05 §2.2 projected ~50% sector positive rates; measured is ~25%. That projection and its "needs no augmentation" conclusion are corrected there. |
| [ ] | [[20_M1_Multitask_Classifier_Upgrade#2. Step 42 — the V7 dataset\|Step 42 · V7 dataset]] | Build `m1_regulations_v7_1110_multitask_fixedsplit` from V6 without touching it. **Gate:** builder must assert 1110 rows, the 777/166/167 split, V6 category parity row-for-row, `sector_vector` round-trip, and `relevance_label == int(any(sector_vector))` on every row. |
| [ ] | [[20_M1_Multitask_Classifier_Upgrade#3. Steps 43–44 — label contract and architecture\|Steps 43–44 · contracts + heads]] | `derive_sme_relevance`, encoders that **reject** unknown sectors rather than dropping them, batch shapes `[]`/`[3]`/`[]`, and the tri-head module. Frozen index order for `CATEGORIES` and `SECTORS` shipped in `labels.json` **and** the registry. |
| [ ] | [[20_M1_Multitask_Classifier_Upgrade#3.5 One sampler, not three\|Loss + sampler]] | 0.65/0.30/0.05 with measured `pos_weight`s. **One sampler on category rarity only** — three compounding samplers would duplicate the 4 `EPF_ETF_CHANGE` rows until they are memorised. |
| [ ] | [[20_M1_Multitask_Classifier_Upgrade#4. Steps 45–49 — training protocol\|Steps 45–49 · training]] | Smoke → one-seed diagnostic → loss-weight comparison → three seeds (42, 1, 2), mean ± std. **Test split untouched until the configuration is frozen** — it has already carried four model comparisons. |
| [ ] | [[20_M1_Multitask_Classifier_Upgrade#5. Step 48 — thresholds\|Step 48 · thresholds]] | **One global threshold**, stored in the registry with `threshold_mode: "global"`. Per-sector values computed as a diagnostic only: 729 grid combinations against 9 informative validation rows is overfitting by construction. |
| [ ] | [[20_M1_Multitask_Classifier_Upgrade#6. Step 50 — evaluation and promotion\|Step 50 · gates]] | Category ≥0.92 **and** regression ≤0.01 vs 0.947220 · sector ≥0.88 · no sector F1 <0.80 · relevance recall ≥0.90 · consistency =100% · **partial-sector exact-set match on the 8 test rows reported separately**. |
| [ ] | [[20_M1_Multitask_Classifier_Upgrade#6.3 The hybrid is a legitimate outcome\|Promotion decision]] | Three permitted outcomes, including **hybrid** — LinearSVC keeps category, V7 serves sectors and derived relevance. A hybrid means one row carries a calibrated probability for sectors and none for category; the response contract must say so. |
| [ ] | [[20_M1_Multitask_Classifier_Upgrade#7. Steps 51–53 — export, inference, freeze\|Steps 51–53 · ship]] | ONNX with three outputs + parity check; `MultitaskGazetteInference` added **without changing** `GazetteInference` or `LinearSVCGazetteInference`; freeze to the V6 standard — hash, package, download, re-score, reproduce exactly. |

---

### Blocking-Gate Ledger

Every `[~]` and `[ ]` above, with the one thing that would close it. If a row is not here, its gate is stated inline.

| Doc | Item | Blocking gate | What closes it |
|---|---|---|---|
| 00 | Document index | Lists 16 docs; series runs to 18 | Add rows 17/18 and correct the file count |
| 01 | Introduction, diffusion timeline, risks | No primary survey evidence | ≥ 100 SME respondents (Phase 5a) |
| 02 | Sources, volume, governance, worked examples | Source URLs are best-known defaults, unverified | Watcher URL triage pass (Phase 4a) |
| 03 | Propagation matching, review queue, acceptance | Match precision never hand-audited | 30-event sample, precision per `match_method`, gate ≥ 0.90 |
| 05 | — | *(closed 2026-08-01)* | — |
| 06 | Class imbalance | `EPF_ETF_CHANGE` 4 train / 1 test | A targeted collection round — **not** resampling |
| 06 | Slice analysis | Never run against the frozen model; the confidence slice is impossible as written | Re-specify on `decision_margin`, then run |
| 06 | Error analysis | No `error_analysis_topwrong.csv`, no taxonomy applied | Enumerate the 7 test + 9 val errors into the 4-type taxonomy |
| 06 | Model versioning | DB-side registry unwired to the frozen pipeline | Wire or explicitly scope out |
| 06 | Backfill / pre-viva | **No production classification run has happened** | One real end-to-end run — highest-value open item |
| 07 | ONNX export | No transformer met the gate | Nothing — deliberately not needed |
| 07 | API integration | No consumer of the `null`-confidence contract | Triage UI |
| 07 | Acceptance | `.venv` holds scikit-learn 1.8.0 against a 1.5.x pin | `uv sync --extra serving` |
| 08 | DB / API / routes / task graph / DoD | Describes surfaces that exist but have never run end-to-end with real data | Phase 4 activation + one production run |
| 09 | SME survey instrument | `/portal/m1/survey` does not exist; 0 respondents | Build the route, then recruit |
| 09 | Taxonomy, contrastive examples, acceptance | Batch 06/07 annotation was assisted/direct | Manual audit *if* strict independent evidence is required |
| 10 | Acceptance criteria | MT quality entirely unmeasured | Sampled human evaluation, ≥ 100 title pairs per language |
| 11 | Classification endpoint | Contract changed to nullable confidence; no client built | Triage UI against the new shape |
| 11 | Model version management | Backend selection is an env var, not an API | Wire or scope out |
| 12 | Classifier monitoring | **Drift reads `classifier_confidence`, which is NULL by design** | Choose: margin-based drift, category-distribution drift, or declare dormant |
| 12 | Retraining / rollback | `retrain.py` targets a model line that is not in production | Retarget at the LinearSVC refit (minutes on CPU) |
| 14 | A2 review queue | Backend ready, no UI | Build it with the three obligations noted in the row |
| 14 | A4 lag analytics, S4 alert history | No propagation or alert data yet | Phase 4 activation |
| 15 | ML / backend / scraper / storage guides | Written before the model froze | Refresh against the frozen artifact paths |
| 16 | Phase 4 | Watchers coded, URLs unverified, never run for real | 4a triage → 4c activation sequence |
| 16 | Phase 5 | Fieldwork not started | `/portal/m1/survey` + recruitment |
| 17 | Doc-set fork | Manual one-way sync, no drift check | Automate the sync or schedule the check |
| 18 | Standing constraints | `EPF_ETF_CHANGE` scarcity | Same as 06 |
| 19 | Rate / amount extraction | Minimal source-figure extraction exists, but there is no dedicated structured rate/levy/threshold slot family | Add typed rate/amount slots with schedule-row and `at the rate of` anchors |
| 19 | `gazette_number` / `effective_date` identity | Summary-side mitigation exists; upstream extraction can still produce wrong or absent metadata | Repair upstream extraction and keep source/body occurrences typed separately from identity metadata |
| 19 | Verifier and review surface | First verifier exists; no dedicated summary-review UI or evaluated review workflow yet | Add admin review/edit surface for `summary_status='review_required'` and sampled generated summaries |
| 19 | Evaluation | 380 generated summaries exist, but no human evaluation exists | 80-document human eval + E vs E′ ablation, plus SI/TA numeric-preservation audit |
| 20 | V7 dataset (step 42) | Not built; `is_sme_relevant` is absent from the V6 parquet | Build from V6 + gold join with the builder assertions in doc 20 §2.3 |
| 20 | Sector multi-label claim | **Only 48 of 1110 rows carry a partial sector set**; `general+grocery` has 0 training rows and `food_service` alone has 0 val/test rows | Targeted annotation of partial-sector regulations — now the highest-value labelling target |
| 20 | Per-sector thresholds | A 729-combination grid against 9 informative validation rows | Serve one global threshold; revisit when partial-sector data grows |
| 20 | Steps 43–53 | Nothing built | Sequential; each step's gate is listed in doc 20 §9 |
| 20 | Promotion | Category benchmark is 0.947220 and V7 must not regress by more than 0.01 | Three permitted outcomes including hybrid — doc 20 §6.3 |
| 09 | Golden workbook field truth | **708 of 1508 combined rows have no field-level ground truth** — that data exists only in the live DB | `scripts/export_gold_only_field_truth.py` then `merge_gold_only_field_truth.py --write` |
| 09 | Measurement filter | A run that ignores `field_truth_verified` scores the extractor against blanks | Seal every measurement dataset version with `field_truth_verified = TRUE` |
| 09 | `is_sme_relevant` conflicts | 151 rows where the workbook and gold disagreed, resolved gold-wins | Adjudicate the 12 FALSE→TRUE rows if the workbook flag is ever treated as evidence |
| 20 | V7 dataset | Step 41 audit exists; no V7 parquet/manifest exists | Build V7 from frozen V6 with explicit relevance recovery, sector vectors, and parent hashes |
| 20 | V7 trainer/inference | Spec exists; no multitask trainer, inference class, or registry exists | Implement Steps 43–53, then evaluate without touching the spent V6 test split for tuning |
| 20 | Sector evidence | Only 48/1110 rows carry partial sector combinations | Report partial-sector exact-set match with denominator; collect more partial-sector evidence before claiming a robust three-way sector classifier |

**Two unblocked items with no gate at all** — do these first, they are cheap: the `promotion.decide()` rollback unit test (4 assertions), and writing F6 against the frozen model's recorded numbers.

### `works/` Document Ledger

What lives in this folder and whether it is current.

| Document | Covers | State |
|---|---|---|
| `00_WORKS_ORGANIZATION_INDEX.md` | Layout and naming rules for this tree | Current |
| `01_MASTER_PROJECT_OVERVIEW.md` | Whole-project context | **Stale** — generated 2026-07-15, predates the model freeze |
| `02_MEMBER1_MODULE1_REPORT.md` | Member-1 scope and status | **Stale** — same date; "pending tasks" list predates Phase-3 closure |
| `03_FEATURE_CHECKLIST.md` | This file — the living status ledger | Current |
| `04_API_AND_PAGES_REFERENCE.md` | Routers, tasks, pages | Partly stale; the repo copy was newer and kept during the 2026-08-01 sync |
| `05_MANUAL_TESTING_GUIDE.md` | Manual test walkthroughs | §5 "Classification (after model deploy)" needs the LinearSVC path |
| `06_CLEANUP_REPORT.md` | Removable files audit | Superseded by `STRUCTURE.md` + the 2026-08-01 audit |
| `07_SETUP_AND_USER_MANUAL.md` | Setup and operations | Current to 2026-07-31 |
| `08_M1_MODULE_REORG_PLAN.md` | Module reorganization plan | Executed |
| `09_PHASE2_MEASUREMENT_EQS_UPGRADE.md` | Extraction-accuracy measurement | Current |
| `10_PIPELINE_STAGING_AND_MANUAL_STEPPING.md` | Stage/status map, manual stepping | Current |
| **`11_CLASSIFIER_FREEZE_AND_INTEGRATION.md`** | V6 → bake-off → freeze → wiring → migration → confidence contract | **New 2026-08-01** |
| **`12_TRILINGUAL_TRANSLATION_PIPELINE.md`** | NLLB-200 pull-based Colab pipeline | **New 2026-08-01** |
| `PHASE1…PHASE4/` | Per-phase analysis + gap-closure + issue folders | Current |
| `PHASE5_RESEARCH_FINDINGS/` | Analysis **+ gap-closure plan** | **Plan added 2026-08-01** — every phase now has both |
| `PROGRAM_READINESS/` | Operator manuals, runbooks, session records | Current |
| `RESEARCH_DESIGN/` | Scope and methodology decisions | Single document; thin |
| `_tooling/`, `_archive/` | Maintenance scripts, superseded material | Current |

### Consolidation Check

| Check | Status |
|---|---|
| Parent docs contain former companion concepts | [x] Represented as linked subtasks in this checklist |
| Root companion Markdown files | [x] Retired after merge |
| Checklist links | [x] Point to canonical parent docs and parent-doc headings |
| Checklist covers the whole numbered series | [x] Sections 00–20 present; 17/18 added in the documentation gap-closure pass, 19/20 added as Stage-E and V7 work became explicit |
| Wikilink pipes escaped inside tables | [x] 136 cells corrected; 7 headers normalised to 3 columns |
| 09 annotation content | [x] Taxonomy examples, IAA protocol, annotation workflow, and SME survey instrument are all inside [[09_M1_Annotation_Guidelines]] |
| 2026-07-30 labeling update | [x] Calibration, Batches 02-05 gold resolution, 800-row gate, IAA metrics, frozen v1 dataset, split, TF-IDF baselines, CPU LoRA smoke, and remaining GPU/rare-domain gates recorded |
| 2026-07-31 rare-domain v3 update | [x] Batch 06/07 rare-domain top-up, 1128-row v3 gold, v3 IAA, stratified split, LinearSVC 0.9080 baseline, and Batch 06/07 assisted-annotation caveat recorded |
| 2026-08-01 model freeze | [x] V6 correction, three rejected XLM-R runs, frozen LinearSVC 0.947220, local reproduction, inference wiring, migration `202608010001`, margin threshold shipped unset |
| Confidence-contract fallout traced | [x] Recorded against 05, 06, 07, 11, 12, 14 — every surface that assumed a probability |
| Extraction measurement documentation | [x] Added program-readiness manual for Excel upload, dataset sealing, DB snapshot, measurement runs, and report export |
| Summarization/translation gap | [x] Readiness plan, shipped NLLB pipeline in [[12_TRILINGUAL_TRANSLATION_PIPELINE]], and first Stage-E backend summary slice now recorded. Remaining gap is evaluation and review, not missing implementation. |
| Observability workstream | [x] Session-101 console rebuild documented in `PHASE2_INGEST_EXTRACTION/observability_console/` |
| Every phase has an analysis **and** a gap-closure plan | [x] Phase 5's plan added 2026-08-01 |
| Multitask upgrade specified | [x] Doc 20 added — Step-41 audit run against the real parquets, V7 schema, tri-head design with relevance derived from sectors, corrected thresholds and gates, steps 41–53 |
| Golden workbook combined | [x] `structured_v2_combined_1508_official.xlsx` — union of the 800-row extraction-truth workbook and the 1128-row gold standard (overlap only 420), 52 columns, summary/provenance snapshot values verified from the raw table, v1 left unmodified |
| Workbook/gold `is_sme_relevant` conflict | [x] 151 disagreements resolved gold-wins, both values retained, all logged to `golden_workbook_gold_relevance_conflicts.csv` |
| Doc 05 sector projection corrected | [x] Projected ~50% sector positive rates replaced with measured ~25% plus `pos_weight`s; the "sector task needs no augmentation" conclusion withdrawn |
| Summarization method specified and first slice built | [x] Doc 19 added — input contract, measured extraction diagnostic, 5-way comparison, selected design, novelty claim, reference-free evaluation; backend slice now implements anchor-bound slots, hard review flags, summary provenance, and SI/TA queueing. |
| V7 multitask classifier upgrade tracked | [x] Doc 20 added — Step 41 audit, measured sector imbalance, relevance derivation decision, V7 dataset/trainer/evaluation/export plan, and explicit "frozen LinearSVC remains untouched" boundary |
| Every `[~]` names its gate | [x] Inline or in the Blocking-Gate Ledger |

### Status Roll-Up

| Group | Shipped `[x]` | Partial `[~]` | Deferred `[ ]` |
|---|---|---|---|
| Orientation & structure | 00, 13, 16, **17** | 15 | — |
| Data, extraction, preprocessing, trilingual | 04, 10 | 02, 03 | — |
| Model & training | **05**, **18** | 06, **20** *(V7 spec/audit)* | — |
| Deployment & ops | — | 07 | 12 |
| Research, annotation, architecture | — | 01, 08, 09 | — |
| Summarization (Stage E) | **19** *(method + first backend slice)* | 19 *(human eval, review UI, full coverage)* | — |
| Multitask classifier (V7) | **20** *(step 41 audit)* | 20 *(steps 42–53)* | — |
| Measurement corpus | **09** *(combined workbook built)* | 09 *(708 rows await field truth)* | — |
| API & tracking UI | — | 11, 14 | — |

**What moved this pass:** 05 `[~]` → `[x]` (model selection closed, though not with the architecture it selected) · 18 and 17 added as `[x]` · 07 `[ ]` → `[~]` (backend integration shipped; ONNX/Fly.io path not taken) · 16 Phase 5 `[ ]` → `[~]` (two items unblocked) · **19 added** — its method is `[x]`, and the later 2026-08-01 sync moves its build from `[ ]` to `[~]`: the first backend slice is shipped and live-tested, while human evaluation/review remains open · **20 added** — Step 41 audit/spec is `[~]`; V7 implementation is explicitly not started.

**The previous highest-value open item is partly closed:** gazettes have now been classified by the frozen model, and the first summary/translation backfill wrote live data. The highest-value remaining evidence task is quality review: inspect the 11 `review_required` summaries, sample at least 80 generated summaries for English faithfulness, and audit Sinhala/Tamil numeric preservation before making final claims.

*This checklist is intentionally more detailed than the index: it shows the parent task, the subtask breakdown, why each subtask exists, which downstream stage consumes the output, and — for anything unfinished — the specific gate that would close it.*
