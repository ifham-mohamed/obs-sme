# 03 — Research Paper Structure Guide

> Goal: tell you exactly what goes in each section of your research paper / thesis chapters, and how to write the methodology and justifications so they pass examiner scrutiny.

---

## 1. Two Document Types You Will Produce

| Document | Audience | Length | Tone |
|----------|----------|--------|------|
| **Final Year Thesis** | Supervisor + examiners | 60–120 pages | Academic, exhaustive, defensive |
| **Research Paper / Conference Submission** | Reviewers in the field | 6–12 pages | Concise, novel-claim-focused, results-heavy |

The thesis contains the paper. Same content, different compression.

---

## 2. Standard Structure (Extended IMRaD)

This is what your thesis must contain, in order. Each section's purpose and required content:

### Section 1 — Introduction (5–8 pages in thesis, 1 page in paper)

**Purpose:** Convince the reader the problem matters and is unsolved.

**Required sub-sections:**
1. **Background** — context about Sri Lankan SMEs and regulatory compliance. Use statistics: how many SMEs, % contribution to GDP, % facing penalties.
2. **Problem statement** — the precise problem in 2–3 sentences. *"Sri Lankan SMEs experience an unmeasured information lag between regulatory publication and their awareness of changes. This results in unintentional non-compliance and significant penalties. No prior work has quantified this lag."*
3. **Motivation** — why this matters now. Use real consequences: penalty amounts, business closures, regulatory complexity post-2022 economic crisis.
4. **Research questions** — list each module's research question explicitly, numbered.
5. **Objectives** — 5–7 bullet points, each starting with a verb (*"To measure...", "To classify...", "To build...", "To validate..."*).
6. **Scope and limitations** — what is in scope (Sri Lanka, tax/EPF/ETF/eROC), what is not (other developing countries, criminal law, other tax categories).
7. **Significance / contributions** — 4 novel datasets + 4 measurable findings, listed as bullets.
8. **Thesis structure** — one paragraph telling the reader what each subsequent chapter contains.

**Common mistake:** Background is too generic ("AI is transforming everything"). **Fix:** Be specific to Sri Lanka, to SMEs, to regulatory compliance.

---

### Section 2 — Literature Review (10–15 pages)

**Purpose:** Show you know what has been done and that what you are doing has not been done.

**Required sub-sections:**
1. **Domain background** — what is known about SME compliance challenges globally and in South Asia.
2. **Existing approaches by problem area:**
   - Information lag in regulatory communication (find any paper that measured this — even in other domains like medical guideline diffusion)
   - NLP for legal / regulatory text classification (cite EUR-Lex work, LEDGAR, LexGLUE benchmark)
   - Multilingual NLP for low-resource South Asian languages (cite XLM-R, IndicBERT, Sinhala/Tamil-specific work)
   - RAG for question-answering on legal / regulatory documents
   - Compliance risk prediction in finance / regtech
   - Misinformation detection on social media (especially low-resource languages)
3. **Technology comparison table** — for each major technology choice, cite 3–5 papers that used it.
4. **Identified gap** — explicit. *"While [X] has been studied in [Y context], no published work measures [your specific finding] for Sri Lanka or any comparable economy."*

**How to write this section:**
- For each paper you cite, in 2–4 sentences explain: what they did, what they found, what their limitation was. Then the next paragraph: how your work differs / extends.
- Use a **comparison table** at the end of the section showing your work in the same row format as the prior work.

| Work | Context | Method | Limitation | Our extension |
|------|---------|--------|------------|---------------|
| Smith et al. 2022 | EU regulations | Rule-based classifier | English only, EU-specific | Multilingual + Sri Lankan + lag measured |

**Common mistake:** Annotated bibliography style — listing papers one by one with no synthesis. **Fix:** Group by theme. Make every paragraph end with a comparison or critique.

---

### Section 3 — Proposed Solution (5–8 pages, one sub-section per module)

**Purpose:** Describe your system at a high level — the *what*, before the *how*.

**Required content per module:**
- **Objective** — what this module achieves.
- **Inputs** — what data feeds in.
- **Outputs** — what comes out and in what format.
- **Algorithms / techniques** — at a paragraph level, not code level.
- **Technologies used** — listed.
- **Justification** — why this approach over alternatives. (Cite from literature review.)
- **Architecture diagram** — a clean block diagram.

Then a section on the **integrated platform** showing how all 4 modules connect — reuse the table in your proposal.

**Common mistake:** Mixing the *what* with the *how* (implementation details). **Fix:** Save implementation for Methodology. This section is for design decisions.

---

### Section 4 — Methodology (15–25 pages — the largest section)

**Purpose:** Tell the reader exactly how you did the research, in enough detail that another researcher could replicate it.

**Required sub-sections per module:**

