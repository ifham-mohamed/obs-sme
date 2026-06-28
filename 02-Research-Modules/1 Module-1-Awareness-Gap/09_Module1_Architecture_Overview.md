# 09 — Module 1: Architecture Overview

> Goal: give Module 1's owner the complete picture of the system to be built — every component, every layer, every connection — before zooming into the detailed PDF extraction (file 10), classifier training (file 11), and end-to-end workflow (file 12).

---

## 1. What Module 1 Is, in One Sentence

**An automated pipeline that detects new regulatory changes from official Sri Lankan sources within hours of publication, classifies them, summarizes them in three languages, and notifies subscribed SMEs — while measuring the lag at every stage of regulatory information diffusion.**

The dual nature is essential:
- **Research output:** quantified information lag dataset + measurable findings.
- **Built artifact:** automated alert system that demonstrably reduces lag.

---

## 2. The Module 1 Research Question (Restated)

> *"Are regulatory changes reaching Sri Lankan SMEs in time to act — and what is the information lag between gazette publication and SME awareness?"*

Three measurable sub-questions:

1. **What is the lag at each stage** of the diffusion path?
   `Gazette publication → Official portal listing → News coverage → SME awareness`
2. **Which channels** deliver regulatory information fastest, and which lag the most?
3. **Does lag vary** by regulation type, sector, business size, or geographic region?

---

## 3. The High-Level Pipeline (Bird's-Eye View)

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│   STAGE A — INGESTION (continuous, scheduled)                            │
│   documents.gov.lk → list new gazettes → download PDFs → store raw       │
│                                                                          │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│   STAGE B — EXTRACTION (per gazette)                                     │
│   PDF → text → section segmentation → notice/rule extraction → cleaned  │
│                                                                          │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│   STAGE C — CLASSIFICATION (per extracted notice)                        │
│   text → classifier → category + confidence → metadata extraction        │
│                                                                          │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│   STAGE D — SECONDARY-SOURCE TRACKING (per regulation, ongoing)          │
│   Watch IRD/EPF/ETF/eROC sites + news + social mentions                  │
│   → record first-appearance timestamps                                   │
│                                                                          │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│   STAGE E — SUMMARIZATION & TRANSLATION                                  │
│   Generate plain-language summary in EN/SI/TA                            │
│                                                                          │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│   STAGE F — ALERTING                                                     │
│   Match regulation → relevant SMEs → notify (email / dashboard / SMS)   │
│                                                                          │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│   STAGE G — LAG MEASUREMENT (research output)                            │
│   Combine pipeline timestamps + SME survey awareness data                │
│   → compute lag distribution per stage, per category, per SME profile   │
│                                                                          │
└────────────────────────────────────────────────────────────────────────┘
```

Each stage is described in detail below; the next files (10, 11, 12) drill deeper.

---

## 4. The Component Inventory

| # | Component | Type | Detailed in |
|---|-----------|------|-------------|
| 1 | Gazette scraper | Python script (Scrapy) | File 10 §3 |
| 2 | PDF downloader | Python script | File 10 §3 |
| 3 | PDF text extractor | Python module (PyMuPDF + pdfplumber + Tesseract OCR) | File 10 §4–7 |
| 4 | Section segmenter | Python module (rule + transformer) | File 10 §8 |
| 5 | Notice / rule extractor | Python module + regex + spaCy | File 10 §9 |
| 6 | Text cleaner | Python module | File 10 §10 |
| 7 | Language detector | Python module (`fasttext` lid) | File 10 §11 |
| 8 | Annotation UI | Next.js admin page | File 11 §3 |
| 9 | TF-IDF baseline classifier | scikit-learn | File 11 §6 |
| 10 | XLM-R fine-tuned classifier | HuggingFace + PyTorch | File 11 §7 |
| 11 | Classifier evaluation harness | Python | File 11 §9 |
| 12 | Classifier serving endpoint | FastAPI | File 11 §11 |
| 13 | Secondary-source watchers | Python scheduled jobs | File 12 §4 |
| 14 | Lag computation engine | Python + SQL | File 12 §5 |
| 15 | Summarizer / translator | LLM API or NLLB-200 | File 12 §6 |
| 16 | Alert delivery service | FastAPI + email/SMS providers | File 12 §7 |
| 17 | SME subscription manager | DB + UI | File 12 §7 |
| 18 | Module 1 dashboard | Next.js page | File 12 §8 |

18 components total. Sounds large; in practice most are 50–200 lines of Python each.

---

## 5. Data Flow Diagram (Detailed)

```
                          documents.gov.lk
                                │
                       (scheduled scraper — daily)
                                │
                                ▼
   ┌────────────────────────────────────────────────┐
   │           raw PDFs in object storage           │
   │           /raw/gazettes/yyyy/mm/dd/...         │
   └────────────────────────────────────────────────┘
                                │
                  (extraction worker, per file)
                                ▼
   ┌────────────────────────────────────────────────┐
   │           cleaned text + metadata              │
   │           PostgreSQL.regulations               │
   └────────────────────────────────────────────────┘
                                │
                       (classifier service)
                                ▼
   ┌────────────────────────────────────────────────┐
   │       category + confidence + metadata         │
   │   PostgreSQL.regulation_classifications        │
   └────────────────────────────────────────────────┘
            │                                  │
            ▼                                  ▼
  (summarizer / translator)        (alert matcher)
            │                                  │
            ▼                                  ▼
  ┌────────────────────┐           ┌──────────────────────┐
  │  multilingual      │           │  outbound emails     │
  │  summaries stored  │           │  + dashboard cards   │
  └────────────────────┘           └──────────────────────┘

  (parallel)
  ┌────────────────────────────────────────────────┐
  │  IRD / EPF / ETF / eROC scrapers — record      │
  │  first-appearance timestamps for the same      │
  │  regulation                                     │
  │  PostgreSQL.regulation_secondary_appearances    │
  └────────────────────────────────────────────────┘
                                │
            ┌───────────────────┼─────────────────────┐
            ▼                                          ▼
  (news scrapers similarly)            (SME awareness survey)
                                                       │
                                                       ▼
                           ┌──────────────────────────────────┐
                           │   PostgreSQL.survey_responses    │
                           │   (per regulation, per SME,      │
                           │   when did you find out?)        │
                           └──────────────────────────────────┘
                                          │
                                          ▼
                          ┌──────────────────────────────┐
                          │  LAG ANALYSIS                │
                          │  (Stage G)                   │
                          │  Joins all timestamps        │
                          │  Produces:                   │
                          │  - per-stage lag distribution│
                          │  - per-category breakdown    │
                          │  - per-SME-profile breakdown │
                          │  - novel research dataset    │
                          └──────────────────────────────┘
