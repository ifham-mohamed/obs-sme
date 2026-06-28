# 08_M1_1 — Research Findings Extraction (F1–F6)

> Companion to [08_M1_Full_System_Architecture.md](08_M1_Full_System_Architecture.md) — for each of F1–F6: data source, sample-size requirement, statistical test, SQL queries, expected effect sizes, notebook scaffold.
> **Implementation status:** 🟡 Notebook scaffolds in `research/notebooks/` exist; population happens during BUILD_07/11 once data flows.

## Purpose

Parent doc §10 lists the six findings in a table. This companion turns each into an *executable plan*: the SQL that produces the input, the statistical test that's run on it, and the expected number of significant figures the thesis claims.

## Detailed process

For each finding the structure is identical:

- **Data source.** Postgres table(s) + filter.
- **Sample-size requirement.** Minimum N for statistical defensibility.
- **Statistical test.** Specific test + significance level.
- **Expected effect size.** A priori hypothesis from the pilot scan.
- **Notebook step.** Which cell in which research notebook computes it.

### F1 — Median lag: gazette → official portal

- **Data source.** `m1_propagation_events` rows where `channel LIKE 'portal_%'`, JOINED with `m1_regulations.gazette_published_date`.
- **Sample size.** ≥ 200 regulations × ≥ 1 portal event each. Confidence interval on median requires N ≥ 30 for normal-approximation; we target 200 for robustness across 6 portals.
- **Statistical test.** Median + bootstrap 95 % CI (10 k iterations). Optional: Mann-Whitney U if comparing two portal subsets (IRD vs CBSL).
- **Expected effect.** Median ≈ 7 days (range 3–14 across portals).
- **Notebook.** `findings_lag_analysis.ipynb`, cell 3.

```sql
SELECT
  pe.channel,
  pe.first_seen_at - r.gazette_published_date::TIMESTAMPTZ AS lag_interval
FROM m1_propagation_events pe
JOIN m1_regulations r ON r.id = pe.regulation_id
WHERE pe.channel LIKE 'portal_%'
  AND pe.is_confirmed = TRUE
  AND r.gazette_published_date IS NOT NULL;
```

### F2 — Median lag: gazette → news first mention

- **Data source.** `m1_propagation_events` rows where `channel LIKE 'news_%'` plus the RSS publish-delay calibration from `m1_sources.publish_delay_p50_minutes`.
- **Sample size.** ≥ 200 regulations × ≥ 1 news mention.
- **Statistical test.** Median + bootstrap CI; with `publish_delay_p50` subtracted from each row's lag to estimate true publication time.
- **Expected effect.** Median ≈ 23 days, IQR 14–35.
- **Notebook.** `findings_lag_analysis.ipynb`, cell 4.
- **Caveat.** The `publish_delay` adjustment is documented in [08_M1_Full_System_Architecture.md §10](08_M1_Full_System_Architecture.md). The thesis reports both raw and adjusted medians.

### F3 — Median lag: gazette → SME first awareness

- **Data source.** `m1_sme_awareness_responses.awareness_date` minus `m1_regulations.gazette_published_date`.
- **Sample size.** ≥ 100 SME respondents × ≥ 200 regulations (= sufficient for sub-group analysis by district).
- **Statistical test.** Mann-Whitney U (urban vs rural districts); Kruskal-Wallis if > 2 groups.
- **Expected effect.** Median urban ≈ 33 days, rural ≈ 58 days; p < 0.05 on the urban-vs-rural difference.
- **Notebook.** `findings_lag_analysis.ipynb`, cell 5–6.

```sql
SELECT
  s.district_classification,                                -- urban / peri-urban / rural
  r.id AS regulation_id,
  a.awareness_date - r.gazette_published_date AS lag_days
FROM m1_sme_awareness_responses a
JOIN m1_regulations r        ON r.id = a.regulation_id
JOIN sme_profiles s          ON s.id = a.sme_profile_id
WHERE a.awareness_date IS NOT NULL;
```

### F4 — Channel effectiveness (sector lag variance)

- **Data source.** `v_m1_channel_effectiveness` (parent doc §2 + view in [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md)).
- **Sample size.** ≥ 10 SMEs per sector to enable per-sector ranking.
- **Statistical test.** One-way ANOVA / Kruskal-Wallis (10 sectors); Dunn post-hoc for pairwise differences.
- **Expected effect.** At least one sector pair differs at p < 0.05; "government_sms" + "enigmatrix_alert" rank fastest; "peer" slowest.
- **Notebook.** `findings_secondary_diffusion.ipynb`, cell 2.

