# Enigmatrix Frontend — Pages Feature Map

**Date:** 2026-05-20
**Codebase:** `enigmatrix-frontend` (Next.js 14, App Router)
**Author:** Generated via static analysis of `app/**/page.tsx`

## Introduction

Enigmatrix is a regulatory-intelligence platform built for Sri Lankan SMEs. It collects survey data across four research modules — M1 (Regulatory Awareness Gap), M2 (Knowledge Accuracy), M3 (Risk & Vulnerability), and M4 (Misinformation Spread) — to measure and analyse regulatory compliance barriers. The frontend is a Next.js 14 application using the App Router, React Server Components, Tailwind CSS, shadcn/ui primitives, and TanStack Query for client-side data fetching. Authentication is session/cookie-based (`/api/auth/establish`), and access is split between three roles: **public** (unauthenticated), **SME user** (authenticated, role = `sme`), and **admin** (role = `admin`).

---

## Summary Table

| URL Path | Access Level | Purpose |
|---|---|---|
| `/` | Public | Root redirect (inferred) |
| `/login` | Public | Email + password sign-in |
| `/register` | Public | SME account registration with sector/profile |
| `/dashboard` | Authenticated (SME + Admin) | Welcome hub with stat cards, pending tasks, recent activity |
| `/regulations` | Authenticated SME | Browse all active regulations; launch regulation-scoped survey |
| `/surveys` | Authenticated SME | Survey hub — pick full or per-module survey; view recent sessions |
| `/surveys/unified` | Authenticated SME | Full 4-module unified survey flow (~20 questions) |
| `/surveys/module/[id]` | Authenticated SME | Single-module survey for m1/m2/m3/m4 |
| `/surveys/regulation/[id]` | Authenticated SME | Regulation-scoped survey flow (questions for one regulation) |
| `/surveys/history` | Authenticated SME | Paginated table of all survey sessions |
| `/risk` | Authenticated SME | M2 knowledge score + M3 compliance risk signals display |
| `/qa` | Authenticated SME | Coming-soon placeholder for RAG-based Q&A |
| `/verify` | Authenticated SME | Coming-soon placeholder for claim-verification (M4) |
| `/profile` | Authenticated SME | Read-only display of account + SME profile fields |
| `/docs` | Authenticated (any) | Documentation index — links to app guide, M1 docs, setup |
| `/docs/m1` | Authenticated (any) | Module 1 research documentation with pipeline, RQs, findings |
| `/docs/m1/[section]` | Authenticated (any) | Individual M1 doc section page (dynamic slug) |
| `/docs/[...slug]` | Authenticated (any) | Catch-all MDX/markdown doc page renderer |
| `/admin/regulations` | Admin | List all regulations with filters; CRUD entry point |
| `/admin/regulations/[id]/edit` | Admin | Edit a regulation record + view linked questions |
| `/admin/regulations/[id]/flow` | Admin | Visual flow canvas — link questions to a regulation |
| `/admin/regulations/new` | Admin | Create new regulation |
| `/admin/regulations/[id]/authoring` | Admin | Authoring view for a regulation (separate flow) |
| `/admin/surveys` | Admin | List all survey configs with filters |
| `/admin/surveys/[id]` | Admin | Edit a survey config |
| `/admin/surveys/[id]/questions` | Admin | Manage questions for a specific survey |
| `/admin/surveys/new` | Admin | Create new survey |
| `/admin/surveys/awareness/responses` | Admin | Browse awareness survey responses |
| `/admin/survey/regulations` | Admin | Survey-regulation mapping view |
| `/admin/questions` | Admin | List/filter all survey questions (all modules) |
| `/admin/questions/[code]/edit` | Admin | Edit a question by code |
| `/admin/questions/new` | Admin | Create new question |
| `/admin/users` | Admin | List/filter all registered users with SME profiles |
| `/admin/m1/pipeline` | Admin | M1 pipeline overview — live metrics, funnel, Celery health |
| `/admin/m1/pipeline/sources` | Admin | Source hub — four gazette source tiles with stats |
| `/admin/m1/pipeline/sources/[sourceId]/extraction` | Admin | Per-source extraction workspace (trigger, monitor, cancel) |
| `/admin/m1/pipeline/steps` | Admin | Six pipeline step index with live counts |
| `/admin/m1/pipeline/steps/[stepId]` | Admin | Step detail page with code refs and recent runs |
| `/admin/m1/pipeline/recent` | Admin | Latest 50 pipeline runs table with live polling |
| `/admin/m1/pipeline/trace` | Admin | Trace index — search or pick a regulation to trace |
| `/admin/m1/pipeline/trace/[regulationId]` | Admin | Full pipeline trace for one regulation (timeline, content diff, penalties) |
| `/admin/m1/pipeline/extraction` | Admin | Legacy extraction page (global, not per-source) |
| `/admin/m1/pdf-records` | Admin | Browse all gazette PDF records with filters |
| `/admin/m2/scores` | Admin | M2 knowledge scores table across all SMEs |
| `/admin/m2/questions` | Admin | M2 knowledge questions — filter, view, verify by chartered accountant |
| `/admin/m3/risk-signals` | Admin | M3 risk signals table across all SMEs |
| `/admin/activity-log` | Admin | Audit log — all platform events with filters |
| `/admin/settings` | Admin | Platform settings — survey submission limits per role |
| `/admin/annotation` | Admin | Annotation tool (separate flow) |
| `/admin/datasets` | Admin | Dataset management |
| `/admin/models` | Admin | ML model management |
| `/admin/training` | Admin | Model training controls |
| `/admin/translations` | Admin | Translation management for multilingual content |
| `/admin/research-log` | Admin | Research log landing — vault snapshot with heatmap and latest sessions |
| `/admin/research-log/sessions` | Admin | Full session timeline from Obsidian SESSIONS.md |
| `/admin/research-log/sessions/[sessionId]` | Admin | Individual session detail |
| `/admin/research-log/features` | Admin | Feature matrix from FEATURES.md with status per group |
| `/admin/research-log/features/[featureId]` | Admin | Feature detail page |
| `/admin/research-log/findings` | Admin | Research findings per module from Obsidian vault |
| `/admin/research-log/findings/[module]/[slug]` | Admin | Individual finding detail |
| `/admin/research-log/changes` | Admin | Changelog view from vault |
| `/admin/research-log/ideas` | Admin | Research ideas / open questions |
| `/admin/research-log/build-tracker` | Admin | Per-module engineering build progress |
| `/app/admin/survey/questions` | Admin (app-group route) | Survey question list under app route group |

