# Phase 3 · Classifier Model Selection — Outcome Analysis

> Group: `PHASE3_ANNOTATION_CLASSIFICATION / classifier_model_training`. The **outcome** record that sits beside `CLASSIFIER_MODEL_TRAINING_READINESS_PLAN.md` — that document says how to train the model; this one says what happened when it was trained, which model won, and why the one the design chose lost.
>
> Written 2026-08-01, after the bake-off closed Phase-3 model selection. Companion to `../PHASE3_GAP_CLOSURE_PLAN.md` and the program-level [[11_CLASSIFIER_FREEZE_AND_INTEGRATION]].
>
> Evidence: `documentation/m1/records/ENIGMATRIX_M1_COMPLETE_END_TO_END_RECORD_2026-07-31_2313_IST.md` §Step 31 · `models/m1/linearsvc_v6_primary/` · [[18_M1_Dataset_And_Model_Lineage]] §3.

---

## 0. The one-paragraph truth

The readiness plan's verdict was *"the code for doc 05 is essentially COMPLETE; what's missing is not code — it is the rare-domain decision, a CUDA/GPU machine, final evaluation, and ONNX export."* That was accurate. The GPU was obtained, the rare-domain top-up was collected, the full LoRA runs were executed — **and the transformer still lost.** The classifier now serving Module 1 is TF-IDF + LinearSVC at **0.947220** temporal-test macro-F1, against XLM-R's best of **0.743563**. Phase-3 model selection is closed. No ONNX artifact was ever promoted, so every part of the plan downstream of "export ONNX" describes a path that was walked up to but not taken.

---

## 1. What the readiness plan predicted, and what actually happened

| Readiness-plan blocker | Outcome |
|---|---|
| **A GPU host** with the `training` extra | Obtained — Kaggle. Three full LoRA runs executed. |
| **Rare-domain decision** (`EPF_ETF_CHANGE=0`, `PRODUCT_STANDARD=4`, `BUSINESS_REGISTRATION=5`, `PENALTY_ENFORCEMENT=5` in v1) | Top-up collected: Batches 06/07 took the gold set from 800 → 1128 rows. `EPF_ETF_CHANGE` still ended at **4 train / 1 test** in V6 — the top-up helped every rare class *except* the rarest. |
| **Compute time + iteration** (3 seeds × 8 epochs + ablation) | Spent on three configurations rather than a seed sweep, because the first two runs failed for structural reasons that more seeds would not have fixed. |
| Step 8: **export ONNX only if gates pass** | **Never reached.** The gates were not passed by the transformer. |
| Step 9: canary promotion | Logic remains sound; its target model changed (see `../../PHASE5_RESEARCH_FINDINGS/PHASE5_GAP_CLOSURE_PLAN.md` §5c-C). |

The plan's structure held up: it correctly identified that nothing was missing in code. What it could not predict was that executing the plan faithfully would produce a negative result about the architecture the plan was written for.

---

## 2. The three transformer runs

| # | Config | Data | Val macro-F1 | Test macro-F1 | What went wrong |
|---|---|---|---:|---:|---|
| 1 | Category-only, unweighted | V5 | ~0.0946 | ~0.0936 | **Collapsed to the majority class.** The score *is* the majority baseline — the model learned to always answer `SECTOR_SPECIFIC`. |
| 2 | Balanced, seed 42, 16 epochs | V5 | 0.596014 | 0.685348 | Class weighting fixed the collapse, but the model emitted **zero** `EPF_ETF_CHANGE` predictions across the entire evaluation. |
| 3 | Underfit-fix, seed 42, 20 epochs | V6 | 0.902693 | **0.743563** | Underfitting demonstrably solved — **training** macro-F1 0.969340. Temporal generalization was not. |

### Why run 1 was not a bug

With 478 of 777 training rows in `SECTOR_SPECIFIC`, always answering `SECTOR_SPECIFIC` is a locally optimal strategy under unweighted cross-entropy. The model behaved correctly given the objective it was handed. Recording it matters because it is the run most likely to be dismissed as "a broken run" — it was not, it was the objective function doing what it was told.

