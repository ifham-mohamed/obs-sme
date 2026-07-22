# Phase 2 · Ingest — Extraction-History Deletion: Hard-Delete (permanent)

> Group: `PHASE2_INGEST_EXTRACTION / extraction_history_deletion`. Companions: [[EXTRACTION_HISTORY_DELETION_ANALYSIS]], [[EXTRACTION_HISTORY_DELETION_ENHANCEMENT_PLAN]], [[EXTRACTION_HISTORY_DELETION_FRONTEND_PLAN]].
> **Status: backend + frontend implemented (2026-07-22).** Adds a **permanent** (hard) delete alongside the existing reversible soft-delete/archive.

## Decision

The soft-delete/archive shipped first (reversible, audited). This adds the other half the owner asked for: **hard-delete — completely remove the records.** Both now coexist; the choice is per-action.

|  | History only | History **+ regulations** |
|---|---|---|
| **Soft (archive)** | run row hidden, restorable | run row hidden + regs `is_active=false` (restorable) |
| **Hard (permanent)** | run row **DELETEd** | run row **DELETEd** + regs deleted (penalty + sub-doc cascade) |

Hard delete is **irreversible** — there is no restore.

## Backend

**Service — `app/m1/services/extraction_run_archive.py`**
- `hard_delete_run(session, *, run, actor_email, with_regulations)` — writes the audit row **first** (it lives in `audit_log`, a separate table, so it survives the delete), then, for `with_regulations`, revokes a still-active task and removes the run's regulations via **ORM `session.delete(row)`** so the penalty + sub-document cascade fires (the exact mechanism `cancel_and_rollback` relies on), then deletes the `m1_extraction_runs` row. Audit events: `m1_extraction_run.hard_deleted` / `m1_extraction_run.hard_purged`.
- `bulk_hard_delete(session, *, run_ids, actor_email, with_regulations)` — loops the above; missing ids reported, not fatal.

**FK safety.** If a regulation still has dependent rows in *other* tables (Phase-4 alerts / propagation events, survey links), the DB raises on the foreign key and the **whole transaction rolls back** — nothing is half-deleted. The endpoint translates that to **HTTP 409** with a message steering the admin to soft-delete instead. (Freshly-extracted regs — the common cleanup case — have no such dependents, so cascade delete succeeds; this guard just makes the dangerous case safe.)

**Endpoints — `app/m1/api/gazette_extraction.py`**
- `DELETE /admin/m1/extraction/runs/{run_id}` gains `?hard=true` → routes to `hard_delete_run` (else archive). `?with_regulations=true` still selects the scope.
- `POST /runs/bulk-archive` body gains `hard: bool` → routes to `bulk_hard_delete` (else bulk archive).
- Both wrap the hard path in `try/except IntegrityError → 409`.

No new migration (uses the columns/rows already there; hard delete just removes rows).

## Frontend

**API client — `lib/api/m1-gazette-extraction.ts`**
- `archiveRun(token, runId, withRegulations, hard)` and `bulkArchiveRuns(token, runIds, withRegulations, hard)` gained the `hard` flag (query param / body field). `RunArchiveResult` gained `deleted` / `permanent` / `regulations_deleted`.

**Table — `components/m1/extraction/extraction-history-table.tsx`**
- A single header toggle **"Permanent delete"** (destructive-tinted) flips *every* delete action — the two per-row buttons **and** the bulk button — from reversible archive to permanent hard-delete. This covers all four combos without adding more per-row icons:
  - 🗑 (history) → soft archive **or** hard delete, per the toggle.
  - 🗄 (history + data) → soft archive+data **or** hard delete+data, per the toggle.
  - Bulk button label becomes **"Permanently delete selected"** and turns destructive when the toggle is on.
- One `confirmDelete(run, withRegs, hard)` helper: a plain soft history-only delete is one click; every other combo confirms, with a stern "This CANNOT be undone" for the hard paths. The bulk permanent action confirms once for the whole selection.

**Page — `.../extraction/page.tsx`**
- `handleArchiveRun` / `handleBulkArchive` gained the `hard` arg and forward it to the client; a 409 (FK conflict) surfaces via the existing catch (currently `console.error`; toast is a noted follow-up).

## Verification (deferred to user)

1. Backend: `python -m compileall app`. Soft path unchanged; `DELETE …/runs/{id}?hard=true` removes the row (gone from `include_archived=true` too); with `?with_regulations=true` the scope regs + their penalties/sub-docs are gone; a `m1_extraction_run.hard_deleted`/`hard_purged` audit row exists.
2. FK guard: hard-delete-with-regs a run whose regs have a Phase-4 alert/propagation row → **409**, nothing deleted (transaction rolled back).
3. Bulk hard: `POST /runs/bulk-archive {run_ids, hard:true, with_regulations:false}` → rows gone; bogus id in `not_found`.
4. Frontend: toggle **Permanent delete** → per-row + bulk buttons turn red; deleting prompts "cannot be undone"; the run disappears and does **not** come back under **Show archived** (it's gone, not archived).
5. `pnpm typecheck && pnpm lint`.

## Follow-ups

- Route the 409 (and other errors) to the page toast instead of `console.error`.
- For the destructive combos, upgrade the native `confirm()` to a shadcn `AlertDialog` showing the run scope + live regulation count (also noted in the enhancement plan backlog).
- Optional: a "type DELETE to confirm" gate for bulk permanent deletes over N runs.
