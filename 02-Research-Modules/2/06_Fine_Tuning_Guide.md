# Fine-Tuning vs Training From Scratch
## Step-by-Step Fine-Tuning Guide for Enigmatrix Modules
## University of Moratuwa 2026

---

## What Fine-Tuning Actually Does Internally

When you fine-tune a pretrained model like XLM-R:

```
Pretrained XLM-R weights (trained on 2.5TB of text across 100 languages)
        ↓
Add a task-specific classification head (new layer with random weights)
        ↓
Feed your labeled domain data
        ↓
Backpropagation updates ALL weights, but:
  - Lower layers (language understanding) change very little
  - Upper layers (task-specific reasoning) change significantly
  - Classification head changes the most
        ↓
Result: Model that understands language (from pretraining)
        AND understands your specific task (from fine-tuning)
```

This is why fine-tuning works with small datasets — the language understanding is already learned.

---

## Fine-Tuning XLM-R for Module 1 (Regulatory Classifier)

### Step 1: Prepare your dataset

```python
import pandas as pd
from sklearn.model_selection import train_test_split

# Your labeled gazette changes
df = pd.read_csv('regulatory_changes_labeled.csv')
# Columns: text, label (0=tax, 1=labor, 2=environmental, 3=financial)

train_df, temp_df = train_test_split(df, test_size=0.3, stratify=df['label'], random_state=42)
val_df, test_df = train_test_split(temp_df, test_size=0.5, stratify=temp_df['label'], random_state=42)

print(f"Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
```

### Step 2: Tokenize

```python
from transformers import AutoTokenizer
import torch
from torch.utils.data import Dataset

tokenizer = AutoTokenizer.from_pretrained('xlm-roberta-base')

class RegulatoryDataset(Dataset):
    def __init__(self, texts, labels, max_length=256):
        self.encodings = tokenizer(
            texts.tolist(),
            truncation=True,
            padding='max_length',
            max_length=max_length,
            return_tensors='pt'
        )
        self.labels = torch.tensor(labels.tolist())

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            'input_ids': self.encodings['input_ids'][idx],
            'attention_mask': self.encodings['attention_mask'][idx],
            'labels': self.labels[idx]
        }

train_dataset = RegulatoryDataset(train_df['text'], train_df['label'])
val_dataset = RegulatoryDataset(val_df['text'], val_df['label'])
test_dataset = RegulatoryDataset(test_df['text'], test_df['label'])
```

### Step 3: Load model and define metrics

```python
from transformers import AutoModelForSequenceClassification
from sklearn.metrics import accuracy_score, f1_score
import numpy as np

NUM_LABELS = 4  # tax, labor, environmental, financial
model = AutoModelForSequenceClassification.from_pretrained(
    'xlm-roberta-base',
    num_labels=NUM_LABELS
)

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return {
        'accuracy': accuracy_score(labels, predictions),
        'f1_macro': f1_score(labels, predictions, average='macro'),
        'f1_weighted': f1_score(labels, predictions, average='weighted')
    }
```

### Step 4: Configure training

```python
from transformers import TrainingArguments, Trainer

training_args = TrainingArguments(
    output_dir='./module1_xlmr_results',
    num_train_epochs=5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=32,
    learning_rate=2e-5,          # Standard for transformer fine-tuning
    weight_decay=0.01,           # L2 regularization
    warmup_ratio=0.1,            # 10% of steps for LR warmup
    evaluation_strategy='epoch',
    save_strategy='epoch',
    load_best_model_at_end=True,
    metric_for_best_model='f1_macro',
    greater_is_better=True,
    logging_dir='./logs',
    fp16=True                    # Mixed precision if GPU available
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    compute_metrics=compute_metrics
)
```

### Step 5: Train and evaluate

```python
trainer.train()

# Evaluate on test set
test_results = trainer.evaluate(test_dataset)
print(f"Test Accuracy: {test_results['eval_accuracy']:.4f}")
print(f"Test F1 (macro): {test_results['eval_f1_macro']:.4f}")

# Save model
trainer.save_model('./module1_trained_model')
tokenizer.save_pretrained('./module1_trained_model')
```

---

