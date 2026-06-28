# Enigmatrix Research Guide — Master Index

**Project:** SME Regulatory Intelligence Platform
**Group:** Enigmatrix | Faculty of Information Technology | University of Moratuwa
**Level 04 Final Year Research Project | 2026**

This guide answers the conceptual and methodological questions behind the research project. It pairs with the engineering companion at [`docs/BUILD_PLAN/`](../BUILD_PLAN/BUILD_00_INDEX.md) — research files answer *what is the science and why*, BUILD files answer *how do we ship it*.

> **Looking for run-instructions, not the methodology?** See [`docs/SETUP/00_INDEX.md`](../SETUP/00_INDEX.md) — the onboarding/setup track for the MVP that ships today.

---

## Layer 1 — Foundational Concepts (Files 01–05)

Conceptual "how does this all work" answers about AI/ML, research methodology, and technology choices.

| #   | File                                                                                  | Covers                                                                                                         |
| --- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| 01  | [`01_AI_ML_Fundamentals.md`](01_AI_ML_Fundamentals.md)                                | How models learn, training from scratch vs fine-tuning, what data is required, when to choose each approach    |
| 02  | [`02_Complete_ML_Lifecycle.md`](02_Complete_ML_Lifecycle.md)                          | The full 9-step ML pipeline from problem definition through monitoring, with concrete examples for each module |
| 03  | [`03_Research_Paper_Structure.md`](03_Research_Paper_Structure.md)                    | How to structure research papers, what each section must contain, methodology writing, justification patterns  |
| 04  | [`04_Technology_Stack_Justification.md`](04_Technology_Stack_Justification.md)        | Python, PyTorch, XLM-R, Next.js, FastAPI, PostgreSQL, ChromaDB — when to use each, advantages, limitations     |
| 05  | [`05_Literature_Review_Guide.md`](05_Literature_Review_Guide.md)                      | How to find papers, extract justifications, compare approaches, what to cite                                   |

---

## Layer 2 — Data & System Architecture (Files 06–08)

How data is collected and how the supporting infrastructure is built.

| #  | File                                                                            | Covers                                                                                                            |
| -- | ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 06 | [`06_Data_Collection_and_Management.md`](06_Data_Collection_and_Management.md)  | Survey design, web scraping ethics, public records, the database-driven data pipeline (replaces spreadsheets). **Reflects April 2026 budget thresholds — see top-of-file note.** |
| 07 | [`07_System_Architecture.md`](07_System_Architecture.md)                        | Frontend (Next.js), Backend (FastAPI), Database (PostgreSQL), Vector DB (ChromaDB), ML serving layer              |
| 08 | [`08_SME_Questionnaire_Design.md`](08_SME_Questionnaire_Design.md)              | Minimum required data per module, attribute selection, question wording, validation, sample size                  |

---

## Layer 3 — Module 1 Deep Dive (Files 09–12)

Module 1 (Regulatory Change Awareness Gap) from raw gazette PDF on `documents.gov.lk` all the way to a deployed alert system.

| #  | File                                                                                                          | Covers                                                                                                                  |
| -- | ------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 09 | [`09_Module1_Architecture_Overview.md`](09_Module1_Architecture_Overview.md)                                  | Full Module 1 system architecture, all layers, all components, how they connect                                         |
| 10 | [`10_Module1_Gazette_PDF_Extraction_Pipeline.md`](10_Module1_Gazette_PDF_Extraction_Pipeline.md)              | Scraping, downloading, text extraction (PyMuPDF/pdfplumber), OCR fallback, section segmentation, cleaning, storage     |
| 11 | [`11_Module1_NLP_Classifier_Training.md`](11_Module1_NLP_Classifier_Training.md)                              | Data labeling, train/val/test split, TF-IDF baseline, fine-tuning XLM-R, evaluation, deployment                         |
| 12 | [`12_Module1_End_to_End_Workflow.md`](12_Module1_End_to_End_Workflow.md)                                      | Gazette → extraction → classification → lag measurement → SME survey integration → alert generation → validation       |

---

## Layer 4 — Module 2/3/4 Architectures (Files 13–15) — *new*

Theoretical / methodological chapters for the remaining three modules. Each pairs with the engineering BUILD file noted in the right column.

| #  | File                                                                                                          | Covers                                                                                                | Engineering pair |
| -- | ------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ---------------- |
| 13 | [`13_Module2_Knowledge_Architecture.md`](13_Module2_Knowledge_Architecture.md)                                | Compliance-knowledge instrument design, validity/reliability theory, RAG-as-pedagogy framing, ethics  | [`BUILD_08`](../../backend/BUILD_PLAN/BUILD_08_Module2_Knowledge.md) |
| 14 | [`14_Module3_Risk_Architecture.md`](14_Module3_Risk_Architecture.md)                                          | Compliance-failure feature taxonomy, gradient-boosted-trees justification, fairness, SHAP-for-policy  | [`BUILD_09`](../../backend/BUILD_PLAN/BUILD_09_Module3_Risk.md)     |
| 15 | [`15_Module4_Misinformation_Architecture.md`](15_Module4_Misinformation_Architecture.md)                      | Misinfo typology, multilingual NLP rationale, RAG-verifier theory, ethics of social-media scraping    | [`BUILD_10`](../../backend/BUILD_PLAN/BUILD_10_Module4_Misinformation.md) |

