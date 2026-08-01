# Official Template Structure Map

Created: 2026-07-30
Purpose: map the B21 FYP final-report template onto the Enigmatrix content, and record what is still open in each section.

Companion: [[00_FINAL_REPORT_CONTEXT_INDEX]] · [[03_M1_EVIDENCE_EVALUATION_AND_COMMANDS]]

## What changed in the second pass

The first draft used a self-invented 7-chapter structure (Introduction, Related Work, Technology, Design & Methodology, Implementation, Testing & Evaluation, Conclusion). The faculty template is different in three material ways:

1. It has **9 chapters**, and separates **Approach** (Chapter 4, input/process/output per module) from **Analysis and Design** (Chapter 5, architecture and diagrams).
2. **Evaluation is Chapter 7** and requires a dedicated **7.1 Metrics Used** section defining accuracy, precision, recall and F1 individually before any results appear.
3. **References is Chapter 9**, and there are exactly two appendices: **A — Individual Contribution** and **B — Additional Implementation Details**.

The report was rebuilt to the template. Front matter (title page, dissertation page, declaration, acknowledgment, abstract, TOC, list of figures, list of tables) was added, which the first draft lacked.

## Section-by-section map

| Template section | Enigmatrix content | Open items |
|---|---|---|
| Title page / dissertation page | Project title, team name, three index numbers | Supervisor names, month, degree name; confirm whether the group has a fourth member |
| DECLARATION | Standard wording, four signature lines | Signatures, date |
| ACKNOWLEDGMENT | Draft supplied | Adapt and sign off |
| ABSTRACT | ~330 words: problem, four modules, Module 1 method, headline numbers, contribution | None |
| 1.1 Introduction | Domain framing: gazette publication vs SME consumption | None |
| 1.2 Background and Motivation | Four existing approaches and why each falls short; information-asymmetry framing | None |
| 1.3 Problem in Brief | One-sentence statement + four gaps mapped to four modules | None |
| 1.4.1 Aim | Single sentence | None |
| 1.4.2 Objectives | 10 numbered objectives + Table 1.1 with RQ1–RQ4 | None |
| 1.5.1–1.5.4 Modules | Module 1 in 10 numbered functions; M2/M3/M4 placeholders | Other members |
| 1.5.5 Flow of the Overall System | Figure 1.1 (Mermaid) | Render and insert PNG |
| 2.2 Overall Related Work | 8 subsections: SME compliance, information asymmetry, RegTech, multilingual NLP, RAG, risk, misinformation, synthesis | None |
| 2.3.1 Module 1 related work | 4 strands + explicit gap statement | None |
| 2.3.2–2.3.4 | Structured placeholders with reference numbers pre-assigned | Other members |
| 3.2 Programming Languages | 9 subsections: FastAPI/Celery, Scrapy, PDF/OCR, fastText, PyTorch/PEFT, scikit-learn, ONNX, NLLB, TypeScript | None |
| 3.3 Cloud and Compute Platforms | Table 3.5: local CPU, Colab, Kaggle, Railway, Vercel, managed Postgres, with the Colab-vs-Kaggle rationale | Fill actual GPU model and runtime |
| 3.4 Other Tools | Label Studio, Docker, uv, pytest, Playwright, data-quality suites, Obsidian, Git, Mermaid | None |
| 4.2 Module 1 I/P/O | Tables 4.1 and 4.2 + Figure 4.1 | Render Figure 4.1 |
| 4.3–4.5 | I/P/O placeholders for M2/M3/M4 | Other members |
| 5.2 Overall architecture | Figure 5.1 (embedded) + Figure 5.2 component view + DFDs, class, sequence, ER (embedded) + Table 5.1 | Render Figure 5.2 |
| 5.3.1 Module 1 design | Figure 5.8 (embedded) + status machine, extraction routing, dual head, propagation (Mermaid) + Tables 5.2, 5.3 | Render Figures 5.9–5.12 |
| 5.3.2–5.3.4 | Interim pipeline diagrams embedded as starting points | Other members replace with implemented designs |
| 6.2 Data Collection | Table 6.1 (five datasets), scraping, 6-step annotation protocol, Listing 6.1, Table 6.2 | Label Studio screenshot |
| 6.3.1 Module 1 implementation | Nine subsections across the five phases, Listings 6.2–6.4, seven screenshot slots | Screenshots |
| 6.3.1.5 GPU training | Identical command for Colab and Kaggle, with the Kaggle Datasets versioning note | Kaggle/Colab screenshot |
| 7.1 Metrics Used | 7.1.1 Accuracy, 7.1.2 Precision, 7.1.3 Recall, 7.1.4 F1 (+ macro-F1), then kappa, field/stage accuracy, CER/WER, ECE/Brier, lag metrics, KL drift | None |
| 7.2.1 Module 1 evaluation | Nine subsections: setup, dataset, IAA, extraction, baselines, smoke test, GPU results, diffusion, reproducibility commands | GPU run, measurement run, findings, translation review |
| 7.3 Overall System Evaluation | 7.3.1 integration (Table 7.23, 8 test cases), 7.3.2 results (Table 7.24), 7.3.3 discussion with strengths, weaknesses and threats to validity | Integration results |
| Chapter 8 Conclusion | Achievement against objectives, five contributions, limitations, near/medium/long-term future work | None |
| Chapter 9 References | 55 IEEE-numbered entries | None |
| Appendix A | A.1 written in full (design, data, implementation, modelling, research, documentation) | A.2–A.4 by other members |
| Appendix B | B.1 artefact inventory, B.2 annotation guideline, B.3 evaluation assumptions + error taxonomy + bands, B.4 figure rendering, B.5 screenshot checklist, B.6 placeholder checklist | None |

## Code listings included

Real excerpts, not paraphrase. Any change to these files should be mirrored in the report.

| Listing | Source file | Shows |
|---|---|---|
| 6.1 | `enigmatrix-ml/m1/model/labels.py` | The 8-category / 3-sector schema and multi-hot sector encoding |
| 6.2 | `enigmatrix-ml/m1/model/architecture.py` | `GazetteClassifier` — LoRA injection, CLS pooling, dual head, CE + BCE loss |
| 6.3 | `enigmatrix-ml/m1/model/config.py` | `ModelConfig` — LoRA and optimisation hyper-parameters, three seeds |
| 6.4 | `enigmatrix-ml/m1/model/promotion.py` | `decide()` — the 0.92 gate and regression tolerance |

## Code fixes applied on 2026-07-30

Stale comments that contradicted the current taxonomy were corrected so the listings in the report match the repository:

- `m1/model/config.py` — comments said 12 categories and 12 sectors; now 8 and 3.
- `m1/model/architecture.py` — docstring said "12-way category head / 10-way sector head"; now describes the widths as driven by `ModelConfig`.

## Rebuild procedure

1. Edit `Enigmatrix_Final_Report_Master.md`.
2. Double-click `Build_Final_Report_DOCX.bat`.
3. Open the `.docx`; when Word asks to update fields, choose **Yes** — this populates the Table of Contents, List of Figures and List of Tables.
4. Save.

The builder understands: `<!--TITLEPAGE-->`, `<!--PAGEBREAK-->`, `<!--TOC-->`, `<!--LOF-->`, `<!--LOT-->`, `>>FIGCAP<<`, `>>TABCAP<<`, `![](path)` images, and fenced blocks tagged `mermaid`, `figure`, `screenshot` or a language name.
