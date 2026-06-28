# SME Regulatory Intelligence Platform
## Module 1 (Awareness Gap) & Module 4 (Misinformation Spread)
### Complete Data Architecture, Source Specifications & Survey Instruments

---

## ⚠️ Pre-Read

This document complements the previously delivered Module 2 & 3 materials. It covers:

- **Module 1** — Tracking how regulatory information flows from Government Gazette → Official portals → News → SME awareness, plus measuring the lag at each stage
- **Module 4** — Tracking how (mis)information about regulations spreads through social media, forums, and messaging apps

Both modules feed the same core platform but have completely different data pipelines. Module 1 is about **official information flow**; Module 4 is about **unofficial/informal information flow**. Together they answer: *"What did the government publish, and what did people actually end up believing?"*

The Next.js web application your team is building will serve as both the data ingestion frontend (for SME survey responses, manual annotation) and the public-facing platform (for SMEs to check claims and receive alerts).

---

# PART A — MODULE 1: REGULATORY CHANGE AWARENESS GAP

## A1. The Problem Restated With a Concrete Example

Imagine the government publishes a new regulation: **"All mobile phone shops and electronic retailers must stop selling multi-pin universal power adapters that do not comply with new SLSI safety standards, effective from a specified date."**

This regulation flows through the following stages — and at each stage, there is a measurable *delay* before the next stage receives the information:

| Stage | Who | Time |
|---|---|---|
| **T0** | Cabinet approves regulation | Day 0 |
| **T1** | Bill drafted and published on documents.gov.lk under "Bills" | Day 0 → +X days |
| **T2** | Act certified by Speaker, published on documents.gov.lk under "Acts" | Day X → +Y days |
| **T3** | Implementing notice published in weekly Gazette (Part I-General) or Extraordinary Gazette | Day Y → +Z days |
| **T4** | IRD / SLSI / Ministry publishes secondary notice on their own portal | Day Z → +A days |
| **T5** | News outlets (Daily FT, Daily Mirror, LBO) report on it | Day A → +B days |
| **T6** | SME owner of an electronics shop in Colombo finally hears about it | Day B → +C days |
| **T7** | Same shop owner in Jaffna or Hambantota hears about it | Day C → +D days |
| **T8** | Effective date of regulation | Predetermined |
| **T9** | First enforcement action / fine / court case against a non-compliant SME | Date of violation |

**Module 1's research finding** = the *measured distribution of T6−T1, T6−T3, T6−T5, etc.* across regulations and across SME profiles. Nobody has ever measured this for Sri Lanka. That measurement IS the novel contribution.

---

## A2. Data Source Catalogue — Module 1

### A2.1 Primary Source: documents.gov.lk

Based on your screenshots, the site has the following navigation structure:

```
documents.gov.lk
├── /view/bill/bl_2026.html        → Bills (drafts before becoming law)
│   └── Each bill: Bill Number, Date, Description, Download (EN/SI/TA)
├── /view/act/acts_2026.html       → Acts (certified law)
│   └── Each act: Act Number, Date, Description, Download (EN/SI/TA)
├── /view/egz/egz_2026.html        → Extraordinary Gazettes
│   └── Each gazette: Gazettes Number, Date, Description, Download (EN/SI/TA)
└── /view/gz/2026.html             → Regular weekly Gazettes
    └── Each gazette has DATE, links to sub-parts:
        ├── PART 1 (I) - General
        ├── PART 1 (IIA) - Advertising
        ├── PART 1 (IIB) - Advertising
        ├── PART 1 (III) - Trade Marks and Patent Notices
        └── PART 2 - Legal Section
        Each part: EN / SI / TA download buttons (some greyed out = not available)
```

### A2.2 Source Inventory Table

| Source ID | Source Name | URL Pattern | Document Type | Languages | Update Frequency | Scrape Method |
|---|---|---|---|---|---|---|
| SRC_GOV_BILL | Government Bills | `documents.gov.lk/view/bill/bl_{year}.html` | Draft legislation | EN/SI/TA | Weekly | Scrapy + PyMuPDF |
| SRC_GOV_ACT | Government Acts | `documents.gov.lk/view/act/acts_{year}.html` | Certified law | EN/SI/TA | Weekly | Scrapy + PyMuPDF |
| SRC_GOV_EGZ | Extraordinary Gazettes | `documents.gov.lk/view/egz/egz_{year}.html` | Time-sensitive notices | EN/SI/TA | Daily | Scrapy + PyMuPDF |
| SRC_GOV_GZ | Weekly Gazette | `documents.gov.lk/view/gz/{year}.html` → `gz/{date}.html` | Regular notices | EN/SI/TA | Weekly (Friday) | Scrapy + PyMuPDF |
| SRC_IRD | Inland Revenue Dept | `ird.gov.lk` (notices, circulars) | Tax updates | EN/SI/TA | Irregular | Scrapy + change detection |
| SRC_EPF | EPF Department | `epf.lk` | EPF circulars | EN/SI/TA | Irregular | Scrapy |
| SRC_ETF | ETF Board | `etfb.lk` | ETF circulars | EN/SI/TA | Irregular | Scrapy |
| SRC_EROC | Registrar of Companies | `drc.gov.lk` | Company law updates | EN/SI/TA | Irregular | Scrapy |
| SRC_SLSI | Sri Lanka Standards Institution | `slsi.lk` | Product standards | EN | Irregular | Scrapy |
| SRC_CBSL | Central Bank of Sri Lanka | `cbsl.gov.lk` | Financial regulations | EN/SI/TA | Daily | Scrapy + RSS |
| SRC_NEWS_FT | Daily FT | `ft.lk` | Business news | EN | Daily | RSS + Scrapy |
| SRC_NEWS_LBO | Lanka Business Online | `lankabusinessonline.com` | Business news | EN | Daily | RSS + Scrapy |
| SRC_NEWS_MIRROR | Daily Mirror | `dailymirror.lk` | General news | EN | Daily | RSS + Scrapy |
| SRC_NEWS_ADA | Ada Derana | `adaderana.lk` | General news | EN/SI/TA | Daily | RSS + Scrapy |
| SRC_NEWS_HIRU | Hiru News | `hirunews.lk` | General news | EN/SI/TA | Daily | RSS + Scrapy |

### A2.3 What We Extract From Each Source — Verified Examples

> **Worked end-to-end example shipped in the app.** The M1→M2→M3 data shape this ingest pipeline should produce per SME-relevant regulation is implemented as the seeded regulation `VAT_SSCL_MERGE_2026` ("VAT and SSCL merged into a single 20% VAT, April 2026 — a restructuring, not a real increase") + its cross-module chain `awareness.v1.q13 → VAT_SSCL_MERGE_FACT_001 → M3_VAT_SSCL_MERGE_PRACTICE → M3_VAT_SSCL_MERGE_PENALTY`, all junction-linked to the regulation. The per-regulation routing pattern: an M0 awareness question (`is_branching_root`, `linked_regulation_id` set) → `next_question_rules` route the non-ideal answers to an M2 factual/application knowledge question → its wrong answers route to M3 behaviour/penalty questions. See [`../SETUP/11_Survey_System.md`](../SETUP/11_Survey_System.md) §10.3 and `module_2_and_3_data_architecture.md` DOMAIN 1.

Your uploaded PDFs are perfect ground truth examples. Let me show what gets extracted:

**Example 1: Bill 31/2026 — Value Added Tax (Amendment) Bill**
```
- bill_number: "31/2026"
- bill_publication_date: "2026-04-29"  (from "Issued on 29.04.2026")
- gazette_part_reference: "Part II of April 24, 2026"
- principal_act_amended: "Value Added Tax Act, No. 14 of 2002"
- title: "Value Added Tax (Amendment) Bill"
- ordering_authority: "Minister of Finance, Planning and Economic Development"
- price_lkr: 115.20
- key_changes_extracted (NLP): [
    "Extension of VAT charging date for digital services to July 1, 2026",
    "Reduction of VAT registration threshold to Rs. 9M per quarter / Rs. 36M annual",
    "VAT on financial services increased from 18% to 20.5%",
    "New Chapter IIIC for digital services by non-residents",
    "Use of secured point-of-sale machines mandated",
    "SVAT scheme repeal consequential amendments",
    "New criminal proceedings provisions",
    ...
  ]
- affects_sectors: ["Universal", "IT & Software", "Financial Services", "Retail", "F&B"]
- effective_dates_mentioned: ["2026-07-01", "2025-10-01", "2026-04-01"]
- english_pdf_url: "documents.gov.lk/files/bill/2026/4/31-2026_E.pdf"
- sinhala_pdf_url: "documents.gov.lk/files/bill/2026/4/31-2026_S.pdf"
- tamil_pdf_url: "documents.gov.lk/files/bill/2026/4/31-2026_T.pdf"
- pdf_pages: 26
```