1. **Data acquisition** — sources, collection method, date ranges, volumes.
2. **Data preprocessing** — cleaning steps, normalization, deduplication, language handling.
3. **Labeling protocol** — categories defined, labeling guidelines summary, annotators, inter-annotator agreement (Cohen's Kappa).
4. **Train / validation / test split** — how the split was made, why (random vs temporal vs stratified).
5. **Model architecture** — which model, why, with citation. Diagram if non-trivial.
6. **Training procedure** — hyperparameters, optimizer, learning rate schedule, hardware, training time, library versions.
7. **Baselines** — list every baseline you compared against, with the same training/eval protocol.
8. **Evaluation metrics** — list every metric and explain why it is appropriate for this task.
9. **Statistical methodology** — confidence intervals, significance tests.
10. **Ethical considerations** — survey consent, data anonymization, ethics committee approval reference.

**The "What / Why / Where / When" pattern (use it for every methodological choice):**

> "**What:** We fine-tune XLM-RoBERTa-base on our regulatory change dataset.
> **Why:** XLM-R is pretrained on 100 languages including Sinhala and Tamil, supports cross-lingual transfer (Conneau et al., 2020), and outperforms mBERT on low-resource South Asian benchmarks.
> **Where:** Used in Module 1 to classify each gazette notice into one of 12 regulatory change categories.
> **When:** Applied after PDF extraction and section segmentation, before the lag-analysis stage."

**This pattern, applied to every choice, is the difference between a B+ and an A thesis.**

---

### Section 5 — Implementation (5–10 pages)

**Purpose:** Show the working system.

**Content:**
- System architecture diagram (frontend + backend + database + ML serving + data sources).
- Database schema (key tables).
- API endpoint list.
- Screenshots of the working application.
- Repository structure.
- Deployment description.

**Common mistake:** Pasting code listings. **Fix:** Code goes in appendix or repository. Implementation chapter is diagrams + descriptions + screenshots.

---

### Section 6 — Results & Evaluation (10–15 pages)

**Purpose:** Present your measurements honestly and analyze them.

**Required sub-sections per module:**

1. **Dataset statistics** — final dataset size, class distribution, language distribution, time coverage.
2. **Quantitative results** — main metric table comparing baselines vs your model.
3. **Per-class / per-slice analysis** — does the model perform worse on certain categories or languages?
4. **Error analysis** — sample wrong predictions, categorize the failure modes.
5. **Validation against research findings** — does your built solution actually reduce the measured barrier? (e.g. for Module 1: does your alert system reduce lag from `X` days to `Y` days?)
6. **Statistical significance** — confidence intervals, p-values for delta vs baseline.
7. **Comparison with prior work** — even if not directly comparable, contextualize.

**Two tables every results section needs:**

**Table 1 — Headline metrics**
| Model | Macro-F1 | Accuracy | Precision | Recall |
|-------|----------|----------|-----------|--------|
| Majority baseline | 0.08 | 0.31 | 0.10 | 0.31 |
| Rule-based | 0.42 | 0.51 | 0.45 | 0.50 |
| TF-IDF + LR | 0.61 | 0.65 | 0.63 | 0.62 |
| GPT-4 zero-shot | 0.68 | 0.71 | 0.70 | 0.69 |
| **XLM-R fine-tuned (ours)** | **0.83** | **0.85** | **0.84** | **0.83** |

**Table 2 — Slice analysis**
| Slice | XLM-R F1 | N |
|-------|----------|---|
| English | 0.87 | 245 |
| Sinhala | 0.81 | 178 |
| Tamil | 0.74 | 92 |
| Tax category | 0.86 | 280 |
| Labor category | 0.78 | 150 |

---

### Section 7 — Discussion (5–8 pages)

**Purpose:** Interpret what your results mean.

**Required content:**
- **Answer to each research question** — explicitly. *"RQ1 asked: what is the information lag? Our finding is X days median, Y days at 90th percentile."*
- **Implications** — for SMEs, for regulators, for similar economies.
- **Limitations** — be honest. Sample size, geographic bias, time period, language coverage gaps.
- **Threats to validity** — internal (confounders), external (generalizability), construct (does your metric measure what you claim).
- **Comparison to related work** — your numbers in context.

---

### Section 8 — Conclusion & Future Work (2–4 pages)

**Purpose:** Summarize and point forward.

**Required content:**
- **Summary of contributions** — bullet list of the 4 datasets and 4 findings.
- **Practical implications** — what should SMEs, regulators, NEDA do with this knowledge?
- **Future work** — 5–7 specific extensions (other countries, more languages, real-time deployment, integration with government APIs, longitudinal study).

---

### Section 9 — References

Use a consistent style: **IEEE** or **ACM** or **APA**. Pick one. Use a reference manager (Zotero, Mendeley) — never format references manually.

Aim for 40–80 references. Mix:
- Foundational ML / NLP papers (BERT, XLM-R, transformer)
- Domain papers (legal NLP, regtech)
- Sri Lanka / South Asia specific papers
- Government documents / official reports
- Methodology references (RAGAS, Cohen's Kappa, SHAP)

---

### Section 10 — Appendices

Put here:
- Survey instruments (full questionnaire)
- Labeling guidelines (full document)
- Database schema (full DDL)
- API endpoint specifications
- Hyperparameter search results
- Ethics approval letter
- Sample raw data (anonymized)

---

## 3. Per-Module Sub-Section Template

For consistency, every module's appearance in Methodology and Results uses the same sub-sections:

```
4.X Module N — [Name]
  4.X.1 Data acquisition
  4.X.2 Preprocessing
  4.X.3 Labeling protocol
  4.X.4 Splits
  4.X.5 Model architecture
  4.X.6 Training procedure
  4.X.7 Baselines
  4.X.8 Evaluation metrics

6.X Module N — [Name]
  6.X.1 Dataset statistics
  6.X.2 Quantitative results
  6.X.3 Per-slice analysis
  6.X.4 Error analysis
  6.X.5 Validation of solution
```

This makes the thesis easy to navigate and the comparison across modules trivial.

---

## 4. Justification Patterns — How to Defend Every Choice

Every methodological choice in your thesis must be defended in one of these ways:

| Justification type | Pattern | Example |
|--------------------|---------|---------|
| **Citation** | "X was used because [paper] showed it outperforms Y" | "XLM-R was selected because Conneau et al. (2020) demonstrated superior performance on cross-lingual classification benchmarks." |
| **Empirical** | "We compared X and Y on a pilot dataset; X outperformed Y" | "Pilot experiments on 200 labeled examples showed XLM-R achieved F1=0.79 vs mBERT F1=0.71." |
| **Practical** | "X was chosen because of [resource constraint]" | "PostgreSQL was selected over MongoDB because relational integrity was required for the trained-status tracking schema." |
| **Domain fit** | "X is suited because [domain property]" | "RAG was chosen over direct fine-tuning for compliance Q&A because the knowledge base must be updated whenever regulations change without requiring model retraining." |

**Rule:** Never write "we chose X" without a *because*. The because-clause must fit one of the four patterns above.

---

## 5. Common Methodology Section Mistakes

| Mistake | Fix |
|---------|-----|
| Vague description ("We trained a transformer model") | Specify: model name, version, library, hyperparameters, hardware, training time |
| No baselines | Always include a trivial baseline + a rule-based baseline + a strong baseline |
| Missing labeling protocol | Document categories, guidelines summary, annotators, agreement measure |
| Only random train/test split for time-series | Use temporal split for any time-sensitive data |
| Ethical considerations missing | One paragraph on consent, anonymization, ethics committee review |
| Hyperparameters not reported | Full table in methodology, justification for any non-default choice |
| Library versions not pinned | List exact versions: `transformers==4.41.2`, `torch==2.3.0` |

---

## 6. Writing Order (Don't Write in Section Order)

The *reading* order is 1 → 9. The *writing* order is:

1. **Methodology** (you know exactly what you did)
2. **Results** (you have the numbers)
3. **Implementation** (you built it)
4. **Literature review** (now you know what to compare against)
5. **Discussion** (now you can interpret)
6. **Introduction** (now you know what story to tell)
7. **Conclusion** (the easiest, last)
8. **Abstract** (writes itself once everything else is done)

---

## 7. The Abstract Template (last thing you write, first thing reviewed)

A 200-word abstract has 6 sentences:

1. Context: *"Sri Lankan SMEs face significant penalties due to regulatory non-compliance, yet the underlying information barriers have not been quantified."*
2. Problem: *"This work investigates four information barriers — change awareness, knowledge accuracy, risk invisibility, and misinformation spread — that drive SME non-compliance."*
3. Approach: *"We construct four novel datasets through public-record scraping, surveys (N=...), and synthetic generation, and develop multilingual classifiers and a RAG-based knowledge system."*
4. Method: *"Models are evaluated against rule-based, classical, and zero-shot baselines using temporal train/test splits."*
5. Results: *"Median information lag is X days; informal-channel guidance accuracy is Y%; the proposed risk model achieves ROC-AUC = Z; misinformation prevalence in studied SME communities is W%."*
6. Contribution: *"To our knowledge this is the first quantitative study of regulatory information barriers facing SMEs in Sri Lanka, and the released datasets and methodology generalize to other low-data developing-economy contexts."*

---

## 8. Per-Module Paper Track (Optional but Recommended)

Each module is large enough to be a standalone paper. Suggested venues:

| Module | Suggested venue type |
|--------|---------------------|
| 1 | Computational Law / RegTech workshop, or NLP-for-developing-countries workshop |
| 2 | RAG / question-answering workshop, multilingual NLP venue |
| 3 | FinTech / SME / data mining venue |
| 4 | Misinformation / fact-checking / WebSci venue |

Even if you do not submit during the project, knowing the venue shapes how you frame the contribution.

---

## Summary

A strong thesis in this domain follows the IMRaD-extended structure, uses the **What/Why/Where/When** pattern for every methodological choice, includes **trivial + rule-based + strong baselines** in every result table, and reports **slice analysis + error analysis + statistical significance**. Write methodology first, abstract last, and never write "we chose X" without a *because*-clause.