---

## Detailed Page Sections

---

### 1. Auth Pages

#### `/login`
- **Access:** Public
- **Purpose:** Authenticates an existing user (SME or admin) and establishes a session cookie.
- **Key Features:**
  - Split-panel layout: left side shows animated DotMap with Enigmatrix branding; right side shows the sign-in form.
  - Email + password form with react-hook-form + Zod validation (`loginSchema`).
  - Password visibility toggle.
  - On success: calls `/api/auth/establish` (POST) to set the session cookie, then `/api/auth/me` to determine role; redirects admins to `/admin/regulations`, SMEs to `/dashboard`. Supports a `?next=` redirect param.
  - Inline error alert on failure.
  - Framer Motion entrance animations; shimmer hover on submit button.
- **API Calls:**
  - `AuthApi.login(email, password)` — POST to backend auth endpoint.
  - `fetch("/api/auth/establish", POST)` — Next.js API route to write cookie.
  - `fetch("/api/auth/me")` — Next.js API route to read current user role.
- **Key Components:** `DotMap`, `Input`, `Button`, `Alert`, `Label` (shadcn/ui), react-hook-form.

---

#### `/register`
- **Access:** Public
- **Purpose:** Creates a new SME account and immediately logs in, redirecting to `/dashboard`.
- **Key Features:**
  - Two-column layout with DotMap branding panel.
  - Multi-field registration form (email, password, confirm password, language, sector, sub-sector, employee band, turnover band, business age, region).
  - Sector options: retail, food & beverage, garment, IT services, transport, agriculture, construction, services_other.
  - Region options: all nine Sri Lankan provinces.
  - Language options: English, Sinhala (සිංහල), Tamil (தமிழ்).
  - Inline validation via Zod `registerSchema`; 2-column grid layout on wider screens.
  - Auto-login on success before redirect.
- **API Calls:**
  - `AuthApi.register({email, password, preferred_language, profile})` — POST to backend register endpoint.
  - `AuthApi.login(email, password)` — POST to auto-login.
  - `fetch("/api/auth/establish", POST)` — set cookie.
- **Key Components:** `DotMap`, `Select`, `Input`, `Button`, `Alert` (shadcn/ui).

---

### 2. SME App Pages

#### `/dashboard`
- **Access:** Authenticated (SME + Admin)
- **Purpose:** Main landing page after login. Provides a personalised overview of the user's compliance status, outstanding tasks, and recent activity.
- **Key Features:**
  - Welcome banner with quick-action CTAs (Take Survey, View Risk, Manage Regulations for admins).
  - Four stat cards: Knowledge Score (M2 overall %), Risk Signal Count (M3), Survey Progress (answered/total questions), and either Total Regulations (admin) or Last Survey Date (SME).
  - Pending regulations widget (up to 3 regulations the SME has not yet assessed) using `RegulationCard`.
  - Pending tasks panel: links to continue survey if in-progress, or take knowledge survey if score is missing.
  - Recent activity panel: shows last survey submission date with CheckCircle icon.
  - Server component (`force-dynamic`); all data fetched in parallel on the server.
- **API Calls (server-side parallel fetches):**
  - `M2Api.knowledgeScore(smeId, token)` — GET M2 score.
  - `M3Api.riskSignals(smeId, token)` — GET M3 risk signals.
  - `SurveyFlowApi.start(token)` — GET current survey flow state.
  - `RegulationsApi.list({size:1}, token)` — admin only, GET regulation count.
  - `DashboardApi.pendingRegulations(3, token)` — GET top-3 pending regulations.
- **Key Components:** `PageHeader`, `RegulationCard`, `Card`, `Badge`, `Button`.

---

#### `/regulations`
- **Access:** Authenticated SME
- **Purpose:** Browse all active regulations published on the platform; each card links to a regulation-scoped survey.
- **Key Features:**
  - Grid of regulation cards: shows short code badge, domain badge, severity badge, effective date, English title and summary, and a "Take Survey" CTA button.
  - Empty state with guidance to contact admin if no regulations yet.
  - Up to 50 regulations loaded server-side (`include_archived: false, size: 50`).
- **API Calls:**
  - `RegulationsApi.list({include_archived: false, size: 50}, token)` — GET list of active regulations.
- **Key Components:** `DomainBadge`, `SeverityBadge`, `Card`, `Button`, `Badge`.

---

#### `/surveys`
- **Access:** Authenticated SME
- **Purpose:** Survey hub — entry point for starting a new survey session (full or per-module) and reviewing recent session history.
- **Key Features:**
  - Submission counter banner showing used/remaining/limit if a limit is configured.
  - In-progress session banner with yellow pulse indicator and "Continue" CTA.
  - Hero CTA card for the Full Survey (all 4 modules, ~15-20 questions, ~12 min).
  - Four per-module cards: M1 Awareness Gap, M2 Knowledge Accuracy, M3 Risk & Severity, M4 Info Spread.
  - All CTAs are disabled (locked) when the submission limit has been reached.
  - Recent sessions mini-table (up to 3 rows) showing type, date, status badge; "View all" link to history.
