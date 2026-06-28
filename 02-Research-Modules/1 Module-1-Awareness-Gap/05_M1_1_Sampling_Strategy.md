# 05_M1_1 — Sampling Strategy

> Companion to [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) — stratified-by-year-language code, k=20 silhouette justification, AL baseline vs production baseline disambiguation, sparse-cell handling.
> **Implementation status:** 🔲 Deferred (BUILD_07 + BUILD_11 — `ml/m1/data/samplers.py`)

## Purpose

Parent doc §1 shows the three sampling steps (stratified → k-means → active learning). This companion specifies the operational decisions glossed over there: how `k=20` was chosen, how to handle year-language cells with < 5 docs, and how the AL baseline is kept distinct from the production baseline.

## Detailed process

### Step 1 — Stratified-with-sparse-handling

The parent doc's edit-in §1.1 covers the rule. Implementation:

```python
SMALL_CELL_THRESHOLD = 5
TARGET_PER_CELL = 20

def stratified_sample(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for (year, lang), g in df.groupby(["year", "primary_language"]):
        if len(g) < SMALL_CELL_THRESHOLD:
            out.append(g)                                          # take all
        else:
            out.append(g.sample(min(len(g), TARGET_PER_CELL), random_state=42))
    return pd.concat(out, ignore_index=True)
```

### Step 2 — k-means cluster diversity (`k=20`)

`k=20` is chosen by silhouette analysis on a 200-document pilot:

| k | Mean silhouette score | Notes |
|---|---|---|
| 10 | 0.16 | Clusters too coarse; multiple regulatory topics per cluster |
| 15 | 0.21 | |
| **20** | **0.24** | Local maximum; each cluster represents one coherent regulatory topic |
| 25 | 0.22 | Topical singletons start appearing |
| 30 | 0.19 | Singletons + over-segmentation |

The script `scripts/find_optimal_k.py` produces the curve; quarterly re-run as the corpus grows. If the optimum shifts > 3, re-run sampling.

### Step 3 — Active learning baseline (NOT the production baseline)

The parent doc §1.3 explains the AL chicken-and-egg resolution. Key invariant:

```python
class ALBaseline:
    """Trained on a sliding window of labels — used ONLY for uncertainty scoring."""
    def __init__(self, version: int):
        self.version = version                            # e.g. v1 at 300 labels, v2 at 500
        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(max_features=20000, ngram_range=(1,2))),
            ("clf", LogisticRegression(class_weight="balanced", max_iter=2000)),
        ])

class ProductionBaseline:
    """Trained on the FULL labeled set — used for XLM-R ablation comparison."""
    def __init__(self):
        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(max_features=20000, ngram_range=(1,2))),
            ("clf", LogisticRegression(class_weight="balanced", max_iter=2000)),
        ])
```

Same pipeline shape, two different artefacts. Stored separately in `storage/models/m1/baseline_al_v<N>.pkl` vs `storage/models/m1/baseline_prod.pkl`. The script that picks the next labeling batch references only the AL artefact; the evaluation script in [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) §6 references only the production baseline.

### Step 4 — AL acquisition rule (uncertainty sampling)

```python
def select_next_batch(unlabeled: pd.DataFrame, baseline: ALBaseline, batch_size: int = 200) -> pd.DataFrame:
    probs = baseline.pipeline.predict_proba(unlabeled["raw_text"])
    margin = 1.0 - probs.max(axis=1)
    top_indices = np.argsort(margin)[::-1][:batch_size]
    return unlabeled.iloc[top_indices]
```

Margin-based uncertainty (`1 - max_prob`) is the simplest acquisition function; the literature suggests entropy or BALD give marginal improvements at higher engineering cost. The marginal-uncertainty approach is sufficient for our 800-doc target.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Stratified + k-means + AL (chosen) | Three orthogonal coverage axes | ✅ Each step addresses a different bias (language imbalance, topical clustering, easy-vs-hard) | If labelling budget triples (then move to pool-based BALD acquisition). |
| Random sampling alone | Cheapest | ❌ Biased toward majority language + topics | Never. |
| Stratified only | Easy | ❌ Misses topical coverage (Tax dominates the corpus). | If topical diversity is somehow guaranteed by the source distribution. |
| Active-learning only (no stratification) | Maximally informative | ❌ Starts cold — the first 300 labels need stratification to even produce a usable AL baseline. | After the first 300 labels are in. |

## Worked example

A typical first batch (n=200):

```
Stratified sample step:  150 docs taken (10 year-language cells × ~15 each)
k-means top-up step:      40 docs taken (clusters that the stratified sample under-covered)
Hand-picked safety net:   10 docs (each of the 4 minority categories has ≥ 5 examples)
Total in batch_01.csv:    200 docs

Sent to Label Studio → annotators tag in 8 working days → batch ready for training
```

After the second batch (next 200 docs via AL):

```
AL baseline v1 trained on labelled 200 docs (TF-IDF + LR)
Uncertainty score computed on remaining 5,000 unlabelled docs
Top 200 by margin → batch_02.csv

Average margin in batch_01 (random): 0.32
Average margin in batch_02 (AL):     0.61  →  AL surfaces harder examples
```

The 0.61 margin batch yields more category-correction value per label, justifying the AL overhead.

## Failure modes & edge cases

- **Year-language cells with 0 documents.** A year-language cell that doesn't exist in the corpus (e.g. 2015 Tamil) is silently skipped. Acceptable — the model F1 for that cell will be undefined, not biased.
- **AL converges on a single category.** If all top-margin docs happen to be one category, the next batch is mono-class. Mitigation: stratify the AL acquisition by predicted category — pick top-K from each category.
- **k-means clusters degenerate.** On very small subsets, k-means with k=20 produces 5 tiny clusters and 15 empty ones. Mitigation: dynamically reduce k when `n < 200`.
- **Random seed drift.** Different `random_state` values produce different batches → un-reproducible labeling. Mitigation: pin `random_state=42` everywhere; tests assert determinism.

## Validation & acceptance criteria

- **Per-cell coverage:** after 4 batches, every year-language cell has at least 5 labelled docs (or "no docs exist in corpus").
- **Class coverage:** every category has at least 50 labelled docs after 4 batches (BUILD_11 entry criterion).
- **AL improvement:** mean uncertainty margin in batch N+1 > batch N (test asserts monotonic increase).
- **Determinism:** running `scripts/sample_for_labeling.py` twice with the same seed produces identical CSV outputs.

## Cross-references

- Parent: [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) §1
- Related: [06_M1_1_Data_Augmentation_Strategy.md](06_M1_1_Data_Augmentation_Strategy.md), [09_M1_Annotation_Guidelines.md](09_M1_Annotation_Guidelines.md)
- BUILD phase: BUILD_11 §sampling pipeline
- Code (when shipped): `ml/m1/data/samplers.py`, `scripts/sample_for_labeling.py`
