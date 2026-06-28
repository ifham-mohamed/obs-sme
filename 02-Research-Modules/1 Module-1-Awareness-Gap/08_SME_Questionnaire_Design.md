# 08 — SME Questionnaire & Survey Design

> Goal: define exactly what data to collect from SMEs for each module, how many questions, what attributes, validation rules, and sample-size targets.

---

## 1. Overall Survey Strategy

You will run **three primary survey instruments** plus one supplementary collection method:

| Instrument | Module | Type | Length | Target N |
|------------|--------|------|--------|----------|
| Awareness Survey | 1 | Recall + channel attribution | ~15 questions | 120–200 |
| Compliance Knowledge Test | 2 | Multiple-choice with right answers | ~30–40 questions | 80–150 |
| Vulnerability Survey | 3 | Self-reported failures + profile | ~20 questions | 100–200 |
| Forwarded Message Submission | 4 | Voluntary upload of messages | open-ended | as many as possible |

All four are bundled into one **modular survey app** so that consenting SMEs can complete one or more in a single visit. Profile fields are shared across instruments — collected once, reused.

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

## 3. Module 1 — Awareness Survey (15 questions)

### Purpose
Measure when SMEs became aware of specific recent regulatory changes, and through which channels.

### Question structure
For each of **3–5 specific recent regulations** (selected by you ahead of time, with verifiable gazette dates), ask:

**Q-A1.** *"Are you aware that [specific regulation summary, e.g. 'VAT was changed to 18% effective 2024-01-01']?"*
- Yes
- No (skip remaining for this regulation)
- Not sure

**Q-A2.** *"Approximately when did you first become aware of this change?"*
- Within 1 week of the announcement
- 2–4 weeks after
- 1–3 months after
- 3–6 months after
- More than 6 months after
- I do not remember

**Q-A3.** *"How did you first learn about this change?"*
- IRD / Government website
- Government gazette
- News (newspaper, TV, online)
- My accountant
- Industry association / Chamber
- Social media (Facebook / Twitter / LinkedIn)
- WhatsApp from friend / colleague
- Penalty notice or audit
- Other (specify)

**Q-A4.** *"Did you take any action as a result of this change?"*
- Yes, immediately
- Yes, but late
- No, I did not need to
- No, but I should have
- Not sure

These four questions per regulation × 3 regulations = 12 questions. Plus 3 general questions:

**Q-A5.** *"In general, how do you usually learn about new tax / labor / business regulations?"* (multi-select)

**Q-A6.** *"On a scale of 1–5, how confident are you that you find out about regulations in time to comply?"*

**Q-A7.** *"What would help you stay better informed?"* (open text)

Total: ~15 structured items plus profile.

### Validation
- If respondent says "aware within 1 week" but the regulation was published last month, accept (recent = recent).
- If respondent says "aware within 1 week" but the regulation was published 2 years ago, recall is unreliable — flag in analysis.
- If respondent answers Q-A1 = "No" but Q-A2 with a date, contradiction — show warning, don't block.

---

## 4. Module 2 — Compliance Knowledge Test (30–40 questions)

### Purpose
Measure how accurately SMEs understand current regulatory requirements. Each question has **one verifiable right answer** based on official documents.

### Categories (allocate questions across these)
- VAT registration thresholds and rates (5 questions)
- VAT filing deadlines and procedures (5)
- EPF / ETF rates and contributions (5)
- PAYE income tax basics (4)
- WHT (withholding tax) rules (3)
- Company registration / Form 6 (3)
- Annual return obligations (3)
- Recent changes (last 12 months) (5)
- General compliance practices (4)

### Question design pattern
Each question is multiple choice with 4 options, one correct.

**Example Q-K1:** *"What is the current VAT registration threshold for businesses in Sri Lanka?"*
- A) 12 million LKR per quarter / 60 million per year ✅
- B) 15 million LKR per quarter / 60 million per year
- C) 80 million LKR per quarter
- D) Not sure / I do not know

**Critical:** Always include "Not sure / I do not know" as an option. Otherwise respondents guess and you measure nothing.

### Construction
- Take questions from official IRD / EPF / ETF / eROC documents.
- Verify each answer with a CA or tax professional.
- Pilot with 5–10 known-knowledgeable respondents — every question they get wrong is either a bad question or genuinely confusing.

### Scoring
- Per-question accuracy.
- Per-category accuracy.
- Overall **Compliance Knowledge Score** (0–100%).
- Slice by sector, region, role, language, business age.

### Length consideration
40 questions is the upper limit. Consider splitting into a "core 20" (mandatory) and "extended 20" (optional, shown only to engaged respondents).

---

## 5. Module 3 — Vulnerability Survey (20 questions)

### Purpose
Identify which SME characteristics correlate with compliance failures.

### Section A — Compliance history (8 questions)

**Q-V1.** *"In the last 24 months, have you received any of the following?"* (multi-select)
- VAT penalty notice
- EPF penalty / surcharge
- ETF penalty
- Late filing penalty
- Audit notification
- Court summons
- None of the above ✅
- Prefer not to say

**Q-V2.** *"How many penalty events of any kind in the last 24 months?"*
- 0 / 1 / 2 / 3+ / Prefer not to say