- **API Calls:**
  - `SurveyFlowApi.getMyHistory(token)` — GET current user's session list.
- **Key Components:** `StatusBadge`, `Card`, `Button`, `Link`.

---

#### `/surveys/unified`
- **Access:** Authenticated SME
- **Purpose:** Launches the unified full survey covering all four research modules (up to 20 questions).
- **Key Features:**
  - Minimal page wrapper with module-mode label and description.
  - Delegates all state to `SurveyLauncher` component with `mode="unified"`.
- **API Calls:** All API calls handled inside `SurveyLauncher` (survey flow start/submit via `SurveyFlowApi`).
- **Key Components:** `SurveyLauncher`.

---

#### `/surveys/module/[id]`
- **Access:** Authenticated SME
- **Purpose:** Launches a single-module survey. The `[id]` param is one of `m1`, `m2`, `m3`, `m4`; any other value returns 404.
- **Key Features:**
  - Module-specific title and description displayed above the survey launcher.
  - Per-module survey modes: `per_module_m1` through `per_module_m4`.
  - 404 on unrecognised module ID.
- **API Calls:** Handled inside `SurveyLauncher`.
- **Key Components:** `SurveyLauncher`.

---

#### `/surveys/regulation/[id]`
- **Access:** Authenticated SME
- **Purpose:** Regulation-scoped survey flow — only asks questions linked to a specific regulation. Navigated to from the Regulations page or Pending Regulations widget.
- **Key Features:**
  - Fetches regulation metadata (title, short code, summary) for display context.
  - Calls `SurveyFlowApi.start(token, {regulation_id})` to scope the question engine.
  - Passes regulation context to `SurveyWizard`.
  - Shows error card if regulation or flow cannot be loaded.
- **API Calls:**
  - `RegulationsApi.getPublic(id, token)` — GET regulation metadata.
  - `SurveyFlowApi.start(token, {regulation_id})` — POST/GET to start scoped flow.
- **Key Components:** `SurveyWizard`, `Card`.

---

#### `/surveys/history`
- **Access:** Authenticated SME
- **Purpose:** Full history of all survey sessions for the current user.
- **Key Features:**
  - Table with columns: Survey Type, Started date, Status badge, Questions Answered (inline progress bar), and Action (Continue / View Summary).
  - Status badges: Completed (success), In Progress (pending), Abandoned (neutral).
  - Per-row progress bar showing answered / cap questions.
  - "Continue" button for in-progress sessions; `ViewSummaryButton` for completed sessions.
  - Empty state with "Start a survey" link.
- **API Calls:**
  - `SurveyFlowApi.getMyHistory(token)` — GET all session history items.
- **Key Components:** `StatusBadge`, `ViewSummaryButton`, `Button`.

---

#### `/risk`
- **Access:** Authenticated SME (requires `sme_id` on profile)
- **Purpose:** Displays the SME's compliance risk profile: M2 knowledge score breakdown and M3 compliance history + behavioural signals.
- **Key Features:**
  - M2 Knowledge Score card (module-m2 colour theme): overall % badge (green ≥70%, amber ≥40%, red otherwise), per-domain breakdown (correct/n/%).
  - M3 Vulnerability card (module-m3 colour theme): compliance history (missed deadlines, penalty received, under audit, self-confidence), top barriers as badges (time, cost_accountant, complex_rules, language_barrier, etc.), filing method.
  - Empty states with links to take the relevant module survey.
  - Guard: redirects to "complete registration" message if no `sme_id`.
- **API Calls:**
  - `M3Api.riskSignals(smeId, token)` — GET combined M3 + M2 risk snapshot.
- **Key Components:** `Card`, `StatusBadge`, `Badge`, `Button`.

---

#### `/qa`
- **Access:** Authenticated SME
- **Purpose:** Placeholder for the future RAG-based "Ask" feature (Module 2 Q&A).
- **Key Features:** Single `ComingSoon` component; build reference linked to `BUILD_08_Module2_Knowledge.md`.
- **API Calls:** None.
- **Key Components:** `ComingSoon`.

---

#### `/verify`
- **Access:** Authenticated SME
- **Purpose:** Placeholder for the future claim-verification feature (Module 4 Misinformation).
- **Key Features:** Single `ComingSoon` component; build reference linked to `BUILD_10_Module4_Misinformation.md`.
- **API Calls:** None.
- **Key Components:** `ComingSoon`.

---

#### `/profile`
- **Access:** Authenticated (any)
- **Purpose:** Read-only display of the current user's account details and SME profile.
- **Key Features:**
  - Divided list: Email, Role, Language, Sector, Sub-sector, Region, Employee Band, Turnover Band.
  - Only non-null fields are shown.
  - Footer note: profile editing deferred to a future release.
- **API Calls:** None (data loaded from session via `requireUser()`).
- **Key Components:** None beyond standard layout.

---

#### `/docs`
- **Access:** Authenticated (any)
- **Purpose:** Documentation index page with cards linking to the major doc sections.
- **Key Features:**
  - Five section cards: Application Guide, Module 1 Documentation, Unified Survey Configuration, Research & Build Tracker, Setup & Architecture.
  - Each card is a Link with an icon, title, and description.
- **API Calls:** None.
- **Key Components:** `PageHeader`, `Card`.

---

