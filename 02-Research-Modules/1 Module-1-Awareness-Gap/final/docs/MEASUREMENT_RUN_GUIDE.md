# Measurement Run Dashboard — Field Guide, Scoring Rules & the `raw_text` Defect

**Reference run:** `5908bc9f-9cb6-48b7-ab02-35913fd6ac56` · completed 2026-07-27 12:36:13 UTC
**Written:** 2026-07-28 · **Contract:** `data/golden/field_contract_v1.yaml` v1.0.0

This document does three things:

1. Explains **every section** of `/admin/datasets/m1/measurements/[runId]`, what each attribute means, and the pass range for it.
2. Explains **why each of the 7 fields in this run scored what it scored**.
3. Diagnoses and fixes the **`raw_text` defect** — baseline showing `—` while the candidate shows a value, producing 51 bogus `Extra` cells.

---

## Part 0 — The headline answer

> **Q: The baseline shows `—` for `raw_text` and every row is `Extra`. What is wrong?**

**The ground truth is not empty. The scorer was looking in the wrong place.**

The golden workbook has `raw_text` filled on **798 of 800 rows** (median 9,529 characters). Verified directly:

```
raw_text        798/800  100%     len: min 853 · median 9529 · max 32767
title_si        800/800  100%
title_ta        800/800  100%
```

The scorer read `baseline_row.get("raw_text")` and got `None`, because on an Excel-uploaded
baseline that value is parked one level down, inside the row's `_extras` blob. The candidate —
a DB snapshot — carries `raw_text` at the top level. Same column, two different shapes, so:

| Side | Where `raw_text` actually lives | What `row.get("raw_text")` returned |
|------|--------------------------------|-------------------------------------|
| Baseline (Excel upload) | `fields["_extras"]["raw_text"]` | `None` |
| Candidate (DB snapshot) | `M1DatasetRow.raw_text` column → top level | the text |

`compute_status(baseline=absent, candidate=present)` → **`extra`**, on all 51 rows.

**It is a field-resolution bug, not a data gap.** The `Extra` badge was accusing the pipeline of
inventing text that the ground truth demonstrably contains.

---

## Part 1 — Root cause chain

```
data/golden/…_official.xlsx           39 columns, raw_text filled 798/800
        │
        ▼
xlsx_reader.read_canonical_excel()    promotes only the 21 CANONICAL_FIELDS
        │                              raw_text is NOT one of them
        ▼                              → lands in  row["_extras"]["raw_text"]
dataset_upload.py                     stores the whole dict into
        │                              M1DatasetRow.fields (JSONB), _extras included.
        ▼                              The dedicated .raw_text COLUMN stays NULL.
run_measurement._load_rows_by_key()   merges fields; promotes .raw_text / .cleaned_text
        │                              columns — both NULL here, so nothing surfaces.
        ▼
field_metrics.score_row()             bv = baseline_row.get("raw_text")  → None
        │                              cv = candidate_row.get("raw_text") → text
        ▼
completeness.compute_status()         not base_present and cand_present → "extra"   ✗
```

The same asymmetry silently affected **five more registry-scored fields** that also sit outside
`CANONICAL_FIELDS`: `gazette_number`, `raw_pdf_path`, `source_url`, `extraction_method`,
`extracted_at`. Those didn't show as `Extra` only because the candidate snapshot didn't carry
them either — both sides absent, so `score_row` skipped the cell entirely and they vanished from
the dashboard. `gazette_number` is the contract's **Tier-A "single most critical extracted
identifier"** and it was not being measured at all, on either side.

### Verified reproduction

Replaying the run against the real golden workbook with pre-fix resolution reproduces the
dashboard **exactly, number for number**:

| Metric | Replay | Screenshot |
|---|---|---|
| Fields scored | 7 | 7 |
| Total primary cells | 357 | 357 |
| Missing/extra | 153 = 43% | 153 = 43% |
| Overall score | 1.000 | 1.000 |
| Tier A pass | 67% (102/153) | 67% (102/153) |
| Tier B pass | 100% (102/102) | 100% (102/102) |
| EQS | 100% over 4 fields | 100% over 4 fields |
| Tier-A gate | FAIL | FAIL |

