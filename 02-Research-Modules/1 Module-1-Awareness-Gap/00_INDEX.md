# Module 1 — Regulatory Change Awareness Gap

> **Research Question:** Are regulatory changes reaching Sri Lankan SMEs in time to act — and what is the information lag between gazette publication and SME awareness?

> [!warning] Truth-ledger sync — 2026-08-02
> This index is the module's status ledger and is **current**. Two figures elsewhere in the doc set were stale and have now been corrected everywhere:
> the gold set is **1128 adjudicated rows → 1110 ML rows** (not 800), and the production classifier is **LinearSVC V6**, not XLM-R.
> A full copy of the submitted final report now lives in `final/report/` so every document can cite it directly.
>
> **Canonical record:** [[final/works/11_CLASSIFIER_FREEZE_AND_INTEGRATION|11_CLASSIFIER_FREEZE_AND_INTEGRATION]] · [[18_M1_Dataset_And_Model_Lineage]] · `final/works/evidence/M1_OPERATING_EVIDENCE_2026-08-02.json`
> **Submitted-report copy:** [[final/report/Enigmatrix_Consolidated_Final_Report_FULL|Enigmatrix_Consolidated_Final_Report_FULL]] (Part I = group report, Part II = Module 1 dissertation).

> [!info] Lineage update — 2026-08-02 (later pass)
> A **second V7 line (V7-M)** on the full 1110-row multitask fixed split is now recorded. It reached the strict promotion gate and **failed on sector macro-F1 `0.888330`** (required ≥ 0.90), consuming its 167-row test split in that single read. A sector-focused improvement run produced **seed 13**, which is validation-selected, **never tested**, and not promoted.
>
> Two docs were added: [[21_M1_Data_Limitations_and_Risk_Register]] and [[22_M1_Data_Usage_and_Row_Count_Register]].
>
> **Next action: Step 55A — fresh holdout v3 lock validation. No model evaluation until it passes; old Step 50 must never be rerun.**

> [!success] RA-HMT hybrid — trained, exported, integrated — 2026-08-03
> **Gazette-SME-RA-HMT** is built end-to-end and is the first system in this module that produces **all four required outputs** — regulation domain, affected SME sectors, SME relevance, and a calibrated confidence with an evidence snippet. Three branches (TF-IDF+LinearSVC · XLM-R+LoRA · multilingual-e5 retrieval) plus a rule prior, fused with validation-fitted simplex weights, temperature-calibrated, constraint-repaired.
>
> **V7 fixed-split test (n=167): domain macro-F1 `0.9351` (95% CI 0.8697–0.9737) · sector macro-F1 `0.9014` · relevance F1 `0.9400` · joint exact-match `0.8802` · domain ECE `0.0319`.** Against the frozen LinearSVC primary the domain difference is `+0.0155`, 95% CI `[−0.0411, +0.0767]`, `p = 0.548` — a statistical tie on the one metric they share.
>
> The artifact bundle is assembled and validated at `C:\Reasearch\xyz\m1_rahmt\results`, and the predictor is wired into `enigmatrix-ml` / `enigmatrix-backend` / `enigmatrix-frontend` as a **third selectable backend**. **It is not promoted.** `M1_CLASSIFIER_BACKEND` still defaults to `linearsvc`, and RA-HMT has never been scored on the unspent fresh holdout v3 — that read is the promotion gate, not the V7 numbers above.
>
> **New doc:** [[24_M1_RAHMT_Hybrid_Architecture]].

---

## Status

