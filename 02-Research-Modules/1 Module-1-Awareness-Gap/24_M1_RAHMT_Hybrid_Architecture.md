# 24 · Gazette-SME-RA-HMT — the hybrid four-output classifier

> **Gazette-SME-RA-HMT**: *A Retrieval-Augmented Hierarchical Multi-Task Hybrid Classifier for SME-Relevant Gazette Regulation Classification.*
>
> Trained end-to-end on Kaggle, exported, assembled into a local artifact bundle at `C:\Reasearch\xyz\m1_rahmt\results`, and wired into the Enigmatrix platform as a selectable classifier backend — 2026-08-03.

> [!success] Status — 2026-08-03
> All five notebooks executed. Three branches, fusion, calibration, constraints and evidence are trained, exported, validated and integrated.
> **Test (n=167): domain macro-F1 0.9351 · sector macro-F1 0.9014 · relevance F1 0.9400 · joint exact-match 0.8802 · domain ECE 0.0319.**
> Against the frozen LinearSVC primary the domain difference is **+0.0155, 95% CI [−0.0411, +0.0767], p = 0.548** — a statistical tie on the one metric they share, while producing three outputs the primary cannot.
> **Not promoted to production.** `M1_CLASSIFIER_BACKEND` still defaults to `linearsvc`. Promotion is a separate decision with its own gate — see §11.

**Related:** [[23_M1_Retrieval_Augmented_Evidence_Branch]] (the Branch C design this realises) · [[20_M1_Multitask_Classifier_Upgrade]] (the V7 multitask line) · [[18_M1_Dataset_And_Model_Lineage]] (dataset and model lineage) · [[05_M1_Model_Architecture]] · [[07_M1_Deployment_Integration]] · [[final/works/11_CLASSIFIER_FREEZE_AND_INTEGRATION|11_CLASSIFIER_FREEZE_AND_INTEGRATION]]

---

## 1. The problem this solves

The Module 1 research question demands **four** outputs per gazette notice:

| # | Output | Type |
|---|---|---|
| O1 | `regulation_domain` | single-label, 8 classes |
| O2 | `affected_sme_sectors` | multi-label, 3 sectors |
| O3 | `is_sme_relevant` | binary |
| O4 | `confidence` + `evidence_snippet` | calibrated probability + extracted text |

The two models already in the repository each produce a slice of that.

| Model | Good at | Cannot do |
|---|---|---|
| TF-IDF + LinearSVC (frozen primary) | legal keyword precision, short notices, tax/duty phrasing, fast CPU inference | semantic meaning, mixed-language text, unseen phrasing, long context — **and O2, O3, O4 entirely** |
| XLM-R + LoRA | multilingual semantics, contextual meaning, generalisation | rare labels, small data, reliable confidence, evidence, legal keyword precision |

`LinearSVCGazetteInference.classify()` returns `confidence=None` **by design**: a LinearSVC
`decision_function` margin is a rank signal, not a probability, and rendering it as a
percentage would be a lie. That is not a bug to patch — it is a structural property of the
model class. O4 does not exist in the current production path.

So the contribution is not "a better domain classifier". It is **the system that can emit
all four outputs at once, with the confidence honest enough to route on**.

---

## 2. Architecture

```
Gazette PDF / OCR text
        │
        ▼
[1] Preprocessing
        ├── unicode NFKC normalisation
        ├── gazette boilerplate + page-marker removal
        ├── OCR confusion repair
        ├── notice-unit splitting        ← newline-preserving (§9.2)
        ├── script detection (en/si/ta/mixed)
        ├── sliding-window chunking (320 words, 80 stride)
        └── legal keyword extraction
        │
        ▼
[2] Three parallel branches + a rule prior
        │
        ├── Branch A  TF-IDF word+char n-grams → calibrated LinearSVC
        │              domain (8-way) · relevance (binary) · 3 × sector (binary)
        │
        ├── Branch B  XLM-R base + LoRA adapter → 3 task heads
        │              mean-pooled encoder → Linear(768→8) softmax
        │                                  → Linear(768→1) sigmoid
        │                                  → Linear(768→3) sigmoid
        │
        ├── Branch C  multilingual-e5-base → top-k=10 train exemplars
        │              similarity-weighted label vote (τ = 0.05)
        │              + label-description matching (works with 4 training rows)
        │
        └── Rules     DOMAIN_KEYWORDS lexicon → normalised prior over 8 domains
        │
        ▼
[3] Hybrid fusion layer
        p_fused = Σ w_b · p_b   over the branches actually present,
                  renormalised by Σ w_b
        weights grid-searched on the 4-simplex, selected on VALIDATION macro-F1
        │
        ▼
[4] Hierarchical multi-task decode
        ├── Head 1  domain     argmax over calibrated softmax
        ├── Head 2  relevance  p ≥ 0.52
        └── Head 3  sectors    p ≥ [0.50, 0.50, 0.43] per sector
        │
        ▼
[5] Constraint + calibration + evidence layer
        ├── temperature scaling T = 0.4625  (Guo et al. 2017)
        ├── constraint repair R1–R3
        ├── blended confidence 0.45·domain + 0.30·sector + 0.25·relevance
        ├── abstention routing → AUTO_ACCEPT / REVIEW_RECOMMENDED / HUMAN_REVIEW_REQUIRED
        └── evidence snippet selection
        │
        ▼
{ regulation_domain, affected_sme_sectors, is_sme_relevant, confidence, evidence_snippet }
```

