# M1 Phase-2 Measurement — Field Contract, EQS Engine & UI Upgrade

> Goal: make extraction accuracy **task-selectable, tier-weighted, phase-separated, and visible in the admin UI** — without conflating classifier confidence with extraction accuracy. This document is the corrected updates plan plus the execution record of what was shipped on 2026-07-26.
>
> Scope: Module 1 (Awareness Gap), Phase-2 extraction measurement. Golden truth is now the 8-batch official workbook `data/golden/structured_v1_batches_1_2_3_4_5_6_7_8_official.xlsx` (sheet `regulations_raw_data`, 800 records, 39 columns).

---

## 0. Reality check — what already existed before this work

The original plan assumed several pieces were still "deferred." A ground-truth read of the `xyz/` monorepo on 2026-07-26 shows the measurement spine is **already built and mature**. Correcting the record so no one re-implements shipped code:

| Plan assumption | Actual state in repo | Evidence |
| --- | --- | --- |
| "No UI to upload golden xlsx" | **Shipped.** `POST /api/v1/m1/datasets/{id}/versions/upload` accepts an Excel/CSV `UploadFile` via `dataset_upload.upload_excel_version`; the admin flow lives at `/admin/datasets/m1/new` + `/extractions`. | `enigmatrix-backend/app/m1/api/datasets.py`, `app/m1/services/dataset_upload.py` |
| "No task-scoped measurement" | **Shipped.** Measurement runs already accept `source_id`, `date_from`, `date_to`, and a `/candidate-versions` picker resolves sealed extraction versions overlapping a publication-date window. | `app/m1/api/measurements.py` (`dispatch_measurement_run`, `list_candidate_versions`) |
| "No per-field drill-down / heatmap / calibration" | **Shipped.** `/{run_id}/per-field`, `/regulations/{key}`, `/worst`, `/calibration`, `/scores` (CSV) endpoints exist and are wired to a polished dashboard. | `app/m1/api/measurements.py`; frontend `components/m1/measurement-dashboard/*` |
| "Frontend is thin" | **Mature.** Runs list has sortable columns, keyboard shortcuts, recent-run sparklines; run detail has KPI cards, field heatmap, slice breakdowns, worst-N, calibration plot, profile-delta — all animated (`framer-motion`, `AnimatedItem`). | `app/(admin)/admin/datasets/m1/measurements/**` |
| "Evaluation package to be written" | **Shipped.** `xlsx_reader`, `field_metrics` (21-field registry), `metrics/*`, `completeness`, `aggregates`, `strata`, `date_scope`, `raw_text` all present with tests. | `enigmatrix-ml/m1/evaluation/*`, `tests/evaluation/*` |

**Genuine gap that everything else in the plan depended on:** there was **no field contract** and **no tier-weighted EQS**. The scorer produced an *unweighted* mean of primary scores (`aggregate_overall`), which silently mixed a fatal wrong-gazette-number with a paraphrased summary, and scored expert-curated classification labels (`change_category`, `severity_level`) as if they were extraction accuracy. That gap is what this work closes.

---

## 1. What was shipped (2026-07-26)

### 1.1 `data/golden/field_contract_v1.yaml` — the sidecar contract
A read-only sidecar (never edits the immutable golden workbook) mapping **all 39 columns 1:1** to `tier / weight / metric / phase / null_ok`, with the real fill-rates measured from the 8-batch workbook.

- **Tiers & weights:** `A` (must-match anchors, w3.0), `B` (primary content, w2.0), `C` (soft/semantic, w1.0), `D` (annotation-only, w0.0 — excluded), `S` (system/provenance, w0.0 — never scored).
- **Join key order:** `gazette_number` → `document_number` → `regulation_short_code`.
- **Gates:** Tier-A pass-rate ≥ 0.95 and extraction EQS ≥ 0.90.
- **Phase separation encoded in data:** classification labels are marked `phase: annotation` and drop out of EQS until Phase-3 dual-annotated gold exists.

