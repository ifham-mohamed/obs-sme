# Phase 3 · Classification — Doc-05 Model: Code Status & Training Runbook

> Group: `PHASE3_ANNOTATION_CLASSIFICATION / classifier_model_training`. Covers docs 05_M1_1/2/3 (+ 06 training/eval). Companion to [[PHASE3_GAP_CLOSURE_PLAN]] and the program-level [[M1_NON_CODING_TASKS_AND_GOLIVE_READINESS_PLAN]].
> **Verdict (2026-07-24): the code for doc 05 is essentially COMPLETE.** What's missing to reach a trained, serving model is *not code* — it's the gold-labeled data, a GPU, and running the pipeline. Details below, command-level.

## 1. Is the code done? — Yes. Module map (all present in `enigmatrix-ml/m1/`)

| Doc / concern | Module | State |
|---|---|---|
| 05_M1_1 Sampling (stratified → k-means k=20 → active-learning + minority hand-picks) | `m1/data/samplers.py` + `scripts/sample_for_labeling.py` | **implemented** (constants match doc: `OPTIMAL_K=20`, thresholds, `CATEGORIES_12`) |
| 05_M1_2 Architecture comparison (4-way) | `m1/model/baselines.py` | **implemented** (baselines for the comparison) |
| 05 Architecture (XLM-R + LoRA + dual heads) | `m1/model/architecture.py` | **implemented** — `AutoModel` + `get_peft_model(LoraConfig(...))`, 12-way category (CE) + 10-way sector (BCE) heads |
| 05_M1_3 LoRA hyperparameters (r, alpha, target_modules, bias="none") | `m1/model/config.py` (`ModelConfig`) + `--lora-r` flag | **implemented** — `bias="none"`, `task_type=FEATURE_EXTRACTION`, configurable r/alpha/targets |
| 06 Gold loading + temporal split | `m1/model/data.py` | **implemented** — reads CSV/parquet gold export, temporal (never random) split, drops un-categorised rows |
| Label vocab | `m1/model/labels.py` | **implemented** (`encode_category`/`encode_sectors`/`parse_sectors`) |
| 06 Training (3-seed, early stop, ≥0.92 gate) | `m1/model/train_xlmr.py` | **implemented** — AdamW + warmup, AMP/fp16, best-val checkpoint, writes `model.pt` + `model_registry.json` with `gate_pass` |
| Slice / held-out eval | `m1/model/eval.py` | **implemented** |
| ONNX export (+ serving) | `m1/model/export_onnx.py`, `m1/model/inference.py` | **implemented** |
| Canary promotion / rollback | `m1/model/promotion.py`, `scripts/retrain.py` | **implemented** |
| Deps | `pyproject.toml` `training` extra (torch, peft, transformers, scikit-learn, onnxruntime) | **declared** |
| Test | `tests/m1/model/test_architecture.py` | present |

So there is **nothing to build** for doc 05 in the normal case. The classifier is `no_model` purely because it has **never been run on a real gold set** — the pieces are all there, unexercised.

## 2. What's needed apart from coding (the real blockers)

1. **A GPU host** with the training extra: `cd enigmatrix-ml && uv sync --extra training` (torch/peft/transformers/onnxruntime; ~GBs, CUDA). The rest of the stack stays torch-free.
2. **The gold-labeled dataset** — the input `data.py` consumes. This is the annotation effort (Phase-3 keystone): sampling → Label Studio → calibration κ≥0.80 → dual-annotation κ≥0.75 → active learning → ~800 gold labels excluding heuristic rows. (See the program readiness plan §3.) *No model can train before this exists.*
3. **Compute time + iteration** — 3 seeds × 8 epochs on XLM-R-base; the LoRA ablation adds a few more runs.

## 3. The full sequence — exactly how to do it (command-level)

```bash
cd C:\Reasearch\xyz\enigmatrix-ml
uv sync --extra training                       # 1. GPU deps

# 2. Pick the annotation batch (coverage-balanced) from the preprocessed corpus
uv run python scripts/sample_for_labeling.py   # → batch for Label Studio (05_M1_1)

#    …annotate in Label Studio → adjudicate → export gold_standard.csv (Phase 3c)…

# 3. Build temporal splits from the gold export
uv run python -m m1.model.data --in gold_standard.csv \
    --out datasets/m1_regulations/ --ratios 0.70 0.15 0.15

# 4. Train — 3 seeds, gate ≥0.92 (writes model_registry.json{gate_pass})
uv run python -m m1.model.train_xlmr --data datasets/m1_regulations \
    --seeds 42 1 2 --base xlm-roberta-base --lora-r 16 --epochs 8 --fp16 \
    --out storage/models/m1/xlmr_lora_v1

# 5. LoRA r×alpha ablation (05_M1_3) — sweep --lora-r (and alpha via config),
#    compare test_macro_f1_mean across runs; pick the smallest r meeting the gate.
#    (Run step 4 repeatedly with different --lora-r; optional: a tiny sweep wrapper.)

# 6. Slice / held-out evaluation (SI/TA, extraction-method, per-category)
uv run python -m m1.model.eval  --data datasets/m1_regulations --model storage/models/m1/xlmr_lora_v1

# 7. Export ONNX (+ INT8) and drop the artifact where the serving path looks
uv run python -m m1.model.export_onnx --model storage/models/m1/xlmr_lora_v1 \
    --out storage/models/m1/baseline/   # serving artifact location

# 8. (optional) canary promotion / rollback
uv run python scripts/retrain.py ...   # promotion.py logic
```

Then the backend side (already built): `classifier_status()` flips to `ready`, `classify_gazette` starts writing `change_category` with `classification_source='model'`, and low-confidence rows land in the classifier-review queue for expert override. This is the **interim-evaluation** milestone.

## 4. Any coding still needed? — minimal, verify these two

1. **Gold export glue.** `data.py` reads a `gold_standard.csv`. Confirm there's a step that produces it from Label Studio / the expert-verified DB rows (`change_category` where `expert_verified` / `classification_source='expert'`). If not present, it's a ~small export query/script — the only plausibly-missing code, and trivial.
2. **Ablation convenience (optional).** The r×alpha sweep (05_M1_3) is run by repeating step 4 with different `--lora-r`; a ~20-line wrapper that loops the grid and tabulates `test_macro_f1_mean` would be nice-to-have, not required.

Everything else in doc 05 is implemented.

## 5. Docs updated

- `AI_WORK_LOG.md` — session entry.
- (No source doc 05 change — code already matches the design.)

## 6. Verification

1. `cd enigmatrix-ml && uv run python -c "import m1.model.architecture"` under the `training` extra imports clean (torch/peft resolve).
2. `uv run pytest tests/m1/model/test_architecture.py`.
3. Dry-run steps 3–4 on a tiny hand-labeled CSV (even 30 rows) to confirm the split→train→registry path runs end-to-end before the real gold set is ready.
4. After a real run: `model_registry.json` shows `gate_pass:true`, `test_macro_f1_mean ≥ 0.92`; `app.m1.health` classifier → `ready`.
