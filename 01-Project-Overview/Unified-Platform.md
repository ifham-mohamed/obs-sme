---
tags: [research, architecture, cross-module]
source: enigmatrix-docs/shared/research/07_System_Architecture.md + shared/research/13_Unified_Survey_Architecture.md
layer: research
module: shared
---

# Unified Platform — How the Four Modules Connect

> One-page synthesis of the unified architecture. Deep technical detail: [07_System_Architecture](../02-Research-Modules/2%20Module-2-Knowledge-Hub/07_System_Architecture.md) and [10_Unified_Survey_Architecture](../02-Research-Modules/2%20Module-2-Knowledge-Hub/10_Unified_Survey_Architecture.md).

## The unification claim

Enigmatrix is one platform, not four. The four modules share:

1. **One identity model** — SMEs register once; the same record powers alert delivery (M1), Q&A history (M2), risk scoring (M3), and misinformation reporting (M4).
2. **One regulatory taxonomy** — the 12 categories and 10 sectors defined for M1 are used by every downstream module.
3. **One survey infrastructure** — a unified survey engine ([10_Unified_Survey_Architecture](../02-Research-Modules/2%20Module-2-Knowledge-Hub/10_Unified_Survey_Architecture.md)) serves both research instruments (M1 awareness survey) and operational questionnaires (M3 risk profile, M4 misinformation reports).
4. **One data architecture** — three stores: PostgreSQL (truth), ChromaDB (vectors), object storage (PDFs). Every module reads/writes through this triad. See [03_Architecture](../04-Technology-Stack/shared/03_Architecture.md).

## Five-layer system view

```
┌──────────────────────────────────────────────────────────────┐
│ L1  Presentation     Next.js 14 (SME dashboard + admin)      │
├──────────────────────────────────────────────────────────────┤
│ L2  API              FastAPI (auth, surveys, alerts, RAG)    │
├──────────────────────────────────────────────────────────────┤
│ L3  Business logic   Scoring engine · Survey state machine   │
│                      Alert routing · Misinformation router   │
├──────────────────────────────────────────────────────────────┤
│ L4  ML services      M1 classifier · M2 retriever · M3 risk  │
│                      M4 misinformation · MarianMT translate  │
├──────────────────────────────────────────────────────────────┤
│ L5  Data             PostgreSQL · ChromaDB · Object storage  │
│                      Redis (Celery broker) · Prometheus/Graf │
└──────────────────────────────────────────────────────────────┘
```

## Data flow — a single regulation, end-to-end

1. **T+0h** Gazette appears on `gazette.lk`. Scrapy spider notices within polling interval.
2. **T+0–6h** PDF downloaded → text extracted (PyMuPDF or Tesseract) → segmented into notices → stored.
3. **T+6h** XLM-R classifier assigns category + sectors. Low confidence → `needs_review` queue for admin.
4. **T+6h** MarianMT generates EN/SI/TA summary; stored alongside the record.
5. **T+6–24h** Alert dispatcher matches the regulation against subscribed SMEs (sector × category) and sends email/SMS/dashboard notification.
6. **T+24h+** SME views regulation in dashboard → can (a) ask Module 2 a question about it, (b) see Module 3 update their risk score based on this regulation's enforcement-history features, (c) flag Module 4 if they have seen contradictory claims circulating.
7. **T+continuous** Module 1's `m1_propagation_events` table accumulates timestamps for the lag-measurement research output.

## Survey unification

A single survey engine drives:

- M1 SME awareness survey (research instrument — RQ3, RQ4)
- M3 SME risk profile (operational — feeds the risk model)
- M4 SME misinformation report (operational — feeds the classifier with field examples)
- M2 KB satisfaction survey (operational — feeds retrieval-quality eval)

Sessions, branching, validation rules, multilingual rendering (EN/SI/TA), and resumability are all handled centrally. See [10_Unified_Survey_Architecture](../02-Research-Modules/2%20Module-2-Knowledge-Hub/10_Unified_Survey_Architecture.md) and [09_SME_Questionnaire_Design](../02-Research-Modules/2%20Module-2-Knowledge-Hub/09_SME_Questionnaire_Design.md).

## Why this matters academically

The unification is itself a contribution: prior work on regulatory NLP (Chalkidis 2019, Bommarito 2018), retrieval-augmented Q&A (Lewis 2020), risk modelling (gradient boosting + SHAP), and misinformation classification have all been studied in isolation. The integrated platform — built around one taxonomy, one identity model, and one survey infrastructure — lets us evaluate whether the modules reinforce each other empirically (e.g., does an SME's M2 query frequency predict their M3 risk reduction over time?).

## Where to go next

- [04-Technology-Stack/shared/03_Architecture](../04-Technology-Stack/shared/03_Architecture.md) — full architecture spec
- [04-Technology-Stack/shared/08_Testing](../04-Technology-Stack/shared/08_Testing.md) — test pyramid across the unified platform
- [Research-Question](Research-Question.md) — RQs at the module level
- [Module 1 — Full System Architecture](../02-Research-Modules/1%20Module-1-Awareness-Gap/08_M1_Full_System_Architecture.md) — the deepest single-module view
