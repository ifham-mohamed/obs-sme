---
tags: [m1, awareness-gap, status, analysis, roadmap, next-level, canonical]
date: 2026-06-28
module: Module 1 — Regulatory Change Awareness Gap
owner: Mohamed M.R.I (215075J)
analysed-from:
  - "C:/sme (canonical Obsidian vault — this folder)"
  - "C:/Reasearch/xyz (full codebase: backend/frontend/ml/docs submodules)"
sources-cross-checked:
  - interim report (Interim/report/SMEs Interim.docx)
  - 08-Findings-Log (master context, trackers, all plans, findings notes)
  - 03-Data-Sources/m1/raw (800 PDFs + classification CSVs)
  - live code + git (HEAD 037a709, work log through Session 58 / 2026-06-02)
status: reference — full status read + next-level roadmap
---

# Module 1 (Awareness Gap) — Full Status Analysis & Next-Level Roadmap

> Single-source read of **what was planned, what is actually built, what the data shows, what is missing, and what to build next** for your part (Module 1). Cross-checked across the canonical vault (`C:/sme`), the full codebase (`C:/Reasearch/xyz`), the interim report, the findings log + all ~25 plans, and the 800-PDF raw corpus. Generated 2026-06-28.

## 0. Read this first — the "two clocks" caveat

Two records of progress exist and they disagree, because one is ahead of the other:

- **The codebase** (`C:/Reasearch/xyz`, submodules `enigmatrix-backend/frontend/ml`) is current to **~Session 58 / 2026-06-02** (git HEAD `037a709`, June 12). It contains the *executed* Phase-2 Upgrade.
- **This vault** (`C:/sme`): the `SESSIONS.md` + `FEATURES.md` trackers are **current** (Session 59 / F-208), but its **summary docs are stale** — `ENIGMATRIX_MASTER_CONTEXT.md` + `RESEARCH_BUILD_TRACKER.md` are frozen (~Session 43–56) and the `2026-05-23_M1_Phase2_Upgrade_Plan` status tables still read "🔲 Not started" (written May 23, before the work shipped, never flipped).

So where the vault and code disagree about **infrastructure**, the **code is the truth** (verified file-by-file below). Where they discuss the **research outputs** (classifier, lag dataset, survey, findings), **they agree: not built.** Closing this vault-vs-code gap is a cheap P0 task (§7).

---

## 1. One-paragraph verdict

Module 1's **engineering is far ahead of its science.** The ingest → extract → preprocess pipeline is shipped, tested, and **live in production on Railway**, wrapped in a deep admin/observability surface, and recently extended with a research-grade **extraction-quality measurement engine** (golden sets, transcription-kappa, dataset versioning, pluggable extraction profiles — Phase-2 Upgrade slices 1–9, in code). You have also assembled an **800-PDF gazette corpus and machine-classified 500 of them.** But **every graded research output of RQ1 is still unbuilt**: there is no trained NLP classifier (the `model/` layer does not exist), no human-verified gold label set, no information-lag dataset, no alert dispatch, and none of the F1–F6 findings are computed. Those rows are LLM/regex *silver* labels in an **ad-hoc 6-label scheme — not the canonical 12-category taxonomy** (`expert_verified=False`, procedural-dominated), not model output and not a gold set. The next level is to convert this strong foundation — and the silver corpus, which is a real head-start — into the two things the thesis is graded on: a classifier at F1 ≥ 0.92 and a measured awareness-lag dataset.

---

## 2. What Module 1 is (the plan anchor)

From the interim report (Ch. 1, 3.3, 4.3 — methodology confirmed present) and the vault design set:

- **RQ1:** *Are regulatory changes reaching Sri Lankan SMEs in time to act, and what is the information lag between Gazette publication and SME awareness?*
- **Objective 1:** Quantify the lag at every stage (gazette → portal → news → SME awareness), identify the fastest channels, and build an automated gazette-monitoring + **alert** system validated against measured awareness times.
- **Methodology — four-stage temporal study** (interim §4.3.2): **A** Source Monitoring (scrape) → **B** Event Reconciliation (link gazette → portal → news, per-event timeline) → **C** Awareness Measurement (SME survey timestamp) → **D** Lag Analysis (per-transition lag distribution; Kruskal–Wallis across change-type/sector/size/region; rank channels by median time-to-inform).
- The interim §6.3 "Implementation Progress" is written in **future tense** ("will be trained / will be implemented") — i.e. at interim submission, M1 was *specified, not built*. It correctly anticipated the procedural/rate-change class imbalance now visible in the data.

**Success metrics (the yardstick):**

