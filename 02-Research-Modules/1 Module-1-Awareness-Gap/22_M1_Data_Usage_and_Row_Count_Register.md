# 22 — Module 1: Data Usage and Row Count Register

> How many rows the project actually has, which split each model was trained/selected/tested on, and which data is spent. Written to answer one recurring question — *"so how much data is there?"* — without the answer changing depending on who counts.
>
> Companion to [[18_M1_Dataset_And_Model_Lineage]] (what each version is), [[21_M1_Data_Limitations_and_Risk_Register]] (what is wrong with it), and [[06_M1_Training_Evaluation]] (how the remaining unspent data may be used).

> [!warning] The counting rule — 2026-08-02
> **Versions are not addends.** V4, V5, V6 and V7 are successive transformations of one corpus, not four datasets. Fresh holdout v1, v2 and v3 are three revisions of one file, not three files.
> The project holds **1110 corpus rows + 286 fresh holdout rows = 1396 distinct rows**.

---

## 1. The count, once

```text
Main model-development corpus          1110 rows
  ├─ train  (all training)              777
  ├─ validation  (all selection/tuning) 166
  └─ test  (consumed)                   167

Fresh Holdout v3  (never trained on)    286 rows

Total distinct project rows            1396
```

Everything else in this document is a breakdown of those two numbers.

| Count | Rows | Meaning |
|---|---:|---|
| Main labelled corpus | **1110** | the V4/V5/V6/V7 corpus — one dataset, four label states |
| Train split | 777 | every model that was trained, was trained on these |
| Validation split | 166 | every seed choice, epoch choice and threshold came from here |
| Old test split | 167 | read once per line, then spent |
| Fresh holdout v1 | 193 | first labelled attempt — diagnostic only, never lockable |
| Fresh holdout v2 | 225 | after round-1 top-up — still not lockable |
| **Fresh holdout v3** | **286** | current master, awaiting Step 55A lock |
| Corpus + final holdout | **1396** | the only defensible "total rows" figure |

---

## 2. Why the non-additive rule needs stating

Wrong:

```text
1110 (V4) + 1110 (V5) + 1110 (V6) + 1110 (V7) + 286  =  4726
193 (v1) + 225 (v2) + 286 (v3)                       =  704
```

Right:

```text
one 1110-row corpus, relabelled three times
one holdout file, revised twice, currently 286 rows
1110 + 286 = 1396
```

Each dataset version is the previous one with corrections applied — V5 fixed 3 category labels, V6 fixed 4 EPF/ETF labels, V7 added stored multitask columns. Not one of them added a document. Likewise the holdout: v2 *is* v1 plus 32 rows, v3 *is* v2 plus 61 rows. The files supersede each other.

Two consequences follow, and both matter more than the arithmetic:

- **The old 167-row test split is part of the 1110, not extra.** It is not a separate dataset that happens to be spent; it is 15 % of the corpus, permanently withdrawn from use.
- **The effective evaluation surface is much smaller than the corpus.** 1110 rows sounds comfortable. The project's actual remaining unspent evaluation data is **286 rows, once**.

---

## 3. Stage-by-stage usage

| Stage | Dataset | Rows | Train | Val | Test / eval | Model | Outcome |
|---|---|---:|---:|---:|---:|---|---|
| V4 cleanup | v4 clean stratified | 1110 | 777 | 166 | 167 | LogReg, LinearSVC | LinearSVC stronger (0.9247 vs 0.8589) |
| V5 fixed split | v5 clean fixedsplit | 1110 | 777 | 166 | 167 | LogReg, LinearSVC | LinearSVC macro-F1 **0.9472** |
| V6 fixed split | v6 clean fixedsplit | 1110 | 777 | 166 | 167 | LinearSVC | **frozen as category-only primary** |
| V6 neural attempt | v6 | 1110 | 777 | 166 | 167 | XLM-R category-only | underfit / collapse — rejected |
| V7-W working | v6 multitask noleak | 1103 | 773 | 163 | 167 | XLM-R LoRA multitask | collapsed — rejected |
| V7-M Steps 47–49 | v7 1110 multitask fixedsplit | 1110 | 777 | 166 | **not loaded** | XLM-R LoRA multitask | validation-only; seed 42 selection 0.91794 |
| **V7-M Step 50** | v7 test split | — | — | — | **167 — CONSUMED** | seed 1 candidate | **strict gate FAILED** — sector 0.888330 |
| V7-M improvement | v7 train/val only | — | 777 | 166 | none | seeds 7 / 13 / 29 | **seed 13 selected on validation** |
| Fresh holdout v1 | new collection | 193 | none | none | none | none | not lockable |
| Fresh holdout v2 | v1 + 32 | 225 | none | none | none | none | not lockable |
| **Fresh holdout v3** | v2 + 61 | **286** | none | none | **future, once** | none yet | **ready for lock validation** |

Read the last four rows together: the fresh holdout has been through three annotated states and **has still never met a model**. That is the property being protected.

---

## 4. What each split was used for

### Train — 777 rows

Every model in the project was fitted on these rows and no others: the LinearSVC category-only primary, the rejected XLM-R category-only attempt, the V7-W multitask runs, the V7-M multitask runs, and the seed13 improvement candidate.

**The fresh holdout has never been trained on and must never be.**

### Validation — 166 rows

Everything selective happened here: model selection, seed selection, early-stopping epoch, and all threshold tuning. For the current candidate: seed 13 chosen from {7, 13, 29}, best epoch 21, thresholds `grocery 0.45 / food 0.45 / general 0.75`.

