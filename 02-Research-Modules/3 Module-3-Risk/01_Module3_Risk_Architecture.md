# 14 — Module 3: Compliance Risk Invisibility — Architecture & Methodology

This chapter develops the theoretical and methodological foundation for Module 3 of the Enigmatrix platform, whose object of study is the structural invisibility of compliance risk among Sri Lankan small and medium enterprises (SMEs). The guiding research question is the following: *which observable SME characteristics correlate with compliance failure — operationalised as the receipt of a regulatory penalty within the preceding twenty-four months or the documented omission of a known applicable filing deadline — and can such failure be predicted from those features at a level of performance sufficient to support a deployable, advisory risk-scoring tool?* The chapter argues that the problem is amenable to gradient-boosted tree modelling on tabular features, that fairness across sectoral and regional slices is a first-class evaluation concern rather than an afterthought, and that the interpretive surface of the model — the SHAP attributions — is itself the primary policy artefact, not merely an explanatory garnish around an opaque score. Engineering instantiation, including database columns, training pipelines, and FastAPI endpoints, is deferred to `docs/BUILD_PLAN/BUILD_09_Module3_Risk.md`; the present document is concerned with justification rather than implementation.

## 1. Compliance-Failure Feature Taxonomy

A defensible risk model begins with a defensible feature taxonomy. The economics of tax compliance, from the canonical expected-utility formulation of [Allingham & Sandmo, 1972] through the behavioural revisions surveyed by [Slemrod, 2007] and the practitioner frameworks codified by the OECD's compliance risk management programme [OECD, 2004; OECD, 2010], converges on a small number of feature families that recur across jurisdictions and firm sizes. These families are augmented here by SME-specific findings from emerging-economy literature [Atawodi & Ojeka, 2012; Inasius, 2019] which emphasise informality, capacity constraints, and the role of intermediaries. Five groups are adopted, summarised in Table 1.

| Group | Examples | Source |
|---|---|---|
| Firmographic | Sector code, employee-count band, firm age in years, district, primary respondent language | SME registration, Chamber/NEDA survey |
| Behavioral | Filing method (manual / agent / online), books-of-account method, accounting software in use, deadline-tracking system, frequency of bookkeeper engagement | Onboarding survey |
| Sectoral | Sector-specific risk items stored as a JSONB blob (e.g. import/export licensing exposure for traders, EPF/ETF observance for labour-intensive firms, BOI conditions for export manufacturers) | Sector schema, normalised per NACE-aligned code |
| Compliance history | Penalty count and amount in last 24 months, missed filings count, audit notifications received, defaulter-list appearances | `m3_compliance_history` + IRD defaulter scrape |
| Cross-module exposure | Count and category mix of M1 alerts the SME received, M2 knowledge score, recency of last regulatory interaction | Module 1 alerting log, Module 2 assessments |

The cross-module group deserves particular emphasis: Modules 1 and 2 are not merely upstream data sources but *behavioural instruments*. An SME that has been repeatedly alerted on Customs notices in M1 yet scores poorly in M2 on Customs questions exhibits a distinct exposure-knowledge gap that is plausibly predictive of failure. Encoding this gap as a feature operationalises the platform-wide hypothesis that fragmentation of regulatory information is a causal driver of non-compliance.

## 2. Why Gradient-Boosted Trees, Not Deep Models, At This Sample Size

The realistic ceiling for the labelled dataset assembled through the Chamber and NEDA partnerships is on the order of one hundred to five hundred SMEs in the first eighteen months of operation. At this scale, the empirical literature on tabular learning is unambiguous. [Grinsztajn et al., 2022] demonstrate that gradient-boosted decision trees outperform deep tabular networks across a wide benchmark suite at sample sizes below ten thousand, and [Borisov et al., 2022] extend the survey to explicitly conclude that architectures such as TabNet and FT-Transformer require sample sizes well into the tens of thousands before their inductive advantages materialise. Adopting a deep tabular model under the present sampling regime would therefore amount to importing complexity without statistical justification.

