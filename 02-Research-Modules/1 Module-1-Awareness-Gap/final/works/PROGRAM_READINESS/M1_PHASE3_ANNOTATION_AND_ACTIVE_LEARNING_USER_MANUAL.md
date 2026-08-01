# M1 Phase 3 Annotation And Active-Learning User Manual

> Updated: 2026-07-30  
> Repo: `C:\Reasearch\xyz`  
> Research data: `C:\Reasearch\xyz\research\data\labeling`  
> Purpose: document how the Label Studio annotation, IAA reducer, manual resolution, and active-learning batch process is used.

## 1. Current State

| Item | Status |
|---|---|
| Calibration set | Complete: `research\data\calibration_set_v1.csv` |
| Calibration scorer | Complete: `scripts\score_calibration.py` |
| Label Studio config | Complete: `research\data\label_studio_config.xml` |
| Batch 02 | Resolved into gold set |
| Batch 03 | Resolved into gold set |
| Batch 04 | Resolved into gold set after 12 manual fallback reviews |
| Batch 05 | Resolved into gold set after 3 manual reviews |
| Batch 06 | Resolved into v3 gold set after rare-domain metadata/workbook top-up |
| Batch 07 | Resolved into v3 gold set after PDF-backed rare-domain top-up |
| Current accepted gold rows | 1128 |
| Current category kappa | 0.947215 |
| Current mean sector kappa | 0.965567 |
| Current SME relevance kappa | 0.914637 |
| Current best baseline | TF-IDF LinearSVC macro-F1 0.908012 on the v3 stratified split |
| LoRA training | v1 Kaggle LoRA was tested but not promoted; future LoRA must beat the v3 LinearSVC baseline |

Important interpretation:

- `gold_standard.csv` currently reflects Batches 02-07 if the latest accepted v3 reducer command has been run.
- The accepted v3 reducer output has 1128 tasks, 2256 annotations, and 1128 paired tasks.
- Kappa is historical annotator agreement before adjudication. Manual resolutions improve the final gold labels, but they do not rewrite the historical agreement score.
- The final accepted current run is the 6-input Batch 02-07 run. Any diagnostic run with fewer inputs overwrites the same output filenames and must not be treated as the current final gold file.
- Batch 06 and Batch 07 used assisted/direct annotation. If strict independent annotation evidence is required, manually audit or re-confirm those rows in Label Studio.

Final validation snapshot:

```text
batch_02 annotations = 400 / 200 tasks / 2 per task
batch_03 annotations = 400 / 200 tasks / 2 per task
batch_04 annotations = 400 / 200 tasks / 2 per task
batch_05 annotations = 400 / 200 tasks / 2 per task
batch_06 annotations = 400 / 200 tasks / 2 per task
batch_07 annotations = 256 / 128 tasks / 2 per task
total annotations    = 2256
gold rows            = 1128
unique IDs           = 1128
manual_review rows   = 44
```

Final gold distribution:

```text
BUSINESS_REGISTRATION     36
EPF_ETF_CHANGE            11
IMPORT_EXPORT            112
LABOUR_LAW                74
PENALTY_ENFORCEMENT       66
PRODUCT_STANDARD          52
SECTOR_SPECIFIC          695
TAX_RATE_CHANGE           82
```

The full Batch 06/07 generation and v3 baseline workflow is documented in `M1_RARE_DOMAIN_TOPUP_AND_V3_BASELINE_MANUAL.md`.

## 1.1 What Was Developed In This Work Session

This work session moved Phase 3 from "annotation process in progress" to "800-row gold dataset ready, split/baseline complete, and CPU LoRA smoke verified".

Work completed:

1. Confirmed calibration pass/retest status for Ifham, Reezma, and Ilham.
2. Debriefed annotators on the three study sectors:
   `grocery_retail`, `food_service`, and `general_retail`.
3. Completed dual-annotator Label Studio exports for Batches 02, 03, 04, and 05.
4. Generated and validated Batch 05 through active-learning/minority-domain sampling.
5. Fixed the Batch 05 duplicate-annotation problem where one task temporarily had 3 annotations.
6. Re-exported/validated Batch 05 so every task has exactly 2 annotations.
7. Ran `resolve_iaa.py` over Batches 02-05.
8. Added all 40 disagreement rows to `manual_resolutions.csv`.
9. Produced the final current `gold_standard.csv` with 800 resolved rows.
10. Documented the process in the vault and connected it to the parent M1 docs.

Approach used:

- Use Label Studio only for human annotation capture and export.
- Use `score_calibration.py` for annotator qualification.
- Use `sample_for_labeling.py` for reproducible batch creation and provenance.
- Use `resolve_iaa.py` as the single reducer for IAA, disagreements, manual resolutions, and gold export.
- Keep manual adjudication separate in `manual_resolutions.csv` so final labels remain auditable.
- Treat high agreement as evidence only when there are exactly two independent annotations per task.