Because 166 rows carried every selection decision, validation figures are optimistically biased by construction. That is why they are not promotion evidence — see §5.

### Old test — 167 rows, spent

| Line | How it was spent | Status |
|---|---|---|
| V6 | frozen-model comparison, then re-read by the V7-W experiment | **spent** |
| V7-M | one strict Step 50 evaluation → sector macro-F1 0.888330, gate failed | **spent** |

```text
CONSUMED
DO NOT RERUN
DO NOT USE FOR SELECTION
DO NOT USE FOR TUNING
DO NOT USE FOR PROMOTION AGAIN
```

The prohibition covers the error table too. Inspecting which 167-row cases failed, in order to choose what to change next, is selection on the test set with extra steps.

### Fresh holdout v3 — 286 rows, unspent

Not yet used for training, validation selection, threshold tuning, evaluation or promotion. Permitted uses, in order:

```text
Step 55A  lock validation only  (no model runs)
Step 55B  one-time evaluation   (only after 55A passes)
```

---

## 5. Which model used which data

### LinearSVC V6 primary — frozen, in production

Used V6 train 777 / val 166 / test 167. Category-only: no sector labels, no relevance labels, no contact with the fresh holdout.

```text
validation macro-F1  0.924476
test macro-F1        0.947220
status               FROZEN — production category classifier
```

### XLM-R LoRA V7-M, Step 50 candidate (seed 1) — failed, archived

Used V7-M train 777 / val 166, then the 167-row test split **once**.

```text
category macro-F1  0.910533   gate >= 0.90   pass
relevance F1       0.92       gate >= 0.90   pass
sector exact       0.916168   gate >= 0.90   pass
sector macro-F1    0.888330   gate >= 0.90   FAIL
status             archived, not promoted; test split consumed
```

### XLM-R LoRA V7-M improvement candidate (seed 13) — current, untested

Used V7-M train 777 / val 166. **Did not load** the old test split. **Has not touched** the fresh holdout.

```text
validation category macro-F1  0.929558
validation sector macro-F1    0.927620
validation sector exact       0.957831
validation relevance F1       0.936170
thresholds                    grocery 0.45 / food 0.45 / general 0.75
status                        VALIDATION_SELECTED_ONLY_NOT_TESTED
promotion_allowed             false
```

**These four numbers are selection evidence, not measurement.** The comparison that makes the point: the Step 50 candidate's *validation* sector macro-F1 was in the same range, and its *test* figure came in at 0.888330. The gap between validation and held-out performance on this task has already been demonstrated once, on this exact metric, by this exact pipeline.

---

## 6. Data that must never be mixed

| Never | Because |
|---|---|
| fresh holdout → any training split | it is the only unspent evaluation surface in the project |
| fresh holdout → threshold tuning | tuning converts it into a validation set and destroys the lock |
| old test rows → selecting or comparing candidates | consumed; a second read is not a second measurement |
| old test error rows → deciding what to change next | that is selection on the test set |
| validation figures → promotion claims | 166 rows carried every selection decision; the bias is structural |
| synthetic or rewritten text → any split | invalidates the source-backed guarantee the whole holdout rests on |

---

## 7. Where the remaining plan stands

| Step | Data | Model | Allowed |
|---|---|---|---|
| **55A** | fresh holdout v3, 286 rows | none | validate structure, record limitations, write locked manifest |
| 55B | locked v3, once | seed13 candidate | evaluate with frozen thresholds; no tuning, no re-runs |
| 56 | — | seed13 candidate | promote only if the pre-declared gate passes |

Frozen thresholds for 55B:

```text
grocery_retail: 0.45
food_service:   0.45
general_retail: 0.75
```

Candidate:

```text
/kaggle/working/storage/models/m1/xlmr_lora_v7_multitask_improvement_validation_only_candidate_seed13_not_tested
bundle SHA256  1964A346CFDA3659BB4D511872D87F46D8B896D5D4D0E3EB334B77A1C47690D9
model  SHA256  7739501786B8501C247397D9E72D37CF4FF8C7D1C3F5494215980C8AAB5FFB26
```

---

## 8. Status summary

```text
Main training corpus              1110 rows
Neural training rows                777
Neural validation rows              166
Old test rows                       167   consumed, never rerun
Fresh holdout v3                    286   not trained on, not evaluated yet
Total distinct project rows        1396

Current model    XLM-R LoRA V7-M multitask, seed 13
Status           validation-selected only · not tested · not promoted
Production       LinearSVC V6 primary (category-only) remains frozen and serving
Next             Step 55A — fresh holdout v3 lock validation
```

The project holds one 1110-row model-development corpus and one separate 286-row fresh holdout. The current candidate was trained only on the 777-row train split and selected only on the 166-row validation split. The 167-row test split was consumed once and cannot be reused. v3 must be locked before any evaluation.

---

## 9. Cross-references

- Dataset versions, hashes, model comparison table: [[18_M1_Dataset_And_Model_Lineage]]
- V7-M lineage and the failed strict gate: [[18_M1_Dataset_And_Model_Lineage]] §∞ V7-M multitask line · [[20_M1_Multitask_Classifier_Upgrade]] §∞ V7-M line
- Limitations attached to these counts: [[21_M1_Data_Limitations_and_Risk_Register]]
- Lock and evaluation protocol: [[06_M1_Training_Evaluation]] §∞ Step 55A/55B
- Holdout collection and version progression: [[03_M1_Data_Collection]] §∞ Step 54A
