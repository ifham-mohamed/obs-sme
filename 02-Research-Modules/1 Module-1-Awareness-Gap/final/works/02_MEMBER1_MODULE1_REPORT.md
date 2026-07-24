# Member 1 Report — Module 1: Regulatory Awareness Gap

**Member:** Mohamed M.R.I (215075J) — Module 1 owner
**Generated:** 2026-07-15 · reflects code at submodule commits of 2026-07-03 and vault Session 72 (F-242)
**Companion:** `01_MASTER_PROJECT_OVERVIEW.md` (whole-project context)

---

## 1. Scope and Responsibilities

Member 1 owns Module 1 end-to-end: the automated gazette pipeline (scrape → extract → preprocess → classify → alert) **and** the diffusion-measurement research programme (propagation tracking, lag analytics, findings F1–F6, retraining loop), plus the admin tooling that operates it (extraction portal, dataset registry, accuracy measurement UI). Research questions:

- **RQ1** — Can a trilingual classifier assign gazette changes to an 8-domain + 3-sector taxonomy at macro-F1 ≥ 0.92 (no language slice worse than 8pp below overall)?
- **RQ2** — Does extraction quality (esp. Sinhala/Tamil OCR + Wijesekara conversion) support reliable downstream classification?
- **RQ3/RQ4** — What is the measured regulatory information-diffusion lag across channels, and do targeted alerts reduce it (F6, difference-in-differences)?

## 2. What Has Been Completed (by phase)

### Phase 1 — Foundation 🟢
Admin regulations CRUD (`/admin/regulations`, soft-delete via `is_active`, expert verification gate, bulk verify, restore), seeds, sector mapping, audit-logging on every mutation.
*Key files:* `app/api/v1/m1_regulations.py`, `app/services/m1_regulation_service.py`, `app/models/regulation.py`.

### Phase 2 — Ingest + Extract + Preprocess + Measure 🟢 (Sessions 23–60; F-145…F-215)
The largest completed block. Why it exists: gazette PDFs are heterogeneous (born-digital EN, scanned SI/TA, legacy Wijesekara-encoded fonts), so extraction must route per document *and per page*, and its quality must be **measured, not assumed**.

1. **Scraping** — 4 Scrapy spiders (gazette, weekly gazette, acts, bills) with date-scoping, EN→SI→TA fallback, completeness verify + re-fetch. *Files:* `enigmatrix-backend/scraper/spiders/*.py`, `app/tasks/m1/{run_scraper,gazette_scraper}.py`, `app/api/v1/m1_completeness.py`.
2. **Extraction chain** (canonical in `enigmatrix-ml/m1/extraction/`) — `classify_pdf` → `text_pdf|hybrid|scanned`; engines pymupdf / pdfplumber / pypdfium2 / tesseract (+ Surya); profiles `legacy_v1`, `page_routing_v1`, `surya_fallback_v1`, `wijesekara_routing_v1`; font-aware Wijesekara→Unicode; CER calculator; segmenter. Backend `app/extraction/` is a thin re-export adapter (−90 LOC; keeps old imports/tests working). *Design decision:* extraction lives in the ML package so it is pip-installable and backend-independent; wired via a uv workspace.
3. **Preprocessing** — cleaning, fastText language ID, metadata extraction (gazette number, dates, penalties incl. multi-penalty enum), chunking, sub-document splitting. *Files:* `enigmatrix-ml/m1/preprocessing/*`, `app/tasks/m1/preprocess_gazette.py`.
4. **Admin extraction portal** — live WebSocket progress, date-range picker, run history, cancel/rollback, PDF Records, per-regulation trace. *Pages:* `/admin/m1/pipeline*`; *API:* `m1_gazette_extraction.py` (17 routes), `m1_extraction_ws.py`.
5. **Accuracy measurement system** *(the feature set that measures extraction-content accuracy)* — dataset registry with immutable sealed versions + Excel ground-truth upload; extraction-profile registry + run dispatcher with overlap detection and auto v1→v2 versioning; measurement engine with per-field metrics (categorical/dates/numeric/strings/semantic/text-summary), strata, completeness, date-scope filtering; measurement dashboard UI with drill-downs, worst-N, calibration; **downloadable accuracy report** `GET /m1/measurements/{run_id}/report.md`; data-quality expectation suites auto-run post-seal; thesis table/figure generator. *Files:* `app/api/v1/{m1_datasets,m1_extractions,m1_measurements}.py`, `app/services/m1_{dataset_service,dataset_upload,profile_service,overlap_service,measurement_aggregates,measurement_report,snapshot_service,xlsx_parser}.py`, `enigmatrix-ml/m1/evaluation/**`, pages `/admin/datasets/m1/**`.
6. **Data population** — 800 raw PDFs bulk-extracted (11 batches); legacy-baseline backfill script materialising pre-registry extractions into the dataset registry (`scripts/backfill_legacy_baseline.py`).