Validity warning:

If a future batch shows perfect agreement, verify that the two annotators actually worked independently. If one annotator copied another, that batch should be redone before using it for model training.

## 1.2 Training Prep And Smoke Test Status

After accepting the 800-row gold set, the first model-preparation pass was completed.

Frozen v1 evidence files:

```text
C:\Reasearch\xyz\research\data\labeling\gold_standard_v1_800.csv
C:\Reasearch\xyz\research\data\labeling\iaa_report_v1_800.json
C:\Reasearch\xyz\research\data\labeling\iaa_report_summary_v1_800.csv
```

Main split command:

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml

uv run --extra research python -m m1.model.data `
  --in ..\research\data\labeling\gold_standard_v1_800.csv `
  --out datasets\m1_regulations `
  --by key
```

Split output:

```text
train = 560 rows -> C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations\train.parquet
val   = 120 rows -> C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations\val.parquet
test  = 120 rows -> C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations\test.parquet
```

Important split limitation:

- This split used `--by key`, not `--by date`, because the current gold file does not contain a reliable `gazette_published_date`.
- It is deterministic, but it is not a strong temporal evaluation split.
- It is not balanced enough for rare-domain claims. `EPF_ETF_CHANGE` has 0 examples, `PRODUCT_STANDARD` has 0 training examples, and `TAX_RATE_CHANGE` has 0 test examples.

Baseline command:

```powershell
uv run --extra training --extra research python -m m1.model.baselines `
  --data datasets\m1_regulations `
  --report ..\storage\models\m1\baselines_v1
```

Baseline result:

```text
TF-IDF LogReg test macro-F1    = 0.4980
TF-IDF LinearSVC test macro-F1 = 0.6167
Report                         = C:\Reasearch\xyz\storage\models\m1\baselines_v1\baselines.json
```

GPU check:

```powershell
uv run --extra training python -c "import torch; print('cuda=', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"
```

Result:

```text
cuda= False
CPU only
```

CPU LoRA smoke command:

```powershell
uv run --extra training --extra research python -m m1.model.train_xlmr `
  --data datasets\m1_regulations_smoke `
  --seeds 42 `
  --base xlm-roberta-base `
  --lora-r 8 `
  --epochs 1 `
  --out ..\storage\models\m1\xlmr_lora_smoke
```

Run-history note:

```text
First attempt:
  data   = datasets\m1_regulations
  scope  = full 560/120/120 split
  result = model downloaded and warnings printed, but no model_registry.json was written
  status = not counted as a valid smoke artifact

Second attempt:
  data   = datasets\m1_regulations_smoke
  scope  = tiny smoke split: train 16, val 8, test 8
  result = model_registry.json and model.pt were written
  status = valid engineering smoke only
```

Smoke result:

```text
val macro-F1       = 0.1111
test macro-F1      = 0.0000
gate_pass          = false
model registry     = C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model_registry.json
checkpoint         = C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model.pt
```

Smoke split distribution:

```text
train 16: SECTOR_SPECIFIC=11, TAX_RATE_CHANGE=2, LABOUR_LAW=2, IMPORT_EXPORT=1
val    8: SECTOR_SPECIFIC=7, PRODUCT_STANDARD=1
test   8: SECTOR_SPECIFIC=8
```

Interpretation:

- The smoke test passed as an engineering check: tokenizer/model download works, LoRA initializes, the training loop runs, and artifacts are written.
- The smoke test failed as a research model: it used a tiny smoke split, one seed, and one epoch, so the F1 scores are not evidence of final classifier performance.
- Do not promote or export the smoke model. The next real classifier step is full LoRA training on a CUDA/GPU machine, or rare-domain top-up before that run.

For the full command order, warning interpretation, class-distribution risk, and GPU-training plan, use:

```text
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\PROGRAM_READINESS\M1_TRAINING_PREPARATION_AND_SMOKE_TEST_RUNBOOK.md
```

## 2. Files You Use

| File | Role |
|---|---|
| `research\data\label_studio_config.xml` | Label Studio labeling interface: category, sectors, SME relevance, confidence, notes |
| `research\data\calibration_set_v1.csv` | Shared calibration set with expert labels |
| `scripts\score_calibration.py` | Scores each annotator against the calibration reference |
| `scripts\sample_for_labeling.py` | Generates Label Studio CSV batches |
| `scripts\resolve_iaa.py` | Parses full Label Studio JSON, computes IAA, emits disagreements, writes gold CSV |
| `research\data\labeling\manual_resolutions.csv` | Final adjudicator decisions for disagreement rows |
| `research\data\labeling\gold_standard.csv` | Training-ready gold rows after reducer/adjudication |
| `research\data\labeling\iaa_report_summary.csv` | Compact metrics for thesis/reporting |
| `research\data\labeling\disagreements.csv` | Audit file of all annotator disagreements |

