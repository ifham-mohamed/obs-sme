---
tags: [m1, phase-3, slice-2, annotation, label-studio, iaa, gold-set]
date: 2026-06-28
status: 🔲 next — start here
---

# Slice 2 — Annotation + gold label set (≥ 800 labels, κ ≥ 0.75)

## Purpose
Produce the **human-verified gold corpus** the classifier trains on: ≥ 800 gazette documents labeled into the canonical **12 categories** + **10-sector** multi-label, with inter-annotator agreement **Cohen's κ ≥ 0.75**. This is the gate for everything downstream — without it the F1 ≥ 0.92 target is unreachable.

## Prerequisites
- Slice 1 outputs (`label_studio_import.json`, `batch_01.csv`).
- A Label Studio instance (Docker, below) — zero licence cost.
- **2 annotators** (per doc 09 IAA protocol). You can pilot solo first, recruit the second in parallel.

## Step 2a — Stand up Label Studio + import batch_01
```bash
pip install label-studio        # or: docker run -it -p 8080:8080 heartexlabs/label-studio:latest
label-start                     # opens http://localhost:8080
# Create project "M1 Gazette Classification" → Settings → Labeling Interface → paste the config below.
# Import: Data Manager → Import → 03-Data-Sources/m1/raw/labeling/label_studio_import.json
```

**Labeling config** (canonical 12 + 10 sectors; the silver pre-annotation pre-selects a `<Choices>` value so annotators *confirm or correct*):
```xml
<View>
  <Header value="Gazette $gazette_number  ($gazette_published_date)"/>
  <Text name="text" value="$text"/>
  <Header value="Change category (choose exactly one)"/>
  <Choices name="category" toName="text" choice="single" showInLine="false">
    <Choice value="TAX_RATE_CHANGE"/>     <Choice value="LABOUR_LAW"/>
    <Choice value="EPF_ETF_CHANGE"/>      <Choice value="PRODUCT_STANDARD"/>
    <Choice value="BUSINESS_REGISTRATION"/><Choice value="IMPORT_EXPORT"/>
    <Choice value="FINANCIAL_REGULATION"/> <Choice value="SECTOR_SPECIFIC"/>
    <Choice value="ENVIRONMENTAL"/>        <Choice value="PENALTY_ENFORCEMENT"/>
    <Choice value="DEADLINE_EXTENSION"/>   <Choice value="NO_SME_IMPACT"/>
  </Choices>
  <Header value="Affected sectors (choose all that apply)"/>
  <Choices name="sector" toName="text" choice="multiple" showInLine="true">
    <Choice value="agriculture"/><Choice value="manufacturing"/><Choice value="retail"/>
    <Choice value="tourism"/><Choice value="construction"/><Choice value="services"/>
    <Choice value="finance"/><Choice value="it"/><Choice value="transport"/><Choice value="food"/>
  </Choices>
</View>
```

## Step 2b — Apply the silver→canonical seed mapping
The silver labels are NOT the canonical 12. Use this **heuristic seed map** to pre-fill, then have annotators verify every row (the ambiguous ones MUST be human-decided):

| Silver label | Heuristic canonical seed | Confidence |
|---|---|---|
| `rate_change` | `TAX_RATE_CHANGE` (or `EPF_ETF_CHANGE` if EPF/ETF) | medium — verify |
| `registration_change` | `BUSINESS_REGISTRATION` | high |
| `new_obligation` | depends — `LABOUR_LAW` / `FINANCIAL_REGULATION` / `ENVIRONMENTAL` | low — human decides |
| `structural_change` | `SECTOR_SPECIFIC` | low — human decides |
| `procedural_change` | `NO_SME_IMPACT` *or* `SECTOR_SPECIFIC` (much of the `lands` bulk is NO_SME_IMPACT) | low — human decides |
| `other` | `NO_SME_IMPACT` | low — human decides |

> ⚠️ Because most silver rows are `procedural_change`/`other`, **do not trust the seed for those** — they need genuine human judgment against doc 09 §2 decision criteria. The seed only saves time on `rate_change`/`registration_change`.

## Step 2c — Calibration round (κ gate before scaling)
- Both annotators independently label the **same 50 docs** from `batch_01`.
- Compute Cohen's κ (use the script in [06_Commands_and_Test_Manual.md](06_Commands_and_Test_Manual.md), or Label Studio's built-in agreement view).
- **Gate: κ ≥ 0.75.** If below, refine the guideline edge-cases (doc 09 §6.1 contrastive pairs) and re-run on a fresh 50.

## Step 2d — Scale to ≥ 800 with active learning
- After the calibration passes, single-annotate the rest of `batch_01`, then generate `batch_02..N` (250 each) by re-running the Slice-1 script with a different `--seed`, or — once a v0 model exists (Slice 3) — by **uncertainty sampling** (lowest-confidence predictions first).
- Dual-annotate a 15% overlap subset each batch to keep tracking κ.
- **Target: ≥ 800 labeled, ≥ 50 per category** (over-sample the rare canonical classes deliberately).

## Step 2e — Freeze the gold set + temporal split
Export from Label Studio → `enigmatrix-ml/datasets/m1_regulations/gold_standard.csv`, then split **temporally** (NOT random) by `gazette_published_date`:
```bash
python -m m1.data.make_splits --in gold_standard.csv \
       --out datasets/m1_regulations/ --ratios 0.70 0.15 0.15   # train/val/test, time-ordered
```

## Tests / DoD
- κ ≥ 0.75 on the dual-annotated subset (report the number).
- `gold_standard.csv` ≥ 800 rows, ≥ 50/category, all 12 categories present.
- `train/val/test.parquet` exist with **no `gazette_published_date` leakage** across splits (test is the latest dates).

## Does NOT do
- No model training (Slice 3). No change to the silver CSVs (gold is a new file).

## Cross-refs
[09_M1_Annotation_Guidelines](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/09_M1_Annotation_Guidelines.md) · [09_M1_2_Annotation_Workflow_IAA_Protocol] · next [03_Slice3_Model_Package_and_Training.md](03_Slice3_Model_Package_and_Training.md)
