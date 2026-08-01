# 11 — Classifier Freeze and Backend Integration

> The program-level record of how Module 1 got a production classifier: the V6 label correction, the model bake-off that ended Phase-3 model selection, the frozen artifact, the two-backend inference service, the database migration, and the confidence contract that came out of choosing a margin-based model over a probability-based one.
>
> Written 2026-08-01. Supersedes the assumption — carried by [[05_M1_Model_Architecture]] and [[06_M1_Training_Evaluation]] since the design phase — that the production classifier would be XLM-R.
>
> Evidence: `documentation/m1/records/ENIGMATRIX_M1_COMPLETE_END_TO_END_RECORD_2026-07-31_2313_IST.md` · `documentation/m1/analysis/MARGIN_THRESHOLD_ANALYSIS.md` · `datasets/m1_regulations_v6_1110_clean_fixedsplit/dataset_manifest_v6.json` · `models/m1/linearsvc_v6_primary/`

---

## 0. The one-paragraph truth

Module 1's production classifier is **TF-IDF + LinearSVC**, not XLM-R. It scores **0.947220 macro-F1** on the 167-row temporal test split against a 0.92 gate, and it beat every transformer configuration tried — including one whose optimization problems had demonstrably been fixed. The model is frozen, hashed, reproduced byte-identically on a second machine, wired into the backend behind a backend switch, and its schema migration is applied to the live database. The cost of that choice is that `LinearSVC.decision_function` returns an **uncalibrated margin, not a probability**, so every downstream surface that expected a percentage now has to handle `confidence: null`. That contract change — not the model swap — is the part that touches the most code and the most documentation.

---

## 1. What changed, in order

```text
V5 dataset (1110 rows, fixed 777/166/167 split)
     │
     ├─ 4 EPF/ETF label corrections, all in TRAIN
     ▼
V6 dataset  ── FROZEN ──▶ bake-off: 3 XLM-R runs vs TF-IDF baselines
                                │
                                ├─ XLM-R rejected (§3)
                                ▼
                       LinearSVC frozen as primary (§4)
                                │
                                ├─ LinearSVCGazetteInference (ML package)
                                ├─ classifier_service two-backend switch (§5)
                                ├─ migration 202608010001 — margin + model name (§6)
                                └─ confidence contract: null, not a number (§7)
```

Each arrow is a decision with a reason attached. The reasons are the point of this document; the numbers are recoverable from the frozen record at any time.

---

## 2. The V6 correction — why a four-row relabel mattered

Four Presidential duties/functions gazettes carried incidental ETF mentions and had been labelled `EPF_ETF_CHANGE` when their subject matter was not an EPF/ETF change at all:

| Key | V5 label | V6 label |
|---|---|---|
| `official-pdf-2226-17` | `EPF_ETF_CHANGE` | `SECTOR_SPECIFIC` |
| `official-pdf-2235-59` | `EPF_ETF_CHANGE` | `SECTOR_SPECIFIC` |
| `official-pdf-2248-35` | `EPF_ETF_CHANGE` | `SECTOR_SPECIFIC` |
| `official-pdf-2412-08` | `EPF_ETF_CHANGE` | `SECTOR_SPECIFIC` |

Four rows out of 1110 is a rounding error in aggregate, and a large fraction of the smallest class: `EPF_ETF_CHANGE` holds **4 train rows and 1 test row** after the correction. A model that learned "the string ETF appears" from four mislabelled examples would have learned a rule that is wrong in exactly the cases the research cares about.

**All four are in the train split.** That is not luck — it is the condition that made the correction safe to make mid-programme. Because the test split is byte-identical between V5 and V6, every V5-vs-V6 model comparison remains valid, and the temporal test score is not contaminated by the relabelling. Cross-split key leakage was verified as zero and per-split SHA256 recorded in `dataset_manifest_v6.json`.

Full lineage, class distribution and hashes: [[18_M1_Dataset_And_Model_Lineage]].

---

