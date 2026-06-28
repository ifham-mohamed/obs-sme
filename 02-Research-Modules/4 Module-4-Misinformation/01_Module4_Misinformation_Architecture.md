# 15 — Module 4: Regulatory Misinformation — Architecture & Methodology

> **Implementation Status:** This is a research methodology chapter describing the target design for M4. **M4 is not yet built.** BUILD_10 has not started. The `per_module_m4` session mode is reserved in the API and DB schema, but no M4 questions are seeded, no classifiers are deployed, and `/api/v1/verify/claim` returns 501. The veracity taxonomy, NLP pipeline, and RAG verifier described here are forward-looking specs. Refer to `docs/BUILD_PLAN/BUILD_10_Module4_Misinformation.md` for the engineering plan.

This chapter formalises the research methodology underlying Module 4 of the Enigmatrix platform. The guiding research question is the following: *what is the prevalence and virality of regulatory misinformation circulating in Sri Lankan SME networks, and can a multilingual classifier paired with a retrieval-augmented (RAG) verifier reliably identify, characterise, and correct such misinformation against the authoritative gazette corpus produced by Module 1?* The chapter is methodological and theoretical; the corresponding engineering specification, schemas, and pipeline contracts are documented in `docs/BUILD_PLAN/BUILD_10_Module4_Misinformation.md`.

The motivation is concrete. Sri Lankan SMEs receive regulatory information through a heterogeneous mixture of channels — Twitter/X commentary, Facebook public pages, WhatsApp forwards, YouTube explainers, and Sinhala/Tamil press articles — most of which are not fact-checked and frequently lag, distort, or pre-date official gazette publication. The April 2026 budget revisions to VAT thresholds, EPF/ETF rates, and SME registration procedures have already produced a measurable surge in conflicting circulating claims. Module 4 therefore treats misinformation not as a single binary but as a layered phenomenon requiring a typology, a mechanics layer, multilingual NLP, and grounded verification.

## 1. Misinformation Typology

Module 4 adopts a nine-way veracity taxonomy. Binary true/false labelling is rejected on the basis of well-established findings in information-disorder research, which demonstrate that the bulk of harmful content occupies intermediate categories of partial truth, decontextualisation, and obsolescence rather than outright fabrication [Wardle & Derakhshan, 2017]. The taxonomy is also aligned with operational categories used by FactCheck.lk and the schema.org `ClaimReview` vocabulary so that external pre-labelled data can be ingested with minimal mapping loss.

| Label             | Description                                                                                  |
|-------------------|----------------------------------------------------------------------------------------------|
| `true`            | Claim is fully supported by current gazette regulations.                                     |
| `mostly_true`     | Core assertion correct; minor numerical or temporal imprecision.                             |
| `partially_true`  | Mixes accurate and inaccurate elements in roughly equal measure.                             |
| `misleading`      | Each component is technically accurate but the framing produces a false impression.          |
| `mostly_false`    | Core assertion incorrect; some incidental detail accurate.                                   |
| `false`           | Claim contradicts current regulation outright.                                                |
| `unverifiable`    | No corresponding regulation exists in M1; insufficient evidence for any verdict.             |
| `opinion`         | Normative or evaluative statement, not a factual claim.                                      |
| `outdated`        | Claim was true under a prior gazette but has been superseded by a later one.                 |

The `outdated` category is operationally critical for the Sri Lankan context. The April 2026 budget cycle supersedes a substantial body of 2023–2024 guidance; without an explicit "outdated" label, content that was once accurate would be mislabelled either `true` (rewarding stale information) or `false` (penalising past good-faith reporting). This category is rare in international taxonomies but indispensable for jurisdictions undergoing rapid regulatory turnover.

## 2. Misleading-Mechanics Annotation

Veracity alone does not capture *how* a piece of content misleads. Module 4 therefore records, orthogonally to the veracity label, five binary mechanics flags that may co-occur in any combination: `wrong_numbers` (incorrect rates, thresholds, percentages), `wrong_dates` (incorrect effective or deadline dates), `fake_authority` (false attribution to a ministry, regulator, or named official), `fear_appeal` (emotional framing emphasising loss, penalty, or harm), and `urgency_appeal` (framing emphasising immediate action, "before it is too late").