#### `/docs/m1`
- **Access:** Authenticated (any)
- **Purpose:** Comprehensive Module 1 (Regulatory Awareness Gap) research documentation page.
- **Key Features:**
  - Hero section with M1 status badge, abstract, and 5 status metric tiles.
  - Key Metrics at a Glance: `M1StatsCounter` animated counter component.
  - Seven-Stage Processing Pipeline: `M1Pipeline` interactive diagram.
  - Research Questions: four RQ cards with method and success criterion.
  - Regulatory Diffusion Timeline: `M1Timeline`.
  - Research Findings: grid of finding cards with statistical test and expected result.
  - Architecture Layers reference table: layer, components, technology.
  - Happy Path reference table: elapsed time, event, component.
  - Inter-Module Connections: three connection cards (M1 → M2/M3/M4).
  - Technology Choices reference table.
  - Database Entities grid.
  - Module 1 Documentation Pages: `M1SectionGrid`.
  - Tracking Workflows: `M1TrackingWorkflows` (8 surfaces, 4 admin + 4 SME).
  - Tracking Map: `M1TrackingMap` (clickable route boxes).
  - Uses `DocsLayout` with a sidebar nav from `getDocsNav()`.
- **API Calls:** None (static data from `@/lib/m1-docs`).
- **Key Components:** `DocsLayout`, `M1Pipeline`, `M1Timeline`, `M1StatsCounter`, `M1TrackingWorkflows`, `M1TrackingMap`, `M1SectionGrid`, `PageHeader`.

---

#### `/docs/m1/[section]` and `/docs/[...slug]`
- **Access:** Authenticated (any)
- **Purpose:** Dynamic MDX/markdown documentation page renderers for M1 sub-sections and general docs.
- **Key Features:** Section-specific content rendering within the DocsLayout navigation context.
- **API Calls:** File system read via `getDocsNav()` / `getM1DocSection()`.

---

### 3. Admin Pages — Regulations & Surveys

#### `/admin/regulations`
- **Access:** Admin
- **Purpose:** Main regulations list — browse, filter, search, and navigate to CRUD actions.
- **Key Features (inferred from `AdminRegulationsClient`):**
  - Paginated table with filters (domain, severity, sector, status, search).
  - Columns: short code, title, domain badge, severity badge, sector badge, effective date, verification badge, action buttons.
  - Links to Edit, Flow Canvas, and Authoring pages.
  - Skeleton loading via `SkeletonRouteShell`.
- **API Calls:** `RegulationsApi.list(...)` with filter params.
- **Key Components:** `AdminRegulationsClient` (client component), `SkeletonRouteShell`.

---

#### `/admin/regulations/[id]/edit`
- **Access:** Admin
- **Purpose:** Edit a regulation record; view linked questions.
- **Key Features:**
  - PageHeader with regulation title, short code breadcrumb, verification badge, and link to Flow Canvas.
  - Expert-verified metadata card (verified by / at).
  - `AuthorshipMeta` (created/updated by/at with link to activity log).
  - `RegulationForm` in edit mode — fields: short code, title (en/si/ta), summary, domain, severity, sector, effective date, amendment type, penalty range, principal act.
  - `LinkedQuestionsPanel` — shows all survey questions linked to this regulation.
- **API Calls:**
  - `RegulationsApi.get(id, token)` — GET single regulation.
  - Form submit: `RegulationsApi.update(...)` via `RegulationForm`.
- **Key Components:** `RegulationForm`, `LinkedQuestionsPanel`, `AuthorshipMeta`, `VerificationBadge`, `PageHeader`.

---

#### `/admin/regulations/[id]/flow`
- **Access:** Admin
- **Purpose:** Visual drag-and-drop flow canvas to link survey questions to a regulation and set question order/conditions.
- **Key Features:**
  - Server component fetches regulation + questions grouped by regulation (`AdminSurveyQuestionsApi.byRegulation`).
  - Delegates to `FlowCanvas` client component for interactive editing.
  - Header shows regulation short code and verification badge; Back button to edit page.
- **API Calls:**
  - `RegulationsApi.get(id, token)` — GET regulation.
  - `AdminSurveyQuestionsApi.byRegulation(id, token)` — GET questions grouped by this regulation.
- **Key Components:** `FlowCanvas`, `VerificationBadge`, `PageHeader`.

---

#### `/admin/surveys`
- **Access:** Admin
- **Purpose:** List all survey configurations with module/sector filters.
- **Key Features (from `AdminSurveysClient`):**
  - Filterable, paginated table of surveys.
  - Module badge, sector badge, active/archived status badge.
  - Links to edit survey and manage its questions.
- **API Calls:** `AdminSurveysApi.list(...)`.
- **Key Components:** `AdminSurveysClient`, `SkeletonRouteShell`.

---

#### `/admin/surveys/[id]`
- **Access:** Admin
- **Purpose:** Edit a survey's configuration (title, module, sector, active flag, etc.).
- **Key Features:**
  - Module badge, sector badge, active/archived badge in header.
  - Buttons: Questions (link to question manager), Back.
  - `AuthorshipMeta` with link to activity log.
  - `SurveyConfigForm` in edit mode.
- **API Calls:**
  - `AdminSurveysApi.get(id, token)` — GET survey.
  - Form submit via `SurveyConfigForm`.
- **Key Components:** `SurveyConfigForm`, `AuthorshipMeta`, `ModuleBadge`, `SectorBadge`, `ActiveStateBadge`.

---

#### `/admin/questions`
- **Access:** Admin
- **Purpose:** View and manage all survey questions across all modules.
- **Key Features (from `AdminQuestionsClient`):**
  - Filterable, searchable, paginated table.
  - Columns: code, module, domain, sector, format, prompt, regulation links, translation status, verification status.
  - Action buttons: Edit, Duplicate, Delete.
  - Filter sidebar: module, domain, sector, translation status, verification status, text search.
- **API Calls:** `AdminSurveyQuestionsApi.list(...)` with filters.
- **Key Components:** `AdminQuestionsClient`, `SkeletonRouteShell`.

---

#### `/admin/users`
- **Access:** Admin
- **Purpose:** Browse and manage all registered users and their SME profiles.
- **Key Features (from `AdminUsersClient`):**
  - Filterable, paginated user table.
  - Columns: email, role, sector, region, language, employee band, join date, actions.
  - Admin can update user role/details.
  - Filter sidebar: role, sector, region.
