---
created: 2026-07-30
module: M1
phase: PHASE3_ANNOTATION_CLASSIFICATION
status: active
source_repo: "C:\\Reasearch\\xyz"
vault_target: "E:\\Obsidian\\sme\\02-Research-Modules\\1 Module-1-Awareness-Gap\\final\\works\\PHASE3_ANNOTATION_CLASSIFICATION"
tags:
  - m1
  - phase3
  - annotation
  - iaa
  - gold-standard
  - active-learning
---

# M1 Phase 3 Labeling, IAA, And Gold-Standard Handoff

This note is the cleaned handoff from the Codex chat/process around M1 Gazette Classifier annotation work on 2026-07-29 to 2026-07-30.

It records:

- what was done
- what files were used
- what outputs were produced
- what the current quality numbers mean
- what still needs review
- the exact next commands

Primary repo:

```text
C:\Reasearch\xyz
```

Primary research data folder:

```text
C:\Reasearch\xyz\research\data\labeling
```

Obsidian vault:

```text
E:\Obsidian\sme
```

Correct Obsidian final-work group:

```text
E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\PHASE3_ANNOTATION_CLASSIFICATION
```

## 1. Short Current Status

The project has completed four resolved annotation batches after calibration:

```text
batch_02 = 200 tasks, 400 annotations, 2 annotators per task
batch_03 = 200 tasks, 400 annotations, 2 annotators per task
batch_04 = 200 tasks, 400 annotations, 2 annotators per task
batch_05 = 200 tasks, 400 annotations, 2 annotators per task
```

The latest accepted IAA/resolution run over Batch 02, Batch 03, Batch 04, and Batch 05 produced:

```text
tasks               = 800
annotations         = 1600
paired tasks        = 800
gold rows           = 800
unique IDs          = 800
blank categories    = 0
blank SME relevance = 0
disagreement rows   = 40
resolution methods  = 760 auto_agree, 40 manual_review, 0 lead_annotator_fallback
```

IAA quality:

```text
overall category kappa      = 0.871534
overall category agreement  = 0.960000
overall sector mean kappa   = 0.863776
sector set agreement        = 0.952500
SME relevance kappa         = 0.723518
SME relevance agreement     = 0.955000
```

Interpretation:

- Category agreement passes the >= 0.75 production-labeling gate.
- Sector agreement is strong enough to continue.
- SME relevance agreement is the weak point, even though raw relevance agreement is high. Use this as annotator feedback.
- Current gold file is accepted and has already been frozen into the v1 split/baseline/smoke preparation flow.
- Rare-domain coverage is still the main validity limitation before making strong per-domain model claims.

Current file-state note:

```text
manual_resolutions.csv has been synchronized into gold_standard.csv, iaa_report.json, iaa_report_summary.csv, and disagreements.csv.
```

Meaning:

Batch 05 is now merged. The 3 new Batch 05 disagreement rows were manually resolved as non-SME-facing public/administrative notices.

Final reducer command used:

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

## 2. Calibration Work Completed

Calibration script:

```text
C:\Reasearch\xyz\scripts\score_calibration.py
```

Reference file:

```text
C:\Reasearch\xyz\research\data\calibration_set_v1.csv
```

Calibration exports used:

```text
C:\Reasearch\xyz\research\data\calibration_export_ifham.json
C:\Reasearch\xyz\research\data\calibration_export_reezma.json
C:\Reasearch\xyz\research\data\calibration_export_ilham.json
C:\Reasearch\xyz\research\data\calibration_export_reezma_retest.json
C:\Reasearch\xyz\research\data\calibration_export_ilham_retest.json
```

Calibration results recorded in chat:

```text
Ifham:
  scorable docs          = 19
  change_category kappa  = 0.875
  sector mean kappa      = 0.541
  exact agreement        = 89.5%
  verdict                = PASS

Reezma first attempt:
  scorable docs          = 19
  change_category kappa  = 0.752
  sector mean kappa      = 0.115
  exact agreement        = 78.9%
  verdict                = CONDITIONAL

Ilham first attempt:
  scorable docs          = 19
  change_category kappa  = 0.506
  sector mean kappa      = 0.002
  exact agreement        = 57.9%
  verdict                = FAIL

Ilham retest:
  scorable docs          = 19
  change_category kappa  = 0.875
  sector mean kappa      = 0.541
  exact agreement        = 89.5%
  verdict                = PASS

Reezma retest:
  scorable docs          = 19
  change_category kappa  = 0.875
  sector mean kappa      = 0.541
  exact agreement        = 89.5%
  verdict                = PASS
```

Calibration decision:

- Ifham passed strongly and is used as lead annotator/resolver ID `1`.
- Reezma passed after retest.
- Ilham passed after retest.
- All annotators were debriefed on sector definitions before real-batch annotation.

Debrief sector definitions:

```text
grocery_retail  = grocery shops, kade, mini marts, small supermarkets
food_service    = restaurants, cafes, bakeries, take-away food
general_retail  = textile, electronics, hardware, other retail shops
```

Important annotation rule:

Do not intentionally create wrong annotations in real Label Studio projects. If error-injection is needed for testing, create a separate test project/export so the research gold data is not corrupted.

## 3. Label Studio Runtime Setup

Start Label Studio from:

```powershell
cd C:\Reasearch\xyz

$env:LABEL_STUDIO_BASE_DATA_DIR = "C:\Reasearch\xyz\mydata"
$env:LOCAL_FILES_SERVING_ENABLED = "true"
$env:LOCAL_FILES_DOCUMENT_ROOT = "C:\Reasearch\xyz"

label-studio start --host 127.0.0.1 --port 8080
```

Local Label Studio data directory:

```text
C:\Reasearch\xyz\mydata
```

Local Label Studio SQLite database:

```text
C:\Reasearch\xyz\mydata\label_studio.sqlite3
```

Security note:

- Do not commit `mydata\.env`.
- Do not commit real Label Studio secret keys.
- Local uploads and local DB are operational artifacts, not clean research exports.

Known Label Studio user IDs:

```text
1 = Ifham
3 = Reezma
4 = Ilham
```

## 4. Label Studio Project History

Batch 02:

```text
Project name : M1 Gazette Classifier - Real Batch 02
Project ID   : 8
Export file  : C:\Reasearch\xyz\research\data\labeling\batch_02_annotations_full.json
Annotators   : user 1 Ifham, user 3 Reezma
```

Batch 03:

```text
Project name : M1 Gazette Classifier - Real Batch 03
Project ID   : 9
Export file  : C:\Reasearch\xyz\research\data\labeling\batch_03_annotations_full.json
Annotators   : user 1 Ifham, user 4 Ilham
```

Batch 04:

```text
Project name : M1 Gazette Classifier - A L Real Batch 04
Project ID   : 11
Export file  : C:\Reasearch\xyz\research\data\labeling\batch_04_annotations_full.json
Annotators   : user 1 Ifham, user 4 Ilham
```

Batch 05:

```text
Project name : M1 Gazette Classifier - Batch 05
Project ID   : 13
Export file  : C:\Reasearch\xyz\research\data\labeling\batch_05_annotations_full.json
Annotators   : user 1, user 3
Status       : exported, reduced, and manually adjudicated
```

Important Label Studio workflow:

- If an existing annotation opens as `Update`, that edits the selected annotator's existing result.
- To create the second annotator result, use `Create an annotation`.
- A blank `Submit` state confirms a new independent annotation.
- The UI should show both annotator initials after the second annotation is saved.

## 5. Batch Input And Output Files

Batch CSV/provenance files:

```text
C:\Reasearch\xyz\research\data\labeling\batch_01.csv
C:\Reasearch\xyz\research\data\labeling\batch_01_provenance.json
C:\Reasearch\xyz\research\data\labeling\batch_02.csv
C:\Reasearch\xyz\research\data\labeling\batch_02_provenance.json
C:\Reasearch\xyz\research\data\labeling\batch_03.csv
C:\Reasearch\xyz\research\data\labeling\batch_03_provenance.json
C:\Reasearch\xyz\research\data\labeling\batch_04.csv
C:\Reasearch\xyz\research\data\labeling\batch_04_provenance.json
C:\Reasearch\xyz\research\data\labeling\batch_05.csv
C:\Reasearch\xyz\research\data\labeling\batch_05_provenance.json
```

Annotation JSON exports:

```text
C:\Reasearch\xyz\research\data\labeling\batch_02_annotations_full.json
C:\Reasearch\xyz\research\data\labeling\batch_03_annotations_full.json
C:\Reasearch\xyz\research\data\labeling\batch_04_annotations_full.json
C:\Reasearch\xyz\research\data\labeling\batch_05_annotations_full.json
```

IAA/resolution outputs:

```text
C:\Reasearch\xyz\research\data\labeling\gold_standard.csv
C:\Reasearch\xyz\research\data\labeling\iaa_report.json
C:\Reasearch\xyz\research\data\labeling\iaa_report_summary.csv
C:\Reasearch\xyz\research\data\labeling\disagreements.csv
```

Manual-resolution files:

```text
C:\Reasearch\xyz\research\data\labeling\manual_resolutions.csv
C:\Reasearch\xyz\research\data\labeling\manual_resolutions.xlsx
C:\Reasearch\xyz\research\data\labeling\batch_04_manual_resolution_todo.csv
C:\Reasearch\xyz\research\data\labeling\batch_04_manual_resolution_todo.xlsx
```

## 6. Annotation Export Validation

Validation command:

```powershell
cd C:\Reasearch\xyz

@'
import json
from pathlib import Path
from collections import Counter

files = [
    Path(r"research\data\labeling\batch_02_annotations_full.json"),
    Path(r"research\data\labeling\batch_03_annotations_full.json"),
    Path(r"research\data\labeling\batch_04_annotations_full.json"),
    Path(r"research\data\labeling\batch_05_annotations_full.json"),
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

Current validated output:

```text
batch_02_annotations_full.json
  tasks                       = 200
  total_annotations           = 400
  annotation_count_distribution = {2: 200}
  users                       = {'1': 200, '3': 200}

batch_03_annotations_full.json
  tasks                       = 200
  total_annotations           = 400
  annotation_count_distribution = {2: 200}
  users                       = {'1': 200, '4': 200}

batch_04_annotations_full.json
  tasks                       = 200
  total_annotations           = 400
  annotation_count_distribution = {2: 200}
  users                       = {'1': 200, '4': 200}

batch_05_annotations_full.json
  tasks                       = 200
  total_annotations           = 400
  annotation_count_distribution = {2: 200}
  users                       = {'1': 200, '3': 200}
