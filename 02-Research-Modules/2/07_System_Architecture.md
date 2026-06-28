# Complete System Architecture
## Enigmatrix SME Regulatory Intelligence Platform
## University of Moratuwa 2026

---

## Full System Data Flow

```
+------------------------------------------------------------------+
|                    DATA COLLECTION LAYER                         |
+------------------------------------------------------------------+
|                                                                  |
|  Government Gazette    Social Media APIs    SME Surveys          |
|  (PyMuPDF, Scrapy)     (Facebook, Twitter,  (Google Forms /      |
|                         Reddit APIs)         Next.js Web App)    |
|         |                    |                     |             |
+---------|--------------------|--------------------|-------------+
          |                    |                     |
          v                    v                     v
+------------------------------------------------------------------+
|                    POSTGRESQL DATABASE                           |
+------------------------------------------------------------------+
|                                                                  |
|  regulatory_changes  |  social_media_claims  |  survey_responses|
|  sme_respondents     |  compliance_tests     |  sme_risk_profiles|
|  model_training_runs |  research_modules     |                  |
|                                                                  |
|  All records have: training_status (untrained | trained)        |
+------------------------------------------------------------------+
          |
          v
+------------------------------------------------------------------+
|                    FASTAPI BACKEND                               |
+------------------------------------------------------------------+
|                                                                  |
|  /api/modules/*        -> Data ingestion, validation            |
|  /api/training/*       -> Fetch untrained, mark trained         |
|  /api/analytics/*      -> Progress tracking, metrics            |
|  /api/predict/*        -> Real-time model inference             |
|                                                                  |
+------------------------------------------------------------------+
          |
          v
+------------------------------------------------------------------+
|                    AI / ML LAYER                                 |
+------------------------------------------------------------------+
|                                                                  |
|  Module 1              Module 2              Module 3           |
|  XLM-R Classifier      LangChain RAG         XGBoost +          |
|  (Regulatory type)     (Compliance Q&A)      SHAP               |
|  TF-IDF Baseline       ChromaDB Vectors      SMOTE              |
|                        RAGAS Evaluation      Risk Scores        |
|                                                                  |
|  Module 4                                                        |
|  XLM-R Misinformation                                            |
|  Classifier + RAG                                                |
|  Claim Verifier                                                  |
|                                                                  |
+------------------------------------------------------------------+
          |
          v
+------------------------------------------------------------------+
|                    NEXT.JS FRONTEND                              |
+------------------------------------------------------------------+
|                                                                  |
|  SME Portal             Research Dashboard    Admin Panel        |
|  - Survey forms         - Training status     - User management  |
|  - Compliance chat      - Module analytics    - Data export      |
|  - Risk score view      - Duplicate review    - Model versions   |
|  - Claim verifier       - Data visualizations                   |
|                                                                  |
+------------------------------------------------------------------+
```

---

## Module-Level Architecture

### Module 1 — Gazette Monitoring & Alert System

```
documents.gov.lk
       ↓
Scrapy Spider (scheduled daily)
       ↓
PyMuPDF: Extract text + publication date
       ↓
PostgreSQL: regulatory_changes table
       ↓
XLM-R Classifier: Predict change_type
       ↓
SME Alert Service (FastAPI background task)
       ↓
Notify subscribed SMEs via email/SMS
```

### Module 2 — Compliance Q&A (RAG Pipeline)

```
Official Documents (PDF)
       ↓
PyMuPDF → Text chunks (512 tokens)
       ↓
Sentence Transformer Embeddings
       ↓
ChromaDB Vector Store
       ↓
User Query (via Next.js chat UI)
       ↓
FAISS/Chroma Retrieval: Top-5 chunks
       ↓
LLM: Generate grounded answer
       ↓
RAGAS: Evaluate faithfulness & relevancy
       ↓
Response with citations → Frontend
```

### Module 3 — Compliance Risk Prediction

```
PostgreSQL: survey_responses + public records
       ↓
Pandas: Feature engineering
  (sector, size, location, years, filing history)
       ↓
SMOTE: Balance violation/non-violation classes
       ↓
XGBoost: Train risk classifier
       ↓
SHAP: Calculate feature importance
       ↓
Risk Score API (/api/predict/risk)
       ↓
Dashboard: Risk score + top risk factors for each SME
```

### Module 4 — Misinformation Detection

```
Social Media APIs + Web Scraping
       ↓
Translation (Google Translate API)
       ↓
Deduplication (content_hash)
       ↓
Label Studio: Human annotation (3 annotators)
       ↓
Cohen's Kappa >= 0.7 quality check
       ↓
XLM-R Fine-tuning: accurate/partially/misleading/false
       ↓
Claim Verification Interface (Next.js)
  User pastes any claim
       ↓
RAG checks against verified knowledge base
       ↓
Verdict: Accurate / Misleading / False + Citation
```

---

## Inter-Module Data Flow

```
Module 1 (New Regulation Detected)
       ↓
  → Triggers Module 2: Update RAG knowledge base with new regulation
  → Triggers Module 3: Recalculate risk scores for affected SME sectors
  → Feeds Module 4: New regulatory claims expected on social media
       ↓
Module 2 (Verified Knowledge Base)
       ↓
  → Powers Module 4: Claim verification uses M2 knowledge base
  → Powers Module 3: Ground truth for compliance rule features
       ↓
Module 3 (Risk Scores)
       ↓
  → Feeds Module 1: High-risk SMEs get priority alerts
  → Feeds Module 4: High-risk SMEs get claim verification prompts
       ↓
Module 4 (Verified Claims)
       ↓
  → Feeds Module 2: Verified accurate claims improve knowledge base
```

---

## Deployment Architecture

```
Development:
  Docker Compose
  - Next.js container (port 3000)
  - FastAPI container (port 8000)
  - PostgreSQL container (port 5432)
  - ChromaDB container (port 8001)

Production (suggested):
  - Next.js → Vercel or AWS Amplify
  - FastAPI → AWS EC2 or Google Cloud Run
  - PostgreSQL → AWS RDS or Supabase
  - ML Models → AWS SageMaker endpoints or local GPU server
  - ChromaDB → Self-hosted on same server as FastAPI
```

---

## Environment Setup

```bash
# Backend dependencies
pip install fastapi uvicorn sqlalchemy psycopg2-binary
pip install transformers torch torchvision datasets
pip install langchain chromadb faiss-cpu sentence-transformers
pip install xgboost shap scikit-learn imbalanced-learn
pip install pandas numpy matplotlib seaborn plotly
pip install scrapy beautifulsoup4 pdfplumber pymupdf
pip install spacy ragas label-studio-sdk
pip install sdv faker

# Frontend dependencies
npx create-next-app@latest enigmatrix-frontend --typescript --tailwind
npm install axios react-query recharts @headlessui/react

# Database setup
createdb enigmatrix_db
psql enigmatrix_db -f schema.sql
```

---
*Generated by Perplexity AI for Enigmatrix Research Group - University of Moratuwa 2026*