## 3. The bake-off — three XLM-R runs and why each failed

| Run | Dataset | Val macro-F1 | Test macro-F1 | Failure mode |
|---|---|---:|---:|---|
| Category-only, unweighted | V5 | ~0.0946 | ~0.0936 | Collapsed to the majority class — the score *is* the majority baseline |
| Balanced, seed 42, 16 epochs | V5 | 0.596014 | 0.685348 | **Zero** `EPF_ETF_CHANGE` predictions; the minority class was never emitted |
| Underfit-fix, seed 42, 20 epochs | V6 | 0.902693 | **0.743563** | Training macro-F1 0.969340 — underfitting solved, generalization not |

The third run is the informative one. Its configuration — separate head (1e-3) and LoRA (2e-4) learning rates, √-balanced clipped class weights, α = 0.5 minority sampling, gradient clipping at 1.0 — **worked**: training macro-F1 went to 0.969340 and validation to 0.902693. The model was no longer underfitting. It still lost 0.16 macro-F1 between validation and the temporal test.

That gap is a generalization result, and it is the honest reading of the whole exercise: **777 training rows across 8 classes with a 4-row minority is inside the regime where a strongly regularized lexical model is the better estimator.** It is not evidence that transformers are unsuited to this task; it is evidence that this corpus is currently too small to identify one.

Transformer tuning was stopped at that point rather than continued, for a reason worth stating: the V6 test split had already been used to compare four models. Continuing to tune against it would have turned a held-out measurement into a selection set (§9.2).

Head-to-head on the 167-row temporal test:

| Outcome | Count |
|---|---:|
| Both correct | 150 |
| LinearSVC only | 10 |
| XLM-R only | 3 |
| Both wrong | 4 |

The single EPF/ETF test record was classified correctly by LinearSVC and missed by XLM-R, which put 0.803 on `LABOUR_LAW` with `EPF_ETF_CHANGE` second at 0.197. Detailed failure tables: end-to-end record §Step 31; outcome analysis: `PHASE3_ANNOTATION_CLASSIFICATION/classifier_model_training/CLASSIFIER_MODEL_SELECTION_ANALYSIS.md`.

---

## 4. The frozen primary model

```text
models/m1/linearsvc_v6_primary/linearsvc_pipeline.joblib
SHA256  1D7F84754421A881EE1B5FA0F008A0CC3DB4E24F52CE6D97CE155CB4D1923CFA
Bundle  2F80BEFE494F1275DCB14FCB5352902A8BF98C1CC3FA86F919D53B7958C5F11B
```

`TfidfVectorizer(max_features=50000, ngram_range=(1,2), min_df=2)` → `LinearSVC(class_weight="balanced")`.

| Metric | Value |
|---|---:|
| Validation macro-F1 | 0.924476 |
| **Temporal test macro-F1** | **0.947220** |
| Test accuracy | 0.958084 (160/167) |
| Gate | ≥ 0.92 — **passed** |

Per-class test F1: `LABOUR_LAW` 1.000 · `EPF_ETF_CHANGE` 1.000 (n=1) · `SECTOR_SPECIFIC` 0.970 · `IMPORT_EXPORT` 0.970 · `PRODUCT_STANDARD` 0.941 · `BUSINESS_REGISTRATION` 0.923 · `TAX_RATE_CHANGE` 0.917 · `PENALTY_ENFORCEMENT` 0.857.

**Read `EPF_ETF_CHANGE` 1.000 as "one test document, classified correctly" and nothing more.** It is a one-sample estimate. Quoting it as a per-class result without that qualifier would be the most easily challenged claim in the module.

### Reproducibility

The bundle was downloaded to the Windows host and re-scored end to end. Test macro-F1 came back `0.9472199858964565` — identical to the Kaggle figure to the last digit — with model and test-data SHA256 both verified. Record: `models/m1/linearsvc_v6_primary/local_windows_verification.json`.

### The scikit-learn pin

