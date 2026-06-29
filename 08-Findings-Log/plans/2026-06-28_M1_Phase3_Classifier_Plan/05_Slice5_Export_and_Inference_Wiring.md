---
tags: [m1, phase-3, slice-5, onnx, inference, celery, deployment]
date: 2026-06-28
status: 🔲 blocked-by Slice 4
---

# Slice 5 — ONNX export + inference wiring (close the loop)

## Purpose
Make the model *operational*: export to ONNX (INT8), serve on CPU, and wire it into the Celery pipeline so every freshly-preprocessed gazette auto-classifies (`preprocessed → classified`). This is what flips RQ1 from "trained model" to "running system."

## Prerequisites
- A passing model + eval from Slices 3–4. The backend `m1_regulations` table already has `change_category` + status columns.

## Steps
1. **Export** — `m1/model/export_onnx.py`: torch → ONNX → INT8 dynamic quantization; verify INT8 macro-F1 within **1.5 pp** of FP32.
2. **Inference engine** — `enigmatrix-ml/m1/model/inference.py`: load ONNX (ONNX Runtime CPU), `classify(text) -> {category, confidence, sector_probs}`; cache the session.
3. **Backend service** — `enigmatrix-backend/app/services/module1/classifier.py` (per BUILD_07): loads the production model from `model_versions`; confidence `< 0.55` → `needs_review`.
4. **Celery task** — `enigmatrix-backend/app/tasks/m1/classify_gazette.py`: chained after `preprocess_gazette`; writes `change_category` + `affected_sectors[]` + `confidence`; flips status `preprocessed → classified`.
5. **Migration** — extend the `status` CHECK enum with `classified`; add `classifier_confidence`, `affected_sectors` if not present.
6. **Deploy** — ship the ONNX model with the worker image; **stage `lid.176.bin` + pre-warm the `xlm-roberta-base` tokenizer in the Dockerfile** (open Phase-2 follow-up). Fly.io `sin` region per doc 07; `M1_MODEL_VERSION=v1.0`.

## Commands
```bash
# export
cd enigmatrix-ml && uv run python -m m1.model.export_onnx \
    --model storage/models/m1/xlmr_lora_v1 --out storage/models/m1/onnx/v1 --int8
# wire + migrate (backend)
cd ../enigmatrix-backend && uv run alembic revision -m "m1_classified_status_and_confidence" && uv run alembic upgrade head
# smoke: classify one preprocessed row end-to-end (eager Celery)
uv run pytest app/tests/integration/test_celery_classify_gazette.py -v
```

## Tests / DoD
- ONNX INT8 within 1.5 pp of FP32; p95 latency ≤ 2 s on `shared-cpu-1x`.
- Integration test: a `preprocessed` row → task → `classified` with non-null `change_category` + `confidence`; low-confidence → `needs_review`.
- A fresh gazette crawled in dev lands at `status='classified'` with sectors populated.

## Does NOT do
No summarisation/alerts (that's Phase 4 — separate plan). No retraining automation (Phase 5).

## Cross-refs
[BUILD_07_Module1_Awareness](../../../04-Technology-Stack/backend/BUILD/BUILD_07_Module1_Awareness.md) · [07_M1_1_ONNX_Export_Quantization] · [07_M1_Deployment_Integration](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/07_M1_Deployment_Integration.md)
