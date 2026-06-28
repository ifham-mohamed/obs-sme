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
