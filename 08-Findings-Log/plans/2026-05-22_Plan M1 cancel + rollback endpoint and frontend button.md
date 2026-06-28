# Plan: M1 cancel + rollback endpoint and frontend button

## Context

Before this work, the only way to "stop" a runaway M1 extraction was to wait for it to finish or to manually `celery_app.control.revoke(...)` from a shell. The Sources-hub UI offered no operator-facing cancel; rows produced by a bad run accumulated in `m1_regulations` and their PDFs piled up on `/data/storage/m1/raw/<source>/`. Operator explicitly asked for: "able to revoke ... rollback to initial state where delete all the extracted and download ... PDF in the storage of relevant folder".

This is Stage 1 of a four-stage feature push agreed on after the Railway deploy went live (Session 55). Decisions taken before code: GitHub PAT auth (Option A), force=true rollback (destructive), draft-vs-applied filter pattern reused later by Stage 3.

## Goal

1. Add a destructive admin endpoint that revokes a running Celery task AND deletes every `m1_regulations` row + on-disk PDF that the run produced.
2. Surface the action in the existing Sources-hub UI as a red "Cancel & roll back" button, gated behind a ConfirmDialog with a full destructive warning.
3. Scope filters must mirror the original `/trigger` payload + the `queued_at` anchor — cancel must never delete rows from an earlier run.

## Steps / tasks

### Backend (F-194)

