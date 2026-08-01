# 20 — Module 1: Multitask Classifier Upgrade (V7)

> The upgrade from a category-only classifier to one that emits **regulation domain + affected SME sectors + SME relevance** from a single shared encoder — and the Step-41 audit that had to run before any architecture change, because it changed three things in the plan.
>
> The frozen `linearsvc_v6_primary` is **not modified**. V7 is additive: a new dataset version, a new trainer, a new inference class, and a promotion decision that may legitimately end in a hybrid.
>
> Companion to [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) (the head design), [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) (protocol and gates), [18_M1_Dataset_And_Model_Lineage.md](18_M1_Dataset_And_Model_Lineage.md) (lineage), and [[final/works/11_CLASSIFIER_FREEZE_AND_INTEGRATION|11_CLASSIFIER_FREEZE_AND_INTEGRATION]] (what is frozen and must stay frozen).

---

## 0. Where this sits

Stage D. The frozen primary answers one question; the upgraded model answers three:

```text
regulation text
      │
      ▼  shared XLM-R encoder
      ├── category head    8-way softmax   → exactly one domain
      ├── sector head      3 × sigmoid     → zero to three sectors
      └── relevance head   1 × sigmoid     → AUXILIARY ONLY, never served
                                 │
                                 ▼
              is_sme_relevant = any(predicted_sectors)     ← derived, not predicted
```

Deriving relevance rather than serving a third prediction is what makes this response structurally impossible:

```json
{ "is_sme_relevant": false, "sectors": ["grocery_retail"] }
```

**Implementation status:** 📋 **Step 41 complete (audit, below). Steps 42–53 not started.** No V7 dataset exists, no multitask trainer exists, and nothing is trained. Every number in §1 is measured from the V6 parquets and the v3 gold standard; everything from §3 onward is specification.

---

## 1. Step 41 — the V6 audit, and what it changed

Run read-only over all three V6 parquets plus `research/data/labeling/gold_standard_v3_1128.csv`. Artifacts:

```text
documentation/m1/analysis/multitask_dataset_audit.json
documentation/m1/analysis/multitask_label_distribution.csv
documentation/m1/analysis/multitask_consistency_errors.csv
```

### 1.1 Schema — the plan assumed a field that is not there

V6 parquet columns are exactly:

```text
key · text · category · sectors · language · date
```

| Expected field                                | Present?                              |
| --------------------------------------------- | ------------------------------------- |
| `key`, `text`, `category`, `language`, `date` | ✅                                     |
| `affected_sectors`                            | ✅ — **named `sectors`**               |
| **`is_sme_relevant`**                         | ❌ **ABSENT**                          |
| `split`                                       | ❌ — implied by the file, not a column |

**`is_sme_relevant` was dropped when V6 was exported.** It must be recovered from the gold standard by joining on `regulation_key`. That join is safe: coverage is **1110 / 1110**, and V6 `sectors` matches gold `affected_sectors` on **1110 / 1110** rows, so the export lost the relevance column and nothing else.

### 1.2 Integrity — clean

| Check | Result |
|---|---|
| Rows | 777 / 166 / 167 = **1110** |
| Duplicate keys | **0** |
| Cross-split overlap | **0** |
| Missing or empty text | **0** |
| Unknown categories | **none** |
| Unknown sector labels | **none** |
| Duplicate sectors within a row | **0** |
| **Total consistency errors** | **1** |

### 1.3 The one derivation-rule violation is not a data error

`is_sme_relevant == bool(affected_sectors)` holds on **1109 of 1110** rows. The single exception, `GZT_2492_10` (train, `IMPORT_EXPORT`), carries `is_sme_relevant=True` with empty sectors — and both annotators independently wrote the same note, agreeing at confidence 1.0:

> *"Export-proceeds rule affects SME exporters, but it is outside the three shop-focused study sectors; affected_sectors left blank."*

This is a **deliberate, reasoned annotation**, not a slip. It exposes that the corpus uses two different meanings:

| Meaning | Scope |
|---|---|
| `is_sme_relevant` **as annotated** | affects *any* SME |
| `is_sme_relevant` **as derived from sectors** | affects at least one of the *three study sectors* |