---

## Part 2 — Every dashboard section explained

### 2.1 Hero header strip

| Attribute | Value in this run | What it means |
|---|---|---|
| Status | `COMPLETE` | Terminal state. Only `complete`/`failed`/`cancelled` render a scorecard. |
| Run ID | `5908bc9f-…` | Primary key of `m1_measurement_runs`. Cite this in any bug report. |
| Overall score | `1.000` | Unweighted mean of primary-metric scores. **Colour: ≥0.85 green · ≥0.60 amber · <0.60 red.** |
| Measurement type | `A/B COMPARE` | Both sides are sealed dataset versions. |
| `Manual upload → DB snapshot` | — | The provenance pair. This mixed pairing is what exposes the `_extras` asymmetry. |
| `extracted` | — | `snapshot_stage`. Selects the **cumulative** field scope (see 2.4). |
| `Full corpus` | — | No publication-date window applied (`date_from`/`date_to` both null). |
| `7 fields (scoped)` | — | How many fields ended up with at least one scored cell. |
| Baseline | Manual GT Jan–Apr 2026, v2, 800 rows | The truth side. `GT` badge = `is_ground_truth`. |
| Candidate | DB snapshot EGZ 2026-03-01..03-07, v2, 54 rows | The side under test. |

**Why 51 regulations from a 54-row candidate and an 800-row baseline?** The run uses an
**inner join** on the canonicalised gazette key (`2478_01` ≡ `2478/1` ≡ `EGZ_2478_01`).
51 matched; 3 candidate rows had no ground truth. Baseline-only rows are a *coverage gap*
reported separately in `completeness_summary._regulation_coverage`, deliberately **not** scored as
per-field `missing` — otherwise 749 unmeasured regulations would tank every field mean.

---

### 2.2 KPI cards

| Card | This run | Formula | Target |
|---|---|---|---|
| **Overall score** | 1.000 | mean of non-null primary scores, excluding headline-excluded fields | **≥ 0.85** green · 0.60–0.85 amber · < 0.60 red |
| **Total regulations** | 51 | `join_matched` | informational |
| **% with ≥1 mismatch** | 0% (0/357) | `Σ mismatch ÷ total primary cells` | **0% ideal; ≥ 20% is red** |
| **% with missing/extra** | 43% (153/357) | `Σ(missing + extra) ÷ total primary cells` | **0% ideal; ≥ 15% is red** |

**Where 153 comes from:** 51 `raw_text` extra (**the bug**) + 51 `title_si` missing + 51 `title_ta`
missing. Of those, only 102 were real — and after the fix, `raw_text` contributes 0.

> **Reading trap:** *Overall score 1.000 next to 43% missing/extra is not a contradiction.*
> `Overall` averages the numeric primary scores; `missing`/`extra` cells have **no numeric score**
> (the metric returns `None`), so they are invisible to the mean. A run can be "100% accurate on
> what it managed to compare" while comparing less than half of it. **Always read the two together.**

---

### 2.3 Extraction Quality Score (EQS) panel

The honest, tier-weighted headline. Where "Overall score" treats a file-path presence flag and a
gazette-number identity match as equal, EQS weights by criticality and scores **extraction-phase
fields only**.

```
EQS = Σ(weight_f × mean_f) / Σ(weight_f)      over in-scope fields
```

| Tier | Weight | Meaning | This run |
|---|---|---|---|
| **A · anchors** | ×3 | Identity / legal anchors. A miss invalidates the record. | 3 fields · **67%** · 102/153 exact |
| **B · content** | ×2 | Primary extracted content. | 2 fields · **100%** · 102/102 |
| **C · soft** | ×1 | Semantic / best-effort content. | 0 fields · — |
| D · annotation | ×0 | Expert-curated labels. **Excluded** — scoring them as "extraction accuracy" is dishonest. | — |
| S · system | ×0 | Provenance / bookkeeping. **Never scored.** | — |

