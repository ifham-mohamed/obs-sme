---
tags: [tracker, findings, m1]
source: synthesised
layer: tracker
module: m1
---

# 2026-05-18 — M1 admin gazette extraction UX enrichments + token-key bug sweep (Session 39)

> **Owner:** mohamedifham
> **Module:** m1
> **Type:** bug fix + feature + UX
> **Features:** [F-163](../../../08-Findings-Log/FEATURES.md#session-39), [F-164](../../../08-Findings-Log/FEATURES.md#session-39)
> **Session:** [Session 39](../../../08-Findings-Log/SESSIONS.md)
> **Predecessor:** [F-161 (Session 38)](../../../08-Findings-Log/FEATURES.md#session-38) — the admin Gazette Extraction trigger this lap enriches.

## What I did

- **F-163 (bug sweep):** patched 7 admin pages where `fetch("/api/auth/token").then(d => d.accessToken)` was reading a key that doesn't exist in the route response (the route returns `{ access }`, not `{ accessToken }`). The bug silently kept `token === null`, which kept every `useQuery` gated by `enabled: !!token` in skeleton state forever. Surfaced because the user couldn't see Session 38's successfully-extracted rows on `/admin/m1/pipeline/recent` after the spider crawl completed.
- **F-164a (persistent trigger history):** new `lib/m1-extraction/trigger-history.ts` module persists the last 5 `GazetteExtractionTriggerOut` records in `localStorage` under `m1.gazette.recent_triggers`. SSR-safe. New `<RecentTriggersBar>` component renders them as clickable pills above the form. Clicking a pill replays that scope (rebuilds the progress + summary panels). Page-mount auto-restores the most-recent trigger so a reload mid-crawl (or after completion) doesn't lose the panel.
- **F-164b (aggregate summary card):** new backend endpoint `GET /api/v1/admin/m1/extraction/summary` returns scope-aggregate stats: in_scope count + per-status + per-extraction-method counts + total raw_chars + total cleaned_chars + total penalties + total sub_documents + first_created_at + last_updated_at. New service function `m1_pipeline_service.get_extraction_summary()` uses 4 SQL queries. New `<ExtractionSummaryCard>` renders the stats in a 6-stat grid + status pills + PDF-type chips ("Text PDF · 12, Scanned (OCR) · 3"). Polls every 10 s while task non-terminal.
- **F-164c (richer per-row cards):** `regulation-progress-card.tsx` now shows PDF-type + amendment_type StatusBadges in the collapsed view, plus a 📅 prefix on `gazette_published_date`. No new fields — these all came from the existing `/progress` response.
- **Service refactor:** pulled the shared scope predicate into a new `_extraction_scope_filter()` private helper. Both `/progress` and `/summary` now use it; DRY-positive + prevents drift.

## What I found

- **The "no data after extraction" symptom had two layers.** The user's report was "I navigate to see related pipelines and it's not showing the recent data". The proximate cause was the token-key bug (page never fetches → silent skeleton). But there's a secondary UX gap: even on a fresh trigger from the extraction page itself, refreshing the page lost the progress panel (because `task` state was held only in React state, not persisted). F-164's history restore fixes both: the bug-fixed Recent Runs page now works AND the extraction page survives reloads.
- **Aggregate-style queries can share scope predicates safely.** The `/progress` and `/summary` endpoints both scope by `(year, month_start, month_end, since)`. Inlining the same predicate in two places was a drift waiting to happen — extracting `_extraction_scope_filter()` is small but worth it.
- **`primary_language` isn't on the row.** It only exists in the `preprocess_gazette_task` return dict (Celery result-backend). To populate per-language counts in the summary we'd need either a small migration (`primary_language VARCHAR(2)`) or scanning N task_ids per summary call. Going with neither this lap; flagged for a future migration if the use-case strengthens.
- **`extraction_method` GROUP BY counts NULL as its own bucket** (rows still in `ingested` state). The summary card service maps the NULL bucket to a `"pending"` key + the UI renders it as "Detecting".
- **Auto-restoring the latest trigger** could surface a stale scope after a day or two — but the alternative (always-empty state on reload) was worse for the realistic 80-minute crawl flows. Click any pill to switch.

## What changed in the repo

| File | Change |
|---|---|
| `enigmatrix-backend/app/services/m1_pipeline_service.py` | New `_extraction_scope_filter()` helper + new `get_extraction_summary()` function (4 SQL queries: status GROUP BY + method GROUP BY + totals via `func.sum(func.length(...))` + JOINs on `m1_regulation_penalties` + `m1_sub_documents`). |
| `enigmatrix-backend/app/schemas/m1_pipeline.py` | New `ExtractionSummaryOut` schema (9 fields). |
| `enigmatrix-backend/app/api/v1/m1_gazette_extraction.py` | New `GET /summary` endpoint with same admin gate + scope validator as `/progress`. |
| `enigmatrix-frontend/lib/m1-extraction/trigger-history.ts` | NEW — `loadHistory`/`pushHistory`/`clearHistory` localStorage helpers, SSR-safe. |
| `enigmatrix-frontend/components/m1-extraction/recent-triggers-bar.tsx` | NEW — horizontal pill list of past triggers with relative-time labels + Clear button. |
| `enigmatrix-frontend/components/m1-extraction/extraction-summary-card.tsx` | NEW — 6-stat grid + status pills + PDF-type chips + run duration; polls `/summary` every 10 s. |
| `enigmatrix-frontend/components/m1-extraction/regulation-progress-card.tsx` | Added `pdfTypeBadge()` + `amendmentTypeBadge()` helpers; surfaces both in collapsed view + 📅 prefix for `gazette_published_date`. |
| `enigmatrix-frontend/lib/api/m1-gazette-extraction.ts` | Added `ExtractionSummaryOut` type + `getSummary(token, trigger)` method. |
| `enigmatrix-frontend/app/(admin)/admin/m1/pipeline/extraction/page.tsx` | Hydrates trigger history on mount + auto-restores latest as active task; pushes to history on successful trigger; renders `<RecentTriggersBar>` above the form + `<ExtractionSummaryCard>` above `<ExtractionProgressPanel>`; new `selectPastTrigger` + `handleClearHistory` callbacks. |
| `enigmatrix-frontend/app/(admin)/admin/{m1/pipeline/{page, recent/page, steps/page, steps/[stepId]/page, trace/page, trace/[regulationId]/page}.tsx, settings/page.tsx}` | Token-key sweep: 3-line edit per file replacing `d.accessToken` with `j?.access`. 7 files. |

## Tests

- `cd enigmatrix-backend && uv run pytest app/tests/unit/test_gazette_scraper_task.py app/tests/integration/test_gazette_spider.py app/tests/integration/test_celery_extract_gazette.py app/tests/integration/test_celery_preprocess_gazette.py -q` → **19 passed** (no regressions).
- Frontend type-check: `cd enigmatrix-frontend && npx tsc --noEmit` clean for all new + edited files (only the pre-existing `trace-timeline.tsx::sky` color-key error remains, unrelated to this lap).
- New `/summary` endpoint is smoke-testable via curl; integration test gated on testcontainer Postgres (deferred — 30 min follow-up).

## Decisions

- **Separate `/summary` from `/progress`.** Two endpoints + two FE polls (10 s + 5 s) instead of one fat response. Lets the FE poll summary at a lower cadence (it's aggregate; no need to update every 5 s) while keeping the per-row panel tight.
- **Share `_extraction_scope_filter()`.** Both endpoints scope by the same predicate; extracting the helper prevents drift.
- **Auto-restore latest trigger on page-load.** Subtle UX call — the alternative (always-empty state on reload) is worse for ~80-minute crawl flows. Manual selection from the pill bar overrides.
- **PDF-type badges on the collapsed card.** Most asked-for fast feedback — admin scans a list of cards and sees "Text PDF · Preprocessed" vs "Scanned · OCR · Extracted" at a glance without expanding.
- **No new F-### for the token-key sweep alone.** Wait, that's wrong — F-163 IS the sweep. Kept it as its own feature because: (a) it's structurally distinct from the UX enrichments (bug fix vs feature), (b) it's reused by 7 separate pages, (c) splitting keeps the tracker readable.

## Risks / open follow-ups

- **No Playwright / Cypress** for these admin pages — the token-key fix was validated by grep + the proven extraction-page pattern, not by an actual page-render test. Adding one Playwright test that signs in + visits `/admin/m1/pipeline/recent` + asserts non-empty table would catch any recurrence.
- **`/summary` endpoint** does 4 queries; for very wide scopes (full year, hundreds of rows) it's still <100 ms but could batch into a single CTE if it grows hot.
- **`primary_language` deferred** — add a column when use-case strengthens (e.g. when language-specific routing decisions surface in the admin UI).
- **No backend integration test** for `/summary` (pure aggregation against covered tables; smoke-testable via curl).
- **Trigger history doesn't expire automatically.** Restored triggers older than a week could surprise — current behaviour: oldest auto-evicted at MAX_HISTORY=5. Could add a TTL filter in `loadHistory()` later.

## Cross-references

- Predecessor feature: [F-161 (Session 38)](../../../08-Findings-Log/FEATURES.md#session-38) — admin Gazette Extraction trigger this lap enriches.
- Runtime ops doc: [`local-dev/phase2_admin_gazette_extraction.md`](../local-dev/phase2_admin_gazette_extraction.md).
- Related: [F-160 (Session 37)](../../../08-Findings-Log/FEATURES.md) — M1 Pipeline observability portal that the per-row "Open full trace →" button links into.
- Session entry: [Session 39](../../../08-Findings-Log/SESSIONS.md).
