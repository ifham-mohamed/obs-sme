# BUILD 16 — Progress Tracker Templates

> **Goal:** turn each BUILD/research file into living, weekly-tracked work. Copy these templates into `docs/progress/` and update them in PR review.

> **Read first:** BUILD_00 (status legend, file map), research/03_Research_Paper_Structure.md.

---

## 1. How to use

These are copy-paste markdown templates. Drop them into the repo under:

```
docs/
  progress/
    module/
      M1_awareness.md
      M2_<name>.md
      M3_<name>.md
      M4_<name>.md
    team/
      risk_register.md
      thesis_mapping.md
      submission_gate.md
    weekly/
      2026-W18_standup.md
      2026-W19_standup.md
      ...
```

**Update cadence:**

- `module/*.md` — updated by the owning team member at the end of each PR that affects that module. Reviewer must confirm the tracker line is touched before approving.
- `weekly/YYYY-Www_standup.md` — created every Monday. Filled by all four members before the supervisor meeting. Generated from the four module trackers using the prompt in Section 7.
- `team/risk_register.md` — reviewed in the weekly standup; `last-reviewed` column must be updated.
- `team/thesis_mapping.md` — frozen after Chapter 4 (Methodology) is signed off; only edited if scope changes.
- `team/submission_gate.md` — touched only in the final 4 weeks before submission.

**Status legend (defined in BUILD_00, repeated here for convenience):**

| Char | Meaning             |
|------|---------------------|
| 🔲   | Not started         |
| 🟡   | In progress         |
| 🟢   | Done / accepted     |
| 🔴   | Blocked             |
| ⚪   | Out of scope / dropped |

Use these characters verbatim in checklists — the status-generation prompts in Section 7 grep for them.

---

## 2. Module-level template

Copy the block below four times into `docs/progress/module/M{1..4}_<name>.md`. Replace the placeholders.

<details>
<summary><b>M1 — Awareness module tracker</b></summary>

```markdown
# M1 — Awareness — Progress Tracker

**Owner:** <name>
**Current status:** 🔲 / 🟡 / 🟢 / 🔴
**Week-of:** YYYY-Www
**Last updated by:** <name> in PR #<id>

## Data collection
- Target N: <e.g., 2,000 records>
- Actual N: <number>
- Source(s): <list>
- Blockers: <free text or "none">

## Annotation
- Target labeled count: <number>
- Actual labeled count: <number>
- Annotators: <names>
- IAA (Cohen κ): <value> on <date>, sample size <N>
- Label guideline version: vX.Y (link)
- Blockers: <free text>

## Model
- Target metric: <e.g., macro-F1 ≥ 0.75>
- Latest run metric: <value>
- MLflow run id: <id>
- Model version (registry): <name@version>
- Pinned config hash: <hash>
- Blockers: <free text>

## Deployment
- Endpoint live? 🔲 / 🟡 / 🟢
- URL: <https://...>
- Latency p95: <ms>
- Last smoke test: <date> — <pass/fail>

## Write-up
- Thesis chapter section drafted? <Ch.X §X.Y> — 🔲 / 🟡 / 🟢
- Word count: <n>
- Supervisor reviewed? <date or "no">
- Reviewer comments addressed? 🔲 / 🟡 / 🟢
```

</details>

<details>
<summary><b>M2 — &lt;name&gt; module tracker</b></summary>

```markdown
# M2 — <name> — Progress Tracker

**Owner:** <name>
**Current status:** 🔲 / 🟡 / 🟢 / 🔴
**Week-of:** YYYY-Www
**Last updated by:** <name> in PR #<id>

## Data collection
- Target N: <number>
- Actual N: <number>
- Source(s): <list>
- Blockers: <free text>

## Annotation
- Target labeled count: <number>
- Actual labeled count: <number>
- IAA (Cohen κ): <value> on <date>, sample size <N>
- Label guideline version: vX.Y (link)
- Blockers: <free text>

## Model
- Target metric: <metric ≥ threshold>
- Latest run metric: <value>
- MLflow run id: <id>
- Model version: <name@version>
- Blockers: <free text>

## Deployment
- Endpoint live? 🔲 / 🟡 / 🟢
- URL: <https://...>
- Latency p95: <ms>

## Write-up
- Thesis chapter section drafted? <Ch.X §X.Y> — 🔲 / 🟡 / 🟢
- Word count: <n>
- Supervisor reviewed? <date or "no">
```

