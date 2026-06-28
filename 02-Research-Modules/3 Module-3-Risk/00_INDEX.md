---
tags: [meta, module-3, index]
source: synthesised
layer: meta
module: m3
---

# Module 3 — Regulatory Risk Scoring (Index)

> Predict an SME's regulatory non-compliance risk score, with SHAP-based explanations, from sector, size, historical penalties, disclosure features, and the M1 alert-engagement record.

## Contents

| # | File | What it covers |
|---|---|---|
| 01 | [01_Module3_Risk_Architecture](01_Module3_Risk_Architecture.md) | Research methodology — features, model (XGBoost/LightGBM), evaluation (AUROC, calibration), SHAP explainability, fairness checks |
| 02 | [02_BUILD_Module3_Risk](02_BUILD_Module3_Risk.md) | Engineering build plan — API surface, scoring service, model registry, deployment |
| 03 | [03_Data_Architecture_M2_M3](03_Data_Architecture_M2_M3.md) | Shared data architecture for Modules 2 + 3 (regulatory KB tables, SME features, score history) |

## Research questions

- **RQ-M3.1** — Can a gradient-boosting model predict an SME's regulatory non-compliance risk score with AUROC ≥ 0.80?
- **RQ-M3.2** — Do SHAP-based explanations change SME compliance behaviour relative to an unexplained score?

## Status

🔲 Architecture designed; training data not yet collected. M1 outputs (regulation timestamps, enforcement records) feed feature engineering for M3.

## See also

- [Module 1 deep-dive](../1%20Module-1-Awareness-Gap/00_INDEX.md) — provides the regulation corpus and SME engagement signal
- [BUILD Master Index](../../00-Meta/BUILD_Master_Index.md)
- [Research Master Index](../../00-Meta/Research_Master_Index.md)