| Metric | Target |
|---|---|
| Category classifier macro-F1 | ≥ 0.92 (BUILD_11 code gate is only ≥ 0.80 — inconsistency, see §6) |
| Sector assignment macro-F1 | ≥ 0.88 |
| Labeled gazette documents | ≥ 800 (≥ 50 / category), IAA Cohen's κ ≥ 0.75 |
| Propagation data points | ≥ 800 (200 regulations × 4 stages) |
| SME awareness survey responses | ≥ 100–200 unique SMEs |
| Ingestion latency | ≤ 6 h from publication |
| Alert delivery latency | ≤ 24 h from publication |

---

## 3. What is actually built (verified against the codebase)

### 3.1 Phase 1 — Foundation ✅
Admin regulation CRUD (list/detail/edit/flow/authoring/new) + expert verify + bulk-verify; audit log on every mutation; awareness survey (12Q, EN/SI/TA) + admin responses; 5 seed regulations + demo SMEs.

### 3.2 Phase 2 — Ingestion + extraction ✅ (shipped, in production)
- **4 Scrapy spiders** — `gazette`, `weekly_gazette`, `acts`, `bills` (+ shared `_base`) behind one parameterised class, with a **Sources hub** (`GET /sources`, `/admin/m1/pipeline/sources`).
- **Celery pipeline** — `gazette_scraper → extract_gazette → preprocess_gazette`, chained; `ingested → extracted → preprocessed`.
- **`enigmatrix-ml/m1/` package** — extraction (`pdf_classifier`, `page_engines/` for PyMuPDF/pdfplumber/pypdfium2/Tesseract + Surya, `ocr`, fastText `language_detection`, **`wijesekara` + `font_aware_wijesekara` + `wijesekara_maps`**, `segmenter`) and preprocessing (`cleaning`, `metadata_extractor`, `chunking`). ~120+ ml tests passing.
- **Operational depth** — completeness check + re-fetch with **EN→SI→TA spider fallback** (found 12–40% monthly miss vs source listings); cancel/rollback endpoint; per-PDF metadata (`sha256`, `pdf_pages`, `language`); durable `m1_extraction_runs` history table; 6-stage pipeline observability portal; **~20 Alembic migrations**.
- **Production** — `enigmatrix-backend` deployed to **Railway** (Session 55).

### 3.3 Phase-2 Upgrade — slices 1–9 ✅ (in code; vault plan status stale)
Verified present in `enigmatrix-ml` + `enigmatrix-backend` + frontend + `data/`:
- **Measurement/evaluation engine** — `enigmatrix-ml/m1/evaluation/` (field metrics, completeness, `date_scope`, strata, **LaBSE semantic** similarity, raw-text CER, aggregates).
- **Raw-text golden set** — `data/golden/raw_text/` (gold + two independent transcriptions `t1`/`t2`, `kappa.json`, `TRANSCRIPTION_PROTOCOL.md`, `STATISTICAL_POWER.md`, `stratum_map.json`).
- **Dataset registry + versioning** — `m1_datasets`/`m1_dataset_versions` + Excel upload + `/admin/datasets/m1/*`.
- **Pluggable extraction profiles** — `legacy_v1`, `page_routing_v1`, `wijesekara_routing_v1`, `surya_fallback_v1`.
- **Measurement runs + comparison UI** — `run_measurement` task + `m1_measurement_runs`/`_scores` + `/admin/datasets/m1/measurements/*`.
- **Slice 9** (Session 58) — dynamic date-range measurement + re-extraction overlap alert + auto v1→v2 versioning.

> Note: this "measurement engine" scores **extraction quality** (extracted fields vs golden, kappa/CER) — it is **not** the RQ1 awareness-lag measurement. Those are two different "measurements"; the second is still ahead (§5).

---

## 4. The data reality (the most important new finding)

`C:/sme/03-Data-Sources/m1/raw/` — assembled mainly in the Session-56 bulk job:

| Item | Reality |
|---|---|
| Raw gazette PDFs on disk | **800** (`pdf/`, SL Extraordinary Gazette, ~Dec 2025–Apr 2026) |
| Machine-generated rows | **500 distinct gazettes** (deduped from 549 curated rows: base `m1_regulations.csv` + 11 `next50/batch*` files; the `v2..v6` CSVs are noisy duplicate snapshots, excluded) |
| Uncovered | **~300 of 800 PDFs** have no curated classified row |
| Classification method | `pdfplumber+claude_classify` / `claude_code_visual_read` — **LLM + regex statute matcher, run outside the production stack** |
| Human-verified? | **No** — `expert_verified=False` and `status='extracted'` for every row; **no gold/label/annotation file exists anywhere** (verified) |
| Category coverage | **6 ad-hoc silver labels, NOT the canonical 12** — `procedural_change` 334, `rate_change` 76, `other` 67, `new_obligation` 15, `registration_change` 7, `structural_change` 1. A **silver→canonical-12 mapping** is required before training. Heavily imbalanced. |
| Sector coverage | `domain_code` lands-heavy (lands 281, customs 68, general 67, …) |
| Extracted full text | Mostly **not persisted** into CSV (only ~11/549 rows carry real `raw_text`/`cleaned_text`) |
| Lag / survey data | **None** — `m1_propagation_events` and `m1_sme_awareness_responses` are defined in schema but **empty**; no train/val/test parquet splits |