### 2.1 Why the name

| Part | Meaning |
|---|---|
| **Gazette-SME** | Sri Lankan gazette regulations, scoped to SME impact |
| **RA** | Retrieval-Augmented — retrieves similar previously labelled gazette examples |
| **H** | Hierarchical — domain → SME relevance → affected sector dependency, enforced |
| **MT** | Multi-Task — domain, sector and relevance predicted together |
| **Hybrid** | TF-IDF LinearSVC + XLM-R LoRA + retrieval + rules + calibration |

The novelty claim is deliberately **not** "we used LoRA". LoRA is an existing PEFT method
that freezes pretrained weights and trains low-rank adapters; using it is engineering, not
contribution. The contribution is the complete hybrid framework: joint structured
prediction under explicit dependency constraints, from three complementary evidence
sources, with calibrated confidence and an auditable evidence snippet, in a low-resource
trilingual regulatory setting.

---

## 3. Inputs and outputs

**Input** — one gazette unit:

```json
{
  "key": "official-egz-1923-65",
  "text": "Gazette paragraph / regulation text ...",
  "language": "en/si/ta/mixed",
  "date": "YYYY-MM-DD",
  "source_file": "gazette.pdf",
  "page_start": 12,
  "page_end": 14
}
```

**Output** — the four required results, per unit:

```json
{
  "source_index": 0,
  "unit_index": 0,
  "language": "en",
  "regulation_domain": "PRODUCT_STANDARD",
  "affected_sme_sectors": ["grocery_retail", "food_service", "general_retail"],
  "is_sme_relevant": true,
  "confidence": {
    "domain": 0.91, "sector": 0.87, "sme_relevance": 0.94, "overall": 0.89
  },
  "status": "AUTO_ACCEPT",
  "evidence_snippet": "The regulation specifies product standards applicable to imported food and retail goods ...",
  "domain_distribution": { "PRODUCT_STANDARD": 0.91, "IMPORT_EXPORT": 0.05, "...": 0.0 }
}
```

Label space is the module canon and matches `m1.model.labels` exactly — that identity is
asserted at load time by the serving adapter, because the fixed order is what makes output
index *i* mean class *i*.

**Domains (8, fixed order):** `TAX_RATE_CHANGE`, `IMPORT_EXPORT`, `SECTOR_SPECIFIC`,
`EPF_ETF_CHANGE`, `LABOUR_LAW`, `PRODUCT_STANDARD`, `BUSINESS_REGISTRATION`,
`PENALTY_ENFORCEMENT`
**Sectors (3):** `grocery_retail`, `food_service`, `general_retail`

---

## 4. The three branches

### 4.1 Branch A — TF-IDF + calibrated LinearSVC

Word **and** character n-grams (the frozen V6 primary is word-only), wrapped in
`CalibratedClassifierCV` so it emits probabilities rather than margins, and trained on all
three targets rather than one. Five-fold out-of-fold train predictions so the stacked
meta-classifier never sees a branch's opinion of its own training rows.

It is also the **evidence term-weight source**: `evidence.class_term_weights()` averages
the coefficient rows of the wrapped LinearSVCs for the predicted class. Branch A is
therefore mandatory at inference even in the degraded mode — removing it removes O4, not
just one vote.

Test: domain macro-F1 **0.9197**, sectors 0.8881, relevance 0.9109, joint 0.8743, ECE 0.0805.

### 4.2 Branch B — XLM-R + LoRA, three heads

One shared encoder, three heads, one combined loss:

