# 14 — M1 Tracking Workflows

> **What this is.** A workflow index for Module 1 — how an admin and an SME *track* regulatory information through every M1 surface in the UI. Eight tracking surfaces (4 admin × 4 SME) plus a cross-cutting category × sector reference. Complements [12_UI_Screens_and_Loading.md](../frontend/SETUP/12_UI_Screens_and_Loading.md), which maps the *screens*; this doc maps the *verbs*.
> **Implementation status:** 🟡 Partial — 3 of 8 surfaces shipped, 2 partial, 3 deferred. Each sub-step companion carries its own status badge.
> **See also (backend):** [README.md](README.md) — the 43-file M1 backend + research doc set.

---

## Why this doc exists

The M1 backend docs (`enigmatrix-docs/m1/`) describe a regulation's life as a state machine: a gazette is ingested → text extracted → classified → summarised → alerted → archived. The frontend docs (12_UI_Screens) map the screens that exist today. Neither answers the question a new contributor most often asks: **"As an admin, what do I do when a low-confidence classification lands? As an SME, what do I do when an alert arrives?"** This doc is that workflow guide — one section per tracking surface, each pointing at the screen (12_UI_Screens), the procedure (this doc + its companions), the backend reference (`m1/`), and the BUILD phase.

---

## The 8+1 tracking surfaces at a glance

| #   | Surface                                               | Audience | Status      | Detail in                                                                              |
| --- | ----------------------------------------------------- | -------- | ----------- | -------------------------------------------------------------------------------------- |
| A1  | Pipeline-state tracking (Stage A→F status machine)    | Admin    | 🟡 Partial  | [14_M1_1_Admin_Pipeline_State_Tracking.md](14_M1_1_Admin_Pipeline_State_Tracking.md)   |
| A2  | Needs-review queue triage                             | Admin    | 🔲 Deferred | [14_M1_2_Admin_Review_Queue_Triage.md](14_M1_2_Admin_Review_Queue_Triage.md)           |
| A3  | Expert-verification ledger                            | Admin    | ✅ Shipped   | [14_M1_3_Admin_Expert_Verification.md](14_M1_3_Admin_Expert_Verification.md)           |
| A4  | Lag analytics + propagation tracker                   | Admin    | 🔲 Deferred | [14_M1_4_Admin_Lag_Analytics.md](14_M1_4_Admin_Lag_Analytics.md)                       |
| S1  | Regulation discovery (sector + region filter)         | SME      | 🟡 Partial  | [14_M1_5_SME_Regulation_Discovery.md](14_M1_5_SME_Regulation_Discovery.md)             |
| S2  | Awareness survey participation (Q1–Q8)                | SME      | ✅ Shipped   | [14_M1_6_SME_Awareness_Survey.md](14_M1_6_SME_Awareness_Survey.md)                     |
| S3  | Compliance / action-taken status per regulation       | SME      | 🟡 Partial  | [14_M1_7_SME_Compliance_Action_Tracking.md](14_M1_7_SME_Compliance_Action_Tracking.md) |
| S4  | Deadline + alert delivery history                     | SME      | 🔲 Deferred | [14_M1_8_SME_Deadline_Alert_History.md](14_M1_8_SME_Deadline_Alert_History.md)         |
| X9  | Category × Sector workflows (cross-cutting reference) | Both     | Reference   | [14_M1_9_Category_Sector_Workflows.md](14_M1_9_Category_Sector_Workflows.md)           |

`✅` = the workflow runs end-to-end in the UI today. `🟡` = the data + some UI exists but a key surface is missing. `🔲` = backend-only today; the companion describes the *intended* UI for when BUILD_07/13 lands it.

---

## How an admin spends a day with M1

The admin's M1 day-to-day is a triage loop. Drawn from the 12_UI_Screens screen map + the M1 backend state machine, the steady-state procedure looks like:

```
[09:00] Open /admin/regulations
         ↓ apply filter "unverified=true" + sort by created_at DESC
         ↓ see the overnight ingestion batch (Stage A → C complete; Stage D pending review)
[09:10] Pick the top row → /admin/regulations/[id]/edit
         ↓ review classifier's change_category + sectors against the regulation summary
         ↓ if confident → click "Verify" → status flips, audit-log row written  [A3]
         ↓ if low-confidence / wrong category → override in form + save  [A1, A2 once shipped]
[10:30] Open /admin/regulations/[id]/flow  for any regulation that has a survey flow
         ↓ verify the M1→M2→M3 branching is wired
[11:30] (Once shipped) Open /admin/m1/review-queue
         ↓ sort by classifier_confidence asc
         ↓ triage the 5–15 items where confidence < 0.70  [A2]
[14:00] (Once shipped) Open /admin/m1/analytics
         ↓ check lag p50 by channel; investigate if any channel slipped > 1 day vs last week  [A4]
[16:00] Open /admin/activity-log
         ↓ scan for verify / archive events; ensure expert_verified coverage trending toward 30%
```

The first three lines are shipped today. The fourth and fifth describe surfaces that are 🔲 — the companions document them so the UI lands consistent with the backend invariants.

## How an SME spends a week with M1

The SME's M1 cadence is *not* daily — it's "when a deadline approaches" or "when something new lands". The procedure:

```
[Monday morning] /dashboard
                  ↓ "Pending regulations" widget shows up to 3 sector-relevant cards  [S1, S3]
                  ↓ "Survey progress" stat shows 7/9 questions answered
[Click a card] → /surveys/regulation/[id]
                  ↓ unified M1→M2→M3 wizard scoped to that regulation
                  ↓ answer Q1–Q7 awareness questions + M2 knowledge + M3 vulnerability  [S2]
[After submit]   /surveys/history
                  ↓ see the completed session row; status pill = completed
                  ↓ scan recent runs to confirm action-taken on prior regulations  [S3]
[Later — once shipped] /portal/m1/deadlines
                  ↓ deadline countdown widget for the regulations they've engaged with  [S4]
                  ↓ alert-history table — every email/SMS sent to this SME for M1
```

S1 + S2 are shipped (with S1 missing the sector-applicability filter). S3 is captured in survey responses but has no dedicated tracker page. S4 is fully deferred.

---

## Cross-references

- **Screen map**: [12_UI_Screens_and_Loading.md](../frontend/SETUP/12_UI_Screens_and_Loading.md) — every M1 screen this workflow doc references is documented there.
- **Backend state machine + tables**: [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) (pipeline-state status enum), [08_M1_Full_System_Architecture.md §4](08_M1_Full_System_Architecture.md) (route table).
- **Research findings the analytics surfaces produce**: [08_M1_1_Research_Findings_Extraction.md](08_M1_1_Research_Findings_Extraction.md).
- **Frontend components catalogue**: [12_UI_Screens_and_Loading.md §4](../frontend/SETUP/12_UI_Screens_and_Loading.md) (`<RegulationCard>`, `<VerificationBadge>`, `<SurveyWizard>`, `<FlowCanvas>`, etc.).
- **Build phases that ship the deferred surfaces**: [../BUILD_PLAN/BUILD_13_Admin_and_Annotation.md](../frontend/BUILD_PLAN/BUILD_13_Admin_and_Annotation.md) (admin), BUILD_07 (ingest pipeline that feeds A1/A4), BUILD_12 (schedulers that feed A4/S4).

---

## Notes on the audience split

The companion files mix two reader roles — the *user* (admin or SME going through the procedure) and the *implementer* (the frontend dev building or maintaining the surface). The convention:

- **"Detailed process"** is the user procedure (verbs, no jargon).
- **"Technology choices"** + **"Validation & acceptance criteria"** are for the implementer (component picks, loading-state contracts, a11y notes).
- **"Worked example"** is a concrete walkthrough using the seeded demo regulations (`VAT_2024_AMD`, `EPF_2024_RATE`, the multi-pin adapter case from [m1/02_M1_4_Worked_Examples_All_Tables.md](02_M1_4_Worked_Examples_All_Tables.md)).

When a surface is 🔲 deferred, the "Detailed process" describes the *intended* workflow drawn from the backend M1 docs; the section header marks it explicitly so a reader doesn't mistake an intended UI for a shipped one.


# 14_M1_1 — Admin Pipeline-State Tracking

> Companion to [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) — covers tracking surface **A1: Pipeline-state tracking (Stage A→F status machine per regulation)**.
> **Implementation status:** 🟡 Partial — status field exists on every regulation row; admin list surfaces it in the table; no dedicated stage-by-stage dashboard yet.

## Purpose

A regulation moves through six pipeline stages (`ingested → extracted → classified → summarized → alerted → archived`) defined in [m1/02_M1_Data_Requirements.md §2.1](02_M1_Data_Requirements.md). At any moment, an admin needs to answer: *which regulations are stuck mid-pipeline?* and *what stage is the bottleneck right now?* This tracking surface is the daily-triage entry point — what the admin opens first in the morning.

## Detailed process

Today the workflow runs through [`/admin/regulations`](../../../frontend/app/(admin)/admin/regulations) with the status surfaced as a column on the table.

1. **Open the regulation bank.** Navigate to `/admin/regulations`. The page renders a polished `<Table>` (per [12_UI_Screens §3.1](../frontend/SETUP/12_UI_Screens_and_Loading.md)) with per-row `status` rendered as a `<StatusBadge>` (`components/ui/status-badge.tsx` — colour-coded success / warning / pending / error / neutral).
2. **Filter by status.** Use the vertical filter rail on the left to apply `Status = "ingested"` (or any pipeline stage). The URL reflects the filter (`?status=ingested`). Sort by `created_at DESC` to see the most recent stuck items first.
3. **Inspect a single regulation.** Click a row → `/admin/regulations/[id]/edit`. The detail page shows the regulation's current stage in the header band + the next expected transition.
4. **Manual transition.** Where the admin can advance a stage manually (e.g. forcing a re-classify when the auto-pipeline is unhealthy), the action lives in the row's `<RowActions>` menu or as a primary button on the detail page.
5. **Bulk re-trigger** (advanced). For systemic issues — say, "yesterday's batch all stuck at `extracted` because the classifier was down" — the admin selects multiple rows + clicks "Re-classify selected" in the bulk-action bar. The action enqueues a Celery task per row (see [m1/03_M1_Data_Collection.md §6.1](03_M1_Data_Collection.md) for the Celery + Scrapy interaction).