| Dimension                      | Target                             | Status                  |
| ------------------------------ | ---------------------------------- | ----------------------- |
| Category classifier F1 (macro) | ≥ 0.92                             | **PASSED** — V6 TF-IDF LinearSVC = **0.9472** (temporal test), frozen as primary |
| Sector assignment F1 (macro)   | ≥ 0.88                             | **No sector model in production** — the frozen classifier is category-only (`sectors: []`). Best measured sector macro-F1 is **0.888330** from the V7-M Step 50 candidate, which **failed** its own stricter ≥ 0.90 gate and was archived. The current seed13 candidate is untested |
| Sector label coverage          | usable multi-label structure       | **Weak in training** — 73.2% of gold rows carry no sector, 84% of the rest carry all three; only 48 rows (4.3%) are partial. **Fixed for evaluation** — fresh holdout v3 is 93.4% partial among its sector-positive rows |
| Labeled gazette documents      | ≥ 800                              | 1128 resolved v3 gold rows → 1110 after artifact exclusion; IAA gate passed. Plus **286** newly collected fresh-holdout rows = **1396 distinct rows** ([[22_M1_Data_Usage_and_Row_Count_Register]]) |
| Fresh evaluation surface       | one unspent locked holdout         | **286-row v3 ready for lock** — both prior test splits (V6, V7-M) are consumed. Step 55A pending |
| Propagation data points        | ≥ 800 (200 regulations × 4 stages) | Data collection         |
| SME awareness survey responses | ≥ 100 unique SMEs                  | Instrument, authenticated flow, and public `/portal/m1/survey` route exist; real field responses remain 0/100 |
| Ingestion latency              | ≤ 6 hours from gazette publication | Pipeline deployed       |
| Alert delivery latency         | ≤ 24 hours from publication        | Pipeline deployed       |
| System uptime                  | ≥ 99.9%                            | Monitoring active       |
| Expert verification coverage   | ≥ 30% of production regulations    | In progress             |
| Production classification run  | ≥ 1 end-to-end                     | **Completed** — the frozen model has classified live gazettes; retain the run evidence and complete the remaining quality review |
| Four-output capability (domain + sectors + relevance + confidence/evidence) | all four emitted by one system | **Built, not promoted** — RA-HMT emits all four. V7 test: domain `0.9351`, sectors `0.9014`, relevance `0.9400`, joint `0.8802`, ECE `0.0319`, evidence on 167/167. Production still runs the category-only LinearSVC primary ([[24_M1_RAHMT_Hybrid_Architecture]]) |
| Calibrated confidence          | a probability that can be routed on | **Achieved in RA-HMT** — domain ECE `0.0319` vs `0.0805` for Branch A alone; abstention routing 134 AUTO_ACCEPT / 18 REVIEW_RECOMMENDED / 15 HUMAN_REVIEW_REQUIRED. The production path still returns `confidence=None` by design |

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

### V7-M line and the fresh holdout — 2026-08-02, later pass

- **A second V7 line exists and must not be confused with the 1103-row working experiment.** V7-M trains on the full 1110-row `m1_regulations_v7_1110_multitask_fixedsplit` (777/166/167, multitask fields stored rather than derived). It did not collapse: Step 47 reached category macro-F1 `0.91096`, and Step 49's three-seed validation run peaked at selection score `0.91794`.
- **The strict gate was reached and failed.** Step 50 evaluated the seed-1 candidate once: category `0.910533` ✅, relevance `0.92` ✅, sector exact `0.916168` ✅, **sector macro-F1 `0.888330` ❌** against ≥ 0.90. Four of five gates passed; the failure margin is `0.0117`, concentrated in `general_retail` (F1 `0.873563`, recall `0.844` at threshold 0.75). Candidate archived, not promoted.
- **That single read consumed the V7-M test split.** Old Step 50 must never be rerun, and its 167 rows — including their error table — may not inform any later selection, tuning or claim.
- **The current candidate is `…improvement_validation_only_candidate_seed13_not_tested`.** Sector-focused run over seeds 7/13/29; seed 13 selected on validation at category `0.929558` / sector `0.927620` / sector-exact `0.957831` / relevance `0.936170`, thresholds `0.45 / 0.45 / 0.75`. These are **selection** figures, not measurement — the previous candidate's validation numbers were in the same range before it failed on real held-out data.
- **Fresh holdout v3 is the only unspent evaluation surface left.** 286 rows, English, leakage-verified, never seen by a model. It went 193 (v1, `IMPORT_EXPORT`=0) → 225 (v2, `general_retail`=11) → 286 (v3, `general_retail`=29, all sector minimums met, six of eight category targets met).
- **Two limitations remain open by source, not by effort:** `EPF_ETF_CHANGE` 3/8 (no genuine EPF/ETF instruments exist in the 39,649-item gazette index) and `PENALTY_ENFORCEMENT` 10/15 with all 10 sector-`NONE` (SME-facing offence clauses live in by-law Schedules beyond the page-1 extraction scope). Full register: [[21_M1_Data_Limitations_and_Risk_Register]].
- **Next action is Step 55A**, which runs no model: validate v3's structure and labels, correct the `row_count_in_150_200` flag, record limitations, write the locked manifest. Only then may Step 55B evaluate the seed13 candidate once, with thresholds frozen from validation.