```
Total = 1.0·Domain_CE + 1.2·Sector_BCE + 1.0·Relevance_BCE + 0.3·Consistency
```

Sector weight is highest because multi-label BCE over three correlated sigmoids is the
weakest-gradient task of the three. The consistency term penalises the
`relevant=false ∧ sectors≠∅` contradiction directly in training, which is what makes the
constraint layer in stage 5 a guarantee rather than a patch.

Test: domain macro-F1 **0.6443** — below Branch A, as predicted before the run. 777
training rows against 278M parameters, four `EPF_ETF_CHANGE` examples, and ~90% English
corpus so most of XLM-R's cross-lingual capacity is idle. Its sector (0.8108) and relevance
(0.8444) heads are far closer to Branch A's, and its standalone ECE (**0.0581**) is *better*
than Branch A's. Report per-output; a single verdict on the branch would be wrong.

### 4.3 Branch C — multilingual-e5 retrieval

777 training units embedded with `intfloat/multilingual-e5-base` (768-dim, L2-normalised,
`passage: ` prefix). A query (`query: ` prefix) retrieves its top-10 nearest neighbours by
cosine similarity, and their gold labels become a similarity-weighted vote softmaxed at
τ = 0.05 — so one very close neighbour dominates while ten mediocre ones do not fabricate
confidence.

Separately, the eight **written domain descriptions** are embedded and scored against the
query. That path needs *no training rows at all*, which is the direct answer to
`EPF_ETF_CHANGE` (4 train / 2 val / 1 test).

Test: domain macro-F1 **0.8590** on a mechanism with no discriminative training. For a
retrieval branch over 777 exemplars that is the strongest single piece of evidence in the
package that exemplar memory is a real evidence source.

**Leakage rules, enforced in code:**

* the index contains **train rows only** — never val, never test, never the holdout;
* train queries use leave-one-out retrieval, so a row can never retrieve itself.

Without the second rule the train features are perfect and the fusion layer learns to trust
retrieval far too much.

---

## 5. Fusion layer

Two options are implemented; both were run.

**Option A — weighted fusion over the simplex.** Grid search at step 0.05 over the
4-simplex, selected on **validation** macro-F1. The grid **contains every corner**, so
`(1,0,0,0)` … `(0,0,0,1)` are candidates and the fused model is by construction at least as
good as the best single branch on the selection split.

**Option B — stacked meta-classifier.** Multinomial logistic regression over concatenated
branch probabilities, fitted on out-of-fold train predictions.

### Fitted configuration (`results/fusion/fusion_config.json`)

```json
{
  "weights": { "tfidf": 0.35, "retrieval": 0.30, "rules": 0.20, "xlmr": 0.15 },
  "temperature": 0.4625434304057596,
  "relevance_threshold": 0.5200000000000002,
  "sector_thresholds": {
    "grocery_retail": 0.5000000000000002,
    "food_service":   0.5000000000000002,
    "general_retail": 0.4300000000000002
  },
  "branches_available": ["tfidf", "xlmr", "retrieval"],
  "selection_policy": "weights, thresholds and temperature fitted on VALIDATION only"
}
```

Validation macro-F1 **0.9428** against single-branch validation of tfidf 0.9100,
retrieval 0.8460, xlmr 0.6475, rules 0.6228 — a **+0.0328** gain over the best single
branch, on a grid that could have returned that branch alone and did not.

Two details worth stating in the methodology chapter:

* **`rules = 0.20` is high** for a lexicon that scores 0.6228 alone. A weak but
  *decorrelated* signal earns weight in a fused ensemble precisely because it is wrong
  about different documents. That is the mechanism the whole design rests on, visible in
  the fitted numbers.
* **`xlmr = 0.15` is the honest quantification** of what a 278M-parameter multilingual
  transformer contributes at this data scale. A weight of 0.0 would also have been a
  legitimate, publishable result.

`general_retail` gets a lower threshold (0.43) than the other two sectors because it is the
scarce positive class — the same shortfall recorded in
[[21_M1_Data_Limitations_and_Risk_Register]].

---

## 6. Constraint layer

The three heads are trained jointly but decoded independently, so nothing stops them
emitting `{"is_sme_relevant": false, "affected_sme_sectors": ["food_service"]}` — which
violates the rule the human annotators actually followed.

