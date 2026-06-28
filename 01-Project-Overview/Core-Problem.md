---
tags: [research, module-1, problem-statement]
source: enigmatrix-docs/m1/01_M1_Research_Problem.md
layer: research
module: m1
---

# Core Problem — The SME Regulatory Awareness Gap

> One-page framing of the central problem. Full technical statement and research questions live in [01_M1_Research_Problem](../02-Research-Modules/1%20Module-1-Awareness-Gap/01_M1_Research_Problem.md).

## In one sentence

Sri Lankan SMEs systematically miss regulatory changes because the Official Gazette publishes ~500 binding amendments a year in three languages, as unstructured PDFs, with no push-notification infrastructure, no machine-readable metadata, and a median 33–70 day diffusion lag to the average SME.

## Why this matters

- SMEs represent **52% of Sri Lanka's GDP** and **45% of employment** (Department of Census and Statistics, 2022).
- The IRD's 2023 Annual Report records that **34% of SME penalty assessments** arose from non-compliance with amendments gazetted more than 90 days prior.
- EPF field audits (2022–2023) found **61% of audited SMEs were unaware** of at least one EPF contribution-rate change in the previous 12 months.
- This is not wilful non-compliance — it is a measurable, addressable information asymmetry.

## Why it has not been solved

| Structural barrier | Effect |
|---|---|
| Gazettes are PDFs, not data | No API, no push, no metadata beyond volume/part/date. |
| Three languages (EN/SI/TA), mixed encodings | Off-the-shelf NLP tooling struggles with Sinhala/Tamil (Wijesekara fonts, low-resource embeddings). |
| Scanned-image PDFs for older gazettes | OCR fallback required; quality varies. |
| Secondary dissemination (newspapers, ministry portals, chambers) | Adds 7–58 day median lag. |
| No prior empirical measurement of the diffusion lag in Sri Lanka | We cannot quantify the gap — only assert it. |

## What we are doing about it

Module 1 of Enigmatrix builds an automated pipeline that:

1. **Ingests** every gazette within 6 hours of publication (Scrapy spider over [gazette.lk](https://www.gazette.lk) / [documents.gov.lk](https://documents.gov.lk))
2. **Extracts** text via PyMuPDF + pdfplumber, with Tesseract OCR fallback for scanned pre-2018 documents
3. **Classifies** each notice into one of 12 SME-relevant regulatory categories (XLM-R + LoRA, target macro F1 ≥ 0.92)
4. **Maps** to one or more of 10 SME industry sectors (target F1 ≥ 0.88)
5. **Translates / summarises** into EN/SI/TA (MarianMT)
6. **Alerts** matched SMEs within 24 hours via email/SMS/dashboard
7. **Measures** the lag $\Delta t = t_{\text{awareness}} - t_{\text{publication}}$ via timestamps + a paired SME awareness survey

## Two simultaneous research outputs

| Output | Academic value | Practical value |
|---|---|---|
| **Deployed alert system** | NLP feasibility in a low-resource multilingual setting | Reduces SME awareness lag from 33–70 days to < 24 hours |
| **Empirical lag dataset** | First quantified measurement of Sri Lankan regulatory information diffusion | Evidence for government / chambers to reform dissemination |

## Where to go next

- [Research-Question](Research-Question.md) — RQ1–RQ4 with method + success criteria
- [Project-Overview](Project-Overview.md) — how Module 1 connects to Modules 2–4
- [Module 1 deep-dive](../02-Research-Modules/1%20Module-1-Awareness-Gap/00_INDEX.md) — full 61-doc technical specification
