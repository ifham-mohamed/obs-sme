> [!warning] Superseded
> This is the first-pass draft, written before the official B21 FYP template was available. The live text is now in `Enigmatrix_Final_Report_Master.md` in the deliverable folder. Keep this note only as a record of the earlier wording. See [[00_FINAL_REPORT_CONTEXT_INDEX]] and [[04_OFFICIAL_TEMPLATE_STRUCTURE_MAP]].

# Chapter 2 - Related Work

Note: This draft reuses the interim report bibliography numbering from `E:\Obsidian\sme\Interim\report\SMEs Interim.md`. Before final submission, verify that the final reference list still uses the same numbers.

## 2.1 Introduction

This chapter reviews literature relevant to the Enigmatrix platform and its four research modules. The review begins with the overall SME regulatory-compliance problem, especially in developing economies where small businesses face high compliance costs, fragmented official information, and limited access to specialist advice. It then reviews work in regulatory technology, information asymmetry, multilingual natural language processing, retrieval-augmented question answering, compliance risk modelling, and misinformation detection.

The purpose of the review is not only to list existing systems. It identifies the gap that Enigmatrix addresses: existing work explains that SME compliance depends on knowledge, trust, and institutional support, but very little work measures or automates the flow of regulatory information from official publication to SME understanding and action in the Sri Lankan context.

## 2.2 Overall Related Work

Prior research consistently shows that SME compliance is shaped by regulatory complexity, knowledge requirements, perceived fairness, compliance cost, and access to trustworthy guidance. Studies from Uganda, Indonesia, and other developing-economy contexts show that tax literacy and procedural understanding have a direct relationship with voluntary compliance [22], [23], [24]. The slippery-slope framework further explains compliance behaviour through the interaction between trust in authorities and perceived enforcement power [25]. These findings support the central assumption of Enigmatrix: improving SME access to accurate and timely regulatory knowledge can improve compliance behaviour.

However, much of this literature treats knowledge as a static attribute of the SME owner. It usually measures whether the SME owner knows the law, not how regulatory information moved from the state to the SME, how long that movement took, whether the message was distorted, or whether the information was available in a usable language. This leaves an important gap between compliance theory and information-system implementation.

Information asymmetry provides the broader theoretical lens for this project. Akerlof's work on information asymmetry [26] showed how markets can fail when one party has better information than another. In the SME compliance context, the asymmetry is between the regulator and the regulated enterprise. The state may publish a rule, but if the SME does not discover or understand it in time, the existence of a public notice does not translate into practical compliance. This regulator-to-SME information asymmetry is the main problem Enigmatrix attempts to reduce.

Regulatory Technology (RegTech) is the closest technical field to the proposed system. Arner, Barberis, and Buckley [11] describe RegTech as a response to the growing scale and complexity of compliance. McKinsey [16] similarly frames RegTech as software that helps organizations monitor, manage, and report compliance. Butler and O'Brien [20] discuss how semantic technologies and natural language processing can make regulatory content more machine-readable. More recent work applies NLP to regulatory document monitoring and obligation extraction [30], [31], [32], while RegNLP-style systems explore automated information retrieval and answer generation for compliance documents [33].

The limitation is that most RegTech systems are designed for large institutions, especially banks and financial firms, rather than resource-constrained SMEs. They also tend to assume English-first data, enterprise compliance staff, and access to structured regulatory feeds. Sri Lankan SMEs face a different situation: official documents may be multilingual or scanned, SME owners may rely on informal channels, and regulatory relevance depends heavily on sector, business size, and locality.

Multilingual NLP is therefore a core enabling technology. XLM-R, introduced by Conneau et al. [19], provides cross-lingual representations across many languages and is suitable for low-resource settings. Sinhala-specific work has shown that transformer-based models can outperform older multilingual baselines for Sinhala text classification [5]. More recent Sinhala and code-mixed financial text studies further support the use of XLM-R-style models for Sri Lankan language contexts [47], [48]. This literature justifies the use of multilingual transformer models in Enigmatrix rather than building separate pipelines for English, Sinhala, and Tamil from the beginning.

Retrieval-Augmented Generation (RAG) is relevant to the knowledge component of the system. Lewis et al. [17] introduced RAG as a way to ground generated answers in retrieved evidence. Legal and regulatory QA work such as CBR-RAG [18] and FinSage [46] shows that grounding is especially important in high-stakes domains where hallucinated answers are unacceptable. Evaluation frameworks such as RAGAS, ARES, VERA, and trustworthiness surveys define metrics for faithfulness, answer relevancy, context precision, and context recall [52], [53], [54], [55]. These methods are directly relevant to Module 2.