| Rule | Condition | Repair |
|---|---|---|
| **R1** | relevant, no sector | set the argmax sector |
| **R2** | irrelevant, has sector | clear sectors — **unless** a sector fires ≥ 0.85, in which case flip relevance to true instead (a very confident sector signal is better evidence than a marginal relevance call) |
| **R3** | domain ∈ {`EPF_ETF_CHANGE`, `LABOUR_LAW`}, relevant, only some sectors fired above 0.35 | widen to all three — employer duties fall on every employer |
| **R4** | confidence < 0.70 | route to `HUMAN_REVIEW_REQUIRED` rather than silently accept |
| **R5** | any `AUTO_ACCEPT` record | must carry a non-empty evidence snippet from its own text |

Every repair is logged, and **`violation_rate_before_repair` is itself a result**: it
measures directly what the multi-task consistency loss bought, and no single-output
baseline can be scored on it at all.

**Measured on the final system: 0.0% — 0 rows of 167 needed repair** (down from 1.2%, 2
rows, on the Branch-A-only build). Interpret that honestly in both directions: the heads
agreed without help, so the layer's operational value here is as a *guarantee* rather than
a correction. Keep the rules in the thesis regardless — an unfired safety rule is still a
specified contract, and the rate is a property of this 167-row sample, not of the system.

---

## 7. Confidence calibration and abstention

Raw fused probabilities are not reliable. Temperature scaling (Guo et al., 2017) fits a
single scalar **T on validation NLL**; test is never touched.

```
domain_confidence    = max calibrated domain probability
sector_confidence    = mean probability of the SELECTED sectors,
                       or 1 − max prob when none are selected
relevance_confidence = |p − 0.5| mapped to [0.5, 1]

overall = 0.45·domain + 0.30·sector + 0.25·relevance
```

```
overall ≥ 0.85  → AUTO_ACCEPT
overall ≥ 0.70  → REVIEW_RECOMMENDED
otherwise       → HUMAN_REVIEW_REQUIRED
```

**Measured routing on the test split: 134 / 18 / 15.** 80.2% of the corpus clears without
a human.

### The calibration result is the headline

| system | domain macro-F1 | **domain ECE** |
|---|---|---|
| Branch A | 0.9197 | 0.0805 |
| weighted fusion (uncalibrated) | 0.9351 | **0.1357** |
| **RA-HMT full (calibrated)** | 0.9351 | **0.0319** |

Read the middle row. Blending three differently-scaled probability vectors produces an
**over-confident** mixture — worse calibrated than any single branch. Temperature scaling
is what turns 0.1357 into 0.0319, the best calibration in the whole ablation table and less
than half Branch A's. Those two rows differ *only* in the calibration stage, which is the
cleanest available evidence that the stage is load-bearing rather than decorative.

---

## 8. Evidence snippet

```
evidence_score = 0.40 · similarity_to_predicted_label_description
               + 0.30 · tfidf_term_importance_for_predicted_class
               + 0.20 · similarity_to_retrieved_neighbours
               + 0.10 · legal_keyword_match
```

Two implementations:

* **`evidence_sparse`** — no neural dependency. Implements the 0.30 and 0.10 terms plus a
  length prior (a three-word fragment is rarely the operative clause) and renormalises.
  Runs on CPU, and is what `predict.py` uses.
* **`branch_c_retrieval.select_evidence`** — the e5 semantic version, all four terms,
  better quality, needs a GPU.

Measured: **167/167 records carry a non-empty snippet**; keyword-hit-rate **0.7246**. That
metric is a proxy — a real evaluation needs humans judging whether the snippet justifies
the label (100 sampled records, two raters, report agreement). It is listed as an open gate
in §11.

---

## 9. Corrections applied on the way to the local bundle

Both were found in the Kaggle notebooks and patched there; the local `src/` had drifted and
now matches.

### 9.1 Branch C probability accumulation — `src/branch_c_retrieval.py`

`label_distribution()` accumulated the similarity-weighted vote in **float32**. Ten float32
weights summing to 1.0 leave a residue of ~1e-7, producing values such as `1.000000119` — a
probability above 1.

Not cosmetic. `fusion.apply_temperature` takes `log()` of these values and
`metrics.expected_calibration_error` bins them into `[0, 1]`, so an out-of-range
probability corrupts calibration and can move a record into the wrong abstention rung. The
corrected function accumulates in **float64**, scrubs nan/inf, clips to `[0, 1]`,
renormalises the domain block onto the simplex, and casts to float32 only on return.

### 9.2 Notice splitting — `src/preprocess.py`

