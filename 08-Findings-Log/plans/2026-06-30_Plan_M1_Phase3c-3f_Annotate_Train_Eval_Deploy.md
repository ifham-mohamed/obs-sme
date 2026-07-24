---
tags: [m1, phase-3, plan, classifier, annotation, xlm-roberta, lora, onnx]
date: 2026-06-30
author: Mohamed M.R.I (215075J) — Module 1 owner
session: 62
status: 🟡 ready-to-execute — continues Session 61 (Phase 3a/3b done); covers 3c–3f
features: F-221 (this plan) · F-222 (3c) · F-223 (3d) · F-224 (3e) · F-225 (3f)
---

# M1 Phase 3c–3f — Annotate → Train → Eval → Deploy (the RQ1 classifier)

> **Goal:** finish the regulatory-change classifier RQ1 is named after — a multilingual (EN/SI/TA) model labelling each gazette into the **12-category** change taxonomy + **10-sector** multi-label, reaching **macro-F1 ≥ 0.92**, exported to ONNX and wired into the Celery pipeline (`preprocessed → classified`).
>
> Phase 3a/3b are already done (Session 61). This plan covers only the remaining steps.

## Starting point (Session 61 — already shipped, do NOT rebuild)
- `research/data/label_studio_config.xml` (F-216) — Label Studio interface; canonical **12 categories** + **10 sectors** + `is_sme_relevant` + confidence + notes.
- `research/data/calibration_set_v1.csv` (F-217) — 20 calibration docs, all 12 categories, EN/SI/TA, 4 edge cases (expert labels locked).
- `enigmatrix-ml/m1/data/samplers.py` (F-218) — `stratified_sample` + `kmeans_diversity_sample` (k=20) + `select_uncertainty_batch` (margin AL) + `sample_for_labeling`.
- `scripts/sample_for_labeling.py` (F-219) + `research/data/labeling/batch_01.csv` (F-220, **200-row demo**) + `make labeling-batch` / `labeling-batch-demo`.

---

## Step 3c — Annotate to ≥ 800 gold labels (F-222) 🔲 START HERE
**Goal:** a human-verified gold corpus, ≥ 800 docs, ≥ 50/category, IAA Cohen's κ ≥ 0.75.

1. **Produce the real batch_01** (replace the demo): `make labeling-batch` against the production DB (`DATABASE_URL` set) → real `research/data/labeling/batch_01.csv` (200 docs: 150 stratified + 40 k-means + 10 minority).
2. **Stand up Label Studio**, paste `label_studio_config.xml`, import `batch_01.csv` (heuristic `predicted_category` pre-annotations from F-219 reduce effort).
3. **Calibration round** — both annotators label `calibration_set_v1.csv`; gate **κ ≥ 0.80** vs the locked `expert_change_category` (Artstein & Poesio threshold). If below, refine edge-case guidance (09 §6.1) and re-run.
4. **Scale with active learning** — once a baseline exists, generate `batch_02..N` via `select_uncertainty_batch` (lowest-margin first); dual-annotate a 15% overlap each batch to keep tracking κ. Over-sample rare canonical domains (e.g. `PENALTY_ENFORCEMENT`, `BUSINESS_REGISTRATION`).
5. **Freeze + split** — export `gold_standard.csv`; temporal 70/15/15 split by `gazette_published_date` (test = latest dates, no leakage) → `enigmatrix-ml/datasets/m1_regulations/{train,val,test}.parquet`.

**DoD:** κ ≥ 0.75 on the dual-annotated subset; `gold_standard.csv` ≥ 800 rows, ≥ 50/category, all 12 present; temporal splits with no date leakage.

**Commands**
```bash
cd C:\Reasearch\xyz\enigmatrix-backend && make labeling-batch                 # real batch_01 (needs DATABASE_URL)
pip install label-studio && label-start                                       # paste config, import batch_01.csv
# Cohen's kappa on a dual-annotated export (cols: cat_A, cat_B)
python -c "import pandas as pd;from sklearn.metrics import cohen_kappa_score;d=pd.read_csv('dual.csv');print(round(cohen_kappa_score(d.cat_A,d.cat_B),3))"
cd ..\enigmatrix-ml && uv run python -m m1.data.make_splits --in datasets/m1_regulations/gold_standard.csv --out datasets/m1_regulations/ --ratios 0.70 0.15 0.15 --by gazette_published_date
```

---

## Step 3d — Model package + XLM-R + LoRA training (F-223) 🔲
**Goal:** train the dual-head classifier to macro-F1 ≥ 0.92 over a 3-seed temporal-split run.

**Create `enigmatrix-ml/m1/model/`:** `config.py` · `architecture.py` (GazetteClassifier: XLM-R encoder + LoRA `r=16,alpha=32,target=["query","value"]` + 12-cat softmax head + 10-sector sigmoid head) · `train_xlmr.py` (3 seeds {42,1,2}, AdamW, warmup 10%, early-stop on val macro-F1, FP16, weighted CE + back-translation ≤5× on minority, train-only) · `model_registry.json` writer.

