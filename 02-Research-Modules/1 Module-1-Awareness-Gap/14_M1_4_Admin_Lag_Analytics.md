# 14_M1_4 — Admin Lag Analytics + Propagation Tracker

> Companion to [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) — covers tracking surface **A4: Lag analytics dashboard + propagation tracker**.
> **Implementation status:** 🔲 Deferred — backend ingests `m1_propagation_events` rows on every channel observation and exposes them via `/api/v1/m1/analytics/lag` + `/api/v1/m1/analytics/channel-effectiveness`, but no admin UI consumes them. This companion describes the intended dashboard.

## Purpose

The four lag findings F1–F4 ([m1/08_M1_1_Research_Findings_Extraction.md](08_M1_1_Research_Findings_Extraction.md)) are the platform's empirical research contribution. The admin lag dashboard is the *operational* surface for the same data: per-channel median lag, propagation traces per regulation, drill-down into which regulations are missing channel coverage, and trend lines week-on-week.

The dashboard is the deferred surface that, once shipped, lets the project answer in 30 seconds questions that today require a Jupyter notebook session.

## Detailed process

> 🔲 Intended workflow — design not yet locked.

### Entry point — `/admin/m1/analytics`

The page opens to four cards stacked top-to-bottom, designed to answer the four findings F1–F4 in order:

1. **Card 1 — Median lag by channel (F1 + F2).** A horizontal bar chart with one bar per channel, sorted ascending by median lag. Channel groups: `portal_*` (government portals), `news_*` (RSS news outlets), `alert_delivery` (Enigmatrix alerts as comparison), `government_sms` (when available). Y-axis = channels, X-axis = lag days. Click a bar → drill into the per-regulation lag table for that channel.

2. **Card 2 — SME awareness lag (F3).** Same bar shape but per district (`urban / peri-urban / rural`) with sub-bars per sector. Drill-down → respondent-level (anonymised) lag table.

3. **Card 3 — Channel effectiveness ranking (F4).** A ranked table of channels with columns: rank, channel, p50 lag, p95 lag, sample size, weekly change (▲/▼). The header has a toggle: "this week" vs "this month" vs "all time".

4. **Card 4 — Propagation tracker (per regulation).** A search-pickable per-regulation timeline view. Pick a regulation → see a horizontal timeline with each channel's `first_seen_at` plotted, plus the SME-awareness-survey responses overlaid. The visualisation is what the M1 backend docs call the "T0–T9 diffusion timeline" from [m1/01_M1_Research_Problem.md §8](01_M1_Research_Problem.md).

### Filter controls (top of page)

- Time range: last 7 days / 30 days / quarter / all
- Sector filter (multi-select)
- Category filter (multi-select)
- Verified-only toggle (excludes `expert_verified=false` rows from analytics)

### Drill-downs

Every chart is clickable → opens a slim `<Sheet>` with the underlying data table + a CSV export button. The CSV exports the same data the research notebooks consume.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Dedicated `/admin/m1/analytics` page (chosen target) | Single surface for all 4 findings | 🔲 Target — BUILD_13 | If analytics use becomes a daily power-user workflow, split into per-finding pages |
| Recharts as chart library | Already in the stack (used in `/risk` per [12_UI_Screens §2](../frontend/SETUP/12_UI_Screens_and_Loading.md)) | ✅ Recharts | If we need draggable / zoom-able timelines, evaluate Visx or D3 directly |
| Server-rendered cards with `loading.tsx` streaming | Each card streams independently | ✅ Streaming | If a card becomes interactive (filter that reshapes the chart), client-side |
| CSV export per drill-down | Reproducibility for thesis | ✅ Ship — small effort, large value | Never remove |
| Live (web-socket) updates | Always-fresh dashboard | ❌ Not needed — propagation data refreshes hourly | If admins request sub-minute freshness |
| Per-channel sparkline weeks (mini-trend) | Adds noise at MVP | ❌ Skip MVP; add post-launch if requested | After 3 months of production data |

## Worked example

A research-finding spot-check (intended):

