# M1 Full Chat Execution Log And Results

> Created: 2026-07-31 23:21:34 +05:30  
> Repo root: `C:\Reasearch\xyz`  
> ML package root: `C:\Reasearch\xyz\enigmatrix-ml`  
> Obsidian vault root: `E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap`  
> Purpose: preserve the complete working sequence from Label Studio setup, calibration, IAA, gold dataset freezing, split/baseline preparation, LoRA smoke testing, errors, results, and vault-documentation synchronization.

## 0. Source And Redaction Note

This file records the implementation conversation and terminal results that were shared in the Codex chat. It is written as an audit trail: what was attempted, what failed, what passed, what files were created, and what each result means.

One item is intentionally redacted: plaintext Label Studio user passwords were mentioned in the chat. They are not stored in this permanent research note. The accounts are recorded only as annotator/user identities where relevant.

## 1. Main Local Paths Used

| Purpose | Path |
|---|---|
| Main repo | `C:\Reasearch\xyz` |
| ML package | `C:\Reasearch\xyz\enigmatrix-ml` |
| Label Studio local data | `C:\Reasearch\xyz\mydata` |
| Labeling data | `C:\Reasearch\xyz\research\data\labeling` |
| Frozen v1 gold | `C:\Reasearch\xyz\research\data\labeling\gold_standard_v1_800.csv` |
| Main model split | `C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations` |
| Tiny smoke split | `C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations_smoke` |
| Baseline report | `C:\Reasearch\xyz\storage\models\m1\baselines_v1\baselines.json` |
| CPU smoke output | `C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke` |
| SME vault | `E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap` |

## 2. High-Level Result

The annotation and first model-preparation gate moved from incomplete to a usable v1 training-preparation state.

Completed:

1. Label Studio was configured and run locally.
2. Annotator calibration was scored.
3. Failed/conditional annotators were retested.
4. Batches 02, 03, 04, and 05 were exported from Label Studio as full JSON.
5. IAA was computed.
6. Manual disagreement resolution was applied.
7. `gold_standard.csv` reached 800 unique rows.
8. v1 gold files were frozen.
9. Main train/validation/test parquet splits were created.
10. TF-IDF baselines were run.
11. CUDA check showed this laptop is CPU-only.
12. Full-split CPU LoRA attempt did not produce a registry.
13. A tiny smoke split was created.
14. CPU LoRA smoke succeeded as an engineering check.
15. SME vault documentation was updated and synchronized.

Still not complete:

1. Full LoRA training on a CUDA/GPU machine.
2. Real model evaluation and slice analysis.
3. ONNX export and deployment activation.
4. Rare-domain coverage fix or limitation statement.
5. Trilingual production summarization pipeline.
6. Final extraction-accuracy evidence run using real ground truth.

## 3. Label Studio Local Startup

### 3.1 Command Used

```powershell
cd C:\Reasearch\xyz

$env:LABEL_STUDIO_BASE_DATA_DIR = "C:\Reasearch\xyz\mydata"
$env:LOCAL_FILES_SERVING_ENABLED = "true"
$env:LOCAL_FILES_DOCUMENT_ROOT = "C:\Reasearch\xyz"

label-studio start --host 127.0.0.1 --port 8080
```

### 3.2 Output/Error Observed

```text
=> Database and media directory: C:\Reasearch\xyz\mydata
=> Static URL is set to: /static/
! HOST variable found in environment, but it must start with http:// or https://, ignore it: 127.0.0.1
=> Database and media directory: C:\Reasearch\xyz\mydata
=> Static URL is set to: /static/
Read environment variables from: C:\Reasearch\xyz\mydata\.env
get 'SECRET_KEY' casted as '<class 'str'>' with default ''
```

### 3.3 Interpretation

Label Studio was reading from `C:\Reasearch\xyz\mydata`. The important issue was the missing/empty `SECRET_KEY` in the environment or `.env`. The `HOST` message was a warning about an environment variable format, not the main blocker.

### 3.4 Corrected Startup Pattern

```powershell
cd C:\Reasearch\xyz

$env:LABEL_STUDIO_BASE_DATA_DIR = "C:\Reasearch\xyz\mydata"
$env:LOCAL_FILES_SERVING_ENABLED = "true"
$env:LOCAL_FILES_DOCUMENT_ROOT = "C:\Reasearch\xyz"
$env:SECRET_KEY = "local-dev-change-this-secret"

label-studio start --host 127.0.0.1 --port 8080
```

