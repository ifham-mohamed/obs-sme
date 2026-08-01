# M1 Program Readiness Master Index

> Updated: 2026-07-31  
> Repo: `C:\Reasearch\xyz`  
> Scope: final readiness map for the M1 work completed in the July 30 annotation/IAA/documentation session.

## 1. Current Program State

The M1 annotation and gold-labeling gate is complete. The first training-preparation pass is also complete: v1 gold files were frozen, deterministic train/validation/test parquet splits were generated, TF-IDF baselines were run, and a CPU-only LoRA smoke test wrote a registry/checkpoint. The full LoRA result is still pending because this machine has no CUDA GPU and rare-domain coverage remains weak.

```text
gold rows          = 800
unique IDs         = 800
annotations        = 1600
tasks              = 800
manual resolutions = 40
auto-agreed rows   = 760
category kappa     = 0.871534
mean sector kappa  = 0.863776
SME relevance kappa= 0.723518
```

Final gold files:

```text
C:\Reasearch\xyz\research\data\labeling\gold_standard.csv
C:\Reasearch\xyz\research\data\labeling\iaa_report.json
C:\Reasearch\xyz\research\data\labeling\iaa_report_summary.csv
C:\Reasearch\xyz\research\data\labeling\disagreements.csv
C:\Reasearch\xyz\research\data\labeling\manual_resolutions.csv
C:\Reasearch\xyz\research\data\labeling\gold_standard_v1_800.csv
C:\Reasearch\xyz\research\data\labeling\iaa_report_v1_800.json
C:\Reasearch\xyz\research\data\labeling\iaa_report_summary_v1_800.csv
```

Training-preparation artifacts:

```text
C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations\train.parquet  = 560 rows
C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations\val.parquet    = 120 rows
C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations\test.parquet   = 120 rows
C:\Reasearch\xyz\storage\models\m1\baselines_v1\baselines.json
C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations_smoke\train.parquet
C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations_smoke\val.parquet
C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations_smoke\test.parquet
C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model_registry.json
C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model.pt
```

Model-prep metrics:

```text
split method              = deterministic --by key, not temporal
TF-IDF LogReg macro-F1    = 0.4980
TF-IDF LinearSVC macro-F1 = 0.6167
CUDA availability         = false; CPU only
full-split CPU attempt    = no registry written; not counted as smoke evidence
smoke split               = train 16 / val 8 / test 8
LoRA smoke base           = xlm-roberta-base
LoRA smoke config         = seed 42, r=8, epochs=1
LoRA smoke val macro-F1   = 0.1111
LoRA smoke test macro-F1  = 0.0000
LoRA smoke gate_pass      = false
```

Final batch annotation exports:

```text
C:\Reasearch\xyz\research\data\labeling\batch_02_annotations_full.json
C:\Reasearch\xyz\research\data\labeling\batch_03_annotations_full.json
C:\Reasearch\xyz\research\data\labeling\batch_04_annotations_full.json
C:\Reasearch\xyz\research\data\labeling\batch_05_annotations_full.json
```

## 2. Read These Manuals

| Manual | Use it for |
|---|---|
| `M1_PHASE3_ANNOTATION_AND_ACTIVE_LEARNING_USER_MANUAL.md` | How calibration, Label Studio, batch creation, IAA reduction, manual resolution, and gold export work. |
| `2026-07-31_M1_FULL_CHAT_EXECUTION_LOG_AND_RESULTS.md` | Full preserved execution log from Label Studio setup through calibration, IAA, v1 gold freeze, split, baselines, CPU smoke errors/results, and vault sync. |
| `M1_TRAINING_PREPARATION_AND_SMOKE_TEST_RUNBOOK.md` | How the 800-row gold set was split, how baselines/smoke were run, and what must happen before full LoRA training. |
| `M1_RARE_DOMAIN_TOPUP_AND_V3_BASELINE_MANUAL.md` | How Batch 06/07 rare-domain top-up, v3 gold freezing, v3 stratified splitting, and the latest 0.9080 LinearSVC baseline were produced. |
| `M1_EXTRACTION_ACCURACY_AND_DATASET_MANAGEMENT_MANUAL.md` | How Excel upload, sealed datasets, DB snapshots, measurement runs, dashboards, and report export work. |
| `M1_SUMMARIZATION_TRANSLATION_READINESS_PLAN.md` | How to build the next trilingual SME summary pipeline using classified fields and NLLB translation. |
| `M1_NON_CODING_TASKS_AND_GOLIVE_READINESS_PLAN.md` | Non-coding evidence, screenshots, admin/user readiness, and final go-live checklist. |
| `M1_MODEL_INTEGRATION_AND_REORGANIZATION_SESSION_RECORD_2026-08-01.md` | **Session-level record for 2026-08-01.** V6 correction, the model bake-off that closed Phase-3 model selection, backend wiring, the margin threshold derivation, the applied database migration, and the workspace/vault reorganization. Start here for anything dated 2026-08-01. |
| `LOG_AND_WORKS/2026-08-01_M1_INTEGRATION_REORG_AND_SYNC_WORK_RECORD.md` | Stage-by-stage detail behind the session record above — exact commands, per-file move manifest, threshold sweep, and schema verification output. |

