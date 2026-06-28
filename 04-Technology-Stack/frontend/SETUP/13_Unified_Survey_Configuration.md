# Unified Survey Configuration Guide

The unified survey is a single-spine question flow that crosses all three implemented modules (Awareness M1, Knowledge M2, Vulnerability M3) in one session. A fourth module (Misinformation M4) is reserved in the session API but has no questions seeded; see §2 table note. This document explains how it is configured, how to add/edit questions, how to wire branching rules, and how to test the full end-to-end flow.

> See also: [11_Survey_System.md](11_Survey_System.md) for the data architecture and [APP_GUIDE.md](../APP_GUIDE.md) for the admin UI walkthrough.

---

## 1. What Makes It "Unified"

| Aspect | How it's unified |
|--------|-----------------|
| Storage | Single `survey_responses` table; `module_number` column (1/2/3/4) identifies which module each row belongs to |
| Flow control | One service (`survey_question_service`) evaluates `next_question_rules` JSONB on any question from any module |
| Branching | Cross-module jumps are data-driven: a rule on an M1 question can `goto` an M2 question code |
| Regulation scope | `?regulation_id=uuid` param scopes the flow to baseline questions + junction-linked questions for that regulation |
| Scoring | M2 only; computed eagerly after each answer; cached in `m2_knowledge_scores` |
| Submission | Single `POST /api/v1/survey-flow/answer` handles all three modules; M3 answers are also projected into legacy snapshot tables |

---

## 2. Session-Based Flow Loop

The survey system uses a **session-based** architecture. Each survey run is tracked as a `survey_sessions` row; questions are served one at a time through a six-endpoint API.

```
POST /api/v1/survey-sessions/start  { survey_mode }
                 ↓  returns SessionOut (201)
GET  /api/v1/survey-sessions/{id}/next-question
                 ↓  returns FlowNextOut
POST /api/v1/survey-sessions/{id}/answer  { question_code, answer_text|answer_numeric|answer_options }
                 ↓  returns FlowNextOut
GET  /api/v1/survey-sessions/{id}/next-question
                 ↓  ...repeat until status = "completed"
POST /api/v1/survey-sessions/{id}/complete
                 ↓  returns { "status": "completed" }
```

**`survey_mode` values** (exact strings):

| Value | Questions | Cap |
|---|---|---|
| `per_module_m1` | M1 Awareness only | 10 |
| `per_module_m2` | M2 Knowledge only | 10 |
| `per_module_m3` | M3 Vulnerability only | 10 |
| `per_module_m4` | M4 Misinformation only | 10 (mode defined; no questions seeded — session starts but immediately completes; BUILD_10 pending) |
| `unified` | All 4 modules | 20 |

**`SessionOut` response shape:**
```json
{
  "session_id": "0f5f3eb7-6ef8-4d65-b845-2dfd0d0c1abc",
  "sme_id": "6b6d3b28-8d3f-4d11-b6df-bb372f56cdef",
  "survey_mode": "unified",
  "status": "in_progress",
  "questions_shown": 0,
  "questions_answered": 0,
  "started_at": "2026-05-10T11:00:00Z",
  "completed_at": null
}
```

**`FlowNextOut` response shape:**
```json
{
  "session_id": "0f5f3eb7-6ef8-4d65-b845-2dfd0d0c1abc",
  "question": {
    "question_code": "awareness.v1.q04",
    "module_number": 1,
    "question_format": "yes_no",
    "prompt_en": "Are you aware of the April 2026 VAT threshold change?",
    "options_json": [{"value": "yes", "label": "Yes"}, {"value": "no", "label": "No"}],
    "is_required": true
  },
  "progress": { "questions_shown": 1, "questions_answered": 0 },
  "status": "in_progress"
}
```

When `question` is `null` and `status` is `"completed"`, the session is exhausted — call `/complete` to close it.

> **Legacy note:** The old `GET /api/v1/survey-flow/start` + `POST /api/v1/survey-flow/answer` endpoints serve the regulation-scoped flow (SETUP/11 §10). They operate on the question bank directly and do **not** create `survey_sessions` rows. The session-based endpoints above are the canonical path for SME survey submission counting and limit enforcement.

---

## 3. Adding a Question via Admin UI

Go to `/admin/questions/new`. The form has five cards:

### Card 1 — Identity
| Field | Description | Example |
|-------|-------------|---------|
| `question_code` | Unique versioned key. Auto-suggested as `awareness.v1.qNN` from selected module. | `awareness.v1.q13` |
| Module | 1 = Awareness, 2 = Knowledge, 3 = Vulnerability | `1` |
| Format | `mcq_single / multi / likert / numeric / date / short_text / ordered_steps / yes_no / open / scenario_response` | `single` |
| Knowledge type | `factual / procedural / application / exception / behavioural / history` | `factual` |
| Sort order | Display order within the section | `13` |

