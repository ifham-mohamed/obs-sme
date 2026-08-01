# Module 1 Full Work Session Chronology And Evidence Trail

Created: 2026-07-31 23:20:39 +05:30  
Repo: `C:\Reasearch\xyz`  
Vault file: `E:\Obsidian\sme\Final-Report\06_M1_FULL_WORK_SESSION_CHRONOLOGY_2026-07-31.md`  
Scope: the full practical chat workflow from Label Studio setup, calibration, annotation, IAA, gold datasets, training errors, Kaggle runs, rare-domain top-up, Batch 06/07, v3 baseline, and documentation sync.

> Security note: one chat message contained an annotator password. This chronology intentionally does not record that password. It records the workflow and evidence only.

---

## 1. Working Folders

```text
Main repo                         C:\Reasearch\xyz
ML package                        C:\Reasearch\xyz\enigmatrix-ml
Research data                     C:\Reasearch\xyz\research\data
Labeling data                     C:\Reasearch\xyz\research\data\labeling
Label Studio local data           C:\Reasearch\xyz\mydata
Model storage                     C:\Reasearch\xyz\storage\models\m1
Kaggle result extraction          C:\Reasearch\xyz\storage\models\m1\kaggle_v1
SME Obsidian vault                E:\Obsidian\sme
Module 1 vault docs               E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap
Program readiness docs            E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\PROGRAM_READINESS
Final report evidence docs        E:\Obsidian\sme\Final-Report
```

---

## 2. Label Studio Startup

Command used:

```powershell
cd C:\Reasearch\xyz

$env:LABEL_STUDIO_BASE_DATA_DIR = "C:\Reasearch\xyz\mydata"
$env:LOCAL_FILES_SERVING_ENABLED = "true"
$env:LOCAL_FILES_DOCUMENT_ROOT = "C:\Reasearch\xyz"

label-studio start --host 127.0.0.1 --port 8080
```

Observed output:

```text
=> Database and media directory: C:\Reasearch\xyz\mydata
=> Static URL is set to: /static/
! HOST variable found in environment, but it must start with http:// or https://, ignore it: 127.0.0.1
Read environment variables from: C:\Reasearch\xyz\mydata\.env
get 'SECRET_KEY' casted as '<class 'str'>' with default ''
```

Interpretation:

- Label Studio used `C:\Reasearch\xyz\mydata`.
- Local file serving was enabled.
- The `HOST` warning was not fatal.
- The `SECRET_KEY` message came from Label Studio `.env` loading.

---

## 3. Calibration Stage

Commands:

```powershell
cd C:\Reasearch\xyz

uv run python scripts\score_calibration.py --export research\data\calibration_export_ifham.json --reference research\data\calibration_set_v1.csv --name ifham
uv run python scripts\score_calibration.py --export research\data\calibration_export_reezma.json --reference research\data\calibration_set_v1.csv --name reezma
uv run python scripts\score_calibration.py --export research\data\calibration_export_ilham.json --reference research\data\calibration_set_v1.csv --name ilham
```

Initial results:

```text
ifham:
  scorable docs      = 19
  category kappa     = 0.875
  sector mean kappa  = 0.541
  exact agreement    = 89.5%
  verdict            = PASS

reezma:
  scorable docs      = 19
  category kappa     = 0.752
  sector mean kappa  = 0.115
  exact agreement    = 78.9%
  verdict            = CONDITIONAL

ilham:
  scorable docs      = 19
  category kappa     = 0.506
  sector mean kappa  = 0.002
  exact agreement    = 57.9%
  verdict            = FAIL
```

Ilham retest:

```powershell
uv run python scripts\score_calibration.py --export research\data\calibration_export_ilham_retest.json --reference research\data\calibration_set_v1.csv --name ilham_retest
```

```text
category kappa     = 0.875
sector mean kappa  = 0.541
exact agreement    = 89.5%
verdict            = PASS
```

Reezma retest:

```powershell
uv run python scripts\score_calibration.py --export research\data\calibration_export_reezma_retest.json --reference research\data\calibration_set_v1.csv --name reezma_retest
```

```text
category kappa     = 0.815
sector mean kappa  = 0.541
exact agreement    = 84.2%
verdict            = PASS
```

Conclusion:

- Ifham passed immediately.
- Reezma and Ilham needed retest/debrief before full annotation.
- All production annotators were allowed after passing/retesting.

---

## 4. Annotator Debrief Rules

Sector definitions:

```text
grocery_retail = grocery shops, kade, mini marts, small supermarkets
food_service   = restaurants, cafes, bakeries, take-away food
general_retail = textile, electronics, hardware, other retail shops
```

Additional SME relevance rules:

```text
land-title notices are usually not SME relevant
election vacancy notices are usually not SME relevant
public-security/prisons/state-appointment notices are usually not SME relevant
large-entity notices are usually not SME relevant
SME relevant means direct change to tax, imports, product standards, labour, EPF/ETF, registration, penalties, costs, or operating obligations
```

---

## 5. Multi-Annotator Label Studio Behavior

Question: can Reezma annotate in the same project without overwriting Ifham?

Finding:

```text
Existing Ifham result opened as Update.
Create an annotation opened a blank Submit state.
After Reezma saved, UI showed both IF and RE.
No Ifham annotation was overwritten.
```