#### Acceptance gates

| Gate | Threshold | This run | Verdict |
|---|---|---|---|
| **Tier-A pass rate** | **≥ 95%** exact | 67% | ❌ **FAIL** |
| **EQS** | **≥ 90%** | 100% | ✅ PASS |

A run is **green only when both gates hold.**

**Why Tier-A failed at exactly 67%:** Tier A holds `document_type`, `document_number`, `raw_text`.
Two are perfect (102 exact); `raw_text`'s 51 `extra` cells count as non-exact → 102/153 = 66.7%.
**The single defect cost the acceptance gate.**

**Why EQS still read 100% "over 4 scored fields":** EQS averages field *means*. `raw_text`'s mean is
`null` (every cell scored `None`), so it drops out of the weighted average entirely while still
counting against the Tier-A pass rate. Five fields are in EQS scope; only four had a usable mean.
**That divergence — a gate at 67% beside a score of 100% — is itself the tell that a field is
producing null scores.**

#### Phase split

`7 extraction · 0 annotation (excluded)` — all seven scored fields are extraction-phase. Annotation
fields (`domain_code`, `change_category`, `severity_level`, …) are counted for visibility but never
scored until Phase-3 dual-annotated gold exists.

---

### 2.4 Per-field heatmap

One row per field; five status columns plus the primary-metric mean.

#### The five statuses

| Status | Condition | Numeric score? |
|---|---|---|
| **Exact** | both present, `primary_score ≥ threshold` | yes |
| **Partial** | both present, `0.5 ≤ score < threshold` | yes |
| **Mismatch** | both present, `score < 0.5` or `None` | yes / null |
| **Missing** | baseline has a value, candidate does not | **no** |
| **Extra** | candidate has a value, baseline does not | **no** |

Cells where *neither* side has a value are omitted entirely. `Missing`/`Extra` carry no score —
which is why they never move `Overall` and must be read from this heatmap.

#### Why the scope is 7 fields

`snapshot_stage = extracted` selects a **cumulative** field list — `ingested` + `extracted`:

```
regulation_key · gazette_number · document_type · document_number · raw_pdf_path · source_url
title_en · title_si · title_ta · raw_text · extraction_method · extracted_at        → 12 fields
```

Only 7 appeared. The other 5 were absent on **both** sides (baseline in `_extras` and unresolved;
candidate never emitted them) so every cell was skipped.

#### Field-by-field verdict

| Field | Tier | Primary metric | Threshold | Result | Verdict |
|---|---|---|---|---|---|
| `document_number` | A | `normalized_exact_match` | 1.0 | 51 exact · 1.00 | ✅ Correct |
| `document_type` | A | `categorical_exact` | 1.0 | 51 exact · 1.00 | ✅ Correct — 100% `extraordinary_gazette` |
| `regulation_key` | B | `gazette_id_match` | 1.0 | 51 exact · 1.00 | ✅ Correct — canonicaliser reconciles `2478_01`/`EGZ_2478_01` |
| `title_en` | B | `normalized_exact_match` | 0.95 | 51 exact · 1.00 | ✅ Correct |
| **`raw_text`** | **A** | `presence_nonempty` | 1.0 | **51 extra · mean —** | ❌ **BUG** — GT has it 798/800 |
| `title_si` | C | `char_f1` | 0.80 | 51 missing · mean — | ⚠️ **Real gap** — GT 800/800, candidate 0/51 |
| `title_ta` | C | `char_f1` | 0.80 | 51 missing · mean — | ⚠️ **Real gap** — same |

