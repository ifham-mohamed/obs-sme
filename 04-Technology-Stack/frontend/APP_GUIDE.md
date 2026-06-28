# Enigmatrix — Complete Application Guide

Enigmatrix is a web platform that helps Sri Lankan Small and Medium Enterprises (SMEs) understand, track, and comply with tax and regulatory changes. It collects structured data across three active modules — Awareness (M1), Knowledge (M2), and Vulnerability (M3) — to produce an SME-specific regulatory compliance risk profile. A fourth module, Misinformation Detection (M4), is defined in the architecture but not yet implemented.

**Technology stack:** Next.js 14 (App Router) · FastAPI · PostgreSQL · Tailwind CSS · Radix UI · next-intl (EN / SI / TA)

---

## 1. User Roles

| Role | Code | What they can do |
|------|------|-----------------|
| SME | `sme` | Take surveys, view their own dashboard, regulations list, risk score, Q&A |
| Admin | `admin` | Everything an SME can do + full back-office: user management, regulation CRUD, question CRUD, translations, audit log |
| Annotator | `annotator` | Currently same access as SME; planned: annotate survey responses and regulation summaries for ML training |

Role is set at registration (`sme` self-registration only) or by an admin creating the account.  
Role rank: `sme` (0) < `annotator` (1) < `admin` (2) — `hasAtLeast(role, "annotator")` checks `≥ 1`.

---

## 2. Application Shell

### Navigation

**Desktop** (≥ `md` breakpoint): sticky sidebar on the left. Collapses to icon-only mode via the toggle in the topbar. Active route highlighted with an accent background and a left-border stripe.

**Mobile**: hamburger icon in the topbar opens a sheet drawer. Closes automatically on navigation.

**Topbar** (always visible):
- Sidebar collapse toggle (desktop only)
- App name / role badge
- Locale switcher: EN / Sinhala / Tamil (writes `NEXT_LOCALE` cookie)
- Light / dark / system theme toggle
- Avatar menu → Sign out

---

## 3. SME Screens

### 3.1 Landing Page — `/`
Public. Shows the Enigmatrix brand with "Sign In" and "Register" buttons.  
Also provides a theme toggle and locale switcher for accessibility before login.

### 3.2 Register — `/register`
Public. Collects:
- Email and password (min 8 chars)
- SME profile: sector, sub-sector, region, employee band, turnover band, business age, preferred language

On submit → creates User (role = `sme`) + SMEProfile → auto-logs-in → redirects to `/dashboard`.

### 3.3 Login — `/login`
Public. Email + password. On success → stores HTTP-only `access` and `refresh` cookies → redirects to the `next` query param or `/dashboard`.  
Failed logins are rate-limited (5 tries / minute) and recorded in the audit log.

### 3.4 Dashboard — `/dashboard`

What you see:
- **Pending regulations card** — regulations not yet surveyed by this SME, showing title, domain, severity badge, and a "Start survey" link
- **Summary stats** — answered survey count, overall knowledge score, latest vulnerability snapshot date
- **Module status chips** — green/amber/grey per module completion

**Example:** An SME in the retail sector sees "VAT Rate Change 2026" as pending (because it applies to `universal` + retail). Clicking "Start survey" goes to `/surveys/regulation/{uuid}` — the unified wizard scoped to that regulation.

> **SME tracking workflows** are documented in [SETUP/14_M1_Tracking_Workflows.md](../m1/14_M1_Tracking_Workflows.md) — the workflow series covers regulation discovery ([14_M1_5](../m1/14_M1_5_SME_Regulation_Discovery.md)), awareness survey participation ([14_M1_6](../m1/14_M1_6_SME_Awareness_Survey.md)), compliance status tracking ([14_M1_7](../m1/14_M1_7_SME_Compliance_Action_Tracking.md)), and deadline + alert history ([14_M1_8](../m1/14_M1_8_SME_Deadline_Alert_History.md), deferred). Each carries a status badge so the SME sees what's available today vs in a future release.

