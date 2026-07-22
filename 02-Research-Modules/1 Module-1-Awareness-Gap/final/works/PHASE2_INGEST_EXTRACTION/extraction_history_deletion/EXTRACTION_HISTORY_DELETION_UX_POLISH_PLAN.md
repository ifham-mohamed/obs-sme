# Phase 2 · Ingest — Extraction-History Deletion: UX Polish + Clean-DB Command

> Group: `PHASE2_INGEST_EXTRACTION / extraction_history_deletion`. Companions: [[EXTRACTION_HISTORY_DELETION_DELETE_MENU_PLAN]], [[EXTRACTION_HISTORY_DELETION_HARD_DELETE_PLAN]].
> **Status: implemented (2026-07-22).** Closes the two follow-ups from the prior docs (toast, confirm dialog) and adds the requested "completely clean the DB" backend command.

## 1. Toast on success/error (was `console.error`)

The page's delete/restore handlers now surface outcomes through the app's toast surface (`@/components/ui/toast`, sonner-backed) instead of `console.error`:

- `handleArchiveRun` → `toast.success("Run archived" | "Run permanently deleted")`; on failure `toast.error(err.message)`.
- `handleRestoreRun` → `toast.success("Run restored")`.
- `handleBulkArchive` → `toast.success("N run(s) archived|deleted")`.
- Errors are `ApiError`, so the **409** returned when a hard-delete-with-regulations is FK-blocked now shows its actual message (steering to soft-delete), not a silent console log.

**File:** `app/(admin)/admin/m1/pipeline/sources/[sourceId]/extraction/page.tsx`.

## 2. Confirm dialog (was `window.confirm`)

`@radix-ui/react-alert-dialog` isn't a dependency, but the radix **`Dialog`** (`@/components/ui/dialog`) is — functionally an alert dialog. The destructive delete paths now open a styled modal instead of a native `confirm()`:

- Any action that touches data (`with_regulations`) OR is permanent (`hard`) routes through `requestDelete(...)` → sets `pending` → renders a `Dialog`. A plain **soft history-only** delete still executes in one click (no dialog).
- The dialog shows the **scope** (`SOURCE from…to`, or "N selected run(s)") and a **regulation count** (`≈ N`, summed from the run rows' `rows_ingested/extracted/preprocessed` snapshot — no extra fetch), then states the effect: *archived (restorable)* vs *permanently erased (with penalties + sub-documents)*, with a red **"This cannot be undone"** for hard deletes.
- The confirm button is `destructive`-variant for hard deletes; Cancel dismisses. Works for both per-row and bulk (`bulk` flag on `pending`).

**File:** `components/m1/extraction/extraction-history-table.tsx` (added `Dialog` import, `pending` state, `requestDelete` / `executePending` / `pendingRegCount`; the `⋯` and bulk menus now call `requestDelete`).

## 3. "Completely clean the DB" backend command

New guarded full-wipe command — the "start over" button the owner asked for.

- **`app/scripts/db_clean.py`** — `TRUNCATE`s **every** table (CASCADE, RESTART IDENTITY) by reusing `db_truncate._truncate_all`, so all data (pipeline rows, users, surveys, extraction history, …) is gone while **schema + `alembic_version` are preserved** (no re-migration needed). Two guards the raw truncate lacks, because this deletes everything:
  1. **Production guard** — refuses when `APP_ENV` looks like production unless `--force`.
  2. **Typed confirmation** — must type `CLEAN`, unless `--yes`.
  - `--seed` re-seeds dev data (`seed_dev.main()`) after cleaning. Disposes the engine in `finally` (re-runnable).
- **`Makefile`** — `db-clean` target + `.PHONY` + help line; flags via `ARGS`.

```
uv run python -m app.scripts.db_clean                 # prompt, then wipe
uv run python -m app.scripts.db_clean --yes --seed    # wipe + re-seed (CI/dev)
make db-clean ARGS="--yes --seed"
```

**Why a new command, not just `db-truncate`:** `db-truncate` (and `db-reset`/`db-fresh`) already exist but have **no confirmation** — easy to fire by accident. `db-clean` is the explicit, guarded "wipe everything" entry point, safe to document for daily dev use. Documented in `07_SETUP_AND_USER_MANUAL.md` §5 + §11.

## Verification (deferred to user)

1. Frontend: `pnpm typecheck && pnpm lint`. Trigger a delete → a styled dialog (not a browser prompt) shows scope + `≈ regs`; confirm → a toast; a hard delete of a run with Phase-4 dependents → the **409 message** appears as an error toast.
2. Backend: `python -m compileall app`. `make db-clean` → prompts for `CLEAN`; `--yes` skips it; with `APP_ENV=production` it refuses without `--force`; `--seed` leaves the seed admin present.
3. `graphify update .`.

## Build fix (2026-07-22)

The toast wiring initially added a second `import { toast } from "@/components/ui/toast"` to the extraction page, which already imported `toast` (SWC: *"the name `toast` is defined multiple times"*). Removed the duplicate — the single existing import is used. No behaviour change.

## Follow-ups

- If richer confirmation is wanted, add `@radix-ui/react-alert-dialog` + the shadcn `AlertDialog` and swap the `Dialog` (cosmetic; behaviour identical).
- Optional: fetch a *live* in-scope regulation count (via the summary endpoint) instead of the run-row snapshot for the dialog, if snapshots drift from reality.
