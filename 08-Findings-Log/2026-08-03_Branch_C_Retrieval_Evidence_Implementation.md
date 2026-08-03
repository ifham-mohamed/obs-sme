---
tags: [m1, branch-c, retrieval, evidence, calibration, leakage, dataset-lineage, implementation]
date: 2026-08-03
author: Mohamed M.R.I (215075J) — Module 1 owner
session: 74
status: shipped — Branch C code-complete (Phases 1–4, 8); dataset provenance tooling added
feature: F-244 – F-247
---

# Branch C — retrieval-augmented evidence branch implemented + dataset provenance audit

> Builds [[23_M1_Retrieval_Augmented_Evidence_Branch|23_M1_Retrieval_Augmented_Evidence_Branch]] Phases 1–4 and 8 as code in `enigmatrix-ml`. Additive throughout — `linearsvc_v6_primary` is byte-identical before and after (14/14 SHA-256 sums verified).
>
> Second half of the session answered a separate request — "merge all the dataset folders into one unique dataset" — which turned out to be the wrong operation, and surfaced a lineage problem worth more than the merge would have been.

## What I did

- **Implemented Branch C** per doc 23's build plan: hybrid BM25 + dense retrieval over a train-only index, C1 similarity-weighted precedent vote, C2 temperature-scaled fusion with Branch A margins, and the Output-4 evidence contract.
- **Wrote the near-duplicate audit** doc 23 §7.1 specified as blocking, plus a hash-based exact-duplicate check it did not specify (reason below).
- **Built dataset provenance tooling** — an inventory across all 11 dataset directories and a unified-corpus builder — instead of the naive merge that was asked for.
- **Verified everything runnable in a sandbox**: 132 tests, all three Branch C CLIs end-to-end on synthetic data, both dataset CLIs on the real CSV-readable versions.

## What I found

### 1. A real tokenizer defect — Sinhala/Tamil words were being shredded

The BM25 tokenizer started as `re.findall(r"\w+", text)`. Python's `\w` matches what `str.isalnum()` accepts, which **excludes Unicode combining marks (Mn/Mc)**. Sinhala and Tamil write vowels as combining signs, so:

```
tokenize("බදු අනුපාතය")  →  ['බද', 'අන', 'තය']     # before — vowel signs dropped, words split
tokenize("බදු අනුපාතය")  →  ['බදු', 'අනුපාතය']      # after
```

`බදු` (tax) is බ + ද + ු(U+0DD4, category Mn). The mark was silently discarded and the word split at that point. This would have degraded sparse retrieval recall on **exactly the two languages Branch C exists to serve** — and it would have looked like "embeddings fail on Sinhala/Tamil", which is [[23_M1_Retrieval_Augmented_Evidence_Branch|doc 23]] §8's third listed risk, pointing the diagnosis at the wrong component.

Fixed by adding the Sinhala (U+0D80–U+0DFF), Tamil (U+0B80–U+0BFF), ZWJ, and combining-diacritical ranges to the token class, with a regression test. Caught by a unit test, not by inspection.

### 2. The Step-41 leakage is still present in the canonical V6 on disk

Doc 23 §7 records the Step-41 audit finding "8 within-split duplicate-text rows and 6 train–val overlap rows in V6, cleaned to 1103 rows / 773-163-167". **I reproduced that independently and it matches exactly** — 8 duplicate-text groups (16 rows), of which 3 groups (6 rows) straddle train↔val:

| Group | Keys | Splits | Chars | Category |
|---|---|---|---|---|
| dup_001 | `GZT_2483_26`, `GZT_2483_31` | **train + val** | 1176 | SECTOR_SPECIFIC |
| dup_002 | `GZT_2483_46`, `GZT_2483_54` | **train + val** | 404 | SECTOR_SPECIFIC |
| dup_003 | `GZT_2493_63`, `GZT_2493_64` | **train + val** | 348 | SECTOR_SPECIFIC |
| dup_004–008 | 5 further pairs | within one split | — | SECTOR_SPECIFIC |

The new information is not the finding — it is the **lineage status**:

- The de-leaked **1103-row split does not exist in `datasets/`**. Per [[22_M1_Data_Usage_and_Row_Count_Register|22_M1_Data_Usage_and_Row_Count_Register]] row "V7-W working", 1103 / 773-163-167 was built for the V7-W multitask attempt, which **collapsed and was rejected**. The de-leaked artifact went with it.
- The frozen primary is registered against `m1_regulations_v6_1110_clean_fixedsplit`, 777/166/167 — the split that **still contains the 6 overlap rows**.

Stated precisely, and no further:

- **Validation macro-F1 0.9245 is optimistic.** 3 of 166 validation rows (1.8%) are byte-identical to a training row under a different key. Direction of bias is known; magnitude is not, because the model may have classified them correctly regardless.
- **Test macro-F1 0.9472 is unaffected.** The only within-test duplicate is dup_005, a test↔test pair. No train↔test text duplication exists. **This remains the number to quote.**

`dataset_manifest_v6.json` reports `leakage: {train_val: 0, train_test: 0, val_test: 0}` and that is **true as written** — it is a *key*-based check and the keys genuinely do not overlap. It cannot see the same text filed under two keys. That is a gap in the check, not a false entry in the manifest.

### 3. Why the audit needed a hash check as well as embeddings

Doc 23 §7.1 specifies cosine > 0.95 against train. Necessary but not sufficient: an encoder can score a **verbatim** duplicate at 0.93 and slip under the threshold. Hashing cannot miss and costs nothing, so `audit_near_duplicates.py` now emits `exact_text_duplicates.csv` alongside the cosine report, computed independently of `--threshold` and of the encoder.

### 4. There was nothing to merge

