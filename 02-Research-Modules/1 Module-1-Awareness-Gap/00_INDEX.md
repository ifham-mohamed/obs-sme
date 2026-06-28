# Enigmatrix Research Guide — Master Index

**Project:** SME Regulatory Intelligence Platform
**Group:** Enigmatrix | Faculty of Information Technology | University of Moratuwa
**Level 04 Final Year Research Project | 2026**

This guide answers every question raised in your concerns document and provides a complete, structured roadmap for executing the research project. It is organized into three logical layers:

---

## Layer 1 — Foundational Concepts (Files 01–05)

These files answer the conceptual "how does this all work" questions about AI/ML, research methodology, and technology choices.

| #   | File                                   | Covers                                                                                                         |
| --- | -------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| 01  | `01_AI_ML_Fundamentals.md`             | How models learn, training from scratch vs fine-tuning, what data is required, when to choose each approach    |
| 02  | `02_Complete_ML_Lifecycle.md`          | The full 9-step ML pipeline from problem definition through monitoring, with concrete examples for each module |
| 03  | `03_Research_Paper_Structure.md`       | How to structure research papers, what each section must contain, methodology writing, justification patterns  |
| 04  | `04_Technology_Stack_Justification.md` | Python, TensorFlow, PyTorch, Next.js, FastAPI, PostgreSQL — when to use each, why, advantages, limitations     |
| 05  | `05_Literature_Review_Guide.md`        | How to find papers, how to extract justifications, how to compare approaches, what to cite                     |

---

## Layer 2 — Data & System Architecture (Files 06–08)

These files answer how to collect data and build the supporting infrastructure for the research.

| # | File | Covers |
|---|------|--------|
| 06 | `06_Data_Collection_and_Management.md` | Survey design, web scraping ethics, public records, the database-driven data pipeline (replaces spreadsheets) |
| 07 | `07_System_Architecture.md` | Frontend (Next.js), Backend (FastAPI), Database (PostgreSQL), Vector DB (ChromaDB), ML serving layer |
| 08 | `08_SME_Questionnaire_Design.md` | Minimum required data per module, attribute selection, question wording, validation, sample size |

---

## Layer 3 — Module 1 Deep Dive (Files 09–12) ⭐

This is the section you specifically asked to be thoroughly detailed. These files take Module 1 (Regulatory Change Awareness Gap) from raw gazette PDF on `documents.gov.lk` all the way to a deployed alert system.

| # | File | Covers |
|---|------|--------|
| 09 | `09_Module1_Architecture_Overview.md` | The full Module 1 system architecture, all layers, all components, how they connect |
| 10 | `10_Module1_Gazette_PDF_Extraction_Pipeline.md` | Step-by-step: scraping, downloading, text extraction (PyMuPDF/pdfplumber), OCR fallback, section segmentation, legal-rule extraction, cleaning, storage |
| 11 | `11_Module1_NLP_Classifier_Training.md` | Step-by-step model training: data labeling, train/val/test split, TF-IDF baseline, fine-tuning XLM-R, evaluation, deployment |
| 12 | `12_Module1_End_to_End_Workflow.md` | The complete loop: gazette → extraction → classification → lag measurement → SME survey integration → alert generation → validation |

---

## How to Use This Guide

1. **First read:** `01` and `02` to understand the AI/ML fundamentals if you are unsure how training actually works.
2. **For your supervisor meeting:** Use `03` (paper structure) and `04` (tech justification) — these answer "why this technology" questions.
3. **For your individual module work:** Each member reads `06`, `07`, `08` and then their module-specific guide. Module 1 owner reads files `09–12` in order.
4. **For implementation:** File `10` is your build instruction set for the data extraction layer, file `11` is your build instruction set for the model layer, file `12` ties it all together.

---

## Quick Answers to Your Top Concerns

| Your Concern | Short Answer | Detailed In |
|--------------|--------------|-------------|
| Train from scratch or fine-tune? | **Fine-tune.** You do not have the data, compute, or time to train from scratch. | `01` |
| What does "training" actually do internally? | Adjusts millions of numerical weights so that input → output mapping minimizes a loss function. | `01` |
| Is database-driven training a good architecture? | **Yes** — it solves duplicate detection, training-status tracking, and scalability problems that spreadsheets cannot. | `06`, `07` |
| Is Next.js + PostgreSQL + FastAPI suitable? | **Yes** — this is a mainstream, well-documented research stack. Justifications in `04`. | `04`, `07` |
| How do we structure research papers? | IMRaD-extended structure with module-specific sub-sections. Template provided. | `03` |
| How do we get gazette data and turn it into model input? | Scrape → download PDF → extract text → segment → classify → store. Fully detailed pipeline. | `10` |
| How do we actually train the Module 1 classifier? | Label ~500–1000 examples → split → train baseline → fine-tune transformer → evaluate → deploy. Full code patterns provided. | `11` |

---

## Document Status

All 12 documents in this guide are complete, self-contained, and ready to be used as both planning documents and implementation references. They are written in plain Markdown and can be opened in any editor, converted to PDF/Word, or used directly as supplementary material in your thesis appendix.