### Why run 3 is the informative one

Run 3's configuration — separate head (1e-3) and LoRA (2e-4) learning rates, √-balanced clipped class weights, α = 0.5 minority sampling, gradient clipping at 1.0 — **worked as an optimization fix**. Training macro-F1 reached 0.969340; validation 0.902693. The model was fitting the data.

It then lost **0.159** macro-F1 between validation and the temporal test split.

That gap is the entire result. It is not an underfitting problem, not a class-weighting problem, and not a hyperparameter that was left untuned. It is a **generalization** problem, and the most likely cause is sample size: 777 training rows across 8 classes, with a 4-row minority, is inside the regime where a strongly regularized lexical model is simply the better estimator.

**This is not "classical beats neural."** It is "this corpus is currently too small to identify a transformer." Those are different claims and only the second one is defensible from this evidence. The honest form of the finding, for the write-up, is: *at n = 777 with 8 classes and a temporal split, a TF-IDF LinearSVC generalized better than a LoRA-adapted XLM-R whose optimization had been verified as sound.*

---

## 3. The head-to-head

167-row temporal test split, both models scored on identical rows:

| Outcome | Count | Share |
|---|---:|---:|
| Both correct | 150 | 89.8% |
| **LinearSVC only** | **10** | 6.0% |
| XLM-R only | 3 | 1.8% |
| Both wrong | 4 | 2.4% |

The two models agree on the overwhelming majority of documents. Where they differ, LinearSVC is right more than three times as often.

**The single EPF/ETF test record was classified correctly by LinearSVC and missed by XLM-R** — the transformer put 0.803 on `LABOUR_LAW`, with `EPF_ETF_CHANGE` second at 0.197. On the class the research most needs to detect, from 4 training examples, the lexical model found the signal and the transformer overrode it with topical context.

That is an interpretable outcome: with four examples, "the tokens EPF and ETF appear in a contribution-rate context" is learnable as a lexical rule and is not learnable as a distributed representation.

---

## 4. What was frozen

```text
models/m1/linearsvc_v6_primary/linearsvc_pipeline.joblib
SHA256  1D7F84754421A881EE1B5FA0F008A0CC3DB4E24F52CE6D97CE155CB4D1923CFA
```

`TfidfVectorizer(max_features=50000, ngram_range=(1,2), min_df=2)` → `LinearSVC(class_weight="balanced")`

| Metric | Value |
|---|---:|
| Validation macro-F1 | 0.924476 |
| **Temporal test macro-F1** | **0.947220** |
| Accuracy | 0.958084 (160/167) |
| Gate ≥ 0.92 | **passed** |

Reference baseline on the same split: TF-IDF + Logistic Regression, 0.882481 test macro-F1. The V3 stratified LinearSVC baseline that preceded all of this scored 0.9080 and **missed** the gate — so the improvement from 0.9080 to 0.9472 is attributable to the V5/V6 label corrections and the fixed temporal split, not to a change of algorithm.

Per-class test F1:

| Category | F1 | Note |
|---|---:|---|
| `LABOUR_LAW` | 1.000 | |
| `EPF_ETF_CHANGE` | 1.000 | **n = 1 — a one-sample estimate, not a result** |
| `SECTOR_SPECIFIC` | 0.970 | |
| `IMPORT_EXPORT` | 0.970 | |
| `PRODUCT_STANDARD` | 0.941 | |
| `BUSINESS_REGISTRATION` | 0.923 | |
| `TAX_RATE_CHANGE` | 0.917 | |
| `PENALTY_ENFORCEMENT` | 0.857 | weakest measured class — watch this one |

**Reproducibility.** The bundle was downloaded to Windows and re-scored: `0.9472199858964565`, identical to the Kaggle figure to the last digit, with model and test-data SHA256 verified. Record: `local_windows_verification.json`.

---

## 5. What this closes, and what it opens