Rule:

- Use `Create an annotation` for the second annotator.
- Do not edit another annotator's saved annotation.

---

## 6. Batch 02

Project:

```text
M1 Gazette Classifier - Real Batch 02
Project ID: 8
```

Ifham verified:

```text
200 / 200 tasks annotated
submitted annotations = 200
Label Studio user ID = 1
all tasks include confidence
40 low-confidence rows include notes
SME relevant = 15
SME false / no sectors = 185
```

Reezma verified:

```text
Ifham annotations = 200
Reezma annotations = 199 initially
total submitted annotations = 399 initially
task 10 skipped exactly as requested
task 10 remained Ifham-only at that point
Ifham annotation was not overwritten
```

Final Batch 02 export state:

```text
tasks = 200
total_annotations = 400
annotation_count_distribution = Counter({2: 200})
users = {'1': 200, '3': 200}
```

Final export:

```text
C:\Reasearch\xyz\research\data\labeling\batch_02_annotations_full.json
```

---

## 7. Batch 03

Project:

```text
M1 Gazette Classifier - Real Batch 03
Project ID: 9
```

Ifham pass:

```text
tasks = 200 / 200
submitted annotations = 200
annotator = IF
Batch 02 not touched
```

Ifham Batch 03 category summary:

```text
SECTOR_SPECIFIC          179
IMPORT_EXPORT              7
LABOUR_LAW                11
BUSINESS_REGISTRATION      1
PRODUCT_STANDARD           2
SME relevant              16
SME not relevant         184
```

Ilham pass:

```text
tasks = 200 / 200
submitted annotations = 400
annotators shown = IF + TI
database check = exactly 2 annotations per task
Ifham = 200
Ilham = 200
```

Important decision:

```text
No intentionally wrong annotations were added to the real batch because that would corrupt the research data.
```

Final Batch 03 export state:

```text
tasks = 200
total_annotations = 400
annotation_count_distribution = Counter({2: 200})
users = {'1': 200, '4': 200}
```

Final export:

```text
C:\Reasearch\xyz\research\data\labeling\batch_03_annotations_full.json
```

---

## 8. Export Location Error

A validation script failed because it expected:

```text
research\data\labeling\batch_02_annotations_full.json
research\data\labeling\batch_03_annotations_full.json
```

Error:

```text
FileNotFoundError: [Errno 2] No such file or directory:
'research\\data\\labeling\\batch_02_annotations_full.json'
```

Discovery:

```powershell
Get-ChildItem -Path .\research\data\labeling -Filter *.json
Get-ChildItem -Path .\research\data -Filter *.json
```

Files initially found in `research\data`:

```text
batch_02_annotations_full.json        874797
batch_03_annotations_full.json        865311
calibration_export_ifham.json          49528
calibration_export_ilham_retest.json   48120
calibration_export_ilham.json          48010
calibration_export_reezma_retest.json  49750
calibration_export_reezma.json         49108
```

Fix:

- Move/regenerate annotation exports into `research\data\labeling`.
- Re-run validation.

Final validation command:

```powershell
cd C:\Reasearch\xyz

@'
import json
from pathlib import Path
from collections import Counter

files = [
    Path(r"research\data\labeling\batch_02_annotations_full.json"),
    Path(r"research\data\labeling\batch_03_annotations_full.json"),
]

for p in files:
    data = json.loads(p.read_text(encoding="utf-8"))
    ann_counts = [len(t.get("annotations", [])) for t in data]
    users = Counter()
    for task in data:
        for ann in task.get("annotations", []):
            users[str(ann.get("completed_by"))] += 1

    print("\n", p)
    print("tasks:", len(data))
    print("total_annotations:", sum(ann_counts))
    print("annotation_count_distribution:", Counter(ann_counts))
    print("users:", dict(users))
'@ | python
```

Final output:

```text
batch_02:
  tasks = 200
  total_annotations = 400
  annotation_count_distribution = Counter({2: 200})
  users = {'1': 200, '3': 200}

batch_03:
  tasks = 200
  total_annotations = 400
  annotation_count_distribution = Counter({2: 200})
  users = {'1': 200, '4': 200}
```

---

## 9. IAA Reducer Implementation

Script:

```text
C:\Reasearch\xyz\scripts\resolve_iaa.py
```

Purpose:

- Read full Label Studio JSON exports.
- Parse two annotations per task.
- Calculate IAA.
- Write disagreements.
- Resolve to one gold row per regulation.

Inputs:

```text
batch_02_annotations_full.json
batch_03_annotations_full.json
batch_04_annotations_full.json
batch_05_annotations_full.json
batch_06_annotations_full.json
batch_07_annotations_full.json
```

Outputs:

```text
C:\Reasearch\xyz\research\data\labeling\gold_standard.csv
C:\Reasearch\xyz\research\data\labeling\iaa_report.json
C:\Reasearch\xyz\research\data\labeling\iaa_report_summary.csv
C:\Reasearch\xyz\research\data\labeling\disagreements.csv
```

Parsed row contract:

```text
batch_id
regulation_id
regulation_key
gazette_number
classification_chunk
annotator_id
change_category
affected_sectors
is_sme_relevant
confidence
annotator_notes
```

Resolution rule:

```text
agreeing rows = accepted automatically
disagreements = manual_resolutions.csv if available
fallback = lead annotator user ID 1
```

