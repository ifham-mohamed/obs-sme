---
tags: [m1, phase-2, plan, upgrade, datasets, profiles, measurement]
date: 2026-05-23
author: Mohamed M.R.I (215075J) — Module 1 owner
source-of-truth: this folder
status: ready-to-execute — all 8 decisions resolved 2026-05-23 (see [12_Open_Questions](12_Open_Questions.md))
---

# M1 Phase 2 — Upgrade Plan (2026-05-23)

> Successor plan to the six uploaded `00–05` documents (`00_Phase2_Master_Plan` through `05_Build_Sequence_and_Risks`). It absorbs everything in those documents, **aligns them to the live xyz codebase**, and **adds upgrades** that the original drafts left out (audit-log integration, vault sync, i18n, SSE progress, Aiven connection-pool math, retention policy, security hardening on Excel upload, idempotency, and a more honest treatment of the legacy profile's missing-confidence problem).
>
> Read [01_Alignment_Audit](01_Alignment_Audit.md) first if you have read the uploaded plan and want to know exactly which lines need to change before slice 4 ships.
>
> Read this `00_INDEX` if you want the headline picture.

## The four ideas (unchanged from the original master plan)

1. **Datasets become first-class.** A new `m1_datasets` table separates "where data came from" (manual Excel, extraction run, expert review) from `m1_regulations` (which becomes a backward-compatibility view).
2. **Datasets are versioned.** A `m1_dataset_versions` table holds immutable, sealed snapshots; each upload or extraction run produces a new version.
3. **Extractors are pluggable profiles.** A `m1_extraction_profiles` registry holds named, versioned recipes. The Phase 1 chain becomes `legacy_v1`. Three new profiles (`page_routing_v1`, `wijesekara_routing_v1`, `surya_fallback_v1`) sit beside it.
4. **Measurement is a separate engine.** A Celery task `run_measurement(baseline_version_id, candidate_version_id)` writes `m1_measurement_runs` + `m1_measurement_scores` rows from a per-field metric registry.

## The eight slices (the order to ship in)

| # | File | What ships | Independently shippable? |
|---|---|---|---|
| 1 | [02_Slice1_Measurement_Scaffolding](02_Slice1_Measurement_Scaffolding.md) | `enigmatrix-ml/m1/evaluation/` package + field-metric registry + golden Excel locked + baseline JSON | ✅ |
| 2 | [03_Slice2_RawText_Golden_Set](03_Slice2_RawText_Golden_Set.md) | 10 hand-transcribed PDFs across 8 strata + kappa report + CER tooling | ✅ (parallel to slice 1) |
| 3 | [04_Slice3_Dataset_Registry_and_Upload](04_Slice3_Dataset_Registry_and_Upload.md) | `m1_datasets` + `m1_dataset_versions` + `m1_dataset_rows` + `/admin/m1/datasets` + Excel upload UI | ✅ |
| 4 | [05_Slice4_Extraction_Profile_Registry](05_Slice4_Extraction_Profile_Registry.md) | `m1_extraction_profiles` + `ExtractorProfile` protocol + `LegacyV1Profile` adapter (API-corrected) + `run_extraction_with_profile` Celery task + `/admin/m1/extractions/run` | ✅ |
| 5 | [06_Slice5_Measurement_Engine](06_Slice5_Measurement_Engine.md) | `m1_measurement_runs` + `m1_measurement_scores` + `run_measurement` Celery task + endpoint family | ✅ |
| 6 | [07_Slice6_Comparison_UI](07_Slice6_Comparison_UI.md) | `/admin/m1/measurements/*` — list, dashboard, per-regulation comparison view | ✅ (after slice 5) |
| 7 | [08_Slice7_New_Extraction_Profiles](08_Slice7_New_Extraction_Profiles.md) | `page_routing_v1`, `wijesekara_routing_v1`, `surya_fallback_v1` | ✅ (each profile is independently shippable) |
| 8 | [09_Slice8_Backfill_Polish_Thesis](09_Slice8_Backfill_Polish_Thesis.md) | `legacy_baseline_v1` backfill + Great Expectations + `make thesis-artifacts` + Phase 3 handoff | — |

## What this upgrade adds over the uploaded plan

See [10_Upgrades_Over_Original](10_Upgrades_Over_Original.md) for the full delta. Highlights:

- **Adapter API corrections** — the uploaded `LegacyV1Profile.extract()` would crash because it calls `extract_with_pymupdf` / `extract_with_pdfplumber` / `extract_with_tesseract` / `language_detection.detect_language` / `wijesekara.convert` — none of which exist. Actual symbols are `extract_pymupdf` / `extract_pdfplumber` / `extract_tesseract` / `detect_document_language` (returns a `LanguageDetection` dataclass with `.language` + `.confidence`) / `convert_wijesekara` (or `wijesekara_to_unicode`). The corrected adapter ships in slice 4.
- **`classify_pdf` return type** — Session 28 made it a `Literal['text_pdf','hybrid','scanned']`, not a dict. The uploaded plan reads `classification["type"]` and `classification.get("page_count", 0)` — those crash. The corrected adapter calls helpers separately for page count and routing.
- **Migration naming convention** — uploaded plan uses `010_m1_datasets_versioning.py`; codebase uses `YYYYMMDDNNNN_<name>.py`. New migrations rebased onto `202605300001_merge_gazette_items_and_extraction_runs` (the current tip).
- **Storage path** — code uses partitioned `storage/m1/raw/<source_id>/YYYY/MM/<slug>.pdf` (Session 38+). Plan must read this layout, not the flat one.
- **`audit_log` integration** — `AGENTS.md` rule: every admin mutation writes to `audit_log` via `audit_service.record()`. The uploaded plan is silent on this. Every Phase 2 admin action (dataset upload, version seal, profile activation, measurement-run trigger, ground-truth promotion) now records an audit row.
- **i18n** — every new user-facing string gets EN/SI/TA translations via `next-intl`, per the existing project rule.
- **SSE progress, not polling** — Session 57 added chokidar + SSE for vault sync; the existing extraction-runs page already polls every 5 s via TanStack Query. Slice 6 reuses the polling pattern; new long-running tasks (extraction-with-profile, measurement) also emit progress through the same `/api/vault/stream` SSE channel.
- **Aiven 20-conn budget enforcement** — Celery groups for 400-PDF runs must throttle. `--concurrency=2` is the budget. The dispatcher in slice 4 explicitly caps in-flight subtasks.
- **Excel security** — upload size cap (50 MB), MIME validation, ClamAV scan (deferred), Pydantic strict mode, audit row per upload.
- **Versioned metrics** — the field metric registry records `metric_version` alongside `metric_name`, so historical scores remain interpretable after a metric implementation changes.
- **Legacy-profile confidence proxy** — `legacy_v1` cannot produce per-page confidence. Calibration plots gracefully degrade (a notice replaces the plot) rather than misleading.
- **Vault sync** — these plan files exist in **two places**: this vault folder AND a mirror at `enigmatrix-docs/plans/2026-05-23_M1_Phase2_Upgrade_Plan/`. They will appear in the `/admin/m1/knowledge` portal via the existing `lib/vault/` reader chain (Session 57).
- **Retention policy** — slice 8 ships a nightly Celery beat that auto-retires dataset versions older than 30 days unless `keep=TRUE`. The original plan called this out as a risk; the upgrade promotes it to a deliverable.

## Vocabulary (canonical, use everywhere)

- **regulation key** — `gazette_number` style string, e.g. `2468/44`, that joins any baseline to any candidate.
- **dataset** — named, owned collection. `kind ∈ {manual_excel, extraction_run, expert_review}`.
- **dataset version** — immutable, sealed snapshot keyed by `version_number` (monotonic per dataset).
- **extraction profile** — named, versioned recipe in `m1_extraction_profiles`. Phase 1 = `legacy_v1`.
- **measurement run** — one act of scoring two versions against each other. Persists summary + per-field scores.
- **field metric** — one scoring function (e.g. `char_f1`, `labse_cosine`) registered for a specific field.
- **completeness status** — `{exact, partial, mismatch, missing, extra}` per `(regulation_key, field_name)`.
- **ground truth dataset** — the (exactly one) dataset row with `is_ground_truth=TRUE`. Default baseline for new measurement runs.

## Status (2026-05-23)

| Slice | Status | Blockers |
|---|---|---|
| 1 — Measurement scaffolding | 🔲 Not started | None — start here |
| 2 — Raw-text golden set | 🔲 Not started | Need second transcriber recruited |
| 3 — Dataset registry | 🔲 Not started | Slice 1 vocab must be locked first |
| 4 — Profile registry + legacy adapter | 🔲 Not started | Slice 3 |
| 5 — Measurement engine | 🔲 Not started | Slice 3 + 4 |
| 6 — Comparison UI | 🔲 Not started | Slice 5 |
| 7 — Three new profiles | 🔲 Not started | Slice 5 (so we can measure improvement) |
| 8 — Backfill + thesis polish | 🔲 Not started | Slices 1–7 |

## Open decisions — RESOLVED 2026-05-23

All 8 decisions resolved with the recommended defaults. See [12_Open_Questions](12_Open_Questions.md) for the resolved-decisions block at the top of that file. Key locked choices:

- **Q1 — Canonical writes during Phase 2:** Conditional flag (`update_canonical: bool = False`). Experimental safety wins.
- **Q2 — Excel storage:** Vault canonical at `C:\sme\_Attachments\structured_v1.xlsx`; `data/golden/` is the synced + gitignored working copy.
- **Q3 — Surya GPU:** Deferred to Phase 3. Slices 7A + 7B still ship.
- **Q4 — Slice-2 transcriber:** Pilot-first, recruit in parallel.

Slice 1 is unblocked. Start there.

## How to use this folder

This folder is **append-only**. Edits in place are fine for fixing typos or correcting facts; structural changes get a new file with a higher number. The eight slice files are the body of the plan; `00`–`01` and `10`–`12` are meta. After slice N ships, the corresponding slice file gets a `## Status` block at the top updated to `✅ shipped @ <session>` and the relevant `FEATURES.md` row gets the F-id assigned.

The same files exist at `C:\Reasearch\xyz\enigmatrix-docs\plans\2026-05-23_M1_Phase2_Upgrade_Plan\` so the knowledge portal at `/admin/m1/knowledge` (Session 57) can surface them.

## Related vault / repo nodes

- [16_M1_Development_Roadmap](../../02-Research-Modules/1%20Module-1-Awareness-Gap/16_M1_Development_Roadmap.md) — the parent roadmap. Phase 2 in this upgrade plan ≠ Phase 2 there; that one is the ingest-extract pipeline that already shipped. This plan is the "what comes between Phase 2-as-shipped and Phase 3-ML-training" wedge.
- [13_M1_Folder_Structure_and_Implementation_Flow](../../02-Research-Modules/1%20Module-1-Awareness-Gap/13_M1_Folder_Structure_and_Implementation_Flow.md) — the canonical folder spec all new code must conform to.
- [ENIGMATRIX_MASTER_CONTEXT](../ENIGMATRIX_MASTER_CONTEXT.md) — full project context as of Session 55.
- `enigmatrix-backend/app/services/m1_pipeline_service.py` — current pipeline service that the new dispatcher will live next to.
- `enigmatrix-backend/app/tasks/m1/` — existing Celery tasks (`gazette_scraper`, `extract_gazette`, `preprocess_gazette`, `run_scraper`).
- `enigmatrix-ml/m1/extraction/__init__.py` — canonical public API for the legacy extraction chain (what `LegacyV1Profile` adapts).