### Phase 3 — Annotation + Classification (3a/3b 🟢 · 3d–3f code 🟢 · 3c human gate 🔲)
- **3a/3b:** Label Studio config (8 domains × 3 sectors × relevance × confidence), 20-doc trilingual calibration set with expert rationales, sampling library (stratified × k-means × active learning) → `batch_01.csv` (200 docs). *Files:* `research/data/label_studio_config.xml`, `research/data/calibration_set_v1.csv`, `enigmatrix-ml/m1/data/samplers.py`, `scripts/sample_for_labeling.py`.
- **3d:** `m1/model/` — XLM-R + LoRA dual-head classifier, temporal-split data loader (leakage-tested), 3-seed trainer with F1 gate ≥ 0.92, `model_registry.json`. *Why XLM-R+LoRA:* one multilingual encoder covers EN/SI/TA; LoRA keeps training feasible on a single GPU; dual head handles single-label category + multi-label sectors jointly (CE + BCE loss).
- **3e:** per-slice evaluation (language / quarter / length, slice-cliff ≤ 8pp) + TF-IDF baselines — the RQ1 comparison is itself a finding.
- **3f:** ONNX export (LoRA-merged, optional INT8) + `GazetteInference` runtime + `m1_classifier_service` (min-confidence 0.55 review threshold) + `classify_gazette` Celery task auto-chained after preprocessing. Migration `202606300001`.
- **In progress:** a local Label Studio instance exists (`xyz/mydata/` — sqlite + media), i.e. the annotation environment is stood up; gold labels not yet collected.

### Phase 4 — Watchers + Alerts + Analytics 🟢 code-complete (Sessions 66–68)
- **4a Propagation:** `m1_propagation_events` (unique regulation × source, `first_seen_at`) + 2-step matcher (exact gazette-no conf 1.0 → difflib fuzzy ≥ 0.78) + portal/RSS watchers on 2-h Beat. *Why:* every downstream appearance timestamp is a data point in the diffusion-lag dataset — the platform's research instrument.
- **4b Alerts:** `m1_alerts` + content builder + SendGrid/Twilio providers (dev-safe skip) + idempotent sector-matched dispatch + public/SME API + `/alerts` page. *Why idempotent + unique-keyed:* re-dispatching must never double-send.
- **4c Analytics:** lag materialized views + nightly refresh + KL-divergence confidence-drift monitor (> 0.15 triggers retraining).

### Phase 5 — Findings + Retraining 🟢 code-complete (Sessions 69–70)
- **5b:** preregistration (F1–F6, α=0.05) + `findings_common.py` + 4 notebooks (lag, secondary diffusion, alert DiD, classifier eval). Demo smoke: F1 portal ≈6.8 d, F2 news ≈21.8 d, F6 DiD −19.9 d.
- **5c:** `m1_retraining_runs` + canary `promotion.decide()` (promote/hold/rollback, unit-tested) + `retrain.py --dry-run` verified + quarterly/drift-triggered `run_retraining`.

### Hygiene / documentation (Sessions 71–72)
F1-gate reconciled to 0.92 everywhere; MASTER_CONTEXT + dossier/Excel regenerated; measurement-UI audit (10 prioritized upgrades) + accuracy-report export shipped.

## 3. Pending Tasks (prioritized)

### HIGH — critical path
| # | Task | Notes |
|---|---|---|
| 1 | **Phase 3c annotation** — recruit 2–3 annotators, run calibration (κ ≥ 0.80 on 20-doc set), label batch_01 (200), iterate AL batches to ≥800 gold (κ ≥ 0.75) | Blocks everything ML. Label Studio env exists in `mydata/`; import `calibration_set_v1.csv` first |
| 2 | Apply migrations `202606300001–005` in production + `uv sync` extras (`serving`, `training`, `research`, feedparser) | Until then Phases 3f/4/5 code is dormant in prod |
| 3 | **Train + evaluate + deploy the classifier** (3d→3f): `m1.model.data` → `train_xlmr` (GPU) → `eval` + `baselines` → `export_onnx --int8` → set `M1_MODEL_ONNX_DIR` | Gate: macro-F1 ≥ 0.92, slice cliff ≤ 8pp |
| 4 | **Re-extract clean SI/TA text** — resolve `(cid:…)` glyph spans before training | Known RQ2 risk (Session 62); use `scripts/log_fonts_for_cid_spans.py` + `wijesekara_routing_v1` profile |
| 5 | Confirm portal/RSS source URLs + first live watcher runs write real `m1_propagation_events` | URLs in `m1_secondary_sources.py` marked "to confirm" |