> **🔲 Intended workflow — Stage Dashboard.** Once BUILD_13 ships the stage dashboard, an admin opens `/admin/m1/pipeline` for a Sankey-style view of how many regulations sit in each stage right now. Each block is clickable → filters the regulation list to that stage. Not yet built; this companion documents the *target*.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Status column on the existing `/admin/regulations` list (chosen) | Uses the regulation bank polish (filter rail, pagination, search) for free | ✅ Ship-fast — the column already exists | Once the regulation count exceeds ~500 active rows, a dedicated dashboard becomes more useful |
| Dedicated `/admin/m1/pipeline` Sankey-style dashboard | Best at-a-glance bottleneck view | 🔲 Deferred to BUILD_13 | After backend Stage A–F metrics are exposed in `m1_pipeline_audits` |
| Stage transitions as a separate `m1_regulation_stage_log` table | Audit-grade transition history | ❌ Audit log already captures every `status` field change — no new table needed | If we need ms-precision transitions for SLA reporting |
| Real-time push (websocket) of status changes | Live dashboard | ❌ Polling every 30s is sufficient for this workflow | If admins start reporting they want sub-second freshness |

## Worked example

A Monday-morning triage on a hypothetical overnight batch:

```
09:02 — admin opens /admin/regulations?status=ingested&sort=created_at:desc
         42 rows returned; all from the overnight Scrapy run; none have advanced
09:03 — admin spots that none reached "extracted" → Celery extraction worker is dead
09:04 — admin pages on-call (Slack #enigmatrix-ml); confirms Tesseract dependency missing
09:30 — on-call redeploys with the language pack; worker comes back up
09:35 — admin clicks "Refresh" → all 42 rows now at status="extracted"; 14 already at "classified"
09:40 — admin moves to the verification workflow (see 14_M1_3) for the 14 classified rows
```

The admin never had to write a SQL query — the table filter + status badges surface the bottleneck.

## Failure modes & edge cases

- **Status badge colour ambiguity.** `extraction_failed` and `extracted` could be confused at a glance. Mitigation: `StatusBadge` renders `extraction_failed` in `destructive` (red) and `extracted` in `pending` (amber). Visual hierarchy reinforced by an icon (X vs ⏳).
- **Stuck rows.** A regulation that has been at the same status > 24 h is *probably* stuck. Mitigation: when the stage-dashboard ships, rows older than the SLA flash an `<Alert>` (see [m1/12_M1_Monitoring_Maintenance.md §1](12_M1_Monitoring_Maintenance.md)).
- **Stale list during a Celery backlog.** A user mid-page might see counts shift under them as workers catch up. The admin list is `React Query`'s default `staleTime: 30s` — refresh button available in the topbar.
- **Archived rows.** `is_active=false` rows hide by default unless `?include_archived=true`. Admin can still filter to find them.

## Validation & acceptance criteria

- **A11y.** Status badges render an accessible label (`aria-label="Status: extraction failed"`) in addition to colour. Confirmed by axe-core CI sweep.
- **Loading state.** The table shows `<AnimatedLoadingSkeleton>` (chrome-stripped) inside the `<Table>` border during the first React Query fetch + on filter changes.
- **Empty state.** When the filter returns zero rows, show "No regulations match this filter" + a "Reset filters" button — not a blank table body.
- **Filter persistence.** Filters persist in the URL so the browser back button returns to the same view; refresh preserves the filter state.
- **Pagination state.** Page + page-size in the URL (`?page=2&size=50`) so deep-links work.

## Cross-references

- Parent: [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md)
- Screen reference: [12_UI_Screens_and_Loading.md §3.1](../frontend/SETUP/12_UI_Screens_and_Loading.md)
- Backend status enum: [02_M1_Data_Requirements.md §2.1](02_M1_Data_Requirements.md) (the 6 status values)
- Backend Celery transitions: [03_M1_Data_Collection.md §6.1](03_M1_Data_Collection.md)
- Monitoring of pipeline health: [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md)
- BUILD phase: BUILD_07 (backend Stage A–F), BUILD_13 (dedicated stage dashboard)
- Code: `frontend/app/(admin)/admin/regulations/page.tsx`, `frontend/components/ui/status-badge.tsx`


# 14_M1_2 — Admin Review-Queue Triage

> Companion to [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) — covers tracking surface **A2: Needs-review queue triage**.
> **Implementation status:** 🔲 Deferred — the backend flags `needs_review = true` on every classification with `confidence < 0.70`; no dedicated UI exists yet. The `/admin/regulations?needs_review=true` filter is the workaround. This companion describes the intended page.

## Purpose

The XLM-R classifier produces a confidence score per regulation. When confidence falls below 0.70, the row is auto-flagged `needs_review = true` and *the alert is suppressed* until an admin confirms. The review-queue page is where the admin clears that backlog — sorted by confidence ascending so the riskiest cases come first.

Without this dedicated surface, admins must scroll through the regulation bank with a filter applied; that works for a handful of items but breaks down once the queue exceeds ~20 rows. The page is the highest-value 🔲 deferred surface for M1.

## Detailed process

> 🔲 Intended workflow — design not yet locked.

1. **Open the queue.** Navigate to `/admin/m1/review-queue` (intended route). The page renders a table sorted by `confidence ASC` so the lowest-confidence rows surface first.
2. **Inspect a row.** Each row shows: regulation short code, title (locale-aware), classifier's predicted category, sectors, `confidence` (rendered as a thin bar 0–100 %), `created_at`, age in hours.
3. **Open detail (per-row).** Click a row → opens a slim `<Sheet>` drawer (not a full page) showing: the classification chunk that fed the classifier (first 512 tokens of cleaned text), the alternative top-3 category predictions with their softmax probabilities, the model version (`v1.0`, `v1.1` …), and a side-by-side "Classifier says X | Override to:" picker.
4. **Decide.** Three buttons in the drawer footer:
   - **Confirm** — accept the classifier's prediction; `needs_review = false`, alert dispatches.
   - **Override + Verify** — admin picks the correct category (and any sector edits) from the dropdowns; backend updates the row and writes an audit-log entry.
   - **Escalate to expert** — set `escalated_to_expert = true` on the row; the domain expert (CA / Attorney) receives an email + the row appears in their `/admin/m1/expert-queue` (a separate companion, not in this MVP).
5. **Bulk actions.** Multi-select checkboxes + a bulk action bar at the bottom: "Confirm selected" (only enables when all selected rows have the same category — otherwise greyed with tooltip "mixed categories — confirm individually").
6. **Keyboard navigation.** `j` / `k` move row focus; `Enter` opens the drawer; `c` confirms in the drawer; `o` opens the override picker. The keyboard shortcuts are documented in a `?` help modal.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Dedicated `/admin/m1/review-queue` page (chosen target) | Single-purpose surface optimised for high-throughput triage | 🔲 Target — ship in BUILD_13 | If queue volume stays below ~20/day after BUILD_07 launches, the filter-on-regulation-bank workaround stays viable |
| Drawer for detail (vs full-page route) | Triage flow stays in one tab; admin doesn't lose context | ✅ Drawer | If the drawer becomes too cramped — drawer width is 480 px; switch to full page if more than 3 stacked cards needed |
| Sort by confidence ASC by default | Highest-risk items get attention first | ✅ Default sort | If high-volume / low-confidence dominates, switch to `(confidence_bucket, age_hours) ASC` |
| Bulk "Confirm selected" (chosen) + Bulk "Override selected" (rejected) | Confirm is safe; override is dangerous in bulk | ✅ Confirm-only bulk; override is per-row | If admins request bulk-override, gate behind a second confirm modal |
| Keyboard shortcuts (`j`/`k`/`Enter`) | Power-user throughput | ✅ Ship at MVP — triage is a power-user workflow | Never remove |

## Worked example

A morning queue clear (intended):

```
09:15 — admin opens /admin/m1/review-queue
         Queue depth: 12 items, sorted by confidence ASC
         Top item: classifier confidence 0.42
         Item is VAT-amendment look-alike; classifier said "BUSINESS_REGISTRATION"
09:16 — admin clicks the row → drawer opens
         classification_chunk shows: "VAT registration threshold raised from LKR 60M to LKR 80M..."
         Top-3: TAX_RATE_CHANGE 0.32 | BUSINESS_REGISTRATION 0.42 | SECTOR_SPECIFIC 0.18
         Admin sees classifier ranked FINANCIAL above TAX_RATE_CHANGE — wrong
09:16 — admin clicks "Override + Verify" → picks TAX_RATE_CHANGE → save
         needs_review=false; expert_verified=true; audit-log row written
         Row disappears from queue; next item auto-focuses
09:22 — admin clears item #2–8 (most are straight Confirms — classifier was right but low-confidence)
09:25 — item #9 is genuinely ambiguous → admin clicks "Escalate to expert"
         Expert receives email; row tagged expert_pending
09:27 — queue cleared (5 confirmed, 3 overridden, 1 escalated, 3 left for expert)
```

This loop currently takes the admin ~30 minutes via the regulation-bank filter workaround. The dedicated page targets ≤ 15 minutes for the same workload.

## Failure modes & edge cases