### Supplementary — Engineering architecture reference (Session 16+)

| File | Covers | Engineering pair |
| ---- | ------ | ---------------- |
| [`13_Unified_Survey_Architecture.md`](13_Unified_Survey_Architecture.md) | Session-based survey architecture shipped in Sessions 16–19: `survey_sessions` table + schema, 6-endpoint API (`POST /start`, `GET /next-question`, `POST /answer`, `POST /complete`, `GET /my-history`, `GET /{id}`), five survey modes (`per_module_m1/m2/m3/m4`, `unified`) with question caps, `survey_limits` singleton, `SurveyLauncher` + `SurveyWizard` frontend loop, `module_number` 1/2/3/4 convention (Session 19). | [`SETUP/13_Unified_Survey_Configuration.md`](../../frontend/SETUP/13_Unified_Survey_Configuration.md) |

---

## Layer 5 — Cross-Cutting Reference Documents

Long-form supporting material that does not fit the numbered-guide cadence.

| File                                                                                                                  | Type        | Covers                                                                                                  |
| --------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------- |
| [`Enigmatrix_Research_Proposal_Upgraded.md`](Enigmatrix_Research_Proposal_Upgraded.md)                                | Markdown    | The current research proposal — module scopes, schemas, technology stack, ML lifecycle per module. **Most up-to-date scope statement.** |
| [`module_1_and_4_data_architecture.md`](module_1_and_4_data_architecture.md)                                          | Markdown    | Joint Module 1 + 4 data architecture: gazette tables, social-media tables, schema source-of-truth for BUILD_07/10 |
| [`module_2_and_3_data_architecture.md`](module_2_and_3_data_architecture.md)                                          | Markdown    | Joint Module 2 + 3 data architecture: question bank, survey schemas, **canonical April-2026 thresholds** (VAT/SSCL 36M, VAT 18%) |
| [`Module_1_Regulatory_Change_Awareness_Gap.md.pdf`](Module_1_Regulatory_Change_Awareness_Gap.md.pdf)                  | PDF (~614 KB) | Standalone Module 1 dossier — useful as a thesis appendix exhibit                                       |
| [`G28 - Enigmatrix - Interim Report.pdf`](G28%20-%20Enigmatrix%20-%20Interim%20Report.pdf)                            | PDF (~1.1 MB) | Interim report submitted to faculty — preserves the project's historical state for the viva           |

---

## Research ↔ BUILD Crosswalk

Map each research file to the BUILD file(s) it informs. Use this to find "where is the engineering for this research idea" and vice versa.

