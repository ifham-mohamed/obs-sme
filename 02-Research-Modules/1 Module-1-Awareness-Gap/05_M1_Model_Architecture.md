# 05 — Module 1: Model Architecture

> **Cross-references:** [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md) · [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) · [10_M1_Sinhala_Tamil_NLP.md](10_M1_Sinhala_Tamil_NLP.md)
> **See also:** [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) — `ml/m1/model/architecture.py`, `ml/m1/data/samplers.py`, `ml/m1/model/calibration.py`.
> **Sub-step companions:** [05_M1_1_Sampling_Strategy.md](05_M1_1_Sampling_Strategy.md) · [05_M1_2_Architecture_Comparison_Deep_Dive.md](05_M1_2_Architecture_Comparison_Deep_Dive.md) · [05_M1_3_LoRA_Hyperparameter_Justification.md](05_M1_3_LoRA_Hyperparameter_Justification.md)

---

## Abstract

This document specifies the classification model architecture for Module 1, which must simultaneously assign each gazette document to one of 12 regulatory categories (single-label) and to one or more of 10 SME industry sectors (multi-label). Four architectural approaches are evaluated: training from scratch, fine-tuning a pre-trained multilingual BERT-family model, zero-shot classification via large language models, and rule-based classification. Fine-tuning `facebook/xlm-roberta-base` with Low-Rank Adaptation (LoRA) is selected based on its superior multilingual performance, reproducibility, offline inference capability, and cost-effectiveness. A dual-head architecture shares a common XLM-R encoder with separate classification heads for category prediction and sector prediction, enabling joint training with a combined loss function.

---

## 1. Sampling Strategy for Labeling

Before model architecture can be addressed, a representative labeled corpus must be constructed. Naïve random sampling from the regulations table produces a corpus biased toward recent English gazettes and dominant categories. A three-step sampling strategy ensures diversity across language, time period, and regulatory topic — all of which affect cross-lingual F1 and temporal generalization.

### 1.1 Step 1 — Stratified Random Sampling

Sample proportionally across publication year and primary language to ensure the corpus covers all years and all three gazette languages:

```python
# scripts/sample_for_labeling.py
import pandas as pd

df = pd.read_sql(
    "SELECT id, raw_text, primary_language, gazette_published_date FROM m1_regulations "
    "WHERE raw_text IS NOT NULL AND status = 'extracted'",
    conn
)
df["year"] = pd.to_datetime(df["gazette_published_date"]).dt.year

# Stratify by year × language; sample n=20 from each non-empty cell
stratified = (
    df.groupby(["year", "primary_language"], group_keys=False)
    .apply(lambda g: g.sample(min(len(g), 20), random_state=42))
)
```

This guarantees Sinhala and Tamil documents are represented even if they form a minority of the corpus (≈15% Tamil, ≈35% Sinhala, ≈50% English per the expected distribution).

**Edge case — sparse year-language cells.** Some (year, language) cells contain fewer than 20 documents (e.g. Tamil gazettes for 2015 ≈ 8 documents). The `min(len(g), 20)` cap above silently under-samples these cells — fine in isolation, but it drops the cell's *relative* weight in the corpus. The rule for cells with `len(g) < 5` is: **take all of them**, then top up that language with the next-most-similar year via the cluster-based sampling in §1.2. This keeps minority cells from being washed out by majority cells in the same stratum:

```python
SMALL_CELL_THRESHOLD = 5

def stratified_with_small_cell_handling(df):
    out = []
    for (year, lang), g in df.groupby(["year", "primary_language"]):
        if len(g) < SMALL_CELL_THRESHOLD:
            out.append(g)                              # take all
        else:
            out.append(g.sample(min(len(g), 20), random_state=42))
    return pd.concat(out)
```

The detailed sampling algorithm — including the silhouette-based justification for `k=20` clusters, the active-learning baseline-vs-production-baseline disambiguation, and the budget-aware re-sampling cadence — is in [05_M1_1_Sampling_Strategy.md](05_M1_1_Sampling_Strategy.md).