## 4. Annotator Calibration Scoring

### 4.1 Initial Calibration Commands

```powershell
cd C:\Reasearch\xyz

uv run python scripts\score_calibration.py --export research\data\calibration_export_ifham.json --reference research\data\calibration_set_v1.csv --name ifham

uv run python scripts\score_calibration.py --export research\data\calibration_export_reezma.json --reference research\data\calibration_set_v1.csv --name reezma

uv run python scripts\score_calibration.py --export research\data\calibration_export_ilham.json --reference research\data\calibration_set_v1.csv --name ilham
```

### 4.2 Initial Calibration Results

```text
Annotator          : ifham
Scorable docs      : 19
κ (change_category): 0.875   [gate ≥ 0.8]
κ (sectors, mean3) : 0.541
  - grocery_retail : 0.565
  - food_service   : 0.232
  - general_retail : 0.826
Exact agreement    : 89.5%
Verdict            : PASS
```

```text
Annotator          : reezma
Scorable docs      : 19
κ (change_category): 0.752   [gate ≥ 0.8]
κ (sectors, mean3) : 0.115
  - grocery_retail : 0.174
  - food_service   : 0.012
  - general_retail : 0.159
Exact agreement    : 78.9%
Verdict            : CONDITIONAL
```

```text
Annotator          : ilham
Scorable docs      : 19
κ (change_category): 0.506   [gate ≥ 0.8]
κ (sectors, mean3) : 0.002
  - grocery_retail : -0.061
  - food_service   : 0.095
  - general_retail : -0.027
Exact agreement    : 57.9%
Verdict            : FAIL
```

### 4.3 Interpretation

Ifham was qualified immediately. Reezma needed review/retest because category kappa was below 0.8 and sector agreement was weak. Ilham needed retest because category kappa and sector agreement were not acceptable.

The main feedback theme was that many land-title, election, public-security, and general administrative notices are not SME-relevant for the study unless they directly affect the target SME sectors.

## 5. Calibration Retests

### 5.1 Retest Commands And Results

```powershell
uv run python scripts\score_calibration.py --export research\data\calibration_export_ilham_retest.json --reference research\data\calibration_set_v1.csv --name ilham_retest
```

```text
Annotator          : ilham_retest
Scorable docs      : 19
κ (change_category): 0.875   [gate ≥ 0.8]
κ (sectors, mean3) : 0.541
  - grocery_retail : 0.565
  - food_service   : 0.232
  - general_retail : 0.826
Exact agreement    : 89.5%
Verdict            : PASS
```

```powershell
uv run python scripts\score_calibration.py --export research\data\calibration_export_reezma_retest.json --reference research\data\calibration_set_v1.csv --name reezma_retest
```

```text
Annotator          : reezma_retest
Scorable docs      : 19
κ (change_category): 0.875   [gate ≥ 0.8]
κ (sectors, mean3) : 0.541
  - grocery_retail : 0.565
  - food_service   : 0.232
  - general_retail : 0.826
Exact agreement    : 89.5%
Verdict            : PASS
```

### 5.2 Final Calibration Status

| Annotator | Final status | Evidence |
|---|---|---|
| Ifham | PASS | Initial calibration passed |
| Reezma | PASS after retest | `calibration_export_reezma_retest.json` |
| Ilham | PASS after retest | `calibration_export_ilham_retest.json` |

## 6. Batch 02 And Batch 03 Full Annotation Export Validation

### 6.1 Files Observed

```text
batch_01_provenance.json
batch_02_annotations_full.json
batch_02_provenance.json
batch_03_annotations_full.json
batch_03_provenance.json
```

### 6.2 Validation Script Used

```powershell
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

### 6.3 Validation Result

```text
research\data\labeling\batch_02_annotations_full.json
tasks: 200
total_annotations: 400
annotation_count_distribution: Counter({2: 200})
users: {'1': 200, '3': 200}