XGBoost and LightGBM are additionally well-suited to four further requirements of the deployment context: heterogeneous feature scales without forced normalisation; native handling of missing values, which is non-trivial given the patchiness of SME self-report data; tractable interpretability via SHAP attributions [Lundberg & Lee, 2017]; and post-hoc probability calibration via isotonic regression, which is necessary for any risk score that is to be presented to a human decision-maker as a probability rather than as a rank. An optional LSTM branch is held in reserve, to be activated only if and when the historical-filings table accumulates at least four longitudinal observations on at least fifty SMEs; until that threshold is met, the temporal signal is collapsed into engineered aggregates.

## 3. Synthetic Data — Justification & Risk

Augmentation with synthetic data using SDV and CTGAN [Xu et al., 2019] is permitted under tightly bounded conditions. The synthetic share of the training set is capped at thirty percent, the marginal distributions of the synthetic sample are calibrated against CBSL SME population statistics where those statistics exist, and the methodology section of any reported result must state the synthetic ratio explicitly. To guard against Goodhart-style overfitting — the failure mode in which the model learns the generator rather than the phenomenon — every reported metric is computed twice, once with synthetic augmentation and once on real data only; if the gap between the two is larger than a pre-registered tolerance the synthetic component is rejected. Synthetic data is never the sole source of positive-class examples for any sector slice: a slice with no real failures is reported as unmodelled rather than as imputed.

## 4. Fairness & Bias

Sri Lankan SME regulation does not designate firm-level protected classes in the manner of personal anti-discrimination law, but the advisory function of the risk score creates a downstream disparate-impact channel that is normatively comparable. Four slices are evaluated independently of overall performance and reported in every model card.

| Slice | Rationale |
|---|---|
| Sector | Penalising small-sector subgroups misallocates intervention capacity and invisibilises rare but compliant industries |
| District / region | An urban-rural performance gap mirrors and amplifies existing infrastructural inequalities |
| Employee-count band | The smallest firms are the most vulnerable to over-flagging; false positives in this band have the highest welfare cost |
| Primary-respondent language | A proxy for ethnicity in the Sri Lankan context; an unaccounted gap here is a constitutional concern |

For each slice the platform reports ROC-AUC, precision at the top decile, and the calibration error separately. The fairness criterion adopted is *equalised odds* in the [Hardt et al., 2016] sense, restricted to the advisory regime: because the score does not trigger automated punitive action, demographic parity would over-constrain the optimisation, but unequal true-positive and false-positive rates across slices remain unacceptable because they would systematically mistarget interventions.

## 5. SHAP for Policy

The model's output is not interpreted as a number alone. For every prediction the platform extracts the top-five SHAP contributors and translates them, via a curated lookup table maintained jointly with NEDA, into actionable interventions. A high contribution from `accounting_software_used = none` becomes a recommendation for the software subsidy programme; a high contribution from `m2_knowledge_score < threshold` on a particular regulatory category becomes a referral into the corresponding Module 2 learning track. This pipeline operationalises the position of [Caruana et al., 2015] that for high-stakes decisions an intelligible model that exposes its reasoning is preferable to a marginally more accurate opaque one. SHAP is selected over LIME because of the global-consistency guarantees established in [Lundberg & Lee, 2017] and because additivity makes contributions aggregable across an SME's history, supporting longitudinal advisory narratives.

## 6. Target & Label Definition

The label is binary and is defined operationally as

`compliance_failure = 1` if either at least one regulatory penalty has been recorded against the SME in the preceding twenty-four months, or at least one filing deadline known to be applicable to that SME has been missed; `0` otherwise.

Two alternative formulations were considered and rejected for the v1 model. A *count* target — number of penalties — would carry information about repeat offending but is heavily zero-inflated at the available sample size and would require a hurdle or zero-inflated regression with poor calibration properties. A *severity-weighted score*, in which penalty amounts are aggregated, was rejected because penalty amounts in the Sri Lankan context are largely formulaic and dominated by a handful of statutory ceilings, so the severity weights do not carry enough independent variance to justify the loss of interpretability. The binary formulation is documented as a v1 choice and is expected to be revisited once the labelled set exceeds approximately one thousand SMEs.

## 7. Evaluation

A temporal split is used in preference to a random split to forestall information leakage from regulatory events that postdate the prediction horizon. With `T` denoting the cutoff at the time of the evaluation run, the training set comprises observations on or before `T - 90 days`, the validation set comprises the window `(T - 90d, T - 30d]`, and the test set comprises `(T - 30d, T]`. The headline metrics are ROC-AUC with a deployment threshold of at least 0.75, precision at the top decile of risk scores of at least 0.60, expected calibration error below 0.05 [Naeini et al., 2015], and fairness slices reported as a non-aggregated panel. A model that meets the headline thresholds but fails any slice threshold is rejected at the gate.