### Closed

| Item | Resolution |
|---|---|
| "Which architecture goes to production?" | TF-IDF + LinearSVC. Decided on evidence, not preference. |
| "Does the ≥ 0.92 gate pass?" | Yes — 0.947220. The V3 baseline's 0.9080 miss is superseded. |
| ONNX export + INT8 quantization (readiness plan step 8) | **Not performed.** No transformer artifact met the gate to export. The ONNX serving path remains in the codebase, reachable via `M1_CLASSIFIER_BACKEND=onnx`, and is unpromoted. |
| Sector-head arrangement | **Rejected.** No split LinearSVC-category + ONNX-sector production model. Sector routing stays with existing or expert-maintained `m1_regulation_sectors` rows. |
| LoRA r × alpha ablation (readiness plan step 6) | Moot. Ablating a configuration that loses by 0.20 macro-F1 would not change the selection. |

### Opened

1. **The V6 test split is spent.** Four models have been compared on it. It is now final-evaluation-only; further model selection needs a fresh split or nested CV.
2. **`EPF_ETF_CHANGE` needs documents, not resampling.** 4 train / 1 test. The rare-domain top-up raised every other minority class and left this one where it was — the corpus genuinely contains very few EPF/ETF gazettes in the labelled window. Only a targeted collection round fixes it; SMOTE on four examples manufactures confidence rather than evidence.
3. **`PENALTY_ENFORCEMENT` at 0.857** is the weakest class with a meaningful sample, and the natural target for the next annotation batch.
4. **The confidence contract changed.** LinearSVC emits margins, not probabilities — which propagates into the API, the review queue, the drift check and the findings notebooks. That fallout is documented in [[11_CLASSIFIER_FREEZE_AND_INTEGRATION]] §7 and is the larger downstream consequence of this selection.
5. **A transformer is not ruled out — it is deferred pending data.** The right time to retry is after the corpus roughly doubles, not after more hyperparameter search. Recording that explicitly stops the next person re-running run 3 with a different seed.

---

## 6. Method notes for the write-up

Three properties of this comparison are worth defending explicitly, because they are the ones an examiner would probe:

1. **The split is temporal, not random** — sorted by `gazette_published_date`. A random split on a regulatory corpus leaks: amendments to the same principal act appear across the boundary and inflate every model. The temporal split is the reason these numbers are lower and more believable than a random-split equivalent would be.
2. **The split never moved.** 777 / 166 / 167 from V4 onward. A V5-vs-V6 score difference is therefore a labelling effect and never a split effect. The four V6 corrections all landed in **train**, leaving the test split byte-identical to V5.
3. **The threshold was derived on validation, never on test.** The review-queue margin sweep used the validation split only, precisely so that the reported 0.947220 remains a clean held-out measurement. See [[11_CLASSIFIER_FREEZE_AND_INTEGRATION]] §8.

---

## 7. Cross-references

- **Training runbook (the plan this document reports the outcome of):** `CLASSIFIER_MODEL_TRAINING_READINESS_PLAN.md`
- **Phase-3 gap-closure plan:** `../PHASE3_GAP_CLOSURE_PLAN.md`
- **Phase-3 analysis:** `../PHASE3_ANNOTATION_CLASSIFICATION_ANALYSIS.md`
- **Labeling / IAA handoff:** `../2026-07-30_M1_PHASE3_LABELING_IAA_HANDOFF.md`
- **Program-level freeze and integration record:** [[11_CLASSIFIER_FREEZE_AND_INTEGRATION]]
- **Dataset and model lineage:** [[18_M1_Dataset_And_Model_Lineage]]
- **Architecture as designed, annotated with this outcome:** [[05_M1_Model_Architecture]]
- **Training and evaluation method:** [[06_M1_Training_Evaluation]]
- **Full chronology, every epoch and failure:** `documentation/m1/records/ENIGMATRIX_M1_COMPLETE_END_TO_END_RECORD_2026-07-31_2313_IST.md`
