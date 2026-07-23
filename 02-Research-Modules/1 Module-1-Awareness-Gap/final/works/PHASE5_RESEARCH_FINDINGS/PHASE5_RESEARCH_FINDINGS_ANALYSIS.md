# Module 1 — Phase 5 (Research Findings + Survey Deployment): Complete Analysis

> Single-file analysis of **Phase 5 — Research findings + survey deployment** *only*: scope, technologies, what is actually built vs. blocked, the full data journey, and the approaches missed. Grounded in the live codebase (`enigmatrix-ml/research/notebooks/findings_*.ipynb`, `findings_common.py`, `preregistration.md`, `enigmatrix-ml/scripts/retrain.py`, `m1/model/promotion.py`, `app/m1/tasks/retraining.py`, `app/m1/models/retraining_run.py`, `scripts/regenerate_thesis_tables.py`) and the vault (`16_M1_Development_Roadmap.md §Phase 5`, `FEATURES.md` F-238/F-239).
>
> Generated 2026-07-18; **reviewed 2026-07-21** — no Phase-5 code changed in the Session 64–71 gap-closure work, but that work tightened three of Phase 5's data-validity preconditions (see the Session 64–71 note below §0). **Honest status: the analysis machinery is built and methodologically sound, but it has no real data to analyse.** Phase 5 is the terminal dependency of the whole module — it cannot produce findings until Phase 3 (classifier) and Phase 4 (watchers/alerts) run for real and Phase 5a collects primary survey data.

---

## 0. The one-paragraph truth

Phase 5's *code* is in good shape: four findings notebooks compute F1–F6 with **bootstrap median CIs, Mann-Whitney U, Kruskal-Wallis and DiD**, backed by a shared `findings_common.py` loader layer and — importantly for research integrity — a committed **`preregistration.md`**. Phase 5c is genuinely complete as logic: `promotion.decide()` is a pure, unit-testable canary gate (promote / rollback / hold against an F1 ≥ 0.92 gate and a 1 pp regression tolerance), persisted per attempt to `m1_retraining_runs`, wired to quarterly Beat and to the 4c drift trigger. But three things block the phase from delivering: (1) the **`/portal/m1/survey` embed does not exist** and there has been no partner outreach, so there are **zero real SME respondents** — the primary empirical contribution has no primary data; (2) the notebooks **run on a synthetic demo** unless `DATABASE_URL` is set, and the real inputs (lag views, propagation events, classifier confidence) are empty because Phases 3–4 haven't run for real; (3) `run_retraining` **defaults to `dry_run=True`** and has no trained base model to retrain. Phase 5 is therefore "instrument built, experiment not yet conducted."

---

### Session 64–71 note — what the upstream gap-closure changed for Phase 5

The Phase 2–4 hardening (Sessions 64–71) didn't touch Phase-5 code, but it moved three preconditions the findings depend on, and each is now an explicit obligation on the notebooks:

1. **`classification_source` filtering is now mandatory (Session 70).** Every `change_category` row is tagged `heuristic | model | expert`. F6 (classifier evaluation) and any finding that reads categories/sectors **must facet or filter on `classification_source`** — the 800 F-199 heuristic rows are covariate-shifted seed data, not model output, and mixing them in would bias the results. This is the single most important validity change for the findings layer.
2. **The F1/F2 lag findings are gated on the Phase-4 matching-precision audit (Session 71 plan §6.7).** A false secondary-source match dates "awareness" earlier than reality and biases the headline lag *downward*. The gap-closure plan makes a ≥ 0.90 precision hand-audit a **publish gate** before any lag number leaves the notebook — treat it as a Phase-5 prerequisite, not a Phase-4 nicety.
3. **Lag inputs now span 15 sources, not 4 (Session 71).** The `m1_sources` registry seeded to 15 widens the diffusion dataset the notebooks read — but the seed URLs are best-known defaults needing triage, so channel-effectiveness comparisons should note which sources actually produced events.

