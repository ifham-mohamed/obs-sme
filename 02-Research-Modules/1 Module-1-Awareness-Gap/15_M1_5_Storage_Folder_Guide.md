# 15_M1_5 — `storage/` Folder Build Guide

> Companion to [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) — build guide for the `storage/` slice of doc 13's M1 tree.
> **Implementation status snapshot:** 🟡 Conventions documented; directories populate as Phase 2 (PDFs/OCR cache) + Phase 3 (model artifacts) run.

## Purpose

`storage/` is the on-disk artifact store — raw PDFs the scraper downloads, OCR caches, the inference cache mirror, and the versioned ONNX model files. Everything here is *operational state*: gitignored except for the `model_registry.json` manifests (small + version-controlled for reproducibility). On Fly.io, the production mount is a persistent volume; locally, it's the repo `storage/` directory.

## Files in this folder

### `storage/m1/`

| Path | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `m1/raw/` | Downloaded gazette PDFs, keyed by `gazette_number` | 🔲 | [03_M1_Data_Collection.md](03_M1_Data_Collection.md) + [02_M1_3_Data_Governance_Retention.md](02_M1_3_Data_Governance_Retention.md) | `scraper/pipelines.py` writes here; S3 lifecycle moves > 2y to Glacier |
| `m1/ocr_cache/` | Tesseract output keyed by `SHA-256(image_bytes)` | 🔲 | [03_M1_1_PDF_Extraction_Chain.md](03_M1_1_PDF_Extraction_Chain.md) | Idempotent — re-running OCR returns cached result; TTL 30 days |
| `m1/inference_cache/` | Redis dump (operational; not authoritative) | 🔲 | [07_M1_Deployment_Integration.md §3.2](07_M1_Deployment_Integration.md) | Local backup of the Redis cache for cold-start warming |

### `storage/models/m1/`

| Path | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `models/m1/v1.0/gazette_classifier.onnx` | Production FP32 ONNX model | 🔲 | [07_M1_1_ONNX_Export_Quantization.md](07_M1_1_ONNX_Export_Quantization.md) | Produced by `ml/m1/model/export_onnx.py` |
| `models/m1/v1.0/gazette_classifier_int8.onnx` | INT8-quantized variant (2× speedup) | 🔲 | [07_M1_1 §INT8](07_M1_1_ONNX_Export_Quantization.md) | Produced by `quantize_onnx.py`; F1 within 1.5pp of FP32 |
| `models/m1/v1.0/adapter_model.bin` | LoRA adapter weights (for retraining) | 🔲 | [05_M1_3_LoRA_Hyperparameter_Justification.md](05_M1_3_LoRA_Hyperparameter_Justification.md) | PEFT's `save_pretrained()` output (~10MB; never overwrite) |
| `models/m1/v1.0/tokenizer/` | XLM-R SentencePiece tokenizer (frozen) | 🔲 | [05_M1_Model_Architecture.md §4.2](05_M1_Model_Architecture.md) | Copied from `facebook/xlm-roberta-base` at training time |
| `models/m1/v1.0/model_registry.json` | Reproducibility fingerprint | 🔲 | [06_M1_Training_Evaluation.md §reproducibility hash](06_M1_Training_Evaluation.md) | **Committed to git** (small JSON); contains git SHA + data SHA-256 + env.yml hash + per-language F1 |
| `models/m1/v1.0/metrics.json` | Per-language F1 + confusion matrix + ECE | 🔲 | [06_M1_Training_Evaluation.md §4](06_M1_Training_Evaluation.md) | **Committed to git**; consumed by monitoring dashboard |
| `models/m1/v0.9/` | Previous version (rollback target) | 🔲 | [07_M1_2_Fly_io_Deployment_Operations.md §rollback](07_M1_2_Fly_io_Deployment_Operations.md) | Always kept on the Fly volume for ~60s rollback |
| `models/m1/baseline/tfidf_lr_model.pkl` | Production-baseline TF-IDF + LR | 🔲 | [05_M1_2_Architecture_Comparison_Deep_Dive.md](05_M1_2_Architecture_Comparison_Deep_Dive.md) | Trained on the full labelled set; used for ablation only |
| `models/m1/baseline/vocabulary.pkl` | Baseline's vocabulary | 🔲 | Same | Companion to `tfidf_lr_model.pkl`; pickle for reproducibility |

## How to start building

This folder is **mostly conventions** — directories appear as Phase 2 + Phase 3 run. The build work is *setting up the conventions* + *enforcing them in CI*.