</details>

<details>
<summary><b>M3 — &lt;name&gt; module tracker</b></summary>

```markdown
# M3 — <name> — Progress Tracker

**Owner:** <name>
**Current status:** 🔲 / 🟡 / 🟢 / 🔴
**Week-of:** YYYY-Www
**Last updated by:** <name> in PR #<id>

## Data collection
- Target N: <number>
- Actual N: <number>
- Blockers: <free text>

## Annotation
- Target labeled count: <number>
- Actual labeled count: <number>
- IAA (Cohen κ): <value> on <date>
- Blockers: <free text>

## Model
- Target metric: <metric ≥ threshold>
- Latest run metric: <value>
- MLflow run id: <id>
- Model version: <name@version>

## Deployment
- Endpoint live? 🔲 / 🟡 / 🟢
- URL: <https://...>
- Latency p95: <ms>

## Write-up
- Thesis chapter section drafted? <Ch.X §X.Y> — 🔲 / 🟡 / 🟢
- Word count: <n>
- Supervisor reviewed? <date or "no">
```

</details>

<details>
<summary><b>M4 — &lt;name&gt; module tracker</b></summary>

```markdown
# M4 — <name> — Progress Tracker

**Owner:** <name>
**Current status:** 🔲 / 🟡 / 🟢 / 🔴
**Week-of:** YYYY-Www
**Last updated by:** <name> in PR #<id>

## Data collection
- Target N: <number>
- Actual N: <number>
- Blockers: <free text>

## Annotation
- Target labeled count: <number>
- Actual labeled count: <number>
- IAA (Cohen κ): <value> on <date>
- Blockers: <free text>

## Model
- Target metric: <metric ≥ threshold>
- Latest run metric: <value>
- MLflow run id: <id>
- Model version: <name@version>

## Deployment
- Endpoint live? 🔲 / 🟡 / 🟢
- URL: <https://...>
- Latency p95: <ms>

## Write-up
- Thesis chapter section drafted? <Ch.X §X.Y> — 🔲 / 🟡 / 🟢
- Word count: <n>
- Supervisor reviewed? <date or "no">
```

</details>

---

## 3. Weekly standup template

Copy into `docs/progress/weekly/YYYY-Www_standup.md` every Monday.

```markdown
# Weekly standup — YYYY-Www

**Date:** YYYY-MM-DD
**Attendees:** <names>
**Supervisor present?** yes / no

## Last week — done
- M1: <bullets>
- M2: <bullets>
- M3: <bullets>
- M4: <bullets>
- Cross-cutting (infra/thesis): <bullets>

## This week — plan
- M1: <owner> — <task> — <expected status by Fri>
- M2: <owner> — <task>
- M3: <owner> — <task>
- M4: <owner> — <task>

## Blockers
- <id> — <description> — owner — needed-by date

## Risks (new or escalated)
- <id from risk register> — <change>

## Asks for supervisor
- <bullets>
```

---

## 4. Risk register template

Copy into `docs/progress/team/risk_register.md`. Pre-filled rows below cover the four open questions from BUILD_00 plus two operational risks.