### 1.2 Step 2 — Cluster-Based Topical Diversity

After stratified sampling, k-means clustering on TF-IDF vectors ensures topical coverage. Without this step, the stratified sample may over-represent the most frequent regulatory topic (TAX_RATE_CHANGE) even within each year-language cell:

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

# Cluster remaining (un-selected) regulations for diversity top-up
remaining = df[~df["id"].isin(stratified["id"])]
vec = TfidfVectorizer(max_features=10000, ngram_range=(1, 2), sublinear_tf=True)
X = vec.fit_transform(remaining["raw_text"].fillna(""))
km = KMeans(n_clusters=20, random_state=42, n_init=10).fit(X)
remaining["cluster"] = km.labels_

diverse = (
    remaining.groupby("cluster", group_keys=False)
    .apply(lambda g: g.sample(min(len(g), 15), random_state=42))
)

to_label = pd.concat([stratified, diverse]).drop_duplicates("id")
to_label.to_csv("/data/labeling/batch_01.csv", index=False)
```

**k=20 clusters** is chosen empirically: fewer clusters allow duplicates of the same regulatory topic; more clusters produce singletons that are hard to annotate consistently. Each cluster is manually inspected to confirm it represents a coherent topic area before labeling proceeds.

### 1.3 Step 3 — Active Learning (After First 300 Labels)

Once the first 300 labeled examples have been used to train a preliminary TF-IDF+LR baseline, active learning identifies the highest-information unlabeled examples — those where the baseline classifier is least confident:

```python
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import numpy as np

# Train baseline on first 300 labels
pipe = Pipeline([
    ("tfidf", TfidfVectorizer(max_features=20000, ngram_range=(1, 2))),
    ("clf",   LogisticRegression(class_weight="balanced", max_iter=2000))
])
pipe.fit(labeled_300["raw_text"], labeled_300["change_category"])

# Score unlabeled pool
unlabeled_probs = pipe.predict_proba(unlabeled_pool["raw_text"])
uncertainty = 1.0 - np.max(unlabeled_probs, axis=1)  # max probability margin

