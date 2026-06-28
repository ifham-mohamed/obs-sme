**RESEARCH PROJECT PROPOSAL**

**Understanding Information Barriers to Regulatory Compliance**

**Among Sri Lankan SMEs: A Data-Driven Investigation**

Group: Enigmatrix | Faculty of Information Technology | University of Moratuwa

Level 04 Final Year Research Project | 2026

# 1. The One Core Problem

|   |
|---|
|**In One Sentence:**<br><br>Sri Lankan SMEs want to comply — but they do not have access to the right information, at the right time, in the right language.|

This is the single real-world problem driving the entire research project. Everything else flows from this one human truth:

|**Information Failure**|**What It Means**|
|---|---|
|Right TIME|SMEs find out about regulatory changes weeks or months after they happen|
|Right INFORMATION|The guidance SMEs receive — from accountants, forums, social media — is often incorrect|
|Right LANGUAGE|Official documents are in English, but most SME owners operate in Sinhala or Tamil|
|Right AWARENESS|SMEs do not know they are heading toward non-compliance until a penalty arrives|

# 2. Why This Is a Research Project — Not Just a System Build

A system build asks: "How do we build X?"

A research project asks: "We do not know if X is true, or how bad it is — let us find out."

|**System Build (What we had before)**|**Research Project (What we have now)**|
|---|---|
|Built because it seemed useful|Built because research proves it is needed|
|Features decided by assumption|Features decided by measured findings|
|No validation of impact|Validated against real measured barriers|
|No novel contribution|4 novel datasets + 4 measurable findings|
|AI is the subject|AI is the tool — the real world is the subject|

# 3. The Overarching Research Question

|   |
|---|
|**Main Research Question:**<br><br>What are the information barriers that drive regulatory non-compliance among Sri Lankan SMEs — and how can they be systematically identified and addressed?|

This question is:

- Genuinely unanswered — nobody has studied or measured this for Sri Lanka
- About the real world — not about how well AI works
- Requires all 4 modules to fully answer
- Generalizable — findings apply to any developing economy with similar regulatory fragmentation

# 4. The Four Research Modules

Each module investigates one specific information barrier. Together they form a complete picture of why Sri Lankan SMEs fail at compliance.

## Module 1 — Regulatory Change Awareness Gap

|   |
|---|
|**Research Question:**<br><br>Are regulatory changes reaching Sri Lankan SMEs in time to act — and what is the information lag between gazette publication and SME awareness?|

**The Real-World Problem**

When a new regulation is published in the Government Gazette, how long does it take before an average SME owner knows about it? Days? Weeks? Months? Nobody has ever measured this for Sri Lanka. SMEs are getting penalized for missing deadlines they never even knew existed.

**What You Investigate**

- Measure the exact lag at every stage: Gazette → Official Portal → News → SME Awareness
- Identify which communication channels deliver regulatory information fastest
- Determine which types of regulatory changes have the longest awareness gap
- Find whether lag differs by SME sector, size, or location

**Data Sources**

|**Data Source**|**What You Collect**|**How You Get It**|
|---|---|---|
|Government Gazette Archive|Publication dates of all regulatory changes 2018–2026|www.documents.gov.lk — all public PDFs|
|IRD / EPF / ETF / eROC websites|Secondary publication dates on official portals|Web scraping + manual archive|
|News Archives|First news coverage date of each regulatory change|Daily FT, LBO, Daily Mirror — searchable|
|SME Owner Survey|When SMEs actually became aware + which channel informed them|Google Forms via Chamber of Commerce, NEDA, LinkedIn|

**Procedures and Technologies**

- Parse gazette PDFs using PyMuPDF / pdfplumber to extract publication dates and change content
- Train NLP classifier (TF-IDF baseline vs fine-tuned XLM-R) to categorize regulatory change types
- Calculate lag duration at each stage for every regulatory change
- Statistical analysis: mean, median, distribution of lags by change type and SME profile
- Channel effectiveness ranking — which source delivers information fastest

**Novel Contribution**

- First ever measured information lag dataset for Sri Lankan regulatory changes
- First ranked map of regulatory communication channel effectiveness in Sri Lanka
- First NLP classifier for Sri Lankan regulatory change categorization

**The Solution Built**

An automated gazette monitoring and SME alert system — validated by proving it delivers regulatory information significantly faster than current average awareness times.

## Module 2 — Compliance Knowledge Accuracy Gap

|   |
|---|
|**Research Question:**<br><br>How accurate is the compliance guidance Sri Lankan SMEs receive — and what is the gap between official regulatory requirements and what SMEs actually understand?|