### 3.5 Regulations — `/regulations`
Lists all active regulations with:
- Title (in user's preferred language with EN fallback)
- Domain badge (VAT, EPF, etc.)
- Severity level (1–5 stars)
- Effective date
- Penalty range (LKR)
- "Start survey" / "Completed" button

SMEs can filter by domain or search by title.

### 3.6 Surveys Hub — `/surveys`
Two-tab layout:

**Tab 1 — By Regulation:** Cards for each pending regulation. Each card shows the regulation title, domain, severity, and a "Begin" button that links to the regulation-scoped unified wizard.

**Tab 2 — By Module:** Three cards for the standalone module surveys:
- Awareness (`/surveys/awareness`)
- Knowledge test (`/surveys/knowledge`)
- Vulnerability profile (`/surveys/vulnerability`)

### 3.7 Awareness Survey — `/surveys/awareness`
Standalone M1 module. 12 questions drawn from the `survey_questions` table (module_number = 1).

**Question types in this module:**
- Single-choice: "How did you first learn about the April 2026 VAT threshold change?"
- Multi-select: "Which channels do you actively monitor at least weekly?"
- Likert 1–5: "How confident are you that you would learn about a new regulation within one week?"
- Yes/no with conditional follow-up: "Are you aware of the April 2026 VAT threshold change?" → if Yes → "What is the new threshold?"

**No scoring** — answers profile awareness gaps only.  
On submit → `/surveys/awareness/thank-you`.

### 3.8 Knowledge Test — `/surveys/knowledge`
Standalone M2 module. Questions from `survey_questions` (module_number = 2) filtered by the SME's sector.

**Question types:**
- MCQ single: "What is the current VAT rate?" → correct answer: 18%
- Ordered steps: "Arrange the VAT filing steps in order"
- Numeric: "What is the VAT registration threshold (LKR millions)?"
- Scenario response: "Given this scenario, what would be the penalty?"

**Auto-scoring:** Each answer is scored against `correct_answer_json`. `ordered_steps` supports partial credit (first + last correct → 0.5 pts).

After submit → M2 knowledge score is recomputed (cached in `m2_knowledge_scores`) → redirect to `/surveys/knowledge/thank-you` with score summary.

### 3.9 Vulnerability Profile — `/surveys/vulnerability`
Standalone M3 module. ~32 questions across 4 sections:

| Section | What it covers | Example |
|---------|---------------|---------|
| Compliance History | Missed deadlines, penalties, audits | "In the last 24 months, has your business missed ANY tax filing deadline?" |
| Day-to-Day Behaviour | Filing method, record-keeping, staff | "How do you currently maintain your business books?" |
| Stress & Capacity | Cash flow, language barriers | "Rate cash-flow difficulty affecting compliance (1 = no difficulty, 5 = severe)" |
| Sector-specific | Conditional on sector | Only shows for retail: "Do you track daily cash-register reconciliations?" |

**No scoring** — answers build the SME's behavioural risk profile.  
Answers projected into `m3_compliance_history` + `m3_behavioural_signals` snapshots.

### 3.10 Unified Wizard — `/surveys/regulation/[id]`
Regulation-scoped flow that crosses all three modules in one session.

**How it works (session-based API, Session 16+):**
1. `<SurveyLauncher>` calls `POST /api/v1/survey-sessions/start` with `survey_mode="unified"` + `regulation_id` → creates a `survey_sessions` row; enforces the `survey_limits` cap.
2. `<SurveyWizard>` loops: `GET /api/v1/survey-sessions/{id}/next-question` → render → `POST /api/v1/survey-sessions/{id}/answer` → repeat.
3. The engine evaluates `next_question_rules` JSONB on each question to determine routing.
4. When all questions are answered: `POST /api/v1/survey-sessions/{id}/complete` → redirect to thank-you.

**Session modes and caps:**

| Mode | Survey | Cap |
|------|--------|-----|
| `per_module_m1` | M1 Awareness only | 10 questions |
| `per_module_m2` | M2 Knowledge only | 10 questions |
| `per_module_m3` | M3 Vulnerability only | 10 questions |
| `per_module_m4` | M4 Misinformation only | 10 questions |
| `unified` | Cross-module (all four) | 20 questions |

**Visual cues:** The accent colour shifts as the flow crosses module boundaries:
- M1 questions → trust-blue (`module-m1`)
- M2 questions → emerald (`module-m2`)
- M3 questions → amber (`module-m3`)

**Example journey** (VAT regulation):
1. "Aware of April 2026 VAT threshold change?" (M1) → answer: No
2. → rule fires → "What are the steps to VAT registration?" (M2) → wrong answer
3. → → "In the last 24 months, has your business missed any filing deadline?" (M3)
4. → Complete → session marked `completed` → redirect to thank-you

### 3.11 Survey History — `/surveys/history`
SME's list of completed survey sessions.

**What you see:** a table of past `survey_sessions` rows — session ID (truncated UUID), mode, questions answered, completion date, status badge. Backed by `GET /api/v1/survey-sessions/my-history`.

Empty state links back to `/surveys` to start a new session.

### 3.13 Risk Assessment — `/risk`
Displays the SME's composite risk profile combining M2 knowledge score + M3 behavioural signals.

**Fully implemented.** The page fetches two sources in parallel and renders two cards:

1. **Knowledge score card** — overall `%` + per-domain breakdown (VAT, Income Tax, EPF, etc.) showing correct/total counts and percentage per domain. Colour-coded: green ≥70%, amber ≥40%, red <40%.
2. **Vulnerability signals card** — latest M3 compliance-history snapshot (missed deadlines in last 24 months, penalty band, under-audit status, self-confidence Likert) + behavioural signals (top barriers ranked by SME, filing method, books method).

If a card has no data yet (SME hasn't taken the M2 or M3 survey), it shows an empty-state prompt with a CTA button to `/surveys/module/m2` or `/surveys/module/m3`. Backed by `GET /api/v1/m2/sme/{sme_id}/knowledge_score` (M2 side) and `GET /api/v1/m3/sme/{sme_id}/risk-signals` (M3 combined view). The risk signals endpoint joins the latest `m3_compliance_history` + `m3_behavioural_signals` snapshots with the cached M2 score in one payload.

> **Note:** The full ML risk score (XGBoost/LightGBM, BUILD_09) is not yet wired. The page shows raw signals today; the ML model will add a composite risk score when BUILD_09 ships.

### 3.14 Q&A — `/qa`
RAG-backed question answering against the regulation database.  
Current status: **coming soon** — backend returns 501.

### 3.15 Verify — `/verify`
Claim verification (Module 4 — Misinformation Detection).  
Current status: **coming soon** — backend returns 501.

---

## 4. Admin Screens

All admin routes require `role = "admin"`. Non-admins are redirected to `/dashboard`.

> **Admin tracking workflows** are documented in [SETUP/14_M1_Tracking_Workflows.md](../m1/14_M1_Tracking_Workflows.md) — the workflow series covers pipeline-state triage ([14_M1_1](../m1/14_M1_1_Admin_Pipeline_State_Tracking.md)), needs-review queue ([14_M1_2](../m1/14_M1_2_Admin_Review_Queue_Triage.md), deferred), expert verification ([14_M1_3](../m1/14_M1_3_Admin_Expert_Verification.md)), and lag analytics ([14_M1_4](../m1/14_M1_4_Admin_Lag_Analytics.md), deferred). Each carries a status badge so a new admin sees what's shipped today vs deferred to BUILD_13.

### 4.1 Users — `/admin/users`
Full user management table.

**What you see:** paginated table with email, role badge, sector, status (active/inactive), created date.

**Actions:**
| Action | How |
|--------|-----|
| Create user | "New user" button → dialog with email, password, role (sme/admin/annotator), profile fields |
| Edit role / profile | Row action → edit dialog |
| Activate / deactivate | Toggle via row action; cannot deactivate the last admin |
| Reset password | Row action → sets a new password; old sessions invalidated |
| Delete | Row action → soft-delete (sets `is_active = false`); cannot delete self |

**Example:** Admin creates an annotator account for a research assistant:
1. Click "New user" → fill email, set role = `annotator` → save
2. Annotator receives credentials and can log in with SME-equivalent survey access

### 4.2 Regulations — `/admin/regulations`
Browse and manage all regulations (M1 entries).

**List view:** paginated table with title (EN), document type, domain, severity, active status, expert-verified badge.

**Actions:**
| Action | Route |
|--------|-------|
| View list | `/admin/regulations` |
| Create new | `/admin/regulations/new` — form with all fields |
| Edit | `/admin/regulations/[id]/edit` — same form pre-filled |
| Authoring wizard | `/admin/regulations/[id]/authoring` — 3-step guided wizard |
| Flow canvas | `/admin/regulations/[id]/flow` — CSS-grid visual flow builder |
| Archive (soft-delete) | Row action → sets `is_active = false` |

**Regulation form fields:**
- Short code (e.g., `VAT-2026-01`)
- Title in EN / SI / TA
- Summary in EN / SI / TA
- Document type: bill / act / extraordinary_gazette / weekly_gazette / circular / order / notification
- Domain: VAT / INCOME_TAX / WHT / SSCL / EPF / ETF / ROC / CUS / TDL
- Effective date, penalty range (LKR), severity (1–5)
- Sectors this applies to (multi-select)
- SME relevance toggle + confidence score
- Expert verified toggle

### 4.3 Authoring Wizard — `/admin/regulations/[id]/authoring`
3-step wizard for building the question flow attached to a regulation:

1. **Step 1 (M1 root):** Select or create the awareness question that starts this regulation's flow
2. **Step 2 (M2 branch):** Add knowledge questions that fire when awareness answer indicates a gap
3. **Step 3 (M3 branch):** Add vulnerability questions for high-risk signals

Each step shows a preview of the question and allows editing `next_question_rules`.

### 4.4 Flow Canvas — `/admin/regulations/[id]/flow`
Visual CSS-grid layout of the full branching flow for a regulation.

- Each question is a card showing: question code, format, first 60 chars of prompt, branching predicates
- Arrows indicate flow direction (M1 → M2 → M3)
- Click a card to open `<FlowQuestionDrawer>` for inline editing of the question's text, options, and `next_question_rules`

### 4.5 Question Bank — `/admin/questions`
Unified CRUD for all questions across modules 1, 2, and 3.

**Filter bar:** module number, domain, sector, knowledge type, format, active/archived, search by prompt text.

**List columns:** code, module badge, format, domain, sector, verified status, linked regulations count, active status.

**Actions:**
| Action | How |
|--------|-----|
| Create question | "New question" → `/admin/questions/new` |
| Edit | Row action → `/admin/questions/[code]/edit` |
| Verify / unverify | Row action (single) or checkbox + "Bulk verify" |
| Archive | Row action → `is_active = false` |
| Restore | Row action (on archived rows) |
| Duplicate | Row action → creates a copy with `-copy` suffix |

**Question form** (5 cards):

| Card | Fields |
|------|--------|
| Identity | `question_code` (auto-suggested `awareness.v1.qNN`), module (1/2/3), format, knowledge type |
| Linkage | Linked regulation (combobox with search), `is_primary`, `weight`, `is_branching_root`, `is_baseline` |
| Localised text | Prompt EN / SI / TA, `is_required` |
| Answers | `options_json` (add/remove/reorder option chips), `correct_answer_json`, `scoring_rubric_json` |
| Branching | `next_question_rules` editor — add rule rows (`answer_eq / answer_in / answer_lt / answer_gt`) with `goto_question_code` target picker |

### 4.6 Translation Queue — `/admin/translations`
Lists all questions and regulations that are missing Sinhala or Tamil translations.

**Columns:** type (question/regulation), primary text (EN), SI status, TA status.

**Actions:** Click a row to expand the edit fields for the missing locale. Save updates the database record directly.

### 4.7 M2 Scores — `/admin/m2/scores`
Per-SME knowledge score breakdown.

**Columns:** SME email, sector, overall score %, by-domain breakdown (VAT %, EPF %, etc.), computed date.

**Pagination:** link-mode, server-rendered.

### 4.8 M3 Risk Signals — `/admin/m3/risk-signals`
Combined view: M2 knowledge score + latest M3 compliance history snapshot + latest M3 behavioural signals — one row per SME.

**Columns:** SME, sector, overall knowledge %, penalty history, under audit flag, filing method, penalty band, latest snapshot date.

**Use case:** Researcher or admin can quickly identify the highest-risk SMEs for follow-up or ML training data selection.

### 4.9 Survey Responses — `/admin/surveys/awareness/responses`
Paginated list of all Awareness (M1) survey submissions.

**Columns:** SME email, sector, region, submitted date, answer count.

**Click row** → expands to show individual question + answer pairs.

### 4.10 Activity Log — `/admin/activity-log`
Append-only audit trail of every data-mutating action across the platform.

**Filters:** event type (dropdown), table name, actor (email prefix), record ID, record key, date range (since/until), free-text search.

**Columns:** When, Event (colour-coded badge), Target (table + record key/ID), User, Details.

**Detail rendering is type-aware:**
- `survey.submitted` → "awareness · 12 answers · scored · risk snapshot"
- `*.updated` → list of changed fields as muted chips
- `auth.login.failure` → email + reason
- `*.bulk_verified` → "N verified by X"
- Anything else → collapsible raw JSON `<details>`

**Authorship footer:** The regulation edit page and question edit page both show "Created by · Last edited by · View history" linking back to the Activity Log filtered to that record.

### 4.11 Settings — `/admin/settings`
Survey submission limits — the one place where admins control how many times each role can submit surveys.

**What you see:** Three number inputs:
- **SME limit** — default 10; maximum number of survey sessions an SME account can complete.
- **Annotator limit** — default 0 (unlimited); maximum for annotator accounts.
- **Admin limit** — default 0 (unlimited); maximum for admin accounts.

**How it works:** The values are stored in the `survey_limits` singleton table (single row, `id=1`). On every `POST /api/v1/survey-sessions/start`, the service reads this singleton and rejects with a 403 if the caller's completed-session count meets or exceeds their cap. Changes take effect immediately — no restart needed.

**Resilience:** if `alembic upgrade head` hasn't been run yet, the service falls back to safe in-memory defaults and the settings page shows those defaults.

---

## 5. Documentation — `/docs`

In-app viewer for all documentation files in the `docs/` folder.  
Accessible to all authenticated users via the "Documentation" link in the sidebar.

**Routes:**
- `/docs` → hub with section cards
- `/docs/APP_GUIDE` → this document
- `/docs/SETUP/[file]` → setup and architecture guides
- `/docs/tracker/[file]` → progress trackers
- `/docs/research/[file]` → research and ML architecture docs
- `/docs/BUILD_PLAN/[file]` → build plan specifications

All files render with GitHub-flavored markdown: tables, code blocks, task lists, strikethrough, blockquotes.

---

## 6. Navigation Summary by Role

| Section | SME | Annotator | Admin |
|---------|-----|-----------|-------|
| Dashboard | ✅ | ✅ | ✅ |
| Regulations (survey hub) | ✅ | ✅ | ✅ |
| Awareness / Knowledge / Vulnerability surveys | ✅ | ✅ | ✅ |
| Unified wizard | ✅ | ✅ | ✅ |
| Risk dashboard (`/risk`) | ✅ (implemented) | ✅ (implemented) | ✅ (implemented) |
| Q&A (`/qa`) | ✅ (coming soon — BUILD_08) | ✅ (coming soon) | ✅ (coming soon) |
| Verify claim (`/verify`) | ✅ (coming soon — BUILD_10) | ✅ (coming soon) | ✅ (coming soon) |
| Documentation | ✅ | ✅ | ✅ |
| Users management | ❌ | ❌ | ✅ |
| Regulations CRUD | ❌ | ❌ | ✅ |
| Question bank | ❌ | ❌ | ✅ |
| Translations | ❌ | ❌ | ✅ |
| M2 scores | ❌ | ❌ | ✅ |
| M3 risk signals | ❌ | ❌ | ✅ |
| Survey responses | ❌ | ❌ | ✅ |
| Activity log | ❌ | ❌ | ✅ |

---

## 7. Example End-to-End Journey

**Scenario:** Priya, a retail SME owner, logs in for the first time.

1. **Register** → fills sector=retail, region=Western Province, preferred language=EN
2. **Dashboard** → sees "VAT Rate Change 2026" as pending (universal + retail regulation)
3. **Start survey** → `/surveys/regulation/{vat-uuid}`
4. **Q1 (M1):** "Are you aware of the April 2026 VAT threshold change?" → answers "No"
5. Rule fires → **Q2 (M2):** "What are the steps to VAT registration?" — shown in emerald (M2 accent)
6. Answers incorrectly (wrong order) → partial credit: 0.5/1.0
7. Rule fires → **Q3 (M3):** "Has your business missed any tax filing deadline in the last 24 months?" — shown in amber (M3 accent)
8. Answers "Yes, 1–2 times" → follow-up Q4 fires (M3_HIST_002) — "Which deadlines?"
9. Completes all M3 questions → `flow_status: "completed"`
10. **Dashboard** → knowledge score updated to 50%, vulnerability snapshot captured
11. **Admin view** → Priya appears in M3 risk signals with: knowledge_pct=0.50, missed_deadline=true, penalty_received=false

---

## 8. Auth & Session Details

- Tokens: HS256 JWT, stored in HTTP-only cookies (`access` 15 min, `refresh` 7 days)
- Server-side route protection: `requireUser()` in `(app)/layout.tsx`, `requireRole("admin")` in `(admin)/layout.tsx`
- Middleware fast-path: checks `access` cookie presence for `/dashboard`, `/surveys`, `/regulations`, `/qa`, `/verify`, `/risk`, `/admin` — redirects to `/login?next=...` if absent
- All auth events (register, login success/failure, refresh, password reset) are written to the audit log