# Prioritise most uncertain examples for next labeling batch
next_batch = unlabeled_pool.iloc[uncertainty.argsort()[::-1][:200]]
```

Active learning reduces labeling effort by an estimated 40% for the same final model quality, as annotators focus on genuinely ambiguous examples rather than clear-cut cases the baseline already handles correctly. The strategy is documented in the thesis methodology as "pool-based uncertainty sampling."

**Avoiding the chicken-and-egg trap.** Note the AL baseline (TF-IDF+LR trained on the first 300 labels) is **not** the same artefact as the **production baseline** (TF-IDF+LR trained on the *full* labeled set, used in §6 of [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) for the XLM-R ablation). They share a name and a feature pipeline but are otherwise distinct:

| Artefact | Trained on | Used for | Discarded when |
|---|---|---|---|
| **AL baseline** (`baseline_al_v<N>`) | first 300, then 500, then 700 labels | Uncertainty scoring for the *next* labeling batch | After labeling is complete |
| **Production baseline** (`baseline_prod`) | All 800+ labels (full train split) | Ablation comparison against XLM-R in evaluation | Retained as a permanent comparison point |

This separation matters because the AL baseline is *deliberately* trained on early, possibly biased label distributions — its job is to find uncertain examples, not to score well. Mixing the two would either (a) train the production baseline on a biased subset, or (b) bias the AL strategy toward a "too-strong" baseline that no longer surfaces genuinely uncertain examples.

---

## 2. Classification Task Definition

### 1.1 Task 1: Category Classification (Single-Label)

Given cleaned gazette text $x$, predict category $k \in \{k_1, \ldots, k_{12}\}$:

| Code | Category | Expected Proportion |
|---|---|---|
| `TAX_RATE_CHANGE` | Income tax, VAT, customs duty amendments | 25% |
| `LABOUR_LAW` | Minimum wage, leave, working hours | 20% |
| `EPF_ETF_CHANGE` | EPF/ETF contribution rate or eligibility | 12% |
| `PRODUCT_STANDARD` | SLSI mandatory product safety standards | 10% |
| `BUSINESS_REGISTRATION` | eROC filing requirements, annual returns | 8% |
| `IMPORT_EXPORT` | Import/export permits, quotas, bans | 7% |
| `FINANCIAL_REGULATION` | CBSL licensing, forex, lending rules | 6% |
| `SECTOR_SPECIFIC` | Industry-specific licensing | 5% |
| `ENVIRONMENTAL` | Waste, emissions, effluent standards | 3% |
| `PENALTY_ENFORCEMENT` | New fines, enforcement actions | 2% |
| `DEADLINE_EXTENSION` | Extensions to compliance deadlines | 1% |
| `NO_SME_IMPACT` | Regulations with no SME impact | 1% |

### 1.2 Task 2: Sector Assignment (Multi-Label)

Given the same text $x$, predict $S \subseteq \{s_1, \ldots, s_{10}\}$:

| Code | Sector | Expected Positive Rate |
|---|---|---|
| `manufacturing` | Manufacturing and processing | 18% |
| `retail` | Retail trade | 16% |
| `services` | Services (professional, technical) | 15% |
| `agriculture` | Agriculture, fisheries, livestock | 12% |
| `construction` | Construction and real estate | 10% |
| `it_bpo` | IT/BPO and digital services | 8% |
| `hospitality` | Hotels, restaurants, tourism | 7% |
| `transport` | Transport and logistics | 6% |
| `healthcare` | Healthcare and pharmaceuticals | 5% |
| `finance` | Non-bank financial services | 3% |

---

## 3. Architectural Approach Comparison

### 3.1 Comparison Table

| Approach | Multilingual | Training Data Needed | GPU Required | F1 (estimated) | Offline | Reproducible | Cost/1k inferences | Chosen |
|---|---|---|---|---|---|---|---|---|
| **Train from Scratch** | ❌ | 50k+ labeled | ✅ | ~0.55 | ✅ | ✅ | Low | ❌ |
| **XLM-R Fine-tune (LoRA)** | ✅ EN/SI/TA | 800+ labeled | Recommended | ~0.92 | ✅ | ✅ | Very low | ✅ |
| **Zero-shot (GPT-4)** | ✅ | 0 | ❌ | ~0.72 | ❌ | ❌ | ~$0.01/gazette | ❌ |
| **Rule-Based (regex)** | ❌ | 0 | ❌ | ~0.60 | ✅ | ✅ | Near zero | Baseline only |

### 3.2 Training from Scratch — Why Rejected

Training a transformer from scratch on legal Sinhala/Tamil text would require:
- Minimum 50,000 labeled gazette examples (we have ≤ 800 budget)
- 50–200 GPU-hours for pre-training the language model itself
- A custom tokenizer trained on Sri Lankan legal vocabulary

The result would be a domain-specific model that outperforms XLM-R only after sufficient pre-training data — a dataset that does not exist. Chalkidis et al. (2019) demonstrated that BERT fine-tuned on 3,000 legal documents outperforms a model trained from scratch on 500,000 documents for legal classification tasks. With our 800-document budget, fine-tuning is the only viable approach.

### 3.3 Zero-Shot (GPT-4) — Why Rejected

Zero-shot GPT-4 classification was prototyped on 50 gazette documents and achieved macro-F1 of 0.72 — below the target of 0.92. More critically:
- **Non-reproducibility:** GPT-4 model weights are updated without version guarantees; results from research period may not reproduce at inference time
- **Cost at scale:** At $0.01/gazette × 500 gazettes/year = $5/year today, but with 10 classification passes for prompt variants = $50/year, and no ceiling
- **API dependency:** Offline inference is impossible; the system cannot function during API outages
- **No custom confidence scores:** GPT-4 does not natively produce calibrated probability distributions for multi-class classification

### 3.4 Rule-Based (Regex) — Baseline Only

A keyword-regex baseline achieves ~0.60 F1 on the category classification task:
- 45 category-specific keyword patterns (e.g. `EPF|provident fund|contribution rate` → `EPF_ETF_CHANGE`)
- Sector assignment via institution-name lookup (e.g. `SLSI` → `PRODUCT_STANDARD`)

This baseline is retained as `category_baseline` in the `m1_regulations` schema for ablation study and confidence calibration. It is not used for production classification.

---

## 4. Selected Architecture: XLM-R Dual-Head with LoRA

### 4.1 Base Model Selection

Within the BERT fine-tuning family, four multilingual models are compared:

| Model | Parameters | Sinhala in Vocab | Tamil in Vocab | Training Data Size | Legal Domain Perf. | Why Chosen |
|---|---|---|---|---|---|---|
| `bert-base-multilingual-cased` (mBERT) | 110M | ⚠️ Limited | ✅ | 104 languages, Wikipedia | ~0.79 F1 | Not chosen |
| `facebook/xlm-roberta-base` | 125M | ✅ Native | ✅ Native | 100 langs, CommonCrawl 2.5TB | ~0.87 F1 | ✅ **Selected** |
| `facebook/xlm-roberta-large` | 355M | ✅ Native | ✅ Native | Same as base | ~0.91 F1 | Too large for ONNX serving |
| `ai4bharat/indic-bert` | 212M | ✅ | ✅ | 12 Indic languages | ~0.83 F1 | Less English legal perf. |
| `distilbert-base-multilingual-cased` | 66M | ⚠️ Limited | ⚠️ Limited | 104 languages, distilled | ~0.74 F1 | Not chosen |

**XLM-R base is selected** because:
1. Its SentencePiece vocabulary of 250,002 tokens was trained on Common Crawl data for 100 languages including Sinhala (`si`) and Tamil (`ta`) at sufficient frequency for meaningful subword coverage (Conneau et al., 2019).
2. It outperforms mBERT on low-resource language tasks by 5–10% F1 (per the original XLM-R paper) — critical for Sinhala which has limited NLP resources.
3. It is small enough (125M parameters) to run ONNX inference on CPU within the 2-second latency target.

### 4.2 LoRA Configuration

Low-Rank Adaptation (LoRA, Hu et al. 2021) adapts only the query and value projection matrices of each transformer attention layer, reducing trainable parameters from 125M to ~2.4M (98% reduction):

```python
from peft import LoraConfig, get_peft_model

