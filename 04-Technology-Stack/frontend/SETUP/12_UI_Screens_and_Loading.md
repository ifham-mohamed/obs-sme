# 12 — UI Screens & Loading States

> **What this is.** A screen-by-screen map of the frontend as it stands after Sessions 6–13, with the *why* behind each surface, the components it leans on, and the loading-state strategy (`<Skeleton>` vs `<AnimatedLoadingSkeleton>` vs streaming `loading.tsx`).
> **What this is not.** A workflow guide — for "how do I add a primitive / wire a form / use the toast" see [`05_Frontend_Development.md`](05_Frontend_Development.md). For the survey *engine* (branching, M:N regulation links, flow canvas internals) see [`11_Survey_System.md`](11_Survey_System.md). For the request lifecycle / ERD see [`03_Architecture.md`](03_Architecture.md). For M1 *user workflows* (admin triage, SME compliance, etc. — what the user *does* on each screen, including the deferred surfaces) see [`14_M1_Tracking_Workflows.md`](../../m1/14_M1_Tracking_Workflows.md) and its 9 companions.

---

## 0. Why this doc exists

The UI grew in layers: an app-shell redesign (Session 8), regulations admin (Session 7), the unified survey wizard (Session 6), the question bank + branching-rules editor (Session 11), then in Session 12 the visual flow canvas, the translation queue, DB-driven SME surveys, and a two-tab surveys hub. There was no single place that said *which screen does what and why it looks the way it does* — a new contributor had to read `sidebar.tsx` plus a dozen `page.tsx` files. This doc is that place. Session 13 also added a richer loading affordance (`<AnimatedLoadingSkeleton>`, framer-motion) and streaming `loading.tsx` segments — §6–§7 cover that.

Design north star: **a calm, dark-first dashboard for a non-technical SME owner who is also being asked to do admin work.** Hence the floating-card shell (orientation), the per-module accent colours (the survey crosses three modules — colour tells you where you are), the trilingual everything (en/si/ta), and loading placeholders that mirror the eventual layout rather than a blocking spinner.

---

## 1. The app shell

Two route groups, two layouts:

| Group | Layout file | Guard | Who sees it |
|---|---|---|---|
| `(app)` | `frontend/app/(app)/layout.tsx` | `requireUser()` | any authenticated user (SME, annotator, admin) |
| `(admin)` | `frontend/app/(admin)/layout.tsx` | admin-only | `role === "admin"` |

Both layouts render the same chrome — a sticky left **`<Sidebar>`** + a **`<Topbar>`** + the page body.

- **`components/layout/sidebar.tsx`** — floating rounded sidebar with the brand mark + gradient logo. Collapsible (toggle persists to `localStorage` via `components/layout/sidebar-state.tsx`); collapsed mode shows icon-only items with a `<Tooltip>` on hover; the active item gets a left-border accent. Two item sets: the always-visible SME nav (Dashboard, Surveys hub, Awareness, Knowledge test, Vulnerability profile, My risk, Ask, Verify a claim) and — gated on `role === "admin"` — the ADMIN section (Survey responses, Regulations, Question bank (unified), Translations, Question bank [legacy M2], Knowledge scores, Risk signals, Users). `components/layout/mobile-sidebar.tsx` is the drawer variant below the `md` breakpoint.
- **`components/layout/topbar.tsx`** — shows the current page's breadcrumb (each page declares it once via `<PageHeader>` → `components/layout/breadcrumb-context.tsx`), a sidebar-collapse trigger, a refresh button, the **`components/layout/theme-toggle.tsx`** (light/dark, `next-themes`), the **`components/layout/locale-switcher.tsx`** (en/si/ta, sets the `NEXT_LOCALE` cookie), and **`components/layout/avatar-menu.tsx`** (initials avatar → dropdown with email + role + Sign out).
- **`components/layout/page-header.tsx`** — `<PageHeader title subtitle breadcrumb actions />`. Every page uses it so the breadcrumb is declared in exactly one place and the topbar picks it up via context. *Why*: avoids breadcrumb drift, gives every screen a consistent header band.

---

## 2. SME-facing screens

> Template per screen: **route** · **purpose** · **key components** · **why it's designed this way** · **what you see**. File paths are under `frontend/app/(app)/`.