Adopting `is_sme_relevant = any(sectors)` therefore **narrows the field's meaning**, and that narrowing must be stated rather than absorbed silently. It is the right trade — a servable, internally consistent contract beats a broader one the model cannot represent — but the API field should be read as *"affects a studied sector"*.

**V7 decision:** relabel `GZT_2492_10` to `is_sme_relevant = false`, record it in the V7 change log with the annotator note preserved, and add it to the limitations section of the write-up. Do not delete the row and do not silently flip it.

### 1.4 The finding that most changes the plan — the sector task is nearly degenerate

| Sector combination  | Train |   Val |  Test |   Total |     Share |
| ------------------- | ----: | ----: | ----: | ------: | --------: |
| `[]` — no sectors   |   574 |   121 |   117 | **812** | **73.2%** |
| all three           |   172 |    36 |    42 | **250** | **22.5%** |
| `grocery + food`    |    25 |     7 |     5 |      37 |      3.3% |
| `general` only      |     4 |     1 |     2 |       7 |      0.6% |
| `food` only         |     2 | **0** | **0** |       2 |      0.2% |
| `general + grocery` | **0** |     1 |     1 |       2 |      0.2% |

Of the 298 rows that carry any sector, **250 (84%) carry all three.** Genuine partial-sector structure is **48 rows — 4.3%** of the dataset: 31 train, 9 val, 8 test.

Four consequences, each of which invalidates something in the original plan:

1. **A model that only learns "relevant vs not" and emits all three whenever relevant scores well on sector macro-F1.** The proposed ≥ 0.88 sector gate is therefore **gameable by a degenerate solution** and cannot stand alone (§6.2 adds the gate that closes it).
2. **Per-sector threshold tuning is not statistically supportable here.** A 9-point grid × 3 sectors is 729 combinations selected against **9 informative validation rows**. That is overfitting by construction. Use **one global threshold**; report per-sector thresholds as a diagnostic only (§5.3).
3. **`general + grocery` has zero training examples** and one row each in val and test. The model cannot learn that combination, so exact-set-match accuracy has a hard ceiling below 100% for reasons that are nothing to do with the model.
4. **`food_service` alone has zero val and zero test examples.** That pattern cannot be evaluated at all.

**What may honestly be claimed:** a relevance detector with a partially-informative sector refinement. **Not:** a validated three-way multi-label sector classifier. The data does not currently support the second claim, and saying so first is cheaper than being asked.

### 1.5 Measured class weights — use these, do not assume balance

From the **training split only**:

| Task | Positives | Negatives | `pos_weight` = neg/pos |
|---|---:|---:|---:|
| `grocery_retail` | 197 | 580 | **2.944** |
| `food_service` | 199 | 578 | **2.905** |
| `general_retail` | 176 | 601 | **3.415** |
| relevance (derived) | 204 | 573 | **2.809** |

Relevance balance per split: train 204/573 · val 45/121 · test 50/117.

---

## 2. Step 42 — the V7 dataset

**V6 is frozen and is not touched.** V7 is derived.

```text
source   /kaggle/input/datasets/ifhammohamed1/m1-regulations-v6-1110-clean-fixed-split/
                m1_regulations_v6_1110_clean_fixedsplit
target   /kaggle/working/enigmatrix-ml/datasets/m1_regulations_v7_1110_multitask_fixedsplit
```

Preserved unchanged: all 1110 keys · the 777/166/167 split · every V6 category label · text · date · language.

Added: `is_sme_relevant` (recovered by gold join), `sector_vector`, `category_id`, `relevance_label`, explicit `split`.

### 2.1 Row schema

```json
{
  "key": "official-example-001",
  "text": "The importation of specified electrical equipment...",
  "category": "IMPORT_EXPORT",
  "category_id": 1,
  "sectors": ["general_retail"],
  "sector_vector": [0, 0, 1],
  "is_sme_relevant": true,
  "relevance_label": 1,
  "language": "en",
  "date": "2025-03-27",
  "split": "train"
}
```

### 2.2 The frozen orders

Both orders are **permanent**. A vector written under one order and read under another is silently wrong — the same failure class as the FLORES-200 code trap in [10_M1_Sinhala_Tamil_NLP.md](10_M1_Sinhala_Tamil_NLP.md) §10.3.

