# Phase 2 · Data-Ops Admin UI (02_M1_1/2/3 + 03_M1_3): Analysis

> Group: `PHASE2_INGEST_EXTRACTION / data_ops_admin_ui`. Companion: [[DATA_OPS_ADMIN_UI_PLAN]].
> Surfaces the backend built in [[PHASE2_DATA_VALIDATION_GOVERNANCE_ANALYSIS]], [[PHASE2_SOURCES_WORKED_EXAMPLES_ANALYSIS]], and [[PHASE2_SECONDARY_MATCHING_ANALYSIS]] as admin UI. **Status: implemented 2026-07-23 (verification deferred — sandbox VHDX down, `pnpm` unrun).**

## 1. The gap: backend without a face

The 02/03 builds shipped tasks, models, and services but almost no *admin-facing* surface. The nightly data-quality run wrote `m1_pipeline_audits` that nobody could see; source health lived in `m1_sources` columns + a log line; retention windows + storage projection existed only as settings/code; and Tier-3 propagation candidates were *counted and discarded*. Four surfaces needed both a read API endpoint **and** a page — the frontend can't read the DB directly.

## 2. Where it fits

The `/admin/m1/pipeline` observability portal (`admin_pipeline.py` + `app/(admin)/admin/m1/pipeline/*`) already existed with the exact conventions to reuse: `require_admin` read endpoints returning Pydantic models; client pages using TanStack Query + `useAuthToken` + `PageHeader`/`Card`/`StatusBadge`/`Skeleton`. So all four surfaces were added to that router and route group rather than a new area — they inherit auth, layout, and the existing "M1 Pipeline" breadcrumb.

## 3. Propagation review needed real persistence first

Data Quality / Source Health / Retention are pure reads over data that already exists (`m1_pipeline_audits`, `m1_sources` + catalogue, settings + projection). **Propagation Review could not be built as UI-only** because the 03_M1_3 build deliberately did *not* persist Tier-3 candidates (to protect the lag views). So this build adds the missing persistence layer:

- new table `m1_propagation_reviews` (migration `202607230003`, model, `pending|confirmed|rejected` + `UNIQUE(regulation_id, source_id)`);
- `record_items` now writes a pending review row (idempotent) instead of only incrementing a counter;
- confirm promotes the candidate to a real `human_confirmed` `m1_propagation_events` row (earliest-wins), reject just closes it — both audited.

The review table still never feeds the analytical views; only a *confirmed* row enters `m1_propagation_events`. This finally uses the `human_confirmed` value the previous migration (`202607230002`) added to `ck_m1_prop_match_method`.

## 4. Attribute mapping (real fields, not the docs' idealized ones)

Each page renders the **real** columns, consistent with the earlier schema-reality findings: `classifier_confidence`/`language`/`status` for regulations; `m1_sources` health (`last_checked_at`/`last_ok_at`/`consecutive_failures`/`last_error`) + catalogue `scrape_every_hours`/`fallback`; `m1_pipeline_audits` `check_name`/`value`/`passed`/`detail`; storage projection `hot_pdf_gb`/`glacier_pdf_gb`/`postgres_on_disk_mb`/…; review `cosine`/`source_id`/`channel`/`item_text`. No invented fields.

## 5. Risk posture

All four API endpoints are read-only except the two review actions (POST confirm/reject, audited, 409 on non-pending). No existing endpoint or page was modified except the pipeline landing page (added a 4-tile "Operations" nav row) and `propagation_service.record_items` (pending rows now persisted). Frontend couldn't be type-checked this session, so pages were written strictly against the existing component/hook imports proven by the neighbouring `sources/page.tsx`.