research\data\labeling\batch_03_annotations_full.json
tasks: 200
total_annotations: 400
annotation_count_distribution: Counter({2: 200})
users: {'1': 200, '4': 200}
```

### 6.4 Interpretation

Batches 02 and 03 were structurally valid for IAA/reduction because each task had exactly two annotations.

## 7. Reducer Creation And First Gold Standard Outputs

### 7.1 Reducer Outputs Created/Updated

```text
C:\Reasearch\xyz\scripts\resolve_iaa.py
C:\Reasearch\xyz\research\data\labeling\gold_standard.csv
C:\Reasearch\xyz\research\data\labeling\disagreements.csv
C:\Reasearch\xyz\research\data\labeling\iaa_report.json
C:\Reasearch\xyz\research\data\labeling\iaa_report_summary.csv
```

Excel outputs also existed:

```text
gold_standard.xlsx
disagreements.xlsx
iaa_report.xlsx
```

### 7.2 Initial Reducer Validation

```text
gold rows          = 400
unique IDs         = 400
blank categories   = 0
blank relevance    = 0
invalid sectors    = 0
disagreement rows  = 25
```

### 7.3 Initial IAA

```text
overall category κ     = 0.72793
overall sector mean κ  = 0.859065
SME relevance κ        = 0.699856

batch_02 category κ    = 0.750872
batch_03 category κ    = 0.707877
```

### 7.4 Interpretation

The first `gold_standard.csv` was structurally correct but provisional because category kappa was below the 0.75 target and 25 disagreement rows needed adjudication.

Important rule established:

Manual review improves final gold labels, but it does not change historical IAA. Kappa measures annotator agreement before adjudication.

## 8. Manual Disagreement Review

### 8.1 User Question

The user asked how to manually review the 25 disagreements and later asked Codex to explain/fix the workflow from the assistant side.

### 8.2 Adjudication Rule

The 25 disagreement review was treated as adjudication, not re-annotation of all 400 rows. Only rows where two annotators disagreed were manually reviewed.

### 8.3 Manual Resolution Command

```powershell
cd C:\Reasearch\xyz

uv run python scripts\resolve_iaa.py `
  --input research\data\labeling\batch_02_annotations_full.json `
  --input research\data\labeling\batch_03_annotations_full.json `
  --lead-annotator 1 `
  --resolutions research\data\labeling\manual_resolutions.csv
```

### 8.4 Result

```text
IAA + resolution complete
  inputs             : 2
  tasks              : 400
  annotations        : 800
  category kappa     : 0.72793
  mean sector kappa  : 0.859065
  SME relevance kappa: 0.699856
  disagreement rows  : 25
  gold rows          : 400
  wrote              : research\data\labeling\gold_standard.csv
  wrote              : research\data\labeling\iaa_report.json
  wrote              : research\data\labeling\iaa_report_summary.csv
  wrote              : research\data\labeling\disagreements.csv
```

### 8.5 Interpretation

The final gold labels were improved by manual adjudication. The kappa did not change because kappa is historical pre-resolution agreement.

## 9. Batch 04 Active-Learning Direction

### 9.1 Reason For Batch 04

The target before LoRA was:

```text
800 resolved rows
at least 50 examples per domain if possible
IAA >= 0.75
```

After Batches 02 and 03, the row count was only 400 and category kappa was below target. Batch 04 was needed to grow the dataset and improve agreement.

### 9.2 Targeted Domains For Batch 04

```text
EPF_ETF_CHANGE
PENALTY_ENFORCEMENT
TAX_RATE_CHANGE
PRODUCT_STANDARD
BUSINESS_REGISTRATION
IMPORT_EXPORT
```

### 9.3 Key Guidance

Do not run LoRA at this point. Build/modify the sampler for minority-domain targeting and annotate another batch with two annotators.

## 10. Batch 04 IAA Result

### 10.1 Command

```powershell
cd C:\Reasearch\xyz

uv run python scripts\resolve_iaa.py `
  --input research\data\labeling\batch_02_annotations_full.json `
  --input research\data\labeling\batch_03_annotations_full.json `
  --input research\data\labeling\batch_04_annotations_full.json `
  --lead-annotator 1 `
  --resolutions research\data\labeling\manual_resolutions.csv
```

### 10.2 Result

```text
IAA + resolution complete
  inputs             : 3
  tasks              : 600
  annotations        : 1200
  category kappa     : 0.86753
  mean sector kappa  : 0.854008
  SME relevance kappa: 0.690265
  disagreement rows  : 37
  gold rows          : 600
  wrote              : research\data\labeling\gold_standard.csv
  wrote              : research\data\labeling\iaa_report.json
  wrote              : research\data\labeling\iaa_report_summary.csv
  wrote              : research\data\labeling\disagreements.csv
```

