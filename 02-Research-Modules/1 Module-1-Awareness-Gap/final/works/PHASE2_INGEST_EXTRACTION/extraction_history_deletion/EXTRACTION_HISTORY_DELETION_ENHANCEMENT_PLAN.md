# Phase 2 · Ingest — Extraction-History Deletion: Enhancement Plan

> Group: `PHASE2_INGEST_EXTRACTION / extraction_history_deletion`. Companion: [[EXTRACTION_HISTORY_DELETION_ANALYSIS]].
> **Status: backend implemented (2026-07-22); frontend UI specced as a follow-up.** Code in `C:\Reasearch\xyz\enigmatrix-backend`.

## What was built (backend)

| Piece | Where |
|---|---|
| Soft-delete columns `archived_at` / `archived_by` / `archive_kind` + partial index `ix_m1_extraction_runs_active` | `app/m1/models/extraction_run.py`, migration `alembic/versions/202607220001_m1_extraction_run_archive.py` |
| Archive service — `archive_run` (history-only / with-regulations), `restore_run`, `bulk_archive`, `prune_old_runs`; scope soft-delete of regulations; audited | `app/m1/services/extraction_run_archive.py` (new) |
| Endpoints on the extraction router | `app/m1/api/gazette_extraction.py` |
| Retention Beat task + setting + registration | `app/m1/tasks/prune_extraction_runs.py` (new), `app/settings.py` (`M1_EXTRACTION_RUN_RETENTION_DAYS`, default 0), `app/celery_config.py` (include + `prune-extraction-runs-daily` 20:00 UTC) |

### Endpoints (all `require_admin`, under `/api/v1/admin/m1/extraction`)

| Method + path | Action |
|---|---|
| `DELETE /runs/{run_id}?with_regulations=false` | Archive one run. `with_regulations=true` also soft-deletes its regulations. |
| `POST /runs/bulk-archive` `{run_ids:[…], with_regulations:false}` | Archive many; missing ids reported, not fatal. |
| `POST /runs/{run_id}/restore` | Un-archive the history row (regulations restored separately). |
| `GET /runs?include_archived=false` | The existing list — now hides archived runs by default; `true` shows them. |

Audit event types: `m1_extraction_run.archived` (history-only), `.purged` (with regulations), `.restored`, `.retention_pruned`.

## Enhancements included / recommended

**Included in this build:**
1. **Two distinct, clearly-named actions** so "delete the log entry" can never be confused with "delete the ingested data".
2. **Soft-delete + restore** — reversible, with a partial index so the common list stays fast.
3. **Live-run safeguard** — with-regulations on a non-terminal run revokes the task first (avoids racing the pipeline writers) without adding a status block.
4. **Full audit trail** — every archive/restore/prune writes an Activity-Log row with actor + scope + regulation count.
5. **Retention prune** — bounded history growth, history-only (never deletes data), off by default.

**Recommended follow-ups (not yet built):**
6. **Frontend slice** (below) — the buttons/checkboxes/toggle on the recent page.
7. **Undo window** — a toast with an inline "Undo" that calls `/restore` (leverages the soft-delete already in place).
8. **Hard-purge sweeper** (optional, opt-in) — a much-later Beat job that *physically* deletes rows archived > N months, for teams that want the table to actually shrink; keep it separate and clearly gated.
9. **Per-run → regulation drill-down** — since the link is scope+time, add a read-only "N regulations in this run's scope (M still active)" count on each history row so the admin sees the blast radius *before* choosing with-regulations.
10. **Export-before-delete** — optional CSV/JSON export of a run (or selection) prior to archive, for record-keeping.
11. **Confirmation friction for with-regulations** — a typed confirm ("type the gazette count") in the UI, since that path deactivates data.

## Frontend spec (follow-up — `(admin)/admin/m1/pipeline/recent` + extraction page)

- Each history row: a kebab menu → **Delete history** (calls `DELETE /runs/{id}`) and **Delete history + regulations** (calls `DELETE /runs/{id}?with_regulations=true`, guarded by a confirm dialog showing the scope + regulation count).
- **Bulk**: row checkboxes + a toolbar "Archive selected" → `POST /runs/bulk-archive` with the chosen `with_regulations` toggle.
- **Archived view**: a "Show archived" toggle that re-queries `GET /runs?include_archived=true`; archived rows render muted with a **Restore** button (`POST /runs/{id}/restore`).
- Empty/error states mirror the existing metadata/classifier review tables.

## Verification (deferred to user — sandbox lacks Postgres/Redis)

1. `alembic upgrade head` → `202607220001` applies; `\d m1_extraction_runs` shows the three columns + the partial index.
2. `python -m compileall app`.
3. History-only: `DELETE /admin/m1/extraction/runs/{id}` → run disappears from `GET /runs`; reappears with `GET /runs?include_archived=true` (`archive_kind='history_only'`); its regulations are untouched. `POST /runs/{id}/restore` → back in the default list. Audit rows present.
4. With-regulations: `DELETE …/{id}?with_regulations=true` on a terminal run → run archived (`archive_kind='with_regulations'`); its scope regulations are `is_active=false`; response reports `regulations_archived`. Restore brings the history back; regulations stay inactive (restore them via the regulation endpoint) — matches the design note.
5. Bulk: `POST /runs/bulk-archive` with 2–3 ids → all archived; a bogus id lands in `not_found`, not an error.
6. Retention: set `M1_EXTRACTION_RUN_RETENTION_DAYS=30`, run `celery -A app.celery_config call app.tasks.m1.prune_extraction_runs.prune_extraction_runs` → terminal runs older than 30 d archived history-only; `retention_pruned` audit row written; with the setting at 0 the task returns `{disabled:true}`.
7. `uv run pytest -q` (add unit tests for `prune_old_runs` date cutoff + `archive_run` idempotency — pure-ish, mock the session).
8. `graphify update .`.

## Process note (per owner)

From here on, each requested enhancement / bug / fix is documented in this same MD format under `final/works/<PHASE>/<group>/` — an `_ANALYSIS.md` (what + why + design) and a `_FIX_PLAN.md` / `_ENHANCEMENT_PLAN.md` (what changed + verification). Prior items this session already follow it: `scraper_crawl_exit1`, `scraper_stale_model_import` (Phase 2), `classifier_onnxruntime_missing` (Phase 3). The **90-day session** change (Phase 1) is the one still to be back-filled into a Phase-1 group doc.