- **API Calls:** `UsersApi.list(...)` with filters; `UsersApi.update(...)`.
- **Key Components:** `AdminUsersClient`, `SkeletonRouteShell`.

---

### 4. Admin Pages — M1 Pipeline

#### `/admin/m1/pipeline`
- **Access:** Admin
- **Purpose:** Live M1 gazette ingestion and extraction pipeline overview — the primary monitoring dashboard.
- **Key Features:**
  - Auto-refreshes every 5 seconds (paused when tab is not visible) via `usePageVisible` + TanStack Query `refetchInterval`.
  - Phase 2 status banner (shipped badge with ML/backend test counts).
  - Four hero metric tiles: Total regulations, Throughput 24h, Error rate 24h, Celery active tasks.
  - `PipelineFlowDiagram` — visual flowchart showing counts at each pipeline status.
  - `ThroughputChart` — extracted/preprocessed counts for 24h and 7d.
  - `StatusDistribution` — bar/donut chart of current status breakdown.
  - `FunnelChart` — conversion funnel from ingested through preprocessed.
  - Latest 5 runs table (`RecentRunsTable`).
  - `ErrorLogPanel` — recent extraction errors.
  - `CeleryHealthCard` — worker count, active tasks, queued tasks (Broker card).
  - `LivePollingIndicator` + `RefreshButton` in header.
- **API Calls:**
  - `M1PipelineApi.getOverview(token)` — GET pipeline overview (counts, throughput, errors, Celery).
  - `M1PipelineApi.getRecent(token, 5)` — GET latest 5 pipeline runs.
- **Key Components:** `PipelineFlowDiagram`, `ThroughputChart`, `StatusDistribution`, `FunnelChart`, `RecentRunsTable`, `ErrorLogPanel`, `CeleryHealthCard`, `LivePollingIndicator`, `RefreshButton`, `PageHeader`.

---

#### `/admin/m1/pipeline/sources`
- **Access:** Admin
- **Purpose:** Gazette source hub — four source tiles (EGZ, GZ, BILL, ACT) with stats and freshness badges.
- **Key Features:**
  - Polls every 30 seconds.
  - Per-source staleness thresholds: EGZ (daily), GZ (weekly), BILL/ACT (monthly) — prevents false-alarm stale badges.
  - Source card shows: display name, cadence badge, freshness badge (Fresh / Stale warnings), failure count badge, description, ingested count, preprocessed count, last run timestamp.
  - "Open extraction →" button links to `/admin/m1/pipeline/sources/[sourceId]/extraction`.
  - Needs Categorisation card for uncategorised PDFs.
  - "Reconcile all raw folders" button (with `ConfirmDialog`) via `M1GazetteExtractionApi.reconcile(token)`.
  - Reconcile result summary displayed inline.
- **API Calls:**
  - `M1GazetteExtractionApi.listSources(token)` — GET all sources with stats.
  - `M1GazetteExtractionApi.reconcile(token)` — POST reconcile all.
- **Key Components:** `PageHeader`, `ConfirmDialog`, `StatusBadge`, `Card`, `Button`, `Skeleton`.

---

#### `/admin/m1/pipeline/sources/[sourceId]/extraction`
- **Access:** Admin
- **Purpose:** Per-source extraction workspace — trigger, monitor, cancel, and resume gazette extractions for a specific source (EGZ, GZ, BILL, ACT).
- **Key Features (most complex page in the app):**
  - Shows `UnknownCategorizePanel` for `sourceId = UNKNOWN`.
  - Extraction history table (up to 50 runs from API, or localStorage as fallback).
  - Date range picker (within a single calendar year; validates year bounds).
  - "Start extraction" button (triggers Celery task via API); disabled during active run.
  - "Reconcile [source] folder" button gated behind `ConfirmDialog` (danger action).
  - Live task status card: polls every 5s (stops at terminal status), shows task ID, Celery status, date scope.
  - "Cancel & roll back" button (second `ConfirmDialog`): revokes task and deletes created rows/PDFs.
  - Cancel result card: shows revoked flag, deleted rows, deleted/skipped PDFs, errors.
  - `ResumeExtractionCard`: appears when terminal + rows stuck mid-pipeline (extracted or ingested rows not advanced).
  - `ExtractionSummaryCard`: shows status_counts summary (ingested/extracted/preprocessed/failed) for the active task scope.
  - `ExtractionProgressPanel`: per-PDF progress grid with scope toggle (this trigger vs all in date range).
  - Toast feedback for trigger success/failure (task ID shown), reconcile success/failure, cancel results.
  - localStorage write-through on trigger to show history immediately before API refresh.
- **API Calls:**
  - `M1GazetteExtractionApi.getSource(token, sourceId)` — GET source metadata.
  - `M1GazetteExtractionApi.listRuns(token, {sourceId, pageSize: 50})` — GET run history.
  - `M1GazetteExtractionApi.trigger(token, {source_id, date_from, date_to})` — POST start extraction.
  - `M1GazetteExtractionApi.getStatus(token, task_id)` — GET Celery task status (polled).
  - `M1GazetteExtractionApi.getSummary(token, trigger, ...)` — GET extraction summary counts.
  - `M1GazetteExtractionApi.cancel(token, task_id, ...)` — POST cancel + rollback.
  - `M1GazetteExtractionApi.reconcile(token, {sourceId})` — POST reconcile single source.
- **Key Components:** `ExtractionHistoryTable`, `DateRangePicker`, `ExtractionProgressPanel`, `ExtractionSummaryCard`, `ResumeExtractionCard`, `ConfirmDialog`, `StatusBadge`, `PageHeader`, toast.

---

