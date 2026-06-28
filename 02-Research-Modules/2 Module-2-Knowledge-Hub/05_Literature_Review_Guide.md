# 05 — Literature Review Guide

> Goal: tell you exactly how to find papers, how to extract the right information from them, and how to write a literature review section that satisfies examiners.

---

## 1. Why the Literature Review Matters Most

Examiners use the literature review to test two things:
1. Do you know the field?
2. Is your gap actually a gap, or did you miss prior work?

A weak literature review makes everything else (data, results) suspect. A strong one earns trust before you present a single result.

---

## 2. Where to Search (in priority order)

| Source | What for | Why |
|--------|----------|-----|
| **Google Scholar** | First broad search | Indexes nearly all academic content; citation counts visible |
| **arXiv** | Latest preprints (NLP, ML) | Most modern NLP papers appear here months before publication |
| **ACL Anthology** | NLP-specific, peer-reviewed | The authoritative NLP venue (ACL, EMNLP, NAACL, EACL) |
| **IEEE Xplore** | Engineering / systems | For deployment, system architecture papers |
| **ACM Digital Library** | CS broadly | For databases, data management, web systems |
| **Semantic Scholar** | Citation graph navigation | Cleaner UI than Google Scholar; AI-enhanced |
| **Connected Papers** | Visual exploration | Find related work via citation network — fast for finding things you missed |
| **Papers with Code** | Implementation availability | Filter to papers that have code, useful for replication baselines |
| **SSRN** | Economics, law, regtech | Where finance and legal papers live |
| **Sri Lankan / regional venues** | Local context | UoM Engineer Journal, ICTer, Sri Lanka Journal of Tax Policy, etc. |

---

## 3. Search Query Patterns

Search terms to use, by module:

### Module 1 (Awareness Gap)
- `regulatory information lag SME`
- `gazette monitoring NLP classification`
- `legal text classification multilingual`
- `regulatory change detection automated`
- `policy diffusion small business`
- `regulatory intelligence developing country`

### Module 2 (Knowledge Gap)
- `retrieval augmented generation legal`
- `question answering tax compliance`
- `RAG faithfulness evaluation`
- `multilingual legal QA`
- `LLM grounding regulatory documents`
- `compliance chatbot SME`

### Module 3 (Risk Gap)
- `tax compliance prediction machine learning`
- `SME default prediction`
- `regulatory non-compliance risk model`
- `interpretable risk scoring SHAP`
- `synthetic data tabular CTGAN`
- `class imbalance compliance prediction`

### Module 4 (Misinformation Gap)
- `misinformation detection low-resource language`
- `cross-lingual fact verification`
- `tax misinformation social media`
- `claim verification RAG`
- `WhatsApp forwarded message classification`
- `regulatory misinformation spread`

### Cross-cutting / context
- `Sri Lanka SME compliance`
- `Sinhala NLP`
- `Tamil NLP low-resource`
- `XLM-R South Asian languages`
- `regulatory technology developing economy`

---

## 4. How to Process Each Paper (the 30-Minute Protocol)

For every paper you cite, do this once and record the result in a table:

1. **Read abstract + intro + conclusion** (10 min) — decide if relevant.
2. If relevant: **read methodology + results** (15 min) — extract the answers below.
3. **Record in your tracker** (5 min).

### Tracker Columns

| Column | What to write |
|--------|---------------|
| Citation key | `Smith2022` |
| Title | Full title |
| Year | YYYY |
| Venue | Journal / conference name |
| Problem | One sentence: what they tackle |
| Method | One sentence: what they did |
| Dataset | What data they used (size, language, domain) |
| Result | Headline metric |
| Limitation | One thing wrong / missing |
| Relevance to us | Which module(s), how |
| Use as | Background / baseline / method-source / dataset-source / contrast |
| Cited by us in | Section X.Y of thesis |

A spreadsheet (or your own web app from Module 1 of these notes) with this structure is the foundation of a strong literature review.

---

## 5. How Researchers Justify Technology / Method Choices in Papers

You asked specifically how existing papers justify their choices. The patterns are consistent across the literature:

### Pattern A — Cite a benchmark
> "We use XLM-R because it achieves state-of-the-art results on the XNLI benchmark for low-resource languages [Conneau et al., 2020]."

### Pattern B — Empirical comparison
> "We tested BERT, mBERT, and XLM-R on a 200-sample pilot. XLM-R's F1 of 0.79 surpassed both alternatives, motivating its selection for the full study."

### Pattern C — Domain fit
> "Our data is short, code-mixed, and multilingual. XLM-R's training corpus includes informal social media text in Sinhala and Tamil, making it a natural fit."

### Pattern D — Practical constraint
> "Given GPU memory constraints (16 GB), we used XLM-R-base (270M parameters) over XLM-R-large (550M parameters), accepting a small accuracy trade-off."

### Pattern E — Reproducibility / open-source
> "We selected ChromaDB over commercial alternatives (Pinecone) to enable open replication of our pipeline."

**Use these patterns yourself.** Your thesis methodology should justify every major choice with one of these five patterns and a citation.

---

## 6. Identifying YOUR Gap

Two parts:

### Part 1 — What is missing in the literature
For each module, the gap is some combination of:

- **Geographic:** Has been done elsewhere, not for Sri Lanka.
- **Linguistic:** Has been done in English, not multilingually with Sinhala/Tamil.
- **Domain:** Has been done in health/news/finance, not in regulatory compliance for SMEs.
- **Measurement:** Has been studied qualitatively, not quantitatively measured.
- **Combination:** No prior work measures information lag for any developing-country tax regime.