---

## 10. First Batch 02-03 Gold Run

Result:

```text
tasks              = 400
annotations        = 800
gold rows          = 400
unique IDs         = 400
blank categories   = 0
blank relevance    = 0
invalid sectors    = 0
disagreement rows  = 11
```

IAA:

```text
overall category kappa    = 0.873725
overall sector mean kappa = 0.927599
SME relevance kappa       = 0.861111
batch_02 category kappa   = 0.750872
batch_03 category kappa   = 1.000000
```

Conclusion:

- 389 rows accepted automatically.
- 11 rows listed in `disagreements.csv`.
- Ifham/user 1 was used as provisional resolver until manual review.

---

## 11. XLSX And Manual Review Files

Created/used review files:

```text
C:\Reasearch\xyz\research\data\labeling\disagreements_provisional.csv
C:\Reasearch\xyz\research\data\labeling\disagreements_updated.xlsx
C:\Reasearch\xyz\research\data\labeling\gold_standard_provisional.csv
C:\Reasearch\xyz\research\data\labeling\manual_resolutions.csv
C:\Reasearch\xyz\research\data\labeling\manual_resolutions.xlsx
```

Temporary inspection files:

```text
disagreements.xlsx.inspect.ndjson
gold_standard.xlsx.inspect.ndjson
iaa_report.xlsx.inspect.ndjson
```

Purpose:

- Make disagreements reviewable in Excel.
- Record explicit resolver choices.
- Avoid hidden fallback decisions.

---

## 12. Batch 04 Generation

Script changed:

```text
C:\Reasearch\xyz\scripts\sample_for_labeling.py
```

Added CLI options:

```text
--minority-targeted
--gold-standard
--target-per-domain
--target-domains
--overwrite
```

Target domains:

```text
EPF_ETF_CHANGE
PENALTY_ENFORCEMENT
TAX_RATE_CHANGE
PRODUCT_STANDARD
BUSINESS_REGISTRATION
IMPORT_EXPORT
```

Outputs:

```text
C:\Reasearch\xyz\research\data\labeling\batch_04.csv
C:\Reasearch\xyz\research\data\labeling\batch_04_provenance.json
```

Validation:

```text
rows = 200
unique regulation_ids = 200
blank classification chunks = 0
overlap with batch_01/02/03 = 0
minority_targeted rows = 75
coverage_topup rows = 125
target signals visible in chunks = 75/75
```

Target selection:

```text
TAX_RATE_CHANGE          32
IMPORT_EXPORT            27
PENALTY_ENFORCEMENT       6
EPF_ETF_CHANGE            4
BUSINESS_REGISTRATION     3
PRODUCT_STANDARD          3
```

Export:

```text
C:\Reasearch\xyz\research\data\labeling\batch_04_annotations_full.json
```

IAA through Batch 04:

```text
inputs              = 3
tasks               = 600
annotations         = 1200
category kappa      = 0.867530
mean sector kappa   = 0.854008
SME relevance kappa = 0.690265
disagreement rows   = 37
gold rows           = 600
```

---

## 13. Batch 05 And V1 Gold

Project:

```text
M1 Gazette Classifier - Batch 05
```

User state correction:

```text
User first said Ifham was logged in.
User then corrected that Reezma was logged in.
Annotation continued according to the actual logged-in user.
```

Export:

```text
C:\Reasearch\xyz\research\data\labeling\batch_05_annotations_full.json
```

Accepted Batch 02-05 command:

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

Important intermediate 800-row result:

```text
tasks               = 800
annotations         = 1600
category kappa      = 0.882411
mean sector kappa   = 0.874081
SME relevance kappa = 0.725899
disagreement rows   = 37
gold rows           = 800
```

Final corrected v1 result after fixing temporary extra annotation:

```text
tasks               = 800
annotations         = 1600
category kappa      = 0.871534
mean sector kappa   = 0.863776
SME relevance kappa = 0.723518
disagreement rows   = 40
gold rows           = 800
```

Validation:

```text
rows = 800
unique_ids = 800
batch_02 = 200
batch_03 = 200
batch_04 = 200
batch_05 = 200
```

V1 category distribution:

```text
BUSINESS_REGISTRATION      5
IMPORT_EXPORT             32
LABOUR_LAW                27
PENALTY_ENFORCEMENT        5
PRODUCT_STANDARD           4
SECTOR_SPECIFIC          671
TAX_RATE_CHANGE           56
EPF_ETF_CHANGE             0
```

Frozen v1 files:

```text
C:\Reasearch\xyz\research\data\labeling\gold_standard_v1_800.csv
C:\Reasearch\xyz\research\data\labeling\iaa_report_v1_800.json
C:\Reasearch\xyz\research\data\labeling\iaa_report_summary_v1_800.csv
```

Important warning:

```text
Diagnostic reducer runs with fewer batches overwrite gold_standard.csv and reports.
The accepted v1 state is the 4-input Batch 02-05 run.
```

---

## 14. V1 Training Preparation

Split command:

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml

uv run python -m m1.model.data `
  --in ..\research\data\labeling\gold_standard_v1_800.csv `
  --out datasets\m1_regulations `
  --by key
```

Reason:

```text
gold_standard_v1_800.csv had no reliable gazette_published_date
therefore --by key was used instead of a true temporal split
```

