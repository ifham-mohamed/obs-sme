# Module 1 Evidence, Evaluation, and Commands

Generated: 2026-07-30 · updated 2026-08-01 with V6 classifier freeze
Module: Module 1 - Regulatory Change Awareness Gap  
Owner: Mohomed M.R.I (215075J) — working name Ifham Mohamed

> [!info] Chapter numbering
> This pack was written against the first-pass 7-chapter draft. The report now follows the official B21 FYP template, so the evaluation content lives in **Chapter 7**, not Chapter 6: metrics are §7.1, Module 1 results are §7.2.1, and the reproducibility commands are §7.2.1.9. The evidence, formulas and commands below are unchanged and remain the working source. See [[04_OFFICIAL_TEMPLATE_STRUCTURE_MAP]].

This file is the working evidence pack for writing the final report sections related to Module 1. It separates what is already supported by the codebase and artifacts from what still needs additional evidence before final submission.

## 0. 2026-08-01 V6 Supersession

The V1 and V3 sections below remain useful historical evidence, but they are no longer the latest classifier result. The current final classifier evidence is:

| Evidence | Current value |
|---|---|
| Dataset | `m1_regulations_v6_1110_clean_fixedsplit` |
| Local dataset path | `C:\Reasearch\xyz\datasets\m1_regulations_v6_1110_clean_fixedsplit` |
| Kaggle input path | `/kaggle/input/datasets/ifhammohamed1/m1-regulations-v6-1110-clean-fixed-split/m1_regulations_v6_1110_clean_fixedsplit` |
| Split | 777 train / 166 validation / 167 temporal test |
| Frozen model | `m1_linearsvc_v6_primary` |
| Local model path | `C:\Reasearch\xyz\models\m1\linearsvc_v6_primary` |
| Model bundle | `C:\Reasearch\xyz\models\m1\linearsvc_v6_primary_bundle.zip` |
| Validation macro-F1 | 0.924476 |
| Temporal test macro-F1 | 0.947220 |
| Test accuracy | 0.958084, 160/167 correct |
| XLM-R V6 comparison | 0.743563 test macro-F1, not promoted |
| Decision | TF-IDF + balanced LinearSVC is the frozen primary classifier |

Use this wording for the current completed classifier work:

> Module 1's final promoted classifier is a TF-IDF word uni/bi-gram pipeline with `LinearSVC(class_weight="balanced")`, trained on the frozen V6 temporal split. It achieved validation macro-F1 0.9245 and temporal-test macro-F1 0.9472, passing the 0.92 gate. XLM-R LoRA was trained and debugged but not promoted because its V6 temporal-test macro-F1 was 0.7436. The promoted model is category-only and emits an uncalibrated decision margin, not calibrated probability confidence.

Do not claim:

> The production classifier is XLM-R/ONNX, predicts sectors, or produces calibrated confidence percentages.

### 0.1 Verify Current Local Artifacts

```powershell
Get-ChildItem C:\Reasearch\xyz\datasets\m1_regulations_v6_1110_clean_fixedsplit
Get-ChildItem C:\Reasearch\xyz\models\m1\linearsvc_v6_primary

Get-FileHash -Algorithm SHA256 `
  C:\Reasearch\xyz\kaggle_bundle\m1_regulations_v6_1110_clean_fixedsplit.zip, `
  C:\Reasearch\xyz\models\m1\linearsvc_v6_primary_bundle.zip
```

Expected hashes:

```text
66EF4CF6FB187146641173BBB71628AD711C635FCEADE34CAB01AADDD99F35F0  m1_regulations_v6_1110_clean_fixedsplit.zip
2F80BEFE494F1275DCB14FCB5352902A8BF98C1CC3FA86F919D53B7958C5F11B  linearsvc_v6_primary_bundle.zip
```

### 0.2 Print Current Dataset Distribution

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml
@'
from pathlib import Path
import pandas as pd

base = Path(r"C:\Reasearch\xyz\datasets\m1_regulations_v6_1110_clean_fixedsplit")
for split in ["train", "val", "test"]:
    df = pd.read_parquet(base / f"{split}.parquet")
    print(f"\n{split}: {len(df)} rows")
    print(df["category"].value_counts().sort_index().to_string())
