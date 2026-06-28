# 02 — The Complete ML Lifecycle (Step-by-Step, With Examples From Each Module)

> Goal: walk through the full pipeline from "we have a problem" to "we have a deployed, monitored model" — with concrete examples from each Enigmatrix module so the abstract steps become real.

The lifecycle has **9 stages**. Many beginners skip stages 1, 4, 7, and 9. That is exactly what makes student projects look like demos and not research.

---

## Stage 0 — Why a Lifecycle Matters

Without a lifecycle, you end up doing things in the wrong order:

- Building a model before you know what you are predicting (skipped Stage 1)
- Reporting results without a held-out test set (skipped Stage 7 properly)
- Calling something "production-ready" with no monitoring plan (skipped Stage 9)

A lifecycle ensures every research finding is defensible.

---

## Stage 1 — Problem Identification & Framing

**What you do:** Convert a vague real-world concern into a measurable, model-shaped problem.

**The three questions to answer:**

1. What is the **input**? (What goes in?)
2. What is the **output**? (What comes out?)
3. How will you **measure success**? (What number tells you it worked?)

| Module | Input | Output | Success Metric |
|--------|-------|--------|----------------|
| 1 — Awareness | Gazette PDF text excerpt | Regulatory change category (TAX_RATE_CHANGE / DEADLINE / NEW_FORM / etc.) + extracted metadata | Macro-F1 ≥ 0.80 on held-out test set; mean information lag reduction ≥ 50% |
| 2 — Knowledge | SME natural-language question + verified knowledge base | Cited answer | RAGAS faithfulness ≥ 0.85; answer accuracy vs expert ≥ 0.80 |
| 3 — Risk | SME profile (sector, age, size, region, history) | Risk score 0–1 | ROC-AUC ≥ 0.75; precision @ top 10% ≥ 0.60 |
| 4 — Misinformation | Social media post text | Verdict (accurate / partially accurate / misleading / false) + evidence | Macro-F1 ≥ 0.75; coverage ≥ 80% of test claims |

**Deliverable of this stage:** A 1-page problem statement per module containing exactly the three things above.

---

## Stage 2 — Research Module Planning

**What you do:** Decompose the system, define module boundaries, and define interfaces.

For Enigmatrix, this is already done in your proposal. Each module has:

- **Responsibility:** Investigates one specific information barrier.
- **Inputs:** Public records, surveys, social media (varies per module).
- **Outputs:** A trained model + a novel dataset + a measurable finding + a deployable component.
- **Interfaces:** Module 1's classified regulations feed Module 2's knowledge base; Module 2's verified facts feed Module 4's verifier; Module 1's lag data correlates with Module 4's misinformation timing.

**Best practice:** Document the inter-module data contracts as JSON schemas. For example, what does a "classified regulatory change" record look like when Module 1 hands it to Module 2?

```json
{
  "regulation_id": "GAZ-2026-2401-12",
  "publication_date": "2026-04-15",
  "source": "documents.gov.lk",
  "category": "TAX_RATE_CHANGE",
  "agency": "IRD",
  "language": "en",
  "title_en": "Amendment to VAT rates",
  "summary_en": "...",
  "effective_date": "2026-07-01",
  "raw_text": "...",
  "classifier_confidence": 0.94
}
```

This contract is what every other module consumes.

---

## Stage 3 — Data Collection

**What you do:** Acquire the inputs and the labeled examples.

For each module, data comes from three buckets:

1. **Public records** — gazettes, court judgments, IRD lists, news, social posts.
2. **Survey data** — SME owner / staff responses you collect via Google Forms or your own web app.
3. **Synthetic data** — generated programmatically when real data is too sparse (Module 3 specifically).

**Collection methods:**

| Method | Tools | Used in |
|--------|-------|---------|
| Web scraping (HTML) | Scrapy, BeautifulSoup, Playwright (for JS-heavy pages) | All modules |
| PDF download + parsing | requests, PyMuPDF, pdfplumber | Modules 1, 2 |
| Social media APIs | Twitter API, Reddit API, Facebook Graph API | Module 4 |
| Surveys | Google Forms (quick start) → custom Next.js + PostgreSQL app (scalable) | All modules |
| Synthetic generation | SDV, CTGAN, Faker | Module 3 |

**Critical:** Save EVERYTHING raw. Never overwrite a downloaded file. Your raw archive is your audit trail.

