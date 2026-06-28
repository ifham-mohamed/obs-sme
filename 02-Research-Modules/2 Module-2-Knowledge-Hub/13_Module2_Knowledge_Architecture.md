# 13 — Module 2: Compliance Knowledge Gap — Architecture & Methodology

This chapter develops the research framing and methodological architecture for Module 2 of the Enigmatrix platform. The module addresses a single, falsifiable research question: *how accurately do Sri Lankan small and medium enterprises (SMEs) understand the substantive content of the regulatory obligations they are legally required to comply with — namely Value Added Tax (VAT), Income Tax, Withholding Tax (WHT), Social Security Contribution Levy (SSCL), Employees' Provident Fund (EPF), Employees' Trust Fund (ETF), Company Registration, Customs duties, and the Trade Development Levy (TDL)?* The chapter elaborates the constructs being measured, the instruments designed to measure them, the validity and reliability targets that the measurements must satisfy before they are admitted into the downstream risk model, and the ethical commitments that constrain instrument design. The corresponding engineering specification is maintained in `docs/BUILD_PLAN/BUILD_08_Module2_Knowledge.md`; this chapter does not duplicate that material.

## 1. Research Framing

Knowledge of regulation, in the SME compliance literature, is treated as a latent construct that can only be inferred through observable response behaviour on properly designed items [Loo et al., 2009; Saad, 2014]. The framing adopted here distinguishes two related but non-equivalent constructs. *Awareness* denotes a respondent's recognition that an obligation exists — for instance, that a VAT regime applies to firms above a turnover threshold. *Knowledge* denotes the ability to state the content of that obligation correctly — the threshold value, the rate, the filing cadence, the penalty structure. The distinction matters because awareness without knowledge is a well-documented failure mode in financial-literacy research: respondents over-estimate their own competence, and self-reported understanding correlates only weakly with measured understanding [Lusardi & Mitchell, 2014]. Module 2 therefore declines to treat self-report as a proxy for knowledge, and instead measures the two constructs separately. The third construct, *vulnerability*, captures self-reported behaviours (late filing, reliance on informal advice, absence of bookkeeping software) that act as indirect indicators of knowledge gaps [OECD, 2021]. Triangulating across the three constructs is intended to control for the social-desirability and self-enhancement biases known to inflate self-reported tax knowledge in low- and middle-income contexts [Saad, 2014].

## 2. Three-Instrument Design

A single survey cannot serve all three constructs without confounding them. Awareness items are necessarily short, broad, and self-report; knowledge items must be cognitively demanding and objectively scored against a verified key; vulnerability items must be behavioural and time-anchored. The architecture therefore specifies three distinct instruments, administered to overlapping but not identical samples.

| Instrument | Items | Target n | Construct | Scoring |
|---|---|---|---|---|
| Awareness Survey | ~15 | 120–200 | Self-reported recognition of obligations | Likert + binary |
| Compliance Knowledge Test | 30–40 | 80–150 | Objectively assessed regulatory knowledge | Multiple-choice, keyed |
| Vulnerability Survey | ~20 | 100–200 | Self-reported risky behaviours | Frequency + binary |

The Awareness Survey is designed for breadth and low respondent burden, enabling sector-level coverage. The Compliance Knowledge Test is the methodological core of the module: each item is a multiple-choice question with one correct answer and three or four plausible distractors, where correctness is determined by reference to a Chartered Accountant (CA) verified ground-truth key derived from current Inland Revenue Department circulars and the most recent budget proposals. The Vulnerability Survey provides convergent evidence: a respondent who reports that they file VAT returns "when the accountant reminds them" or who reports never having read a gazette is, on the compliance-behaviour reading of vulnerability, expressing a knowledge gap whether or not they admit to one. Triangulation across the three instruments is the principal defence against the self-report inflation discussed in §1.

## 3. Validity and Reliability

The instruments must satisfy four classes of psychometric criterion before the resulting `knowledge_score` is permitted to flow downstream into Module 3.

*Content validity* is established through expert-panel review. Every item — across all three instruments — is reviewed by a panel of at least three practising Chartered Accountants drawn from at least two distinct firms, to mitigate the firm-level interpretive bias discussed in §9. Items not endorsed by a majority of the panel are revised or discarded. The procedure follows the content-validity-ratio approach of Lawshe [1975].

*Construct validity* is assessed by exploratory factor analysis on the 30–40 knowledge items after pilot administration. The expected factor structure comprises four to six latent factors aligned with the major tax domains (income tax, indirect tax, payroll levies, customs/trade, registration). A factor solution that fails to recover this structure — for instance, one in which all items load on a single general-knowledge factor — would indicate that the instrument is measuring test-taking skill rather than domain-specific knowledge, and would trigger item revision before further administration.

