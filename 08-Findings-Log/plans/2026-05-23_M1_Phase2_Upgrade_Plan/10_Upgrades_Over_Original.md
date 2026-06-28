---
tags: [m1, phase-2, upgrades, delta, design-rationale]
date: 2026-05-23
status: reference
---

# 10 — Upgrades Over the Original Six Uploaded Documents

> This file enumerates every concrete change this upgrade plan makes relative to the six uploaded files (`00_Phase2_Master_Plan.md` → `05_Build_Sequence_and_Risks.md`). For each change: what the original said, what the upgrade says, and why.
>
> The audit in [01_Alignment_Audit](01_Alignment_Audit.md) covers the *code-vs-plan* drift; this file covers the *plan-vs-upgraded-plan* delta. They overlap but read for different reasons: the audit is for engineers about to ship; this file is for the operator deciding whether the upgraded plan is the right plan.

## Category A — Fixes (these are non-negotiable corrections)

### A.1 The `LegacyV1Profile` adapter

- **Original** (`03_Extraction_Profiles_System.md`): an adapter that calls `extract_with_pymupdf`, `extract_with_pdfplumber`, `extract_with_tesseract`, `language_detection.detect_language`, `wijesekara.convert`, and `preprocess_gazette(..., regulation_key, None)`. None of those symbols exist; the call would crash on import or at runtime.
- **Upgrade** (slice 4): a corrected adapter using `extract_pymupdf` / `extract_pdfplumber` / `extract_tesseract` / `detect_document_language` (returns `LanguageDetection` dataclass) / `is_wijesekara_encoded` + `convert_wijesekara` / `preprocess_gazette(text, regulation_id=..., published_date=...)`. Same intent; runs.

### A.2 `classify_pdf` return type

- **Original**: reads `classification["type"]` and `classification.get("page_count", 0)`.
- **Upgrade**: uses the actual `Literal['text_pdf','hybrid','scanned']` return. Page count comes from a separate `fitz.open(path).page_count` call.

### A.3 Migration numbering

- **Original**: `010_m1_datasets_versioning.py`, `011_m1_extraction_profiles.py`, `012_m1_measurement.py`.
- **Upgrade**: `202605240002_m1_datasets_versioning.py`, `202605240003_m1_extraction_profiles.py`, `202605240004_m1_measurement.py` — matches the existing `YYYYMMDDNNNN` convention, chains correctly off the current tip `202605300001_merge_gazette_items_and_extraction_runs`.

### A.4 Storage path

- **Original**: `storage/m1/raw/<source_id>/<slug>.pdf`.
- **Upgrade**: `storage/m1/raw/<source_id>/YYYY/MM/<slug>.pdf` (partitioned, post-Session 38 + Railway volume mount).

### A.5 Aiven connection-pool budget

- **Original**: "the dispatcher creates a Celery group, one subtask per PDF."
- **Upgrade** (slice 4): batches of 8 with a Redis counter for synchronisation. Direct response to the documented 20-conn budget on Aiven entry tier.

## Category B — Additions (things the original plan was silent on)

### B.1 `audit_log` integration