```
data/
├── raw/
│   └── gazettes/
│       └── 2026-04-15_extraordinary_2401.pdf
├── interim/
│   └── gazettes/
│       └── 2026-04-15_extraordinary_2401.txt
└── processed/
    └── gazette_changes_v1.parquet
```

---

## Stage 4 — Data Preprocessing

**What you do:** Turn raw, messy data into clean model-ready data.

This is where most projects spend 60–70% of their time. Sub-stages:

### 4.1 Cleaning
- Remove header / footer noise from PDFs
- Strip HTML tags from web pages
- Normalize whitespace, unicode (`unicodedata.normalize('NFKC', text)`)
- Remove non-printable characters
- Fix encoding issues (especially for Sinhala / Tamil text)

### 4.2 Deduplication
- Exact duplicate removal: hash each record, drop duplicate hashes.
- Near-duplicate removal: MinHash or SimHash for posts that are 95% identical (common on social media).

### 4.3 Normalization
- Lowercasing (English only — be careful with Sinhala/Tamil)
- Date normalization (`"April 15, 2026"`, `"15/04/2026"`, `"2026-04-15"` → all become ISO `2026-04-15`)
- Currency normalization (LKR / Rs. / රු.)
- Number normalization (replace digits with `<NUM>` token if classifier should not memorize specific amounts)