'@ | python -
```

Expected headline counts:

```text
train / val / test = 777 / 166 / 167
EPF_ETF_CHANGE     = 4 / 2 / 1
total rows         = 1110
```

### 0.3 Re-score The Frozen Model Locally

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml
@'
from pathlib import Path
import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score

model_path = Path(r"C:\Reasearch\xyz\models\m1\linearsvc_v6_primary\linearsvc_pipeline.joblib")
test_path = Path(r"C:\Reasearch\xyz\datasets\m1_regulations_v6_1110_clean_fixedsplit\test.parquet")

model = joblib.load(model_path)
df = pd.read_parquet(test_path)
y_true = df["category"].astype(str)
y_pred = model.predict(df["text"].fillna("").astype(str))

print("rows:", len(df))
print("macro_f1:", f1_score(y_true, y_pred, average="macro"))
print("accuracy:", accuracy_score(y_true, y_pred))
print(classification_report(y_true, y_pred, digits=6))
'@ | python -
```

Expected result:

```text
rows: 167
macro_f1: 0.9472199858964565
accuracy: 0.9580838323353293
```

### 0.4 Kaggle Metric Recovery Commands

Use this inside the Kaggle notebook where the V6 model artifact exists:

```bash
python - <<'PY'
import json
from pathlib import Path

model_dir = Path("/kaggle/working/storage/models/m1/linearsvc_v6_primary")
for name in ["model_registry.json", "validation_summary.json", "test_summary.json"]:
    path = model_dir / name
    print(f"\n== {name} ==")
    print(json.dumps(json.loads(path.read_text()), indent=2))
PY
```

Use this to print the V6 dataset distribution from Kaggle input:

```bash
python - <<'PY'
from pathlib import Path
import pandas as pd

base = Path("/kaggle/input/datasets/ifhammohamed1/m1-regulations-v6-1110-clean-fixed-split/m1_regulations_v6_1110_clean_fixedsplit")
for split in ["train", "val", "test"]:
    df = pd.read_parquet(base / f"{split}.parquet")
    print(f"\n{split}: {len(df)} rows")
    print(df["category"].value_counts().sort_index().to_string())
PY
```

Use this to preserve Kaggle model evidence before leaving the notebook:

```bash
zip -r /kaggle/working/linearsvc_v6_primary_bundle.zip /kaggle/working/storage/models/m1/linearsvc_v6_primary
zip -r /kaggle/working/linearsvc_v6_diagnostics.zip /kaggle/working/storage/reports/m1/linearsvc_v6_diagnostics
```

Use this on Windows if Kaggle API credentials are configured:

```powershell
kaggle datasets download ifhammohamed1/m1-regulations-v6-1110-clean-fixed-split `
  -p C:\Reasearch\xyz\kaggle_bundle `
  --unzip

kaggle datasets download ifhammohamed1/m1-training-v1 `
  -p C:\Reasearch\xyz\kaggle_bundle\m1-training-v1 `
  --unzip
```

### 0.5 Current Caveats For Final Writing

- The V6 test split is spent for model selection. Further tuning must use fresh validation evidence or a new external split.
- `EPF_ETF_CHANGE` still has only one temporal-test row. Report its correct classification as a note, not as robust per-class performance.
- LinearSVC does not predict sectors. Sector applicability remains in the expert/manual sector ledger.
- LinearSVC emits margins, not calibrated probabilities. Do not render margins as percentages.

## 1. Final Report Position For Module 1

Module 1 can be presented as an implemented regulatory-change awareness pipeline with strong evidence for annotation quality, dataset preparation, baseline modelling, and training-pipeline readiness.

Use this wording for the current completed work:

> Module 1 implements the upstream regulatory intelligence pipeline of Enigmatrix. It supports regulation ingestion, text extraction, preprocessing, annotation, gold-dataset generation, regulatory-change classification preparation, sector matching, alert readiness, and evaluation artifact generation. The current gold dataset contains 800 reconciled labelled regulation records.

Do not claim this for v1:

> The XLM-R LoRA model achieved the final target macro-F1.

Correct wording for now:

> XLM-R LoRA training was validated through a local CPU smoke test and Kaggle GPU diagnostics. The best Kaggle LoRA diagnostic improved to 0.6415 macro-F1, but it remained below the stratified TF-IDF LinearSVC baseline of 0.7894 and therefore was not promoted.

## 2. Implemented Evidence Snapshot