```

Conclusion:

All four real batches have exactly two annotations per task. No batch currently has a missing second pass.

## 7. Batch 04 Sampling Context

Batch 04 was generated with the minority-domain targeted sampler.

Script:

```text
C:\Reasearch\xyz\scripts\sample_for_labeling.py
```

Batch 04 files:

```text
C:\Reasearch\xyz\research\data\labeling\batch_04.csv
C:\Reasearch\xyz\research\data\labeling\batch_04_provenance.json
```

Batch 04 sampler outcome recorded in chat:

```text
rows                              = 200
unique regulation_ids             = 200
blank classification chunks       = 0
overlap with batch_01/02/03       = 0
minority_targeted rows            = 75
coverage_topup rows               = 125
target signals visible in chunks  = 75/75
```

Batch 04 target-selection distribution:

```text
TAX_RATE_CHANGE          = 32
IMPORT_EXPORT            = 27
PENALTY_ENFORCEMENT       = 6
EPF_ETF_CHANGE            = 4
BUSINESS_REGISTRATION     = 3
PRODUCT_STANDARD          = 3
```

Important limitation:

The remaining DB pool does not contain many true candidates for EPF, product standards, business registration, and penalty/enforcement. Batch 04 targeted all available candidates that matched signals, but annotators can still mark some rows as another category or not SME relevant.

## 8. IAA And Resolution Script

Resolver script:

```text
C:\Reasearch\xyz\scripts\resolve_iaa.py
```

Purpose:

- Parse raw Label Studio JSON exports.
- Flatten each annotation into comparable rows.
- Calculate inter-annotator agreement.
- Create disagreement rows.
- Resolve agreed rows automatically.
- Apply manual resolutions where available.
- Fall back to lead annotator `1` where no manual resolution is supplied.
- Export one training-ready gold row per regulation.

Required parsed annotation fields:

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

Latest command used:

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

Latest command output recorded:

```text
IAA + resolution complete
  inputs             : 4
  tasks              : 800
  annotations        : 1600
  category kappa     : 0.871534
  mean sector kappa  : 0.863776
  SME relevance kappa: 0.723518
  disagreement rows  : 40
  gold rows          : 800
  wrote              : research\data\labeling\gold_standard.csv
  wrote              : research\data\labeling\iaa_report.json
  wrote              : research\data\labeling\iaa_report_summary.csv
  wrote              : research\data\labeling\disagreements.csv
```

## 9. IAA Summary

Overall:

```text
tasks                   = 800
annotations             = 1600
paired tasks            = 800
category kappa          = 0.871534
category agreement      = 0.960000
mean sector kappa       = 0.863776
sector set agreement    = 0.952500
SME relevance kappa     = 0.723518
SME relevance agreement = 0.955000
disagreement rows       = 40
gold rows               = 800
```

Overall sector kappa:

```text
grocery_retail  = 0.784483
food_service    = 0.854939
general_retail  = 0.951906
```

By batch:

```text
batch_02:
  tasks                   = 200
  annotations             = 400
  category kappa          = 0.750872
  category agreement      = 0.950000
  mean sector kappa       = 0.872110
  sector set agreement    = 0.945000
  SME relevance kappa     = 0.745763
  SME relevance agreement = 0.955000
  disagreements           = 11

batch_03:
  tasks                   = 200
  annotations             = 400
  category kappa          = 0.707877
  category agreement      = 0.930000
  mean sector kappa       = 0.854148
  sector set agreement    = 0.930000
  SME relevance kappa     = 0.660194
  SME relevance agreement = 0.930000
  disagreements           = 14

batch_04:
  tasks                   = 200
  annotations             = 400
  category kappa          = 0.955506
  category agreement      = 0.975000
  mean sector kappa       = 0.845916
  sector set agreement    = 0.950000
  SME relevance kappa     = 0.669967
  SME relevance agreement = 0.940000
  disagreements           = 12

batch_05:
  tasks                   = 200
  annotations             = 400
  category kappa          = 0.883743
  category agreement      = 0.985000
  mean sector kappa       = 0.915566
  sector set agreement    = 0.985000
  SME relevance kappa     = 0.938575
  SME relevance agreement = 0.995000
  disagreements           = 3