### 10.3 Interpretation

Batch 04 improved category kappa above the 0.75 gate. It still produced fallback/manual-review rows, and rare-domain coverage still needed attention.

## 11. Batch 05 Completion And Final 800-Row Gold Gate

### 11.1 Final 4-Batch Reducer Command

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

### 11.2 Final 4-Batch Result

```text
IAA + resolution complete
  inputs             : 4
  tasks              : 800
  annotations        : 1601
  category kappa     : 0.871523
  mean sector kappa  : 0.863776
  SME relevance kappa: 0.723518
  disagreement rows  : 40
  gold rows          : 800
  wrote              : research\data\labeling\gold_standard.csv
  wrote              : research\data\labeling\iaa_report.json
  wrote              : research\data\labeling\iaa_report_summary.csv
  wrote              : research\data\labeling\disagreements.csv
```

### 11.3 Gold Row Validation Command

```powershell
$gold = Import-Csv research\data\labeling\gold_standard.csv

"rows=$($gold.Count)"
"unique_ids=$(($gold.regulation_id | Select-Object -Unique).Count)"
$gold | Group-Object batch_id | Select-Object Name,Count
$gold | Group-Object change_category | Select-Object Name,Count
```

### 11.4 Gold Row Validation Result

```text
rows=800
unique_ids=800

batch_02 = 200
batch_03 = 200
batch_04 = 200
batch_05 = 200

BUSINESS_REGISTRATION     5
IMPORT_EXPORT            32
LABOUR_LAW               27
PENALTY_ENFORCEMENT       5
PRODUCT_STANDARD          4
SECTOR_SPECIFIC         671
TAX_RATE_CHANGE          56
```

### 11.5 Important Later Correction

The final accepted state was later documented as exactly 1600 annotations after the temporary Batch 05 duplicate/1601 annotation issue was fixed. The accepted documentation state is:

```text
tasks              = 800
annotations        = 1600
gold rows          = 800
manual resolutions = 40
category kappa     = 0.871534
mean sector kappa  = 0.863776
SME relevance kappa= 0.723518
```

### 11.6 Interpretation

The row-count and category-IAA gates were met. The dataset became usable as v1 training-preparation evidence. Rare-domain coverage remained weak and had to be documented as a limitation or fixed with more targeted collection.

## 12. Rare-Domain Limitation

### 12.1 Final Known Gold Distribution

```text
SECTOR_SPECIFIC          671
TAX_RATE_CHANGE           56
IMPORT_EXPORT             32
LABOUR_LAW                27
BUSINESS_REGISTRATION      5
PENALTY_ENFORCEMENT        5
PRODUCT_STANDARD           4
EPF_ETF_CHANGE             0
```

### 12.2 Meaning

The model cannot learn `EPF_ETF_CHANGE` from v1 because there are zero examples. Strong rare-domain claims are not defensible from this dataset. The thesis must either:

1. collect extra EPF/product/business/penalty/import-export examples, or
2. train now and explicitly document rare-domain scarcity as a limitation.

## 13. Dataset Freeze

### 13.1 Freeze Commands

```powershell
cd C:\Reasearch\xyz

Copy-Item research\data\labeling\gold_standard.csv research\data\labeling\gold_standard_v1_800.csv
Copy-Item research\data\labeling\iaa_report.json research\data\labeling\iaa_report_v1_800.json
Copy-Item research\data\labeling\iaa_report_summary.csv research\data\labeling\iaa_report_summary_v1_800.csv
```

### 13.2 Freeze Verification

```powershell
cd C:\Reasearch\xyz

Get-Item `
  research\data\labeling\gold_standard_v1_800.csv, `
  research\data\labeling\iaa_report_v1_800.json, `
  research\data\labeling\iaa_report_summary_v1_800.csv
```

### 13.3 Freeze Files

```text
C:\Reasearch\xyz\research\data\labeling\gold_standard_v1_800.csv
Length: 1411899
LastWriteTime: 07/30/2026 11:59 AM

C:\Reasearch\xyz\research\data\labeling\iaa_report_v1_800.json
Length: 4208
LastWriteTime: 07/30/2026 11:59 AM