- **Stale queue.** Admin starts working on a row that's already been confirmed in another tab (or by another admin). Mitigation: optimistic UI — when "Confirm" returns 409 Conflict, drawer surfaces "Already confirmed by {admin_email} at {time}" + offers "Move to next".
- **Confidence-only sort hides high-impact items.** A high-confidence classification on a critical regulation (e.g. nationwide VAT change) deserves a second look even at 0.85 confidence. Mitigation: a secondary `severity_level >= 4` view at the top of the page (collapsible).
- **Expert queue grows unbounded.** If the domain expert is OOO, escalated rows sit. Mitigation: 7-day SLA banner at the top of `/admin/m1/expert-queue`; aged items annotate the regulation bank with a warning badge.
- **Override choice taxonomy drift.** If the 12-category taxonomy ever changes, old override choices need migration. Mitigation: per [m1/09_M1_Annotation_Guidelines.md §2](09_M1_Annotation_Guidelines.md), the taxonomy is locked at Week 5 of the project; changes go through a migration script.

## Validation & acceptance criteria

- **A11y.** Drawer is focus-trapped; `Escape` closes; keyboard nav drives every action without mouse.
- **Loading state.** While the queue fetches, show `<AnimatedLoadingSkeleton>` chrome-stripped to the table border. Drawer body uses `<Skeleton>` strips during the per-row fetch.
- **Empty state.** "Queue clear" celebration when 0 items, with a link back to `/admin/regulations`.
- **Race-condition safety.** Concurrent admin actions are eventually consistent — last-writer-wins on the regulation row; full audit log preserves each decision.
- **Sort persistence.** Sort + filter state in the URL so deep-links share specific queries (`?sort=confidence:asc&min_severity=4`).
- **Audit-trail completeness.** Every Confirm / Override / Escalate writes an `audit_log` row referencing the regulation_id + the user_id + the prior + new state.

## Cross-references

- Parent: [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md)
- Screen reference (current workaround): [12_UI_Screens_and_Loading.md §3.1](../frontend/SETUP/12_UI_Screens_and_Loading.md)
- Backend confidence floor + `needs_review`: [02_M1_Data_Requirements.md §2.1](02_M1_Data_Requirements.md)
- Backend triage trigger (the retraining linkage): [12_M1_Monitoring_Maintenance.md §3.3](12_M1_Monitoring_Maintenance.md)
- Backend retraining/rollback: [12_M1_2_Retraining_Deployment_Rollback.md](12_M1_2_Retraining_Deployment_Rollback.md)
- BUILD phase: BUILD_13 §admin tracking dashboards
- Code (when shipped): `frontend/app/(admin)/admin/m1/review-queue/page.tsx`, `frontend/components/forms/review-queue-drawer.tsx`


# 14_M1_3 — Admin Expert Verification

> Companion to [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) — covers tracking surface **A3: Expert-verification ledger (sign-off + coverage tracking)**.
> **Implementation status:** ✅ Shipped — Verify button + `<VerificationBadge>` on every regulation row; bulk-verify action on the list; audit-log writes verified by Session 14.

## Purpose

Production-classified regulations carry the classifier's prediction, not an expert's. The verification workflow is the formal sign-off where a CA / Attorney admin says "yes, this category + sectors are correct" — flipping `expert_verified = true`, recording who verified, and emitting an `audit_log` event. The coverage-tracking widget answers the SLA question from the success metrics ([m1/01_M1_Research_Problem.md §5](01_M1_Research_Problem.md)): ≥ 30 % of production regulations expert-verified.

## Detailed process

This workflow runs across two surfaces — single-row verification on the regulation detail page, and bulk verification on the regulation list.

### Single-row verification

1. **Open the detail page.** `/admin/regulations/[id]/edit` (per [12_UI_Screens §3.2](../frontend/SETUP/12_UI_Screens_and_Loading.md)). The header band shows the `<VerificationBadge>` (red "Unverified" or green "Verified" with name + timestamp).
2. **Review the classification.** Scroll the form — Section 1 (Identity & classification) shows the `change_category` + sectors. Section 4 (Localised content) shows the trilingual title + summary. The right-rail "Preview as SME" pane renders the `<RegulationContextCard>` exactly as the SME will see it.
3. **Override (if needed).** Edit any field; the form is unrestricted for admins. The sticky save bar at the bottom shows a "Save changes" button.
4. **Click "Verify".** The button lives next to the save bar. On click:
   - Backend: `PATCH /api/v1/m1/regulations/{id}/verify { verified_by: "{ca_name}" }`.
   - The badge flips to green; the verifier's name + timestamp render.
   - Audit-log row written: `event_type='regulation.verified'`, `actor=current_user.email`, `old_value`/`new_value` showing `expert_verified false → true`.
5. **Toast confirmation.** A `toast(...)` "Verified by {name}" — dismissible.

### Bulk verification

1. **Open the regulation bank list.** `/admin/regulations`.
2. **Select rows.** Each row has a checkbox; the sticky bulk-action bar at the bottom appears when ≥ 1 row is selected.
3. **Click "Verify selected".** A modal prompts for the verifier's name (defaults to the current user's name; can be overridden if a CA is signing off for a batch they reviewed).
4. **Confirm.** The N rows verify in a single backend call: `POST /api/v1/m1/regulations/bulk-verify { ids: [...], verified_by: "{ca_name}" }`. Toast: "Verified N regulations".
5. **List refreshes.** Each verified row's badge flips green. The list-level "Verified coverage" stat (top-right of the page header) recomputes — e.g. `47 / 134 (35 %) verified`.

### Coverage tracking

The list page renders a small `<Stat>` card or inline counter showing the running coverage percent. Refreshed every time the table re-fetches (every 30 s + after every mutation). When coverage drops below 30 %, the counter renders in `destructive` colour with a tooltip linking to the success-metric definition.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Single button on detail page (chosen) | Simple, discoverable | ✅ Shipped — most natural sign-off surface | Never remove |
| Bulk-verify on list (chosen) | Throughput when a CA reviews 20 rows in one session | ✅ Shipped | If bulk-verify is misused (admin verifying without review), gate behind a "I reviewed each row" checkbox |
| Verifier name override per action | Allows recording the actual CA's name | ✅ Default current user; admin can override | Never remove |
| Coverage stat inline on the list | Always-visible — admin sees it without navigating | ✅ Shipped | Add a dashboard-level rollup if coverage tracking becomes a weekly-review concern |
| Two-step verify (preview + confirm) | Prevents fat-finger | ❌ Single click — admins find double-clicks annoying | If error rate (verify-then-immediately-unverify) exceeds 5 % |
| Unverify action | Allows mistakes to be undone | ✅ Available as `<RowActions>` "Unverify" — same audit trail | Never remove |

## Worked example

A CA-led batch review using the seeded demo regulations:

```
10:00 — CA "K. Perera (FCA)" logs in as admin
         opens /admin/regulations?domain=VAT&needs_review=false&is_verified=false
         filters down to 14 VAT regulations awaiting expert sign-off
10:05 — CA opens VAT_2024_AMD detail page
         reviews classifier output: change_category=TAX_RATE_CHANGE ✓
         reviews sectors: [manufacturing, retail, services, ..., 10 sectors] ✓ (it's a universal VAT change)
         clicks "Verify" → green badge appears with "Verified by K. Perera at 2026-05-14 10:06"
         audit_log row: event_type='regulation.verified', actor='kperera@enigmatrix.lk'
10:15 — CA spot-checks 12 more rows individually; finds all correct
10:25 — CA returns to the list, selects the remaining 12 rows, clicks "Verify selected"
         modal prompts: verifier_name = "K. Perera (FCA)" (defaulted from user record)
         CA confirms → 12 rows verify in one batch call
10:26 — list refreshes; coverage counter goes from 31% → 38%
```

Throughout, [m1/02_M1_Data_Requirements.md §2.1](02_M1_Data_Requirements.md)'s `expert_verified_by` and `expert_verified_at` columns are populated; the audit-log captures every action.

## Failure modes & edge cases

- **CA verifies own override.** The same admin who overrode the classifier in the review queue then verifies. Today this is allowed — the audit log records both actions with timestamps so a reviewer can spot it. If institutional rules require separation, gate via role: `m1.classify` can be set by an `admin` but `m1.verify` can require an additional `expert` role on the user.
- **Verify-then-unverify churn.** If an admin verifies then a colleague unverifies, both events log. Mitigation: the `<VerificationBadge>` shows the *latest* state + verifier; click to expand shows the full history.
- **Coverage stat lags.** The stat is computed client-side from the current paginated view, not the full table. Mitigation: a separate `/api/v1/admin/regulations/coverage` endpoint returns the true total + verified count; the stat polls it every 30 s.
- **Bulk-verify on mixed-category rows.** If the bulk selection includes rows with different `change_category` values, the modal warns "10 rows span 3 categories — verify all anyway?" — admin can proceed or cancel.

## Validation & acceptance criteria

- **A11y.** `<VerificationBadge>` carries an `aria-label` describing both state + verifier ("Verified by K. Perera on May 14, 2026").
- **Idempotency.** Verifying an already-verified row is a no-op (returns 200 but no audit-log row written; the backend service deduplicates).
- **Audit completeness.** Every verify + unverify writes one `audit_log` row. CI test asserts this on every PR that touches the verification path.
- **Concurrent verify safety.** Two admins clicking Verify on the same row at the same moment → one succeeds; the second sees the toast "Already verified by {name}".
- **Verifier name validation.** The verifier-name field rejects empty strings + > 200 chars; renders in the badge truncated with full text in a tooltip.

## Cross-references

