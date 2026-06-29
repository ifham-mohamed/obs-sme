---
tags: [m1, phase-3, slice-1, labeling, data-prep]
date: 2026-06-28
status: ✅ shipped 2026-06-28 (executed in Cowork; outputs in 03-Data-Sources/m1/raw/labeling/)
---

# Slice 1 — Labeling dataset preparation

## Purpose
Convert the existing **silver** (LLM/regex) classified gazette rows into an **annotation-ready first batch** so Slice 2 starts from *correction*, not blank labeling. Pre-loading the silver label as a Label Studio prediction cuts annotator effort substantially.

## Prerequisites
- Python 3.9+ (stdlib only — no pip installs).
- Silver CSVs present at `03-Data-Sources/m1/raw/csv/` (base `m1_regulations.csv` + `next50`/`batch*`).

## What it does (the script)
`scripts/prepare_labeling_dataset.py`:
1. Loads the **curated** CSVs only — base + `next50` + `batch2..11` (the `v2..v6` snapshots are noisy duplicates and are excluded).
2. **Dedupes by `gazette_number`**, keeping the most complete row (then longest `raw_text`).
3. Stratified-samples a first batch: **all rare-category rows + quarter-diversified round-robin fill** from the common categories, so annotators calibrate on the hard/rare classes.
4. Emits Label Studio tasks with the silver label as a **pre-annotation** (`model_version: silver_v0`).

## Steps (commands)
```bash
# from the vault root (C:\sme). Paths are relative; adjust for your OS.
python "08-Findings-Log/plans/2026-06-28_M1_Phase3_Classifier_Plan/scripts/prepare_labeling_dataset.py" \
    --csv-dir "03-Data-Sources/m1/raw/csv" \
    --out-dir "03-Data-Sources/m1/raw/labeling" \
    --batch-size 250 --seed 42
```

## Outputs (already generated)
`03-Data-Sources/m1/raw/labeling/`:
- `batch_01.csv` — 250 stratified rows (full schema + `__quarter`).
- `label_studio_import.json` — 250 tasks, **all 250 carry silver pre-annotations**.
- `category_distribution_before.csv` — silver distribution over the 500 deduped gazettes.

## Result of this run (2026-06-28)
- Loaded **549** curated rows → deduped to **500 distinct gazettes**.
- Silver distribution: `procedural_change 334 · rate_change 76 · other 67 · new_obligation 15 · registration_change 7 · structural_change 1`.
- `batch_01` = **250 tasks** — `procedural_change 84 · rate_change 76 · other 67 · new_obligation 15 · registration_change 7 · structural_change 1` (every rare class fully included).

## Tests / verification
```bash
# task count + every task has a prediction
python - <<'PY'
import json; d=json.load(open("03-Data-Sources/m1/raw/labeling/label_studio_import.json"))
assert len(d)==250, len(d)
assert all(t["predictions"] for t in d), "some tasks missing pre-annotation"
print("OK", len(d), "tasks; all pre-annotated")
PY
# batch is deduplicated on gazette_number
python - <<'PY'
import csv
g=[r["gazette_number"] for r in csv.DictReader(open("03-Data-Sources/m1/raw/labeling/batch_01.csv",encoding="utf-8"))]
assert len(g)==len(set(g)), "duplicate gazette in batch"
print("OK", len(g), "unique gazettes")
PY
```

## DoD ✅
A deterministic, re-runnable batch of 250 annotation tasks with silver pre-annotations exists in the vault, covering all 6 silver categories with the rare classes fully represented.

## Does NOT do (deliberately)
- Does **not** re-extract PDF text (uses CSV `title_en`/`summary_en`/`raw_text`; Sinhala `(cid:…)` dumps are skipped). Full-text enrichment is an optional command in [06_Commands_and_Test_Manual.md](06_Commands_and_Test_Manual.md).
- Does **not** map silver→canonical-12 (that is a Slice 2 annotation decision).
- Does **not** touch the production DB or backend.

## Cross-refs
- Next: [02_Slice2_Annotation_and_Gold_Set.md](02_Slice2_Annotation_and_Gold_Set.md)
- Sampling rationale: [05_M1_1_Sampling_Strategy](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/05_M1_Model_Architecture.md)
