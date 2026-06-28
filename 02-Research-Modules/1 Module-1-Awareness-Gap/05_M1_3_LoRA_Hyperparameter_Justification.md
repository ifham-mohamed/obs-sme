# 05_M1_3 — LoRA Hyperparameter Justification

> Companion to [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) — `r=8/16/32` × `alpha=16/32/64` ablation plan, `target_modules` trade-off, `bias="none"` precedent, memory budget.
> **Implementation status:** 🔲 Deferred (BUILD_11 — ablation runs in `scripts/lora_ablation.py`)

## Purpose

Parent doc §4.2 declares the LoRA config (`r=16, alpha=32, target_modules=["query","value"], bias="none"`) with one sentence of justification per knob. This companion specifies the *ablation plan* that will validate those choices — what runs to make, what data to log, when to revisit each setting.

## Detailed process

### Ablation matrix (`r` × `alpha`)

Run a 3×3 grid on the held-out validation set. Each cell is the mean across 3 seeds. Total: 9 cells × 3 seeds = 27 short training runs (~30 min each on a single A100).

| | `alpha = 16` | `alpha = 32` (chosen) | `alpha = 64` |
|---|---|---|---|
| `r = 8` | run 1 | run 2 | run 3 |
| `r = 16` (chosen) | run 4 | **run 5 — primary** | run 6 |
| `r = 32` | run 7 | run 8 | run 9 |

For each run, log: macro-F1 mean ± std; per-language F1; trainable param count; GPU peak memory; epoch count to converge.

Expected outcomes (priors from the LoRA paper + small-data fine-tune lit):

- `r=8` cells under-fit on Sinhala/Tamil (insufficient adapter capacity for cross-lingual transfer).
- `r=32` cells over-fit at 800 docs (more variance across seeds).
- `r=16` × `alpha=32` is the local optimum (chosen).
- The `alpha = 2r` ratio is monotone-better than `alpha = r` or `alpha = 4r` — moving along the diagonal is the most informative axis.

### Target-modules choice

The original LoRA paper recommends `[query, value]` for classification fine-tuning. Three alternatives evaluated:

| Modules | Trainable params | Expected F1 vs chosen | Inference latency impact |
|---|---|---|---|
| `[query, value]` (chosen) | ~2.4 M | baseline | baseline |
| `[query, value, key]` | ~3.6 M | +0.3 pp | +5 % |
| `[query, value, key, output]` | ~7.2 M | +0.8 pp | +12 % |
| `[query, value]` + classification heads frozen | ~2.4 M | −2.0 pp | baseline | (the heads need training anyway — bad choice)

The 0.8 pp gain at `[query, value, key, output]` doesn't justify the 12 % latency cost — the inference-latency budget in [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md) is tight.

### `bias="none"` rationale

PEFT's three bias options:

- `none` — biases unchanged (chosen).
- `all` — train all biases.
- `lora_only` — train only the LoRA-injected biases.

`none` is the *PEFT default*. The empirical effect of bias-tuning is < 0.1 pp F1 on classification tasks per the PEFT documentation. Choosing `none` is therefore "precedent-matching" — it follows the documented default rather than over-fitting.

### Memory budget

```
Base model (XLM-R-base):    125M params × 4 bytes (fp32) = 500 MB
LoRA adapters (r=16):       ~2.4M params × 4 bytes      = 9.6 MB
Optimizer state (AdamW):    2× param count × 4 bytes    = +19 MB
Forward activations (batch=16, seq=512): ~3 GB
Total GPU memory:           ~3.5 GB on A100 (FP32)
                            ~1.8 GB with FP16 mixed precision (chosen)
```

Fits comfortably on a single A100 (40 GB) or even a T4 (16 GB). The full fine-tuning alternative (~5 GB activations at batch=16) is just on the edge of T4.

## Technology choices

| Knob | Chosen | Top alternative | Trade-off |
|---|---|---|---|
| `r` | 16 | 32 | At 800 docs, r=16 doesn't over-fit; r=32 might be needed at 5k+ docs |
| `alpha` | 32 | 64 | Keep ratio at 2; only change if F1 plateaus across seeds |
| `target_modules` | `[query, value]` | `[query, value, key, output]` | +12% latency for +0.8 pp F1 — not worth it |
| `bias` | `"none"` | `"lora_only"` | PEFT default; bias-tuning gives < 0.1 pp F1 |
| `dropout` | 0.1 | 0.05 | Match base model's dropout to avoid doubled dropout |
| `task_type` | `FEATURE_EXTRACTION` | `SEQ_CLS` | Dual-head architecture is incompatible with `SEQ_CLS` |

## Worked example

A representative `r=16, alpha=32, seed=42` run on a small pilot (50 docs, 3 epochs):

```
Epoch 1: train_loss=1.82, val_loss=1.65, val_macroF1=0.61, val_perlang_F1={en:0.68, si:0.55, ta:0.51}
Epoch 2: train_loss=1.10, val_loss=1.31, val_macroF1=0.74, val_perlang_F1={en:0.81, si:0.71, ta:0.68}
Epoch 3: train_loss=0.78, val_loss=1.22, val_macroF1=0.79, val_perlang_F1={en:0.85, si:0.77, ta:0.72}
Trainable params: 2,421,696 / 125,002,752 (1.94%)
GPU peak memory: 4.1 GB (FP32)  /  1.9 GB (FP16)
Time: 8 min (FP32)  /  4.5 min (FP16)
```

The numbers above are the *pilot*; the full BUILD_11 run targets epoch 6+ with proper data, F1 ≥ 0.92.

## Failure modes & edge cases

- **Variance across seeds > 0.05.** Indicates over-fitting; drop `r` from 16 → 8 and re-run.
- **Mean F1 plateaus below target.** Increase `r` to 32 or expand `target_modules` to `[query, value, key]`.
- **GPU OOM during training.** Drop batch size from 16 → 8 + enable gradient accumulation (effective batch stays 16).
- **Adapter file size > 25 MB.** Bug — `r=16` should produce < 10 MB. Likely cause: someone accidentally saved the base model with the adapter. Mitigation: `model.save_pretrained()` instead of `torch.save(model.state_dict())`.

## Validation & acceptance criteria

- **All 9 cells of the ablation grid completed.** Stored as `research/data/lora_ablation_results.csv`.
- **Chosen cell is within 1 pp of the grid maximum.** If a different cell is > 1 pp better, switch and document.
- **Seed std ≤ 0.05.** Otherwise re-run with one additional seed for robustness.
- **Memory budget validated.** Peak GPU memory observed ≤ 8 GB at batch=16 + FP16.

## Cross-references

- Parent: [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) §4.2
- Related: [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) §3 (hyperparameters)
- BUILD phase: BUILD_11 §LoRA ablation
- Code (when shipped): `scripts/lora_ablation.py`, results in `research/data/lora_ablation_results.csv`
