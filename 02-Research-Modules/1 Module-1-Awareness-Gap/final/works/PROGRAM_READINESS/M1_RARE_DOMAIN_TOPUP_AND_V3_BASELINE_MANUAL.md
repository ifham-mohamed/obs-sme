# M1 Rare-Domain Top-Up And V3 Baseline Manual

Updated: 2026-07-31  
Repo: `C:\Reasearch\xyz`  
Use this manual when regenerating rare-domain batches, resolving annotation exports, freezing a new gold dataset, or rerunning the v3 baseline.

## 1. Current Accepted State

```text
accepted version       = v3
gold file              = C:\Reasearch\xyz\research\data\labeling\gold_standard_v3_1128.csv
gold rows              = 1128
tasks                  = 1128
annotations            = 2256
category kappa         = 0.947215
mean sector kappa      = 0.965567
SME relevance kappa    = 0.914637
disagreement rows      = 44
best current baseline  = TF-IDF LinearSVC
baseline macro-F1      = 0.908012
```

Do not use the older 800-row v1 files as the current training source unless the experiment specifically says "v1 comparison".

## 2. Artifact Map

| Artifact | Path |
|---|---|
| Batch 06 generator | `C:\Reasearch\xyz\scripts\collect_rare_domain_topup.py` |
| Batch 07 PDF generator | `C:\Reasearch\xyz\scripts\collect_pdf_rare_topup.py` |
| Batch 06 CSV | `C:\Reasearch\xyz\research\data\labeling\batch_06.csv` |
| Batch 07 CSV | `C:\Reasearch\xyz\research\data\labeling\batch_07.csv` |
| Batch 06 export | `C:\Reasearch\xyz\research\data\labeling\batch_06_annotations_full.json` |
| Batch 07 export | `C:\Reasearch\xyz\research\data\labeling\batch_07_annotations_full.json` |
| Current live gold | `C:\Reasearch\xyz\research\data\labeling\gold_standard.csv` |
| Frozen v3 gold | `C:\Reasearch\xyz\research\data\labeling\gold_standard_v3_1128.csv` |
| Frozen v3 IAA | `C:\Reasearch\xyz\research\data\labeling\iaa_report_v3_1128.json` |
| Frozen v3 summary | `C:\Reasearch\xyz\research\data\labeling\iaa_report_summary_v3_1128.csv` |
| Frozen v3 disagreements | `C:\Reasearch\xyz\research\data\labeling\disagreements_v3_1128.csv` |
| V3 split | `C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations_v3_1128_stratified` |
| V3 baseline report | `C:\Reasearch\xyz\storage\models\m1\baselines_v3_1128_stratified` |

## 3. Regenerate Batch 06

Use Batch 06 when you want rare-domain candidates from listing metadata and local structured workbooks.

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml

uv run --extra research python ..\scripts\collect_rare_domain_topup.py `
  --batch 6 `
  --years 2010-2026 `
  --batch-size 200 `
  --target-per-domain 50 `
  --overwrite
```

Expected outputs:

```text
research\data\labeling\batch_06.csv
research\data\labeling\batch_06.xlsx
research\data\labeling\batch_06_provenance.json
research\data\labeling\rare_domain_candidate_pool_v2.csv
research\data\labeling\rare_domain_candidate_pool_v2.xlsx
```

Expected validation:

```text
rows = 200
unique regulation_id = 200
blank chunks = 0
overlap with previous gold = 0
```

## 4. Regenerate Batch 07

Use Batch 07 when you need PDF-backed official text for rare-domain classes.

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml

uv run --extra research python ..\scripts\collect_pdf_rare_topup.py `
  --batch 7 `
  --years 2010-2026 `
  --batch-size 200 `
  --target-per-domain 60 `
  --overwrite
```

Expected outputs:

```text
research\data\labeling\batch_07.csv
research\data\labeling\batch_07.xlsx
research\data\labeling\batch_07_provenance.json
research\data\labeling\rare_domain_pdf_candidate_pool_v3.csv
research\data\labeling\rare_domain_pdf_candidate_pool_v3.xlsx
raw\rare_domain_pdf_cache
```

Expected validation:

```text
rows = 128
unique regulation_id = 128
blank chunks = 0
blank PDF URLs = 0
missing PDF text = 0
overlap with previous gold = 0
```

## 5. Label Studio Workflow

Start Label Studio:

```powershell
cd C:\Reasearch\xyz

$env:LABEL_STUDIO_BASE_DATA_DIR = "C:\Reasearch\xyz\mydata"
$env:LOCAL_FILES_SERVING_ENABLED = "true"
$env:LOCAL_FILES_DOCUMENT_ROOT = "C:\Reasearch\xyz"

label-studio start --host 127.0.0.1 --port 8080
```

For each batch:

1. Create a separate project with the correct project name.
2. Import the matching batch CSV.
3. Use the same XML interface: `C:\Reasearch\xyz\research\data\label_studio_config.xml`.
4. Complete two annotator passes.
5. Export full JSON with all tasks and annotations.
6. Save the export under `C:\Reasearch\xyz\research\data\labeling`.

Project names used:

```text
Batch 06: M1 Gazette Classifier - RareDomain Top-Up Batch 06
Batch 07: M1 Gazette Classifier - PDF Rare Top-Up Batch 07
```

Research limitation:

Batch 06 and Batch 07 were assisted/direct Label Studio annotations using rule-based preparation logic. If the final evaluation needs stricter manual evidence, review and confirm those rows in Label Studio before submission.

## 6. Resolve IAA Through Batch 07

```powershell
cd C:\Reasearch\xyz

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

Expected accepted output:

```text
tasks              = 1128
annotations        = 2256
category kappa     = 0.947215
mean sector kappa  = 0.965567
SME relevance kappa= 0.914637
disagreement rows  = 44
gold rows          = 1128
```

## 7. Validate And Freeze V3

Validate:

```powershell
cd C:\Reasearch\xyz

$gold = Import-Csv research\data\labeling\gold_standard.csv

"rows=$($gold.Count)"
"unique_ids=$(($gold.regulation_id | Select-Object -Unique).Count)"
"blank_category=$(($gold | Where-Object { [string]::IsNullOrWhiteSpace($_.change_category) }).Count)"
"blank_relevance=$(($gold | Where-Object { [string]::IsNullOrWhiteSpace($_.is_sme_relevant) }).Count)"

$gold | Group-Object batch_id | Select-Object Name,Count
$gold | Group-Object change_category | Select-Object Name,Count
```

Freeze:

```powershell
cd C:\Reasearch\xyz

Copy-Item research\data\labeling\gold_standard.csv research\data\labeling\gold_standard_v3_1128.csv -Force
Copy-Item research\data\labeling\iaa_report.json research\data\labeling\iaa_report_v3_1128.json -Force
Copy-Item research\data\labeling\iaa_report_summary.csv research\data\labeling\iaa_report_summary_v3_1128.csv -Force
Copy-Item research\data\labeling\disagreements.csv research\data\labeling\disagreements_v3_1128.csv -Force
```

## 8. Create Stratified Split

Use a stratified split for current model work. The older `--by key` split was not good enough after rare-domain expansion because rare classes could land unevenly.

Current split path:

```text
C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations_v3_1128_stratified
```

Expected split sizes:

```text
train = 790
val   = 169
test  = 169
```

## 9. Run V3 Baselines

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml

uv run python -m m1.model.baselines `
  --data datasets\m1_regulations_v3_1128_stratified `
  --report ..\storage\models\m1\baselines_v3_1128_stratified
```

Expected current results:

```text
tfidf_logreg macro-F1 = 0.862652
tfidf_linsvc macro-F1 = 0.908012
```

## 10. Decision Rules

Use these rules before claiming final model success:

1. Do not promote the old v1 LoRA run.
2. Treat v3 TF-IDF LinearSVC as the current strongest baseline.
3. A future XLM-R LoRA run must beat 0.9080 macro-F1 on the same v3 split before it is worth promoting.
4. The final target remains 0.92 macro-F1.
5. `EPF_ETF_CHANGE` and `PENALTY_ENFORCEMENT` need the most review.
6. If strict annotation evidence is required, manually audit Batch 06 and Batch 07 because those two batches used assisted/direct annotation.

## 11. What To Document In The Thesis

Report the work as:

- A first 800-row labelled dataset was built through Batches 02-05.
- Rare-domain scarcity was identified through v1 evaluation.
- Batch 06 and Batch 07 were added as targeted rare-domain top-up.
- The final current dataset contains 1128 resolved labelled records.
- IAA is strong: category kappa 0.9472, mean sector kappa 0.9656, SME relevance kappa 0.9146.
- TF-IDF LinearSVC reached 0.9080 macro-F1 on the v3 stratified split.
- The classifier is close to, but not yet past, the 0.92 target.
- Transformer LoRA was tested earlier but not promoted because it underperformed the baseline.