- Parent: [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md)
- Screen reference: [12_UI_Screens_and_Loading.md §3.1, §3.2](../frontend/SETUP/12_UI_Screens_and_Loading.md)
- Backend verification columns: [02_M1_Data_Requirements.md §2.1](02_M1_Data_Requirements.md) (`expert_verified`, `expert_verified_by`, `expert_verified_at`)
- Coverage SLA: [01_M1_Research_Problem.md §5](01_M1_Research_Problem.md), [12_M1_Monitoring_Maintenance.md §1](12_M1_Monitoring_Maintenance.md)
- Audit log (Session 14): `backend/app/services/audit_service.py`, `backend/app/models/audit_log.py`
- BUILD phase: BUILD_13 §verification + Session 14 (audit) — both already shipped
- Code (shipped): `frontend/app/(admin)/admin/regulations/page.tsx`, `frontend/app/(admin)/admin/regulations/[id]/edit/page.tsx`, `frontend/components/regulations/verification-badge.tsx`


# 14_M1_4 — Admin Lag Analytics + Propagation Tracker

> Companion to [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) — covers tracking surface **A4: Lag analytics dashboard + propagation tracker**.
> **Implementation status:** 🔲 Deferred — backend ingests `m1_propagation_events` rows on every channel observation and exposes them via `/api/v1/m1/analytics/lag` + `/api/v1/m1/analytics/channel-effectiveness`, but no admin UI consumes them. This companion describes the intended dashboard.

## Purpose

The four lag findings F1–F4 ([m1/08_M1_1_Research_Findings_Extraction.md](08_M1_1_Research_Findings_Extraction.md)) are the platform's empirical research contribution. The admin lag dashboard is the *operational* surface for the same data: per-channel median lag, propagation traces per regulation, drill-down into which regulations are missing channel coverage, and trend lines week-on-week.

The dashboard is the deferred surface that, once shipped, lets the project answer in 30 seconds questions that today require a Jupyter notebook session.

## Detailed process

> 🔲 Intended workflow — design not yet locked.

### Entry point — `/admin/m1/analytics`

The page opens to four cards stacked top-to-bottom, designed to answer the four findings F1–F4 in order:

1. **Card 1 — Median lag by channel (F1 + F2).** A horizontal bar chart with one bar per channel, sorted ascending by median lag. Channel groups: `portal_*` (government portals), `news_*` (RSS news outlets), `alert_delivery` (Enigmatrix alerts as comparison), `government_sms` (when available). Y-axis = channels, X-axis = lag days. Click a bar → drill into the per-regulation lag table for that channel.

2. **Card 2 — SME awareness lag (F3).** Same bar shape but per district (`urban / peri-urban / rural`) with sub-bars per sector. Drill-down → respondent-level (anonymised) lag table.

3. **Card 3 — Channel effectiveness ranking (F4).** A ranked table of channels with columns: rank, channel, p50 lag, p95 lag, sample size, weekly change (▲/▼). The header has a toggle: "this week" vs "this month" vs "all time".

4. **Card 4 — Propagation tracker (per regulation).** A search-pickable per-regulation timeline view. Pick a regulation → see a horizontal timeline with each channel's `first_seen_at` plotted, plus the SME-awareness-survey responses overlaid. The visualisation is what the M1 backend docs call the "T0–T9 diffusion timeline" from [m1/01_M1_Research_Problem.md §8](01_M1_Research_Problem.md).

### Filter controls (top of page)

- Time range: last 7 days / 30 days / quarter / all
- Sector filter (multi-select)
- Category filter (multi-select)
- Verified-only toggle (excludes `expert_verified=false` rows from analytics)

### Drill-downs

Every chart is clickable → opens a slim `<Sheet>` with the underlying data table + a CSV export button. The CSV exports the same data the research notebooks consume.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Dedicated `/admin/m1/analytics` page (chosen target) | Single surface for all 4 findings | 🔲 Target — BUILD_13 | If analytics use becomes a daily power-user workflow, split into per-finding pages |
| Recharts as chart library | Already in the stack (used in `/risk` per [12_UI_Screens §2](../frontend/SETUP/12_UI_Screens_and_Loading.md)) | ✅ Recharts | If we need draggable / zoom-able timelines, evaluate Visx or D3 directly |
| Server-rendered cards with `loading.tsx` streaming | Each card streams independently | ✅ Streaming | If a card becomes interactive (filter that reshapes the chart), client-side |
| CSV export per drill-down | Reproducibility for thesis | ✅ Ship — small effort, large value | Never remove |
| Live (web-socket) updates | Always-fresh dashboard | ❌ Not needed — propagation data refreshes hourly | If admins request sub-minute freshness |
| Per-channel sparkline weeks (mini-trend) | Adds noise at MVP | ❌ Skip MVP; add post-launch if requested | After 3 months of production data |

## Worked example

A research-finding spot-check (intended):

```
Quarterly review — admin opens /admin/m1/analytics
Filter: last quarter, verified-only

Card 1 (median lag by channel) shows:
  alert_delivery       0.3 days     ◄═══════
  government_sms       1.0 days     ◄════════════
  portal_ird           5.2 days     ◄═══════════════════
  portal_epf           7.1 days     ◄═══════════════════════
  news_daily_ft       22.5 days     ◄═══════════════════════════════════
  news_lankadeepa     27.0 days     ◄═══════════════════════════════════════
  news_virakesari     31.8 days     ◄══════════════════════════════════════════
  peer_referral       48.2 days     ◄══════════════════════════════════════════════

Card 4 (propagation tracker) — admin picks VAT_2024_AMD:
  gazette         | 2024-01-01 (T0)
  portal_ird      | 2024-01-09 (+8 days)
  news_daily_ft   | 2024-01-23 (+22)
  news_lankadeepa | 2024-02-03 (+33)
  sme_aware_50pct | 2024-02-18 (+48)
  alert_delivery  | 2024-01-01 (+0 — same-day to subscribed SMEs)

Click portal_ird bar → drill table shows all 27 regulations seen on the IRD portal last quarter
  Sortable by lag DESC → identifies 3 regulations the IRD took > 14 days to post
  CSV export → feeds the F1 thesis chapter
```

The dashboard makes the same numbers the research notebook computes available without a notebook context-switch.

## Failure modes & edge cases

- **Cold start with no data.** Pre-BUILD_07, `m1_propagation_events` is empty. Page renders empty states: "Propagation data starts arriving when BUILD_07 ships the ingestion pipeline".
- **One channel dominates.** If 90 % of observations are `alert_delivery`, the channel-effectiveness ranking is degenerate. Mitigation: minimum sample size 30 per channel before it appears in the table.
- **Time-zone confusion.** All `first_seen_at` timestamps are stored in UTC; rendered in Asia/Colombo by default. Filter date inputs in IST; round to local day boundaries. Documented at the bottom of the page in fine print.
- **Slow query on large windows.** Quarter-range filter on 100k+ events is slow without DB indexes. Mitigation: indexes pre-created per [m1/02_M1_Data_Requirements.md §2.10](02_M1_Data_Requirements.md); query timeout 30 s; pagination on drill-down tables.
- **CSV export of PII-adjacent data.** Per-respondent F3 drill-down. Mitigation: respondent identifiers are hashed in the CSV (`sme_profile_id` → anonymised); sector + district preserved.

## Validation & acceptance criteria

- **A11y.** Every chart has a table-mode toggle (visible table beneath the chart), readable by screen readers; bars have `aria-label` describing channel + value.
- **Loading state.** Each card streams via `loading.tsx`; `<AnimatedLoadingSkeleton>` while data fetches.
- **Empty state.** Per card, per drill-down — never blank canvas.
- **CSV format.** UTF-8, RFC 4180 quoted, columns documented in the page footer.
- **Sample-size disclaimers.** Any chart with N < 30 per slice renders an amber "low-confidence" banner referencing [m1/08_M1_1_Research_Findings_Extraction.md](08_M1_1_Research_Findings_Extraction.md).
- **Filter persistence.** All filters in URL state for shareable deep-links.

## Cross-references

- Parent: [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md)
- Backend findings + statistical tests: [08_M1_1_Research_Findings_Extraction.md](08_M1_1_Research_Findings_Extraction.md)
- Backend lag views: [02_M1_Data_Requirements.md §3.3](02_M1_Data_Requirements.md) (`v_m1_regulation_lag_summary`, `v_m1_channel_effectiveness`)
- Backend monitoring of lag pipeline: [12_M1_Monitoring_Maintenance.md §5](12_M1_Monitoring_Maintenance.md)
- BUILD phase: BUILD_13 §lag dashboard, BUILD_12 §schedulers (the nightly view refresh feeding this UI)
- Code (when shipped): `frontend/app/(admin)/admin/m1/analytics/page.tsx`, `frontend/components/analytics/*`


# 14_M1_5 — SME Regulation Discovery

> Companion to [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) — covers tracking surface **S1: Regulation discovery (sector + region filter)**.
> **Implementation status:** 🟡 Partial — `/regulations` list + dashboard "Pending regulations" widget are shipped; the sector-applicability filter that the SME *would* expect is deferred.

## Purpose

An SME wants to answer: *which of the ~500 active regulations actually apply to my business?* Today the platform makes a partial answer — the dashboard's "Pending regulations" widget surfaces sector-relevant items via the backend filter (server-side join on `m1_regulation_sectors` and the SME's `primary_sector`). The full discovery surface (sticky filter rail, applicability score, "save filter" affordance) is deferred.

This companion documents both halves: the shipped widget + list, and the intended full discovery surface.

## Detailed process

### Today (✅ shipped)

1. **Open the dashboard.** `/dashboard`. The "Regulations awaiting your assessment" widget renders up to 3 `<RegulationCard>` instances (`components/surveys/regulation-card.tsx`) sourced from `GET /api/v1/dashboard/pending-regulations`.
2. **See what applies.** Each card shows: `regulation_short_code`, locale-aware title (with "Showing English" badge if SI/TA translation is missing), domain badge, severity badge, effective date. The card is clickable → routes to `/surveys/regulation/[id]`.
3. **"View all".** A small link → `/surveys?view=regulation` opens the surveys hub with the regulation-tab pre-selected. Shows every pending regulation, paginated.
4. **Browse the full list.** `/regulations` (separate route) shows every active regulation, not just pending. Used as a reference catalogue rather than a triage queue.

