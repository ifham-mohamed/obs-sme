# 09_M1_3 — SME Survey Instrument

> Companion to [09_M1_Annotation_Guidelines.md](09_M1_Annotation_Guidelines.md) — extracts the full Q1–Q8 survey from parent §9 and expands the operational delivery + response-tracking schema.
> **Implementation status:** 🔲 Deferred (BUILD_07 — survey is portal-embedded, distributed through partner networks)

## Purpose

Parent doc §9 contains the full Q1–Q8 instrument inline. This companion is the operational accompaniment: the per-sector tailoring SQL (which gets the same treatment in parent §9.5), the delivery mechanism (portal embed vs partner email), the response-tracking schema, and the rules for what counts as a "valid" response.

## Detailed process

### Step 1 — Recruitment funnel

Three channels seed respondents into the survey:

| Channel | Volume estimate (BUILD_07 target) | Per-respondent cost | Bias risk |
|---|---|---|---|
| Enigmatrix portal embed | ~60 % of total (active platform users) | Free | Self-selection — opt-in to the platform |
| NEDA / Chamber partner email | ~30 % | Free (partner provides list) | List bias — toward members + active SMEs |
| Snowball / referral | ~10 % | Free | Familiarity bias — limited |

Target: 100 + responses across all 10 sectors with ≥ 10 / sector.

### Step 2 — Per-sector regulation selection

Each respondent sees 7 sector-tailored regulations + 2 universal (IRD + EPF). The full SQL is in parent doc §9.5. The query is parameterised on `respondent_sector` from `sme_profiles`. The 7 regulations are the most recent for that sector with `needs_review=false`.

### Step 3 — Response delivery flow

```
Respondent lands on /portal/m1/survey
   ↓
Server fetches 9-regulation list via parent §9.5 SQL
   ↓
Render: 1 introduction block + 9 per-regulation blocks (Q1–Q7) + 1 open block (Q8)
   ↓
Respondent submits → POST /api/v1/m1/survey-responses
   ↓
Server validates consent_acknowledged_at; rejects without
   ↓
Per-regulation answers → m1_sme_awareness_responses (9 rows)
Q8 free-text → m1_survey_qualitative_responses (1 row)
sme_profiles.survey_completed_at updated
   ↓
Confirmation email + small thank-you (a 1-page personalised regulatory summary PDF)
```

### Step 4 — Response validation rules

| Rule | Triggers | Action |
|---|---|---|
| Consent missing | `consent_acknowledged_at IS NULL` | Reject submission with 422 |
| < 7 of 9 regulation blocks answered | partial submission | Save what's there; flag `is_partial=true` |
| Q2 awareness_date > today | future date | Treat as `NULL`; flag for review |
| Q2 awareness_date < gazette_published_date | impossible | Treat as `NULL`; flag for review |
| Same SME submits twice | unique constraint on (sme_profile_id) | First submission wins; second goes to `m1_survey_re_submissions` for separate analysis |

### Step 5 — Response-tracking schema

Two tables, with the same shape as the Session-14 audit pattern:

```sql
CREATE TABLE m1_survey_attempts (
    attempt_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sme_profile_id    UUID NOT NULL REFERENCES sme_profiles(id),
    started_at        TIMESTAMPTZ NOT NULL,
    submitted_at      TIMESTAMPTZ,                          -- NULL = abandoned
    consent_at        TIMESTAMPTZ,
    n_regulations_answered SMALLINT,
    is_partial        BOOLEAN GENERATED ALWAYS AS (n_regulations_answered < 9) STORED,
    user_agent        TEXT,
    referrer_channel  TEXT                                  -- 'portal'|'neda'|'chamber'|'snowball'
);

CREATE TABLE m1_survey_qualitative_responses (
    response_id       UUID PRIMARY KEY,
    sme_profile_id    UUID NOT NULL,
    q8_text           TEXT,
    submitted_at      TIMESTAMPTZ NOT NULL
);
```

The `m1_sme_awareness_responses` rows from parent §2.4 carry the quantitative Q1–Q7 data.