The pipeline was fitted under scikit-learn **1.5.2**; the workspace `.venv` holds **1.8.0** and emits `InconsistentVersionWarning` on unpickle. Validation accuracy still reproduced exactly (`0.9457831325301205`), so this artifact is unaffected in practice — but the dependency range that allowed the drift was `>=1.4,<2`, which is precisely how it happened.

`enigmatrix-ml/pyproject.toml` now pins `scikit-learn>=1.5.2,<1.6` in **both** the `serving` and `training` extras, on the rule that *a model trained under one line must be loadable by the other*, and declares `joblib` explicitly rather than relying on it arriving transitively.

⚠ **The pin constrains future resolution; it does not fix the existing environment.** Run `uv sync --extra serving` before trusting a deploy.

---

## 5. Backend integration — the two-backend service

### 5.1 The crash that reading prevented

`classify_gazette.py` contained:

```python
row.classifier_confidence = Decimal(str(round(result["confidence"], 2)))
result["confidence"] < MIN_CONFIDENCE
```

The LinearSVC engine returns `confidence: None` by design. Pointing the existing service at the new engine would have raised `TypeError` on **every row** — a total pipeline outage on the first gazette. This was found by reading the call site before switching the backend, not by running it.

### 5.2 What the service does now

| Setting | Default | Meaning |
|---|---|---|
| `M1_CLASSIFIER_BACKEND` | `linearsvc` | `linearsvc` (frozen primary) or `onnx` (XLM-R dual-head) |
| `M1_MODEL_LINEARSVC_DIR` | `models/m1/linearsvc_v6_primary` | Resolved against cwd, then the workspace root |
| `M1_MODEL_ONNX_DIR` | `storage/models/m1/onnx/v1` | Unchanged |
| `M1_CLASSIFIER_MIN_CONFIDENCE` | `0.55` | **ONNX path only** — calibrated probability threshold |
| `M1_CLASSIFIER_MIN_MARGIN` | *(unset)* | **LinearSVC path** — margin threshold, disabled by default (§8) |

Path resolution tries cwd first, then the workspace root, then falls back to the cwd form so an error message names the path the operator expects. This matters because the artifacts live at the workspace root, one level above the backend package, and the service can legitimately be started from either directory.

`classify_gazette` writes `classifier_confidence` **only** when the backend supplies a calibrated probability. On the LinearSVC path the column is left NULL rather than being fed a raw margin. The task result payload gained `decision_margin` and `model_name`; the log line carries `backend`, `conf` (or `n/a`) and `margin`. The stale "12-category" docstring was corrected to the frozen 8-category V6 taxonomy.

### 5.3 Tests

6 targeted + 3 export + 7 chunk-contract tests; the non-slow M1 model suite runs **26 passed, 2 deselected** (run three times). `py_compile` clean on five backend modules; imports resolve with `backend=linearsvc`, `min_margin=None`, model directory resolved.

---

## 6. The migration — and the review queue defect it fixed

### 6.1 The defect

The review queue read:

```sql
WHERE status='classified' AND classifier_confidence < 0.55 AND NOT expert_verified
```

On the LinearSVC backend `classifier_confidence` is always NULL, so **that predicate matches nothing — and an empty review queue is indistinguishable from a clean bill of health.** This is the failure worth naming: not an error, not a log line, just a screen that says everything is fine because it asked a question the data cannot answer.

### 6.2 What was added

Migration `202608010001`:

| Object | Live state (verified) |
|---|---|
| `classifier_decision_margin` | `numeric(10,6)`, nullable ✓ |
| `classifier_model_name` | `varchar(64)`, nullable ✓ |
| `classifier_confidence` | `numeric(3,2)` — **deliberately unchanged** ✓ |
| CHECK | `margin IS NULL OR margin >= 0` ✓ |
| Partial index | `WHERE classifier_decision_margin IS NOT NULL` ✓ |
| `alembic_version` | `202608010001` ✓ |

A row now carries a confidence **or** a margin depending on which engine classified it, and never a margin coerced into the probability column.

