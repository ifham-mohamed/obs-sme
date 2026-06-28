# Enigmatrix — Master Reference Document

> **Generated:** 2026-05-20 from Obsidian research vault at `C:\sme\`
> **Vault last updated:** Session 55 / F-193–F-198 (2026-05-22)
> **Primary researcher (Module 1):** Mohamed M.R.I — 215075J

---

## 0. Session 55 architectural updates (2026-05-22)

### Production deployment topology — Railway (LIVE as of 2026-05-22)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Vercel (frontend only)                                                 │
│  enigmatrix-frontend.vercel.app                                         │
│  NEXT_PUBLIC_API_BASE_URL = https://enigmatrix-backend-production       │
│                                  .up.railway.app                        │
└─────────────────────────────────────────────────────────────────────────┘
                                  │ HTTPS (CORS regex-gated)
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Railway project: satisfied-prosperity (production env)                  │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  Service enigmatrix-backend (single container)                  │    │
│  │  start_railway.sh runs:                                         │    │
│  │    1. git config insteadOf injection (uses $GITHUB_TOKEN)       │    │
│  │    2. alembic upgrade head                                      │    │
│  │    3. celery -A app.celery_config:celery_app worker             │    │
│  │       --concurrency=2 (background)                              │    │
│  │    4. celery -A app.celery_config:celery_app beat (background)  │    │
│  │    5. uvicorn app.main:app --port $PORT (foreground)            │    │
│  └────────────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────┐  ┌──────────────────────────────────┐   │
│  │ Redis plugin             │  │ Volume /data/storage (10 GB)     │   │
│  │ CELERY_BROKER_URL =      │  │ STORAGE_LOCAL_PATH ←              │   │
│  │ ${{Redis.REDIS_URL}}     │  │ holds m1/raw/<source_id>/*.pdf    │   │
│  └──────────────────────────┘  └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                  │ DATABASE_URL (sslmode=require)
                  ▼
       External managed Postgres (Aiven, ~20-25 connection budget)
```

**Key facts of record:**

- Repo owner is **`ghubfri-bot`** (NOT `Enigmatrixx` as the original `Railway-Deployment-Plan.md` says). Both `enigmatrix-backend` and `enigmatrix-ml` live under `github.com/ghubfri-bot/`.
- `uv` does **NOT** expand `${ENV_VAR}` inside `tool.uv.sources` URLs. The literal string is passed verbatim and URL-encoded. The correct pattern is git URL-rewrite via `git config --global url."https://x-access-token:${TOKEN}@github.com/".insteadOf "https://github.com/"`, applied at BOTH image build (via `ARG GITHUB_TOKEN`) and container startup (via env var in `start_railway.sh`).
- `CELERY_BROKER_URL = ${{Redis.REDIS_URL}}` is a **Railway variable reference**, not the resolved URL. The literal string `${{Redis.REDIS_URL}}` must be pasted in the service Variables panel; pasting the resolved URL goes stale on Redis restart with a new internal hostname.

### Known security risk (pending #12)

The Stage 0 deploy printed the operator's GitHub PAT in plaintext in the Railway build log and baked it into the container image's `/root/.gitconfig`. Root cause: Docker's `RUN if [ -n "$GITHUB_TOKEN" ]; then git config --global url."https://x-access-token:${GITHUB_TOKEN}@github.com/" ...` expanded the env var into the executed command string, which Railway logged verbatim. Docker emitted its own `SecretsUsedInArgOrEnv` warning. Operator deferred rotation. Remediation sequence: revoke PAT → audit registry for visible image layers → switch Dockerfile to `RUN --mount=type=secret,id=github_token` BuildKit secrets → generate fresh PAT → rotate Railway env var → add pre-commit hook to catch `GITHUB_TOKEN` patterns in commits.

### `ForbiddenError` latent bug in `app/deps.py:44`

Confirmed during Session 55 Stage 4 audit and fixed inline: `require_admin` references `ForbiddenError` but only `UnauthorizedError` was imported. Currently masked in production because every real user with an admin token has `role == "admin"` so the raise branch never fires. A non-admin token hitting any admin endpoint would have crashed with `NameError` instead of returning a clean 403. Fix: added `ForbiddenError` to the `from app.exceptions import ...` line. **Lesson of record:** code paths that only fire in error states need their own test coverage; production traffic alone is not sufficient to surface them.

### `detect_language` lives twice (intentional divergence)

`enigmatrix-backend/app/extraction/pdf_metadata.py` carries a lightweight Unicode-codepoint-ratio implementation (returns `'si'/'ta'/'en'/'unknown'` using ISO 639-1 codes). `enigmatrix-ml/m1/extraction/language_detection.py` carries the fasttext-based canonical implementation (requires the 125 MB `lid.176.bin` model). Both produce the same output codes. The divergence is intentional: the heuristic runs in the Railway dyno without needing the model file; the fasttext path is canonical for the ml worker where the model is already loaded. Documented in the helper module docstring. Reconciliation tracked as follow-up #18.

### Cowork-artifacts `.gitignore` policy (now enforced)

The four `.gitignore` files (backend, frontend, ml, xyz root) now exclude `.claude/`, `.cowork/`, `outputs/`, `local-agent-mode-sessions/`, `MEMORY.md`. These directories hold Cowork session transcripts, agent memory, and scratch outputs that must never leak into the repos. Lesson of record from Session 55: operator explicitly said "do not include the claude cowork in all the commit and push" — this is now enforced at the `.gitignore` layer rather than relying on per-commit discipline.

---

---

## Table of Contents

