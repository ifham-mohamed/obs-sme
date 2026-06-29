---
tags: [m1, phase-3, slice-4, evaluation, slices, baselines]
date: 2026-06-28
status: 🔲 blocked-by Slice 3
---

# Slice 4 — Evaluation, slice analysis & baselines

## Purpose
Prove the model is honestly ≥ 0.92 and robust — not just on aggregate but on every slice — and establish the baselines that make the result a *research finding*.

## Prerequisites
- A trained model from Slice 3 + the held-out `test.parquet`.

## Steps
1. **Baselines** (the comparison IS a finding — no prior baseline exists for SL regulatory text): TF-IDF + Logistic Regression, TF-IDF + Linear SVM, and a zero-shot LLM. Same test split, same macro-F1.
2. **Slice analysis** (`eval.py`): macro-F1 broken down per **language (EN/SI/TA)**, per **year-quarter**, per **text-length bucket**, per **extraction-method** (`pymupdf|pdfplumber|tesseract`). Gate: **no slice cliff > 8 pp** below the aggregate.
3. **Calibration + confidence**: reliability diagram; verify monotonic accuracy by confidence bucket; pick the review-queue threshold (default 0.55).
4. **Error taxonomy**: dump `error_analysis_topwrong.csv` (true vs pred + text) and bucket the top errors into a 4-type taxonomy (doc 06).

## Commands
```bash
cd enigmatrix-ml
uv run python -m m1.model.eval --model storage/models/m1/xlmr_lora_v1 \
    --test datasets/m1_regulations/test.parquet --report storage/models/m1/eval_v1
uv run python -m m1.model.baselines --data datasets/m1_regulations --report storage/models/m1/baselines_v1
```

## Tests / DoD
- `eval_v1/metrics.json` shows macro-F1 ≥ 0.92, per-language gates met, no slice > 8 pp below aggregate.
- Baseline table produced (XLM-R beats TF-IDF baselines by a reported margin).
- `error_analysis_topwrong.csv` + reliability diagram saved.

## Does NOT do
No serving/export (Slice 5).

## Cross-refs
[06_M1_2_Slice_Analysis_Framework] · [06_M1_Training_Evaluation](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/06_M1_Training_Evaluation.md) · next [05_Slice5_Export_and_Inference_Wiring.md](05_Slice5_Export_and_Inference_Wiring.md)
