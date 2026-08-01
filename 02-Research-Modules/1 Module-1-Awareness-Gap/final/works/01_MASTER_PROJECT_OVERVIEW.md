# Enigmatrix — Master Project Overview

**Generated:** 2026-07-15 · from codebase `C:\Reasearch\xyz` (root commit `3b6e584`, submodule commits of 2026-07-03) + Obsidian vault `E:\Obsidian\sme` (Session 72, F-242)
**Purpose:** single self-contained context document. A new developer, researcher, or external AI assistant (Perplexity, Claude, etc.) reading only this file understands the whole project: the research idea, what has been built across frontend / backend / ML, how it works, and what remains.

---

## 1. The Research Idea

**Enigmatrix — SME Regulatory Intelligence Platform.** Final-year research project, Faculty of Information Technology, University of Moratuwa, 2026.

**Problem.** Sri Lankan SMEs systematically miss regulatory changes. The Official Gazette publishes ~500 binding amendments per year in three languages (English / Sinhala / Tamil) as unstructured PDFs — no push notification, no machine-readable metadata, and a measured 33–70 day information-diffusion lag. 34% of IRD SME penalty assessments (2023) result from this addressable information asymmetry, not wilful non-compliance.

**Solution.** A four-module trilingual web platform:

| Module | Name | Research question | Status |
|---|---|---|---|
| **M1** | Regulatory Awareness Gap (gazette ingest → extract → classify → alert → measure diffusion) | RQ1–RQ4: can a pipeline detect/classify gazette changes within 24 h, and what is the measured awareness lag? | **Phases 1–5 code-complete** (human/data gates remain) |
| M2 | Knowledge Hub (SME regulatory-knowledge scoring) | Knowledge-score instrument | Shipped (surveys + auto-scoring + admin UI) |
| M3 | Compliance Risk | Risk snapshot from behavioural + compliance-history signals | Survey + snapshot level shipped; ML risk model not started |
| M4 | Misinformation Verifier | Claim verification against regulation corpus | Architecture researched; `/verify` router is a 501 stub |

**M1's dual contribution:** (a) an operational alerting pipeline; (b) the first measured Sri Lankan regulatory information-diffusion dataset (≥200 regulations × ≥4 channel stages × ≥100 SME survey respondents), analysed as findings F1–F6 (preregistered, `enigmatrix-ml/research/preregistration.md`).

**Module 1 owner (Member 1):** Mohamed M.R.I (215075J). See `02_MEMBER1_MODULE1_REPORT.md`.

---

## 2. Repository Layout

