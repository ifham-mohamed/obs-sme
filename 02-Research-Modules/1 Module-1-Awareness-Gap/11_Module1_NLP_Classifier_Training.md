# 11 — Module 1: NLP Classifier Training

> Goal: turn the populated `regulations` table from file 10 (cleaned, language-tagged but uncategorized notices) into a trained, evaluated, deployable multi-class classifier that assigns each notice to one of the 12 regulatory categories — and to do this in a way that is rigorously defensible in your thesis.

This is where the **AI/ML research contribution** of Module 1 becomes concrete: a multilingual (Sinhala / Tamil / English) regulatory text classifier — the first published one for Sri Lanka.

---

## 1. The Classification Task — Concretely Defined

**Input:** a string `text` — the cleaned body of a single regulatory notice (typically 100–3000 words).

**Output:** one of 12 category labels (taxonomy from file 09 §8) plus a confidence score, plus an optional "NOT_REGULATORY" / "UNCERTAIN" flag.

**Why it must be multilingual:** notices arrive in English, Sinhala, and Tamil — sometimes with mixed-script body text. A monolingual model would either drop two-thirds of your data or require translation (which loses regulatory nuance).

**Why it can't be hand-rules:** Sri Lankan regulatory language is messy. Tax notices and Customs notices use overlapping vocabulary. A keyword-only classifier collapses to ~60% accuracy. You need representation learning.

---

## 2. The 12-Way Taxonomy (recap from file 09)

```
1.  TAX_INCOME              7.  ENVIRONMENTAL
2.  TAX_VAT_SVAT            8.  EMPLOYMENT_LABOUR
3.  TAX_CUSTOMS_TARIFF      9.  COMPANY_REGISTRATION
4.  EPF_ETF                 10. SECTOR_SPECIFIC (food, telecom, banking…)
5.  IMPORT_EXPORT_CONTROL   11. CONSUMER_PROTECTION
6.  HEALTH_SAFETY           12. OTHER_REGULATORY
```

