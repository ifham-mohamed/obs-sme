# 18 — Module 1: Dataset and Model Lineage

> One page that traces every M1 classification dataset from the raw gold standard to the frozen production model: which version came from which, what changed between them, what the split was, what each artifact hashes to, and which model was trained on which. Companion to [[06_M1_Training_Evaluation]] (method) and [[09_M1_Annotation_Guidelines]] (how labels were produced).
>
> Evidence base: `documentation/m1/records/ENIGMATRIX_M1_COMPLETE_END_TO_END_RECORD_2026-07-31_2313_IST.md` (5,642 lines) and `datasets/m1_regulations_v6_1110_clean_fixedsplit/dataset_manifest_v6.json`.
> Verified and reconciled with the executed V7 working branch: 2026-08-02.
> Extended 2026-08-02 with the **V7-M 1110-row multitask line** (Steps 47–50 strict-gate failure and the untested seed13 candidate) — see §∞ V7-M multitask line.

> [!warning] Truth-ledger sync — 2026-08-02
> This document is the lineage of record and is **already reconciled to 2026-08-02**. No corrections needed — it is the source the other documents were corrected *against*.
>
> **Canonical record:** [[final/works/11_CLASSIFIER_FREEZE_AND_INTEGRATION|11_CLASSIFIER_FREEZE_AND_INTEGRATION]] · [[18_M1_Dataset_And_Model_Lineage]] · `final/works/evidence/M1_OPERATING_EVIDENCE_2026-08-02.json`
> **Submitted-report copy:** [[final/report/Enigmatrix_Consolidated_Final_Report_FULL|Enigmatrix_Consolidated_Final_Report_FULL]] (Part I = group report, Part II = Module 1 dissertation).

---

## 1. Lineage at a glance

```text
Label Studio batches 01–07
        │  2 annotations per task · 1128 tasks · 2256 annotations
        ▼
gold_standard.csv  (research/data/labeling/)
        │
        ├─ Legacy experiment branch inside enigmatrix-ml/datasets/
        │
        │  L1      m1_regulations                     800 rows · 560 / 120 / 120
        │  Smoke   m1_regulations_smoke                32 rows · 16 / 8 / 8
        │  L2      m1_regulations_v2_1000             1000 rows · 700 / 150 / 150
        │  L2s     m1_regulations_v2_1000_stratified  1000 rows · 700 / 150 / 150
        │  L3      m1_regulations_v3_1128_stratified  1128 rows · 790 / 169 / 169
        │
        └─ Fixed reporting branch
           │
           ▼
           V4  m1_regulations_v4_1128            ── 1128 rows, raw gold freeze
           │  drop 18 OCR/page-number artifacts (ML use only — gold history keeps them)
           ▼
           V5  m1_regulations_v5_1110_clean_fixedsplit
           │  + 3 PDF-adjudicated category corrections (all in test split)
           │  fixed reporting split established: 777 / 166 / 167
           ▼
           V6  m1_regulations_v6_1110_clean_fixedsplit   ◄── FROZEN, current
           │  + 4 EPF/ETF label corrections (all in train split)
           │  split preserved byte-for-byte from V5
           ├─ V7-W  m1_regulations_v6_1110_multitask_noleak   ◄── WORKING EXPERIMENT, completed and rejected
           │       1103 rows · 773 / 163 / 167 after seven exact-text duplicate/overlap exclusions
           │       original six columns retained; sector vectors/relevance derived by the trainer
           │       3-seed e8 run: category macro-F1 0.0936, sector macro-F1 0.1207
           │
           ├─ V7-F  m1_regulations_v7_1103_multitask_noleak   ◄── FORMAL ENRICHED RELEASE, not built
           │       would add stored sector_vector, category_id, relevance_label and explicit split
           │
           └─ V7-M  m1_regulations_v7_1110_multitask_fixedsplit  ◄── SECOND V7 LINE, current candidate lineage
                   1110 rows · 777 / 166 / 167 — the full V6 corpus with stored multitask fields
                   Steps 47–49 validation-only · Step 50 strict test run once and FAILED (sector macro-F1 0.888330)
                   improvement run seeds 7/13/29 → seed 13 validation-selected, NOT tested, NOT promoted

Separate, and never merged with the corpus above:

           FH-v3  research/data/labeling/fresh_locked_holdout_intake_v1
                  286 newly collected rows · evaluation-only · single-use · awaiting Step 55A lock
```

**Two distinct V7 lines exist. Do not merge their numbers.** V7-W is the 1103-row no-leak *working experiment* that collapsed and was rejected (category 0.0936). V7-M is the later 1110-row *multitask fixed-split* line that trained successfully, consumed the old test split once at Step 50, failed the strict sector gate at 0.888330, and produced the current untested seed13 candidate. They share an encoder design and nothing else — different row counts, different splits, different outcomes. Full V7-M record: §∞ V7-M multitask line.

Four rules keep the lineage clean:

1. **Legacy datasets are provenance only.** They explain how early baselines were produced, but they are not used for final model claims.
2. **The reporting split never moved from V5 to V6.** 777 train / 166 validation / 167 test, so a V5-vs-V6 score difference is a labelling effect, never a split effect. V7-M inherits the same split unchanged.
3. **Nothing was deleted from the gold history.** The 18 excluded artifacts are excluded from *ML training and evaluation only*; they remain in the adjudicated gold record.
4. **Versions are not addends.** V4, V5, V6 and V7-M are successive transformations of one 1110-row corpus, not four datasets. The project holds **1110 corpus rows + 286 fresh holdout rows = 1396 distinct rows**, and the fresh holdout's own v1/v2/v3 revisions (193 → 225 → 286) are cumulative versions of one file, not three files. Counting rules and the stage-by-stage usage table: [[22_M1_Data_Usage_and_Row_Count_Register]].

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

**Local artifact map (verified 2026-08-01):**

```text
C:\Reasearch\xyz\datasets\m1_regulations_v6_1110_clean_fixedsplit\
C:\Reasearch\xyz\kaggle_bundle\m1_regulations_v6_1110_clean_fixedsplit.zip
C:\Reasearch\xyz\kaggle_bundle\m1_regulations_v5_1110_clean_fixedsplit.zip
C:\Reasearch\xyz\kaggle_bundle\m1_v6_epf_etf_corrections\m1_v6_epf_etf_corrections_bundle.zip
C:\Reasearch\xyz\kaggle_bundle\m1_v6_epf_etf_corrections\extracted\
```

| Archive | SHA256 |
|---|---|
| `m1_regulations_v6_1110_clean_fixedsplit.zip` | `66EF4CF6FB187146641173BBB71628AD711C635FCEADE34CAB01AADDD99F35F0` |
| `m1_regulations_v5_1110_clean_fixedsplit.zip` | `E1CA910E690F59C77F9859F57BE15069E48CBC6DF9C952BC8B28106C5A25FB29` |
| `m1_v6_epf_etf_corrections_bundle.zip` | `2C9169B54C99B21241354E378172DEF8BC8071AC8FF40AAA22ED9551BD386597` |

### V7 — working experiment completed; formal enriched release not built

Two artifacts must not be conflated:

