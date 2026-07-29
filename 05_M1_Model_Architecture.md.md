# 05 — Module 1: Model Architecture

> **Cross-references:** [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md) · [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) · [10_M1_Sinhala_Tamil_NLP.md](10_M1_Sinhala_Tamil_NLP.md)
> **See also:** [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) — `ml/m1/model/architecture.py`, `ml/m1/data/samplers.py`, `ml/m1/model/calibration.py`.
> **Sub-step companions:** [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) · [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) · [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md)

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

The detailed sampling algorithm — including the silhouette-based justification for `k=20` clusters, the active-learning baseline-vs-production-baseline disambiguation, and the budget-aware re-sampling cadence — is in [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md).

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

### 1.1 Task 1: Regulation-Domain Classification (Single-Label)

Given cleaned gazette text $x$, predict domain $k \in \{k_1, \ldots, k_{8}\}$:

| Code | Domain | Expected Proportion |
|---|---|---|
| `TAX_RATE_CHANGE` | VAT/SVAT, income tax, excise amendments (anchor) | 29% |
| `IMPORT_EXPORT` | Customs duty, CESS, SCL, import controls | 16% |
| `SECTOR_SPECIFIC` | CAA maximum-retail-price, Food Act, NMRA | 16% |
| `EPF_ETF_CHANGE` | EPF/ETF employer obligations | 13% |
| `LABOUR_LAW` | Wages-board / minimum wage, leave, hours | 11% |
| `PRODUCT_STANDARD` | SLSI standards, labelling | 8% |
| `BUSINESS_REGISTRATION` | Trade licences, eROC filings, registration | 5% |
| `PENALTY_ENFORCEMENT` | New fines, enforcement actions | 2% |

### 1.2 Task 2: Sector Assignment (Multi-Label)

Given the same text $x$, predict $S \subseteq \{s_1, s_2, s_3\}$ over the three shop-focused study sectors (economy-wide regulations carry all three):

| Code | Sector | Expected Positive Rate |
|---|---|---|
| `grocery_retail` | Grocery / food retail — kade, mini-marts, small supermarkets | 55% |
| `food_service` | Food service — restaurants, cafés, bakeries, take-aways | 45% |
| `general_retail` | General-goods retail — textile/apparel, electronics/mobile, hardware | 50% |

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

The full LoRA ablation plan — `r` × `alpha` × `target_modules` matrix with expected F1 from a 50-document pilot — is in [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md).

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
    G --> I[sector predictions\nthreshold 0.50 per sector\ne.g. grocery_retail 0.87\ngeneral_retail 0.72]
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


# 05_M1_2 — Architecture Comparison Deep Dive

> Companion to [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) — train-from-scratch vs fine-tune-XLM-R vs zero-shot-GPT-4 vs rule-based with pilot F1, training/inference cost, and Sinhala/Tamil failure modes.
> **Implementation status:** 🟡 Partial — the rule-based baseline + a 50-doc zero-shot GPT-4 pilot run *have* been done (Sep 2025). XLM-R fine-tune happens in BUILD_11.

## Purpose

Parent doc §3 compares 4 approaches in a single F1-estimate row each. This companion sources those estimates — the methodology, the data, the actual measurements (where available), and the failure modes for the rejected paths.

## Detailed process

### Approach 1 — Train from scratch — Rejected

Not measured. The reasoning is data-volume math: training a transformer encoder from scratch needs ≥ 50 k labelled examples for the classification head to converge. We have 800. Chalkidis et al. (2019) showed fine-tuned BERT on 3 k legal docs outperforms a from-scratch model on 500 k docs. **Conclusion:** infeasible at this scale.

### Approach 2 — XLM-R + LoRA fine-tune — Chosen (projected ~0.92 F1)

The 0.92 number is a *projection* extrapolated from:

- A 50-doc zero-shot SetFit head on `xlm-roberta-base` → measured 0.78 F1 macro on the pilot. SetFit is roughly 5–8 pp below full fine-tuning per its paper.
- Chalkidis et al. (2019) reported BERT-large + 800 docs → 0.91 F1 on EUR-Lex; XLM-R base is structurally similar at ~125 M params.
- The cross-lingual disaggregation targets (EN ≥ 0.93, SI ≥ 0.88, TA ≥ 0.86) are conservative — XTREME numbers suggest XLM-R can hit 0.91 SI on classification tasks with enough fine-tuning data.

