# 14_M1_1 — Admin Pipeline-State Tracking

> Companion to [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) — covers tracking surface **A1: Pipeline-state tracking (Stage A→F status machine per regulation)**.
> **Implementation status:** 🟡 Partial — status field exists on every regulation row; admin list surfaces it in the table; no dedicated stage-by-stage dashboard yet.

## Purpose

A regulation moves through six pipeline stages (`ingested → extracted → classified → summarized → alerted → archived`) defined in [m1/02_M1_Data_Requirements.md §2.1](02_M1_Data_Requirements.md). At any moment, an admin needs to answer: *which regulations are stuck mid-pipeline?* and *what stage is the bottleneck right now?* This tracking surface is the daily-triage entry point — what the admin opens first in the morning.

## Detailed process

Today the workflow runs through [`/admin/regulations`](../../../frontend/app/(admin)/admin/regulations) with the status surfaced as a column on the table.

1. **Open the regulation bank.** Navigate to `/admin/regulations`. The page renders a polished `<Table>` (per [12_UI_Screens §3.1](../frontend/SETUP/12_UI_Screens_and_Loading.md)) with per-row `status` rendered as a `<StatusBadge>` (`components/ui/status-badge.tsx` — colour-coded success / warning / pending / error / neutral).
2. **Filter by status.** Use the vertical filter rail on the left to apply `Status = "ingested"` (or any pipeline stage). The URL reflects the filter (`?status=ingested`). Sort by `created_at DESC` to see the most recent stuck items first.
3. **Inspect a single regulation.** Click a row → `/admin/regulations/[id]/edit`. The detail page shows the regulation's current stage in the header band + the next expected transition.
4. **Manual transition.** Where the admin can advance a stage manually (e.g. forcing a re-classify when the auto-pipeline is unhealthy), the action lives in the row's `<RowActions>` menu or as a primary button on the detail page.
5. **Bulk re-trigger** (advanced). For systemic issues — say, "yesterday's batch all stuck at `extracted` because the classifier was down" — the admin selects multiple rows + clicks "Re-classify selected" in the bulk-action bar. The action enqueues a Celery task per row (see [m1/03_M1_Data_Collection.md §6.1](03_M1_Data_Collection.md) for the Celery + Scrapy interaction).

> **🔲 Intended workflow — Stage Dashboard.** Once BUILD_13 ships the stage dashboard, an admin opens `/admin/m1/pipeline` for a Sankey-style view of how many regulations sit in each stage right now. Each block is clickable → filters the regulation list to that stage. Not yet built; this companion documents the *target*.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Status column on the existing `/admin/regulations` list (chosen) | Uses the regulation bank polish (filter rail, pagination, search) for free | ✅ Ship-fast — the column already exists | Once the regulation count exceeds ~500 active rows, a dedicated dashboard becomes more useful |
| Dedicated `/admin/m1/pipeline` Sankey-style dashboard | Best at-a-glance bottleneck view | 🔲 Deferred to BUILD_13 | After backend Stage A–F metrics are exposed in `m1_pipeline_audits` |
| Stage transitions as a separate `m1_regulation_stage_log` table | Audit-grade transition history | ❌ Audit log already captures every `status` field change — no new table needed | If we need ms-precision transitions for SLA reporting |
| Real-time push (websocket) of status changes | Live dashboard | ❌ Polling every 30s is sufficient for this workflow | If admins start reporting they want sub-second freshness |

## Worked example

A Monday-morning triage on a hypothetical overnight batch:

```
09:02 — admin opens /admin/regulations?status=ingested&sort=created_at:desc
         42 rows returned; all from the overnight Scrapy run; none have advanced
09:03 — admin spots that none reached "extracted" → Celery extraction worker is dead
09:04 — admin pages on-call (Slack #enigmatrix-ml); confirms Tesseract dependency missing
09:30 — on-call redeploys with the language pack; worker comes back up
09:35 — admin clicks "Refresh" → all 42 rows now at status="extracted"; 14 already at "classified"
09:40 — admin moves to the verification workflow (see 14_M1_3) for the 14 classified rows
```

The admin never had to write a SQL query — the table filter + status badges surface the bottleneck.

## Failure modes & edge cases

- **Status badge colour ambiguity.** `extraction_failed` and `extracted` could be confused at a glance. Mitigation: `StatusBadge` renders `extraction_failed` in `destructive` (red) and `extracted` in `pending` (amber). Visual hierarchy reinforced by an icon (X vs ⏳).
- **Stuck rows.** A regulation that has been at the same status > 24 h is *probably* stuck. Mitigation: when the stage-dashboard ships, rows older than the SLA flash an `<Alert>` (see [m1/12_M1_Monitoring_Maintenance.md §1](12_M1_Monitoring_Maintenance.md)).
- **Stale list during a Celery backlog.** A user mid-page might see counts shift under them as workers catch up. The admin list is `React Query`'s default `staleTime: 30s` — refresh button available in the topbar.
- **Archived rows.** `is_active=false` rows hide by default unless `?include_archived=true`. Admin can still filter to find them.

## Validation & acceptance criteria

- **A11y.** Status badges render an accessible label (`aria-label="Status: extraction failed"`) in addition to colour. Confirmed by axe-core CI sweep.
- **Loading state.** The table shows `<AnimatedLoadingSkeleton>` (chrome-stripped) inside the `<Table>` border during the first React Query fetch + on filter changes.
- **Empty state.** When the filter returns zero rows, show "No regulations match this filter" + a "Reset filters" button — not a blank table body.
- **Filter persistence.** Filters persist in the URL so the browser back button returns to the same view; refresh preserves the filter state.
- **Pagination state.** Page + page-size in the URL (`?page=2&size=50`) so deep-links work.

## Cross-references

- Parent: [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md)
- Screen reference: [12_UI_Screens_and_Loading.md §3.1](../frontend/SETUP/12_UI_Screens_and_Loading.md)
- Backend status enum: [02_M1_Data_Requirements.md §2.1](02_M1_Data_Requirements.md) (the 6 status values)
- Backend Celery transitions: [03_M1_Data_Collection.md §6.1](03_M1_Data_Collection.md)
- Monitoring of pipeline health: [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md)
- BUILD phase: BUILD_07 (backend Stage A–F), BUILD_13 (dedicated stage dashboard)
- Code: `frontend/app/(admin)/admin/regulations/page.tsx`, `frontend/components/ui/status-badge.tsx`
