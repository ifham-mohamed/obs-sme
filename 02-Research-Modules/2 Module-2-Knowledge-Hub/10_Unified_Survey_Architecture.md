# 13 — Unified Survey Architecture

> This document is the single authoritative reference for the target-state Enigmatrix survey architecture. It defines the survey modes, regulation-block model, branching rules, session model, and survey schema that the rest of the team should build toward.

> **Implementation Status (Session 19):** M1 Awareness, M2 Knowledge, and M3 Vulnerability are **fully implemented** — questions seeded, session API live, scoring/snapshots running, admin surfaces delivered. M4 Misinformation (`per_module_m4` session mode) is **stub only**: the mode is defined in the API enum and `survey_sessions.survey_mode` CHECK constraint, but no `module_number=4` questions are seeded and `/api/v1/verify/claim` returns 501. The four-question-per-regulation-block design (§3) and M4 branching (§4) are **target-state specs**, not current implementation. BUILD_10 has not started.

---

## 1. Overview

The survey system uses **one question bank** and **one shared schema** to support **four per-module surveys plus one unified survey**:

- Four per-module surveys:
  - Module 1 — Awareness
  - Module 2 — Knowledge
  - Module 3 — Risk / Vulnerability
  - Module 4 — Misinformation
- One unified survey that combines all four modules into regulation-scoped blocks

The core design principle is:

1. Regulations are the primary organizing unit.
2. Each applicable regulation produces one four-step block: **M1 → M2 → M3 → M4**.
3. The SME's sector determines which regulation blocks appear.
4. Every survey run is tracked by `survey_sessions`.
5. Every answer is recorded in `survey_responses` and linked back to the session.

Question-count policy:

- **Per-module mode:** 8–10 questions
- **Unified mode:** 15–20 questions total

This allows the same regulation content to be reused across focused module-specific surveys and the full unified experience without creating separate schema variants.

---

## 2. Survey Modes Table

| Mode                           | Questions                        | Cap | Route                   |
| ------------------------------ | -------------------------------- | --: | ----------------------- |
| Per-Module M1 (Awareness)      | M1 only, sector-filtered         |  10 | `/surveys/module/m1`    |
| Per-Module M2 (Knowledge)      | M2 only, sector-filtered         |  10 | `/surveys/module/m2`    |
| Per-Module M3 (Risk)           | M3 only, sector-filtered         |  10 | `/surveys/module/m3`    |
| Per-Module M4 (Misinformation) | M4 only, sector-filtered         |  10 | `/surveys/module/m4`    |
| Unified                        | All 4 modules, regulation blocks |  20 | `/surveys/unified`      |

`survey_mode` values used by the API and database (actual string values):

- `per_module_m1`
- `per_module_m2`
- `per_module_m3`
- `per_module_m4`
- `unified`

> **Note:** The prefix `per_module_m` is always followed by the module letter (`m1`–`m4`), not a digit only. The value `unified` is unchanged. Old references to `module_1` / `module_2` / `module_3` / `module_4` are incorrect.

---

## 3. Regulation Block Structure

Each regulation is represented as one independent survey block containing exactly four module-aligned questions in sequence:

1. **M1 Awareness**
2. **M2 Knowledge**
3. **M3 Risk / Vulnerability**
4. **M4 Misinformation**

Example block:

```text
Regulation: VAT Restructure
Sector visibility: Manufacturing, Wholesale & Retail, Services (VAT-registered)

Q-A-VAT-1-v1  -> M1 Awareness
Q-K-VAT-1-v1  -> M2 Knowledge
Q-V-VAT-1-v1  -> M3 Risk
Q-F-VAT-1-v1  -> M4 Misinformation
```

```text
Regulation: MRP Enforcement
Sector visibility: Retail, Food & Beverage, Tourism, Manufacturing

Q-A-MRP-1-v1  -> M1 Awareness
Q-K-MRP-1-v1  -> M2 Knowledge
Q-V-MRP-1-v1  -> M3 Risk
Q-F-MRP-1-v1  -> M4 Misinformation
```

Rules for block composition:

- The SME's `sector` is matched against `regulation_sector_map`.
- Only regulations relevant to that sector are included.
- Within a block, questions are always shown in **M1 → M2 → M3 → M4** order.
- **Blocks are independent.** There is no branching from one regulation block into another regulation block.
- Unified mode is formed by concatenating applicable blocks and applying the global 15–20 question cap.