`split_notices()` called `clean_text()` on the whole document **first**. `clean_text()` ends
in `normalise_whitespace()`, which collapses every whitespace run — **including line
breaks** — to one space. `NOTICE_START_RE` is a multiline `(?m)^…` pattern, so by the time
it ran there were no line starts left to anchor on, and the split silently returned the
whole page as one unit.

**Measured on a three-notice test page: old = 1 unit, corrected = 3 units.**

Because a page classified as one label is the single biggest source of label noise in this
corpus ([[03_M1_Data_Collection]] §segmentation), this correction is what makes
`--split-units` mean what it says.

---

## 10. The local artifact bundle

`C:\Reasearch\xyz\m1_rahmt\results` — one artifact root, four runtime folders.

```
results/
├── branch_a/    branch_a_models.joblib (10.3 MB) · branch_a_report.json · keys/scores
├── branch_b/    heads.pt · lora_adapter/ (3.5 MB) · tokenizer/ (22 MB) · report · log
├── branch_c/    index_train.npz (777×768) · index_labels.csv · branch_c_report.json
├── fusion/      fusion_config.json · results_full.json · predictions_test.csv · ablation_table.csv
├── final_eval/  4 figures + 2 tables + results_paragraph.txt   (NOT used at runtime)
├── models/      offline base encoders (empty by default)
├── _huggingface_repos.json   pinned base-model commit hashes
└── _source_zips/             the five raw Kaggle downloads
```

### Assembly is not a straight unzip

Kaggle's "download all output" produced five generically-named archives, not the
`branch_a_complete.zip` names the plan assumed. Two facts govern the assembly:

1. **`results (3).zip` has no `branch_c_report.json`.** `_load_branch_c()` reads it for the
   encoder name and top-k, so extracting only that archive yields a `branch_c/` that looks
   complete and fails at load.
2. **`results (4).zip` carries `fusion_inputs_clean/{branch_a,branch_b,branch_c}`** — the
   exact sanitised branch outputs the fusion weights were fitted against. Those are the
   canonical copies; using a different `branch_c` than the one fusion saw is a silent
   inconsistency.

The bundle was therefore built as: three branches from `fusion_inputs_clean/`, plus
`fusion/` and `final_eval/`, plus manifests and training logs from the per-branch archives.
Full PowerShell in `m1_rahmt/LOCAL_INFERENCE_RUNBOOK.md` §2.

### Pre-flight validation

`m1_rahmt/scripts/validate_artifacts.py` — exit `0` valid, `1` missing file, `2` incomplete
fusion run. The `2` case is the one that matters: `branches_available` must contain
`tfidf`, `xlmr` **and** `retrieval`. If it does not, the weights on disk were fitted while a
branch was absent, and applying them when that branch *is* present silently mis-weights the
ensemble. **Run against the real bundle 2026-08-03: `All runtime artifacts are valid.`**

### Base models are not in the bundle

`branch_b/lora_adapter/` is 3.5 MB of adapter matrices; LoRA freezes the pretrained weights,
so the 1.1 GB `xlm-roberta-base` encoder is still required at inference. Branch C needs
`intfloat/multilingual-e5-base`, and **that one is not a choice** — `index_train.npz` holds
vectors from that specific encoder, and a different encoder produces a different vector
space in which every cosine similarity is meaningless.

First full run therefore needs internet. For an air-gapped host, populate
`results/models/{xlm-roberta-base,multilingual-e5-base}`; `predict.py` prefers those folders
and falls back to the hub id, so nothing else changes. Commit hashes are pinned in
`_huggingface_repos.json`.

---

## 11. Enigmatrix integration

The predictor is wired in as a **third selectable classifier backend**, not a replacement.
Nothing about the frozen LinearSVC primary changes until `M1_CLASSIFIER_BACKEND` is
switched.

| Layer | File | Change |
|---|---|---|
| ML | `enigmatrix-ml/m1/model/rahmt_inference.py` | `RAHMTGazetteInference` adapter (**new**) |
| ML | `enigmatrix-ml/m1/model/__init__.py` | lazy export, matching the existing pattern |
| Backend | `enigmatrix-backend/app/settings.py` | `M1_MODEL_RAHMT_DIR`, `M1_RAHMT_*` |
| Backend | `.../app/m1/services/classifier_service.py` | `rahmt` backend branch, review rule, sector contract, health |
| Frontend | `enigmatrix-frontend/lib/m1/classifier-display.ts` | four-output display helpers |
| Research | `m1_rahmt/src/rahmt_service.py` | process-level singleton + health payload (**new**) |

