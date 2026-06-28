# Research Paper & Module Documentation Structure
## Enigmatrix | SME Regulatory Intelligence Platform | University of Moratuwa 2026

---

## Research Paper Structure

### 1. Introduction
**What to write:**
- Start with the real-world problem (not with AI or technology)
- State what is currently unknown or unmeasured
- Explain why it matters (impact on Sri Lankan SMEs)
- State the main research question clearly
- List the 4 sub-questions (one per module)
- Describe your novel contributions in 1 paragraph
- Provide chapter/section overview

**Example opening sentence:**
> "Despite regulatory compliance being mandatory for Sri Lankan SMEs, no study has measured the information lag between gazette publication and actual SME awareness — leaving businesses exposed to penalties for rules they never knew existed."

---

### 2. Literature Review
**Structure per technology/approach:**

| Section | What to Cover |
|---|---|
| Existing NLP approaches | TF-IDF, BERT, XLM-R papers — cite with limitations |
| RAG systems | Lewis et al. 2020 (RAG paper), LangChain use cases |
| Compliance AI research | Any prior work in legal/regulatory NLP |
| Misinformation detection | Social media fake news classifiers |
| SME research in developing economies | Prior surveys, compliance studies |
| Risk prediction models | Credit risk, churn prediction as analogs |

**How to justify technology selection in literature review:**
1. Cite paper that first used this technology for this type of problem
2. State its reported accuracy/performance
3. State its limitation relevant to your context
4. Explain why your adaptation addresses that limitation

**Example:**
> "Devlin et al. (2019) introduced BERT achieving state-of-the-art results on English NLP tasks; however, its English-only architecture makes it unsuitable for Sri Lankan multilingual content. Conneau et al. (2020) proposed XLM-RoBERTa, trained on 100 languages including Sinhala, making it the appropriate choice for cross-lingual regulatory text classification in this study."

---

### 3. Proposed Solution — Per Module Template

#### Module 1 — Regulatory Change Awareness Gap

**Objective:** Measure the information lag between gazette publication and SME awareness

**Inputs:**
- Government Gazette PDFs (2018–2026)
- Official portal publication dates
- News archive first-mention dates
- SME survey responses (awareness date + channel)

**Outputs:**
- Lag duration dataset (days: gazette → portal → news → SME)
- Channel effectiveness ranking
- Regulatory change type classifier
- Automated gazette monitoring alert system

**Algorithm:**
- PDF parsing: PyMuPDF / pdfplumber for date and content extraction
- Classification: TF-IDF (baseline) → fine-tuned XLM-R (final)
- Statistical: Kruskal-Wallis test for lag differences across SME sectors

**Technologies Used & Justification:**
| Technology | Why Used | Limitation |
|---|---|---|
| PyMuPDF | Fast, accurate PDF text extraction | Cannot handle scanned image PDFs |
| XLM-R | Multilingual transformer, supports Sinhala | Requires GPU for fine-tuning |
| Scrapy | Production-grade web scraper | Rate limiting on government portals |
| PostgreSQL | Structured relational storage for lag timelines | Not optimal for vector search |

---

#### Module 2 — Compliance Knowledge Accuracy Gap

**Objective:** Measure the gap between official compliance requirements and SME understanding

**Inputs:**
- Official IRD/EPF/ETF/eROC documents (verified by CA)
- SME compliance knowledge survey responses (80–120 participants)
- Social media compliance claims

**Outputs:**
- Compliance knowledge gap score (by domain, sector, SME size)
- Informal guidance accuracy rate
- Verified Q&A benchmark dataset
- RAG-based multilingual compliance chatbot

**Algorithm:**
- Knowledge base construction: Document chunking → embedding → FAISS vector store
- RAG pipeline: Query → retrieve top-k chunks → generate grounded answer
- Evaluation: RAGAS faithfulness + answer relevancy scores

**Technologies Used & Justification:**
| Technology | Why Used | Limitation |
|---|---|---|
| LangChain | Modular RAG pipeline construction | Abstraction can hide errors |
| FAISS | Fast vector similarity search | In-memory, needs periodic rebuilding |
| ChromaDB | Persistent vector storage | Less mature than FAISS for large scale |
| spaCy | Fast NLP for claim extraction | Limited Sinhala support |
| RAGAS | Standardized RAG evaluation framework | Requires LLM API calls |

---

#### Module 3 — Compliance Risk Invisibility

**Objective:** Identify which SME characteristics predict compliance failure before it occurs