Output:

```text
train = 560
val   = 120
test  = 120
```

Baseline command:

```powershell
uv run python -m m1.model.baselines `
  --data datasets\m1_regulations `
  --report ..\storage\models\m1\baselines_v1
```

V1 baseline:

```json
{
  "tfidf_logreg": {
    "test_macro_f1": 0.49803921568627446
  },
  "tfidf_linsvc": {
    "test_macro_f1": 0.6167449139280126
  }
}
```

---

## 15. Local CPU LoRA Smoke

CUDA check:

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml

uv run --extra training python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"
```

Output:

```text
False
CPU only
```

Smoke split creation:

```powershell
@'
import pandas as pd
from pathlib import Path

src = Path("datasets/m1_regulations")
out = Path("datasets/m1_regulations_smoke")
out.mkdir(parents=True, exist_ok=True)

for name, n in [("train", 16), ("val", 8), ("test", 8)]:
    df = pd.read_parquet(src / f"{name}.parquet")
    sample = df.sample(n=min(n, len(df)), random_state=42)
    sample.to_parquet(out / f"{name}.parquet", index=False)
    print(name, len(sample), "->", out / f"{name}.parquet")
'@ | uv run --extra research python -
```

Smoke output:

```text
train 16 -> datasets\m1_regulations_smoke\train.parquet
val 8 -> datasets\m1_regulations_smoke\val.parquet
test 8 -> datasets\m1_regulations_smoke\test.parquet
```

Training command:

```powershell
uv run --extra training --extra research python -m m1.model.train_xlmr `
  --data datasets\m1_regulations_smoke `
  --seeds 42 `
  --base xlm-roberta-base `
  --lora-r 8 `
  --epochs 1 `
  --out ..\storage\models\m1\xlmr_lora_smoke
```

Output:

```text
seed 42 epoch 1: val macro-F1=0.1111
3-seed mean test macro-F1 = 0.0000 (BELOW 0.92)
```

Registry:

```text
C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model_registry.json
C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model.pt
```

Conclusion:

```text
CPU smoke proves the training loop and artifact writing.
CPU smoke is not model quality evidence.
Full LoRA needs GPU.
```

---

## 16. Kaggle Setup Issues

Kaggle was selected as the best free GPU option after local CPU-only limitation.

Kaggle GPU UI issue:

```text
Accelerator options were greyed out.
Likely causes: account verification, quota, or disabled GPU access.
```

Dataset mount error:

```python
import os
print(os.listdir("/kaggle/input/m1-training-v1"))
```

Error:

```text
FileNotFoundError: [Errno 2] No such file or directory: '/kaggle/input/m1-training-v1'
```

Fix:

```python
import os
print(os.listdir("/kaggle/input"))
```

Actual source path later used:

```text
/kaggle/input/datasets/ifhammohamed1/m1-training-v1/enigmatrix-ml
```

Dependency warning after install:

```text
pip dependency resolver warning
numpy 1.26.4 conflicts with some Kaggle preinstalled packages requiring numpy >= 2.0
pandas version conflicts with google-colab package
```

Interpretation:

```text
These were Kaggle environment warnings, not direct blockers for M1 training.
Restarting the notebook/session after dependency changes is safer.
```

Notebook syntax mistake:

```text
numpy 1.26.4
```

Error:

```text
SyntaxError: invalid syntax
```

Correct version check:

```python
import numpy as np
print(np.__version__)
```

---

## 17. Kaggle LoRA Errors And Fixes

TorchAO/PEFT error:

```text
ImportError: Found an incompatible version of torchao.
Found version 0.10.0, but only versions above 0.16.0 are supported
```

Cause:

```text
Kaggle had incompatible torchao installed.
PEFT failed while injecting LoRA adapters.
```

Fix:

```text
Remove incompatible torchao or install compatible torchao.
Restart Kaggle session after package changes.
```

Missing split error:

```text
FileNotFoundError: [Errno 2] No such file or directory: 'datasets/m1_regulations/train.parquet'
```

Cause:

```text
The expected split folder was not present in the Kaggle working directory.
```

Fix:

```text
Copy the uploaded enigmatrix-ml folder from /kaggle/input to /kaggle/working,
or regenerate the train/val/test parquet splits before training.
```

Argparse duplicate error after trainer patch:

```text
argparse.ArgumentError: argument --lr-head: conflicting option string: --lr-head
```

Cause:

```text
--lr-head was registered twice in argparse.
```

Fix:

```text
Remove duplicate add_argument line.
Run python -m py_compile m1/model/train_xlmr.py.
No output from py_compile means syntax check passed.
```

Training warnings:

```text
FutureWarning: torch.cuda.amp.GradScaler(args...) is deprecated
FutureWarning: torch.cuda.amp.autocast(args...) is deprecated
UserWarning: lr_scheduler.step() called before optimizer.step()
```

Interpretation:

```text
Warnings did not stop training.
Scheduler order should be fixed later.
Warnings were not the main reason for low macro-F1.
```

---

## 18. Kaggle V1 LoRA Runs

First poor diagnostic:

```text
seed 42 epoch 1: val macro-F1=0.0028
test macro-F1 = 0.0081
```

Eight-epoch majority-class-collapse run:

```text
epoch 1 val macro-F1 = 0.0159
epoch 2 val macro-F1 = 0.0630
epoch 3 val macro-F1 = 0.1523
epoch 4 val macro-F1 = 0.1540
epoch 5 val macro-F1 = 0.1548
epoch 6 val macro-F1 = 0.1548
epoch 7 val macro-F1 = 0.1548
epoch 8 val macro-F1 = 0.1548
test macro-F1 = 0.1556
gate_pass = false
```

Stratified split created:

```text
train = 558
val   = 121
test  = 121
```

Stratified split category counts:

```text
train:
SECTOR_SPECIFIC 469
TAX_RATE_CHANGE 40
IMPORT_EXPORT 22
LABOUR_LAW 19
BUSINESS_REGISTRATION 3
PENALTY_ENFORCEMENT 3
PRODUCT_STANDARD 2