```

Disagreement counts:

```text
batch_02 = 11
batch_03 = 14
batch_04 = 12
total    = 37
```

Field-level disagreement counts:

```text
change_category    = 29
affected_sectors   = 35
is_sme_relevant    = 35
```

Interpretation:

The dominant disagreement is not only category selection. The main review risk is the combination of sector relevance and SME relevance. The team should review the decision rule for "not SME relevant" carefully.

## 10. Gold Standard Current Shape

Current `gold_standard.csv` validation:

```text
rows              = 800
unique_ids        = 800
blank_categories  = 0
blank_relevance   = 0
```

Batch distribution:

```text
batch_02 = 200
batch_03 = 200
batch_04 = 200
batch_05 = 200
```

Category distribution:

```text
SECTOR_SPECIFIC        = 671
TAX_RATE_CHANGE        = 56
IMPORT_EXPORT          = 32
LABOUR_LAW             = 27
BUSINESS_REGISTRATION  = 5
PENALTY_ENFORCEMENT    = 5
PRODUCT_STANDARD       = 4
EPF_ETF_CHANGE         = 0
```

Interpretation:

- The dataset is heavily dominated by `SECTOR_SPECIFIC`.
- Minority classes are still small.
- The 800-row annotation gate is met.
- Split, baseline, and CPU smoke preparation are complete; run full GPU LoRA next, or collect another rare-domain top-up batch first if strong rare-domain model claims are required.

## 11. Manual Resolution Status

Current manual-resolution file:

```text
C:\Reasearch\xyz\research\data\labeling\manual_resolutions.csv
```

Current row count:

```text
manual_resolutions rows = 40
batch_02 rows           = 11
batch_03 rows           = 14
batch_04 rows           = 12
batch_05 rows           = 3
```

Current issue:

```text
All manual resolutions are synchronized into the current 800-row gold file.
No lead-annotator fallback rows remain.
```

Batch 04 note:

`GZT_2470_01` was reviewed as a Customs Ordinance rates-of-exchange notice and should stay documented as an adjudication example: broad customs exchange-rate notices can affect import/export duty valuation and may be SME relevant across all study sectors when imported goods are in scope.

## 12. SME Relevance Review Rule

Use `is_sme_relevant = True` only when the gazette notice directly changes obligations, permissions, costs, controls, standards, registration, taxes, import/export requirements, labour duties, penalties, or compliance risk for at least one of the study sectors:

```text
grocery_retail
food_service
general_retail
```

Usually `False` unless directly SME-facing:

```text
land title notices
election vacancy notices
public security or armed forces notices
individual labour disputes
public service appointments
company-specific Port City incentives
municipal governance inquiries
prison or police establishment notices
noisy/OCR-damaged notices with no visible SME obligation
```

Usually `True` when clearly broad or sector-facing:

```text
customs/import/export valuation or permit notices
VAT/excise/SCL/tax rate changes that affect shops
consumer affairs maximum retail price notices
Food Act/NMRA/SLSI product standards for goods sold by shops
trade licence or business registration obligations
labour/wages rules for retail/food-service workers
penalty/enforcement clauses tied to SME-facing compliance obligations
```

## 13. Immediate Next Commands

Step 1: validate the accepted gold file and reducer outputs.

```powershell
cd C:\Reasearch\xyz

$gold = Import-Csv research\data\labeling\gold_standard.csv

"rows=$($gold.Count)"
"unique_ids=$(($gold.regulation_id | Select-Object -Unique).Count)"
"blank_categories=$(($gold | Where-Object { [string]::IsNullOrWhiteSpace($_.change_category) }).Count)"
"blank_relevance=$(($gold | Where-Object { [string]::IsNullOrWhiteSpace($_.is_sme_relevant) }).Count)"

$gold | Group-Object batch_id | Select-Object Name,Count
$gold | Group-Object change_category | Select-Object Name,Count
$gold | Group-Object resolution_method | Select-Object Name,Count
```

Expected:

```text
rows             = 800
unique_ids       = 800
blank_categories = 0
blank_relevance  = 0
auto_agree        = 760
manual_review     = 40
fallback          = 0
```

Step 2: validate IAA summary.

```powershell
cd C:\Reasearch\xyz

