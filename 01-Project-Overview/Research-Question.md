---
tags: [research, module-1, module-2, module-3, module-4, research-questions]
source: enigmatrix-docs/m1/01_M1_Research_Problem.md
layer: research
module: shared
---

# Research Questions

> Formal research questions across all four Enigmatrix modules. The Module 1 RQs are primary (anchored in measurable empirical contribution); Modules 2–4 carry supporting RQs.

## Module 1 — Regulatory Awareness Gap (primary)

| # | Question | Method | Success Criterion |
|---|---|---|---|
| **RQ1** | Can NLP classify Sri Lankan gazettes into SME-relevant categories with macro F1 ≥ 0.92? | Fine-tuned XLM-R + LoRA on ≥ 800 labeled examples (≥ 50/category) | Macro F1 ≥ 0.92 on 15 % held-out test set |
| **RQ2** | Can multilingual models handle English/Sinhala/Tamil gazette text without per-language pipelines? | XLM-R vs mBERT vs IndicBERT ablation | F1 within 5 % across all three languages |
| **RQ3** | What is the median information lag between gazette publication and SME awareness? | Propagation event timestamps + paired SME awareness survey | Dataset of ≥ 200 regulations × ≥ 4 channel stages, ≥ 100 SME respondents |
| **RQ4** | Which dissemination channels deliver regulatory information fastest? | Channel-stratified lag analysis (portal, news, chamber, peer) | Ranked channel table with median lag in days |

### Formal problem statement (Module 1)

Given Sri Lankan Official Gazette PDFs $G = \{g_1, \ldots, g_n\}$ published at $T = \{t_1, \ldots, t_n\}$, construct an automated pipeline $P$ such that:

1. Each $g_i$ is ingested within 6 hours of publication
2. Classifier $C$ assigns $g_i$ to one of 12 regulatory categories with macro F1 ≥ 0.92
3. Sector mapper $S$ assigns $g_i$ to one or more of 10 SME industry sectors with F1 ≥ 0.88
4. Structured alerts reach matched SMEs within 24 hours of $t_i$

**Secondary question:** what is the measurable information lag $\Delta t = t_{\text{awareness}} - t_{\text{publication}}$, and which dissemination channels minimise it?

## Module 2 — Knowledge Hub (supporting)

- **RQ-M2.1:** Can a retrieval-augmented Q&A system answer SME compliance queries with citation-grounded responses, evaluated against a held-out expert-annotated benchmark?
- **RQ-M2.2:** Does ChromaDB-backed dense retrieval over gazette + regulatory-knowledge-base content reduce answer hallucination rate vs an unretrieved baseline?

See: [Module 2 Knowledge Architecture](../02-Research-Modules/2%20Module-2-Knowledge-Hub/13_Module2_Knowledge_Architecture.md)

## Module 3 — Risk Scoring (supporting)

- **RQ-M3.1:** Can a gradient-boosting model predict an SME's regulatory non-compliance risk score from sector, size, historical penalties, and disclosure features with AUROC ≥ 0.80?
- **RQ-M3.2:** Do SHAP-based explanations of the risk score change SME compliance behaviour relative to an unexplained score?

See: [Module 3 Risk Architecture](../02-Research-Modules/3%20Module-3-Risk/01_Module3_Risk_Architecture.md)

## Module 4 — Misinformation Classification (supporting)

- **RQ-M4.1:** Can a 9-class classifier distinguish authentic regulatory information from each of 8 misinformation patterns (rumour, false-attribution, outdated-recycled, fabricated-source, partial-truth, sarcasm-misread, premature-leak, scam) with macro F1 ≥ 0.78 on Sri Lankan social-media data?
- **RQ-M4.2:** Does a Perplexity-API verification layer reduce false-positive flagging on legitimate regulatory news?

See: [Module 4 Misinformation Architecture](../02-Research-Modules/4%20Module-4-Misinformation/01_Module4_Misinformation_Architecture.md)

## Cross-module integration

The four modules share the SME identity model, the regulatory taxonomy, and the lag dataset. Module 1 produces the labelled gazette corpus that Modules 2–4 consume; Module 3's risk score is informed by Module 1's alert delivery records; Module 4's classification influences which Module 1 alerts are confidence-weighted.

## Where to go next

- [Core-Problem](Core-Problem.md) — the problem this set of RQs addresses
- [Project-Overview](Project-Overview.md) — module-level wiring
- [Unified-Platform](Unified-Platform.md) — how the modules combine into one platform