C:\Reasearch\xyz\research\data\labeling\iaa_report_summary_v1_800.csv
Length: 4259
LastWriteTime: 07/30/2026 11:59 AM
```

### 13.4 Interpretation

This created a stable v1 dataset snapshot. All future split, baseline, and model results should point back to this frozen file rather than a moving `gold_standard.csv`.

## 14. First Split Attempt And Missing Parquet Dependency

### 14.1 Command

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml

uv run python -m m1.model.data `
  --in ..\research\data\labeling\gold_standard_v1_800.csv `
  --out datasets\m1_regulations `
  --by key
```

### 14.2 Error

```text
ImportError: Unable to find a usable engine; tried using: 'pyarrow', 'fastparquet'.
A suitable version of pyarrow or fastparquet is required for parquet support.
Missing optional dependency 'pyarrow'. pyarrow is required for parquet support.
Missing optional dependency 'fastparquet'. fastparquet is required for parquet support.
```

### 14.3 Interpretation

The split code worked up to the point of writing parquet, but the environment lacked a parquet engine. The required fix was to install/use an extra that includes `pyarrow` or add `pyarrow` directly.

## 15. Dependency/Environment Lock Error

### 15.1 Error

```text
Resolved 294 packages in 3ms
Prepared 66 packages in 2m 29s
error: failed to remove file `C:\Reasearch\xyz\.venv\Lib\site-packages\../../Scripts/celery.exe`: The process cannot access the file because it is being used by another process. (os error 32)
```

### 15.2 Interpretation

`uv sync` or package installation was blocked because `celery.exe` was still running from the virtual environment. The correct action was to stop the running Celery/Label Studio/process that held the executable, then rerun the dependency command.

## 16. Successful Dataset Split

### 16.1 Command

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml

uv run --extra research python -m m1.model.data `
  --in ..\research\data\labeling\gold_standard_v1_800.csv `
  --out datasets\m1_regulations `
  --by key
```

### 16.2 Output

```text
train: 560 rows -> datasets\m1_regulations\train.parquet
val: 120 rows -> datasets\m1_regulations\val.parquet
test: 120 rows -> datasets\m1_regulations\test.parquet
```

### 16.3 Warning

```text
RuntimeWarning: 'm1.model.data' found in sys.modules after import of package 'm1.model', but prior to execution of 'm1.model.data'; this may result in unpredictable behaviour
```

### 16.4 Interpretation

The warning did not block output. The split succeeded. `--by key` was used because the current gold file did not contain reliable `gazette_published_date`.

## 17. Main Split Distribution

### 17.1 Command

```powershell
Get-ChildItem datasets\m1_regulations

@'
import pandas as pd
from pathlib import Path

d = Path("datasets/m1_regulations")
for name in ["train", "val", "test"]:
    df = pd.read_parquet(d / f"{name}.parquet")
    print("\n", name, len(df))
    print(df["category"].value_counts())
'@ | uv run --extra research python -
```

### 17.2 Output

```text
train 560
SECTOR_SPECIFIC          462
TAX_RATE_CHANGE           53
IMPORT_EXPORT             20
LABOUR_LAW                18
BUSINESS_REGISTRATION      4
PENALTY_ENFORCEMENT        3

val 120
SECTOR_SPECIFIC        104
LABOUR_LAW               6
IMPORT_EXPORT            5
TAX_RATE_CHANGE          3
PRODUCT_STANDARD         1
PENALTY_ENFORCEMENT      1

test 120
SECTOR_SPECIFIC          105
IMPORT_EXPORT              7
LABOUR_LAW                 3
PRODUCT_STANDARD           3
PENALTY_ENFORCEMENT        1
BUSINESS_REGISTRATION      1
```

### 17.3 Interpretation

The split is deterministic but not strong for rare-domain evaluation:

```text
EPF_ETF_CHANGE = 0 everywhere
PRODUCT_STANDARD = 0 in train
TAX_RATE_CHANGE = 0 in test
rare class counts are too low for strong per-class claims
```

## 18. TF-IDF Baselines

### 18.1 Command

```powershell
uv run --extra training --extra research python -m m1.model.baselines `
  --data datasets\m1_regulations `
  --report ..\storage\models\m1\baselines_v1
