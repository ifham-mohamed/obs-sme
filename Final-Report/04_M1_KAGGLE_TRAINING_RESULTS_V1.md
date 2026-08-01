# Module 1 Kaggle GPU Training Results V1

Generated: 2026-07-30  
Module: Module 1 - Regulatory Change Awareness Gap  
Environment: Kaggle Free GPU notebook  
Purpose: record the latest GPU training attempt and the final model decision for the 800-row v1 dataset.

## 1. Final Decision

The v1 transformer model should **not** be promoted.

```text
Current best v1 model         = TF-IDF LinearSVC baseline
Best v1 baseline macro-F1     = 0.789365
Best LoRA diagnostic macro-F1 = 0.641471
LoRA gate_pass                = false
ONNX export/promote           = not done
```

Correct report wording:

> GPU-based XLM-R LoRA diagnostics were executed on Kaggle using the frozen 800-record gold dataset. Although trainer adjustments improved LoRA performance from a majority-class collapse to 0.6415 macro-F1, the transformer model remained below the stratified TF-IDF LinearSVC baseline of 0.7894 macro-F1. Therefore, the v1 transformer model was not promoted, and TF-IDF LinearSVC remains the strongest current v1 classifier baseline.

Do not claim:

```text
XLM-R LoRA achieved the final target macro-F1.
XLM-R LoRA was exported/promoted as the production model.
The model passed the 0.92 target gate.
```

## 2. Dataset Used

Original frozen gold dataset:

```text
C:\Reasearch\xyz\research\data\labeling\gold_standard_v1_800.csv
```

Kaggle uploaded project dataset path:

```text
/kaggle/input/datasets/ifhammohamed1/m1-training-v1/enigmatrix-ml
```

Working copy path:

```text
/kaggle/working/enigmatrix-ml
```

The first split was deterministic by key and heavily majority-class dominated. A stratified diagnostic split was created in Kaggle:

```text
/kaggle/working/enigmatrix-ml/datasets/m1_regulations_stratified
```

Stratified split distribution:

```text
train 558:
  SECTOR_SPECIFIC         = 469
  TAX_RATE_CHANGE          = 40
  IMPORT_EXPORT            = 22
  LABOUR_LAW               = 19
  BUSINESS_REGISTRATION     = 3
  PENALTY_ENFORCEMENT       = 3
  PRODUCT_STANDARD          = 2

validation 121:
  SECTOR_SPECIFIC         = 101
  TAX_RATE_CHANGE           = 8
  IMPORT_EXPORT             = 5
  LABOUR_LAW                = 4
  PENALTY_ENFORCEMENT       = 1
  PRODUCT_STANDARD          = 1
  BUSINESS_REGISTRATION     = 1

test 121:
  SECTOR_SPECIFIC         = 101
  TAX_RATE_CHANGE           = 8
  IMPORT_EXPORT             = 5
  LABOUR_LAW                = 4
  PENALTY_ENFORCEMENT       = 1
  PRODUCT_STANDARD          = 1
  BUSINESS_REGISTRATION     = 1
```

Important limitation:

```text
EPF_ETF_CHANGE = 0 examples in the whole v1 dataset
PRODUCT_STANDARD, BUSINESS_REGISTRATION, and PENALTY_ENFORCEMENT remain extremely sparse
```

## 3. Kaggle Setup Notes

Kaggle dataset path was not the simple path originally expected. The correct source path was:

```text
/kaggle/input/datasets/ifhammohamed1/m1-training-v1/enigmatrix-ml
```

Project copy command used:

```python
!rm -rf /kaggle/working/enigmatrix-ml
!cp -r /kaggle/input/datasets/ifhammohamed1/m1-training-v1/enigmatrix-ml /kaggle/working/
%cd /kaggle/working/enigmatrix-ml
```

Dependency notes:

- Kaggle GPU selection required account/GPU access to be enabled.
- After `pip install -e ".[training,research,serving]" hf_xet`, Kaggle printed dependency conflict warnings because preinstalled packages expected different NumPy versions. These warnings did not block the M1 training dependencies.
- `torchao 0.10.0` conflicted with PEFT and was removed with `pip uninstall -y torchao`.
- Restarting the Kaggle session after package changes fixed dirty-kernel NumPy/import issues.

## 4. Baseline Results

Original deterministic split baseline:

```text
TF-IDF Logistic Regression macro-F1 = 0.498039
TF-IDF LinearSVC macro-F1           = 0.616745
```

Stratified split baseline:

```text
TF-IDF Logistic Regression macro-F1 = 0.771087
TF-IDF LinearSVC macro-F1           = 0.789365
```