Tier assignment reflects measured reality, not guesswork:

| Field(s) | Tier | Phase | Why |
| --- | --- | --- | --- |
| `gazette_number`, `gazette_published_date`, `effective_date`, `document_type`, `document_number`, `raw_text` (presence) | A | extraction | Identity + legal-effect anchors; a miss invalidates the record. |
| `title_en`, `summary_en`, `principal_act_amended`, `regulation_short_code` | B | extraction | Primary extracted content. |
| `title_si`, `title_ta`, `bill_published_date`, `cleaned_text` (presence) | C | extraction | Soft/semantic; `null_ok` because SI/TA titles (74% filled) are legitimately empty when the source has none. |
| `domain_code`, `change_category`, `severity_level`, `is_sme_relevant`, `penalty_range_lkr`, `amendment_type`, SI/TA summaries, real-world examples | D | annotation | Expert-curated or not-yet-extracted (0% filled). **Excluded from EQS.** |
| `regulation_id`, `source_url`, `expert_verified*`, `sme_relevance_confidence`, `is_active`, `status`, `raw_pdf_path`, `extraction_method`, timestamps | S | system/provenance | Bookkeeping; `extraction_method` is a **stratum**, not a scored field. |

Measured fill-rates that justify `null_ok` (so completeness is not mistaken for accuracy): SI/TA titles 74%, principal act 83%, bill date 67%, SI/TA summaries 0%, penalties ~0%, real-world examples ~1%, cleaned_text 0% (Stage C not yet run on this batch).