```

### 18.2 Output

```text
tfidf_logreg: macro-F1=0.4980
tfidf_linsvc: macro-F1=0.6167
```

### 18.3 Baseline JSON

```powershell
Get-Content ..\storage\models\m1\baselines_v1\baselines.json
```

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

### 18.4 Interpretation

LinearSVC is the current non-neural floor to beat. Any XLM-R/LoRA result must clearly exceed this baseline to justify the extra complexity.

## 19. CUDA/GPU Check

### 19.1 Command

```powershell
uv run --extra training python -c "import torch; print('cuda=', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"
```

### 19.2 Output

```text
cuda= False
CPU only
```

### 19.3 Interpretation

This laptop cannot run the final full LoRA training properly. It can run small smoke tests, but full training should be done on a CUDA/GPU machine.

## 20. First CPU LoRA Attempt On Full Split

### 20.1 Command

```powershell
uv run --extra training --extra research python -m m1.model.train_xlmr `
  --data datasets\m1_regulations `
  --seeds 42 `
  --base xlm-roberta-base `
  --lora-r 8 `
  --epochs 1 `
  --out ..\storage\models\m1\xlmr_lora_smoke
```

### 20.2 Output

```text
Xet Storage is enabled for this repo, but the 'hf_xet' package is not installed.
Falling back to regular HTTP download.
model.safetensors: 100% ... 1.12G/1.12G
FutureWarning: `torch.cuda.amp.GradScaler(args...)` is deprecated.
FutureWarning: `torch.cuda.amp.autocast(args...)` is deprecated.
```

### 20.3 Registry Check

```powershell
Get-Content ..\storage\models\m1\xlmr_lora_smoke\model_registry.json
```

### 20.4 Error

```text
Get-Content: Cannot find path 'C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model_registry.json' because it does not exist.
```

### 20.5 Interpretation

This full-split CPU attempt is not a valid model run and not even a valid smoke artifact because no `model_registry.json` was written. It only proved that the base model downloaded and the process reached training initialization.

The `hf_xet` message is a performance warning only. It is not the cause of failure.

The AMP warnings are harmless deprecation warnings and do not block training.

## 21. Tiny Smoke Split Creation

### 21.1 Command

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml

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

### 21.2 Output

```text
train 16 -> datasets\m1_regulations_smoke\train.parquet
val 8 -> datasets\m1_regulations_smoke\val.parquet
test 8 -> datasets\m1_regulations_smoke\test.parquet
```

### 21.3 Smoke Split Distribution

Verified later from parquet files:

```text
train 16
SECTOR_SPECIFIC    11
TAX_RATE_CHANGE     2
LABOUR_LAW          2
IMPORT_EXPORT       1

val 8
SECTOR_SPECIFIC     7
PRODUCT_STANDARD    1

test 8
SECTOR_SPECIFIC     8
```

### 21.4 Interpretation

This split is intentionally tiny. It is only for checking that the training code can run end to end and write artifacts. It is not for model performance.

## 22. Successful CPU LoRA Smoke Test

### 22.1 Command

```powershell
uv run --extra training --extra research python -m m1.model.train_xlmr `
  --data datasets\m1_regulations_smoke `
  --seeds 42 `
  --base xlm-roberta-base `
  --lora-r 8 `
  --epochs 1 `
  --out ..\storage\models\m1\xlmr_lora_smoke
```

### 22.2 Output

```text
FutureWarning: `torch.cuda.amp.GradScaler(args...)` is deprecated.
FutureWarning: `torch.cuda.amp.autocast(args...)` is deprecated.
seed 42 epoch 1: val macro-F1=0.1111
3-seed mean test macro-F1 = 0.0000 (BELOW 0.92)
```

### 22.3 Output Files

```powershell
Get-ChildItem ..\storage\models\m1\xlmr_lora_smoke

Get-Content ..\storage\models\m1\xlmr_lora_smoke\model_registry.json
```

```text
C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model_registry.json
Length: 799
LastWriteTime: 07/30/2026 12:57 PM