#### `/admin/m1/pipeline/steps`
- **Access:** Admin
- **Purpose:** Index of all six pipeline steps (2a–2f) with live cumulative counts.
- **Key Features:**
  - Polls every 5 seconds when tab is visible.
  - Grid of 6 `StepTile` cards (steps 2a through 2f): each shows step ID, title, counter status (current point-in-time count), and `reachedCount` (cumulative, computed from all statuses that pass through this step).
  - Each tile links to the step detail page.
- **API Calls:**
  - `M1PipelineApi.getOverview(token)` — GET overview with `status_counts`.
- **Key Components:** `StepTile`, `LivePollingIndicator`, `RefreshButton`, `PageHeader`.

---

#### `/admin/m1/pipeline/steps/[stepId]`
- **Access:** Admin
- **Purpose:** Detail view for a single pipeline step (2a–2f): code references, test links, inputs/outputs, and filtered recent runs.
- **Key Features:**
  - Prev/Next navigation buttons between steps (1/6, 2/6, ... 6/6 counter).
  - `StepDetailCard` — shows step description, code ref, test ref, input/output status names, and live count.
  - Recent runs table filtered to runs that have reached this step.
  - Polls both overview (5s) and recent runs (10s).
- **API Calls:**
  - `M1PipelineApi.getOverview(token)` — GET for live count.
  - `M1PipelineApi.getRecent(token, 25)` — GET for recent runs table.
- **Key Components:** `StepDetailCard`, `RecentRunsTable`, `LivePollingIndicator`, `RefreshButton`, `PageHeader`.

---

#### `/admin/m1/pipeline/recent`
- **Access:** Admin
- **Purpose:** Latest 50 pipeline runs ordered by `updated_at`, with search and click-through to trace.
- **Key Features:**
  - Polls every 5 seconds when visible.
  - Error state handling: friendly card for HTTP 503 with Retry button and link to Trace page (F-06 fix).
  - `RecentRunsTable` with `showSearch=true` to filter by gazette number / short code inline.
  - Each row links to `/admin/m1/pipeline/trace/[regulationId]`.
- **API Calls:**
  - `M1PipelineApi.getRecent(token, 50)` — GET latest 50 runs.
- **Key Components:** `RecentRunsTable`, `LivePollingIndicator`, `RefreshButton`, `PageHeader`.

---

#### `/admin/m1/pipeline/trace`
- **Access:** Admin
- **Purpose:** Trace index — search for a regulation by UUID or pick from recent runs.
- **Key Features:**
  - UUID input field with "Open trace" submit (navigates to `/admin/m1/pipeline/trace/[id]`).
  - Recent runs table (25 rows, fetched on mount — F-08 fix) with search enabled.
  - Error card with Retry button if fetch fails (F-08 fix).
- **API Calls:**
  - `M1PipelineApi.getRecent(token, 25)` — GET recent runs on mount.
- **Key Components:** `RecentRunsTable`, `Input`, `Button`, `PageHeader`.

---

#### `/admin/m1/pipeline/trace/[regulationId]`
- **Access:** Admin
- **Purpose:** Full pipeline trace for a single regulation — shows every processing step, content, penalties, and sub-documents.
- **Key Features:**
  - Polls every 15 seconds (lighter than overview since most rows are terminal).
  - Header metadata card: status badge, amendment type, document type, extraction method, effective date, gazette published date, penalty range, principal act, raw PDF path.
  - `TraceTimeline` — visual timeline of 6 pipeline steps derived from timestamps and status.
  - Four tabs:
    - **Content**: `TraceContentDiff` — side-by-side raw text preview vs cleaned text preview with length stats.
    - **Penalties**: `TracePenaltiesTable` — structured penalty records extracted from the gazette.
    - **Sub-documents**: `TraceSubDocumentsGrid` — sub-document records from the gazette.
    - **Raw row**: JSON dump of the full regulation record.
  - Error card with regulation_id if fetch fails.
- **API Calls:**
  - `M1PipelineApi.getTrace(token, regulationId)` — GET full trace (regulation + penalties + sub_documents + timeline).
- **Key Components:** `TraceTimeline`, `TraceContentDiff`, `TracePenaltiesTable`, `TraceSubDocumentsGrid`, `RefreshButton`, `PageHeader`, `Tabs`.

---

#### `/admin/m1/pdf-records`
- **Access:** Admin
- **Purpose:** Browse all gazette PDF records ingested by the M1 pipeline, with detailed filters.
- **Key Features:**
  - Sticky filter sidebar via `AdminPageLayout`: Source (EGZ/GZ/BILL/ACT), Status (ingested/extracted/preprocessed/failed), Language (en/si/ta/unknown), Published date range.
  - Search bar (Enter-to-commit, not on every keystroke) for gazette number or short code.
  - Paginated table (server-side, 10 per page with size selector and quick-jumper): Source/Gazette, Published date, Status badge + last_error, Language, Pages, File size, Extraction method.
  - Per-row action icons: External Link (source URL), Download PDF (gazette portal `download_url`), View trace (Eye icon → `/admin/m1/pipeline/trace/[id]`).
  - All icons have `aria-label` and `title` attributes (F-13 fix).
  - Date filter locale: dd/mm/yyyy (F-14 fix).
  - Total count badge in page header.
- **API Calls:**
  - `M1GazetteExtractionApi.listPdfRecords(token, filters)` — GET paginated PDF records with filters.
- **Key Components:** `AdminPageLayout`, `Combobox`, `Input`, `Table`, `Pagination`, `StatusBadge`, `PageHeader`.

---

### 5. Admin Pages — M2 & M3 Analytics