`C:\Reasearch\xyz\` is a monorepo with git submodules:

```
xyz/
├── enigmatrix-backend/        FastAPI + SQLAlchemy 2.0 async + Alembic + Celery + Scrapy
├── enigmatrix-frontend/       Next.js 14 App Router + shadcn-pattern UI + next-intl (EN/SI/TA)
├── enigmatrix-ml/             Python package `m1` — extraction, evaluation, model, research notebooks
├── enigmatrix-docs/           MkDocs docs: m1/ (61+ docs), plans/, tracker/, backend/, frontend/
├── enigmatrix-infrastructure/ infra configs
├── graphify-out/              knowledge graph (8,778 nodes; stale — built from commit 94ae62d0, 2026-05-23)
├── research/data/             Label Studio config, calibration set, labeling batches
├── scripts/                   cross-repo scripts (sample_for_labeling.py, regenerate_thesis_tables.py)
├── mydata/                    LOCAL Label Studio working data (sqlite + media) — untracked
├── AGENTS.md / CLAUDE.md / AI_WORK_LOG.md / AI_SYNC.md — AI-assistant context files
└── docker-compose.dev.yml / Makefile — dev infra (Postgres + ChromaDB + Redis)
```

**Companion Obsidian vault** `E:\Obsidian\sme` — the research knowledge base. Canonical trackers live in `08-Findings-Log/`: `SESSIONS.md` (diary, Session 72), `FEATURES.md` (F-01…F-242), `CHANGES.md`, `RESEARCH_BUILD_TRACKER.md`, `plans/`. ⚠️ `C:\sme` is a divergent, out-of-date copy — never treat it as canonical.

**Deployment.** Backend on Railway (single container: uvicorn + Celery worker + Beat), frontend on Vercel, Postgres on Aiven, Redis as Railway plugin. Known follow-up: PAT leak in a Railway build log (Session 55); docker image digests in `infra/docker-image-pin.txt` still placeholders.

---

## 3. Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic v2, Celery + Beat (Redis), slowapi rate-limits |
| Scraping | Scrapy — spiders: `gazette_spider`, `weekly_gazette_spider`, `acts_spider`, `bills_spider` (gazette.lk + documents.gov.lk) |
| Extraction | PyMuPDF, pdfplumber, pypdfium2, Tesseract 5 (`eng+sin+tam`), Surya OCR fallback; font-aware Wijesekara→Unicode conversion |
| Classification | XLM-RoBERTa + LoRA dual head (8-domain single-label + 3-sector multi-label), ONNX Runtime CPU inference (INT8 option) |
| Frontend | Next.js 14 App Router, Tailwind + shadcn-pattern HSL tokens (trust-blue/amber, light+dark), next-intl EN/SI/TA, TanStack Query, Playwright E2E |
| Storage | Postgres (Aiven in prod), ChromaDB (RAG, deferred), Redis (Celery broker) |
| Data quality | Great-Expectations-style JSON suites in `enigmatrix-backend/data_quality/` |
| Annotation | Label Studio (config `research/data/label_studio_config.xml`, 20-doc calibration set) |

---

## 4. Architecture & Data Flow (M1 pipeline, end-to-end)

```
gazette.lk / documents.gov.lk
   │  Scrapy spiders (run_scraper / gazette_scraper Celery tasks; date-scoped; EN→SI→TA fallback)
   ▼
m1_regulations (status: ingested)  + raw PDF in storage/
   │  extract_gazette task — classify_pdf → text_pdf | hybrid | scanned
   │    text: PyMuPDF (TEXTFLAGS_TEXT) → pdfplumber (layout+tables)
   │    scanned/low-yield pages: Tesseract --oem 1 --psm 6 -l eng+sin+tam @300dpi; Surya fallback profile
   ▼
status: extracted
   │  preprocess_gazette — cleaning → fastText language ID → Wijesekara→Unicode →
   │  metadata extraction (gazette no, dates, penalties incl. multi-penalty) → chunking → sub-documents
   ▼
status: preprocessed
   │  classify_gazette (auto-chained) — ONNX XLM-R+LoRA → change_category + classifier_confidence
   │  (< 0.55 confidence ⇒ review; expert_verified rows never overwritten)
   ▼
status: classified
   │  dispatch_regulation_alerts — sector-matched in-app + email (SendGrid) + SMS (Twilio); public broadcast
   ▼
m1_alerts → frontend /alerts (public feed + SME sector feed)

Parallel measurement loop (diffusion research):
   portal_watcher + rss_watcher (Beat every 2 h) → 2-step matcher (exact gazette-no → fuzzy ≥0.78)
   → m1_propagation_events → nightly refresh_lag_analytics (21:00 UTC) → materialized views
   v_m1_regulation_lag_summary + v_m1_channel_effectiveness → findings notebooks F1–F6

Quality loop:
   extraction accuracy measurement (dataset registry + versions + measurement engine, §5.3)
   confidence drift (KL > 0.15) + quarterly Beat → run_retraining → canary promotion.decide()
   (promote if macro-F1 ≥ 0.92 and no regression; else rollback)