### `/dashboard` — the landing page
- **File**: `dashboard/page.tsx` (server component) · streaming fallback `dashboard/loading.tsx`.
- **Purpose**: one-glance status + the obvious next action.
- **Key components**: `<PageHeader>`, a gradient welcome-banner `<Card>` with CTAs (Continue the unified survey → `/surveys`; View risk profile → `/risk`; admins also get Manage regulations), four stat `<Card>`s (Knowledge score / Risk signals / Survey progress / Regulations-or-Last-update) with tinted circular icon badges, a **Regulations awaiting your assessment** widget (up to 3 `<RegulationCard>`s from `/api/v1/dashboard/pending-regulations`; "View all" → `/surveys?view=regulation`; hides itself when empty), and two lower panels (Pending tasks · Recent activity).
- **Why**: an SME owner opens this once a week — it has to answer "am I OK?" and "what should I do next?" without scrolling. Parallel `Promise.all` fetches (knowledge score, risk signals, flow state, pending regulations) with graceful per-call fallbacks so a missing SME profile (admin user) doesn't blank the page.
- **You see**: "Welcome back, {name}" banner; coloured stat cards; a row of regulation cards if any are pending; pending-tasks/recent-activity.
- **Workflow:** see [14_M1_5_SME_Regulation_Discovery.md](../../m1/14_M1_5_SME_Regulation_Discovery.md) — the pending-regulations widget is the today path; the deferred deadline banner is in [14_M1_8_SME_Deadline_Alert_History.md](../../m1/14_M1_8_SME_Deadline_Alert_History.md).

### `/surveys` — the surveys hub (two tabs)
- **File**: `surveys/page.tsx` (server component) · streaming fallback `surveys/loading.tsx`.
- **Purpose**: pick *what* to do — assess a specific regulation, or take one instrument across everything.
- **Key components**: `<SurveysHubTabs>` (`components/surveys/surveys-hub-tabs.tsx`). Tab state lives in the URL (`?view=regulation|module`) so the back button + deep links work. **By regulation** tab: a grid of `<RegulationCard>` (`components/surveys/regulation-card.tsx`) — title (locale-aware with a "Showing English" badge when SI/TA is missing), effective date, severity badge, domain chip — each routing to `/surveys/regulation/[id]`. **By module** tab: three abstract instrument cards (Regulatory awareness / Compliance knowledge / Vulnerability profile) routing to the standalone surveys, each wrapped in its `module-m{1,2,3}` accent.
- **Why**: Session 12 made every survey item regulation-anchored, so the natural mental model is "here are the regulations you need to deal with" — but we keep the older "take the whole awareness/knowledge/vulnerability survey" entry too (some SMEs want a single sweep). The two-tab split serves both without one burying the other.
- **You see**: a tab strip; on "By regulation", regulation cards; on "By module", three coloured cards.

### `/surveys/regulation/[id]` — regulation-scoped unified flow
- **File**: `surveys/regulation/[id]/page.tsx` (server) · streaming fallback `surveys/regulation/[id]/loading.tsx`.
- **Purpose**: walk M1 → M2 → M3 for *one* regulation.
- **Key components**: a header (instrument label + `regulation_short_code` + title + summary) then `<SurveyWizard>` (`components/forms/survey-wizard.tsx`) given `regulationId`. The wizard renders one question at a time, swaps its accent class as the flow crosses modules, shows a `<RegulationContextCard>` above any question that carries a `linked_regulation`, and a "this follows up on your earlier answer" cross-module hint when `module_number` changes. It threads `regulation_id` into every `SurveyFlowApi.answer` call so the engine stays scoped (see `11_Survey_System.md` §10.8).
- **Why**: the SME shouldn't have to context-switch between three separate surveys to understand one rule — the engine stitches the relevant M1/M2/M3 questions into a single guided run.
- **You see**: one question per screen, a sticky progress bar, the regulation context card, then a thank-you state with CTAs when `flow_status === "completed"`.
- **Workflow:** see [14_M1_6_SME_Awareness_Survey.md](../../m1/14_M1_6_SME_Awareness_Survey.md) (per-regulation flow path); follow-on compliance tracking is [14_M1_7_SME_Compliance_Action_Tracking.md](../../m1/14_M1_7_SME_Compliance_Action_Tracking.md).

### `/surveys/module/[id]` — per-module session-based survey
- **File**: `surveys/module/[id]/page.tsx` (server).
- **Purpose**: take a single module survey (M1/M2/M3/M4) under the session-based architecture with submission limits enforced.
- **Key components**: `<SurveyLauncher>` (`components/surveys/survey-launcher.tsx`) — checks `survey_limits` cap and calls `POST /api/v1/survey-sessions/start` with `survey_mode=per_module_m{n}`; resumes an existing `in_progress` session from `localStorage`. Then hands off to `<SurveyWizard>` which calls the session endpoints: `GET /{id}/next-question` → `POST /{id}/answer` loop → `POST /{id}/complete`. On completion → per-module thank-you.
- **M4 note**: `per_module_m4` is a valid `survey_mode` value accepted by `POST /survey-sessions/start`, but since no `module_number=4` questions are seeded, `GET /{id}/next-question` immediately returns `flow_status: "completed"`. The `/surveys/module/m4` route is not exposed in the nav; M4 data capture is deferred to BUILD_10.

