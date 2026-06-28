# 14_M1_5 — SME Regulation Discovery

> Companion to [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) — covers tracking surface **S1: Regulation discovery (sector + region filter)**.
> **Implementation status:** 🟡 Partial — `/regulations` list + dashboard "Pending regulations" widget are shipped; the sector-applicability filter that the SME *would* expect is deferred.

## Purpose

An SME wants to answer: *which of the ~500 active regulations actually apply to my business?* Today the platform makes a partial answer — the dashboard's "Pending regulations" widget surfaces sector-relevant items via the backend filter (server-side join on `m1_regulation_sectors` and the SME's `primary_sector`). The full discovery surface (sticky filter rail, applicability score, "save filter" affordance) is deferred.

This companion documents both halves: the shipped widget + list, and the intended full discovery surface.

## Detailed process

### Today (✅ shipped)

1. **Open the dashboard.** `/dashboard`. The "Regulations awaiting your assessment" widget renders up to 3 `<RegulationCard>` instances (`components/surveys/regulation-card.tsx`) sourced from `GET /api/v1/dashboard/pending-regulations`.
2. **See what applies.** Each card shows: `regulation_short_code`, locale-aware title (with "Showing English" badge if SI/TA translation is missing), domain badge, severity badge, effective date. The card is clickable → routes to `/surveys/regulation/[id]`.
3. **"View all".** A small link → `/surveys?view=regulation` opens the surveys hub with the regulation-tab pre-selected. Shows every pending regulation, paginated.
4. **Browse the full list.** `/regulations` (separate route) shows every active regulation, not just pending. Used as a reference catalogue rather than a triage queue.

### Intended (🟡 partial — what's missing)

> 🔲 Intended workflow — sector-applicability filter design not yet locked.

1. **Sticky filter chip bar** at the top of `/regulations`: chips for `Sector = manufacturing`, `Region = Colombo`, `Status = applicable to me`, `Effective in next 30 days`, `Has my action?` Clicking a chip toggles it; chips reflect in the URL (`?sector=manufacturing&region=colombo&applicable=true`).
2. **Applicability score per row.** Each `<RegulationCard>` shows a small badge: `100 % applicable` (the SME's sector is in `affected_sectors` AND district matches), `50 % applicable` (sector match only), `10 %` (universal regulations that apply to all sectors). Computed client-side from the SME's profile + the regulation's `affected_sectors[]`.
3. **Sort options.** Newest, earliest effective date, severity DESC, "most relevant to me" (applicability × severity).
4. **Save filter.** Power-user feature: save a filter set to the SME's profile so it's pre-applied on next visit.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Dashboard widget (chosen) | One-glance recommendation | ✅ Shipped — top-of-page card on `/dashboard` | Never remove |
| Full `/regulations` list (chosen) | Browseable catalogue | ✅ Shipped — paginated table-cards hybrid | Never remove |
| Sector-applicability filter | Sharply narrows the list | 🟡 Target — backend supports it; UI deferred | Ship in BUILD_07 when sector-filter URL params are wired in the API client |
| Applicability score badge | Helps SMEs prioritise | 🟡 Target | Add when telemetry shows SMEs scroll the list without clicking |
| "Save filter" power-user feature | High value, low priority | ❌ Skip MVP | Add when ≥ 10 active SMEs request it |
| Client-side filtering | Snappy | ✅ Acceptable up to ~500 active regulations | If list grows past 1k rows, push filters server-side |

## Worked example

A retail SME's discovery flow (today):

```
Monday morning — SME opens /dashboard
Widget "Regulations awaiting your assessment" renders 3 cards:
  1. VAT_2024_AMD — VAT (severity 5, effective 2024-01-01)
  2. EPF_2024_RATE — EPF (severity 4, effective 2024-02-01)
  3. SLSI_ADAPTER — Product Standard (severity 3, effective 2026-08-01)

SME clicks card #1 → /surveys/regulation/VAT_2024_AMD-uuid → unified M1→M2→M3 wizard

(Later) SME wants the full list → clicks "View all" → /surveys?view=regulation
  sees the 3 cards above plus 2 more universal regulations
  no per-card "applies to me 100%/50%" badge yet (deferred)

(SME's actual flow ends here — 3-5 cards is enough.)
```

### Intended (🟡):

```
Same SME opens /regulations
Sticky filter bar pre-applies `sector = retail` + `applicable=true` from saved filter
  → list collapses from 47 active regulations to 12 retail-applicable
Each card shows applicability badge — 100 % for retail-specific, 50 % for cross-sector
Sort = "most relevant to me" → severity-weighted top first
Click card → same /surveys/regulation/[id] flow
```

## Failure modes & edge cases

- **SME has no `primary_sector`.** Brand-new SME with empty profile. Mitigation: the dashboard widget hides itself; the user is prompted to complete their profile (currently routes to `/profile`).
- **Cross-sector regulation (universal).** Applies to all 10 sectors — `affected_sectors` is the full list. Renders as "10 % applicable" today; future could be "applies to everyone" with a special badge.
- **Profile updated → cached widget stale.** SME changes sector; widget on dashboard might still show the old recommendations until next fetch. Mitigation: `react-query` invalidation on profile mutate (already in place per Session 13).
- **Empty pending list.** SME has surveyed everything; widget shows "All caught up — view all regulations →".
- **Trilingual list:** locale-aware title with EN fallback ("Showing English" badge when SI/TA missing). Existing pattern from [12_UI_Screens §3.5](../frontend/SETUP/12_UI_Screens_and_Loading.md).

## Validation & acceptance criteria

- **A11y.** Filter chips are keyboard-toggleable; chip state read aloud ("Sector retail, active filter").
- **Loading state.** Widget shows `<RegulationCardSkeleton>` placeholders while the dashboard's `Promise.all` fetches; full list shows `<AnimatedLoadingSkeleton>`.
- **Empty state.** Widget: "All caught up — view all regulations". List: per filter, a specific empty-state message + "Reset filters" button.
- **URL state.** Filters in URL so deep-links + back button work.
- **Translation fallback.** `<RegulationCard>` shows the "Showing English" badge when SI/TA title is empty; never crashes on a missing locale.
- **Sector match correctness.** When applicability badge ships, unit test asserts `100 %` only when SME's sector ∈ `affected_sectors` + district ∈ `affected_districts` (when present).

## Cross-references

- Parent: [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md)
- Screen reference: [12_UI_Screens_and_Loading.md §2 (dashboard widget) + §3.5 (/regulations list)](../frontend/SETUP/12_UI_Screens_and_Loading.md)
- Backend sectors schema: [02_M1_Data_Requirements.md §2.2](02_M1_Data_Requirements.md) (`m1_regulation_sectors` M2M)
- Backend dashboard endpoint: `GET /api/v1/dashboard/pending-regulations`
- BUILD phase: BUILD_07 (full sector filter), BUILD_13 (saved-filter feature)
- Code (shipped): `frontend/app/(app)/dashboard/page.tsx`, `frontend/app/(app)/regulations/page.tsx`, `frontend/components/surveys/regulation-card.tsx`
- Code (when deferred bits ship): `frontend/components/regulations/filter-chip-bar.tsx`, `frontend/components/regulations/applicability-badge.tsx`