1. **Create the directory tree.** `mkdir -p storage/m1/{raw,ocr_cache,inference_cache} storage/models/m1/{baseline,v1.0}`. Add `.gitkeep` files so empty dirs are tracked.
2. **`.gitignore` setup.** Add `storage/m1/raw/`, `storage/m1/ocr_cache/`, `storage/m1/inference_cache/`, `storage/models/m1/v*/*.onnx`, `storage/models/m1/v*/adapter_model.bin`, `storage/models/m1/v*/tokenizer/` to gitignore. The only things that ARE tracked: `model_registry.json` + `metrics.json` files (small, reproducibility-critical).
3. **S3 lifecycle config.** Per [02_M1_3 §Step 4](02_M1_3_Data_Governance_Retention.md), commit `infra/aws/s3_m1_lifecycle.yaml`. AWS CLI applies the rules; CI asserts byte-equality with the committed YAML.
4. **Fly volume.** `fly volumes create ml_models --size 3 --region sin` once Phase 3 ships the first ONNX. Volume mounted at `/app/storage/models/` per [07_M1_2 §fly.toml](07_M1_2_Fly_io_Deployment_Operations.md).
5. **Model versioning convention.** When Phase 3's training pipeline lands, every `model_registry.json` must include: `model_version` (semver), `trained_at` (ISO), `git_commit_sha`, `dataset.labeled_set_sha256`, `dataset.split_boundaries`, `environment.python` + `torch` + `transformers` + `peft` + `onnxruntime` versions, `training.seeds` + `final_macro_f1_mean` + `final_macro_f1_std`, `metrics_per_language`. See [06_M1_Training_Evaluation.md §reproducibility hash](06_M1_Training_Evaluation.md) for the full schema.
6. **Backup + retention.** `storage/m1/raw/` PDFs > 2y old auto-migrate to Glacier (S3 lifecycle). Local repo dev: just rely on the lifecycle; don't try to delete locally.

The two committed files per model version (`model_registry.json` + `metrics.json`) are the *only* things from this folder that ship in the docs/PR review. Everything else is operational.

## Dependencies

- **`scraper/pipelines.py`** ([15_M1_3_Scraper_Folder_Guide.md](15_M1_3_Scraper_Folder_Guide.md)) — writes to `storage/m1/raw/`.
- **`ml/m1/extraction/ocr.py`** ([15_M1_1_ML_Folder_Guide.md](15_M1_1_ML_Folder_Guide.md)) — reads/writes `storage/m1/ocr_cache/`.
- **`ml/m1/model/inference.py`** ([15_M1_1_ML_Folder_Guide.md](15_M1_1_ML_Folder_Guide.md)) — reads `storage/models/m1/v<X>/*.onnx`.
- **`ml/m1/model/training.py`** + `export_onnx.py` ([15_M1_1_ML_Folder_Guide.md](15_M1_1_ML_Folder_Guide.md)) — writes the entire `storage/models/m1/v<X>/` tree.
- **AWS S3** — Glacier lifecycle for raw PDFs > 2 years old.
- **Fly.io persistent volume** — mounts production model files at `/app/storage/models/`.

## Tests & acceptance criteria

- **Gitignore correctness.** `git status` after a clean checkout + Phase 2 run shows ZERO untracked files under `storage/m1/raw/` etc. (they're gitignored). CI test: spider produces PDFs locally; `git status --porcelain storage/` is empty.
- **`model_registry.json` validity.** Every committed `model_registry.json` matches `ml/m1/schema/manifest.py`'s Pydantic schema. CI test on every PR.
- **No model files committed by accident.** CI fails any PR that adds `*.onnx`, `adapter_model.bin`, or files under `tokenizer/` to git. Pre-commit hook enforces.
- **S3 lifecycle in sync.** `aws s3api get-bucket-lifecycle-configuration --bucket enigmatrix-m1-pdfs` byte-matches `infra/aws/s3_m1_lifecycle.yaml`. Drift detection in monitoring.
- **Rollback works.** Quarterly drill: flip `M1_MODEL_VERSION=v<previous>` on staging → confirm previous model serves traffic correctly → `< 60s` end-to-end.

## Cross-references

- Folder map spec: [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md)
- Roadmap: [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md) §Phase 3 (model artifacts ship) + §Phase 2 (PDFs land)
- Reproducibility: [06_M1_Training_Evaluation.md §reproducibility hash](06_M1_Training_Evaluation.md)
- ONNX export: [07_M1_1_ONNX_Export_Quantization.md](07_M1_1_ONNX_Export_Quantization.md)
- Fly deployment: [07_M1_2_Fly_io_Deployment_Operations.md](07_M1_2_Fly_io_Deployment_Operations.md)
- Retention + S3 lifecycle: [02_M1_3_Data_Governance_Retention.md](02_M1_3_Data_Governance_Retention.md)
- Sibling folders: [15_M1_1_ML_Folder_Guide.md](15_M1_1_ML_Folder_Guide.md), [15_M1_3_Scraper_Folder_Guide.md](15_M1_3_Scraper_Folder_Guide.md)