- **Original**: not mentioned.
- **Upgrade**: every admin endpoint added in slices 3 / 4 / 5 / 6 records to `audit_log` via `audit_service.record()` per the `AGENTS.md` rule. Verb taxonomy spelled out in [01_Alignment_Audit §E](01_Alignment_Audit.md#e-the-audit_log-rule-🟡-convention-drift).

### B.2 i18n via `next-intl`

- **Original**: UI specs in English only.
- **Upgrade**: ~80 keys under `m1.phase2.*` in `frontend/messages/{en,si,ta}.json`. EN ships first; SI/TA can land with English placeholders + a follow-up sweep.

### B.3 Excel security

- **Original**: not mentioned.
- **Upgrade** (slice 3): 50 MB cap, MIME whitelist (`.xlsx`, `.csv` only), `openpyxl` `read_only=True, data_only=True` (no formula evaluation), per-upload audit row. ClamAV scan deferred to slice 8.

### B.4 Idempotency for re-uploads

- **Original**: not mentioned.
- **Upgrade** (slice 3): SHA-256 over the upload bytes. Re-upload of the same SHA → 409 Conflict. Re-upload while the previous parse is still running → 423 Locked.

### B.5 PDF resolver helper

- **Original**: assumes `raw_pdf_path` always exists.
- **Upgrade** (slice 4 / task 4.5): `m1_pdf_resolver.resolve_pdf_path(regulation_id)` tries partitioned path → flat path → web download from `m1_gazette_items.download_url`. Raises `PDFUnavailable` if all three fail.

### B.6 Confidence-aware calibration plot

- **Original**: dashboard always renders the reliability diagram.
- **Upgrade** (slice 6): plot renders only when the candidate version has ≥ 1 row with non-null `confidence`. For `legacy_v1` candidate, a placeholder card explains why the plot is hidden. Avoids misleading visualisations.

### B.7 Versioned metrics

- **Original**: metric registry is just `(metric_fn, threshold)`.
- **Upgrade** (slice 1): every metric carries `__version__` and the score row records `metric_version` alongside `metric_name`. Dashboard filters by metric version when drawing trend lines. Mitigates the original plan's risk #7 (metric registry drift).

### B.8 SSE / polling reuse

- **Original**: implies new polling endpoints from scratch.
- **Upgrade**: reuses TanStack Query 5 s polling (already in production for the extraction-progress page). Vault SSE channel (Session 57) is an opt-in enhancement, not a default. Pattern reuse keeps the bundle small.

### B.9 Font-instrumentation task

- **Original**: assumes the 87 → 180 entry expansion is fine.
- **Upgrade** (slice 7 task 7.3): a one-week instrumentation run on the existing corpus identifies the actual fonts in use BEFORE the map is expanded. The expansion is empirically prioritised, not aspirational.

### B.10 PDF resolver web-fallback

- **Original**: assumes every PDF is on disk.
- **Upgrade**: `m1_pdf_resolver` falls back to `m1_gazette_items.download_url` and caches the result. Reflects the actual current architecture (where new spider rows post Session 55 only carry web URLs).

### B.11 Backward-compatibility freeze on legacy code

- **Original**: implied but not codified.
- **Upgrade**: explicit rule in slice 4 — `enigmatrix-ml/m1/extraction/` and `enigmatrix-ml/m1/preprocessing/` are FROZEN during Phase 2. New work goes to `enigmatrix-ml/m1/extraction/profiles/` and `enigmatrix-ml/m1/extraction/page_engines/`. Slice 8's `legacy_v1` regression test asserts the cleaned-text output is byte-stable.

### B.12 Plan vault-sync

- **Original**: lives in a single folder of upload-only files.
- **Upgrade**: lives in TWO synchronised folders — vault (`C:\sme\08-Findings-Log\plans\2026-05-23_M1_Phase2_Upgrade_Plan\`) and repo (`enigmatrix-docs/plans/2026-05-23_M1_Phase2_Upgrade_Plan/`). The Session-57 vault-sync chain ensures the `/admin/m1/knowledge` portal renders these files automatically.

## Category C — Sharpenings (the original was fine, this is just clearer)

### C.1 Vocabulary terms

The original master plan defines the seven core terms. The upgrade re-states them in `00_INDEX` at the top and uses them consistently across all 12 files — no `regulation_id` vs `regulation_key` drift, no `extraction_run` vs `extraction_dataset` ambiguity.

### C.2 Slice dependency graph

The original dependency graph is mostly linear. The upgrade calls out which slices are independently shippable (1, 2, 3, 4, 5, 7) and which are not (6 depends on 5; 8 is wrap-up). Each slice file has a "What this slice deliberately does NOT do" section that bounds scope sharply.

### C.3 Gate definitions

The original gates are mostly textual. The upgrade specifies gates as bullet-point verifiable claims with thresholds (e.g. "score ≥ legacy + 3 pp", not "score should improve"). The slice-7 outcome write-up template formalises this.

### C.4 Risk register expansion

The original lists 7 risks. The upgrade keeps all 7, addresses each in the relevant slice, and adds risks unique to the upgrades themselves (e.g. heatmap legibility on small screens, GE suites being too strict).

### C.5 Honesty checks

Every slice with quantitative output (1, 5, 7) has an explicit "honesty check" step where the engineer eyeballs five rows / five PDFs against intuition before declaring the slice green. Without this, the pipeline produces numbers nobody trusts.

## Category D — Things kept exactly as the original

- The four architectural ideas (datasets-first-class, versions, profiles, measurement-as-pure-function).
- The seven core vocabulary terms (regulation key, dataset, dataset version, extraction profile, measurement run, field metric, completeness status).
- The three new profiles' algorithms (`page_routing_v1`, `wijesekara_routing_v1`, `surya_fallback_v1`).
- The field-metric registry shape and the choice of metrics per field.
- The completeness model (5 statuses).
- The eight-stratum sampling for the raw-text golden set.
- The 800-PDF Phase-3 dependency for statistical power on CER claims.

## Category E — Things explicitly deferred to Phase 3 (consistent with the original)

- `pymupdf4llm_v1` profile (mentioned in the original; deferred here too).
- XLM-R + LoRA classifier training.
- 100-PDF raw-text golden set expansion for full statistical power.
- MarianMT trilingual summarisation.
- Alert dispatch (SendGrid + Twilio).
- DiD effect measurement (treatment vs control).

## How to use this delta when reviewing the plan

For each slice file (02–09), the audit-driven corrections are inline — you don't need to cross-reference this file to find them. This file exists for the operator who wants to understand *why* the upgrade plan is structured differently from the upload. If you've already accepted the upgrades and want to start shipping, jump straight to [02_Slice1_Measurement_Scaffolding](02_Slice1_Measurement_Scaffolding.md).

## Cross-references

- [01_Alignment_Audit](01_Alignment_Audit.md) — the technical detail behind every Category A fix.
- [11_Risks_Register](11_Risks_Register.md) — consolidated risks with mitigations.
- [12_Open_Questions](12_Open_Questions.md) — decisions the operator still needs to make.
