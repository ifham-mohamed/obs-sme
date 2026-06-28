# Plan: PDF Records browse-all admin page

## Context

Stage 3 of the four-stage push. The existing extraction-status view (`/admin/m1/pipeline/sources/[sourceId]/extraction`) is **scoped to a single trigger run**: it shows the rows the current `task_id` produced. The operator asked for a **browse-all** view that shows every PDF the M1 pipeline has ever ingested, with filters (source, status, language, date range, search by gazette number) and pagination.

This page reads the per-PDF metadata fields added in Stage 2 (Plan: Per-PDF metadata schema and population) — file size, language, page count are surfaced as columns. It uses the existing `/raw-pdf` download endpoint per regulation, not a separate bulk endpoint.

User invoked the design skills `design:ux-copy`, `design:user-research`, `design:design-system` at the same time the Stage 3 work was requested. These shaped UX decisions (concrete empty-state copy, draft-vs-applied filter pattern, pagination over infinite-scroll) but did not produce separate audit artifacts.

## Goal

1. New backend endpoint `GET /api/v1/admin/m1/extraction/pdf-records` — paginated, filter-rich, returns a lean per-row shape (no `raw_text`/`cleaned_text` payloads).
2. New admin page `/admin/m1/pdf-records` — filter bar + table + pagination, links into existing `/raw-pdf` download and `/admin/m1/pipeline/trace/<id>` detail.
3. Sidebar nav entry + i18n labels.

## Steps / tasks

### Backend

1. ✅ **Schemas** — Added `PdfRecordOut` (lean row shape, drops raw_text/cleaned_text in favour of `*_length` counts) and `PdfRecordsListOut` (`items`, `total`, `page`, `page_size`, `server_time`) to `enigmatrix-backend/app/schemas/m1_pipeline.py`.
2. ✅ **Endpoint** — Added `GET /api/v1/admin/m1/extraction/pdf-records` to `enigmatrix-backend/app/api/v1/m1_gazette_extraction.py`. Query params: `source_id`, `status` (aliased — Python keyword), `language`, `date_from`, `date_to`, `search` (substring match, case-insensitive, against `gazette_number` OR `regulation_short_code`), `page` (default 1, min 1), `page_size` (default 50, min 1, max 200). Sort: `gazette_published_date DESC NULLS LAST, created_at DESC`. Count query uses the same WHERE-condition list as the page query so pagination is never inconsistent. Behind `require_admin`. Imports added: `PdfRecordOut`, `PdfRecordsListOut` from schemas.

### Frontend

3. ✅ **API client** — Added `PdfRecord`, `PdfRecordsListOut`, `PdfRecordsFilters` interfaces and `listPdfRecords(token, filters)` method on `M1GazetteExtractionApi` in `enigmatrix-frontend/lib/api/m1-gazette-extraction.ts`. Builds a `URLSearchParams` query string from the filters dict.
4. ✅ **Page (initial draft)** — Created `enigmatrix-frontend/app/(admin)/admin/m1/pdf-records/page.tsx` (NEW, ~350 lines). Filter bar with 6 controls (source dropdown, status dropdown, language dropdown, date_from, date_to, search input). Draft-vs-applied filter state pattern: typing in the search box updates `draftFilters` but doesn't refetch; pressing Apply (or Enter on the search input) copies into `appliedFilters` which is the actual query key. Responsive table with `formatBytes` / `formatDate` / `statusTone` helpers inline. Per-row actions: `ExternalLink` icon to source URL, `Download` icon to `/raw-pdf` endpoint, `Eye` icon to existing trace page. Loading skeleton, error state, empty state with concrete next-step copy. Pagination (Previous/Next + page-of-total). `export const dynamic = "force-dynamic"`.
   - **Note (subsequent rework):** the page was subsequently refactored (by user/linter) to use the project's shared `AdminPageLayout` with a sticky filter sidebar, the `Combobox` primitive for single-select dropdowns, `Pagination` component, project `Table` components instead of raw `<table>`, the new `useAuthToken()` hook, and the shared `pipelineStatusTone` utility (the kind of consolidation that Stage 4 follow-up #21 was intended to drive). The filter UX also flipped from "draft-vs-applied for all" to "immediate-apply for dropdowns/dates, Enter-to-apply for search" — closer to how Users page works. The endpoint contract and visible columns are unchanged.