You will probably revise these once you've labeled your first 200 examples — that's normal and expected. **Lock the taxonomy by week 5; do not change it after that** (or you'll re-label everything).

---

## 3. The Full Training Pipeline at a Glance

```
1. SAMPLING       →  pull diverse subset from regulations table for labeling
2. LABELING       →  human annotation (Label Studio); inter-annotator agreement
3. SPLITTING      →  temporal train / val / test split
4. BASELINES      →  TF-IDF + Logistic Regression; GPT-4 zero-shot
5. FINE-TUNING    →  XLM-RoBERTa with HuggingFace Trainer
6. EVALUATION     →  macro-F1, per-class, per-language slice
7. ERROR ANALYSIS →  confusion matrix, hard examples, ablations
8. VERSIONING     →  freeze model, store metadata in model_versions
9. SERVING        →  FastAPI endpoint; batch inference for backfill
```

---

## 4. Stage 1 — Sampling for Labeling

You cannot label everything. You must label a **representative, diverse, sufficient** subset.

### 4.1 How many to label

A defensible minimum for a 12-class multilingual classifier:
- **800 labeled examples to start** — train + val + test split
- **Aim for 1500–2000** by the end of the project
- Per-class minimum: **40 examples** for the smallest class (otherwise it's untrainable)

### 4.2 Sampling strategy — stratified + active

Don't just take the first 800. Use a 3-step sample:

1. **Stratified random** — sample roughly evenly across `language` and `publication_date` quarters, so you cover all years and all three languages
2. **Pre-cluster** — run k-means on TF-IDF vectors (k=20) and sample from each cluster → ensures topical diversity, avoids labeling 200 near-duplicate VAT amendments
3. **Active learning (after first 300 labeled)** — train a baseline, then prioritize labeling examples where the baseline is *least confident* — these are the highest-information labels

```python
# scripts/sample_for_labeling.py
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import pandas as pd

df = pd.read_sql("SELECT id, raw_text, language, publication_date FROM regulations", conn)

# 1. stratified sample by year + language
strat = df.groupby([df.publication_date.dt.year, "language"]).sample(n=20, random_state=42)

# 2. cluster-based diversity sampling on the rest
vec = TfidfVectorizer(max_features=10000, ngram_range=(1, 2))
X = vec.fit_transform(df.raw_text)
km = KMeans(n_clusters=20, random_state=42).fit(X)
df["cluster"] = km.labels_
diverse = df.groupby("cluster").sample(n=15, random_state=42)

to_label = pd.concat([strat, diverse]).drop_duplicates("id")
to_label.to_csv("/data/labeling/batch_01.csv", index=False)
```

---

## 5. Stage 2 — Labeling (the unglamorous part that decides everything)

### 5.1 Use Label Studio

Don't label in spreadsheets. Use [Label Studio](https://labelstud.io) — it's open-source, self-hostable, and supports text classification with multi-language interfaces.

```yaml
# label_studio_config.xml — text classification with side-by-side metadata
<View>
  <Header value="Regulation Category Classification"/>
  <Text name="text" value="$raw_text"/>
  <Choices name="category" toName="text" choice="single" required="true">
    <Choice value="TAX_INCOME"/>
    <Choice value="TAX_VAT_SVAT"/>
    <Choice value="TAX_CUSTOMS_TARIFF"/>
    <Choice value="EPF_ETF"/>
    <Choice value="IMPORT_EXPORT_CONTROL"/>
    <Choice value="HEALTH_SAFETY"/>
    <Choice value="ENVIRONMENTAL"/>
    <Choice value="EMPLOYMENT_LABOUR"/>
    <Choice value="COMPANY_REGISTRATION"/>
    <Choice value="SECTOR_SPECIFIC"/>
    <Choice value="CONSUMER_PROTECTION"/>
    <Choice value="OTHER_REGULATORY"/>
    <Choice value="NOT_REGULATORY"/>
    <Choice value="UNCERTAIN"/>
  </Choices>
  <Choices name="confidence" toName="text" choice="single">
    <Choice value="high"/>
    <Choice value="medium"/>
    <Choice value="low"/>
  </Choices>
  <TextArea name="notes" toName="text" placeholder="Why uncertain? Multi-category?"/>
</View>
```

### 5.2 Write a labeling guideline document

Before any labels are produced, write a 4–6 page "Annotation Guidelines" document. This is a thesis appendix later. For each category include:

- **Definition** in one sentence
- **3 positive examples** (real notices)
- **2 hard negatives** (notices that look similar but belong elsewhere)
- **Tie-breaking rules** (when a notice could fit two categories — e.g., a VAT exemption for medical devices: tax or health? → resolve as TAX_VAT_SVAT, document the rule)

### 5.3 Inter-annotator agreement (IAA)

If only you label, your model learns *your* biases — and your viva panel will rightly attack this.

**Minimum standard:**
- Have **at least 2 annotators** label the same 100 examples
- Compute **Cohen's Kappa** — target ≥ 0.7 (substantial agreement)
- Disagreements → discuss, refine guidelines, re-label

```python
from sklearn.metrics import cohen_kappa_score
kappa = cohen_kappa_score(annotator_a, annotator_b)
print(f"Cohen's Kappa: {kappa:.3f}")
```

If you can't recruit a second annotator, label 100 examples *yourself*, wait two weeks, label them again, and report intra-annotator Kappa as a lower-bound proxy. Disclose this honestly in the methodology.

---

## 6. Stage 3 — Splitting (the part most students get wrong)

### 6.1 Don't use random splits — use temporal splits

Regulations evolve. A model trained on 2020–2023 data and tested on 2018 data is testing the wrong thing. Use:

- **Train:** notices from earlier dates
- **Val:** middle slice
- **Test:** most recent slice (the future, from the model's perspective)

Example for a project running in 2026:
- Train: 2018 – mid-2024
- Val: mid-2024 – end-2024
- Test: 2025 onward

This simulates **how the model will actually be used** — predicting categories for new gazettes it hasn't seen.

```python
df = df.sort_values("publication_date")
n = len(df)
train = df.iloc[:int(0.7*n)]
val   = df.iloc[int(0.7*n):int(0.85*n)]
test  = df.iloc[int(0.85*n):]
```

### 6.2 Stratify within each split

Within each temporal split, ensure category distribution doesn't collapse. If a class has < 5 examples in the test set, your test metric for that class is meaningless — note it in the report.

---

## 7. Stage 4 — Baselines (always train these first)

Two non-negotiable baselines before any deep learning:

### 7.1 Baseline A — TF-IDF + Logistic Regression

```python
# train_baseline_tfidf.py
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report

pipe = Pipeline([
    ("tfidf", TfidfVectorizer(max_features=20000, ngram_range=(1, 2),
                               sublinear_tf=True, min_df=2)),
    ("clf",   LogisticRegression(max_iter=2000, class_weight="balanced",
                                  C=1.0, n_jobs=-1)),
])
pipe.fit(train.raw_text, train.category)
preds = pipe.predict(test.raw_text)
print(classification_report(test.category, preds, digits=3))
```

This gives you a number to beat. On a 12-class regulatory text problem with 800 training examples, expect **macro-F1 around 0.55–0.70** — depending heavily on class imbalance. Anything you build later must beat this convincingly, or you can't justify the complexity.

### 7.2 Baseline B — Zero-shot LLM (GPT-4 / Claude)

Send the notice and the 12 categories with their definitions to a frontier LLM and ask for classification. This:
- Costs more per inference, so you can't deploy it cheaply
- But sets a "ceiling" expectation — what's possible without training
- Reveals which classes are *intrinsically* hard to disambiguate

If GPT-4 zero-shot scores 0.75 macro-F1 and your fine-tuned XLM-R scores 0.78, you've shown that custom training delivers real, deployable value at much lower cost — that's a publishable finding.

Document baseline numbers in a table:

| Method | Macro-F1 | Per-EN F1 | Per-SI F1 | Per-TA F1 | Cost / 1k inferences |
|--------|----------|-----------|-----------|-----------|----------------------|
| TF-IDF + LR | 0.62 | 0.68 | 0.55 | 0.51 | ~$0.001 |
| GPT-4 zero-shot | 0.75 | 0.79 | 0.71 | 0.69 | ~$3.00 |
| **XLM-R fine-tuned** | **0.81** | **0.84** | **0.79** | **0.77** | **~$0.005** |

(Numbers illustrative — yours will differ.)

---

## 8. Stage 5 — Fine-tune XLM-RoBERTa

### 8.1 Why XLM-R

- Pretrained on 100 languages including Sinhala and Tamil
- Outperforms mBERT on low-resource languages
- Available in HuggingFace
- 270M params (base) — fits on a single 16GB GPU

### 8.2 The training loop (HuggingFace Trainer)

```python
# train_xlmr.py
from transformers import (AutoTokenizer, AutoModelForSequenceClassification,
                          Trainer, TrainingArguments, EarlyStoppingCallback)
from datasets import Dataset
import numpy as np
from sklearn.metrics import f1_score, accuracy_score

MODEL = "xlm-roberta-base"
NUM_LABELS = 12

tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForSequenceClassification.from_pretrained(MODEL, num_labels=NUM_LABELS)

def tokenize(examples):
    return tokenizer(examples["raw_text"], truncation=True, max_length=512, padding=False)

label2id = {c: i for i, c in enumerate(sorted(train.category.unique()))}
id2label = {i: c for c, i in label2id.items()}

def to_hf(df):
    df = df.copy()
    df["labels"] = df.category.map(label2id)
    return Dataset.from_pandas(df[["raw_text", "labels"]]).map(tokenize, batched=True)

train_ds, val_ds, test_ds = to_hf(train), to_hf(val), to_hf(test)

args = TrainingArguments(
    output_dir="/data/models/xlmr-reg-cls",
    num_train_epochs=4,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=32,
    learning_rate=2e-5,
    weight_decay=0.01,
    warmup_ratio=0.1,
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="macro_f1",
    greater_is_better=True,
    logging_steps=50,
    seed=42,
    fp16=True,            # mixed precision — ~2x faster on modern GPUs
    report_to="none",
)

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "macro_f1": f1_score(labels, preds, average="macro"),
        "weighted_f1": f1_score(labels, preds, average="weighted"),
    }

trainer = Trainer(
    model=model, args=args,
    train_dataset=train_ds, eval_dataset=val_ds,
    tokenizer=tokenizer, compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
)
trainer.train()
trainer.save_model("/data/models/xlmr-reg-cls/final")
```

### 8.3 Hyperparameters — defensible defaults

| Hyperparameter | Value | Why |
|---------------|-------|-----|
| Learning rate | 2e-5 | HuggingFace canonical for transformer fine-tuning |
| Batch size | 16 | Fits 16 GB GPU for 512-token sequences |
| Epochs | 3–5 (with early stopping) | More → overfit on small dataset |
| Max sequence length | 512 | XLM-R hard limit |
| Warmup ratio | 0.1 | Standard for stable training |
| Weight decay | 0.01 | Standard regularization |
| Random seed | 42 (and 1, 2 for reproducibility runs) | Always report seed |

**Run with at least 3 different seeds** and report mean ± std. A single-seed result is not a result.

### 8.4 If notices exceed 512 tokens

Strategies:
- **Truncate** — keep first 512 (loses information from the end)
- **Mean pooling over windows** — split into overlapping windows, embed each, average → classify (more accurate, more compute)
- **Use the title + opening + closing** — concatenate three regions

For your initial version, truncate. If macro-F1 plateaus, try the windowing approach as an ablation experiment.

### 8.5 LoRA / parameter-efficient fine-tuning (optional but viva-impressive)

If your GPU is constrained or you want a "modern best practice" angle:

```python
from peft import LoraConfig, get_peft_model
lora_cfg = LoraConfig(r=16, lora_alpha=32, target_modules=["query", "value"],
                     lora_dropout=0.1, task_type="SEQ_CLS")
model = get_peft_model(model, lora_cfg)
# now only ~1% of params train; everything else stays frozen
```

This trains in less than a third of the time, requires far less memory, and produces nearly identical accuracy. A great paragraph in your "Implementation efficiency" section.

---

## 9. Stage 6 — Evaluation

### 9.1 The metric set

Always report:
- **Accuracy** (overall correctness — but misleading on imbalanced data)
- **Macro-F1** (treats all classes equally — your headline number)
- **Weighted-F1** (accounts for class frequency)
- **Per-class precision / recall / F1** (find weak classes)
- **Confusion matrix** (what's confused with what)

### 9.2 Slice analysis — the part that's actually novel

Your contribution isn't "fine-tuned a transformer" (everyone does that). Your contribution is **"how does this model perform across Sri Lankan languages and across regulation types in a multilingual low-resource setting?"** That requires slice analysis:

```python
for lang in ["en", "si", "ta"]:
    mask = test.language == lang
    if mask.sum() > 0:
        f1 = f1_score(test.category[mask], preds[mask], average="macro")
        print(f"  Macro-F1 [{lang}] (n={mask.sum()}): {f1:.3f}")
```

Report:
- Macro-F1 per language
- Macro-F1 per year quarter (does the model generalize forward in time?)
- Macro-F1 per text length bucket (short notices vs long)
- Macro-F1 by extraction method (text-PDF vs OCR-derived) — this exposes if OCR errors hurt classification

These slice tables are what makes a viva panel say "this is solid empirical work."

---

## 10. Stage 7 — Error Analysis

For every model version:

1. Pull the **100 worst-confidence test predictions** and the **100 most confidently-wrong**
2. Read them. Categorize the errors:
   - Truly ambiguous (multi-category, your taxonomy is incomplete)
   - OCR-corrupted text
   - Domain shift (new sub-topic the training data doesn't cover)
   - Annotator inconsistency (your own labels were wrong)

This analysis goes into your thesis as a **qualitative error taxonomy**. It's far more valuable than another decimal point of F1.

```python
# After predictions, look at the confused ones
import numpy as np
probs = trainer.predict(test_ds).predictions
preds = np.argmax(probs, axis=-1)
confidence = np.max(softmax(probs, axis=-1), axis=-1)
wrong = preds != test_labels
hard = test_df[wrong].assign(pred=[id2label[p] for p in preds[wrong]],
                              conf=confidence[wrong])
hard.sort_values("conf", ascending=False).head(100).to_csv("error_analysis_topwrong.csv")
```

---

## 11. Stage 8 — Versioning and Reproducibility

Every trained model gets a record in the `model_versions` table (schema in file 06):

```sql
INSERT INTO model_versions (
    model_name, version, framework, base_checkpoint,
    train_run_id, macro_f1_test, accuracy_test,
    metrics_per_class_json, metrics_per_language_json,
    artifact_path, training_data_snapshot_id,
    git_commit, hyperparams_json, trained_at, trained_by
) VALUES (...);
```

A model artifact is **never** referenced without a version. A FastAPI endpoint loads `model_versions WHERE is_active = true`. Demoting an old model is one row update, not a redeploy.

Also: store the random seeds, the exact `training_args.json`, and the commit hash of the training code. Two months from now your future self will need to reproduce a result for a thesis question — without these, you can't.

---

## 12. Stage 9 — Serving (FastAPI Inference Endpoint)

```python
# api/routers/classify.py
from fastapi import APIRouter
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

router = APIRouter(prefix="/classify")

# loaded once at app startup via lifespan, not per request
class ClassifierState:
    tokenizer = None
    model = None
    id2label = None

state = ClassifierState()

class ClassifyIn(BaseModel):
    text: str

class ClassifyOut(BaseModel):
    category: str
    confidence: float
    top_3: list[dict]

@router.post("", response_model=ClassifyOut)
def classify(payload: ClassifyIn):
    inputs = state.tokenizer(payload.text, truncation=True, max_length=512,
                              return_tensors="pt")
    with torch.no_grad():
        logits = state.model(**inputs).logits[0]
    probs = torch.softmax(logits, dim=-1).cpu().numpy()
    top_idx = probs.argsort()[::-1][:3]
    return ClassifyOut(
        category=state.id2label[int(top_idx[0])],
        confidence=float(probs[top_idx[0]]),
        top_3=[{"category": state.id2label[int(i)], "confidence": float(probs[i])}
                for i in top_idx],
    )
```

Wire model loading into the FastAPI `lifespan` event so it loads once at startup (covered in file 07). Add a batch endpoint for backfilling all unlabeled rows in `regulations`.

### 12.1 Backfill the existing data

After your first deployable model:

```python
# scripts/backfill_classifications.py
unlabeled = pd.read_sql(
    "SELECT id, raw_text FROM regulations WHERE category IS NULL", conn)
# batch through the model
for batch in chunked(unlabeled, 32):
    preds = classifier.classify_batch(batch.raw_text.tolist())
    update_db_categories(batch.id, preds)
```

Now every existing notice has a category — the alert system (file 12) can run.

---

## 13. Pre-Viva Sanity Checklist

Before submitting / presenting:

- [ ] At least 3 different model seeds; mean ± std reported
- [ ] All metrics reported per-class AND per-language
- [ ] Both baselines (TF-IDF, zero-shot LLM) run with same train/test split
- [ ] Confusion matrix included as a figure
- [ ] Error analysis table with at least 30 hand-categorized errors
- [ ] Annotation guidelines as appendix
- [ ] Cohen's Kappa reported (or honest disclosure if only one annotator)
- [ ] Training compute / time / GPU reported (energy/cost transparency)
- [ ] Hyperparameter table with justification for each value
- [ ] Reproducibility: seed, commit hash, data-snapshot ID stored in `model_versions`

---

## 14. What This Stage Produces (Feeds File 12)

You now have:
- A trained classifier accessible via `POST /classify`
- Every row in `regulations` populated with `category` + `category_confidence`
- A `model_versions` row with full provenance
- Per-class, per-language F1 numbers ready to be the headline of your "Results" section

The next file (12) wires this together with the secondary-source watchers, the lag computation, the summarizer, and the alert delivery — the parts that make Module 1 a *deployed system* and not just a model on a hard drive.

---

## Summary

Train the classifier in nine stages: sample → label → split → baselines → fine-tune XLM-R → evaluate → error-analyze → version → serve. The labeling and the slice analysis matter more than the model architecture. Always run baselines. Always temporal-split. Always report per-language. Versioning makes everything reproducible. Output: a deployable multilingual regulatory classifier — and the empirical numbers that constitute your research contribution.