```python
CATEGORIES = [
    "TAX_RATE_CHANGE",        # 0
    "IMPORT_EXPORT",          # 1
    "SECTOR_SPECIFIC",        # 2
    "EPF_ETF_CHANGE",         # 3
    "LABOUR_LAW",             # 4
    "PRODUCT_STANDARD",       # 5
    "BUSINESS_REGISTRATION",  # 6
    "PENALTY_ENFORCEMENT",    # 7
]

SECTORS = [
    "grocery_retail",   # index 0
    "food_service",     # index 1
    "general_retail",   # index 2
]
```

Write both into `labels.json` beside the model artifact and assert them at load time. An index order is a contract, exactly as `datasets/` and `models/` paths are ([18_M1_Dataset_And_Model_Lineage.md](18_M1_Dataset_And_Model_Lineage.md) §5).

### 2.3 Builder acceptance

The V7 build script must fail loudly rather than write a bad dataset:

- 1110 rows, split sizes 777/166/167 exactly
- every key present in V6 and no key added
- category labels identical to V6, row for row
- `sector_vector` reconstructs `sectors` exactly under the frozen order
- `relevance_label == int(any(sector_vector))` on **every** row (after the `GZT_2492_10` relabel)
- per-split SHA256 recorded in `dataset_manifest_v7.json`, and the V6 hashes recorded as the parent

---

## 3. Steps 43–44 — label contract and architecture

### 3.1 `m1/model/labels.py`

```python
def derive_sme_relevance(sector_vector: list[int]) -> bool:
    return any(int(v) == 1 for v in sector_vector)
```

Plus `encode_category` / `decode_category` / `encode_sectors` / `decode_sectors` / `validate_label_consistency`. `encode_sectors` must **reject** an unknown sector rather than dropping it — a silently dropped label is a wrong training target.

### 3.2 `m1/model/data.py` batch contract

```python
{
  "input_ids": ...,          "attention_mask": ...,
  "cat_labels": tensor(int),          # shape []
  "sec_labels": tensor([0., 1., 1.]), # shape [3]
  "rel_labels": tensor(1.),           # shape []
  "key": regulation_key,
}
```

The loader rejects: unknown categories, unknown sectors, duplicate sectors, relevance/sector contradictions, missing text, and malformed string-encoded sector lists. **The last one matters in practice** — V6 stores `sectors` as a numpy array, and a CSV round-trip turns it into the string `"['grocery_retail']"`. Parse defensively and assert the result.

### 3.3 Architecture

Shared encoder, three heads, relevance served only as a derivation. Head design as specified in the upgrade brief and consistent with [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) §4:

```python
category_logits  = self.category_head(pooled)   # (B, 8)
sector_logits    = self.sector_head(pooled)     # (B, 3)
relevance_logits = self.relevance_head(pooled).squeeze(-1)  # (B,)
```

### 3.4 Losses

```python
category_loss  = CrossEntropyLoss(weight=category_class_weights)
sector_loss    = BCEWithLogitsLoss(pos_weight=tensor([2.944, 2.905, 3.415]))
relevance_loss = BCEWithLogitsLoss(pos_weight=tensor(2.809))

total = 0.65 * category_loss + 0.30 * sector_loss + 0.05 * relevance_loss
```

`pos_weight` values are **measured** (§1.5), not assumed. Relevance is weighted low on purpose: it is auxiliary supervision, and it is ~99.9% redundant with the sector head by construction, so a large weight buys a second copy of the same gradient.

### 3.5 One sampler, not three

Build the training sampler from **category rarity alone**. Three independent weighted samplers would compound: `EPF_ETF_CHANGE` has 4 training rows, and a sampler that also up-weights rare sector patterns and the minority relevance class would duplicate a handful of rows to the point where the model memorises them. Category imbalance is the severe one; sector and relevance imbalance are handled by `pos_weight` in the loss.

---

## 4. Steps 45–49 — training protocol