---

## 4. Full Branching Logic

| M1 Answer    | M2 Shown?                                   | M3 Shown?                    | M4 Shown?                  | Backend Flag                                  |
| ------------ | ------------------------------------------- | ---------------------------- | -------------------------- | --------------------------------------------- |
| Yes (aware)  | Yes — full set                              | Yes — full set               | Yes — if sector matches    | `awareness = confirmed`                       |
| No (unaware) | Yes — framed as "do you know current rule?" | Yes — risk questions shown   | Yes — misinformation check | `awareness = gap_detected`                    |
| Not sure     | Yes                                         | Yes                          | Yes                        | `awareness = uncertain`                       |
| M2 correct   | —                                           | M3 severity normal           | M4 shown                   | `knowledge = accurate`                        |
| M2 wrong     | —                                           | M3 higher severity questions | M4 triggered regardless    | `knowledge = gap_detected + risk_flag = true` |

Implementation interpretation:

- M2 is still shown even when M1 indicates lack of awareness.
- M3 is always part of the block, but the wording or severity tier may change based on the M2 result.
- M4 remains in the same regulation block; it is not treated as a separate submission flow in the unified survey.

Typical trigger-condition notation:

```json
null
```

```json
{ "depends_on": "Q-A-VAT-1-v1", "answer_in": ["yes", "not_sure"] }
```

```json
{ "depends_on": "Q-K-VAT-1-v1", "is_correct": false, "severity": "high" }
```

```json
{ "sector_in": ["retail", "food_beverage", "tourism", "manufacturing"] }
```

---

## 5. Question ID Convention

All newly authored questions use this format:

```text
Q-{M}-{REG_CODE}-{N}-{v}
```

Examples:

```text
Q-A-VAT-1-v1   = Module 1, VAT regulation, question 1
Q-K-MRP-2-v1   = Module 2, MRP regulation, question 2
Q-V-EPF-1-v1   = Module 3, EPF regulation, question 1
Q-F-VAT-1-v1   = Module 4, VAT regulation, question 1
```

Legend:

- `A` = Awareness
- `K` = Knowledge
- `V` = Vulnerability / Risk
- `F` = Forwarded / Misinformation

Legacy compatibility:

- Existing legacy IDs such as `awareness.v1.q01` are still accepted for historical rows.
- New questions always use the new format.
- Old rows are not renamed retroactively.

---

## 6. Full DB Schema

This section defines the target survey schema used by the unified architecture. The regulation master table lives outside this section; the tables below are the survey-specific tables and mappings.

### 6.1 `survey_sessions`

Top-level grouping unit for one SME survey run. Each call to `POST /api/v1/survey-sessions/start` creates one row.

```sql
CREATE TABLE survey_sessions (
    session_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sme_id               UUID NOT NULL REFERENCES sme_profiles(sme_id),
    survey_mode          TEXT NOT NULL CHECK (survey_mode IN (
                             'per_module_m1', 'per_module_m2',
                             'per_module_m3', 'per_module_m4', 'unified'
                         )),
    status               TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN (
                             'in_progress', 'completed', 'abandoned'
                         )),
    questions_shown      INT NOT NULL DEFAULT 0,
    questions_answered   INT NOT NULL DEFAULT 0,
    recruitment_channel  TEXT,
    started_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at         TIMESTAMPTZ
);

CREATE INDEX idx_survey_sessions_sme_started
    ON survey_sessions (sme_id, started_at DESC);

CREATE INDEX idx_survey_sessions_mode_status
    ON survey_sessions (survey_mode, status);
```

> **Removed columns:** `question_cap`, `last_question_id`, and `meta` do not exist in the implemented schema. The question cap is computed at runtime from the `survey_limits` singleton (see §10).

### 6.2 `survey_responses`

One row per answered question, linked to the parent session.

```sql
CREATE TABLE survey_responses (
    response_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id       UUID NOT NULL REFERENCES survey_sessions(session_id) ON DELETE CASCADE,
    sme_id           UUID NOT NULL REFERENCES sme_profiles(sme_id),
    regulation_id    UUID,
    module_number    SMALLINT NOT NULL CHECK (module_number IN (1, 2, 3, 4)),
    survey_mode      TEXT NOT NULL CHECK (survey_mode IN (
                        'per_module_m1', 'per_module_m2',
                        'per_module_m3', 'per_module_m4', 'unified'
                     )),
    question_id      TEXT NOT NULL,
    answer_text      TEXT,
    answer_numeric   NUMERIC,
    answer_date      DATE,
    answer_options   JSONB,
    is_correct       BOOLEAN,
    submitted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, question_id)
);

CREATE INDEX idx_survey_responses_session
    ON survey_responses (session_id);

CREATE INDEX idx_survey_responses_regulation_module
    ON survey_responses (regulation_id, module_number);
```