### Intended (🟡 partial — what's missing)

> 🔲 Intended workflow — sector-applicability filter design not yet locked.

1. **Sticky filter chip bar** at the top of `/regulations`: chips for `Sector = manufacturing`, `Region = Colombo`, `Status = applicable to me`, `Effective in next 30 days`, `Has my action?` Clicking a chip toggles it; chips reflect in the URL (`?sector=manufacturing&region=colombo&applicable=true`).
2. **Applicability score per row.** Each `<RegulationCard>` shows a small badge: `100 % applicable` (the SME's sector is in `affected_sectors` AND district matches), `50 % applicable` (sector match only), `10 %` (universal regulations that apply to all sectors). Computed client-side from the SME's profile + the regulation's `affected_sectors[]`.
3. **Sort options.** Newest, earliest effective date, severity DESC, "most relevant to me" (applicability × severity).
4. **Save filter.** Power-user feature: save a filter set to the SME's profile so it's pre-applied on next visit.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Dashboard widget (chosen) | One-glance recommendation | ✅ Shipped — top-of-page card on `/dashboard` | Never remove |
| Full `/regulations` list (chosen) | Browseable catalogue | ✅ Shipped — paginated table-cards hybrid | Never remove |
| Sector-applicability filter | Sharply narrows the list | 🟡 Target — backend supports it; UI deferred | Ship in BUILD_07 when sector-filter URL params are wired in the API client |
| Applicability score badge | Helps SMEs prioritise | 🟡 Target | Add when telemetry shows SMEs scroll the list without clicking |
| "Save filter" power-user feature | High value, low priority | ❌ Skip MVP | Add when ≥ 10 active SMEs request it |
| Client-side filtering | Snappy | ✅ Acceptable up to ~500 active regulations | If list grows past 1k rows, push filters server-side |

## Worked example

A retail SME's discovery flow (today):

```
Monday morning — SME opens /dashboard
Widget "Regulations awaiting your assessment" renders 3 cards:
  1. VAT_2024_AMD — VAT (severity 5, effective 2024-01-01)
  2. EPF_2024_RATE — EPF (severity 4, effective 2024-02-01)
  3. SLSI_ADAPTER — Product Standard (severity 3, effective 2026-08-01)

SME clicks card #1 → /surveys/regulation/VAT_2024_AMD-uuid → unified M1→M2→M3 wizard

(Later) SME wants the full list → clicks "View all" → /surveys?view=regulation
  sees the 3 cards above plus 2 more universal regulations
  no per-card "applies to me 100%/50%" badge yet (deferred)

(SME's actual flow ends here — 3-5 cards is enough.)
```

### Intended (🟡):

```
Same SME opens /regulations
Sticky filter bar pre-applies `sector = retail` + `applicable=true` from saved filter
  → list collapses from 47 active regulations to 12 retail-applicable
Each card shows applicability badge — 100 % for retail-specific, 50 % for cross-sector
Sort = "most relevant to me" → severity-weighted top first
Click card → same /surveys/regulation/[id] flow
```

## Failure modes & edge cases

- **SME has no `primary_sector`.** Brand-new SME with empty profile. Mitigation: the dashboard widget hides itself; the user is prompted to complete their profile (currently routes to `/profile`).
- **Cross-sector regulation (universal).** Applies to all 10 sectors — `affected_sectors` is the full list. Renders as "10 % applicable" today; future could be "applies to everyone" with a special badge.
- **Profile updated → cached widget stale.** SME changes sector; widget on dashboard might still show the old recommendations until next fetch. Mitigation: `react-query` invalidation on profile mutate (already in place per Session 13).
- **Empty pending list.** SME has surveyed everything; widget shows "All caught up — view all regulations →".
- **Trilingual list:** locale-aware title with EN fallback ("Showing English" badge when SI/TA missing). Existing pattern from [12_UI_Screens §3.5](../frontend/SETUP/12_UI_Screens_and_Loading.md).

## Validation & acceptance criteria

- **A11y.** Filter chips are keyboard-toggleable; chip state read aloud ("Sector retail, active filter").
- **Loading state.** Widget shows `<RegulationCardSkeleton>` placeholders while the dashboard's `Promise.all` fetches; full list shows `<AnimatedLoadingSkeleton>`.
- **Empty state.** Widget: "All caught up — view all regulations". List: per filter, a specific empty-state message + "Reset filters" button.
- **URL state.** Filters in URL so deep-links + back button work.
- **Translation fallback.** `<RegulationCard>` shows the "Showing English" badge when SI/TA title is empty; never crashes on a missing locale.
- **Sector match correctness.** When applicability badge ships, unit test asserts `100 %` only when SME's sector ∈ `affected_sectors` + district ∈ `affected_districts` (when present).

## Cross-references

- Parent: [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md)
- Screen reference: [12_UI_Screens_and_Loading.md §2 (dashboard widget) + §3.5 (/regulations list)](../frontend/SETUP/12_UI_Screens_and_Loading.md)
- Backend sectors schema: [02_M1_Data_Requirements.md §2.2](02_M1_Data_Requirements.md) (`m1_regulation_sectors` M2M)
- Backend dashboard endpoint: `GET /api/v1/dashboard/pending-regulations`
- BUILD phase: BUILD_07 (full sector filter), BUILD_13 (saved-filter feature)
- Code (shipped): `frontend/app/(app)/dashboard/page.tsx`, `frontend/app/(app)/regulations/page.tsx`, `frontend/components/surveys/regulation-card.tsx`
- Code (when deferred bits ship): `frontend/components/regulations/filter-chip-bar.tsx`, `frontend/components/regulations/applicability-badge.tsx`


# 14_M1_6 — SME Awareness Survey

> Companion to [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) — covers tracking surface **S2: Awareness survey participation (Q1–Q8 across 9 regulations)**.
> **Implementation status:** ✅ Shipped — `/surveys/regulation/[id]` runs the per-regulation flow, `/surveys/awareness` runs the standalone awareness instrument, `/surveys/history` tracks completed sessions.

## Purpose

The awareness survey is the *only* data-collection workflow in M1 today, and the entire RQ3 / RQ4 / F3 / F4 research relies on it. The instrument (Q1–Q8) is defined in [m1/09_M1_Annotation_Guidelines.md §9](09_M1_Annotation_Guidelines.md) and [m1/09_M1_3_SME_Survey_Instrument.md](09_M1_3_SME_Survey_Instrument.md): 7 sector-tailored regulations + 2 universal regulations = 9 question blocks per session, each capturing awareness date, channel, action taken.

This companion documents what the SME experiences end-to-end, the resume-mid-session behaviour, and how the frontend threads `regulation_id` into the session-based survey engine.

## Detailed process

The SME has two paths into the awareness survey:

### Path A — Per-regulation flow (`/surveys/regulation/[id]`)

1. **Trigger.** SME clicks a `<RegulationCard>` on `/dashboard` or `/surveys?view=regulation`.
2. **Wizard opens.** `/surveys/regulation/[id]/page.tsx` renders a header (regulation title + short code + locale-aware summary), then `<SurveyWizard>` (`components/forms/survey-wizard.tsx`) takes over.
3. **One question at a time.** Wizard calls `POST /api/v1/survey-sessions/start { survey_mode: "regulation", regulation_id: ... }` → loops `GET /next-question` → `POST /answer` → `GET /next-question` until `flow_status: "completed"`.
4. **Module accent swap.** The wizard reads `module_number` (1 for M1 awareness, 2 for M2 knowledge, 3 for M3 vulnerability) from each question and swaps its accent class (`module-m1` blue → `module-m2` emerald → `module-m3` amber). The SME sees a colour transition as they cross modules.
5. **Context card.** When a question carries `linked_regulation`, the wizard shows `<RegulationContextCard>` above the question — the SME sees *which regulation* the question is about before answering.
6. **Submit.** Final question → submit → thank-you state with CTAs back to `/dashboard` or `/risk`.

### Path B — Standalone awareness instrument (`/surveys/awareness`)

1. **Open** `/surveys/awareness`. The page renders `<SurveyForm>` (`components/forms/survey-form.tsx`) with all awareness questions concatenated — 12 baseline `is_baseline=true` questions first, then per-regulation awareness questions sorted by `effective_date DESC`.
2. **Auto-grow.** Adding a regulation in admin auto-adds its awareness question to this survey — no code change. The list is fetched via `SurveysApi.questionsForInstrument("awareness", { sector, include_baseline: true })`.
3. **Submit as one batch.** Unlike Path A which streams answers, Path B collects all answers + submits once. Limits: see [13_Unified_Survey_Configuration.md](../frontend/SETUP/13_Unified_Survey_Configuration.md).

### Resume + history

- **Resume.** If the SME closes mid-session, `<SurveyAutosave>` has already persisted a draft to `localStorage`. On next visit, `<SurveyForm>` shows a banner: "Resume your survey from {N of total}?".
- **History.** `/surveys/history` lists every completed and in-progress session (`session_id`, `survey_mode`, `questions_answered/total`, `started_at`, `completed_at`, `status`). Each row has a status pill (`<StatusBadge>`) + "Resume" button for in-progress + "View summary" for completed.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| `<SurveyWizard>` (one question per screen) for per-regulation | Focused; cross-module accent swap teaches the SME where they are | ✅ Shipped — natural for the unified M1→M2→M3 flow | Never replace for per-regulation flow |
| `<SurveyForm>` (full-page form) for standalone awareness | Faster for repeat users who want to sweep through | ✅ Shipped — supports section dividers for baseline + per-regulation groups | If standalone-survey completion rate drops below per-regulation rate, consolidate on wizard |
| Session API (start → next-question loop → complete) | Server-controlled branching | ✅ Used by per-regulation flow | Never replace |
| Batch submit (one POST at end) | Simpler for non-branching flows | ✅ Used by standalone awareness | Switch to streamed answers if branching is added to the instrument |
| `<SurveyAutosave>` to localStorage | Resume works across tabs / page refresh | ✅ Used by both paths | If localStorage limits become an issue, move to IndexedDB |
| Trilingual question content via next-intl | Required by the project's EN/SI/TA scope | ✅ Used everywhere | Never compromise |

## Worked example

A retail SME's first session (using seeded demo regulations):

```
Dashboard → SME clicks VAT_2024_AMD card
Route: /surveys/regulation/VAT_2024_AMD-uuid
Page renders: header "VAT Amendment Act, No. 8 of 2024" + summary

POST /survey-sessions/start { mode: "regulation", regulation_id: "..." }
→ { session_id: "sess_01...", next_question: { code: "awareness.v1.q1", module: 1, prompt: "Were you aware..." } }

Wizard shows Q1 with two options [Yes, No]; module-m1 (blue) accent
SME picks "No"; POST /answer { session_id, answer: "no" }
→ next_question: { code: "awareness.v1.q3", module: 1, prompt: "How did you first hear..." }
   (note: Q2 is skipped because Q1=No — branching rule from m1/09_M1_Annotation_Guidelines)
SME picks "news" → POST /answer
→ next_question: { module: 2, prompt: "What is the new VAT registration threshold?" }
   Wizard fades the m1 blue to m2 emerald; <RegulationContextCard> stays sticky at top

... continues through M2 + M3 questions for VAT_2024_AMD ...

Final answer → POST /answer
→ { flow_status: "completed", next_question: null }
Wizard renders thank-you state; "Back to dashboard" CTA

/surveys/history now shows the session row: 
  session_id, mode=regulation, questions_answered=11, completed_at=NOW, status=completed
```

The full instrument (Q1–Q8) is defined in [m1/09_M1_3_SME_Survey_Instrument.md](09_M1_3_SME_Survey_Instrument.md).

## Failure modes & edge cases

- **Mid-session network failure.** `<SurveyAutosave>` retains progress; on reload the resume banner offers to continue. The session_id is in `localStorage` so the next `GET /next-question` resumes from the correct question.
- **Limit reached.** SME has already submitted `survey_limits.sme_limit` sessions. `POST /start` returns 403; the launcher shows "Daily limit reached".
- **Translation missing.** A question's SI/TA translation is empty. The locale-aware getter falls back to EN; the SME sees a "Showing English" badge inline.
- **Branching rule misconfigured.** A question's `next_question_rules` points at a deleted question. Backend returns 500; wizard catches → shows "There was a problem loading the next question" → emails the admin.
- **Duplicate submission.** SME hits Submit twice. Backend's idempotency (the session lifecycle) prevents the second from creating a duplicate row.

## Validation & acceptance criteria

- **A11y.** Every input has a `<Label>`; radio groups are `<RadioGroup>` keyboard-navigable; required-field violations are read by `<SurveyErrorSummary>`.
- **Loading state.** Wizard shows `<Skeleton>` strips during `GET /next-question`; the form's `<Skeleton>` mirrors the eventual question layout (radio buttons / textarea / date picker).
- **Empty state.** "No questions to answer" — only seen if the per-regulation flow is launched for an unseeded regulation; shows a "We're sorry" with a contact-admin CTA.
- **Resume correctness.** Closing the tab on Q5 and reopening returns to Q5, not Q1 or Q6. Test: pause + resume across 10 separate browser sessions; zero data loss.
- **Trilingual parity.** Every question renders correctly in EN/SI/TA; switching the locale mid-survey doesn't lose answers.

## Cross-references

- Parent: [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md)
- Screen reference: [12_UI_Screens_and_Loading.md §2 (surveys hub / regulation flow / awareness / history)](../frontend/SETUP/12_UI_Screens_and_Loading.md)
- Survey engine internals: [13_Unified_Survey_Configuration.md](../frontend/SETUP/13_Unified_Survey_Configuration.md)
- Backend instrument definition: [09_M1_Annotation_Guidelines.md §9](09_M1_Annotation_Guidelines.md), [09_M1_3_SME_Survey_Instrument.md](09_M1_3_SME_Survey_Instrument.md)
- Backend survey-attempts schema: [09_M1_3_SME_Survey_Instrument.md §5](09_M1_3_SME_Survey_Instrument.md)
- BUILD phase: BUILD_05 (survey wizard), BUILD_07 (server-side flow engine) — both shipped
- Code (shipped): `frontend/app/(app)/surveys/regulation/[id]/page.tsx`, `frontend/app/(app)/surveys/awareness/page.tsx`, `frontend/app/(app)/surveys/history/page.tsx`, `frontend/components/forms/survey-wizard.tsx`, `frontend/components/forms/survey-form.tsx`, `frontend/components/surveys/survey-launcher.tsx`


# 14_M1_7 — SME Compliance & Action-Taken Tracking

> Companion to [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) — covers tracking surface **S3: Compliance / action-taken status per regulation**.
> **Implementation status:** 🟡 Partial — action-taken status (`yes_complied / in_progress / no_not_aware / no_not_applicable`) is captured per regulation by the awareness survey's Q7; survey-history surfaces it; no dedicated "My Regulations" tracker page yet.

## Purpose

After the SME has answered the awareness survey for a regulation, the platform knows their action status. The SME wants a single screen that says: *for each regulation, what did I last say I'm doing, and when?* — a personal compliance ledger.

Today that data lives in `m1_sme_awareness_responses.action_taken` ([m1/02_M1_Data_Requirements.md §2.4](02_M1_Data_Requirements.md)) and can be inferred from `/surveys/history`, but there's no purpose-built tracker. This companion describes both the shipped Q7 capture flow and the intended tracker page.

## Detailed process

### Today (✅ partial)

1. **Capture.** During a per-regulation flow ([14_M1_6](14_M1_6_SME_Awareness_Survey.md)), Q7 asks "Did your business take the required action?" with four options: `yes_complied`, `yes_in_progress`, `no_not_aware_of_deadline`, `no_not_applicable`. The answer writes one row to `m1_sme_awareness_responses` keyed by `(sme_profile_id, regulation_id)`.
2. **Recall via history.** `/surveys/history` shows every session; clicking a completed session opens a summary panel listing each question + answer. The SME can scroll for the Q7 answer per regulation.
3. **Recall via dashboard.** The "Pending regulations" widget excludes regulations where the SME has already completed the awareness survey. So a fully-pending list = "regulations I haven't dealt with yet" — implicit compliance state.

### Intended (🟡 — `/portal/m1/my-regulations`)

> 🔲 Intended workflow — design not yet locked.

1. **Open `/portal/m1/my-regulations`** (intended route, may live at `/regulations/mine` depending on routing convention).
2. **Each row** is a regulation × the SME's action status:
   - regulation short code + locale-aware title
   - `<ActionStatusPill>` showing `yes_complied` (green) / `yes_in_progress` (amber) / `no_not_aware` (red) / `no_not_applicable` (grey)
   - last-updated timestamp ("answered 3 weeks ago")
   - severity + effective date
   - upcoming deadline indicator (when applicable — see [14_M1_8](14_M1_8_SME_Deadline_Alert_History.md))
3. **Update the status.** Click a row → opens a slim drawer (similar to [14_M1_2](14_M1_2_Admin_Review_Queue_Triage.md)'s drawer pattern) → SME picks a new status → `PATCH /api/v1/m1/sme/compliance/{regulation_id} { action_taken: "yes_complied" }`. The drawer surfaces the regulation summary + the original Q7 answer for comparison.
4. **Filter by status.** Chips at the top: "Show all", "Still pending", "In progress", "Completed".
5. **Sort by severity, effective date, or "needs attention".** The "needs attention" sort surfaces regulations where the status is stale (> 30 days since last update) AND the deadline is approaching.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Q7 captures status inside the survey (shipped) | Reuses the survey engine; no separate UI to maintain | ✅ Shipped — works as an MVP | Insufficient when SMEs want to *update* status without re-doing the survey |
| Dedicated `/portal/m1/my-regulations` tracker (target) | Single-purpose surface for compliance management | 🟡 Target — BUILD_13 or earlier if SMEs request | Ship when ≥ 5 SMEs have completed > 3 surveys (real signal of need) |
| Inline status edit on `/regulations` cards | Cheap to add | ❌ Mixes browsing (find a regulation) with managing (update my status) — bad UX | Never |
| Per-status counts on the dashboard ("3 in progress, 1 needs action") | Tiny stat that motivates return visits | 🟡 Easy add when the tracker page ships | Ship together |
| Reminders / scheduled checks | Push behaviour | ❌ Out of scope — handled by alerts ([14_M1_8](14_M1_8_SME_Deadline_Alert_History.md)) |  |

## Worked example

A retail SME's compliance audit (mix of today + intended):

```
Today:
SME opens /surveys/history
  Session row: regulation=VAT_2024_AMD, completed 3 weeks ago, status=completed
  Click → summary panel: 11 questions answered
  Scroll to Q7: "Did your business take the required action?" → answered "yes_in_progress"
  SME thinks: "I should have completed that by now"
  → No way to update without re-doing the survey
  → SME re-takes /surveys/regulation/VAT_2024_AMD → answers Q7 = "yes_complied"
  → A new m1_sme_awareness_responses row written; the old row is preserved (insert-only)
  → /surveys/history now has 2 session rows for this regulation

Intended (🟡):
SME opens /portal/m1/my-regulations
  3 cards visible:
    VAT_2024_AMD     yes_in_progress  updated 3 weeks ago  ⚠ effective 2024-01-01
    EPF_2024_RATE    yes_complied     updated 2 weeks ago  ✓ done
    SLSI_ADAPTER     no_not_aware     updated 1 month ago  ⚠ effective 2026-08-01
  SME clicks VAT_2024_AMD row → drawer opens
  Sees Q7 answer "yes_in_progress" + the regulation's required action checklist
  Updates status to "yes_complied" → save → drawer closes; card flips to green
  No re-survey needed; single PATCH call writes the update
```

The intended flow takes ~30 s vs the workaround's ~5 min.

## Failure modes & edge cases

- **Conflicting updates.** SME updates status, then re-takes the awareness survey. The newer survey answer wins. The tracker page reads from the latest non-superseded `m1_sme_awareness_responses` row.
- **Status drift.** SME marks `yes_complied`, but the regulation is later amended (e.g. VAT_2024_AMD → VAT_2025_AMD2). The tracker doesn't auto-reset; the SME has to manually re-engage when prompted by a new alert.
- **Stale "in progress" rows.** Rows untouched for > 90 days flash a warning on the tracker — "this update is stale; please confirm". A click on the warning opens the status drawer.
- **No SME profile.** SME hasn't completed `sme_profiles`. The tracker is empty + prompts profile completion.
- **Migration of old responses.** When the tracker ships, the page reads from existing `m1_sme_awareness_responses` rows. SMEs immediately see their historical Q7 answers without re-doing the survey.

## Validation & acceptance criteria

- **A11y.** Status pills use both colour and label (not colour alone); `aria-label` describes status + last-updated.
- **Loading state.** `<RegulationCardSkeleton>` placeholders while the list fetches.
- **Empty state.** "You haven't taken any regulation surveys yet" + CTA to `/surveys`.
- **Status update is idempotent.** Submitting the same status twice → no-op; backend returns 200.
- **Optimistic UI.** Status drawer flips the card colour immediately; rolls back if the PATCH fails.
- **Timezone display.** "Updated 3 weeks ago" uses relative time in the SME's locale; tooltip shows absolute timestamp in Asia/Colombo.

## Cross-references

- Parent: [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md)
- Screen reference (today's path): [12_UI_Screens_and_Loading.md §2 (/surveys/history)](../frontend/SETUP/12_UI_Screens_and_Loading.md)
- Survey companion: [14_M1_6_SME_Awareness_Survey.md](14_M1_6_SME_Awareness_Survey.md)
- Backend response schema: [02_M1_Data_Requirements.md §2.4](02_M1_Data_Requirements.md) (`m1_sme_awareness_responses`)
- BUILD phase: BUILD_13 §SME tracker page
- Code (shipped — Q7 capture): `frontend/components/forms/survey-wizard.tsx`, the awareness survey questions
- Code (when shipped — tracker): `frontend/app/(app)/portal/m1/my-regulations/page.tsx`, `frontend/components/regulations/action-status-pill.tsx`, `frontend/components/regulations/status-drawer.tsx`


# 14_M1_8 — SME Deadline + Alert Delivery History

> Companion to [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) — covers tracking surface **S4: Deadline countdown + alert delivery history**.
> **Implementation status:** 🔲 Deferred — backend writes one `m1_propagation_events` row per alert with `channel='alert_delivery'`; no SME-facing UI exists. This companion describes the intended page.

## Purpose

After the alert pipeline (Stage F, [m1/02_M1_Data_Requirements.md §3.5](02_M1_Data_Requirements.md)) sends an SME their first regulation alert, the SME needs:
1. **Deadline countdown** — "I have 12 days left to comply with this regulation"; visible at a glance, persistent across sessions.
2. **Alert history** — "did the system actually send me an alert for this last month?" — auditable record of email + SMS + in-portal alerts.

Today the SME receives alerts but has no UI to confirm receipt, see upcoming deadlines, or browse historical alerts. This is the highest-friction deferred SME surface.

## Detailed process

> 🔲 Intended workflow — design not yet locked.

### Entry point — `/portal/m1/deadlines` (intended)

1. **Open the page.** Two cards stacked top-to-bottom:
   - **Card 1 — Upcoming deadlines:** sorted by `effective_date` ASC. Each row: regulation short code + locale-aware title + `<DeadlineCountdown>` ("12 days left" / "5 hours left" / "passed 3 days ago"). Click → opens [14_M1_7](14_M1_7_SME_Compliance_Action_Tracking.md)'s status drawer.
   - **Card 2 — Alert history table:** paginated; columns = regulation, channel (email / SMS / portal), sent_at, status (`delivered` / `opened` / `failed`).
2. **Filter deadlines.** Chips: "Next 7 days" / "Next 30 days" / "Past due" (rare — only if the SME ignored alerts).
3. **Resend / unsubscribe.** Per-row actions in the alert history:
   - **Resend** (admin-only operation, but the SME can request it) → POSTs a re-delivery request to the backend; admin sees the request in a `/admin/m1/resend-queue` (not in scope of this companion).
   - **Mute this regulation** → flags the SME's profile so future alerts for this regulation aren't sent (rare; usually for already-completed regulations).
4. **Drill into a single alert.** Click a row → opens a drawer showing the alert content as it was sent (`subject`, `body_preview`, `language_sent`, links to the regulation detail).

### Deadline countdown widget on dashboard

A condensed version of Card 1 appears on `/dashboard` — a single banner: "1 deadline in 12 days · 2 deadlines this month" — clickable, routes to `/portal/m1/deadlines`.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Dedicated `/portal/m1/deadlines` page (target) | Single-purpose surface for deadline + alert history | 🔲 Target — BUILD_13 | If alert volume per SME stays below ~5/month, a section on the dashboard might suffice |
| `<DeadlineCountdown>` component (target) | Reusable across dashboard banner + tracker page | 🔲 Target | Ship with the page |
| Real-time countdown vs polling | Countdown re-renders every minute via `setInterval` (cheap) | ✅ `setInterval` per minute | If sub-minute precision needed, switch to a `requestAnimationFrame` updater |
| Alert history paginated server-side | Standard for unbounded history | ✅ `?page=&size=` URL state | Never client-side fetch for unbounded data |
| Resend / unsubscribe per-row | Power features without cluttering MVP | 🟡 Add post-MVP; observe whether SMEs ask for them | Survey users after 3 months in production |
| Deadline filter chips | URL state shareable | ✅ Same pattern as [14_M1_5](14_M1_5_SME_Regulation_Discovery.md) | Never |

## Worked example

A typical retail SME's deadline check (intended):

```
SME opens /portal/m1/deadlines

Card 1 — Upcoming deadlines:
  SLSI_ADAPTER     effective Aug 1, 2026   12 days left   severity 3   action: no_not_aware
  VAT_2024_AMD     effective Jan 1, 2024   passed 4 months ago         severity 5   action: yes_complied

SME clicks SLSI_ADAPTER row → status drawer opens (from [14_M1_7])
SME sees the regulation's required action checklist; updates status to "yes_in_progress"

Card 2 — Alert history (paginated, last 50):
  date         regulation       channel  status     language
  2026-04-15   SLSI_ADAPTER     email    delivered  en
  2026-04-15   SLSI_ADAPTER     sms      delivered  en
  2026-04-22   SLSI_ADAPTER     portal   opened     en
  2024-01-01   VAT_2024_AMD     email    delivered  en
  ...

SME clicks the SMS row → drawer shows: "From: Enigmatrix. Re: SLSI safety cert mandate. New rule effective Aug 1, 2026. View: enigmatrix.lk/r/SLSI_ADAPTER"
SME notes the SMS arrived 0 days after gazette publication → confirms the system worked
```

## Failure modes & edge cases

- **No alerts yet** (brand-new SME): page renders empty state "No alerts yet. Subscribe to alerts in your profile."
- **Alerts but no deadlines** (SME has only completed regulations): Card 1 hidden; Card 2 shown.
- **Past-due regulation.** Countdown renders in red `destructive` with "passed N days ago"; an action drawer prompts the SME to update status to `yes_complied` retrospectively or `no_not_aware_of_deadline` honestly.
- **Channel failure** (`status=failed`). E.g. SendGrid bounced the email. The row renders in amber with a tooltip "Delivery failed. Try resending or update your contact email."
- **Alert language mismatch.** SME's profile says SI; alert was sent in EN (translation missing at send time). Row tags `language_sent=en` with a note "your preferred language was Sinhala — translation not available at send time".

## Validation & acceptance criteria

- **A11y.** Countdown component has `aria-live="polite"` so screen readers announce remaining time on update.
- **Loading state.** Cards stream independently via `loading.tsx`; `<AnimatedLoadingSkeleton>` while data fetches.
- **Empty state.** Distinct for "no alerts" vs "no deadlines" vs "no SME profile yet".
- **Past-due handling.** Countdown text + colour communicate "overdue"; never crashes on negative duration.
- **Pagination state.** Page + filter in URL.
- **Channel-status truthfulness.** Status column shows the *backend-recorded* delivery state — no optimistic "delivered" without confirmation from the provider.

## Cross-references

- Parent: [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md)
- Backend alert dispatch (Stage F): [02_M1_Data_Requirements.md §3.5](02_M1_Data_Requirements.md)
- Backend alert-batching contract: [08_M1_Full_System_Architecture.md §8.1](08_M1_Full_System_Architecture.md)
- Backend propagation event schema: [02_M1_Data_Requirements.md §2.3](02_M1_Data_Requirements.md) (`m1_propagation_events`)
- Sibling tracker: [14_M1_7_SME_Compliance_Action_Tracking.md](14_M1_7_SME_Compliance_Action_Tracking.md)
- BUILD phase: BUILD_07 (alert dispatch backend), BUILD_13 (this UI)
- Code (when shipped): `frontend/app/(app)/portal/m1/deadlines/page.tsx`, `frontend/components/regulations/deadline-countdown.tsx`, `frontend/components/regulations/alert-history-table.tsx`


# 14_M1_9 — Category × Sector Workflows (cross-cutting reference)

> Companion to [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) — covers the cross-cutting reference **X9: how the 12 categories + 10 sectors flow through every M1 surface**.
> **Implementation status:** Reference doc — describes existing conventions across the 8 tracking surfaces (A1–A4, S1–S4). The 12 categories + 10 sectors are shipped in the schema + admin form; the badge colour conventions documented here are shipped via `components/ui/`.

## Purpose

The M1 taxonomy has 12 mutually-exclusive **categories** (single-label) + 10 **sectors** (multi-label), defined in [m1/09_M1_Annotation_Guidelines.md §2 + §3](09_M1_Annotation_Guidelines.md). Each appears on dozens of frontend surfaces — admin filters, badges on cards, columns in tables, chips in URL state, accent colours on per-module shells. Without a single reference, naming + colour drifts across surfaces ("Manufacturing" vs "manufacturing" vs "Mfg"; tax-blue vs slate). This doc is the lookup table — what each value is, where it appears, what colour + label it carries.

## Detailed process

### Category convention table

| Code | Label (EN) | Badge variant | Where it appears |
|---|---|---|---|
| `TAX_RATE_CHANGE` | Tax rate change | `<DomainBadge variant="domain-tax">` (slate) | Admin list filter, regulation card, survey context card |
| `LABOUR_LAW` | Labour law | `<DomainBadge variant="domain-labour">` | same |
| `EPF_ETF_CHANGE` | EPF / ETF change | `<DomainBadge variant="domain-epf">` | same |
| `PRODUCT_STANDARD` | Product standard | `<DomainBadge variant="domain-product">` | same |
| `BUSINESS_REGISTRATION` | Business registration | `<DomainBadge variant="domain-business">` | same |
| `IMPORT_EXPORT` | Import / export | `<DomainBadge variant="domain-trade">` | same |
| `SECTOR_SPECIFIC` | Sector-specific (CAA MRP / Food Act / NMRA) | `<DomainBadge variant="domain-sector">` | same |
| `PENALTY_ENFORCEMENT` | Penalty enforcement | `<DomainBadge variant="domain-penalty">` | same |

Labels render in EN by default; SI/TA via next-intl message keys `m1.category.{code}`. Trilingual parity is a CI-tested invariant.

### Sector convention table

| Code | Label (EN) | Badge | Affects (sample) |
|---|---|---|---|
| `grocery_retail` | Grocery / Food Retail | `<SectorBadge>` (uniform colour; sector identity isn't colour-coded, only label) | VAT, CAA MRP, Food Act, SCL |
| `food_service` | Food Service | same | VAT, Food Act hygiene, Labour, Excise licences |
| `general_retail` | General-Goods Retail | same | VAT, Customs/CESS, SLSI standards, MRP |

> Categories use **colour** as a primary identity cue (12 distinct hues); sectors use **label only** (10 uniform-coloured chips). The asymmetry is intentional — categories are more numerous than colours-distinguishable, but the design constraint is that an admin filter rail can hold 12 coloured filter chips without becoming a rainbow soup.

### Where these values appear across the 8 surfaces

| Surface | Category usage | Sector usage |
|---|---|---|
| A1 (Pipeline-state) | Filter column on `/admin/regulations` | Filter column on `/admin/regulations` |
| A2 (Review queue) | Category dropdown in the override drawer | Sector multi-select in the override drawer |
| A3 (Verification) | Read-only badge on the detail page | Read-only chip list on the detail page |
| A4 (Lag analytics) | Cross-tab dimension (lag-by-category) | Cross-tab dimension (lag-by-sector) |
| S1 (Discovery) | Filter chip on `/regulations` | Filter chip + applicability badge |
| S2 (Survey) | Survey is partitioned per-regulation (categories are read-only on the context card) | Sector-tailored regulation selection (7 sector regulations + 2 universal) |
| S3 (Compliance tracker) | Status pill on the row + category badge | Sector chips on the row |
| S4 (Deadlines + alerts) | Category badge in the alert-history table | n/a (alerts already filtered to SME's sector at send time) |

The cross-cutting concern: **the same enum value must render identically on every surface**. The `<DomainBadge>` component is the single source of truth — every surface imports it; nobody hand-rolls a coloured pill.

### URL-state convention

When categories or sectors land in URL state, they use lowercase enum codes (NOT labels), comma-separated:

```
/admin/regulations?change_category=TAX_RATE_CHANGE,EPF_ETF_CHANGE
/regulations?sector=manufacturing,retail
```

Multi-value: comma. Negation: leading `!` (e.g. `change_category=!PENALTY_ENFORCEMENT`). Date-range and other filters follow the same lowercase + comma + `!` convention.

### Sort orderings

Default sort across surfaces uses `(severity_level DESC, effective_date ASC)` — most-severe-soonest-first. Categories + sectors are alphabetised in their filter dropdowns by code (not label, so the order is stable across locales).

### Accessibility considerations

- Every badge has both colour AND a label — colour is never the sole carrier of information.
- Badge variants use the WCAG AA contrast ratio (4.5:1) on both light + dark themes — verified by the project's existing axe-core CI.
- Trilingual labels are mandatory; CI fails any PR that adds a new category/sector without `m1.{category|sector}.{code}` translations in `messages/{en,si,ta}.json`.

## Technology choices

This is a reference doc; the conventions are shipped, not designed-from-scratch. The choices captured:

| Convention | Locked at | Why |
|---|---|---|
| 12 categories single-label | [m1/09_M1_Annotation_Guidelines.md §2](09_M1_Annotation_Guidelines.md) | Mutually exclusive in the data model — UI mirrors |
| 10 sectors multi-label | Same | Multi-label in the data model — UI mirrors |
| `<DomainBadge>` per-category colour | `frontend/components/ui/domain-badge.tsx` | One component owns the colour map |
| Sector chips uniform colour | `frontend/components/ui/sector-badge.tsx` | Avoids the "rainbow soup" problem |
| Lowercase enum + comma URL state | Existing pattern across `/admin/regulations`, `/admin/questions` | Consistency across admin surfaces |
| Trilingual labels via next-intl | Project-wide convention | EN/SI/TA is the project's scope |

## Worked example

An admin filter on `/admin/regulations`:

```
URL: /admin/regulations?change_category=TAX_RATE_CHANGE,EPF_ETF_CHANGE&sector=manufacturing&page=1

Filter rail (left):
  Category
    [✓] Tax rate change         (slate badge)
    [ ] Labour law
    [✓] EPF / ETF change        (purple badge)
    [ ] Product standard
    ... 8 more
  Sector
    [✓] Manufacturing
    [ ] Retail
    [ ] Services
    ... 7 more

Result table renders 18 rows.
Each row's category column shows the same coloured <DomainBadge> as the filter rail.
Sector column shows multi-chip stack — sectors alphabetised.
```

The SME-side mirror (intended):

```
URL: /regulations?sector=retail&applicable=true

Filter chip bar (top):
  [Sector: Retail ×]  [Applicable to me ×]

Result: 12 cards, each showing:
  <DomainBadge variant="domain-tax">   for a VAT regulation
  <SectorBadge>retail</SectorBadge>   <SectorBadge>services</SectorBadge>
  <ApplicabilityBadge level="100%">applicable</ApplicabilityBadge>
```

## Failure modes & edge cases

- **New category added.** Adding a 13th category requires: schema migration (per [m1/09_M1_Annotation_Guidelines.md §2](09_M1_Annotation_Guidelines.md)) + new `<DomainBadge>` variant (new CSS class + colour) + trilingual labels in `messages/*.json` + CI translation test pass. The convention freezes new categories until the next quarterly review — taxonomy drift is documented as a risk in [m1/01_M1_Research_Problem.md §10](01_M1_Research_Problem.md).
- **Renamed enum.** Renaming an existing enum (e.g. `EPF_ETF_CHANGE` → `EPF_CONTRIBUTION_CHANGE`) breaks every URL ever shared. Mitigation: never rename; deprecate + add new.
- **Locale-missing label.** A new category landed without SI/TA. CI fails the PR — translation must land with the enum.
- **Colour-blind users.** Categories rely on colour; mitigated by always-present labels. Plus the `<DomainBadge>` uses distinguishable hue + saturation pairs.
- **URL state parsing errors.** Unknown enum value in URL (e.g. someone hand-typed `?sector=manufaturing`). Mitigation: filter falls back to "no filter" + toast warns "Unknown filter value; showing all".

## Validation & acceptance criteria

- **Single source of truth for badges.** No surface re-implements category/sector rendering. CI grep: `class.*tax|class.*epf` outside `domain-badge.tsx` → fail.
- **Trilingual parity.** Every category/sector code has en + si + ta translations. CI test: `Object.keys(messages.en.m1.category) === Object.keys(messages.si.m1.category) === Object.keys(messages.ta.m1.category)`.
- **WCAG AA contrast.** All badge variants pass axe-core's contrast check on both themes.
- **URL state round-trip.** A shared URL with filters renders the same view in any session.
- **Sort stability.** Sorting by category renders the same order regardless of locale (sort by code, not label).

## Cross-references

- Parent: [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md)
- Backend taxonomy: [09_M1_Annotation_Guidelines.md §2 + §3](09_M1_Annotation_Guidelines.md)
- Worked examples per category: [09_M1_1_Category_Taxonomy_Examples.md](09_M1_1_Category_Taxonomy_Examples.md)
- Frontend component primitives: [12_UI_Screens_and_Loading.md §4](../frontend/SETUP/12_UI_Screens_and_Loading.md)
- Code: `frontend/components/ui/domain-badge.tsx`, `frontend/components/ui/sector-badge.tsx`, `frontend/components/ui/severity-badge.tsx`, `frontend/components/ui/module-badge.tsx`
- Translation keys: `frontend/messages/{en,si,ta}.json` under `m1.category.*` + `m1.sector.*`
