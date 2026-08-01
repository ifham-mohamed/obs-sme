# 18 — Module 1: Dataset and Model Lineage

> One page that traces every M1 classification dataset from the raw gold standard to the frozen production model: which version came from which, what changed between them, what the split was, what each artifact hashes to, and which model was trained on which. Companion to [[06_M1_Training_Evaluation]] (method) and [[09_M1_Annotation_Guidelines]] (how labels were produced).
>
> Evidence base: `documentation/m1/records/ENIGMATRIX_M1_COMPLETE_END_TO_END_RECORD_2026-07-31_2313_IST.md` (5,642 lines) and `datasets/m1_regulations_v6_1110_clean_fixedsplit/dataset_manifest_v6.json`.
> Verified: 2026-08-01.

---

## 1. Lineage at a glance

```text
Label Studio batches 01–07
        │  2 annotations per task · 1128 tasks · 2256 annotations
        ▼
gold_standard.csv  (research/data/labeling/)
        │  freeze
        ▼
V4  m1_regulations_v4_1128            ── 1128 rows, raw gold freeze
        │  drop 18 OCR/page-number artifacts (ML use only — gold history keeps them)
        ▼
V5  m1_regulations_v5_1110_clean_fixedsplit
        │  + 3 PDF-adjudicated category corrections (all in test split)
        │  fixed split established: 777 / 166 / 167
        ▼
V6  m1_regulations_v6_1110_clean_fixedsplit   ◄── FROZEN, current
           + 4 EPF/ETF label corrections (all in train split)
           split preserved byte-for-byte from V5
```

Two rules held across every version and are what make the model comparisons valid:

1. **The split never moved.** 777 train / 166 validation / 167 test from V4 onward, so a V5-vs-V6 score difference is a labelling effect, never a split effect.
2. **Nothing was deleted from the gold history.** The 18 excluded artifacts are excluded from *ML training and evaluation only*; they remain in the adjudicated gold record.

---

## 2. Version-by-version

### V4 — `m1_regulations_v4_1128`

The first freeze of the 1128-row gold set. Also present as `_stratified` and `_clean_stratified` variants from the pre-fixed-split era. Superseded — kept for provenance only.

### V5 — `m1_regulations_v5_1110_clean_fixedsplit`

1110 rows after excluding 18 OCR/page-number artifacts, plus three adjudicated corrections resolved against the source PDFs — all three landed in the test split:

| Key | Was | Corrected to |
|---|---|---|
| `GZT_2491_01` | `SECTOR_SPECIFIC` | `IMPORT_EXPORT` |
| `official-egz-2337-19` | `IMPORT_EXPORT` | `PRODUCT_STANDARD` |
| `GZT_2471_56` | `SECTOR_SPECIFIC` | `LABOUR_LAW` |

Ships with `dataset_manifest.json`, `label_changes_from_v4_to_v5.csv`, `split_distribution.csv`, and both CSV and Parquet forms.

### V6 — `m1_regulations_v6_1110_clean_fixedsplit` (current, frozen)

Produced by `scripts/build_m1_v6_fixedsplit.py` from a Kaggle correction bundle (SHA256 `2C9169B5…86597`). The change is narrow and deliberate: four Presidential duties/functions gazettes carried incidental ETF mentions and had been labelled `EPF_ETF_CHANGE` when their subject matter was not an EPF/ETF change.

| Key | V5 label | V6 label |
|---|---|---|
| `official-pdf-2226-17` | `EPF_ETF_CHANGE` | `SECTOR_SPECIFIC` |
| `official-pdf-2235-59` | `EPF_ETF_CHANGE` | `SECTOR_SPECIFIC` |
| `official-pdf-2248-35` | `EPF_ETF_CHANGE` | `SECTOR_SPECIFIC` |
| `official-pdf-2412-08` | `EPF_ETF_CHANGE` | `SECTOR_SPECIFIC` |

All four are in the **train** split, so the test set is untouched between V5 and V6. Cross-split key leakage was verified as zero.

**Class distribution (V6):**

| Category | Train | Total |
|---|---:|---:|
| `SECTOR_SPECIFIC` | 478 | 679 |
| `IMPORT_EXPORT` | 78 | 112 |
| `TAX_RATE_CHANGE` | 58 | 82 |
| `LABOUR_LAW` | 52 | 75 |
| `PENALTY_ENFORCEMENT` | 46 | 66 |
| `PRODUCT_STANDARD` | 36 | 53 |
| `BUSINESS_REGISTRATION` | 25 | 36 |
| `EPF_ETF_CHANGE` | 4 | 7 |

`EPF_ETF_CHANGE` at 4 training rows and **1 test row** is the dataset's structural weakness: its per-class F1 is a one-sample estimate and cannot be treated as a stable measurement.

**Integrity:**

| File | SHA256 |
|---|---|
| `train.parquet` | `17AAA80E7BEE8DE2513705753C6C045043D6308BD1E4AE115ADB9387C3E1312C` |
| `val.parquet` | `D7E8115A6E7546281936BE5081AE7D5C54F4656189EC123A5550736ACD315BF4` |
| `test.parquet` | `83583F15E95FA28795DDDBA16D5BECEDCCD1649271ADFFC879466FD7614224F9` |
| dataset ZIP | `66EF4CF6FB187146641173BBB71628AD711C635FCEADE34CAB01AADDD99F35F0` |

