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
