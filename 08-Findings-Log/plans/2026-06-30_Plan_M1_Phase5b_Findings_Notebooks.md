---
tags: [m1, phase-5, plan, findings, notebooks, statistics, thesis]
date: 2026-06-30
author: Mohamed M.R.I (215075J) — Module 1 owner
session: 69
status: 🟡 in-execution — notebooks + helpers scaffolded this session (Session 69)
features: F-237 (findings_common + preregistration) · F-238 (4 findings notebooks)
---

# M1 Phase 5b — F1–F6 findings notebooks

> **Goal (roadmap Phase 5, Step 5b):** four `research/notebooks/findings_*.ipynb` that compute the empirical findings F1–F6 — each with a **median + bootstrap 95% CI** and the appropriate **statistical test** — the thesis contribution answering RQ1/RQ3/RQ4.
>
> **Why:** the platform is the research vehicle; these notebooks turn the Phase-4 lag data + the survey + the classifier metrics into defensible findings. **Preregistration first** (fix hypotheses + tests before unblinding).

## Findings ↔ source ↔ test
| # | Finding | Source (built) | Test |
|---|---|---|---|
| F1 | Median lag gazette → official portal | `v_m1_regulation_lag_summary.portal_lag_days` (4a/4c) | median + bootstrap CI |
| F2 | Median lag gazette → news | `…news_lag_days` | median + bootstrap CI |
| F3 | SME awareness lag by urban/rural + sector | `m1_sme_awareness_responses` (survey, 5a) | Mann-Whitney U (urban vs rural) |
| F4 | Channel effectiveness (median lag ranked) + sector variance | `v_m1_channel_effectiveness` (4c) | Kruskal–Wallis |
| F5 | Language lag differential (EN vs SI vs TA) | F3 disaggregated by `language` | Kruskal–Wallis |
| F6 | Alert-system effectiveness (treatment vs control) | `m1_alerts` (4b) × awareness | Difference-in-Differences |

## Notebooks (4)
1. `findings_lag_analysis.ipynb` — F1 · F2 · F3 · F5.
2. `findings_secondary_diffusion.ipynb` — F4.
3. `findings_alert_effectiveness.ipynb` — F6 (DiD).
4. `findings_classifier_evaluation.ipynb` — RQ1/RQ2 (macro-F1 ≥ 0.92 + per-language slices, from the 3e eval).

## Design
- **`research/notebooks/findings_common.py`** — shared helpers: `bootstrap_median_ci` (pure numpy, unit-tested) + loaders (`load_lag_summary`, `load_channel_effectiveness`, `load_awareness`, `load_alerts_awareness`, `load_model_metrics`). Each loader reads the **production replica** when `DATABASE_URL` is set, else returns a **reproducible synthetic demo** so every notebook runs end-to-end for review.
- **`research/preregistration.md`** — hypotheses, primary metrics, tests, decision rules, α — committed *before* running on real data.
- **`research` pyproject extra** — pandas / numpy / scipy / jupyter / matplotlib.

## Definition of Done
- `bootstrap_median_ci` returns median + 95% CI (lo ≤ median ≤ hi) — unit-tested; empty input safe.
- The 4 notebooks execute top-to-bottom on the synthetic demo (no DB needed) and print each finding's median + CI + test statistic.
- Preregistration committed.

## How to run (manual test — T-18)
```bash
cd enigmatrix-ml && uv sync --extra research
uv run pytest tests/research/test_findings_common.py -v
# demo (no DB): open + Run-All each notebook
uv run jupyter nbconvert --to notebook --execute research/notebooks/findings_lag_analysis.ipynb --stdout >/dev/null && echo OK
# real data:
DATABASE_URL=postgresql://… uv run jupyter lab   # then Run-All
```

## Risks / follow-ups
- Real F1/F2/F4 need 4a propagation data; F3/F5/F6 need the 5a survey responses (≥100) + F6 needs alert-subscription data; F1(classifier) needs the 3d/3e trained model. Until then the notebooks run on the demo and are wired to swap in real data via `DATABASE_URL`.
- Preregister on the supervisor's sign-off before unblinding.

## Cross-refs
`08_M1_Full_System_Architecture.md` · `06_M1_Training_Evaluation.md` · roadmap §Phase 5 5b.
