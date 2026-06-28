# Frontend Domain

Next.js 14 (App Router) · React · TypeScript · Tailwind CSS · Radix UI · next-intl (EN/SI/TA) · React Query

## Implemented screens

### SME routes
| Route | Description |
|-------|-------------|
| `/dashboard` | Pending-regulations feed; sector-relevant active regulations not yet touched |
| `/surveys` | Survey hub — lists all available per-module + unified survey modes |
| `/surveys/module/[id]` | Per-module session survey — SurveyLauncher → SurveyWizard one-question loop |
| `/surveys/unified` | Unified survey (all modules) — same session-based flow |
| `/surveys/history` | Completed session list — session_id, mode, questions_answered, completed_at |
| `/regulations` | Regulation browser — active regulations with detail view |
| `/risk` | **Fully implemented** — two-card layout: M2 knowledge score by domain + M3 compliance/behavioural signals |

### Admin routes
| Route | Description |
|-------|-------------|
| `/admin/questions` | Unified question bank — CRUD for all modules |
| `/admin/questions/new` | New question form (5-card, 5 formats) |
| `/admin/questions/[code]/edit` | Edit question |
| `/admin/regulations` | Regulations list |
| `/admin/regulations/new` | 3-step authoring wizard |
| `/admin/regulations/[id]/edit` | Edit regulation |
| `/admin/regulations/[id]/flow` | CSS-grid visual branching flow canvas (M1/M2/M3 columns) |
| `/admin/regulations/[id]/authoring` | Authoring wizard |
| `/admin/translations` | Translation queue — untranslated questions + regulations |
| `/admin/users` | User CRUD |
| `/admin/settings` | Survey submission limits — per-role caps persisted to `survey_limits` singleton |
| `/admin/activity-log` | Append-only audit log |
| `/admin/m2/scores` | M2 knowledge scores per SME — color-coded green/amber/red |
| `/admin/m3/risk-signals` | Combined M2 score + M3 snapshots per SME |
| `/admin/surveys/awareness/responses` | M1 awareness responses view |

## Stub screens

| Route | Status |
|-------|--------|
| `/qa` | ComingSoon placeholder — ChromaDB RAG (BUILD_08) |
| `/verify` | ComingSoon placeholder — M4 misinformation classifier (BUILD_10) |

## Key components

| Component | Description |
|-----------|-------------|
| `survey-launcher.tsx` | Start/resume session button; LocalStorage-backed draft session |
| `survey-wizard.tsx` | One-question renderer; module accent CSS class swap (module-m1/m2/m3) |
| `flow-canvas.tsx` | CSS-grid visual branching editor (M1/M2/M3 columns) |
| `authoring-wizard.tsx` | 3-step regulation authoring wizard |
| `question-form.tsx` | 5-card admin question form |
| `vulnerability-form.tsx` | M3-specific form owning submit fan-out to M3Api.submitHistory + M3Api.submitBehavioural |
| `animated-loading-skeleton.tsx` | Animated shimmer placeholder |
| `pagination.tsx` | Shared paginator primitive |

## Files

### SETUP/
| File | Description |
|------|-------------|
| [05_Frontend_Development.md](SETUP/05_Frontend_Development.md) | Day-to-day commands, App Router structure, i18n, component patterns |
| [12_UI_Screens_and_Loading.md](SETUP/12_UI_Screens_and_Loading.md) | Screen-by-screen SME + admin map; reusable-component catalog; loading strategy |
| [13_Unified_Survey_Configuration.md](SETUP/13_Unified_Survey_Configuration.md) | Session-based survey flow, branching rules, regulation scoping, submission limits |

### Related M1 tracking workflows (in `../m1/`)
> The M1 tracking-workflow docs live in `enigmatrix-docs/m1/` alongside the rest of the M1 backend + research doc set. They are cross-referenced here so frontend devs can find them; the canonical home is the m1/ folder.

| File | Audience | Status |
|------|----------|--------|
| [14_M1_Tracking_Workflows.md](../m1/14_M1_Tracking_Workflows.md) | Both | 🟡 (parent index) |
| [14_M1_1_Admin_Pipeline_State_Tracking.md](../m1/14_M1_1_Admin_Pipeline_State_Tracking.md) | Admin | 🟡 Partial |
| [14_M1_2_Admin_Review_Queue_Triage.md](../m1/14_M1_2_Admin_Review_Queue_Triage.md) | Admin | 🔲 Deferred |
| [14_M1_3_Admin_Expert_Verification.md](../m1/14_M1_3_Admin_Expert_Verification.md) | Admin | ✅ Shipped |
| [14_M1_4_Admin_Lag_Analytics.md](../m1/14_M1_4_Admin_Lag_Analytics.md) | Admin | 🔲 Deferred |
| [14_M1_5_SME_Regulation_Discovery.md](../m1/14_M1_5_SME_Regulation_Discovery.md) | SME | 🟡 Partial |
| [14_M1_6_SME_Awareness_Survey.md](../m1/14_M1_6_SME_Awareness_Survey.md) | SME | ✅ Shipped |
| [14_M1_7_SME_Compliance_Action_Tracking.md](../m1/14_M1_7_SME_Compliance_Action_Tracking.md) | SME | 🟡 Partial |
| [14_M1_8_SME_Deadline_Alert_History.md](../m1/14_M1_8_SME_Deadline_Alert_History.md) | SME | 🔲 Deferred |
| [14_M1_9_Category_Sector_Workflows.md](../m1/14_M1_9_Category_Sector_Workflows.md) | Both | Reference |

### BUILD_PLAN/
| File | Description |
|------|-------------|
| [BUILD_05_Frontend_App.md](BUILD_PLAN/BUILD_05_Frontend_App.md) | Next.js 14 scaffold spec: design tokens, API client layer, i18n setup |
| [BUILD_13_Admin_and_Annotation.md](BUILD_PLAN/BUILD_13_Admin_and_Annotation.md) | Admin console, Label Studio bridge, audit trail, bulk CSV operations |

### Root
| File | Description |
|------|-------------|
| [APP_GUIDE.md](APP_GUIDE.md) | User-facing application guide — roles, feature matrix, survey flow, risk dashboard |