### 4.4 Labeling (the most important sub-stage)
- Define a **clear labeling guideline document** (categories, examples, edge cases, what to do when uncertain)
- Use **Label Studio** (open source) — easy install, supports text classification and span labeling
- At least **two annotators** per item for ≥ 10% of the data → measure agreement (Cohen's Kappa ≥ 0.7 is the minimum acceptable)
- Resolve disagreements via discussion → update guidelines → re-label disputed items

### 4.5 Feature Engineering
- For classical ML (Module 3 baselines): create derived features — `business_age = (now - registration_date).days`, `years_since_last_filing`, etc.
- For NLP transformers: minimal — just tokenize. The model handles everything else.

### 4.6 Splitting
The single most important step in this entire stage:

```
Total dataset
├── 70% Training set     (model sees this and adjusts weights)
├── 15% Validation set   (used during training for early stopping, hyperparameter tuning)
└── 15% Test set         (locked away until final evaluation, opened ONCE)
```

For time-series data (Module 1, Module 3), do a **temporal split** (train on 2018–2024, test on 2025–2026) — not random — because random splits leak future information.

---

## Stage 5 — Model Selection

**What you do:** Decide what model to use, and crucially, decide your baselines.

### 5.1 Always have baselines
- **Trivial baseline:** Predict the majority class. (Tells you what accuracy means nothing.)
- **Rule-based baseline:** Hand-written keyword rules. (Often surprisingly good.)
- **Classical ML baseline:** TF-IDF + Logistic Regression, or XGBoost on tabular features.
- **Pretrained zero-shot baseline:** Run the task through GPT-4 / Claude / a multilingual model with no training.

### 5.2 Then your candidate model
- Fine-tuned XLM-R for text classification (Modules 1, 4)
- XGBoost for tabular risk prediction (Module 3)
- LSTM / temporal model if you have sequential data (Module 3 temporal pattern detection)
- RAG + LLM for QA (Module 2)

### 5.3 Selection criteria

| Criterion | Why it matters |
|-----------|----------------|
| Accuracy on test set | The headline number |
| Inference speed | Affects whether real-time alerts are feasible |
| Memory / compute requirements | Affects whether you can deploy on a small VM |
| Multilingual support | Critical — your data is Sinhala / Tamil / English |
| Reproducibility | Pin versions, log seeds, save weights |

---

## Stage 6 — Model Training

**What you do:** Run the actual training loop.

### 6.1 Setup
- Choose hardware — Google Colab (free T4 GPU), Kaggle (free P100), or paid (Lambda Labs, RunPod). For your fine-tuning, free tiers are sufficient.
- Set seeds (`torch.manual_seed(42)`, `numpy.random.seed(42)`, `random.seed(42)`) — this matters for reproducibility.
- Log everything with **Weights & Biases** (`wandb`) or **MLflow**. Free, professional, lets you compare runs.

### 6.2 Hyperparameters to tune
For transformer fine-tuning, the only ones that matter at first:

| Parameter | Typical value | Why |
|-----------|---------------|-----|
| Learning rate | 2e-5 to 5e-5 | Lower for larger models |
| Batch size | 8 / 16 / 32 | Limited by GPU memory |
| Epochs | 3 to 5 | More risks overfitting |
| Weight decay | 0.01 | Standard |
| Warmup steps | 10% of total | Helps stability |
| Max sequence length | 256 / 512 | Longer = slower |

### 6.3 Training loop (conceptually)
```
for epoch in range(num_epochs):
    for batch in train_loader:
        outputs = model(batch.inputs)
        loss = loss_fn(outputs, batch.labels)
        loss.backward()                  # backpropagation
        optimizer.step()                 # update weights
        optimizer.zero_grad()
    
    val_metrics = evaluate(model, val_loader)
    if val_metrics.f1 > best_f1:
        save_checkpoint(model)
        best_f1 = val_metrics.f1
    else:
        patience -= 1
        if patience == 0: break          # early stopping
```

### 6.4 What to watch
- **Training loss going down** but **validation loss going up** = overfitting → stop earlier or add regularization.
- **Both losses flat at high value** = model not learning → check learning rate, data quality, label correctness.
- **Validation metric oscillates wildly** = batch size too small or learning rate too high.

---

## Stage 7 — Evaluation

**What you do:** Honestly measure how well the model performs.

### 7.1 Quantitative metrics

| Task type | Required metrics |
|-----------|------------------|
| Binary classification | Accuracy, Precision, Recall, F1, ROC-AUC, Confusion Matrix |
| Multi-class classification | Macro-F1, Weighted-F1, per-class precision/recall, Confusion Matrix |
| Risk regression | MAE, RMSE, R², calibration plot |
| RAG / QA | RAGAS (faithfulness, answer-relevance, context-precision, context-recall), expert-rated accuracy |
| Information retrieval | Recall@k, Precision@k, MRR, NDCG |

### 7.2 Qualitative analysis
- **Error analysis** — sample 50 wrong predictions, categorize the failure modes. This is where research insights come from.
- **Slice analysis** — does the model perform worse on Sinhala vs English? On rural vs urban SMEs? On certain regulatory categories? Report these slices.
- **Human comparison** — for some tasks, ask a CA / tax professional to do the same task on a small sample. Compare model accuracy with human accuracy. Powerful for the discussion section.

### 7.3 Statistical rigor
- Report confidence intervals — bootstrap your test set 1000 times to get a 95% CI on F1.
- Report the **delta vs baseline** with significance — is your fine-tuned model statistically significantly better than TF-IDF? Use McNemar's test for paired classifiers.

### 7.4 The validation hierarchy
1. **Internal validation** — your held-out test set.
2. **Cross-validation** — k-fold (5 or 10) on the train+val set, useful when data is small.
3. **External validation** — a fresh dataset you collected later, ideally from a different time period.
4. **User validation** — actual SMEs interact with your system, you measure satisfaction and real-world utility.

All four matter. Most theses do (1) only. Doing (1)+(3)+(4) is what makes the research strong.

---

## Stage 8 — Deployment

**What you do:** Make the model usable from your application.

### 8.1 Options
- **REST API** (recommended): wrap the model in a FastAPI endpoint, frontend calls it.
- **Batch jobs**: cron job that runs the model nightly on new gazettes.
- **Embedded in app**: only for very small models.

### 8.2 Pattern (FastAPI + transformers)

```python
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

app = FastAPI()

# load once at startup, not per request
tokenizer = AutoTokenizer.from_pretrained("./models/regulatory_classifier_v1")
model = AutoModelForSequenceClassification.from_pretrained("./models/regulatory_classifier_v1")
model.eval()

class ClassifyRequest(BaseModel):
    text: str

@app.post("/classify-regulation")
def classify(req: ClassifyRequest):
    inputs = tokenizer(req.text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.softmax(logits, dim=-1)[0].tolist()
    pred_idx = int(torch.argmax(logits, dim=-1).item())
    return {
        "category": model.config.id2label[pred_idx],
        "confidence": probs[pred_idx],
        "all_probs": dict(zip(model.config.id2label.values(), probs)),
        "model_version": "regulatory_classifier_v1.0.0"
    }
```

### 8.3 Production concerns
- **Versioning** — every model deployed must have a version string returned in every response. Future-you will thank you.
- **Logging** — log every input, prediction, latency, confidence. This becomes your monitoring data.
- **Fallback** — if the model fails or returns low confidence, fall back to "uncertain — flag for human review".
- **Latency budget** — for real-time SME alerts, < 500 ms per inference is comfortable on a single CPU.

---

## Stage 9 — Monitoring & Updating

**What you do:** Watch the model in production and decide when to retrain.

This is the stage almost every student project skips — and skipping it means you cannot claim your system is "production-ready" or "scalable".

### 9.1 What to monitor
- **Latency** — p50, p95, p99 response times.
- **Throughput** — requests per minute.
- **Confidence distribution** — if average confidence drops, your data distribution may have shifted (a new regulation type appeared).
- **Prediction distribution** — if suddenly 80% of inputs are classified as one category, something is off.
- **User feedback** — if SMEs flag predictions as wrong, log them.

### 9.2 The retraining trigger
Retrain when one of:
- Confidence has dropped > 10% from baseline (data drift)
- 200+ new labeled examples have been collected
- A new regulatory category appears in the wild that the model was not trained on
- Quarterly schedule, regardless

### 9.3 Tracking trained vs untrained data (your idea — confirmed correct)

You proposed: store data in PostgreSQL, mark each record as `trained=true` once it has been used in a training run, only export `trained=false` records for the next training cycle. **This is exactly right.** Implementation in file `06_Data_Collection_and_Management.md`.

---

## Stage Mapping Per Module

The 9 stages apply to every module, but with different emphasis:

| Stage        | Module 1 emphasis                  | Module 2 emphasis                  | Module 3 emphasis                   | Module 4 emphasis            |
| ------------ | ---------------------------------- | ---------------------------------- | ----------------------------------- | ---------------------------- |
| 1 Problem    | Information lag definition         | Knowledge gap score                | Risk prediction definition          | Misinformation taxonomy      |
| 2 Modules    | Pipeline orchestration             | KB structure                       | Feature space                       | Annotation taxonomy          |
| 3 Data       | Gazette + news + survey            | Official docs + survey + social    | Defaulter list + survey + synthetic | Social media + FactCheck.lk  |
| 4 Preprocess | PDF extraction = HUGE work         | Document chunking                  | Class balancing (SMOTE)             | Multi-language normalization |
| 5 Model      | XLM-R classifier                   | RAG (retrieval + generation)       | XGBoost + LSTM                      | XLM-R + RAG verifier         |
| 6 Train      | Fine-tune classifier               | Tune retrieval, prompt engineering | Hyperparameter sweep                | Fine-tune classifier + RAG   |
| 7 Eval       | F1 + lag-reduction measurement     | RAGAS + expert                     | ROC-AUC + SHAP                      | F1 + spread analysis         |
| 8 Deploy     | Scheduled gazette monitor + alerts | QA chatbot endpoint                | Risk score endpoint                 | Real-time verifier           |
| 9 Monitor    | New regulation detection           | KB freshness                       | Concept drift                       | New misinformation themes    |

---

## What "Missing Steps" Means in Your Proposal

You asked about missing layers between data collection and final output. Looking at your proposal, the layers actually present are:

- ✅ Data collection (described)
- ✅ Procedures and technologies (described)
- ✅ Solution built (described)

The layers your proposal needs to make explicit (and which this guide provides):

- ⚠ **Preprocessing layer** — exactly how raw PDF becomes clean text becomes labeled examples (covered in `10_Module1_Gazette_PDF_Extraction_Pipeline.md`)
- ⚠ **Labeling protocol** — what categories, what guidelines, who labels, agreement measure (covered in `11_Module1_NLP_Classifier_Training.md`)
- ⚠ **Train/val/test split policy** — temporal split for time-sensitive data (covered in `11`)
- ⚠ **Baseline → fine-tuned comparison** — required for research credibility (covered in `11`)
- ⚠ **Deployment & monitoring** — turning the model into a service (covered in `12_Module1_End_to_End_Workflow.md`)

These are the "missing layers" your supervisor would otherwise ask about.

---

## Summary

The lifecycle is **non-negotiable**: skip a stage and your evaluation becomes indefensible. The stages most often skipped are **Stage 4** (preprocessing rigor — labeling guidelines and inter-annotator agreement) and **Stage 7** (proper baselines and slice analysis). Make these visible in your thesis and your work will pass viva confidently.
