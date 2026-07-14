---
tags: [m1, audit, ux, extraction, measurement, accuracy, upgrades]
date: 2026-06-30
author: Mohamed M.R.I (215075J) — Module 1 owner
session: 72
status: reference — audit + shipped upgrade (accuracy-report export)
feature: F-242
---

# Extraction + Measurement — UI/UX audit & upgrades

> Focused review of the **PDF extraction + accuracy-measurement** surface (the pipeline funnel, extraction runs, and the dataset/measurement comparison — the "verify extraction + measure its accuracy" features), with concrete upgrades.

## What's already strong (verified in code)
- **Measurement engine is mature.** `m1_measurement_aggregates` computes overall (mean primary score), per-field mean/median/CI + status counts (`exact/partial/mismatch/missing/extra`), per-regulation drill-in, and worst-N. The API exposes all of it (`/per-field`, `/regulations/{key}`, `/worst`, `/progress`, `/calibration`).
- **The funnel "7,700 %" bug is already fixed.** `components/m1-pipeline/funnel-chart.tsx` caps conversion at 100 %, anchors bar widths to the largest tier, and shows a ⚠ when a rate is > 95 % (data-inconsistency signal).
- **Confidence-aware calibration.** The calibration plot 404s when the candidate profile (e.g. `legacy_v1`) has no per-field confidence — hidden rather than misleading (per Alignment Audit §J).
- **Completeness "verify".** `m1_completeness_check` diffs the website listing vs the DB with retry/timeout handling and returns the missing rows.
- No `TODO/FIXME` left in the audited files.

## Shipped this session (F-242) — Accuracy-report export
A one-click **thesis artifact** was missing: the measurement data was viewable in the UI but not exportable.
- **`app/services/m1_measurement_report.py`** — pure `build_markdown_report()` (unit-tested): overall accuracy + a per-field table (mean/median/n + status breakdown) + worst offenders.
- **`GET /api/v1/m1/measurements/{run_id}/report.md`** — returns a downloadable Markdown report (`text/markdown`, `Content-Disposition: attachment`).
- **Test:** `app/tests/unit/test_m1_measurement_report.py` (pass).

**Frontend button (ready-to-paste; needs your env to verify):**
```tsx
// on the measurement dashboard page — a "Download report" button
async function downloadReport(runId: string, token: string) {
  const r = await fetch(`${API}/m1/measurements/${runId}/report.md`,
    { headers: { Authorization: `Bearer ${token}` } });
  const blob = await r.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `accuracy_report_${runId}.md`;
  a.click(); URL.revokeObjectURL(a.href);
}
```

## Prioritized upgrade recommendations (for your env)
| # | Upgrade | Area | Priority | Effort | Status |
|---|---|---|---|---|---|
| 1 | Exportable accuracy report (Markdown) | Backend + FE button | High | S | 🟢 backend shipped; FE button snippet above |
| 2 | CSV export of per-field + worst (for Excel/thesis) | Backend | High | S | 🔲 mirror the `.md` endpoint with `.csv` |
| 3 | "Extraction accuracy at a glance" badge on `/admin/m1/pipeline` overview (latest ground-truth run's overall %) | FE + BE | High | M | 🔲 |
| 4 | Per-field accuracy **trend across versions** (sparkline v1→v2→…) | FE | Medium | M | 🔲 (partial sparkline exists) |
| 5 | Empty states — no-measurement-yet / no-golden-dataset guidance with a CTA | FE | Medium | S | 🔲 |
| 6 | Accessibility — `aria-label`s on funnel bars + heatmap cells; keyboard nav for the per-field grid | FE | Medium | S | 🔲 |
| 7 | SI/TA i18n for the new dataset/measurement strings (currently EN + `[TODO]`) | FE | Medium | M | 🔲 |
| 8 | Surface **confidence / needs-review** on the pipeline once the classifier ships (3f) | FE + BE | Medium | M | 🔲 blocked on 3d/3f model |
| 9 | Extraction-run **diff view polish** — highlight changed characters in `trace-content-diff` | FE | Low | S | 🔲 |
| 10 | Downloadable **worst-offenders CSV** straight from the heatmap cell filter | FE + BE | Low | S | 🔲 |

## Notes
- The `/admin/m1/pipeline/recent` 503 is **environmental** (Railway cold-start / DB pool), already handled by `error.tsx` + a retry card — not a code defect (see Session 71).
- `app/api/v1/m1_measurements.py` carries pre-existing 3.11/3.12 syntax that a 3.10 interpreter can't parse (unrelated to this change) — run `ruff`/`py_compile` in the 3.11+ env to confirm the new endpoint.

## Cross-refs
`06_M1_2_Slice_Analysis_Framework.md` · Phase-2 Upgrade Plan slices 5–6 (measurement + comparison UI) · Session 53 pipeline UX audit.