Mechanics are tracked separately from veracity for two principled reasons. First, a *true* claim can still be propagated through fear or urgency appeals, which is relevant for studying virality dynamics independent of veracity. Second, a *false* claim may be propagated without manipulative mechanics — a sincere error, for instance, where a small business owner mis-states the VAT threshold. Conflating the two collapses an analytically useful distinction and prevents downstream regression of virality on rhetorical mechanics with veracity held constant.

## 3. Multilingual NLP Justification

SME social discourse in Sri Lanka is trilingual: English in formal business and urban Twitter contexts, Sinhala for the majority of Facebook and WhatsApp content, and Tamil for the Northern and Eastern provincial discourse. Code-mixing ("Singlish", Tamil-English) is pervasive. This rules out monolingual fine-tuning per language as a primary architecture: it is data-thirsty, produces three non-interoperable model artefacts, and cannot natively handle code-mixed inputs.

Among multilingual encoders, XLM-RoBERTa-base is selected. Multilingual BERT (mBERT) underperforms substantially on low-resource Indic languages and was trained on a Wikipedia mixture in which Sinhala and Tamil are heavily under-represented [Conneau et al., 2020]. IndicBERT covers a strong set of Indo-Aryan and Dravidian languages but excludes Sinhala, which alone disqualifies it for this corpus. LaBSE produces sentence-level embeddings optimised for cross-lingual retrieval rather than supervised classification and is therefore complementary, not substitutive. XLM-R is trained on CommonCrawl in 100 languages including both Sinhala and Tamil, demonstrates strong cross-lingual transfer to low-resource languages, and exposes a token-level classification head suitable for the present multi-label task [Conneau et al., 2020]. Recent benchmarks on Sinhala and Tamil text classification corroborate XLM-R's lead over mBERT on classification accuracy and macro-F1 [Ranathunga et al., 2022; Dhananjaya et al., 2022].

Translation, where required for cross-lingual normalisation or annotator review, is performed via NLLB-200 [NLLB Team, 2022], with translation noise treated as a measurable confounder rather than ignored.

## 4. RAG Verifier Theory

The verifier is framed as a retrieval-augmented natural language inference (NLI) problem. Given a user-submitted claim *c*, the system retrieves the top-*k* (default *k* = 5) passages from `regulations_chunks_v1`, the chunked and embedded gazette corpus produced by Module 1, using dense retrieval over multilingual sentence embeddings. Each (claim, passage) pair is then scored by an NLI head producing one of three labels — `entailment`, `contradiction`, `neutral` — together with a confidence score. The aggregate verdict is computed by majority and confidence-weighted vote across the *k* passages.

The framing is grounded in the FEVER fact-verification paradigm [Thorne et al., 2018], which established retrieval-then-NLI as the canonical decomposition of textual claim verification, and in zero-shot NLI as classification [Yin et al., 2019], which demonstrates that NLI heads can serve as label-agnostic verifiers across domains without per-domain re-training. The choice of RAG over closed-book LLM verification follows the original RAG argument that grounding generation in retrieved evidence improves factual accuracy and provides citation auditability [Lewis et al., 2020]. The verifier output is therefore a structured object — `{verdict, supporting_regulations, nli_label, confidence}` — and never a single boolean. Each verdict is traceable to specific gazette passages.

## 5. Why the M1 Corpus Is Treated as Ground Truth

Verifying regulatory claims against general LLM world knowledge is unsound: LLM training cut-offs lag the present, jurisdiction-specific Sri Lankan content is sparse in pre-training corpora, and hallucinated regulatory text is indistinguishable from genuine text without grounding. The M1 corpus — PDF-extracted, classified, summarised, and chunk-embedded gazette content — is by construction the only authoritative source for Sri Lankan regulatory truth available to the platform. Grounding the verifier against M1 makes every verdict auditable: a contradiction verdict carries with it the specific gazette identifier, section, and page from which the contradiction was inferred. This auditability is a precondition for any user-facing correction; an unsourced "false" verdict is operationally indistinguishable from a hallucination.