### F5 — Language lag (EN vs SI vs TA)

- **Data source.** F3 disaggregated by `m1_regulations.primary_language`.
- **Sample size.** ≥ 30 respondents reading each of EN / SI / TA.
- **Statistical test.** Kruskal-Wallis (3 groups, non-parametric).
- **Expected effect.** SI and TA lags > EN by ≥ 5 days; p < 0.05.
- **Notebook.** `findings_lag_analysis.ipynb`, cell 7.

### F6 — Alert system effectiveness (DiD)

- **Data source.** F3 split on `sme_profiles.is_subscribed_to_alerts`.
- **Sample size.** ≥ 30 subscribed + ≥ 30 non-subscribed respondents.
- **Statistical test.** Difference-in-Differences regression on `lag_days ~ subscribed + is_post_alert_intervention + subscribed*is_post`, controlling for sector + district.
- **Expected effect.** Subscribed SMEs: ≤ 1 day lag post-deployment; non-subscribed: 33–58 days. DiD estimate ≈ −30 days, p < 0.01.
- **Notebook.** `findings_alert_effectiveness.ipynb`, cell 4–6.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Bootstrap CI (chosen) | Distribution-free | ✅ Robust for skewed lag distributions | If distributions look Gaussian (unlikely). |
| Mann-Whitney U (chosen for 2-group) | Non-parametric, no normality assumption | ✅ Lag data is heavy-tailed; t-test would be wrong | Never use t-test on these. |
| Kruskal-Wallis (chosen for 3+ group) | Non-parametric ANOVA-equivalent | ✅ Same reasoning | Never. |
| DiD regression for F6 | Standard causal-inference workhorse | ✅ The pre/post + subscribed/not split is textbook DiD | If we get enough data for an RDD or RCT — both stronger. |
| Frequentist (chosen) | Standard in academic publishing | ✅ Aligns with reviewer expectations | If Bayesian (`pymc`) is requested. |

## Worked example

Pseudo-output of F3 cell after BUILD_07:

```
F3 — SME awareness lag (n_respondents=112, n_regulations=237):
  Median urban (n=68):  31.2 days (95% bootstrap CI: 27.8 – 35.1)
  Median rural (n=44):  56.7 days (95% bootstrap CI: 49.3 – 63.4)
  Mann-Whitney U: 11,532  p < 0.001
  Effect size r:  0.42 (medium-to-large)

Caveat: 7 respondents have awareness_date=NULL ("don't remember") — excluded
from this analysis but included in F6 ITT analysis.
```

The number is reported in the thesis as: "SMEs in urban districts learn of new regulations a median of 31 days after publication; SMEs in rural districts a median of 57 days (Mann-Whitney U=11,532, p<0.001)."

## Failure modes & edge cases

- **Insufficient sample per cell.** If F4 has < 10 respondents in a sector, that sector is reported as "insufficient data" rather than aggregated into a misleading median.
- **Survey self-selection bias.** Respondents are self-selected (opted into the Enigmatrix portal). This is a sampling caveat reported in thesis limitations; the BUILD_07 plan offsets via partner outreach (NEDA, Chamber).
- **F6 DiD assumption violation.** If subscribed and non-subscribed groups have different pre-intervention trends, DiD is biased. Mitigation: plot pre-intervention parallel-trends figure as a robustness check.
- **F1/F2 missing portal data.** Some regulations are never re-posted to portals (sector-specific gazettes the IRD doesn't cover). These contribute to F1 with `lag_days = NULL`; downstream median ignores them.

## Validation & acceptance criteria

- **All 6 cells run end-to-end** on the production replica.
- **CIs computed** for every median; effect sizes for every test.
- **Pre-registration document** (`research/preregistration.md`) lists the hypotheses + tests *before* data unblinding.
- **Sensitivity analyses** documented per F4/F5/F6 (remove extreme respondents; recompute).

## Cross-references

- Parent: [08_M1_Full_System_Architecture.md](08_M1_Full_System_Architecture.md) §10, §11
- Related: [02_M1_Data_Requirements.md §3.3](02_M1_Data_Requirements.md) (`v_m1_*` views), [09_M1_3_SME_Survey_Instrument.md](09_M1_3_SME_Survey_Instrument.md)
- BUILD phase: BUILD_07 §research notebooks
- Code (when shipped): `research/notebooks/findings_*.ipynb`