*Internal consistency* is reported per subscale rather than for the instrument as a whole, because a single Cronbach's α for a deliberately multi-domain test is uninformative. The acceptance threshold is α ≥ 0.7 per subscale [Nunnally, 1978]. For the binary-scored items in the knowledge test, the Kuder–Richardson formula 20 (KR-20) is reported, with the same threshold.

*Test–retest reliability* is established by re-administering the knowledge test to a randomly selected ten-percent subsample after a two-week interval, with the test–retest correlation expected to satisfy r ≥ 0.7. The two-week window is short enough to suppress genuine learning effects yet long enough to suppress short-term memory of specific items.

*Inter-rater reliability* applies to any open-ended items (currently a small number of short-answer items in the knowledge test that ask the respondent to compute a tax liability). Two CAs grade each open-ended response independently, and Cohen's κ ≥ 0.7 is required before the items contribute to the score.

## 4. April 2026 Threshold Reference

The question bank is the canonical source of current thresholds for the platform; downstream services consume the same key. Thresholds prevailing at the time of writing are reproduced in Table 2 strictly for the convenience of the reader of this chapter, and are subject to budget revision.

| Regime | Parameter | April 2026 value |
|---|---|---|
| VAT | Annual turnover registration threshold | LKR 36,000,000 |
| VAT | Standard rate | 18% |
| SSCL | Annual turnover threshold | LKR 36,000,000 |
| SSCL | Rate | 2.5% |
| Income Tax | Corporate standard rate | 30% |
| WHT | Resident interest | 10% |
| EPF | Employer + employee combined | 20% |
| ETF | Employer only | 3% |

When the national budget revises any of these parameters, the question bank is the artefact that must be updated first, after which the CA panel re-verifies the key and the affected items are re-piloted. Items written against superseded thresholds are retired rather than silently edited, to preserve the audit trail required for the validity claims in §3.

## 5. Retrieval-Augmented Generation as Pedagogy

The module includes a retrieval-augmented generation (RAG) service that, given a free-text question from an SME user, returns an answer grounded in the Module 1 corpus and in CA-verified summary documents. The framing adopted here is pedagogical rather than purely informational. Following Lewis et al. [2020], RAG is treated as an architecture in which generation is conditioned on retrieved evidence, but the contribution claimed in this work is not the architecture itself — it is the choice of evidence corpus. By restricting retrieval to Module 1's gazette-extracted clauses and to CA-verified summary text, the system produces answers that the user can verify by inspecting the cited source. This addresses the *trust gap* repeatedly identified in Sri Lankan compliance studies [placeholder citations], in which SMEs report distrust of both informal advisers and unsigned web content. Grounding answers in identifiable, dated, and CA-endorsed sources is the design response to that gap.

The embedding model selected for retrieval is `multilingual-e5-base`. The justification is threefold: it provides competitive performance on the MTEB retrieval benchmark relative to alternatives of comparable size [Wang et al., 2024]; it is trained on a mixture that includes Sinhala and Tamil, the two non-English languages relevant to the population; and it is released under a permissive licence compatible with the project's open-research commitments. Larger commercial embeddings were rejected on cost and reproducibility grounds rather than on performance grounds.

## 6. Sampling Frame and External Validity

Generalisability of the findings is bounded by the sampling frame. The frame is stratified across seven sectors (retail, food and beverage, garment manufacture, information technology services, transport, agriculture, and other services), three firm-size bands by employee count, three administrative regions (Western, Central, Southern), and three respondent languages (English, Sinhala, Tamil). Stratification is intended to surface sector- and language-level variation in knowledge that would otherwise be averaged away. Recruitment proceeds through the Ceylon Chamber of Commerce, the National Enterprise Development Authority (NEDA), and sector associations, supplemented by snowball referral. The principal external-validity threat is self-selection: SMEs willing to complete a forty-item knowledge test are plausibly more compliance-engaged than the population mean, biasing knowledge estimates upward. The bias is partially, not wholly, mitigated by the snowball component, which reaches firms outside association membership rolls. The asymmetry is acknowledged in §9 and is reported alongside any aggregate knowledge statistic that the platform exposes externally.

## 7. Ethics