**Interpretation:** this is a **silver bootstrap corpus** — a genuine head-start for labeling, but not model output and not a gold test set. It does **not** yet meet RQ1's "≥ 800 labeled, ≥ 50/category, κ ≥ 0.75" bar, and the 800-row CSVs have **no production loader** into the `m1_regulations` DB table.

---

## 5. What is NOT done — the entire research-contribution layer

Vault and code agree on all of the following (statuses quoted from `RESEARCH_BUILD_TRACKER.md` / `ENIGMATRIX_MASTER_CONTEXT.md`):

| Surface | Status | Evidence / what's missing | Blocks |
|---|---|---|---|
| **NLP category classifier (XLM-R + LoRA)** | 🔲 not started | No `enigmatrix-ml/m1/model/` (`architecture`/`training`/`inference`), no `classify_gazette.py`, no `model_registry.json`, no ONNX, no Fly inference, no macro-F1. *"Module 1 NLP (gazette classifier) 🔲 — no training data yet."* BUILD_11 (training) + BUILD_07 (inference) specs exist but unbuilt. | **RQ1, RQ2** |
| **Human gold label set / annotation** | 🔲 not started | No Label Studio, no `gold_standard.csv`, no IAA. *"No annotated training data → M1 classifier blocked → Annotation sprint (Phase 3)."* | RQ1 |
| **Summarisation (MarianMT)** | 🔲 not started | Stage E — `m1_sub_documents` exist to summarise, but no integration. | alerts content |
| **Alert dispatch (SendGrid/Twilio)** | 🔲 not started | `news_watcher.py`/`portal_watcher.py` don't exist; Beat not running for all 15 sources (on-demand only, defaults to a `egz_2026.html` that goes stale in 2027). | **Objective 1 alert system; ≤24h** |
| **Lag dataset / `m1_propagation_events`** | 🔲 not started | Table + views defined, **no insert path, no data**. | **RQ3, RQ4** |
| **SME survey deployment (lag)** | 🟡 instrument only | M0 awareness instrument built; lag-tied, per-regulation responses not collected; needs ≥100–200 + ethics/IRB. | RQ3, F3/F5/F6 |
| **Findings F1–F6** | 🔲 uncomputed | `08_M1_1_Research_Findings_Extraction.md` status *"🟡 notebook scaffolds … population happens during BUILD_07/11 once data flows."* All six gated on the empty propagation/survey tables. | the empirical thesis result |

---

## 6. Plan vs reality — drift, inconsistencies & bugs to fix