| Evidence area | Current artifact | Current result |
|---|---|---|
| Gold labelled dataset | `C:\Reasearch\xyz\research\data\labeling\gold_standard_v1_800.csv` | 800 labelled rows |
| Dual annotation and reconciliation | `C:\Reasearch\xyz\research\data\labeling\iaa_report_v1_800.json` | 800 paired tasks, 1600 annotations, 40 disagreement rows |
| Category agreement | same IAA JSON | Cohen's kappa = 0.871534; raw agreement = 0.960000 |
| Sector agreement | same IAA JSON | Mean sector kappa = 0.863776; sector-set agreement = 0.952500 |
| SME relevance agreement | same IAA JSON | Cohen's kappa = 0.723518; raw agreement = 0.955000 |
| Baseline model 1 | `C:\Reasearch\xyz\storage\models\m1\baselines_v1\baselines.json` | TF-IDF Logistic Regression test macro-F1 = 0.498039 |
| Baseline model 2 | same baselines JSON | TF-IDF LinearSVC test macro-F1 = 0.616745 |
| Stratified baseline | Kaggle diagnostic split | TF-IDF LinearSVC test macro-F1 = 0.789365 |
| Local transformer smoke test | `C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model_registry.json` | Pipeline ran with XLM-R base, LoRA r=8, 1 seed, 1 epoch; test macro-F1 = 0.0; gate_pass = false |
| Kaggle transformer diagnostic | `04_M1_KAGGLE_TRAINING_RESULTS_V1.md` | Best LoRA diagnostic test macro-F1 = 0.641471; slice cliff = 27.89 pp; gate_pass = false; not promotable |
| Production classifier readiness | `C:\Reasearch\xyz\enigmatrix-backend\app\m1\services\classifier_service.py` | ONNX inference wrapper exists; status is `no_model` until ONNX artifact is placed in `storage/models/m1/onnx/v1` |
| Summarization/translation readiness | Backend schema, admin translation queue, NLLB helper, title scraper, field metrics | Architecture is present; production summary generation and backfill need final implementation/evidence |

## 3. Current Dataset And Label Schema

### 3.1 Current Gold Dataset

Current file:

`C:\Reasearch\xyz\research\data\labeling\gold_standard_v1_800.csv`

Current columns:

```text
batch_id, regulation_id, regulation_key, gazette_number, year, language,
classification_chunk, change_category, affected_sectors, is_sme_relevant,
confidence, confidence_mean, annotator_ids, resolution_method, resolver_id,
disagreement_fields, annotator_notes, resolver_notes, source_exports
```

Current category distribution:

| Category | Count |
|---|---:|
| `SECTOR_SPECIFIC` | 671 |
| `TAX_RATE_CHANGE` | 56 |
| `IMPORT_EXPORT` | 32 |
| `LABOUR_LAW` | 27 |
| `BUSINESS_REGISTRATION` | 5 |
| `PENALTY_ENFORCEMENT` | 5 |
| `PRODUCT_STANDARD` | 4 |
| `EPF_ETF_CHANGE` | 0 |

Important limitation:

The current gold CSV does not include `gazette_published_date`. The ML data loader expects `gazette_published_date` for temporal splitting, so the current Parquet splits have `date = NaT` for all rows. Do not describe the current split as a true temporal split unless publication dates are backfilled and the split is regenerated with `--by date`.

The current gold CSV uses `language`, while the ML data loader expects `primary_language`. If per-language evaluation is required, normalize this field before generating final splits.

### 3.2 Current Classification Taxonomy

The current code source of truth is:

`C:\Reasearch\xyz\enigmatrix-ml\m1\model\labels.py`

Current categories:

1. `TAX_RATE_CHANGE`
2. `IMPORT_EXPORT`
3. `SECTOR_SPECIFIC`
4. `EPF_ETF_CHANGE`
5. `LABOUR_LAW`
6. `PRODUCT_STANDARD`
7. `BUSINESS_REGISTRATION`
8. `PENALTY_ENFORCEMENT`

Current study sectors:

1. `grocery_retail`
2. `food_service`
3. `general_retail`

Do not copy older planning text that says 12 categories and 10 sectors unless the code and dataset are changed back to that taxonomy.

### 3.3 Current Split Counts

Current folder:

`C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations`

| Split | Rows | Notes |
|---|---:|---|
| Train | 560 | Contains 462 `SECTOR_SPECIFIC` rows |
| Validation | 120 | Contains 104 `SECTOR_SPECIFIC` rows |
| Test | 120 | Contains 105 `SECTOR_SPECIFIC` rows |

The current split is heavily imbalanced. This makes macro-F1 more important than accuracy, because accuracy can look high if the model overpredicts the majority class.

## 4. Annotation Reliability Results

Source:

`C:\Reasearch\xyz\research\data\labeling\iaa_report_v1_800.json`

### 4.1 Overall Results

| Measure | Value |
|---|---:|
| Tasks | 800 |
| Annotations | 1600 |
| Paired tasks | 800 |
| Gold rows | 800 |
| Disagreement rows | 40 |
| Category Cohen's kappa | 0.871534 |
| Category raw agreement | 0.960000 |
| Grocery retail sector kappa | 0.784483 |
| Food service sector kappa | 0.854939 |
| General retail sector kappa | 0.951906 |
| Mean sector kappa | 0.863776 |
| Sector set agreement | 0.952500 |
| SME relevance kappa | 0.723518 |
| SME relevance raw agreement | 0.955000 |