## 6. Spread and Virality Methodology

The `m4_spread_events` table records share, retweet, repost, and forward events with their timestamps and inferred reach. A virality score is computed per post as `log(reach) × engagement_rate`, log-transforming reach to compress heavy tails. Distributions of virality conditional on veracity label are compared using the Mann–Whitney U test (non-parametric, no normality assumption on highly skewed engagement data). The hypothesis under test is that of Vosoughi et al. [2018], who reported that false news on Twitter diffused significantly farther, faster, deeper, and more broadly than true news across all categories of information. Module 4 will confirm or disconfirm this finding for the narrower regulatory niche in Sri Lanka, and will report virality conditional on each of the five mechanics flags to isolate rhetorical from veracity effects.

## 7. Linguistic-Marker Analysis

For each post the pipeline extracts a fixed feature vector: word count, emoji count, ALL-CAPS token count, sentiment polarity (multilingual sentiment model), presence of percentage tokens, presence of currency tokens, count of named entities resolving to ministries or regulators, count of URLs, and count of mentions. Two analyses are performed. First, marker-by-label correlation tables are produced (point-biserial for binary markers, Spearman for counts) and reported as descriptive findings of independent thesis interest. Second, the markers are concatenated with XLM-R [CLS] embeddings as inputs to a baseline classifier; this is particularly important given the modest labelled corpus size and provides a non-transformer ablation baseline.

## 8. Inter-Annotator Agreement and Consensus

Every post in the labelled corpus is annotated by at least two annotators independently. Cohen's κ is computed per annotator pair and per label; a label is promoted to `is_consensus_label = TRUE` only when both annotators agree and aggregate κ on the relevant label exceeds 0.7, the conventional threshold for substantial agreement. Disagreements are escalated to a senior annotator whose adjudication is recorded but flagged. As an external quality check, the FactCheck.lk pre-labelled subset is held out and annotator accuracy and recall against it are reported. Drift in κ over time is monitored and the codebook is revised when sustained drops occur on specific categories.

## 9. Ethics of Social-Media Scraping

Module 4 follows an informed-consent gradient calibrated by platform affordances and Terms of Service. The principle is that no private content is ever ingested, no platform ToS is breached, and PII is stripped before storage. Phone numbers, NIC numbers, email addresses, and account handles in free-text fields are removed by deterministic regex plus named-entity scrubbing prior to persistence. WhatsApp data is *only* obtained through voluntary forwards uploaded via the SME survey instrument with explicit consent. The ethical frame draws on Townsend & Wallace [2016] on social-media research ethics, particularly their guidance that the public availability of content does not by itself constitute consent for research use.

| Platform   | Access Mechanism             | Scope                              | Consent Basis                   |
|------------|-------------------------------|------------------------------------|---------------------------------|
| Twitter/X  | Academic / v2 API             | Public tweets, public profiles     | Platform ToS, public posting    |
| Facebook   | Graph API                     | Public pages only, no groups       | Page operator public posting    |
| Reddit     | PRAW                          | Public subreddits                  | Platform ToS, public posting    |
| YouTube    | YouTube Data API              | Public video metadata, comments    | Platform ToS, public posting    |
| WhatsApp   | Survey upload only            | Voluntarily forwarded messages     | Explicit informed consent       |
| News sites | RSS / permitted scraping      | Article body, no paywalled content | Publisher ToS / robots.txt      |

ToS compliance per platform, rate-limit policy, and PII-stripping regex inventory are documented in BUILD_10.

## 10. External Validity

Platform sampling skews demography and topic. WhatsApp forwards bias toward older, more engaged, and family-network users; Twitter biases toward urban, English-speaking, professionally networked users; Facebook reaches a broader demographic but with regional and language-cluster skews; Reddit reaches a small, predominantly English diaspora-adjacent subset. Findings are therefore reported stratified by platform, and aggregate statements about "Sri Lankan SME misinformation" are avoided where stratified figures diverge meaningfully. Population-level inference is not claimed.

