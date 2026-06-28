# Enigmatrix — Module 1 Evaluation-Panel Brief

**What I planned, what I built, what I upgraded, and what I will train.** A complete, demonstration-ready account of Module 1 for the interim evaluation panel — written so I can walk a panel through my contribution end-to-end, defend every design choice, and show exactly where the work stands.

|||
|---|---|
|**Presenter / module owner**|Mohamed M.R.I (215075J) — Module 1 (Regulatory Change Awareness Gap)|
|**Project**|Enigmatrix — SME Regulatory Intelligence Platform (4-person group)|
|**Group**|215075J Mohamed M.R.I (M1) · 215007F Ahamadh M.S.A · 215008J Ahamed T.I · 215019T Cader Z.R|
|**Programme**|Final-year research project · Faculty of IT · University of Moratuwa · Batch 21, 2026|
|**Compiled**|2026-06-02 (verified against codebase HEAD `fca3a2f`, migrations & submodule git logs)|

> **How to use this in the panel.** §1 frames the whole platform and the four modules in one minute. §2–§3 are my Module-1 elevator pitch and the pipeline map. **§4 is the extraction engine — Phase 1 (what I built) then the Phase-2 Upgrade explained slice by slice.** **§5 is the model-training / fine-tuning plan — the next level, fully designed.** §6 covers the other three modules briefly. §7 is my concrete demo list. §8 is the planned/did/upgraded/pending ledger. §9 is anticipated questions + answers.

---

## 1. The platform and the four modules (1-minute overview)

**The problem.** Sri Lankan SMEs (52 % of GDP, 45 % of employment) systematically miss regulatory changes: the Official Gazette publishes ~500 binding amendments a year, in three languages (EN/SI/TA), as unstructured PDFs — no push notification, no machine-readable metadata, a measured **33–70 day** awareness lag. Evidence: **34 %** of IRD SME penalty assessments (2023) came from amendments gazetted > 90 days before audit; **61 %** of audited SMEs were unaware of an EPF rate change; our 40-SME pre-pilot found median lag **33 d urban / 58 d rural**, **72 % rely on WhatsApp**.

**The solution.** A trilingual web platform of four modules. **Each tackles a distinct "gap":**

|#|Module|The gap it closes|Characteristic output|Status|
|---|---|---|---|---|
|**1**|**Awareness Gap** (mine)|SMEs don't _know_ a regulation changed|Auto-ingested, classified, sector-mapped gazettes + alerts ≤ 24 h + a measured lag dataset|🟡 Pipeline shipped; classifier next|
|2|Knowledge Gap (Knowledge Hub)|SMEs don't _understand_ the rules they know|Auto-scored knowledge assessment + RAG Q&A over the corpus|✅ Surveys + scoring shipped; RAG pending|
|3|Risk Invisibility (Risk Scoring)|SMEs can't _see their own_ compliance risk|Composite vulnerability score + SHAP explanations|🟡 Data shipped; model pending|
|4|Misinformation|SMEs can't tell _authentic_ regulatory info from rumour|9-class veracity classifier + claim verifier|🔲 Design only; `/verify` returns 501|

**The research trick worth stating to the panel:** _the platform is the research instrument._ The same Module-1 pipeline that helps SMEs also timestamps the awareness lag — so one build produces both an engineering artefact (the alert system) and a research artefact (the first measured Sri Lankan regulatory-diffusion dataset). Module 1 also produces the labelled gazette corpus that Modules 2/3/4 consume.

---

## 2. Module 1 at a glance (my elevator pitch)

**One sentence:** Module 1 ingests every gazette within ~6 hours, classifies it into 12 regulatory categories + 10 SME sectors, summarises and alerts matched SMEs within 24 hours, and records timestamps so the awareness lag becomes measurable for the first time.

**My research questions and how I answer them:**

|RQ|Question|Method|Target|
|---|---|---|---|
|RQ1|Can NLP classify SL gazettes into SME categories?|XLM-R + LoRA on ≥ 800 labelled docs|macro-F1 ≥ 0.92|
|RQ2|One multilingual model for EN/SI/TA (no per-language pipelines)?|XLM-R vs mBERT vs IndicBERT ablation|F1 within 5 % across languages|
|RQ3|What is the median publication→awareness lag?|Propagation timestamps + paired SME survey|≥ 200 reg × ≥ 4 stages × ≥ 100 SMEs|
|RQ4|Which channels deliver fastest?|Channel-stratified lag analysis|Ranked channel table|
|RQ-DiD|Does my alert system _reduce_ the lag?|Difference-in-Differences (alerted vs control)|Significant reduction (33 d → < 1 d)|