### 4.2 Disagreement Fields

| Field | Disagreement count |
|---|---:|
| `change_category` | 32 |
| `affected_sectors` | 38 |
| `is_sme_relevant` | 36 |

### 4.3 Batch-Level Results

| Batch | Category kappa | Mean sector kappa | SME relevance kappa |
|---|---:|---:|---:|
| Batch 02 | 0.750872 | 0.872110 | 0.745763 |
| Batch 03 | 0.707877 | 0.854148 | 0.660194 |
| Batch 04 | 0.955506 | 0.845916 | 0.669967 |
| Batch 05 | 0.883743 | 0.915566 | 0.938575 |

Suggested report interpretation:

> The annotation process produced strong agreement for regulatory change category and sector relevance. SME relevance showed lower kappa than category classification, indicating that the boundary between SME-facing and non-SME-facing notices is more subjective and required resolver rules.

## 5. Baseline And Transformer Model Status

### 5.1 Baseline Results

Source:

`C:\Reasearch\xyz\storage\models\m1\baselines_v1\baselines.json`

Original deterministic key split:

| Model | Test macro-F1 |
|---|---:|
| TF-IDF Logistic Regression | 0.498039 |
| TF-IDF LinearSVC | 0.616745 |

Kaggle stratified diagnostic split:

| Model | Test macro-F1 |
|---|---:|
| TF-IDF Logistic Regression | 0.771087 |
| TF-IDF LinearSVC | 0.789365 |

Suggested report wording:

> LinearSVC over TF-IDF features provided the strongest current v1 classifier result. On the original deterministic split it reached 0.6167 macro-F1, and on the stratified diagnostic split it reached 0.7894 macro-F1. This result became the practical non-transformer reference point that XLM-R LoRA had to exceed.

### 5.2 Local XLM-R LoRA Smoke Test

Source:

`C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model_registry.json`

| Field | Value |
|---|---|
| Base model | `xlm-roberta-base` |
| Seeds | `[42]` |
| Epochs | 1 |
| LoRA r | 8 |
| LoRA alpha | 32 |
| LoRA dropout | 0.1 |
| LoRA target modules | `query`, `value` |
| Number of categories | 8 |
| Number of sectors | 3 |
| Validation macro-F1 mean | 0.111111 |
| Test macro-F1 mean | 0.000000 |
| Gate pass | `false` |
| Created at | `2026-07-30T12:57:25` |

Suggested report wording:

> A local CPU smoke test was executed to validate dependency loading, tokenizer setup, LoRA initialization, the training loop, checkpoint writing, and registry generation. Because it used a reduced configuration, one seed, and one epoch, its metric values are not used as final model-performance evidence.

### 5.3 Kaggle XLM-R LoRA Diagnostic

Detailed record:

`E:\Obsidian\sme\Final-Report\04_M1_KAGGLE_TRAINING_RESULTS_V1.md`

| Run | Split | Key settings | Test macro-F1 | Decision |
|---|---|---|---:|---|
| Original LoRA diagnostic | deterministic key split | seed 42, 8 epochs | 0.155556 | Majority-class collapse |
| Fixed trainer diagnostic | stratified split | weighted sampler/loss, `lr_head=5e-4`, `lr_lora=2e-4`, sector loss 0.2, 8 epochs | 0.487084 | Improved but below baseline |
| Category-only extended diagnostic | stratified split | weighted sampler/loss, `lr_head=1e-3`, `lr_lora=3e-4`, sector loss 0.0, 16 epochs | 0.641471 | Best LoRA run, still below baseline |

Evaluation check for the best LoRA diagnostic:

```text
overall macro-F1 = 0.6415
slice cliff      = 27.89 pp
gate             = want macro-F1 >= 0.92 and slice cliff <= 8 pp
gate_pass        = false
```

Final v1 decision:

> XLM-R LoRA was not promoted for the v1 dataset. The best LoRA diagnostic remained 14.79 percentage points below the stratified TF-IDF LinearSVC baseline and showed a large slice cliff. The result supports the conclusion that the current 800-row dataset is sufficient for baseline modelling but too sparse and imbalanced for reliable transformer fine-tuning across all rare regulatory domains.

### 5.4 Production Classifier Activation

The backend classifier wrapper is implemented at:

`C:\Reasearch\xyz\enigmatrix-backend\app\m1\services\classifier_service.py`

Current behaviour:

- The classifier loads an ONNX artifact from `M1_MODEL_ONNX_DIR`.
- Default ONNX directory: `storage/models/m1/onnx/v1`.
- If the directory is missing or empty, `classifier_status()` returns `no_model`.
- `classify_gazette_task` leaves the regulation at preprocessed/classification-pending state until a model artifact exists.
- This is expected because the v1 LoRA checkpoint was not promoted to ONNX.

