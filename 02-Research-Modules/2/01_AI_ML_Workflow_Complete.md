# Complete AI/ML Model Development Lifecycle
## Enigmatrix | SME Regulatory Intelligence Platform | University of Moratuwa 2026

---

## 1. Overview: Training From Scratch vs Fine-Tuning

| Dimension          | Train From Scratch                | Fine-Tune Existing Model           |
| ------------------ | --------------------------------- | ---------------------------------- |
| Data Required      | Millions of labeled samples       | Hundreds to thousands of samples   |
| Compute Cost       | Very high (GPUs for weeks/months) | Low to moderate (hours to days)    |
| Time to Production | Months                            | Days to weeks                      |
| Domain Accuracy    | High if data is available         | High with proper fine-tuning       |
| Novelty            | Full control over architecture    | Limited to base model capabilities |
| When to Use        | Truly unique domain, huge data    | Most real-world research projects  |

### Recommendation for Enigmatrix
**Use fine-tuning** for all four modules. Your datasets are in the hundreds-to-thousands range, not millions. Fine-tune `XLM-R` (multilingual) for Modules 1, 2, 4 and use `scikit-learn + XGBoost` for Module 3 (tabular risk prediction). Training from scratch is not justified given your data volume and timeline.

---

## 2. How Models Learn: The Internal Process

```
Raw Text / Tabular Data
        ↓
  Tokenization / Feature Extraction
        ↓
  Forward Pass → Predictions
        ↓
  Loss Calculation (how wrong the prediction is)
        ↓
  Backpropagation (calculate gradients)
        ↓
  Optimizer updates weights (Adam, SGD)
        ↓
  Repeat for N epochs
        ↓
  Converged Model
```

**Key concepts:**
- **Epoch**: One complete pass through the entire training dataset
- **Batch size**: Number of samples processed before updating weights
- **Learning rate**: How large each weight update step is (too high = unstable, too low = slow)
- **Loss function**: Measures prediction error (Cross-Entropy for classification, MSE for regression)
- **Gradient**: Direction and magnitude of weight change needed to reduce loss
- **Backpropagation**: Algorithm that computes gradients by flowing error backward through layers

---

## 3. Complete AI Pipeline — Step by Step

### Step 1 — Problem Identification
- Define a single, measurable research question per module
- Identify expected model inputs and outputs
- Determine whether classification, regression, or generation is needed
- Set success criteria (e.g., accuracy > 80%, F1 > 0.75)

### Step 2 — Research Module Planning
- Divide system into independent modules with clear boundaries
- Define data flow between modules
- Identify shared components (e.g., verified knowledge base used by Modules 2 and 4)
- Assign ownership per team member

### Step 3 — Data Collection
- Identify primary data sources (surveys, scraping, public records)
- Define minimum data requirements per class/label
- Document every data source with URL, access method, and license
- Store raw data immediately in PostgreSQL with collection timestamp

**For Enigmatrix specifically:**
| Module | Primary Novel Data | Collection Method |
|---|---|---|
| M1 | Regulatory lag timeline | Gazette PDF scraping + survey |
| M2 | Compliance knowledge test | 40-50 question Google Form |
| M3 | SME vulnerability dataset | Survey + IRD public records + CTGAN synthetic |
| M4 | Annotated misinformation corpus | Social media scraping + Label Studio annotation |

### Step 4 — Data Preprocessing
1. **Cleaning**: Remove nulls, fix encoding issues, strip HTML tags
2. **Normalization**: Scale numeric features to 0–1 or z-score for ML models
3. **Deduplication**: Hash-based exact duplicate removal; semantic deduplication for text
4. **Labeling**: Use Label Studio for manual annotation; calculate Cohen's Kappa for inter-annotator agreement
5. **Feature Engineering**:
   - Text: TF-IDF vectors, BERT embeddings, token length, language detection
   - Tabular: SME sector encoding, lag duration in days, violation count
6. **Train/Validation/Test Split**: 70% / 15% / 15% — stratified by class

### Step 5 — Model Selection
| Module | Baseline Model | Final Model | Justification |
|---|---|---|---|
| M1 (NLP Classifier) | TF-IDF + Logistic Regression | Fine-tuned XLM-R | Multilingual support for Sinhala/English |
| M2 (RAG Q&A) | BM25 keyword retrieval | LangChain + FAISS + OpenAI/Llama | Grounded, cited answers from verified docs |
| M3 (Risk Prediction) | Logistic Regression | XGBoost + SHAP | Handles class imbalance, explainable |
| M4 (Misinformation) | TF-IDF classifier | Fine-tuned XLM-R + RAG verification | Cross-lingual, Sinhala/Tamil coverage |

### Step 6 — Model Training
```python
# Example: Fine-tuning XLM-R with HuggingFace
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments

tokenizer = AutoTokenizer.from_pretrained("xlm-roberta-base")
model = AutoModelForSequenceClassification.from_pretrained("xlm-roberta-base", num_labels=4)

training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=5,
    per_device_train_batch_size=16,
    learning_rate=2e-5,           # Standard for fine-tuning transformers
    weight_decay=0.01,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    compute_metrics=compute_metrics
)

trainer.train()
```

**Key hyperparameters to tune:**
- `learning_rate`: 1e-5 to 5e-5 for transformers; 0.01–0.3 for XGBoost
- `num_train_epochs`: 3–10 for transformers
- `batch_size`: 8, 16, or 32 depending on GPU memory
- `max_seq_length`: 128–512 tokens for text classification

### Step 7 — Evaluation
| Metric | When to Use | Formula |
|---|---|---|
| Accuracy | Balanced classes | Correct / Total |
| Precision | When false positives are costly | TP / (TP + FP) |
| Recall | When false negatives are costly | TP / (TP + FN) |
| F1-Score | Imbalanced classes | 2 × (P × R) / (P + R) |
| AUC-ROC | Binary classification | Area under ROC curve |
| RAGAS Faithfulness | RAG systems | Grounded answer verification |
| Cohen's Kappa | Annotation agreement | Agreement beyond chance |

### Step 8 — Deployment
```
PostgreSQL Database
       ↓
FastAPI Backend (model loaded at startup)
       ↓
REST API Endpoints (/predict, /classify, /verify)
       ↓
React.js / Next.js Frontend
```

**FastAPI model serving example:**
```python
from fastapi import FastAPI
from transformers import pipeline

app = FastAPI()
classifier = pipeline("text-classification", model="./trained_model")

@app.post("/classify")
def classify_text(text: str):
    result = classifier(text)
    return {"label": result[0]["label"], "score": result[0]["score"]}
```

### Step 9 — Monitoring & Retraining
- Track prediction confidence scores in PostgreSQL with a `model_predictions` table
- Flag low-confidence predictions for human review
- Set up a `training_status` column: `untrained | in_training | trained`
- Retrain when: new data batch > 10% of original training size, or accuracy drops > 5%
- Version models using MLflow or simple folder naming: `model_v1`, `model_v2`

---

## 4. Missing Steps Most Researchers Overlook

| Missing Step | What It Is | Where It Fits |
|---|---|---|
| Data versioning | Track which data trained which model | Between Steps 4 and 6 |
| Baseline comparison | Always test simplest model first | Before Step 6 |
| Error analysis | Manually inspect wrong predictions | After Step 7 |
| Bias/fairness audit | Check model fairness across groups | After Step 7 |
| Reproducibility | Set random seeds, log all configs | Throughout |
| Ethics review | Especially for social media data | Before Step 3 |

---
*Generated by Perplexity AI for Enigmatrix Research Group — University of Moratuwa 2026*