### `/surveys/unified` — cross-module unified session survey
- **File**: `surveys/unified/page.tsx` (server).
- **Purpose**: one survey run that spans all four modules (20-question cap) via the session API.
- **Key components**: same `<SurveyLauncher>` + `<SurveyWizard>` pattern, `survey_mode="unified"`.

### `/surveys/history` — completed session list
- **File**: `surveys/history/page.tsx` (server).
- **Purpose**: SME reviews their past survey runs.
- **Key components**: fetches `GET /api/v1/survey-sessions/my-history`; renders a table of sessions (session_id, mode, questions_answered, completed_at, status). Empty state links to `/surveys`.
- **Workflow:** see [14_M1_7_SME_Compliance_Action_Tracking.md](../../m1/14_M1_7_SME_Compliance_Action_Tracking.md) — survey-history is the today-stand-in for the deferred "My Regulations" tracker.

### `/surveys/awareness` · `/surveys/knowledge` · `/surveys/vulnerability` — standalone per-module surveys
- **Files**: `surveys/awareness/page.tsx`, `surveys/knowledge/page.tsx`, `surveys/vulnerability/page.tsx` (all server components, `dynamic = "force-dynamic"`).
- **Purpose**: take one instrument across **all** active regulations + the baseline questions in one pass.
- **How they're built (Session 12)**: each fetches `SurveysApi.questionsForInstrument(instrument, { sector, include_baseline: true })` and converts the SME-safe `SurveyQuestionPublic[]` to the UI `Question[]` shape via `lib/surveys/db-question-adapter.ts`. **Adding a regulation in admin auto-grows these surveys — no code change.** They all render `<SurveyForm>` (`components/forms/survey-form.tsx`), which composes `<QuestionRenderer>` (one input per question type, evaluates `dependsOn` rules), `<SurveyProgress>` (sticky `n / total` bar), `<SurveyAutosave>` (debounced draft to `localStorage` with a resume banner), `<SurveyErrorSummary>` (jump-to-field on submit), and optional `<RegulationContextCard>`s.
  - **Awareness** (`module-m1`, trust-blue): shows the 12 baseline questions (`is_baseline=true`) first, then per-regulation awareness questions ordered by effective date.
  - **Knowledge** (`module-m2`, emerald): groups questions into domain sections (VAT / Income Tax / EPF / …) via the row's `domain_code`; builds the regulation-context map *dynamically* from each question's `linked_regulation` (no more hardcoded April-2026 VAT card).
  - **Vulnerability** (`module-m3`, amber): groups into the four sections (Compliance history / Day-to-day behaviour / Stress & capacity / Sector-specific risk) via `instrument_section`; uses the `<VulnerabilityForm>` client shell (`components/forms/vulnerability-form.tsx`) which owns the partition-on-submit logic — answers fan out to `M3Api.submitHistory` + `M3Api.submitBehavioural` (the M3 storage is two append-only snapshot tables, not one flat response set).
- **Why DB-driven**: before Session 12 these were hardcoded TS banks (`lib/surveys/awareness.ts`, `m3-vulnerability.ts`) — every new regulation needed a code edit + redeploy. Now the admin authoring surface (`/admin/regulations/[id]/flow`, `/admin/questions`) is the single source of truth and the SME surveys reflect it instantly.
- **You see**: a card-titled survey, section dividers, a sticky progress bar, a draft-resume banner if you left mid-way, regulation context cards inline, then a redirect to the matching `/thank-you` page on submit.

### `/surveys/{awareness,knowledge,vulnerability}/thank-you` — completion pages
- Small confirmation `<Card>`s with onward CTAs (view risk, take another survey). Static; no data fetch.

### `/risk` — your risk profile
- **File**: `risk/page.tsx`. **Purpose**: surface the computed knowledge score + M3 risk signals back to the SME. Knowledge-score-by-domain breakdown, top barriers, vulnerability snapshot. Empty states nudge you to take the missing survey. *Why*: closes the loop — the surveys feed this; if it's blank, you know what to do.

### `/regulations` — surveys-hub alias / SME regulation list
- **File**: `regulations/page.tsx`. Sidebar's "Surveys hub" link historically points here; functionally overlaps with `/surveys`. (Consolidation candidate — see `tracker/SESSIONS.md`.)
- **Workflow:** see [14_M1_5_SME_Regulation_Discovery.md](../../m1/14_M1_5_SME_Regulation_Discovery.md) (covers the discovery flow today + the sector-applicability filter target).

### `/qa` ("Ask") and `/verify` ("Verify a claim") — Coming-soon stubs
- **Files**: `qa/page.tsx`, `verify/page.tsx`. Render the shared `<ComingSoon>` card — these modules (RAG QA = BUILD_08, M4 misinformation verifier = BUILD_10) are documented in the BUILD plan but not wired in the current MVP slice. *Why keep the nav entries*: they signal the product surface without pretending the feature exists.
- **M4 / `/verify` specifically**: `per_module_m4` session mode and `module_number=4` are reserved in the schema. No M4 questions are seeded. `/api/v1/verify/claim` returns 501. BUILD_10 has not started.