Final report wording after ONNX export:

> After the final trained model was exported to ONNX and placed in `storage/models/m1/onnx/v1`, the backend classifier service loaded the artifact in-process and classified preprocessed gazette text with confidence-based review routing.

## 6. Summarization And Translation Status

The user plan includes automatic English summarization and Sinhala/Tamil translation after extraction and classification. The current codebase contains partial support for this, but it should be reported accurately.

### 6.1 Existing Support

Existing or planned assets found in the codebase/vault:

- Database/model/schema fields for `title_en`, `title_si`, `title_ta`, `summary_en`, `summary_si`, and `summary_ta`.
- Admin translation queue: `C:\Reasearch\xyz\enigmatrix-backend\app\api\v1\admin_translations.py`
- NLLB helper for English to Sinhala/Tamil translation: `C:\Reasearch\xyz\scripts\lib\nllb_translate.py`
- Gazette title scraper helper: `C:\Reasearch\xyz\scripts\lib\title_scraper.py`
- Field-metric support for title and summary fields in M1 measurement tooling.
- Readiness plan: `E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\final\works\PROGRAM_READINESS\M1_SUMMARIZATION_TRANSLATION_READINESS_PLAN.md`

### 6.2 Current Limitation

The production summarization step that generates `summary_en` from cleaned/classified regulatory text is not yet complete as a final evidence artifact. The NLLB helper can translate titles and short summaries, but a batch backfill script or Colab notebook should be completed if final report claims large-scale automatic summary/translation output.

### 6.3 Recommended Final Pipeline

Use this as the final design description if the implementation is completed before submission:

1. Extract raw text from the gazette or official regulatory source.
2. Clean and preprocess the text into `classification_chunk`.
3. Classify the regulation into change category and affected SME sectors.
4. Generate a controlled English summary using the title, domain, affected sectors, amendment type, and cleaned regulatory text.
5. Translate `title_en` and `summary_en` into Sinhala and Tamil using NLLB in Google Colab.
6. Store `title_si`, `title_ta`, `summary_si`, and `summary_ta`.
7. Route low-confidence or low-quality outputs to admin review.
8. Use reviewed summaries/translations in SME alerts, dashboards, and final evaluation samples.

Suggested report wording if completed:

> After classification, each regulation was converted into a controlled English summary using its title, regulatory domain, affected sectors, amendment type, and extracted text. The English title and summary were then translated into Sinhala and Tamil using the NLLB-200 model on Google Colab GPU, allowing SME-facing alerts to be delivered in the user's preferred language.

Suggested report wording if not completed:

> The schema, translation helper, and admin translation workflow were implemented, but the final production summarization and bulk translation backfill were left as future work.

## 7. Evaluation Formulas

### 7.1 Classification Metrics

For each category `i`:

```text
Precision_i = TP_i / (TP_i + FP_i)
Recall_i    = TP_i / (TP_i + FN_i)
F1_i        = 2 * Precision_i * Recall_i / (Precision_i + Recall_i)
```

Macro-F1:

```text
Macro-F1 = (1 / K) * sum(F1_i for i in categories)
```

Multi-class accuracy:

```text
Accuracy = number_of_correct_predictions / total_predictions
```

For sector relevance, treat each sector as a binary label:

```text
Micro-F1 = 2 * sum(TP_s) / (2 * sum(TP_s) + sum(FP_s) + sum(FN_s))
Macro-F1 = mean(F1_s for s in sectors)
```

Use macro-F1 as the primary category metric because the dataset is imbalanced.

### 7.2 Inter-Annotator Agreement

Cohen's kappa:

```text
kappa = (p_o - p_e) / (1 - p_e)
```

Where:

- `p_o` = observed agreement between annotators.
- `p_e` = expected agreement by chance.

Use kappa to report reliability for category labels, sector labels, and SME relevance labels.

### 7.3 Extraction And Field Accuracy

The extraction evaluation should use field-level scoring, following the M1 evaluation specification:

```text
field_accuracy(f) = mean(s(r, f))
record_score(r)   = sum(s(r, f) for f in V(r)) / |V(r)|
overall_micro     = sum_r sum_f s(r, f) / sum_r |V(r)|
overall_macro     = mean(record_score(r))
```

Where:

- `r` = regulation record.
- `f` = evaluated field.
- `V(r)` = fields visible/valid for record `r`.
- `s(r, f)` = score for field `f` in record `r`, usually 1 for exact match, 0 for incorrect, or a partial similarity score for text fields.

For raw text extraction:

```text
CER = edit_distance(predicted_chars, gold_chars) / len(gold_chars)
text_score = 1 - CER
```

