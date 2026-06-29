---
tags: [m1, phase-3, plan, classifier, annotation, xlm-roberta, lora, onnx]
date: 2026-06-28
author: Mohamed M.R.I (215075J) — Module 1 owner
source-of-truth: this folder
status: in-execution — Slice 1 ✅ shipped 2026-06-28; Slices 2–5 ready to execute
supersedes-handoff: 2026-05-23_M1_Phase2_Upgrade_Plan/09_Slice8_Backfill_Polish_Thesis.md (Phase-3 dataset card)
---

# M1 Phase 3 — Regulatory-Change Classifier (the RQ1 headline)

> **Goal:** turn the shipped ingest→extract→preprocess pipeline and the 500-row silver corpus into the **trained NLP classifier RQ1 is named after** — a multilingual (EN/SI/TA) model that labels each gazette into the **12-category** change taxonomy + **10-sector** multi-label schema, reaching **macro-F1 ≥ 0.92**, served via ONNX and wired into the Celery pipeline (`preprocessed → classified`).
>
> This is the unambiguous "next state of development": every roadmap (`06-Timeline/02_Module1_Roadmap.md` Phase 3), the Phase-2 Upgrade Plan's slice-8 handoff, and the trackers point here. The pipeline that *feeds* the model is done; the model is the missing piece between you and RQ1/RQ2.

## Where this starts from (verified 2026-06-28)

- **Pipeline:** ingest → extract → preprocess shipped & live on Railway (Phase 2 + Upgrade slices 1–9, in code).
- **Data:** 800 gazette PDFs; **500 distinct gazettes silver-classified** (LLM/regex, `expert_verified=False`), ~300 PDFs uncovered.
- **Critical gap surfaced:** the silver labels use a **6-label ad-hoc scheme** (`procedural_change / rate_change / other / new_obligation / registration_change / structural_change`) — **NOT** the canonical 12-category taxonomy in [09_M1_Annotation_Guidelines.md §2](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/09_M1_Annotation_Guidelines.md). A **silver→canonical-12 mapping** is required (Slice 2).
- **Model layer:** `enigmatrix-ml/m1/model/` does **not exist** yet.

## Canonical label schema (source of truth: doc 09)

**12 change categories:** `TAX_RATE_CHANGE`, `LABOUR_LAW`, `EPF_ETF_CHANGE`, `PRODUCT_STANDARD`, `BUSINESS_REGISTRATION`, `IMPORT_EXPORT`, `FINANCIAL_REGULATION`, `SECTOR_SPECIFIC`, `ENVIRONMENTAL`, `PENALTY_ENFORCEMENT`, `DEADLINE_EXTENSION`, `NO_SME_IMPACT`.
**10 sectors (multi-label):** `agriculture, manufacturing, retail, tourism, construction, services, finance, it, transport, food` (confirm against [09 §3](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/09_M1_Annotation_Guidelines.md)).

## The five slices (order to ship in)

| # | Slice | What ships | Status |
|---|---|---|---|
| 1 | [Labeling dataset prep](01_Slice1_Labeling_Dataset_Prep.md) | Dedupe silver → stratified `batch_01.csv` + Label Studio import w/ pre-annotations | ✅ **shipped 2026-06-28** |
| 2 | [Annotation + gold set](02_Slice2_Annotation_and_Gold_Set.md) | Label Studio project + silver→canonical-12 map + 2-annotator rounds → **≥800 gold labels, κ ≥ 0.75** | 🔲 next |
| 3 | [Model package + training](03_Slice3_Model_Package_and_Training.md) | `enigmatrix-ml/m1/model/` (XLM-R + LoRA dual head) + 3-seed temporal-split training | 🔲 |
| 4 | [Evaluation + slices](04_Slice4_Evaluation_and_Slices.md) | `eval.py` per-language/quarter/length slices + baselines + error taxonomy | 🔲 |
| 5 | [Export + inference wiring](05_Slice5_Export_and_Inference_Wiring.md) | ONNX/INT8 export + `classify_gazette` Celery task + `classifier.py` service + deploy | 🔲 |

Companion runbooks: **[06_Commands_and_Test_Manual.md](06_Commands_and_Test_Manual.md)** (every command + test, copy-paste) · **[07_Risks_and_Open_Questions.md](07_Risks_and_Open_Questions.md)**.

## Dependency order (you cannot skip)

```
Slice 1 (done) ─► Slice 2 (gold labels) ─► Slice 3 (train) ─► Slice 4 (eval) ─► Slice 5 (export+wire)
                         ▲                                         │
                         └──────── active-learning loop ◄──────────┘  (after first model, pre-annotate batch_02+)
```

## Phase-3 Definition of Done (overall)

New gazettes flowing out of Phase 2 auto-classify: `m1_regulations.change_category` + `affected_sectors[]` + `confidence` populate via the ONNX inference task; 3-seed mean **macro-F1 ≥ 0.92** with per-language gates (EN ≥ 0.93, SI ≥ 0.88, TA ≥ 0.86) and no slice cliff > 8 pp; low-confidence (< 0.55) rows route to a review queue; reproducibility hash + metrics recorded in `model_registry.json`.

## How to use this plan

- Each slice file is self-contained: **Purpose → Prerequisites → Steps (with commands/code) → Tests → DoD → Does-NOT-do → Cross-refs**.
- Start at the **"Do this next"** call-out in the slice marked 🔲 next.
- All commands are also consolidated in [06_Commands_and_Test_Manual.md](06_Commands_and_Test_Manual.md).
- This folder is **append-only**; flip a slice's status badge to ✅ when its DoD passes, and add the matching `F-2xx` row to [FEATURES.md](../../FEATURES.md) + a [SESSIONS.md](../../SESSIONS.md) entry.

## Cross-references

- Specs: [BUILD_11_ML_Training_Pipeline](../../../04-Technology-Stack/ml/BUILD/BUILD_11_ML_Training_Pipeline.md) · [BUILD_07_Module1_Awareness](../../../04-Technology-Stack/backend/BUILD/BUILD_07_Module1_Awareness.md)
- Design: [05_M1_Model_Architecture](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/05_M1_Model_Architecture.md) · [06_M1_Training_Evaluation](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/06_M1_Training_Evaluation.md) · [09_M1_Annotation_Guidelines](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/09_M1_Annotation_Guidelines.md)
- Status read: [STATUS_2026-06-28_Module1_Analysis_and_Next_Level_Roadmap](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/STATUS_2026-06-28_Module1_Analysis_and_Next_Level_Roadmap.md)
- Predecessor: [2026-05-23_M1_Phase2_Upgrade_Plan/00_INDEX](../2026-05-23_M1_Phase2_Upgrade_Plan/00_INDEX.md)
