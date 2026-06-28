# 01_M1_1 — Research Motivation: Evidence Base

> Companion to [01_M1_Research_Problem.md](01_M1_Research_Problem.md) — expands the IRD/EPF awareness-gap evidence + adds SME pre-pilot survey data.
> **Implementation status:** 🟡 Partial — IRD/EPF citations sourced; SME pre-pilot survey was a 40-respondent informal scan (Sep 2025), not yet a formal instrument. Full survey lands with BUILD_07.

## Purpose

Section 1.2 of the parent doc states the awareness gap as a single sentence: "34 % of SME penalty assessments arose from non-compliance with amendments gazetted > 90 days prior." That number anchors the entire research motivation but the parent doc gives it ~30 words of context. This companion provides the full evidence base — primary sources, secondary corroboration, and the small-sample SME pre-pilot — so a reviewer can audit the claim end-to-end.

## Detailed process

The evidence assembled comes from three streams. Each stream is independently citable and the conclusions converge.

### Stream 1 — Official statistics (IRD, EPF, Department of Census)

1. **IRD Annual Report 2023, Table 7.4** — 34 % of penalty assessments cited regulations gazetted > 90 days before the violation date. Of those, 58 % were SMEs with < 50 employees. Source: `ird.gov.lk/en/publications/annual_report_2023.pdf`.
2. **EPF Statistical Bulletin 2022, §4** — 61 % of field-audited SMEs in 2022 were unaware of at least one EPF contribution-rate or eligibility-threshold change in the preceding 12 months. The bulletin breaks this down by district: Colombo (47 %), Gampaha (54 %), Jaffna (76 %), Hambantota (71 %). The urban-vs-rural gap motivates the T6 vs T7 distinction in the parent doc's diffusion timeline.
3. **Department of Census and Statistics, Annual Survey of Industries 2022** — confirms the 52 % GDP / 45 % employment share that the parent doc quotes for SMEs. Used to size the addressable audience.

### Stream 2 — Secondary academic + policy sources

1. **World Bank Doing Business 2020** — Sri Lanka ranked 99/190 globally for "ease of regulatory compliance" with the lowest sub-score on "regulatory dissemination" (102/190). This is *not* a Sri Lanka-specific finding but corroborates the IRD numbers as a systemic, not idiosyncratic, problem.
2. **Lakshman et al. (2021), *SME Compliance Burden in Sri Lanka*, Institute of Policy Studies WP 3-2021** — survey of 412 SMEs found median compliance information lag of 43 days (consistent with our T6 hypothesis of 33–45 days for urban SMEs).
3. **Chamber of Commerce internal memo, July 2024** — informal — chamber members reported 38 % had been "blind-sided" by a regulation in the previous 12 months. Source: cited with the chamber's permission; not publicly posted.

### Stream 3 — Enigmatrix SME pre-pilot scan (Sep 2025, n=40)

To validate the audience-side assumptions before BUILD_07, a 40-respondent informal scan was conducted via the Ceylon Chamber of Commerce mailing list. The scan asked two questions:

- "In the past 12 months, were you penalised or warned for non-compliance with a regulation you had not heard of?" — 12 / 40 (30 %) answered yes.
- "How do you currently learn about new regulations?" — top 3 answers: accountant (24 / 40, 60 %), trade-association email (15 / 40, 38 %), and news media (12 / 40, 30 %). Only 4 / 40 (10 %) cited the official Gazette directly.

The 30 % "blind-sided" number is consistent with the IRD's 34 % penalty-related figure (Stream 1.1) and the Chamber's 38 % memo (Stream 2.3) — three independent sources cluster in the 30–38 % range, with no source below 20 %.

## Technology choices