Get-Content research\data\labeling\iaa_report_summary.csv -TotalCount 20
```

Expected headline:

```text
tasks                  = 800
annotations            = 1600
paired_tasks           = 800
category_kappa         = 0.871534
mean_sector_kappa      = 0.863776
sme_relevance_kappa    = 0.723518
disagreement_rows      = 40
gold_rows              = 800
```

Step 3: freeze/archive the accepted files before training.

```text
C:\Reasearch\xyz\research\data\labeling\gold_standard.csv
C:\Reasearch\xyz\research\data\labeling\iaa_report.json
C:\Reasearch\xyz\research\data\labeling\iaa_report_summary.csv
C:\Reasearch\xyz\research\data\labeling\disagreements.csv
C:\Reasearch\xyz\research\data\labeling\manual_resolutions.csv
```

Step 4: decide whether to train now or collect a rare-domain top-up batch.

Training can start if the thesis accepts this limitation:

```text
SECTOR_SPECIFIC dominates the gold set.
EPF_ETF_CHANGE is absent.
PRODUCT_STANDARD, BUSINESS_REGISTRATION, PENALTY_ENFORCEMENT, and IMPORT_EXPORT remain below 50/domain.
```

If the thesis needs stronger rare-domain performance claims, collect another targeted batch before final LoRA.

## 13.1 Training Prep, Baseline, And CPU Smoke Update

After the 800-row handoff, the accepted gold set was frozen and the first training-preparation pass was completed.

Frozen v1 files:

```text
C:\Reasearch\xyz\research\data\labeling\gold_standard_v1_800.csv
C:\Reasearch\xyz\research\data\labeling\iaa_report_v1_800.json
C:\Reasearch\xyz\research\data\labeling\iaa_report_summary_v1_800.csv
```

Main split:

```text
Command: uv run --extra research python -m m1.model.data --in ..\research\data\labeling\gold_standard_v1_800.csv --out datasets\m1_regulations --by key
train  : 560 rows -> C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations\train.parquet
val    : 120 rows -> C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations\val.parquet
test   : 120 rows -> C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations\test.parquet
```

Split limitation:

```text
This is deterministic by regulation key, not temporal.
It is not stratified enough for rare-domain performance claims.
EPF_ETF_CHANGE has 0 examples.
PRODUCT_STANDARD has 0 train examples.
TAX_RATE_CHANGE has 0 test examples.
```

Baselines:

```text
TF-IDF LogReg macro-F1    = 0.4980
TF-IDF LinearSVC macro-F1 = 0.6167
Report path              = C:\Reasearch\xyz\storage\models\m1\baselines_v1\baselines.json
```

Compute environment:

```text
cuda = False
CPU only
```

CPU smoke:

```text
Data path      = C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations_smoke
Output path    = C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke
Base model     = xlm-roberta-base
LoRA r         = 8
Seeds          = 42
Epochs         = 1
Val macro-F1   = 0.1111
Test macro-F1  = 0.0000
gate_pass      = false
```

Interpretation:

```text
The smoke test is successful as a technical pipeline check.
The smoke test is not valid classifier evidence and must not be exported/promoted.
The next real model step is full GPU LoRA training, unless rare-domain top-up is collected first.
```

## 14. Correct Order From Here

```text
1. Keep the frozen v1 800-row gold set as the stable dataset evidence.
2. Keep the deterministic key split and TF-IDF baselines as completed preparation evidence.
3. Record the rare-domain limitation in the thesis notes.
4. Decide whether to collect a rare-domain top-up batch before final training.
5. If not collecting top-up, run full XLM-R + LoRA training on a CUDA/GPU machine.
6. Run slice evaluation by language, quarter, text length, extraction method, category, and sector.
7. Export ONNX/INT8 only after model gates pass.
8. Promote the model only after the final registry, metrics, and artifact paths are recorded.
```

## 15. Do Not Forget

Do not claim rare-domain robustness from this gold set without qualification.

Reason:

```text
SECTOR_SPECIFIC = 671 / 800
EPF_ETF_CHANGE  = 0 / 800
PRODUCT_STANDARD = 4 / 800
BUSINESS_REGISTRATION = 5 / 800
PENALTY_ENFORCEMENT = 5 / 800
```

Do not use the real Label Studio projects for intentional wrong annotations.

Reason:

```text
intentional wrong labels corrupt real IAA and gold-standard data
```

Do not overwrite the frozen gold set after training starts.

Reason:

```text
model metrics must point to a stable dataset hash/version
```

## 16. Repo Git State At Time Of Handoff

Observed `git status --short`:

```text
 m enigmatrix-ml
 M mydata/label_studio.sqlite3
 M research/data/labeling/disagreements.csv
 M research/data/labeling/gold_standard.csv
 M research/data/labeling/iaa_report.json
 M research/data/labeling/iaa_report_summary.csv
 M research/data/labeling/manual_resolutions.csv
 M scripts/sample_for_labeling.py