| Stage | What | Gate to proceed |
|---|---|---|
| **A** Smoke | 32–64 rows, 1 epoch | All three heads receive gradients; shapes `(B,8)`, `(B,3)`, `(B,)`; loss finite; save/reload parity; eval files written |
| **B** Diagnostic | seed 42, 15–20 epochs, LoRA r=16, LoRA LR 2e-4, head LR 1e-3, clip 1.0, patience 5 | Category macro-F1 within reach of 0.92 on **validation** |
| **C** Loss weights | A (0.70/0.30/0.00) · B (0.65/0.30/0.05) · C (0.60/0.30/0.10) | **Validation only** |
| **D** Final | seeds 42, 1, 2 | Report mean ± std for every metric |

**The test split is not touched until the configuration is frozen.** It has already been used to compare four models ([18_M1_Dataset_And_Model_Lineage.md](18_M1_Dataset_And_Model_Lineage.md) §5) and is close to spent; using it for weight selection would end its usefulness as a held-out measurement entirely.

Do not modify `m1/model/train_xlmr_v6_underfit_fix.py`. Add `m1/model/train_xlmr_v7_multitask.py`.

---

## 5. Step 48 — thresholds

### 5.1 0.50 is not a default, it is a decision

A sigmoid trained with `pos_weight ≈ 3` does not produce probabilities centred such that 0.50 is the operating point. Tune on validation and **store the chosen value in `model_registry.json`**, so serving reads it rather than hard-coding it.

### 5.2 Use one global threshold

Search `[0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]` and select on validation sector macro-F1.

**Per-sector thresholds are not supportable on this data** (§1.4): the three sectors co-occur in 84% of positive rows, and only 9 validation rows carry a partial pattern. Fitting three thresholds against 9 informative rows will produce values that do not survive the test split. Compute the per-sector variant, record it as a diagnostic, and do **not** serve it until the corpus carries materially more partial-sector data.

### 5.3 Post-processing

```python
predicted_sectors = [s for s, p in sector_probs.items() if p >= threshold]
is_sme_relevant   = bool(predicted_sectors)
```

Review rule using the auxiliary head — its only production role:

```python
needs_review = (relevance_probability >= relevance_threshold) != bool(predicted_sectors)
```

A disagreement between the auxiliary head and the sector-derived answer is a **useful uncertainty signal**, and it is the one thing the third head is for. It never overrides the derivation.

---

## 6. Step 50 — evaluation and promotion

### 6.1 Metrics

| Task | Report |
|---|---|
| Domain | macro-F1, weighted-F1, accuracy, per-class P/R/F1, confusion matrix, prediction distribution |
| Sector | macro-F1, micro-F1, per-sector P/R/F1, exact-set-match, Hamming loss, sample-averaged F1, per-sector false negatives, combination confusion |
| Relevance | precision, recall, F1, accuracy, PR-AUC, confusion matrix, false-negative count |
| Consistency | `is_sme_relevant == bool(predicted_sectors)` on every row |

**Relevance recall deserves separate inspection.** Missing a relevant regulation means an SME never hears about a rule that binds them; one extra alert is a minor annoyance. The costs are not symmetric and the metric should not be averaged into an F1 that hides it.

**Report exact-set-match with its ceiling stated.** `general + grocery` has zero training examples, so a portion of the error is structural.

### 6.2 Promotion gates

| Gate | Threshold |
|---|---|
| Category macro-F1 | **≥ 0.92** |
| Category regression vs the frozen benchmark **0.9472199858964565** | **≤ 0.01** |
| Sector macro-F1 | **≥ 0.88** |
| No individual sector F1 | **< 0.80** |
| SME relevance recall | **≥ 0.90** |
| Sector/relevance consistency | **= 100%** |
| **Partial-sector exact-set-match on the 8 test rows that carry one** | **reported explicitly, not folded into any average** |

The last gate exists because of §1.4. Without it, sector macro-F1 ≥ 0.88 can be met by a model that has learned only "relevant → all three", which would be a relevance detector wearing a sector head. Reporting the partial-pattern rows separately is what distinguishes the two, even though 8 rows is too few to gate on numerically — hence *reported*, not thresholded.

### 6.3 The hybrid is a legitimate outcome

**Do not promote on a combined average.** The frozen LinearSVC scores **0.947220** on category. A multitask transformer scoring 0.925 on category and 0.90 on sector is *worse at the thing that already works* and better at a thing that does not exist yet.

