# Plan: M1 extraction page UX improvements — sticky sidebar, resume/restart, history table, auto-scroll

## Context

Four UX/UI improvements to the M1 gazette extraction admin page (`/admin/m1/pipeline/sources/[sourceId]/extraction`) were identified and implemented in Session 54 (2026-05-22). These were completed as tasks #16–19 in the Cowork session and the work spanned a compacted prior context that was resumed. All four tasks were delivered together as a single UX audit improvement sprint.

The extraction page serves as the primary operational interface for triggering, monitoring, and recovering gazette extraction jobs. The improvements target layout stability (sticky sidebar), operational recovery (resume/restart), history visibility (full table replacing 5-item pill strip), and navigation UX (auto-scroll on history row click).

## Goal

Improve the usability and observability of the M1 extraction admin page across four axes:

1. **Sticky inner sidebar** — prevent the left nav from scrolling away on tall content pages.
2. **Resume/restart actions** — allow operators to recover from mid-pipeline failures without manual DB intervention.
3. **Full history table** — replace the 5-item recent-trigger pill strip with a scrollable full table showing all historical runs with live Celery status badges.
4. **Auto-scroll** — when a historical run is selected from the history table, automatically scroll the viewport to the progress panel below.

## Steps / tasks

1. ✅ **Sticky sidebar fix** — Added `lg:items-start` to the grid container in `app/(admin)/admin/m1/pipeline/layout.tsx` to prevent CSS grid default stretch behaviour from stopping `position:sticky`; added `max-h-[calc(100vh-2rem)] overflow-y-auto` to the nav card so the sidebar scrolls independently on very long nav lists.
2. ✅ **Resume/restart card** — Created `components/m1-extraction/resume-extraction-card.tsx` (NEW). Shown when `isTerminal && (extractedCount > 0 || ingestedCount > 0)`. Two actions: "Resume preprocessing" (fetches all extracted rows via `getProgress`, calls `rePreprocess` serially on each) and "Restart from scratch" (re-triggers same date range, calls `onRestart` callback with new trigger).
3. ✅ **History table** — Changed `MAX_HISTORY` from 5 to 20 in `lib/m1-extraction/trigger-history.ts`. Created `components/m1-extraction/extraction-history-table.tsx` (NEW) replacing the `RecentTriggersBar` pill strip. Full table columns: task_id (truncated mono), date range, queued (relative), live Celery status badge (via `useQueries` polling each task, interval 10 s, pauses on terminal), source_id. Active row highlighted with blue dot + "viewing" pill.
4. ✅ **Auto-scroll** — Added `progressRef` (React ref) and `scrollIntoView` call in `selectHistoricalTrigger` in `app/(admin)/admin/m1/pipeline/sources/[sourceId]/extraction/page.tsx`. When an operator clicks a historical run row in the history table, the viewport scrolls to the progress panel.

## Technical notes

- **CSS grid stretch:** `lg:items-start` on the grid container breaks the default `align-items:stretch`, which was causing the `<aside>` to grow to full content height and making `position:sticky` a no-op (sticky needs a bounded containing block).
- **`useQueries` for history polling:** Each history row polls its own Celery status independently via `useQueries`. The `refetchInterval` callback returns `false` once a terminal status (SUCCESS, FAILURE, REVOKED, RETRY) is observed, so polling stops automatically and does not produce unnecessary requests for finished jobs.
- **ResumeExtractionCard `rePreprocess` loop:** The re-preprocess calls are made serially (not in parallel) to avoid overwhelming the Celery queue with simultaneous task submissions for potentially hundreds of rows.
- **`summaryForResume` query:** Hoisted to the extraction page level (above the card) so the same `extractedStuck` / `ingestedStuck` counts are available both to the `ResumeExtractionCard` show/hide decision and to the card's internal logic.

## Decisions taken

- Replaced pill strip entirely with the history table — the pill strip (5 items, no status, no date range visible) was not useful for operators monitoring multi-day extraction campaigns.
- `MAX_HISTORY` raised to 20 (from 5) in localStorage, as a safety backstop for when the API is unavailable (the primary source is now the server-side `m1_extraction_runs` table — see companion plan).
- Resume preprocessing chosen over full restart as the default/primary action — preserves already-extracted text and avoids re-downloading PDFs.
- `once:false` not needed for `scrollIntoView` — a simple `behavior:'smooth'` call in the click handler is sufficient.

## Open questions

- Should the history table be paginated (client-side or server-side) once run counts grow large? Currently shows all rows from the API response (default `page_size=20`).
- Should "Restart from scratch" require a confirmation dialog given it creates a new extraction run and may produce duplicate rows?

## Acceptance criteria

- [x] Sticky sidebar stays fixed at top of viewport when content below it scrolls.
- [x] Sidebar nav scrolls independently within `max-h-[calc(100vh-2rem)]` if nav list is tall.
- [x] `ResumeExtractionCard` appears when a terminal run has `extractedCount > 0 || ingestedCount > 0`.
- [x] "Resume preprocessing" calls `rePreprocess` on each extracted row serially.
- [x] "Restart from scratch" triggers a new extraction for the same date range.
- [x] History table shows all runs (up to `page_size`) with live status badges.
- [x] Status polling pauses for terminal-status rows.
- [x] Clicking a history row scrolls the viewport to the progress panel.

## Linked trackers

- [CHANGES.md](../CHANGES.md) — F-185, F-186, F-187, F-188
- [FEATURES.md](../FEATURES.md) — F-185, F-186, F-187, F-188
- [SESSIONS.md](../SESSIONS.md) — Session 54
- [BUILD_PLAN_COVERAGE.md](../BUILD_PLAN_COVERAGE.md) — Session 54 add-on
- [RESEARCH_BUILD_TRACKER.md](../RESEARCH_BUILD_TRACKER.md) — Session 54 row