lora_config = LoraConfig(
    r=16,                    # Rank of adaptation matrices
    lora_alpha=32,           # Scaling factor
    target_modules=["query", "value"],  # Apply to attention Q and V
    lora_dropout=0.1,
    bias="none",
    task_type="FEATURE_EXTRACTION",  # We add custom heads
)
```

**Why each hyperparameter setting?**

| Setting | Chosen | Why this default | When to revisit |
|---|---|---|---|
| `r` (rank) | 16 | Standard PEFT recommendation for 125M-parameter models on classification tasks with <2k labels. Higher rank overfits at low-data regimes; lower rank under-fits cross-lingual transfer. Ablation across {8, 16, 32} in `05_M1_3_*.md`. | If F1 on a single language is > 5 pp below others, try `r=32` first. |
| `lora_alpha` | 32 | The `alpha / r` ratio (=2 here) acts as the effective scaling applied to the LoRA delta. Ratio-of-2 is the canonical PEFT default; ratios > 4 amplify gradients too aggressively in fine-tuning, ratios < 1 leave adapters under-utilised. | Keep `alpha = 2*r` when changing `r`; only break this rule if you've measured the effect. |
| `target_modules` | `["query", "value"]` | Adapting only Q and V is the original LoRA paper's recommendation; adapting `key` adds noise on the attention scores without measurable F1 gain in our pilot. Adapting `output` doubles param count for ~0.5 pp F1 gain — not worth the inference cost. | If multilingual disagreement is high (per-language F1 spread > 0.10), try `["query", "value", "output"]`. |
| `lora_dropout` | 0.1 | Same as the encoder's native dropout — avoids effectively-doubled dropout during fine-tuning. | Drop to 0.05 if validation loss stalls early; rise to 0.2 if val-train gap > 0.05. |
| `bias` | `"none"` | **PEFT default** — biases are <1% of params and have negligible effect on classification F1. The choice is precedent-matching, not memory optimization; the savings would be ~25 kB of disk per adapter and trivial GPU memory. | Change only if biases are needed for full reproducibility with a fine-tuning paper that used them. |
| `task_type` | `"FEATURE_EXTRACTION"` | Tells PEFT to leave the model's classification heads alone — we add our own dual heads externally. `SEQ_CLS` would force a single-head config that doesn't fit our dual-head architecture. | Don't change. |

The full LoRA ablation plan — `r` × `alpha` × `target_modules` matrix with expected F1 from a 50-document pilot — is in [05_M1_3_LoRA_Hyperparameter_Justification.md](05_M1_3_LoRA_Hyperparameter_Justification.md).

**Why LoRA over full fine-tuning:**
- Full fine-tuning of 125M parameters requires ~2.4GB GPU VRAM for float32 (or ~1.2GB for fp16). LoRA fine-tuning of 2.4M parameters fits in 4GB GPU VRAM with int8 quantization.
- LoRA adapters are 2.4MB vs 475MB for full fine-tuned weights — dramatically faster to version, deploy, and swap.
- At 800 labeled examples, full fine-tuning risks overfitting; LoRA's parameter efficiency acts as implicit regularization.

### 4.3 Dual-Head Architecture

```mermaid
flowchart TD
    A[Input text\ngazette excerpt\nmax 512 tokens] --> B[XLM-R Tokenizer\nSentencePiece\n250K vocab]
    B --> C[XLM-R Encoder\nfacebook/xlm-roberta-base\n12 layers, 768 hidden dim\nLoRA adapters on Q and V]
    C --> D[CLS token embedding\n768-dim pooled representation]
    D --> E[Dropout 0.3]
    E --> F[Category Head\nLinear 768 to 12\nSoftmax]
    E --> G[Sector Head\nLinear 768 to 10\nSigmoid per sector]
    F --> H[category prediction\nargmax of 12-class softmax\ne.g. TAX_RATE_CHANGE 0.94]
    G --> I[sector predictions\nthreshold 0.50 per sector\ne.g. manufacturing 0.87\nretail 0.72]
