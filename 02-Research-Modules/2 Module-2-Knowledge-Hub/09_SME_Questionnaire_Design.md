# 08 — SME Questionnaire & Survey Design

> Goal: define exactly what data to collect from SMEs for each module, how many questions, what attributes, validation rules, and sample-size targets.

---

## 1. Overall Survey Strategy

You will run **five survey modes** built on one shared question bank:

| Mode | Modules covered | Length | Organizing rule |
|---|---|---|---|
| Module 1 survey | M1 only | 8–10 questions | sector-filtered subset of awareness questions |
| Module 2 survey | M2 only | 8–10 questions | sector-filtered subset of knowledge questions |
| Module 3 survey | M3 only | 8–10 questions | sector-filtered subset of risk questions |
| Module 4 survey | M4 only | 8–10 questions | sector-filtered subset of misinformation questions |
| Unified survey | M1 + M2 + M3 + M4 | 15–20 questions total | regulation blocks shown in sequence |

The **regulation block model** is the core organizing principle:

1. Each regulation contributes one block.
2. Each block contains one M1, one M2, one M3, and one M4 question sequence.
3. The SME's sector determines which blocks are included.
4. Blocks do not branch into each other.
5. Every survey run is grouped under `survey_sessions`.

This replaces the earlier design where awareness, knowledge, vulnerability, and forwarded-message collection were treated as four largely separate instruments.

---

## 2. Shared SME Profile Fields (collected once)

These attributes appear in every survey because every analysis joins on them.

| Attribute | Type | Options / format | Why |
|-----------|------|------------------|-----|
| Sector | Single-choice | Manufacturing / Wholesale & Retail / Services / Tourism / Agriculture / Construction / IT-Tech / Other | Slice variable for all analyses |
| Sub-sector | Single-choice (depends on sector) | Conditional list | Finer-grained sector |
| Employee count band | Single-choice | 1–5 / 6–10 / 11–25 / 26–50 / 51–100 / 101–250 | SME size definition (avoids exact count) |
| Annual turnover band | Single-choice | < 5 M LKR / 5–15 M / 15–50 M / 50–250 M / > 250 M / Prefer not to say | Size correlate; banded for privacy |
| Business age (years) | Numeric | 0 to 100 | Older businesses likely more aware |
| Region (province) | Single-choice | All 9 provinces | Geographic slice |
| District | Single-choice (depends on province) | Conditional list | Finer geographic |
| Urban / rural | Single-choice | Urban / Semi-urban / Rural | Information access correlate |
| Primary business language | Single-choice | Sinhala / Tamil / English / Mixed | Survey routing + analysis |
| Respondent role | Single-choice | Owner / Co-owner / Finance staff / Accountant / Manager / Other | Role-based knowledge difference |
| Years in current role | Numeric | 0 to 60 | Knowledge proxy |
| Educational qualification | Single-choice | O-Level / A-Level / Diploma / Degree / Postgrad / Prefer not | Knowledge / digital literacy proxy |
| Has external accountant | Yes/No | | Channel for compliance information |
| Has digital tools | Multi-select | None / Bank app / IRD e-filing / Accounting software / WhatsApp Business / Other | Digital presence indicator |

These ~14 fields take 3 minutes to fill and unlock all the slicing analyses you need.

---

## 3. Module 1 — Awareness Questions Inside Regulation Blocks

### Purpose

Module 1 remains the awareness layer, but it now lives inside regulation blocks rather than as a standalone survey design pattern.

### VAT block example

**Q-A-VAT-1-v1**  
*"Were you aware that the 18% VAT plus 2% SSCL structure was consolidated into a single 20% VAT arrangement?"*

- Yes
- No
- Not sure

Trigger condition:

```json
null
```

### MRP block example

**Q-A-MRP-1-v1**  
*"Were you aware that selling selected goods above the marked retail price is an enforceable offence?"*

- Yes
- No
- Not sure

Trigger condition:

```json
null
```

### Design rule

- M1 is the opening question for a regulation block.
- A "No" answer does **not** skip the rest of the regulation.
- Instead, M2 and M3 remain in the block and are used to distinguish lack of awareness from lack of knowledge and downstream compliance risk.

---

## 4. Module 2 — Knowledge Questions Inside Regulation Blocks

### Purpose

Module 2 tests whether the SME knows the current operational rule tied to the same regulation block.

### VAT block example

**Q-K-VAT-1-v1**  
*"Under the restructured VAT regime, what is the currently applicable VAT rate?"*

- A) 15%
- B) 18%
- C) 20% ✅
- D) Not sure / I do not know

Trigger condition:

```json
null
```

### MRP block example

**Q-K-MRP-1-v1**  
*"If a regulated item has a printed MRP, which statement is correct?"*

- A) The MRP is only advisory
- B) The seller may exceed the MRP if costs increased
- C) Selling above MRP may constitute an offence ✅
- D) Not sure / I do not know