```dotenv
M1_CLASSIFIER_BACKEND=rahmt
M1_MODEL_RAHMT_DIR=m1_rahmt/results
M1_RAHMT_PACKAGE_ROOT=m1_rahmt
M1_RAHMT_USE_XLMR=true
M1_RAHMT_USE_RETRIEVAL=true
M1_RAHMT_REVIEW_STATUS=REVIEW_RECOMMENDED
```

### Four decisions worth recording

**The adapter locates the research package rather than vendoring it.** Two copies of the
same model code would drift, and the thesis is written against `m1_rahmt/src`.
`M1_RAHMT_PACKAGE_ROOT`, or auto-detection next to the workspace root.

**Label identity is asserted, not assumed.** The adapter raises at load time if
`m1.model.labels.CATEGORIES != src.labels.DOMAINS` or the sector orders differ. A silent
mismatch would relabel every prediction.

**Review flagging uses the model's own abstention rung**, not a re-derived threshold.
Re-thresholding the confidence in the service would decouple the review queue from the
calibration the thresholds were fitted with.

**Switching backend changes the sector contract.** On `linearsvc`,
`sector_output_available=false` and sectors are expert/manual data
([[final/works/11_CLASSIFIER_FREEZE_AND_INTEGRATION|the freeze record]]). On `rahmt`,
sectors are a model output with validation-tuned thresholds. Decide what happens to
existing `m1_regulation_sectors` rows **before** promoting.

The response shape is stable across backends — `is_sme_relevant`, `status`,
`evidence_snippet`, `confidence_breakdown`, `active_branches` and `language` are present as
`None`/empty on the other two, so no caller has to branch on the backend name.

### Frontend

`lib/m1/classifier-display.ts` gains `isRahmtOutput`, `hasCalibratedConfidence`,
`abstentionLabel/Tone/Title`, `formatSectors`, `relevanceLabel/Tone` and
`fourOutputSummary()`. `classifierSignal()` now checks **calibrated confidence first**: on
the RA-HMT path the blended confidence is a real probability and outranks the decision
margin. On the LinearSVC path the existing "margin, not a percentage" behaviour is
unchanged — that guard is the whole reason the helper exists.

---

## 12. Results

Test split n = 167. Selection on validation only; test read once.

| system | domain macro-F1 | sectors | relevance | joint exact | domain ECE | AURC | cov @98% acc |
|---|---|---|---|---|---|---|---|
| rule keywords only | 0.5829 | 0.4368 | 0.4608 | 0.1617 | 0.1053 | 0.1094 | 0.186 |
| Branch A | 0.9197 | 0.8881 | 0.9109 | 0.8743 | 0.0805 | 0.0052 | 0.904 |
| Branch B | 0.6443 | 0.8108 | 0.8444 | 0.7605 | 0.0581 | 0.0275 | 0.665 |
| Branch C | 0.8590 | 0.8675 | 0.9020 | 0.8443 | 0.0564 | 0.0082 | 0.844 |
| A + B | 0.7632 | 0.8450 | 0.8817 | 0.8323 | 0.0627 | 0.0086 | 0.802 |
| A + C | 0.9225 | 0.8902 | 0.9307 | 0.8743 | 0.0777 | 0.0040 | 0.904 |
| B + C | 0.7147 | 0.8450 | 0.8817 | 0.8323 | 0.0412 | 0.0126 | 0.778 |
| weighted fusion | 0.9351 | 0.9014 | 0.9400 | 0.8802 | 0.1357 | 0.0040 | 0.898 |
| meta fusion | 0.8955 | 0.9014 | 0.9400 | 0.8623 | 0.0839 | 0.0038 | **0.934** |
| **RA-HMT full** | **0.9351** | **0.9014** | **0.9400** | **0.8802** | **0.0319** | 0.0050 | 0.880 |

Domain accuracy 0.9461; domain macro-F1 95% CI **[0.8697, 0.9737]**.

Paired bootstrap vs Branch A on domain macro-F1: **+0.0155, 95% CI [−0.0411, +0.0767],
p = 0.548**, 2000 resamples.

### The claim to make