**Headline status:** the data-collection apparatus (ingest → extract → preprocess) and a measurement/evaluation layer are **built and deployed**; the **classifier (the keystone) and everything downstream of it are designed but not yet trained**. That honest split is the spine of this brief.

---

## 3. The Module-1 pipeline, end to end

```
Stage A  Ingestion (Scrapy spiders)         ✅ BUILT        → status: ingested
Stage B  Extraction (PDF → text)            ✅ BUILT        → status: extracted
Stage B+ Preprocessing (clean/lang/meta)    ✅ BUILT        → status: preprocessed
   +  Phase-2 Upgrade: measurement engine, dataset registry, extraction-profile registry  ✅ BUILT
══════════════════════════════════════════════  ◀── WE ARE HERE today
Stage C  Classification (XLM-R + LoRA)       🔲 PLANNED  ← the keystone   → classified
Stage D  Summarisation (MarianMT, EN/SI/TA)  🔲 PLANNED                    → summarised
Stage E  Alert dispatch (SendGrid + Twilio)  🔲 PLANNED                    → alerted
Stage F  Lag measurement (portal/RSS watchers → m1_propagation_events)  🔲 PLANNED
Stage G  Research notebooks (Findings F1–F6) 🔲 PLANNED
```

**Each stage as Planned → Did → Why (brief):**

|Stage|What I planned|What I did|Why this design|
|---|---|---|---|
|A Ingest|Auto-crawl `documents.gov.lk` + `gazette.lk`|Scrapy spiders (`_base` → EGZ/GZ/BILL/ACT/weekly), SHA-256 dedup, partitioned storage, early-exit|Gazettes have no API; a polite crawler is the only reliable feed; early-exit cut a 2-day crawl from 10 min → 1–2 min|
|B Extract|Turn any PDF (text/scanned, 3 languages) into clean text|3-tier `classify_pdf` → PyMuPDF / pdfplumber / Tesseract chain|Gazettes are a mix of digital and scanned PDFs; one extractor can't handle all → route by type|
|B+ Preprocess|Normalise, detect language, pull metadata + penalties|Cleaning + fastText language ID + Wijesekara conversion + regex metadata + multi-penalty + §-chunking|Sinhala/Tamil + legacy fonts + section structure all need handling before a model can read it|
|**Upgrade**|Make extraction _measurable and swappable_|Measurement engine + versioned datasets + pluggable extraction profiles (8 slices)|Phase 1 had no objective accuracy number; I rebuilt it so every improvement is a measurable delta (see §4.2)|
|C Classify|Auto-assign 12 categories + 10 sectors|**Not yet — needs labels + model**|This is the research core (RQ1/RQ2); §5 is the full plan|
|D–G|Summarise, alert, measure lag, compute findings|**Not yet — downstream of C**|All unlock mechanically once rows flip `preprocessed → classified`|

---

## 4. Deep dive 1 — The Extraction Engine (the heart of what I built)

This is my largest shipped contribution. I built it in two phases: a working chain (**Phase 1**), then a re-engineering that makes extraction **measurable, versioned, and swappable** (**Phase 2 Upgrade**).

### 4.1 Phase 1 — the original extraction approach (built, deployed)

**The plan:** take any gazette PDF — digital or scanned, in any of three languages, sometimes in a pre-2010 legacy Sinhala font — and reliably produce clean, structured text.

**What I built, and why each choice:**