val:
SECTOR_SPECIFIC 101
TAX_RATE_CHANGE 8
IMPORT_EXPORT 5
LABOUR_LAW 4
PENALTY_ENFORCEMENT 1
PRODUCT_STANDARD 1
BUSINESS_REGISTRATION 1

test:
SECTOR_SPECIFIC 101
TAX_RATE_CHANGE 8
IMPORT_EXPORT 5
LABOUR_LAW 4
PENALTY_ENFORCEMENT 1
PRODUCT_STANDARD 1
BUSINESS_REGISTRATION 1
```

Stratified baseline:

```json
{
  "tfidf_logreg": {
    "test_macro_f1": 0.7710866910866911
  },
  "tfidf_linsvc": {
    "test_macro_f1": 0.7893650793650793
  }
}
```

Fixed LoRA run:

```bash
python -m m1.model.train_xlmr \
  --data datasets/m1_regulations_stratified \
  --seeds 42 \
  --base xlm-roberta-base \
  --lora-r 16 \
  --epochs 8 \
  --fp16 \
  --lr-head 5e-4 \
  --lr-lora 2e-4 \
  --sector-loss-weight 0.2 \
  --out /kaggle/working/storage/models/m1/xlmr_lora_v1_fixed_seed42
```

Fixed LoRA result:

```text
best val macro-F1 = 0.266328
test macro-F1     = 0.487084
gate_pass         = false
```

Category-only extended LoRA:

```bash
python -m m1.model.train_xlmr \
  --data datasets/m1_regulations_stratified \
  --seeds 42 \
  --base xlm-roberta-base \
  --lora-r 16 \
  --epochs 16 \
  --fp16 \
  --lr-head 1e-3 \
  --lr-lora 3e-4 \
  --sector-loss-weight 0.0 \
  --out /kaggle/working/storage/models/m1/xlmr_lora_v1_catonly_seed42_e16
```

Important mistake corrected:

```text
The user first read xlmr_lora_v1_fixed_seed42/model_registry.json.
Correct registry was xlmr_lora_v1_catonly_seed42_e16/model_registry.json.
```

Category-only result:

```json
{
  "val_macro_f1_mean": 0.4032849175706318,
  "test_macro_f1_mean": 0.6414707319391846,
  "gate_pass": false,
  "lr_head": 0.001,
  "lr_lora": 0.0003,
  "epochs": 16,
  "sector_loss_weight": 0.0
}
```

Evaluation command:

```bash
python -m m1.model.eval \
  --model /kaggle/working/storage/models/m1/xlmr_lora_v1_catonly_seed42_e16 \
  --test datasets/m1_regulations_stratified/test.parquet \
  --report /kaggle/working/storage/models/m1/eval_catonly_seed42_e16 \
  --base xlm-roberta-base
```

Evaluation:

```text
overall macro-F1 = 0.6415
slice cliff      = 27.89pp
gate_pass        = false
```

Decision:

```text
Do not promote LoRA v1.
Do not export ONNX.
Do not tune first.
Collect rare-domain data.
```

---

## 19. Kaggle Result Zip Local Storage

Kaggle zip included:

```text
baselines_v1
baselines_v1_stratified
xlmr_lora_v1_fixed_seed42
xlmr_lora_v1_catonly_seed42_e16
xlmr_lora_gpu_smoke
eval_catonly_seed42_e16
xlmr_lora_v1_seed42_diag
eval_seed42_diag
```

Local placement:

```powershell
cd C:\Reasearch\xyz

New-Item -ItemType Directory -Force storage\models\m1

Copy-Item "$env:USERPROFILE\Downloads\m1_training_kaggle_results_v1.zip" `
  "C:\Reasearch\xyz\storage\models\m1\m1_training_kaggle_results_v1.zip" `
  -Force

Expand-Archive `
  -Path "C:\Reasearch\xyz\storage\models\m1\m1_training_kaggle_results_v1.zip" `
  -DestinationPath "C:\Reasearch\xyz\storage\models\m1\kaggle_v1" `
  -Force
```

Verification paths:

```text
C:\Reasearch\xyz\storage\models\m1\kaggle_v1\kaggle\working\storage\models\m1\baselines_v1_stratified\baselines.json
C:\Reasearch\xyz\storage\models\m1\kaggle_v1\kaggle\working\storage\models\m1\xlmr_lora_v1_catonly_seed42_e16\model_registry.json
C:\Reasearch\xyz\storage\models\m1\kaggle_v1\kaggle\working\storage\models\m1\eval_catonly_seed42_e16\metrics.json
```