```

---

## 6. The Two Outputs: Solution and Research

| Output                            | What it is                                      | Used by                                 |
| --------------------------------- | ----------------------------------------------- | --------------------------------------- |
| **Built artifact (the platform)** | The pipeline above, deployed and running        | SMEs receiving alerts                   |
| **Research dataset & findings**   | Lag distribution dataset + statistical analysis | Your thesis, papers, future researchers |

The same pipeline produces both. The platform is the *vehicle* for the research, and the research is the *justification* for the platform.

---

## 7. Database Tables Needed for Module 1

(These extend the schema in file 06.)

```sql
-- Tracks where a regulation appeared after its initial gazette publication
CREATE TABLE regulation_secondary_appearances (
    appearance_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    regulation_id    UUID NOT NULL REFERENCES regulations(regulation_id),
    source_type      TEXT NOT NULL,    -- 'ird_portal' | 'epf_portal' | 'news' | 'twitter' | 'fb_group'
    source_url       TEXT NOT NULL,
    first_seen_at    TIMESTAMPTZ NOT NULL,
    matching_method  TEXT,             -- 'keyword' | 'semantic' | 'manual'
    matching_confidence REAL,
    UNIQUE (regulation_id, source_type, source_url)
);

-- Tracks SME subscriptions for alert routing
CREATE TABLE sme_alert_subscriptions (
    subscription_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sme_id           UUID REFERENCES sme_profiles(sme_id),
    category_filter  TEXT[],          -- e.g. {'TAX_RATE_CHANGE', 'EPF_CHANGE'}
    sector_filter    TEXT[],
    delivery_channel TEXT NOT NULL,   -- 'email' | 'sms' | 'dashboard'
    language         TEXT NOT NULL,
    active           BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Logs every alert sent (for measuring "lag from gazette to alert delivery")
CREATE TABLE alerts_sent (
    alert_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    regulation_id    UUID REFERENCES regulations(regulation_id),
    sme_id           UUID REFERENCES sme_profiles(sme_id),
    sent_at          TIMESTAMPTZ DEFAULT NOW(),
    channel          TEXT,
    delivery_status  TEXT,
    opened_at        TIMESTAMPTZ
);

-- Multilingual summaries
CREATE TABLE regulation_summaries (
    summary_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    regulation_id    UUID REFERENCES regulations(regulation_id),
    language         TEXT NOT NULL,
    summary_text     TEXT NOT NULL,
    generation_method TEXT,           -- 'gpt-4' | 'nllb-200' | 'human'
    generated_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (regulation_id, language)
);
```

---

## 8. The 12 Regulatory Change Categories (Initial Taxonomy)

The classifier will assign each notice to one of these (refine after labeling pilots):

| # | Category | Example trigger |
|---|----------|-----------------|
| 1 | TAX_RATE_CHANGE | "VAT rate increased to 18%" |
| 2 | TAX_THRESHOLD_CHANGE | "Income tax threshold raised to..." |
| 3 | DEADLINE_EXTENSION_OR_CHANGE | "Filing deadline extended to..." |
| 4 | NEW_FORM_OR_PROCEDURE | "Form A123 introduced for..." |
| 5 | EPF_ETF_CHANGE | EPF/ETF contribution / rate / procedure |
| 6 | LICENSING_OR_REGISTRATION_CHANGE | Form 6, eROC requirements |
| 7 | INDUSTRY_SPECIFIC_REGULATION | Targeted at one sector |
| 8 | PENALTY_CHANGE | Fines, surcharges, interest |
| 9 | EXEMPTION_OR_RELIEF | New exemption, COVID-style relief |
| 10 | CLARIFICATION_OR_FAQ | Issued to clarify earlier rule |
| 11 | REPEAL_OR_RESCISSION | Removes earlier rule |
| 12 | OTHER_REGULATORY | Fits none of the above |

You may also need a "NOT_REGULATORY" filter category for non-regulatory gazette content (proclamations, appointments, etc.) — see file 11.

---

## 9. Success Criteria for Module 1

The module is a research success if it shows:

| Criterion | Target |
|-----------|--------|
| Classifier macro-F1 on test set | ≥ 0.80 |
| Information lag dataset built | ≥ 200 regulations × 4 stages = 800 timestamp points |
| SME survey responses | ≥ 100 valid responses |
| Statistically significant lag differences across stages | p < 0.05 |
| Channel ranking with 95% CI | Yes |
| Alert system delivers regulations within 24 hours of gazette publication | Yes (median) |
| Lag reduction demonstrated vs measured baseline | ≥ 50% reduction |

---

## 10. Timeline (Module 1 Member's Perspective)

| Week | Activities |
|------|-----------|
| 1–2 | Literature review, finalize taxonomy, schema design |
| 3 | Build gazette scraper + PDF storage |
| 4 | Build PDF extraction pipeline (text + segmentation) |
| 5 | Manually label first 300 examples for classifier |
| 6 | Train baselines + first XLM-R fine-tune |
| 7 | Iterate on labeling, expand to 800 examples, re-train |
| 8 | Build secondary-source watchers + lag computation |
| 9 | Deploy SME awareness survey (in parallel with Module 1 owner's other tasks) |
| 10 | Build summarizer + translator + alert service |
| 11 | Build Module 1 dashboard, integrate with platform |
| 12 | Validation, retrospective testing, write up findings |

---

## 11. Risks Specific to Module 1

| Risk | Mitigation |
|------|------------|
| Older gazettes are scanned PDFs (no extractable text) | OCR fallback (Tesseract); accept slightly lower accuracy on pre-2018 |
| Sinhala/Tamil OCR quality | Use Tesseract Sinhala/Tamil traineddata; expect 5–10% character error rate; manual spot-check |
| Gazettes contain non-regulatory content (proclamations, appointments) | Add a NOT_REGULATORY filter step before category classification |
| Survey response rate too low for lag measurement | Bundle with Modules 2/3 surveys; partner with NEDA/Chambers |
| News scrapers blocked by paywalls | Use RSS feeds and headlines only where full text is paywalled — sufficient for first-mention timestamp |
| Classifier confused by long PDF context | Use chunking + per-chunk classification, then aggregate |
| New category appears in 2026 that wasn't in training | Have a "low confidence → flag for human review" path |

---

## 12. What File 10, 11, and 12 Cover Next

- **File 10 — Gazette PDF Extraction Pipeline:** how to scrape, download, parse, segment, and clean. Step-by-step with code patterns.
- **File 11 — NLP Classifier Training:** how to label, split, train baselines, fine-tune XLM-R, evaluate, and version.
- **File 12 — End-to-End Workflow:** how all components run together, alerting, lag computation, validation, and the research findings extraction.

Read them in order.

---

## Summary

Module 1 is a 7-stage pipeline (ingestion → extraction → classification → secondary-source tracking → summarization → alerting → lag measurement) producing two outputs: a deployable alert system AND a novel quantified-lag research dataset. 18 components, 12 weeks, 4 new database tables, 12-category taxonomy. The next three files give you the full implementation detail.