- **Executed working dataset:** `/kaggle/working/storage/datasets/m1/m1_regulations_v6_1110_multitask_noleak`. It was derived without modifying V6, removed seven exact-text duplicate/overlap records, and contains **1103 rows split 773/163/167**. It deliberately retains the original six columns; the trainer computes sector vectors and derived relevance at load time. The 3-seed e8 experiment trained on it and was rejected.
- **Formal enriched V7 release:** not built. If weighted-loss recovery ever justifies creating it, it must derive from the cleaned 1103-row working set, carry a seven-row exclusion manifest, and add stored `sector_vector`, `category_id`, `relevance_label`, and `split` fields. It must not claim to preserve all 1110 rows.

The pre-build **V6 source audit** covered all 1110 rows. V6 columns are exactly `key · text · category · sectors · language · date`; `is_sme_relevant` was absent. Joining `research/data/labeling/gold_standard_v3_1128.csv` on `regulation_key` established the following before the no-leak exclusions:

| Check | Result |
|---|---|
| Join coverage | **1110 / 1110** |
| V6 `sectors` == gold `affected_sectors` | **1110 / 1110** |
| Duplicate keys · cross-split overlap · empty text | 0 · 0 · 0 |
| Unknown categories · unknown sectors | none · none |
| `is_sme_relevant == bool(affected_sectors)` | **1109 / 1110** |
| **Total consistency errors** | **1** |

V6 lost the relevance column and nothing else. The working trainer did not materialize the recovered field: it derives the served relevance target from the sector vector so the two outputs cannot contradict.

**The single violation is a reasoned annotation, not an error.** `GZT_2492_10` (train, `IMPORT_EXPORT`) is marked SME-relevant with an empty sector list, and both annotators independently recorded the same reason at confidence 1.0: *"Export-proceeds rule affects SME exporters, but it is outside the three shop-focused study sectors; affected_sectors left blank."* Adopting `is_sme_relevant = any(sectors)` therefore **narrows** the field to *"affects at least one of the three study sectors"*. The working experiment derives this row as `false`; any formal release must preserve the original note and record the narrowing in its manifest and limitations.

**Sector label shape in the audited 1110-row V6 source** — the finding that most constrains what the sector head can claim:

| Combination | Train | Val | Test | Total | Share |
|---|---:|---:|---:|---:|---:|
| `[]` | 574 | 121 | 117 | 812 | **73.2 %** |
| all three | 172 | 36 | 42 | 250 | **22.5 %** |
| `grocery + food` | 25 | 7 | 5 | 37 | 3.3 % |
| `general` | 4 | 1 | 2 | 7 | 0.6 % |
| `food` | 2 | 0 | 0 | 2 | 0.2 % |
| `general + grocery` | 0 | 1 | 1 | 2 | 0.2 % |

84 % of sector-bearing rows carry all three; genuine partial structure is 48 rows (4.3 %). `general + grocery` has **zero training examples** and `food_service` alone has **zero validation and test examples**.

**Measured class weights (train split)** — `pos_weight` = neg/pos: `grocery_retail` 2.944 · `food_service` 2.905 · `general_retail` 3.415 · relevance 2.809.

Consequences for thresholds and promotion gates: [20_M1_Multitask_Classifier_Upgrade.md](20_M1_Multitask_Classifier_Upgrade.md) §1.4 and §6.2. Audit artifacts: `documentation/m1/analysis/multitask_dataset_audit.json` · `multitask_label_distribution.csv` · `multitask_consistency_errors.csv`.

### V7-M — `m1_regulations_v7_1110_multitask_fixedsplit` (second V7 line, current candidate lineage)

*Recorded 2026-08-02. This is a **separate later line** from the V7-W working experiment above; the V7-W figures stay as historical record and are not superseded by these.*

```text
/kaggle/working/enigmatrix-ml/datasets/m1_regulations_v7_1110_multitask_fixedsplit
```

| Property | Value |
|---|---|
| Rows | **1110** — the full V6 corpus, no no-leak exclusions |
| Split | **777 / 166 / 167**, inherited unchanged from V5/V6 |
| Difference from V7-W | keeps all 1110 rows and **stores** the multitask fields instead of deriving them at load |

Columns: `key · text · category · category_id · sectors · affected_sectors · sector_vector · is_sme_relevant · relevance_label · sector_grocery_retail · sector_food_service · sector_general_retail · sector_combo · language · date · split`.

Task heads: category = 8-way single-label · sector = 3-label multi-label · relevance = auxiliary binary diagnostic. Production relevance stays **derived** — `is_sme_relevant = bool(predicted_affected_sectors)` — and the relevance head is diagnostic only. Sector index order remains the frozen `["grocery_retail", "food_service", "general_retail"]`; there is no universal sentinel, and economy-wide instruments carry all three.

**Rebuilt checksums after the Kaggle reset:**

```text
train.parquet  2BDEF31BE676D81FA900DCFCE6CD756F0B14BF9F1B872C2A64F391C00E3786C6
val.parquet    5A8DD14AB04EB8595E31664C60DFB69A5E60090CACFAC23B65D7568F2DC95400
test.parquet   8A0BBB09028046D16E6397FCF15BB3B892F1E71195903F7AE55D271557394FFD
```

The 167-row test parquet listed here is the split that Step 50 consumed. It is retained for reproducibility of that one run and must not be scored again — see §5.8.

### Legacy L1 — `enigmatrix-ml\datasets\m1_regulations`

800 rows with a deterministic/key split of 560 / 120 / 120. This is the earliest retained ML split and is historical only. It is not comparable with V6 because `EPF_ETF_CHANGE` is absent from train and test, while the test split is dominated by `SECTOR_SPECIFIC` (115 of 120 rows).

### Legacy smoke — `enigmatrix-ml\datasets\m1_regulations_smoke`

32 rows with a 16 / 8 / 8 split. This is a CPU smoke-test fixture only. It is not a research dataset and must not be used for reported model quality.

### Legacy L2 — `enigmatrix-ml\datasets\m1_regulations_v2_1000`

1000 rows with a 700 / 150 / 150 split. Superseded. The split is not well balanced by category: `SECTOR_SPECIFIC` has 583 training rows but only 16 test rows, while some rarer categories appear mostly in validation/test. Keep only as an early experiment record.

### Legacy L2-stratified — `enigmatrix-ml\datasets\m1_regulations_v2_1000_stratified`

1000 rows with a 700 / 150 / 150 stratified split. Superseded by the larger 1128-row set, but useful as the first retained stratified classical-baseline comparison.

### Legacy L3 — `enigmatrix-ml\datasets\m1_regulations_v3_1128_stratified`

1128 rows with a 790 / 169 / 169 stratified split. This is the rare-domain baseline predecessor: it includes all eight categories, including 7 / 2 / 2 `EPF_ETF_CHANGE` rows. It is superseded by V6 for final model claims because V6 removes known artifacts, applies adjudicated corrections, and freezes the final reporting split.

All legacy folders are currently retained inside `enigmatrix-ml/datasets/`, still untracked in git (`?? datasets/`). They are the sets the module docstrings use as `--data` examples. Left in place deliberately; superseded for any result that will be reported.

Verified legacy split inventory:

