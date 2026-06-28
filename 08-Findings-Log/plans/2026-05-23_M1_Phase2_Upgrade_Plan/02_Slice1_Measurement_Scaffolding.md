---
tags: [m1, phase-2, slice-1, evaluation, golden-set, metrics]
date: 2026-05-23
status: 🔲 not started — recommended start point
estimated-effort: 1 week (4–6 focused days)
prerequisites: manual Excel (~400 regulations) exists and is column-clean
---

# 02 — Slice 1: Measurement Scaffolding and Golden-Set Lock

## What this slice produces

A new Python package `enigmatrix-ml/m1/evaluation/` containing the field-metric registry, four working metric families (string-similarity, semantic, date, categorical), one CLI script (`scripts/run_baseline_measurement.py`), and a JSON scorecard at `data/eval/baseline_v0.json` that scores the current `m1_regulations` table against the manually-curated Excel.

When this slice is done you can answer the question *"how good is `legacy_v1` against ground truth on the 16 structured fields we care about?"* with a single number per field plus a single overall number. That number is the row labelled "Phase 1 baseline" in every accuracy chart you produce from now until the end of the thesis.

## Why this is slice 1

Two reasons. First, vocabulary needs to be locked before slices 3–7 reference field names — pinning the canonical name set once here prevents `title_si` vs `title_sinhala` divergence later. Second, every later slice claims to improve accuracy; you cannot claim improvement without a fixed baseline.

## Inputs