The drift-triggered retraining path (§5c) still stays dormant until Phase 3 ships a model (classifier confidence is NULL everywhere), consistent with [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/20_PHASE4_SCHEDULERS_ALERTS_ANALYSIS]] §4c.

---

## 1. What Phase 5 is (scope + goal)

**Goal (roadmap):** F1–F6 findings are computed end-to-end; the SME survey is in production; the thesis chapter is data-ready. *"The platform is the research vehicle and produces the empirical contribution simultaneously."*

| Step | Deliverable | Real status |
|---|---|---|
| **5a** | Survey portal embed at `/portal/m1/survey` wired to the 9-regulation selection; partner outreach (NEDA, Chamber); **≥ 100 unique SME respondents**, 10/sector | 🔲 **portal route does not exist**; survey engine exists from Phase 1 at `/surveys`; **no real respondents** |
| **5b** | Four `research/notebooks/findings_*.ipynb` computing F1–F6 with median + bootstrap CI + statistical test; pre-registration honoured | 🟡 **notebooks + preregistration built**; run on **synthetic demo** — real-data run pending |
| **5c** | `scripts/retrain.py` + canary rollout wired to `m1_retraining_runs`; quarterly dry-run; auto-rollback on synthetic F1 drop | 🟢 **logic complete + Beat-wired**; 🟡 never executed for real (`dry_run=True` default, no base model) |

---

## 2. Technologies used in Phase 5

### Used
| Technology | Layer | Phase-5 role |
|---|---|---|
| **Jupyter + pandas** | Research | the four F1–F6 findings notebooks |
| **scipy + numpy** | ML/Stats | `mannwhitneyu` (F3 urban vs rural), `kruskal` (F5 EN/SI/TA), bootstrap median CI, DiD (alert effectiveness) |
| **PostgreSQL materialized views** | Storage | `v_m1_regulation_lag_summary` / `v_m1_channel_effectiveness` are the notebooks' primary input |
| **Celery Beat** | Queue | `retraining-quarterly` (1st of Jan/Apr/Jul/Oct, 03:00 UTC) + drift-triggered from 4c |
| **PyTorch / XLM-R + LoRA** | ML | retraining path (dormant — no base model) |
| **SQLAlchemy / Alembic** | Backend | `m1_retraining_runs` (migration `202606300005`) |
| **Survey engine (Phase 1)** | Backend/Frontend | the awareness instrument that would collect 5a's primary data |

### Not exercised
No production survey deployment, no real-data notebook execution, no actual retraining run. The `research` extra (scipy) is optional — the notebooks degrade gracefully and print a warning if it's absent.

---

## 3. Step-by-step: planned vs. built (with code files)

### 5a — SME survey deployment (🔲 the real gap)
The **survey machinery** shipped in Phase 1: unified session engine, `next_question_rules` branching, regulation-scoped flows, 12 baseline awareness questions, admin response list. What Phase 5a additionally required — a **public/partner-facing embed at `/portal/m1/survey`** wired to a 9-regulation selection — **does not exist**: there is no `/portal/` route anywhere in `enigmatrix-frontend/app/`. Respondents would have to register and use `(app)/surveys`, which is a much higher-friction path for partner-recruited SMEs. No outreach artefacts, and no evidence of real respondents. **This is fieldwork, not code** — and it is the single largest blocker to the thesis contribution.

### 5b — F1–F6 findings extraction (🟡)
`enigmatrix-ml/research/notebooks/`:
- **`findings_lag_analysis.ipynb`** — F1 (gazette → official portal lag), F2 (gazette → news lag), F3 (SME awareness lag urban vs rural, **Mann-Whitney U**, one-sided `rural > urban`), F5 (language differential EN/SI/TA, **Kruskal-Wallis**).
- **`findings_secondary_diffusion.ipynb`** — secondary-channel diffusion.
- **`findings_alert_effectiveness.ipynb`** — F4-style alert impact (**DiD**).
- **`findings_classifier_evaluation.ipynb`** — F6 classifier performance.
- **`findings_common.py`** — shared loaders (`load_lag_summary`, `load_awareness`) + `bootstrap_median_ci`.
- **`preregistration.md`** — committed pre-registration; each notebook links it and states the decision rules. *(Good research practice — worth highlighting in the thesis.)*