C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model.pt
Length: 1113501831
LastWriteTime: 07/30/2026 12:57 PM
```

### 22.4 Registry Content

```json
{
  "base_model": "xlm-roberta-base",
  "seeds": [42],
  "val_macro_f1_mean": 0.1111111111111111,
  "test_macro_f1_mean": 0.0,
  "test_macro_f1_std": 0.0,
  "per_seed_test_macro_f1": [0.0],
  "gate_pass": false,
  "config": {
    "base_model": "xlm-roberta-base",
    "num_categories": 8,
    "num_sectors": 3,
    "max_length": 512,
    "lora_r": 8,
    "lora_alpha": 32,
    "lora_dropout": 0.1,
    "lora_targets": ["query", "value"],
    "lr_head": 2e-05,
    "lr_lora": 0.0001,
    "weight_decay": 0.01,
    "warmup_ratio": 0.1,
    "epochs": 1,
    "batch_size": 16,
    "early_stop_patience": 3,
    "fp16": false,
    "sector_loss_weight": 1.0,
    "seeds": [42]
  },
  "created_at": "2026-07-30T12:57:25"
}
```

### 22.5 Interpretation

The smoke test passed as an engineering check:

```text
model loads
LoRA initializes
training loop runs
registry is written
checkpoint is written
```

The smoke test failed as a research/model result:

```text
tiny data only
one seed only
one epoch only
test split contains only SECTOR_SPECIFIC
gate_pass=false
test macro-F1=0.0
```

Do not export or promote this model.

## 23. What Codex Updated In The SME Vault

### 23.1 Main Sync After 800-Row Gold And Training Prep

The following vault files were updated to reflect:

```text
800-row v1 gold dataset
rare-domain limitation
deterministic --by key split
TF-IDF baseline metrics
CPU LoRA smoke result
GPU requirement for full LoRA
```

Updated files included:

```text
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\00_INDEX.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\05_M1_Model_Architecture.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\06_M1_Training_Evaluation.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\09_M1_Annotation_Guidelines.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\12_M1_Monitoring_Maintenance.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\13_M1_Folder_Structure_and_Implementation_Flow.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\15_M1_Folder_Reference.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\16_M1_Development_Roadmap.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\01_MASTER_PROJECT_OVERVIEW.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\02_MEMBER1_MODULE1_REPORT.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\03_FEATURE_CHECKLIST.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\07_SETUP_AND_USER_MANUAL.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\PROGRAM_READINESS\M1_PROGRAM_READINESS_MASTER_INDEX.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\PROGRAM_READINESS\M1_PHASE3_ANNOTATION_AND_ACTIVE_LEARNING_USER_MANUAL.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\PROGRAM_READINESS\M1_NON_CODING_TASKS_AND_GOLIVE_READINESS_PLAN.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\PHASE3_ANNOTATION_CLASSIFICATION\2026-07-30_M1_PHASE3_LABELING_IAA_HANDOFF.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\PHASE3_ANNOTATION_CLASSIFICATION\PHASE3_GAP_CLOSURE_PLAN.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\PHASE3_ANNOTATION_CLASSIFICATION\PHASE3_ANNOTATION_CLASSIFICATION_ANALYSIS.md
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\PHASE3_ANNOTATION_CLASSIFICATION\classifier_model_training\CLASSIFIER_MODEL_TRAINING_READINESS_PLAN.md
```

### 23.2 Second Sync After Latest Smoke Transcript

The latest transcript clarified that:

```text
full-split CPU attempt wrote no registry
tiny smoke split wrote registry and checkpoint
```

Codex updated:

```text
M1_PHASE3_ANNOTATION_AND_ACTIVE_LEARNING_USER_MANUAL.md
M1_PROGRAM_READINESS_MASTER_INDEX.md
06_M1_Training_Evaluation.md
03_FEATURE_CHECKLIST.md
CLASSIFIER_MODEL_TRAINING_READINESS_PLAN.md
```

## 24. Important Files Created In Repo

### 24.1 Labeling/IAA Files

```text
C:\Reasearch\xyz\research\data\labeling\batch_02_annotations_full.json
C:\Reasearch\xyz\research\data\labeling\batch_03_annotations_full.json
C:\Reasearch\xyz\research\data\labeling\batch_04_annotations_full.json
C:\Reasearch\xyz\research\data\labeling\batch_05_annotations_full.json
C:\Reasearch\xyz\research\data\labeling\manual_resolutions.csv
C:\Reasearch\xyz\research\data\labeling\disagreements.csv
C:\Reasearch\xyz\research\data\labeling\gold_standard.csv
C:\Reasearch\xyz\research\data\labeling\iaa_report.json
C:\Reasearch\xyz\research\data\labeling\iaa_report_summary.csv
```

### 24.2 Frozen v1 Files

```text
C:\Reasearch\xyz\research\data\labeling\gold_standard_v1_800.csv
C:\Reasearch\xyz\research\data\labeling\iaa_report_v1_800.json
C:\Reasearch\xyz\research\data\labeling\iaa_report_summary_v1_800.csv
```

### 24.3 Split Files

```text
C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations\train.parquet
C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations\val.parquet
C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations\test.parquet

