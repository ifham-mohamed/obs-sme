# ML Domain

PyTorch · HuggingFace Transformers (XLM-RoBERTa) · scikit-learn · XGBoost / LightGBM · MLflow · Optuna · SHAP · RAGAS · SDV

## Implementation status

| Module            | ML component                                              | Status                                                          |
| ----------------- | --------------------------------------------------------- | --------------------------------------------------------------- |
| M1 Awareness      | XLM-R 12-class regulatory classifier + gazette scraper    | **Pending** — BUILD_07 not started                              |
| M2 Knowledge      | Auto-scoring engine (rule-based, 5 formats)               | **Delivered** — lives in `backend/` (`m2_scoring.py`)           |
| M2 Knowledge      | ChromaDB RAG pipeline + RAGAS eval                        | **Pending** — BUILD_08 not started                              |
| M3 Vulnerability  | XGBoost/LightGBM risk model + SHAP                        | **Pending** — data capture live; model needs ≥200 response rows |
| M4 Misinformation | 9-way veracity classifier + social scrapers               | **Stub only** — BUILD_10 not started                            |
| Shared            | MLflow model registry + Optuna sweeps + training pipeline | **Pending** — BUILD_11 not started                              |

> The M2 auto-scoring engine (`m2_scoring.py`) and M3 data capture (`m3_compliance_history`, `m3_behavioural_signals` tables, dual-snapshot projection) are **already live** in the backend. Documents in this domain cover the pending ML model training work.

## Build order (pending work)

```
BUILD_11 (shared training pipeline) → BUILD_07 (M1 XLM-R) → BUILD_09 (M3 XGBoost) → BUILD_10 (M4 classifier)
                                                           ↘ BUILD_08 (M2 ChromaDB RAG)
```

## Files

### BUILD_PLAN/
| File | Description |
|------|-------------|
| [BUILD_11_ML_Training_Pipeline.md](BUILD_PLAN/BUILD_11_ML_Training_Pipeline.md) | Shared training infra: dataset versioning, MLflow tracking, Optuna sweeps, eval gates per module |

### research/ — Methodology
| File | Description |
|------|-------------|
| [01_AI_ML_Fundamentals.md](research/01_AI_ML_Fundamentals.md) | What is a model, loss functions, backprop, fine-tuning vs training from scratch |
| [02_Complete_ML_Lifecycle.md](research/02_Complete_ML_Lifecycle.md) | 9-stage pipeline: problem framing → data → labeling → training → eval → deploy → monitor |
| [11_Module1_NLP_Classifier_Training.md](research/11_Module1_NLP_Classifier_Training.md) | 12-way regulatory taxonomy (TAX_INCOME, TAX_VAT_SVAT, EPF_ETF…), XLM-R training harness |
| [13_Module2_Knowledge_Architecture.md](research/13_Module2_Knowledge_Architecture.md) | Compliance knowledge as latent construct; three-instrument design; psychometric validity |
| [14_Module3_Risk_Architecture.md](research/14_Module3_Risk_Architecture.md) | Feature taxonomy (firmographic, behavioral, sectoral, M1-exposure, M2-knowledge); gradient-boosted trees |
| [15_Module4_Misinformation_Architecture.md](research/15_Module4_Misinformation_Architecture.md) | 9-way veracity taxonomy; misleading mechanics; claim-check tool design (target spec) |
| [module_4_data_collection.md](research/module_4_data_collection.md) | M4 data sources: Twitter/X, Reddit, Facebook, YouTube, WhatsApp — dedup via content_hash |
| [module_4_perplexity_prompt.md](research/module_4_perplexity_prompt.md) | Perplexity AI prompt for M4 source research |
| [module_4_sri_lankan_sources.md](research/module_4_sri_lankan_sources.md) | Sri Lankan social media groups, Twitter accounts, fact-check platforms (FactCheck.lk) |