### MEDIUM
| # | Task | Notes |
|---|---|---|
| 6 | Survey fieldwork (5a) — ≥100 SME respondents; then run F1–F6 notebooks on real data; preregister before unblinding | Instrument shipped; needs field ops |
| 7 | Wire `dispatch_regulation_alerts` to a verify/publish action or daily Beat scan; set SendGrid/Twilio keys; add SME phone field for SMS | Currently manual-dispatch only |
| 8 | Frontend: `/alerts` middleware public-route + nav link; accuracy-report download button + CSV export; remaining Session-72 audit items (empty states, a11y, confidence surfacing) | Snippets ready in the audit doc |
| 9 | SI/TA translations for newest i18n keys (`[TODO]` placeholders) | Sessions 58–59, 67 strings |
| 10 | Integration tests: auto-v2 routing path, date-scoped measurement run, alert dispatch end-to-end | Unit coverage exists; integration gaps flagged |

### LOW
| # | Task | Notes |
|---|---|---|
| 11 | `graphify update .` — knowledge graph 6+ weeks stale (built at `94ae62d0`) | AST-only, no API cost |
| 12 | git tag `m1-phase2-complete`; real Docker digests in `infra/docker-image-pin.txt`; rotate the leaked Railway PAT | Session 55/60 follow-ups |
| 13 | Populate thesis `table_4_2` (needs gold set) + Wilcoxon p-values in `table_4_3` | After annotation |
| 14 | Full D3 force-directed `/knowledge/graph` view + ⌘K search index | Deferred UX polish |

## 4. Risks & Dependencies

| Risk | Impact | Mitigation |
|---|---|---|
| Annotation slips (recruiting, κ below gate) | Blocks 3d–3f, 5c, RQ1 | Calibration set + decision hints already built; AL sampling minimizes label count |
| SI/TA extraction quality (`cid` glyphs, Wijesekara edge cases) | RQ2 failure; slice cliff > 8pp | Font-aware conversion + Surya fallback + re-extraction pass (#4); CER measurement in place |
| Macro-F1 < 0.92 with 800 labels | Miss RQ1 gate | AL batches to grow gold set; baselines quantify headroom; per-slice eval finds where to add labels |
| Survey response < 100 | F3/F5/F6 underpowered | Bootstrap CIs preregistered; window can extend |
| Single-container Railway (worker + beat + web) | Beat tasks contend with API under load | Split worker dyno when live pipelines start |
| Watcher source URLs unstable | Propagation dataset gaps | Registry is data-driven; add sources incrementally |

**Dependency chain:** 3c annotation → 3d train → 3e eval → 3f deploy → (4 already live-capable) → 5b real findings; 5c retraining needs 3d's registry; F6 needs alerts live + survey.

## 5. Estimated Remaining Work

| Workstream | Estimate |
|---|---|
| Annotation ops (3c, 800 labels) | 3–4 weeks calendar (annotator throughput bound) |
| Training + eval + deploy (3d–3f) | 3–5 days once gold lands (GPU available) |
| Prod migrations + env sync + watcher URL confirmation | 1 day |
| Alert wiring + FE polish (items 7–8) | 2–3 days |
| Survey fieldwork (5a) | 4–6 weeks calendar, parallel to above |
| Findings notebooks on real data + thesis tables | 3–4 days after data lands |

## 6. How to Verify the Current Build (quick)

Full steps in `05_MANUAL_TESTING_GUIDE.md`. Smoke: `make up && make migrate && make seed` → login `admin@enigmatrix.lk` / `admin12345` → `/admin/m1/pipeline` (funnel) → run a date-scoped extraction → `/admin/datasets/m1/measurements/run` → open the run → download `report.md`. Tests: `uv run pytest` in `enigmatrix-backend` and `enigmatrix-ml`; `pnpm exec playwright test` in `enigmatrix-frontend`.