**Example 2: Act 10/2026 — Social Security Contribution Levy (Amendment) Act**
```
- act_number: "10/2026"
- act_certified_date: "2026-04-09"
- gazette_publication_date: "2026-04-10"
- principal_act_amended: "Social Security Contribution Levy Act, No. 25 of 2022"
- key_changes_extracted (NLP): [
    "SSCL registration threshold reduced from 60M to 36M annually",
    "Quarter threshold of Rs. 9M added effective July 1, 2026",
    "Motor vehicles added to SSCL imposable category from May 1, 2026",
    "Coconut oil/palm oil shifted from Special Commodity Levy to SSCL"
  ]
- affects_sectors: ["Universal", "Manufacturing", "Retail", "Transport"]
- effective_dates_mentioned: ["2026-07-01", "2026-05-01"]
- prerequisite_bill_reference: (link to original bill that became this act)
```

**Example 3: Extraordinary Gazette 2486/15**
```
- gazette_number: "2486/15"
- gazette_date: "2026-04-28"
- subject: "Election Commission - Filling of vacancy, Negombo Municipal Council"
- relevant_to_smes: false  (this is about an election, not a business regulation)
- sector_relevance: []
```
**Important:** Not every gazette is SME-relevant. The classifier must filter.

**Example 4: Regular Gazette 2487 (April 30, 2026, Part I-General)**
```
- gazette_number: "2487"
- gazette_date: "2026-04-30"
- gazette_part: "I-General"
- contents_extracted: [
    {section: "Cabinet Appointments", subject: "District Secretary appointments", sme_relevant: false},
    {section: "Justice of Peace Appointments", subject: "140 JoP appointments", sme_relevant: false},
    {section: "Tissamaharama Pilgrimage Regulation", subject: "Pilgrimage period declaration", sme_relevant: true, sectors: ["Tourism", "F&B", "Retail-Hambantota"]},
    {section: "Bank Foreclosure Notices", subject: "NDB, Pan Asia, DFCC, Sampath, Commercial Bank loan default notices", sme_relevant: true, sectors: ["Universal-distressed-SMEs"]}
  ]
```

---

## A3. PostgreSQL Schema for Module 1