Trigger condition:

```json
null
```

### Design rule

- Module 2 questions always include a "Not sure / I do not know" option.
- The M2 result sets the block-level knowledge flag:
  - correct → `knowledge = accurate`
  - wrong / not sure → `knowledge = gap_detected`
- The M2 result influences M3 severity in the same regulation block.

---

## 5. Module 3 — Vulnerability / Risk Questions Inside Regulation Blocks

### Purpose

Module 3 measures whether the SME has already experienced, or is likely to experience, compliance difficulty related to the same regulation.

### VAT block example

**Q-V-VAT-1-v1**  
*"In the last 24 months, have you received any VAT-related penalty, surcharge, or late-filing notice?"*

- Yes
- No
- Not sure

Normal trigger condition:

```json
{"depends_on": "Q-K-VAT-1-v1", "is_correct": true, "severity": "normal"}
```

Higher-severity variant:

```json
{"depends_on": "Q-K-VAT-1-v1", "is_correct": false, "severity": "high"}
```

### MRP block example

**Q-V-MRP-1-v1**  
*"Have you ever received a warning, complaint, or inspection related to pricing above the marked retail price?"*

- Yes
- No
- Not sure

Higher-severity variant trigger:

```json
{"depends_on": "Q-K-MRP-1-v1", "is_correct": false, "severity": "high"}
```

### Design rule

- M3 stays within the same regulation block.
- M3 does not jump into a different regulation's questions.
- A wrong M2 answer does not suppress M3; it escalates it.

---

## 6. Module 4 — Misinformation Questions Inside Regulation Blocks

### Purpose

Module 4 captures whether the SME is exposed to informal or misleading information about the same regulation.

### VAT block example

**Q-F-VAT-1-v1**  
*"Have you received messages or informal advice claiming a different VAT rule than the current official position?"*

- Yes
- No
- Not sure

Trigger condition:

```json
{"sector_in": ["manufacturing", "wholesale_retail", "services"]}
```

### MRP block example

**Q-F-MRP-1-v1**  
*"Have you seen or received messages saying sellers are allowed to exceed MRP under current market conditions?"*

- Yes
- No
- Not sure

Trigger condition:

```json
{"sector_in": ["retail", "food_beverage", "tourism", "manufacturing"]}
```

### Design rule

- M4 remains part of the regulation block model even if evidence-intake workflows also exist elsewhere in the platform.
- In unified mode, M4 follows M3 for that regulation.
- In module-only mode, the SME sees only the M4 subset relevant to their sector.

---

## 7. Sample Size Targets

| Module | Minimum N for credible analysis | Stretch goal | Rationale |
|--------|--------------------------------|---------------|-----------|
| Awareness Survey | 100 | 200+ | 95% CI on lag percentile estimates; sufficient for sector slicing |
| Knowledge Test | 80 | 150+ | Per-question accuracy needs ~80 responses for tight CI |
| Vulnerability Survey | 100 | 200+ | Need positive class (penalized SMEs) ≥ 30 for ML training |
| Forwarded Messages | 50+ unique items | 200+ | Annotation-ready corpus |

If you cannot reach minimum N, **be honest in limitations** and use the sample as exploratory rather than confirmatory. A small sample with rigorous analysis is far better than a large sample with sloppy analysis.

---

## 8. Sampling Strategy

### Channels (mix to reduce bias)
1. **Industry chambers / NEDA** — formal, gives legitimacy.
2. **LinkedIn ads / posts** — broad, biased toward digitally active.
3. **WhatsApp groups** (industry-specific) — high response rate.
4. **In-person at industrial zones** (Katunayake, Biyagama) — high quality, time-intensive.
5. **Snowball** — respondents share with peers.

