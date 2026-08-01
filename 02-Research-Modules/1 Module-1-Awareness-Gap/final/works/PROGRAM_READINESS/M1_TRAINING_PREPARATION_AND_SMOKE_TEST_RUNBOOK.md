# M1 Training Preparation And LoRA Smoke-Test Runbook

> Updated: 2026-07-30  
> Repo: `C:\Reasearch\xyz`  
> ML folder: `C:\Reasearch\xyz\enigmatrix-ml`  
> Purpose: record the current 800-row training-preparation state, explain the CPU smoke-test result, and define the next real model-training order.

## 1. Current Training State

The 800-row gold-label gate is complete and has already been converted into model parquet splits.

```text
gold source      = C:\Reasearch\xyz\research\data\labeling\gold_standard_v1_800.csv
gold rows        = 800
split method     = deterministic --by key
train rows       = 560
validation rows  = 120
test rows        = 120
baseline report  = C:\Reasearch\xyz\storage\models\m1\baselines_v1\baselines.json
smoke registry   = C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model_registry.json
smoke checkpoint = C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model.pt
CUDA on laptop   = false
```

The current laptop is CPU-only, so the LoRA run completed only as a technical smoke test. It must not be used as final model-performance evidence.

## 2. What The Smoke Test Proved

The valid smoke command was:

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml

uv run --extra training --extra research python -m m1.model.train_xlmr `
  --data datasets\m1_regulations_smoke `
  --seeds 42 `
  --base xlm-roberta-base `
  --lora-r 8 `
  --epochs 1 `
  --out ..\storage\models\m1\xlmr_lora_smoke
```

Result:

```text
seed 42 epoch 1: val macro-F1 = 0.1111
test macro-F1                  = 0.0000
gate_pass                      = false
registry written               = yes
checkpoint written             = yes
```

Correct interpretation:

- This is a successful engineering smoke test because the dataset loads, XLM-R downloads, LoRA initializes, training runs, and the registry/checkpoint are written.
- This is not a valid research score because the smoke split has only 16 train rows, 8 validation rows, 8 test rows, one seed, and one epoch.
- The `0.0000` test macro-F1 is expected for such a tiny and imbalanced test set. It does not mean the real model is finished or broken.

Smoke split distribution:

```text
train 16:
  SECTOR_SPECIFIC = 11
  TAX_RATE_CHANGE = 2
  LABOUR_LAW      = 2
  IMPORT_EXPORT   = 1

validation 8:
  SECTOR_SPECIFIC  = 7
  PRODUCT_STANDARD = 1

test 8:
  SECTOR_SPECIFIC = 8
```

## 3. Terminal Warnings And Meaning

`hf_xet` warning:

```text
Xet Storage is enabled for this repo, but the 'hf_xet' package is not installed.
```

Meaning: not a failure. Hugging Face fell back to normal HTTP download. Optional improvement only:

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml
uv pip install hf_xet
```

Torch AMP warnings:

```text
torch.cuda.amp.GradScaler is deprecated
torch.cuda.amp.autocast is deprecated
```

Meaning: not a failure. The code should later be modernized to `torch.amp.GradScaler('cuda')` and `torch.amp.autocast('cuda')`, but this is not blocking the smoke or final training.

Missing registry from the first full-split CPU attempt:

```text
Get-Content ..\storage\models\m1\xlmr_lora_smoke\model_registry.json
Cannot find path...
```

Meaning: that earlier attempt is not counted as a completed run because no registry was written. The later smoke run is the valid artifact because it wrote both `model_registry.json` and `model.pt`.

## 4. Full Dataset Split Distribution

Current split:

```text
train 560:
  BUSINESS_REGISTRATION = 4
  IMPORT_EXPORT         = 20
  LABOUR_LAW            = 18
  PENALTY_ENFORCEMENT   = 3
  SECTOR_SPECIFIC       = 462
  TAX_RATE_CHANGE       = 53

validation 120:
  IMPORT_EXPORT         = 5
  LABOUR_LAW            = 6
  PENALTY_ENFORCEMENT   = 1
  PRODUCT_STANDARD      = 1
  SECTOR_SPECIFIC       = 104
  TAX_RATE_CHANGE       = 3

test 120:
  BUSINESS_REGISTRATION = 1
  IMPORT_EXPORT         = 7
  LABOUR_LAW            = 3
  PENALTY_ENFORCEMENT   = 1
  PRODUCT_STANDARD      = 3
  SECTOR_SPECIFIC       = 105
```