Each notebook header states: *"Runs on a synthetic demo unless `DATABASE_URL` is set (then it reads the production replica)."* So they execute and produce numbers today — **but those numbers are synthetic**. `scripts/regenerate_thesis_tables.py` (Makefile `thesis-artifacts`) regenerates thesis tables from the same sources.

### 5c — Retraining cadence + auto-rollback (🟢 logic, 🟡 unrun)
- **`enigmatrix-ml/m1/model/promotion.py`** — `decide(prod_f1, candidate_f1, gate=0.92, regression_tol=0.01) -> (action, reason)`; `hold` if no candidate metric, `rollback` if below gate **or** regressing > 1 pp vs prod, else `promote`. Pure stdlib → unit-testable (F-239).
- **`enigmatrix-ml/scripts/retrain.py`** — orchestrates `m1.model.train_xlmr` → `m1.model.eval` → `promotion.decide`.
- **`app/m1/tasks/retraining.py`** — `run_retraining(trigger="scheduled", dry_run=True)`: inserts an `M1RetrainingRun` (`status='running'`), runs (GPU steps skipped in dry-run), applies the canary decision, sets `promoted` / `rolled_back` / `status ∈ {succeeded, failed, rolled_back}`. Beat quarterly + drift-triggered from `analytics.refresh_lag_analytics`.
- **`app/m1/models/retraining_run.py`** — `m1_retraining_runs`: `trigger ∈ {scheduled, drift, manual}`, `status ∈ {queued,running,succeeded,failed,rolled_back}`, `candidate_f1`, `prod_f1`, `action ∈ {promote,rollback,hold}`, `reason`, `promoted`, `rolled_back`, timestamps, `notes`. A clean, auditable retraining ledger.

---

## 4. How it was developed (stages)

- **S68 / F-236** — 4c nightly analytics + drift trigger (the hook that fires 5c retraining).
- **S69 / F-238** — the four findings notebooks (tracker marks 🟡: *"valid JSON; demo smoke computes every finding; real-data run pending survey/propagation/model"*).
- **F-239** — Phase 5c canary promotion logic + `m1_retraining_runs` + quarterly Beat.
- Pre-registration + `findings_common.py` committed alongside the notebooks; `regenerate_thesis_tables.py` + `make thesis-artifacts` for reproducible thesis tables.

---

## 5. Verification present today

