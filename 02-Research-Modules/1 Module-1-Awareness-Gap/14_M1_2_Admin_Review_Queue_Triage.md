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
         Item is VAT-amendment look-alike; classifier said "FINANCIAL_REGULATION"
09:16 — admin clicks the row → drawer opens
         classification_chunk shows: "VAT registration threshold raised from LKR 60M to LKR 80M..."
         Top-3: TAX_RATE_CHANGE 0.32 | FINANCIAL_REGULATION 0.42 | BUSINESS_REGISTRATION 0.18
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