Important limitations:

- `EPF_ETF_CHANGE` has 0 gold examples, so the model cannot learn that class.
- `PRODUCT_STANDARD` has 0 training examples, so any test/validation performance for that class is not learnable from the current split.
- `TAX_RATE_CHANGE` has 0 test examples, so the final test score will not prove tax-rate performance.
- `SECTOR_SPECIFIC` dominates the data at 671/800 rows, so macro-F1 and per-class reports are more important than accuracy.
- Because the gold file does not contain reliable `gazette_published_date`, the split used `--by key`; this is deterministic but not a true temporal evaluation.

## 5. Baseline Result

Baseline command:

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml

uv run --extra training --extra research python -m m1.model.baselines `
  --data datasets\m1_regulations `
  --report ..\storage\models\m1\baselines_v1
```

Baseline result:

```text
TF-IDF Logistic Regression macro-F1 = 0.4980
TF-IDF LinearSVC macro-F1           = 0.6167
```

The full XLM-R + LoRA model should beat the LinearSVC baseline before it is treated as an improvement.

## 6. Training Code Checks Before Final Claim

Before final thesis/model claims, review these implementation details:

- `m1.model.train_xlmr` currently reports category macro-F1 only. Sector-head quality needs a separate evaluation report.
- `ModelConfig.lr_lora` exists, but the current optimizer uses one AdamW learning rate for all trainable parameters. If separate LoRA/head learning rates are required, update the optimizer before the final run.
- `compute_loss()` supports `class_weights`, but the trainer does not currently pass class weights. Given the class imbalance, add weighted loss or a sampler if rare-domain performance matters.
- Final evaluation should include per-class precision/recall/F1 and confusion matrix, not only one macro-F1 number.
- The final report should record dataset hash, split hash, model registry, command, seed list, machine/GPU, and package lock/version.

## 7. Correct Real Plan From Here

### Option A: Train Now And Document Limitation

Use this if the project needs a model quickly and the thesis can clearly state rare-domain scarcity.

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml

uv run --extra training --extra research python -m m1.model.train_xlmr `
  --data datasets\m1_regulations `
  --seeds 42 1 2 `
  --base xlm-roberta-base `
  --lora-r 16 `
  --epochs 8 `
  --fp16 `
  --out ..\storage\models\m1\xlmr_lora_v1
```

Use only on a CUDA/GPU machine. On CPU, omit `--fp16`, but expect the run to be very slow.

### Option B: Improve Dataset Before Final Training

Use this if the thesis needs stronger rare-domain evidence.

```text
1. Add or mine extra EPF_ETF_CHANGE examples.
2. Add more PRODUCT_STANDARD, BUSINESS_REGISTRATION, and PENALTY_ENFORCEMENT rows.
3. Re-run annotation and IAA/resolution for the extra rows.
4. Re-freeze a new gold version, for example gold_standard_v2_rare_topup.csv.
5. Rebuild splits so every class appears in train and test where possible.
6. Re-run baselines.
7. Run full XLM-R + LoRA on GPU.
```

Preferred thesis-safe route: Option B if time allows. Pragmatic route: Option A, but explicitly state that EPF and extremely rare domains are limitations of the v1 dataset.

## 8. Final Model Promotion Gate

Do not promote the smoke model.

Only promote a model when all are true:

```text
full training split used       = yes
three seeds used               = yes
baseline comparison recorded   = yes
overall macro-F1 acceptable    = yes
per-class failure reviewed     = yes
sector-head evaluation done    = yes
model registry saved           = yes
large artifact kept out of git = yes
```

`C:\Reasearch\xyz\storage\` is ignored by git, so `model.pt` should stay as a local/heavy model artifact unless a separate model registry or release storage is used.

