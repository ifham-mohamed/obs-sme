# Phase 2 · Ingest — Extraction-History Deletion: Explicit Delete Menu (UX)

> Group: `PHASE2_INGEST_EXTRACTION / extraction_history_deletion`. Companions: [[EXTRACTION_HISTORY_DELETION_FRONTEND_PLAN]], [[EXTRACTION_HISTORY_DELETION_HARD_DELETE_PLAN]].
> **Status: implemented (2026-07-22).** Replaces the icon-buttons + "Permanent delete" toggle with an explicit, labelled menu so each delete choice is unmistakable.

## Why

The first cut used two per-row icons (🗑 / 🗄) whose meaning flipped depending on a header "Permanent delete" toggle — powerful but not self-evident. The owner asked for the choices to be **named explicitly**: *delete the extraction record*, *delete history + archive regulations*, *delete history + hard-delete regulations*. So the actions are now spelled out in a dropdown menu instead of encoded in icons + a mode toggle.

## What changed — `components/m1/extraction/extraction-history-table.tsx`

- Removed the `permanentMode` header toggle and the two ambiguous icon buttons.
- **Per active row:** a `⋯` (kebab) `DropdownMenu` with four labelled items:
  1. **Delete history (archive)** — soft, reversible; regulations untouched.
  2. **Delete history + archive regulations** — soft; regs `is_active=false` (restorable).
  3. **Delete history + permanently delete regulations** — *destructive-styled*; hard-deletes the regs (penalty/sub-doc cascade). Confirms.
  4. **Permanently delete history** — *destructive-styled*; hard-deletes the run record. Confirms.
- **Archived rows:** unchanged — an inline **Restore** button.
- **Bulk:** the selection toolbar's single button became a **"Delete selected ▾"** `DropdownMenu` offering the *same four* options applied to the selection (with a one-shot confirm for the hard paths).
- One `deleteRun(run, withRegs, hard)` helper backs the per-row items and one `bulkDelete(withRegs, hard)` backs the bulk items; both map straight onto the existing `onArchive(run, withRegs, hard)` / `onBulkArchive(ids, withRegs, hard)` callbacks — **no backend or page-handler change was needed** (the `hard` flag plumbing from the previous step already carries it).
- Uses the existing shadcn `components/ui/dropdown-menu` (Radix) — no new dependency.

## Mapping to the backend

| Menu item | Call | Endpoint effect |
|---|---|---|
| Delete history (archive) | `onArchive(run, false, false)` | `DELETE /runs/{id}` → soft archive, restorable |
| Delete history + archive regulations | `onArchive(run, true, false)` | `+ is_active=false` on scope regs |
| Delete history + permanently delete regulations | `onArchive(run, true, true)` | `DELETE …?hard=true&with_regulations=true` → rows erased (cascade); 409 if FK-blocked |
| Permanently delete history | `onArchive(run, false, true)` | `DELETE …?hard=true` → run row erased |

## Verification (deferred to user)

1. `pnpm typecheck && pnpm lint`.
2. Open the extraction page → each active run shows a `⋯` menu with the four named items; the two destructive ones are red and confirm before acting.
3. Item 1 removes the run (reappears under **Show archived**, restorable). Item 4 removes it permanently (does **not** reappear under Show archived).
4. Select rows → **Delete selected ▾** offers the same four; the hard ones confirm once for the whole selection.
5. A hard "+ regulations" on a run whose regs have Phase-4 dependents → backend 409 (surfaced via the page catch; toast is the noted follow-up).

## Follow-ups (unchanged from prior docs)

- Route the 409/errors to the page toast instead of `console.error`.
- Optional shadcn `AlertDialog` (with a live regulation count) in place of `window.confirm` for the two destructive items.