**`title_si` / `title_ta` are correctly scored, but the policy around them is now stale.** They are
`optional: true`, so they are excluded from both the headline and EQS. That exemption was written
when the golden set was only 74% filled ("empty is valid when the source has no Sinhala title").
Batches 4–8 backfilled it to **800/800**. The exemption now hides a genuine Tier-C extraction gap:
the extract stage populates **0 of 51** SI/TA titles and the dashboard still reads 100%.
See "Open decision" below.

---

### 2.5 Slice breakdowns

`Coming soon` for all five dimensions (document type, primary language, year bucket, source,
extraction method). **This is an intentional, honest placeholder, not a failure** — the slice-5
backend does not yet surface per-row dimensions in aggregated form. Once populated, the
`extraction_method` slice is the important one: it separates native-PDF text from OCR, and OCR
strata are where the corruption visible in the worst-list originates.

---

### 2.6 Worst regulations

The 20 lowest-scoring primary rows across `mismatch / missing / extra`, ordered mismatches first
(numerically worst), then missings, then extras. Clicking a heatmap cell filters this list.

In this run it is **entirely `raw_text (presence_nonempty)` rows with `BASELINE —`** — every entry a
symptom of the same defect. Note what the candidate text looks like:

```
2478/1   ණ්‌ 3 . YIN (Ge CoS ॥ (9) 80009 80801 25087 0:20 89% The Gazette of the Democra…
2478/13  ෴ ap SS | LES SY ©) © ම போத்‌ ॥ ein 8009 60808 990860 00 89% The Gazette of t…
```

**This is separately diagnostic and should not be dismissed.** That is Sinhala/Tamil OCR failing —
legacy-font glyphs mis-mapped to Latin. `presence_nonempty` only asks *"is the column non-empty?"*,
so garbage scores 1.0 the moment the baseline resolves. **Presence is not quality.** Character-level
quality already exists in `m1/evaluation/raw_text.py` (CER/WER against transcribed gold pages) but is
not wired into this dashboard. Recommended follow-up.

---

### 2.7 Calibration plot

Reliability diagram over 15 confidence buckets: candidate-side confidence (x) vs. mean primary score
(y), against a 45° perfect-calibration line. Below the line = overconfident.

In this run it rendered as **empty axes**. The candidate's `confidence` JSONB is non-null but holds
no numeric value, so the API's `candidate_has_confidence` check passes, returns 200, and every
bucket comes back null — bare axes that read as "calibration is flat" rather than "nothing to plot."
**Fixed** (see 3.5): zero plottable points now renders the same honest placeholder as the 404 path.

---

### 2.8 Profile delta

Compares this run against another candidate measured against the **same baseline** — the mechanism
for answering "did the extractor improve?". Empty here because no sibling run exists yet. After
re-running with the fixes, this is where old-vs-new should be compared.

---

## Part 3 — Fixes applied

### 3.1 `resolve_field` — `_extras` fallback *(ml, pre-existing in working tree)*

`enigmatrix-ml/m1/evaluation/field_metrics.py`

Read a field from the row, falling back to `_extras` when the top level is absent. Top level always
wins, so a populated canonical column is never overridden by a stray same-named extra. Header-shaped
keys (`"Raw text"`, `"RAW-TEXT"`) are snake-cased before matching.

**Effect:** `raw_text` → **51 exact**, Tier A → **3 fields at 100%**, Tier-A gate → **PASS**.

### 3.2 Candidate-side symmetry *(backend)*

`app/m1/services/snapshot_service.py` — `_reg_to_fields` now also emits `gazette_number`,
`raw_pdf_path`, `source_url`, `extracted_at`. Every temporal value is ISO-coerced, not just the two
in `_DATE_FIELDS`, because `extracted_at` is a `datetime` and JSONB would otherwise fail the INSERT.

`app/m1/tasks/run_measurement.py` — `_load_rows_by_key` now promotes the `extraction_method` column
alongside `raw_text` / `cleaned_text`.

**Why this is required, not optional:** fixing 3.1 alone makes the baseline resolve five *more*
fields that the candidate still doesn't emit. They flip from "both absent → skipped" to
`missing`, and overall drops **1.000 → 0.627** without a single extraction result changing.
Confirmed by replay. **3.1 must not ship without 3.2.**