| Component                        | What it does                                                                                                                                                                    | Why this choice                                                                                                                                                                                            |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `classify_pdf()` — 3-tier router | Reads avg chars/page → labels `text_pdf` (≥ 200), `hybrid` (30–200), or `scanned` (< 30)                                                                                        | One extractor can't serve all PDF types; cheap heuristic routing avoids running slow OCR on digital PDFs. Thresholds `(200, 30)` were **calibrated** to maximise `min(text_pdf_recall, scanned_precision)` |
| PyMuPDF extractor                | Fast path for digital PDFs; `TEXTFLAGS_TEXT` preserves Sinhala/Tamil ligatures                                                                                                  | ~80 ms/page, accurate, keeps column order and complex glyphs                                                                                                                                               |
| pdfplumber extractor             | Layout-aware path (`layout=True`) for multi-column / table pages                                                                                                                | Handles the gazette's two-column legal layout that PyMuPDF flattens                                                                                                                                        |
| Tesseract OCR                    | `--oem 1 --psm 6 --lang eng+sin+tam` @ 300 dpi for scanned pages                                                                                                                | Only offline engine with trained Sinhala + Tamil models; per-page timeout stops it hanging                                                                                                                 |
| fastText language ID             | `lid.176.bin`, predicts on first 500 chars, `k=3`, conf ≥ 0.70 else `mixed`                                                                                                     | 500-char window dropped EN-preamble/SI-body misclassification from 12 % → < 3 %; ~97 % accuracy offline in < 1 ms                                                                                          |
| Wijesekara conversion            | Detects ≥ 50 consecutive ASCII-alpha in a Sinhala span → converts legacy font to Unicode                                                                                        | Pre-2010 gazettes (~38 % of that era) use non-Unicode fonts a model can't read                                                                                                                             |
| Preprocessing                    | Noise removal → metadata regex (`gazette_number`, `effective_date`, `amendment_type`, `principal_act_amended`) → `extract_all_penalties()` (7 penalty types) → §-aware chunking | A model needs clean, sectioned text within the 512-token window; Sinhala/Tamil cost 2–2.3× tokens, so chunking by section avoids truncation                                                                |

**Outcome:** a fresh PDF flows `ingested → extracted → preprocessed`, with `cleaned_text`, penalties, and sub-document sections persisted, plus an admin pipeline portal to watch it. **This is demonstrable live.**

### 4.2 Phase 2 — the Upgrade, explained slice by slice

**The problem I found with Phase 1:** it worked, but I had _no objective number_ for how good the extraction was, and the chain was hard-wired — I couldn't try a better extractor without risking the production data. So I re-architected extraction around **four ideas**, delivered as **eight slices**.

**The four architectural ideas:**

1. **Datasets become first-class** — a versioned dataset registry replaces the single implicit `m1_regulations` table.
2. **Versioning** — every extraction/measurement references a _sealed, SHA-256-hashed_ dataset version → reproducible accuracy claims.
3. **Pluggable profiles** — an `ExtractorProfile` protocol turns the hard-wired chain into one interchangeable profile (`legacy_v1`) among many.
4. **Measurement-as-a-pure-function** — an engine that scores any two dataset versions with no side effects → deterministic, repeatable scoring.

**The eight slices (one by one):**

