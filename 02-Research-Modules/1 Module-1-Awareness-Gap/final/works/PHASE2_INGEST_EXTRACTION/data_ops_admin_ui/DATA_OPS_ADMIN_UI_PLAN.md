# Phase 2 · Data-Ops Admin UI: Plan

> Group: `PHASE2_INGEST_EXTRACTION / data_ops_admin_ui`. Companion: [[DATA_OPS_ADMIN_UI_ANALYSIS]].
> **Status: implemented 2026-07-23.** Verification deferred (sandbox down; `pnpm`/`alembic` unrun).

## 1. Files added / changed

**Backend — `app/m1/api/admin_pipeline.py` (edit, all `require_admin`, mounted `/api/v1/admin/m1/pipeline`)**
- `GET /data-quality` — latest `m1_pipeline_audits` run: checks + pass/fail + overall.
- `GET /source-health` — active `m1_sources` + catalogue ops (`source_catalogue.get_source_ops`) + healthy/degraded verdict.
- `GET /retention` — settings windows + dry-run flag + `storage_projection.projection_table()`.
- `GET /propagation-review` (paged) + `POST /propagation-review/{id}/confirm` + `/reject`.

**Backend — propagation review persistence (03_M1_3 follow-up)**
- `app/m1/models/propagation_review.py` (new) — `M1PropagationReview`.
- `alembic/versions/202607230003_m1_propagation_reviews.py` (new) — table + status CHECK + unique + index. `down_revision="202607230002"`.
- `app/m1/services/propagation_service.py` (edit) — `record_items` persists Tier-3 pending rows (idempotent) instead of only counting.

**Frontend**
- `lib/api/m1-pipeline.ts` (edit) — types + `M1PipelineOpsApi` (4 getters + confirm/reject).
- `app/(admin)/admin/m1/pipeline/{data-quality,source-health,retention,propagation-review}/page.tsx` (new) — TanStack Query client pages.
- `app/(admin)/admin/m1/pipeline/page.tsx` (edit) — 4-tile "Operations" nav row + `OpsTile`.

## 2. Conventions honoured

`require_admin` + Pydantic response models on the backend; `"use client"` + `useAuthToken` + `useQuery`/`useMutation` + `PageHeader` breadcrumb + `Card`/`StatusBadge`/`Skeleton` + `export const dynamic = "force-dynamic"` on pages; `api.post(path, body, token)` for the 204 review actions; `toast` (sonner) for confirm/reject feedback + `ApiError` message on 409. All proven against the neighbouring `sources/page.tsx`.

## 3. Migration head

`…202607230001 → 202607230002 → 202607230003`. One `alembic upgrade head` applies all three (validation/governance, match-method widen, propagation reviews).

## 4. Verification (deferred to operator)

1. Backend: `python -m compileall app` — router + model + service edits.
2. `alembic upgrade head` → `m1_propagation_reviews` exists; `\d+` shows the status CHECK + unique.
3. API smoke (admin token): `GET …/data-quality`, `/source-health`, `/retention`, `/propagation-review` return 200 with the documented shapes; a non-admin gets 403.
4. Propagation loop: with embeddings on, feed a review-band mention → a `pending` review row; `POST …/confirm` → a `human_confirmed` `m1_propagation_events` row + review `confirmed`; `/reject` → review `rejected`, no event. Both audited; second call → 409.
5. Frontend: `pnpm typecheck && pnpm lint`; open each page → data renders, refresh works, confirm/reject fires a toast; landing page shows the 4 Operations tiles.
6. `graphify update .`.

## 4b. Fix (2026-07-23) — "No QueryClient set"

The four new pages (and the pre-existing `steps/[stepId]`) threw `No QueryClient set, use QueryClientProvider to set one` at runtime, even though the root `app/layout.tsx` wraps everything in `<Providers>` (which includes `<ReactQueryProvider>`) **and** `pipeline/layout.tsx` re-wraps in `<ReactQueryProvider>`. `package.json` has a single `@tanstack/react-query@^5.55.4`, so the ancestor provider *should* reach these routes — the failure is the classic "provider present but not seen" edge (stale chunk / nested-provider/context mismatch on newly-added routes).

**Fix:** each affected page now wraps its own body in `ReactQueryProvider` (imported from `@/components/providers`) — the default export renders `<ReactQueryProvider><…Body/></ReactQueryProvider>` and the hooks moved into `…Body`. Because the provider and the `useQuery`/`useQueryClient` consumers are now co-located in the same module graph, they resolve to the same react-query instance and a client is guaranteed regardless of ancestor state. Nested providers are safe (innermost wins); each page keeps its own cache, which is fine for standalone admin views. Files: `data-quality`, `source-health`, `retention`, `propagation-review`, and `steps/[stepId]` pages.

**If it recurs on other pipeline pages** (overview/recent/trace): the true root cause is environmental — delete `.next` and restart `next dev` (new route files + a modified client layout often need a clean rebuild), and/or `npm ls @tanstack/react-query` to rule out a lockfile duplicate.

## 5. Follow-ups

Filters/pagination controls on Data Quality history (trend over run_dates); a "run now" button wired to trigger the nightly job; source-health `active` toggle from the card (endpoint already exists — `PATCH /sources/{id}`); propagation-review cross-language threshold hint + stale-auto-reject surfacing. Sidebar entry (currently reachable via the pipeline landing tiles) if a top-level nav link is wanted.
