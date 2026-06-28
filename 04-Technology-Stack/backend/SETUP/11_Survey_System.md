# 11 — Survey System & Cross-Module Linkage

> **Goal:** explain how the three SME-facing surveys (M1 Awareness, M2 Knowledge, M3 Vulnerability) work as one system — how questions are stored, scored, linked across modules, and surfaced in the admin dashboard.
>
> **Reference:** [`docs/research/module_2_and_3_data_architecture.md`](../research/module_2_and_3_data_architecture.md), [`docs/research/module_1_and_4_data_architecture.md`](../research/module_1_and_4_data_architecture.md) §A5.2, [`docs/BUILD_PLAN/BUILD_08_Module2_Knowledge.md`](../BUILD_PLAN/BUILD_08_Module2_Knowledge.md), [`docs/BUILD_PLAN/BUILD_09_Module3_Risk.md`](../BUILD_PLAN/BUILD_09_Module3_Risk.md).

---

## 1. Three surveys, one storage spine

| Module | Instrument | Question source | Scoring | Storage |
|--------|-----------|-----------------|---------|---------|
| 1 (M1 awareness) | `awareness` | DB-driven `survey_questions` (`module_number=1`), seeded from [`seed_awareness_questions.py`](../../backend/app/scripts/seed_awareness_questions.py) — the 12 baseline `awareness.v1.qNN` + regulation-scoped extras (e.g. `q13`) | None (profile data) | `survey_responses` rows with `module_number = 1` |
| 2 (Knowledge) | `knowledge` | DB-driven `survey_questions` (`module_number=2`), seeded from [`seed_m23_questions.py`](../../backend/app/scripts/seed_m23_questions.py) | Auto-scored on submit against `correct_answer_json` | `survey_responses` rows with `module_number = 2`, `is_correct`, `score_points`, `domain_code`; cached aggregate in `m2_knowledge_scores` |
| 3 (Vulnerability) | `vulnerability` | DB-driven `survey_questions` (`module_number=3`), seeded from [`seed_vulnerability_questions.py`](../../backend/app/scripts/seed_vulnerability_questions.py) | None (behavioural / profile data) | `survey_responses` rows with `module_number = 3`, **and** a projection into `m3_compliance_history` / `m3_behavioural_signals` (see §10.4) |
| 4 (Misinformation) | `misinformation` | **Not seeded.** `module_number=4` is reserved in the schema; no `survey_questions` rows exist. `per_module_m4` session mode is defined in the API enum and `survey_sessions.survey_mode` CHECK constraint. | N/A | N/A — no data captured. `/verify` page is a ComingSoon placeholder; `/api/v1/verify/claim` returns 501. BUILD_10 pending. |

> **Naming.** "M1" in this repo means the SME awareness survey, `module_number = 1`, `instrument_section = "awareness"`, the 12 `awareness.v1.q01..q12` baselines (plus regulation-scoped extras). The separate "M1 Regulations" pipeline ([BUILD_07](../BUILD_PLAN/BUILD_07_Module1_Awareness.md)) populates `m1_regulations` via gazette ingest — that is **not** survey-driven. They share the "M1" label because awareness is *about* regulatory changes. The hardcoded `frontend/lib/surveys/{awareness,m3-vulnerability}.ts` banks are dead since Session 12 — questions live in the DB now.

The single spine is `survey_responses` (long-form, append-only). Every row carries `module_number`, `domain_code`, `sector_code`, `question_version`, `is_correct`, `score_points`, `linked_regulation_id` (the regulation the answer was about — see §10.10), and a `meta` JSONB (which now also carries the `from_question_code`/`from_rule` flow breadcrumb — §10.10). Question ids are **versioned**: `awareness.v1.q07`, `knowledge.v1.VAT_FACT_001`, `vulnerability.v1.M3_HIST_001`. When a question's `correct_answer_json` changes the `version` bumps; old answers stay queryable.