```sql
-- =====================================================================
-- MODULE 1 — REGULATORY AWARENESS GAP
-- Schema for tracking regulations from publication → SME awareness
-- =====================================================================

-- ---------------------------------------------------------------
-- A3.1 Source registry — every place we collect data from
-- ---------------------------------------------------------------
CREATE TABLE m1_sources (
    source_id           SERIAL PRIMARY KEY,
    source_code         VARCHAR(30) NOT NULL UNIQUE,  -- e.g. SRC_GOV_BILL
    source_name         VARCHAR(200) NOT NULL,
    source_type         VARCHAR(30) NOT NULL CHECK (source_type IN
                            ('official_primary',     -- documents.gov.lk
                             'official_secondary',   -- IRD, EPF etc portals
                             'news_media',           -- Daily FT, etc
                             'social_media',         -- not used in M1, used in M4
                             'industry_body')),      -- Chamber of Commerce, etc
    base_url            TEXT,
    languages_available VARCHAR(20),  -- 'en,si,ta' or 'en' etc
    update_frequency    VARCHAR(20),  -- 'daily','weekly','irregular'
    scrape_method       VARCHAR(50),
    is_active           BOOLEAN DEFAULT TRUE,
    last_scraped_at     TIMESTAMPTZ,
    notes               TEXT
);

-- ---------------------------------------------------------------
-- A3.2 The CORE entity — a regulatory change event
-- This is what we track end-to-end through every stage
-- ---------------------------------------------------------------
CREATE TABLE m1_regulations (
    regulation_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- Identification
    regulation_short_code   VARCHAR(50) UNIQUE,  -- internal slug e.g. "VAT_AMD_2026_31"
    document_type           VARCHAR(30) NOT NULL CHECK (document_type IN
                                ('bill','act','extraordinary_gazette',
                                 'weekly_gazette','circular','order','notification')),
    document_number         VARCHAR(50),  -- e.g. "31/2026", "10/2026", "2486/15"
    title_en                TEXT NOT NULL,
    title_si                TEXT,
    title_ta                TEXT,
    principal_act_amended   TEXT,  -- "Value Added Tax Act, No. 14 of 2002"
    -- Stage timestamps (the heart of M1)
    cabinet_approval_date       DATE,
    bill_published_date         DATE,    -- T1
    act_certified_date          DATE,    -- T2 (if applicable)
    gazette_published_date      DATE,    -- T3
    effective_date              DATE,    -- T8 (often future-dated)
    -- Source linkage
    primary_source_id           INTEGER REFERENCES m1_sources(source_id),
    primary_source_url          TEXT,
    pdf_en_url                  TEXT,
    pdf_si_url                  TEXT,
    pdf_ta_url                  TEXT,
    pdf_pages                   INTEGER,
    -- Classification (filled by NLP classifier)
    is_sme_relevant             BOOLEAN,
    sme_relevance_confidence    NUMERIC(3,2),  -- 0.00 to 1.00
    regulatory_domain_id        INTEGER REFERENCES regulatory_domains(domain_id),
    change_category             VARCHAR(50) CHECK (change_category IN
                                    ('rate_change','threshold_change','deadline_change',
                                     'new_obligation','new_exemption','penalty_change',
                                     'procedural_change','registration_change',
                                     'sector_specific','definition_change','repeal','other')),
    severity_level              SMALLINT CHECK (severity_level BETWEEN 1 AND 5),  -- 5 = major impact
    -- Audit
    scraped_at                  TIMESTAMPTZ DEFAULT NOW(),
    extracted_at                TIMESTAMPTZ,
    classified_at               TIMESTAMPTZ,
    expert_verified             BOOLEAN DEFAULT FALSE,
    expert_verified_by          VARCHAR(100),
    expert_verified_at          DATE,
    notes                       TEXT
);

CREATE INDEX idx_m1_reg_dates ON m1_regulations(bill_published_date, gazette_published_date, effective_date);
CREATE INDEX idx_m1_reg_sme ON m1_regulations(is_sme_relevant) WHERE is_sme_relevant = TRUE;
CREATE INDEX idx_m1_reg_domain ON m1_regulations(regulatory_domain_id);

-- ---------------------------------------------------------------
-- A3.3 Sectors affected (many-to-many)
-- ---------------------------------------------------------------
CREATE TABLE m1_regulation_sectors (
    regulation_id   UUID NOT NULL REFERENCES m1_regulations(regulation_id) ON DELETE CASCADE,
    sector_id       INTEGER NOT NULL REFERENCES sectors(sector_id),
    impact_level    SMALLINT CHECK (impact_level BETWEEN 1 AND 5),
    PRIMARY KEY (regulation_id, sector_id)
);

-- ---------------------------------------------------------------
-- A3.4 Specific changes within one regulation (clause-level)
-- A single VAT Amendment Act can have 19 distinct changes
-- ---------------------------------------------------------------
CREATE TABLE m1_regulation_changes (
    change_id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    regulation_id           UUID NOT NULL REFERENCES m1_regulations(regulation_id) ON DELETE CASCADE,
    clause_reference        VARCHAR(50),  -- e.g. "Clause 5", "Section 25C(3)"
    change_summary_en       TEXT NOT NULL,
    change_summary_si       TEXT,
    change_summary_ta       TEXT,
    old_value               TEXT,  -- e.g. "60 million", "18%"
    new_value               TEXT,  -- e.g. "36 million", "20.5%"
    effective_date          DATE,
    applies_to              TEXT,  -- "all VAT-registered businesses", "financial services only"
    real_world_impact       TEXT,  -- short plain-language description
    extracted_by            VARCHAR(50)  -- 'nlp_xlm_r','manual','rule_based'
);

CREATE INDEX idx_m1_change_reg ON m1_regulation_changes(regulation_id);

-- ---------------------------------------------------------------
-- A3.5 Real-world examples (for the platform's explainer feature)
-- e.g. "Multi-pin adapter ban" example
-- ---------------------------------------------------------------
CREATE TABLE m1_real_world_examples (
    example_id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    regulation_id           UUID NOT NULL REFERENCES m1_regulations(regulation_id) ON DELETE CASCADE,
    scenario_title          VARCHAR(200) NOT NULL,
    scenario_description    TEXT NOT NULL,  -- "Mobile/electronics shops cannot sell non-SLSI multi-pin adapters"
    affected_business_type  VARCHAR(200),
    sme_required_action     TEXT,           -- "Remove non-compliant stock by date X, switch to SLSI-approved supplier"
    sme_required_records    TEXT,           -- "Maintain SLSI certificate for each batch sold"
    typical_violation_pattern TEXT,
    operational_flow_steps  JSONB,          -- step-by-step ordered procedure
    is_published_on_platform BOOLEAN DEFAULT FALSE,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------
-- A3.6 Penalties and enforcement (for the deterrent/awareness piece)
-- ---------------------------------------------------------------
CREATE TABLE m1_regulation_penalties (
    penalty_id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    regulation_id           UUID NOT NULL REFERENCES m1_regulations(regulation_id) ON DELETE CASCADE,
    violation_type          VARCHAR(200) NOT NULL,
    penalty_type            VARCHAR(50) CHECK (penalty_type IN
                                ('fine','imprisonment','both','license_revocation',
                                 'business_closure','public_naming','asset_seizure')),
    penalty_min_lkr         NUMERIC(15,2),
    penalty_max_lkr         NUMERIC(15,2),
    imprisonment_max_months SMALLINT,
    additional_consequences TEXT,
    legal_basis_section     VARCHAR(100)  -- e.g. "Section 66(3) of VAT Act"
);

-- ---------------------------------------------------------------
-- A3.7 Court judgments / enforcement actions (links real cases to regulations)
-- ---------------------------------------------------------------
CREATE TABLE m1_court_cases (
    case_id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    regulation_id           UUID REFERENCES m1_regulations(regulation_id),
    case_number             VARCHAR(100),
    court_name              VARCHAR(200),  -- "Magistrate Court Colombo", etc
    case_filed_date         DATE,
    judgment_date           DATE,
    defendant_business_type VARCHAR(200),
    defendant_sector_id     INTEGER REFERENCES sectors(sector_id),
    defendant_size          VARCHAR(20),  -- 'micro','small','medium','large'
    violation_summary       TEXT,
    judgment_outcome        VARCHAR(50) CHECK (judgment_outcome IN
                                ('convicted','acquitted','settled','withdrawn','pending','appealed')),
    fine_imposed_lkr        NUMERIC(15,2),
    imprisonment_imposed_months SMALLINT,
    additional_orders       TEXT,
    source_url              TEXT,  -- lawnet.gov.lk link
    summary_for_smes        TEXT   -- plain language version for the platform
);

-- ---------------------------------------------------------------
-- A3.8 Multi-stage timeline tracking (the LAG measurement table)
-- One row per regulation per propagation event
-- ---------------------------------------------------------------
CREATE TABLE m1_propagation_events (
    event_id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    regulation_id           UUID NOT NULL REFERENCES m1_regulations(regulation_id) ON DELETE CASCADE,
    source_id               INTEGER NOT NULL REFERENCES m1_sources(source_id),
    event_type              VARCHAR(40) NOT NULL CHECK (event_type IN
                                ('bill_published','act_certified','gazette_published',
                                 'official_portal_notice','news_first_coverage',
                                 'industry_body_alert','social_media_first_mention',
                                 'sme_first_aware')),
    event_timestamp         TIMESTAMPTZ NOT NULL,
    event_url               TEXT,
    event_title             TEXT,
    event_summary           TEXT,
    -- Lag from baseline (gazette publication)
    lag_days_from_gazette   INTEGER,  -- calculated; can be negative if leak
    detected_method         VARCHAR(50),  -- 'scraper','manual','rss','survey'
    detected_at             TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_m1_prop_reg ON m1_propagation_events(regulation_id);
CREATE INDEX idx_m1_prop_event_type ON m1_propagation_events(event_type);

-- ---------------------------------------------------------------
-- A3.9 SME AWARENESS SURVEY responses (the "when did you find out?" data)
-- Connected to the same respondents table from M2/M3
-- ---------------------------------------------------------------
CREATE TABLE m1_sme_awareness_responses (
    awareness_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    respondent_id           UUID NOT NULL REFERENCES respondents(respondent_id) ON DELETE CASCADE,
    regulation_id           UUID NOT NULL REFERENCES m1_regulations(regulation_id),
    -- Awareness facts
    is_aware                BOOLEAN NOT NULL,
    awareness_date_reported DATE,            -- "When did you first hear about it?"
    awareness_date_precision VARCHAR(20)     -- 'exact','approximate_week','approximate_month','dont_remember'
                            CHECK (awareness_date_precision IN
                                ('exact','approximate_week','approximate_month','dont_remember')),
    -- Channel
    first_channel           VARCHAR(50) CHECK (first_channel IN
                                ('official_website','government_letter','accountant',
                                 'tax_consultant','industry_body','chamber_of_commerce',
                                 'newspaper','tv_news','radio','online_news',
                                 'facebook','whatsapp_group','linkedin','twitter','youtube',
                                 'colleague','customer','supplier','other','not_aware')),
    first_channel_other     TEXT,
    -- Understanding depth (links to M2 logic)
    self_rated_understanding SMALLINT CHECK (self_rated_understanding BETWEEN 1 AND 5),
    knows_effective_date     BOOLEAN,
    knows_required_action    BOOLEAN,
    has_taken_action         BOOLEAN,
    action_taken_description TEXT,
    -- Calculated (server-side)
    lag_days_vs_gazette      INTEGER,  -- awareness_date_reported - regulation.gazette_published_date
    answered_at              TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (respondent_id, regulation_id)
);

CREATE INDEX idx_m1_aware_reg ON m1_sme_awareness_responses(regulation_id);
CREATE INDEX idx_m1_aware_resp ON m1_sme_awareness_responses(respondent_id);

-- ---------------------------------------------------------------
-- A3.10 ANALYTICAL VIEWS for Module 1
-- ---------------------------------------------------------------

-- View: per-regulation lag summary
CREATE OR REPLACE VIEW v_m1_regulation_lag_summary AS
SELECT
    r.regulation_id,
    r.document_number,
    r.title_en,
    r.gazette_published_date,
    r.effective_date,
    -- Channel lags
    MIN(CASE WHEN p.event_type = 'official_portal_notice' THEN p.lag_days_from_gazette END) AS lag_to_official_portal,
    MIN(CASE WHEN p.event_type = 'news_first_coverage' THEN p.lag_days_from_gazette END) AS lag_to_news,
    MIN(CASE WHEN p.event_type = 'social_media_first_mention' THEN p.lag_days_from_gazette END) AS lag_to_social,
    -- SME awareness statistics
    COUNT(a.awareness_id) AS smes_surveyed,
    SUM(CASE WHEN a.is_aware THEN 1 ELSE 0 END) AS smes_aware,
    ROUND(AVG(a.lag_days_vs_gazette), 1) AS avg_sme_lag_days,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY a.lag_days_vs_gazette) AS median_sme_lag_days
FROM m1_regulations r
LEFT JOIN m1_propagation_events p ON p.regulation_id = r.regulation_id
LEFT JOIN m1_sme_awareness_responses a ON a.regulation_id = r.regulation_id
WHERE r.is_sme_relevant = TRUE
GROUP BY r.regulation_id, r.document_number, r.title_en, r.gazette_published_date, r.effective_date;

-- View: channel effectiveness ranking
CREATE OR REPLACE VIEW v_m1_channel_effectiveness AS
SELECT
    first_channel,
    COUNT(*) AS sme_count,
    ROUND(AVG(lag_days_vs_gazette), 1) AS avg_lag_days,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY lag_days_vs_gazette) AS median_lag_days,
    MIN(lag_days_vs_gazette) AS min_lag_days,
    MAX(lag_days_vs_gazette) AS max_lag_days
FROM m1_sme_awareness_responses
WHERE is_aware = TRUE AND lag_days_vs_gazette IS NOT NULL
GROUP BY first_channel
ORDER BY median_lag_days ASC;
```