| id   | description                                                                 | likelihood | impact | mitigation                                                                                          | owner    | status | last-reviewed |
|------|-----------------------------------------------------------------------------|------------|--------|-----------------------------------------------------------------------------------------------------|----------|--------|---------------|
| R-01 | OQ1 — pinned library versions drift between members                         | M          | H      | Lock `pyproject.toml` + `uv.lock`; CI fails on hash mismatch; weekly `uv sync` check                | infra    | 🟡     | YYYY-MM-DD    |
| R-02 | OQ2 — hyperparameters not reproducible across runs                          | M          | H      | All runs go through MLflow with config hash; no notebook-only training; seed pinned per BUILD_11    | M-leads  | 🟡     | YYYY-MM-DD    |
| R-03 | OQ3 — ethics approval delayed beyond data-collection start                  | M          | H      | Submit IRB form by week 3; have synthetic-data fallback for early model dev (per BUILD_12)          | PI       | 🔴     | YYYY-MM-DD    |
| R-04 | OQ4 — NEDA partnership letter not signed                                    | L          | H      | Weekly contact log; backup partner list (2 alternatives identified); no PII shared until signed     | PI       | 🟡     | YYYY-MM-DD    |
| R-05 | Annotator IAA below κ ≥ 0.6 threshold for any module                        | M          | M      | Adjudication round + label-guideline revision; budget one extra annotation week per module          | M-owners | 🔲     | YYYY-MM-DD    |
| R-06 | Deployment endpoint exceeds latency budget (p95 > 500 ms)                   | L          | M      | Quantise model; cache embeddings; fall back to batch endpoint for non-realtime UI                   | infra    | 🔲     | YYYY-MM-DD    |

Add new rows as `R-07`, `R-08`, ... — never reuse ids.

---

## 5. Thesis-chapter mapping table

Copy into `docs/progress/team/thesis_mapping.md`. Freeze after Chapter 4 sign-off. Chapter numbering follows research/03_Research_Paper_Structure.md (Extended IMRaD).

| Chapter                   | Section(s)         | Source files                                                                          |
|---------------------------|--------------------|---------------------------------------------------------------------------------------|
| Ch.1 Introduction         | §1.1–§1.4          | research/Enigmatrix_Research_Proposal_Upgraded.md (problem + RQs), BUILD_00 (open questions) |
| Ch.2 Literature Review    | §2.1–§2.5          | research/05_Literature_Review_Guide.md, research/13/14/15 (per-module references)     |
| Ch.3 Proposed Solution    | §3.1 architecture  | research/07_System_Architecture.md, BUILD_02, BUILD_03, BUILD_04                      |
| Ch.3 Proposed Solution    | §3.2 modules       | research/09–15 (per-module architecture), BUILD_07, BUILD_08, BUILD_09, BUILD_10      |
| Ch.4 Methodology          | §4.1 data          | research/06_Data_Collection_and_Management.md, research/module_*_data_architecture.md, BUILD_12 |
| Ch.4 Methodology          | §4.2 annotation    | research/11_Module1_NLP_Classifier_Training.md (§labeling), BUILD_13                  |
| Ch.4 Methodology          | §4.3 modelling     | research/02_Complete_ML_Lifecycle.md, research/11/14/15, BUILD_11                     |
| Ch.4 Methodology          | §4.4 evaluation    | research/02_Complete_ML_Lifecycle.md (§eval), BUILD_11 (§eval gates), BUILD_15 (§ML tests) |
| Ch.5 Implementation       | §5.1 backend       | BUILD_03, BUILD_04, BUILD_06                                                          |
| Ch.5 Implementation       | §5.2 frontend      | BUILD_05, BUILD_07 (UI section)                                                       |
| Ch.5 Implementation       | §5.3 ML pipeline   | BUILD_11, BUILD_12                                                                    |
| Ch.5 Implementation       | §5.4 deployment    | BUILD_13, BUILD_14, BUILD_15                                                          |
| Ch.6 Results              | §6.1–§6.4 per-module | module trackers (M1–M4), MLflow exports                                             |
| Ch.7 Discussion           | §7.1–§7.3          | research/13/14/15 (Limitations sections), supervisor review log                       |
| Ch.8 Conclusion           | §8.1–§8.3          | research/Enigmatrix_Research_Proposal_Upgraded.md (RQ recap), risk register, future work bullets |
| Appendices                | A–F                | submission_gate.md (see Section 6)                                                    |

---

## 6. Submission readiness gate

