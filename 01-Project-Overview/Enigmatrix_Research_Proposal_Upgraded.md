# RESEARCH PROJECT PROPOSAL
# RESEARCH PROJECT PROPOSAL
## Understanding Information Barriers to Regulatory Compliance Among Sri Lankan SMEs: A Data-Driven Investigation

**Group:** Enigmatrix | Faculty of Information Technology | University of Moratuwa
**Level 04 Final Year Research Project | 2026**

---

## 1. The One Core Problem

**In One Sentence:**
> Sri Lankan SMEs want to comply — but they do not have access to the right information, at the right time, in the right language.

This is the single real-world problem driving the entire research project. Everything else flows from this one human truth:

| Information Failure | What It Means |
|---------------------|---------------|
| **Right TIME** | SMEs find out about regulatory changes weeks or months after they happen |
| **Right INFORMATION** | The guidance SMEs receive — from accountants, forums, social media — is often incorrect |
| **Right LANGUAGE** | Official documents are in English, but most SME owners operate in Sinhala or Tamil |
| **Right AWARENESS** | SMEs do not know they are heading toward non-compliance until a penalty arrives |

---

## 2. Why This Is a Research Project — Not Just a System Build

A system build asks: *"How do we build X?"*
A research project asks: *"We do not know if X is true, or how bad it is — let us find out."*

| System Build (What we had before) | Research Project (What we have now) |
|-----------------------------------|--------------------------------------|
| Built because it seemed useful | Built because research proves it is needed |
| Features decided by assumption | Features decided by measured findings |
| No validation of impact | Validated against real measured barriers |
| No novel contribution | 4 novel datasets + 4 measurable findings |
| AI is the subject | AI is the tool — the real world is the subject |

---

## 3. The Overarching Research Question

**Main Research Question:**
> What are the information barriers that drive regulatory non-compliance among Sri Lankan SMEs — and how can they be systematically identified and addressed?

This question is:
- **Genuinely unanswered** — nobody has studied or measured this for Sri Lanka
- **About the real world** — not about how well AI works
- **Requires all 4 modules** to fully answer
- **Generalizable** — findings apply to any developing economy with similar regulatory fragmentation

---

## 4. The Four Research Modules

Each module investigates one specific information barrier. Together they form a complete picture of why Sri Lankan SMEs fail at compliance.

### Module 1 — Regulatory Change Awareness Gap

**Research Question:**
> Are regulatory changes reaching Sri Lankan SMEs in time to act — and what is the information lag between gazette publication and SME awareness?

#### The Real-World Problem
When a new regulation is published in the Government Gazette, how long does it take before an average SME owner knows about it? Days? Weeks? Months? Nobody has ever measured this for Sri Lanka. SMEs are getting penalized for missing deadlines they never even knew existed.

#### What You Investigate
- Measure the exact lag at every stage: `Gazette → Official Portal → News → SME Awareness`
- Identify which communication channels deliver regulatory information fastest
- Determine which types of regulatory changes have the longest awareness gap
- Find whether lag differs by SME sector, size, or location

#### Data Sources

| Data Source                     | What You Collect                                              | How You Get It                           |
| ------------------------------- | ------------------------------------------------------------- | ---------------------------------------- |
| Government Gazette Archive      | Publication dates of all regulatory changes 2018–2026         | www.documents.gov.lk — all public PDFs   |
| IRD / EPF / ETF / eROC websites | Secondary publication dates on official portals               | Web scraping + manual archive            |
| News Archives                   | First news coverage date of each regulatory change            | Daily FT, LBO, Daily Mirror — searchable |
| SME Owner Survey                | When SMEs actually became aware + which channel informed them | Own Next js web application              |

#### The Full Module 1 Pipeline (7 Stages)

```
STAGE A — INGESTION (scheduled, every 6 hours)
  documents.gov.lk → list new gazettes → download PDFs → store raw

STAGE B — EXTRACTION (per gazette)
  PDF → text → section segmentation → notice/rule extraction → cleaned text

STAGE C — CLASSIFICATION (per extracted notice)
  text → XLM-R classifier → category + confidence → metadata extraction

STAGE D — SECONDARY-SOURCE TRACKING (per regulation, ongoing)
  Watch IRD/EPF/ETF/eROC sites + news + social → record first-appearance timestamps

STAGE E — SUMMARIZATION & TRANSLATION
  Generate plain-language summary in EN/SI/TA

STAGE F — ALERTING
  Match regulation → relevant SMEs → notify (email / dashboard / SMS)

STAGE G — LAG MEASUREMENT (research output)
  Combine pipeline timestamps + SME survey awareness data
  → compute lag distribution per stage, per category, per SME profile
```

#### PDF Extraction Sub-Pipeline (7 Stages)

```
1. DISCOVER   → find new gazette URLs not yet seen (Scrapy spider on documents.gov.lk)
2. DOWNLOAD   → fetch PDF (rate-limited, retries via tenacity, content-addressable storage)
3. INSPECT    → classify as text-based / scanned / hybrid (PyMuPDF avg chars/page test)
4. EXTRACT    → text via PyMuPDF, tables via pdfplumber, OCR via Tesseract (eng+sin+tam)
5. SEGMENT    → split full gazette into individual notices using heading detection + rules
6. CLEAN      → normalize Unicode (NFC), collapse whitespace, strip artifacts, detect language (fastText lid.176)
7. STORE      → write to PostgreSQL regulations table + filesystem /raw/gazettes/
```

**Key extraction code patterns:**