**The Real-World Problem**

When an SME files a VAT return, how correct is their understanding of what they need to do? When they ask their accountant or look at a Facebook group, how often is the answer wrong? Nobody has measured the accuracy of compliance guidance reaching Sri Lankan SMEs — or quantified how much misunderstanding exists.

**What You Investigate**

- Build a verified ground truth of all Sri Lankan compliance requirements across key regulatory domains
- Test SME owners and finance staff with specific compliance knowledge questions
- Calculate a compliance knowledge gap score — how far is SME understanding from official requirements?
- Measure accuracy of informal guidance (social media, forums, accountants) vs official sources

**Data Sources**

|**Data Source**|**What You Collect**|**How You Get It**|
|---|---|---|
|IRD / EPF / ETF / eROC documents|All official compliance rules — exact rates, deadlines, formats|Public PDFs — verified by CA / tax professional|
|Compliance Knowledge Survey|SME responses to specific verifiable compliance questions|Google Forms — 80-120 SME owners and finance staff|
|Social Media and Forums|Compliance claims made in public groups|Facebook group scraping, Reddit Sri Lanka, forums|
|FactCheck.lk|Pre-labeled misinformation claims about regulations|Public website scraping|

**Procedures and Technologies**

- Construct structured Q&A ground truth knowledge base from official documents — verified by expert
- Design and distribute a 40-50 question compliance knowledge test to SME owners
- Score responses against ground truth — calculate domain-specific accuracy rates
- Extract compliance claims from social media using spaCy NLP
- Verify each claim against ground truth — calculate informal guidance accuracy rate
- Build RAG system on verified knowledge base — evaluate using RAGAS faithfulness framework

**Novel Contribution**

- First measured compliance knowledge gap score for Sri Lankan SMEs
- First accuracy measurement of informal guidance channels in Sri Lankan regulatory context
- First Sri Lankan compliance Q&A benchmark dataset — verified against official sources

**The Solution Built**

A RAG-based multilingual compliance guidance system grounded strictly in verified official documents — validated by showing it produces more accurate answers than informal channels measured in the research.

## Module 3 — Compliance Risk Invisibility

|   |
|---|
|**Research Question:**<br><br>Which characteristics of Sri Lankan SMEs predict compliance failure — and can these signals be detected before a violation occurs?|

**The Real World Problem**

SMEs do not know they are heading toward non-compliance until a penalty notice arrives. There is no early warning system. No one has studied which types of SMEs are most at risk or what behavioral patterns appear before a violation occurs. The risk is completely invisible until it is too late.

**What You Investigate**

- Which SME characteristics — sector, size, age, location — most strongly predict compliance failure?
- What behavioral patterns appear in the period before a compliance violation?
- Can risk be detected 1 month, 3 months, or 6 months before a violation occurs?
- Which ML approach generalizes best when labeled data is scarce?

**Data Sources**

|**Data Source**|**What You Collect**|**How You Get It**|
|---|---|---|
|IRD Published Defaulter Lists|Records of actual tax violations with business type|IRD website — publicly published|
|Court Judgment Records|SME tax dispute cases with outcomes and timelines|www.lawnet.gov.lk — all public judgments|
|Central Bank Annual Reports|Sector-level SME financial health indicators over time|CBSL website — all public reports|
|SME Vulnerability Survey|Self-reported compliance failures with SME characteristics|Google Forms via Chamber of Commerce, NEDA|
|Synthetic Dataset|Realistic SME profiles calibrated to population statistics|SDV / CTGAN synthetic generation|

**Procedures and Technologies**

- Combine real violation records, survey data, and synthetic data into unified labeled dataset
- Handle class imbalance using SMOTE oversampling
- Exploratory analysis: visualize compliance failure rates by sector, size, age, region
- Train and compare: Logistic Regression (baseline), Random Forest, XGBoost, LSTM
- SHAP analysis — identify which features most strongly predict non-compliance
- Temporal analysis — measure how early before violation risk signals become detectable

**Novel Contribution**

- First SME compliance risk prediction model for a developing economy using only public data
- First feature importance study identifying predictors of SME non-compliance in Sri Lanka
- Generalizable methodology for compliance risk prediction in any data-scarce regulatory environment

**The Solution Built**

An SME compliance risk early warning system with SHAP-explainable risk scores — validated by retrospective testing against known historical violations.

## Module 4 — Regulatory Misinformation Spread