Compliance risk prediction literature is relevant to Module 3. Existing studies use explainable machine learning for SME credit risk and financial risk modelling [12], [36], while SHAP has become a common method for explaining model predictions in regulated decision-making [15], [39]. Related work also highlights common technical challenges such as class imbalance, for which SMOTE and class-weighted approaches are often used [40], [41]. Enigmatrix can adapt these ideas to compliance risk, but the available data is different from banking credit datasets, so the module must be evaluated carefully.

Misinformation detection literature is relevant to Module 4. WhatsApp and social media studies show how misinformation spreads through informal networks [13], [14], [34], [35]. Transformer-based misinformation classifiers, including multilingual approaches, provide technical foundations for detecting false or misleading claims [43], [45]. However, the existing misinformation literature focuses mainly on health, politics, or general financial misinformation. There is limited work on routine SME regulatory misinformation in Sri Lanka, which creates a clear research gap for Enigmatrix.

Overall, related work supports the need for a unified platform but also shows that no single existing approach addresses the full pathway from official regulatory publication to SME awareness, grounded guidance, risk prioritization, and misinformation verification in a Sri Lankan multilingual setting.

## 2.3 Module-wise Related Work

### 2.3.1 Module 1 - Regulatory Change Awareness Gap

Module 1 is concerned with detecting official regulatory changes and converting them into structured SME-relevant intelligence. Related work for this module falls into four areas: RegTech monitoring, legal/regulatory NLP, multilingual classification, and regulatory information diffusion.

RegTech literature establishes the need for automated monitoring of regulatory changes. Arner et al. [11] describe the rise of RegTech as a response to the increasing cost and complexity of compliance. McKinsey [16] describes regulatory technology as a way to automate compliance monitoring and improve responsiveness to changing rules. Butler and O'Brien [20] show that semantic and NLP-based approaches can help transform regulatory text into machine-processable forms. These works justify the overall direction of Module 1: a software pipeline should continuously monitor regulatory sources instead of expecting SMEs to manually search for new rules.

Recent NLP work extends this idea by applying transformer models to regulatory documents. Automated compliance monitoring pipelines have been proposed for PDF ingestion, entity extraction, and regulatory-impact assessment [30], [31], [32]. RegNLP-style research investigates retrieval and answer generation over regulatory and legal documents [33]. These approaches show that regulatory documents can be computationally processed, but they are usually designed for better-resourced organizations and do not directly measure SME awareness lag.

Multilingual classification work supports the technical choice of XLM-R for Sri Lankan regulatory content. XLM-R provides strong cross-lingual transfer across low-resource languages [19], and Sinhala classification studies show that transformer-based language models are practical for local-language NLP [5]. This is important because Sri Lankan regulatory information and SME communication may involve English, Sinhala, and Tamil. A single multilingual classifier is more maintainable than separate language-specific models at MVP stage.

The current Module 1 implementation uses an 8-category regulatory taxonomy and a 3-sector SME relevance taxonomy. The 8 categories are `TAX_RATE_CHANGE`, `IMPORT_EXPORT`, `SECTOR_SPECIFIC`, `EPF_ETF_CHANGE`, `LABOUR_LAW`, `PRODUCT_STANDARD`, `BUSINESS_REGISTRATION`, and `PENALTY_ENFORCEMENT`. The 3 sectors are `grocery_retail`, `food_service`, and `general_retail`. This taxonomy turns broad regulatory text into measurable classification outputs that can be evaluated with macro-F1, per-class F1, and sector multi-label F1.

A further methodological requirement is annotation reliability. Since the labelled dataset becomes the ground truth for model training and evaluation, the report should describe dual annotation, disagreement resolution, and inter-annotator agreement. Cohen's kappa is suitable because it accounts for agreement that may occur by chance. The current Module 1 evidence shows 800 paired annotation tasks, category kappa of 0.8715, mean sector kappa of 0.8638, and SME relevance kappa of 0.7235. This provides evidence that the dataset is usable, while also showing that SME relevance decisions remain more subjective than category labels.

Module 1 also connects to literature on information asymmetry and communication lag. Existing SME compliance studies show that knowledge and literacy affect compliance [22], [23], [24], but they rarely measure how long it takes for a regulation to reach SMEs after official publication. Enigmatrix therefore contributes not only a classifier, but a measurable awareness pipeline that can support lag analysis, alert delivery, and future survey-based evaluation.

#### Module 1 Research Gap Summary

The main research gap addressed by Module 1 is:

> Existing RegTech and NLP systems can process regulatory text, but there is limited evidence for a Sri Lankan SME-focused, multilingual pipeline that measures and reduces the delay between official regulatory publication and SME awareness.

### 2.3.2 Module 2 - Compliance Knowledge Accuracy Gap

`[M2 PLACEHOLDER]`

Suggested related-work structure for the responsible member:

1. Explain why SMEs need accurate plain-language compliance guidance, not only access to raw regulations.
2. Use SME tax literacy and compliance knowledge studies to show why knowledge quality matters [22], [23], [24].
3. Use RAG literature to justify grounded question answering over verified regulatory content [17], [18], [46].
4. Use RAG evaluation literature to define answer faithfulness, context precision, context recall, and answer relevancy [52], [53], [54], [55].
5. Identify the gap: existing RAG/legal QA systems are not tailored to Sri Lankan SMEs, multilingual explanations, or informal compliance-question workflows.

Suggested final paragraph:

> Module 2 builds on RAG and legal QA literature by grounding SME compliance answers in verified Enigmatrix regulatory records. Its research contribution should be evaluated through answer correctness, evidence grounding, retrieval quality, and user-facing usefulness.

### 2.3.3 Module 3 - Compliance Risk Invisibility Gap

`[M3 PLACEHOLDER]`

Suggested related-work structure for the responsible member:

1. Explain why SMEs need prioritization rather than a long list of possible compliance duties.
2. Use explainable ML risk literature to justify risk scoring and transparent explanations [12], [15], [36], [39].
3. Discuss class imbalance and sparse compliance-event data as methodological challenges [40], [41].
4. Explain how SME profile, survey, and regulation data can be combined into a compliance-risk signal.
5. Identify the gap: existing SME risk models often focus on credit/default risk using proprietary financial datasets, not compliance risk using regulatory-awareness and survey data.

Suggested final paragraph:

> Module 3 adapts explainable risk modelling concepts to the SME compliance setting. Its contribution should be evaluated through expert validation, scenario tests, risk-score consistency, and the clarity of explanations shown to users.

### 2.3.4 Module 4 - Regulatory Misinformation Spread Gap

`[M4 PLACEHOLDER]`

Suggested related-work structure for the responsible member:

1. Explain how SMEs often depend on informal channels such as accountants, peers, messaging groups, and social media.
2. Use misinformation-spread literature to show how false or misleading claims can spread through social networks [13], [14], [34], [35].
3. Use transformer-based misinformation detection and multilingual classification literature as technical grounding [43], [45].
4. Connect misinformation verification to retrieval over verified regulation records, similar to evidence-grounded QA [46].
5. Identify the gap: existing misinformation detection work focuses mainly on politics, health, and general financial misinformation, not SME regulatory claims in Sri Lanka.

Suggested final paragraph:

> Module 4 extends misinformation detection into the regulatory-compliance domain by checking user-facing compliance claims against verified legal and regulatory evidence.

## 2.4 Summary

The literature shows that SME compliance failures are strongly connected to knowledge, complexity, cost, trust, and access to reliable information. RegTech research shows that automated regulatory monitoring is technically feasible, while multilingual NLP research supports the use of transformer models for English, Sinhala, and Tamil content. RAG literature provides a foundation for grounded compliance guidance, explainable risk literature supports transparent risk scoring, and misinformation research highlights the danger of informal and unreliable information channels.

The gap that remains is the integration of these ideas into a Sri Lankan SME-focused platform. Enigmatrix addresses this by combining regulatory change awareness, grounded knowledge support, risk assessment, and misinformation verification. Module 1 provides the upstream verified regulatory intelligence layer, while Modules 2, 3, and 4 consume that intelligence for SME-facing decision support.

## Reference Numbers To Preserve From Interim Report

Use these existing references first before adding new bibliography entries:

| Topic | Suggested references |
|---|---|
| Sri Lankan SMEs and compliance burden | [1], [2], [4], [6], [7], [10] |
| Tax literacy and SME compliance behaviour | [22], [23], [24], [25] |
| Information asymmetry | [26], [27], [28], [29] |
| RegTech and regulatory NLP | [11], [16], [20], [30], [31], [32], [33] |
| Multilingual NLP and Sinhala/Tamil relevance | [5], [19], [43], [44], [47], [48], [49] |
| RAG and legal/regulatory QA | [17], [18], [46], [50], [51], [52], [53], [54], [55] |
| Risk prediction and explainability | [12], [15], [36], [37], [38], [39], [40], [41] |
| Misinformation detection and spread | [13], [14], [34], [35], [43], [45], [46] |