### 1.2 `enigmatrix-ml/m1/evaluation/field_contract.py` — loader + EQS engine
- `load_field_contract(path)` parses the YAML, resolves columns → canonical evaluation field names, and dedupes collapses (`regulation_short_code`/`gazette_number` → strongest tier wins).
- `compute_eqs(scores, contract)` consumes the **exact `Score` objects** `field_metrics.score_corpus` already emits — so it drops into both the offline baseline script and the slice-5 Celery task with zero change to how scores are produced. It returns:
  - per-record EQS = `Σ(w·m) / Σ(w)` over in-scope extraction cells, mean-aggregated to a corpus EQS (equal weight per record so a fat-title record can't dominate a thin one);
  - tier roll-ups (pass-rate = fraction at status `exact`);
  - phase split (extraction vs annotation cell counts);
  - gate evaluation (Tier-A ≥ 95%, EQS ≥ 90%).
- **Honest edge handling:** a `null_ok` field whose candidate is absent (`missing`) is dropped, not counted as 0; a `mismatch` with no numeric score counts as a real 0.

### 1.3 Tests — `tests/evaluation/test_field_contract.py`
9 tests, all passing. They mirror the slice-1 patterns (small hand-built `Score` fixtures, exact numeric assertions) and additionally guard invariants against the shipped YAML: 39 columns present, annotation labels excluded from EQS scope, weighted-mean math (`5/6` fixture), `null_ok` drop-out, mismatch-as-zero, gate evaluation, phase split. Verified against the real `data/eval/baseline_v0_rows.csv` (194 score rows → EQS 0.79, Tier-A pass 100%, Tier-B pass 50%).

### 1.4 Frontend EQS surface (additive, non-breaking)
- `lib/m1/field-contract.ts` — a tiny client mirror of the contract (canonical field → tier/phase) + `computeEqs()` that reuses the per-field summary the run page already fetches. **No new endpoint.**
- `components/m1/measurement-dashboard/EqsPanel.tsx` — an animated panel: a headline EQS gauge, Tier A/B/C pass-rate bars showing weight + field counts, the two acceptance gates as pass/fail chips, and an extraction-vs-annotation phase-split bar (annotation labelled *excluded*). Uses `framer-motion`, `Card`, and the in-house tone tokens, matching `KpiCards` grammar exactly.
- Wired into `/admin/datasets/m1/measurements/[runId]` as the second staggered block (after KPI cards, before the heatmap). Typechecks clean; existing blocks untouched apart from monotonic stagger indices.

The EQS panel answers the plan's Step 6.3 ("Dashboard cards: Completeness %, EQS %, Tier-A pass rate") and 6.6 ("show extraction confidence and classifier confidence in different columns, never one bar for both") — annotation cells are visually and numerically separated from the extraction EQS.

---

## 2. How to use it

### 2.1 Upload the golden workbook from the UI
1. Go to `/admin/datasets/m1` → create (or open) the golden dataset.
2. Upload `structured_v1_batches_1_2_3_4_5_6_7_8_official.xlsx` via the version-upload control (`POST /datasets/{id}/versions/upload`). The reader auto-detects the header row and canonicalises columns.
3. **Seal** the version (`/versions/{id}/seal`) — only sealed versions are measurable.
4. Later, a corrected/upgraded workbook in the **same 39-column format** uploads as a new version of the same dataset; version governance keeps the lineage. Re-run measurement against the new version — never overwrite an old baseline.

### 2.2 Run a measurement + read the EQS
1. `/admin/datasets/m1/measurements/run` — pick baseline (golden) + candidate (extraction run, optionally scoped by `source_id` + date window).
2. Dispatch → the run detail page polls progress, then renders KPI cards **and the new EQS panel** with tier pass-rates and gate status.
3. Drill failing fields via the heatmap → worst-N → per-regulation view.

### 2.3 Offline baseline (unchanged path)
```powershell
cd C:\Reasearch\xyz
uv run python scripts/run_baseline_measurement.py   # -> data/eval/baseline_vN.json
```
Extend the baseline JSON with the EQS block by calling `compute_eqs()` on the same `Score` list the script already builds.

---

## 3. Operational loop (Step 7, corrected)
1. Score the full 800-record corpus → `baseline_v0` (done).
2. Read the EQS panel: fix extractors/regex for the lowest **Tier-A** fields first (they carry weight 3.0 and gate the run).
3. Re-run → `baseline_v1` (versioned; never overwrite).
4. **Gate:** Tier-A pass ≥ 95% **and** extraction-only EQS ≥ 0.90. Both chips green = ready.
5. Only then promote rows into Phase-3 sampling (`sample_for_labeling.py`).

Classifier confidence (Stage D softmax, ECE, review-queue at <0.70) stays **out of this loop** — it is Phase-3d+ and must never share a bar with extraction accuracy.

---

## 4. Follow-ups not done here (explicitly deferred)
- **Persist EQS in the backend `field_summary`** so the panel reads server-computed EQS instead of recomputing client-side (current version is a faithful field-weighted mirror; the per-record engine lives in Python and can be surfaced via a `/{run_id}/eqs` endpoint when wanted).
- **`gazette_number` as a distinct scored field** — the scorer currently folds gazette identity into `regulation_key` (Tier B). The contract already declares `gazette_number` Tier A for when the scorer emits it separately.
- **Extraction-side confidence calibration** (`confidence_calibration.py`) — reliability diagram of metadata-extractor confidence vs field accuracy.
- **`data/golden/README` refresh** stating golden immutability, the contract, thresholds, and the "not for classification IAA" boundary.

---

## 5. Files touched

| File | Change |
| --- | --- |
| `data/golden/field_contract_v1.yaml` | **new** — 39-column sidecar contract |
| `enigmatrix-ml/m1/evaluation/field_contract.py` | **new** — loader + EQS engine |
| `enigmatrix-ml/tests/evaluation/test_field_contract.py` | **new** — 9 passing tests |
| `enigmatrix-frontend/lib/m1/field-contract.ts` | **new** — client contract mirror + `computeEqs` |
| `enigmatrix-frontend/components/m1/measurement-dashboard/EqsPanel.tsx` | **new** — animated EQS surface |
| `enigmatrix-frontend/app/(admin)/admin/datasets/m1/measurements/[runId]/page.tsx` | **edit** — mount `EqsPanel` (additive) |

_Last updated: 2026-07-26._
