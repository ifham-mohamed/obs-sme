# Phase 2 · Ingest — Extraction-History Deletion: Analysis & Design

> Group: `PHASE2_INGEST_EXTRACTION / extraction_history_deletion`. Companion: [[EXTRACTION_HISTORY_DELETION_ENHANCEMENT_PLAN]].
> Enhancement requested 2026-07-22. Feature owner decisions captured below.

## What "extraction history" is today

Every time an admin fires **POST `/admin/m1/extraction/trigger`** (pick a source + date range → run the spider), a durable audit row is written to **`m1_extraction_runs`**. It records the scope, who triggered it, the Celery `task_id`, the lifecycle status (`PENDING → … → SUCCESS/FAILURE/REVOKED`), row-count snapshots, and timestamps. This table backs the **`/admin/m1/pipeline/recent`** history list (it replaced the old per-browser localStorage history so the record is shared and never lost).

Two facts shape the feature:

1. **A run is NOT hard-linked to its regulations.** `m1_extraction_runs` has no FK to `m1_regulations`. The connection is by **scope + time** — `COALESCE(gazette_published_date, date(created_at)) BETWEEN date_from AND date_to` AND `created_at ≥ queued_at`, filtered to the source's document type. This is the exact predicate `_extraction_scope_filter` already provides and that `/cancel`'s rollback uses.
2. **There was no delete** for these history records — the table only grows.

## The ask

Let an admin **delete extraction-run history**, safely, once the regulations it produced are already saved in the DB. Per the owner's decisions:

| Decision | Choice |
|---|---|
| What "delete" removes | **Two separate actions**: (a) *history only* — remove the run record, keep the regulations; (b) *with regulations* — also remove the run's interlinked regulations. |
| Delete type | **Soft-delete (archive)** — reversible, nothing physically destroyed. |
| Trigger surfaces | **Single-run**, **bulk-select**, and **auto-retention prune** (all three). |
| Status guard | **None** — any run may be archived (with a correctness safeguard, not a block, for still-active runs). |

## Design

**Soft-delete columns on `m1_extraction_runs`** (migration `202607220001`): `archived_at` (NULL = active), `archived_by`, `archive_kind ∈ {history_only, with_regulations}`. A **partial index** `ix_m1_extraction_runs_active` on `(source_id, queued_at) WHERE archived_at IS NULL` keeps the default list index-only as archived rows accumulate.

**Two actions, both soft:**

- **history-only** — set `archived_at/archived_by/archive_kind='history_only'`. The run drops off the recent list; its regulations are untouched (they're already saved — exactly the "already migrated" case).
- **with-regulations** — additionally set `is_active=False` on the run's regulations (matched by `_extraction_scope_filter`). Nothing is hard-deleted, so both the history row (via restore) and each regulation (via the existing regulation-restore endpoint) are recoverable.

**No guard, with a safeguard:** any run — even a still-running one — can be archived. For the *with-regulations* path on a **non-terminal** run, the service best-effort **revokes the Celery task first** so a live pipeline writer doesn't keep inserting rows into the scope being soft-deleted. This is correctness, not a status block.

**Reversibility:** `restore_run` un-archives the history row. It deliberately does **not** auto-reactivate regulations that a with-regulations archive deactivated — bulk-reactivating data should be a conscious act (use the per-regulation restore). The restore response says so.

**Everything is audited** (Activity-Log policy): `m1_extraction_run.archived` / `.purged` / `.restored` / `.retention_pruned` rows carry the actor, run, scope, and regulation count — so "who deleted which history, and did it touch data" is always answerable.

**Retention:** a daily Beat task auto-archives **history-only** terminal runs older than `M1_EXTRACTION_RUN_RETENTION_DAYS` (default `0` = off). Retention **never** touches regulations — automated cleanup must not delete ingested data.

## Why soft-delete (not hard-delete)

`m1_extraction_runs` exists precisely because the ephemeral localStorage history kept getting lost. Hard-deleting rows would repeat that mistake and destroy the audit trail. Soft-delete gives the same clean list (archived rows hidden by default, `?include_archived=true` to see them) while keeping every action reversible and auditable — the right default for an audit table.

See [[EXTRACTION_HISTORY_DELETION_ENHANCEMENT_PLAN]] for the concrete files/endpoints, the enhancement backlog, the frontend spec, and verification.