C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations_smoke\train.parquet
C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations_smoke\val.parquet
C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations_smoke\test.parquet
```

### 24.4 Model/Baseline Files

```text
C:\Reasearch\xyz\storage\models\m1\baselines_v1\baselines.json
C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model_registry.json
C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model.pt
```

## 25. Errors And Their Meaning

| Error/message | Where it happened | Meaning | Resolution/status |
|---|---|---|---|
| `SECRET_KEY` default empty | Label Studio startup | Local Label Studio env missing secret | Set `$env:SECRET_KEY` before startup |
| `HOST variable ... must start with http:// or https://` | Label Studio startup | Host env var format warning | Not the main blocker |
| Missing `pyarrow` / `fastparquet` | `m1.model.data` parquet export | Pandas could not write parquet | Use `--extra research` or install parquet dependency |
| `celery.exe` locked | `uv sync` | Running process held venv executable | Stop Celery/Label Studio process and rerun |
| `hf_xet` not installed | XLM-R download | Hugging Face performance fallback warning | Safe to ignore; optional install only |
| AMP `FutureWarning` | LoRA training | PyTorch API deprecation warning | Safe to ignore for now |
| No `model_registry.json` after full split CPU attempt | Full 560/120/120 CPU attempt | No valid artifact produced | Do not count this as smoke success |
| `gate_pass=false` in smoke registry | Tiny smoke run | Expected because tiny split/1 epoch cannot meet model gate | Keep only as engineering proof |

## 26. Current Accepted Research State

```text
Annotation gate        = passed
Gold rows              = 800
Unique IDs             = 800
Final category kappa   = about 0.8715
Final sector mean kappa= 0.863776
SME relevance kappa    = 0.723518
Manual resolutions     = 40
Main split             = created
Baselines              = completed
CPU smoke              = completed as engineering check
Full LoRA              = not completed
ONNX export            = not completed
Production classifier  = not active
```

## 27. Correct Next Work Order

### 27.1 If Training Now With v1 Limitation

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml

uv run --extra training python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"
```

Only continue if CUDA is available.

```powershell
uv run --extra training --extra research python -m m1.model.train_xlmr `
  --data datasets\m1_regulations `
  --seeds 42 1 2 `
  --base xlm-roberta-base `
  --lora-r 16 `
  --epochs 8 `
  --fp16 `
  --out ..\storage\models\m1\xlmr_lora_v1
```

Then:

```powershell
uv run --extra training --extra research python -m m1.model.eval `
  --data datasets\m1_regulations `
  --model ..\storage\models\m1\xlmr_lora_v1
```

Only export ONNX if gates pass.

### 27.2 If Fixing Rare Domains First

Collect another targeted top-up batch for:

```text
EPF_ETF_CHANGE
PRODUCT_STANDARD
BUSINESS_REGISTRATION
PENALTY_ENFORCEMENT
IMPORT_EXPORT
```

Then:

```text
export Label Studio JSON
rerun resolve_iaa.py with all accepted batches
freeze v2 gold dataset
rebuild split
rerun baselines
rerun full GPU LoRA
```

## 28. Thesis Limitation Text To Preserve

Use wording like this if training proceeds with v1:

```text
The accepted v1 gold set contains 800 dual-annotated and adjudicated gazette records with category kappa above the annotation gate. However, the corpus remains strongly imbalanced toward SECTOR_SPECIFIC notices. EPF_ETF_CHANGE has no examples in v1, and several rare regulatory domains have fewer than 10 examples. Therefore, the v1 classifier evaluation should be interpreted as evidence for the dominant and moderately represented classes, not as a strong per-domain robustness claim for rare categories.
```

## 29. Final Interpretation

The project is in a valid post-annotation, pre-final-training state.

The important distinction is:

```text
TF-IDF baselines = real measured baselines on the v1 split
CPU LoRA smoke   = engineering proof only
Full LoRA model  = not yet trained
ONNX model       = not yet exported
Production model = not yet active
```

The next decisive technical step is not another CPU smoke. It is either rare-domain top-up or full GPU training.