> This research contributes **Gazette-SME-RA-HMT**, a retrieval-augmented hierarchical
> multi-task architecture for SME-relevant gazette regulation classification in a
> low-resource trilingual setting. The contribution is the system design: joint prediction
> of regulation domain, affected SME sector and SME relevance under explicit dependency
> constraints, with calibrated confidence and an extracted evidence snippet, from three
> complementary evidence sources. Against a strong single-output TF-IDF + LinearSVC
> baseline it is statistically indistinguishable on regulation-domain macro-F1 (0.9351 vs
> 0.9197; Δ = +0.0155, 95% CI [−0.0411, +0.0767], p = 0.548), while additionally producing
> affected SME sectors (macro-F1 0.9014), SME relevance (F1 0.9400), a joint exact-match
> across all three of 0.8802, and reducing expected calibration error from 0.0805 to
> **0.0319**, with an evidence snippet on 100% of records.

Do **not** claim the hybrid outperforms the baseline on macro-F1. On 167 rows that is not
supportable and a careful examiner will ask for the interval.

### One projection this work falsified — say so in the viva

The Branch-A-only build predicted coverage@98%-accuracy would rise 0.904 → 0.946. On the
full three-branch run it went the other way: **0.904 → 0.880**. Temperature scaling with
T = 0.46 *sharpens* the fused distribution (T < 1), lowering ECE but making the
selective-risk ordering slightly less favourable at that operating point. RA-HMT buys
**calibration quality and output completeness**, not extra auto-accept coverage. If coverage
is the operational priority, `fusion_meta` is the row to quote: 0.934 coverage at 0.0839 ECE.

Dropping a claim your own measurement contradicted is a better look than defending it.

---

## 13. Evaluation plan and metrics

| Output | Metric |
|---|---|
| O1 regulation domain | macro-F1, weighted-F1, per-class F1 **with support printed** |
| O2 SME sector | macro-F1, micro-F1, Hamming loss |
| O3 SME relevance | F1, precision, recall |
| Full output | exact match (all three), mean outputs correct |
| O4 confidence | ECE, Brier, reliability diagram, risk–coverage curve, AURC |
| O4 evidence | keyword-hit-rate (automatic proxy) + human review accuracy |

Report in this order: the **four-output scorecard** first (one row per system, one column
per output — only the hybrid fills every cell, which is the table that makes the argument
visually), then reliability, then the ablation, and a bootstrap CI beside every macro-F1
with a paired bootstrap test for every pairwise claim.

Figures are in `results/final_eval/`: `fig1_reliability.png`, `fig2_risk_coverage.png`,
`fig3_per_class_f1.png`, `fig4_confusion.png`; tables in `table1_ablation.csv` and
`table2_four_output_scorecard.csv`; the auto-generated results paragraph in
`results_paragraph.txt`.

---

## 14. Limitations — state these before an examiner finds them

1. **`EPF_ETF_CHANGE` is not evaluable.** 4 train / 2 val / **1 test** row. Macro-F1
   averages over eight classes, so that single row carries 12.5% of the headline metric.
   Report it, mark it `n/a`, or report macro-F1 with and without it. Do not report F1 = 1.0
   on one row as a result.
2. **The test set is 167 rows.** Any difference below roughly ±0.06 macro-F1 is noise.
   Every claim gets a CI.
3. **A single fixed split.** Add 5-fold CV over the pooled 1110 rows and report mean ± std
   alongside the fixed-split number.
4. **Sector labels are correlated with relevance by construction** (the annotation rule is
   *relevant ⇔ at least one sector*), so joint exact-match is not three independent tasks.
   Report per-output as well as joint.
5. **IAA bounds the ceiling.** Pooled SME-relevance κ is 0.915; a model cannot meaningfully
   exceed the agreement of the humans who produced its labels. Quoting κ next to 0.94
   relevance F1 reframes it as *at human level* rather than *only 0.94*.
6. **Language coverage is thin.** 18 Tamil training rows, 8 Tamil test rows. No per-language
   claim on Tamil; report it as an observation with support printed.
7. **Evidence quality is proxied.** Keyword-hit-rate 0.7246 is automatic, not a judgement of
   whether the snippet justifies the label.
8. **The retrieval index is frozen at 777 training rows.** It does not learn from production
   traffic, and rebuilding it against a larger gold set is a retraining event with its own
   leakage checks — the index must never contain val, test or holdout rows.
9. **Everything here is the V7 fixed split, not the fresh holdout v3.** The 286-row locked
   holdout ([[21_M1_Data_Limitations_and_Risk_Register]],
   [[22_M1_Data_Usage_and_Row_Count_Register]]) remains unspent and is the correct surface
   for any promotion decision.

---

## 15. Tracking — what is done and what is open

### Done (2026-08-03)

