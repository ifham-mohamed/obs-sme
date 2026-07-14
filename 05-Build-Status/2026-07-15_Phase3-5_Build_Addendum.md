# Build-Status Addendum — Phases 3–5 (as of 2026-07-15)

> Brings `Backend_ML_Technical_Documentation.md` and `Frontend_Pages_Feature_Map.md` (both "as of 2026-05-20") current. Covers everything shipped in Sessions 57–72 that those docs predate. Session-level detail: [[SESSIONS]] 57–72; feature rows F-200…F-243 in [[FEATURES]].

## New since 2026-05-20 — Backend

**Migrations:** chain extended `202605240001…202605310002` (datasets/measurements/overlap) then `202606300001–005` (classifier confidence · propagation events · alerts · lag materialized views · retraining runs). ⚠️ The last five may still need `alembic upgrade head` in production.

**New tables:** `m1_datasets` / `m1_dataset_versions` / `m1_dataset_rows` · `m1_extraction_profiles` / `m1_extraction_runs` · `m1_measurement_runs` / `m1_measurement_scores` · `m1_propagation_events` · `m1_alerts` · `m1_retraining_runs` · MVs `v_m1_regulation_lag_summary`, `v_m1_channel_effectiveness`.

**New routers:** `m1_datasets` (14 routes) · `m1_extractions` (8) · `m1_measurements` (11, incl. `GET /{run_id}/report.md` accuracy export) · `m1_alerts` (3).

**New services:** dataset service/upload/xlsx-parser/snapshot · profile service · overlap service (auto v1→v2 versioning) · measurement aggregates + report · classifier service (ONNX, min-conf 0.55) · propagation matching + service + secondary-sources registry · alert content/providers/service · drift (KL divergence).

**New Celery tasks + Beat:** run_extraction · run_measurement · validate_dataset_version (post-seal DQ suites) · classify_gazette (auto-chained after preprocess) · portal_watcher + rss_watcher (2 h) · alert_dispatch · refresh_lag_analytics (21:00 UTC) · retire_old_versions (20:30 UTC) · run_retraining (quarterly + drift-triggered).

**Data quality:** `data_quality/expectations/*.json` (4 suites) + checkpoint YAML. **Scripts:** `backfill_legacy_baseline.py`, `regenerate_thesis_tables.py` (`make thesis-artifacts`), `log_fonts_for_cid_spans.py`.

## New since 2026-05-20 — ML (`enigmatrix-ml`)

- `m1/evaluation/**` — measurement engine: per-field metrics (categorical/dates/numeric/strings/semantic/text-summary), aggregates, strata, raw-text, completeness, date-scope filter.
- `m1/extraction/` additions — page_engines (pymupdf/pdfplumber/pypdfium2/tesseract), profiles (legacy_v1, page_routing_v1, surya_fallback_v1, wijesekara_routing_v1), surya_engine, font-aware Wijesekara.
- `m1/data/samplers.py` — stratified + k-means + active-learning sampling (Phase 3a/3b).
- `m1/model/` — labels, config, temporal-split data, XLM-R+LoRA architecture, 3-seed trainer (gate ≥0.92), eval (per-slice + cliff ≤8pp), baselines, ONNX export (+INT8), GazetteInference, canary promotion.decide().
- `research/` — preregistration.md + findings_common.py + 4 F1–F6 notebooks. `scripts/retrain.py` (--dry-run verified).

## New since 2026-05-20 — Frontend

- `/admin/datasets` hub + `/admin/datasets/m1/**` (dataset CRUD, Excel upload, versions, extraction runs + progress, measurements dashboard/run/detail/drill-down/worst-N/calibration, sparkline + shortcuts).
- `/alerts` — public feed + SME sector-matched feed (middleware/nav wiring pending).
- `/knowledge/**` — 23-surface vault-backed portal + chokidar→SSE live sync + ⌘K palette (Session 57).
- Measurement list UX polish, recent-runs failure drill-down, CandidateRangePicker with snapshot + in-window counts.

## Current gates (unchanged since Session 72)

1. Phase 3c annotation → ≥800 gold (Label Studio env exists in `xyz/mydata/`).
2. GPU training run → eval → ONNX deploy (`M1_MODEL_ONNX_DIR`).
3. Prod migrations `202606300001–005` + uv extras + watcher URL confirmation.
4. Phase 5a survey fieldwork (≥100 SMEs) → run findings notebooks on real data.
5. Re-extract clean SI/TA text (`(cid:…)` issue) before training.

External bundle with full detail: `C:\Users\Administrator\Documents\Claude\Projects\SME\01–06_*.md`.