5. ✅ **Sidebar nav** — Added a fifth `NavItem` to `ADMIN_M1_PIPELINE_ITEMS` in `enigmatrix-frontend/components/layout/sidebar.tsx`: `{ href: "/admin/m1/pdf-records", label: "nav.adminM1PdfRecords", icon: FileText }`.
6. ✅ **i18n** — Added `"adminM1PdfRecords": "PDF Records"` to the `nav` block in `enigmatrix-frontend/lib/i18n/messages/en.json`, `si.json`, `ta.json`. The Sinhala/Tamil entries keep the English string for now, matching the existing untranslated-admin-nav pattern (Sinhala/Tamil translation is tracked as follow-up #20).

## Errors fixed (during implementation)

- None during the writes themselves.

## Technical notes

- **Why a new endpoint instead of reusing `/progress`** — `/progress` requires `date_from`+`date_to` and is hard-coded to filter within `since` (the trigger's `queued_at`). A browse-all view needs all filters optional and sorted by gazette date, not creation date. Different consumer, different sort key, different filter set — separate endpoint is cleaner.
- **`status` query param alias** — `status` collides with FastAPI's `status` module import in the endpoint file. Used `Query(None, alias="status")` and renamed the Python variable to `status_filter`.
- **Index-friendly query** — `gazette_published_date` is already indexed in the existing migration chain. The default sort (`gazette_published_date DESC NULLS LAST`) hits the index. Search uses ILIKE which is sequential but bounded by `min_length=1, max_length=100` on the param and by pagination — acceptable at current row counts.
- **Pagination over cursor** — Operators want shareable links (`?page=3&source_id=BILL`) and stable counts; cursor pagination would lose the `total` headline. Pagination cap at `page_size=200` keeps the response size bounded.
- **Sidebar `nav.adminM1PdfRecords` key** — Matches the existing camelCase nav-key pattern (`adminM1Overview`, `adminM1Steps`, etc.).

## Decisions taken

- **Lean `PdfRecordOut` shape** — Drops `raw_text` + `cleaned_text` payloads. The browse view never displays the text body; if an operator wants it, the existing `/pipeline/trace/<regulation_id>` page handles the heavy data.
- **`force-dynamic` route segment** — The list is read from live DB; no benefit to caching at the Next.js layer.
- **Empty-state copy with concrete next steps** — Per the design-skills guidance, copy reads "Try widening the date range, clearing the search, or picking All sources" rather than a vague "No results".
- **Action button affordances** — Three icon-only per-row actions (external link, download, view) with `title` tooltips. Accessible-label gap on the icons was flagged by Stage 4 audit (frontend agent finding) but kept LOW severity since the title attribute does screen-reader fallback.

## Open questions

- Should the table support multi-select + bulk actions (bulk re-extract, bulk delete)?
- Should the page wire up the WebSocket live feed (Session 46 / F-173) so newly-arriving rows appear without a full refetch?
- Should the search filter expand to include `last_error` substring search (useful for triaging extraction failures)?
- Should the column set be operator-configurable (column-toggle dropdown), or kept fixed for now?

## Acceptance criteria

- [x] `GET /api/v1/admin/m1/extraction/pdf-records` returns paginated rows with `source_id` / `status` / `language` / `date_from` / `date_to` / `search` filters.
- [x] `/admin/m1/pdf-records` page renders with filter bar + table + pagination.
- [x] Per-row "Download" link opens the PDF via the existing `/raw-pdf` endpoint.
- [x] Per-row "Open original" link goes to `row.source_url` in a new tab.
- [x] Per-row "View trace" link goes to `/admin/m1/pipeline/trace/<regulation_id>`.
- [x] Sidebar shows "PDF Records" under M1 Pipeline group.
- [x] i18n keys present in en/si/ta JSON.
- [x] Empty / loading / error states render cleanly with concrete next-step copy.

## Linked trackers

- [CHANGES.md](../CHANGES.md) — F-197
- [FEATURES.md](../FEATURES.md) — F-197
- [SESSIONS.md](../SESSIONS.md) — Session 55
- Dependency: [2026-05-22_Plan Per-PDF metadata schema and population](./2026-05-22_Plan%20Per-PDF%20metadata%20schema%20and%20population.md) — supplies file_size_bytes / sha256 / pdf_pages / language fields rendered here
- Related: [2026-05-22_Plan Cross-repo code quality audit — Stage 4](./2026-05-22_Plan%20Cross-repo%20code%20quality%20audit%20—%20Stage%204.md) — flagged the consolidation that drove the subsequent page refactor (useAuthToken, pipelineStatusTone, AdminPageLayout)