**Q-V3.** *"What was the approximate financial impact of penalties in the last 24 months?"*
- None / < 50k LKR / 50k–250k LKR / 250k–1M LKR / > 1M LKR / Prefer not to say

**Q-V4.** *"What was the most recent penalty type?"* (single choice)

**Q-V5.** *"In your opinion, what caused the penalty?"* (single choice)
- Did not know about the requirement
- Knew but missed the deadline
- Knew but disagreed with the requirement
- Filed but the calculation was wrong
- Filing system / process error
- Other (specify)

**Q-V6.** *"How often do you file your VAT returns?"*
- Monthly / Quarterly / Annually / Not registered for VAT / Other

**Q-V7.** *"Have you ever filed a return after the deadline?"*
- Never / Once or twice / Several times / Often

**Q-V8.** *"In the last 12 months, have you missed any compliance deadline you were aware of?"*
- Yes / No / Not sure

### Section B — Behavioral / capacity factors (8 questions)

**Q-V9–V12.** Frequency questions on:
- How often you check IRD website
- How often you read news on regulations
- How often you discuss compliance with your accountant
- How often you participate in industry forums

**Q-V13.** *"Do you maintain digital records for tax purposes?"* (single choice)

**Q-V14.** *"Do you use accounting software?"* (single choice)
- Yes (specify) / No / Manual ledgers / Excel only

**Q-V15.** *"Approximately what percentage of your time per month do you spend on compliance tasks?"*
- < 5% / 5–15% / 15–30% / > 30% / Prefer not to say

**Q-V16.** *"How easily can you understand official tax/labor documents in their original language?"*
- Very easily / With some effort / With great difficulty / I rely on others entirely

### Section C — Forward-looking (4 questions)

**Q-V17.** *"On a scale of 1–5, how worried are you about upcoming compliance changes?"*
**Q-V18.** *"What would reduce your compliance burden most?"* (multi-select)
**Q-V19.** *"Would you use a real-time alert system for new regulations relevant to your business?"* (Yes/No/Maybe)
**Q-V20.** *"Anything else you want to share about compliance challenges?"* (open text)

### Outcome label for Module 3 model
- The **target variable** for the risk model is constructed from Q-V1–V8.
- Define `compliance_failure = 1` if (any penalty event in last 24 months) OR (missed known deadline).
- Use the rest of the survey + profile fields as features.

---

## 6. Module 4 — Forwarded Message Submission

### Purpose
Build a corpus of compliance claims circulating informally.

### Mechanism
A simple form on the survey app:

**Field 1.** *"Please paste any message you have received about taxes, EPF, registration, or other regulations."*

**Field 2.** *"Where did you receive this message?"*
- WhatsApp group
- Direct WhatsApp
- Facebook post
- Facebook group
- Twitter / X
- Email forward
- Verbal (heard from someone)
- Other

**Field 3.** *"Roughly when did you receive it?"*
- Within last week / Last month / 1–6 months ago / Over 6 months ago / Cannot recall

**Field 4.** *"Did you act on this information?"* (Yes / No / Plan to / Decided not to)

### Privacy
- Do NOT collect sender names or phone numbers.
- Auto-strip phone numbers from pasted text (regex pre-clean).
- Inform respondent that pasted text will be reviewed for accuracy and potentially included anonymously in research.

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

Survey responses go into the schema defined in file `06`:

```
sme_profiles    ← profile fields, one row per SME
survey_responses ← one row per question answered
forwarded_messages ← one row per submitted message (Module 4 specific table)
```

Each `survey_responses` row has:
- `survey_instrument` ('awareness_v1', 'knowledge_v1', 'vulnerability_v1')
- `question_id` ('Q-A1', 'Q-K23', etc.)
- The appropriate answer field (`answer_text`, `answer_numeric`, or `answer_date`)

This long-form structure makes adding/removing questions painless — no schema changes.

---

## 13. Question ID Convention

Use a stable scheme:

```
Q-{module-letter}-{question-number}-{version}
e.g. Q-A1-v1, Q-K23-v1, Q-V7-v1
```

Where:
- A = Awareness (Module 1)
- K = Knowledge (Module 2)
- V = Vulnerability (Module 3)
- F = Forwarded message (Module 4)

If you revise a question after deployment, increment the version. This lets you analyze responses across versions correctly.

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

When you build the survey app:

```sql
INSERT INTO survey_questions (question_id, instrument, language, text, type, options_json) VALUES
  ('Q-A1-v1', 'awareness_v1', 'en', 'Are you aware that VAT was...', 'single_choice', '["Yes","No","Not sure"]'),
  ('Q-A1-v1', 'awareness_v1', 'si', 'ඔබ දැනුවත්ද ...', 'single_choice', '["ඔව්","නැත","සැක සහිතයි"]'),
  ...
```

The frontend pulls questions for the right instrument + language and renders them dynamically. This way, adding a new instrument or language requires no code changes.

---

## Summary

The survey design is **profile-shared, instrument-modular, multilingual, validated, pilot-tested, and stored in a single normalized schema**. Aim for 100+ responses per instrument minimum. Always include "I don't know" options. Always pilot. Always back-translate. Track channel of recruitment. The instruments above are sufficient to answer all four module research questions and feed labeled examples directly into the ML pipelines.