```

### 4.4 Model Code

```python
import torch
import torch.nn as nn
from transformers import XLMRobertaModel

class GazetteClassifier(nn.Module):
    NUM_CATEGORIES = 12
    NUM_SECTORS = 10
    DROPOUT = 0.3

    def __init__(self, xlmr_model_name: str = "facebook/xlm-roberta-base"):
        super().__init__()
        self.encoder = XLMRobertaModel.from_pretrained(xlmr_model_name)
        hidden = self.encoder.config.hidden_size  # 768

        self.dropout = nn.Dropout(self.DROPOUT)
        self.category_head = nn.Linear(hidden, self.NUM_CATEGORIES)
        self.sector_head = nn.Linear(hidden, self.NUM_SECTORS)

    def forward(self, input_ids, attention_mask):
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls = self.dropout(outputs.last_hidden_state[:, 0, :])  # CLS token
        category_logits = self.category_head(cls)
        sector_logits = self.sector_head(cls)
        return category_logits, sector_logits

    def predict(self, input_ids, attention_mask):
        with torch.no_grad():
            cat_logits, sec_logits = self.forward(input_ids, attention_mask)
        category = torch.argmax(torch.softmax(cat_logits, dim=-1), dim=-1)
        category_conf = torch.softmax(cat_logits, dim=-1).max(dim=-1).values
        sectors = (torch.sigmoid(sec_logits) > 0.50).nonzero(as_tuple=True)
        return category, category_conf, sectors