### Step 6 — Q8 thematic coding (qualitative)

Q8 ("What single change to how the government communicates regulations would most help your business?") is open-text. Coded post-hoc via thematic analysis:

1. Two researchers each independently code the first 30 responses into emergent themes.
2. Themes consolidated; codebook frozen.
3. Both researchers re-code all responses against the codebook.
4. IAA on themes (Cohen's κ) ≥ 0.70 acceptable.

Themes feed the thesis discussion + policy recommendations.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Portal-embedded form (chosen) | Native integration; auto-fill from `sme_profiles` | ✅ Lowest friction; best response quality | If portal adoption stays below 100 SMEs at month 6, supplement with Typeform. |
| Google Forms / Typeform | Easy to start | ❌ Loses `sme_profile_id` linkage → can't disaggregate F3 by district | Only for pre-pilot (already done in [01_M1_1_Research_Motivation_Evidence.md](01_M1_1_Research_Motivation_Evidence.md)). |
| Paper / phone | Maximum reach | ❌ 10× the cost per response, no auto-validation | Never. |
| Per-respondent thank-you PDF | Boosts completion rate | ✅ Pre-pilot showed 18 → 32 % completion lift with personalised PDF reward | If completion rates collapse, add more incentive. |

## Worked example

A typical respondent flow:

```
[Day 0 09:14] respondent (sme_alpha, manufacturing, Kandy) lands on /portal/m1/survey
[Day 0 09:14] server retrieves 7 manufacturing regulations + 2 universal = 9
[Day 0 09:14] m1_survey_attempts row inserted (started_at=09:14)
[Day 0 09:24] respondent submits — 9 regulations answered, Q8 filled (n=180 chars)
[Day 0 09:24] server validates consent; OK
[Day 0 09:24] writes:
                  9 rows in m1_sme_awareness_responses
                  1 row in m1_survey_qualitative_responses
                  m1_survey_attempts.submitted_at = 09:24
[Day 0 09:25] thank-you email sent with attached PDF
```

The submission takes ~10 minutes — short enough that the abandonment rate stays low (target: < 30 %).

## Failure modes & edge cases

- **Respondent abandons mid-survey.** Partial submission saved; `is_partial=true`. Excluded from F3/F4 but included in F6 ITT analysis.
- **Repeat respondent (different account).** Detected by IP + behavioral fingerprint; flagged for review. Treated as separate respondent unless evidence of fraud.
- **Consent withdrawn after submission.** Right-of-erasure (see [02_M1_3_Data_Governance_Retention.md](02_M1_3_Data_Governance_Retention.md)) anonymises the rows but keeps the aggregate research signal.
- **Q3 channel selection conflicts with Q4 confidence.** Some respondents pick 5+ channels with high confidence; others pick 1 with low. Both are valid; downstream coding handles the variance.

## Validation & acceptance criteria

- **Survey instrument identical to parent doc §9.** No drift between the parent doc and what the portal renders (CI test on the rendered form).
- **Per-sector quota.** ≥ 10 respondents in each of the 10 sectors before F4 is reported.
- **Q8 thematic IAA.** κ ≥ 0.70 between the two coders on the final coding pass.
- **Completion rate.** ≥ 30 % of survey-started respondents complete all 9 regulations. If below, audit drop-off page (which Q is the abandonment point).

## Cross-references

- Parent: [09_M1_Annotation_Guidelines.md §9](09_M1_Annotation_Guidelines.md)
- Related: [01_M1_1_Research_Motivation_Evidence.md](01_M1_1_Research_Motivation_Evidence.md) (pre-pilot scan), [08_M1_1_Research_Findings_Extraction.md](08_M1_1_Research_Findings_Extraction.md) (F3, F4, F6 use this data)
- BUILD phase: BUILD_07 §survey portal
- Code (when shipped): `backend/app/api/v1/m1_survey.py`, frontend `app/(portal)/portal/m1/survey/page.tsx`, `m1_survey_attempts` + `m1_survey_qualitative_responses` tables