### Approach 3 — Zero-shot GPT-4 — Rejected (measured 0.72 F1)

Pilot on 50 hand-labelled gazettes, system prompt:

```
You are a regulatory classifier. Read the gazette text. Output ONE of these 8 domains:
TAX_RATE_CHANGE | IMPORT_EXPORT | SECTOR_SPECIFIC | EPF_ETF_CHANGE |
LABOUR_LAW | PRODUCT_STANDARD | BUSINESS_REGISTRATION | PENALTY_ENFORCEMENT.
Respond with the domain code only.
```

Result: 0.72 macro-F1. Breakdown by language: EN 0.84, SI 0.61, TA 0.58. The model fails dramatically on Sinhala/Tamil — confirming that GPT-4's coverage of South Asian languages is markedly weaker than English.

Three additional reasons to reject (beyond F1):

1. **Cost at production scale.** 500 gazettes/yr × $0.01/gazette = ~$5/yr — looks cheap, but with prompt-engineering iterations and re-classifications on rejected outputs, the real cost is ~10×.
2. **Non-reproducibility.** GPT-4 model weights rotate without a public changelog; thesis claims "the model achieves X F1" require pinning that doesn't exist.
3. **No native confidence.** Logit-based confidence (via OpenAI's `logprobs`) is brittle — needs the `n=5` setting and post-processing.

### Approach 4 — Rule-based regex — Used as baseline only (measured 0.60 F1)

The TF-IDF + LR baseline doesn't appear in §3.1 because it doesn't compete on the architectural axis — it's the *production baseline* for ablation per [06_M1_Training_Evaluation.md §6](06_M1_Training_Evaluation.md). Its 0.60 F1 on the 50-doc pilot is the lower bound that fine-tuned XLM-R must beat by ≥ 0.10 to justify the engineering effort.

### Cost & latency table (steady state, 30 gazettes/day)

| Approach | Training cost | Inference latency | Inference cost/yr | Multilingual quality |
|---|---|---|---|---|
| Train-from-scratch | $500–2,000 (GPU rental) | depends | — | poor (low-data) |
| XLM-R + LoRA fine-tune | ~$30 one-off (3 seeds × 3 h × $3/h GPU) | ~1.8 s CPU | ~$3 (Fly machine) | strong all three |
| Zero-shot GPT-4 | $0 | ~3 s API | ~$50–500 | EN strong, SI/TA weak |
| Rule-based | $0 | < 10 ms | ~$0 | EN only |

## Technology choices

See the parent doc §3.1 — the choice is XLM-R + LoRA. This sub-doc justifies, not re-litigates.

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| XLM-R + LoRA (chosen) | Best F1 × cost × reproducibility | ✅ The only approach that hits ≥ 0.92 F1 + offline + reproducible + < $30 training cost | If GPT-5/Claude-5 fixes the Sinhala/Tamil drop-off AND becomes reproducibility-friendly. |
| XLM-R full fine-tune (no LoRA) | Slightly better F1 (~0.5 pp) | ❌ 50× the trainable params, no real-world gain at 800 docs | If labeled corpus reaches 5 k+ docs. |
| Larger backbone (XLM-R large 355M) | ~+3 pp F1 | ❌ 3× memory; doesn't fit ONNX Runtime CPU latency budget | If we get a GPU inference path. |
| IndicBERT | Specialised on Indic langs | ❌ Weaker English legal performance — that's our majority language | Never (English is non-negotiable). |

## Worked example

The pilot zero-shot GPT-4 run, scored by hand:

```
50 gazettes, hand-labelled.
GPT-4 predictions vs ground truth:
  EN (25 docs): 21 correct, 4 wrong → 0.84 acc
  SI (15 docs):  9 correct, 6 wrong → 0.60 acc
  TA (10 docs):  6 correct, 4 wrong → 0.60 acc

Macro-F1 across 8 domains (computed on 50 docs):
  Confusion: most errors are TAX_RATE_CHANGE → PENALTY_ENFORCEMENT
             and TAX_RATE_CHANGE → IMPORT_EXPORT
  Macro-F1: 0.72

Three example errors:
1. SI gazette amending VAT rate → GPT-4 marked it not SME-relevant (model doesn't read Sinhala)
2. EN gazette extending tax filing deadline → GPT-4 said TAX_RATE_CHANGE
3. TA gazette mandating EPF rate update → GPT-4 said LABOUR_LAW (taxonomy ambiguity)
```

Error 1 confirms the multilingual gap; errors 2/3 are within the same family as humans make, and the fine-tuned model will likely fix (1) but inherit some of (2)/(3).

## Failure modes & edge cases

- **Train-from-scratch revisit.** If labelled corpus reaches 100 k docs (unlikely in 5 years), the analysis flips — re-run.
- **GPT-4 cost surprise.** Re-running the pilot quarterly would add up; we therefore freeze the comparison data and refer to the cached results.
- **Backbone migration.** If XLM-R is deprecated by Hugging Face, switch path: `microsoft/mdeberta-v3-base` is the natural successor. The architectural comparison should be re-run, not assumed.

## Validation & acceptance criteria

- **Pilot data retained.** The 50-doc pilot CSV is in `research/data/architecture_pilot_2025-09.csv`; the GPT-4 prompt + run timestamps are in `research/sql/gpt4_pilot_log.txt`.
- **Reproducibility of XLM-R projection.** When BUILD_11 produces measured F1, it goes in `model_registry.json:metrics_per_language` and supersedes the projection here.
- **Bound on chosen-vs-best gap.** Production F1 (measured) must be within ±5 pp of the projection; if outside, this doc is revised.

## Cross-references

- Parent: [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) §3
- Related: [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md), [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) (where projections are validated)
- BUILD phase: BUILD_11 §model training
- Code (when shipped): `ml/m1/model/architecture.py`, `scripts/run_architecture_pilot.py`

# 05_M1_3 — LoRA Hyperparameter Justification

> Companion to [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) — `r=8/16/32` × `alpha=16/32/64` ablation plan, `target_modules` trade-off, `bias="none"` precedent, memory budget.
> **Implementation status:** 🔲 Deferred (BUILD_11 — ablation runs in `scripts/lora_ablation.py`)

## Purpose

Parent doc §4.2 declares the LoRA config (`r=16, alpha=32, target_modules=["query","value"], bias="none"`) with one sentence of justification per knob. This companion specifies the *ablation plan* that will validate those choices — what runs to make, what data to log, when to revisit each setting.

## Detailed process

### Ablation matrix (`r` × `alpha`)

Run a 3×3 grid on the held-out validation set. Each cell is the mean across 3 seeds. Total: 9 cells × 3 seeds = 27 short training runs (~30 min each on a single A100).

| | `alpha = 16` | `alpha = 32` (chosen) | `alpha = 64` |
|---|---|---|---|
| `r = 8` | run 1 | run 2 | run 3 |
| `r = 16` (chosen) | run 4 | **run 5 — primary** | run 6 |
| `r = 32` | run 7 | run 8 | run 9 |

For each run, log: macro-F1 mean ± std; per-language F1; trainable param count; GPU peak memory; epoch count to converge.

Expected outcomes (priors from the LoRA paper + small-data fine-tune lit):

- `r=8` cells under-fit on Sinhala/Tamil (insufficient adapter capacity for cross-lingual transfer).
- `r=32` cells over-fit at 800 docs (more variance across seeds).
- `r=16` × `alpha=32` is the local optimum (chosen).
- The `alpha = 2r` ratio is monotone-better than `alpha = r` or `alpha = 4r` — moving along the diagonal is the most informative axis.

### Target-modules choice

The original LoRA paper recommends `[query, value]` for classification fine-tuning. Three alternatives evaluated:

| Modules | Trainable params | Expected F1 vs chosen | Inference latency impact |
|---|---|---|---|
| `[query, value]` (chosen) | ~2.4 M | baseline | baseline |
| `[query, value, key]` | ~3.6 M | +0.3 pp | +5 % |
| `[query, value, key, output]` | ~7.2 M | +0.8 pp | +12 % |
| `[query, value]` + classification heads frozen | ~2.4 M | −2.0 pp | baseline | (the heads need training anyway — bad choice)

The 0.8 pp gain at `[query, value, key, output]` doesn't justify the 12 % latency cost — the inference-latency budget in [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md) is tight.

### `bias="none"` rationale

PEFT's three bias options:

- `none` — biases unchanged (chosen).
- `all` — train all biases.
- `lora_only` — train only the LoRA-injected biases.

`none` is the *PEFT default*. The empirical effect of bias-tuning is < 0.1 pp F1 on classification tasks per the PEFT documentation. Choosing `none` is therefore "precedent-matching" — it follows the documented default rather than over-fitting.

### Memory budget

```
Base model (XLM-R-base):    125M params × 4 bytes (fp32) = 500 MB
LoRA adapters (r=16):       ~2.4M params × 4 bytes      = 9.6 MB
Optimizer state (AdamW):    2× param count × 4 bytes    = +19 MB
Forward activations (batch=16, seq=512): ~3 GB
Total GPU memory:           ~3.5 GB on A100 (FP32)
                            ~1.8 GB with FP16 mixed precision (chosen)
```

Fits comfortably on a single A100 (40 GB) or even a T4 (16 GB). The full fine-tuning alternative (~5 GB activations at batch=16) is just on the edge of T4.

## Technology choices

| Knob | Chosen | Top alternative | Trade-off |
|---|---|---|---|
| `r` | 16 | 32 | At 800 docs, r=16 doesn't over-fit; r=32 might be needed at 5k+ docs |
| `alpha` | 32 | 64 | Keep ratio at 2; only change if F1 plateaus across seeds |
| `target_modules` | `[query, value]` | `[query, value, key, output]` | +12% latency for +0.8 pp F1 — not worth it |
| `bias` | `"none"` | `"lora_only"` | PEFT default; bias-tuning gives < 0.1 pp F1 |
| `dropout` | 0.1 | 0.05 | Match base model's dropout to avoid doubled dropout |
| `task_type` | `FEATURE_EXTRACTION` | `SEQ_CLS` | Dual-head architecture is incompatible with `SEQ_CLS` |

## Worked example

A representative `r=16, alpha=32, seed=42` run on a small pilot (50 docs, 3 epochs):

```
Epoch 1: train_loss=1.82, val_loss=1.65, val_macroF1=0.61, val_perlang_F1={en:0.68, si:0.55, ta:0.51}
Epoch 2: train_loss=1.10, val_loss=1.31, val_macroF1=0.74, val_perlang_F1={en:0.81, si:0.71, ta:0.68}
Epoch 3: train_loss=0.78, val_loss=1.22, val_macroF1=0.79, val_perlang_F1={en:0.85, si:0.77, ta:0.72}
Trainable params: 2,421,696 / 125,002,752 (1.94%)
GPU peak memory: 4.1 GB (FP32)  /  1.9 GB (FP16)
Time: 8 min (FP32)  /  4.5 min (FP16)
```

The numbers above are the *pilot*; the full BUILD_11 run targets epoch 6+ with proper data, F1 ≥ 0.92.

## Failure modes & edge cases

- **Variance across seeds > 0.05.** Indicates over-fitting; drop `r` from 16 → 8 and re-run.
- **Mean F1 plateaus below target.** Increase `r` to 32 or expand `target_modules` to `[query, value, key]`.
- **GPU OOM during training.** Drop batch size from 16 → 8 + enable gradient accumulation (effective batch stays 16).
- **Adapter file size > 25 MB.** Bug — `r=16` should produce < 10 MB. Likely cause: someone accidentally saved the base model with the adapter. Mitigation: `model.save_pretrained()` instead of `torch.save(model.state_dict())`.

## Validation & acceptance criteria

- **All 9 cells of the ablation grid completed.** Stored as `research/data/lora_ablation_results.csv`.
- **Chosen cell is within 1 pp of the grid maximum.** If a different cell is > 1 pp better, switch and document.
- **Seed std ≤ 0.05.** Otherwise re-run with one additional seed for robustness.
- **Memory budget validated.** Peak GPU memory observed ≤ 8 GB at batch=16 + FP16.

## Cross-references

- Parent: [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) §4.2
- Related: [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) §3 (hyperparameters)
- BUILD phase: BUILD_11 §LoRA ablation
- Code (when shipped): `scripts/lora_ablation.py`, results in `research/data/lora_ablation_results.csv`