### 6.3 `survey_question_bank`

Structure, logic, and scoring metadata for every survey question.

```sql
CREATE TABLE survey_question_bank (
    question_id          TEXT PRIMARY KEY,
    regulation_id        UUID NOT NULL,
    module_number        SMALLINT NOT NULL CHECK (module_number IN (1, 2, 3, 4)),
    question_order       INT NOT NULL,
    version              TEXT NOT NULL DEFAULT 'v1',
    question_type        TEXT NOT NULL,
    trigger_condition    JSONB,
    severity_variant     TEXT,
    answer_options       JSONB,
    correct_answer_json  JSONB,
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_survey_question_bank_regulation_module
    ON survey_question_bank (regulation_id, module_number, question_order);

CREATE INDEX idx_survey_question_bank_active
    ON survey_question_bank (is_active);
```

### 6.4 `survey_question_text`

Multilingual question text separated from the structural bank record.

```sql
CREATE TABLE survey_question_text (
    question_id    TEXT NOT NULL REFERENCES survey_question_bank(question_id) ON DELETE CASCADE,
    lang_code      TEXT NOT NULL CHECK (lang_code IN ('en', 'si', 'ta')),
    question_text  TEXT NOT NULL,
    helper_text    TEXT,
    PRIMARY KEY (question_id, lang_code)
);
```

### 6.5 `regulation_sector_map`

Declares which sectors should see each regulation block.

```sql
CREATE TABLE regulation_sector_map (
    regulation_id  UUID NOT NULL,
    sector_code    TEXT NOT NULL,
    impact_level   TEXT NOT NULL DEFAULT 'primary',
    PRIMARY KEY (regulation_id, sector_code)
);

CREATE INDEX idx_regulation_sector_map_sector
    ON regulation_sector_map (sector_code);
```

---

## 7. Regulation Bank Setup Procedure

The research team prepares each new regulation block manually in this order:

1. Add the regulation to the regulation registry used by Module 1.
2. Add sector mappings to `regulation_sector_map`.
3. Write one English question per module:
   - M1 awareness
   - M2 knowledge
   - M3 risk / vulnerability
   - M4 misinformation
4. Insert the structural question rows into `survey_question_bank`.
5. Insert multilingual text rows into `survey_question_text`:
   - English first
   - Sinhala second
   - Tamil third
6. Add `trigger_condition` rules where applicable.
7. Add `correct_answer_json` for M2 knowledge questions.
8. Mark the question rows active only after research review and translation review.

In short:

- Research team manually adds each regulation to `regulation_sector_map`
- Writes M1/M2/M3/M4 questions in EN → SI → TA
- Enters the questions into `survey_question_bank`

---

## 8. Confirmed Regulations

| Regulation           | Code  | Sectors                                                      | Change                              |
| -------------------- | ----- | ------------------------------------------------------------ | ----------------------------------- |
| VAT Restructure      | VAT   | Manufacturing, Wholesale & Retail, Services (VAT-registered) | 18%+2% SSL → 20% VAT                |
| MRP Enforcement      | MRP   | Retail, Food & Beverage, Tourism, Manufacturing              | Selling above MRP = offence         |
| EPF/ETF Update       | EPF   | All with employees                                           | Contribution rate/procedure changes |
| Annual Return Form 6 | FORM6 | All registered businesses                                    | Filing obligation update            |
| Food Safety (SLSI)   | SLSI  | Food & Beverage, Manufacturing                               | SLS certification requirement       |
| Data Protection      | DPDPA | IT-Tech, Services                                            | DPDPA compliance requirement        |

---

## 9. Session-Based API Reference

The implemented API is session-first. All survey interaction goes through six endpoints under `/api/v1/survey-sessions/`.

### 9.1 Start a session

```text
POST /api/v1/survey-sessions/start
```

Request body:

```json
{ "survey_mode": "per_module_m1" }
```