## 3. Start Label Studio Correctly

Use this from PowerShell:

```powershell
cd C:\Reasearch\xyz

$env:LABEL_STUDIO_BASE_DATA_DIR = "C:\Reasearch\xyz\mydata"
$env:LOCAL_FILES_SERVING_ENABLED = "true"
$env:LOCAL_FILES_DOCUMENT_ROOT = "C:\Reasearch\xyz"
$env:SECRET_KEY = "local-dev-change-this-secret"

label-studio start --host 127.0.0.1 --port 8080
```

Why these variables matter:

- `LABEL_STUDIO_BASE_DATA_DIR` keeps the SQLite DB and media under the repo working folder.
- `LOCAL_FILES_SERVING_ENABLED=true` lets Label Studio preview local files/paths.
- `LOCAL_FILES_DOCUMENT_ROOT=C:\Reasearch\xyz` prevents Label Studio from serving files outside the project root.
- `SECRET_KEY` avoids startup failure or unstable session signing. For a real shared machine, store a strong local value in `C:\Reasearch\xyz\mydata\.env` and do not commit it.

If Label Studio logs this warning:

```text
HOST variable found in environment, but it must start with http:// or https://
```

ignore it if the server still opens at:

```text
http://127.0.0.1:8080
```

## 4. Calibration Process

Run calibration before real annotation. The goal is to catch misunderstandings before they contaminate the full batches.

```powershell
cd C:\Reasearch\xyz

uv run python scripts\score_calibration.py `
  --export research\data\calibration_export_ifham.json `
  --reference research\data\calibration_set_v1.csv `
  --name ifham

uv run python scripts\score_calibration.py `
  --export research\data\calibration_export_reezma_retest.json `
  --reference research\data\calibration_set_v1.csv `
  --name reezma_retest

uv run python scripts\score_calibration.py `
  --export research\data\calibration_export_ilham_retest.json `
  --reference research\data\calibration_set_v1.csv `
  --name ilham_retest
```

Acceptance rule:

- Preferred calibration gate: change-category kappa >= 0.80.
- If an annotator fails or is conditional, explain the mistakes and retest before assigning full batches.
- Do not treat low sector kappa alone as a full failure if category agreement is strong, but use it as feedback.

Main feedback learned in this run:

- Land-title notices are usually not SME relevant.
- Election vacancy notices are usually not SME relevant.
- Public-security, prisons, state-appointment, and large-entity notices are usually not SME relevant.
- A notice is SME relevant only when it directly changes cost, tax, registration, imports/exports, product standards, labour/EPF/ETF, penalties, or operating obligations for the study sectors.

## 5. Creating A Label Studio Batch

Use `sample_for_labeling.py` for normal active-learning batches. Batch 06 and Batch 07 have already been completed as rare-domain top-ups. If another batch is needed after the current v3 dataset, use the next number, usually Batch 08, and document why the new batch is needed.

```powershell
cd C:\Reasearch\xyz

uv run python scripts\sample_for_labeling.py `
  --batch 8 `
  --minority-targeted `
  --target-domains EPF_ETF_CHANGE,PRODUCT_STANDARD,BUSINESS_REGISTRATION,PENALTY_ENFORCEMENT,LABOUR_LAW,IMPORT_EXPORT `
  --n-minority-targeted 120 `
  --n-active-learning 80 `
  --gold-standard research\data\labeling\gold_standard.csv
```

Do not create another batch unless the error analysis justifies it. The current likely reasons are more `EPF_ETF_CHANGE` support, `PENALTY_ENFORCEMENT` boundary review, or a strict manual audit replacement for assisted Batch 06/07 annotations.

Why this sampler exists:

- The corpus is dominated by `SECTOR_SPECIFIC` notices.
- LoRA training needs minority-domain examples too.
- Active learning chooses uncertain rows from a temporary TF-IDF + LogisticRegression model trained on the current gold set.
- Minority targeting tries to fill weak domains first, then active learning and coverage top-up fill the rest.

## 6. Importing A Batch Into Label Studio

Manual UI steps:

1. Open `http://127.0.0.1:8080`.
2. Create a new project named with the batch, for example `M1 Batch 05`.
3. Use the labeling config from:

```text
C:\Reasearch\xyz\research\data\label_studio_config.xml
```

4. Import the batch CSV:

```text
C:\Reasearch\xyz\research\data\labeling\batch_05.csv
```