- The manual Excel (`Module 1 master.xlsx` or equivalent). Located at `C:\sme\_Attachments\` ideally; if not, copy it there first so the vault carries the source-of-truth blob.
- The 16 canonical field names (pinned in this slice — see § canonical fields below).
- The existing `m1_regulations` table.

## Tasks

### Task 1.1 — Audit and canonicalise the Excel (½ day)

Open the Excel. Verify:

- A column exists for the regulation key (gazette number). If the header is "Gazette No." or "Reg. No." or anything else, rename to `regulation_key`.
- Every row has a non-empty `regulation_key` matching the pattern `^\d+/\d+$` (e.g. `2468/44`). Quarantine rows that don't.
- The 16 fields listed below are present (rename Sinhala/Tamil column headers as needed). Missing columns are added empty.

**Canonical field names** (pin these now; everything downstream uses them):

| Field | Type | Example value |
|---|---|---|
| `regulation_key` | string | `2468/44` |
| `document_type` | enum | `extraordinary_gazette` |
| `document_number` | string | `31/2026` |
| `title_en` | string | "Value Added Tax (Amendment) Order — 2026" |
| `title_si` | string | "එකතු කළ අගය මත බදු (සංශෝධන) නියෝගය — 2026" |
| `title_ta` | string | "மதிப்பு கூட்டப்பட்ட வரி (திருத்தம்) ஆணை — 2026" |
| `summary_en` | string | (1–3 sentence plain-language summary) |
| `summary_si` | string | (same, Sinhala) |
| `summary_ta` | string | (same, Tamil) |
| `principal_act_amended` | string | "Value Added Tax Act, No. 14 of 2002" |
| `gazette_published_date` | ISO date | `2026-04-15` |
| `effective_date` | ISO date | `2026-05-01` |
| `domain_code` | enum | `tax` |
| `change_category` | enum | `amendment` |
| `severity_level` | int 1–4 | `3` |
| `is_sme_relevant` | bool | `TRUE` |
| `penalty_range_lkr` | string range | `50,000 – 500,000` |
| `amendment_type` | enum | `amendment` / `repeal` / `new_act` |
| `real_world_example_en` | string | (free-text scenario; nullable) |
| `real_world_example_si` | string | nullable |
| `real_world_example_ta` | string | nullable |

Save the canonicalised file as `data/golden/structured_v1.xlsx` in the repo and `_Attachments/structured_v1.xlsx` in the vault. Compute SHA-256, write to a sidecar `structured_v1.xlsx.sha256` file.

### Task 1.2 — Scaffold `enigmatrix-ml/m1/evaluation/` (½ day)

Create the package:

```
enigmatrix-ml/m1/evaluation/
├── __init__.py            # public surface
├── field_metrics.py       # FIELD_METRICS dict (the registry)
├── metrics/
│   ├── __init__.py
│   ├── strings.py         # normalized_exact_match, token_set_ratio, char_f1
│   ├── semantic.py        # labse_cosine, bertscore_f, bertscore_f_labse
│   ├── dates.py           # date_exact_match, date_within_tolerance_7d
│   ├── categorical.py     # categorical_exact, ordinal_within_one, boolean_exact
│   ├── numeric.py         # numeric_range_iou, log_mae_on_midpoint
│   └── text_summary.py    # rouge_l_f
├── completeness.py        # compute_status(baseline, candidate) -> {exact,partial,mismatch,missing,extra}
└── types.py               # Score dataclass + MetricResult dataclass
```

Each metric function is a pure function `(baseline_value, candidate_value) -> float` returning a score in `[0, 1]` (or `NaN` if undefined for the pair). Each metric carries a `version` constant (`__version__ = "1.0.0"`) used by the measurement engine in slice 5 to mark scored rows.

Dependencies added to `enigmatrix-ml/pyproject.toml`:

```toml
[project.optional-dependencies]
evaluation = [
    "jiwer>=4.0,<5",
    "sentence-transformers>=3.0.1,<4",
    "bert-score>=0.3.13,<0.4",
    "rouge-score>=0.1.2,<0.2",
    "rapidfuzz>=3.9.7,<4",
    "torch>=2.2,<3",  # cpu-only is fine for slice 1
]
```

Install with `uv sync --extra evaluation` at repo root.

### Task 1.3 — Implement the field metric registry (1 day)

Build `field_metrics.py` exactly as specified in `04_Measurement_Engine_and_UI.md §The per-field metric registry`, with the following corrections / additions:

- Each entry is `(metric_callable, threshold, metric_version)` — the version is new vs the upload.
- Add `regulation_key`, `document_type`, `document_number` to the registry with `(normalized_exact_match, 1.0, "1.0.0")` as the only metric (they are identifiers; partial match makes no sense).
- For the `gazette_published_date` field, the threshold is genuinely `1.0` (the publication date is observable; off-by-one means the extraction is reading the wrong field).
- For `effective_date`, the upload's `(date_within_tolerance_7d, 0.95)` is right because the effective date is sometimes inferred from "ten days after publication" text.

Unit-test each metric in `enigmatrix-ml/tests/evaluation/test_metrics.py`. For each metric, write 3 cases: an exact-match input (should return ≥ threshold), a clear-mismatch input (should return < threshold), an empty / None input (should return `NaN` and not crash). LaBSE and BERTScore tests can be marked `slow` so CI doesn't load the 1.5 GB model on every run.

### Task 1.4 — Implement completeness logic (½ day)

`completeness.py`:

```python
def compute_status(
    baseline: Any, candidate: Any, *, primary_score: float | None, threshold: float
) -> Literal["exact","partial","mismatch","missing","extra"]:
    base_present = baseline not in (None, "", [])
    cand_present = candidate not in (None, "", [])
    if not base_present and not cand_present:
        return "exact"  # omit-from-scorecard handled by caller
    if base_present and not cand_present:
        return "missing"
    if cand_present and not base_present:
        return "extra"
    # both present
    if primary_score is None:
        return "mismatch"
    if primary_score >= threshold:
        return "exact"
    if primary_score >= 0.5:
        return "partial"
    return "mismatch"