### 3.3 Headline excludes Tier-S provenance *(ml)*

`field_metrics.py` gains `NON_ACCURACY_FIELDS` = {`raw_pdf_path`, `source_url`, `extraction_method`,
`extracted_at`} — the four columns the contract marks `tier: S, metric: none`.
`aggregate_overall` now excludes `OPTIONAL_ACCURACY_FIELDS | NON_ACCURACY_FIELDS` by default.

They remain **scored and visible** per-field (useful completeness signal) but no longer vote in the
headline. `gazette_number` and `raw_text` are explicitly **not** in this set — the contract puts both
at Tier A. This brings the backend into agreement with the frontend EQS mirror, which already
omitted them.

### 3.4 Contract fill-rate drift *(config)*

`data/golden/field_contract_v1.yaml` — `title_si` / `title_ta` `fill_rate` corrected `0.74 → 1.00`,
with a dated `REVIEW:` note recording that the justification for `optional: true` no longer holds.

### 3.5 Calibration placeholder *(frontend)*

`CalibrationPlot.tsx` — zero plottable buckets now renders the "unavailable" card instead of empty axes.

### 3.6 Regression tests *(ml)*

`tests/evaluation/test_field_metrics.py`:

- `test_non_accuracy_fields_are_tier_s_provenance_only` — pins the exclusion set; fails loudly if
  `gazette_number` or `raw_text` ever drifts into it.
- `test_aggregate_overall_ignores_provenance_presence_probes` — a perfect extraction with empty
  provenance columns must still score 1.000, the fields must still be visible, and
  `exclude_fields=frozenset()` must still expose the completeness gap.

**Suite status: 132 passed, 0 failed.**

---

## Part 4 — Before / after

Same golden workbook, same 51 regulations, faithful DB-snapshot candidate:

| | Before | After |
|---|---|---|
| `raw_text` | **51 extra**, mean — | **51 exact**, mean 1.00 |
| `gazette_number` (Tier A) | not scored at all | **51 exact**, mean 1.00 |
| Fields scored | 7 | 12 |
| Missing/extra | 153/357 = **43%** | 102/611 = **17%** |
| Overall score | 1.000 | 1.000 |
| Tier A | 3 fields · **67%** (102/153) | 4 fields · **100%** (204/204) |
| Tier B | 2 fields · 100% | 2 fields · 100% |
| EQS | 100% over 4 fields | 100% over 6 fields |
| **Tier-A gate ≥95%** | ❌ **FAIL** | ✅ **PASS** |
| **EQS gate ≥90%** | ✅ PASS | ✅ PASS |

The residual 17% missing/extra is the **real** `title_si`/`title_ta` extraction gap. It is no longer
mixed in with a scoring artefact.

---

## Part 5 — Deploying & re-running

`enigmatrix-ml` is an **editable uv workspace member**, so no rebuild is needed — but the Celery
worker caches the module at import:

1. **Restart the Celery worker.** Without this the worker keeps the old `score_row` in memory and a
   re-run reproduces the identical wrong numbers.
2. **Re-snapshot the candidate.** 3.2 changes what `_reg_to_fields` writes; the existing sealed v2
   snapshot does not contain `gazette_number` / `raw_pdf_path` / `source_url` / `extracted_at`.
   Sealed versions are immutable by design — take a new snapshot rather than mutating it.
3. **Re-run** against the same baseline, then use **Profile delta** to compare old vs. new.

**Expected after re-run:** `raw_text` 51 exact · Tier A 100% over 4 fields · Tier-A gate **PASS** ·
missing/extra ≈ 17% · `title_si`/`title_ta` still 51 missing each.

---

## Part 6 — Reference: thresholds & targets

### Acceptance gates (`field_contract_v1.yaml`)

| Gate | Threshold |
|---|---|
| `tier_a_pass_rate_min` | **0.95** |
| `eqs_extraction_min` | **0.90** |