```
Quarterly review — admin opens /admin/m1/analytics
Filter: last quarter, verified-only

Card 1 (median lag by channel) shows:
  alert_delivery       0.3 days     ◄═══════
  government_sms       1.0 days     ◄════════════
  portal_ird           5.2 days     ◄═══════════════════
  portal_epf           7.1 days     ◄═══════════════════════
  news_daily_ft       22.5 days     ◄═══════════════════════════════════
  news_lankadeepa     27.0 days     ◄═══════════════════════════════════════
  news_virakesari     31.8 days     ◄══════════════════════════════════════════
  peer_referral       48.2 days     ◄══════════════════════════════════════════════

Card 4 (propagation tracker) — admin picks VAT_2024_AMD:
  gazette         | 2024-01-01 (T0)
  portal_ird      | 2024-01-09 (+8 days)
  news_daily_ft   | 2024-01-23 (+22)
  news_lankadeepa | 2024-02-03 (+33)
  sme_aware_50pct | 2024-02-18 (+48)
  alert_delivery  | 2024-01-01 (+0 — same-day to subscribed SMEs)

Click portal_ird bar → drill table shows all 27 regulations seen on the IRD portal last quarter
  Sortable by lag DESC → identifies 3 regulations the IRD took > 14 days to post
  CSV export → feeds the F1 thesis chapter
```

The dashboard makes the same numbers the research notebook computes available without a notebook context-switch.

## Failure modes & edge cases

- **Cold start with no data.** Pre-BUILD_07, `m1_propagation_events` is empty. Page renders empty states: "Propagation data starts arriving when BUILD_07 ships the ingestion pipeline".
- **One channel dominates.** If 90 % of observations are `alert_delivery`, the channel-effectiveness ranking is degenerate. Mitigation: minimum sample size 30 per channel before it appears in the table.
- **Time-zone confusion.** All `first_seen_at` timestamps are stored in UTC; rendered in Asia/Colombo by default. Filter date inputs in IST; round to local day boundaries. Documented at the bottom of the page in fine print.
- **Slow query on large windows.** Quarter-range filter on 100k+ events is slow without DB indexes. Mitigation: indexes pre-created per [m1/02_M1_Data_Requirements.md §2.10](02_M1_Data_Requirements.md); query timeout 30 s; pagination on drill-down tables.
- **CSV export of PII-adjacent data.** Per-respondent F3 drill-down. Mitigation: respondent identifiers are hashed in the CSV (`sme_profile_id` → anonymised); sector + district preserved.

## Validation & acceptance criteria

- **A11y.** Every chart has a table-mode toggle (visible table beneath the chart), readable by screen readers; bars have `aria-label` describing channel + value.
- **Loading state.** Each card streams via `loading.tsx`; `<AnimatedLoadingSkeleton>` while data fetches.
- **Empty state.** Per card, per drill-down — never blank canvas.
- **CSV format.** UTF-8, RFC 4180 quoted, columns documented in the page footer.
- **Sample-size disclaimers.** Any chart with N < 30 per slice renders an amber "low-confidence" banner referencing [m1/08_M1_1_Research_Findings_Extraction.md](08_M1_1_Research_Findings_Extraction.md).
- **Filter persistence.** All filters in URL state for shareable deep-links.

## Cross-references

- Parent: [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md)
- Backend findings + statistical tests: [08_M1_1_Research_Findings_Extraction.md](08_M1_1_Research_Findings_Extraction.md)
- Backend lag views: [02_M1_Data_Requirements.md §3.3](02_M1_Data_Requirements.md) (`v_m1_regulation_lag_summary`, `v_m1_channel_effectiveness`)
- Backend monitoring of lag pipeline: [12_M1_Monitoring_Maintenance.md §5](12_M1_Monitoring_Maintenance.md)
- BUILD phase: BUILD_13 §lag dashboard, BUILD_12 §schedulers (the nightly view refresh feeding this UI)
- Code (when shipped): `frontend/app/(admin)/admin/m1/analytics/page.tsx`, `frontend/components/analytics/*`