---

## A4. Real-World Example — Worked End to End

Let's use your "multi-pin power adapter" hypothetical to show how every table fills out.

### Scenario
Imagine SLSI publishes Extraordinary Gazette **2486/22** on **2026-04-15** mandating that all multi-pin universal power adapters sold in Sri Lanka must carry SLSI safety certification, effective **2026-08-01**. Penalty: fine up to LKR 500,000 or imprisonment up to 6 months under the Consumer Affairs Authority Act.

### Database population

**`m1_regulations` row:**
```json
{
  "regulation_short_code": "SLSI_ADAPTER_2026_2486_22",
  "document_type": "extraordinary_gazette",
  "document_number": "2486/22",
  "title_en": "Mandatory SLSI Safety Certification for Multi-Pin Universal Power Adapters",
  "principal_act_amended": "Consumer Affairs Authority Act, No. 9 of 2003",
  "gazette_published_date": "2026-04-15",
  "effective_date": "2026-08-01",
  "is_sme_relevant": true,
  "regulatory_domain_id": <SLSI domain ID>,
  "change_category": "new_obligation",
  "severity_level": 4
}
```

**`m1_regulation_sectors`:**
```
[Retail & Wholesale, impact 5]
[Manufacturing, impact 4]   (importers/assemblers)
[IT & Software, impact 3]  (computer/peripheral shops)
```

**`m1_real_world_examples` row:**
```json
{
  "scenario_title": "Multi-pin power adapter sales restriction for electronics shops",
  "scenario_description": "From Aug 1, 2026, mobile phone shops, computer shops, and general electronics retailers cannot sell, display, or import multi-pin universal power adapters that lack SLSI safety certification.",
  "affected_business_type": "Electronics retailers, mobile phone shops, computer accessory shops, hardware shops, importers",
  "sme_required_action": "1) Audit current adapter stock, 2) Identify SLSI-certified vs uncertified, 3) Return/dispose uncertified stock by July 31, 2026, 4) Source only from SLSI-certified suppliers, 5) Display SLSI mark on product/invoice",
  "sme_required_records": "SLSI certification number for each batch, supplier declaration, sales invoice with SLSI reference",
  "typical_violation_pattern": "Continuing to sell legacy stock past Aug 1; sourcing cheaper non-certified imports through informal channels",
  "operational_flow_steps": [
    {"step": 1, "action": "Receive SLSI certificate from supplier with each batch"},
    {"step": 2, "action": "Verify certificate validity on slsi.lk lookup"},
    {"step": 3, "action": "Tag stock with SLSI batch reference"},
    {"step": 4, "action": "Issue sales invoice mentioning SLSI mark"},
    {"step": 5, "action": "Retain certificate for 3 years for inspection"}
  ]
}
```

**`m1_regulation_penalties` row:**
```json
{
  "violation_type": "Selling/displaying non-SLSI-certified multi-pin adapter",
  "penalty_type": "both",
  "penalty_min_lkr": 50000,
  "penalty_max_lkr": 500000,
  "imprisonment_max_months": 6,
  "additional_consequences": "Stock seizure; possible business name publication on CAA defaulter list",
  "legal_basis_section": "Section 30(1) of Consumer Affairs Authority Act"
}
```

**`m1_court_cases` row (hypothetical example after enforcement):**
```json
{
  "case_number": "MC/COL/4523/2026",
  "court_name": "Magistrate Court Maligakanda",
  "case_filed_date": "2026-09-12",
  "judgment_date": "2026-11-04",
  "defendant_business_type": "Mobile phone accessory shop, Pettah",
  "defendant_sector_id": <Retail>,
  "defendant_size": "micro",
  "violation_summary": "Sold 47 units of non-SLSI-certified multi-pin adapters between Aug 5 - Sep 8, 2026",
  "judgment_outcome": "convicted",
  "fine_imposed_lkr": 75000,
  "additional_orders": "Stock confiscation; warning notice issued",
  "summary_for_smes": "A small phone accessory shop in Pettah was fined LKR 75,000 for selling 47 uncertified adapters. The shop owner stated they were unaware of the regulation. The court did not accept ignorance as a defense."
}
```

**`m1_propagation_events` rows (the lag tracking):**
```
event_type                     | timestamp           | lag_days_from_gazette
--------------------------------+---------------------+----------------------
gazette_published              | 2026-04-15          |    0
official_portal_notice (SLSI)  | 2026-04-22          |   +7
news_first_coverage (Daily FT) | 2026-05-08          |  +23
industry_body_alert (Chamber)  | 2026-05-15          |  +30
social_media_first_mention     | 2026-05-18          |  +33
sme_first_aware (avg)          | 2026-06-12          |  +58
```