| #     | Slice                                            | What it builds                                                                                                                                                                                                                                                       | Why it beats Phase 1                                                                                                         | Status                                            |
| ----- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| **1** | **Measurement scaffolding + golden-set lock**    | ML `evaluation/` package: field-metric registry (string/semantic/date/categorical/numeric/text-summary) + completeness model; locks the 16 canonical fields; baseline scorecard of `legacy_v1` vs a manual Excel ground-truth → `baseline_v0.json`                   | Phase 1 had **zero** accuracy measure; this fixes a baseline so all later work is a measurable delta                         | ✅ Built                                           |
| **2** | **Raw-text golden set + κ tooling**              | 10 hand-transcribed PDFs across 8 failure-mode strata; Cohen's κ inter-annotator report; `jiwer` CER/WER tooling; adjudicated `gold.txt`                                                                                                                             | Phase 1 never quantified character-level corruption (e.g. legacy-font CID markers); now I can measure it                     | ✅ Built                                           |
| **3** | **Dataset registry + versioning + Excel upload** | Tables `m1_datasets` / `m1_dataset_versions` / `m1_dataset_rows`; tolerant Excel parser; admin flow to upload → review → seal → promote to ground truth (SHA-256 idempotent, 50 MB cap, MIME-whitelisted)                                                            | Phase 1 had no concept of a versioned ground-truth dataset — the backbone everything else references                         | ✅ Built                                           |
| **4** | **Extraction-profile registry + legacy adapter** | `ExtractorProfile` protocol; `LegacyV1Profile` wrapping the frozen Phase-1 chain; Celery dispatcher (`run_extraction_with_profile`); table `m1_extraction_profiles`; PDF resolver. Faithfulness test: legacy output is **byte-identical** to existing `cleaned_text` | Turns the hard-wired chain into a swappable plugin → enables apples-to-apples profile comparison without touching production | ✅ Built                                           |
| **5** | **Measurement engine (backend)**                 | Pure-function Celery task `run_measurement(baseline, candidate)` → `m1_measurement_runs` + `m1_measurement_scores`; 9 API routes (`/per-field`, `/worst`, `/calibration`)                                                                                            | Promotes slice-1's script into reproducible, UI-triggerable infrastructure comparing _any_ two versions                      | ✅ Built                                           |
| **6** | **Comparison UI + dashboard**                    | Admin pages: runs list, per-run dashboard (KPI cards, per-field heatmap, slice breakdowns, worst-20, conditional calibration plot), per-regulation side-by-side diff                                                                                                 | Makes failure modes (e.g. a CID-corrupted `title_si`) findable at a glance instead of SQL-only                               | 🔲 Planned (depends on 5)                         |
| **7** | **Three new extraction profiles**                | `page_routing_v1`, `wijesekara_routing_v1`, `surya_fallback_v1` + `page_engines/` + font-aware Wijesekara + per-font YAML maps; each gated at "≥ +3 pp vs legacy"                                                                                                    | Directly attacks Phase 1's worst failure — document-level routing letting a clean cover page mask a corrupted body           | 🟡 Partial (2 profiles built; Surya GPU-deferred) |
| **8** | **Backfill, polish, thesis artefacts**           | Backfill `m1_regulations` → `legacy_baseline_v1`; Great Expectations schema suite; `make thesis-artifacts`; 30-day retention; CI; `m1-phase2-complete` tag                                                                                                           | Makes historical extractions measurable, makes the thesis chapter reproducible, hands Phase 3 a clean dataset card           | 🔲 Planned (depends on 1–7)                       |

**The three new extraction profiles (slice 7) — what each adds over `legacy_v1`:**

- **`page_routing_v1`** — routes extraction **per page** (not per document) with multi-engine consensus, so a clean cover page can no longer hide a corrupted body the way the document-averaged `classify_pdf` did.
- **`wijesekara_routing_v1`** — inherits page-routing and adds **font-name detection**, converting legacy-font spans _before_ page assembly, using an expanded **~180-entry** map (vs the old 87) with per-font YAML tables; reports a `cid_marker_count` quality signal.
- **`surya_fallback_v1`** — inherits Wijesekara-routing and re-extracts low-confidence (< 0.6) Sinhala pages through the **Surya OCR** model instead of Tesseract; GPU-preferred, so deliberately deferred to Phase 3 where GPU is available.

**What I can claim to the panel about the Upgrade:** I turned a working-but-opaque extractor into a _measurable, versioned, swappable_ extraction platform — slices 1–5 are built and deployed (migrations `202605240002/3/4`, backend + ML submodule commits "slice 3/4/5"), slice 7 has two of three profiles, and slices 6 & 8 are scoped and ready to build.

### 4.3 Phase 1 vs Phase 2 — at a glance

|Dimension|Phase 1|Phase 2 Upgrade|
|---|---|---|
|Extraction|One hard-wired chain|Many pluggable `ExtractorProfile`s; `legacy_v1` is just one|
|Accuracy|No objective measure|Field-level + character-level (CER/WER) measurement engine|
|Ground truth|None|Versioned, SHA-256-sealed datasets + manual Excel gold set|
|Reproducibility|Implicit|Every run pinned to a sealed version|
|Improving it|Risky (touches prod)|Safe A/B: run a new profile, measure the delta, promote only if it wins|

---

## 5. Deep dive 2 — Model Training (the next level: designed, not yet trained)

This is the research core (RQ1 + RQ2) and **the keystone gap**: there is no trained classifier yet (no `enigmatrix-ml/m1/model/`, zero labelled examples). Below is the full plan I will execute — and which I can defend in detail to the panel.

> **Honesty note for the panel:** the Session-56 bulk run that "classified 800 PDFs" used a **regex statute classifier** for corpus seeding — it is _not_ the ML model and does _not_ satisfy RQ1. The trained classifier is genuinely the next phase.

### 5.1 The task and why a model is needed

