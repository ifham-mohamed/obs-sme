# Phase 3 · Classification — Doc-05 Model: Code Status & Training Runbook

> Group: `PHASE3_ANNOTATION_CLASSIFICATION / classifier_model_training`. Covers docs 05_M1_1/2/3 (+ 06 training/eval). Companion to [[PHASE3_GAP_CLOSURE_PLAN]] and the program-level [[M1_NON_CODING_TASKS_AND_GOLIVE_READINESS_PLAN]].
> **Verdict (updated 2026-07-30): the code for doc 05 is essentially COMPLETE, and the v1 gold/split/baseline/smoke preparation is now done.** What's missing to reach a trained, serving model is *not code* — it is the rare-domain decision, a CUDA/GPU machine for the full LoRA run, final evaluation, and ONNX export. Details below, command-level.

## 1. Is the code done? — Yes. Module map (all present in `enigmatrix-ml/m1/`)

| Doc / concern | Module | State |
|---|---|---|
| 05_M1_1 Sampling (stratified → k-means k=20 → active-learning + minority hand-picks) | `m1/data/samplers.py` + `scripts/sample_for_labeling.py` | **implemented** (constants match doc: `OPTIMAL_K=20`, thresholds, `CATEGORIES_12`) |
| 05_M1_2 Architecture comparison (4-way) | `m1/model/baselines.py` | **implemented** (baselines for the comparison) |
| 05 Architecture (XLM-R + LoRA + dual heads) | `m1/model/architecture.py` | **implemented** — `AutoModel` + `get_peft_model(LoraConfig(...))`, 12-way category (CE) + 10-way sector (BCE) heads |
| 05_M1_3 LoRA hyperparameters (r, alpha, target_modules, bias="none") | `m1/model/config.py` (`ModelConfig`) + `--lora-r` flag | **implemented** — `bias="none"`, `task_type=FEATURE_EXTRACTION`, configurable r/alpha/targets |
| 06 Gold loading + split | `m1/model/data.py` | **implemented and run for v1** — reads CSV/parquet gold export; current split uses deterministic `--by key` because reliable dates are absent |
| Label vocab | `m1/model/labels.py` | **implemented** (`encode_category`/`encode_sectors`/`parse_sectors`) |
| 06 Training (3-seed, early stop, ≥0.92 gate) | `m1/model/train_xlmr.py` | **implemented** — AdamW + warmup, AMP/fp16, best-val checkpoint, writes `model.pt` + `model_registry.json` with `gate_pass` |
| Slice / held-out eval | `m1/model/eval.py` | **implemented** |
| ONNX export (+ serving) | `m1/model/export_onnx.py`, `m1/model/inference.py` | **implemented** |
| Canary promotion / rollback | `m1/model/promotion.py`, `scripts/retrain.py` | **implemented** |
| Deps | `pyproject.toml` `training` extra (torch, peft, transformers, scikit-learn, onnxruntime) | **declared** |
| Test | `tests/m1/model/test_architecture.py` | present |

So there is **nothing to build** for doc 05 in the normal case. The classifier is `no_model` because no full GPU-trained ONNX artifact has been exported yet. The code has now been exercised through split creation, TF-IDF baselines, and a CPU LoRA smoke run.

## 2. What's needed apart from coding (the real blockers)

1. **A GPU host** with the training extra: `cd enigmatrix-ml && uv sync --extra training --extra research` (torch/peft/transformers/onnxruntime + parquet/research dependencies; ~GBs, CUDA). The rest of the stack stays torch-free.
2. **Rare-domain decision.** The v1 gold set exists, but `EPF_ETF_CHANGE=0`, `PRODUCT_STANDARD=4`, `BUSINESS_REGISTRATION=5`, and `PENALTY_ENFORCEMENT=5`. Either collect a rare-domain top-up or state this limitation before final model claims.
3. **Compute time + iteration** — 3 seeds × 8 epochs on XLM-R-base; the LoRA ablation adds a few more runs.

## 3. The full sequence — exactly how to do it (command-level)

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml
uv sync --extra training --extra research      # 1. GPU + parquet/research deps