```json
{ "survey_mode": "unified" }
```

`survey_mode` must be one of: `per_module_m1`, `per_module_m2`, `per_module_m3`, `per_module_m4`, `unified`.

Response (201 Created — `SessionOut`):

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

The endpoint checks the caller's role against the `survey_limits` singleton before creating the session. If the SME has already reached their cap of completed sessions, a `403 Forbidden` is returned with `code: "forbidden"`.

### 9.2 Get next question

```text
GET /api/v1/survey-sessions/{session_id}/next-question
```

Response (`FlowNextOut`):

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
  "progress": {
    "questions_shown": 1,
    "questions_answered": 0
  },
  "status": "in_progress"
}
```

When `question` is `null` and `status` is `"completed"`, the session is exhausted.

### 9.3 Submit an answer

```text
POST /api/v1/survey-sessions/{session_id}/answer
```

Request body:

```json
{
  "question_code": "awareness.v1.q04",
  "answer_text": "yes"
}
```

Numeric or option-array answers use `answer_numeric` or `answer_options` instead.

Response (`FlowNextOut`) — same shape as §9.2; the next question (or `null`) is returned immediately.

### 9.4 Complete a session

```text
POST /api/v1/survey-sessions/{session_id}/complete
```

Response:

```json
{ "status": "completed" }
```

### 9.5 History and single-session lookup

```text
GET /api/v1/survey-sessions/my-history?page=1&size=20
GET /api/v1/survey-sessions/{session_id}
```

`my-history` returns a paginated `SessionHistoryPage` — the single source of truth for recently completed surveys, in-progress sessions, per-mode completion tracking, and session timestamps. The frontend `/surveys` hub uses this to show the in-progress banner and recent-sessions list.

---

## 10. Survey Submission Limits

### 10.1 Role-based caps

Each role has a default cap on the number of **completed** survey sessions:

| Role | Default cap | Meaning |
|---|---|---|
| `sme` | 10 | Up to 10 completed sessions total |
| `annotator` | 0 | Unlimited (0 = unlimited) |
| `admin` | 0 | Unlimited |

The cap is stored in the `survey_limits` DB singleton (§10.2) and can be changed by an admin without redeployment.

### 10.2 `survey_limits` DB singleton

```sql
CREATE TABLE survey_limits (
    id               INT PRIMARY KEY DEFAULT 1,
    sme_limit        INT NOT NULL DEFAULT 10,
    annotator_limit  INT NOT NULL DEFAULT 0,
    admin_limit      INT NOT NULL DEFAULT 0,
    updated_by       TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Always exactly one row: id = 1
INSERT INTO survey_limits (id, sme_limit, annotator_limit, admin_limit)
VALUES (1, 10, 0, 0)
ON CONFLICT DO NOTHING;
```

`0` in any limit column means **unlimited**.

### 10.3 Admin configuration

Admins configure limits at **Settings** (`/admin/settings`) in the admin UI. The page calls:

```text
GET  /api/v1/admin/survey-limits   → SurveyLimitsOut
PATCH /api/v1/admin/survey-limits  → SurveyLimitsOut
```

Both endpoints require the `admin` role.

### 10.4 Enforcement

`survey_limits_service.get_limits(db)` is called on every `POST /survey-sessions/start`. It reads the singleton row and returns defaults in memory if the table hasn't been migrated yet (`ProgrammingError` → rollback → safe defaults). The count of the caller's completed sessions is compared against the role limit; exceeding it raises `ForbiddenError`.

---

## 11. Module Number Convention

> **Callout — intentional gaps in module numbers**

The `module_number` integers stored in the DB are:

| `module_number` | Survey module | `instrument` string |
|---|---|---|
| `1` | M1 Awareness | `"awareness"` |
| `2` | M2 Knowledge | `"knowledge"` |
| `3` | M3 Vulnerability | `"vulnerability"` |
| `4` | M4 Misinformation | `"misinformation"` |

Module numbers are consecutive: 1, 2, 3, 4 — matching the M1/M2/M3/M4 display labels.

---

## 13. What Is Not Changed

This survey redesign does **not** change the downstream non-survey systems. The following remain unchanged in principle:

- ML training pipeline
- alert delivery system
- lag computation logic
- risk model
- RAG pipeline
- misinformation verifier

The survey redesign changes **how inputs are collected and grouped**, not the existence of those downstream components.