---

## 3. Admin-facing screens

> File paths under `frontend/app/(admin)/admin/`. All behind the admin guard.

### `/admin/regulations` — the regulation bank (list)
- **File**: `regulations/page.tsx` (client component, React Query).
- **Purpose**: browse / filter / verify / archive the admin-curated regulation rows.
- **Key components**: `<PageHeader>`, a vertical filter rail (Verification / Domain / Sector groups — click-to-toggle, reflected in the URL), a search `<Input>` (matches code + title), a polished `<Table>` (avatar+code cells, hover-row highlight, severity dots, responsive column hiding), `<Pagination>` (page numbers + prev/next + page-size changer + quick-jump + "Total N items", state in the URL `?page=&size=`), a bulk-verify action bar (select rows → "Verify selected" with a CA name), per-row `<RowActions>` (Edit / Duplicate / Archive ↔ Restore), `<ConfirmDialog>` on archive. **Loading**: while React Query is `isLoading`, the table area shows `<AnimatedLoadingSkeleton>` (chrome-stripped to sit inside the table border) instead of a "Loading…" string.
- **Why a filter rail (not a top filter bar)**: the regulation bank gets long; a persistent left rail keeps filters visible while you scroll the table.
- **Workflow:** see [14_M1_1_Admin_Pipeline_State_Tracking.md](../../m1/14_M1_1_Admin_Pipeline_State_Tracking.md) (pipeline-state triage flow); the verification flow is [14_M1_3_Admin_Expert_Verification.md](../../m1/14_M1_3_Admin_Expert_Verification.md); the deferred review-queue page is [14_M1_2_Admin_Review_Queue_Triage.md](../../m1/14_M1_2_Admin_Review_Queue_Triage.md).

### `/admin/regulations/new` and `/admin/regulations/[id]/edit` — the regulation form
- **Files**: `regulations/new/page.tsx`, `regulations/[id]/edit/page.tsx` (server component, `dynamic = "force-dynamic"`) · edit has a streaming fallback `regulations/[id]/edit/loading.tsx`.
- **Key components**: `<RegulationForm>` (`components/forms/regulation-form.tsx`) — four numbered `<Card>` sections (Identity & classification / Dates / Affected sectors / Localised content), EN/SI/TA `<Tabs>` for the trilingual fields, a sticky save bar (`sticky bottom-0 backdrop-blur`), and a live "Preview as SME" panel powered by `useWatch` + `<RegulationContextCard>` so the author sees the card the SME will see. Edit mode disables `regulation_short_code` (immutable). On the edit page only: a `<LinkedQuestionsPanel>` (`components/forms/linked-questions-panel.tsx`) Card grouping linked questions by module (M1/M2/M3) with deep-links into `/admin/questions/[code]/edit`, plus an **"Open flow canvas"** CTA in the header and the verification badge. **Loading**: `<LinkedQuestionsPanel>` shows `<AnimatedLoadingSkeleton>` inside its Card while fetching.
- **Why the live preview**: the regulation summary becomes an SME-facing context card; authors need to see it rendered, not imagine it from form fields.
- **Workflow:** see [14_M1_3_Admin_Expert_Verification.md](../../m1/14_M1_3_Admin_Expert_Verification.md) — the Verify button on this page is the canonical sign-off action.

### `/admin/regulations/[id]/flow` — the visual flow canvas
- **File**: `regulations/[id]/flow/page.tsx` (server component) · streaming fallback `regulations/[id]/flow/loading.tsx`.
- **Purpose**: see and edit the M1 → M2 → M3 branching graph for one regulation.
- **Key components**: `<FlowCanvas>` (`components/forms/flow-canvas.tsx`) — a three-column CSS-grid layout (M1 Awareness · M2 Knowledge · M3 Vulnerability, each lane wrapped in its `module-m{1,2,3}` accent). Each question is a node card listing its answer options as clickable chips; an existing branching rule shows a `→ TARGET` badge on the chip it fires from. Clicking a chip opens `<FlowQuestionDrawer>` (`components/forms/flow-question-drawer.tsx`) — a slim creation form in a `<Sheet>` pre-filled with the parent question + the chip's answer value + the regulation id; on save it (1) creates the child question and (2) upserts a `next_question_rules` entry on the parent so the new node is wired in. A `<FlowValidationBanner>` (`components/forms/flow-validation-banner.tsx`) at the top surfaces the soft-warn validator output (forward-refs / archived targets / cycles) with click-to-jump to the offending node.
- **Why CSS grid, not a graph library**: the layout is determined by data (module = column, sort order = row), not by free-form node positions, so a 3-lane grid says everything a draggable canvas would — at zero bundle cost. The data shape *is* a graph, so swapping in a graph library later (pan/zoom/drag) is a `<FlowCanvas>`-body change, nothing else. (Recorded as an open follow-up in `tracker/SESSIONS.md`.)
- **Why "slim drawer", not the full `<QuestionForm>`**: adding a follow-up is a focused action — code, module, format, trilingual prompt, options. The author fine-tunes (correct answer, sector scope, deeper branching) afterwards via `/admin/questions/[code]/edit`.

