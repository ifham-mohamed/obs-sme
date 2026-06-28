# Literature Review Guide
## How to Identify, Justify, and Compare Research Technologies
## Enigmatrix | SME Regulatory Intelligence Platform | University of Moratuwa 2026

---

## Purpose of a Literature Review in AI Research

The literature review is NOT a list of summaries. It serves three specific functions:
1. **Prove the research gap exists** — nobody has done exactly this before
2. **Justify your technology choices** — cite papers that prove your tech works for similar problems
3. **Benchmark your expected results** — what accuracy did prior work achieve so you can compare

---

## How to Read a Research Paper for Literature Review

When reading any paper, extract these 6 elements:
1. **Problem** — What problem did they solve?
2. **Dataset** — What data did they use? How large? What language?
3. **Method** — What algorithm/model did they use?
4. **Results** — What accuracy/F1/AUC did they achieve?
5. **Limitation** — What did they NOT do or what failed?
6. **Relevance to your work** — How does this inform your module?

---

## Key Papers Per Module

### Module 1 — Regulatory Change Detection & NLP Classification

| Paper | Key Method | Result | Limitation | Your Relevance |
|---|---|---|---|---|
| Bommarito & Katz (2018) — Legal NLP survey | BERT variants for legal text | State-of-the-art on English legal NLP | English only | Confirms transformer approach; XLM-R needed for Sinhala |
| Conneau et al. (2020) — XLM-R | Multilingual transformer | SOTA on 100 languages | Large model size | Direct justification for choosing XLM-R |
| Loshchilov & Hutter (2019) — AdamW | Optimizer for transformers | Better fine-tuning than Adam | Hyperparameter sensitive | Justifies AdamW in training config |

**How to cite for technology justification:**
> "Bommarito & Katz (2018) demonstrated BERT-based models achieve superior performance on legal text classification compared to traditional TF-IDF approaches; however, their work was confined to English legal corpora. Given that Sri Lankan regulatory documents appear in both Sinhala and English, we adopt XLM-RoBERTa (Conneau et al., 2020), which extends multilingual transformer pretraining to 100 languages including Sinhala, as the foundation for our regulatory change classifier."

---

### Module 2 — RAG Systems for Compliance Q&A

| Paper | Key Method | Result | Limitation | Your Relevance |
|---|---|---|---|---|
| Lewis et al. (2020) — RAG | Retrieval-Augmented Generation | Strong open-domain QA | English only | Foundational RAG architecture citation |
| Es et al. (2023) — RAGAS | RAG evaluation framework | Standardized RAG metrics | LLM-dependent evaluation | Justifies RAGAS for your evaluation |
| Gao et al. (2023) — Survey of RAG | RAG variants (naive, advanced, modular) | Comparison of approaches | Limited multilingual coverage | Helps justify modular RAG choice |

**Gap statement for Module 2:**
> "While Lewis et al. (2020) established RAG as an effective architecture for knowledge-grounded Q&A, no prior work applies RAG specifically to Sri Lankan regulatory compliance guidance or evaluates accuracy of informal guidance channels against official regulatory sources — both of which this module investigates."

---

### Module 3 — ML Risk Prediction

| Paper | Key Method | Result | Limitation | Your Relevance |
|---|---|---|---|---|
| Chen & Guestrin (2016) — XGBoost | Gradient boosting trees | Wins most Kaggle tabular competitions | Not for sequential text | Justifies XGBoost for tabular SME features |
| Lundberg & Lee (2017) — SHAP | Shapley value explanations | Model-agnostic interpretability | Slow on large datasets | Justifies SHAP for feature importance |
| Chawla et al. (2002) — SMOTE | Synthetic minority oversampling | Improves rare class recall | Can create noise | Justifies SMOTE for imbalanced violations |
| Altman (1968) — Z-Score Model | Logistic regression for bankruptcy | Early financial distress predictor | Finance-specific, dated | Baseline analog for SME compliance risk |