| Outcome | Action |
|---|---|
| V7 category ≥ 0.9372 **and** sector gates pass | Promote V7 for both tasks |
| V7 sector gates pass, category regresses > 0.01 | **Hybrid:** LinearSVC serves category, V7 sector head serves sectors and derived relevance |
| Sector gates fail | Do not promote. Keep LinearSVC; sectors stay with `m1_regulation_sectors` |

The hybrid is not a fallback or an embarrassment — it is the arrangement that gives each task its best available model, and the confidence contract already supports two backends ([[final/works/11_CLASSIFIER_FREEZE_AND_INTEGRATION|11_CLASSIFIER_FREEZE_AND_INTEGRATION]] §5.2). Note that a hybrid means one row carries a **calibrated softmax probability for sectors and no probability at all for category** — the response contract must express that rather than paper over it.

---

## 7. Steps 51–53 — export, inference, freeze

### 7.1 ONNX

Export three outputs: `category_logits`, `sector_logits`, `relevance_logits`. Verify PyTorch/ONNX parity to a stated tolerance on a fixed batch before anything is promoted.

### 7.2 Inference

Add `MultitaskGazetteInference`, exported from `m1/model/__init__.py`. **Do not change `GazetteInference` or `LinearSVCGazetteInference` incompatibly** — the LinearSVC class is what production currently runs, and its behaviour is recorded in a frozen research record.

Response contract:

```json
{
  "category": "IMPORT_EXPORT",
  "category_confidence": 0.9341,
  "category_probs": { "...": "..." },
  "sectors": ["general_retail", "grocery_retail"],
  "sector_probs": { "grocery_retail": 0.7124, "food_service": 0.1831, "general_retail": 0.9437 },
  "is_sme_relevant": true,
  "relevance_probability": 0.9712,
  "relevance_source": "derived_from_sector_predictions",
  "sector_thresholds": { "grocery_retail": 0.48, "food_service": 0.46, "general_retail": 0.51 },
  "model_type": "xlmr_lora_multitask",
  "model_version": "m1_xlmr_v7_multitask"
}
```

Out of scope:

```json
{
  "category": "SECTOR_SPECIFIC",
  "sectors": [],
  "sector_probs": { "grocery_retail": 0.08, "food_service": 0.04, "general_retail": 0.12 },
  "is_sme_relevant": false,
  "relevance_source": "derived_from_sector_predictions"
}
```

`relevance_source` is not decoration. It tells a consumer that the boolean is a **function of the sector array**, so the two can never be inconsistent and a client must not treat them as independent evidence.

> ⚠ **`category_confidence` here is a softmax probability and is *not* comparable with the LinearSVC path**, which returns `confidence: null` and an uncalibrated margin. A row classified by V7 and a row classified by the frozen model carry different, non-interchangeable confidence semantics. Persist `model_name` per row — the column already exists — and never compare the two numerically.

### 7.3 Registry

```json
{
  "model_name": "m1_xlmr_v7_multitask",
  "dataset_source": "m1_regulations_v6_1110_clean_fixedsplit",
  "derived_dataset": "m1_regulations_v7_1110_multitask_fixedsplit",
  "tasks": ["regulation_domain", "affected_sectors", "sme_relevance_auxiliary"],
  "categories": 8,
  "sectors": 3,
  "category_order": ["TAX_RATE_CHANGE", "..."],
  "sector_order": ["grocery_retail", "food_service", "general_retail"],
  "sector_thresholds": { "grocery_retail": 0.48, "food_service": 0.46, "general_retail": 0.51 },
  "threshold_mode": "global",
  "relevance_rule": "derived_from_predicted_sectors",
  "seeds": [42, 1, 2],
  "metrics": { "category_macro_f1": 0.0, "sector_macro_f1": 0.0, "sector_micro_f1": 0.0, "relevance_f1": 0.0, "consistency_rate": 1.0 }
}
```

`category_order` and `sector_order` are recorded **in the registry**, not only in code, so a model loaded by a future version can assert the order it was trained under.

### 7.4 Freeze

Same discipline as the V6 freeze: hash the artifact and each split, package the bundle, download it, re-score locally, and confirm the metrics reproduce **exactly** before the model is called frozen. The V6 pass reproduced `0.9472199858964565` to the last digit; anything less than that standard is not a freeze.