#### `/admin/m2/scores`
- **Access:** Admin
- **Purpose:** Knowledge scores table — all SMEs that have completed the M2 survey.
- **Key Features:**
  - Server-side: lists all users with `sme_id`, fetches knowledge score for each in parallel.
  - Table columns: Email, Sector, Score badge (green/amber/red), By-domain breakdown, Computed at.
  - Link-mode pagination.
  - Only shows users with a score (max_points > 0).
- **API Calls:**
  - `UsersApi.list(token)` — GET all users.
  - `M2Api.knowledgeScore(sme_id, token)` — GET per-SME score (parallel for all SMEs).
- **Key Components:** `Table`, `Badge`, `Pagination`.

---

#### `/admin/m2/questions`
- **Access:** Admin
- **Purpose:** M2 knowledge questions viewer with verification workflow for chartered accountants (CA).
- **Key Features:**
  - Filters: Domain, Sector, Only unverified toggle.
  - Verifier name input (CA name required to mark questions as verified).
  - Table: code, domain badge, sector badge, knowledge type, question format, prompt_en + translation badge, verify button or verified badge.
  - Verify action calls `M2Api.verifyQuestion(code, by, token)` with toast feedback.
  - Counts: total / verified badges in header.
- **API Calls:**
  - `M2Api.listQuestions({domain_code, sector_code, only_unverified}, token)` — GET questions.
  - `M2Api.verifyQuestion(code, by, token)` — POST verify mutation.
- **Key Components:** `AdminPageLayout`, `Combobox`, `Table`, `DomainBadge`, `SectorBadge`, `VerificationBadge`, `PageHeader`.

---

#### `/admin/m3/risk-signals`
- **Access:** Admin
- **Purpose:** M3 risk signals table — compliance history and behavioural signals for all SMEs.
- **Key Features:**
  - Server-side parallel fetch of risk signals for all SMEs with `sme_id`.
  - Table columns: Email, Sector, Knowledge score badge (M2 cross-reference), Missed deadlines, Penalty band, Under audit, Filing method, Snapshot date.
  - Link-mode pagination.
- **API Calls:**
  - `UsersApi.list(token)` — GET all users.
  - `M3Api.riskSignals(sme_id, token)` — GET per-SME risk signals (parallel).
- **Key Components:** `Table`, `Badge`, `Pagination`.

---

### 6. Admin Pages — Audit & Settings

#### `/admin/activity-log`
- **Access:** Admin
- **Purpose:** Immutable audit log of all platform events — auth, M1 regulations, survey questions, translations, submissions.
- **Key Features:**
  - Server-side rendering with `searchParams` filters: event_type, table_name, actor, record_id, record_key, since, until, page, size.
  - `ActivityFilters` sidebar component with dropdowns for event types and table names (fetched from the API).
  - Table columns: Timestamp (yyyy-MM-dd HH:mm), Event badge (colour-coded by type), Target (table + record key), User, Details (type-specific rendering).
  - Type-aware detail rendering: survey.submitted shows instrument/answer count/regulation count/scoring flags; bulk operations show count; login failures show email/reason; duplications show new short code; fallback collapses to JSON details/summary.
  - Link-mode pagination preserving filter params.
- **API Calls:**
  - `AdminAuditApi.list({event_type, table_name, actor, record_id, ...}, token)` — GET audit log.
  - `AdminAuditApi.eventTypes(token)` — GET available event type/table_name lists for filter dropdowns.
- **Key Components:** `AdminPageLayout`, `ActivityFilters`, `StatusBadge`, `Table`, `Pagination`, `PageHeader`.

---

#### `/admin/settings`
- **Access:** Admin
- **Purpose:** Platform settings for survey submission limits per role.
- **Key Features:**
  - Loads current limits (`sme_limit`, `annotator_limit`, `admin_limit`; 0 = unlimited).
  - Three numeric inputs in a grid; Save button with loading/toast feedback.
  - Shows last updated by / updated at metadata.
- **API Calls:**
  - `AdminSurveyLimitsApi.get(token)` — GET current limits.
  - `AdminSurveyLimitsApi.update(form, token)` — PATCH/PUT save limits.
- **Key Components:** `Card`, `Input`, `Button`, `PageHeader`, toast.

---

### 7. Admin Pages — Research Log (Obsidian Vault Mirror)

The Research Log pages read the Obsidian vault on disk via `loadVaultSnapshot()` (a server-side file reader). They display the research project's internal documentation live, without a backend API.

#### `/admin/research-log`
- **Access:** Admin
- **Purpose:** Landing page for the live vault mirror — sessions heatmap, feature counts, latest sessions.
- **Key Features:**
  - Six metric tiles: Sessions, Features (shipped/total), Changes 7d, Findings, In Progress, Active RQs.
  - Blocked features warning card with link to features page.
  - `ActivityHeatmap` — calendar heat-map of session items per day.
  - Latest 5 sessions using `SessionCard` (collapsible).
  - `VaultStatusPill` showing vault freshness; `RefreshButton`.
- **Key Components:** `ActivityHeatmap`, `SessionCard`, `VaultStatusPill`, `RefreshButton`.

---

#### `/admin/research-log/sessions`
- **Access:** Admin
- **Purpose:** Full chronological session timeline from `SESSIONS.md`.
- **Key Features:** All sessions rendered via `SessionTimeline`; vault mtime pill for SESSIONS.md.
- **Key Components:** `SessionTimeline`, `VaultStatusPill`, `RefreshButton`.

---

#### `/admin/research-log/sessions/[sessionId]`
- **Access:** Admin
- **Purpose:** Individual session detail view.

---

#### `/admin/research-log/features`
- **Access:** Admin
- **Purpose:** Feature status matrix from `FEATURES.md`.
- **Key Features:** `FeatureMatrix` groups features by module/area with status badges (done, in_progress, blocked, planned).
- **Key Components:** `FeatureMatrix`, `VaultStatusPill`, `RefreshButton`.

---