Confirmed:

```text
v1 stratified LinearSVC macro-F1 = 0.7893650793650793
best v1 LoRA macro-F1           = 0.6414707319391846
best v1 LoRA gate_pass          = false
```

---

## 20. Rare-Domain Top-Up Decision

Target rare classes after v1:

```text
EPF_ETF_CHANGE          0 -> 30-50
PRODUCT_STANDARD        4 -> 30-50
BUSINESS_REGISTRATION   5 -> 30-50
PENALTY_ENFORCEMENT     5 -> 30-50
IMPORT_EXPORT          32 -> 50+
```

Reason:

```text
The v1 training failure was mainly a data coverage problem.
The model could not learn classes with zero or very low examples.
```

---

## 21. Batch 06 Rare-Domain Top-Up

Script:

```text
C:\Reasearch\xyz\scripts\collect_rare_domain_topup.py
```

Command:

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml

uv run --extra research python ..\scripts\collect_rare_domain_topup.py `
  --batch 6 `
  --years 2010-2026 `
  --batch-size 200 `
  --target-per-domain 50 `
  --overwrite
```

Outputs:

```text
C:\Reasearch\xyz\research\data\labeling\batch_06.csv
C:\Reasearch\xyz\research\data\labeling\batch_06.xlsx
C:\Reasearch\xyz\research\data\labeling\batch_06_provenance.json
C:\Reasearch\xyz\research\data\labeling\rare_domain_candidate_pool_v2.csv
C:\Reasearch\xyz\research\data\labeling\rare_domain_candidate_pool_v2.xlsx
```

Sources:

```text
official documents.gov.lk extraordinary Gazette listings 2010-2026
C:\Reasearch\xyz\data\golden\structured_v1_batches_1_2_3_4_5_6_7_8_official.xlsx
```

Selected counts:

```text
BUSINESS_REGISTRATION    45
EPF_ETF_CHANGE           22
IMPORT_EXPORT            72
PENALTY_ENFORCEMENT      15
PRODUCT_STANDARD         46
```

Validation:

```text
rows = 200
unique regulation_id = 200
blank chunks = 0
blank category hints = 0
overlap gold IDs = 0
overlap gold gazettes = 0
```

Label Studio:

```text
M1 Gazette Classifier - RareDomain Top-Up Batch 06
Project ID = 14
```

Annotation:

```text
Reezma pass completed
Ifham pass completed
assisted/direct annotation used
```

Export:

```text
C:\Reasearch\xyz\research\data\labeling\batch_06_annotations_full.json
```

---

## 22. V2 Gold After Batch 06

Command:

```powershell
cd C:\Reasearch\xyz

uv run python scripts\resolve_iaa.py `
  --input research\data\labeling\batch_02_annotations_full.json `
  --input research\data\labeling\batch_03_annotations_full.json `
  --input research\data\labeling\batch_04_annotations_full.json `
  --input research\data\labeling\batch_05_annotations_full.json `
  --input research\data\labeling\batch_06_annotations_full.json `
  --lead-annotator 1 `
  --resolutions research\data\labeling\manual_resolutions.csv