### 7.4 Alert And Awareness Lag Metrics

Recommended timeliness metrics:

```text
extraction_latency = extracted_at - source_discovered_at
classification_latency = classified_at - preprocessed_at
alert_latency = alert_created_at - gazette_published_at
awareness_lag = sme_first_awareness_at - gazette_published_at
```

Recommended alert relevance metrics:

```text
alert_precision = relevant_alerts_sent / total_alerts_sent
alert_recall = relevant_alerts_sent / total_relevant_regulations_for_sme
```

For the report, use median and interquartile range for time-lag distributions because lag data is usually skewed.

### 7.5 Calibration Metrics

If confidence scores are reported, add calibration metrics:

```text
Brier score = mean((predicted_probability - actual_label)^2)
ECE = sum_b (|B_b| / N) * abs(accuracy(B_b) - confidence(B_b))
```

Where `B_b` is confidence bin `b`.

## 8. Commands To Retrieve Or Recompute Evidence

Run PowerShell from the indicated working directory.

### 8.1 Capture Local Laptop Configuration

Use this for the final report section that says the local machine was used only for smoke testing.

```powershell
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors
Get-CimInstance Win32_ComputerSystem | Select-Object @{Name='RAM_GB';Expression={[math]::Round($_.TotalPhysicalMemory/1GB,2)}}
nvidia-smi
```

PyTorch environment check:

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml
uv run python -c "import torch, platform; print(platform.platform()); print('torch', torch.__version__); print('cuda', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"
```

If `nvidia-smi` fails or `torch.cuda.is_available()` is false, describe the local run as CPU-only.

### 8.2 Print Current IAA Summary

```powershell
cd C:\Reasearch\xyz
@'
import json
from pathlib import Path
p = Path(r"research\data\labeling\iaa_report_v1_800.json")
d = json.loads(p.read_text(encoding="utf-8"))
o = d["overall"]
for key in [
    "tasks", "annotations", "paired_tasks", "gold_rows", "disagreement_rows",
    "category_kappa", "category_agreement", "mean_sector_kappa",
    "sector_set_agreement", "sme_relevance_kappa", "sme_relevance_agreement"
]:
    print(f"{key}: {o[key]}")
print("sector_kappa:", o["sector_kappa"])
print("disagreement_fields:", o["disagreement_fields"])
'@ | uv run python -
```

### 8.3 Recompute IAA And Gold CSV

```powershell
cd C:\Reasearch\xyz
uv run python scripts\resolve_iaa.py `
  --input research\data\labeling\batch_02_annotations_full.json `
  --input research\data\labeling\batch_03_annotations_full.json `
  --input research\data\labeling\batch_04_annotations_full.json `
  --input research\data\labeling\batch_05_annotations_full.json `
  --resolutions research\data\labeling\manual_resolutions.csv `
  --out-dir research\data\labeling `
  --lead-annotator 1
```

### 8.4 Validate Gold Dataset Counts

```powershell
cd C:\Reasearch\xyz
@'
from pathlib import Path
import pandas as pd
p = Path(r"research\data\labeling\gold_standard_v1_800.csv")
df = pd.read_csv(p)
print("rows:", len(df))
print("columns:", list(df.columns))
print("\ncategory counts:")
print(df["change_category"].value_counts(dropna=False).to_string())
print("\naffected_sectors nonblank:", df["affected_sectors"].fillna("").astype(str).str.strip().ne("").sum())
print("unique regulation_key:", df["regulation_key"].nunique())
'@ | uv run python -
```

### 8.5 Normalize Gold CSV Before Final Training

Use this if per-language metrics are required. This only fixes the language column mapping. It does not fix publication dates.

```powershell
cd C:\Reasearch\xyz
@'
from pathlib import Path
import pandas as pd
src = Path(r"research\data\labeling\gold_standard_v1_800.csv")
dst = Path(r"research\data\labeling\gold_standard_v1_800_ml_normalized.csv")
df = pd.read_csv(src)
if "primary_language" not in df.columns and "language" in df.columns:
    df["primary_language"] = df["language"]
df.to_csv(dst, index=False)
print(dst)
'@ | uv run python -
```

If publication dates are available in another table/export, add a `gazette_published_date` column before the next step. If not, use `--by key` and describe the split as deterministic, not temporal.

### 8.6 Generate Train/Validation/Test Splits

Current honest deterministic split:

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml
uv run python -m m1.model.data --in ..\research\data\labeling\gold_standard_v1_800_ml_normalized.csv --out datasets\m1_regulations --ratios 0.70 0.15 0.15 --by key
```

Temporal split only after `gazette_published_date` is backfilled:

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml
uv run python -m m1.model.data --in ..\research\data\labeling\gold_standard_v1_800_ml_normalized.csv --out datasets\m1_regulations --ratios 0.70 0.15 0.15 --by date
```

