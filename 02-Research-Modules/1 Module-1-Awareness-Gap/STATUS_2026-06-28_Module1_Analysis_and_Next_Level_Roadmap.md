---
tags: [m1, awareness-gap, status, analysis, roadmap, next-level]
date: 2026-06-28
module: Module 1 — Regulatory Change Awareness Gap
owner: Mohamed M.R.I (215075J)
analysed-from: [E:/Obsidian/sme (vault), C:/Reasearch/xyz (code)]
status: reference — full status read + next-level roadmap
---

# Module 1 (Awareness Gap) — Status Analysis & Next-Level Roadmap

> A single-source read of **what was planned, what is actually built, what is missing, and what to build next** for your part (Module 1) of the Enigmatrix SME Regulatory Intelligence Platform. Cross-checked against both the research vault (`E:/Obsidian/sme`) and the full codebase (`C:/Reasearch/xyz`), the interim report, the `enigmatrix-docs/m1/` design set, the AI work log through Session 58, and the live file tree on 2026-06-28.

---

## 1. The one-paragraph verdict

Module 1 is in an unusually strong but **lopsided** position. The **ingestion + extraction + extraction-quality-measurement infrastructure is built to a genuinely research-grade standard** — well beyond what the original plan asked for — yet the **headline research output of RQ1 has not been produced yet**. You have a working gazette scraper, a multi-engine PDF extraction stack with Sinhala legacy-font handling, a versioned dataset registry, pluggable extraction profiles, and a per-field measurement engine with golden sets and transcription-kappa tooling. What you do **not** yet have is (a) the **NLP classifier** that RQ1 is named after (the `model/` folder is empty), and (b) the **empirical lag findings** (propagation timeline + SME survey at scale + findings notebooks). In short: the plumbing is excellent; the science output is not computed. The next level is to convert that foundation into the two things your thesis is actually graded on — a classifier at F1 ≥ 0.92 and a measured information-lag dataset.

---

## 2. What Module 1 was supposed to be (the plan anchor)

From the **interim report** (Ch. 1, 3.3, 4.3) and the `m1/` design set:

- **RQ1:** *Are regulatory changes reaching Sri Lankan SMEs in time to act, and what is the information lag between Gazette publication and SME awareness?*
- **Objective 1:** Quantify the information lag at every stage (gazette → portal → news → SME awareness), identify the most effective communication channels, and build an automated gazette-monitoring + alert system **validated against measured awareness times**.
- **Methodology — a four-stage temporal study** (interim §4.3.2):
  - **Stage A — Source Monitoring:** continuous scraping (hourly gazette, daily news).
  - **Stage B — Event Reconciliation:** link each gazette publication to its downstream appearances (portals, news) → per-event timeline.
  - **Stage C — Awareness Measurement:** SME survey attaches the "date the SME became aware" timestamp.
  - **Stage D — Lag Analysis:** lag distribution per transition; Kruskal–Wallis across change-type / sector / size / region; rank channels by median time-to-inform.
- **Two research outputs:** (1) an alert system, (2) a propagation/lag dataset → empirical findings.

**Declared success metrics** (from `enigmatrix-docs/m1/README.md`):

| Metric | Target |
|---|---|
| Category classifier F1 (macro) | ≥ 0.92 |
| Sector assignment F1 (macro) | ≥ 0.88 |
| Labeled gazette documents | ≥ 800 |
| Propagation data points | ≥ 800 (200 regulations × 4 stages) |
| SME awareness survey responses | ≥ 100 unique SMEs |
| Ingestion latency | ≤ 6 h from publication |
| Alert delivery latency | ≤ 24 h from publication |

These targets are the yardstick for everything in §5–§7 below.

---

## 3. What is actually built (verified against the file tree)

### 3.1 Phase 1 — Foundation ✅ (shipped)
- Admin **regulation CRUD** — list / detail / edit / flow-canvas / authoring / new (`/admin/regulations/*`), expert verify + bulk-verify.
- **Audit log** on every admin mutation (`audit_service.record()`).
- **Awareness survey** — 12 questions, EN/SI/TA, plus admin responses view (`/admin/surveys/awareness/responses`).
- **Seed data** — 5 demo regulations + demo SMEs walked through the M1→M2→M3 wizard.