Informed consent is obtained in the respondent's preferred language (English, Sinhala, or Tamil) before any instrument is administered, with consent forms translated and back-translated to detect drift. CA verification of the ground-truth key is itself an ethical commitment, not merely a methodological one: a platform that *teaches* incorrect compliance to SMEs would impose direct financial and legal harm on its users, and the CA panel is the procedural guarantee against that harm. Data minimisation is applied throughout: no respondent-level personally identifying information is collected beyond what is required for stratification (sector, size band, region, language) and for the test–retest linkage (a hashed pseudonym). Respondents are informed of the right to withdraw at any point, including after submission, and withdrawal entails deletion of their responses from analytic datasets. Project-level ethics-committee approval through the University of Moratuwa is flagged here as an open governance question to be resolved before pilot administration; this chapter does not assert that approval has been obtained.

## 8. Integration with Module 3

Module 3's risk model consumes a per-firm `knowledge_score` derived from the Module 2 instruments. The dependency is methodological, not merely architectural: noise in the Module 2 measurement propagates as feature noise into the Module 3 model, attenuating any coefficient estimated on `knowledge_score` and inflating its standard error. This is a textbook errors-in-variables problem [Carroll et al., 2006]. The mitigation adopted in this work is procedural rather than statistical: `knowledge_score` is not exposed to Module 3 until the per-subscale Cronbach's α threshold of §3 is satisfied, and the score is versioned so that downstream model runs can be reproduced against the exact score definition that was current at training time. Releasing a score that fails the reliability threshold would invalidate any causal interpretation of Module 3's coefficients and is therefore precluded.

## 9. Limitations

Several limitations qualify the conclusions that Module 2 will support. First, sector-level n is uneven: agriculture is over-represented in the population of Sri Lankan SMEs but under-represented in association membership rolls, and the realised n for agricultural respondents may be small enough to preclude sector-level inference. Second, literacy variation across the smallest SMEs is a known measurement threat; an audio-administered version of the awareness and vulnerability surveys is under consideration but is not committed to in the current design. Third, the CA expert panel is itself a sampling problem: a panel dominated by a single accounting firm will encode that firm's interpretive conventions into the ground-truth key. The minimum-two-firm rule in §3 is a partial mitigation, not a complete one. Fourth, policy churn is an irreducible threat: an April 2026 budget revision that changes the VAT or SSCL parameters in Table 1 invalidates a portion of the question bank by construction, and the validity evidence accumulated against the prior parameters does not transfer.

## 10. Crosswalk

For the implementation — schema definitions, ingestion scripts, scoring code, RAG service, and admin interfaces — see `docs/BUILD_PLAN/BUILD_08_Module2_Knowledge.md`. This chapter governs the *why* and the *what-must-be-true*; that document governs the *how*.

## 11. References

The following stubs are placeholders to be completed in IEEE format by the project team during the literature-review pass.

[1] A. Lusardi and O. S. Mitchell, "The economic importance of financial literacy: Theory and evidence," *Journal of Economic Literature*, vol. 52, no. 1, pp. 5–44, 2014.

[2] N. Saad, "Tax knowledge, tax complexity and tax compliance: Taxpayers' view," *Procedia — Social and Behavioral Sciences*, vol. 109, pp. 1069–1075, 2014.

[3] E. C. Loo, M. McKerchar, and A. Hansford, "Understanding the compliance behaviour of Malaysian individual taxpayers using a mixed method approach," *Journal of the Australasian Tax Teachers Association*, vol. 4, no. 1, pp. 181–202, 2009.

[4] OECD, *Tax Administration 2021: Comparative Information on OECD and Other Advanced and Emerging Economies*. Paris: OECD Publishing, 2021.

[5] C. H. Lawshe, "A quantitative approach to content validity," *Personnel Psychology*, vol. 28, no. 4, pp. 563–575, 1975.

[6] J. C. Nunnally, *Psychometric Theory*, 2nd ed. New York: McGraw-Hill, 1978.

[7] L. J. Cronbach, "Coefficient alpha and the internal structure of tests," *Psychometrika*, vol. 16, no. 3, pp. 297–334, 1951.

[8] P. Lewis et al., "Retrieval-augmented generation for knowledge-intensive NLP tasks," in *Advances in Neural Information Processing Systems 33*, 2020, pp. 9459–9474.

[9] L. Wang et al., "Multilingual E5 text embeddings: A technical report," *arXiv:2402.05672*, 2024.

[10] R. J. Carroll, D. Ruppert, L. A. Stefanski, and C. M. Crainiceanu, *Measurement Error in Nonlinear Models: A Modern Perspective*, 2nd ed. Boca Raton: Chapman & Hall/CRC, 2006.

[11] [Placeholder] Survey methodology in Sri Lankan SME contexts — author and year to be supplied.

[12] [Placeholder] IRC voluntary-compliance behavioural model — author and year to be supplied.