## 11. Limitations

Several limitations are acknowledged candidly. First, language detection is imperfect on code-mixed Sinhala-English and Tamil-English ("Singlish"), which is precisely the register most prevalent on Twitter and Facebook; misidentification rate will be reported and code-mixed inputs routed to a manual-review queue when language confidence is below threshold. Second, NLLB-200 translations introduce label noise on the order of several percent on Sinhala-English; the rate is measured on a bilingually annotated holdout and reported. Third, the labelled corpus is modest at an expected 500–1,000 posts, which is small for full transformer fine-tuning; the methodology consequently leans on linear and tree-based baselines over XLM-R embeddings rather than full encoder fine-tuning, and reports both. Fourth, the M1 corpus has known coverage gaps — some regulations exist only in PDFs not yet ingested — which causes false `unverifiable` verdicts; the rate of `unverifiable` against a manually-curated answerability set is reported as a corpus-coverage diagnostic rather than a verifier failure.

## 12. Crosswalk

Implementation, schemas (`m4_posts`, `m4_labels`, `m4_spread_events`, `m4_verifications`), pipeline DAGs, model-training procedures, evaluation harness, and ToS-compliance checklists are specified in `docs/BUILD_PLAN/BUILD_10_Module4_Misinformation.md`. This chapter is the methodological counterpart and should be read alongside it.

## 13. References

[1] C. Wardle and H. Derakhshan, *Information Disorder: Toward an Interdisciplinary Framework for Research and Policymaking*, Council of Europe, 2017.

[2] A. Conneau, K. Khandelwal, N. Goyal, V. Chaudhary, G. Wenzek, F. Guzmán, E. Grave, M. Ott, L. Zettlemoyer, and V. Stoyanov, "Unsupervised Cross-lingual Representation Learning at Scale," in *Proc. ACL*, 2020.

[3] J. Thorne, A. Vlachos, C. Christodoulopoulos, and A. Mittal, "FEVER: a Large-scale Dataset for Fact Extraction and VERification," in *Proc. NAACL-HLT*, 2018.

[4] W. Yin, J. Hay, and D. Roth, "Benchmarking Zero-shot Text Classification: Datasets, Evaluation and Entailment Approach," in *Proc. EMNLP-IJCNLP*, 2019.

[5] S. Vosoughi, D. Roy, and S. Aral, "The spread of true and false news online," *Science*, vol. 359, no. 6380, pp. 1146–1151, 2018.

[6] P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, H. Küttler, M. Lewis, W.-t. Yih, T. Rocktäschel, S. Riedel, and D. Kiela, "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in *Proc. NeurIPS*, 2020.

[7] FactCheck.lk, "Methodology and Rating Scale," editorial documentation, accessed 2026.

[8] Schema.org, "ClaimReview" type specification, https://schema.org/ClaimReview, accessed 2026.

[9] S. Ranathunga, E. A. Lee, M. Prifti Skenduli, R. Shekhar, M. Alam, and R. Kaur, "Neural Machine Translation for Low-Resource Languages: A Survey," *ACM Computing Surveys*, 2022 (Sinhala/Tamil benchmark discussion).

[10] V. Dhananjaya, P. Demotte, S. Ranathunga, and S. Jayasena, "BERTifying Sinhala — A Comprehensive Analysis of Pre-trained Language Models for Sinhala Text Classification," in *Proc. LREC*, 2022.

[11] NLLB Team et al., "No Language Left Behind: Scaling Human-Centered Machine Translation," Meta AI Technical Report, 2022.

[12] L. Townsend and C. Wallace, *Social Media Research: A Guide to Ethics*, University of Aberdeen, 2016.

[13] L. De Silva and U. Thayasivam, "Sentiment Analysis on Sinhala and Tamil Social Media Text: A Comparative Study," in *Proc. ICTer*, Sri Lanka, 2021.

[14] N. de Silva, "Survey on Publicly Available Sinhala Natural Language Processing Tools and Research," arXiv:1906.02358, 2019.