**Inputs:**
- IRD published defaulter records
- Court judgment records (lawnet.gov.lk)
- Central Bank SME sector statistics
- SME vulnerability survey responses
- Synthetically generated SME profiles (CTGAN)

**Outputs:**
- Compliance risk prediction model
- SHAP feature importance ranking
- Early warning detection window (1/3/6 months)
- Risk score dashboard

**Algorithm:**
- Baseline: Logistic Regression
- Final: XGBoost with SMOTE oversampling for class imbalance
- Explainability: SHAP TreeExplainer
- Optional: LSTM for temporal patterns in violation sequences

**Technologies Used & Justification:**
| Technology | Why Used | Limitation |
|---|---|---|
| XGBoost | Strong tabular performance, handles missing data | Less interpretable than linear models alone |
| SHAP | Model-agnostic explainability | Computationally expensive for large datasets |
| SMOTE | Synthetic oversampling for rare violation class | Can create unrealistic samples |
| SDV/CTGAN | Realistic synthetic data generation | Distribution may not perfectly match real data |
| scikit-learn | Baseline models, preprocessing, evaluation | Not optimized for very large datasets |

---

#### Module 4 — Regulatory Misinformation Spread

**Objective:** Measure misinformation prevalence and spread patterns in Sri Lankan SME networks

**Inputs:**
- Public Facebook group posts with engagement metrics
- Twitter/X tax discussions
- Reddit Sri Lanka finance threads
- FactCheck.lk labeled claims
- Survey-collected WhatsApp forwarded messages

**Outputs:**
- Annotated misinformation corpus (first for Sri Lanka)
- Misinformation prevalence rate per platform
- Virality prediction model
- Real-time claim verification interface

**Algorithm:**
- Annotation: Label Studio with 3-annotator consensus, Cohen's Kappa ≥ 0.7
- Translation: Google Translate API → manual spot-check
- Classification: Fine-tuned XLM-R vs RAG-based claim verification vs GPT API
- Virality: Logistic regression on linguistic features (sentiment, certainty language, urgency)

**Technologies Used & Justification:**
| Technology | Why Used | Limitation |
|---|---|---|
| XLM-R | Cross-lingual (Sinhala + Tamil + English) | Large model size (~1.1GB) |
| Label Studio | Open-source, flexible annotation UI | Self-hosted, needs server setup |
| Google Translate API | Handles Sinhala, Tamil, English | Mistranslations in technical regulatory language |
| Facebook Graph API | Access to public group posts with metadata | Rate limits, restricted access |
| GPT API | Strong baseline for claim verification | Cost per call, not locally deployable |

---

### 4. Methodology Section — Standard Template Per Module

For each module, structure methodology as:

**4.1 Data Collection Procedure**
- What: exact data attributes collected
- Where: source URLs and access methods
- How: tools used (scraper, API, form)
- When: collection period
- Ethics: consent, anonymization, IRB approval

**4.2 Data Preprocessing Steps**
- Step-by-step with justification for each step
- Include cleaning decisions (what was removed and why)

**4.3 Model Development**
- Baseline model → final model progression
- Hyperparameter selection process
- Training environment (CPU/GPU, RAM, time)

**4.4 Evaluation Design**
- Metrics selected and why
- Train/val/test split rationale
- Comparison against prior work

---

### 5. Results & Evaluation

**Structure:**
1. Descriptive statistics of collected dataset (table)
2. Baseline model results
3. Final model results
4. Comparison table: Baseline vs Final vs Prior Work
5. Error analysis: what types of samples the model gets wrong
6. Ablation study: removing each feature and measuring impact

**Required tables:**
```
Table X: Model Performance Comparison
| Model | Accuracy | Precision | Recall | F1 | Notes |
|---|---|---|---|---|---|
| TF-IDF Baseline | 71.2% | 0.69 | 0.68 | 0.68 | Simple, fast |
| Fine-tuned XLM-R | 89.4% | 0.88 | 0.87 | 0.87 | Best overall |
| Prior Work (Author, Year) | 85.0% | 0.83 | 0.82 | 0.82 | English only |
```

---

### 6. Conclusion & Future Work

**Conclusion must answer:**
- Was the research question answered? With what evidence?
- What was measured that was unknown before?
- How does the solution reduce the measured barrier?
- What are the limitations of this study?

**Future Work examples:**
- Extend to other regulatory domains (EPF, ETF beyond IRD)
- Expand to other South Asian SME contexts
- Improve Sinhala NLP with larger training corpus
- Deploy as mobile application for field SME use

---
*Generated by Perplexity AI for Enigmatrix Research Group — University of Moratuwa 2026*