| Folder | Split rows | Role now |
|---|---:|---|
| `enigmatrix-ml\datasets\m1_regulations` | 560 / 120 / 120 | V1 deterministic/key split; historical only |
| `enigmatrix-ml\datasets\m1_regulations_smoke` | 16 / 8 / 8 | CPU smoke-test fixture only |
| `enigmatrix-ml\datasets\m1_regulations_v2_1000` | 700 / 150 / 150 | superseded |
| `enigmatrix-ml\datasets\m1_regulations_v2_1000_stratified` | 700 / 150 / 150 | superseded |
| `enigmatrix-ml\datasets\m1_regulations_v3_1128_stratified` | 790 / 169 / 169 | rare-domain baseline predecessor; superseded by V6 for final model claims |

---

## 3. Models trained on these datasets

### Current/final model evidence

| Model                                     | Dataset | Val macro-F1 | Test macro-F1 | Verdict                             |
| ----------------------------------------- | ------- | -----------: | ------------: | ----------------------------------- |
| XLM-R LoRA, category-only, unweighted     | V5      |      ~0.0946 |       ~0.0936 | Collapsed to majority class         |
| XLM-R LoRA, balanced (seed 42, 16 ep)     | V5      |     0.596014 |      0.685348 | Rejected — 0 EPF predictions        |
| XLM-R LoRA, underfit-fix (seed 42, 20 ep) | V6      |     0.902693 |      0.743563 | Experimental only — failed the gate |
| **TF-IDF + balanced LinearSVC**           | **V6**  | **0.924476** |  **0.947220** | **Primary — frozen**                |
| TF-IDF + Logistic Regression              | V6      |            — |      0.882481 | Baseline reference                  |
| XLM-R LoRA, multitask (3 seeds, 8 ep)      | V7-W 1103 |          — | category **0.0936**; sector **0.1207** | Rejected — collapsed; never promoted |
| XLM-R LoRA, weighted multitask (seed 42, 15 ep) | V7-W 1103 | category **0.899862**; sector **0.884312** | **not read** | Validation diagnostic only — partial exact `4/9`; stopped before final run |
| XLM-R LoRA multitask, diagnostic (seed 42, 20 ep) | V7-M 1110 | category **0.91096**; sector **0.92428** *(tuned)* | **not read** | Diagnostic only — Step 47/48, promoted nothing |
| XLM-R LoRA multitask, 3-seed validation-only (42/1/2) | V7-M 1110 | best seed 42 selection **0.91794** | **not read** | Step 49 — validation-only, no test load |
| XLM-R LoRA multitask, **strict Step 50 candidate (seed 1)** | V7-M 1110 | — | category **0.910533**; sector **0.888330**; sector-exact **0.916168**; relevance **0.92** | **Strict gate FAILED** (sector < 0.90) — archived, not promoted, **test split now consumed** |
| **XLM-R LoRA multitask, improvement candidate (seed 13, 24 ep)** | **V7-M 1110** | category **0.929558**; sector **0.927620**; sector-exact **0.957831**; relevance **0.936170** | **NOT TESTED** | **Current candidate** — validation-selected only, `promotion_allowed = false`, awaiting locked fresh-holdout evaluation |

The last four rows are the **V7-M line** and are recorded in full in §∞ V7-M multitask line. Only one of them ever touched a test split — the Step 50 seed-1 candidate — and that single read is what consumed the V7-M test split. The seed13 row's validation figures are **not** promotion evidence; they are selection evidence, and the model has never seen held-out data of any kind.

The weighted row is deliberately not a new final model result. It used only the no-leak 773-row training and 163-row validation branches, wrote no promotable checkpoint, and did not load the V6 test split. It demonstrates optimization recovery, while its below-gate category score and nine-row partial-sector denominator demonstrate why a fresh temporal holdout plus genuine EPF/ETF and partial-sector examples are required before another claim.

### Historical legacy model records

These rows explain the path to the frozen model. They should not be mixed into final claims about production performance because the data versions, splits and label corrections differ from V6.

| Model | Dataset / run | Val macro-F1 | Test macro-F1 | Record source | Status |
|---|---|---:|---:|---|---|
| TF-IDF + Logistic Regression | V1 deterministic/key | — | 0.498039 | archived Kaggle `baselines_v1/baselines.json` | historical |
| TF-IDF + balanced LinearSVC | V1 deterministic/key | — | 0.616745 | archived Kaggle `baselines_v1/baselines.json` | historical |
| TF-IDF + Logistic Regression | V1 stratified archived run | — | 0.771087 | archived Kaggle `baselines_v1_stratified/baselines.json` | historical |
| TF-IDF + balanced LinearSVC | V1 stratified archived run | — | 0.789365 | archived Kaggle `baselines_v1_stratified/baselines.json` | historical |
| TF-IDF + Logistic Regression | V2 1000 | — | 0.294196 | local `baselines_v2_1000/baselines.json` | superseded |
| TF-IDF + balanced LinearSVC | V2 1000 | — | 0.210263 | local `baselines_v2_1000/baselines.json` | superseded |
| TF-IDF + Logistic Regression | V2 1000 stratified | — | 0.698545 | local `baselines_v2_1000_stratified/baselines.json` | superseded |
| TF-IDF + balanced LinearSVC | V2 1000 stratified | — | 0.808523 | local `baselines_v2_1000_stratified/baselines.json` | superseded |
| TF-IDF + Logistic Regression | V3 1128 stratified | — | 0.862652 | local `baselines_v3_1128_stratified/baselines.json` | rare-domain predecessor |
| TF-IDF + balanced LinearSVC | V3 1128 stratified | — | 0.908012 | local `baselines_v3_1128_stratified/baselines.json` | rare-domain predecessor |

Archived V1 GPU records also exist under `storage/models/m1/kaggle_v1/kaggle/working/storage/models/m1/`: `xlmr_lora_v1_seed42_diag` (val 0.154762, test 0.155556), `xlmr_lora_v1_fixed_seed42` (val 0.266328, test 0.487084), and `xlmr_lora_v1_catonly_seed42_e16` (val 0.403285, test 0.641471). All failed the gate and are retained for chronology only.

There is also a separate local `baselines_v1/baselines.json` rerun with LogReg 0.743363 and LinearSVC 0.872826. Do not cite it as the archived Kaggle V1 result unless the rerun command and local dataset state are included.

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