?? mydata/export/project-11-at-2026-07-30-03-23-4c3ef401-info.json
?? mydata/export/project-11-at-2026-07-30-03-23-4c3ef401.json
?? mydata/export/project-13-at-2026-07-30-11-38-81103914-info.json
?? mydata/export/project-13-at-2026-07-30-11-38-81103914.json
?? mydata/media/upload/10/
?? mydata/media/upload/11/
?? mydata/media/upload/13/
?? research/data/labeling/2026-07-30_M1_PHASE3_LABELING_IAA_HANDOFF.md
?? research/data/labeling/batch_04.csv
?? research/data/labeling/batch_04_annotations_full.json
?? research/data/labeling/batch_04_manual_resolution_todo.csv
?? research/data/labeling/batch_04_manual_resolution_todo.xlsx
?? research/data/labeling/batch_04_provenance.json
?? research/data/labeling/batch_05.csv
?? research/data/labeling/batch_05_annotations_full.json
?? research/data/labeling/batch_05_provenance.json
```

Commit guidance:

- Commit clean research artifacts and scripts.
- Be careful with `mydata/label_studio.sqlite3` and `mydata/media/upload/*`; these are local Label Studio state, not always suitable for source control.
- Do not add co-author trailers if committing.

Suggested commit grouping:

```text
1. Batch 04 sampler/code:
   scripts/sample_for_labeling.py
   research/data/labeling/batch_04.csv
   research/data/labeling/batch_04_provenance.json

2. Batch 04 annotation export:
   research/data/labeling/batch_04_annotations_full.json

3. IAA/resolution outputs:
   research/data/labeling/disagreements.csv
   research/data/labeling/gold_standard.csv
   research/data/labeling/iaa_report.json
   research/data/labeling/iaa_report_summary.csv
   research/data/labeling/manual_resolutions.csv
   research/data/labeling/batch_04_manual_resolution_todo.csv
   research/data/labeling/batch_04_manual_resolution_todo.xlsx

4. Batch 05 active-learning/export artifacts:
   research/data/labeling/batch_05.csv
   research/data/labeling/batch_05_provenance.json
   research/data/labeling/batch_05_annotations_full.json
```

Suggested commit names:

```text
Add active-learning Batch 04 sampler output
Add Batch 04 Label Studio annotation export
Update M1 IAA resolution through Batch 04
Add Batch 05 active-learning annotation export
```

## 17. Final Decision Summary

The research pipeline is now in the correct Phase 3 state:

```text
calibration passed
four real batches resolved into gold
IAA reducer exists
gold_standard.csv exists
800 accepted gold rows exist from Batches 02-05
Batch 05 active-learning loop executed
manual resolution workflow exists
frozen v1 gold artifacts exist
deterministic train/val/test split exists
TF-IDF baselines completed
CPU LoRA smoke completed as a pipeline check
```

The next research-critical action is:

```text
document rare-domain limitation -> decide top-up vs train-now -> run full GPU LoRA -> evaluate/export/promote only if gates pass
```

The main quality risk to control is:

```text
SME relevance consistency
```

The main class-balance risk to control is:

```text
minority regulatory categories are still underrepresented
```

The correct next milestone is:

```text
full GPU XLM-R/LoRA training results and final evaluation on the accepted 800-row v1 gold set
```