### 3.2 Phase 2 — Ingestion + extraction ✅ (shipped, then heavily upgraded)
- **Scrapy spiders** — `gazette_spider`, `weekly_gazette_spider`, `acts_spider`, `bills_spider` (+ shared `_base`). This is *more* than the single planned spider.
- **Celery pipeline** — `gazette_scraper → extract_gazette → preprocess_gazette`, chained; rows flow `ingested → extracted → preprocessed`.
- **`enigmatrix-ml/m1/` — a real, installable Python package** (its own submodule + tests + graph):
  - `extraction/` — `pdf_classifier`, `text_extractors`, `ocr`, `segmenter`, fastText `language_detection`, **`wijesekara` + `font_aware_wijesekara` + `wijesekara_maps`** (the hard legacy-Sinhala-font problem — built), `surya_engine`, a `page_engines/` set (PyMuPDF / pdfplumber / pypdfium2 / Tesseract + a page classifier), and an **extraction-profile registry** (`legacy_v1`, `page_routing_v1`, `wijesekara_routing_v1`, `surya_fallback_v1`).
  - `preprocessing/` — `cleaning`, `chunking`, `metadata_extractor`.
  - `evaluation/` — a **measurement engine**: `field_metrics`, `completeness`, `date_scope`, `strata`, `raw_text`, `xlsx_reader`, `aggregates`, and a `metrics/` registry (categorical / dates / numeric / **semantic** / strings / text_summary).
  - ~40 unit tests across extraction / preprocessing / evaluation.
- **Backend M1 surface** (far beyond admin CRUD): datasets + versioning (`m1_dataset*`, `m1_xlsx_parser`, upload), extraction runs (`m1_extractions`, `run_extraction`, `extraction_run_status`, `extraction_live_feed`, `extraction_cancel`, a **WebSocket** feed), measurement (`m1_measurements`, `run_measurement`, `measurement_aggregates`), profiles (`m1_profile_service`), completeness check, pipeline service, snapshot, **overlap detection**, sources catalogue, PDF resolver, sub-documents, gazette items. **~20 Alembic migrations** for M1.
- **Frontend admin** — `/admin/m1/pipeline/*` (extraction, recent, sources, steps, trace, pdf-records) and `/admin/datasets/m1/*` (versions, upload, extractions/runs, measurements + per-regulation comparison).
- **Knowledge portal** (`/knowledge`) live-syncing this Obsidian vault (chokidar + SSE).
- **Research ground-truth assets** in `data/golden/` — hand-transcribed gazette pages (`gold` + two independent transcriptions `t1`/`t2`), `kappa.json`, `TRANSCRIPTION_PROTOCOL.md`, `STATISTICAL_POWER.md`, `stratum_map.json`, a `structured_v1_sample.xlsx`; plus `data/eval/baseline_v0`.

### 3.3 The Phase-2 Upgrade Plan (slices 1–9) ✅ (shipped through Session 58, 2026-06-02)
Your own `2026-05-23_M1_Phase2_Upgrade_Plan` — the deliberate "wedge between Phase-2-as-shipped and Phase-3-ML-training" — is essentially complete:

| Slice | What it shipped | State |
|---|---|---|
| 1 | `evaluation/` package + field-metric registry + golden Excel + baseline JSON | ✅ |
| 2 | 10 hand-transcribed PDFs across 8 strata + kappa + CER tooling | ✅ |
| 3 | Dataset registry + versions + Excel upload UI | ✅ |
| 4 | Extraction-profile registry + `legacy_v1` adapter + `run_extraction` | ✅ |
| 5 | Measurement engine (`run_measurement` + scores) | ✅ |
| 6 | Comparison UI (`/admin/datasets/m1/measurements/*`) | ✅ |
| 7 | Three new profiles (`page_routing_v1`, `wijesekara_routing_v1`, `surya_fallback_v1`) | ✅ |
| 8 | Backfill + thesis-artifacts + Phase-3 handoff | ✅ |
| 9 | Dynamic date-range measurement + re-extraction overlap alert + auto v1→v2 versioning | ✅ (Session 58) |

---

## 4. Plan vs reality — the file / README gap check

You asked specifically whether "all the files are already there per the README." Two findings:

**(a) Many files the docs still mark `🔲 deferred` now actually exist** — the docs are *behind* the code:

| Documented target (m1/README "Backend Source Files") | Real status (2026-06-28) |
|---|---|
| `app/tasks/m1/gazette_scraper.py` | ✅ exists |
| `scraper/spiders/gazette_spider.py` | ✅ exists (+ 3 more spiders) |
| `ml/m1/extraction/pdf_classifier.py` | ✅ exists (as `enigmatrix-ml/m1/extraction/`) |
| `ml/m1/preprocessing/cleaning.py` | ✅ exists |
| `app/tasks/m1/classify_gazette.py` | ❌ **missing** |
| `ml/m1/model/architecture.py` | ❌ **missing** |
| `ml/m1/model/training.py` | ❌ **missing** |
| `ml/m1/model/inference.py` | ❌ **missing** |
| `research/notebooks/findings_*.ipynb` (×4) | ❌ **none exist** |

**(b) The numbered design docs are stale.** `16_M1_Development_Roadmap.md` and `m1/README.md` are dated **2026-05-14** and predate the entire Phase-2 upgrade — they describe Phases 1–2 and then jump to "Phase 3 = ML," with no mention of the datasets / profiles / measurement layer that now dominates the codebase. That whole layer lives only in `plans/2026-05-23_M1_Phase2_Upgrade_Plan/` + the work log. The knowledge graph (`graphify-out/`) was built from commit `94ae62d0` (2026-05-23) and is ~10 commits + many submodule bumps stale; `enigmatrix-ml` carries its **own** separate graph. **Net: the docs undersell what you've built and overstate what's missing on the extraction side — but they are correct that the model and findings layers are genuinely absent.**

---

## 5. The gaps — what is NOT done (and which RQ it blocks)

> Important distinction: the "measurement engine" you built measures **extraction quality** (field accuracy vs golden, completeness, CER/kappa). It does **not** measure the **RQ1 information lag**. Those are two different "measurements," and the second one — the actual research finding — is still ahead.

**Phase 3 — Annotation + Classification (the RQ1 headline).** No `enigmatrix-ml/m1/model/` at all → no XLM-R + LoRA classifier, no `training.py` / `evaluation.py` / `export_onnx.py` / `inference.py`, no `classify_gazette.py` Celery task, no ONNX/Fly serving. The 12-category + 10-sector taxonomy is fully specified in `05_M1_Model_Architecture.md` and you have the golden-set tooling, but the labeled set is at ~10 transcribed PDFs, not the **≥ 800 labels** the F1 target needs. **This blocks RQ1's "F1 ≥ 0.92" result and RQ2's cross-lingual claim.**

**Phase 4 — Schedulers, alerts, lag tracking.** No portal/RSS watchers populating `m1_propagation_events`, no `alert_dispatch` (SendGrid/Twilio), no nightly view refresh / drift. **This blocks the ≥ 800 propagation data points and the ≤ 24 h alert metric.**

**Phase 5 — Research findings + survey deployment.** No `findings_*.ipynb` (F1–F6 not computed), the SME survey is not deployed to **≥ 100 respondents**, no lag dataset, no retraining cadence. **This is the actual empirical answer to RQ1 — currently uncomputed.**

Also explicitly deferred (per your own `10_Upgrades_Over_Original.md` Category E): `pymupdf4llm_v1` profile, 100-PDF golden expansion for full CER statistical power, MarianMT trilingual summarisation, DiD treatment-vs-control effect measurement.

---

## 6. Next-level roadmap (prioritized + sequenced)

The foundation is done, so the next level is **the two graded outputs**: the classifier and the lag findings. Sequenced so each step unblocks the next.

