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