## 8. External Validity

The labelled population is drawn from SMEs that engage with the Chamber of Commerce or with NEDA programmes, and is therefore systematically biased toward firms that already participate in the formal advisory ecosystem. The disengaged tail — informal, semi-formal, or simply unreached SMEs — is under-represented in the training distribution, and the model is expected to under-predict risk in that tail. This limitation is declared explicitly in the model card rather than papered over with reweighting tricks, because the appropriate response is a sampling expansion in subsequent project phases rather than a statistical correction within the current sample.

## 9. Ethics

The risk score is an advisory artefact, not a punitive one. SMEs see their own score and the top-three SHAP contributors to it; no third party — including the Chamber, NEDA, or any state actor — receives an SME's score without that SME's consent. A right to challenge and override a score is implemented via the admin override workflow specified in `BUILD_PLAN/BUILD_13`. Project-level ethics-committee approval through the University of Moratuwa research ethics process remains an open milestone and is tracked as a precondition to any external publication of model outputs.

## 10. Limitations

Several limitations bound the claims that can be made on the basis of v1 results. Penalty data is sparse and unevenly distributed across sectors. The IRD defaulter-list scrape is a source of label noise: defaulter status sometimes reflects administrative lag rather than underlying non-compliance. Behavioural features collected by self-report are subject to social-desirability bias, particularly on items concerning bookkeeping practice. Finally, the regulatory exposure features inherit drift from the Module 1 corpus: when a regulation is repealed or supplanted, the historical alert counts that referenced it become semantically stale and require either remapping or windowing.

## 11. Crosswalk

Implementation, including database schema, training pipeline, monitoring, and override workflow, is specified in `docs/BUILD_PLAN/BUILD_09_Module3_Risk.md`. The present chapter is referenced from that document at the points where engineering choices instantiate methodological commitments made here.

## 12. References

[Allingham & Sandmo, 1972] M. G. Allingham and A. Sandmo, "Income tax evasion: a theoretical analysis," *Journal of Public Economics*, vol. 1, no. 3–4, 1972.

[Slemrod, 2007] J. Slemrod, "Cheating ourselves: the economics of tax evasion," *Journal of Economic Perspectives*, vol. 21, no. 1, 2007.

[OECD, 2004] OECD, *Compliance Risk Management: Managing and Improving Tax Compliance*, Forum on Tax Administration, 2004.

[OECD, 2010] OECD, *Understanding and Influencing Taxpayers' Compliance Behaviour*, 2010.

[Atawodi & Ojeka, 2012] O. W. Atawodi and S. A. Ojeka, "Factors that affect tax compliance among SMEs," *International Journal of Business and Management*, vol. 7, no. 12, 2012.

[Inasius, 2019] F. Inasius, "Factors influencing SME tax compliance: evidence from Indonesia," *International Journal of Public Administration*, vol. 42, no. 5, 2019.

[Grinsztajn et al., 2022] L. Grinsztajn, E. Oyallon, and G. Varoquaux, "Why do tree-based models still outperform deep learning on typical tabular data?," *NeurIPS*, 2022.

[Borisov et al., 2022] V. Borisov et al., "Deep neural networks and tabular data: a survey," *IEEE Transactions on Neural Networks and Learning Systems*, 2022.

[Lundberg & Lee, 2017] S. M. Lundberg and S.-I. Lee, "A unified approach to interpreting model predictions," *NeurIPS*, 2017.

[Caruana et al., 2015] R. Caruana et al., "Intelligible models for healthcare: predicting pneumonia risk and hospital 30-day readmission," *KDD*, 2015.

[Xu et al., 2019] L. Xu et al., "Modeling tabular data using conditional GAN," *NeurIPS*, 2019.

[Naeini et al., 2015] M. P. Naeini, G. Cooper, and M. Hauskrecht, "Obtaining well calibrated probabilities using Bayesian binning," *AAAI*, 2015.

[Hardt et al., 2016] M. Hardt, E. Price, and N. Srebro, "Equality of opportunity in supervised learning," *NeurIPS*, 2016.
