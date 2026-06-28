---
tags: [m1, phase-2, slice-6, frontend, comparison, dashboard, ux]
date: 2026-05-23
status: 🔲 not started
estimated-effort: 1 week
prerequisites: slice 5 (every endpoint to consume)
---

# 07 — Slice 6: Comparison UI and Measurement Dashboard (Frontend)

## What this slice produces

Three new frontend page families under `/admin/m1/measurements/`:

1. `/admin/m1/measurements` — the runs list (table + filters + "Run new" button).
2. `/admin/m1/measurements/{run_id}` — the per-run dashboard (KPI cards, heatmap, slice breakdown, worst-N, calibration plot).
3. `/admin/m1/measurements/{run_id}/regulations/{regulation_key}` — the per-regulation side-by-side comparison view.

When this slice ships, the daily debugging workflow becomes visual: pick a measurement run, scan the heatmap to find the worst field, click into a worst-N row, see the per-regulation diff, identify the failure mode, decide which profile or metric needs work.

## The three pages

### Page 6.A — Runs list (`/admin/m1/measurements/page.tsx`)

Simple table. Columns:

| Created | Baseline | Candidate | Overall | Status | Actions |
|---|---|---|---|---|---|
| 2026-05-26 14:32 | Manual ground truth v1 | legacy_v1 extraction v3 | 0.71 | ✅ complete | View / Re-run |

Filters: by baseline dataset (chip), by candidate dataset (chip), by status (chip), by extraction profile of candidate (chip).

"Run new measurement" button at top right opens a modal with two version pickers (defaults: baseline = current ground-truth version, candidate = most-recent extraction-run version), then POSTs to `/measurements/run` and redirects to the run page.

### Page 6.B — Per-run dashboard (`/admin/m1/measurements/[runId]/page.tsx`)

Five sections, vertically stacked:

**Section 1 — Header strip.** Run id, baseline label, candidate label, overall score in a big number, regulation count, started/completed timestamps, status badge.

**Section 2 — KPI cards row.** Four cards: overall score (big number with sparkline if history exists), total regulations, % with ≥ 1 mismatch, % with `missing` or `extra` worst-field status.

**Section 3 — Per-field heatmap.** A `Recharts`-based composed chart. Rows = field names, columns = `{exact, partial, mismatch, missing, extra}` count + `primary_metric_mean` (the 6th column). Cells coloured green-to-red gradient on the count's share of total regulations. Click a cell → opens a filtered worst-N panel.

**Section 4 — Slice breakdowns.** Small bar charts in a horizontal grid: by `document_type`, by `primary_language` (eng/sin/tam/mixed), by `year_bucket` (2018–2020, 2021–2023, 2024–2026), by `source_id`, by `extraction_method`. Each bar is clickable and filters the page.

**Section 5 — Worst-twenty list.** A table of the 20 lowest-scoring regulations with link to the per-regulation page.

**Section 6 (conditional) — Calibration plot.** Renders only when the candidate version has ≥ 1 row with non-null `confidence`. The plot is a 15-bin reliability diagram with ECE in the caption. When the conditional is false (legacy_v1 case), renders a placeholder card:

> *"Calibration plot unavailable — the candidate profile (`legacy_v1`) does not produce per-field confidence scores. Profiles `page_routing_v1`, `wijesekara_routing_v1`, and `surya_fallback_v1` (slice 7) will populate this section."*

**Section 7 — Profile-delta block (conditional).** Renders only when this run's candidate and *another existing run's* candidate were measured against the same baseline. Shows a "compare against" dropdown listing those other runs; selecting one renders a per-field delta table with paired Wilcoxon p-values.

### Page 6.C — Per-regulation comparison (`/admin/m1/measurements/[runId]/regulations/[key]/page.tsx`)

The debugging workhorse. Two-column layout:

```
┌─ Header ─────────────────────────────────────────────────────────┐
│ Gazette 2468/44  · 4 pages · published 2026-04-15                │
│ Baseline: Manual GT v1  ·  Candidate: legacy_v1 extraction v3    │
│ Score for this reg: 0.41                                          │
│ [Open original PDF] [Re-extract this reg] [Pair version dropdown] │
└──────────────────────────────────────────────────────────────────┘

┌─ Field-by-field ─────────────────────────────────────────────────┐
│ Field                  Baseline                Candidate         │
│ title_en               "Value Added Tax …"     —                  missing
│ title_si               "එකතු කළ අගය …"          "(cid:675)(cid:8113)…"   mismatch (0.04)
│ summary_en             "This amendment…"        —                  missing
│ effective_date         2026-05-01               2026-05-01         exact (1.00)
│ amendment_type         amendment                amendment          exact (1.00)
│ penalty_range_lkr      "50,000 – 500,000"      "50,000 – 500,000"  exact (1.00)
│ …                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

Each row is collapsible. Expanded view shows:
- All metrics that ran (`char_f1=0.04`, `labse_cosine=0.12`, with versions).
- Thresholds.
- Diagnostic JSON (`{"cid_marker_count": 482}`).
- Per-field error signals (e.g. "field was extracted from Wijesekara-converted text" or "field was inferred from heading regex").

Toolbar:
- Checkbox "Show only mismatches and missing" — hides exact/partial rows.
- Toggle "Authoritative view" — switches to a non-admin-style read showing only the baseline.
- "Re-extract this regulation" — opens slice-4's extraction form pre-filled with this regulation_key + a profile picker.
- "Open original PDF" — links to the source PDF via `m1_pdf_resolver`.

A "Pair version dropdown" lets the user switch the candidate version on the fly (e.g. compare baseline vs `legacy_v1` then quickly flip to `wijesekara_routing_v1` on the same regulation). The dropdown is sourced from `GET /measurements?baseline_version_id=<this run's baseline>` and lists every other measurement run that shared the same baseline.

## Tasks

### Task 6.1 — Set up the route group (½ day)

Create the folder structure:

```
enigmatrix-frontend/app/(app)/admin/m1/measurements/
├── page.tsx                                          (runs list)
├── new/page.tsx                                      (modal-as-page fallback for the "Run new" action)
├── [runId]/page.tsx                                  (dashboard)
└── [runId]/regulations/[regulationKey]/page.tsx      (comparison view)
```

Add the route to the admin sidebar nav config in `lib/vault/nav-config.ts` (added in Session 57 / F-193). Place it under the "M1" group, after "Pipeline" and "Extractions".

### Task 6.2 — API client (½ day)

`enigmatrix-frontend/lib/api/m1-measurements.ts`. Typed wrappers around all eight endpoints from slice 5. Reuses `getAccessToken` (god node per graph) and the existing `apiClient` base. Errors thrown as `ApiError` per the existing pattern.

### Task 6.3 — Build page 6.A: runs list (½ day)

- `data-table` component (already exists in `components/ui`) for the table.
- `Badge` for status.
- A modal triggered by "Run new measurement" that contains two `<Select>` populated by `GET /m1/datasets/{id}/versions` for sealed versions of each kind. Defaults to current ground-truth and most recent extraction.
- POST to `/measurements/run`, capture run_id, redirect.

### Task 6.4 — Build page 6.B: dashboard (2 days)

This is the biggest visual piece. Build each section as a separate component in `components/m1/measurement-dashboard/`:

- `KpiCards.tsx`
- `FieldHeatmap.tsx` — Recharts `<ScatterChart>` with custom cell shape, or `<ComposedChart>` with a custom layer; alternatively a hand-coded SVG grid since it's a heatmap not a standard chart.
- `SliceBreakdowns.tsx` — five small `<BarChart>` components in a `<Grid>`.
- `WorstNList.tsx` — table of 20 worst.
- `CalibrationPlot.tsx` — `<LineChart>` for the reliability diagram + a `<ScatterChart>` overlay for bin observations. 404 from the API → placeholder card.
- `ProfileDeltaPanel.tsx` — conditional, fetches a sibling measurement run, shows the delta table.

Each component fetches via TanStack Query. The dashboard page polls `GET /measurements/{id}/progress` every 5 s while `status='pending'` or `'running'`, then stops polling once `complete`.

### Task 6.5 — Build page 6.C: comparison view (1½ days)

- `FieldComparisonTable.tsx` — the field-by-field table with the collapsible rows.
- `StatusBadge.tsx` — green / yellow / red / gray / blue badge with the threshold-vs-score tooltip.
- `FieldExpandedDetail.tsx` — the expanded row content (all metrics + diagnostic JSON).
- `ComparisonToolbar.tsx` — the toolbar.
- `PairVersionDropdown.tsx` — fetches sibling runs sharing the same baseline, lets the user switch the candidate.

Sinhala / Tamil rendering: the comparison cells use `font-noto-sans-sinhala` / `font-noto-sans-tamil` Tailwind classes from `app/globals.css` (Session 4 / F-23). The cells are `whitespace-pre-wrap break-words` so long CID-corrupted titles don't break the layout.

### Task 6.6 — i18n strings (½ day)

`frontend/messages/{en,si,ta}.json` — add ~50 keys under `m1.measurements.*`:

```json
{
  "m1.measurements.list.title": "Measurement runs",
  "m1.measurements.list.runNew": "Run new measurement",
  "m1.measurements.dashboard.kpi.overall": "Overall score",
  "m1.measurements.dashboard.calibration.unavailable": "Calibration plot unavailable — the candidate profile does not produce per-field confidence scores.",
  "m1.measurements.comparison.status.exact": "Exact",
  "m1.measurements.comparison.status.partial": "Partial",
  "m1.measurements.comparison.status.mismatch": "Mismatch",
  "m1.measurements.comparison.status.missing": "Missing",
  "m1.measurements.comparison.status.extra": "Extra",
  ...
}
```