### KPI colour bands

| Metric | Green | Amber | Red |
|---|---|---|---|
| Overall / field mean | ≥ 0.85 | 0.60 – 0.85 | < 0.60 |
| % with ≥1 mismatch | 0% | 0 – 20% | ≥ 20% |
| % missing or extra | 0% | 0 – 15% | ≥ 15% |

### Per-field primary thresholds

| Field | Metric | Threshold |
|---|---|---|
| `regulation_key` | `gazette_id_match` | 1.00 |
| `gazette_number` | `gazette_id_match` | 1.00 |
| `document_type` | `categorical_exact` | 1.00 |
| `document_number` | `normalized_exact_match` | 1.00 |
| `title_en` | `normalized_exact_match` | 0.95 |
| `title_si` / `title_ta` | `char_f1` | 0.80 |
| `summary_en` | `rouge_l_f` | 0.45 |
| `gazette_published_date` | `date_exact_match` | 1.00 |
| `effective_date` | `date_within_tolerance_7d` | 0.85 |
| `raw_text` / `cleaned_text` / provenance | `presence_nonempty` | 1.00 |
| `m1_sub_documents` / `m1_regulation_penalties` | soft-F1 | 0.80 |

Thresholds are the **exact** cut. `0.5 ≤ score < threshold` → `partial`; below 0.5 → `mismatch`.

---

## Part 7 — Open items

### Open decision — `title_si` / `title_ta` `optional: true`

**Not changed**, because it is a scoring-policy call, not a bug. The golden set is now 800/800
filled, so the exemption lets an extract stage that produces **0 of 51** SI/TA titles report 100%.
Setting `optional: false` surfaces it as a real Tier-C gap and will lower the headline. Your call.

### Recommended follow-ups

1. **Promote `raw_text` beyond presence.** `presence_nonempty` cannot distinguish clean text from the
   OCR garbage in the worst-list. `m1/evaluation/raw_text.py` already implements CER/WER against
   transcribed gold pages — wire it in as the primary metric with presence as the fallback.
2. **Add `raw_text` to `xlsx_reader.CANONICAL_FIELDS`.** `resolve_field` is a correct safety net, but
   promoting the six stage-scoped fields to first-class canonical status removes the asymmetry at
   source instead of compensating for it downstream.
3. **Land the slice breakdowns**, prioritising the `extraction_method` dimension — it separates
   native-PDF from OCR and would have isolated the Sinhala/Tamil corruption immediately.
4. **Emit per-field confidence** from the extraction profile so the calibration plot becomes usable.

---

## Appendix — Files changed

| File | Change |
|---|---|
| `enigmatrix-ml/m1/evaluation/field_metrics.py` | `resolve_field` + `_extras` fallback; presence guard; `NON_ACCURACY_FIELDS`; `HEADLINE_EXCLUDED_FIELDS` |
| `enigmatrix-ml/m1/evaluation/aggregates.py` | `aggregate_overall` defaults to `HEADLINE_EXCLUDED_FIELDS` |
| `enigmatrix-ml/m1/evaluation/completeness.py` | `_is_present` → public `is_present` (alias retained) |
| `enigmatrix-ml/m1/evaluation/__init__.py` | export `NON_ACCURACY_FIELDS`, `HEADLINE_EXCLUDED_FIELDS`, `resolve_field` |
| `enigmatrix-ml/tests/evaluation/test_field_metrics.py` | 2 regression tests |
| `enigmatrix-backend/app/m1/services/snapshot_service.py` | emit 4 stage-scoped fields; datetime coercion |
| `enigmatrix-backend/app/m1/tasks/run_measurement.py` | promote `extraction_method` column |
| `enigmatrix-frontend/components/m1/measurement-dashboard/CalibrationPlot.tsx` | placeholder on zero plottable buckets |
| `data/golden/field_contract_v1.yaml` | `fill_rate` correction + `REVIEW:` note |