5. Assign two independent human annotators.

Ethics and validity rule:

- Do not annotate under another person's account.
- Do not let one person fill both annotator accounts.
- IAA is only meaningful when annotators label independently.
- Codex can prepare batches, inspect exports, and adjudicate documentation, but it must not impersonate human annotators.

## 7. Exporting Full Annotation JSON

After both annotators finish the batch, export from Label Studio as full JSON.

Correct naming pattern:

```text
C:\Reasearch\xyz\research\data\labeling\batch_05_annotations_full.json
```

Verify the export shape:

```powershell
cd C:\Reasearch\xyz

$data = Get-Content -LiteralPath "research\data\labeling\batch_05_annotations_full.json" -Raw | ConvertFrom-Json
$users = @{}
$counts = @{}
foreach ($task in $data) {
  $n = @($task.annotations).Count
  if (-not $counts.ContainsKey($n)) { $counts[$n] = 0 }
  $counts[$n]++
  foreach ($ann in @($task.annotations)) {
    $u = [string]$ann.completed_by
    if (-not $users.ContainsKey($u)) { $users[$u] = 0 }
    $users[$u]++
  }
}
"tasks=$($data.Count)"
"annotation_count_distribution=$($counts.GetEnumerator() | ForEach-Object { "$($_.Name):$($_.Value)" })"
"users=$($users.GetEnumerator() | ForEach-Object { "$($_.Name):$($_.Value)" })"
```

Expected for a clean full batch:

```text
tasks=200
total_annotations=400
annotation_count_distribution=2:200
```

## 8. Reducing IAA And Gold Labels

Current next command:

```powershell
cd C:\Reasearch\xyz

uv run python scripts\resolve_iaa.py `
  --input research\data\labeling\batch_02_annotations_full.json `
  --input research\data\labeling\batch_03_annotations_full.json `
  --input research\data\labeling\batch_04_annotations_full.json `
  --input research\data\labeling\batch_05_annotations_full.json `
  --lead-annotator 1 `
  --resolutions research\data\labeling\manual_resolutions.csv
```

Outputs:

```text
research\data\labeling\gold_standard.csv
research\data\labeling\iaa_report.json
research\data\labeling\iaa_report_summary.csv
research\data\labeling\disagreements.csv
```

Why this step is required:

- Label Studio JSON is nested and user-specific.
- Training needs one resolved row per regulation.
- IAA must be measured before adjudication.
- Disagreements must be retained as audit evidence.

## 9. Manual Disagreement Review

You are not re-annotating all rows. You only adjudicate disagreement rows.

Open:

```text
C:\Reasearch\xyz\research\data\labeling\disagreements.csv
```

or the Excel version if generated:

```text
C:\Reasearch\xyz\research\data\labeling\disagreements.xlsx
```

For each unresolved/fallback row, decide the final:

- `chosen_change_category`
- `chosen_affected_sectors`
- `chosen_is_sme_relevant`
- `resolver_notes`

Append decisions into:

```text
C:\Reasearch\xyz\research\data\labeling\manual_resolutions.csv
```

Required columns:

```text
batch_id,regulation_id,regulation_key,gazette_number,chosen_change_category,chosen_affected_sectors,chosen_is_sme_relevant,resolver_id,resolver_notes
```

Example:

```csv
batch_05,00000000-0000-0000-0000-000000000000,GZT_2499_01,2499/01,TAX_RATE_CHANGE,"grocery_retail,food_service,general_retail",True,codex_manual_review,"VAT rate change directly affects pricing and compliance for all study sectors."
```

Adjudication rule:

- If the notice creates a direct SME obligation, cost, tax, registration, import/export, product, labour, EPF/ETF, or penalty effect, mark it SME relevant.
- If it is land title, election, prison/public-security, appointment, municipal boundary, or single-large-entity governance without SME operating impact, mark it not SME relevant.

After appending manual rows, rerun `resolve_iaa.py` with the same command.

## 10. When You Can Train LoRA

LoRA can move to training preparation when all of these are true:

- `gold_standard.csv` has 800 rows.
- `regulation_id` is unique.
- blank `change_category` count is 0.
- blank `is_sme_relevant` count is 0.
- category kappa is >= 0.75.
- rare-domain coverage is defensible, or the thesis explicitly states the corpus limitation.
- Batch 05 fallback rows have been manually reviewed.

Current known weakness:

```text
EPF_ETF_CHANGE = 0 in the accepted 800-row gold set.
PRODUCT_STANDARD, BUSINESS_REGISTRATION, PENALTY_ENFORCEMENT, IMPORT_EXPORT are still below the preferred 50/domain target.
```

If the final gold set still cannot reach 50/domain, document the limitation and collect more rare-domain source notices before final model training.