### Stratification
Aim for representation across:
- 3+ sectors (don't oversample IT; SMEs are predominantly retail/services)
- 3+ regions (Western, North-Central, Southern)
- 3+ size bands

Track which channel each response came from. Report channel breakdown in your thesis.

---

## 9. Validation Logic

Build into the survey app:

| Rule | Action on violation |
|------|--------------------|
| Required field empty | Block submission, show clear error in respondent's language |
| Numeric out of plausible range | Soft warning, allow override |
| Date in the future for past event | Hard block |
| Internal contradiction (e.g. "no penalties" + "penalty amount > 0") | Soft warning, ask to confirm |
| Respondent finishes in < 90 seconds | Flag as potential straight-lining; review carefully |
| Same IP submits twice within an hour | Soft duplicate warning |

---

## 10. Multilingual Equivalence

Do not just translate — **back-translate** to verify equivalence:

1. Author writes English version.
2. Native Sinhala speaker translates to Sinhala.
3. Different native speaker back-translates Sinhala → English.
4. Compare back-translation to original. Discrepancies → revise.
5. Repeat for Tamil.

Document this process in your methodology.

---

## 11. Pilot Then Deploy

| Phase | N | Goal | Duration |
|-------|---|------|----------|
| Pilot 1 (cognitive) | 5 | Watch them fill it out, find confusion | 1 week |
| Pilot 2 (full deploy small) | 20 | Find systemic issues in flow / channels | 1 week |
| Full deploy | 100+ | Real data collection | 4–6 weeks |
| Top-up | as needed | Reach minimum N per slice | 2 weeks |

---

## 12. Database Schema Mapping

Survey data is now grouped first by `survey_sessions`, then by `survey_responses`.

```text
sme_profiles          <- shared SME profile fields
survey_sessions       <- one row per SME survey run
survey_responses      <- one row per answered question within a session
survey_question_bank  <- question structure, routing, and scoring metadata
survey_question_text  <- EN / SI / TA question text
regulation_sector_map <- which sectors should see which regulation blocks
```

Each `survey_responses` row should carry:

- `session_id`
- `regulation_id`
- `module_number`
- `survey_mode`
- `question_id`
- the appropriate answer field (`answer_text`, `answer_numeric`, or `answer_date`)

This preserves a long-form answer store while making the session the top-level grouping unit per survey run.

---

## 13. Question ID Convention

Use the new stable scheme:

```text
Q-{M}-{REG}-{N}-{v}
```

Examples:

```text
Q-A-VAT-1-v1
Q-K-MRP-2-v1
Q-V-EPF-1-v1
Q-F-DPDPA-1-v1
```

Where:

- `A` = Awareness
- `K` = Knowledge
- `V` = Vulnerability / Risk
- `F` = Forwarded / Misinformation

Legacy note:

- Existing historical data may still use formats such as `awareness.v1.q01`.
- Old format remains valid for legacy rows.
- Newly authored questions use the new format only.

---

## 14. Common Survey Design Mistakes

| Mistake | Fix |
|---------|-----|
| Asking exact penalty amounts | Use bands |
| No "I don't know" option | Always include — measure non-knowledge |
| Leading questions ("Don't you agree...") | Neutral phrasing |
| Double-barreled questions ("Are you aware AND have you complied?") | Split into two questions |
| Long open-text fields as required | Make optional; offer Likert + optional comment |
| All questions on one page | Split into 3–5 pages with progress bar |
| No save-and-resume | Implement; abandonment drops 30% |

---

## 15. Question Bank — Putting It All Together

When you build the survey app, the target-state SQL pattern looks like this:

```sql
INSERT INTO survey_sessions (
    session_id,
    sme_id,
    survey_mode,
    status,
    question_cap
) VALUES (
    gen_random_uuid(),
    '<sme-uuid>',
    'unified',
    'in_progress',
    20
);

INSERT INTO regulation_sector_map (
    regulation_id,
    sector_code,
    impact_level
) VALUES
    ('<vat-uuid>', 'manufacturing', 'primary'),
    ('<vat-uuid>', 'wholesale_retail', 'primary'),
    ('<mrp-uuid>', 'retail', 'primary');

INSERT INTO survey_question_bank (
    question_id,
    regulation_id,
    module_number,
    question_order,
    version,
    question_type,
    trigger_condition,
    answer_options,
    correct_answer_json,
    is_active
) VALUES
    (
        'Q-A-VAT-1-v1',
        '<vat-uuid>',
        1,
        1,
        'v1',
        'single_choice',
        NULL,
        '["yes","no","not_sure"]'::jsonb,
        NULL,
        TRUE
    ),
    (
        'Q-K-VAT-1-v1',
        '<vat-uuid>',
        2,
        2,
        'v1',
        'single_choice',
        NULL,
        '["15%","18%","20%","not_sure"]'::jsonb,
        '{"correct":"20%"}'::jsonb,
        TRUE
    );

INSERT INTO survey_question_text (
    question_id,
    lang_code,
    question_text
) VALUES
    ('Q-A-VAT-1-v1', 'en', 'Were you aware that VAT was restructured into a single 20% VAT arrangement?'),
    ('Q-A-VAT-1-v1', 'si', 'වැට් බදු පද්ධතිය තනි 20% වැට් ආකෘතියකට යාවත්කාලීන කළ බව ඔබ දැන සිටියාද?'),
    ('Q-A-VAT-1-v1', 'ta', 'VAT ஒரு 20% ஒற்றை அமைப்பாக மாற்றப்பட்டதை நீங்கள் அறிந்தீர்களா?');
```

The frontend then renders module-specific or unified flows from the same shared bank and session model.

---

## Summary

The survey design is now **session-grouped, regulation-block-driven, multilingual, validated, and based on one shared question bank**. The SME profile remains shared. The major structural change is that every question now belongs to a regulation block and every run belongs to `survey_sessions`, allowing both per-module and unified survey experiences without splitting the schema into separate survey systems.