### Part 2 — Why it matters
The gap is only worth filling if filling it has consequences. State the consequence:

> "Without measuring this lag, regulators have no evidence-based basis for setting communication policy, SMEs continue to be penalized for unintended non-compliance, and similar developing economies have no replicable methodology for diagnosing the same problem in their context."

This becomes your "significance" paragraph.

---

## 7. Sample Comparison Table to Include in Your Lit Review

End each thematic subsection with a table like this (Module 1 example):

| Paper | Year | Domain | Lang | Method | Dataset Size | Reported Lag? | Notes |
|-------|------|--------|------|--------|--------------|---------------|-------|
| Anwar et al. | 2021 | EU GDPR | EN | Manual coding | 200 firms | Yes (12 days mean) | Limited to one regulation |
| Kumar et al. | 2022 | India SME | EN | Survey only | 320 firms | Partial (categorical) | No automated detection |
| Park et al. | 2023 | Korean tax | KO | Rule-based extraction | 1.2k notices | No | Detection only, no lag |
| Patel et al. | 2024 | Indian financial regs | EN/HI | Fine-tuned BERT | 5k notices | No | Classification only |
| **Ours (proposed)** | **2026** | **Sri Lanka tax/labor/registration** | **EN/SI/TA** | **XLM-R + survey + lag analysis** | **~2k notices + ~150 firms** | **Yes (full distribution)** | **First measured for SL** |

This single table positions your work clearly against the field.

---

## 8. Required Number of References

Rough guideline by section:

| Section | References |
|---------|------------|
| Introduction | 5–10 |
| Literature Review | 30–60 |
| Methodology | 10–20 (mostly methods/tools) |
| Discussion | 5–15 (context comparison) |

Total: **50–100 references** for a strong final-year thesis. Use Zotero or Mendeley to manage them — never format manually.

---

## 9. Citation Style

For UoM FIT projects, **IEEE numbered style** is the most common, but check with your supervisor. Examples:

- IEEE: `[1] A. Smith, "Regulatory NLP," in Proc. ACL, 2022, pp. 100-110.`
- APA: `Smith, A. (2022). Regulatory NLP. In Proceedings of ACL (pp. 100-110).`
- ACM: `Smith, A. 2022. Regulatory NLP. In Proceedings of ACL. ACM, 100-110.`

---

## 10. Time Allocation for Literature Review

Budget at the very start of the project — do not leave it to the end.

| Week | Activity |
|------|----------|
| Week 1 | Broad search per module — 15–20 candidate papers each |
| Week 2 | Detailed read of top 8 per module → fill tracker |
| Week 3 | Identify gap, write thematic sub-sections |
| Week 4 | Write comparison tables, link to your modules |
| Ongoing | Add new papers as they appear during the project |

---

## 11. Required Reading — Foundational Papers Every Module Should Cite

These are the must-cite papers for your project. Read them first.

### Cross-cutting NLP foundations
- Vaswani et al. 2017 — *Attention is All You Need* (transformer)
- Devlin et al. 2019 — *BERT*
- Conneau et al. 2020 — *XLM-R*
- Wolf et al. 2020 — *HuggingFace Transformers*

### Module 1 (legal/regulatory NLP)
- Chalkidis et al. 2020 — *LEGAL-BERT*
- Chalkidis et al. 2022 — *LexGLUE benchmark*
- Tuggener et al. 2020 — *LEDGAR (legal classification dataset)*

### Module 2 (RAG)
- Lewis et al. 2020 — *Retrieval-Augmented Generation*
- Karpukhin et al. 2020 — *Dense Passage Retrieval*
- Es et al. 2023 — *RAGAS*

### Module 3 (interpretable risk)
- Chen & Guestrin 2016 — *XGBoost*
- Lundberg & Lee 2017 — *SHAP*
- Patki et al. 2016 — *Synthetic Data Vault*

### Module 4 (misinformation / fact-checking)
- Thorne et al. 2018 — *FEVER (fact verification dataset)*
- Guo et al. 2022 — *Survey on automated fact-checking*

### South Asian / low-resource NLP
- Kakwani et al. 2020 — *IndicNLPSuite*
- de Silva 2019 — *Sinhala NLP survey*

---

## 12. Common Mistakes

| Mistake | Fix |
|---------|-----|
| Listing papers without synthesis | Group by theme, end each theme with a comparison |
| Citing only old foundational work | Mix foundational (5+ years) with current (2 years) |
| Saying "no work exists" without searching enough | Search exhaustively; almost always *some* analogous work exists in adjacent domains |
| Citing papers you have not read | Examiners will ask. Read what you cite |
| Overciting a single source | If 70% of your citations are from one author/lab, broaden |

---

## 13. Where Sri Lanka–Specific Work Will Be Sparse

You should expect that:
- Almost no NLP work exists on Sri Lankan regulatory text. **This is your gap.**
- Some Sinhala/Tamil NLP work exists, mostly tokenization, sentiment, NER. Cite all of it.
- Some Sri Lankan economic / SME policy work exists in journals — cite for background.

When the gap is real, **say so explicitly and confidently**: "To our knowledge no prior work has [X]." Examiners respect honest claims of novelty more than vague hedging.

---

## Summary

A strong literature review is the result of disciplined paper processing (the 30-minute protocol), thematic synthesis (not annotated bibliography), explicit comparison tables, and confident articulation of your gap. Spend the first 4 weeks of the project on this — it shapes every subsequent decision.