```python
# Inspect: text vs scanned
import fitz
def classify_pdf(path):
    doc = fitz.open(path)
    avg_chars = sum(len(p.get_text("text")) for p in doc) / len(doc)
    if avg_chars > 200: return {"type": "text_pdf", "method": "pymupdf"}
    elif avg_chars > 30: return {"type": "hybrid", "method": "pymupdf+ocr"}
    else: return {"type": "scanned", "method": "ocr"}

# Clean
import unicodedata, re
def clean_text(text):
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

# Language detection
import fasttext
LID = fasttext.load_model("/data/models/lid.176.bin")
def detect_language(text):
    labels, probs = LID.predict(text[:1000].replace("\n"," "), k=1)
    return labels[0].replace("__label__",""), float(probs[0])
```

#### NLP Classifier Training Pipeline (9 Stages)

The **12-Way Regulatory Change Taxonomy:**

| # | Category | Example Trigger |
|---|----------|----------------|
| 1 | TAX_INCOME | Income tax rate or threshold change |
| 2 | TAX_VAT_SVAT | VAT rate revised to 18% |
| 3 | TAX_CUSTOMS_TARIFF | Import duty schedule amended |
| 4 | EPF_ETF | Contribution rate / procedure change |
| 5 | IMPORT_EXPORT_CONTROL | Export restriction announced |
| 6 | HEALTH_SAFETY | Food safety regulation |
| 7 | ENVIRONMENTAL | Environmental compliance requirement |
| 8 | EMPLOYMENT_LABOUR | Labour law amendment |
| 9 | COMPANY_REGISTRATION | eROC form change, Form 6 |
| 10 | SECTOR_SPECIFIC | Regulation targeting one sector |
| 11 | CONSUMER_PROTECTION | Consumer rights notice |
| 12 | OTHER_REGULATORY | Fits none of the above |

**Training Pipeline:**
1. **Sampling** — stratified random by year+language + k-means cluster diversity (k=20) + active learning on low-confidence examples
2. **Labeling** — Label Studio with 4–6 page Annotation Guidelines; minimum 800 labeled (aim 1500–2000); ≥ 40 per class
3. **Splitting** — temporal split: Train 2018–mid-2024 / Val mid-2024–end-2024 / Test 2025–2026 (never random — prevents future-leakage)
4. **Baselines** — TF-IDF + Logistic Regression; GPT-4 zero-shot; keyword rule set
5. **Fine-tuning** — XLM-RoBERTa-base (270M params, supports Sinhala + Tamil + English)
6. **Evaluation** — macro-F1 ≥ 0.80; per-class F1; per-language slice (EN/SI/TA)
7. **Error Analysis** — confusion matrix; 50+ hard-example review; qualitative failure taxonomy
8. **Versioning** — `model_versions` table with run_id, git commit hash, seed, hyperparams
9. **Serving** — FastAPI `POST /classify` endpoint; batch backfill for all existing regulations

**Inter-annotator agreement:**
```python
from sklearn.metrics import cohen_kappa_score
kappa = cohen_kappa_score(annotator_a, annotator_b)
# Target: kappa >= 0.70 (substantial agreement)
```

**Lag computation definitions:**
```
lag_to_portal    = first_seen_at(channel='ird'|'epf'|…) − gazette_publication_date
lag_to_news      = first_seen_at(channel='news_*')       − gazette_publication_date
lag_to_social    = first_seen_at(channel='social_*')     − gazette_publication_date
lag_to_sme_aware = sme_reported_aware_date               − gazette_publication_date
```

**Secondary-source matching strategy (two-step):**
1. Exact gazette number or Act/Section reference → direct lookup
2. Sentence-transformer embedding cosine similarity > 0.78 → auto-match; 0.6–0.78 → human review queue

#### Novel Contributions
- First ever measured information lag dataset for Sri Lankan regulatory changes
- First ranked map of regulatory communication channel effectiveness in Sri Lanka
- First NLP classifier (multilingual EN/SI/TA) for Sri Lankan regulatory change categorization

#### Success Criteria
| Criterion                                               | Target                                               |
| ------------------------------------------------------- | ---------------------------------------------------- |
| Classifier macro-F1 (test set)                          | ≥ 0.80                                               |
| Information lag dataset                                 | ≥ 200 regulations × 4 stages = 800+ timestamp points |
| SME survey responses                                    | ≥ 100 valid responses                                |
| Statistically significant lag differences across stages | p < 0.05                                             |
| Alert delivery within 24h of gazette publication        | Yes (median)                                         |
| Lag reduction vs baseline                               | ≥ 50%                                                |

#### The Solution Built
An automated gazette monitoring and SME alert system — validated by proving it delivers regulatory information significantly faster than the current average awareness times measured in the research.

---

### Module 2 — Compliance Knowledge Accuracy Gap

**Research Question:**
> How accurate is the compliance guidance Sri Lankan SMEs receive — and what is the gap between official regulatory requirements and what SMEs actually understand?

#### The Real-World Problem
When an SME files a VAT return, how correct is their understanding of what they need to do? When they ask their accountant or look at a Facebook group, how often is the answer wrong? Nobody has measured the accuracy of compliance guidance reaching Sri Lankan SMEs — or quantified how much misunderstanding exists.

#### What You Investigate
- Build a verified ground truth of all Sri Lankan compliance requirements across key regulatory domains
- Test SME owners and finance staff with specific compliance knowledge questions
- Calculate a **Compliance Knowledge Gap Score** — how far is SME understanding from official requirements?
- Measure accuracy of informal guidance (social media, forums, accountants) vs official sources

#### Data Sources

| Data Source | What You Collect | How You Get It                                                                        |
| -------------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| IRD / EPF / ETF / eROC documents | All official compliance rules — exact rates, deadlines, formats | Public PDFs — verified by CA / tax professional                                       |
| Compliance Knowledge Survey | SME responses to 30–40 specific verifiable compliance questions | own next j application for the data management  — 80–150 SME owners and finance staff |
| Social Media and Forums | Compliance claims made in public groups | Facebook group scraping, Reddit Sri Lanka, forums                                     |
| FactCheck.lk | Pre-labeled misinformation claims about regulations | Public website scraping                                                               |