- [x] Branch A trained, exported, calibrated, three targets
- [x] Branch B trained (XLM-R + LoRA, 3 heads, multi-task loss), adapter + heads + tokenizer exported
- [x] Branch C index built (777 × 768, e5-base), leave-one-out train retrieval, label descriptions
- [x] Fusion weights, temperature and thresholds fitted on validation only
- [x] Constraint layer, abstention routing, evidence snippet
- [x] Full ablation (10 rows) + bootstrap CIs + paired bootstrap test
- [x] Final eval figures and tables
- [x] Local artifact bundle assembled at `m1_rahmt/results`, no double nesting
- [x] `scripts/validate_artifacts.py` written and **passing** against the real bundle
- [x] Branch C float64 probability correction applied locally
- [x] Notice-splitting correction applied locally (verified 1 unit → 3 units)
- [x] `src/rahmt_service.py` process-level singleton + health payload
- [x] `scripts/classify_text.py` CLI
- [x] `input/new_gazettes.csv` smoke input
- [x] `enigmatrix-ml` adapter + lazy export
- [x] `enigmatrix-backend` settings + `rahmt` backend branch + health
- [x] `enigmatrix-frontend` four-output display helpers
- [x] `LOCAL_INFERENCE_RUNBOOK.md`, `results/models/README.md`
- [x] `README.md` and `NOVELTY_AND_EVALUATION.md` refreshed with measured three-branch numbers

### Open

| Item | Gate | What closes it |
|---|---|---|
| `.venv` created and requirements installed | needs the Windows shell | run `LOCAL_INFERENCE_RUNBOOK.md` §6 |
| Branch A-only smoke run | same | §9 |
| Full four-branch run | needs internet on first execution (two ~1.1 GB base encoders) | §10 |
| Offline base-model folders | only for air-gapped deployment | §7 + `results/models/README.md` |
| Promotion to production backend | RA-HMT has never been scored on the **fresh holdout v3**; the V7 test split it was scored on is now consumed | Step 55A holdout lock, then a single scored read |
| Sector-contract decision | promoting `rahmt` makes sectors a model output | decide what happens to existing `m1_regulation_sectors` rows |
| Human evidence evaluation | keyword-hit-rate is a proxy | 100 sampled records, two raters, report agreement |
| 5-fold CV over the pooled 1110 rows | single fixed split | run and report mean ± std |
| Per-language breakdown | not yet computed for the hybrid | slice the test predictions by `detect_script` output |
| Disagreement matrix A vs B vs C | the empirical justification for the ensemble | count per-branch right/wrong off-diagonals on test |

---

## 16. File map

| Path | What |
|---|---|
| `m1_rahmt/src/labels.py` | taxonomy, descriptions, keyword lexicon, constraint rules, abstention thresholds |
| `m1_rahmt/src/preprocess.py` | stage [1] — cleanup, **notice splitting**, chunking, script detection |
| `m1_rahmt/src/branch_a_tfidf.py` | Branch A + 5-fold OOF |
| `m1_rahmt/src/branch_b_xlmr_lora.py` | Branch B, 3 heads, LoRA/LoRA+, k-fold OOF |
| `m1_rahmt/src/branch_c_retrieval.py` | Branch C — index, **`label_distribution`**, label descriptions, evidence |
| `m1_rahmt/src/fusion.py` | weighted + meta fusion, temperature scaling, threshold tuning |
| `m1_rahmt/src/constraints.py` | stage [5a] — repair, abstention, confidence blend |
| `m1_rahmt/src/evidence.py` | stage [5c] — sparse evidence snippet + hit-rate metric |
| `m1_rahmt/src/metrics.py` | four-output scorecard, ECE, Brier, AURC, bootstrap tests |
| `m1_rahmt/src/run_fusion.py` | every ablation row in one pass |
| `m1_rahmt/src/predict.py` | end-to-end inference, CLI |
| `m1_rahmt/src/rahmt_service.py` | process-level singleton, health payload |
| `m1_rahmt/scripts/validate_artifacts.py` | artefact + fusion-config pre-flight |
| `m1_rahmt/scripts/classify_text.py` | one-shot CLI |
| `m1_rahmt/LOCAL_INFERENCE_RUNBOOK.md` | exports → local predictor → platform |
| `m1_rahmt/NOVELTY_AND_EVALUATION.md` | what to report and how to defend it |
| `enigmatrix-ml/m1/model/rahmt_inference.py` | serving adapter |
| `enigmatrix-backend/app/m1/services/classifier_service.py` | backend selection, review rule, health |
| `enigmatrix-frontend/lib/m1/classifier-display.ts` | four-output display helpers |