- Notebooks are valid JSON and **execute end-to-end on the synthetic demo**, computing every finding (F-238's DoD).
- `promotion.decide` is pure and unit-testable; `run_retraining` compiles and is Beat-registered.
- **Absent:** any real-data notebook run; ≥ 100 real respondents; a completed retraining (dry or wet) with genuine `candidate_f1` / `prod_f1`; a recorded auto-rollback test on a synthetic F1 drop.

---

## 6. Gaps & missed approaches (the analytical part)

1. **No primary survey data — the biggest gap in the whole module.** `/portal/m1/survey` is unbuilt, no partner outreach has happened, and there are 0 of the required ≥ 100 respondents. F3 (urban vs rural) and F5 (language differential) are *survey-derived* findings — without respondents they cannot be computed at all, synthetic or not. This is calendar-risk, not code-risk: recruitment takes weeks.
2. **Findings are synthetic.** Every number the notebooks currently print is demo data. The real inputs are empty: lag views need Phase-4 watchers running against a real source registry (**now built + seeded to 15, Session 71 — but URLs need triage**); classifier evaluation (F6) needs a trained model (Phase 3); alert effectiveness (F4) needs real dispatches. When real data arrives, the notebooks must filter `change_category` by `classification_source` (Session 70) and honour the matching-precision gate (Session 71) — see the Session 64–71 note above §1.
3. **Retraining defaults to `dry_run=True`.** The quarterly Beat job will therefore never actually retrain unless invoked explicitly — sensible as a safety default, but it means the "quarterly retraining dry-run completes end-to-end on staging" DoD is the *only* thing that could pass, and even that needs a base model.
4. **Auto-rollback never tested on synthetic drift.** The logic looks correct, but the DoD explicitly asks for a fired rollback on a synthetic F1 drop; no such test result is recorded. This is cheap to close now — `decide()` is pure, so a unit test with `candidate_f1=0.80, prod_f1=0.93` would satisfy it immediately.
5. **Everything is serialized behind Phases 3–4.** Phase 5 has no independent path to completion. The dependency chain is: gold labels → trained model → real classifications → watchers + alerts → propagation/lag data + survey responses → findings. Any slip upstream lands directly on the thesis timeline.
6. **Pre-registration must be honoured retroactively.** The pre-registration is committed (excellent), but analyses so far have only run on synthetic data — take care that seeing synthetic results doesn't drift the analysis choices before real data arrives.
7. **Survey instrument vs. the 9-regulation design.** The Phase-1 engine has 12 baseline questions and regulation-scoped flows, but the 5a "9 regulations × 10 SMEs/sector" selection SQL isn't evidenced in code — the sampling design that guarantees per-sector coverage still needs wiring.

**Fastest path to a defensible thesis:** close #4 immediately (a unit test), build the low-friction public survey route (#1) and start recruitment *in parallel* with fixing Phase 3's training — recruitment latency, not code, is the critical path.

---

## 7. Traceability (capability → code → doc → F-id)

| Capability | Code path(s) | Doc | F-id |
|---|---|---|---|
| Survey instrument (from Phase 1) | `services/survey_{session,question}_service.py`, `(app)/surveys/*` | `09_M1_3_SME_Survey_Instrument` | F-33, F-35 |
| Public survey portal embed | **missing** (`/portal/m1/survey`) | `09_M1_3` | — |
| F1/F2/F3/F5 lag findings | `research/notebooks/findings_lag_analysis.ipynb` | `08_M1_1_Research_Findings_Extraction` | F-238 |
| Secondary diffusion | `findings_secondary_diffusion.ipynb` | `03_M1_3` | F-238 |
| Alert effectiveness (DiD) | `findings_alert_effectiveness.ipynb` | `08_M1_1` | F-238 |
| Classifier evaluation (F6) | `findings_classifier_evaluation.ipynb` | `06_M1_Training_Evaluation` | F-238 |
| Shared loaders + bootstrap CI | `research/notebooks/findings_common.py` | `08_M1_1` | F-238 |
| Pre-registration | `enigmatrix-ml/research/preregistration.md` | `08_M1_1` | F-238 |
| Thesis tables | `scripts/regenerate_thesis_tables.py`, `make thesis-artifacts` | — | — |
| Canary promotion logic | `enigmatrix-ml/m1/model/promotion.py` | `12_M1_2_Retraining_Deployment_Rollback` | F-239 |
| Retraining orchestration | `enigmatrix-ml/scripts/retrain.py` | `12_M1_2` | F-239 |
| Retraining task + ledger | `app/m1/tasks/retraining.py`, `app/m1/models/retraining_run.py`, migration `202606300005` | `12_M1_2` | F-239 |

---

## 8. Data flow — how data travels through the stages (Phase 5)

Phase 5 has three journeys: **survey collection** (the only one with a human/browser in the loop), **findings computation** (offline, Jupyter), and **retraining/canary** (Beat-driven).

### 8.0 Inputs / data sources
| Input | Where it enters | Becomes |
|---|---|---|
| SME survey answers (≥ 100 respondents × 9 regulations) | `(app)/surveys` — *portal embed missing* | `survey_sessions` + `survey_responses` → `awareness_lag_days` |
| Propagation events (Phase 4) | nightly refresh | `v_m1_regulation_lag_summary`, `v_m1_channel_effectiveness` |
| Classifier confidence + predictions (Phase 3) | `classify_gazette` | F6 inputs + drift baseline |
| Alert send/read records (Phase 4) | `m1_alerts` | F4 alert-effectiveness (DiD) |

### 8.1 Survey-collection journey (frontend in the loop)
```
[SME] (planned) /portal/m1/survey  ←  MISSING route
[SME] (actual)  /surveys → (app)/surveys/awareness
  → survey_session_service.create_session → INSERT survey_sessions
  → per answer: record_answer → INSERT survey_responses
        (M1 awareness answers unscored by design)
  → complete_session
  → derived: awareness_lag_days per (sme, regulation, location, language)
        → the F3 / F5 inputs
```

### 8.2 Findings-computation journey (Jupyter, offline)
```
PostgreSQL (production replica)
  → findings_common.py  load_lag_summary()  ← v_m1_regulation_lag_summary   [Phase 4]
                        load_awareness()    ← survey_responses               [Phase 5a]
     (falls back to a SYNTHETIC demo when DATABASE_URL is unset ← today's state)
  → findings_lag_analysis.ipynb
        F1 = bootstrap_median_ci(portal_lag_days)
        F2 = bootstrap_median_ci(news_lag_days)
        F3 = median CI urban vs rural + mannwhitneyu(rural, urban, alternative='greater')
        F5 = median CI per en/si/ta + kruskal(en, si, ta)
        (F6 + any category/sector finding: FILTER change_category BY classification_source='model'   [Session 70]
         F1/F2: apply the ≥0.90 matching-precision publish gate before reporting                       [Session 71])
  → findings_secondary_diffusion.ipynb / findings_alert_effectiveness.ipynb (DiD)
    / findings_classifier_evaluation.ipynb (F6)
  → scripts/regenerate_thesis_tables.py  (make thesis-artifacts) → thesis tables
  → interpretation against preregistration.md decision rules
```

### 8.3 Retraining + canary journey (Beat-driven)
```
Celery Beat (quarterly: 1st Jan/Apr/Jul/Oct 03:00 UTC)
   OR analytics 4c drift (KL > 0.15) → run_retraining.delay(trigger='drift')
  → app/m1/tasks/retraining.run_retraining(trigger, dry_run=True)   ← DEFAULT dry-run
      → INSERT m1_retraining_runs (status='running', trigger)
      → (wet run) enigmatrix-ml/scripts/retrain.py
             → m1.model.train_xlmr  → candidate checkpoint
             → m1.model.eval        → candidate_f1
      → m1.model.promotion.decide(prod_f1, candidate_f1, gate=0.92, tol=0.01)
             → 'promote' | 'rollback' | 'hold' (+ reason)
      → UPDATE m1_retraining_runs SET candidate_f1, prod_f1, action, reason,
                                      promoted, rolled_back, status, finished_at
  → (promote) new ONNX artifact becomes the model classifier_service loads
```

### 8.4 Where each stage lives (quick map)
| Stage | Component | Code |
|---|---|---|
| Collect survey data | survey engine + pages | `services/survey_*_service.py`, `(app)/surveys/*` (portal embed **missing**) |
| Load research data | notebook loaders | `research/notebooks/findings_common.py` |
| Compute F1–F6 | Jupyter + scipy | `research/notebooks/findings_*.ipynb` |
| Pre-registration | methodology | `enigmatrix-ml/research/preregistration.md` |
| Thesis tables | script | `scripts/regenerate_thesis_tables.py` |
| Retrain + decide | ML + task | `scripts/retrain.py`, `m1/model/promotion.py`, `app/m1/tasks/retraining.py` |
| Retraining ledger | DB | `app/m1/models/retraining_run.py`, migration `202606300005` |

---

*Scope note: this document covers Phase 5 only. Phase 1 → `PHASE1_FOUNDATION_ANALYSIS.md`; Phase 2 → `PHASE2_INGEST_EXTRACTION_ANALYSIS.md`; Phase 3 → `PHASE3_ANNOTATION_CLASSIFICATION_ANALYSIS.md`; Phase 4 → `PHASE4_SCHEDULERS_ALERTS_ANALYSIS.md`. Phase 5 is the terminal dependency: the analysis instrument is built and pre-registered, but the empirical contribution requires real survey respondents plus live Phase-3/4 output.*