**Gap statement for Module 3:**
> "Existing compliance risk prediction models (Altman, 1968; Campbell et al., 2008) focus on financial distress in large enterprises using proprietary accounting data. No model exists that predicts regulatory compliance failure for small businesses in developing economies using only publicly available signals — which this module addresses using XGBoost, SMOTE, and SHAP on Sri Lankan public records."

---

### Module 4 — Misinformation Detection

| Paper | Key Method | Result | Limitation | Your Relevance |
|---|---|---|---|---|
| Zhou et al. (2020) — FakeNews survey | Survey of fake news detection methods | BERT models dominate | English-focused | Establishes transformer approach |
| Conneau et al. (2020) — XLM-R | Multilingual pretraining | SOTA cross-lingual | Large model | Justifies XLM-R for Sinhala/Tamil content |
| Vosoughi et al. (2018) — Spread of false news | Twitter virality analysis | False news spreads 6x faster | Twitter-only | Grounds your virality prediction hypothesis |
| Thorne et al. (2018) — FEVER dataset | Fact verification benchmark | Standardized claim verification | Wikipedia-based only | Annotation methodology analog |
| Cohen (1960) — Cohen's Kappa | Inter-annotator agreement | Statistical agreement measure | Not for continuous labels | Justifies Kappa ≥ 0.7 as quality threshold |

**Gap statement for Module 4:**
> "Vosoughi et al. (2018) demonstrated false information spreads significantly faster than accurate content on Twitter; however, their analysis is limited to English content on a single platform. No study has examined misinformation spread in South Asian SME networks across multilingual platforms (Sinhala, Tamil, English), nor constructed a verified tax regulation misinformation corpus for this context."

---

## How to Write Technology Justification in Literature Review

### Template Structure

```
[Technology X] was introduced by [Author, Year] to address [original problem].
In the context of [your domain], [Technology X] is appropriate because [specific reason].
[Alternative Technology Y], while used by [Author, Year] for similar tasks,
is unsuitable for this study because [specific limitation in your context].
```

### Example: Justifying PostgreSQL over MongoDB
> "Relational databases such as PostgreSQL have been widely used in research data management systems requiring structured query capabilities and referential integrity (Date, 2003). For this study, PostgreSQL is selected over document-oriented alternatives such as MongoDB because the research data has clearly defined relational structures — survey respondents link to responses, which link to training runs — and referential integrity is critical to prevent orphaned training records. PostgreSQL's JSONB column type additionally allows storage of flexible SHAP feature importance vectors without sacrificing relational structure."

---

## Where to Find Research Papers

| Source | URL | Best For |
|---|---|---|
| Google Scholar | scholar.google.com | General search, citation counts |
| Semantic Scholar | semanticscholar.org | AI/CS papers, free PDFs |
| ACL Anthology | aclanthology.org | NLP papers (all free) |
| arXiv | arxiv.org | Preprints, latest models |
| IEEE Xplore | ieeexplore.ieee.org | Engineering/systems papers |
| ACM Digital Library | dl.acm.org | Computing research |
| PubMed | pubmed.ncbi.nlm.nih.gov | Health/social science |

### Search Terms for Your Modules

| Module | Search Terms |
|---|---|
| M1 | "regulatory text classification NLP", "legal document change detection", "multilingual NLP compliance" |
| M2 | "retrieval augmented generation legal QA", "compliance knowledge gap survey", "RAG evaluation RAGAS" |
| M3 | "SME compliance risk prediction", "tax default prediction machine learning", "SHAP feature importance financial risk" |
| M4 | "tax misinformation detection social media", "multilingual fake news classification", "cross-lingual misinformation NLP" |

---

## Literature Review Comparison Table Format

Use this in your paper for each module:

```
Table X: Comparison of Existing Approaches for [Module Task]

| Study | Method | Dataset | Language | Accuracy | Limitation |
|---|---|---|---|---|---|
| Author et al. (Year) | BERT | English legal | EN | 88% | English only |
| Author et al. (Year) | mBERT | Multi-domain | EN+FR | 82% | No Sinhala |
| This Study | XLM-R fine-tuned | Sri Lankan gazette | EN+SI | TBD | Domain-specific |
```

---
*Generated by Perplexity AI for Enigmatrix Research Group - University of Moratuwa 2026*