```

Result:

```text
tasks = 1000
annotations = 2000
category kappa = 0.932094
mean sector kappa = 0.954130
SME relevance kappa = 0.889124
disagreement rows = 43
gold rows = 1000
```

Frozen v2 files:

```text
C:\Reasearch\xyz\research\data\labeling\gold_standard_v2_1000.csv
C:\Reasearch\xyz\research\data\labeling\iaa_report_v2_1000.json
C:\Reasearch\xyz\research\data\labeling\iaa_report_summary_v2_1000.csv
C:\Reasearch\xyz\research\data\labeling\disagreements_v2_1000.csv
```

V2 category counts:

```text
SECTOR_SPECIFIC          691
IMPORT_EXPORT            112
TAX_RATE_CHANGE           56
LABOUR_LAW                51
PRODUCT_STANDARD          36
BUSINESS_REGISTRATION     32
PENALTY_ENFORCEMENT       16
EPF_ETF_CHANGE             6
```

V2 `--by key` baseline was poor:

```text
train = 700
val   = 150
test  = 150
tfidf_logreg macro-F1 = 0.2942
tfidf_linsvc macro-F1 = 0.2103
```

Interpretation:

```text
The v2 key split was not suitable for current evidence.
Need PDF-backed top-up and stratified split.
```

---

## 23. Batch 07 PDF Rare Top-Up

Script:

```text
C:\Reasearch\xyz\scripts\collect_pdf_rare_topup.py
```

Outputs:

```text
C:\Reasearch\xyz\research\data\labeling\batch_07.csv
C:\Reasearch\xyz\research\data\labeling\batch_07.xlsx
C:\Reasearch\xyz\research\data\labeling\batch_07_provenance.json
C:\Reasearch\xyz\research\data\labeling\rare_domain_pdf_candidate_pool_v3.csv
C:\Reasearch\xyz\research\data\labeling\rare_domain_pdf_candidate_pool_v3.xlsx
C:\Reasearch\xyz\raw\rare_domain_pdf_cache
```

Sources:

```text
official documents.gov.lk listings
official English Gazette PDFs
PyMuPDF PDF text extraction
```

Candidate counts:

```text
PENALTY_ENFORCEMENT     60
TAX_RATE_CHANGE         20
LABOUR_LAW              20
EPF_ETF_CHANGE          12
PRODUCT_STANDARD        12
BUSINESS_REGISTRATION    4
```

Validation:

```text
batch rows = 128
candidate pool rows = 128
unique IDs = 128
blank chunks = 0
blank PDF URLs = 0
PDF text missing = 0
overlap gold gazettes = 0
overlap gold IDs = 0
```

Label Studio:

```text
M1 Gazette Classifier - PDF Rare Top-Up Batch 07
Project ID = 15
```

Annotation:

```text
Ifham pass completed
Reezma pass completed
assisted/direct annotation used
password from chat intentionally not recorded
```

Backups:

```text
C:\Reasearch\xyz\mydata\label_studio.before_batch07_ifham_20260731_003035.sqlite3.bak
C:\Reasearch\xyz\mydata\label_studio.before_batch07_reezma_20260731_003231.sqlite3.bak
```

Export:

```text
C:\Reasearch\xyz\research\data\labeling\batch_07_annotations_full.json
```

Export validation:

```text
tasks = 128
annotations = 256
annotation_count_distribution = 2 per task
users = {'1': 128, '3': 128}
```

Batch 07 labels across both annotators:

```text
LABOUR_LAW              46
EPF_ETF_CHANGE          10
SECTOR_SPECIFIC          8
TAX_RATE_CHANGE         52
PENALTY_ENFORCEMENT    100
PRODUCT_STANDARD        32
BUSINESS_REGISTRATION    8
```

SME relevance:

```text
FALSE = 60
TRUE  = 196
```

---

## 24. V3 Gold After Batch 07

Command:

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

Result:

```text
inputs              = 6
tasks               = 1128
annotations         = 2256
category kappa      = 0.947215
mean sector kappa   = 0.965567
SME relevance kappa = 0.914637
disagreement rows   = 44
gold rows           = 1128
```

Batch 07 IAA:

```text
category_kappa = 0.989611
category_agreement = 0.992188
mean_sector_kappa = 0.992982
sector_set_agreement = 0.992188
SME relevance kappa = 0.977977
SME relevance agreement = 0.992188
disagreement fields: change_category 1, affected_sectors 1, is_sme_relevant 1
```

Frozen v3 files:

```text
C:\Reasearch\xyz\research\data\labeling\gold_standard_v3_1128.csv
C:\Reasearch\xyz\research\data\labeling\iaa_report_v3_1128.json
C:\Reasearch\xyz\research\data\labeling\iaa_report_summary_v3_1128.csv
C:\Reasearch\xyz\research\data\labeling\disagreements_v3_1128.csv
```

V3 distribution:

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

By batch:

```text
batch_02 = 200
batch_03 = 200
batch_04 = 200
batch_05 = 200
batch_06 = 200
batch_07 = 128
```

Disagreements by batch:

```text
batch_02 = 11
batch_03 = 14
batch_04 = 12
batch_05 = 3
batch_06 = 3
batch_07 = 1
```

---

## 25. V3 Stratified Split And Baseline

Split:

```text
C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations_v3_1128_stratified
```

Sizes:

```text
train = 790
val = 169
test = 169
```

Train:

```text
BUSINESS_REGISTRATION 26
EPF_ETF_CHANGE 7
IMPORT_EXPORT 78
LABOUR_LAW 52
PENALTY_ENFORCEMENT 46
PRODUCT_STANDARD 36
SECTOR_SPECIFIC 487
TAX_RATE_CHANGE 58
```

Validation and test each:

```text
BUSINESS_REGISTRATION 5
EPF_ETF_CHANGE 2
IMPORT_EXPORT 17
LABOUR_LAW 11
PENALTY_ENFORCEMENT 10
PRODUCT_STANDARD 8
SECTOR_SPECIFIC 104
TAX_RATE_CHANGE 12
```

Baseline command:

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml

uv run python -m m1.model.baselines `
  --data datasets\m1_regulations_v3_1128_stratified `
  --report ..\storage\models\m1\baselines_v3_1128_stratified
```

Result:

```text
tfidf_logreg macro-F1 = 0.8626517496950933
tfidf_linsvc macro-F1 = 0.9080119023133729
```

Per-class LinearSVC:

```text
BUSINESS_REGISTRATION F1 = 1.000000 support = 5
EPF_ETF_CHANGE        F1 = 0.800000 support = 2
IMPORT_EXPORT         F1 = 0.909091 support = 17
LABOUR_LAW            F1 = 0.900000 support = 11
PENALTY_ENFORCEMENT   F1 = 0.761905 support = 10
PRODUCT_STANDARD      F1 = 0.941176 support = 8
SECTOR_SPECIFIC       F1 = 0.951923 support = 104
TAX_RATE_CHANGE       F1 = 1.000000 support = 12
```

Diagnostic files:

```text
C:\Reasearch\xyz\storage\models\m1\baselines_v3_1128_stratified\baselines.json
C:\Reasearch\xyz\storage\models\m1\baselines_v3_1128_stratified\linsvc_per_class_report.csv
C:\Reasearch\xyz\storage\models\m1\baselines_v3_1128_stratified\linsvc_test_predictions.csv
C:\Reasearch\xyz\storage\models\m1\baselines_v3_1128_stratified\linsvc_confusion_matrix.csv
```