> **Session 6 update.** The three direct-entry URLs (`/surveys/awareness`, `/surveys/knowledge`, `/surveys/vulnerability`) still work for testing and admin-driven flows, but the **canonical SME entry point is now the unified wizard at `/surveys`** — one walk that crosses all three modules based on actual answers, server-side. The hardcoded TS banks have been replaced by DB rows in the unified `survey_questions` table (modules 1/2/3 in one schema; see [`06_Database_and_Migrations.md`](06_Database_and_Migrations.md) §3 for the column list). See [§10](#10-unified-survey-wizard) below for the loop and the rule shape.

## 2. Conditional questions — the "if yes → do you know?" pattern

The user's brief describes a flow like *"are you aware of the new VAT regulation? if yes — do you know the steps? if yes — do you know the penalties?"* Implemented as `dependsOn` on the question schema:

```ts
// frontend/lib/surveys/types.ts
export type ConditionalRule = {
  questionId: string;
  equals: string | number | boolean | string[];
};
```

Used in [`m3-vulnerability.ts`](../../frontend/lib/surveys/m3-vulnerability.ts):

```ts
{
  id: "vulnerability.v1.M3_HIST_001",
  type: "single",
  label: "In the last 24 months, has your business missed ANY tax filing deadline?",
  options: [{ value: "yes", ... }, { value: "no", ... }, ...],
  required: true,
},
{
  id: "vulnerability.v1.M3_HIST_002",
  type: "single",
  label: "If yes, approximately how many times?",
  options: [...],
  // Only renders when M3_HIST_001 = "yes"
  dependsOn: { questionId: "vulnerability.v1.M3_HIST_001", equals: "yes" },
},
{
  id: "vulnerability.v1.M3_HIST_003",
  type: "multi",
  label: "Which deadlines have you missed?",
  options: [...],
  dependsOn: { questionId: "vulnerability.v1.M3_HIST_001", equals: "yes" },
},
```

[`QuestionRenderer`](../../frontend/components/forms/question-renderer.tsx) uses `useWatch()` to re-evaluate on every change of any watched id; [`SurveyForm.valuesToAnswers()`](../../frontend/components/forms/survey-form.tsx) strips skipped values before submit, so the backend never sees orphan rows.

The same pattern is what [`module_1_and_4_data_architecture.md`](../research/module_1_and_4_data_architecture.md) §A5.2 calls the per-regulation Q1–Q8 block: Q2 (when did you find out?) only shows if Q1 (were you aware?) is "Yes"; Q5–Q7 are conditional on Q1 too. When BUILD_07 ships gazette ingest, that flow drops in by adding more `dependsOn`-rich question banks — the renderer doesn't change.

## 3. Cross-module linkage — three contracts

> **Session 6 note.** Contract **C1** (awareness answers → M2 question selection) is now expressed as data, not code: each awareness question carries a `next_question_rules` JSONB column that names the next M2/M3 question to surface. The Python rule registry [`m2_linkage_rules.py`](../../backend/app/services/m2_linkage_rules.py) is preserved for the direct-entry `/surveys/knowledge` page, but the unified wizard reads rules straight off the row. See [§10](#10-unified-survey-wizard) for the rule shape and the new flow engine. **C2** and **C3** are unchanged.

### Contract C1: M1 awareness answers → M2 question selection

When an SME opens `/surveys/knowledge`, the backend reads their most-recent **awareness** answers from `survey_responses` and applies linkage rules from [`m2_linkage_rules.py`](../../backend/app/services/m2_linkage_rules.py):

| Awareness signal | M2 outcome |
|-----------------|-----------|
| Q1 (channel) ∈ {gazette, ird_portal} | boost `procedural` knowledge questions in the bank |
| Q4 (April 2026 VAT threshold awareness) = "no" | **force** `VAT_FACT_002` into the bank — even if the SME isn't in a VAT-heavy sector |
| Q5 (VAT rate awareness) = "no" | **force** `VAT_FACT_001` into the bank |

The rule registry is intentionally small and one-place. When research file 13 (M2 Knowledge Architecture) decides on more rules, add them to that file.

### Contract C2: M2 knowledge_score → M3 risk features

The BUILD_00 inter-module data contract — `GET /api/v1/m2/sme/{sme_id}/knowledge_score` — returns:

```json
{
  "sme_id": "uuid",
  "version": "v1",
  "overall_pct": 0.667,
  "overall_score_points": 2.0,
  "overall_max_points": 3.0,
  "by_domain": {
    "VAT": { "pct": 1.0, "n": 2, "correct": 2 },
    "EPF": { "pct": 0.0, "n": 1, "correct": 0 }
  },
  "instrument_breakdown": {
    "factual": { ... },
    "procedural": { ... }
  },
  "computed_at": "2026-05-09T...",
  "last_updated": "2026-05-09T..."
}
```

Cached in `m2_knowledge_scores`, recomputed eagerly on every `/api/v1/surveys/knowledge/submit`. The SME-facing `/risk` page reads this *and* the latest `m3_compliance_history` + `m3_behavioural_signals` snapshots through `GET /api/v1/m3/sme/{sme_id}/risk-signals`, returning a single `M3RiskSignals` payload that future BUILD_09 ML training will consume directly as features.

### Contract C3: M1 corpus → M2 RAG

Deferred. When BUILD_07 ships gazette ingestion and BUILD_08 §7 ships RAG, the same `survey_responses.meta.linked_regulation_id` field that the regulation-context cards already accept becomes the join key. Today's slice ships the *card surface* with one curated VAT-threshold example; the backend infrastructure is in place.

## 4. The `m2_questions` table — DB-driven, CA-verified

Schema highlights ([`m2_question.py`](../../backend/app/models/m2_question.py)):

| Column | Purpose |
|--------|---------|
| `question_code` | Stable PK: `VAT_FACT_001`, `EPF_FACT_001`, `VAT_RTL_001`, … |
| `domain_code` / `sector_code` | FK to lookups; sector NULL = universal |
| `question_format` | `mcq_single` \| `ordered_steps` \| `scenario_response` \| `numeric` \| `open` |
| `prompt_en` / `prompt_si` / `prompt_ta` | Trilingual prompts. `needs_translation = TRUE` until SI/TA filled |
| `options_json` | render-only options list |
| `correct_answer_json` | the ground truth — never sent to the frontend |
| `scoring_rubric_json` | partial-credit rules (e.g. ordered_steps `first_and_last_only`) |
| `ground_truth_source` | citation: "VAT Act Section 7 — exports zero-rated…" |
| `ground_truth_verified_by` / `verified_at` | CA verification — `NULL` until [Admin → Question bank → Verify] is clicked |
| `version` | bumps when correct_answer changes; old answers stay queryable |

The seed script [`seed_m23_questions.py`](../../backend/app/scripts/seed_m23_questions.py) is the executable form of `module_2_and_3_data_architecture.md` PART A — when the doc changes, edit the script too. The seed is idempotent (`ON CONFLICT DO NOTHING` per row) so `make seed` is safe to re-run.

**Per-sector partition.** `sector_code` is nullable; `NULL` (and the `"universal"` sentinel) means "every SME sees it". Both the unified flow (`_next_in_section` / `_sector_visible` in [`survey_question_service.py`](../../backend/app/services/survey_question_service.py)) and the standalone fetch (`questions_for_instrument`) apply `sector_code IS NULL OR sector_code = <SME.sector>`; the admin list-view OR's the same way when you filter by sector. So a `retail` SME gets the universal VAT block *plus* `VAT_RTL_001`; an `it` SME gets the universal block *plus* `VAT_ITS_001/002`; nobody gets another sector's questions. (Code-only before this was documented.)

## 5. The scoring engine

[`m2_scoring.py`](../../backend/app/services/m2_scoring.py) is pure logic — no DB. Each format has its own scorer:

| `question_format` | Scoring rule |
|-------------------|--------------|
| `mcq_single` | `selected_option == correct_answer.selected_option` → 1.0 / 0.0 |
| `scenario_response` | same as `mcq_single` |
| `numeric` | `min ≤ answer ≤ max` |
| `ordered_steps` | full match → 1.0; if `partial_credit` rule = `first_and_last_only` and first+last match → 0.5 |
| `open` | partial: hits/total of `required_elements` (case-insensitive substring) |

`survey_service.submit()` calls the scorer on every `knowledge` row, denormalises `domain_code` + `version` from the matched question, and writes `is_correct` + `score_points`. The aggregate cache row is then written by `m2_service.recompute_knowledge_score()`.

## 6. UX system — surveys

The `SurveyForm` ([`survey-form.tsx`](../../frontend/components/forms/survey-form.tsx)) composes:

- [`SurveyProgress`](../../frontend/components/forms/survey-progress.tsx) — sticky progress bar; counts only currently-visible questions so conditionals don't inflate the denominator until they appear.
- [`useAutosave + ResumeBanner`](../../frontend/components/forms/survey-autosave.tsx) — writes to `localStorage` every 10 s, shows a banner on next visit so the SME can resume mid-survey.
- [`SurveyErrorSummary`](../../frontend/components/forms/survey-error-summary.tsx) — anchored list at the top of the form when validation fails on submit.
- [`RegulationContextCard`](../../frontend/components/forms/regulation-context-card.tsx) — inline card before any question with a context entry; today only powers the April 2026 VAT threshold question.

Per-module accent (M1 trust-blue, M2 emerald, M3 amber) is a single CSS-variable swap in [`globals.css`](../../frontend/app/globals.css) — wrap a survey page in `module-m{1,2,3}` and the primary buttons + focus rings shift accordingly. Light + dark variants both defined.

Section grouping is driven by `groupKey` on the question — M2 surveys group by domain (VAT / Income Tax / WHT…), M3 by section (history / behaviour / stress / sector).

## 7. Admin surface

| Route | What it shows |
|-------|--------------|
| `/admin/regulations` | **Session 7.** List of admin-managed `m1_regulations` rows with domain/sector filters, "Only unverified" toggle, server-side pagination, inline **Verify** action that flips `expert_verified` + records `expert_verified_by` / `expert_verified_at`. Sidebar entry: `nav.adminRegulations`. |
| `/admin/regulations/new` | **Session 7.** Create form with EN/SI/TA Tabs panels, sectors multi-checkbox, severity 1–5 chip row, dates, source URL. Saves via `POST /api/v1/m1/regulations` and lands on the edit page. |
| `/admin/regulations/[id]/edit` | **Session 7.** Same form as `new/`, prefilled. Live "Preview as SME" panel renders the same `RegulationContextCard` an SME sees on `/surveys`, bound to `useWatch()` so the CA can verify the SME-side appearance while editing. |
| `/admin/m2/questions` | The question bank with sector + domain filters; inline **Verify** action sets `ground_truth_verified_by` + `verified_at` for the typed CA name. Wrapped in `module-m2` (Session 7 visual coherence — primary buttons / focus rings emerald). |
| `/admin/m2/scores` | Per-SME knowledge score + by-domain breakdown. Wrapped in `module-m2` (Session 7). |
| `/admin/m3/risk-signals` | Combined per-SME view: M2 score + M3 history + M3 behaviour, in one table. Wrapped in `module-m3` (Session 7 — buttons + focus rings amber). |

`require_admin` on every endpoint behind these pages; the `(admin)` route-group layout already runs `requireRole("admin")`.

> **Visual coherence note (Session 7).** The unified `/surveys` wizard swaps `module-m{1,2,3}` on the wrapper as the SME crosses module boundaries (trust-blue → emerald → amber). The admin shells for the same modules carry the matching class so the CA sees the same colour the SME is seeing while answering. M1 (awareness) renders in trust-blue (`module-m1`); M2 in emerald (`module-m2`); M3 in amber (`module-m3`). See §10.3 note.

## 8. Where to extend

- **New M2 question** → add a row in [`seed_m23_questions.py`](../../backend/app/scripts/seed_m23_questions.py), `make seed` again. No code deploy needed once DB-driven editing ships ([`BUILD_13`](../../frontend/BUILD_PLAN/BUILD_13_Admin_and_Annotation.md)).
- **New conditional follow-up** → add `dependsOn` to the question definition in `m3-vulnerability.ts` (or whatever bank); no renderer change needed.
- **New M2 question format** → add a scorer to [`m2_scoring.py`](../../backend/app/services/m2_scoring.py) and a renderer branch in [`question-renderer.tsx`](../../frontend/components/forms/question-renderer.tsx).
- **M1 per-regulation Q1–Q8** (see `module_1_and_4_data_architecture.md` §A5.2) → ships with BUILD_07. The renderer already handles every shape needed (single/likert/date/multi/short_text + `dependsOn`).
- **RAG-backed regulation cards** → `RegulationContextCard` already accepts the props; switch the data source from the curated map to a backend lookup once BUILD_08 ships ChromaDB ingest.

## 9. Verification of this slice

1. `make migrate && make seed` — applies `202605090001_module23_schema.py`; populates 9 domains, 12 sectors, ~40 M2 questions.
2. `make dev-backend && make dev-frontend`.
3. Sign in as `sme@enigmatrix.lk` (sector retail). Visit `/regulations` → three survey cards. Take Knowledge → see score on the thank-you page. Take Vulnerability → confirm the `M3_HIST_002` follow-up appears only after picking "Yes" on `M3_HIST_001`. Visit `/risk` → see the score + history.
4. Sign in as `admin@enigmatrix.lk`. Visit `/admin/m2/questions` → verify a question. Visit `/admin/m2/scores` and `/admin/m3/risk-signals` → see the SME's data.
5. `cd backend && uv run pytest -q` — green: existing tests + `test_m2_scoring`, `test_m2_flow`, `test_m3_flow`.
6. `cd frontend && pnpm e2e` — green: existing spec + `surveys_knowledge_vulnerability.spec.ts`.

## 10. Unified survey wizard

Session 6 ships a single regulation-aware flow at `/surveys` that walks the SME through M1 → M2 → M3 in one trip, branching server-side based on actual answers. Session 16 replaced the two-endpoint flow with the session-based API (see §11). This section documents the rule shape and branching logic; the loop is documented in §11.

### 10.1 The loop

Two endpoints; one request per question:

| Method + path | Returns | Notes |
|---------------|---------|-------|
| `GET /api/v1/survey-flow/start` | `FlowState { next_question, progress, last_submitted_at, flow_status }` | First unanswered branching-root question. Resumes mid-flow by replaying existing `survey_responses` rows — no separate progress table. |
| `POST /api/v1/survey-flow/answer` | same shape | Persists the single answer, then returns the next question (or `flow_status: "completed"` when the flow ends). |

Source: [`backend/app/api/v1/survey_flow.py`](../../backend/app/api/v1/survey_flow.py), schemas in [`backend/app/schemas/survey_flow.py`](../../backend/app/schemas/survey_flow.py), engine in [`backend/app/services/survey_question_service.py`](../../backend/app/services/survey_question_service.py).

The frontend wizard at [`frontend/components/forms/survey-wizard.tsx`](../../frontend/components/forms/survey-wizard.tsx) renders one question at a time, calls `SurveyFlowApi.answer` ([`lib/api/survey-flow.ts`](../../frontend/lib/api/survey-flow.ts)), and replaces local state with the response.

### 10.2 The `next_question_rules` shape

Every row in `survey_questions` carries a `next_question_rules` JSONB column. List of predicates evaluated top-down; first match wins:

```jsonc
[
  { "when": { "answer_eq": "no" },                    "goto_question_code": "VAT_FACT_002" },
  { "when": { "answer_in": ["no", "unsure"] },        "goto_question_code": "VAT_FACT_002" },
  { "when": { "answer_lt": 3 },                       "goto_question_code": "M3_HIST_004" },
  { "when": { "answer_gt": 0 },                       "goto_question_code": "M3_HIST_002" }
]
```

When no rule matches, the engine falls back to "next question in `instrument_section` by `sort_order`". When the named `goto_question_code` doesn't exist, it falls back the same way — and logs a structured warning so the admin can fix the rule.

Predicate evaluator: `_resolve_rule` in [`survey_question_service.py`](../../backend/app/services/survey_question_service.py). Adding a new predicate type means adding a branch there + documenting it here.

### 10.3 Cross-module branching example

The seeded links encoded in [`seed_awareness_questions.py`](../../backend/app/scripts/seed_awareness_questions.py), [`seed_m23_questions.py`](../../backend/app/scripts/seed_m23_questions.py) (`CROSS_MODULE_LINKAGE`), and [`seed_vulnerability_questions.py`](../../backend/app/scripts/seed_vulnerability_questions.py):

```
awareness.v1.q04 (April 2026 VAT-threshold awareness)
   answer ∈ {"no", "unsure"}
        └─► next_question = VAT_FACT_002 (M2 procedural — "do you know the steps to register?")
                 wrong answer
                      └─► next_question = M3_HIST_004 (M3 — "do you know the penalties?")
```

A second, fully-wired chain — the reference implementation for a per-regulation M1→M2→M3 journey — is anchored on the seeded regulation `VAT_SSCL_MERGE_2026` ("VAT and SSCL merged into a single 20% VAT, April 2026 — a *restructuring*, not a real 2-point increase"). All four questions are junction-linked to that regulation, so the regulation-scoped flow (`/surveys/regulation/<id>`) traverses the whole chain; the `yes_restructure` answer is the fully-aware one and progresses linearly (no jump):

```
awareness.v1.q13  (is_branching_root, linked → VAT_SSCL_MERGE_2026)
   answer ∈ {"yes_increase", "no", "unsure"}        ← "yes_restructure" → linear progress
        └─► VAT_SSCL_MERGE_FACT_001 (M2 factual — "which two charges does the 20% VAT replace?")
                 answer ∈ {"B","C","D"}
                      └─► M3_VAT_SSCL_MERGE_PRACTICE (M3 behaviour — "one 20% line, or still VAT+SSCL separately?")
                              answer ∈ {"still_separate","stopped_sscl_wrong_rate","unsure"}
                                   └─► M3_VAT_SSCL_MERGE_PENALTY (M3 stress — penalty consequence)
```

A wrong answer at any step routes to the matching follow-up; a right answer linearly progresses by `sort_order`. The wizard's accent class swaps from `module-m1` (trust-blue) → `module-m2` (emerald) → `module-m3` (amber) as the flow crosses module boundaries, giving the SME a visual cue that they've changed territory.

> **Reachability note.** `awareness.v1.q13` is `is_baseline = false`, so it does **not** appear in the standalone awareness survey or the global "by module" flow's awareness section — it surfaces only in the `VAT_SSCL_MERGE_2026`-scoped flow / the "By regulation" hub tab. (In the global flow, `start_flow` returns `awareness.v1.q01`, the baseline root.) If a regulation-scoped flow has no in-scope `is_branching_root` question at all, `start_flow` now falls back to the first in-scope question by `(module_number, sort_order)` rather than returning nothing.

> **Note.** `module-m1` is the trust-blue accent class for M1 Awareness. `globals.css` defines `module-m1`, `module-m2` (emerald), and `module-m3` (amber) rules. Session 19 renamed the awareness module from 0 → 1, aligning the CSS class name with the DB `module_number`.

### 10.4 M3 projection on submit

When the unified wizard answers a `module_number = 3` question, the row lands in `survey_responses` (canonical) **and** is projected into the legacy M3 tables (`m3_compliance_history` / `m3_behavioural_signals`) via the `_project_m3_snapshots` helper in [`survey_service.py`](../../backend/app/services/survey_service.py). This keeps the existing `/risk` page and the `M3RiskSignals` payload (Contract C2) working unchanged when answers come in via the unified flow.

**Which column an answer feeds is data-driven (OQ32).** Each M3 question carries a `survey_questions.m3_field_mapping` JSONB column — `{"target": "compliance_history" | "behavioural_signals", "column": "<col>", "coerce": "yes_no" | "band" | "int" | "csv_list"}`. When it's `NULL`, the projection falls back to `_M3_DEFAULT_MAPPINGS` keyed by the canonical `question_code` (so the built-in `M3_HIST_*` / `M3_BEH_*` / `M3_STR_*` bank behaves exactly as before). An M3 question with neither a custom mapping nor a default (e.g. an admin-authored stress question, or the seeded `M3_VAT_SSCL_MERGE_*` follow-ups) is recorded in `survey_responses` but doesn't project — and the admin can opt it in by setting `m3_field_mapping` on the question (Admin → Question bank → edit → "M3 risk-signal mapping" card, module-3 only). The writable column allow-list is derived at import time from the `m3_compliance_history` / `m3_behavioural_signals` models (`survey_service.M3_MAPPING_COLUMNS`); bad mappings are rejected at write time (`survey_service.validate_m3_mapping`).

### 10.5 Resume semantics

`GET /survey-flow/start` does not require a separate progress row. The engine queries `survey_responses` for the SME, builds the set of answered `question_code`s, and walks past them in `(instrument_section, sort_order)` order. The first unanswered branching root (or the next unanswered question following the last answered one's rules) is returned.

OQ10 was resolved in this direction during Session 6 — see [`docs/tracker/SESSIONS.md`](../../tracker/SESSIONS.md) Session 6 "Decisions".

### 10.6 Field-name sanitisation (F-89, Session 9)

react-hook-form interprets `.` in field names as object-path notation. Awareness `question_code` values are dotted (e.g. `awareness.v1.q01`), so naïvely calling `register(q.id)` with `q.id = q.question_code` writes the value at `values.awareness.v1.q01` (nested) — and the wizard's submit handler reads `values[code]` (flat) → `undefined` → backend rejects → silent failure.

The wizard sanitises form-field ids via [`frontend/lib/surveys/safe-field-id.ts`](../../frontend/lib/surveys/safe-field-id.ts):

```ts
toFieldId(code: string): string  // "awareness.v1.q01" → "awareness__DOT__v1__DOT__q01"
```

`flow-question-to-ui.ts` returns the safe id as `Question.id`, so `QuestionRenderer.register(q.id, …)` sees a flat key. The wizard's `onSubmit` reads `values[toFieldId(current.question_code)]`. **The backend still receives the original `question_code` over the wire** — only the RHF boundary is sanitised.

If you add a new question whose `question_code` contains a `.`, this works automatically. If you add one that contains `[` or `]` (also RHF path metacharacters), extend `toFieldId` to escape them. See troubleshooting entry #24 for the bug class.

### 10.7 Regulation-anchored question authoring (Session 11, F-100 → F-105)

The unified `survey_questions` table has been read-only on the admin side until Session 11. F-100 → F-105 ship the full write surface — backend admin CRUD + an `<QuestionForm>` + a `<BranchingRulesEditor>` (Visual + JSON tabs) + a regulation-anchored 3-step wizard at `/admin/regulations/[id]/authoring`. New questions and regulations no longer require a Python seed edit and a `make seed` re-run.

#### Worked example — VAT 20 % regulation

1. Admin creates a regulation `VAT_RATE_2026_20PCT` at `/admin/regulations/new`.
2. From the regulation's edit page, click **Author from scratch** → lands on `/admin/regulations/VAT_RATE_2026_20PCT/authoring`.
3. **Step 1 (M1 awareness root).** Form pre-fills `module_number=1`, `linked_regulation_id`, `is_branching_root=true`, `instrument_section=awareness`. Admin types *"Are you aware that VAT changed to 20 %?"*, picks `yes_no` format, fills SI/TA prompts under the Tabs primitive, saves.
4. **Step 2 (M2 knowledge follow-ups).** Two side-by-side panels (`yes` / `no`). Admin authors *"Do you know how to register / calculate / file the new rate?"* under the "yes" panel — `mcq_single` with one option flagged correct (writes to `correct_answer_json`).
5. **Step 3 (M3 vulnerability).** Two panels (`m1_no` / `m2_wrong`). Admin authors *"Do you know the penalties for late VAT remittance under the new rate?"* under "M2 wrong".
6. **Wire the branching rules.** Open the M1 root in `<QuestionForm>` and add rules in the `<BranchingRulesEditor>`:
   ```jsonc
   [
     { "when": { "answer_eq": "yes" }, "goto_question_code": "VAT_M2_KNOW_RATE" },
     { "when": { "answer_eq": "no" },  "goto_question_code": "VAT_M3_PENALTY_AWARE" }
   ]
   ```
   Then on `VAT_M2_KNOW_RATE`, add a rule routing wrong answers to `VAT_M3_PENALTY_AWARE`. The flow engine reads `next_question_rules` server-side via `_resolve_rule` (§10.2) — no code deploy.

The SME-side `/surveys` wizard (F-71) walks this graph live the moment the questions are saved.

#### Backend surface (F-100)

```
GET    /api/v1/admin/survey-questions?module_number=&regulation_id=&sector_code=&domain_code=&knowledge_type=&only_unverified=&include_archived=&search=&page=&size=
GET    /api/v1/admin/survey-questions/by-regulation/{regulation_id}
POST   /api/v1/admin/survey-questions/bulk-verify
POST   /api/v1/admin/survey-questions
GET    /api/v1/admin/survey-questions/{question_code}
PATCH  /api/v1/admin/survey-questions/{question_code}
DELETE /api/v1/admin/survey-questions/{question_code}            # soft-archive
POST   /api/v1/admin/survey-questions/{question_code}/restore
POST   /api/v1/admin/survey-questions/{question_code}/duplicate
POST   /api/v1/admin/survey-questions/{question_code}/verify
```

All require `require_admin`. Mutations write `survey_question.{created,updated,archived,restored,duplicated,verified,bulk_verified}` events to `audit_log`. The legacy `/m2/questions` endpoint stays live with a `Deprecation: true` header pointing at `successor-version=/admin/survey-questions?module_number=2`; OQ12 (the hard redirect) is deferred.

#### Frontend surface (F-101 → F-103)

- **`/admin/questions`** — unified list with Module / Domain / Sector / Format / unverified-only / archived-toggle filters, search across `question_code` + `prompt_en`, bulk-verify action bar, row actions (Duplicate / Archive ↔ Restore).
- **`/admin/questions/new`** and **`/admin/questions/[code]/edit`** — five-card `<QuestionForm>` (Identity / Linkage / Localised / Answers / Branching) with a sticky save bar.
- **`<BranchingRulesEditor>`** — Visual + JSON tabs sharing a single `next_question_rules` form-state field. Visual mode adapts the value input to `question_format` (Combobox of options for categorical, numeric input for likert/numeric, free-text fallback). JSON mode parses on **Apply**; invalid JSON renders inline as a destructive Alert.
- **`/admin/regulations/[id]/authoring`** — the 3-step wizard above.
- **Regulation edit page** — `<LinkedQuestionsPanel>` Card at the bottom groups linked questions by module (M1 / M2 / M3) with deep-links into the question edit page.

#### Schema invariants enforced at write time

- `BranchingPredicate` requires **exactly one** of `answer_eq` / `answer_in` / `answer_lt` / `answer_gt`. Backend rejects with 422; frontend zod superRefine surfaces inline before submit.
- `question_code` is unique + immutable after creation (PATCH ignores it, edit form disables the input).
- `goto_question_code` validity is **soft-warned**, not enforced (OQ30) — the engine already falls back to linear next when the target is missing, so partial authoring isn't blocked.

### 10.8 Universal regulation-anchored architecture (Session 12, F-106 → F-118)

Session 11 shipped admin authoring for one regulation at a time using a rigid 3-step wizard (M1 awareness → M2 yes/no → M3 vulnerability). Session 12 generalises this in five layers:

1. **M:N junction `survey_question_regulations`** — a question can now belong to N regulations. Composite PK `(question_code, regulation_id)`, `weight smallint`, `is_primary bool`. The pre-existing `survey_questions.linked_regulation_id` column is kept as a **cached primary pointer** so the admin list-view JOIN still hits one column. The migration drops only the FK constraint; the junction's own FK enforces integrity. Service helper `_sync_primary_junction(question_code, new_linked_regulation_id)` keeps cache + junction in lockstep on every create/update.
2. **`is_baseline` flag** — orthogonal to regulation links. A baseline question (`is_baseline=true`) shows in the standalone awareness/knowledge/vulnerability surveys regardless of which regulations are active. The 12 generic awareness questions (`awareness.v1.q01` through `q12`) are baseline; q04 + q05 are *both* baseline AND linked to VAT regulations (always-show + also-show-when-filtering).
3. **Branching validators (soft-warn)** — `validate_branching(question_code)` runs DFS over `next_question_rules` and returns three warning kinds: `forward_ref` (target doesn't exist), `archived_target` (target inactive), `cycle` (loop back to source). `create_question` / `update_question` re-run on every write. Soft-warn matches OQ30 — the engine already falls back to linear progression on broken targets. Surfaced via `validation_warnings` on `SurveyQuestionAdminOut` and the standalone endpoint `GET /admin/survey-questions/{code}/validate-flow`.
4. **Regulation-scoped flow** — `start_flow` / `next_question` accept `regulation_id`. When set, root selection + linear fallback + `goto_question_code` resolution all scope to junction-linked questions. `/api/v1/survey-flow/{start,answer}?regulation_id={uuid}` powers the new SME page `/surveys/regulation/[id]`.
5. **DB-driven per-instrument fetch** — `GET /api/v1/surveys/{instrument}/questions?sector?=&regulation_id?=&include_baseline=true` returns merged baselines + regulation-linked rows ordered by `is_baseline DESC, effective_date ASC, sort_order ASC`. SME-safe `SurveyQuestionPublicOut` strips `correct_answer_json`, `scoring_rubric_json`, `ground_truth_*`. Adding a regulation in admin auto-grows the standalone surveys with no code changes.

#### Visual flow canvas (`/admin/regulations/[id]/flow`)

Replaces the rigid 3-step wizard for advanced flows; wizard kept as a "Quick start" entry. Implementation: CSS-grid three-column layout (`module-m1` / `module-m2` / `module-m3` accents), each card lists answer options as clickable chips. Click a chip → `<FlowQuestionDrawer>` opens (Radix Sheet), pre-filled with parent context. On save:

1. `AdminSurveyQuestionsApi.create({...})` creates the child question with `linked_regulation_id` pre-set.
2. `AdminSurveyQuestionsApi.update(parentCode, { next_question_rules: [...existing, { when: { answer_eq: parentValue }, goto_question_code: childCode } ] })` upserts the parent's rule.

`<FlowValidationBanner>` surfaces validator output with click-to-jump behaviour. Existing rules show as "→ TARGET" badges next to chips that already route somewhere.

CSS-grid was chosen over `@xyflow/react` (ReactFlow) to avoid the ~60 KB dep on admin chunks; the data shape is already a graph and can be retrofitted with pan/zoom/drag by swapping `<FlowCanvas>`'s body without changing the data flow.

#### Two-tab surveys hub (`/surveys`)

URL state: `?view=regulation|module`.

- **By regulation** — lists pending sector-relevant regulations as `<RegulationCard>` (severity badge, effective date, English-fallback flag if SI/TA missing). Click → `/surveys/regulation/[id]` runs the regulation-scoped unified flow.
- **By module** — three abstract instrument cards routing to the (now DB-driven) standalone awareness / knowledge / vulnerability surveys.

Dashboard widget "Regulations awaiting your assessment" reads `/api/v1/dashboard/pending-regulations` (active sector-relevant regulations the SME hasn't answered any question for yet).

#### Translations admin (`/admin/translations`)

Lists every `survey_question` with `needs_translation=true` plus every `m1_regulation` missing any SI/TA field. Inline SI/TA edit per row; bulk-mark-translated for questions. Backend i18n fallback (`localised(record, field_base, locale)`) means SMEs see English with a "Showing English" badge until SI/TA lands, no broken-prompt UX.

#### New audit events

- `survey_question.linked_to_regulation`
- `survey_question.unlinked_from_regulation`
- `survey_question.primary_regulation_changed`
- `translation.completed` (single + bulk both emit it)
- `survey.submitted` (Session 14 — one row per SME `survey_service.submit`, with `{ instrument, answered_count, regulation_ids, m2_scored, m3_snapshots_projected }`; the M2 score recompute + M3 snapshot projection are folded into this row, not separate events)

> A flow *start* (`/surveys/regulation/[id]`) is a read, not a mutation — it writes no audit row. See [`07_Auth_and_Roles.md` §6](07_Auth_and_Roles.md) for the full audit-event registry and the `/admin/activity-log` UI.

### 10.9 Where to extend

- **A new per-regulation M1→M2→M3 chain** (like the seeded `VAT_SSCL_MERGE_2026` reference): (1) add the regulation (`/admin/regulations/new` or [`seed_regulations.py`](../../backend/app/scripts/seed_regulations.py)); (2) add an M1 awareness question with `is_branching_root = true`, its `linked_regulation_id` set, and a `next_question_rules` entry routing the non-ideal answers to the M2 question; (3) add the M2 question with `correct_answer_json` set and a rule routing wrong answers to the M3 question; (4) add the M3 question(s) (optionally with an `m3_field_mapping` so the answer feeds the risk model); (5) **junction-link *all* of those questions to the regulation** — the engine discards an out-of-scope `goto_question_code` and falls back to linear, so a chain whose mid-link isn't in scope dead-ends in the regulation-scoped flow; (6) optionally update [`seed_demo_responses.py`](../../backend/app/scripts/seed_demo_responses.py). No code deploy. (`seed_awareness_questions.py` / `seed_vulnerability_questions.py` take a `linked_regulation_short` per row that resolves the short code → id and writes the junction primary row.)
- **New cross-module rule** → add a row to `next_question_rules` on the source question via the admin UI (flow canvas chip click) or by extending the seed script. No code change.
- **Many-to-many a question across regulations** → use the M:N endpoints (`POST /admin/survey-questions/{code}/regulations`, then `…/regulations/{id}/primary` to pick which one becomes the cached primary). Or just use the existing `linked_regulation_id` field — `_sync_primary_junction` writes a junction row automatically.
- **New predicate type** (e.g. `answer_contains`) → extend `BranchingPredicate.model_validator`, add a branch to `_answer_matches`, document in §10.2 and the validator.
- **A new M3 risk-signal target column** → add the column to the `m3_compliance_history` / `m3_behavioural_signals` model (+ migration); `survey_service.M3_MAPPING_COLUMNS` picks it up from the model automatically. Mirror the column name in `frontend/lib/validators/survey-question.ts` `M3_MAPPING_COLUMNS` so the admin select offers it. (If it needs a new coercion, add it to `survey_service._COERCERS` and the `coerce` literal in both the backend schema and the frontend validator.)
- **New question format** → add the format to `lib/surveys/db-question-adapter.ts` and to `QuestionRenderer`.
- **New module** → add to `ModuleNumber` literal, `INSTRUMENT_TO_MODULE_NUMBER` map, and a fourth column to `<FlowCanvas>`.
- **Custom branching policy** → override `_resolve_rule` (e.g. weighted random routing for A/B-style experiments).
- **Admin-managed regulations** → use the CRUD endpoints under `/api/v1/m1/regulations` (see [`07_Auth_and_Roles.md`](07_Auth_and_Roles.md) §2).

### 10.10 Per-row regulation link + flow breadcrumb (Session 15)

`survey_responses.linked_regulation_id` is now written on **every** row: the scoped `regulation_id` when the answer arrived via `/survey-flow/answer?regulation_id=…` (authoritative), otherwise the answered question's cached `survey_questions.linked_regulation_id` (so standalone-page submits and un-scoped flow answers still link rows for single-regulation questions). NULL = a generic question with no link. Consequences: the `survey.submitted` audit event's `regulation_ids` is non-empty for regulation-scoped flows; `GET /api/v1/dashboard/pending-regulations` marks a regulation "answered" once any of its linked questions is answered; the admin Activity Log keeps the regulation context.

`survey_responses.meta` carries the **flow breadcrumb** `{"from_question_code": "<parent code>", "from_rule": {"when": …, "goto_question_code": …}}` on any row that was reached by a `next_question_rules` jump — absent on the branching root and on linearly-reached rows, and absent on batch submits from the standalone instrument pages (a batch isn't a flow). `survey_flow.py::_flow_breadcrumb` computes it by checking whether the SME's prior answered row had a rule that resolved to the question being answered. The full M1→M2→M3 path is reconstructible by walking `from_question_code` backwards across the SME's rows.

---

## 11. Phase 3 — Session-Based Survey Architecture (Sessions 16–17)

> **Note:** Sections 1–10 above describe the regulation-scoped question-flow system (`/api/v1/survey-flow/…`). This section documents a **parallel, additive** layer that was introduced to track per-SME survey submission counts and enforce admin-configurable limits.

### What changed

A new `survey_sessions` table groups responses per SME survey run. Rather than calling the regulation-scoped flow endpoints directly, the session-based path wraps each survey in a `survey_sessions` row that tracks status, question counts, and completion.

Key additions:

- **`survey_sessions` table** — one row per survey run; linked to `sme_profiles` via `sme_id`.
- **Session API** (`/api/v1/survey-sessions/…`) — 6 endpoints: `POST /start`, `GET /my-history`, `GET /{id}`, `GET /{id}/next-question`, `POST /{id}/answer`, `POST /{id}/complete`. See [`13_Unified_Survey_Configuration.md`](13_Unified_Survey_Configuration.md) §2 for the full loop.
- **`survey_limits` table** — DB singleton (`id=1`) holding per-role caps (`sme_limit`, `annotator_limit`, `admin_limit`). Checked on every `/start` call. Admin-configurable at `/admin/settings`.
- **`SurveyLauncher` + `SurveyWizard`** frontend components — session lifecycle management (create/resume via localStorage) and one-question-at-a-time rendering with module accent CSS and back-navigation.
- **SME get-or-create** — `get_current_sme` dep in `deps.py` auto-creates a blank `SMEProfile` on first access; no separate registration needed.
- **Migration resilience** — `survey_limits_service.get_limits(db)` catches `ProgrammingError` (table not yet migrated), rolls back the aborted transaction, and returns safe in-memory defaults so surveys continue to work before `alembic upgrade head` is run.

### Coexistence with the flow system

The two systems are complementary:

| System | Entry point | Session row? | Limit check? | Used for |
|--------|------------|:---:|:---:|---------|
| Regulation-scoped flow | `GET /survey-flow/start?regulation_id=…` | ✗ | ✗ | In-app per-regulation survey flow + branching |
| Session-based survey | `POST /survey-sessions/start` | ✅ | ✅ | SME submission counting + admin-configurable limits |

A full deployment uses both: the regulation-scoped flow for the question-by-question logic, and the session layer for accounting and governance.

> **M4 status.** `per_module_m4` appears in `MODE_CAPS` and `MODE_INSTRUMENT` in `survey_session_service.py` and in the `survey_sessions.survey_mode` CHECK constraint. Starting a `per_module_m4` session succeeds, but `GET /{id}/next-question` immediately returns `flow_status: "completed"` because there are no `module_number=4` questions in the DB. The `/verify` route and `/api/v1/verify/claim` remain 501 stubs. BUILD_10 has not started.

---

**Prev:** [`10_Next_Steps.md`](10_Next_Steps.md) &nbsp;·&nbsp; **Next:** [`12_UI_Screens_and_Loading.md`](12_UI_Screens_and_Loading.md)