**DoD:** 3-seed mean macro-F1 ≥ 0.92; EN ≥ 0.93 / SI ≥ 0.88 / TA ≥ 0.86; reproducibility hash recorded. Start with the LoRA ablation `r ∈ {8,16,32}` on the first 300 labels to sanity-check the loop.

**Commands**
```bash
cd C:\Reasearch\xyz\enigmatrix-ml && uv sync --extra ml
uv run pytest tests/m1/model -v                                               # shape/config tests (no GPU)
uv run python -m m1.model.train_xlmr --data datasets/m1_regulations --seeds 42 1 2 --base xlm-roberta-base --lora-r 16 --epochs 8 --fp16 --out storage/models/m1/xlmr_lora_v1
```

---

## Step 3e — Evaluation, slices & baselines (F-224) 🔲
**Build `m1/model/eval.py`** — macro-F1 per **language / quarter / text-length / extraction-method**; **baselines** TF-IDF+LR, TF-IDF+SVM, zero-shot LLM (same test split — the comparison is itself a finding); reliability diagram + 4-type error taxonomy (`error_analysis_topwrong.csv`).

**DoD:** `metrics.json` shows macro-F1 ≥ 0.92, per-language gates met, **no slice cliff > 8 pp** below aggregate; baseline table; error dump saved.

```bash
uv run python -m m1.model.eval --model storage/models/m1/xlmr_lora_v1 --test datasets/m1_regulations/test.parquet --report storage/models/m1/eval_v1
uv run python -m m1.model.baselines --data datasets/m1_regulations --report storage/models/m1/baselines_v1
```

---

## Step 3f — ONNX export + inference wiring + deploy (F-225) 🔲
1. **Export** `m1/model/export_onnx.py` → ONNX + INT8 (verify within **1.5 pp** of FP32).
2. **Inference** `m1/model/inference.py` (ONNX Runtime CPU) → `classify(text)`.
3. **Backend** `app/services/module1/classifier.py` (loads production model from `model_versions`; confidence `< 0.55` → `needs_review`) + `app/tasks/m1/classify_gazette.py` (chained after `preprocess_gazette`; writes `change_category` + `affected_sectors[]` + `confidence`; status `preprocessed → classified`).
4. **Migration** — extend status enum with `classified`; add `classifier_confidence`. **Deploy** to Fly (`sin`), `M1_MODEL_VERSION=v1.0`; stage `lid.176.bin` + pre-warm the `xlm-roberta-base` tokenizer in the worker Dockerfile.

**DoD:** INT8 within 1.5 pp of FP32, p95 ≤ 2 s; integration test takes a `preprocessed` row → `classified`; low-confidence → `needs_review`; a fresh crawled gazette auto-classifies.

```bash
cd C:\Reasearch\xyz\enigmatrix-ml && uv run python -m m1.model.export_onnx --model storage/models/m1/xlmr_lora_v1 --out storage/models/m1/onnx/v1 --int8
cd ..\enigmatrix-backend && uv run alembic revision -m "m1_classified_status_and_confidence" && uv run alembic upgrade head
uv run pytest app/tests/integration/test_celery_classify_gazette.py -v
```

---

## Risks / open questions
- **SI/TA text quality** — Sinhala `raw_text` shows `(cid:…)` font artifacts; re-extract clean SI/TA (OCR + Wijesekara path) before building the gold text, or SI/TA F1 (RQ2) collapses.
- **F1-gate inconsistency** — BUILD_11 enforces `f1_macro ≥ 0.80`, RQ1 publishes ≥ 0.92. Reconcile to **0.92**.
- **Class imbalance / missing categories** — the silver corpus is `procedural`-heavy; some canonical categories have ~0 examples. Source more gazettes for the missing domains; over-sample + augment.
- **GPU** — use Colab/Kaggle/Fly A10 for the 3-seed run; CPU only for unit tests + ONNX inference.

## Cross-references
- Roadmap: [06-Timeline/02_Module1_Roadmap.md](../../06-Timeline/02_Module1_Roadmap.md) §Phase 3 (3c/3d/3e/3f).
- Specs: [BUILD_11_ML_Training_Pipeline](../../04-Technology-Stack/ml/BUILD/BUILD_11_ML_Training_Pipeline.md) · [BUILD_07_Module1_Awareness](../../04-Technology-Stack/backend/BUILD/BUILD_07_Module1_Awareness.md).
- Design: [05_M1_Model_Architecture](../../02-Research-Modules/1%20Module-1-Awareness-Gap/05_M1_Model_Architecture.md) · [06_M1_Training_Evaluation](../../02-Research-Modules/1%20Module-1-Awareness-Gap/06_M1_Training_Evaluation.md) · [09_M1_Annotation_Guidelines](../../02-Research-Modules/1%20Module-1-Awareness-Gap/09_M1_Annotation_Guidelines.md).
- Predecessor: Session 61 (Phase 3a/3b) — F-216–F-220.