1. **The V6 test split is spent.** It was used for the frozen-model comparison and again by the rejected V7 working experiment. Do not tune, select, or make a new final claim on it; any recovery run needs a fresh temporal holdout, nested CV, or newly collected data. **(2026-08-02: satisfied — a fresh, leakage-verified 286-row holdout now exists. See §∞ Fresh locked holdout v3.)**
2. **`EPF_ETF_CHANGE` needs real data, not resampling.** 4 train / 1 test rows. **(2026-08-02: three independent searches of all 39,649 indexed extraordinary gazette items returned zero genuine EPF/ETF instruments. This class is not obtainable from gazettes; it needs Department of Labour EPF circulars or Central Bank notices, or an explicit out-of-scope declaration. See §∞ Fresh locked holdout v3.)**
3. **Do not rename or move `datasets/` or `models/`.** Their paths are recorded inside `model_registry.json`, `SHA256SUMS.json`, `local_windows_verification.json` and the frozen record.
4. **Re-derive, don't hand-edit.** Every table here is regenerable from the record generator; if a number changes, change the source and regenerate.
5. **The sector label space is nearly degenerate.** 73.2 % of rows carry no sector and 84 % of the remainder carry all three. Collecting **partial-sector** regulations — ones affecting one or two of the three study sectors — is now a higher-value annotation target than general volume, because it is the only thing that turns the sector head from a relevance detector into a sector classifier. **(2026-08-02: satisfied for evaluation — the fresh holdout is 46.9 % no-sector and 93.4 % partial among its sector-positive rows. Still open for training data, which that artifact must never become.)**
6. **`CATEGORIES` and `SECTORS` index order is a contract.** `SECTORS = ["grocery_retail", "food_service", "general_retail"]` is frozen. A `sector_vector` written under one order and read under another is silently wrong, so the order ships in `labels.json` *and* in `model_registry.json`, and is asserted at load.

Two further constraints are declared in the dated sections below and are equally binding:

7. **The fresh holdout is evaluation-only and single-use** — §∞ Fresh locked holdout v3.
8. **The V7-M test split is consumed; old Step 50 must never be rerun** — §∞ V7-M multitask line.

The full limitation set, with severity and required lock-manifest wording, is [[21_M1_Data_Limitations_and_Risk_Register]].

---

## 6. Kaggle and local recovery commands

Use this section when the final report needs the exact dataset/model metric evidence from Kaggle or the local downloaded bundle.

### Kaggle input locations

```text
Original Kaggle project dataset:
/kaggle/input/datasets/ifhammohamed1/m1-training-v1/enigmatrix-ml

Legacy V1 dataset inside original Kaggle project dataset:
/kaggle/input/datasets/ifhammohamed1/m1-training-v1/enigmatrix-ml/datasets/m1_regulations

V6 Kaggle input dataset:
/kaggle/input/datasets/ifhammohamed1/m1-regulations-v6-1110-clean-fixed-split/m1_regulations_v6_1110_clean_fixedsplit

Kaggle working model artifact:
/kaggle/working/storage/models/m1/linearsvc_v6_primary
```

Current Kaggle inputs verified from the notebook expose V1, V5 and V6. V2, V2-stratified and V3 will print as missing unless those legacy folders are attached/uploaded as a Kaggle dataset.

### Discover attached legacy datasets in Kaggle

Run this first. It finds the dataset folders wherever Kaggle mounted them and prints exact split counts, class distributions and Parquet hashes.

```python
from pathlib import Path
import hashlib
import json
import pandas as pd

SPLITS = ("train", "val", "test")
LEGACY_NAMES = [
    "m1_regulations",
    "m1_regulations_smoke",
    "m1_regulations_v2_1000",
    "m1_regulations_v2_1000_stratified",
    "m1_regulations_v3_1128_stratified",
]

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()

def find_dataset_dir(name: str) -> Path | None:
    for path in Path("/kaggle/input").rglob(name):
        if path.is_dir() and all((path / f"{split}.parquet").exists() for split in SPLITS):
            return path
    return None

report = {}
for name in LEGACY_NAMES:
    base = find_dataset_dir(name)
    if base is None:
        report[name] = {"status": "missing_from_attached_kaggle_inputs"}
        continue

    report[name] = {"status": "found", "path": str(base), "splits": {}}
    for split in SPLITS:
        parquet = base / f"{split}.parquet"
        df = pd.read_parquet(parquet)
        report[name]["splits"][split] = {
            "rows": int(len(df)),
            "sha256": sha256_file(parquet),
            "category_counts": {
                str(k): int(v)
                for k, v in df["category"].value_counts().sort_index().items()
            },
        }

print(json.dumps(report, indent=2))
```

### Rebuild legacy classical baseline scores in Kaggle

Run this only after the discovery cell. It copies the codebase into `/kaggle/working`, then runs the project baseline command against every attached legacy dataset.

```python
from pathlib import Path
import json
import shutil
import subprocess
import sys

SPLITS = ("train", "val", "test")
LEGACY_NAMES = [
    "m1_regulations",
    "m1_regulations_smoke",
    "m1_regulations_v2_1000",
    "m1_regulations_v2_1000_stratified",
    "m1_regulations_v3_1128_stratified",
]

def find_dataset_dir(name: str) -> Path | None:
    for path in Path("/kaggle/input").rglob(name):
        if path.is_dir() and all((path / f"{split}.parquet").exists() for split in SPLITS):
            return path
    return None

CODE_INPUT = Path("/kaggle/input/datasets/ifhammohamed1/m1-training-v1/enigmatrix-ml")
CODE_WORK = Path("/kaggle/working/enigmatrix-ml")

if CODE_WORK.exists():
    shutil.rmtree(CODE_WORK)
shutil.copytree(CODE_INPUT, CODE_WORK)

subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "pandas", "pyarrow", "scikit-learn"],
    check=True,
)

baseline_results = {}
for name in LEGACY_NAMES:
    base = find_dataset_dir(name)
    if base is None or name == "m1_regulations_smoke":
        continue

    out = Path("/kaggle/working/storage/models/m1") / f"baselines_{name}"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "m1.model.baselines",
            "--data",
            str(base),
            "--report",
            str(out),
        ],
        cwd=CODE_WORK,
        check=True,
    )
    baseline_results[name] = json.loads((out / "baselines.json").read_text())

print(json.dumps(baseline_results, indent=2))
```

Expected locally verified legacy score records:

| Dataset | LogReg test macro-F1 | LinearSVC test macro-F1 |
|---|---:|---:|
| V1 deterministic/key, archived Kaggle | 0.498039 | 0.616745 |
| V1 stratified archived run | 0.771087 | 0.789365 |
| V2 1000 | 0.294196 | 0.210263 |
| V2 1000 stratified | 0.698545 | 0.808523 |
| V3 1128 stratified | 0.862652 | 0.908012 |

### Find any saved metric JSON files in Kaggle

Use this instead of opening one hard-coded path. It avoids `FileNotFoundError` when the model artifact is not present in the current Kaggle session.

```python
from pathlib import Path
import json

patterns = ["baselines.json", "metrics.json", "model_registry.json", "validation_summary.json", "test_summary.json"]
roots = [Path("/kaggle/working"), Path("/kaggle/input")]

found = []
for root in roots:
    for pattern in patterns:
        found.extend(root.rglob(pattern))

print("FOUND FILES:", len(found))
for path in sorted(set(found)):
    print("\n" + "=" * 100)
    print(path)
    print("=" * 100)
    try:
        print(json.dumps(json.loads(path.read_text()), indent=2))
    except Exception as exc:
        print(f"Could not parse JSON: {exc}")
```

### Print the frozen model metrics in Kaggle

```bash
python - <<'PY'
import json
from pathlib import Path

model_dir = Path("/kaggle/working/storage/models/m1/linearsvc_v6_primary")
for name in ["model_registry.json", "validation_summary.json", "test_summary.json"]:
    path = model_dir / name
    print(f"\n== {path} ==")
    print(json.dumps(json.loads(path.read_text()), indent=2))
PY
```

### Print the V6 dataset split distribution in Kaggle