|   |
|---|
|**Research Question:**<br><br>How significantly does tax regulation misinformation spread through Sri Lankan SME networks — and what makes certain misinformation more viral than accurate official guidance?|

**The Real World Problem**

When an SME owner cannot find clear guidance from official sources, they turn to WhatsApp groups, Facebook, and online forums. Wrong information about tax regulations spreads rapidly through these channels. No one has measured how prevalent this misinformation is, how fast it spreads, or what makes it more believable than accurate information.

**What You Investigate**

- What percentage of tax regulation content on Sri Lankan social media is inaccurate?
- Which regulatory topics generate the most misinformation?
- Does misinformation spread faster and further than accurate content?
- What linguistic features make misinformation more viral than correct information?
- Does misinformation spike when new regulations are announced — correlating with Module 1 lag findings?

**Data Sources**

|**Data Source**|**What You Collect**|**How You Get It**|
|---|---|---|
|Public Facebook Groups|Posts making compliance claims with engagement metrics|Facebook Graph API + manual collection from public groups|
|Twitter / X|Tax regulation discussions with retweet / reply data|Twitter Academic API with Sinhala / English keywords|
|Reddit Sri Lanka|Finance and tax discussion threads|Reddit API — public posts|
|FactCheck.lk|Pre-labeled Sri Lankan regulatory claims|Website scraping — publicly available|
|SME Survey (WhatsApp)|Anonymized forwarded messages about tax regulations|Collected via Module 1 / 2 survey instrument|

**Procedures and Technologies**

- Collect and clean all social media posts containing tax regulation claims
- Translate Sinhala / Tamil posts using Google Translate API with manual verification
- Annotate dataset using Label Studio — accurate / partially accurate / misleading / false
- Calculate inter-annotator agreement using Cohen's Kappa
- Analyze spread patterns — compare engagement metrics of accurate vs inaccurate content
- Train misinformation classifier: compare fine-tuned XLM-R vs RAG-based claim verification vs GPT API
- Virality prediction model — identify linguistic features that predict high spread

**Novel Contribution**

- First annotated Sri Lankan tax regulation misinformation dataset
- First measurement of misinformation prevalence in Sri Lankan SME social networks
- First cross-lingual misinformation detection model for South Asian regulatory content

**The Solution Built**

A real-time claim verification interface — SME owners paste any compliance claim received from any source, and the system instantly checks it against verified official regulations with a cited verdict.

# 5. How All Four Modules Connect

The four modules are not separate tools — they are four investigations of the same problem feeding into one unified platform:

|**Module**|**Barrier Investigated**|**What It Feeds Into the Platform**|
|---|---|---|
|1 — Awareness Gap|Regulatory changes not reaching SMEs in time|Gazette monitor → auto-updates knowledge base → triggers risk reassessment|
|2 — Knowledge Gap|Incorrect guidance being received by SMEs|Verified knowledge base used by all other modules|
|3 — Risk Gap|Compliance risk invisible until too late|Risk scores updated when Module 1 detects new regulations|
|4 — Misinformation Gap|Wrong information spreading faster than correct information|Claim verifier draws from Module 2 knowledge base|

|   |
|---|
|**The Unified Platform Name:**<br><br>SME Regulatory Intelligence Platform — An AI-powered system that delivers the right information, to the right SME, at the right time, in the right language.|

# 6. Data Collection Summary

|**Module**|**Primary Novel Data**|**Supporting Public Data**|**Collection Method**|
|---|---|---|---|
|1|SME awareness survey — when did they find out?|Gazette archives, news archives, IRD notices|Survey + web scraping + PDF parsing|
|2|Compliance knowledge test — what do SMEs actually know?|IRD / EPF / ETF / eROC official documents|Survey + document analysis + social media scraping|
|3|SME vulnerability survey — who fails and why?|Court records, IRD defaulter lists, Central Bank stats|Survey + public records + synthetic generation|
|4|Annotated social media misinformation dataset|FactCheck.lk, Facebook groups, Twitter, Reddit|Social media scraping + manual annotation|

Important: No private enterprise data is required. All data is either publicly available, collectable through ethical surveys, or synthetically generated and calibrated against public population statistics.

# 7. Technology Stack