1. ✅ **Schemas** — Added `CancelExtractionIn` (`date_from`, `date_to`, `source_id?`, `queued_at`, `force=True`) and `CancelExtractionOut` (`task_id`, `revoked`, `rolled_back_at`, `deleted_rows`, `deleted_pdfs`, `skipped_pdfs`, `errors`) to `enigmatrix-backend/app/schemas/m1_pipeline.py`.
2. ✅ **Service** — Created `enigmatrix-backend/app/services/m1_extraction_cancel.py` (NEW, ~150 lines). `cancel_and_rollback(db, *, task_id, date_from, date_to, source_id, queued_at, force=True)` does four things in order: (a) `celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")` — broker-down recovery path swallows the exception and still runs the DB rollback so state stays consistent; (b) selects rows in scope where `created_at >= queued_at` AND matching source/date filters (date filter passes through rows with NULL `gazette_published_date` so very-fresh inserts don't get missed); (c) when `force=False`, excludes rows already at `status='preprocessed'`; (d) deletes the on-disk PDFs **before** the DB rows so a mid-rollback crash leaves orphan files (recoverable via the existing `/reconcile` endpoint) rather than orphan DB rows pointing at deleted files. Path-traversal guard uses the same `relative_to(storage_root)` check as the existing `/raw-pdf` streaming endpoint.
3. ✅ **Endpoint** — Added `POST /api/v1/admin/m1/extraction/cancel/{task_id}` to `enigmatrix-backend/app/api/v1/m1_gazette_extraction.py`. Behind `require_admin`. Validates scope via existing `_validate_scope()` + `doctype_for_source()`. Lazy-imports the service module so the hot `/trigger` + `/status` cold-start path isn't affected.

### Frontend (F-195)

4. ✅ **Types + client** — Added `CancelExtractionIn` and `CancelExtractionOut` TypeScript interfaces and a `cancel(token, taskId, payload)` method on `M1GazetteExtractionApi` in `enigmatrix-frontend/lib/api/m1-gazette-extraction.ts`.
5. ✅ **Cancel button + confirm dialog** — Edited `enigmatrix-frontend/app/(admin)/admin/m1/pipeline/sources/[sourceId]/extraction/page.tsx`. Added `XCircle` lucide icon import + `ConfirmDialog` import. New state: `cancelOpen`, `cancelResult`. New `cancel = useMutation<CancelExtractionOut, ApiError, void>(...)` that posts the scope from `task` (date_from, date_to, source_id, queued_at) with `force: true`. On success: `queryClient.invalidateQueries` for `["m1-source", sourceId]`, `["m1-extraction-progress", task?.task_id]`, `["m1-extraction-summary", task?.task_id]` so the panel updates without waiting for the next 5s poll. Inline result panel renders deleted_rows, deleted_pdfs, errors (first 5 + "…and N more" overflow).
6. ✅ **Visibility** — Button only renders when `isRunning` (task status not in TERMINAL_STATUSES). Destructive variant + `XCircle` icon. Disabled while `cancel.isPending`.
7. ✅ **ConfirmDialog wiring** — Reused project's existing `components/ui/confirm-dialog.tsx`. Title `"Cancel extraction and roll back?"`, description includes the task_id prefix, scope, source, and the line `"This cannot be undone."`, danger variant. `onConfirm={() => cancel.mutateAsync()}`.

## Errors fixed (during implementation)

- Initial frontend Edit appended a stray `}` after `/>` of `<ConfirmDialog />` — TypeScript would have errored on next build. Caught by re-reading the file after the Edit; fixed with a second Edit removing the trailing `}`.

## Technical notes

- **Scope anchor design** — `queued_at` is the load-bearing field that prevents accidental deletion of rows from an earlier run. The frontend pulls it straight from the `GazetteExtractionTriggerOut.queued_at` that the original `/trigger` returned, so the round-trip is exact.
- **PDFs before DB rows** — Mid-rollback crash recovery: `/reconcile` already exists for the "orphan PDFs on disk" case and will pick them up. The reverse (orphan DB rows pointing at deleted files) would surface as 404 on every `/raw-pdf` download and require manual SQL cleanup.
- **Cascade-delete via ORM relationships** — `M1Regulation.penalties` and `M1Regulation.sub_documents` are declared with `cascade="all, delete-orphan"`. `await db.delete(row)` handles children automatically; no explicit DELETE on `m1_regulation_penalties` or `m1_sub_documents` needed.
- **`force=False` semantic** — Excludes rows at `status='preprocessed'` (the terminal happy-path state). Useful when the operator wants to cancel a stuck run but preserve work that's already produced clean output. UI defaults to `force=true` for the destructive "rollback to initial state" the operator asked for.
- **Broker-down fallback** — Revoke best-effort: if Redis is unreachable, `revoked=false` is returned but the DB rollback still runs so the operator's view matches the intended state.

## Decisions taken

- **Single-table rollback (no new `m1_extraction_runs` table just for this)** — Stage 1 reuses the existing scope+queued_at filter. Note: Session 54 (F-189) added a separate `m1_extraction_runs` table for run history; this endpoint pre-dates that integration and uses scope params instead of a `run_id` lookup. Could be migrated to a `run_id`-based variant in a future pass.
- **No rate limit on `/cancel`** — Destructive but admin-gated and ConfirmDialog-gated. Follow-up #22 will add `@limiter.limit("5/minute")` to all destructive admin endpoints uniformly.
- **No undo button** — Rollback is irreversible by design. The ConfirmDialog warning copy is the only guardrail.

## Open questions

- Should `force=true` be made an explicit operator choice in the UI (toggle in the dialog) rather than a hardcoded default?
- Should the result panel persist across page reloads (e.g. via the new `m1_extraction_runs` table's `celery_status=REVOKED` row), or is the in-memory `cancelResult` state enough?
- Should the endpoint emit a structured audit-log entry (admin email + task_id + deleted counts) via the existing `AuditMiddleware` pattern?

## Acceptance criteria

- [x] `POST /api/v1/admin/m1/extraction/cancel/{task_id}` accepts the scope payload, revokes the task, and returns `CancelExtractionOut`.
- [x] On-disk PDFs in scope are unlinked before DB rows are deleted.
- [x] Cascade-delete handles penalties + sub_documents.
- [x] Cancel button appears in the running-task status card only while `isRunning`.
- [x] ConfirmDialog warns destructively before any deletion.
- [x] On success, source counts + progress + summary queries invalidate immediately.
- [x] On error, the dialog stays open and the error message is shown inline.

## Linked trackers

- [CHANGES.md](../CHANGES.md) — F-194 (backend), F-195 (frontend)
- [FEATURES.md](../FEATURES.md) — F-194, F-195
- [SESSIONS.md](../SESSIONS.md) — Session 55
- Related Stage: [2026-05-22_Plan Per-PDF metadata schema and population](./2026-05-22_Plan%20Per-PDF%20metadata%20schema%20and%20population.md), [2026-05-22_Plan PDF Records browse-all admin page](./2026-05-22_Plan%20PDF%20Records%20browse-all%20admin%20page.md)