#### `/admin/research-log/features/[featureId]`
- **Access:** Admin
- **Purpose:** Individual feature detail.

---

#### `/admin/research-log/findings`
- **Access:** Admin
- **Purpose:** Per-module research findings across all supported modules.
- **Key Features:** Groups findings by module (M1–M4); `FindingCard` grid; empty states with storage path hints.
- **Key Components:** `FindingCard`.

---

#### `/admin/research-log/findings/[module]/[slug]`
- **Access:** Admin
- **Purpose:** Individual finding detail.

---

#### `/admin/research-log/changes`
- **Access:** Admin
- **Purpose:** Changelog view from vault.

---

#### `/admin/research-log/ideas`
- **Access:** Admin
- **Purpose:** Open research questions / ideas from vault.

---

#### `/admin/research-log/build-tracker`
- **Access:** Admin
- **Purpose:** Per-module engineering build progress from `RESEARCH_BUILD_TRACKER.md`.
- **Key Features:** `ModuleProgress` progress bars per module; vault mtime pill.
- **Key Components:** `ModuleProgress`, `VaultStatusPill`, `RefreshButton`.

---

### 8. Admin Pages — Other (Placeholders / Lighter Pages)

#### `/admin/annotation`
- **Access:** Admin
- **Purpose:** Annotation tool for labelling gazette content (separate workflow, likely for training data).
- **Key Features:** Not fully inspected — assumed to use `AdminPageLayout`.

---

#### `/admin/datasets`
- **Access:** Admin
- **Purpose:** ML dataset management.

---

#### `/admin/models`
- **Access:** Admin
- **Purpose:** ML model registry/management.

---

#### `/admin/training`
- **Access:** Admin
- **Purpose:** Model training trigger and monitoring.

---

#### `/admin/translations`
- **Access:** Admin
- **Purpose:** Multilingual content translation management — flag questions/regulations needing translation and mark them translated.

---

#### `/admin/regulations/new` and `/admin/regulations/[id]/authoring`
- **Access:** Admin
- **Purpose:** Create new regulation and open the authoring/drafting view for an existing regulation.

---

#### `/admin/surveys/new`
- **Access:** Admin
- **Purpose:** Create a new survey configuration.

---

#### `/admin/surveys/awareness/responses`
- **Access:** Admin
- **Purpose:** Browse M1 awareness survey responses.

---

#### `/admin/survey/regulations`
- **Access:** Admin (app-group route under `(app)`)
- **Purpose:** Survey-regulation mapping view — which surveys are linked to which regulations.

---

## Key Shared Components

The following components appear across multiple pages and carry significant functionality:

| Component | Used In | Purpose |
|---|---|---|
| `SurveyLauncher` | `/surveys/unified`, `/surveys/module/[id]` | Full survey wizard controller; manages flow state, answer submission, branching |
| `SurveyWizard` | `/surveys/regulation/[id]` | Regulation-scoped survey form (similar to Launcher but accepts initial state + regulationId) |
| `RegulationCard` | `/dashboard`, `/regulations` (via surveys page) | Compact regulation display card with Take Survey CTA |
| `FlowCanvas` | `/admin/regulations/[id]/flow` | Drag-and-drop canvas for linking questions to regulations |
| `RegulationForm` | `/admin/regulations/[id]/edit`, `/admin/regulations/new` | Full regulation CRUD form |
| `PageHeader` | Nearly all pages | Title, subtitle, breadcrumb, and optional right-side action slot |
| `AdminPageLayout` | Admin list pages | Two-column layout with sticky filter sidebar and main content area |
| `RecentRunsTable` | `/admin/m1/pipeline`, `…/recent`, `…/trace`, `…/steps/[id]` | Pipeline runs table with optional search and click-to-trace |
| `PipelineFlowDiagram` | `/admin/m1/pipeline` | Visual flowchart of pipeline stage counts |
| `TraceTimeline` | `/admin/m1/pipeline/trace/[id]` | Step-by-step timeline for a single gazette's pipeline journey |
| `ExtractionProgressPanel` | `/admin/m1/pipeline/sources/[sourceId]/extraction` | Per-PDF progress cards within a task scope |
| `ExtractionSummaryCard` | Same as above | Aggregated status_counts summary for a task |
| `CeleryHealthCard` | `/admin/m1/pipeline` | Celery broker stats card (workers, active tasks, queued) |
| `LivePollingIndicator` | M1 pipeline pages | Animated pulse showing last-fetched timestamp and polling state |
| `DocsLayout` | `/docs/m1`, `/docs/[slug]` | Docs sidebar nav + main content area |
| `ActivityHeatmap` | `/admin/research-log` | GitHub-style calendar heatmap of session activity |
| `ConfirmDialog` | Sources page, extraction page | Accessible modal confirmation for destructive actions |
| `StatusBadge` | Everywhere | Colour-coded status badge (success/warning/error/pending/neutral) |
| `AuthorshipMeta` | Regulation and survey edit pages | Created/updated by+at row with optional activity log link |

---

## Notes

- **M4 pages** (misinformation module) are not yet implemented beyond the `/verify` placeholder. No dedicated admin or SME pages exist for M4 data.
- **Q&A / RAG** (`/qa`) is similarly a placeholder.
- **Profile editing** is deferred (read-only display only).
- The **Research Log** section is unusual: it reads the Obsidian vault on disk at render time rather than via a database, making it a live documentation mirror rather than a data application.
- The **extraction workspace** (`/admin/m1/pipeline/sources/[sourceId]/extraction`) is the most complex page: it combines localStorage persistence, TanStack Query polling, multiple confirm dialogs, toast feedback, and real-time Celery task monitoring.
- Pages under the `(admin)` route group do not enforce admin access at the route level via Next.js middleware — access control is enforced server-side via `getAccessToken()` / `requireUser()` and API-level permission checks.