# 2. Existing v1 evidence, already created
# C:\Reasearch\xyz\research\data\labeling\gold_standard_v1_800.csv
# C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations\{train,val,test}.parquet
# C:\Reasearch\xyz\storage\models\m1\baselines_v1\baselines.json
# C:\Reasearch\xyz\enigmatrix-ml\datasets\m1_regulations_smoke\{train,val,test}.parquet
# C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model_registry.json

# Smoke clarification:
# - full-split CPU attempt used datasets\m1_regulations and wrote no registry; not counted
# - valid tiny smoke used datasets\m1_regulations_smoke with train=16, val=8, test=8
# - tiny smoke wrote model_registry.json and model.pt with gate_pass=false

# 3. Rebuild the deterministic v1 split only if needed
uv run --extra research python -m m1.model.data `
  --in ..\research\data\labeling\gold_standard_v1_800.csv `
  --out datasets\m1_regulations `
  --by key

# 4. Re-run baselines only if the split or gold file changed
uv run --extra training --extra research python -m m1.model.baselines `
  --data datasets\m1_regulations `
  --report ..\storage\models\m1\baselines_v1

# 5. Train — 3 seeds, gate >=0.92 (writes model_registry.json{gate_pass})
uv run --extra training --extra research python -m m1.model.train_xlmr `
  --data datasets\m1_regulations `
  --seeds 42 1 2 `
  --base xlm-roberta-base `
  --lora-r 16 `
  --epochs 8 `
  --fp16 `
  --out ..\storage\models\m1\xlmr_lora_v1

# 6. LoRA r×alpha ablation (05_M1_3) — sweep --lora-r (and alpha via config),
#    compare test_macro_f1_mean across runs; pick the smallest r meeting the gate.
#    (Run step 4 repeatedly with different --lora-r; optional: a tiny sweep wrapper.)

# 7. Slice / held-out evaluation (SI/TA, extraction-method, per-category)
uv run --extra training --extra research python -m m1.model.eval `
  --data datasets\m1_regulations `
  --model ..\storage\models\m1\xlmr_lora_v1

# 8. Export ONNX (+ INT8) only if full training/eval gates pass
uv run --extra training --extra serving python -m m1.model.export_onnx `
  --model ..\storage\models\m1\xlmr_lora_v1 `
  --out ..\storage\models\m1\onnx\v1

# 9. (optional) canary promotion / rollback
uv run --extra training python scripts\retrain.py ...   # promotion.py logic
```

Then the backend side (already built): `classifier_status()` flips to `ready`, `classify_gazette` starts writing `change_category` with `classification_source='model'`, and low-confidence rows land in the classifier-review queue for expert override. This is the **interim-evaluation** milestone.

## 4. Any coding still needed? — minimal, verify these two

1. **Gold export glue — done.** `scripts/resolve_iaa.py` produces `gold_standard.csv`, IAA reports, disagreement rows, and uses `manual_resolutions.csv`.
2. **Ablation convenience (optional).** The r×alpha sweep (05_M1_3) is run by repeating the full training command with different `--lora-r`; a small wrapper that loops the grid and tabulates `test_macro_f1_mean` would be nice-to-have, not required.

Everything else in doc 05 is implemented.

## 5. Docs updated

- `AI_WORK_LOG.md` — session entry.
- `05_M1_Model_Architecture.md`, `06_M1_Training_Evaluation.md`, and Program Readiness docs now record the v1 gold/split/baseline/smoke state.

## 6. Verification

1. `cd enigmatrix-ml && uv run python -c "import m1.model.architecture"` under the `training` extra imports clean (torch/peft resolve).
2. `uv run pytest tests/m1/model/test_architecture.py`.
3. CPU smoke already verified the split→train→registry path on `datasets\m1_regulations_smoke`; keep it as an engineering artifact only.
4. After a real full GPU run: `model_registry.json` shows `gate_pass:true`, `test_macro_f1_mean ≥ 0.92`; `app.m1.health` classifier → `ready` after ONNX export and `M1_MODEL_ONNX_DIR` activation.