Full record: [[final/works/11_CLASSIFIER_FREEZE_AND_INTEGRATION|11_CLASSIFIER_FREEZE_AND_INTEGRATION]] · lineage: [17_M1_Repo_Structure_Map.md](17_M1_Repo_Structure_Map.md) and [18_M1_Dataset_And_Model_Lineage.md](18_M1_Dataset_And_Model_Lineage.md) · status ledger: [[final/works/03_FEATURE_CHECKLIST|03_FEATURE_CHECKLIST]].

### RA-HMT hybrid — 2026-08-03

- **The four-output system exists.** `Gazette-SME-RA-HMT` combines Branch A (TF-IDF word+char, calibrated, three targets), Branch B (XLM-R + LoRA, three heads, multi-task loss), Branch C (multilingual-e5 retrieval over a 777-row train-only index) and a legal-keyword rule prior. Weights, temperature and every threshold were fitted on **validation only**; test was read once.
- **Measured on the V7 fixed-split test (n=167):** domain macro-F1 `0.9351` (95% CI `0.8697`–`0.9737`), domain accuracy `0.9461`, sector macro-F1 `0.9014`, relevance F1 `0.9400`, joint exact-match `0.8802`, domain ECE `0.0319`, evidence snippet on 167/167 records, constraint violations before repair **0/167**.
- **The calibration stage is the load-bearing one.** Weighted fusion alone scores ECE `0.1357` — worse than any single branch, because blending three differently-scaled probability vectors over-confidently. Temperature scaling (T = `0.4625`) turns that into `0.0319`, less than half Branch A's `0.0805`. Those two ablation rows differ only in that stage.
- **The fusion weights are a result, not a setting.** The simplex grid contained every single-branch corner and still selected `tfidf 0.35 · retrieval 0.30 · rules 0.20 · xlmr 0.15`, beating the best single branch by `+0.0328` on validation. `w_xlmr = 0.15` is the honest quantification of what a 278M-parameter transformer contributes at 777 training rows.
- **One earlier projection was falsified and has been withdrawn.** The Branch-A-only build predicted coverage@98%-accuracy would rise `0.904 → 0.946`; on the full run it moved `0.904 → 0.880`. RA-HMT buys calibration quality and output completeness, not extra auto-accept coverage. The claim was dropped rather than restated.
- **Two source defects were found and fixed** while assembling the local bundle: Branch C accumulated its similarity-weighted vote in `float32`, emitting probabilities such as `1.000000119` that corrupt `log()` and ECE binning; and `split_notices()` collapsed newlines before applying a multiline regex, so full-page splitting silently returned one unit (verified: 1 unit → 3 units after the fix).
- **Integrated, not promoted.** `enigmatrix-ml/m1/model/rahmt_inference.py`, the `rahmt` branch in `classifier_service.py`, `M1_*RAHMT*` settings and the frontend four-output helpers all exist. `M1_CLASSIFIER_BACKEND` still defaults to `linearsvc`. Promotion requires a scored read on the **unspent fresh holdout v3** — the V7 test split these numbers come from is now consumed, and switching backend also changes the sector contract from expert/manual data to a model output.

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
| 3 | [03_M1_Data_Collection.md](03_M1_Data_Collection.md) | Scrapy scraper (4-way comparison), PyMuPDF/pdfplumber/Tesseract chain, PDF type classification (`classify_pdf()`), 3 segmentation strategies (A: heading regex / B: block-gap heuristic / C: LLM fallback), NOT_REGULATORY pre-filter (6 patterns), 2-step secondary-source matching (exact + embedding ≥ 0.78), 7-checkpoint validation table, 6-pitfall table, **Step 54A fresh locked holdout collection (2026-08-02) — page-1 extraction recipe, four-part leakage gate, and the 128-cached-PDF training-leakage trap** |
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
| 18 | [18_M1_Dataset_And_Model_Lineage.md](18_M1_Dataset_And_Model_Lineage.md) | **V4 → V5 → V6 dataset lineage and every model trained on them** — per-version label changes, class distribution, per-split SHA256, the five-model comparison table, why the transformer lost, the frozen LinearSVC artifact and its hashes, the confidence contract, and four standing constraints., plus the **fresh locked holdout v3 (286 rows, leakage-verified, 93.4 % partial-sector)** that satisfies the fresh-holdout precondition. |
| 19 | [19_M1_Regulation_Summarization.md](19_M1_Regulation_Summarization.md) | **Stage-E summarisation method** — the input contract (raw text + the 6 Stage-C metadata fields + classifier context), a measured diagnostic showing the extractors return a *wrong* gazette number on 31.1% of test rows, a 5-way approach comparison (decisive-constraint table + scored matrix + one real gazette walked through every approach), and the selected **field-grounded constrained generation** design with four faithfulness invariants, a reference-free evaluation protocol, and the novelty claim it supports. **§8.1 the routing hold** (why a summary must not exist before its classification, and the four release paths); **§8.2 localised composition** (why SI/TA are composed rather than machine-translated, and the literal-parity check that enforces it). |
| 20 | [20_M1_Multitask_Classifier_Upgrade.md](20_M1_Multitask_Classifier_Upgrade.md) | **V7 multitask upgrade** — one shared XLM-R encoder emitting regulation domain (8-way softmax), affected SME sectors (3 sigmoids) and SME relevance **derived** from the sector output so the two can never contradict. Contains the 1,110-row source audit, the executed 1,103-row no-leak working dataset, parser/trainer fixes, smoke and 3-seed rejected run, plus the still-unbuilt formal enriched V7 package — and, in §∞, the **separate V7-M line**: sector-focused training config, the Step 50 strict gate failed at sector macro-F1 `0.888330`, the frozen thresholds and why they may not move, and the untested seed13 candidate awaiting Step 55A/55B. |
| 21 | [21_M1_Data_Limitations_and_Risk_Register.md](21_M1_Data_Limitations_and_Risk_Register.md) | **Every known data weakness, with severity and required wording** — L1–L10 open limitations (EPF/ETF 3/8, PENALTY 10/15 all sector-`NONE`, page-1 extraction, English-only, targeted sampling, 286-row spec deviation, formulaic families, context-dependent labels, the self-contradicting `row_count_in_150_200` flag), R1–R4 resolved ones (`IMPORT_EXPORT`=0, `general_retail` shortfall, SME-irrelevant majority, the 128-PDF training-leakage trap), the failure modes deliberately avoided, and the **verbatim lock-manifest declaration**. |
| 22 | [22_M1_Data_Usage_and_Row_Count_Register.md](22_M1_Data_Usage_and_Row_Count_Register.md) | **How much data there is, and who spent what** — the non-additive counting rule (**1110 corpus + 286 holdout = 1396 distinct rows**, not 4,726), the stage-by-stage usage table, what each split was used for, which model touched which data, the never-mix table, and why 166 validation rows carrying every selection decision means validation figures are not promotion evidence. |
| [23_M1_Retrieval_Augmented_Evidence_Branch.md](23_M1_Retrieval_Augmented_Evidence_Branch.md) | Branch C design: power arithmetic, Output-4 argument, hybrid retrieval architecture, leakage rules, kill criteria, implementation status |
| [24_M1_RAHMT_Hybrid_Architecture.md](24_M1_RAHMT_Hybrid_Architecture.md) | The trained hybrid: five-stage architecture, three branches, fusion/calibration/constraints/evidence, measured results, artifact bundle, Enigmatrix backend integration, limitations, promotion gate |
| 23 | [23_M1_Retrieval_Augmented_Evidence_Branch.md](23_M1_Retrieval_Augmented_Evidence_Branch.md) | **Branch C — the retrieval-augmented evidence branch**, additive alongside the frozen Branch A. Opens with the power arithmetic that kills the accuracy framing (167 test rows, 7 errors → Branch C must fix 6 of 7 and break none for *p* < 0.05; one `EPF_ETF_CHANGE` row is worth 12.5 points of macro-F1), then argues the branch on what it uniquely delivers: **Output 4**, which does not exist today because `LinearSVCGazetteInference` returns `confidence=None` by design. Contains the hybrid BM25 + LaBSE architecture, the C1 precedent-vote and C2 `λ`-fusion design, the leakage rules in §7, the kill criteria in §8, and — added 2026-08-03 — **§11 implementation status**: Phases 1–4 and 8 built and tested, the deviations from plan and why, the Sinhala/Tamil tokenizer defect found in the process, and the confirmation that the Step-41 duplicate-text leakage is still present in the canonical V6. |
| 24 | [24_M1_RAHMT_Hybrid_Architecture.md](24_M1_RAHMT_Hybrid_Architecture.md) | **Gazette-SME-RA-HMT — the hybrid four-output classifier, trained and integrated 2026-08-03.** The first system in the module that emits all four required outputs from one pass. Contains the five-stage architecture (preprocess → three branches + rule prior → simplex fusion → hierarchical multi-task decode → constraint/calibration/evidence), the per-branch design and measured scores (A `0.9197`, B `0.6443`, C `0.8590`), the validation-fitted fusion configuration (`tfidf 0.35 · retrieval 0.30 · rules 0.20 · xlmr 0.15`, T `0.4625`, thresholds `0.52 / 0.50 / 0.50 / 0.43`), the R1–R5 constraint contract and its **0/167** violation rate, the calibration result that is the real headline (fusion ECE `0.1357` → calibrated `0.0319`), the evidence scorer, the full 10-row ablation with bootstrap CIs, the two source corrections found on the way to the local bundle (float32 probabilities > 1.0; whitespace-collapse breaking multiline notice splitting, 1 unit → 3), how the five Kaggle archives were actually assembled, the Enigmatrix `rahmt` backend wiring across ml/backend/frontend, nine stated limitations, and the open promotion gate.

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
| [20_M1_Multitask_Classifier_Upgrade.md](20_M1_Multitask_Classifier_Upgrade.md) | V7 multitask: domain + sectors + derived relevance, V6 audit, gates, steps 41–53, plus the V7-M line and steps 53A–56 |
| [21_M1_Data_Limitations_and_Risk_Register.md](21_M1_Data_Limitations_and_Risk_Register.md) | Open and resolved limitations, severity table, avoided failure modes, lock-manifest declaration, reporting rules |
| [22_M1_Data_Usage_and_Row_Count_Register.md](22_M1_Data_Usage_and_Row_Count_Register.md) | Row counts, non-additive counting rule, stage-by-stage usage, per-model split usage, never-mix table |