The endpoint selects its signal from the active backend and reports which one it used:

| Backend | Predicate | `mode` |
|---|---|---|
| `onnx` | `classifier_confidence < 0.55` | `confidence` |
| `linearsvc` + threshold set | `classifier_decision_margin < threshold` | `margin` |
| `linearsvc`, no threshold | *(no query issued)* | `disabled` |

`mode='disabled'` exists so that "nothing configured" and "nothing flagged" cannot be confused again.

### 6.3 Applying it

A read-only state check first showed the database was **two** revisions behind, not one — `upgrade head` would also create `m1_translation_jobs` and `m1_translation_workers` from the translation workstream (§[[12_TRILINGUAL_TRANSLATION_PIPELINE]]). Both additive, but applying another workstream's pending migration is not a silent decision. It was approved explicitly, then applied.

Verification queried `information_schema`, `pg_constraint` and `pg_indexes` directly rather than trusting alembic's exit code. Target: Supabase session pooler, `aws-0-ap-southeast-1`, port 5432. Alembic chain: 53 migrations, single head.

---

## 7. The confidence contract

This is the part most likely to be got wrong by a future consumer, so it is stated as a contract rather than a note.

`LinearSVC.decision_function` returns **signed distances from the decision hyperplane**. They are not probabilities, they are not bounded, and they are not monotone in any calibrated sense across classes. The adapter therefore returns:

```json
{
  "confidence": null,
  "confidence_type": "not_available_uncalibrated_linearsvc",
  "decision_score": 1.84,
  "decision_margin": 0.97,
  "second_category": "TAX_RATE_CHANGE",
  "second_decision_score": 0.87,
  "class_scores": { "…": "…" }
}
```

| Permitted | Not permitted |
|---|---|
| Ranking rows against each other | Displaying a margin as a percentage |
| Prioritising a review queue | Thresholding as though 0.5 meant "50% sure" |
| Sorting by uncertainty | Feeding a margin into `classifier_confidence` |
| Storing for later calibration research | Reporting a margin as model confidence in the thesis |

If calibrated probabilities are needed, **train and evaluate a calibration layer separately** — do not transform margins. Two stale frontend strings in `lib/m1/docs.ts` describing a 12-category XLM-R dual-head with a `confidence < 0.70` rule were corrected as part of this work; nothing else consumes `classifier-review` or renders `classifier_confidence` yet, so there was nothing else to break. That window closes as soon as a triage UI is built (§9.1).

**No sector head.** The frozen primary is category-only: it returns `"sectors": []` and `"sector_probs": {}`. The split arrangement — LinearSVC categories plus ONNX sectors — was considered and **rejected**: sector routing stays with existing or expert-maintained `m1_regulation_sectors` rows until a separately evaluated sector model is promoted.

---

## 8. The review threshold — derived, and shipped unset

`scripts/derive_m1_margin_threshold.py`, run on the **validation split only**. The test split stays reserved; selecting an operating point on it would invalidate the reported 0.947220.

Margins separate cleanly:

| Group | n | Median margin |
|---|---:|---:|
| Correct | 157 | **1.5954** |
| Incorrect | 9 | **0.3896** |

| Threshold | Flagged | % of split | Error recall | Flag precision |
|---:|---:|---:|---:|---:|
| 0.20 | 5 | 3.0% | 22.2% | 40.0% |
| **0.40** | **11** | **6.6%** | **55.6%** | **45.5%** |
| 0.70 | 21 | 12.7% | 77.8% | 33.3% |

**It ships unset, and that is the finding — not an omission.** Nine errors in 166 rows means one reclassified row moves error recall by roughly 11 percentage points; the curve above is not stable enough to freeze an operating point from. Two of the nine errors are also unreachable by *any* margin rule: `GZT_2487_01` (margin 1.2670) and `GZT_2479_56` (1.4632) are **confidently wrong**, which is exactly the failure an uncalibrated margin cannot detect.