> **Superseded by 2026-08-01:** rows in this index that describe v3 as the active training dataset, the 0.9080 LinearSVC baseline, or full LoRA promotion as the pending gate are **out of date**. Phase-3 model selection is closed: the frozen primary is TF-IDF + balanced LinearSVC on the **V6** dataset with temporal-test macro-F1 **0.9472**, and XLM-R was trained but **not promoted** (test 0.7436). See the session record above and [[18_M1_Dataset_And_Model_Lineage]].

> **Sector-head decision closed after the 2026-08-01 record:** the frozen primary model is category-only. Do **not** run a split production arrangement where LinearSVC supplies category and ONNX supplies sectors. Sector routing remains from existing or expert-maintained `m1_regulation_sectors` rows until a separate sector model is trained, evaluated, and promoted.

## 3. What Was Done In This Chat/Work Session

Completed:

1. Confirmed all relevant real batches have exactly two annotations per task.
2. Fixed the temporary Batch 05 `1601` annotation export problem.
3. Re-ran the final 4-batch IAA reducer.
4. Verified `gold_standard.csv` contains exactly 800 unique rows.
5. Confirmed all 40 disagreement rows are covered by `manual_resolutions.csv`.
6. Documented the final Phase 3 process in the vault.
7. Reviewed the extraction-accuracy measurement feature and added its missing documentation.
8. Wrote the summarization/NLLB readiness plan for the next implementation slice.
9. Froze the accepted 800-row gold set as `gold_standard_v1_800.csv` plus versioned IAA report files.
10. Generated train/validation/test parquet splits with `m1.model.data --by key`.
11. Ran TF-IDF baseline models and saved `baselines_v1`.
12. Verified this laptop is CPU-only and completed a one-epoch LoRA smoke test only to prove the training loop and artifact writing path.
13. Added the dedicated training-preparation and smoke-test runbook with warnings, split distribution, baseline interpretation, and the real GPU-training order.

## 3.1 2026-07-31 Rare-Domain V3 Addendum

The v1 800-row dataset remains a historical milestone, but the current active training dataset is now v3:

```text
gold rows            = 1128
tasks                = 1128
annotations          = 2256
category kappa       = 0.947215
mean sector kappa    = 0.965567
SME relevance kappa  = 0.914637
disagreement rows    = 44
```

New top-up batches:

```text
Batch 06 = 200 rare-domain metadata/workbook candidates
Batch 07 = 128 PDF-backed rare-domain candidates
```

Current v3 category distribution:

```text
SECTOR_SPECIFIC          695
IMPORT_EXPORT            112
TAX_RATE_CHANGE           82
LABOUR_LAW                74
PENALTY_ENFORCEMENT       66
PRODUCT_STANDARD          52
BUSINESS_REGISTRATION     36
EPF_ETF_CHANGE            11
```

Current v3 model-preparation evidence:

```text
split path                 = C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations_v3_1128_stratified
train / val / test          = 790 / 169 / 169
TF-IDF LogReg macro-F1      = 0.862652
TF-IDF LinearSVC macro-F1   = 0.908012
baseline report             = C:\Reasearch\xyz\storage\models\m1\baselines_v3_1128_stratified
```

Important caveat: Batch 06 and Batch 07 used assisted/direct Label Studio annotation. They are acceptable as development evidence, but manually audit them if strict independent human annotation evidence is required for the final submission.

## 4. Parent Document Mapping