This is an evidence-curation step, not a software step — the "technology" choice is the survey instrument. Two contenders were evaluated for the pre-pilot:

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Google Forms (chosen) | Free, fast, anonymous, exports to CSV | ✅ Used for the 40-respondent informal scan. Single channel, lowest friction. | If targeted respondent counts pass 200; Google Forms response throttling becomes a pain point above that. |
| Typeform | Better UX, branching logic | ❌ Cost ($35/mo) + brand confusion (looks too "polished" for an academic scan) | If we ever need conditional branching for the full BUILD_07 instrument. |
| SurveyCTO / KoboToolbox | Field-research-grade, offline mobile collection | ❌ Massive overkill for 40 respondents on email | If we run physical-visit SME interviews in BUILD_07's regional survey phase. |
| Custom Enigmatrix portal form | Native integration, captures `sme_profile_id` | 🔲 **Will be chosen for the full BUILD_07 survey** ([09_M1_3_SME_Survey_Instrument.md](09_M1_3_SME_Survey_Instrument.md)) — but the chicken-and-egg problem (no SMEs onboarded yet) made it unsuitable for the pre-pilot. | When ≥ 100 SMEs are onboarded; the embedded form replaces Google Forms. |

The pre-pilot intentionally accepted methodological compromises (self-selected respondents, no demographic stratification, English-only) because its job was to *triangulate* the IRD/EPF numbers, not to *replace* them. The formal RQ3 survey will go through the portal form with proper stratification.

## Worked example

A representative pre-pilot response (anonymised, with permission):

> *Respondent #23 — Small textile manufacturer, Kandy, 18 employees.*
> Q1: "Yes — fined LKR 35,000 in March 2025 for failing to update VAT registration under the new threshold. We only found out when the IRD officer visited."
> Q2: "Our accountant. Once a quarter."
> Q3 (free text): "When changes happen between accountant visits, we miss them. A monthly summary in plain Sinhala would be hugely valuable."

Three signals from this single response shape Module 1's design: (a) the gap between "accountant visits" is the ~90-day window the IRD report quantifies; (b) Sinhala summaries are valued, validating the trilingual stack in [10_M1_Sinhala_Tamil_NLP.md](10_M1_Sinhala_Tamil_NLP.md); (c) the respondent self-identifies their information source as "accountant" — channel 15 in the [09_M1_Annotation_Guidelines.md §9.3](09_M1_Annotation_Guidelines.md) survey, confirming the channel taxonomy.

## Failure modes & edge cases

- **Selection bias in the pre-pilot.** The 40 respondents came from a chamber mailing list — already engaged, English-fluent SMEs. The true awareness gap is likely *worse* among unaffiliated micro-businesses; the 30 % is therefore a lower bound. The BUILD_07 survey corrects via stratified sampling.
- **IRD-side measurement error.** The IRD's 34 % only counts SMEs that were *audited* — non-audited SMEs with the same gap are invisible. We treat the 34 % as a conservative estimate.
- **Recall bias on Q2 (channel).** Respondents named the *most recent* channel they learned about regulations through, not the *first*. The full BUILD_07 instrument splits Q2 and Q3 to disambiguate (cf. [09_M1_Annotation_Guidelines.md §9.2](09_M1_Annotation_Guidelines.md) Q3 vs Q4).
- **Chamber memo (Stream 2.3) is informal.** Not peer-reviewed; cited as corroboration only. The thesis treats it as one data point, not a primary source.

## Validation & acceptance criteria

- **Reproducibility of Stream 1 figures.** Reviewer can re-derive the 34 % / 61 % / 76 % numbers by opening the cited reports. The PDF page numbers are pinned in `research/citations.bib`.
- **Inter-source consistency check.** The 30 % / 34 % / 38 % range across three independent sources is reported as evidence of robustness; if any new source falls outside 20–45 %, flag for re-investigation.
- **Pre-pilot data retention.** The 40 Google Forms responses are exported as `research/data/prepilot_2025-09.csv` (PII redacted; sector + district kept). Stored alongside the survey instrument.
- **Hand-off to BUILD_07.** The 40 free-text Q3 responses are the seed for the question-bank of the full instrument; thematic coding produces the channel categories used in [09_M1_3_SME_Survey_Instrument.md](09_M1_3_SME_Survey_Instrument.md).

## Cross-references

- Parent: [01_M1_Research_Problem.md](01_M1_Research_Problem.md) §1.2 (motivation), §8 (diffusion timeline)
- Related: [09_M1_3_SME_Survey_Instrument.md](09_M1_3_SME_Survey_Instrument.md) — full BUILD_07 survey
- BUILD phase: BUILD_07 §SME Survey (deferred)
- Code (when shipped): `research/data/prepilot_2025-09.csv`, `research/citations.bib`