| Research file               | BUILD counterpart(s)                                                                       | Direction          |
| --------------------------- | ------------------------------------------------------------------------------------------ | ------------------ |
| 01 AI/ML Fundamentals       | BUILD_11 (training infra), BUILD_07/08/09/10 (per-module training references)              | informs all        |
| 02 ML Lifecycle             | BUILD_11 (training pipeline + eval gates), BUILD_15 (drift monitoring, ML tests)           | informs cross-cut  |
| 03 Research Paper Structure | BUILD_16 (thesis-chapter mapping table)                                                    | thesis only        |
| 04 Tech Stack Justification | BUILD_01 (tooling), BUILD_03/04 (FastAPI/Postgres/Chroma), BUILD_05 (Next.js)             | informs Layer 1    |
| 05 Literature Review Guide  | (no direct BUILD; informs every module's discussion section)                                | thesis only        |
| 06 Data Collection          | BUILD_02 (folder layout), BUILD_04 (schema), BUILD_07/12 (ingestion)                       | informs all        |
| 07 System Architecture      | BUILD_02/03/04/05/06 (layered foundation), BUILD_14 (deployment topology)                  | informs foundation |
| 08 SME Questionnaire        | BUILD_08 (survey delivery + scoring)                                                       | M2                 |
| 09 Module 1 Architecture    | BUILD_07 (component map mirrors §1)                                                        | M1                 |
| 10 Module 1 Extraction      | BUILD_07 §3 (segmenter strategies), BUILD_12 §2/3 (gazette scrapers)                       | M1                 |
| 11 Module 1 Classifier      | BUILD_11 (training infra), BUILD_07 §5 (inference)                                         | M1 + cross-cut     |
| 12 Module 1 End-to-end      | BUILD_07 §10 (orchestration), BUILD_12 §8/9 (schedulers)                                   | M1                 |
| 13 Module 2 Architecture    | BUILD_08 (engineering pair)                                                                | M2                 |
| 14 Module 3 Architecture    | BUILD_09 (engineering pair)                                                                | M3                 |
| 15 Module 4 Architecture    | BUILD_10 (engineering pair)                                                                | M4                 |
| Research Proposal           | BUILD_00 (open questions), every module BUILD                                              | informs all        |
| `module_1_and_4_data_architecture.md` | BUILD_07/10 schema DDL                                                          | M1 + M4            |
| `module_2_and_3_data_architecture.md` | BUILD_08/09 schema DDL + April 2026 thresholds                                  | M2 + M3            |
| `13_Unified_Survey_Architecture.md` | Session-based survey API + `survey_sessions` / `survey_limits` schemas; `module_number` 1/2/3/4; shipped Sessions 16–19. Engineering counterpart: [`SETUP/13_Unified_Survey_Configuration.md`](../../frontend/SETUP/13_Unified_Survey_Configuration.md) | Platform-wide survey infra |

---

## How to Use This Guide

1. **First read:** `01` and `02` to understand the AI/ML fundamentals if you are unsure how training actually works.
2. **For your supervisor meeting:** Use `03` (paper structure) and `04` (tech justification) — these answer "why this technology" questions.
3. **For your individual module work:** Each member reads `06`, `07`, `08`, then their module-specific architecture file:
   - Module 1 owner → `09–12` then [`BUILD_07`](../../backend/BUILD_PLAN/BUILD_07_Module1_Awareness.md)
   - Module 2 owner → `13` then [`BUILD_08`](../../backend/BUILD_PLAN/BUILD_08_Module2_Knowledge.md)
   - Module 3 owner → `14` then [`BUILD_09`](../../backend/BUILD_PLAN/BUILD_09_Module3_Risk.md)
   - Module 4 owner → `15` then [`BUILD_10`](../../backend/BUILD_PLAN/BUILD_10_Module4_Misinformation.md)
4. **For implementation:** Switch to [`docs/BUILD_PLAN/BUILD_00_INDEX.md`](../BUILD_PLAN/BUILD_00_INDEX.md) and follow the BUILD package end-to-end.
5. **For thesis writing:** Use the chapter-mapping table in [`BUILD_16`](../BUILD_PLAN/BUILD_16_Progress_Tracker_Template.md) to know which file feeds which IMRaD section.

---

## Quick Answers to Top Concerns

| Concern                                                  | Short answer                                                                                | Detailed in   |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ------------- |
| Train from scratch or fine-tune?                         | **Fine-tune.** No data, compute, or time to train from scratch.                              | `01`          |
| What does training actually do internally?               | Adjusts millions of weights so input → output minimizes a loss function.                     | `01`          |
| Is database-driven training a good architecture?         | **Yes** — solves duplicate detection, training-status tracking, scalability.                | `06`, `07`    |
| Is Next.js + PostgreSQL + FastAPI suitable?              | **Yes** — mainstream, well-documented research stack.                                        | `04`, `07`    |
| How do we structure research papers?                     | IMRaD-extended structure with module-specific sub-sections. Template provided.               | `03`          |
| How do we get gazette data and turn it into model input? | Scrape → download PDF → extract → segment → classify → store. Detailed pipeline.             | `10`          |
| How do we train the Module 1 classifier?                 | Label ~500–1000 examples → split → baseline → fine-tune transformer → evaluate → deploy.    | `11`          |
| How do we measure SME compliance knowledge?              | Three triangulated instruments (awareness / knowledge test / vulnerability), CA-verified.   | `13`, `08`    |
| Why XGBoost, not deep learning, for risk?                | Tabular + small-n favours gradient-boosted trees; SHAP is built-in.                          | `14`          |
| How do we verify a misinformation claim?                 | RAG retrieval against M1 corpus + NLI head; verdict cites a specific gazette.                | `15`          |

---

## Open Project-Level Questions

These are mirrored in [`BUILD_00_INDEX.md`](../BUILD_PLAN/BUILD_00_INDEX.md) — listed here so research-stream readers see them too.

- **OQ1** Library *versions* not yet pinned across the stack.
- **OQ2** Per-module training hyperparameters (LR, batch, epochs) not locked.
- **OQ3** Ethics committee approval reference missing.
- **OQ4** NEDA / Chamber of Commerce survey-distribution partnership unconfirmed.

---

## Document Status

All 15 numbered guides plus `13_Unified_Survey_Architecture.md` (supplementary engineering reference), the proposal, two data-architecture deep-dives, and two PDF dossiers are complete and self-contained. They can be opened in any markdown editor, converted to PDF/Word, or used directly as supplementary material in the thesis appendix.

*Last refreshed: 2026-05-12 (Session 19).*