Stage C must assign each gazette to **one of 12 regulatory categories** (single-label) **and** to **one or more of 10 SME sectors** (multi-label). Rules/keywords top out around F1 ≈ 0.60–0.65; the research bar is **macro-F1 ≥ 0.92** across three languages — only a fine-tuned multilingual transformer reaches that.

### 5.2 How I get the data (solving the chicken-and-egg)

Training needs labels; good sampling needs a model. The resolution: **pool-based active learning.**

1. Stand up **Label Studio**; deploy the 12-category + 10-sector config; run a **20-doc calibration** round (gate annotators at κ ≥ 0.80).
2. Sample the first **200** docs (stratified by year+language + k-means k=20 diversity + minority-class hand-picks) from the `preprocessed` corpus.
3. Train a throwaway **AL baseline** (TF-IDF + LR) → score the unlabelled pool by uncertainty → annotate the next most-uncertain batch → repeat to **800 labels** (≥ 50/category, dual-annotated IAA κ ≥ 0.75). Active learning cuts labelling effort ~40 %.

The AL baseline (used only to pick what to label) is kept **separate** from the production baseline (trained on the full set) so early/biased labels never contaminate the comparison.

### 5.3 Which models I compared, and why XLM-R + LoRA (the "trying existing models" part)

I evaluated the realistic candidates against four constraints: **≥ 0.92 macro-F1**, **strong Sinhala+Tamil**, **fits a CPU latency budget (≤ 2 s)**, and **offline + reproducible + cheap**.

|Model / approach|Est. macro-F1|Cost|Deploy size|Decision & reason|
|---|---|---|---|---|
|Rule-based regex|~0.60|$0|~0|Baseline only (ablation reference)|
|TF-IDF + Logistic Regression|~0.65|~$0|tiny|**Production baseline** XLM-R must beat by ≥ 0.10|
|Train transformer from scratch|~0.55|$500–2k, 50k labels|—|Reject — infeasible at 800 docs|
|distilBERT-multilingual (66M)|~0.74|low|small|Reject — limited SI/TA vocab|
|Zero-shot GPT-4|~0.72 (EN 0.84 / SI 0.61 / TA 0.58)|API|n/a|Reject — weak SI/TA, non-reproducible, no offline, no calibrated confidence|
|mBERT (110M)|~0.79–0.83|~$0.005/1k|~440 MB|Reject — below XLM-R; thinner Sinhala vocab|
|**XLM-R base (125M) + LoRA**|**~0.87 → target 0.92**|**~$30 one-off**|**125M + 2.4M adapter**|**SELECTED**|
|XLM-R large (355M)|~0.91|3× memory|too big|Reject — blows the CPU latency budget|
|IndicBERT (212M)|~0.83|—|—|Reject — weaker English (English is the majority language)|
|XLM-R full fine-tune (no LoRA)|+~0.5 pp|50× trainable params|475 MB|Reject — no real gain at 800 docs|