### 8.7 Inspect Split Distribution

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml
@'
from pathlib import Path
import pandas as pd
base = Path("datasets/m1_regulations")
for split in ["train", "val", "test"]:
    df = pd.read_parquet(base / f"{split}.parquet")
    print("\n" + split, len(df))
    print("date non-null:", df["date"].notna().sum() if "date" in df.columns else "missing")
    print(df["category"].value_counts(dropna=False).to_string())
'@ | uv run python -
```

### 8.8 Run Baselines

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml
uv run python -m m1.model.baselines --data datasets\m1_regulations --report ..\storage\models\m1\baselines_v1
```

### 8.9 Local CPU Smoke Test

Use this only to prove the pipeline runs locally.

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml
uv sync --extra training --extra research
uv run python -m m1.model.train_xlmr --data datasets\m1_regulations_smoke --seeds 42 --base xlm-roberta-base --lora-r 8 --epochs 1 --out ..\storage\models\m1\xlmr_lora_smoke
```

### 8.10 Kaggle GPU Training Attempt And Current Decision

Kaggle Free GPU was used after the local CPU smoke test. The first GPU diagnostic showed majority-class collapse, so a stratified diagnostic split and trainer patch were tested. The best LoRA diagnostic still underperformed TF-IDF LinearSVC, so no ONNX export/promotion was performed.

Kaggle project path:

```text
/kaggle/input/datasets/ifhammohamed1/m1-training-v1/enigmatrix-ml
```

Best LoRA diagnostic command:

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

Best LoRA evaluation command:

```bash
python -m m1.model.eval \
  --model /kaggle/working/storage/models/m1/xlmr_lora_v1_catonly_seed42_e16 \
  --test datasets/m1_regulations_stratified/test.parquet \
  --report /kaggle/working/storage/models/m1/eval_catonly_seed42_e16 \
  --base xlm-roberta-base
```

Final result:

```text
best LoRA macro-F1      = 0.641471
stratified LinearSVC    = 0.789365
slice cliff             = 27.89 pp
gate_pass               = false
promotion/export status = not promoted
```

Preserve Kaggle evidence:

```bash
zip -r /kaggle/working/m1_training_kaggle_results_v1.zip /kaggle/working/storage/models/m1
```

Download `m1_training_kaggle_results_v1.zip` from Kaggle and store it locally under `C:\Reasearch\xyz\storage\models\m1\` when available. If the zip is not downloaded, cite `04_M1_KAGGLE_TRAINING_RESULTS_V1.md` as the chat-derived run record and clearly state that the model artifact itself is not part of the repo.

### 8.11 Test NLLB Title Translation Locally

```powershell
cd C:\Reasearch\xyz
uv run python scripts\lib\nllb_translate.py "Value Added Tax (Amendment) Order"
```

Expected behaviour:

- First run downloads `facebook/nllb-200-distilled-600M`.
- It prints Sinhala and Tamil translations for the sample title.
- CPU is acceptable for a small title smoke test.
- For 800+ title/summary translations, use Google Colab GPU.

### 8.12 Suggested Colab Translation Notebook Pattern

Use this after summaries are generated. This is a notebook pattern, not an existing production script.

```python
import pandas as pd
from scripts.lib.nllb_translate import Translator

df = pd.read_csv("/content/gold_or_regulation_export_with_summaries.csv")
translator = Translator(device="cuda")

df["title_si"] = df["title_en"].fillna("").map(translator.to_sinhala)
df["title_ta"] = df["title_en"].fillna("").map(translator.to_tamil)
df["summary_si"] = df["summary_en"].fillna("").map(translator.to_sinhala)
df["summary_ta"] = df["summary_en"].fillna("").map(translator.to_tamil)

