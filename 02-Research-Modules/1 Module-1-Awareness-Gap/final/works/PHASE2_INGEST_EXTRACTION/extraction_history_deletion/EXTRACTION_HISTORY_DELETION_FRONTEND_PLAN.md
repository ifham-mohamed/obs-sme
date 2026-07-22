# Phase 2 · Ingest — Extraction-History Deletion: Frontend Slice

> Group: `PHASE2_INGEST_EXTRACTION / extraction_history_deletion`. Companions: [[EXTRACTION_HISTORY_DELETION_ANALYSIS]], [[EXTRACTION_HISTORY_DELETION_ENHANCEMENT_PLAN]].
> **Status: implemented (2026-07-22).** The frontend follow-up specced in the enhancement plan is now built. Code in `C:\Reasearch\xyz\enigmatrix-frontend`.

## What was built

The extraction-run **history table** on `(admin)/admin/m1/pipeline/sources/[sourceId]/extraction` now exposes the soft-delete backend directly.

### API client — `lib/api/m1-gazette-extraction.ts`

- `ExtractionRunOut` extended with `archived_at` / `archived_by` / `archive_kind`.
- New result types `RunArchiveResult`, `BulkArchiveResult`.
- `listRuns(..., { includeArchived })` → adds `?include_archived=true`.
- New calls: `archiveRun(token, runId, withRegulations)` (`DELETE /runs/{id}`), `bulkArchiveRuns(token, runIds, withRegulations)` (`POST /runs/bulk-archive`), `restoreRun(token, runId)` (`POST /runs/{id}/restore`).

### Table component — `components/m1/extraction/extraction-history-table.tsx`

- New optional props: `runByTaskId` (task_id → full API run row, carrying `run_id` + archive state), `includeArchived`, `busy`, and callbacks `onToggleArchived`, `onArchive`, `onRestore`, `onBulkArchive`. All additive — the component still renders unchanged when they're absent (localStorage-only rows get no actions).
- **Per-row actions** (only for rows that exist server-side): a 🗑 **Delete history** (history-only) button and a 🗄 **Delete + data** button that opens a `confirm()` explaining the regulations are soft-deleted (restorable), not erased.
- **Bulk**: a checkbox per active row + a toolbar (`N selected` · *also delete regulations* checkbox · **Archive selected** · Clear selection) → one `bulkArchiveRuns` call.
- **Archived view**: a **Show archived** header toggle; archived rows render muted with an `archived` / `archived · data` chip and a ↩ **Restore** button.
- Row-level clicks on checkboxes/action buttons `stopPropagation()` so they don't also trigger the existing "view this run" row-select.

### Page wiring — `.../extraction/page.tsx`

- `includeArchived` + `historyBusy` state; `includeArchived` folded into the `listRuns` query key + options so toggling refetches.
- `runByTaskId` memo built from `runsQuery.data.items`.
- `handleArchiveRun` / `handleRestoreRun` / `handleBulkArchive` call the API and `invalidateQueries(["m1-extraction-runs", sourceId])` to refresh; `historyBusy` disables the action buttons while in flight.
- The existing **Clear history** button is relabelled **Clear local cache** — it only clears the localStorage write-through cache, never server rows (that distinction was previously ambiguous).

## Design notes

- **No new modal dependency.** The one destructive path (delete + regulations) uses a native `confirm()` — sufficient friction for an admin tool without pulling in a dialog component. A shadcn `AlertDialog` upgrade is a trivial future swap if richer confirmation is wanted (see backlog #11 in the enhancement plan).
- **Actions only on server rows.** localStorage-only history entries (shown before the API responds) have no `run_id`, so they render without archive actions — you can't delete something the server doesn't yet know about.
- **Soft everywhere.** Restore is one click; the with-regulations path is reversible per-regulation via the existing regulation-restore endpoint (the confirm text says so).

## Verification (deferred to user — needs the app running)

1. `cd enigmatrix-frontend && pnpm typecheck && pnpm lint` (no new type/lint errors).
2. Open a source's extraction page → the history table shows a checkbox column + Actions column.
3. 🗑 on a run → it vanishes from the list; **Show archived** on → it reappears muted with a **Restore** button; Restore → back to active.
4. 🗄 on a run → confirm dialog → on OK the run archives (`archived · data` chip) and its regulations go inactive (check `/admin/m1/pipeline/recent` or the DB).
5. Select 2–3 rows → **Archive selected** (optionally *also delete regulations*) → all archived in one call; toggling *also delete regulations* flips the button to the destructive variant.
6. Buttons disable while an action is in flight (`historyBusy`).

## Follow-ups

- Swap the `confirm()` for a shadcn `AlertDialog` that shows the run's scope + live regulation count (ties to enhancement-plan backlog #9 "blast-radius count" + #11 "typed confirm").
- Surface API errors via the page's toast instead of `console.error` (kept minimal here to avoid assuming a toast util).
- A small "N archived" count + a dedicated archived-only view if the history grows large (retention prune already bounds it server-side).