|**Layer**|**Technology**|**Used In**|
|---|---|---|
|Data Collection|Scrapy, BeautifulSoup, Facebook API, Twitter API, Google Forms|All modules|
|PDF Parsing|PyMuPDF, pdfplumber|Module 1, 2|
|Data Processing|Python, Pandas, NumPy|All modules|
|NLP / Classification|HuggingFace Transformers, XLM-R, mBERT, spaCy|Module 1, 2, 4|
|RAG Pipeline|LangChain, ChromaDB, FAISS|Module 2, 4|
|ML Models|scikit-learn, XGBoost, TensorFlow / Keras|Module 1, 3|
|Model Interpretability|SHAP|Module 3|
|Annotation Tool|Label Studio|Module 4|
|Synthetic Data|SDV, Faker|Module 3|
|Translation|Google Translate API|Module 4|
|Evaluation|RAGAS, Cohen's Kappa, scikit-learn metrics|Module 2, 4|
|Visualization|Plotly, Seaborn, Matplotlib|All modules|
|Frontend|React.js, TailwindCSS|All modules|
|Backend|FastAPI|All modules|
|Database|PostgreSQL, ChromaDB|All modules|

# 8. Novel Contributions — Why This Has Research Value

|**Contribution Type**|**What It Is**|**Why It Is Novel**|
|---|---|---|
|New Dataset|Information lag dataset for Sri Lankan regulatory changes|Never measured or published before|
|New Dataset|Compliance knowledge gap scores for Sri Lankan SMEs|No benchmark exists for this|
|New Dataset|Sri Lankan tax misinformation annotated corpus|First of its kind for South Asian regulatory context|
|New Finding|Measured lag between gazette publication and SME awareness|Unknown — this research discovers it|
|New Finding|Accuracy rate of informal compliance guidance channels|Unknown — this research measures it|
|New Finding|Top predictors of SME compliance failure in Sri Lanka|Unknown — this research identifies them|
|New Finding|Misinformation prevalence and spread patterns in SME networks|Unknown — this research quantifies it|
|New Framework|Public-signal-based compliance risk prediction methodology|Applicable to any data-scarce developing economy|

# 9. The Complete Research Loop

|**Stage**|**What Happens**|
|---|---|
|Problem|Sri Lankan SMEs are non-compliant due to 4 information barriers|
|Investigation|Each barrier is measured — lag duration, knowledge gap score, risk predictors, misinformation rate|
|Finding|Specific, quantified evidence of each barrier's severity — things nobody knew before|
|Solution|Each module directly addresses its measured barrier with a validated intervention|
|Validation|Solution is tested against the same measurements used to investigate the problem|
|Contribution|Proof that the solution reduces each barrier — with numbers, not assumptions|

# 10. How to Present This to the Supervisor

|   |
|---|
|**What to Say:**<br><br>Our research question is about a real human problem — why Sri Lankan SMEs fail at compliance despite intending to comply. We identify 4 specific information barriers as root causes and investigate each one empirically. Technology is our investigative instrument — not our research subject. Our findings will tell us something new about SME compliance behavior in Sri Lanka that nobody currently knows — backed by 4 novel datasets and 4 measurable research findings. No private enterprise data is required — all data is public, surveyable, or synthetically generated.|

# 11. Individual Member Responsibilities

|**Member**|**Module**|**Individual Research Question**|**Novel Dataset**|
|---|---|---|---|
|215075J — Mohamed M.R.I|Module 1 — Awareness Gap|What is the information lag between gazette publication and SME awareness?|Regulatory change lag timeline dataset|
|215007F — Ahamadh M.S.A|Module 2 — Knowledge Gap|How accurate is the compliance guidance Sri Lankan SMEs receive?|Compliance Q&A benchmark dataset|
|215008J — Ahamed T.I|Module 3 — Risk Gap|Which SME characteristics predict compliance failure before it occurs?|SME vulnerability and violation dataset|
|215019T — Cader Z.R|Module 4 — Misinformation Gap|How does tax misinformation spread through Sri Lankan SME networks?|Annotated misinformation corpus|

# 12. Suggested Timeline

|**Phase**|**Period**|**Key Activities**|
|---|---|---|
|Phase 1 — Problem & Literature|Feb 2026|Literature review, confirm research gap, finalize research questions per module|
|Phase 2 — Data Collection|Mar 2026|Gazette scraping, survey design and distribution, social media collection, ethics approval|
|Phase 3 — Analysis and Modelling|Apr 2026|Data analysis, model training, annotation, benchmark construction|
|Phase 4 — Platform Development|May 2026|Build unified prototype integrating all 4 module solutions|
|Phase 5 — Validation|Jun 2026|User testing, solution validation against research findings, evaluation metrics|
|Phase 6 — Write-up and Submission|Jul–Aug 2026|Research report, thesis chapters, demo preparation, viva rehearsal|

_— End of Research Proposal Summary —_