- **Doc drift, both directions.** The numbered `m1/` docs + `06-Timeline/02_Module1_Roadmap.md` (dated **2026-05-14**) *undersell* the extraction work (mark shipped things as "🔲 deferred"). The `ENIGMATRIX_MASTER_CONTEXT` + `RESEARCH_BUILD_TRACKER` + the `2026-05-23_M1_Phase2_Upgrade_Plan` status tables (frozen ~Session 43–56) *under-report the code* — they still show the Phase-2 Upgrade as "not started," even though `SESSIONS.md`/`FEATURES.md` did record it (F-200–F-208).
- **Metric inconsistency (fix before viva).** RQ1's published success criterion is **macro-F1 ≥ 0.92**, but the `BUILD_11` code-enforced promotion gate is **`f1_macro ≥ 0.80`**. Pick one and reconcile across docs.
- **Critical UI bug.** `/admin/m1/pipeline/recent` returns **HTTP 503 on every RSC fetch** (Session 53 / F-184); the funnel widget shows impossible rates (7,700%). Still open.
- **Ops gaps.** Beat scheduler not autonomous; the production worker image must stage `lid.176.bin` + pre-warm the `xlm-roberta-base` tokenizer (Dockerfile TODO); `detect_language` is duplicated (follow-up #18); a leaked Railway PAT needs rotation (#12).
- **Knowledge graph stale.** Built from commit `94ae62d0` (2026-05-23); `enigmatrix-ml` carries a separate graph. Re-run `graphify update .` so `/knowledge` stops under-reporting your work.

---

## 7. Next-level roadmap (prioritized & sequenced)

### P0 — Cheap, do-now hygiene (a day or two, high credibility payoff)
1. **Fix the `/recent` 503** and the funnel rate math (F-184).
2. **Classify the remaining ~300 uncovered PDFs** (run the silver classifier over them) to complete 800/800 corpus coverage.
3. **Reconcile the 0.80 ↔ 0.92** F1 gate across BUILD_11 / roadmap / interim.
4. **Promote the 800-row CSVs into `m1_regulations`** via a real loader (BUILD_07 has no import-from-CSV path yet).
5. **Sync the stale summary docs:** flip the `2026-05-23_M1_Phase2_Upgrade_Plan` slice statuses to ✅ and refresh `ENIGMATRIX_MASTER_CONTEXT` + `RESEARCH_BUILD_TRACKER` (the `SESSIONS`/`FEATURES` trackers are already current to F-208), then run `graphify update .`.
6. **Stage models in the worker Docker image** (`lid.176.bin` + tokenizer).

### P1 — The classifier (RQ1/RQ2 headline) 🔴 highest leverage
7. **Build the human gold set.** Stand up Label Studio (config in `09_M1_Annotation_Guidelines.md`); **seed it with your 500 silver-classified rows as pre-annotations** (huge time-saver) + sample from the 300 unclassified; 2 annotators, **κ ≥ 0.75**, reach **≥ 800 labels, ≥ 50/category**. Deliberately over-sample minority categories to fix the procedural/lands skew.
8. **Create `enigmatrix-ml/m1/model/`** — `architecture.py` (XLM-R + LoRA dual head: 12-category + 10-sector), `training.py` (3-seed loop, **temporal 70/15/15 split**, AdamW, early-stop, FP16, back-translation ≤5× train-only), `eval.py` (per-language / per-quarter / per-length / per-extraction-method slices). Specs: `BUILD_11`, `05_*`, `06_*`.
9. **Wire inference** — `app/services/module1/classifier.py` + `classify_gazette.py` Celery task (`preprocessed → classified`); confidence `< 0.55` → review queue; ONNX/INT8 export; deploy. **DoD:** 3-seed macro-F1 ≥ 0.92; EN ≥ 0.93 / SI ≥ 0.88 / TA ≥ 0.86; no slice cliff > 8 pp.

### P2 — Lag dataset + alerts (RQ3/RQ4 + Objective 1) 🟠
10. **Propagation watchers** — `portal_watcher.py` + `news_watcher.py` over the 15-source registry → populate `m1_propagation_events` (Stage A/B). Run Celery Beat for all sources.
11. **Alert dispatch** — `alert_dispatch.py` (SendGrid + Twilio), sector-matched, idempotent on `(regulation_id, sme_id, channel)`, ≤ 24 h.

### P3 — Findings + survey (the empirical answer) 🟡
12. **Deploy the SME survey** at scale (Stage C) — ≥ 100–200 respondents, ethics/IRB, partner outreach (NEDA, Chamber).
13. **Compute F1–F6** — the `findings_*.ipynb` notebooks with median + bootstrap CI + Kruskal–Wallis/Mann-Whitney/DiD; **write `preregistration.md` before unblinding.**
14. **Retraining cadence + auto-rollback.**

---

## 8. Suggested immediate first move

**P1, step 7 — stand up Label Studio and load your 500 silver rows as pre-annotations.** This is the single unlock for RQ1, and you are in a *better* position than the docs imply: the corpus exists and is pre-labeled, so annotation becomes *correction*, not labeling-from-scratch. Everything upstream (scrape → extract → preprocess → dataset versioning → measurement) already feeds the model; the only missing piece between you and a trained classifier is verified labels.

---

## 9. Quick reference

- **Canonical vault:** `C:/sme` (this folder) · **code:** `C:/Reasearch/xyz` (submodules `enigmatrix-backend/frontend/ml/docs/infrastructure`).
- **Data:** `03-Data-Sources/m1/raw/{pdf (800),csv (500 silver-classified, unverified),summary,labeling (Phase-3 batch_01)}`.
- **Plans:** `08-Findings-Log/plans/` (~25) incl. `2026-05-23_M1_Phase2_Upgrade_Plan/`; **trackers/master:** `08-Findings-Log/{ENIGMATRIX_MASTER_CONTEXT,RESEARCH_BUILD_TRACKER,FEATURES,SESSIONS}.md` (latest F-id **F-208**, Session 59).
- **Specs:** classifier training `04-Technology-Stack/ml/BUILD/BUILD_11_ML_Training_Pipeline.md`; inference `…/backend/BUILD/BUILD_07_Module1_Awareness.md`; findings `02-Research-Modules/1 Module-1-Awareness-Gap/08_M1_1_Research_Findings_Extraction.md`.
- **ML model layer to create:** `enigmatrix-ml/m1/model/` (currently absent).
- **Owner:** Mohamed M.R.I (215075J) — Module 1.

*Generated 2026-06-28 from a full read of both folders, the interim report, all plans, and the 800-PDF corpus. Infrastructure status reflects code at git HEAD `037a709` (Session 58 / 2026-06-02); research-output status agrees across vault and code: unbuilt.*