```bash
python - <<'PY'
from pathlib import Path
import pandas as pd

base = Path("/kaggle/working/enigmatrix-ml/datasets/m1_regulations_v6_1110_clean_fixedsplit")
if not base.exists():
    base = Path("/kaggle/input/datasets/ifhammohamed1/m1-regulations-v6-1110-clean-fixed-split/m1_regulations_v6_1110_clean_fixedsplit")

for split in ["train", "val", "test"]:
    df = pd.read_parquet(base / f"{split}.parquet")
    print(f"\n{split}: {len(df)} rows")
    print(df["category"].value_counts().sort_index().to_string())
PY
```

### Re-score the frozen LinearSVC locally after downloading from Kaggle

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml
uv run python - <<'PY'
from pathlib import Path
import joblib
import pandas as pd
from sklearn.metrics import classification_report, f1_score, accuracy_score

model_path = Path(r"C:\Reasearch\xyz\models\m1\linearsvc_v6_primary\linearsvc_pipeline.joblib")
test_path = Path(r"C:\Reasearch\xyz\datasets\m1_regulations_v6_1110_clean_fixedsplit\test.parquet")

model = joblib.load(model_path)
df = pd.read_parquet(test_path)
pred = model.predict(df["text"].fillna("").astype(str))
y = df["category"].astype(str)

print("rows", len(df))
print("macro_f1", f1_score(y, pred, average="macro"))
print("accuracy", accuracy_score(y, pred))
print(classification_report(y, pred, digits=6))
PY
```

Expected local result: macro-F1 `0.9472199858964565`, accuracy `0.9580838323353293`, 160/167 correct.

### Kaggle CLI recovery commands

Run these on Windows only if Kaggle API credentials are configured.

```powershell
kaggle datasets download ifhammohamed1/m1-regulations-v6-1110-clean-fixed-split `
  -p C:\Reasearch\xyz\kaggle_bundle `
  --unzip

kaggle datasets download ifhammohamed1/m1-training-v1 `
  -p C:\Reasearch\xyz\kaggle_bundle\m1-training-v1 `
  --unzip