> **Versioning:** When you change `correct_answer_json`, bump the version in `question_code` (e.g., `VAT_FACT_001` → `VAT_FACT_001_v2`) so historical answers remain queryable against the original correct answer.

### Card 2 — Linkage
| Field | Description |
|-------|-------------|
| Linked regulation | Which regulation this question tests (M:N, select multiple) |
| Is primary | Is this the primary regulation for this question? |
| Weight | Relative weight for regulation scoring (default 1.0) |
| `is_branching_root` | Can this question be the starting question of a flow? |
| `is_baseline` | Always include this question regardless of regulation filter |

**Baseline vs regulation-scoped:** A question with `is_baseline = true` always appears in the flow regardless of `regulation_id`. A junction-linked question only appears when the flow is scoped to that regulation. A question can be both.

### Card 3 — Localised Text
Fill prompts in all three languages (EN required; SI and TA optional — missing ones enter the translation queue).

### Card 4 — Answers (M2 only)

**`options_json` format** (for MCQ, multi, ordered_steps):
```json
[
  { "value": "option_a", "label": "Register online via IRD portal" },
  { "value": "option_b", "label": "Submit Form VAT-1 at district office" }
]
```

**`correct_answer_json` by format:**

| Format | Structure | Example |
|--------|-----------|---------|
| `mcq_single` | `{ "selected_option": "option_a" }` | `{"selected_option": "option_a"}` |
| `multi` | `{ "selected_options": ["a", "b"] }` | `{"selected_options": ["vat_1", "online"]}` |
| `ordered_steps` | `{ "ordered_values": ["step1", "step2", "step3"] }` | `{"ordered_values": ["register", "submit", "pay"]}` |
| `numeric` | `{ "min": 15, "max": 21 }` | `{"min": 18, "max": 18}` (exact) |
| `yes_no` | `{ "selected_option": "yes" }` | `{"selected_option": "yes"}` |
| `open` | `{ "required_elements": ["keyword1", "keyword2"] }` | `{"required_elements": ["18%", "VAT"]}` |

**`scoring_rubric_json`** (optional, M2 only):
```json
{ "partial_credit": "first_and_last_only" }
```
With `ordered_steps`, if only the first and last steps are correct → 0.5 points instead of 0.

### Card 5 — Branching Rules

Click "Add rule" to add a predicate row:

| Field | Options | Meaning |
|-------|---------|---------|
| Condition | `answer_eq` | Answer exactly equals this value |
| | `answer_in` | Answer is one of these values (array) |
| | `answer_lt` | Numeric answer is less than this value |
| | `answer_gt` | Numeric answer is greater than this value |
| Value | string / number / array | The comparison value |
| Go to | question code (picker) | Jumps to this question next |

Rules are evaluated top-down; first match wins. If no rule matches → linear progression (next by `instrument_section`, then `sort_order`).

**Example rules for an awareness question:**
```json
[
  { "when": { "answer_eq": "no" },              "goto_question_code": "VAT_FACT_001" },
  { "when": { "answer_eq": "unsure" },          "goto_question_code": "VAT_FACT_001" },
  { "when": { "answer_eq": "yes" },             "goto_question_code": "M3_HIST_001" }
]
```

---

## 4. Adding a Question via API

```bash
curl -X POST http://localhost:8000/api/v1/admin/survey-questions \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question_code": "awareness.v1.q13",
    "module_number": 1,
    "question_format": "yes_no",
    "prompt_en": "Are you aware of the SSCL changes effective March 2026?",
    "prompt_si": null,
    "prompt_ta": null,
    "options_json": [{"value": "yes", "label": "Yes"}, {"value": "no", "label": "No"}],
    "is_required": true,
    "is_baseline": false,
    "is_branching_root": false,
    "sort_order": 13,
    "next_question_rules": [
      { "when": { "answer_eq": "no" }, "goto_question_code": "SSCL_FACT_001" }
    ]
  }'
```

---

## 5. Linking a Question to a Regulation

**Via admin UI:** On the question edit page → Card 2 "Linkage" → regulation combobox → select → save.

**Via API:**
```bash
# Link question to regulation
POST /api/v1/admin/survey-questions/{question_code}/regulations/{regulation_id}

# Set as primary regulation
POST /api/v1/admin/survey-questions/{question_code}/regulations/{regulation_id}/primary

# Unlink
DELETE /api/v1/admin/survey-questions/{question_code}/regulations/{regulation_id}
```

---

## 6. Configuring a Regulation-Scoped Survey (End-to-End)

**Goal:** A new regulation "SSCL Rate Change Q3-2026" is published. You want SMEs to answer 3 awareness questions → 2 knowledge questions → 1 vulnerability question.

