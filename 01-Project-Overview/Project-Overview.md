---
tags: [research, project-overview, vault-overview]
source: enigmatrix-docs/README.md + shared/research/Enigmatrix_Research_Proposal_Upgraded.md
layer: research
module: shared
---

# Project Overview — Enigmatrix

> One-page framing of the **Enigmatrix SME Regulatory Intelligence Platform**. For the formal proposal, see [Enigmatrix_Research_Proposal_Upgraded](Enigmatrix_Research_Proposal_Upgraded.md). For the problem statement, see [Core-Problem](Core-Problem.md). For research questions, see [Research-Question](Research-Question.md).

## What it is

A unified, multilingual web platform for Sri Lankan small- and medium-enterprises (SMEs) that automates four regulatory-intelligence functions:

| # | Module | What it does | Status |
|---|---|---|---|
| 1 | **Awareness Gap** | Ingests Official Gazette PDFs, classifies them into 12 SME categories + 10 sectors, alerts matched SMEs within 24 hours | 🟡 Pipeline scaffolded; XLM-R training pending |
| 2 | **Knowledge Hub** | Retrieval-augmented Q&A over gazettes + regulatory KB, with citation-grounded answers | 🟡 ChromaDB scaffolded; ingestion + eval harness pending |
| 3 | **Risk Scoring** | Predicts SME regulatory non-compliance risk score with SHAP explanations | 🔲 Architecture designed; training data not yet collected |
| 4 | **Misinformation Classifier** | 9-class classifier distinguishing authentic regulatory info from 8 misinformation patterns | 🔲 Data sources + Perplexity prompt drafted; classifier not yet trained |

## Why now

- SMEs are **52 % of Sri Lankan GDP** and **45 % of employment** but have **no monitoring infrastructure** equivalent to what large enterprises operate internally.
- **34 % of SME penalty assessments** in 2023 (IRD) were against amendments gazetted more than 90 days prior — measurable, addressable information asymmetry.
- Off-the-shelf legal-NLP tooling is English-only and trained on US/EU corpora — the Sri Lankan trilingual (EN/SI/TA), low-resource, scanned-PDF context is unaddressed in the literature.

## How the modules connect

```
Official Gazette (PDF)
   ↓ ingest + extract + classify (Module 1)
Structured regulatory record + sector mapping + EN/SI/TA summary
   ↓                                    ↓                     ↓
 Module 2 Q&A                Module 3 risk score      Module 4 verifies
 (RAG over corpus)           (XGBoost + SHAP)         social-media claims
   ↓                                    ↓                     ↓
            Unified SME-facing platform (Next.js)
                          ↓
            SMEs receive alerts, query KB, see their
            risk score, and verify claims they encounter
```

## Technology stack

| Layer | Stack |
|---|---|
| Backend | FastAPI · SQLAlchemy async · Alembic · Celery |
| Frontend | Next.js 14 (App Router) · Tailwind · next-intl (EN/SI/TA) |
| Data | PostgreSQL 16 (truth) · ChromaDB (vectors) · Object storage (PDFs) |
| ML | PyTorch · HuggingFace Transformers (XLM-R + LoRA) · XGBoost · MarianMT · MLflow · Optuna |
| Infra | Docker Compose (local) · GitHub Actions · Prometheus + Grafana · nginx |

Detailed justifications: [03_Technology_Justification](../02-Research-Modules/2%20Module-2-Knowledge-Hub/03_Technology_Justification.md).

## What is novel

1. **First measured Sri Lankan regulatory information-diffusion dataset** — 200+ regulations × 4+ channel stages × 100+ SME survey respondents.
2. **Low-resource trilingual NLP pipeline** with empirical validation across EN/SI/TA Tesseract OCR, Wijesekara-font legacy gazettes, and XLM-R fine-tuning on a hand-annotated 800-example corpus.
3. **Unified four-module platform** where the same gazette ingestion feeds awareness alerts, RAG retrieval, risk scoring, and misinformation verification — vs the prior art's single-purpose systems.

## Where to go next

- [Core-Problem](Core-Problem.md) — the empirical problem
- [Research-Question](Research-Question.md) — RQ1–RQ4 with success criteria
- [Unified-Platform](Unified-Platform.md) — how the four modules share infra and data
- [Module 1 deep-dive](../02-Research-Modules/1%20Module-1-Awareness-Gap/00_INDEX.md) — 61-doc technical specification (the flagship deliverable)
- [Timeline](../06-Timeline/00_Timeline_Overview.md) — phases and milestones
- [Team-Roles](../07-Team/Team-Roles.md) — who is doing what