Decision:

```text
V3 LinearSVC is current strongest baseline.
Macro-F1 0.908012 is close to 0.92 but not a pass.
Do not promote LoRA yet.
Do not export ONNX yet.
Focus next on EPF_ETF_CHANGE scarcity and PENALTY_ENFORCEMENT errors.
```

---

## 26. Documentation Created And Updated

Created:

```text
E:\Obsidian\sme\Final-Report\05_M1_RARE_DOMAIN_TOPUP_AND_V3_BASELINE.md
E:\Obsidian\sme\Final-Report\06_M1_FULL_WORK_SESSION_CHRONOLOGY_2026-07-31.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\PROGRAM_READINESS\M1_RARE_DOMAIN_TOPUP_AND_V3_BASELINE_MANUAL.md
```

Updated:

```text
E:\Obsidian\sme\Final-Report\00_FINAL_REPORT_CONTEXT_INDEX.md
E:\Obsidian\sme\Final-Report\03_M1_EVIDENCE_EVALUATION_AND_COMMANDS.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\00_INDEX.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\05_M1_Model_Architecture.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\06_M1_Training_Evaluation.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\03_FEATURE_CHECKLIST.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\07_SETUP_AND_USER_MANUAL.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\PROGRAM_READINESS\M1_PROGRAM_READINESS_MASTER_INDEX.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\PROGRAM_READINESS\M1_PHASE3_ANNOTATION_AND_ACTIVE_LEARNING_USER_MANUAL.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\PROGRAM_READINESS\M1_NON_CODING_TASKS_AND_GOLIVE_READINESS_PLAN.md
```

Purpose of documentation update:

- Preserve v1 as historical evidence.
- Mark v3 as current active training dataset.
- Record Batch 06/07 assisted/direct annotation caveat.
- Record all local and Kaggle evidence paths.
- Prevent future confusion between diagnostic reducer runs and accepted gold state.

---

## 27. Current Correct State

```text
Current dataset version      = v3
Gold rows                    = 1128
Annotations                  = 2256
Annotation batches           = batch_02 through batch_07
Current category kappa       = 0.947215
Current mean sector kappa    = 0.965567
Current SME relevance kappa  = 0.914637
Current best baseline        = TF-IDF LinearSVC
Current best baseline F1     = 0.908012
Final target                 = macro-F1 >= 0.92
Current model promotion      = no
Current ONNX export          = no
```

---

## 28. Correct Next Work Order

1. Review `C:\Reasearch\xyz\research\data\labeling\disagreements_v3_1128.csv`.
2. Confirm any needed entries in `manual_resolutions.csv`.
3. Manually audit Batch 06 and Batch 07 if strict independent human annotation evidence is required.
4. Review:

```text
C:\Reasearch\xyz\storage\models\m1\baselines_v3_1128_stratified\linsvc_confusion_matrix.csv
C:\Reasearch\xyz\storage\models\m1\baselines_v3_1128_stratified\linsvc_test_predictions.csv
```

5. Focus error analysis on `PENALTY_ENFORCEMENT`.
6. Search for more official `EPF_ETF_CHANGE` examples if possible.
7. Keep TF-IDF LinearSVC as the current strongest baseline.
8. Retry XLM-R LoRA only if the plan can beat 0.9080 macro-F1 on the same v3 split.
9. Promote/export only after:

```text
macro-F1 >= 0.92
slice cliff <= 8 percentage points
rare-domain behavior explainable
```

10. Continue separate final-report work for:

```text
extraction accuracy measurement
dataset snapshot evidence
summarization from classified regulation text
NLLB Sinhala/Tamil translation backfill
translation review queue
screenshots for Label Studio, Kaggle, dashboard, measurement, and summaries
```

---

## 29. Copy-Ready Final Paragraph

Module 1 progressed from annotator calibration and Label Studio production labeling into a versioned gold dataset and model-preparation pipeline. Ifham passed calibration strongly, while Reezma and Ilham passed after retest. Batches 02-05 produced the first 800-row v1 gold dataset with 1600 annotations, category kappa 0.871534, mean sector kappa 0.863776, and SME relevance kappa 0.723518. V1 model preparation showed that TF-IDF LinearSVC outperformed early XLM-R LoRA diagnostics; the best Kaggle LoRA result reached 0.641471 macro-F1 and failed the 0.92 target, so no LoRA checkpoint was promoted.

The main weakness was rare-domain scarcity, especially `EPF_ETF_CHANGE=0`. Batch 06 and Batch 07 were then created as rare-domain top-up batches using official Gazette sources and PDF-backed extraction. After resolving Batches 02-07, the current v3 gold dataset contains 1128 rows and 2256 annotations, with category kappa 0.947215, mean sector kappa 0.965567, and SME relevance kappa 0.914637. The v3 stratified split contains 790 train, 169 validation, and 169 test rows. The current best classifier baseline is TF-IDF LinearSVC with macro-F1 0.908012, close to but still below the 0.92 success target. Remaining work is to audit Batch 06/07 if stricter annotation evidence is needed, improve `EPF_ETF_CHANGE` coverage and `PENALTY_ENFORCEMENT` errors, and only then retry or promote XLM-R LoRA if it beats the v3 baseline.