**Step 1 — Create the regulation:**
1. `/admin/regulations/new` → fill all fields, domain = SSCL, severity = 3, effective_date = 2026-09-01
2. Save → get `regulation_id = {uuid}`

**Step 2 — Create or identify questions:**
- `SSCL_AWR_001` (M1, `yes_no`, `is_branching_root: true`) — "Aware of SSCL rate change?"
- `SSCL_AWR_002` (M1, `mcq_single`) — "What is the SSCL basis?"
- `SSCL_AWR_003` (M1, `likert`) — "Confidence you'd identify SSCL change quickly (1–5)?"
- `SSCL_FACT_001` (M2, `mcq_single`) — "What is the new SSCL rate?" `correct_answer_json: {"selected_option": "2_5"}`
- `SSCL_FACT_002` (M2, `ordered_steps`) — "File SSCL return steps"
- `M3_HIST_001` (M3, existing baseline) — "Missed filing deadlines?" (already `is_baseline: true`)

**Step 3 — Link questions to the regulation:**
Link all 5 questions to `{uuid}`. Set `SSCL_AWR_001` as the branching root for this regulation.

**Step 4 — Set branching rules:**
On `SSCL_AWR_001`:
```json
[
  { "when": { "answer_eq": "no" },    "goto_question_code": "SSCL_FACT_001" },
  { "when": { "answer_eq": "yes" },   "goto_question_code": "SSCL_AWR_002" }
]
```
On `SSCL_AWR_002` → linear progression to `SSCL_AWR_003` (no rule needed if sort order is sequential).  
On `SSCL_FACT_001` → goto `SSCL_FACT_002`.  
After `SSCL_FACT_002` → linear progression finds `M3_HIST_001` (via baseline flag).

**Step 5 — Test:**
```bash
curl "http://localhost:8000/api/v1/survey-flow/start?regulation_id={uuid}" \
  -H "Authorization: Bearer $SME_TOKEN"
# Should return SSCL_AWR_001

curl -X POST "http://localhost:8000/api/v1/survey-flow/answer" \
  -H "Authorization: Bearer $SME_TOKEN" \
  -d '{"question_code": "SSCL_AWR_001", "answer_text": "no"}'
# Should return SSCL_FACT_001 (because rule: answer_eq "no" → goto SSCL_FACT_001)
```

---

## 7. Scoring Configuration (M2 Only)

The scoring engine (`backend/app/services/m2_scoring.py`) scores each M2 answer immediately on submit.

| Format | Scoring logic |
|--------|--------------|
| `mcq_single`, `yes_no`, `scenario_response` | Exact match → 1.0; no match → 0.0 |
| `multi` | All required options selected → 1.0; else 0.0 |
| `numeric` | `min ≤ answer ≤ max` → 1.0; else 0.0 |
| `ordered_steps` | Exact order → 1.0; if `partial_credit: "first_and_last_only"` and both correct → 0.5; else 0.0 |
| `open` | Count matching `required_elements`; score = `hits / total_required` (0.0–1.0) |
| `likert` | Numeric range check |

After scoring, `m2_service.recompute_knowledge_score(sme_id)` recomputes the aggregate and updates `m2_knowledge_scores`.

---

## 8. Seeding Questions

The dev seed scripts populate the `survey_questions` table:

```bash
cd backend

# Seed M1 awareness questions (12 rows)
python -m app.scripts.seed_awareness_questions

# Seed M2 + M3 questions (~40 rows)
python -m app.scripts.seed_m23_questions

# Seed vulnerability-specific M3 questions
python -m app.scripts.seed_vulnerability_questions
```

**When to re-seed:**
- After a fresh `alembic upgrade head` on a new DB
- Never on production (seeds are idempotent but use `INSERT ... ON CONFLICT DO NOTHING`)

**When to version-bump a question:**  
Change the `question_code` suffix (e.g., `VAT_FACT_001` → `VAT_FACT_002`) when `correct_answer_json` changes. Old answers remain linked to the old code; new answers use the new code.

---

## 9. Question Format Quick Reference

| Format constant | UI widget | Scoring possible |
|----------------|-----------|-----------------|
| `mcq_single` | Radio group | ✅ |
| `multi` | Checkboxes | ✅ |
| `likert` | 1–N scale buttons | ✅ (range) |
| `numeric` | Number input | ✅ (range) |
| `date` | Date picker | ✅ (range) |
| `short_text` | Single-line text | ❌ (manual review) |
| `open` | Textarea | ✅ (keyword match) |
| `ordered_steps` | Drag-sort list | ✅ (full / partial) |
| `yes_no` | Two-option radio | ✅ |
| `scenario_response` | Radio with scenario preamble | ✅ |

---

## 10. Accent Colours per Module

The wizard applies a CSS class to its wrapper `<div>` based on which module the current question belongs to. This switches all HSL token overrides for the module accent:

| Module | Class | Primary colour |
|--------|-------|----------------|
| M1 — Awareness | `module-m1` | Trust-blue (217 91% 50%) |
| M2 — Knowledge | `module-m2` | Emerald (160 84% 39%) |
| M3 — Vulnerability | `module-m3` | Amber (38 92% 50%) |

No code change needed when routing crosses module boundaries — the `module_number` from the API response drives the class.

---

## 11. Frontend Session Components

Two React components manage the session lifecycle for the SME-facing survey experience.

### `SurveyLauncher`

Manages session **create or resume**. On mount:
1. Checks localStorage for a stored `session_id` matching the requested `survey_mode`.
2. If found and still `in_progress`, resumes the existing session (no new `POST /start` call).
3. If not found, calls `POST /api/v1/survey-sessions/start` and stores the new `session_id`.
4. Passes the resolved `session_id` down to `<SurveyWizard>`.

Clearing localStorage (or calling `/complete`) ends the session. If an SME refreshes mid-survey, the banner on the `/surveys` hub shows the in-progress session via `GET /survey-sessions/my-history`.

### `SurveyWizard`

One-question-at-a-time renderer. Receives a `session_id` and:
- Calls `GET /survey-sessions/{id}/next-question` to fetch the current question.
- Renders the question using the format specified in `question_format` (`yes_no`, `mcq_single`, `multi`, `likert`, `numeric`, etc.).
- Applies a `module-m{N}` accent CSS class on the wrapper `<div>` based on the question's `module_number` — trust-blue for M1 (`module-m1`), emerald for M2 (`module-m2`), amber for M3 (`module-m3`).
- Supports back-navigation within the current session (tracks the question history in component state).
- Shows a progress bar derived from `questions_shown` / estimated total.
- On the final question, calls `POST /survey-sessions/{id}/complete`.

---

## 12. Survey Submission Limits

### Configuration

Limits are stored in the `survey_limits` DB singleton (one row, always `id = 1`) and are configurable by admins without redeployment:

| Role | Default | Meaning |
|------|---------|---------|
| `sme` | `10` | Up to 10 completed sessions |
| `annotator` | `0` | Unlimited |
| `admin` | `0` | Unlimited |

`0` in any field means **unlimited**.

### Admin UI

Navigate to **Settings** at `/admin/settings` in the admin sidebar. The page shows the current limits and allows updating them via a form that calls `PATCH /api/v1/admin/survey-limits`.

### Service layer

`survey_limits_service.get_limits(db)` is called by `POST /survey-sessions/start`. It:
1. Tries `db.get(SurveyLimits, 1)`.
2. If the `survey_limits` table doesn't exist yet (migration pending), catches `ProgrammingError`, rolls back the session, and returns in-memory defaults (`sme=10`, `annotator=0`, `admin=0`) so the rest of the request proceeds normally.
3. If the row is missing (fresh DB, post-migration), creates it with defaults and commits.

This makes the survey system resilient to the migration not having been run yet.

---

## 13. SME Profile Auto-Creation

The `get_current_sme` dependency in `backend/app/deps.py` uses a **get-or-create** pattern. On the first call for any authenticated user:

1. Looks up `SMEProfile` by `user.id`.
2. If not found, inserts a blank profile row (sector, region, etc. all `null`) and commits.
3. Returns the profile.

This means SMEs do **not** need a separate registration step to take a survey — any user with the `sme` role can call `POST /survey-sessions/start` immediately after login, and the profile will be auto-created on first access.

Downstream code (survey session creation, limit checks, response recording) reads from the returned profile, so the `null` sector is acceptable at survey start.

---

## 14. Common Mistakes & How to Fix Them

| Mistake | Symptom | Fix |
|---------|---------|-----|
| `goto_question_code` references a non-existent code | Warning logged; flow falls back to linear progression | Check `validation_warnings` in the question detail API response |
| Question not appearing in regulation-scoped flow | Flow skips the question | Ensure question is linked to the regulation via junction OR has `is_baseline: true` |
| M2 question has `correct_answer_json: null` | Score always 0.0 | Set `correct_answer_json` in the admin UI answer card |
| `ordered_steps` scoring wrong | Always 0.0 despite correct answer | Verify `options_json[*].value` exactly matches `correct_answer_json.ordered_values` entries |
| Missing SI/TA translation shows EN | Expected — `i18n_utils.get_text(question, locale)` falls back to EN | Translations appear in queue at `/admin/translations`; fill them to remove fallback |
| Survey start returns 500 on fresh DB | `survey_limits` table not migrated | Run `alembic upgrade head`; the resilience fix returns defaults in the meantime |
| Limit reached error not displayed in UI | `HTTPException(detail=dict)` format not parsed | The backend raises `ForbiddenError` (not `HTTPException`) to produce `{"code":"forbidden","message":"..."}` at the top level |