EN ships first. SI / TA can land with English placeholders if native speakers aren't immediately available; a follow-up sweep is fine.

### Task 6.7 — Playwright tests (½ day)

`frontend/tests/admin-m1-measurements.spec.ts`:

1. Log in as admin.
2. Navigate to `/admin/m1/measurements`.
3. Click "Run new". Modal opens. Pick baseline + candidate. Submit.
4. Land on dashboard, polling visible.
5. Wait for `status=complete` (mock the API in the test env to short-circuit).
6. Assert KPI cards, heatmap, worst-N list all visible.
7. Click `2468/44` from worst-N list.
8. Land on comparison view. Assert the `title_si` row shows status `mismatch`.
9. Click the toggle "Show only mismatches and missing". Assert `exact` rows are hidden.

## Files touched

| Path | New/Edit | Purpose |
|---|---|---|
| `enigmatrix-frontend/app/(app)/admin/m1/measurements/page.tsx` | new | Runs list |
| `enigmatrix-frontend/app/(app)/admin/m1/measurements/new/page.tsx` | new | Fallback modal-as-page |
| `enigmatrix-frontend/app/(app)/admin/m1/measurements/[runId]/page.tsx` | new | Dashboard |
| `enigmatrix-frontend/app/(app)/admin/m1/measurements/[runId]/regulations/[regulationKey]/page.tsx` | new | Comparison |
| `enigmatrix-frontend/components/m1/measurement-dashboard/*.tsx` | new | 6 dashboard components |
| `enigmatrix-frontend/components/m1/measurement-comparison/*.tsx` | new | 5 comparison components |
| `enigmatrix-frontend/lib/api/m1-measurements.ts` | new | API client |
| `enigmatrix-frontend/lib/vault/nav-config.ts` | edit | Sidebar nav entry |
| `enigmatrix-frontend/messages/{en,si,ta}.json` | edit | i18n |
| `enigmatrix-frontend/tests/admin-m1-measurements.spec.ts` | new | E2E |

## Gate

End-to-end:

1. From the runs list, click "Run new", pick the manual GT + legacy_v1 extraction → land on dashboard.
2. Once complete, the heatmap visibly shows `title_si` as red, `effective_date` as green.
3. Click the `title_si` cell → worst-N opens filtered to title_si mismatches.
4. Click `2468/44` → comparison view shows the CID-corrupted candidate title with a `mismatch` badge.
5. The "Calibration plot unavailable" card renders (because candidate is `legacy_v1`).
6. Repeat the flow but with a candidate from `wijesekara_routing_v1` (after slice 7 ships) → calibration plot now renders with bins.

## What this slice deliberately does NOT do

- It does NOT add an admin "edit metric registry" UI — the registry is code-only (slice 1).
- It does NOT add a CSV exporter UI button — but the backend endpoint exists (`GET /scores?format=csv`) and `curl` works.
- It does NOT animate transitions between heatmap cells (decorative; defer).

## Risks specific to this slice

- **Heatmap legibility on small screens.** Mitigation: heatmap renders as a vertical-scroll table on screens < lg; the visual encoding is still colour gradient + numeric value.
- **Recharts performance with 400 regulations × 16 fields = 6 400 cells.** Mitigation: the heatmap is aggregated to 16 rows × 6 columns (not per-regulation), so it's only 96 cells. The worst-N list caps at 20.
- **Sinhala / Tamil font fallback on first load.** Mitigation: `next/font` preloads the Noto Sans Sinhala and Tamil subsets at the layout level (already done in Session 4 / F-23).
- **Pair-version dropdown noise** (every measurement run ever, even noisy slice-7 experiments). Mitigation: filter to runs in the last 30 days by default + a "show all" toggle.

## Cross-references

- [06_Slice5_Measurement_Engine](06_Slice5_Measurement_Engine.md) — the endpoints this slice consumes.
- [08_Slice7_New_Extraction_Profiles](08_Slice7_New_Extraction_Profiles.md) — populates the calibration plot once it ships.
- [01_Alignment_Audit §G](01_Alignment_Audit.md#g-progress-ui-sse-not-polling-from-scratch-🟢-refinement), [§F](01_Alignment_Audit.md#f-i18n-🟡-convention-drift), [§J](01_Alignment_Audit.md#j-confidence-scoring-for-legacy_v1-🟢-refinement) — the upgrades this slice implements.
- Session 57 / F-193 — `lib/vault/nav-config.ts` is where the new admin nav entry lives.