```

If a future correction bundle is uploaded as its own Kaggle dataset, download it the same way and verify its SHA256 before deriving a new dataset version.

---

## 7. Cross-references

- **Training method and metrics:** [[06_M1_Training_Evaluation]]
- **Architecture and sampling:** [[05_M1_Model_Architecture]]
- **Annotation, taxonomy and IAA protocol:** [[09_M1_Annotation_Guidelines]]
- **Physical layout of `datasets/` and `models/`:** [[17_M1_Repo_Structure_Map]]
- **Duplicate-text disclosure (dataset-card addendum):** §∞ below
- **Full chronology with every epoch and error:** `documentation/m1/records/ENIGMATRIX_M1_COMPLETE_END_TO_END_RECORD_2026-07-31_2313_IST.md`

---

## ∞ Duplicate-text disclosure — V6 (2026-08-03)

*Dataset-card addendum requested by [[23_M1_Retrieval_Augmented_Evidence_Branch|23_M1_Retrieval_Augmented_Evidence_Branch]] §7.2. Produced by `enigmatrix-ml/scripts/inventory_m1_datasets.py` against the V6 files on disk. Full session record: [[2026-08-03_Branch_C_Retrieval_Evidence_Implementation|2026-08-03_Branch_C_Retrieval_Evidence_Implementation]].*

### What is in the canonical V6 split

`m1_regulations_v6_1110_clean_fixedsplit` (777 / 166 / 167) contains **8 groups of byte-identical text under different keys** — 16 rows, all `SECTOR_SPECIFIC`. Three groups straddle train↔val:

| Group | Keys | Splits | Chars |
|---|---|---|---|
| dup_001 | `GZT_2483_26`, `GZT_2483_31` | **train + val** | 1176 |
| dup_002 | `GZT_2483_46`, `GZT_2483_54` | **train + val** | 404 |
| dup_003 | `GZT_2493_63`, `GZT_2493_64` | **train + val** | 348 |
| dup_004 | `GZT_2469_26`, `GZT_2469_27` | train | 338 |
| dup_005 | `GZT_2483_59`, `GZT_2483_63` | test | 1223 |
| dup_006 | `GZT_2485_45`, `GZT_2488_65` | train | 1190 |
| dup_007 | `GZT_2487_18`, `GZT_2487_19` | train | 348 |
| dup_008 | `GZT_2493_95`, `GZT_2495_13` | train | 447 |

This reproduces the Step-41 audit ("8 within-split duplicate-text rows and 6 train–val overlap rows") exactly, independently, on the current files.

### Why `dataset_manifest_v6.json` reports zero leakage

The manifest's `leakage: {train_val: 0, train_test: 0, val_test: 0}` is **true as written**. It is a *key*-based check and the keys genuinely do not overlap. It cannot detect the same text filed under two different keys. This is a gap in the check, not an incorrect entry — and it is why the audit now also hashes text.

### Effect on the recorded numbers

> [!warning] Validation macro-F1 0.9245 is optimistic; test macro-F1 0.9472 is not.
> **3 of 166 validation rows (1.8%)** are byte-identical to a training row. The direction of the bias is known; the magnitude is **not**, because the model may have classified those rows correctly regardless. There is **no train↔test text duplication** — dup_005 is a test↔test pair — so the temporal test number is unaffected. **Quote the test number.**

### Why the de-leaked split is not the canonical one

A cleaned 1103-row / 773-163-167 variant was built and appears in [[22_M1_Data_Usage_and_Row_Count_Register|22_M1_Data_Usage_and_Row_Count_Register]] as the **"V7-W working"** row. That experiment collapsed and was rejected, and the de-leaked artifact went with it — it does not exist in `datasets/`. `linearsvc_v6_primary` is therefore registered against the 1110-row split that still contains the 6 overlap rows.

### The 18 excluded OCR-noise rows

`dataset_manifest.json` records `excluded_ocr_noise_rows: 18` for the V4→V5 clean step. Their full text was extracted for the first time on 2026-08-03 and the exclusion is **confirmed correct**: lengths 2–26 characters, median 8, all labelled `SECTOR_SPECIFIC`.

```
GZT_2469_28 (5 chars):  '1A 2A'
GZT_2471_06 (2 chars):  '2A'
GZT_2471_08 (12 chars): '2A BWග 4A 6A'
GZT_2471_11 (17 chars): '1A 2A 3A 4A 5A 6A'
```

They are retrievable for re-inspection in `datasets/m1_regulations_unified_v6core/excluded_rows_for_review.csv` and are never training data.

### Undocumented V5 whitespace normalisation

V4_clean and V5 have **identical 1110-key sets**. 409 texts differ byte-for-byte between them but **0 differ after whitespace normalisation** — V5 applied a whitespace clean-up that its manifest records only as 3 label changes. Benign, recorded here for completeness.

### Open decision

Two defensible dispositions, and this is a lineage call rather than a cleanup task:

1. **Keep V6 as-is and caveat the validation number** with the 1.8% disclosure above. Zero risk; the frozen primary stays comparable. *Current state.*
2. **Rebuild the 1103-row de-leaked split as a canonical artifact and re-measure Branch A on it.** This invalidates the recorded 0.9245, changes the validation split, and requires a re-freeze plus a new registry entry.

Either way: **on the next re-split, deduplicate on normalised text hash, not just on `key`.** That is the fix for this entire class of defect, and it is one line of the split script.

---

## ∞ Final-report reconciliation (2026-08-02)

*Added by the 2026-08-02 consolidation pass. Maps this document onto the submitted final report and records where the two disagree.*

**Where this document appears in the report:** Part I Table 6.1 (datasets used in this project), Table 6.2 (columns of the frozen gold dataset), Table 7.3 (change category distribution) and Table 7.4 (train / validation / test split).

### Where the report's dataset tables are wrong

The report's Table 7.3 and Table 7.4 describe the **v1 800-row set with a 560 / 120 / 120 split**. That is the L1 legacy branch in §1 of this document — provenance only, not a reporting artifact. The reporting branch is V4 → V5 → V6 with the fixed **777 / 166 / 167** split.

Anyone reading the report alone will attribute the module's results to the wrong dataset. If the report is revised, Tables 7.3 and 7.4 are the first things to replace.

### The three rules, restated

1. **Legacy datasets are provenance only.** They explain how early baselines were produced; they are not used for final model claims.
2. **The reporting split never moved from V5 to V6.** A V5-vs-V6 score difference is a labelling effect, never a split effect.
3. **Nothing was deleted from the gold history.** The 18 excluded artifacts are excluded from ML training and evaluation only; they remain in the adjudicated gold record.

### V7 status, for the record

`V7-W` (`m1_regulations_v6_1110_multitask_noleak`, 1103 rows, 773 / 163 / 167) ran to completion and was **rejected**: test category macro-F1 0.0936, sector micro-F1 0.2113, derived relevance accuracy 0.5948. `V7-F`, the formal enriched release with stored `sector_vector` / `category_id` / `relevance_label`, was **never built**. The frozen `linearsvc_v6_primary` is untouched by any of it.

---

## ∞ Fresh locked holdout v3 (2026-08-02) — the standing constraint answered

*Added by the 2026-08-02 holdout collection pass. §5.1 of this document required "a fresh temporal holdout, nested CV, or newly collected data" before any new final claim. This section records the newly collected data and what it does and does not fix. Collection methodology is in [[03_M1_Data_Collection]] §∞ Step 54A.*

### The artifact

`research/data/labeling/fresh_locked_holdout_intake_v1/fresh_holdout_label_template.csv`

| Property | Value |
|---|---|
| Rows | **286** (`fresh-v1-001` … `fresh-v1-286`) |
| Distinct source gazettes | 286 — one row per gazette, no internal duplicates |
| Date range | 2010-01-27 → 2025-12-23 |
| Language | 100 % English (`_E` PDFs) |
| Schema | the 12 intake columns, all populated |
| Annotator | ifham, from the row's own page-1 text |
| Provenance | `fresh_holdout_provenance_report.csv`, per-row category and sector reasoning plus duplicate-check status |

**Leakage status: clean.** Zero gazette-id overlap with the 1,128 consumed gazette ids across V6 train/val/test and the Kaggle bundle. Zero exact-text overlap against 1,910 consumed rows. Zero duplicate text within the holdout. Max 8-gram Jaccard among accepted rows 0.489, below the 0.50 near-duplicate threshold. Re-verified on the full merged set after each of the two collection rounds.

### Label distribution

| Category | Rows | Spec target | |
|---|---:|---:|---|
| LABOUR_LAW | 88 | ~20 | met |
| SECTOR_SPECIFIC | 59 | ~45 | met |
| TAX_RATE_CHANGE | 58 | ~20 | met |
| PRODUCT_STANDARD | 30 | ~20 | met |
| IMPORT_EXPORT | 22 | ~20 | met |
| BUSINESS_REGISTRATION | 16 | ~12 | met |
| PENALTY_ENFORCEMENT | 10 | ~15 | short |
| EPF_ETF_CHANGE | 3 | ~8 | short |

| Sector | Positive rows | Minimum | |
|---|---:|---:|---|
| grocery_retail | 136 | 20 | met |
| food_service | 88 | 20 | met |
| general_retail | 29 | 20 | met |

`is_sme_relevant`: 152 true / 134 false.

### This directly answers §5.5 — the partial-sector constraint

§5.5 records that the sector label space in V6 is nearly degenerate: **73.2 % of rows carry no sector and 84 % of the remainder carry all three**, and names partial-sector regulations as a higher-value annotation target than general volume.

The v3 holdout inverts that shape:

| | V6 training data | v3 holdout |
|---|---:|---:|
| rows with no sector | 73.2 % | **46.9 %** |
| of sector-positive rows, carrying all three | 84 % | **6.6 %** |
| of sector-positive rows, carrying one or two | 16 % | **93.4 %** |

142 of the 152 sector-positive rows are partial. The combination spread is: grocery_retail + food_service 73, grocery_retail alone 46, general_retail alone 11, all three 10, grocery_retail + general_retail 7, food_service alone 4, food_service + general_retail 1.

This is the first dataset in the project where the sector head could be evaluated as a sector classifier rather than a relevance detector.

### What it does not fix

**`EPF_ETF_CHANGE` remains 3 rows, and §5.2 should now be read as a source finding rather than a collection backlog.** Three independent searches across all 39,649 indexed extraordinary gazette items returned zero genuine EPF or ETF instruments. This is not a search-quality problem: EPF and ETF rules are published through Department of Labour circulars and Central Bank notices, not extraordinary gazettes. The three rows carried here are provincial Co-operative Employees' Pension Scheme instruments, which are contributory employee-fund rules but not EPF or ETF proper. Either source those channels separately, or declare `EPF_ETF_CHANGE` out of scope for this holdout and record it as a limitation. Blocking a lock indefinitely on a class the source cannot supply is the worse option.

**`PENALTY_ENFORCEMENT` is 10 rows and all 10 carry `affected_sectors = NONE`.** What gazette titles surface are property forfeitures, provincial court-fines statutes, a prosecution-jurisdiction regulation and sports-offence investigation units. None imposes an offence, fine or inspection duty on a grocery, food-service or general retail business. The SME-facing offence provisions do exist — inside the Schedules of the Pradeshiya Sabha and Municipal Council trade by-laws, several of which are already in this set — but those Schedules sit on page 2 and later and the extraction is page-1 only. Reaching them means changing the extraction scope for that instrument family, which would make those rows structurally unlike the other 280.

**`IMPORT_EXPORT` is 22 rows of which 21 carry `NONE`.** Same page-1 cause: Imports and Exports (Control) regulations carry their controlled-goods Schedules beyond page 1, so the category is testable but sector attribution within it is not.

### Standing-constraint updates

- **§5.1 (V6 test split spent)** — still binding, but the precondition it names is now satisfied. A fresh, leakage-verified holdout exists.
- **§5.2 (`EPF_ETF_CHANGE` needs real data)** — reclassify from "next annotation round should target it" to "not obtainable from extraordinary gazettes; needs Department of Labour or Central Bank sources, or an explicit out-of-scope declaration".
- **§5.5 (partial-sector is the higher-value target)** — substantially satisfied for evaluation purposes by this holdout (93.4 % partial among positives). It remains open for *training* data, which this artifact must never become.

### Standing constraint added

7. **The fresh holdout is evaluation-only and single-use.** It must not be added to any training split, used for threshold selection, or read more than once for a promotion decision. Its value is entirely in never having been seen. Row-level provenance and the gate criteria are recorded so a future reader can re-verify rather than re-trust.

### Open decision before locking

286 rows exceeds the 150–200 window in the original intake spec, which was written for the intake stage. `LABOUR_LAW` (88) and `TAX_RATE_CHANGE` (58) are internally formulaic — 25 near-identical cocoa/cardamom/pepper cost-of-living allowance notices, 42 single-employer industrial dispute and collective agreement notices, 54 Special Commodity Levy orders. Subsampling those two families would restore the row count and lift every other class's relative weight without touching category coverage or the sector minimums. Not done unilaterally: it is a research-design decision, and the full 286 remains the reproducible base either way.

---

## ∞ V7-M multitask line (2026-08-02) — the strict-gate failure and the untested seed13 candidate

*Added by the 2026-08-02 lineage pass. This records a **second, later V7 line** trained on the full 1110-row `m1_regulations_v7_1110_multitask_fixedsplit`. It does not supersede the V7-W 1103-row working experiment recorded in §2 and §3 — that remains the historical record of the collapsed run. These are two separate lines with different row counts, different splits and different outcomes.*

### Why this line exists

V7-W collapsed to majority-class behaviour (category macro-F1 0.0936). V7-M rebuilt the multitask dataset on the full 1110 rows with **stored** rather than derived multitask fields, and trained with explicit class weights, a weighted sampler and per-head loss weights. It did not collapse. It reached the strict promotion gate, and failed it on one metric.

### Step 47 — single-seed diagnostic (validation only)

Seed 42, best epoch 18, `diagnostic_only = true`, test split never loaded.

| Metric | Value |
|---|---:|
| selection_score | 0.9117 |
| category macro-F1 | 0.91096 |
| sector macro-F1 | 0.91249 |
| sector exact match | 0.93373 |
| relevance F1 | 0.9072 |
| aux relevance F1 | 0.9263 |

### Step 48 — threshold tuning on validation

Thresholds `grocery_retail 0.45 · food_service 0.45 · general_retail 0.70` lifted the same checkpoint to sector macro-F1 **0.92428**, sector exact **0.95181**, relevance F1 **0.9263**, selection score **0.91762**. Category is unchanged by thresholds (0.91096) because it is argmax over a softmax.

### Step 49 — three-seed validation-only run

`/kaggle/working/storage/models/m1/xlmr_lora_v7_multitask_final_validation_only_3seed_e20`

| Seed | selection | category macro | sector macro |
|---:|---:|---:|---:|
| 42 | 0.91794 | 0.91385 | 0.92202 |
| 1  | 0.91666 | 0.93214 | 0.90119 |
| 2  | 0.90886 | 0.91858 | 0.89914 |

No test split was loaded during this run.

### Step 50 — the strict test, run once, failed

Candidate: **seed 1**, thresholds `grocery_retail 0.50 · food_service 0.60 · general_retail 0.75`. Evaluated once against the 167-row V7-M test split.

| Metric | Result | Gate | Passed |
|---|---:|---:|:--:|
| category macro-F1 | 0.910533 | ≥ 0.90 | ✅ |
| relevance F1 | 0.92 | ≥ 0.90 | ✅ |
| sector exact match | 0.916168 | ≥ 0.90 | ✅ |
| **sector macro-F1** | **0.888330** | **≥ 0.90** | ❌ |
| prediction consistency | 1.0 | = 1.0 | ✅ |

Supporting figures: category weighted-F1 0.942027, category accuracy 0.940120, sector micro-F1 0.888889, sector Hamming loss 0.061876, relevance accuracy 0.952096, aux relevance F1 0.891089, selection score 0.899432.

**Verdict: `STRICT_GATE_PASSED = FALSE`. Do not promote. Do not rerun.**

The failure margin is 0.0117 on one metric. Per-sector, the shortfall is concentrated in the two rarer sectors:

| Sector | Threshold | TP | TN | FP | FN | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| grocery_retail | 0.50 | 44 | 114 | 5 | 4 | 0.897959 | 0.916667 | **0.907216** | 48 |
| food_service | 0.60 | 42 | 114 | 6 | 5 | 0.875 | 0.893617 | **0.884211** | 47 |
| general_retail | 0.75 | 38 | 118 | 4 | 7 | 0.904762 | 0.844444 | **0.873563** | 45 |

Error overlap across the 167 rows: 145 clean · 8 category-only · 6 sector-only · 6 sector + relevance · 2 all three. Totals: 10 category errors, 14 sector errors, 8 relevance errors. `general_retail` recall (0.844) at threshold 0.75 is the single largest contributor — the threshold was tuned for precision on a validation split where general_retail is thin.

Archived, not deleted:

```text
/kaggle/working/storage/models/m1/xlmr_lora_v7_multitask_strict_gate_failed_archive
bundle  ...strict_gate_failed_archive.zip
SHA256  CC0080B9A92A6408AFB44A3812E4E0E1621C4279C3EEE3F26456E506CA5A2AA3
status  FAILED_STRICT_GATE · ARCHIVED · NOT PROMOTED
```

### What the failure consumed

**The V7-M 167-row test split is now spent.** It was read once, under a pre-declared gate, and the result was a rejection. That single read exhausts it:

- Old Step 50 must not be rerun.
- Its 167 rows must not be used to select, tune, threshold or compare any later candidate.
- Its per-row errors must not be inspected to guide the next architecture — reading the error table *is* tuning on the test set.
- No later promotion claim may cite it.

This is the constraint that made the fresh holdout necessary. The same rule that retired the V6 test split (§5.1) now applies to V7-M's.

### The improvement run — seeds 7, 13, 29 (validation only)

`/kaggle/working/storage/models/m1/xlmr_lora_v7_multitask_improvement_validation_only_sector_focus_e24`

Sector-focused configuration: `xlm-roberta-base`, LoRA r=16, 24 epochs, batch 16, max_length 512, head LR 1e-3, LoRA LR 2e-4, **sector_loss_weight 0.45**, relevance_loss_weight 0.03, sampling_alpha 0.65, loss_weight_cap 4.0, sector/relevance pos-weight caps 8.0, grad-clip 1.0, patience 6, fp16. Safety flags recorded in the run: `diagnostic_only: true`, `test_split_loaded: false`, `promotion_allowed: false`.

| Seed | Best epoch | selection | category macro | sector macro | sector exact | relevance F1 |
|---:|---:|---:|---:|---:|---:|---:|
| **13** | **21** | **0.926686** | **0.929558** | **0.923813** | **0.951807** | **0.926316** |
| 7 | 20 | 0.912371 | 0.923732 | 0.901010 | 0.939759 | 0.914894 |
| 29 | 20 | 0.904222 | 0.903170 | 0.905274 | 0.939759 | 0.926316 |

**Seed 13 selected on validation.** Thresholds re-tuned on validation only: `grocery_retail 0.45 · food_service 0.45 · general_retail 0.75`.

| Tuned validation metric | Value |
|---|---:|
| category macro-F1 | 0.929558 |
| category weighted-F1 | 0.934945 |
| category accuracy | 0.933735 |
| sector macro-F1 | 0.927620 |
| sector micro-F1 | 0.927757 |
| sector exact match | 0.957831 |
| sector Hamming loss | 0.038153 |
| relevance F1 | 0.936170 |
| relevance accuracy | 0.963855 |
| selection score | 0.928589 |
| sector-focus selection score | 0.928395 |
| aux relevance F1 | 0.936170 |

Run flags at archive time: `test_evaluation_completed: false`, `final_test_split_loaded_for_evaluation: false`, `promotion_allowed: false`.

### The current candidate artifact

```text
/kaggle/working/storage/models/m1/xlmr_lora_v7_multitask_improvement_validation_only_candidate_seed13_not_tested
bundle       ...candidate_seed13_not_tested.zip
bundle SHA256  1964A346CFDA3659BB4D511872D87F46D8B896D5D4D0E3EB334B77A1C47690D9
model  SHA256  7739501786B8501C247397D9E72D37CF4FF8C7D1C3F5494215980C8AAB5FFB26