| Parent document | Status after this session | Next edit/use |
|---|---|---|
| `00_INDEX.md` | Navigation remains valid. | Link this Program Readiness index if a final status section is added. |
| `01_M1_Research_Problem.md` | Research motivation unchanged. | Use final IAA and gold set as evidence for methodology readiness. |
| `02_M1_Data_Requirements.md` | Dataset/gold/summary fields are relevant. | Add final summary metadata fields after summarization implementation. |
| `03_M1_Data_Collection.md` | Extraction and snapshot evidence remain important. | Add final real measurement run details after Excel-vs-DB measurement. |
| `04_M1_Preprocessing_Pipeline.md` | Chunking/cleaning supports classification and future summarization. | Add summarizer input selection once implemented. |
| `05_M1_Model_Architecture.md` | Labeling, active-learning data, rare-domain top-up, baseline evidence, and smoke-test evidence are now concrete. | Reference v1 as historical and v3 as the active training dataset. Keep the Batch 06/07 assisted-annotation caveat. |
| `06_M1_Training_Evaluation.md` | V3 stratified split and baseline are complete; full LoRA promotion remains pending. | Add final dataset hash, split fingerprint, future GPU LoRA results, per-slice metrics, and export evidence only after a model beats the v3 LinearSVC baseline. |
| `07_M1_Deployment_Integration.md` | Still blocked by trained model and summary stage. | Add summarization latency budget and ONNX export only after training. |
| `08_M1_Full_System_Architecture.md` | Dataset measurement and annotation flows are now clearer. | Add end-to-end gold dataset and measurement evidence diagrams if needed. |
| `09_M1_Annotation_Guidelines.md` | Annotation gate is complete through Batch 07. | Add final IAA table, rare-domain top-up method, and assisted-annotation caveat. |
| `10_M1_Sinhala_Tamil_NLP.md` | NLLB title translation exists; summary translation plan is pending. | Add NLLB summary backfill after implementation. |
| `11_M1_API_Reference.md` | Dataset/measurement/translation APIs are relevant. | Add final summary-generation/review endpoints if new APIs are built. |
| `12_M1_Monitoring_Maintenance.md` | Monitoring still not complete. | Add measurement-run health, summary completeness, translation completeness, and model-drift checks. |
| `13_M1_Folder_Structure_and_Implementation_Flow.md` | Folder ownership remains valid. | Add final gold artifacts and Program Readiness docs to folder examples. |
| `14_M1_Tracking_Workflows.md` | Annotation and dataset-measurement workflows are documented. | Add screenshots for dataset upload, DB snapshot, measurement dashboard, and trilingual summaries. |
| `15_M1_Folder_Reference.md` | Research artifact paths are now important. | Add Batch 02-07 exports, v3 frozen gold-standard files, and v3 baseline outputs. |
| `16_M1_Development_Roadmap.md` | Phase 3 gold labeling plus rare-domain v3 training-prep pass are complete. | Move LoRA promotion behind the v3 LinearSVC baseline and rare-class error-review gate. |

## 5. What Is Still Missing

### Must Do Before Final LoRA Claim

- Use the v3 stratified split for current classifier evidence. The older deterministic `--by key` split remains historical v1 evidence only.
- Decide whether to collect more `EPF_ETF_CHANGE` examples. It is no longer zero, but v3 still has only 11 total rows.
- Review `PENALTY_ENFORCEMENT` errors because it is the weakest current LinearSVC class.
- Record dataset hash and split fingerprint.
- Run full XLM-R + LoRA training on a CUDA machine. The CPU smoke test is only a pipeline proof and must not be promoted.
- Run final evaluation, slice analysis, error analysis, and ONNX export only after full training.

### Must Do Before Extraction Accuracy Claim

- Upload real ground-truth Excel.
- Seal the uploaded dataset version.
- Create a DB snapshot version for the same scope.
- Run the measurement.
- Save the measurement run ID, dataset version IDs, Markdown report, and screenshots.

### Must Do Before Trilingual Summary Claim

- Implement `summary_en` generation from classified/extracted text.
- Backfill `summary_si` and `summary_ta` through NLLB.
- Preserve numbers, dates, percentages, gazette numbers, and legal citations.
- Add review flags for low-confidence summaries/translations.
- Store summaries in DB and include them in snapshots/measurement.

## 6. Correct Next Work Order

```text
1. Keep v1 as historical 800-row evidence. [done]
2. Use v3 1128-row gold as the active training dataset. [done]
3. Use the v3 stratified split and LinearSVC 0.9080 baseline as the current model gate. [done]
4. Review or manually audit Batch 06/07 if strict independent annotation evidence is required.
5. Improve `EPF_ETF_CHANGE` and `PENALTY_ENFORCEMENT` before claiming robust rare-domain performance.
6. Retry XLM-R + LoRA only if the diagnostic plan can beat the v3 LinearSVC baseline.
7. Evaluate/export/promote only after passing the 0.92 macro-F1 target and slice checks.
8. Run extraction accuracy measurement evidence workflow.
9. Build trilingual summary + NLLB translation backfill.
10. Update parent M1 docs with final screenshots, metrics, and run IDs.
```

## 7. Do Not Confuse These States

The reducer overwrites the same output files every time. The current accepted v3 command is the one with all six batch exports:

```powershell
uv run python scripts\resolve_iaa.py `
  --input research\data\labeling\batch_02_annotations_full.json `
  --input research\data\labeling\batch_03_annotations_full.json `
  --input research\data\labeling\batch_04_annotations_full.json `
  --input research\data\labeling\batch_05_annotations_full.json `
  --input research\data\labeling\batch_06_annotations_full.json `
  --input research\data\labeling\batch_07_annotations_full.json `
  --lead-annotator 1 `
  --resolutions research\data\labeling\manual_resolutions.csv
```

Do not treat one-batch, two-batch, three-batch, four-batch, or five-batch diagnostic runs as the current final gold state unless the note explicitly says it is a historical v1 or v2 comparison.