**`m1_sme_awareness_responses` rows (from your platform's survey):**
Each shop owner who fills out the survey contributes one row per regulation. If we ask 100 electronics shop owners about regulation 2486/22, we get 100 rows. Then we calculate: average awareness lag = 58 days; median = 45 days; 23% of SMEs were *still unaware* at time of survey (after the effective date had already passed).

---

## A5. Module 1 Survey Instrument — The "When Did You Find Out?" Survey

This survey is presented to SME owners through your Next.js platform. It's ideally administered AFTER they have already filled out Module 2/3 surveys (so you have their profile linked).

### A5.1 Survey Flow

```
Step 1: "We're going to show you 5-7 recent regulatory changes that may affect your business.
        For each one, tell us if you knew about it, when, and how you found out."

Step 2: For each regulation (auto-selected based on respondent's sector):
        - Display: title, plain-language summary, effective date, real-world example
        - Ask the awareness questions (below)

Step 3: Open question: "Were there any other recent regulations you wish you had known about
                       earlier? Tell us about them."
```

### A5.2 Per-Regulation Question Block

For each regulation shown, ask:

**Q1.** Were you aware of this regulation before today? *(Yes / No / Not sure)*

**Q2.** *(If Yes)* When did you first hear about it?
- Exact date: ___________
- "About a week before today" / "About a month ago" / "Several months ago" / "Don't remember"

**Q3.** How did you first hear about it? *(Single select — show channels)*
- Official government website (IRD/EPF/SLSI/eROC)
- A letter from a government department
- My accountant or auditor
- A tax consultant
- An industry body or trade association
- Chamber of Commerce
- Newspaper (Sinhala/Tamil/English)
- TV news
- Radio
- Online news website
- Facebook post
- WhatsApp group / forwarded message
- LinkedIn
- Twitter / X
- YouTube video
- A colleague or business friend
- A customer mentioned it
- A supplier mentioned it
- Other: ___________

**Q4.** On a scale of 1–5, how well do you understand what this regulation requires you to do? *(1 = no understanding, 5 = complete understanding)*

**Q5.** Do you know the date this regulation takes effect? *(Yes — please tell us / No)*

**Q6.** Do you know what specific actions your business must take to comply? *(Yes / No / Partially)*

**Q7.** Have you taken any action yet? *(Yes / No / In progress)*
- *(If Yes)* Briefly describe what you've done: ___________

**Q8.** *(Optional)* If you found out late, what would have helped you find out sooner?
*(Multi-select)*
- A direct SMS/email from the government
- Better notification from my accountant
- A central app/website that shows all regulations
- More media coverage
- A WhatsApp alert from my Chamber of Commerce
- Other: ___________

### A5.3 Sector-Tailored Regulation Selection Logic

When a respondent loads the survey, the system selects regulations to ask about based on their `business_profile.sector_id` from the M2/M3 profile. Pseudocode:

```
relevant_regulations = SELECT r.* FROM m1_regulations r
  JOIN m1_regulation_sectors rs ON rs.regulation_id = r.regulation_id
  WHERE rs.sector_id = <respondent.sector_id>
    AND r.gazette_published_date BETWEEN (today - 24 months) AND (today - 14 days)
    AND r.is_sme_relevant = TRUE
    AND r.severity_level >= 3
  ORDER BY r.gazette_published_date DESC, rs.impact_level DESC
  LIMIT 7;

# Plus 2 universal questions everyone gets (e.g. VAT threshold change)
universal = SELECT r.* FROM m1_regulations r
  WHERE r.is_universal_change = TRUE
  ORDER BY published_date DESC LIMIT 2;

display_to_user(universal + relevant_regulations);
```

### A5.4 Real-World Example Questions (for the multi-pin adapter scenario)

If a respondent is in the **Retail & Wholesale** or **IT & Software** sectors, they get this regulation in their survey. The platform shows them:

> **Regulation:** Mandatory SLSI Safety Certification for Multi-Pin Universal Power Adapters
> **Published:** April 15, 2026 (Extraordinary Gazette 2486/22)
> **Effective:** August 1, 2026
>
> **What this means:** From August 2026, electronics shops, mobile phone shops, and computer accessory retailers cannot sell or display multi-pin universal power adapters unless they carry SLSI safety certification.
>
> **Penalty if violated:** Fine LKR 50,000–500,000 and/or imprisonment up to 6 months.
>
> **A real case:** A small phone accessory shop in Pettah was fined LKR 75,000 in November 2026 for selling 47 uncertified adapters.

Then ask Q1–Q8 above. The respondent's answers go into `m1_sme_awareness_responses`.

---

## A6. Sample Screenshot Mockup — Module 1 Survey Screen

Below is an ASCII wireframe showing what the Next.js page looks like for one regulation question:

```
┌──────────────────────────────────────────────────────────────────────┐
│  SME Regulatory Intelligence Platform                    [Profile] │
│  Awareness Survey   |   Question 3 of 7                     [Save] │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  📋 REGULATION                                                       │
│  ─────────────────────────────────────────────────                   │
│  Mandatory SLSI Safety Certification for                             │
│  Multi-Pin Universal Power Adapters                                  │
│                                                                      │
│  Published: 15 April 2026  (Extraordinary Gazette 2486/22)          │
│  Effective: 1 August 2026                                            │
│  Sector: Electronics retailers, mobile shops, computer shops         │
│                                                                      │
│  📌 What this means for your business:                               │
│  From Aug 2026, you cannot sell or display multi-pin                 │
│  power adapters without SLSI safety certification.                   │
│  Existing stock must be cleared or returned by July 31.              │
│                                                                      │
│  ⚠️ Penalty: LKR 50,000–500,000 fine and/or 6 months prison.        │
│                                                                      │
│  📖 Real case: A Pettah phone shop was fined LKR 75,000              │
│  for selling 47 uncertified adapters in late 2026.                  │
│                                                                      │
│  ─────────────────────────────────────────────────                   │
│                                                                      │
│  ❓ Were you aware of this regulation before today?                  │
│      ( • ) Yes      (   ) No      (   ) Not sure                    │
│                                                                      │
│  ❓ When did you first hear about it?                                │
│      [📅  About 3 weeks ago     ▼ ]                                 │
│                                                                      │
│  ❓ How did you first hear about it?                                 │
│      [▼ WhatsApp group / forwarded message            ]              │
│                                                                      │
│  ❓ How well do you understand what you need to do?                  │
│      ◯─◯─●─◯─◯   (3/5 — somewhat understand)                       │
│                                                                      │
│  ❓ Do you know the effective date?              ☑ Yes    ☐ No       │
│  ❓ Do you know what action to take?             ☐ Yes    ☑ No       │
│  ❓ Have you taken any action yet?               ☐ Yes    ☑ No       │
│                                                                      │
│  ─────────────────────────────────────────────────                   │
│                                                                      │
│  [  ← Back  ]                              [  Next →  ]              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

# PART B — MODULE 4: REGULATORY MISINFORMATION SPREAD

## B1. The Problem (Restated)

Per your handwritten notes, the full process is:

> **Step 1**: Collect data → **Step 2**: Clean data → **Step 3**: Label data → **Step 4**: Analyze data (Evaluation) → **Step 5**: Build the tool

The labeled dataset is the **biggest novel contribution**. The pipeline is:

```
Raw Posts (from Facebook, Twitter, Reddit, WhatsApp, FactCheck.lk)
    ↓
Clean (remove duplicates, irrelevant posts, translate Sinhala/Tamil, remove PII, standardize)
    ↓
Label (read each post, tag as True / False / Misleading / Partially-True via Label Studio)
    ↓
Analyze (compare engagement of true vs false; find linguistic patterns)
    ↓
Build (claim verification tool — paste a claim, get verdict)
```

---

## B2. Data Source Catalogue — Module 4

| Source ID | Platform | What We Collect | Method | Languages |
|---|---|---|---|---|
| M4_FB_GROUPS | Facebook (Public Groups) | Posts about tax, EPF, business regulations | Facebook Graph API + manual collection | SI/TA/EN |
| M4_FB_PAGES | Facebook (Public Pages) | Posts from accounting firms, "tax advice" pages | Facebook Graph API | SI/TA/EN |
| M4_TWITTER | Twitter/X | Tweets with keywords (#SriLankaTax, #VAT, etc) | Twitter Academic API | SI/TA/EN |
| M4_REDDIT | Reddit (r/srilanka, r/AskSriLanka) | Threads about taxes, business compliance | Reddit API (PRAW) | EN (mostly) |
| M4_WHATSAPP | WhatsApp forwards | Anonymized forwards SMEs share with us | Survey upload | SI/TA/EN |
| M4_FACTCHECK | FactCheck.lk | Pre-labeled claims/debunks | Web scraping | EN |
| M4_YOUTUBE | YouTube comments | Comments on tax/business explainer videos | YouTube Data API | SI/TA/EN |
| M4_TIKTOK | TikTok (manual) | Viral "tax advice" clips | Manual collection (no API) | SI/TA/EN |

---

## B3. PostgreSQL Schema for Module 4 — Mirroring Your 5-Step Process

### B3.1 Stage 1: Raw Data Table (matches your "Raw Data" hand-drawn table: Post Text, Source, Likes, Shares, Language)

```sql
-- =====================================================================
-- MODULE 4 — MISINFORMATION SPREAD
-- Schema mirrors the 5-step pipeline from your notebook
-- =====================================================================

-- ---------------------------------------------------------------
-- B3.1 STEP 1: RAW DATA — gathered from all platforms
-- ---------------------------------------------------------------
CREATE TABLE m4_raw_posts (
    raw_post_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- Source identification
    platform                VARCHAR(30) NOT NULL CHECK (platform IN
                                ('facebook_group','facebook_page','twitter','reddit',
                                 'whatsapp_forward','factcheck_lk','youtube_comment',
                                 'tiktok','linkedin','blog','other')),
    platform_post_id        VARCHAR(200),  -- the platform's native ID
    source_url              TEXT,
    source_account_handle   VARCHAR(200),  -- @user, group name, page name
    source_account_followers INTEGER,
    source_account_verified BOOLEAN,
    -- Content
    post_text               TEXT NOT NULL,    -- raw text as collected
    post_text_length        INTEGER,
    contains_image          BOOLEAN DEFAULT FALSE,
    image_urls              TEXT[],
    contains_video          BOOLEAN DEFAULT FALSE,
    contains_link           BOOLEAN DEFAULT FALSE,
    external_links          TEXT[],
    -- Engagement metrics (your notebook: Likes, Shares)
    likes_count             INTEGER DEFAULT 0,
    shares_count            INTEGER DEFAULT 0,
    comments_count          INTEGER DEFAULT 0,
    views_count             INTEGER,  -- where available
    reactions_breakdown     JSONB,    -- {"haha": 12, "angry": 5, ...} for FB
    -- Language (your notebook: Language)
    language_detected       VARCHAR(10) CHECK (language_detected IN ('si','ta','en','mixed','unknown')),
    language_confidence     NUMERIC(3,2),
    -- Temporal (your notebook: Date)
    posted_at               TIMESTAMPTZ,
    collected_at            TIMESTAMPTZ DEFAULT NOW(),
    -- Quality flags
    is_duplicate            BOOLEAN DEFAULT FALSE,
    duplicate_of            UUID REFERENCES m4_raw_posts(raw_post_id),
    is_relevant             BOOLEAN,  -- NULL until reviewed
    relevance_check_method  VARCHAR(50),
    -- Audit
    collection_method       VARCHAR(50),  -- 'graph_api','scrapy','manual','survey_upload'
    collection_query        TEXT,         -- what keyword/query found this
    collected_by            VARCHAR(100), -- user or system identifier
    raw_metadata            JSONB         -- everything else from API
);

CREATE INDEX idx_m4_raw_platform ON m4_raw_posts(platform);
CREATE INDEX idx_m4_raw_lang ON m4_raw_posts(language_detected);
CREATE INDEX idx_m4_raw_posted ON m4_raw_posts(posted_at);
CREATE INDEX idx_m4_raw_relevant ON m4_raw_posts(is_relevant) WHERE is_relevant = TRUE;
```

### B3.2 Stage 2: Cleaned Data Table (matches your "Step 2" table: Post Text, Source, Likes, Shares, Language, Translated Text)

```sql
-- ---------------------------------------------------------------
-- B3.2 STEP 2: CLEANED DATA — deduplicated, translated, PII-stripped
-- ---------------------------------------------------------------
CREATE TABLE m4_cleaned_posts (
    cleaned_post_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    raw_post_id             UUID NOT NULL UNIQUE REFERENCES m4_raw_posts(raw_post_id),
    -- Cleaned content
    post_text_cleaned       TEXT NOT NULL,    -- PII removed, normalized
    post_text_translated_en TEXT,             -- English version (if originally SI/TA)
    translation_method      VARCHAR(50),      -- 'google_translate','manual','llm'
    translation_quality     VARCHAR(20),      -- 'verified','auto','low_confidence'
    -- Standardized engagement (matches notebook)
    likes_normalized        INTEGER,          -- per-1000-followers, for cross-platform comparison
    shares_normalized       INTEGER,
    engagement_score        NUMERIC(8,2),    -- composite engagement metric
    -- Topic classification (your notebook implicitly references this with "Topic")
    primary_topic           VARCHAR(50) CHECK (primary_topic IN
                                ('vat','income_tax','epf','etf','sscl','wht',
                                 'company_registration','customs','licensing',
                                 'fines_penalties','tax_filing','exemptions','general','other')),
    topic_confidence        NUMERIC(3,2),
    secondary_topics        VARCHAR(50)[],
    -- Sector relevance
    relevant_sectors        INTEGER[],        -- FK array to sectors
    -- Cleaning audit
    pii_removed             BOOLEAN DEFAULT FALSE,
    pii_removed_types       TEXT[],          -- ['phone','email','nic']
    spam_score              NUMERIC(3,2),
    cleaning_notes          TEXT,
    cleaned_at              TIMESTAMPTZ DEFAULT NOW(),
    cleaned_by              VARCHAR(100)
);

CREATE INDEX idx_m4_clean_topic ON m4_cleaned_posts(primary_topic);
```

### B3.3 Stage 3: Labeled Data Table (matches your "Step 3" table: Post Text, Source, Likes, Shares, Label)

```sql
-- ---------------------------------------------------------------
-- B3.3 STEP 3: LABELED DATA — your biggest novel contribution
-- ---------------------------------------------------------------
CREATE TABLE m4_labeled_posts (
    label_id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cleaned_post_id         UUID NOT NULL REFERENCES m4_cleaned_posts(cleaned_post_id),
    -- The label (your notebook's True/False)
    veracity_label          VARCHAR(30) NOT NULL CHECK (veracity_label IN
                                ('true',                -- factually correct
                                 'mostly_true',         -- minor inaccuracies
                                 'partially_true',     -- mix of correct and incorrect
                                 'misleading',          -- technically true but creates wrong impression
                                 'mostly_false',        -- minor truths within larger falsehood
                                 'false',               -- factually incorrect
                                 'unverifiable',       -- cannot be verified against ground truth
                                 'opinion',            -- not a factual claim
                                 'outdated')),         -- was true, no longer applies
    label_confidence        SMALLINT CHECK (label_confidence BETWEEN 1 AND 5),
    -- The factual claim being judged
    extracted_claim         TEXT,             -- e.g. "VAT rate is 15%"
    correct_information     TEXT,             -- e.g. "VAT rate is 18% as of Jan 2024"
    ground_truth_source     TEXT,             -- "VAT Amendment Act, Sec 2"
    ground_truth_url        TEXT,
    -- Misleading mechanics (for the linguistic feature analysis)
    contains_outdated_info  BOOLEAN DEFAULT FALSE,
    contains_wrong_numbers  BOOLEAN DEFAULT FALSE,
    contains_wrong_dates    BOOLEAN DEFAULT FALSE,
    contains_fake_authority BOOLEAN DEFAULT FALSE,    -- false attribution to IRD/Min
    contains_fear_appeal    BOOLEAN DEFAULT FALSE,
    contains_urgency_appeal BOOLEAN DEFAULT FALSE,
    -- Annotation audit
    annotated_by            VARCHAR(100) NOT NULL,    -- annotator ID
    annotation_round        SMALLINT DEFAULT 1,
    annotated_at            TIMESTAMPTZ DEFAULT NOW(),
    annotator_notes         TEXT,
    label_studio_task_id    VARCHAR(100),
    -- Multi-annotator agreement
    is_consensus_label      BOOLEAN DEFAULT FALSE,
    cohens_kappa_score      NUMERIC(4,3),
    UNIQUE (cleaned_post_id, annotator_id, annotation_round)
);

CREATE INDEX idx_m4_label_veracity ON m4_labeled_posts(veracity_label);

-- Inter-annotator disagreements requiring resolution
CREATE TABLE m4_label_disagreements (
    disagreement_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cleaned_post_id         UUID NOT NULL REFERENCES m4_cleaned_posts(cleaned_post_id),
    annotator_1_label       VARCHAR(30),
    annotator_2_label       VARCHAR(30),
    resolution_label        VARCHAR(30),
    resolved_by             VARCHAR(100),
    resolved_at             TIMESTAMPTZ,
    resolution_reasoning    TEXT
);
```

### B3.4 Stage 4: Analysis & Spread Tracking

```sql
-- ---------------------------------------------------------------
-- B3.4 STEP 4: ANALYSIS — spread patterns, virality
-- ---------------------------------------------------------------
CREATE TABLE m4_spread_events (
    spread_id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cleaned_post_id         UUID NOT NULL REFERENCES m4_cleaned_posts(cleaned_post_id),
    event_type              VARCHAR(30) CHECK (event_type IN
                                ('share','retweet','repost','forward','quote','reply')),
    event_platform          VARCHAR(30),
    event_account_handle    VARCHAR(200),
    event_timestamp         TIMESTAMPTZ,
    hours_since_original    NUMERIC(8,2),
    is_cross_platform       BOOLEAN DEFAULT FALSE
);

-- Linguistic features extracted for virality prediction
CREATE TABLE m4_linguistic_features (
    cleaned_post_id         UUID PRIMARY KEY REFERENCES m4_cleaned_posts(cleaned_post_id),
    word_count              INTEGER,
    sentence_count          INTEGER,
    has_question_mark       BOOLEAN,
    has_exclamation         BOOLEAN,
    exclamation_count       INTEGER,
    has_all_caps_words      BOOLEAN,
    all_caps_word_count     INTEGER,
    has_emoji               BOOLEAN,
    emoji_count             INTEGER,
    sentiment_score         NUMERIC(4,3),    -- -1 to 1
    emotion_anger           NUMERIC(3,2),
    emotion_fear            NUMERIC(3,2),
    emotion_surprise        NUMERIC(3,2),
    readability_score       NUMERIC(4,2),
    has_numbers             BOOLEAN,
    has_currency_amounts    BOOLEAN,
    has_dates               BOOLEAN,
    has_percentages         BOOLEAN,
    contains_named_entities TEXT[],          -- ['IRD','EPF','Minister of Finance']
    extracted_at            TIMESTAMPTZ DEFAULT NOW()
);
```

### B3.5 Stage 5: Verification Tool Logs (for the "Build the tool" output)

```sql
-- ---------------------------------------------------------------
-- B3.5 STEP 5: VERIFICATION TOOL — claim check requests from SMEs
-- ---------------------------------------------------------------
CREATE TABLE m4_claim_verifications (
    verification_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    respondent_id           UUID REFERENCES respondents(respondent_id),  -- nullable for anonymous
    submitted_claim         TEXT NOT NULL,
    submitted_at            TIMESTAMPTZ DEFAULT NOW(),
    submitted_language      VARCHAR(10),
    received_via_channel    VARCHAR(50),    -- where the SME originally got the claim
    -- The system's verdict
    verdict_label           VARCHAR(30),
    verdict_confidence      NUMERIC(3,2),
    verdict_explanation     TEXT,
    matched_ground_truth_ids INTEGER[],
    matched_labeled_post_ids UUID[],         -- similar previously-labeled posts
    -- Method used
    method                  VARCHAR(50),     -- 'rag','xlm_r_classifier','keyword_match','manual'
    processing_time_ms      INTEGER,
    -- Feedback
    user_found_helpful      BOOLEAN,
    user_feedback           TEXT
);

CREATE INDEX idx_m4_verify_submitted ON m4_claim_verifications(submitted_at);

-- ---------------------------------------------------------------
-- B3.6 ANALYTICAL VIEWS for Module 4
-- ---------------------------------------------------------------

-- View: misinformation prevalence by topic
CREATE OR REPLACE VIEW v_m4_misinformation_by_topic AS
SELECT
    cp.primary_topic,
    COUNT(*) AS total_posts,
    SUM(CASE WHEN lp.veracity_label IN ('false','mostly_false','misleading') THEN 1 ELSE 0 END) AS misinfo_count,
    ROUND(100.0 * SUM(CASE WHEN lp.veracity_label IN ('false','mostly_false','misleading') THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS misinfo_pct,
    ROUND(AVG(cp.engagement_score), 2) AS avg_engagement
FROM m4_cleaned_posts cp
JOIN m4_labeled_posts lp ON lp.cleaned_post_id = cp.cleaned_post_id
WHERE lp.is_consensus_label = TRUE
GROUP BY cp.primary_topic
ORDER BY misinfo_pct DESC;

-- View: virality of true vs false content (the headline finding)
CREATE OR REPLACE VIEW v_m4_truth_vs_falsehood_spread AS
SELECT
    CASE
        WHEN lp.veracity_label IN ('true','mostly_true') THEN 'accurate'
        WHEN lp.veracity_label IN ('false','mostly_false','misleading') THEN 'inaccurate'
        ELSE 'ambiguous'
    END AS content_type,
    COUNT(*) AS post_count,
    ROUND(AVG(cp.likes_normalized), 2) AS avg_likes_per_1k_followers,
    ROUND(AVG(cp.shares_normalized), 2) AS avg_shares_per_1k_followers,
    ROUND(AVG(cp.engagement_score), 2) AS avg_engagement_score,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cp.engagement_score) AS median_engagement
FROM m4_cleaned_posts cp
JOIN m4_labeled_posts lp ON lp.cleaned_post_id = cp.cleaned_post_id
WHERE lp.is_consensus_label = TRUE
GROUP BY content_type;
```

---

## B4. Real-World Examples — Module 4 With Actual Sample Data

### Example 1: A FALSE post collected from a Facebook group

**Raw Data captured:**
```json
{
  "platform": "facebook_group",
  "source_account_handle": "Sri Lanka SME Owners Forum",
  "source_account_followers": 24500,
  "post_text": "මුදල් අමාත්‍යාංශය නවතම නිවේදනය - VAT අනුපාතය 15% දක්වා අඩු කරලා. අද ඉඳන් ක්‍රියාත්මක වෙනවා. Share කරන්න!!!",
  "likes_count": 1247,
  "shares_count": 892,
  "comments_count": 156,
  "language_detected": "si",
  "posted_at": "2026-04-20 14:23:00"
}
```

**Cleaned Data:**
```json
{
  "post_text_translated_en": "Ministry of Finance latest announcement - VAT rate reduced to 15%. Effective from today. Please share!!!",
  "primary_topic": "vat",
  "engagement_score": 87.4
}
```

**Labeled Data:**
```json
{
  "veracity_label": "false",
  "extracted_claim": "VAT rate has been reduced to 15% effective immediately",
  "correct_information": "VAT rate is 18% (effective 1 January 2024). VAT rate on financial services will increase to 20.5% from 1 July 2026 per VAT Amendment Bill 31/2026.",
  "ground_truth_source": "VAT Amendment Act sources, Bill 31/2026",
  "contains_wrong_numbers": true,
  "contains_fake_authority": true,
  "contains_urgency_appeal": true,
  "label_confidence": 5
}
```

**Analysis output:** This false post got 1,247 likes and 892 shares within hours. The same week, an accurate IRD-published correction got 23 likes and 4 shares. This is your **headline finding**: misinformation outperforms accurate content by orders of magnitude.

### Example 2: A MISLEADING post about EPF

```json
{
  "post_text": "If you don't pay your EPF for 3 months you go to jail!",
  "veracity_label": "misleading",
  "extracted_claim": "Non-payment of EPF for 3 months results in imprisonment",
  "correct_information": "Non-payment of EPF results in surcharges and may eventually lead to legal action. Imprisonment is theoretically possible under EPF Act for willful evasion but requires court order; not automatic after 3 months.",
  "contains_fear_appeal": true,
  "contains_wrong_numbers": true
}
```

### Example 3: An OUTDATED post (was true, no longer accurate)

```json
{
  "post_text": "VAT registration is only required if your turnover exceeds 80 million per year",
  "veracity_label": "outdated",
  "extracted_claim": "VAT registration threshold is LKR 80 million",
  "correct_information": "VAT registration threshold reduced to LKR 36 million annually (LKR 9M quarterly) effective from July 1, 2026. The 80M figure was outdated even before the latest change.",
  "contains_outdated_info": true
}
```

---

## B5. Sample Screenshot Mockups — Module 4

### B5.1 Stage 1 Mockup: Raw Data Collection View (matches your Image 1)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              Module 4 — Regulatory Misinformation Spread                            │
│                                       STAGE 1: RAW DATA INGEST                                       │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ # │ Post Text                                          │ Source             │Likes│Shares│Lang │Date │
├───┼────────────────────────────────────────────────────┼────────────────────┼─────┼──────┼─────┼─────┤
│ 1 │ මුදල් අමාත්‍යාංශය - VAT 15% දක්වා අඩු කරලා...    │ FB: SL SME Forum   │1247 │ 892  │ SI  │04-20│
│ 2 │ EPF පැය 24 තුළ ගෙවන්න ඕනේ අලුත් නීතිය එක්ක      │ WhatsApp Forward   │ N/A │ N/A  │ SI  │04-21│
│ 3 │ New tax rule: every business must pay 25% advance  │ Twitter @lkbiznews │ 89  │ 234  │ EN  │04-22│
│ 4 │ வரி 18% ஆக உயர்த்தப்பட்டுள்ளது, ஜூலை முதல்   │ FB: Tamil Business │ 567 │ 312  │ TA  │04-23│
│ 5 │ EPF & ETF combined = 23% of salary - mandatory     │ Reddit r/srilanka  │ 145 │  18  │ EN  │04-23│
│ 6 │ SVAT scheme is being abolished, last day Sep 30    │ FB: Tax Tips Page  │ 423 │ 201  │ EN  │04-24│
│ 7 │ Importing under 250 USD now needs special permit   │ Twitter @customs_lk│  67 │ 145  │ EN  │04-24│
└───┴────────────────────────────────────────────────────┴────────────────────┴─────┴──────┴─────┴─────┘
                                                                              [+ Collect More] [Export]
```

### B5.2 Stage 2 Mockup: Cleaned Data View (matches your Image 2 lower table)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                          STAGE 2: CLEANED & TRANSLATED DATA                                                │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ # │ Post Text (Original)                  │Source           │Likes│Shares│Lang │ Translated Text (English)                  │
├───┼───────────────────────────────────────┼─────────────────┼─────┼──────┼─────┼────────────────────────────────────────────┤
│ 1 │ මුදල් අමාත්‍යාංශය - VAT 15%...        │FB: SL SME Forum │1247 │ 892  │ SI  │ Ministry of Finance - VAT reduced to 15%   │
│ 4 │ வரி 18% ஆக உயர்த்தப்பட்டுள்ளது      │FB: Tamil Biz    │ 567 │ 312  │ TA  │ Tax has been raised to 18%, from July      │
│ 5 │ EPF & ETF combined = 23%              │Reddit r/srilanka│ 145 │  18  │ EN  │ EPF & ETF combined = 23% of salary         │
│ 6 │ SVAT scheme is being abolished        │FB: Tax Tips     │ 423 │ 201  │ EN  │ SVAT scheme is being abolished, Sep 30 last│
└───┴───────────────────────────────────────┴─────────────────┴─────┴──────┴─────┴────────────────────────────────────────────┘
                                                                                  [Show Removed Duplicates] [Re-translate]
```

### B5.3 Stage 3 Mockup: Labeling Interface (matches your Image 3)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                STAGE 3: LABELING (Label Studio)                                       │
│                                  Annotator: ahamed_t  |  Task 247 of 1,200                            │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Post Text (cleaned + translated):                                                                     │
│ ─────────────────────────────────────────────────────────────────────────                             │
│ "Ministry of Finance - VAT reduced to 15%. Effective from today. Please share!!!"                    │
│                                                                                                       │
│ Source: FB: Sri Lanka SME Owners Forum   Engagement: 1,247 likes / 892 shares                        │
│ Topic: VAT                                                                                            │
│ ─────────────────────────────────────────────────────────────────────────                             │
│                                                                                                       │
│ ❓ Veracity Label:                                                                                    │
│   ◯ True              ◯ Mostly True       ◯ Partially True    ◯ Misleading                          │
│   ◯ Mostly False      ● False             ◯ Outdated          ◯ Unverifiable    ◯ Opinion           │
│                                                                                                       │
│ ❓ Extracted claim:                                                                                   │
│   [VAT rate has been reduced to 15% effective immediately                       ]                    │
│                                                                                                       │
│ ❓ Ground truth (correct info):                                                                       │
│   [VAT rate is 18% (since Jan 2024). Bill 31/2026 raises financial services VAT to 20.5%.]           │
│                                                                                                       │
│ ❓ Misleading mechanics (multi-select):                                                               │
│   ☑ Wrong numbers      ☑ Fake authority claim   ☐ Wrong dates    ☑ Urgency appeal                   │
│   ☐ Fear appeal        ☐ Outdated information   ☐ Cherry-picked facts                                │
│                                                                                                       │
│ ❓ Confidence in your label (1-5):    ◯─◯─◯─◯─●   (5 - very confident)                              │
│                                                                                                       │
│ Annotator notes (optional):                                                                           │
│ [Same false claim has been recirculating for months. Always spikes when budget changes.]              │
│                                                                                                       │
│ [Skip Task]                                                            [Save & Next →]               │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## B6. The Pipeline Flow Diagram (matches your Image 2 top diagram)

```
       ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐
       │ Step 1  │      │ Step 2  │      │ Step 3  │      │ Step 4  │      │ Step 5  │
       │ Collect │ ──>  │  Clean  │ ──>  │  Label  │ ──>  │ Analyze │ ──>  │  Build  │
       │  data   │      │  data   │      │  data   │      │  data   │      │  tool   │
       └────┬────┘      └────┬────┘      └────┬────┘      └────┬────┘      └────┬────┘
            │                │                │                │                │
            ▼                ▼                ▼                ▼                ▼
       m4_raw_posts   m4_cleaned_posts  m4_labeled_posts  m4_spread_events  m4_claim_
                                                          m4_linguistic_    verifications
                                                          features

       Sources used:                  Tools/Methods:                Output:
       - Facebook Graph API           - Translation (Google API)    - Annotated SL tax
       - Twitter Academic API         - PII removal (regex)         - misinformation
       - Reddit PRAW                  - Topic classification (XLM-R)  corpus (NOVEL)
       - WhatsApp survey upload       - Label Studio annotation     - Misinfo prevalence
       - FactCheck.lk scraper         - Cohen's Kappa agreement     - Virality predictor
       - YouTube comments             - SHAP analysis               - Public claim-check
                                                                      tool
```

---

# PART C — INTEGRATION NOTES FOR YOUR NEXT.JS PLATFORM

## C1. Application Modules to Build

| Page / API Route | Purpose | Module | Tables Touched |
|---|---|---|---|
| `/admin/regulations` | View/edit regulations scraped from documents.gov.lk | M1 | m1_regulations, m1_regulation_changes |
| `/admin/scrape` | Trigger scraping jobs, view scrape logs | M1 | m1_sources |
| `/admin/examples` | Author real-world example narratives | M1 | m1_real_world_examples |
| `/survey/awareness` | SME-facing survey (Module 1 awareness) | M1 | m1_sme_awareness_responses |
| `/survey/knowledge` | SME-facing survey (Module 2 knowledge test) | M2 | m2_responses |
| `/survey/behaviour` | SME-facing survey (Module 3 behaviour) | M3 | m3_behavioural_signals |
| `/admin/posts/raw` | View collected social posts | M4 | m4_raw_posts |
| `/admin/posts/clean` | Cleaning queue / dedup interface | M4 | m4_cleaned_posts |
| `/admin/posts/label` | Label Studio embed or native labeling UI | M4 | m4_labeled_posts |
| `/check-claim` | Public claim verification tool | M4 | m4_claim_verifications |
| `/dashboard/lag` | Module 1 findings: lag distribution charts | M1 | views |
| `/dashboard/misinformation` | Module 4 findings: prevalence/spread charts | M4 | views |
| `/dashboard/risk` | Module 3 findings: SME risk profiles | M3 | views |

## C2. Key API Routes to Implement

```
POST   /api/m1/regulations          Create regulation from scraper
GET    /api/m1/regulations/:id      Get regulation detail with changes/penalties/cases
POST   /api/m1/awareness            Submit awareness survey response (one regulation)
GET    /api/m1/lag-summary          Aggregate lag stats for dashboard
GET    /api/m1/regulations/for-sector/:sectorId   Get relevant regulations for SME

POST   /api/m4/posts/raw            Bulk insert raw posts from scraper
POST   /api/m4/posts/:id/clean      Trigger cleaning pipeline for a post
POST   /api/m4/posts/:id/label      Submit annotation
POST   /api/m4/verify-claim         Public endpoint: submit claim, get verdict
GET    /api/m4/misinformation-stats Aggregate stats for dashboard

POST   /api/respondents             Create respondent
POST   /api/respondents/:id/profile Submit business profile
```

## C3. Critical Implementation Reminders

1. **Always verify regulation ground truth with a CA before publishing on the platform.** Mark `expert_verified` field and never display unverified content publicly.

2. **Preserve original-language data forever.** Never overwrite the raw post text. Translation goes in a separate column.

3. **PII removal is non-negotiable** before any post goes to the labeling stage. Build a pre-processor that strips phone numbers, NIC numbers, email addresses, and personal names before annotators see the post.

4. **Inter-annotator agreement matters.** Have at least 2 annotators label every post in the early phase. Compute Cohen's Kappa; aim for ≥ 0.7 before scaling up.

5. **Module 1 surveys must show SMEs the regulation BEFORE asking if they knew about it.** This may seem to bias the answer, but the question is about *prior* awareness — the display is needed so they can identify which regulation you mean. Frame the question explicitly: "Were you aware of this regulation BEFORE we just showed it to you?"

6. **For Module 4, save Facebook/Twitter API responses verbatim in `raw_metadata` JSONB.** Platforms change their API output frequently; you want the original captured for reproducibility.

7. **The "is_consensus_label" flag in m4_labeled_posts** should only be TRUE after the second annotator agrees OR a senior annotator resolves a disagreement. Only consensus labels go into your published dataset.

8. **Ethics approval needed for both modules.** Module 1 collects SME identification data; Module 4 collects social posts (even public ones may have ethics implications). Get university ethics committee sign-off before launch.

---

## C4. Recommended Next Steps for Your Team

1. **This week:** Get a CA/tax consultant on board to certify ground truth for Modules 1, 2, and 4.
2. **Next week:** Build the documents.gov.lk scraper for Bills/Acts/Gazettes (Module 1 data ingestion).
3. **Two weeks out:** Pilot the Module 1 awareness survey with 5-10 SMEs from your network.
4. **Three weeks out:** Set up Label Studio and label a pilot batch of 100 social posts (Module 4 Stage 3).
5. **One month out:** Get ethics approval, then launch full surveys via Chamber of Commerce/NEDA networks.

---

*End of Module 1 & 4 specification document — version 1.0*

*This document complements the previously delivered:*
- *`sme_survey_schema.sql`* (Modules 2 & 3 PostgreSQL schema)
- *`sme_question_bank.md`* (Modules 2 & 3 question bank)

*Together these four documents specify the complete data architecture for the SME Regulatory Intelligence Platform.*