df.to_csv("/content/m1_summary_translation_backfill.csv", index=False)
```

If this workflow is used for final evidence, sample at least 30 translated records for manual quality review and report the review method.

### 8.13 Planned Summary Backfill Commands

These commands are recommended future scripts. They are not currently verified as existing files.

```powershell
cd C:\Reasearch\xyz
uv run python scripts\generate_regulation_summaries.py --status preprocessed,classified,verified --limit 200 --write
uv run python scripts\backfill_summary_translations_nllb.py --source summary_en --targets si,ta --limit 200 --write
```

Only include these as executed evidence after the scripts exist and produce reviewed outputs.

### 8.14 Regenerate Thesis Extraction Artifacts

```powershell
cd C:\Reasearch\xyz
make thesis-artifacts
```

This Make target runs:

```text
cd enigmatrix-backend && uv run python ../scripts/regenerate_thesis_tables.py
```

Expected output according to the Makefile comments:

```text
data/thesis/table_4_1.csv
data/thesis/table_4_2.csv
data/thesis/table_4_3.csv
data/thesis/figure_4_1.svg
data/thesis/figure_4_2.svg
data/thesis/RUN_PROVENANCE.md
```

## 9. Rare-Domain V3 Addendum

The 800-row V1 evidence remains useful as the first completed gold-labeling gate. The rare-domain V3 dataset then became the predecessor evidence that lifted LinearSVC to 0.9080 macro-F1, but V3 is now superseded for final classifier claims by the V6 dataset and frozen LinearSVC model described in §0.

Current accepted v3 files:

```text
C:\Reasearch\xyz\research\data\labeling\gold_standard_v3_1128.csv
C:\Reasearch\xyz\research\data\labeling\iaa_report_v3_1128.json
C:\Reasearch\xyz\research\data\labeling\iaa_report_summary_v3_1128.csv
C:\Reasearch\xyz\research\data\labeling\disagreements_v3_1128.csv
```

V3 IAA:

```text
tasks                = 1128
annotations          = 2256
gold rows            = 1128
category kappa       = 0.947215
mean sector kappa    = 0.965567
SME relevance kappa  = 0.914637
disagreement rows    = 44
```

V3 category distribution:

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

V3 baseline:

```text
split path                 = C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations_v3_1128_stratified
baseline path              = C:\Reasearch\xyz\storage\models\m1\baselines_v3_1128_stratified
TF-IDF LogReg macro-F1     = 0.862652
TF-IDF LinearSVC macro-F1  = 0.908012
```

Interpretation: the V3 rare-domain top-up made the dataset much stronger and moved the LinearSVC baseline close to the 0.92 gate. It still did not pass the final target. V6 then corrected four EPF/ETF incidental-mention labels, preserved the fixed split, and produced the promoted LinearSVC test macro-F1 of 0.947220. See [[05_M1_RARE_DOMAIN_TOPUP_AND_V3_BASELINE]] for the V3 artifact map and [18_M1_Dataset_And_Model_Lineage](../02-Research-Modules/1%20Module-1-Awareness-Gap/18_M1_Dataset_And_Model_Lineage.md) for the active V6 lineage.

## 10. Final Report Replacement Checklist

Before submission, replace or verify:

| Placeholder | Required final evidence |
|---|---|
| Transformer v1 final decision | Done: LoRA was tested on Kaggle GPU and was not promoted because best macro-F1 = 0.6415, below stratified LinearSVC = 0.7894 |
| V3 predecessor baseline decision | Done: rare-domain V3 LinearSVC reached 0.9080 macro-F1; close to 0.92 but superseded by V6 |
| V6 final classifier decision | Done: frozen TF-IDF + LinearSVC reached 0.947220 temporal-test macro-F1 and passed the 0.92 gate |
| Per-category F1 | Done for v3 LinearSVC baseline in `storage\models\m1\baselines_v3_1128_stratified\linsvc_per_class_report.csv`; still needed for any future promoted LoRA model |
| Sector F1 | Still needed because current LoRA eval reports category macro-F1 only |
| Per-language metrics | Only if `primary_language` is fixed in final split |
| ONNX latency | Not applicable for LoRA v1 because no ONNX export/promotion was done |
| `[ADD SCREENSHOT] classification admin UI` | Final web UI screenshot |
| `[ADD SCREENSHOT] alert UI` | Final web UI screenshot |
| `[ADD SCREENSHOT] translation/admin queue` | Only if translation workflow is included |
| `[VERIFY OFFICIAL NAME]` | Use the official UoM student record name and index |

## 11. Short Copy-Ready Module 1 Evaluation Paragraph

The Module 1 dataset was created through a dual-annotation workflow followed by disagreement resolution. The initial V1 gold dataset contained 800 labelled regulation records. After identifying rare-domain scarcity, two top-up batches produced the V3 1128-row resolved gold set, with category Cohen's kappa 0.9472, mean sector kappa 0.9656, and SME relevance kappa 0.9146. V3 lifted TF-IDF LinearSVC to 0.9080 macro-F1, close to but below the 0.92 gate. The final V6 correction preserved the fixed split, removed four incidental EPF/ETF labels from training, and produced the frozen TF-IDF + balanced LinearSVC primary classifier with temporal-test macro-F1 0.947220. XLM-R LoRA was trained and debugged but not promoted because its V6 temporal-test macro-F1 was 0.7436. The remaining caveats are that `EPF_ETF_CHANGE` has only one test record and `PENALTY_ENFORCEMENT` is the weakest measured class.