---

## 8. Tests

```text
tests/m1/model/test_labels.py · test_data.py · test_architecture.py
tests/m1/model/test_multitask_loss.py · test_multitask_evaluation.py
tests/m1/model/test_multitask_inference.py · test_onnx_export.py
```

Essential assertions:

```python
category_logits.shape  == (B, 8)
sector_logits.shape    == (B, 3)
relevance_logits.shape == (B,)

encode_sectors(["grocery_retail", "general_retail"]) == [1, 0, 1]
derive_sme_relevance([0, 0, 0]) is False
derive_sme_relevance([1, 1, 1]) is True
```

Plus: save/reload parity · PyTorch↔ONNX parity · threshold application from the registry · batch inference · empty-text rejection · unknown-sector rejection · **`GazetteInference` and `LinearSVCGazetteInference` remain importable and unchanged**.

One test that is easy to omit and worth having: **assert the frozen orders**. A test that fails when `SECTORS` is reordered is the cheapest possible guard against a silent index shift.

---

## 9. Order of work

| Step | Work | State |
|---|---|---|
| **41** | Audit V6 schema and sector/relevance labels | ✅ **done — §1** |
| 42 | Build V7 without touching V6 | ⬜ next |
| 43 | `labels.py` / `data.py` contracts + consistency tests | ⬜ |
| 44 | Tri-head `GazetteClassifier` | ⬜ |
| 45 | Three-loss training loop | ⬜ |
| 46 | One-epoch Kaggle smoke | ⬜ |
| 47 | One-seed diagnostic | ⬜ |
| 48 | Threshold + loss-weight selection **on validation** | ⬜ |
| 49 | Three-seed final | ⬜ |
| 50 | Single evaluation on the untouched test split | ⬜ |
| 51 | ONNX export + parity | ⬜ |
| 52 | `MultitaskGazetteInference` + backend integration | ⬜ |
| 53 | Freeze, hash, package, reproduce locally | ⬜ |

---

## 10. Standing constraints

1. **Do not modify `models/m1/linearsvc_v6_primary/` or the V6 parquets.** Their hashes are recorded in frozen artifacts and a research record.
2. **The V6 test split is nearly spent.** Four models have been compared on it. V7 gets **one** evaluation, after the configuration is frozen on validation.
3. **`EPF_ETF_CHANGE` is 4 train / 1 test.** A multitask model does not fix this; only more documents do.
4. **The sector task cannot yet support a strong multi-label claim** (§1.4). Collecting partial-sector examples — regulations affecting one or two of the three sectors — is now the highest-value annotation target, ahead of general volume.
5. **`is_sme_relevant` after derivation means "affects a studied sector"**, which is narrower than the annotated field. State it in the write-up (§1.3).

---

## 11. Cross-references

- **Head design and sampling:** [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md)
- **Training protocol, seeds, gates:** [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md)
- **Dataset lineage and the V6 freeze:** [18_M1_Dataset_And_Model_Lineage.md](18_M1_Dataset_And_Model_Lineage.md)
- **What is frozen and the confidence contract:** [[final/works/11_CLASSIFIER_FREEZE_AND_INTEGRATION|11_CLASSIFIER_FREEZE_AND_INTEGRATION]]
- **Why the transformer lost the first time:** `final/works/PHASE3_ANNOTATION_CLASSIFICATION/classifier_model_training/CLASSIFIER_MODEL_SELECTION_ANALYSIS.md`
- **Sector definitions and annotation rules:** [09_M1_Annotation_Guidelines.md](09_M1_Annotation_Guidelines.md) §4
- **Serving contract:** [11_M1_API_Reference.md](11_M1_API_Reference.md) §4
- **Downstream consumer of sectors and relevance:** [19_M1_Regulation_Summarization.md](19_M1_Regulation_Summarization.md) §2.2
- **Status ledger:** [[final/works/03_FEATURE_CHECKLIST|03_FEATURE_CHECKLIST]]
- **Audit artifacts:** `documentation/m1/analysis/multitask_dataset_audit.json` · `multitask_label_distribution.csv` · `multitask_consistency_errors.csv`