**Why XLM-R base + LoRA wins:** (1) its SentencePiece 250k vocab covers Sinhala + Tamil natively; (2) it beats mBERT 5–10 pp on low-resource languages; (3) at 125M it fits ONNX-CPU within the 2 s budget; (4) **LoRA** adds implicit regularisation at only 800 docs, trains 2.4 MB adapters (vs 475 MB), and fits a 4 GB GPU. _(The 0.92 figure is a projection — extrapolated from a 50-doc pilot at 0.78 and Chalkidis 2019 EUR-Lex at 0.91 — which I'll state honestly as a target, not a result.)_

### 5.4 How I fine-tune it (the method)

**LoRA configuration** (and why each value):

|Hyperparameter|Value|Justification|
|---|---|---|
|`r` (rank)|16|r=8 under-fits SI/TA; r=32 over-fits at 800 docs|
|`lora_alpha`|32|canonical `alpha = 2r`|
|`target_modules`|`["query","value"]`|Hu 2021 standard; adding key/output costs latency for < 1 pp|
|`lora_dropout`|0.1|matches encoder-native dropout|
|Trainable params|**2,421,696 (1.94 %)**|98 % of the model stays frozen|

I'll run a **27-run ablation** (r ∈ {8,16,32} × alpha ∈ {16,32,64} × 3 seeds) to confirm.

**Dual-head architecture:** shared XLM-R encoder → CLS token → Dropout(0.3) → **category head** `Linear(768→12)` + softmax (argmax) **and** **sector head** `Linear(768→10)` + sigmoid (threshold 0.50). Combined loss `= 0.7·CrossEntropy(category) + 0.3·BCEWithLogits(sector)` — α = 0.7 because category is the primary research metric, but sector is trained jointly to share encoder gradients.

**Training protocol:** **temporal** split 70/15/15 (560/120/120) by `gazette_published_date` — _not_ random, to avoid leaking future regulatory language — with a minimum 30-day test window; **3 seeds (42, 1, 2)** reported as mean ± std; **back-translation augmentation** (train split only, capped 5×) for sparse categories; **AdamW** with differential LR (2e-4 LoRA / 2e-5 heads), 10 % warmup, batch 16, ≤ 10 epochs, **early-stop patience 3** on val category macro-F1, grad-clip 1.0, FP16. A `model_registry.json` fingerprint (data SHA-256 + env SHA-256 + git SHA + split boundaries) makes every run reproducible.

### 5.5 How I evaluate it

|Metric|Target|
|---|---|
|Category macro-F1|≥ 0.92 (top-1 ≥ 0.95, ECE ≤ 0.05)|
|Sector macro-F1|≥ 0.88|
|Per-language F1|EN ≥ 0.93 · SI ≥ 0.88 · TA ≥ 0.86 (RQ2: within 5 %)|

Plus **slice analysis** (per-language, per-year-quarter for drift, per-text-length, per-extraction-method) with a "no slice cliff > 8 pp" rule, and a **4-type error taxonomy** (truly-ambiguous, OCR-corrupted, domain-shift, annotator-inconsistency) — I hand-read the 100 most-confidently-wrong predictions into `error_analysis_topwrong.csv`.

### 5.6 BUILD_11 — the training pipeline ("the eleventh")

BUILD_11 is the **ML Training Pipeline** build doc — the opinionated, reproducible training harness that sits around the model. It lays out eight stages: **(1)** versioned datasets (manifest + SHA-256 + row-count gate), **(2)** MLflow experiment tracking, **(3)** a `BaseTrainer` (seed → load → MLflow run → env snapshot → fit/evaluate/save → record to a `training_runs` table), **(4)** Optuna hyperparameter sweeps, **(5)** evaluation gates, **(6)** model-registry promotion (`is_production` flip), **(7)** auto-generated model cards, **(8)** nightly CI retraining on new `data-v*` tags. Prescribed files: `ml/m1/{train_xlmr,sweep,eval}.py`; the research design adds `ml/m1/model/{architecture,training,evaluation,calibration}.py`.

> **Design decision I will flag to the panel (shows rigour):** BUILD_11's scaffold trainer is currently **single-head 12-class full fine-tune with a 0.80 F1 gate (CPU)**, whereas my Module-1 research design is **dual-head XLM-R + LoRA targeting 0.92 (GPU)**. These must be reconciled before training — I'll adopt the dual-head LoRA design as the research target and keep the single-head full-FT as a fallback/sanity baseline. Naming this discrepancy _before_ the panel does demonstrates I've read my own pipeline critically.

### 5.7 Deployment

Export to **ONNX** (opset 17, dynamic batch, outputs `category_logits` + `sector_logits`), serve on **ONNX Runtime CPU** with **INT8** quantisation, target **~1.8 s/gazette** (≤ 2 s budget), behind a `classify_gazette` Celery task that flips rows `preprocessed → classified`. A Redis cache keyed on `model_version:gazette_number:gazette_date:text_hash` avoids re-inference.

---

## 6. The other three modules (brief, for completeness)

I own Module 1, but the panel will want the whole picture and how my module feeds the others.

- **Module 2 — Knowledge Hub (compliance _knowledge_ gap).** ✅ Built: 3-instrument survey design + auto-scoring engine + `knowledge_score` API + demo data. 🔲 Pending: RAG Q&A over the gazette corpus (ChromaDB + RAGAS), real CA-verified question bank. _No classifier trained — only a read-only `multilingual-e5-base` embedding model._ **Consumes my classified corpus** for its knowledge content.
- **Module 3 — Risk Scoring (compliance-risk _invisibility_).** ✅ Built: six `m3_*` tables + the survey-projection pipeline populating `m3_compliance_history` / `m3_behavioural_signals`. 🔲 Pending: the XGBoost + SHAP model (targets AUROC ≥ 0.75, P@10 % ≥ 0.60). **Uses my alert-delivery records** as a risk feature (treatment vs control).
- **Module 4 — Misinformation.** 🔲 Design only — nothing built; `/api/v1/verify/claim` returns **501**. Plan: 9-class veracity classifier (XLM-R) + RAG-NLI verifier, target macro-F1 ≥ 0.75. **Depends on my labelled corpus** to bootstrap.

---

## 7. What I can demonstrate to the panel (concrete)

**Live (deployed / runnable):**

- The platform on Railway + Vercel: auth, the regulation admin CRUD with expert-verification, the unified EN/SI/TA survey wizard.
- The **M1 pipeline portal**: trigger an extraction over a date range and watch a gazette flow `ingested → extracted → preprocessed` with the 6-stage flow diagram, throughput chart, and per-regulation trace.
- A real gazette opened to show extracted `cleaned_text`, detected language, extracted penalties, and sub-document sections.
- The **dataset registry**: upload the manual Excel as a sealed, versioned ground-truth dataset.

**Artefacts / numbers:**

- The **measurement engine** output: a `legacy_v1` baseline scorecard (per-field accuracy) and the raw-text CER/κ tooling — my objective evidence that extraction works.
- The **model-comparison table** and **LoRA/dual-head design** (§5) as the methodology I'm about to execute.
- The codebase scale: 24 Alembic migrations, the `enigmatrix-ml` evaluation + extraction-profile packages, and the Phase-2 Upgrade commits.

**Diagrams to bring:** the top-level platform architecture, the A→G pipeline with the "we are here" marker, and the dual-head classifier diagram.

---

## 8. Status ledger — Planned / Did / Upgraded / Pending

|Area|Planned|Did ✅|Upgraded ⬆|Pending 🔲|
|---|---|---|---|---|
|Ingestion (A)|Auto-crawler|Scrapy spider suite + dedup + early-exit|Multi-source registry, partitioned storage|—|
|Extraction (B)|3-tier PDF→text|`classify_pdf` + PyMuPDF/pdfplumber/Tesseract|Per-page routing profiles (slice 7)|Surya OCR profile (GPU)|
|Preprocess (B+)|clean/lang/meta|fastText + Wijesekara + metadata + penalties + chunking|font-aware Wijesekara, ~180-entry maps|—|
|Measurement|— (new idea)|Eval engine + dataset registry + profile registry (slices 1–5)|the whole layer is the upgrade|Comparison UI (6), backfill/thesis (8)|
|**Classification (C)**|XLM-R + LoRA dual-head|—|—|**Annotation → 800 labels → train → ONNX (the keystone)**|
|Summarise/Alert/Lag (D–F)|MarianMT + SendGrid/Twilio + watchers|—|—|All — downstream of C|
|Findings (G)|F1–F6 notebooks + DiD|—|—|Needs C + survey at scale|

---

## 9. Anticipated panel questions & my answers

- **"Your classifier isn't trained — what _have_ you done?"** → I built and deployed the entire data-collection and _measurement_ apparatus (ingest → extract → preprocess + a versioned measurement engine), which is the prerequisite for a trustworthy classifier. The model is fully designed (§5); the next phase is annotation + training. Interim reports are explicitly allowed to have testing pending.
- **"Why not just use GPT-4 / an LLM?"** → I measured it: zero-shot GPT-4 scores ~0.72 with weak Sinhala/Tamil (0.61/0.58), is non-reproducible, needs the cloud, and gives no calibrated confidence. XLM-R + LoRA is offline, reproducible, ~$30, and hits the multilingual bar.
- **"How do you train with only 800 labels?"** → LoRA (1.94 % trainable params) for regularisation + back-translation augmentation + active learning to spend labels where they matter, all on a temporal split so results generalise forward.
- **"How do you know your extraction is any good?"** → That's exactly why I built the Phase-2 measurement engine: field-level accuracy vs a sealed Excel ground truth and character-level CER/WER vs hand-transcribed gold pages — objective numbers, not claims.
- **"What's the single biggest risk?"** → Label scarcity. Mitigations: active learning, augmentation, and a κ ≥ 0.75 annotation gate. It's why annotation starts now.

---

_Companion document: `Enigmatrix_M1_Master_Analysis_and_Interim_Plan` (the full honest planning master-doc with the interim-report gap analysis and 20-week roadmap)._