**File counts:** 24 numbered main docs (01–24) + this README = **25 canonical Markdown files** at the Module 1 root. Historical implementation notes remain in `final/`, `findings/`, `local-dev/`, and `planned-for-development/`, but root companion files have been retired.

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
| C     | Classification     | **TF-IDF + LinearSVC** on the 8-domain taxonomy, frozen 2026-08-01 (test macro-F1 0.9472). Category only — no sector head, and `confidence` is `null` by design. The XLM-R multitask path has now failed one strict gate (sector macro-F1 `0.888330`) and its replacement candidate is untested; nothing has been promoted. See [18_M1_Dataset_And_Model_Lineage.md](18_M1_Dataset_And_Model_Lineage.md) |
| D     | Secondary Tracking | Watchers on IRD, EPF, ETF, eROC portals; 5 news RSS feeds (every 2h)                |
| E     | Summarisation      | **Backend slice shipped and live-backfilled; trilingual since 2026-08-02.** The deterministic 80-English audit passed 80/80; four false sentence-count reviews were repaired, leaving 7 genuine low-margin reviews. EN/SI/TA are now *composed* from the same verified slots (no MT), and an unrouted row is **held** rather than summarised early — four release paths bring it back. Human faithfulness review, review UI, native-speaker template review, and full coverage remain open. See [19_M1_Regulation_Summarization.md](19_M1_Regulation_Summarization.md) §8 |
| E2    | Translation        | NLLB-200 pull worker shipped and still carries `title` + `real_world_example`. **Summaries left this path on 2026-08-02** after the SI/TA numeric audit passed only 10/152 checks — they are composed per locale instead, making numeric preservation exact by construction. See [10_M1_Sinhala_Tamil_NLP.md §10.7](10_M1_Sinhala_Tamil_NLP.md) |
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
| Stage-E numeric-locale pass rate | 10 / 152 = **6.58%** *(machine-translated summaries, measured 2026-08-02)* |
| Stage-E rows requiring review | 7 |
| SME survey sessions / completed | 0 / 0 against a target of 100 |

Two of those are the honest weak points: **numeric-locale checking passes 6.58%**, and **SME recruitment stands at zero against a target of 100**. Neither is visible in the submitted report.

**Update, same day.** The 6.58% is what retired machine translation for summaries. Locale summaries are now composed from the same verified slots as the English one, so the figure in a Sinhala summary is the figure in the gazette by construction rather than by a model getting it right ([19_M1 §8.2](19_M1_Regulation_Summarization.md)). The 6.58% therefore remains the measurement that justified the change — it is not a number to be re-measured on the new path and quietly improved, and it should be reported as the evidence it is. Rows summarised before the change still carry MT locale text until re-composed; a re-run is needed before any coverage claim is made about the corpus as a whole. SME recruitment is unchanged at zero.