Copy into `docs/progress/team/submission_gate.md`. Touched only in the final four weeks. All boxes must be 🟢 before submission.

```markdown
# Submission readiness gate

**Submission date:** YYYY-MM-DD
**Final sign-off owner:** <PI / supervisor>

## Module acceptance criteria
- [ ] M1 acceptance criteria all 🟢 (BUILD_07)
- [ ] M2 acceptance criteria all 🟢 (BUILD_08)
- [ ] M3 acceptance criteria all 🟢 (BUILD_09)
- [ ] M4 acceptance criteria all 🟢 (BUILD_10)

## Thesis chapters
- [ ] Ch.1 Introduction frozen
- [ ] Ch.2 Literature Review frozen
- [ ] Ch.3 Proposed Solution frozen
- [ ] Ch.4 Methodology frozen
- [ ] Ch.5 Implementation frozen
- [ ] Ch.6 Results frozen
- [ ] Ch.7 Discussion frozen
- [ ] Ch.8 Conclusion frozen
- [ ] Abstract finalised
- [ ] References de-duplicated and formatted

## Ethics & partnerships
- [ ] IRB / ethics approval letter filed in `docs/ethics/`
- [ ] NEDA partnership MoU signed and filed
- [ ] Participant consent forms archived

## Appendices compiled
- [ ] Appendix A — Survey instruments
- [ ] Appendix B — Annotation guidelines (final version)
- [ ] Appendix C — Database schema (frozen)
- [ ] Appendix D — API endpoint reference
- [ ] Appendix E — Hyperparameters & config hashes per module
- [ ] Appendix F — MLflow run table (model card per module)

## Demo
- [ ] End-to-end demo script written
- [ ] Demo recorded (mp4, 5–10 min) and stored in `docs/demo/`
- [ ] Demo URL listed in README

## Final checks
- [ ] CI green on `main` for 3 consecutive days
- [ ] All endpoints responding under SLO
- [ ] Repo tag `v1.0-submission` created
```

---

## 7. Claude Prompts (status generation)

### Prompt 1 — Generate this week's standup from the four module trackers

```
You are given four markdown files: M1_awareness.md, M2_*.md, M3_*.md, M4_*.md
from docs/progress/module/.

Produce a single weekly standup file conforming to the template in
BUILD_16 §3. Rules:

1. Group "Last week — done" by module. Pull bullets from each module
   tracker's "Current status" line plus any items that flipped from 🟡 to 🟢
   since the previous weekly file (diff against docs/progress/weekly/<prev>).
2. "This week — plan" — pull from each module's "Blockers" + open 🔲 items
   in the same file, one bullet per module.
3. "Blockers" — every 🔴 status across all four files, plus any "Blockers:"
   line whose value is not "none".
4. "Risks" — list any risk-register row whose status changed in the last 7
   days (compare last-reviewed column).
5. Output a single markdown file named docs/progress/weekly/<YYYY-Www>_standup.md.
   Do not invent data; if a field is empty in the source, write "TBD".
```

### Prompt 2 — Generate the supervisor-review summary from BUILD/research file checkboxes

```
You are given all files under docs/BUILD_PLAN/ and docs/research/.

For each file:
1. Locate the "## Acceptance Criteria" H2 block (skip files that do not have one,
   e.g., BUILD_00, BUILD_16, BUILD_17).
2. Count checklist items by status using the legend chars 🔲 🟡 🟢 🔴 ⚪.
3. Emit one row in a markdown table with columns:
   file | done (🟢) | in-progress (🟡) | blocked (🔴) | not-started (🔲) | dropped (⚪) | % complete

Then produce a "Highlights" section listing:
- All 🔴 items verbatim with their file path and line number.
- Files where % complete dropped vs the previous run (compare against the
  most recent docs/progress/weekly/*_supervisor_summary.md).

Write output to docs/progress/weekly/<YYYY-Www>_supervisor_summary.md.
Do not modify any source file.
```

---

**Prev:** BUILD_15_Observability_Testing.md  ·  **Next:** BUILD_17_Claude_Prompts_Library.md