### `/admin/regulations/[id]/authoring` — the guided wizard ("Quick start")
- **File**: `regulations/[id]/authoring/page.tsx`. The original Session-11 three-step wizard (Step 1 M1 awareness root → Step 2 M2 yes/no follow-ups → Step 3 M3 vulnerability tails). Kept as a fast path for first-time authors; the flow canvas is the surface for anything branchier than yes/no. Both write to the same `survey_question_regulations` junction.

### `/admin/questions` (+ `/new`, `/[code]/edit`) — the unified question bank
- **Files**: `questions/page.tsx` (client, React Query), `questions/new/page.tsx`, `questions/[code]/edit/page.tsx` (server components).
- **Key components**: list page mirrors `/admin/regulations` polish — filters (Module / Domain / Sector / Format / unverified-only / include-archived), search, bulk-verify, `<RowActions>`, `<Pagination>` (state in local component state here, not the URL); **loading** shows `<AnimatedLoadingSkeleton>`. The form is `<QuestionForm>` (`components/forms/question-form.tsx`) — five numbered `<Card>` sections (01 Identity / 02 Linkage / 03 Localised content / 04 Answers / 05 Branching), with `<OptionsBuilder>` (`components/forms/options-builder.tsx`) adapting the Answers card to the chosen `question_format` and `<BranchingRulesEditor>` (`components/forms/branching-rules-editor.tsx`) for `next_question_rules` (Visual tab = templated rows with predicate select + format-aware value input + goto-question combobox; JSON tab = prettified textarea with apply/reset + inline error). The edit page shows the question's `validation_warnings` (the soft-warn branching validator) and its `linked_regulations` (the M:N hydration).
- **Why five cards, numbered**: a survey question carries a lot of orthogonal concerns (identity, what regulation it's about, the three-language copy, the answer shape, the branching) — chunking them into numbered cards with a sticky save bar keeps a long form navigable. It deliberately mirrors `<RegulationForm>` so admins learn one layout.

### `/admin/translations` — the translation queue
- **File**: `translations/page.tsx` (server component) · streaming fallback `translations/loading.tsx`.
- **Key components**: `<TranslationsQueue>` (`components/admin/translations-queue.tsx`) — a kind filter (question / regulation) + a missing-locale filter (si / ta), one row per item with the English text + has-SI / has-TA badges + inline `<Textarea>` fields to fill the missing translations, a checkbox + "Mark selected as translated" bulk action for questions. **Loading**: while refreshing with no items yet, shows `<AnimatedLoadingSkeleton>`.
- **Why a dedicated queue (vs editing each record)**: translation is its own workflow done by a different person; pulling everything that needs SI/TA into one screen with inline edit beats hunting through the question bank. Backed by `translation.completed` audit events.

### `/admin/m2/questions` — legacy M2 question bank
- **File**: `m2/questions/page.tsx` (client, React Query). The pre-unified M2-only list, kept live for one slice (the unified `/admin/questions` is the successor; OQ12 — the hard redirect — is deferred). **Loading**: `<AnimatedLoadingSkeleton>`.

### `/admin/m2/scores` — knowledge scores
- **File**: `m2/scores/page.tsx`. Read-only admin view of `m2_knowledge_scores` (overall %, by-domain breakdown). Wrapped in `module-m2`.

### `/admin/m3/risk-signals` — risk signals
- **File**: `m3/risk-signals/page.tsx` (server, async). Read-only admin view of the M3 compliance-history + behavioural-signal snapshots. Wrapped in `module-m3`. (Full ML risk scoring is BUILD_09.)

### `/admin/users` — user management
- **File**: `users/page.tsx` (client, React Query). List with role/active filters + search; `<CreateUserDialog>` / `<EditUserDialog>` / `<ResetPasswordDialog>` (`components/forms/`); `<RowActions>` for activate/deactivate/reset-password/delete with a last-active-admin guard. **Loading**: `<AnimatedLoadingSkeleton>`.

### `/admin/surveys/awareness/responses` — survey response list
- **File**: `surveys/awareness/responses/page.tsx` (server, async). Admin read of submitted awareness responses. (Renamed out of `/admin/surveys/awareness` in an earlier session to dodge a parallel-route collision with the SME `/surveys/awareness`.)

### `/admin/activity-log` — audit log viewer
- **File**: `activity-log/page.tsx` (server, async).
- **Purpose**: admin browses the full `audit_log` with filters (event type, table, date range).
- **Key components**: `<PageHeader>`, paginated `<Table>` with `event_type`, `table_name`, `record_key`, `user_name`, `occurred_at` columns. Backed by `GET /api/v1/admin/activity-log`.

### `/admin/settings` — survey submission limits
- **File**: `settings/page.tsx` (server) · client form.
- **Purpose**: admin configures how many survey submissions each role may make (backed by the `survey_limits` DB singleton, `id=1`).
- **Key components**: Three number inputs (`sme_limit` / `annotator_limit` / `admin_limit`). Reads via `GET /api/v1/admin/survey-limits`; writes via `PATCH /api/v1/admin/survey-limits`. Changes take effect immediately — the session-start endpoint reads the singleton on every `POST /survey-sessions/start`. Default caps: SME = 10, annotator = 0, admin = 0.
- **Resilience**: if the `survey_limits` table hasn't been migrated yet, the service returns safe in-memory defaults (10 / 0 / 0) and logs a warning. Run `alembic upgrade head` to persist the table.

---

## 4. Reusable UI components

### 4a. Primitives — `components/ui/` (shadcn pattern, ~24 files)

| Component | What it is | Notable usages |
|---|---|---|
| `alert` | inline notice (default / destructive) | `<FlowValidationBanner>`, form-level errors |
| `animated-loading-skeleton` | **NEW (Session 13)** — full-section loading placeholder; animated search-icon sweep over a shuffling card grid | `loading.tsx` segments, client-table loading states, `<LinkedQuestionsPanel>`, `<TranslationsQueue>` |
| `animated-loading-skeleton-demo` | visual-check demo for the above (not imported by app routes) | docs / manual QA |
| `avatar` | initials-fallback avatar | sidebar brand, topbar avatar menu, table cells |
| `badge` | small status pill (secondary / success / accent / destructive) | verified badges, severity, module tags, "→ N rules" |
| `breadcrumb` | breadcrumb trail | rendered in the topbar via `<PageHeader>` |
| `button` | CVA-variant button (default / outline / ghost / destructive, sizes) | everywhere |
| `card` | `Card` / `CardHeader` / `CardTitle` / `CardContent` / `CardDescription` | every page |
| `checkbox` | radix checkbox | multi-select questions, bulk-select rows |
| `combobox` | searchable select | regulation/question pickers in forms, branching goto-question |
| `confirm-dialog` | yes/no confirmation modal | archive actions |
| `dialog` | radix dialog | create/edit/reset-password user dialogs |
| `dropdown-menu` | radix dropdown | avatar menu, `<RowActions>` |
| `input` | text input | every form, search bars |
| `label` | form label | every form |
| `pagination` | app-themed pagination — page numbers + prev/next + optional page-size changer + quick-jumper + "Total N items"; controlled (`onPageChange`) or link mode (`buildHref`); no external dep | every admin list table |
| `pagination-demo` | visual-check demo for the above (not imported by app routes) | docs / manual QA |
| `radio-group` | radix radio group | single-choice questions |
| `select` | radix select (`Select`/`SelectTrigger`/`SelectValue`/`SelectContent`/`SelectItem`) | format/module pickers, filters |
| `sheet` | radix slide-over panel | `<FlowQuestionDrawer>` |
| `skeleton` | bare `animate-pulse bg-muted` div | inline placeholders inside `<AnimatedLoadingSkeleton>`, small per-field loads |
| `table` | `Table`/`TableHeader`/`TableRow`/`TableHead`/`TableCell`/`TableBody` | every admin list |
| `tabs` | radix tabs | EN/SI/TA panels, surveys hub, branching Visual/JSON |
| `textarea` | multi-line input | prompts, summaries, JSON editors |
| `toaster` | toast notifications (`toast(...)`) | save/verify/archive feedback |
| `tooltip` | radix tooltip | collapsed-sidebar item labels, icon buttons |

### 4b. Domain composites — `components/forms/`, `components/surveys/`, `components/admin/`, `components/layout/`

| Component | What it does | Where used | Why it exists |
|---|---|---|---|
| `layout/sidebar` · `mobile-sidebar` · `sidebar-state` | the collapsible nav (desktop + mobile drawer); collapse state in `localStorage` | both layouts | one nav, two viewports, persistent preference |
| `layout/topbar` · `avatar-menu` · `theme-toggle` · `locale-switcher` | the top bar + its controls | both layouts | breadcrumb display + theme/locale/account in one band |
| `layout/page-header` · `breadcrumb-context` | per-page header; pushes the breadcrumb into the topbar | every page | declare the breadcrumb once |
| `forms/survey-form` | the SME survey runner — composes renderer + progress + autosave + error-summary + context cards; supports `customSubmit` | awareness / knowledge / vulnerability pages | one battle-tested form for all three standalone surveys |
| `forms/question-renderer` | renders one question by `type`, evaluates `dependsOn` rules | inside `<SurveyForm>` | keep the per-type input logic in one place |
| `forms/survey-progress` · `survey-autosave` · `survey-error-summary` | sticky `n/total` bar · debounced draft + resume banner · jump-to-error on submit | inside `<SurveyForm>` | the UX scaffolding that makes a long survey bearable |
| `forms/survey-wizard` | the unified one-question-at-a-time flow; module-accent swap; regulation context card; threads `regulationId` | `/surveys/regulation/[id]` (and historically `/surveys`) | the cross-module flow needs a different shell than the flat per-module form |
| `forms/regulation-context-card` | the SME-facing "this question is about regulation X" card (title / effective date / penalty / real-world example) | inside the wizard and the knowledge survey; previewed in `<RegulationForm>` | give the SME the *why* before the question |
| `forms/regulation-form` | the 4-card regulation editor with EN/SI/TA tabs + live SME preview | `/admin/regulations/{new,[id]/edit}` | admins curate regulations; the preview keeps the SME card honest |
| `forms/linked-questions-panel` | groups a regulation's questions by module with deep-links | `/admin/regulations/[id]/edit` | see at a glance what's attached |
| `forms/question-form` · `options-builder` · `branching-rules-editor` | the 5-card question editor; format-adaptive answers; Visual+JSON branching rules | `/admin/questions/{new,[code]/edit}` | a survey question has many orthogonal concerns — chunk them |
| `forms/authoring-wizard` | the guided 3-step regulation→M1→M2→M3 author flow | `/admin/regulations/[id]/authoring` | fast path for simple yes/no flows |
| `forms/flow-canvas` · `flow-question-drawer` · `flow-validation-banner` | the visual M1/M2/M3 graph; slim follow-up creator; soft-warn banner | `/admin/regulations/[id]/flow` | flexible branching authoring — any answer routes to any follow-up |
| `forms/vulnerability-form` | client shell wrapping `<SurveyForm>` for M3; owns the partition-on-submit (answers → history + behavioural payloads) | `/surveys/vulnerability` | M3 storage is two snapshot tables, not one response set |
| `forms/create-user-dialog` · `edit-user-dialog` · `reset-password-dialog` | admin user CRUD modals | `/admin/users` | keep user mutations off the main page flow |
| `surveys/survey-launcher` | start/resume a session; checks submission limits; stores draft session_id in `localStorage`; renders a CTA button that calls `POST /survey-sessions/start` | `/surveys/module/[id]`, `/surveys/unified` | all session lifecycle in one place |
| `surveys/surveys-hub-tabs` · `regulation-card` | the two-tab hub; the per-regulation card | `/surveys`, `/dashboard` widget | "pick a regulation or a module" |
| `admin/row-actions` | the `⋯` per-row action menu | every admin list | one consistent row-action affordance |
| `admin/translations-queue` | the kind/locale-filtered translation worklist with inline edit + bulk-mark | `/admin/translations` | translation is its own workflow |

---

## 5. Design-system recap

- **Tokens** — `frontend/app/globals.css` defines the shadcn HSL contract (`--background`, `--foreground`, `--card`, `--popover`, `--primary`, `--secondary`, `--accent`, `--muted`, `--destructive`, `--success`, `--warning`, `--border`, `--input`, `--ring`, `--radius`) for `:root` (light) and `.dark`. The palette is "trust-blue primary (`217 91% 50%`) + amber accent (`38 92% 50%`) + slate neutrals" — chosen to read as a calm financial/regulatory dashboard, not a consumer app. Components reference tokens, never raw hex.
- **Dark-first** — the product ships dark by default (see the screenshots in `tracker/`); every component must read on both. *This is why the new `<AnimatedLoadingSkeleton>` was adapted from its `bg-white`/`bg-gray-200`/`text-blue-600` origin to `bg-card`/`<Skeleton>`/`text-primary` — pasted verbatim it would be a white box in dark mode.*
- **Per-module accents** — `.module-m1` (trust-blue, the default), `.module-m2` (emerald), `.module-m3` (amber). Wrapping a survey page (or a flow-canvas lane) in `module-m{n}` overrides `--primary` + `--ring` in that scope, so buttons / focus rings / accent badges shift module-by-module. *Why*: the unified survey crosses three modules in one run — colour is the cheapest way to tell the SME "you're now in the knowledge part / the vulnerability part". `<AnimatedLoadingSkeleton>` inherits this for free because its search-icon glow uses `hsl(var(--primary))`.
- **Trilingual** — every UI string goes through `next-intl` (`useTranslations()` / `getTranslations()`) with `en` / `si` / `ta` message files kept at key-parity; question/regulation *content* is stored on the records (`*_en/si/ta` columns) with a server-side English fallback (see `11_Survey_System.md` §10.8). Fonts: `--font-sans` for Latin, `--font-si` (Sinhala) and `--font-ta` (Tamil) loaded via `next/font`.
- **Radius / spacing** — `--radius: 0.5rem`; Tailwind's default spacing scale; cards are the default surface unit.

---

## 6. Loading states

### The problem
Before Session 13 every async surface fell back to a bare `"Loading…"` text div, and there were no streaming `loading.tsx` files anywhere — server-rendered pages just blocked until their `await`s resolved (blank screen during the fetch). The only skeleton was `<Skeleton>`, a plain `animate-pulse bg-muted` div.

### The two-tier answer
- **`<Skeleton>` (`components/ui/skeleton.tsx`)** — the *inline* placeholder. A single shimmering box you size with Tailwind (`<Skeleton className="h-3 w-24" />`). Use it for individual fields, avatars, single values — anywhere a small bit of content is loading inside an otherwise-rendered layout.
- **`<AnimatedLoadingSkeleton>` (`components/ui/animated-loading-skeleton.tsx`)** — the *full-section / full-page* placeholder. A framer-motion animation: a search icon sweeps a random path over a responsive grid of 6 placeholder cards (3 cols ≥1024px, 2 ≥640px, 1 below), each card built from `<Skeleton>` rows, with a primary-tinted glow pulse on the icon. Use it when a whole table, grid, or page is loading. It's theme-aware (`bg-card`, `from-muted/40 to-muted`, `text-primary`, `hsl(var(--primary))` glow) and accepts a `className` so callers can strip its card chrome when embedding it inside a bordered table (`className="max-w-none border bg-transparent p-2 shadow-none"`).

### The streaming pattern
Next.js App Router: a `loading.tsx` in a route segment automatically wraps that segment's `page.tsx` in a Suspense boundary whose fallback is `loading.tsx` — so a server component that `await`s data streams the skeleton first, then swaps in the real content. Session 13 added `loading.tsx` for the server-rendered surfaces: `app/(app)/surveys/`, `app/(app)/surveys/regulation/[id]/`, `app/(app)/dashboard/`, `app/(admin)/admin/regulations/[id]/flow/`, `app/(admin)/admin/regulations/[id]/edit/`, `app/(admin)/admin/translations/`. Each just renders `<AnimatedLoadingSkeleton>` inside the same width container the page uses, so nothing jumps when content arrives.

For *client* components that fetch via React Query (`/admin/regulations`, `/admin/questions`, `/admin/m2/questions`, `/admin/users`, `<LinkedQuestionsPanel>`, `<TranslationsQueue>`), a `loading.tsx` only covers the brief route transition — so those render `<AnimatedLoadingSkeleton>` directly while `isLoading` is true.

### Why an animated skeleton (not a spinner, not text)
A placeholder that mirrors the eventual layout reduces *perceived* latency (the page already "looks done") and avoids the layout shift a spinner-then-content swap causes. The moving search icon reads as "actively looking things up" without a blocking modal. It's a small cost: framer-motion is ~30 KB gzip, lazy-loaded behind the `loading.tsx`/`isLoading` boundary, and it's the first non-`tailwindcss-animate` animation dep in the project.

---

## 7. When to use which — decision table

| Situation | Use |
|---|---|
| A single value / badge / avatar is loading inside an otherwise-rendered page | `<Skeleton className="h-… w-…" />` |
| A whole list / grid / table in a **client** component (`isLoading` from React Query) | `<AnimatedLoadingSkeleton />` (add `className="max-w-none border bg-transparent p-2 shadow-none"` if it sits inside a table border) |
| A **server** component page that `await`s data before rendering | add `loading.tsx` to that route segment rendering `<AnimatedLoadingSkeleton className="max-w-none" />` in the page's width container |
| A panel inside a `<Card>` is fetching (e.g. `<LinkedQuestionsPanel>`) | `<AnimatedLoadingSkeleton className="max-w-none bg-transparent p-0 shadow-none" />` |
| You want a strictly tabular skeleton (rows, not cards) | not built yet — `<AnimatedLoadingSkeleton>` is fine for now; a `<TableSkeleton>` of N `<Skeleton>` rows is the natural follow-up if a card grid ever looks wrong on a dense table |
| The unified wizard is transitioning between questions | the wizard's own inline pending state (it's a single-question swap, not a page load) |

---

**Prev:** [`11_Survey_System.md`](11_Survey_System.md) &nbsp;·&nbsp; **End of SETUP track.**