```

Unit tests in `tests/evaluation/test_completeness.py` cover the five status outputs with one input each.

### Task 1.5 — Write `scripts/run_baseline_measurement.py` (1 day)

This is a standalone script (not yet a Celery task — slice 5 wires the Celery side). It:

1. Reads the canonicalised Excel from `data/golden/structured_v1.xlsx` and converts to a `dict[regulation_key] -> dict[field -> value]`.
2. Connects to the dev/prod DB via the same `app.db` session machinery the backend uses.
3. Reads `m1_regulations` for every row that exists in the Excel (left join, so Excel-only rows yield `missing` everywhere, DB-only rows are skipped because we don't yet have a "baseline" to score them against).
4. For each `(regulation_key, field, metric)`, runs the metric, records the score, status, and raw values.
5. Aggregates by field and overall.
6. Writes `data/eval/baseline_v0.json` with:

```json
{
  "schema_version": "1.0",
  "baseline_source": "structured_v1.xlsx",
  "baseline_sha256": "...",
  "candidate_source": "m1_regulations @ <git_sha>",
  "candidate_sample_size": 384,
  "overall_score": 0.71,
  "per_field": {
    "title_en": {"primary_metric": "normalized_exact_match", "mean": 0.91, "status_counts": {...}},
    "title_si": {"primary_metric": "char_f1", "mean": 0.34, "status_counts": {...}},
    ...
  },
  "completeness_summary": {...},
  "scored_at": "2026-05-26T14:32:00Z"
}
```

The script also writes the per-row detail to `data/eval/baseline_v0_rows.csv` for spot-checking.

### Task 1.6 — Lock the golden as `structured_v1` (½ day)

The golden file is **never edited in place after this point**. If you find a typo in row 87, you copy `structured_v1.xlsx` → `structured_v2.xlsx`, edit the copy, recompute the SHA, and update the script to read from v2. Every accuracy claim cites the version of the golden it was scored against.

Document this rule in `data/golden/README.md`.

## Files touched

| Path | New/Edit | Purpose |
|---|---|---|
| `data/golden/structured_v1.xlsx` | new | Canonicalised manual Excel |
| `data/golden/structured_v1.xlsx.sha256` | new | Lock file |
| `data/golden/README.md` | new | Conventions for the golden set |
| `enigmatrix-ml/m1/evaluation/**` | new | The evaluation package |
| `enigmatrix-ml/tests/evaluation/**` | new | Unit tests |
| `enigmatrix-ml/pyproject.toml` | edit | Add `[evaluation]` extra |
| `scripts/run_baseline_measurement.py` | new | Standalone baseline script |
| `data/eval/baseline_v0.json` | new (output) | The locked baseline |

## Gate (proves the slice works)

1. `uv run pytest enigmatrix-ml/tests/evaluation/ -v` — all metric tests pass.
2. `uv run python scripts/run_baseline_measurement.py` — completes without errors, writes `data/eval/baseline_v0.json`.
3. The JSON has `overall_score` as a real number (not NaN), and `per_field` has 16+ entries with non-null `mean`.
4. **Honesty check:** open `baseline_v0_rows.csv`, pick five rows, eyeball the scores against your gut. Sinhala titles where the extraction has `(cid:...)` markers should score very low. English titles for cleanly-extracted Phase-1 gazettes should score very high. If the script disagrees with your eye, the metric is broken — investigate before declaring the slice green.

## What this slice deliberately does NOT do

- It does NOT add the `m1_datasets` table (that's slice 3).
- It does NOT make `legacy_v1` selectable from a UI dropdown (slice 4).
- It does NOT add the comparison view (slice 6).
- It does NOT touch the Celery infra (slice 5 introduces the measurement task).
- It does NOT change Phase 1 code paths.

The script is a stepping stone, not the final form. Slice 5 takes its logic and wraps it in `run_measurement` so the same scoring runs from the UI.

## Risks specific to this slice

- **LaBSE model size on local dev (~1.5 GB).** Mitigation: load lazily, document the disk requirement in `data/golden/README.md`, mark BERTScore/LaBSE tests `@pytest.mark.slow`. Pin the checkpoint hash so CI is deterministic.
- **Excel parsing edge cases.** Mitigation: log every row that fails Pydantic validation; don't abort the script. Validation warnings end up in the JSON output's `validation_warnings` array.
- **Vocabulary drift later.** If a later slice wants to add a 17th field (e.g. `gazette_date_si_local` for Sri Lankan calendar), it bumps `golden` to `structured_v2` and re-runs baseline. The original baseline number stays valid — it scored 16 fields.

## What ships into the thesis from this slice

The `baseline_v0.json` overall score becomes a row in Chapter 4 Table 4.1 ("Phase-1 baseline score against manual ground truth"). Every subsequent profile is reported as a delta against this row.

## Cross-references

- [01_Alignment_Audit §F](01_Alignment_Audit.md#f-i18n-🟡-convention-drift) — no UI strings in this slice, so i18n N/A here.
- [04_Slice3_Dataset_Registry_and_Upload](04_Slice3_Dataset_Registry_and_Upload.md) — slice 3 will store this same Excel inside `m1_dataset_rows`. Once that's done, the script becomes redundant and the Celery task in slice 5 takes over.
- `enigmatrix-ml/m1/extraction/__init__.py` — canonical extraction public surface (referenced for vocabulary consistency).
- `enigmatrix-docs/m1/02_M1_4_Worked_Examples_All_Tables.md` — multi-pin-adapter worked example. Use it as a Sinhala-heavy reference row when eyeballing baseline scores.