status                   VALIDATION_SELECTED_ONLY_NOT_TESTED
promotion_allowed        false
old_step50_consumed      true
old_step50_do_not_rerun  true
```

The name carries the status on purpose. This model has been selected but never measured against held-out data. Its validation sector macro-F1 (0.927620) sits **0.039 above** the figure that failed the gate on real test data (0.888330) — and the earlier candidate's validation-to-test drop was of exactly that order. Treating the validation number as a promotion result would repeat the mistake the strict gate was built to catch.

### How this connects to the fresh holdout

| | V6 test | V7-M test | Fresh holdout v3 |
|---|---|---|---|
| Rows | 167 | 167 | **286** |
| Status | spent (§5.1) | **spent — Step 50** | **unread** |
| May be used for | nothing further | nothing further | one locked evaluation |

The seed13 candidate has exactly one unspent evaluation surface left in the project. Spending it before the lock validation passes would leave the project with a candidate and no way to test it.

### Sequenced next steps

| Step | Work | Precondition | State |
|---|---|---|---|
| **55A** | Fresh Holdout v3 lock validation | v3 uploaded to Kaggle | **next action** |
| 55B | One-time evaluation of seed13 on locked v3 | 55A passed | blocked |
| 56 | Promotion decision + export/freeze | 55B gate passed | blocked |

Step 55A performs schema and label validation, recomputes distributions, records limitations and writes the locked manifest. **It runs no model.** Step 55B loads the seed13 candidate with the frozen validation thresholds (`0.45 / 0.45 / 0.75`), evaluates once, and reports with the declared limitations attached. Thresholds must not be re-tuned on v3 — tuning on the holdout converts it into a validation set and destroys the only unspent surface.

Upload folder and file manifest: [[03_M1_Data_Collection]] §∞ Step 54A. Evaluation and reporting protocol: [[06_M1_Training_Evaluation]] §∞ Step 55A/55B. Limitations to carry into the manifest: [[21_M1_Data_Limitations_and_Risk_Register]]. Row-count and usage rules: [[22_M1_Data_Usage_and_Row_Count_Register]].

### Standing constraint added

8. **The V7-M test split is consumed and old Step 50 must never be rerun.** One pre-declared read, one rejection, done. No later candidate may be selected, tuned, thresholded or compared using those 167 rows or their error table, and no promotion claim may cite them. Promotion now requires the locked fresh holdout or another newly collected set.

---

## ∞ · RA-HMT model lineage — 2026-08-03

A sixth model line now exists. It does **not** replace the frozen primary; the artifact,
its SHA256 and the confidence contract recorded above are unchanged.

### Line: Gazette-SME-RA-HMT (V7 fixed split, 777 / 166 / 167)

| Component | Artefact | Notes |
|---|---|---|
| Branch A | `results/branch_a/branch_a_models.joblib` (10.3 MB) | TF-IDF **word + char** n-grams, `CalibratedClassifierCV`, three targets, 5-fold OOF. Distinct from `linearsvc_v6_primary`, which is word-only, uncalibrated and category-only |
| Branch B | `results/branch_b/{lora_adapter/, heads.pt, tokenizer/}` | LoRA adapter 3.5 MB + three task heads 39 KB. Base `xlm-roberta-base` @ `e73636d4f797dec63c3081bb6ed5c7b0bb3f2089` is **not** in the bundle |
| Branch C | `results/branch_c/{index_train.npz, index_labels.csv}` | 777 × 768 float32, L2-normalised, train rows only. Encoder `intfloat/multilingual-e5-base` @ `d128750597153bb5987e10b1c3493a34e5a4502a` |
| Fusion | `results/fusion/fusion_config.json` | `tfidf 0.35 · retrieval 0.30 · rules 0.20 · xlmr 0.15`; T `0.4625`; relevance `0.52`; sectors `0.50 / 0.50 / 0.43` |
| Provenance | `results/_huggingface_repos.json`, `*_manifest.json`, `*_training.log` | Per-branch manifests and training logs retained beside each branch |

### Where it sits in the comparison table

| Model | Domain macro-F1 | Sectors | Relevance | Confidence | Evidence | Promoted |
|---|---|---|---|---|---|---|
| V3 stratified LinearSVC | 0.9080 | — | — | none | none | no — missed the 0.92 gate |
| **V6 LinearSVC (frozen primary)** | **0.9472** temporal | — | — | none by design | none | **yes** |
| XLM-R + LoRA (category) | 0.7436 temporal | — | — | softmax | none | no — generalisation failure |
| V7-M multitask seed 1 | 0.9105 | 0.8883 | 0.92 | softmax | none | no — failed sector ≥ 0.90 |
| V7-M seed 13 | validation only | validation only | validation only | — | — | no — never tested |
| **RA-HMT full (V7 split)** | **0.9351** | **0.9014** | **0.9400** | **calibrated, ECE `0.0319`** | **167/167** | **no — gate below** |

The `0.9472` and `0.9351` figures are **not directly comparable**: the frozen primary was
scored on the V6 *temporal* test, RA-HMT on the V7 fixed-split test. The comparable pair is
RA-HMT `0.9351` against its own Branch A `0.9197` on the same 167 rows — `+0.0155`, 95% CI
`[−0.0411, +0.0767]`, `p = 0.548`.

### Standing constraints this line adds

1. **The V7 fixed-split test is now consumed** by RA-HMT's single scored read. It may not
   inform any later selection, tuning or claim ([[22_M1_Data_Usage_and_Row_Count_Register]]).
2. **Promotion requires the fresh holdout v3.** Validation `0.9428` is a selection figure.
   The V7-M candidate looked equally good on validation and then failed its gate on real
   held-out data.
3. **The Branch C encoder is part of the artefact, not a configuration choice.** A different
   encoder produces a different vector space; every cosine similarity against
   `index_train.npz` would be meaningless.
4. **Rebuilding the index is a retraining event** with its own leakage checks. The index must
   never contain val, test or holdout rows.

Full write-up: [[24_M1_RAHMT_Hybrid_Architecture]].
