# Plan: M1 pipeline admin UX audit — 14 findings report

## Context

A hands-on UX/UI audit of every page under `/admin/m1/pipeline` was conducted via the Claude-in-Chrome MCP extension (localhost:3000) logged in as `admin@enigmatrix.lk`. The audit used `javascript_tool` and computer screenshots (the Chrome extension's `find` / `read_page` tools are blocked for localhost due to `host_permissions` in the extension manifest). Network requests were inspected via `read_network_requests`.

The session spanned two chat contexts (context-compaction between the testing phase and the report-generation phase). Testing was completed first; the Word document was generated in the continuation session on 2026-05-22.

## Goal

Identify every UX/UI defect, confusing state, missing feedback pattern, or accessibility gap across the six M1 pipeline admin areas:
- Overview (`/admin/m1/pipeline`)
- Trace (`/admin/m1/pipeline/trace`)
- Recent Runs standalone page (`/admin/m1/pipeline/recent`)
- Raw Extraction (`/admin/m1/pipeline/extraction`)
- Gazette Table (within extraction)
- Step Detail pages (`/admin/m1/pipeline/steps/[id]`, steps 2a–2f)

Produce a Word document deliverable summarising all findings with severity, problem, recommendation, and impact.

## Findings (14 total)

| ID | Severity | Page | Title |
|----|----------|------|-------|
| F-01 | Medium | Overview | Misleading "Paused - no data yet" badge when pipeline is idle |
| F-02 | Medium | Overview -- Funnel | Funnel conversion rates exceed 100% (7,700% and 1,283%) |
| F-03 | Low | Overview -- Celery Widget | QUEUED count overflows and is clipped |
| F-04 | Low | Overview -- Run Table | "Details ->" links have no hover affordance |
| F-05 | Medium | Step Detail Pages (2a-2f) | No previous / next navigation between step detail pages |
| F-06 | **Critical** | Recent Runs (standalone) | HTTP 503 on every load — completely non-functional |
| F-07 | High | Trace -- Step Timeline | Failed-run steps mislabelled "pending"; duplicate "Step 2b" |
| F-08 | Medium | Trace -- Recent Runs Table | Table only populates after user clicks the search box |
| F-09 | High | Raw Extraction | "Reconcile all raw folders" executes with no confirmation |
| F-10 | High | Raw Extraction | "Start Extraction" buttons give no loading state or feedback |
| F-11 | Medium | Raw Extraction -- Source Cards | Stale badge uses same amber for daily AND weekly sources |
| F-12 | High | Raw Extraction -- Error States | Extraction failure exposes full server path + typo "Reasearch" |
| F-13 | Low | Gazette Table -- Row Actions | Row action icons have no labels or tooltips |
| F-14 | Low | Gazette Table -- Date Filter | Date filter uses US mm/dd/yyyy, not dd/mm/yyyy |

Severity counts: Critical 1 · High 4 · Medium 6 · Low 3.

## Positive findings

Seven strengths observed and documented in the report:

1. Live auto-refresh (5-second polling) keeps pipeline status current without manual reloads.
2. Polling correctly pauses when the browser tab is hidden.
3. Celery Broker card provides at-a-glance worker and queue-depth visibility.
4. Six-step pipeline modelled clearly with named stages (2a-2f) and per-step detail pages.
5. Trace page search filters (date range, status, source type) cover common audit queries.
6. Colour-coded severity badges give immediate visual triage cues.
7. Funnel widget concept (Raw -> Extracted -> Preprocessed) is the right mental model.

## Steps / tasks

1. ✅ Navigate to localhost:3000, log in as admin@enigmatrix.lk / admin12345.
2. ✅ Discover correct sub-routes via Survey Management menu + `javascript_tool` DOM enumeration.
3. ✅ Test all six functional areas; capture screenshots; inspect network requests.
4. ✅ Compile 14 findings with severity ratings.
5. ✅ Generate Word document (`ux_report.py` / python-docx; npm docx blocked by registry 403).
6. ✅ Save `M1_Pipeline_UX_Audit.docx` to workspace.

## Technical notes

- `npm install docx` blocked: npmjs.org returned 403 Forbidden in the Cowork sandbox. Switched to `python-docx` v1.2.0 (already installed).
- `ux_report.py` was written with curly-quote string literals that caused `SyntaxError: invalid character`. Fixed via byte-level Unicode replacement (b'\xe2\x80\x9c' → b'\\"' etc.).
- Chrome extension `find` / `read_page` tools fail on localhost with "Extension manifest must request permission to access the respective host." Workaround: `javascript_tool` for DOM queries, `computer` tool for screenshots and navigation.
- `/admin/m1/pipeline` direct navigation redirects to `/admin/regulations` without menu interaction; the pipeline sub-menu is only revealed by clicking Survey Management in the sidebar.
- Failed rows in the Overview run table have no ">" (chevron) navigation icon; only `preprocessed` rows have it. This is a gap — no drill-down path for failed runs from the table.

## Decisions taken

- Used python-docx instead of npm docx package; same output quality, pure Python.
- Word document output path: `C:\Users\Administrator\Documents\Claude\Projects\Understanding Information Barriers to Regulatory Compliance Among Sri Lankan SMEs\M1_Pipeline_UX_Audit.docx`
- F-IDs in this plan refer to the UX audit finding numbers (not FEATURES.md F-IDs).
- FEATURES.md F-ID assigned to the audit deliverable: **F-184**.

## Open questions

- F-06 (503 on /recent): which backend service/endpoint is the RSC data source? Needs backend investigation.
- F-12: Is the "Reasearch" typo in the production directory name or only a dev path? If production, it is a path-rename operation.
- F-09: Is the Reconcile operation reversible? If not, priority should be Critical, not High.

## Acceptance criteria

- [x] All six pipeline admin pages tested with live data.
- [x] All 14 findings documented with severity, problem, recommendation, impact.
- [x] Word document produced and saved to workspace.

## Linked trackers

- [CHANGES.md](../CHANGES.md) — ux_report.py + M1_Pipeline_UX_Audit.docx entries
- [FEATURES.md](../FEATURES.md) — F-184
- [SESSIONS.md](../SESSIONS.md) — Session 53
- [BUILD_PLAN_COVERAGE.md](../BUILD_PLAN_COVERAGE.md) — Session 53 add-on
- [RESEARCH_BUILD_TRACKER.md](../RESEARCH_BUILD_TRACKER.md) — M1 Pipeline UX audit
