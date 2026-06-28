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