## Fine-Tuning for Module 4 (Misinformation Classifier)

The process is identical to Module 1 but with different labels:
- Labels: 0=accurate, 1=partially_accurate, 2=misleading, 3=false
- Key difference: Add class weights to handle imbalanced annotation data

```python
from torch import nn

# Calculate class weights from annotation distribution
label_counts = df['annotation_label'].value_counts()
total = len(df)
class_weights = torch.tensor([
    total / (4 * label_counts['accurate']),
    total / (4 * label_counts['partially_accurate']),
    total / (4 * label_counts['misleading']),
    total / (4 * label_counts['false'])
], dtype=torch.float)

class WeightedTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False):
        labels = inputs.get('labels')
        outputs = model(**inputs)
        logits = outputs.get('logits')
        loss_fct = nn.CrossEntropyLoss(weight=class_weights.to(model.device))
        loss = loss_fct(logits.view(-1, self.model.config.num_labels), labels.view(-1))
        return (loss, outputs) if return_outputs else loss
```

---

## RAG Pipeline for Module 2 (Compliance Q&A)

```python
from langchain.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI

# Step 1: Load verified compliance documents
loaders = [
    PyMuPDFLoader('ird_vat_guide_2024.pdf'),
    PyMuPDFLoader('epf_employer_guide.pdf'),
    PyMuPDFLoader('eroc_registration_guide.pdf')
]
documents = []
for loader in loaders:
    documents.extend(loader.load())

# Step 2: Split into chunks
splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=64,
    separators=['\n\n', '\n', '. ', ' ']
)
chunks = splitter.split_documents(documents)

# Step 3: Embed and store
embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
vectorstore = Chroma.from_documents(chunks, embeddings, persist_directory='./compliance_vectorstore')
vectorstore.persist()

# Step 4: Build RAG chain
retriever = vectorstore.as_retriever(search_kwargs={'k': 5})
qa_chain = RetrievalQA.from_chain_type(
    llm=OpenAI(temperature=0),
    chain_type='stuff',
    retriever=retriever,
    return_source_documents=True
)

# Step 5: Query
result = qa_chain('What is the current VAT registration threshold in Sri Lanka?')
print(result['result'])
print('Sources:', [doc.metadata['source'] for doc in result['source_documents']])
```

---

## XGBoost Training for Module 3 (Risk Prediction)

```python
import xgboost as xgb
from sklearn.model_selection import StratifiedKFold, cross_val_score
from imblearn.over_sampling import SMOTE
import shap
import numpy as np

# Features: sector, size, years_operating, region, prior_violations, filing_delays
X = df[feature_columns]
y = df['compliance_violation']  # 0=compliant, 1=violation

# Handle class imbalance
smote = SMOTE(random_state=42, sampling_strategy=0.5)
X_resampled, y_resampled = smote.fit_resample(X_train, y_train)

# Train XGBoost
model = xgb.XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=10,    # Additional weight for minority class
    use_label_encoder=False,
    eval_metric='auc',
    random_state=42
)
model.fit(
    X_resampled, y_resampled,
    eval_set=[(X_val, y_val)],
    early_stopping_rounds=30,
    verbose=50
)

# SHAP Explainability
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)
shap.summary_plot(shap_values, X_test, feature_names=feature_columns, show=False)
```

---

## Hyperparameter Selection Reference

| Model | Parameter | Recommended Range | How to Tune |
|---|---|---|---|
| XLM-R | learning_rate | 1e-5 to 5e-5 | Try 2e-5 first |
| XLM-R | num_epochs | 3 to 10 | Use early stopping |
| XLM-R | batch_size | 8, 16, 32 | Largest that fits GPU |
| XLM-R | max_seq_length | 128, 256, 512 | 256 for gazette text |
| XGBoost | n_estimators | 100-500 | Use early stopping |
| XGBoost | max_depth | 3-8 | 6 as default |
| XGBoost | learning_rate | 0.01-0.3 | 0.05-0.1 typically |
| XGBoost | subsample | 0.6-1.0 | 0.8 as default |

---
*Generated by Perplexity AI for Enigmatrix Research Group - University of Moratuwa 2026*