```

Celery Beat schedule (`app/celery_config.py`): scraper every 6 h · retire_old_versions 20:30 UTC · portal_watcher + rss_watcher every 2 h (offset) · refresh_lag_analytics 21:00 UTC · retraining quarterly (1 Jan/Apr/Jul/Oct 03:00).

---

## 5. What Has Been Built (by area)

### 5.1 Platform foundation (F-01…F-92, all 🟢)
Monorepo + docker-compose dev infra; FastAPI app with JWT auth (bcrypt + HS256, access/refresh), RBAC (`sme`/`admin`/`annotator`), slowapi rate limits, audit-log writes on every auth event and admin mutation (`audit_service.record()` — never bypassed); Next.js app shell with theme tokens, trilingual fonts and next-intl; unified survey wizard (`/surveys`, regulation-scoped flows, auto-scoring, admin question bank + translations + survey limits); admin user management; activity log UI.

### 5.2 M1 Phase 1–2 — Ingest, Extract, Preprocess (F-145…F-220, 🟢)
- **Scrapy spiders** with scope-exhaustion close, EN→SI→TA fallback, completeness verify + re-fetch endpoints.
- **Extraction chain** canonical in `enigmatrix-ml/m1/extraction/` (backend `app/extraction` is a thin adapter): PDF classifier (calibratable thresholds), per-page engines (pymupdf / pdfplumber / pypdfium2 / tesseract), profiles (`legacy_v1`, `page_routing_v1`, `surya_fallback_v1`, `wijesekara_routing_v1`), CER calculator, segmenter.
- **Preprocessing** (`m1/preprocessing/`): cleaning, metadata extractor, chunking; fastText LID; font-aware Wijesekara conversion.
- **Admin extraction portal**: live WebSocket progress (`/ws/extraction/{task_id}`), date-range picker, run history, cancel/rollback, PDF Records page, pipeline trace per regulation.
- **800 raw PDFs** bulk-extracted across 11 batches (Session 56).

### 5.3 Extraction Accuracy Measurement (F-200…F-215, F-242 — the "measure the extraction accuracy" feature set)
This answers *"how good is our extraction?"* quantitatively — a core thesis artefact.
- **Dataset registry** (`m1_datasets` / `m1_dataset_versions` / `m1_dataset_rows`): named datasets, immutable sealed versions (SHA-256 content hashes), Excel ground-truth upload (`m1_xlsx_parser`), retire/restore, retention policy (nightly, keeps current + previous + `keep: true`).
- **Extraction profile registry + run dispatcher**: run any extractor profile against a scope; auto v1→v2 versioning when a new run's date range overlaps a prior version; overlap warnings on both trigger endpoints.
- **Measurement engine** (`m1/evaluation/`): per-field metrics (categorical, dates, numeric, strings, semantic, text-summary), aggregates, strata, raw-text scoring, completeness, date-scope filter so date-scoped runs aren't penalised against full ground truth.
- **Measurement UI** (`/admin/datasets/m1/measurements*`): run form (with optional date-range/source scoping), dashboard, per-run detail, per-regulation drill-down, worst-N, calibration view, sortable columns, sparkline, keyboard shortcuts.
- **Accuracy report export**: `GET /api/v1/m1/measurements/{run_id}/report.md` — downloadable Markdown (overall + per-field mean/median + status breakdown + worst-N), built by pure `m1_measurement_report.py`.
- **Data-quality suites** (`data_quality/expectations/*.json`) auto-validated post-seal via `validate_dataset_version` task; violations recorded on the version row.
- **Thesis artefact generator**: `scripts/regenerate_thesis_tables.py` → `data/thesis/table_4_{1,2,3}.csv`, `figure_4_{1,2}.svg`, `RUN_PROVENANCE.md` (`make thesis-artifacts`).

### 5.4 M1 Phase 3 — Annotation + Classification (Sessions 61–65 + 2026-07-30 update, F-216…F-228)
- **3a/3b (complete):** Label Studio project XML (8-domain + 3-sector + SME-relevance + confidence + notes), 20-doc trilingual calibration set with expert labels, stratified + k-means samplers, minority-domain targeting, and hybrid active learning in `scripts/sample_for_labeling.py`.
- **3c (gold gate reached):** Calibration was completed; Batches 02-05 were dual-annotated and reduced into an 800-row `gold_standard.csv`. Current resolved IAA: category kappa 0.871534, mean sector kappa 0.863776, SME relevance kappa 0.723518, with 40 manual-review rows recorded in `manual_resolutions.csv` and zero lead-annotator fallback rows.
- **Batch 05 state:** `batch_05.csv` and `batch_05_annotations_full.json` were merged through `resolve_iaa.py`; its 3 disagreement rows were manually resolved as non-SME-facing public/administrative notices.
- **Rare-domain warning:** Current gold set is dominated by `SECTOR_SPECIFIC` (671/800); `EPF_ETF_CHANGE` is still 0 and product/business/penalty/import remain under the preferred 50/domain target. More source data should be ingested or hand-targeted if the thesis needs strong rare-domain performance claims.
- **3d (training-prep complete, full training pending):** `gold_standard_v1_800.csv` is frozen; `m1.model.data --by key` produced train/validation/test parquet splits of 560/120/120 rows; TF-IDF baselines are complete (`LogReg=0.4980`, `LinearSVC=0.6167` macro-F1); CPU LoRA smoke wrote `storage/models/m1/xlmr_lora_smoke/model_registry.json` with `gate_pass=false`. This smoke proves the training loop, not model quality. Full LoRA still needs CUDA/GPU.
- **3e (code + baseline evidence):** `m1/model/eval.py` exists for per-slice macro-F1 by language/quarter/length, slice-cliff ≤ 8pp check, and error analysis CSV. Final slice evaluation is pending until a promotable GPU-trained model exists.
- **3f (code):** `export_onnx.py` (merges LoRA, optional INT8) + `GazetteInference` ONNX Runtime engine + backend `m1_classifier_service` + `classify_gazette` task auto-chained after preprocessing; migration `202606300001` adds `change_category` confidence columns.
- **Model gate now moves forward:** The 800-row annotation gate, frozen v1 dataset, deterministic key split, TF-IDF baselines, and CPU smoke are complete. Next: decide rare-domain top-up vs. limitation wording, then run full GPU LoRA, evaluate/export, and activate only if gates pass.

### 5.5 M1 Phase 4 — Watchers, Alerts, Analytics (Sessions 66–68, F-229…F-236, code-complete)
- **4a:** `m1_propagation_events` table; secondary-source registry (IRD/EPF/ETF/eROC portals + 5 news RSS); 2-step matcher (exact gazette-number conf 1.0 → difflib fuzzy ≥ 0.78, unit-tested); `portal_watcher` + `rss_watcher` Beat tasks.
- **4b:** `m1_alerts` table (unique regulation × recipient × channel; `sme_id=NULL` = public broadcast); pure alert-content builder; SendGrid/Twilio providers (graceful `skipped` without keys); idempotent alert service; batched dispatch task; API (`/m1/alerts/public`, `/m1/alerts`, mark-read); frontend `/alerts` page.
- **4c:** materialized views `v_m1_regulation_lag_summary` + `v_m1_channel_effectiveness`; KL-divergence confidence-drift helper (alert at KL > 0.15 → retraining trigger); nightly `refresh_lag_analytics`.

### 5.6 M1 Phase 5 — Findings + Retraining (Sessions 69–70, F-237…F-240, code-complete)
- **5b:** `research/preregistration.md` (F1–F6 hypotheses, α=0.05, bootstrap CIs); `findings_common.py` (tested loaders + bootstrap CI; DB-or-synthetic-demo); 4 notebooks — lag analysis (F1/F2/F3/F5), secondary diffusion (F4), alert effectiveness (F6, DiD), classifier evaluation (RQ1/RQ2).
- **5c:** `m1_retraining_runs` table; pure canary `promotion.decide()` (rollback below 0.92 gate or on regression); `retrain.py` CLI (`--dry-run` verified); `run_retraining` task on quarterly Beat + drift trigger.
- **Human gate 🔲:** 5a survey fieldwork (≥100 SMEs) and real propagation data to power the notebooks.

### 5.7 Knowledge Portal (frontend `/knowledge/*`, Session 57)
Live Obsidian-vault-backed portal: chokidar file-watcher → SSE push (~1 s), 23 vault surfaces, grouped sidebar, ⌘K palette, sessions/features/changes/build-tracker/plans/modules/graph pages, `obsidian://` deep links. Reads the vault configured at the sync path (historically `C:\sme` — see cleanup report §5).

### 5.8 Modules 2–4
M2 shipped (question bank per sector, knowledge scoring, verify workflow, admin scores UI). M3 shipped at survey + risk-snapshot level (`/m3/compliance-history`, `/behavioural`, `/sme/{id}/risk-signals`); ML risk model not started. M4: `/verify/claim` and `/qa/ask` are 501 stubs; architecture research only.

---

## 6. Database (principal tables)

`users`, `sme_profiles`, `audit_log`, `survey_*` (questions/sessions/limits/responses), `sectors`, `regulatory_domains` — platform.
M1: `m1_regulations` (+ status machine + extraction + classifier columns), `m1_regulation_sectors`, `m1_regulation_penalties`, `m1_sub_documents`, `m1_gazette_items`, `m1_extraction_profiles`, `m1_extraction_runs`, `m1_datasets` / `m1_dataset_versions` / `m1_dataset_rows`, `m1_measurement_runs` / `m1_measurement_scores`, `m1_propagation_events`, `m1_alerts`, `m1_retraining_runs`, materialized views `v_m1_regulation_lag_summary`, `v_m1_channel_effectiveness`.
M2/M3: `m2_questions`, `m2_knowledge_scores`, `m3_compliance_history`, `m3_behavioural_signals`.
Migrations: linear Alembic chain `202605080001` … `202606300005` (the last five — classifier confidence, propagation, alerts, lag views, retraining — **may still need `alembic upgrade head` in production**).

---

## 7. Current Status & The Critical Path

**Everything in the M1 roadmap (Phases 1–5) is code-complete.** The remaining gates are human/data, not code:

1. **Freeze the accepted gold set** (Phase 3c): archived locally as `gold_standard_v1_800.csv`, `iaa_report_v1_800.json`, and `iaa_report_summary_v1_800.csv`; keep `disagreements.csv` and `manual_resolutions.csv` as adjudication evidence.
2. **Fix data coverage if needed:** if the project needs strong rare-domain claims, ingest or hand-target more EPF/ETF, product-standard, business-registration, penalty/enforcement, tax, and import/export notices before final training.
3. **Train** (3d): use the existing deterministic key split and baseline results as prep evidence, or rebuild a better temporal/stratified split if needed → run `python -m m1.model.train_xlmr` on GPU → eval (3e) → `export_onnx --int8` → set `M1_MODEL_ONNX_DIR` (3f).
4. **Apply migrations** `202606300001–005` + `uv sync` extras (`serving`, `training`, `research`, feedparser) in the deployed env; confirm portal/RSS source URLs.
5. **Survey fieldwork** (5a): ≥100 SME respondents; then run the F1–F6 notebooks on real data.
6. **Re-extract clean SI/TA text** — the `(cid:…)` glyph issue is a known RQ2 risk flagged in Session 62.

Secondary follow-ups: FE accuracy-report download button + CSV export (Session-72 audit list), `/alerts` middleware + nav wiring, SME phone field for SMS, production regulation summarization plus NLLB Sinhala/Tamil title/summary backfill, SI/TA i18n for newest strings, git tag `m1-phase2-complete`, real Docker digests, `graphify update .` (graph is ~6 weeks stale).

---

## 8. Where to Read More

| Topic | File |
|---|---|
| Member 1 full report | `02_MEMBER1_MODULE1_REPORT.md` |
| Feature checklist | `03_FEATURE_CHECKLIST.md` |
| API + pages reference | `04_API_AND_PAGES_REFERENCE.md` |
| Manual testing guide | `05_MANUAL_TESTING_GUIDE.md` |
| Cleanup / removable files | `06_CLEANUP_REPORT.md` |
| Session-by-session history | vault `08-Findings-Log/SESSIONS.md` |
| Full feature table (F-01…F-242) | vault `08-Findings-Log/FEATURES.md` |
| M1 design docs (61+) | `enigmatrix-docs/m1/` |
| Phase-3 dataset card | `enigmatrix-docs/phase3_dataset_card.md` |
| Preregistration | `enigmatrix-ml/research/preregistration.md` |