The request was to combine the dataset folders in `xyz\datasets\` and `enigmatrix-ml\datasets\` into one unique-row dataset. The 11 directories are **successive revisions of one corpus, not separate corpora**:

- `v4_1128_clean_stratified` and `v5_1110_clean_fixedsplit` have **identical 1110-key sets**.
- 409 texts differ byte-for-byte between them but **0 differ after whitespace normalisation** — v5 applied an undocumented whitespace clean-up. Benign, now recorded.
- V6 = V5 + 4 label corrections (`EPF_ETF_CHANGE` 11 → 7).
- The only keys outside V6 are the **18 OCR-noise rows** that `dataset_manifest.json` records as `excluded_ocr_noise_rows: 18`.

### 5. The 18 excluded rows are confirmed garbage

Extracted their full text for the first time. Lengths 2–26 characters, median 8:

```
GZT_2469_28 (5 chars):  '1A 2A'
GZT_2471_06 (2 chars):  '2A'
GZT_2471_08 (12 chars): '2A BWග 4A 6A'
GZT_2471_11 (17 chars): '1A 2A 3A 4A 5A 6A'
```

All 18 labelled `SECTOR_SPECIFIC`. Re-admitting them would add unusable text to the already-dominant class. The exclusion decision in [[18_M1_Dataset_And_Model_Lineage|18_M1_Dataset_And_Model_Lineage]] is correct and now has evidence behind it rather than a row count.

### 6. Branch C behaviour observed so far

Only on a synthetic 360-row corpus with the offline hashing encoder — **no real Branch C numbers exist yet** (no `sentence-transformers`, no network in the sandbox). What was verified is mechanism, not performance:

- The **leakage alarm fires correctly**. Synthetic categories are separable by vocabulary, C1 hit accuracy 1.0 / Recall@1 1.0, and the evaluator refused the result and exited 5 with the doc 23 §8 kill-signal message. The guard works on a case constructed to trip it.
- **λ endpoints behave**: λ=1.00 reproduces Branch A exactly, λ=0.00 reproduces Branch C exactly.
- **Temperature scaling never moved an argmax** across the grid, as it must not.

## What changed in the repo

All in `enigmatrix-ml`. Additive: 3 existing files edited, none of them model or dataset artifacts.

| File | Change |
|---|---|
| `m1/model/retrieval.py` | **NEW** — char-window chunking with spans, BM25-Okapi (pure Python, Unicode-mark-aware), `SentenceTransformerEncoder` (LaBSE default) + offline `HashingEncoder`, `DenseIndex` (FAISS flat → sklearn cosine → NumPy, all exact), RRF, `RetrievalIndex` (train-only guards, no `add` method by design), `RetrievalClassifier` (C1), Output-4 contract + validator |
| `m1/model/calibration.py` | **NEW** — `softmax(margin/T)`, `fit_temperature` (validation NLL), `fuse_probabilities`, `sweep_lambda`, ECE / Brier / NLL / reliability bins / risk–coverage, dependency-free F1 metrics, `BranchAMarginSource` (read-only), `FrozenModelGuard` |
| `scripts/build_m1_retrieval_index.py` | **NEW** — train-only index build; timestamped output; leakage + frozen-model guards |
| `scripts/audit_near_duplicates.py` | **NEW** — cosine > 0.95 audit **+ hash-based exact-duplicate check**; CSV + JSON; never removes rows |
| `scripts/evaluate_m1_retrieval_branch.py` | **NEW** — C1 k-sweep {1,3,5,10,20}, sector-threshold sweep, C2 T-fit + λ-sweep 0.00→1.00/0.05, ECE/Brier/risk–coverage, `--final-test-once` gate |
| `scripts/inventory_m1_datasets.py` | **NEW** — read-only scan of all 11 versions: key relationships, label conflicts, text drift, duplicate-text groups with split spans |
| `scripts/build_m1_unified_dataset.py` | **NEW** — V6-authoritative unified corpus, splits verbatim, quarantine reports, provenance columns |
| `tests/m1/model/test_retrieval_index.py` | **NEW** — train-only construction, leakage guards, chunking, BM25, RRF, Sinhala/Tamil tokenizer regression |
| `tests/m1/model/test_retrieval_classifier.py` | **NEW** — weighted vote, row collapse, sector thresholding, confidence, review bands, leakage alarm |
| `tests/m1/model/test_calibration_fusion.py` | **NEW** — fusion formula, λ endpoints, temperature invariants, ECE/Brier/risk–coverage, frozen-model guard |
| `tests/m1/model/test_evidence_contract.py` | **NEW** — Output-4 schema, precedent-not-attention assertion, audit output format, build→evaluate CLI round-trip |
| `tests/m1/model/test_dataset_unification.py` | **NEW** — version ranking, comparison, dedup, both dataset CLIs |
| `m1/model/__init__.py` | edited — lazy exports for `retrieval` / `calibration` |
| `pyproject.toml` | edited — `retrieval` + `retrieval-faiss` extras (sklearn stays pinned 1.5.x) |
| `Makefile` | edited — `branch-c-*`, `dataset-*`, `test-branch-c` targets |
| `BRANCH_C_README.md` · `BRANCH_C_RUNBOOK.md` · `BRANCH_C_DATASET_UNIFICATION.md` | **NEW** — architecture, step-by-step runbook, dataset findings |
| `runs/branch_c/EXAMPLE_synthetic_smoke/` | **NEW** — schema examples, banner-stamped as synthetic |

### Leakage rules enforced in code, not prose

| Doc 23 rule | Enforcement |
|---|---|
| Index is train rows only | `RetrievalIndex.build` rejects rows tagged `val`/`test`; no `add`/`append` method exists |
| No val/test key in index | `assert_train_only_corpus` at build **and** at eval |
| Test split untouched | requires `--final-test-once`; build reads test **keys only**, never test text; `test_split_read` recorded in results JSON |
| k / threshold / T / λ tuned on validation only | every sweep lives in the validation path |
| Near-perfect C1 is a bug | `leakage_alarm` at accuracy ≥ 0.99 or Recall@1 ≥ 0.99 → exit 5 |
| Frozen model unmodified | `FrozenModelGuard` re-checks all 14 SHA-256 sums before and after every run |
| No run overwrites a previous one | timestamped dirs; reuse needs `--allow-existing-run-dir` |
| λ ties never credited to Branch C | `best_lambda` breaks ties toward higher λ (= Branch A) |

## Verified

- **132 tests pass** (105 Branch C + 27 dataset). Includes 8 subprocess tests driving the real CLIs.
- All modules compile; `import m1.model` still works without torch.
- `FrozenModelGuard` on `models/m1/linearsvc_v6_primary`: **verified True, 14 files, 0 mismatched** after every run.
- `git status` on `models/` clean. Repo-wide "modified" churn is the known CRLF artifact (Session 73), unrelated.

> [!note] Sandbox limits — what is *not* verified
> No network and no `sklearn`/`pyarrow`/`pytest` in the sandbox, so: (a) no real Branch C numbers on the 777/166/167 split, (b) the 5 parquet-only versions under `enigmatrix-ml/datasets/` (v1–v3 lineage + smoke) were **not** readable, so their key sets are unconfirmed, (c) tests ran under a hand-written pytest shim, not pytest itself. Re-run `make test-branch-c` and `make dataset-inventory` on Windows to close all three.

## What's next

- [ ] `make dataset-inventory` on Windows — settles whether the 5 parquet-only versions hold any key V6 lacks.
- [ ] Adjudicate the 3 cross-split pairs. For each: genuine re-publication, amendment, or a segmentation artefact that split one notice into two rows.
- [ ] Decide the V6 leakage disposition. Options: quote validation with the 1.8% caveat (current, zero-risk); or rebuild the de-leaked 1103-row split as a **canonical** artifact and re-measure Branch A on it — which invalidates the recorded 0.9245 and needs a re-freeze, so it is a lineage decision, not a cleanup task.
- [ ] Real Branch C run: `make branch-c-index` with LaBSE → audit → validation eval. Report the λ curve whichever way it goes.
- [ ] Doc 23 Phases 5 (expert evidence evaluation — the long pole), 6 (rare-class), 7 (cross-lingual) remain unbuilt.
- [ ] On the next re-split, deduplicate on `text_sha256_normalised`, not just `key`.

## Blockers

- **Phase 5 needs a domain expert.** Doc 23 §9 flags it as the critical path at ~1 week wall-clock, and the headline contribution (expert-auditable evidence) rests on it. Nothing else in Branch C is blocked.
- **The V6 leakage disposition needs an owner decision**, not more analysis. Both options are defensible; they differ in whether the frozen primary gets re-measured.

## Cross-references

- Design + build plan this implements: [[23_M1_Retrieval_Augmented_Evidence_Branch|23_M1_Retrieval_Augmented_Evidence_Branch]] (§4 architecture, §5 phases, §7 leakage, §8 kill criteria)
- Lineage of record, now carrying the near-duplicate addendum doc 23 §7.2 asked for: [[18_M1_Dataset_And_Model_Lineage|18_M1_Dataset_And_Model_Lineage]]
- Row-count ledger — the "V7-W working 1103" row is the de-leaked split's only trace: [[22_M1_Data_Usage_and_Row_Count_Register|22_M1_Data_Usage_and_Row_Count_Register]]
- Confidence contract this finally implements: [[05_M1_Model_Architecture|05_M1_Model_Architecture]] · [[20_M1_Multitask_Classifier_Upgrade|20_M1_Multitask_Classifier_Upgrade]]
- Protocol + gates: [[06_M1_Training_Evaluation|06_M1_Training_Evaluation]]
- Cross-lingual retrieval context: [[10_M1_Sinhala_Tamil_NLP|10_M1_Sinhala_Tamil_NLP]]
- Risk register (add the tokenizer class of defect): [[21_M1_Data_Limitations_and_Risk_Register|21_M1_Data_Limitations_and_Risk_Register]]
- Features: F-244 – F-247 in [[FEATURES|FEATURES]] · [[CHANGES|CHANGES]] · [[SESSIONS|SESSIONS]]
- Repo docs: `enigmatrix-ml/BRANCH_C_README.md` · `BRANCH_C_RUNBOOK.md` · `BRANCH_C_DATASET_UNIFICATION.md`

## Claims discipline

Unchanged from doc 23 §0 and §10, and now enforced by the code:

- Branch C is for **confidence, evidence, expert audit, and rare-class support**.
- Accuracy comparison against Branch A is **exploratory** — 167 test rows, 7 errors, needs 6-of-7 fixed and none broken for *p* < 0.05.
- Novelty is the **expert-auditable evidence contract** and **low-resource cross-lingual gazette precedent retrieval** — never the retrieval algorithm.
- Not a RAG question-answering system. Retrieval, voting, fusion, confidence, evidence. Nothing generative.