#### Compliance Knowledge Test — Question Categories (30–40 questions)

| Domain | Questions | Example |
|--------|-----------|---------|
| VAT registration thresholds and rates | 5 | "What is the current VAT registration threshold?" |
| VAT filing deadlines and procedures | 5 | "When must a monthly VAT return be filed?" |
| EPF / ETF rates and contributions | 5 | "What is the employer EPF contribution rate?" |
| PAYE income tax basics | 4 | "What is the personal income tax relief threshold?" |
| WHT (withholding tax) rules | 3 | "At what rate is WHT applied to professional fees?" |
| Company registration / Form 6 | 3 | "When must an Annual Return be filed?" |
| Annual return obligations | 3 | — |
| Recent changes (last 12 months) | 5 | — |
| General compliance practices | 4 | — |

**Question design:** Always include *"Not sure / I do not know"* as an option — measuring non-knowledge is as important as measuring wrong knowledge.

#### Procedures and Technologies
- Construct structured Q&A ground truth knowledge base from official documents — verified by a CA/tax professional
- Design and distribute 30–40 question compliance knowledge test to SME owners
- Score responses against ground truth — calculate domain-specific accuracy rates
- Extract compliance claims from social media using spaCy NLP
- Verify each claim against ground truth — calculate informal guidance accuracy rate
- Build RAG system on verified knowledge base — evaluate using RAGAS faithfulness framework (target: faithfulness ≥ 0.85; answer accuracy vs expert ≥ 0.80)

**RAG Architecture:**
```
Official Documents (IRD/EPF/ETF/eROC PDFs)
         ↓ PDF parsing (PyMuPDF + pdfplumber)
         ↓ Chunking + embedding (LaBSE / sentence-transformers)
         ↓ Storage in ChromaDB (collection: mod2_compliance_kb)
         ↓ Retrieval (cosine similarity top-k)
         ↓ Generation (local LLM / Claude / GPT-4 with strict system prompt)
         ↓ Evaluation (RAGAS: faithfulness, answer_relevance, context_precision)
```

#### Novel Contributions
- First measured compliance knowledge gap score for Sri Lankan SMEs
- First accuracy measurement of informal guidance channels in Sri Lankan regulatory context
- First Sri Lankan compliance Q&A benchmark dataset — verified against official sources

#### The Solution Built
A RAG-based multilingual compliance guidance system grounded strictly in verified official documents — validated by showing it produces more accurate answers than informal channels measured in the research.

---

### Module 3 — Compliance Risk Invisibility

**Research Question:**
> Which characteristics of Sri Lankan SMEs predict compliance failure — and can these signals be detected before a violation occurs?

#### The Real World Problem
SMEs do not know they are heading toward non-compliance until a penalty notice arrives. There is no early warning system. No one has studied which types of SMEs are most at risk or what behavioral patterns appear before a violation occurs. The risk is completely invisible until it is too late.

#### What You Investigate
- Which SME characteristics — sector, size, age, location — most strongly predict compliance failure?
- What behavioral patterns appear in the period before a compliance violation?
- Can risk be detected 1 month, 3 months, or 6 months before a violation occurs?
- Which ML approach generalizes best when labeled data is scarce?

#### Data Sources

| Data Source | What You Collect | How You Get It                                 |
| ----------------------------- | ---------------------------------------------------------- | ---------------------------------------------- |
| IRD Published Defaulter Lists | Records of actual tax violations with business type | IRD website — publicly published               |
| Court Judgment Records | SME tax dispute cases with outcomes and timelines | www.lawnet.gov.lk — all public judgments       |
| Central Bank Annual Reports | Sector-level SME financial health indicators over time | CBSL website — all public reports              |
| SME Vulnerability Survey | Self-reported compliance failures with SME characteristics | own next j application for the data management |
| Synthetic Dataset | Realistic SME profiles calibrated to population statistics | SDV / CTGAN synthetic generation               |

#### Vulnerability Survey — Key Sections