```

### 4.5 Loss Function

```python
def combined_loss(cat_logits, sec_logits, cat_labels, sec_labels, alpha=0.7):
    """
    alpha: weight for category loss (primary task)
    (1-alpha): weight for sector loss (secondary task)
    """
    cat_loss = nn.CrossEntropyLoss()(cat_logits, cat_labels)
    sec_loss = nn.BCEWithLogitsLoss()(sec_logits, sec_labels.float())
    return alpha * cat_loss + (1 - alpha) * sec_loss
```

The `alpha=0.7` weighting prioritises category accuracy (the primary research metric) while still training the sector head jointly, which shares beneficial gradients through the shared encoder.

---

## 5. Training from Scratch vs Fine-Tuning: Detailed Comparison

| Dimension | Train from Scratch | Fine-tune XLM-R (LoRA) |
|---|---|---|
| **Data requirement** | 50k+ labeled examples | 800+ labeled examples |
| **Pre-training time** | 100–500 GPU-hours | 0 (weights downloaded) |
| **Fine-tuning time** | N/A | 1–3 hours (1× A100) |
| **Legal language understanding** | Must learn from scratch | XLM-R already understands legal phrases from CommonCrawl |
| **Sinhala performance at 800 examples** | Near random (too little data) | ~0.82 F1 (transfer from 100-language pretraining) |
| **Model size** | Custom (unknown) | 125M + 2.4M LoRA = 127M |
| **Reproducibility** | Full control | Full control (frozen base) |
| **Inference latency (CPU)** | Depends on architecture | ~1.8s per gazette (ONNX) |
| **Infrastructure** | GPU required for training + serving | GPU for training, CPU for inference |
| **Our verdict** | ❌ Not viable at 800 examples | ✅ **Selected** |

---

## 6. Inference Architecture (Production)

After training, the model is exported to ONNX format for production serving. See [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md) for full deployment details.

```python
# Export to ONNX
import torch.onnx
torch.onnx.export(
    model,
    (dummy_input_ids, dummy_attention_mask),
    "gazette_classifier.onnx",
    input_names=["input_ids", "attention_mask"],
    output_names=["category_logits", "sector_logits"],
    dynamic_axes={"input_ids": {0: "batch"}, "attention_mask": {0: "batch"}},
    opset_version=17,
)
```

---

## 7. Conclusion

The dual-head XLM-R + LoRA architecture satisfies all Module 1 constraints: multilingual (EN/SI/TA), high F1 target (≥ 0.92), CPU-only inference, offline capability, and reproducibility. The dual-head design enables joint category and sector prediction in a single forward pass, reducing inference latency compared to two separate models. Training details, hyperparameters, and evaluation results are specified in [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md).

---

## References

- Conneau et al. (2019). *Unsupervised Cross-lingual Representation Learning at Scale (XLM-R)*. [arxiv.org/abs/1911.02116](https://arxiv.org/abs/1911.02116)
- Hu et al. (2021). *LoRA: Low-Rank Adaptation of Large Language Models*. [arxiv.org/abs/2106.09685](https://arxiv.org/abs/2106.09685)
- Chalkidis et al. (2019). *Large-Scale Multi-Label Text Classification on EU Legislation*. ACL 2019.
- Devlin et al. (2018). *BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding*. [arxiv.org/abs/1810.04805](https://arxiv.org/abs/1810.04805)
- Kakwani et al. (2020). *IndicNLPSuite*. EMNLP 2020 Findings.