With nothing configured, the queue reports `mode='disabled'` rather than returning zero rows and looking healthy.

Turning it on is one environment variable — `M1_CLASSIFIER_MIN_MARGIN=0.40` — but it routes ~6.6% of classified rows to a human, which is a **capacity decision**, not a modelling one. Full sweep: `documentation/m1/analysis/MARGIN_THRESHOLD_ANALYSIS.md`.

---

## 9. Open items

### 9.1 Blocking a deploy

1. `uv sync --extra serving` — the pin constrains future resolution; the live `.venv` still holds scikit-learn 1.8.0.
2. Decide on `M1_CLASSIFIER_MIN_MARGIN`. Column, index and endpoint mode all exist; this is a review-capacity question.
3. **Triage UI against `GET /classifier-review`** — must handle `mode='disabled'`, render the margin as a **rank** rather than a percentage, and tolerate `classifier_confidence: null`. Until this ships, the review queue has no surface.

### 9.2 Standing research constraints

4. **The V6 test split is spent for model selection.** Four models have now been compared on it. Any further tuning against it invalidates the 0.947220; further selection needs a fresh split or nested CV.
5. **`EPF_ETF_CHANGE` needs real documents, not resampling.** 4 train / 1 test. Only a targeted annotation round fixes this; SMOTE-style resampling on four examples manufactures confidence rather than evidence.
6. **`PENALTY_ENFORCEMENT` is the weakest measured class** at 0.857 test F1 — the one to watch when the next batch of gold labels lands.

### 9.3 Housekeeping

7. Review and commit the four remaining `enigmatrix-ml` changes (`samplers.py`, `architecture.py`, `config.py`, `pyproject.toml`), which predate this work.
8. `git rm --cached mydata/label_studio.sqlite3` — now ignored, still tracked from before.
9. `VALIDATE CONSTRAINT ck_m1_reg_classifier_confidence_range` — a pre-existing `NOT VALID` constraint found incidentally.
10. **Push.** Everything described here is committed locally and has not left the machine. Root commit `18cc93f` (265 files, 231,653 insertions) is the one that first put the frozen V6 parquets, the LinearSVC pipeline and the labelling gold standard into version control.

---

## 10. Reproducing this

```powershell
py -3 C:\Reasearch\xyz\scripts\build_enigmatrix_m1_complete_record.py   # end-to-end record
py -3 C:\Reasearch\xyz\scripts\build_m1_v6_fixedsplit.py                # V6 dataset
py -3 C:\Reasearch\xyz\scripts\derive_m1_margin_threshold.py            # margin sweep
py -3 C:\Reasearch\xyz\scripts\_alembic_state_check.py                  # read-only migration state
```

---

## 11. Cross-references

- **Dataset and model lineage (hashes, class distribution, version history):** [[18_M1_Dataset_And_Model_Lineage]]
- **Model-selection outcome analysis:** `PHASE3_ANNOTATION_CLASSIFICATION/classifier_model_training/CLASSIFIER_MODEL_SELECTION_ANALYSIS.md`
- **Training-runbook precursor to this work:** `PHASE3_ANNOTATION_CLASSIFICATION/classifier_model_training/CLASSIFIER_MODEL_TRAINING_READINESS_PLAN.md`
- **Session-level decision record:** `PROGRAM_READINESS/M1_MODEL_INTEGRATION_AND_REORGANIZATION_SESSION_RECORD_2026-08-01.md`
- **Stage-by-stage execution detail:** `PROGRAM_READINESS/LOG_AND_WORKS/2026-08-01_M1_INTEGRATION_REORG_AND_SYNC_WORK_RECORD.md`
- **Architecture as originally designed (annotated with this outcome):** [[05_M1_Model_Architecture]]
- **Training method and acceptance criteria:** [[06_M1_Training_Evaluation]]
- **API response contract:** [[11_M1_API_Reference]]
- **Status ledger:** [[03_FEATURE_CHECKLIST]]