Interpretation:

The stratified LinearSVC result is the current best v1 classifier result. Any transformer model must beat `0.789365` on the same stratified split before it is worth promoting.

## 5. LoRA Runs

### 5.1 GPU Smoke

The first Kaggle GPU smoke confirmed that XLM-R downloaded and the training loop ran, but the model score remained near zero. This was a smoke test only.

### 5.2 Original Full-Split Diagnostic

```text
split              = deterministic m1_regulations
seed               = 42
epochs             = 8
test macro-F1      = 0.155556
status             = majority-class collapse
```

Evaluation confirmed the model mostly predicted `SECTOR_SPECIFIC`, which matches the majority-class collapse pattern.

### 5.3 Fixed Trainer Diagnostic

Trainer adjustments applied in Kaggle:

- Stratified split for diagnostics.
- Weighted category loss.
- Weighted random sampler.
- Separate LoRA/head learning rates.
- Reduced sector loss weight.

Result:

```text
output folder       = /kaggle/working/storage/models/m1/xlmr_lora_v1_fixed_seed42
seed                = 42
epochs              = 8
lr_head             = 0.0005
lr_lora             = 0.0002
sector_loss_weight  = 0.2
validation macro-F1 = 0.266328
test macro-F1       = 0.487084
gate_pass           = false
```

### 5.4 Category-Only Extended Diagnostic

Result:

```text
output folder       = /kaggle/working/storage/models/m1/xlmr_lora_v1_catonly_seed42_e16
seed                = 42
epochs              = 16
lr_head             = 0.001
lr_lora             = 0.0003
sector_loss_weight  = 0.0
validation macro-F1 = 0.403285
test macro-F1       = 0.641471
slice cliff         = 27.89 pp
gate_pass           = false
```

Evaluation output:

```text
overall macro-F1 = 0.6415
slice cliff      = 27.89pp
target           = macro-F1 >= 0.92 and cliff <= 8pp
decision         = CHECK / not promotable
```

## 6. Why LoRA Was Not Promoted

LoRA improved after trainer fixes, but it remained below the baseline:

```text
TF-IDF LinearSVC stratified macro-F1 = 0.789365
Best LoRA macro-F1                   = 0.641471
Gap                                  = -0.147894
```

The likely causes are:

- The v1 dataset is small for transformer fine-tuning.
- `SECTOR_SPECIFIC` dominates the dataset.
- `EPF_ETF_CHANGE` has no examples.
- Several minority classes have only 4-5 total examples.
- The stratified test still contains only one example for several rare classes, making macro-F1 unstable.
- The current LoRA trainer still lacks final per-class reporting, confusion-matrix-driven tuning, and production-grade sector-head evaluation.

## 7. Next Work Order

Immediate:

```text
1. Keep TF-IDF LinearSVC as the current v1 classifier baseline.
2. Do not export/promote XLM-R LoRA v1.
3. Download and preserve Kaggle training evidence zip if not already done.
4. Update the final report to state that LoRA was attempted but underperformed the baseline.
```

Before retrying LoRA:

```text
1. Collect rare-domain top-up labels.
2. Create gold_standard_v2_rare_topup.csv.
3. Ensure each class appears in train/validation/test where possible.
4. Add per-class evaluation and confusion matrix outputs.
5. Re-run TF-IDF baseline on the same v2 split.
6. Re-run LoRA diagnostics.
7. Only run 3-seed LoRA if a one-seed diagnostic beats the baseline.
```

Rare-domain target:

```text
EPF_ETF_CHANGE          >= 30-50 examples
PRODUCT_STANDARD        >= 30-50 examples
BUSINESS_REGISTRATION   >= 30-50 examples
PENALTY_ENFORCEMENT     >= 30-50 examples
IMPORT_EXPORT           >= 50 examples if possible
```

## 8. Copy-Ready Final Report Paragraph

> Transformer training was tested on Kaggle GPU using the frozen 800-record v1 gold dataset. The initial LoRA run collapsed toward the majority `SECTOR_SPECIFIC` class, producing macro-F1 of 0.1556. After introducing a stratified diagnostic split, weighted sampling, weighted category loss, and separate learning rates for LoRA and classification heads, the best single-seed LoRA diagnostic improved to 0.6415 macro-F1. However, this remained below the stratified TF-IDF LinearSVC baseline of 0.7894 macro-F1 and failed the required model gate. Therefore, the v1 transformer checkpoint was not promoted; the result is reported as evidence that rare-domain scarcity and class imbalance must be addressed before reliable transformer fine-tuning.