1. [Project Overview — What Is Enigmatrix?](#1-project-overview)
2. [The Core Problem](#2-the-core-problem)
3. [Research Questions](#3-research-questions)
4. [Four Research Modules](#4-four-research-modules)
5. [Module 1 — Awareness Gap (Full Depth)](#5-module-1-awareness-gap)
   - 5.1 Research Problem & Motivation
   - 5.2 Data Requirements & Schema
   - 5.3 Data Sources Catalogue
   - 5.4 Data Collection Pipeline (Scrapy)
   - 5.5 PDF Extraction Chain
   - 5.6 Preprocessing Pipeline
   - 5.7 Sinhala & Tamil NLP
   - 5.8 Model Architecture (XLM-R + LoRA)
   - 5.9 Training & Evaluation Protocol
   - 5.10 Deployment & Integration
   - 5.11 Full System Architecture
   - 5.12 Annotation Guidelines
   - 5.13 API Reference
   - 5.14 Tracking Workflows
   - 5.15 Folder Structure & Implementation Flow
   - 5.16 Development Roadmap
6. [What Has Been Built — Build Status](#6-build-status)
7. [Session Log — Development History](#7-session-log)
8. [What Is Pending — Roadmap & Open Work](#8-pending-roadmap)
9. [Technology Stack Summary](#9-technology-stack)
10. [Key Technical Concepts & Flows](#10-key-technical-concepts)

---

## 1. Project Overview

**Enigmatrix** is a unified multilingual web research platform for Sri Lankan SMEs (Small and Medium Enterprises) that measures, explains, and mitigates information barriers to regulatory compliance. It is a research artefact built as a monorepo (`xyz/`) with four academic modules, each producing both a working software feature and a measurable research finding.

### Platform Identity

| Attribute | Value |
|---|---|
| **Full name** | Enigmatrix — Regulatory Intelligence Platform |
| **Target users** | Sri Lankan SMEs + academic regulators |
| **Languages** | English · Sinhala · Tamil |
| **Platform type** | Multilingual full-stack web app + ML research pipeline |
| **Deployment target** | Fly.io Singapore region (backend + ML), Vercel (frontend) |
| **Academic context** | Undergraduate research project, University, Feb–Aug 2026 |
| **Individual focus** | M1 = Mohamed M.R.I (215075J) |

### Design Palette (Aurora)

- **Teal primary:** `#1D9E75`
- **Navy accent:** `#1B3A5C`
- Per-module CSS variable identity for the survey wizard accent colour

### Monorepo Layout

```
xyz/
├── enigmatrix-backend/     # FastAPI + SQLAlchemy async
├── enigmatrix-frontend/    # Next.js 14 App Router
├── enigmatrix-ml/          # PyTorch + HuggingFace ML package
└── enigmatrix-docs/        # Research docs + vault-mirrored specs
```

---

## 2. The Core Problem

Sri Lankan SMEs face a systemic compliance gap rooted in awareness lag — not bad faith. Key evidence:

### Quantified Evidence

| Source | Statistic |
|---|---|
| IRD Annual Report 2023 | 34% of SME penalty assessments arose from amendments gazetted >90 days prior to the audit |
| EPF Board 2022 | 61% of audited SMEs were unaware of circular changes in force at the time of assessment |
| World Bank Enterprise Survey (IPS Working Paper) | Sri Lankan SMEs report compliance cost as 2nd largest operational burden after financing |
| 40-respondent SME pre-pilot (Sep 2025, Ceylon Chamber) | Median 33-day awareness lag (urban); 58-day lag (rural); WhatsApp cited as primary info channel by 72% |

### Why Previous Solutions Fail

| Gap | What exists | Why it fails |
|---|---|---|
| Gazette notifications | Printed/PDF gazettes on documents.gov.lk | PDFs are not data; no machine-readable extraction |
| Language coverage | English-only official summaries | 41% of SME operators are Sinhala/Tamil primary |
| Scanned documents | Pre-2018 gazettes are scanned images | No OCR pipeline exists |
| Awareness lag | No measurement exists | Baseline for DiD study impossible |
| Alert system | None | SMEs discover changes reactively (audits, peers) |

### What M1 Does

M1 is an end-to-end pipeline that:
1. **Scrapes** official gazette PDFs automatically
2. **Extracts** text from all three gazette types (text PDF, hybrid, scanned OCR)
3. **Classifies** each document to regulatory category + affected sector (ML)
4. **Summarises** content in trilingual plain language
5. **Alerts** registered SMEs via email/SMS
6. **Measures** the awareness lag at each propagation stage (the primary research contribution)

---

## 3. Research Questions

### Module 1 (Primary — Mohamed M.R.I)

| RQ | Question | Method |
|---|---|---|
| **RQ1** | What is the median lag between gazette publication date (T0) and SME awareness (T_aware)? | Platform pipeline timestamps + survey data |
| **RQ2** | Does lag vary by regulatory category, sector, or language? | Stratified analysis on `m1_propagation_events` |
| **RQ3** | Can an XLM-R+LoRA classifier accurately categorise trilingual gazette documents? | Macro-F1 on 12-category + 10-sector dual-head |
| **RQ4** | Does the automated alert system reduce lag (DiD)? | Difference-in-Differences on treatment (registered SME) vs control groups |

### Supporting Modules

| RQ | Module | Question |
|---|---|---|
| RQ-M2.1 | M2 | Does knowledge score correlate with regulation complexity and awareness lag? |
| RQ-M2.2 | M2 | Can knowledge gaps be detected from short quiz responses? |
| RQ-M3.1 | M3 | Which behavioural signals best predict compliance vulnerability? |
| RQ-M3.2 | M3 | Does a composite risk score improve on individual indicators? |
| RQ-M4.1 | M4 | Can a multilingual classifier detect regulatory misinformation in social media? |
| RQ-M4.2 | M4 | Which source types are most likely to propagate misinformation? |

---

## 4. Four Research Modules

### Overview Table

| Module | Name | Research Problem | Primary Output | Status |
|---|---|---|---|---|
| **M1** | Awareness Gap | How long does it take SMEs to discover new regulations? | Lag measurement + alert system | Pipeline shipped; ML training pending |
| **M2** | Knowledge Assessment | How well do SMEs understand the regulations they know? | Knowledge score (domain breakdown) | Survey + scoring engine shipped |
| **M3** | Vulnerability / Risk Scoring | Which SME profiles are most compliance-vulnerable? | Composite risk score | Survey shipped; ML model pending |
| **M4** | Misinformation Detection | How does misinformation about regulations spread? | Multilingual fake-news classifier | Architecture researched; stub only |

### M2 — Knowledge Assessment

- Auto-scoring engine (`m2_scoring.py`): `mcq_single`, `multi`, `numeric`, `ordered_steps` (partial credit), `open` (keyword match)
- `m2_knowledge_scores` cache table (eager recompute on each submit)
- Admin question bank with 5-card form + branching rules editor
- `by_domain_json` column provides domain breakdown for research analysis
- Status: **Fully shipped** (survey, scoring, admin UI)

### M3 — Vulnerability / Risk

- `m3_compliance_history` + `m3_behavioural_signals` tables (append-only snapshots)
- 32 questions across 4 sections
- `GET /api/v1/m3/sme/{id}/risk-signals` — combined M2+M3 view
- ML risk model: **not yet built** (501 placeholder)
- Status: **Survey shipped; ML model pending**

### M4 — Misinformation Detection

- Architecture research document: `research/15_Module4_Misinformation_Architecture.md`
- Data collection plan + Sri Lankan sources list documented
- Backend `/api/v1/verify` returns 501; frontend `/verify` is "coming soon"
- Status: **Research-only; classifier not built**

---

## 5. Module 1 — Awareness Gap (Full Depth)

### 5.1 Research Problem & Motivation

#### Abstract

M1 builds a fully automated trilingual pipeline that ingests Sri Lankan Official Gazette PDFs, classifies them by regulatory category and affected business sector, summarises them in plain-language trilingual output, dispatches email/SMS alerts to registered SMEs, and records timestamped propagation events. The core research contribution is a **formally measured awareness lag** — the delta from gazette publication (T0) to SME awareness (T_aware) — across five propagation channels: official portal, news media, peer networks, government inspectors, and the Enigmatrix alert system itself.

#### Evidence Streams

1. **IRD Annual Report 2023** — 34% of penalty assessments from regulations gazetted >90 days prior
2. **EPF Board 2022** — 61% unaware of EPF circular changes at time of assessment
3. **World Bank / IPS Working Paper** — compliance cost is 2nd largest SME burden
4. **40-SME pre-pilot (Sep 2025, Ceylon Chamber)** — 33d urban / 58d rural awareness lag; 72% cite WhatsApp as primary channel; selection bias acknowledged (Chamber members skew more compliant)

#### Formal Problem Statement

Given a gazette document $g$ published at time $T_0$ and an SME $s$ with registered sector $\sigma$:
- Let $T_{\text{aware}}(s, g)$ = the moment SME $s$ can correctly describe the core obligation in $g$
- The **awareness lag** $\Delta(s, g) = T_{\text{aware}}(s, g) - T_0$
- **Objective:** measure $E[\Delta]$ by channel, sector, language, and test whether the Enigmatrix alert system reduces it

#### T0–T9 Diffusion Timeline

| Timestamp | Event |
|---|---|
| T0 | Gazette publication date |
| T1 | Portal crawl — Enigmatrix ingests the PDF |
| T2 | Classification + summarisation complete |
| T3 | Alert dispatched to registered SMEs |
| T4 | News media covers the regulation |
| T5 | Government inspector briefing |
| T6 | Peer-to-peer diffusion (WhatsApp, chambers) |
| T7 | SME reports awareness in survey |
| T8 | SME demonstrates understanding in M2 quiz |
| T9 | Compliance action observed |

#### Six Research Findings Targets

| Finding | Description | Measurement |
|---|---|---|
| **F1** | Portal-to-Enigmatrix lag (~7 days target) | T1 − T0 from `m1_propagation_events` |
| **F2** | News lag (~23 days target) | T4 − T0 from RSS event records |
| **F3** | SME awareness lag (33d urban / 58d rural) | Survey responses in `m1_sme_awareness_responses` |
| **F4** | Sector variance in lag | Stratified analysis by `affected_sectors` |
| **F5** | Language lag differential | Split by `primary_language` in classification |
| **F6** | Alert system DiD effect | Treatment (registered) vs control (unregistered) |

#### Risk Register (7 items)

| Risk | Likelihood | Implementation Hook |
|---|---|---|
| XPath drift on documents.gov.lk | Medium | Watcher de-duplication contract + `CLOSESPIDER_TIMEOUT_NO_ITEM=60` |
| Sinhala OCR quality degradation | Medium | CER measurement tool; per-page fallback chain |
| Label scarcity (<50 examples/category) | High | Pool-based active learning; back-translation augmentation |
| Cross-contamination in cache | Low | Cache key = `model_version+gazette_number+date` |
| Survey response bias | Medium | Random subsample + rural oversampling planned |
| Alert delivery failure | Medium | SendGrid + Twilio dual-channel with retry |
| Annotation disagreement | Medium | Cohen's κ ≥ 0.75 gate; tiebreaker protocol |

---

### 5.2 Data Requirements & Schema

#### Primary Table: `m1_regulations`

The central state machine for the pipeline. Every gazette document creates exactly one row; status transitions are enforced by the pipeline.

**Status state machine:** `ingested → extracted → preprocessed → classified → summarised → alerted → archived`

Key columns (selected):

| Column | Type | Description |
|---|---|---|
| `regulation_id` | UUID PK | Primary key |
| `gazette_number` | VARCHAR(20) | e.g. `2369/14` |
| `gazette_published_date` | DATE | T0 for lag measurement |
| `primary_language` | VARCHAR(5) | `en` / `si` / `ta` / `mixed` |
| `source_id` | VARCHAR(20) | Which of 15 sources (e.g. `SRC_GOV_EGZ`) |
| `status` | VARCHAR(20) | State machine current state |
| `raw_pdf_path` | TEXT | `m1/raw/<source_id>/YYYY/MM/gazette_number.pdf` |
| `raw_text` | TEXT | Extracted text (kept for audit) |
| `cleaned_text` | TEXT | Post-noise-removal text fed to classifier |
| `extraction_method` | VARCHAR(20) | `pymupdf` / `pdfplumber` / `tesseract` |
| `amendment_type` | VARCHAR(20) | `new_act` / `amendment` / `repeal` |
| `regulatory_category` | VARCHAR(50) | 12-category ML output |
| `affected_sectors` | JSONB | 10-sector multi-label ML output |
| `primary_act_amended` | VARCHAR(200) | Named act being amended |
| `is_admin_set` | BOOLEAN | Admin-curated rows survive pipeline re-extraction |
| `alert_sent_at` | TIMESTAMPTZ | When alert was dispatched |

#### Additional Tables

| Table | Purpose |
|---|---|
| `m1_propagation_events` | Timestamped events for lag measurement (T0–T9) |
| `m1_sme_awareness_responses` | Survey: when/how did SME learn of this regulation |
| `m1_regulation_penalties` | Multi-penalty junction (penalty_type, amount_lkr, sequence_idx) |
| `m1_sub_documents` | Gazette sections identified by segmenter |
| `m1_regulation_sectors` | M:N gazette↔sector junction |
| `m1_regulation_changes` | Per-amendment change records |
| `m1_real_world_examples` | Linked real penalty examples |
| `m1_court_cases` | Linked litigation records |

#### Analytical Views

- `v_m1_regulation_lag_summary` — per-regulation T0/T1/T3/T7 with computed lag deltas
- `v_m1_channel_effectiveness` — aggregated channel comparison for DiD analysis

#### Alembic Migrations (M1 Phase 2)

| Migration | Content |
|---|---|
| `202605220001` | Add `status='preprocessed'` enum value + `cleaned_text` + `amendment_type` |
| `202605230001` | `m1_regulation_penalties` table (initial 3-value enum) |
| `202605240001` | Penalty type enum widened to 7 values + `is_admin_set` flag |
| `202605250001` | `m1_sub_documents` junction table |
| `202605260001` | Sub-document indices and constraints |

---

### 5.3 Data Sources Catalogue

**15 official and news sources:**

| Source ID | Description | Scrape Frequency |
|---|---|---|
| `SRC_GOV_EGZ` | documents.gov.lk — Extraordinary Gazettes | Daily (Beat) |
| `SRC_GOV_GZ` | documents.gov.lk — Ordinary Gazettes | Weekly |
| `SRC_GOV_BILL` | documents.gov.lk — Bills | Weekly |
| `SRC_GOV_ACT` | documents.gov.lk — Acts | Weekly |
| `SRC_IRD` | Inland Revenue Department circulars | Weekly |
| `SRC_EPF` | EPF Board circulars | Weekly |
| `SRC_ETF` | ETF Board circulars | Weekly |
| `SRC_EROC` | Registrar of Companies notices | Weekly |
| `SRC_SLSI` | SLSI standards updates | Monthly |
| `SRC_CBSL` | CBSL regulatory circulars | Weekly |
| `SRC_NEWS_*` (×5) | Newsfirst, Daily Mirror, Hiru, Adaderana, Virakesari RSS | Daily |

**Spider architecture:**
- `BaseDocumentsGovLkSpider` — common auth, XPath, dedup logic
- Subclasses: `EGZSpider`, `GZSpider`, `BILLSpider`, `ACTSpider`
- Sources catalogue: singleton module with per-source operational specs
- Partitioned storage: `m1/raw/<source_id>/YYYY/MM/`
- Fallback: Wayback Machine CDX API for missing PDFs

---

### 5.4 Data Collection Pipeline (Scrapy)

#### Pipeline Overview (Stages A–G)

| Stage | Name | Technology | Output |
|---|---|---|---|
| A | Ingest | Scrapy | PDF file on disk + `m1_regulations` row (status=`ingested`) |
| B | Extract | PyMuPDF / pdfplumber / Tesseract | `raw_text` (status=`extracted`) |
| B+ | Preprocess | Cleaning + metadata + chunking | `cleaned_text`, `amendment_type`, penalties, sub_documents (status=`preprocessed`) |
| C | Classify | XLM-R + LoRA | `regulatory_category`, `affected_sectors` (status=`classified`) |
| D | Summarise | MarianMT | Trilingual plain-language summary (status=`summarised`) |
| E | Alert | SendGrid + Twilio | Email/SMS dispatch (status=`alerted`) |
| F | Lag Measurement | PostgreSQL analytics | Propagation event records |

#### Watcher De-duplication Contract

The spider writes a row only if no row with the same `gazette_number` + `source_id` already exists. Re-crawling is idempotent at Stage A.

#### Celery Task Chain

```
run_gazette_spider (Celery beat or admin trigger)
    → extract_gazette.delay(regulation_id)        # Stage B
        → preprocess_gazette.delay(regulation_id) # Stage B+
            → classify_gazette.delay(...)          # Stage C (not yet built)
```

Tasks use `.delay()` (not Celery `chain`) for observability — each stage fires independently, enabling restart from any point.

#### Cron Schedule (Celery Beat)

- Daily 06:00 LKT: `run_gazette_spider` for extraordinary gazettes
- Weekly Monday 07:00 LKT: ordinary/act/bill/departmental sources
- Daily 08:00 LKT: RSS news-feed harvester

#### 10 Validation Checkpoints

1. PDF is downloadable (HTTP 200, Content-Type PDF)
2. File size > 10KB (not a placeholder)
3. Text extraction yields > 50 chars/page
4. Language detection confidence ≥ 0.70
5. Gazette number matches `\d{4}/\d{1,2}` pattern
6. Published date is parseable and > 2010-01-01
7. No duplicate gazette_number in DB
8. Penalty extraction produces ≥ 0 rows (NOT_REGULATORY returns 0)
9. Chunking yields ≥ 1 chunk
10. Status transition is valid (no backward transitions)

---

### 5.5 PDF Extraction Chain

#### classify_pdf() — Three-tier detection

```
Average chars/page
        ≥ 200 → text_pdf    → PyMuPDF (fast, accurate)
    30–200  → hybrid_pdf → PyMuPDF first, then pdfplumber on low-yield pages
        < 30  → scanned_pdf → Tesseract OCR (eng+sin+tam)
```

#### Threshold Calibration

| Tier boundary | Default | Calibration method |
|---|---|---|
| text/hybrid | 200 chars/page | 100-doc pilot; adjust if >5% misclassification |
| hybrid/scanned | 30 chars/page | Chosen to catch mixed-scan documents |

#### Library Chain

1. **PyMuPDF (fitz)** — fastest; best for digital text PDFs; preserves column order
2. **pdfplumber** — better for tables; handles rotated text; fallback for hybrid
3. **Tesseract OCR** — `--oem 1 --psm 6 eng+sin+tam` — only for pages yielding <30 chars/page

#### Per-Page Decision Example

```
Page 1: PyMuPDF → 420 chars → keep
Page 2: PyMuPDF → 18 chars → switch to pdfplumber → 310 chars → keep
Page 3: pdfplumber → 12 chars → switch to Tesseract → OCR output
Document extraction_method = 'pdfplumber' (mixed = maximum fidelity method used)
```

#### Failure Modes

| Failure | Handling |
|---|---|
| Garbled Wijesekara encoding | `convert_wijesekara_to_unicode()` pre-pass |
| Password-protected PDF | Caught; logged as `extraction_failed`; skipped |
| Tesseract subprocess timeout | 30s timeout; retried once; logged if still fails |
| Zero-yield after all three methods | Status = `extraction_failed`; alert to admin |

---

### 5.6 Preprocessing Pipeline

#### 5-Step Pipeline

1. **Noise removal** — strip headers/footers/page-numbers, normalise whitespace, remove boilerplate
2. **Language routing** — fastText → per-line `extract_language_segments()` → trilingual split
3. **Metadata extraction** — `amendment_type` discriminator, gazette number, effective date, principal act name
4. **Chunking** — §-aware (section boundaries first) + sliding-window fallback for long sections
5. **Output** — `PreprocessedGazette` dataclass → DB persistence by `preprocess_gazette_task`

#### Multilingual Character Range Routing

```python
si_range = range(0x0D80, 0x0E00)  # Sinhala Unicode block
ta_range = range(0x0B80, 0x0C00)  # Tamil Unicode block
# Lines with >30% chars in block → routed to that language bucket
```

#### Token Length Table (XLM-R SentencePiece)

| Language | Chars/token | 512 tokens covers | Relative token cost |
|---|---|---|---|
| English | 4.2 chars/token | ~2,150 chars | 1× |
| Tamil | 2.1 chars/token | ~1,075 chars | 2× |
| Sinhala | 1.8 chars/token | ~922 chars | 2.3× |

**Implication:** Sinhala/Tamil documents consume 2–2.3× more of the 512-token XLM-R window. Section-aware chunking is critical to avoid truncating regulatory content.

#### Tokenizer Selection Rationale

XLM-R's SentencePiece tokenizer was selected over spaCy/NLTK/IndicNLP because:
- Native coverage of Sinhala and Tamil Unicode blocks
- Shared BPE vocabulary with the XLM-R base model weights
- Handles code-switching (mixed-script documents) gracefully

#### Multi-Penalty Extraction

`extract_all_penalties(text)` returns a list of `{penalty_type, amount_lkr, imprisonment_months, context}` dicts. Penalty types: `fine`, `imprisonment`, `both`, `suspension`, `revocation`, `cancellation`, `disqualification`.

---

### 5.7 Sinhala & Tamil NLP

#### Language Detection Library Selection

| Library | Sinhala accuracy | Tamil accuracy | Why selected/rejected |
|---|---|---|---|
| **fastText lid.176.bin** | ~97.3% | ~97%+ | **Selected** — best accuracy, top-K probs, 176 languages, offline, <1ms |
| langdetect | ~89% | ~94% | Unstable on short text (<50 chars) |
| langid | ~94% | ~94% | No top-K probability output |
| cld3 (Google) | ~96% | ~96% | Chrome/Node.js subprocess dependency |

**fastText configuration:** predict on first 500 chars (empirically chosen — 200 chars gives 12% misclassification on EN-preamble/SI-body gazettes; 500 chars drops to <3%); `k=3` top predictions; confidence threshold `min_confidence=0.70`; returns `'mixed'` if confidence below threshold.

#### Wijesekara Font Conversion

Pre-2010 Sinhala gazettes use legacy Wijesekara font (non-Unicode). A 100-doc pilot scan found:
- Pre-2010: ~38% use Wijesekara
- 2010–2015: ~3%
- Post-2015: ~0%

The conversion applies a character-mapping table to translate Wijesekara byte sequences to proper Unicode Sinhala. Implemented in `ml/m1/extraction/ocr.py`. Triggered only when `is_likely_wijesekara()` heuristic detects ≥50 consecutive ASCII-alpha characters in what should be a Sinhala segment.

#### Tesseract OCR Configuration

```
--oem 1      # LSTM engine (best accuracy for SI/TA)
--psm 6      # Assume uniform block of text
-l eng+sin+tam  # Trilingual model
```

CER measurement CLI: `python -m m1.extraction.ocr --measure-cer pred.txt gold.txt`

---

### 5.8 Model Architecture (XLM-R + LoRA)

#### Task Definition

**Dual-head classification on each gazette chunk:**
- **Head 1 (single-label):** 12 regulatory categories
- **Head 2 (multi-label):** 10 affected business sectors

#### 12 Regulatory Categories

Labour, Tax, Company Law, Environmental, Financial Services, Health & Safety, Import/Export, Land & Property, Intellectual Property, Consumer Protection, Local Government, Other/Administrative

#### 10 Business Sectors

Manufacturing, Retail & Trade, Construction, Hospitality & Tourism, Transport, Finance & Insurance, IT & Telecoms, Agriculture & Fisheries, Healthcare & Pharma, Professional Services

#### Architecture Comparison (Why XLM-R+LoRA)

| Approach | Macro-F1 (est.) | Training cost | Deployment size | Decision |
|---|---|---|---|---|
| TF-IDF + SVM | ~0.52 | Seconds | <1MB | Baseline only |
| mBERT fine-tuned | ~0.70 | High | 714MB | Rejected — smaller SI/TA vocab |
| **XLM-R base + LoRA** | **~0.78+** | **Moderate** | **~125MB + 2.4M** | **Selected** |
| XLM-R large + LoRA | Higher | Very high | >1.2GB | Rejected — Fly.io memory limit |
| IndicBERT | ~0.68 | Low | 200MB | Rejected — weaker EN coverage |

#### LoRA Configuration

| Hyperparameter | Value | Justification |
|---|---|---|
| `r` (rank) | 16 | Balance: 8 under-fits SI/TA; 32 exceeds memory |
| `lora_alpha` | 32 | `alpha = 2r` standard ratio |
| `target_modules` | `["query", "value"]` | Standard XLM-R LoRA targets |
| `lora_dropout` | 0.1 | Regularisation |
| Trainable params | ~2.4M | vs 125M total → 98% frozen |
| Frozen params | ~122.6M | Base XLM-R weights unchanged |

#### GazetteClassifier Dual-Head

```python
class GazetteClassifier(nn.Module):
    def __init__(self):
        base = XLMRobertaModel.from_pretrained("xlm-roberta-base")
        self.encoder = get_peft_model(base, lora_config)
        self.category_head = nn.Linear(768, 12)    # single-label
        self.sector_head = nn.Linear(768, 10)       # multi-label

    def forward(self, input_ids, attention_mask):
        cls = self.encoder(...).last_hidden_state[:, 0, :]
        return self.category_head(cls), self.sector_head(cls)
```

#### Combined Loss

```python
def combined_loss(category_logits, sector_logits, category_labels, sector_labels, alpha=0.7):
    cat_loss = F.cross_entropy(category_logits, category_labels)
    sec_loss = F.binary_cross_entropy_with_logits(sector_logits, sector_labels.float())
    return alpha * cat_loss + (1 - alpha) * sec_loss
```

`alpha=0.7` weights regulatory category (primary research dimension) over sector (supporting dimension).

#### ONNX Export

Model is exported at opset 17 with optional INT8 quantisation via `torch.quantization.quantize_dynamic`. Inference via ONNX Runtime (ORT) on Fly.io — eliminates PyTorch runtime dependency, reduces cold-start latency.

---

### 5.9 Training & Evaluation Protocol

#### Dataset Construction

**3-step sampling strategy:**
1. **Stratified random sample** — minimum 50 examples per category
2. **k-means clustering (k=20)** — ensures diverse text patterns within each category
3. **Pool-based active learning** — uncertainty sampling selects hardest examples for annotation next

**Total target:** 800+ annotated examples; Cohen's κ ≥ 0.75 (annotation quality gate)

**Small-cell handling:** if a category has <50 examples after sampling, back-translation augmentation (up to 5× cap) is applied before training. NOT applied to test set.

**Chicken-and-egg trap:** active learning requires a production baseline model to score unlabelled pool; initial 200-example annotation round seeds a v0 model before AL begins.

#### Train/Test Split

**Temporal split — NOT random:**
```
Training: oldest 70% of documents (by gazette_published_date)
Validation: next 15%
Test: most recent 15% (minimum 30-day window)
```

Rationale: regulatory text evolves over time; random splits leak temporal information and inflate test scores.

#### Reproducibility

Seeds: 42 / 1 / 2 (three independent runs; report mean ± std)

`model_registry.json` captures: git SHA, dataset SHA-256, `env.yml` SHA, seeds, training timestamp.

#### Training Configuration

| Parameter | Value |
|---|---|
| Optimizer | AdamW |
| LoRA head LR | 2e-4 |
| Classifier head LR | 2e-5 |
| Batch size | 16 |
| Max epochs | 20 |
| Early stopping patience | 3 |
| Precision | FP16 |
| Scheduler | Linear warmup (10% steps) |

#### Evaluation Protocol

- **Primary metric:** Macro-F1 (across 12 categories, unweighted)
- **Secondary:** Per-category F1, Precision, Recall
- **Slice analysis:** by language (EN/SI/TA), by year-quarter, by text-length bin, by extraction-method
- **Error taxonomy:** 4 types — confusion within related categories, language-induced errors, extraction artefacts, ambiguous regulations
- **Confusion matrix:** tracked for all 12×12 combinations

---

### 5.10 Deployment & Integration

#### Fly.io Selection Rationale

| Criterion | Fly.io | GCP Cloud Run | AWS Lambda |
|---|---|---|---|
| Region | Singapore (low latency for LK) | Available | Available |
| Cold start | No cold start (persistent VMs) | Yes | Yes |
| Persistent volumes | Yes (for ChromaDB + ONNX models) | No (needs GCS) | No |
| Monthly cost (est.) | ~$20/mo | Higher | Higher |
| **Decision** | **Selected** | Rejected | Rejected |

#### CachedInferenceEngine

Redis inference cache with cross-gazette contamination guard:

```
cache_key = f"{model_version}:{gazette_number}:{gazette_date}:{text_hash}"
```

Cache hit → return cached classification immediately (no re-inference).
Cache miss → run ONNX Runtime inference → store result.

**Why include `gazette_number` in key:** prevents a hypothetical contamination where the same text hash appears in two different gazette issues with different regulatory contexts.

#### Latency Budget

| Stage | Budget |
|---|---|
| Spider crawl (per document) | <2 min |
| PDF extraction (per document) | <30s |
| Preprocessing (per document) | <10s |
| ONNX inference (per chunk) | ~1.8s |
| Alert dispatch (per SME) | <5s |
| **End-to-end T0 → alert** | <24h |

**Throughput:** ~2.6 inferences/second with batch size=4 on Fly.io shared CPU.

#### Celery Worker Sizing (Aiven Cloud Postgres)

With Aiven entry-tier Postgres (max ~20 connections):
- Recommended `celery --concurrency=2`
- DB pool: `pool_size=1, max_overflow=2, pool_timeout=10` per worker
- Peak connections: 2 workers × 3 + uvicorn × 3 = ~9 (fits budget)

---

### 5.11 Full System Architecture

#### 6-Layer Stack

```
Browser (Next.js 14)
    ↓ HTTPS
FastAPI (uvicorn, Fly.io)
    ↓ SQLAlchemy async
PostgreSQL 16 (Aiven cloud)
    ↓ Celery tasks
Redis (result backend + inference cache)
    ↓ ONNX Runtime
ML Models (Fly.io persistent volume)
```

#### Admin Frontend Routes

| Route | Description | Status |
|---|---|---|
| `/admin/m1/pipeline` | 6-stage flow diagram with live counts | Shipped (Session 37) |
| `/admin/m1/pipeline/recent` | Recent pipeline runs table | Shipped (Session 37) |
| `/admin/m1/pipeline/steps` | Per-step detail with code refs | Shipped (Session 37) |
| `/admin/m1/pipeline/trace/[id]` | Per-regulation timeline + content | Shipped (Session 37) |
| `/admin/m1/pipeline/extraction` | Gazette extraction trigger + date-range picker | Shipped (Sessions 38, 42) |
| `/admin/research-log/*` | Live vault tracker triplet | Shipped (Session 36) |
| `/admin/regulations` | CRUD for regulations | Shipped (Session 7) |
| `/admin/questions` | Question bank | Shipped (Session 11) |
| `/admin/m2/scores` | Knowledge scores | Shipped |
| `/admin/m3/risk-signals` | Risk signals combined view | Shipped |
| `/admin/settings` | Survey limits + config | Shipped (Session 16) |

#### SME Frontend Routes

| Route | Description | Status |
|---|---|---|
| `/regulations` | Regulation list (filtered by sector) | Shipped |
| `/surveys` | Unified hub (By Reg / By Module tabs) | Shipped |
| `/surveys/awareness` | M1 awareness survey | Shipped |
| `/surveys/knowledge` | M2 knowledge survey | Shipped |
| `/surveys/vulnerability` | M3 vulnerability survey | Shipped |
| `/verify` | M4 misinformation checker | Placeholder (coming soon) |
| `/risk` | SME risk dashboard | Placeholder (needs ML model) |

#### Security Architecture

- JWT auth (access + refresh tokens); role-based (`ADMIN`, `SME`, `RESEARCHER`)
- Rate limiting on auth endpoints (`slowapi`)
- Structured logging (`structlog`)
- Full audit log covering all admin mutations
- `is_active` soft-delete (no hard deletes)

---

### 5.12 Annotation Guidelines

#### Annotation Tool

**Label Studio** — self-hosted; XML config specifies the labelling UI. Selected for: open-source, active learning plugin, Cohen's κ tracking, export to HuggingFace datasets format.

#### IAA Protocol (Inter-Annotator Agreement)

- Minimum 2 annotators per document
- Cohen's κ threshold: ≥ 0.75 (acceptable agreement gate)
- Tiebreaker: third annotator for any κ < 0.75 pair
- Batch size: 50 documents per round

#### 12-Category Decision Guide (summary)

| Category | Key signals | Common exclusions |
|---|---|---|
| Labour | EPF/ETF, wages, employment conditions | Tax withholding on salaries → Tax |
| Tax | IRD circulars, VAT, SSCL rates | Customs tariffs → Import/Export |
| Company Law | ROC notices, company registration | Securities law → Financial Services |
| Environmental | CEA, environmental levy | Pesticide labelling → Health & Safety |
| Financial Services | CBSL circulars, banking ratios | Leasing company registration → Company Law |
| Health & Safety | SLSI, food standards, occupational safety | Drug pricing → Consumer Protection |
| Import/Export | Customs tariff notices, HS codes | Foreign exchange → Financial Services |
| Land & Property | Survey Dept, land titles | Building permits → Local Government |
| IP | Patents, trademarks | Technology licensing → IT/Telecoms |
| Consumer Protection | Consumer Affairs Authority, price controls | — |
| Local Government | Municipal notices, rates, permits | — |
| Other/Administrative | Does not fit any above | — |

---

### 5.13 API Reference

#### Role-Permission Matrix

| Role | Read regulations | Alert preferences | Admin CRUD | Pipeline trigger |
|---|---|---|---|---|
| `ANONYMOUS` | Public list only | No | No | No |
| `SME` | Full list + detail | Yes | No | No |
| `RESEARCHER` | Full + raw fields | No | No | No |
| `ADMIN` | All fields | Yes | Yes | Yes |

#### Key Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/m1/regulations` | Paginated regulation list (sector filter) |
| GET | `/api/v1/m1/regulations/{id}` | Regulation detail |
| POST | `/api/v1/admin/m1/regulations` | Create regulation |
| PATCH | `/api/v1/admin/m1/regulations/{id}` | Update regulation |
| POST | `/api/v1/admin/m1/extraction/trigger` | Trigger gazette extraction (date range) |
| GET | `/api/v1/admin/m1/extraction/progress` | Per-regulation progress |
| GET | `/api/v1/admin/m1/extraction/summary` | Aggregate stats + PDF-type breakdown |
| GET | `/api/v1/admin/m1/pipeline/status-counts` | Live counts by status |
| GET | `/api/v1/survey-flow/start` | Begin regulation-scoped survey |
| POST | `/api/v1/survey-flow/answer` | Submit answer + advance flow |

#### Standard Error Response

```json
{
  "error_code": "REG_NOT_FOUND",
  "message": "Regulation 2369/14 not found",
  "detail": null
}
```

---

### 5.14 Tracking Workflows

#### 8+1 Tracking Surfaces

| Surface | Audience | Description |
|---|---|---|
| A1 | Admin | Pipeline status dashboard (live flow diagram) |
| A2 | Admin | Gazette extraction trigger + progress |
| A3 | Admin | Error log (extraction_failed, alert_failed) |
| A4 | Admin | Research findings tracker |
| S1 | SME | Regulation list with compliance status |
| S2 | SME | Alert preferences |
| S3 | SME | My compliance history |
| S4 | SME | Knowledge score dashboard |
| X9 | Cross-cutting | Audit log (all mutations) |

#### Shipping Status

| Surface | Status |
|---|---|
| A1 Pipeline dashboard | Shipped (Session 37) |
| A2 Gazette extraction | Shipped (Sessions 38, 39, 42, 43) |
| A3 Error log | Shipped (Session 37) |
| A4 Research log portal | Shipped (Session 36) |
| S1 Regulation list | Shipped |
| S2 Alert preferences | Deferred |
| S3 Compliance history | Deferred |
| S4 Knowledge score | Shipped (M2 scores) |
| X9 Audit log | Shipped (Session 14) |

---

### 5.15 Folder Structure & Implementation Flow

#### 5 Design Principles

1. **ML as a library** — `enigmatrix-ml` is a standalone Python package installable into backend; no circular imports
2. **One function per file** — each extraction/preprocessing concern has a dedicated module
3. **Lazy imports in Celery tasks** — backend boots without ML dependencies if `enigmatrix-ml` is absent
4. **Partitioned storage** — raw PDFs stored at `m1/raw/<source_id>/YYYY/MM/` for easy source-level archiving
5. **Extensibility** — `ml/m1/`, `ml/m2/`, `ml/m3/`, `ml/m4/` per-module template; M2/M3/M4 scaffold from M1 pattern

#### Key File Paths

```
enigmatrix-ml/
├── m1/
│   ├── extraction/
│   │   ├── __init__.py          # Public surface: classify_pdf, extract_*, convert_wijesekara
│   │   ├── pdf_classifier.py    # classify_pdf() with threshold calibration
│   │   ├── pymupdf_extractor.py
│   │   ├── pdfplumber_extractor.py
│   │   ├── ocr.py               # Tesseract + Wijesekara conversion
│   │   ├── language_detection.py # fastText lid.176.bin
│   │   └── segmenter.py         # detect_sections_with_labels()
│   └── preprocessing/
│       ├── __init__.py
│       ├── cleaning.py
│       ├── metadata_extractor.py
│       ├── chunking.py
│       └── orchestrator.py      # preprocess_gazette() → PreprocessedGazette

enigmatrix-backend/
├── app/
│   ├── api/v1/
│   │   ├── m1_gazette_extraction.py  # trigger/progress/summary endpoints
│   │   └── m1_pipeline.py            # status counts, recent runs
│   ├── tasks/m1/
│   │   ├── gazette_scraper.py        # run_gazette_spider Celery task
│   │   ├── gazette_extractor.py      # extract_gazette Celery task
│   │   └── gazette_preprocessor.py  # preprocess_gazette Celery task
│   └── services/
│       └── m1_pipeline_service.py   # _extraction_scope_filter, aggregations

enigmatrix-backend/scraper/
└── spiders/
    └── gazette_spider.py            # GazetteSpider with early-exit
```

#### Stage A–G Implementation Flow

```
Stage A (Ingest):
  GazetteSpider.parse() → yields items → GazettePipeline → INSERT m1_regulations(status='ingested')
  Early-exit when gazette_date < date_from (scope exhausted)

Stage B (Extract):
  extract_gazette.delay(regulation_id)
  → classify_pdf() → extract chain → UPDATE m1_regulations SET status='extracted', raw_text=...

Stage B+ (Preprocess):
  preprocess_gazette.delay(regulation_id)
  → orchestrator.preprocess_gazette() → PreprocessedGazette
  → UPDATE m1_regulations SET status='preprocessed', cleaned_text=..., amendment_type=...
  → INSERT m1_regulation_penalties rows
  → INSERT m1_sub_documents rows

Stages C–F: Not yet implemented (classified, summarised, alerted, lag_measured)
```

---

### 5.16 Development Roadmap

#### 5-Phase Structure

| Phase | Description | Status |
|---|---|---|
| **Phase 1** Foundation | Monorepo, DB schema, auth, regulations CRUD, surveys M1/M2/M3 | ✅ Complete |
| **Phase 2** Ingest + Extract | Scrapy spider, Celery extraction chain, preprocessing pipeline, admin extraction portal | ✅ Complete |
| **Phase 3** Annotation + Classification | Label Studio, 800 examples, XLM-R+LoRA training, ONNX deployment | 🔲 Not started |
| **Phase 4** Schedulers + Alerts | Beat scheduling, SendGrid/Twilio alerts, lag measurement | 🔲 Not started |
| **Phase 5** Research Findings | F1–F6 analysis, DiD model, dissertation writing | 🔲 Not started |

#### Phase 3 — Next Steps (current priority)

1. Set up Label Studio instance
2. Export first 200 gazette documents to annotation pool
3. Begin annotation round 1 (50 docs × 2 annotators)
4. Compute Cohen's κ; iterate on guidelines if κ < 0.75
5. Train XLM-R v0 on first 200 examples
6. Begin active learning loop (uncertainty sampling → annotate → retrain)
7. Reach 800 examples with κ ≥ 0.75
8. Final training run (3 seeds, temporal split)
9. ONNX export + INT8 quantisation
10. Deploy to Fly.io; wire `classify_gazette` Celery task

---

## 6. Build Status

### Current Status as of Session 43 / 2026-05-18

#### Infrastructure

| Item | Status |
|---|---|
| Docker Compose dev environment | ✅ `make up` working |
| PostgreSQL 16 (Aiven cloud) | ✅ Configured |
| Redis (result backend + cache) | ✅ Running |
| Alembic migrations (18 versions) | ✅ All applied through Session 34 |
| Celery + Beat scheduler | ✅ Configured |
| Structured logging | ✅ structlog |
| Rate limiting | ✅ slowapi on auth endpoints |
| Audit log | ✅ Full admin mutation coverage |
| CI/CD (GitHub Actions) | 🔲 Not built |
| E2E tests (Playwright) | 🔲 Not built |
| Cloud deployment (Fly.io) | 🔲 Not deployed |

#### M1 Pipeline

| Step | Feature | Status | Session |
|---|---|---|---|
| 2a Scrapy spider | `run_gazette_spider` Celery task; multi-source; early-exit | ✅ | 23, 43 |
| 2b PDF extraction | `extract_gazette` Celery task; 3-library chain | ✅ | 26 |
| 2c Extraction library | `ml/m1/extraction/` canonical package | ✅ | 28 |
| 2d Language detection + Wijesekara | fastText + Wijesekara conversion | ✅ | 30 |
| 2e Preprocessing | Cleaning + metadata + chunking | ✅ | 31 |
| 2f DB persistence | `preprocess_gazette` Celery task + schema | ✅ | 32, 34 |
| Admin extraction portal | Date-range picker, progress, summary | ✅ | 38, 39, 42 |
| Pipeline observability | 6-stage flow diagram, live counts | ✅ | 37 |
| Research log portal | Vault trackers surfaced in admin UI | ✅ | 36 |
| 2g Classification | XLM-R+LoRA inference | 🔲 No training data yet |
| 2h Summarisation | MarianMT trilingual summaries | 🔲 |
| 2i Alert dispatch | SendGrid + Twilio | 🔲 |
| 2j Lag measurement | `m1_propagation_events` analytics | 🔲 |

#### Surveys & Scoring

| Feature | Status |
|---|---|
| M1 Awareness survey (DB-driven) | ✅ |
| M2 Knowledge survey + auto-scoring | ✅ |
| M3 Vulnerability survey + snapshots | ✅ |
| Cross-module unified survey wizard | ✅ |
| Regulation-scoped survey flows | ✅ |
| Admin survey limits | ✅ |
| Admin flow canvas (visual builder) | ✅ |

#### Known Blockers

| Blocker | Impact | Fix |
|---|---|---|
| No annotated training data | M1 classifier, M3 ML model, M4 classifier all blocked | Annotation sprint (Phase 3) |
| CORS env issue in `conftest.py` | Backend integration tests fail | Change `CORS_ORIGINS` to JSON array string |
| Alembic migration not run | `survey_limits` returns defaults | Run `alembic upgrade head` |

---

## 7. Session Log — Development History

### Summary by Phase

| Sessions | Date range | Key theme |
|---|---|---|
| 1–4 | 2026-05-01 to 2026-05-08 | Monorepo scaffold, backend MVP, auth, awareness survey |
| 5–9 | 2026-05-09 | Admin CRUD, unified survey wizard, M2/M3 surveys |
| 10–12 | 2026-05-09 to 2026-05-12 | Question bank, branching rules, regulation-scoped flows |
| 13–16 | 2026-05-12 to 2026-05-14 | UI polish, audit log, authorship, survey limits |
| 17–19 | 2026-05-11 to 2026-05-12 | Hotfix, documentation sync, module number rename |
| 20–22 | 2026-05-12 to 2026-05-15 | Domain restructuring, doc cleanup, seed refactor |
| 23–28 | 2026-05-15 | M1 Phase 2 Steps 2a–2c (Spider, Celery extract, extraction library) |
| 29–34 | 2026-05-17 | Steps 2d–2f (Language detection, preprocessing, DB wiring) + cleanup |
| 35–37 | 2026-05-17 | Local-dev handbook, research log portal, M1 pipeline observability |
| 38–39 | 2026-05-17 | Admin gazette extraction portal + token bug sweep |
| 40–43 | 2026-05-18 | DB pool hotfix, cumulative counts, date-range picker, spider early-exit |

### Selected Notable Sessions

**Session 23 (F-145) — Scrapy Spider MVP**
Built the first working `GazetteSpider`. Scraped `documents.gov.lk`, extracted gazette PDF links via XPath, downloaded to `m1/raw/SRC_GOV_EGZ/YYYY/MM/`, inserted rows with status=`ingested`. Integration test: 4 tests passed.

**Session 26 (F-148) — Celery Extract**
`extract_gazette` Celery task wired to Spider output. 3-library chain (PyMuPDF → pdfplumber → Tesseract) dispatched per regulation_id. Status transitions to `extracted`. Auto-chains to `preprocess_gazette` when both steps deployed.

**Session 30 (F-153) — Language Detection + Wijesekara**
fastText `lid.176.bin` integrated. Per-page OCR fallback chain (text pages use PyMuPDF; low-yield pages flip to Tesseract). Wijesekara → Unicode conversion for pre-2010 Sinhala gazettes. 41 ML tests passing.

**Session 32 (F-155) — Full Pipeline Wiring**
`preprocess_gazette` Celery task. `m1_regulation_penalties` table created. `cleaned_text` + `amendment_type` persisted. Status state machine extended with `preprocessed`. End-to-end: `ingested → extracted → preprocessed` all working.

**Session 37 (F-160) — Pipeline Observability Portal**
`/admin/m1/pipeline/*` suite: 6-stage flow diagram with live status counts, throughput chart (Recharts), status distribution donut, pipeline funnel, per-regulation trace. Auto-refreshes every 5s via TanStack Query. Full verification of all Phase 2 steps.

**Session 38 (F-161) — Admin Gazette Extraction Trigger**
Frontend admin page to trigger gazette extraction with year/month scope. Backend `POST /extraction/trigger` dispatches `run_gazette_spider` Celery task. Progress polling endpoint. Celery integration-test loop fix.

**Session 42 (F-169) — Date-Range Picker**
Replaced year/month comboboxes with a calendar-based date-range picker (react-day-picker v8 + Radix Popover). 7 quick-pick chips (Last 7d, Last 30d, Q1-Q4, This year). API shape changed from `{year, month_start, month_end}` to `{date_from, date_to}` ISO strings. `BETWEEN` query in service layer (index-friendly).

**Session 43 (F-170) — Spider Early-Exit**
Spider now calls `engine.close_spider("scope_exhausted")` when it encounters a gazette dated before `date_from` (documents.gov.lk lists in descending date order). Cuts a Jan 4–5 2026 crawl from ~10 minutes to ~1–2 minutes. `CLOSESPIDER_TIMEOUT_NO_ITEM=60` as safety net.


**Session 54 (F-185–F-192) — M1 Extraction Run History + Pool Architecture**
(1) `m1_extraction_runs` is now the server-side audit log for every extraction trigger. Schema: `run_id` UUID PK, `task_id` TEXT UNIQUE, `source_id`, `date_from/to`, `queued_at`, `queued_by_id` FK→`users.id` ON DELETE SET NULL, `queued_by_email` (denormalised snapshot), `celery_status` (updated lazily via HTTP polling side-effect — not via Celery signals), `result` JSONB, `traceback`, `completed_at`, `rows_ingested/extracted/preprocessed/failed` (captured at terminal state only; NULL while running). Migration: `202605210002`, chain tip `202605280001`. (2) `AuditMiddleware._write_passive_log` opens a fresh `SessionLocal()` on every API request via a detached `asyncio.create_task` — this is an invisible, always-on connection consumer. Any new `db: AsyncSession` dependency added to an endpoint compounds this. Current pool budget: `pool_size=3, max_overflow=5` = 8 uvicorn connections, within Aiven's ~20–25 connection limit. (3) Extraction trigger history is now API-primary (GET /runs) with localStorage as a write-through cache / offline fallback — localStorage is no longer the source of truth. (4) `m1_extraction_runs.celery_status` is synced lazily: a run stays at PENDING until at least one admin polls `/status/{task_id}`. A Celery signal handler (task_success/task_failure) has not yet been implemented. See [CHANGES.md](CHANGES.md) F-189–F-192 and [plan](plans/2026-05-22_Plan%20M1%20extraction%20run%20history%20—%20server-side%20persistence%20and%20pool%20fix.md).

**Session 53 (F-184) — M1 Pipeline Admin UX Audit**
Hands-on audit of all six `/admin/m1/pipeline` admin areas confirmed the following system-shape facts: (1) `/admin/m1/pipeline/recent` (standalone Recent Runs page) returns HTTP 503 on every RSC data fetch — the route exists in the frontend but the backend endpoint is broken or missing; the same run data renders correctly on the Trace page. (2) The admin pipeline sub-menu is not directly URL-addressable; navigating to `/admin/m1/pipeline` redirects to `/admin/regulations` without first clicking Survey Management in the sidebar. (3) The pipeline funnel widget calculation divides by a cumulative total rather than the previous stage count, producing rates of 7,700% and 1,283% (Raw→Extracted, Extracted→Preprocessed). (4) Failed rows in the Overview run table have no drill-down chevron — only `preprocessed` rows have the ">" navigation icon. (5) Auto-refresh polling (5s via TanStack Query) confirmed working; pauses correctly when tab hidden. See [CHANGES.md](CHANGES.md) F-184 and [plan](plans/2026-05-22_Plan%20M1%20pipeline%20admin%20UX%20audit%20—%2014%20findings%20report.md).

---

## 8. Pending Roadmap

### Phase 3 — Annotation + Classification (Next Priority)

1. **Label Studio setup** — deploy instance; configure XML schema for 12-category + 10-sector dual-head
2. **Initial annotation pool** — export first 200 gazette documents; assign to 2 annotators
3. **Annotation round 1** — target 200 docs; compute κ; iterate on guidelines
4. **Augmentation** — back-translation for under-represented categories (up to 5× cap)
5. **v0 model training** — XLM-R+LoRA on first 200 examples; baseline macro-F1
6. **Active learning loop** — uncertainty sampling → annotate → retrain until 800 examples
7. **Final training** — 3 seeds (42/1/2), temporal split, FP16, early stopping patience=3
8. **ONNX export** — opset 17, INT8 optional; CachedInferenceEngine
9. **Fly.io deployment** — Singapore region; persistent volume for models
10. **Wire classify_gazette task** — `preprocessed → classified` status transition

### Phase 4 — Schedulers + Alerts

1. Celery Beat cron schedule for all 15 sources
2. SendGrid integration for email alerts (per-sector subscription)
3. Twilio integration for SMS alerts
4. `m1_propagation_events` inserts at each T-point
5. Alert delivery tracking (sent/delivered/bounced)

### Phase 5 — Research Findings

1. **F1:** Compute portal lag from `m1_propagation_events` (target ~7 days)
2. **F2:** Compute news lag from RSS event records (target ~23 days)
3. **F3:** Survey analysis — mean lag by urban/rural, sector, language
4. **F4:** Sector variance ANOVA
5. **F5:** Language lag differential (EN vs SI vs TA)
6. **F6:** DiD model — treatment (alert-registered SMEs) vs control

### Deferred Features

| Feature | Description | When |
|---|---|---|
| SME alert preferences UI | `/surveys/alerts` subscription management | Phase 4 |
| RAG context card in survey wizard | Gazette-grounded answer explanations | After ML |
| M3 risk score ML model | Composite vulnerability predictor | After M2/M3 data accumulation |
| M4 misinformation classifier | Social media misinformation detector | After M1 ML complete |
| Cross-year crawl support | Chaining N spider crawls for multi-year ranges | On demand |
| E2E Playwright tests | Full browser-level regression tests | CI/CD sprint |
| MLflow experiment tracking | Centralised ML run tracking | Phase 3 |

---

## 9. Technology Stack

### Backend

| Component | Technology | Version | Purpose |
|---|---|---|---|
| Framework | FastAPI | latest | Async REST API |
| ORM | SQLAlchemy | 2.x async | Database abstraction |
| Server | uvicorn | latest | ASGI server |
| Task queue | Celery + Redis | latest | Async pipeline execution |
| DB | PostgreSQL | 16 | Primary data store |
| Migrations | Alembic | latest | Schema version control |
| Auth | JWT (python-jose) | — | Access + refresh tokens |
| Validation | Pydantic v2 | — | Request/response schemas |
| Rate limiting | slowapi | — | Auth endpoint protection |
| Logging | structlog | — | Structured JSON logs |

### Frontend

| Component | Technology | Version | Purpose |
|---|---|---|---|
| Framework | Next.js | 14 App Router | SSR + RSC web app |
| Language | TypeScript | — | Type safety |
| Styling | Tailwind CSS | — | Utility CSS |
| Components | shadcn/ui | — | Radix-based components |
| Charts | Recharts | — | Pipeline analytics charts |
| State | TanStack Query | — | Server state + polling |
| Calendar | react-day-picker | 8.x | Date-range picker |

### ML / NLP

| Component | Technology | Purpose |
|---|---|---|
| Training framework | PyTorch | Model training |
| Pretrained model | XLM-R base (HuggingFace) | Multilingual encoder |
| PEFT | LoRA (PEFT library) | Parameter-efficient fine-tuning |
| Tokeniser | XLM-R SentencePiece | Trilingual tokenisation |
| OCR | Tesseract (`eng+sin+tam`) | Scanned gazette extraction |
| Language detection | fastText `lid.176.bin` | 176-language LID |
| PDF extraction | PyMuPDF + pdfplumber | Text PDF extraction |
| Inference | ONNX Runtime | Production inference |
| Vectors | ChromaDB | Semantic search (planned) |
| Summarisation | MarianMT | Trilingual summarisation (planned) |

### Infrastructure

| Component | Technology | Purpose |
|---|---|---|
| Web scraping | Scrapy | Gazette spider |
| Backend deployment | Fly.io (Singapore) | Low-latency LK region |
| Frontend deployment | Vercel | Next.js hosting |
| DB hosting | Aiven (cloud Postgres) | Managed PostgreSQL |
| Cache / queue | Redis | Celery + inference cache |
| Alerts | SendGrid + Twilio | Email + SMS |
| Annotation | Label Studio | ML training data |

---

## 10. Key Technical Concepts & Flows

### 10.1 End-to-End Data Flow (T+0 to T+24h)

```
T+0:00  Gazette published on documents.gov.lk
T+0:15  Celery Beat fires run_gazette_spider (daily 06:00 LKT)
        → GazetteSpider.parse() XPaths the listing page
        → Downloads PDF → m1/raw/SRC_GOV_EGZ/YYYY/MM/
        → INSERT m1_regulations (status='ingested')
        → Early-exit if gazette_date < date_from

T+0:30  extract_gazette.delay(regulation_id)
        → classify_pdf() determines text/hybrid/scanned
        → PyMuPDF / pdfplumber / Tesseract
        → UPDATE status='extracted', raw_text=...

T+0:45  preprocess_gazette.delay(regulation_id)
        → detect_language() → fastText lid.176.bin
        → is_likely_wijesekara() → convert if needed
        → clean_text() → extract_metadata() → chunk()
        → UPDATE status='preprocessed', cleaned_text=...
        → INSERT m1_regulation_penalties rows
        → INSERT m1_sub_documents rows

T+1:00  classify_gazette.delay() [NOT YET BUILT]
        → ONNX Runtime inference
        → UPDATE status='classified', regulatory_category=..., affected_sectors=...

T+2:00  summarise_gazette.delay() [NOT YET BUILT]
        → MarianMT trilingual summary
        → UPDATE status='summarised'

T+3:00  dispatch_alert.delay() [NOT YET BUILT]
        → Look up registered SMEs matching affected_sectors
        → SendGrid email + Twilio SMS
        → UPDATE status='alerted', alert_sent_at=NOW()
        → INSERT m1_propagation_events (channel='enigmatrix_alert', T3=NOW())
```

### 10.2 Temporal Split Rationale

The 70/15/15 temporal split is methodologically critical:
- Regulations evolve year-on-year in language patterns and topic distribution
- Random splits would let training data "see future" legislative patterns
- Temporal split simulates real deployment: model trained on historical data, tested on unseen future regulations
- The 30-day minimum test window ensures seasonal variation is represented

### 10.3 Active Learning Chicken-and-Egg Solution

Problem: uncertainty sampling requires a model; training requires labels.

Solution:
1. Annotate first 200 examples with no ML guidance (pure random sample, stratified)
2. Train v0 model on these 200
3. Score the remaining unlabelled pool with v0
4. Select highest-uncertainty examples for annotation round 2
5. Train v1, repeat until 800+ examples

### 10.4 Multi-Source Spider Refactor

Original design: single spider for `documents.gov.lk`. Refactored to:
- `BaseDocumentsGovLkSpider` — shared XPath patterns, auth, retry logic
- `EGZSpider`, `GZSpider`, `BILLSpider`, `ACTSpider` — subclasses with source-specific URL patterns
- `SourcesCatalogue` singleton — per-source specs (frequency, URL pattern, failure modes)
- Storage partitioned by source: `m1/raw/<source_id>/YYYY/MM/`

### 10.5 Admin-Curated Data Preservation

When an admin manually sets a penalty record (`is_admin_set=TRUE`), re-running `preprocess_gazette` preserves that row rather than overwriting it. The pipeline inserts new ML-extracted penalties with `sequence_idx` values above the admin row's index. This allows human expert knowledge to coexist with automated extraction.

### 10.6 Inference Cache Anti-Contamination

A naive cache keyed only on `text_hash` could theoretically return a cached result for Gazette A when classifying Gazette B that happens to have identical text (e.g. annual re-publication of unchanged schedules). The cache key includes `gazette_number` and `gazette_date` to prevent this cross-gazette contamination.

### 10.7 Aiven Connection Pool Math

- Aiven entry tier: ~20 max connections
- Celery with `--concurrency=2`: 2 fork workers × 3 conn slots = 6
- uvicorn: ~3 conn slots
- Peak: 9 connections (fits 20-conn budget with room for superuser-reserved slots)
- `pool_timeout=10` (fail-fast instead of 60s asyncpg default)

### 10.8 Spider Early-Exit Logic

documents.gov.lk lists gazettes in descending date order. When the spider sees a row with `gazette_date <