### Priority 1 — Stand up the classifier (RQ1/RQ2 headline) 🔴 highest leverage
1. **Scale the labeled set.** Stand up Label Studio with the config in `09_M1_Annotation_Guidelines.md`; run `sample_for_labeling.py` (stratified-by-year-language + k-means) against your already-extracted gazettes; iterate batches with an active-learning baseline (TF-IDF + LR) to **≥ 800 labels, ≥ 50/category, κ ≥ 0.75**. *You already have the golden/strata/kappa tooling from slice 2 — extend it, don't rebuild it.*
2. **Create `enigmatrix-ml/m1/model/`** — `architecture.py` (XLM-R + LoRA dual head: 12-category + 10-sector), `training.py` (3-seed loop, AdamW, early-stop, FP16, **temporal split** sorted by `gazette_published_date`), `evaluation.py` (per-language / per-quarter / per-length / per-extraction-method slices), `export_onnx.py` + `quantize.py`. Specs are in `05_*`, `05_M1_3_LoRA_*`, `06_*`.
3. **Wire inference** — `app/tasks/m1/classify_gazette.py` + `model/inference.py` (ONNX CPU), chained after `preprocess_gazette`; populate `change_category` + `affected_sectors[]` + `confidence`. Deploy `M1_MODEL_VERSION=v1.0` (Fly.io spec in `07_*`).
- **DoD:** 3-seed mean macro-F1 ≥ 0.92; EN ≥ 0.93 / SI ≥ 0.88 / TA ≥ 0.86; no slice cliff > 8 pp; reproducibility hash recorded.

### Priority 2 — Produce the lag dataset + findings (the empirical RQ1 answer) 🟠
4. **Propagation watchers** — `portal_watcher.py` + `rss_watcher.py` over the 15-source registry, writing `m1_propagation_events` (with `match_method`/`match_confidence`). This is **Stage A/B** of your interim methodology.
5. **Deploy the SME survey** at scale (Stage C) — wire `/portal/m1/survey` to the 9-regulation selection SQL; partner outreach (NEDA, Chamber) → **≥ 100 respondents, 10/sector**.
6. **Findings notebooks** — the four `research/notebooks/findings_*.ipynb`: lag distribution per transition + Kruskal–Wallis (Stage D), channel-effectiveness ranking, classifier eval, alert effectiveness. Each finding gets median + bootstrap CI + test result. **This is the thesis-ready dataset.**

### Priority 3 — Close the loop 🟡
7. **Alert dispatch** (Stage F) — `alert_dispatch.py` (sector-matched, idempotent on `(regulation_id, sme_id, channel)`, ≤ 24 h).
8. **Monitoring** — nightly `v_m1_regulation_lag_summary` refresh + KL-divergence drift; retraining script + canary rollback.

### Priority 0 — Cheap, do-alongside: pay down documentation debt 🟢
9. Refresh `m1/README.md` + `16_M1_Development_Roadmap.md` to reflect the datasets/profiles/measurement layer and the corrected file map (§4); promote the Phase-2 Upgrade Plan from `plans/` into the numbered doc set; run `graphify update .` from the repo root (and inside `enigmatrix-ml/`) so the graph and the `/knowledge` portal stop under-reporting your work. *Low effort, high credibility payoff before viva.*

---

## 7. Suggested immediate first move

If you want one concrete starting point this week: **Priority 1, step 2 — scaffold `enigmatrix-ml/m1/model/`** (the missing folder the README still lists as the core deliverable), starting from the `GazetteClassifier` dual-head spec in `05_M1_Model_Architecture.md §3–4` and the LoRA ablation (`r ∈ {8,16,32}`) in `05_M1_3_LoRA_Hyperparameter_Justification.md`, trained first against whatever labels you can stratify-sample today. Everything upstream (extraction → preprocessing → chunking → dataset versioning) already feeds it.

---

## 8. Quick reference

- **Code root:** `C:/Reasearch/xyz` — submodules `enigmatrix-backend` / `enigmatrix-frontend` / `enigmatrix-ml` / `enigmatrix-docs` / `enigmatrix-infrastructure`.
- **M1 design set:** `enigmatrix-docs/m1/` (61 docs) · **roadmap:** `16_M1_Development_Roadmap.md` · **upgrade plan:** `enigmatrix-docs/plans/2026-05-23_M1_Phase2_Upgrade_Plan/`.
- **ML package:** `enigmatrix-ml/m1/{extraction,preprocessing,evaluation}` (model/ is the gap).
- **Ground truth:** `data/golden/raw_text/` + `data/golden/structured_v1_sample.xlsx`.
- **Read-first (project rule):** `graphify-out/GRAPH_REPORT.md` → `AGENTS.md` → `AI_WORK_LOG.md`.
- **Owner:** Mohamed M.R.I (215075J) — Module 1.

*Analysis generated 2026-06-28 from a full read of both folders. Status reflects the file tree + AI work log through Session 58 (2026-06-02) and git HEAD `037a709`.*
