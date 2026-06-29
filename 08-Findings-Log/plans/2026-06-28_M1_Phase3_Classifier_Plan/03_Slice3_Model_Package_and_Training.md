---
tags: [m1, phase-3, slice-3, model, xlm-roberta, lora, training]
date: 2026-06-28
status: 🔲 blocked-by Slice 2 (needs gold_standard.csv)
---

# Slice 3 — Model package + training (XLM-R + LoRA)

## Purpose
Create the missing `enigmatrix-ml/m1/model/` package and train the dual-head classifier (12-category single-label + 10-sector multi-label) to **macro-F1 ≥ 0.92** over a 3-seed temporal-split run.

## Prerequisites
- Slice 2 gold set + temporal splits at `enigmatrix-ml/datasets/m1_regulations/{train,val,test}.parquet`.
- GPU (Colab/Kaggle/Fly A10 ok) or patience on CPU. Deps: `torch`, `transformers`, `peft`, `datasets`, `scikit-learn`, `mlflow`.

## Files to create (`enigmatrix-ml/m1/model/`)
```
model/
├── __init__.py
├── config.py          # ModelConfig dataclass (base id, LoRA r/alpha/targets, lr, epochs, seeds)
├── data.py            # parquet → tokenized datasets; make_splits CLI (temporal)
├── architecture.py    # GazetteClassifier: XLM-R encoder + 2 heads
├── train_xlmr.py      # entrypoint: 3-seed loop, AdamW, early-stop, FP16, MLflow
├── eval.py            # (Slice 4) metrics + slices
└── export_onnx.py     # (Slice 5)
```

## Architecture (skeleton — `architecture.py`)
```python
import torch, torch.nn as nn
from transformers import AutoModel
from peft import LoraConfig, get_peft_model

class GazetteClassifier(nn.Module):
    def __init__(self, base="xlm-roberta-base", n_cat=12, n_sec=10,
                 lora_r=16, lora_alpha=32, lora_dropout=0.1):
        super().__init__()
        enc = AutoModel.from_pretrained(base)
        self.encoder = get_peft_model(enc, LoraConfig(
            r=lora_r, lora_alpha=lora_alpha, lora_dropout=lora_dropout,
            target_modules=["query", "value"], bias="none"))
        h = enc.config.hidden_size
        self.cat_head = nn.Linear(h, n_cat)   # softmax (single-label)
        self.sec_head = nn.Linear(h, n_sec)   # sigmoid (multi-label)

    def forward(self, input_ids, attention_mask):
        pooled = self.encoder(input_ids=input_ids,
                              attention_mask=attention_mask).last_hidden_state[:, 0]
        return self.cat_head(pooled), self.sec_head(pooled)

# loss = CrossEntropy(cat_logits, cat_y) + BCEWithLogits(sec_logits, sec_y)
```

## Training rules (from BUILD_11 / doc 06)
- **3 seeds** `{42, 1, 2}`; report mean ± std macro-F1.
- **Temporal split already applied** (Slice 2) — never re-shuffle by random.
- AdamW, lr `2e-5` (head) / `1e-4` (LoRA), warmup 10%, early-stop on val macro-F1 (patience 3), FP16.
- Class imbalance: weighted CE + **back-translation augmentation ≤ 5× on minority categories, train split only**.
- Log everything to MLflow; write reproducibility hash + metrics to `model_registry.json`.

## Steps (commands)
```bash
cd enigmatrix-ml
uv sync --extra ml                     # torch/transformers/peft/datasets/mlflow
uv run python -m m1.model.train_xlmr \
    --data datasets/m1_regulations --seeds 42 1 2 \
    --base xlm-roberta-base --lora-r 16 --epochs 8 --fp16 \
    --out storage/models/m1/xlmr_lora_v1
```

## Tests / DoD
- Unit (no GPU): `architecture.py` forward returns shapes `(B,12)` + `(B,10)`; config round-trips. `uv run pytest tests/m1/model -v`.
- Training DoD: **3-seed mean macro-F1 ≥ 0.92**; per-language EN ≥ 0.93 / SI ≥ 0.88 / TA ≥ 0.86; `model_registry.json` written with the run hash.
- Start small: run the LoRA ablation `r ∈ {8,16,32}` on the first 300 labels to sanity-check the loop before the full run (doc 05_M1_3).

## Does NOT do
- No slice/error analysis (Slice 4). No ONNX/serving (Slice 5).

## Cross-refs
[BUILD_11_ML_Training_Pipeline](../../../04-Technology-Stack/ml/BUILD/BUILD_11_ML_Training_Pipeline.md) · [05_M1_Model_Architecture](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/05_M1_Model_Architecture.md) · [06_M1_Training_Evaluation](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/06_M1_Training_Evaluation.md) · next [04_Slice4_Evaluation_and_Slices.md](04_Slice4_Evaluation_and_Slices.md)
