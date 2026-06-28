# 14 — M1 Tracking Workflows

> **What this is.** A workflow index for Module 1 — how an admin and an SME *track* regulatory information through every M1 surface in the UI. Eight tracking surfaces (4 admin × 4 SME) plus a cross-cutting category × sector reference. Complements [12_UI_Screens_and_Loading.md](../frontend/SETUP/12_UI_Screens_and_Loading.md), which maps the *screens*; this doc maps the *verbs*.
> **Implementation status:** 🟡 Partial — 3 of 8 surfaces shipped, 2 partial, 3 deferred. Each sub-step companion carries its own status badge.
> **See also (backend):** [README.md](README.md) — the 43-file M1 backend + research doc set.

---

## Why this doc exists

The M1 backend docs (`enigmatrix-docs/m1/`) describe a regulation's life as a state machine: a gazette is ingested → text extracted → classified → summarised → alerted → archived. The frontend docs (12_UI_Screens) map the screens that exist today. Neither answers the question a new contributor most often asks: **"As an admin, what do I do when a low-confidence classification lands? As an SME, what do I do when an alert arrives?"** This doc is that workflow guide — one section per tracking surface, each pointing at the screen (12_UI_Screens), the procedure (this doc + its companions), the backend reference (`m1/`), and the BUILD phase.

---

## The 8+1 tracking surfaces at a glance

| # | Surface | Audience | Status | Detail in |
|---|---|---|---|---|
| A1 | Pipeline-state tracking (Stage A→F status machine) | Admin | 🟡 Partial | [14_M1_1_Admin_Pipeline_State_Tracking.md](14_M1_1_Admin_Pipeline_State_Tracking.md) |
| A2 | Needs-review queue triage | Admin | 🔲 Deferred | [14_M1_2_Admin_Review_Queue_Triage.md](14_M1_2_Admin_Review_Queue_Triage.md) |
| A3 | Expert-verification ledger | Admin | ✅ Shipped | [14_M1_3_Admin_Expert_Verification.md](14_M1_3_Admin_Expert_Verification.md) |
| A4 | Lag analytics + propagation tracker | Admin | 🔲 Deferred | [14_M1_4_Admin_Lag_Analytics.md](14_M1_4_Admin_Lag_Analytics.md) |
| S1 | Regulation discovery (sector + region filter) | SME | 🟡 Partial | [14_M1_5_SME_Regulation_Discovery.md](14_M1_5_SME_Regulation_Discovery.md) |
| S2 | Awareness survey participation (Q1–Q8) | SME | ✅ Shipped | [14_M1_6_SME_Awareness_Survey.md](14_M1_6_SME_Awareness_Survey.md) |
| S3 | Compliance / action-taken status per regulation | SME | 🟡 Partial | [14_M1_7_SME_Compliance_Action_Tracking.md](14_M1_7_SME_Compliance_Action_Tracking.md) |
| S4 | Deadline + alert delivery history | SME | 🔲 Deferred | [14_M1_8_SME_Deadline_Alert_History.md](14_M1_8_SME_Deadline_Alert_History.md) |
| X9 | Category × Sector workflows (cross-cutting reference) | Both | Reference | [14_M1_9_Category_Sector_Workflows.md](14_M1_9_Category_Sector_Workflows.md) |

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