### Legacy sets inside `enigmatrix-ml/datasets/`

`m1_regulations`, `m1_regulations_smoke`, `m1_regulations_v2_1000`, `m1_regulations_v2_1000_stratified`, `m1_regulations_v3_1128_stratified` — the pre-V4 generations, still untracked in git (`?? datasets/`). They are the sets the module docstrings use as `--data` examples. Left in place deliberately; superseded for any result that will be reported.

---

## 3. Models trained on these datasets

| Model | Dataset | Val macro-F1 | Test macro-F1 | Verdict |
|---|---|---:|---:|---|
| XLM-R LoRA, category-only, unweighted | V5 | ~0.0946 | ~0.0936 | Collapsed to majority class |
| XLM-R LoRA, balanced (seed 42, 16 ep) | V5 | 0.596014 | 0.685348 | Rejected — 0 EPF predictions |
| XLM-R LoRA, underfit-fix (seed 42, 20 ep) | V6 | 0.902693 | 0.743563 | Experimental only — failed the gate |
| **TF-IDF + balanced LinearSVC** | **V6** | **0.924476** | **0.947220** | **Primary — frozen** |
| TF-IDF + Logistic Regression | V6 | — | 0.882481 | Baseline reference |

### Why the transformer lost

The V6 underfit-fix run reached **0.969340 training** macro-F1 — the optimization fixes (separate LoRA/head learning rates, √-balanced clipped loss weights, α=0.5 minority sampling, gradient clipping) demonstrably solved the underfitting. But test macro-F1 fell to 0.743563 while validation held at 0.902693. On the temporal test split the classical model beat it by **+0.204 macro-F1**, was right on 10 records the transformer got wrong, and correctly classified the single EPF/ETF test record the transformer missed (transformer put 0.803 confidence on `LABOUR_LAW`, with `EPF_ETF_CHANGE` second at 0.197).

Read carefully, this is a generalization result, not a "classical beats neural" result: 777 training rows across 8 classes with a 4-row minority is well inside the regime where a lexical model with strong regularization is the better estimator.

### Frozen primary artifact

```text
C:\Reasearch\xyz\models\m1\linearsvc_v6_primary\linearsvc_pipeline.joblib
SHA256  1D7F84754421A881EE1B5FA0F008A0CC3DB4E24F52CE6D97CE155CB4D1923CFA
Bundle  2F80BEFE494F1275DCB14FCB5352902A8BF98C1CC3FA86F919D53B7958C5F11B
```

Configuration: `TfidfVectorizer(max_features=50000, ngram_range=(1,2), min_df=2)` → `LinearSVC(class_weight="balanced")`. Test accuracy 0.958084, 160/167 correct. The score reproduced **exactly** after serialization, download to Windows and reload — `0.9472199858964565` on both Kaggle and local.

Per-class test F1: `LABOUR_LAW` 1.000 · `EPF_ETF_CHANGE` 1.000 (n=1) · `SECTOR_SPECIFIC` 0.970 · `IMPORT_EXPORT` 0.970 · `PRODUCT_STANDARD` 0.941 · `BUSINESS_REGISTRATION` 0.923 · `TAX_RATE_CHANGE` 0.917 · `PENALTY_ENFORCEMENT` 0.857.

---

## 4. The confidence contract

`LinearSVC.decision_function` returns signed margins, **not** calibrated probabilities. The inference adapter therefore returns:

```json
{ "confidence": null, "confidence_type": "not_available_uncalibrated_linearsvc" }
```

and exposes `decision_score`, `decision_margin`, `second_category`, `second_decision_score`, `class_scores` instead. These rank well and are fine for review-queue prioritisation. **They must never be rendered as percentages in the UI.** If calibrated probabilities are needed, train and evaluate a calibration layer separately — do not transform margins.

The frozen primary model also has **no sector head**; it returns `"sectors": []` and `"sector_probs": {}`. Sector prediction still belongs to the older ONNX dual-head `GazetteInference`.

---

## 5. Standing constraints

1. **The V6 test split is spent for tuning.** It is final-evaluation only. Any further model selection needs a fresh split or nested CV.
2. **`EPF_ETF_CHANGE` needs real data, not resampling.** 4 train / 1 test rows. The next annotation round should target genuine EPF/ETF regulations before any per-class claim is made about this category.
3. **Do not rename or move `datasets/` or `models/`.** Their paths are recorded inside `model_registry.json`, `SHA256SUMS.json`, `local_windows_verification.json` and the frozen record.
4. **Re-derive, don't hand-edit.** Every table here is regenerable from the record generator; if a number changes, change the source and regenerate.

---

## 6. Cross-references

- **Training method and metrics:** [[06_M1_Training_Evaluation]]
- **Architecture and sampling:** [[05_M1_Model_Architecture]]
- **Annotation, taxonomy and IAA protocol:** [[09_M1_Annotation_Guidelines]]
- **Physical layout of `datasets/` and `models/`:** [[17_M1_Repo_Structure_Map]]
- **Full chronology with every epoch and error:** `documentation/m1/records/ENIGMATRIX_M1_COMPLETE_END_TO_END_RECORD_2026-07-31_2313_IST.md`