**Section A — Compliance history (8 questions)**
- Q-V1: Penalty types received in last 24 months (multi-select)
- Q-V2: Number of penalty events (0 / 1 / 2 / 3+)
- Q-V3: Approximate financial impact (banded: < 50k / 50k–250k / 250k–1M / > 1M LKR)
- Q-V4: Most recent penalty type
- Q-V5: Perceived cause (didn't know / missed deadline / wrong calculation / system error / other)
- Q-V6: VAT filing frequency
- Q-V7: History of late filing
- Q-V8: Missed known deadline in last 12 months

**Section B — Behavioral / capacity factors (8 questions)**
- Frequency of checking IRD website
- Frequency of consulting accountant on compliance
- Digital records maintenance and accounting software usage
- Compliance time burden (% of monthly time)
- Language comprehension of official documents

**Section C — Forward-looking (4 questions)**
- Concern about upcoming changes (1–5 scale)
- Compliance burden reduction priorities
- Willingness to use real-time alert system

**Outcome label construction:**
```python
# Target variable for risk model
compliance_failure = 1  if  (any penalty event in last 24 months)
                         OR  (missed known deadline in last 12 months)
                    else 0
```

#### Procedures and Technologies
- Combine real violation records, survey data, and synthetic data into unified labeled dataset
- Handle class imbalance using SMOTE oversampling
- Exploratory analysis: visualize compliance failure rates by sector, size, age, region
- Train and compare: Logistic Regression (baseline) → Random Forest → XGBoost → LSTM
- SHAP analysis — identify which features most strongly predict non-compliance
- Temporal analysis — measure how early before violation risk signals become detectable (1 / 3 / 6 month horizons)

**Synthetic data note:** All synthetic profiles must be clearly labeled as synthetic in every figure and table. Report performance separately on real-only vs combined data. Use SDV / CTGAN calibrated against CBSL population statistics.

**Success metrics:**
- ROC-AUC ≥ 0.75
- Precision @ top 10% ≥ 0.60

#### Novel Contributions
- First SME compliance risk prediction model for a developing economy using only public data
- First feature importance study identifying predictors of SME non-compliance in Sri Lanka
- Generalizable methodology for compliance risk prediction in any data-scarce regulatory environment

#### The Solution Built
An SME compliance risk early warning system with SHAP-explainable risk scores — validated by retrospective testing against known historical violations.

---

### Module 4 — Regulatory Misinformation Spread

**Research Question:**
> How significantly does tax regulation misinformation spread through Sri Lankan SME networks — and what makes certain misinformation more viral than accurate official guidance?

#### The Real World Problem
When an SME owner cannot find clear guidance from official sources, they turn to WhatsApp groups, Facebook, and online forums. Wrong information about tax regulations spreads rapidly through these channels. No one has measured how prevalent this misinformation is, how fast it spreads, or what makes it more believable than accurate information.

#### What You Investigate
- What percentage of tax regulation content on Sri Lankan social media is inaccurate?
- Which regulatory topics generate the most misinformation?
- Does misinformation spread faster and further than accurate content?
- What linguistic features make misinformation more viral than correct information?
- Does misinformation spike when new regulations are announced — correlating with Module 1 lag findings?

#### Data Sources

| Data Source | What You Collect | How You Get It |
|-------------|-----------------|----------------|
| Public Facebook Groups | Posts making compliance claims with engagement metrics | Facebook Graph API + manual collection from public groups |
| Twitter / X | Tax regulation discussions with retweet / reply data | Twitter Academic API with Sinhala / English keywords |
| Reddit Sri Lanka | Finance and tax discussion threads | Reddit API — public posts |
| FactCheck.lk | Pre-labeled Sri Lankan regulatory claims | Website scraping — publicly available |
| SME Survey (WhatsApp) | Anonymized forwarded messages about tax regulations | Collected via Module 1 / 2 survey instrument |

#### Annotation Schema (Label Studio)

Each social media post or forwarded message is annotated with:

| Label | Definition |
|-------|-----------|
| ACCURATE | Claim matches official source exactly |
| PARTIALLY_ACCURATE | Core claim correct but details wrong (e.g. wrong deadline date) |
| MISLEADING | Technically true but creates false impression |
| FALSE | Directly contradicts official source |
| UNVERIFIABLE | Cannot be checked against any official source |

**Quality control:** Cohen's Kappa ≥ 0.70 on 100+ double-annotated examples. Resolve disagreements via adjudication with updated guidelines.

#### Procedures and Technologies
- Collect and clean all social media posts containing tax regulation claims
- Translate Sinhala / Tamil posts using NLLB-200 (Meta) with manual spot-check verification
- Annotate dataset using Label Studio — accurate / partially accurate / misleading / false
- Calculate inter-annotator agreement using Cohen's Kappa
- Analyze spread patterns — compare engagement metrics of accurate vs inaccurate content
- Train misinformation classifier: compare fine-tuned XLM-R vs RAG-based claim verification vs GPT API
- Virality prediction model — identify linguistic features that predict high spread

**Misinformation-to-gazette lag correlation (cross-module):**
Combine Module 4 misinformation spike timestamps with Module 1 gazette publication dates. Hypothesis: misinformation prevalence increases sharply in the awareness gap window (days 0–30 post-gazette publication) when official information has not yet reached SMEs.

**Forwarded message collection (privacy-preserving):**
```
Field 1: Paste message text
Field 2: Source channel (WhatsApp group / Direct WhatsApp / Facebook / Email)
Field 3: Approximate received date
Field 4: Did you act on this information?
Auto-strip: phone numbers removed via regex before storage
```

#### Novel Contributions
- First annotated Sri Lankan tax regulation misinformation dataset
- First measurement of misinformation prevalence in Sri Lankan SME social networks
- First cross-lingual misinformation detection model for South Asian regulatory content

#### The Solution Built
A real-time claim verification interface — SME owners paste any compliance claim received from any source, and the system instantly checks it against verified official regulations with a cited verdict.

---

## 5. How All Four Modules Connect

The four modules are not separate tools — they are four investigations of the same problem feeding into one unified platform:

| Module | Barrier Investigated | What It Feeds Into the Platform |
|--------|--------------------|---------------------------------|
| 1 — Awareness Gap | Regulatory changes not reaching SMEs in time | Gazette monitor → auto-updates knowledge base → triggers risk reassessment |
| 2 — Knowledge Gap | Incorrect guidance being received by SMEs | Verified knowledge base used by ALL other modules |
| 3 — Risk Gap | Compliance risk invisible until too late | Risk scores updated when Module 1 detects new regulations |
| 4 — Misinformation Gap | Wrong information spreading faster than correct | Claim verifier draws from Module 2 knowledge base |

**Inter-module data contract (JSON schema):**
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

**The Unified Platform Name:**
> **SME Regulatory Intelligence Platform** — An AI-powered system that delivers the right information, to the right SME, at the right time, in the right language.

---

## 6. Data Collection Summary

| Module | Primary Novel Data | Supporting Public Data | Collection Method |
|--------|-------------------|----------------------|-------------------|
| 1 | SME awareness survey — when did they find out? | Gazette archives, news archives, IRD notices | Survey + web scraping + PDF parsing |
| 2 | Compliance knowledge test — what do SMEs actually know? | IRD / EPF / ETF / eROC official documents | Survey + document analysis + social media scraping |
| 3 | SME vulnerability survey — who fails and why? | Court records, IRD defaulter lists, Central Bank stats | Survey + public records + synthetic generation |
| 4 | Annotated social media misinformation dataset | FactCheck.lk, Facebook groups, Twitter, Reddit | Social media scraping + manual annotation |

> **Important:** No private enterprise data is required. All data is either publicly available, collectable through ethical surveys, or synthetically generated and calibrated against public population statistics.

---

## 7. Survey Instruments — Detailed Design

### 7.1 Overall Survey Strategy

| Instrument | Module | Type | Length | Target N |
|------------|--------|------|--------|----------|
| Awareness Survey | 1 | Recall + channel attribution | ~15 questions | 120–200 |
| Compliance Knowledge Test | 2 | Multiple-choice with right answers | 30–40 questions | 80–150 |
| Vulnerability Survey | 3 | Self-reported failures + SME profile | ~20 questions | 100–200 |
| Forwarded Message Submission | 4 | Voluntary text upload | Open-ended | As many as possible |

All four instruments share a single **SME Profile block** collected once:

| Attribute | Type | Why |
|-----------|------|-----|
| Sector | Single-choice (8 options) | Primary slice variable |
| Employee count band | Single-choice (6 bands: 1–5 to 101–250) | SME size |
| Annual turnover band | Single-choice (5 bands, banded for privacy) | Size correlate |
| Business age (years) | Numeric | Older businesses likely more aware |
| Region / Province | Single-choice (all 9 provinces) | Geographic slice |
| Urban / semi-urban / rural | Single-choice | Information access correlate |
| Primary business language | Single-choice (Sinhala/Tamil/English/Mixed) | Survey routing |
| Respondent role | Single-choice (Owner/Finance/Accountant/Manager) | Knowledge role |
| Has external accountant | Yes/No | Compliance channel |
| Has digital tools | Multi-select | Digital literacy |

### 7.2 Module 1 — Awareness Survey (15 questions)

For each of 3–5 pre-selected recent regulations:
- **Q-A1:** "Are you aware that [regulation summary]?" (Yes/No/Not sure)
- **Q-A2:** "Approximately when did you first become aware?" (1 week / 2–4 weeks / 1–3 months / 3–6 months / 6+ months / Don't remember)
- **Q-A3:** "How did you first learn about it?" (IRD website / Gazette / News / Accountant / Industry body / Social media / WhatsApp / Penalty notice / Other)
- **Q-A4:** "Did you take action as a result?" (Yes, immediately / Yes, but late / No, did not need to / No, should have / Not sure)

Plus 3 general questions (primary channel, confidence in timeliness 1–5, what would help).

### 7.3 Validation Logic (built into survey app)

| Rule | Action |
|------|--------|
| Required field empty | Block submission with error in respondent's language |
| Numeric out of plausible range | Soft warning, allow override |
| Awareness date contradicts publication date | Flag for analysis |
| Internal contradiction (no penalties + penalty amount > 0) | Soft warning, confirm |
| Completion time < 90 seconds | Flag as potential straight-lining |
| Same IP submits twice within an hour | Soft duplicate warning |

### 7.4 Multilingual Equivalence — Back-Translation Protocol
1. Author writes English version
2. Native Sinhala speaker translates to Sinhala
3. Different native speaker back-translates Sinhala → English
4. Compare to original; discrepancies trigger revision
5. Repeat for Tamil
Document this process in the methodology chapter.

### 7.5 Sample Size Targets

| Module | Minimum N | Stretch Goal | Rationale |
|--------|-----------|-------------|-----------|
| Awareness Survey | 100 | 200+ | 95% CI on lag percentile estimates; sector slicing |
| Knowledge Test | 80 | 150+ | Per-question accuracy with tight CI |
| Vulnerability Survey | 100 | 200+ | Positive class (penalized SMEs) ≥ 30 for ML |
| Forwarded Messages | 50 unique items | 200+ | Annotation-ready corpus |

---

## 8. System Architecture

### 8.1 The Five Layers

```
┌──────────────────────────────────────────────────────────────┐
│ Layer 5 — Presentation                                       │
│   Next.js (React, TypeScript, TailwindCSS) + next-intl       │
└──────────────────────────────────────────────────────────────┘
                            │ HTTPS / JSON
┌──────────────────────────────────────────────────────────────┐
│ Layer 4 — API Gateway / Backend                              │
│   FastAPI (Python) + Pydantic + JWT Auth + Rate Limiting     │
└──────────────────────────────────────────────────────────────┘
                            │ Function calls / message queue
┌──────────────────────────────────────────────────────────────┐
│ Layer 3 — Domain / Service Layer                             │
│   Module1Service, RAGPipeline, RiskModel,                    │
│   Verifier, NotificationService, SurveyService               │
└──────────────────────────────────────────────────────────────┘
                            │
┌──────────────────────────────────────────────────────────────┐
│ Layer 2 — Data Layer                                         │
│   PostgreSQL (relational) + ChromaDB (vectors)               │
│   + Object Storage (PDFs, model artifacts)                   │
└──────────────────────────────────────────────────────────────┘
                            │
┌──────────────────────────────────────────────────────────────┐
│ Layer 1 — Ingestion / ETL                                    │
│   Scrapers (gazette, news, social), PDF extractors,          │
│   NLP classifiers, data validators (APScheduler / Celery)    │
└──────────────────────────────────────────────────────────────┘
```

### 8.2 Architectural Goals
1. **Multi-tenant** — each SME has its own profile and risk view
2. **Multilingual** — UI and content in Sinhala, Tamil, English
3. **Modular** — each research module is a separable service
4. **Scalable** — starts at 100 concurrent users, scalable to 10k
5. **Reproducible** — every model version is deployable and rollback-able
6. **Auditable** — every prediction, alert, and survey response is logged
7. **Affordable** — runs on a single VM (≈ $25/month) during research

### 8.3 Key Frontend Pages (Next.js)

| Route | Purpose | Audience |
|-------|---------|---------|
| `/dashboard` | Personalized risk score, recent regulations, alerts | SME owner |
| `/regulations` | Searchable list of classified regulatory changes | SME owner |
| `/qa` | Compliance Q&A chat (Module 2) | SME owner |
| `/verify` | Claim verification UI (Module 4) | SME owner |
| `/admin/annotation` | Labeling queue interface | Research team |
| `/admin/training` | Training run dashboard | Research team |
| `/admin/models` | Model version registry | Research team |

### 8.4 Key Backend Endpoints (FastAPI)

```
POST /auth/register, POST /auth/login
GET  /regulations?category=&from=&to=&q=
GET  /regulations/{id}/translations/{lang}
POST /qa/ask                  → cited answer
POST /verify/claim             → verdict + evidence + citation
GET  /risk/me                  → risk score (0–1) for logged-in SME
GET  /risk/me/explanations     → SHAP feature attributions
POST /surveys/{instrument}/submit
GET  /admin/datasets/module/{n}?status=untrained
POST /admin/datasets/module/{n}/mark-trained
```

### 8.5 Database Schema (Core Tables)

```sql
-- Module 1 primary
CREATE TABLE regulations (
    regulation_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gazette_number       TEXT NOT NULL,
    gazette_date         DATE NOT NULL,
    source_url           TEXT NOT NULL,
    raw_text             TEXT NOT NULL,
    cleaned_text         TEXT,
    detected_language    TEXT,
    issuing_agency       TEXT,
    effective_date       DATE,
    text_hash            TEXT UNIQUE NOT NULL,
    extraction_method    TEXT,
    is_processed         BOOLEAN DEFAULT FALSE,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

-- Training data management
CREATE TABLE labeled_examples (
    example_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_number        INT NOT NULL,
    text                 TEXT NOT NULL,
    label                TEXT NOT NULL,
    annotator            TEXT NOT NULL,
    is_gold              BOOLEAN DEFAULT FALSE,
    inter_annotator_agreement REAL,
    used_in_training     BOOLEAN DEFAULT FALSE,  -- THE KEY FLAG
    used_in_split        TEXT,                    -- 'train'|'val'|'test'
    last_trained_run_id  UUID,
    text_hash            TEXT NOT NULL
);

-- SME profiles
CREATE TABLE sme_profiles (
    sme_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sector               TEXT,
    employee_count_band  TEXT,
    business_age_years   INT,
    region               TEXT,
    primary_language     TEXT,
    consent_given        BOOLEAN DEFAULT TRUE
);

-- Model versioning
CREATE TABLE model_versions (
    version_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_number        INT NOT NULL,
    version_string       TEXT UNIQUE NOT NULL,
    training_run_id      UUID,
    is_production        BOOLEAN DEFAULT FALSE,
    deployed_at          TIMESTAMPTZ
);
```

### 8.6 Architectural Decisions (Viva Defense)

| Decision | Defense |
|----------|---------|
| Monolith over microservices | Project scale does not justify microservices operational complexity |
| PostgreSQL + ChromaDB instead of one DB | Vector search needs a specialized engine; ChromaDB has better built-in tooling for embedding pipelines |
| FastAPI over Django | Async support, built-in OpenAPI docs, type-safety via Pydantic, minimal boilerplate |
| Next.js over plain React | SSR, built-in routing, SEO, production defaults; faster development |
| Local model serving over cloud LLM | Cost (zero per-call), privacy (no data leaves VM), reproducibility (fixed model version) |
| APScheduler over Celery | Project scale has few scheduled jobs; Celery would be over-engineering |

---

## 9. Technology Stack — Full Justification

| Layer | Technology | Module(s) | Why This Choice |
|-------|-----------|----------|----------------|
| **Data Collection** | Scrapy, BeautifulSoup, Playwright | All | Scrapy for bulk crawling; BS4 for one-off parsing; Playwright for JS-heavy pages |
| **PDF Parsing** | PyMuPDF (fitz), pdfplumber, Tesseract OCR | 1, 2 | PyMuPDF fastest for text PDFs; pdfplumber best for tables; Tesseract for scanned gazettes |
| **Data Processing** | Python, Pandas, NumPy | All | Unified ML + backend language; strongest data science ecosystem |
| **NLP / Classification** | HuggingFace Transformers, XLM-R, mBERT, spaCy | 1, 2, 4 | XLM-R: 100-language pretrained, outperforms mBERT on Sinhala/Tamil; spaCy for fast tokenization/NER |
| **RAG Pipeline** | LangChain, ChromaDB, FAISS | 2, 4 | LangChain reduces boilerplate; ChromaDB simple Python API with disk persistence |
| **ML Models** | scikit-learn, XGBoost, TensorFlow/Keras | 1, 3 | XGBoost best for tabular + class-imbalanced; LSTM for temporal sequences |
| **Model Interpretability** | SHAP | 3 | SHAP provides per-feature attributions; essential for explainable risk scores |
| **Annotation Tool** | Label Studio | 4 (all) | Open-source, multi-user, IAA workflow support, standard export formats |
| **Synthetic Data** | SDV, CTGAN, Faker | 3 | SDV preserves statistical properties; CTGAN for correlated tabular data |
| **Translation** | NLLB-200 (Meta), Google Translate API | 4 | NLLB-200 open-source for 200 languages including Sinhala/Tamil; GA for production |
| **Evaluation** | RAGAS, Cohen's Kappa, scikit-learn metrics | 2, 4 | RAGAS: RAG-specific (faithfulness, relevance, precision, recall); Kappa: annotation agreement |
| **Visualization** | Plotly, Seaborn, Matplotlib | All | Plotly for interactive dashboards; Seaborn/Matplotlib for thesis figures |
| **Frontend** | Next.js, TypeScript, TailwindCSS | All | SSR, built-in routing, next-intl for multilingual UI |
| **Backend** | FastAPI, Pydantic | All | Async, auto-OpenAPI docs, type-safe, Python-native |
| **Database** | PostgreSQL, ChromaDB | All | PostgreSQL for all relational data; ChromaDB for vector embeddings |
| **Experiment Tracking** | Weights & Biases (wandb) or MLflow | All | Log hyperparameters, metrics, artifacts across runs |
| **Task Scheduling** | APScheduler (dev) / Celery (if scale needed) | 1, 4 | APScheduler simple for few cron jobs; Celery if background workload grows |
| **Orchestration** | Docker, docker-compose | All | Reproducible environment; single-command deployment |

### Model Choice Justification

| Model | Used In | Why Not Alternative |
|-------|---------|-------------------|
| **XLM-RoBERTa** | Modules 1, 4 classifier | mBERT: weaker on low-resource Sinhala/Tamil. IndicBERT: limited Sinhala coverage. LaBSE: sentence embedding only, not classification |
| **XGBoost** | Module 3 risk model | LightGBM similar but less documentation. Random Forest simpler but lower accuracy. Logistic Regression = baseline only |
| **LSTM** | Module 3 temporal | Transformer time-series overkill for this data size; LSTM sufficient for sequential filing behavior |
| **RAG (LangChain + ChromaDB)** | Modules 2, 4 | Fine-tuning LLM on compliance docs would be expensive and brittle; RAG allows instant knowledge base updates |

**All models are fine-tuned, not trained from scratch.** Novel contribution is in the datasets, measurements, and findings — not the model architecture.

---

## 10. The Complete ML Lifecycle (Applied to Enigmatrix)

Every module follows the same 9-stage lifecycle. Skipping stages = indefensible thesis.

| Stage | Module 1 | Module 2 | Module 3 | Module 4 |
|-------|----------|----------|----------|----------|
| 1 — Problem framing | Information lag definition | Knowledge gap score | Risk prediction | Misinformation taxonomy |
| 2 — Module planning | Pipeline orchestration | KB structure | Feature space | Annotation taxonomy |
| 3 — Data collection | Gazette + news + survey | Official docs + social | Defaulter + survey + synthetic | Social media + FactCheck.lk |
| 4 — Preprocessing | PDF extraction (60% effort) | Document chunking | SMOTE class balancing | Multi-language normalization |
| 5 — Model selection | XLM-R classifier | RAG (retrieval + generation) | XGBoost + LSTM | XLM-R + RAG verifier |
| 6 — Training | Fine-tune on labeled gazettes | Tune retrieval + prompts | Hyperparameter sweep | Fine-tune classifier + RAG |
| 7 — Evaluation | F1 + lag-reduction measurement | RAGAS + expert rating | ROC-AUC + SHAP | F1 + spread analysis |
| 8 — Deployment | Scheduled monitor + alerts | QA chatbot endpoint | Risk score endpoint | Real-time verifier |
| 9 — Monitoring | New regulation detection | KB freshness | Concept drift | New misinformation themes |

**Evaluation requirements (non-negotiable):**
- Always report ≥ 3 model seeds; report mean ± std
- Always report per-class AND per-language metrics
- Always run at least: (a) rule-based baseline, (b) TF-IDF + LR baseline, (c) zero-shot LLM baseline
- Always use held-out test set (opened ONCE, at the end)
- Always report confusion matrix and ≥ 30 hand-reviewed errors

---

## 11. Novel Contributions — Why This Has Research Value

| Contribution Type | What It Is | Why It Is Novel |
|-------------------|-----------|----------------|
| New Dataset | Information lag dataset for Sri Lankan regulatory changes | Never measured or published before |
| New Dataset | Compliance knowledge gap scores for Sri Lankan SMEs | No benchmark exists for this |
| New Dataset | Sri Lankan tax misinformation annotated corpus | First of its kind for South Asian regulatory context |
| New Finding | Measured lag between gazette publication and SME awareness | Unknown — this research discovers it |
| New Finding | Accuracy rate of informal compliance guidance channels | Unknown — this research measures it |
| New Finding | Top predictors of SME compliance failure in Sri Lanka | Unknown — this research identifies them |
| New Finding | Misinformation prevalence and spread patterns in SME networks | Unknown — this research quantifies it |
| New Framework | Public-signal-based compliance risk prediction methodology | Applicable to any data-scarce developing economy |

---

## 12. The Complete Research Loop

| Stage | What Happens |
|-------|-------------|
| **Problem** | Sri Lankan SMEs are non-compliant due to 4 information barriers |
| **Investigation** | Each barrier is measured — lag duration, knowledge gap score, risk predictors, misinformation rate |
| **Finding** | Specific, quantified evidence of each barrier's severity — things nobody knew before |
| **Solution** | Each module directly addresses its measured barrier with a validated intervention |
| **Validation** | Solution is tested against the same measurements used to investigate the problem |
| **Contribution** | Proof that the solution reduces each barrier — with numbers, not assumptions |

---

## 13. How to Present This to the Supervisor

**What to Say:**
> Our research question is about a real human problem — why Sri Lankan SMEs fail at compliance despite intending to comply. We identify 4 specific information barriers as root causes and investigate each one empirically. Technology is our investigative instrument — not our research subject. Our findings will tell us something new about SME compliance behavior in Sri Lanka that nobody currently knows — backed by 4 novel datasets and 4 measurable research findings. No private enterprise data is required — all data is public, surveyable, or synthetically generated.

**Key point for viva defense:**
- The model is the *instrument*; the *measurement* is the contribution
- Our novelty is in the datasets, the measured findings, and the Sri Lankan SME context — not in novel model architectures
- Every technology choice has a justified alternative that was considered and rejected

---

## 14. Individual Member Responsibilities

| Member | Module | Individual Research Question | Novel Dataset |
|--------|--------|----------------------------|--------------|
| **215075J — Mohamed M.R.I** | Module 1 — Awareness Gap | What is the information lag between gazette publication and SME awareness? | Regulatory change lag timeline dataset |
| **215007F — Ahamadh M.S.A** | Module 2 — Knowledge Gap | How accurate is the compliance guidance Sri Lankan SMEs receive? | Compliance Q&A benchmark dataset |
| **215008J — Ahamed T.I** | Module 3 — Risk Gap | Which SME characteristics predict compliance failure before it occurs? | SME vulnerability and violation dataset |
| **215019T — Cader Z.R** | Module 4 — Misinformation Gap | How does tax misinformation spread through Sri Lankan SME networks? | Annotated misinformation corpus |

---

## 15. Suggested Timeline

| Phase | Period | Key Activities |
|-------|--------|---------------|
| **Phase 1 — Problem & Literature** | Feb 2026 | Literature review, confirm research gap, finalize research questions per module, taxonomy lock |
| **Phase 2 — Data Collection** | Mar 2026 | Gazette scraping (2018–2026), survey design + distribution, social media collection, ethics approval, pilot surveys (n=20) |
| **Phase 3 — Analysis and Modelling** | Apr 2026 | Data analysis, NLP classifier training, annotation (Label Studio), benchmark construction, Module 3 synthetic data generation |
| **Phase 4 — Platform Development** | May 2026 | Build unified prototype integrating all 4 module solutions; deploy on VM; connect inter-module data contracts |
| **Phase 5 — Validation** | Jun 2026 | User testing (SME owners), solution validation against research findings, RAGAS / ROC-AUC / F1 evaluation metrics |
| **Phase 6 — Write-up and Submission** | Jul–Aug 2026 | Research report, thesis chapters (IMRaD structure), demo preparation, viva rehearsal |

### Module 1 Detailed Timeline (Weeks)

| Week | Activities |
|------|-----------|
| 1–2 | Literature review, finalize taxonomy, schema design |
| 3 | Build gazette scraper + PDF storage (Scrapy + PostgreSQL) |
| 4 | Build PDF extraction pipeline (PyMuPDF + pdfplumber + Tesseract) |
| 5 | Manually label first 300 examples in Label Studio |
| 6 | Train TF-IDF baseline + first XLM-R fine-tune |
| 7 | Expand to 800+ labels; iterate and re-train; inter-annotator agreement |
| 8 | Build secondary-source watchers + lag computation engine |
| 9 | Deploy SME awareness survey via NEDA/Chambers |
| 10 | Build summarizer (NLLB-200) + alert delivery service |
| 11 | Build Module 1 dashboard; integrate with unified platform |
| 12 | Retrospective validation, lag analysis write-up, thesis chapter |

---

## 16. Risk Register

| Risk | Module | Mitigation |
|------|--------|-----------|
| Older gazettes are scanned PDFs | 1 | OCR fallback (Tesseract eng+sin+tam); accept slightly lower confidence on pre-2018 |
| Sinhala/Tamil OCR quality | 1, 4 | Tesseract Sinhala/Tamil traineddata; expect 5–10% CER; manual spot-check 10% |
| Survey response rate too low | All | Bundle all 4 instruments in one app; partner with NEDA, Chambers; WhatsApp group distribution |
| News scrapers blocked by paywalls | 1 | Use RSS feeds and headlines only — sufficient for first-mention timestamp |
| Classifier confused by long PDF context | 1 | Chunk notices + per-chunk classification; aggregate |
| Class imbalance in violation records | 3 | SMOTE + synthetic generation; report per-class metrics separately |
| Facebook API access restrictions | 4 | Manual collection from public groups as fallback; document clearly |
| New regulatory category appears mid-project | 1 | Low-confidence → human review queue; quarterly retraining trigger |
| Misinformation annotation disagreement > 30% | 4 | Refine annotation guidelines; add adjudication round; report Kappa honestly |
| Team integration failures between modules | All | Define and lock inter-module JSON contracts by end of Phase 2 |

---

## 17. Research Guides Index

All 12 supplementary research guides are available as companion documents:

| File | Covers |
|------|--------|
| `01_AI_ML_Fundamentals.md` | How models learn, fine-tuning vs training from scratch, data requirements per task type |
| `02_Complete_ML_Lifecycle.md` | Full 9-stage ML pipeline with Enigmatrix-specific examples for each module |
| `03_Research_Paper_Structure.md` | IMRaD structure, methodology writing, justification patterns for viva |
| `04_Technology_Stack_Justification.md` | Why/why-not for every technology: Python, XLM-R, XGBoost, FastAPI, Next.js, PostgreSQL |
| `05_Literature_Review_Guide.md` | How to find papers, extract justifications, compare approaches, what to cite |
| `06_Data_Collection_and_Management.md` | Database-driven pipeline, PostgreSQL schema, trained-status tracking, deduplication |
| `07_System_Architecture.md` | 5-layer architecture, all components, deployment, security, cost estimate (< $100) |
| `08_SME_Questionnaire_Design.md` | Full question text for all 4 instruments, validation logic, multilingual equivalence |
| `09_Module1_Architecture_Overview.md` | Module 1 complete system: 18 components, 7-stage pipeline, DB tables, success criteria |
| `10_Module1_Gazette_PDF_Extraction_Pipeline.md` | Step-by-step: scraping → download → inspect → extract → segment → clean → store |
| `11_Module1_NLP_Classifier_Training.md` | Label Studio setup, temporal splitting, TF-IDF baseline, XLM-R fine-tuning, serving |
| `12_Module1_End_to_End_Workflow.md` | Orchestration (Celery), secondary watchers, lag computation SQL, alert delivery, validation |

---

*— End of Research Proposal — Enigmatrix | Faculty of Information Technology | University of Moratuwa | 2026 —*
