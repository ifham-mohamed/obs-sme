# Module 1 — Phase 5 Gap-Closure Plan (Research Findings + Survey Deployment)

> Companion to `PHASE5_RESEARCH_FINDINGS_ANALYSIS.md`. Written 2026-08-01 — the last phase to get a closure plan, because until the classifier froze there was no point planning the findings that depend on it.
>
> **The framing that matters: Phase 5 is not a coding phase.** Its analysis instrument is built, pre-registered and statistically sound. What it lacks is data — survey respondents, real classifications, real propagation events. Most of the work below is fieldwork, scheduling and validation, and the one thing that *is* code takes an afternoon.

## Status

| Step | Gap | Status |
|---|---|---|
| 5a | `/portal/m1/survey` embed does not exist; zero real SME respondents | 🔲 **the critical path** — recruitment latency, not code |
| 5b | Notebooks run on synthetic demo data; real inputs empty | 🟡 unblocked on the F6 side by the frozen classifier — see below |
| 5b | `classification_source` filter and matching-precision gate not yet enforced in the notebooks | 📋 validity obligations, cheap to add |
| 5c | Canary logic complete and Beat-wired, never executed | 🟢 logic · 🟡 unrun |
| 5c | Auto-rollback never tested on a synthetic F1 drop | ✅ **closeable today** — `decide()` is pure; one unit test |

---

## What the frozen classifier changed for Phase 5

The Phase-5 analysis was written when the classifier did not exist. One of its three blockers has now partly lifted, and one new obligation has appeared:

1. **F6 (classifier evaluation) now has a real model to evaluate.** The frozen LinearSVC scores 0.947220 macro-F1 on the V6 temporal test split, with per-class F1 recorded. F6 can be written against real numbers today — see [[11_CLASSIFIER_FREEZE_AND_INTEGRATION]] and [[18_M1_Dataset_And_Model_Lineage]].
2. **But the drift half of 5c is still dormant, and now for a different reason.** It was dormant because `classifier_confidence` was NULL everywhere with no model. On the LinearSVC backend `classifier_confidence` **stays NULL by design** — the model emits an uncalibrated margin, not a probability. The KL-divergence drift branch reads confidence. **It will therefore never fire on the current production backend.** This is a new finding and it needs a decision, not a workaround (§5c-A below).
3. **`EPF_ETF_CHANGE` is a one-sample test class.** Any F6 per-class claim must carry that qualifier explicitly.

---

## 5a — Survey deployment 🔲 (the critical path)

**Problem.** The survey *machinery* shipped in Phase 1 — session engine, `next_question_rules` branching, regulation-scoped flows, 12 baseline awareness questions, admin response list. What 5a additionally requires is a **low-friction public embed at `/portal/m1/survey`** wired to the 9-regulation selection. There is no `/portal/` route anywhere in `enigmatrix-frontend/app/`. Today a partner-recruited SME would have to register an account and navigate `(app)/surveys` — a conversion path that will lose most of a recruited sample.

There are **zero real respondents** against a target of ≥ 100 unique SMEs, 10 per sector. F3 (urban vs rural) and F5 (language differential) are *survey-derived*: without respondents they cannot be computed at all, synthetic or otherwise.

**This is calendar risk, not code risk.** Recruitment takes weeks; the route takes days. Run them in parallel and start the slower one first.

**Steps, in dependency order:**

1. **Fix the 9-regulation selection SQL first, not the page.** The 5a design guarantees per-sector coverage — 9 regulations chosen so each sector is represented. That selection is not evidenced anywhere in code. Write it, run it against the current `m1_regulations`, and *look at the nine rows it returns*. If the corpus cannot yet supply a defensible nine, that is a finding about the ingest coverage and it must be known **before** recruitment, not after 40 responses have been collected against a bad instrument.
2. **Build `/portal/m1/survey`** — unauthenticated or magic-link, no registration wall, mobile-first. Reuse the existing session engine; the only new surface is the entry route and an anonymous session mode.
3. **Decide the SI/TA question.** Regulation context cards can now render Sinhala and Tamil, but that translation is **machine-produced and unmeasured** ([[12_TRILINGUAL_TRANSLATION_PIPELINE]] §6). Showing an unlabelled draft MT string to a research respondent is a validity problem, not a UX one. Either (a) hand-review the SI/TA for the nine selected regulations only — nine regulations × 2 languages is a tractable review — or (b) label them visibly as machine-translated. Option (a) is recommended; the nine are known in advance.
4. **Ethics / consent copy** — PDPA-consistent consent text, data-retention statement, withdrawal path. Cross-check against the governance section of [[02_M1_Data_Requirements]] §7 rather than writing fresh.
5. **Partner outreach** — NEDA, Chamber, sector associations. Track outreach as data: who was contacted, when, response rate per channel. **That recruitment record is itself reportable** — a chamber that does not forward a regulatory survey to its members is evidence about information channels, which is the RQ4 subject.
6. **Pilot with 5–10 SMEs before opening it.** Look for drop-off point, question ambiguity, and whether "when did you first hear about this?" is answerable at all. Fix the instrument once, then freeze it — mid-collection instrument changes split the sample.
7. **Gate:** ≥ 100 unique SMEs, ≥ 10 per sector, before any F3/F5 number is quoted.

**Verify:** `SELECT sector, count(DISTINCT sme_id) FROM survey_sessions … GROUP BY 1` returns ≥ 10 for every sector; completion rate from the pilot recorded next to the DoD.

---

## 5b — Findings extraction 🟡

The four notebooks (`findings_lag_analysis`, `findings_secondary_diffusion`, `findings_alert_effectiveness`, `findings_classifier_evaluation`), `findings_common.py` and the committed `preregistration.md` are built and methodologically sound — bootstrap median CIs, Mann-Whitney U, Kruskal-Wallis, DiD. They execute end to end. **Every number they currently print is synthetic**, because `DATABASE_URL` is unset and the real inputs are empty.

### 5b-A — Enforce the two validity obligations *in code*, now (📋, cheap)

Both are currently prose in the analysis document. Prose does not survive a rushed re-run at 2 a.m. before a deadline.

1. **`classification_source` filtering is mandatory.** Every `change_category` row is tagged `heuristic | model | expert`. The 800 F-199 heuristic rows are covariate-shifted seed data, not model output. F6 and any category/sector finding **must** filter or facet on `classification_source='model'`. Put the filter in `findings_common.py`'s loader with an explicit parameter — so the default is correct and an unfiltered load has to be asked for by name.
2. **The ≥ 0.90 matching-precision publish gate.** A false secondary-source match dates "awareness" earlier than reality and biases the headline lag **downward** — the direction that flatters the finding. Make the gate a runtime assertion in the F1/F2 path that reads the audited precision from a recorded value and refuses to render a lag figure without it. See `PHASE4_SCHEDULERS_ALERTS/PHASE4_GAP_CLOSURE_PLAN.md` §6.7.

### 5b-B — Write F6 against the frozen model (📋, unblocked today)

F6 no longer needs to wait. Sources: V6 test-split predictions, per-class F1, the confusion structure from the bake-off, the head-to-head against XLM-R (150 both correct / 10 SVC-only / 3 XLM-R-only / 4 both wrong).

Three things F6 must state rather than omit:

- **`EPF_ETF_CHANGE` F1 = 1.000 is one test document.** Say so in the same sentence as the number.
- **The test split is spent for model selection** — four models have been compared on it. F6 is reporting a held-out measurement, and any further tuning against that split invalidates it.
- **Confidence is unavailable.** LinearSVC returns margins; F6 cannot report a calibration curve or a confidence-stratified accuracy without a separately trained calibration layer ([[11_CLASSIFIER_FREEZE_AND_INTEGRATION]] §7).

### 5b-C — Real-data run sequencing (📋)

The remaining findings are serialized behind Phase 4:

| Finding | Blocked on | Unblocks when |
|---|---|---|
| F1, F2 (portal / news lag) | Watchers producing events + `gazette_published_date` coverage + the precision audit | Phase-4 4c activation sequence completes |
| F3, F5 (urban/rural, language) | 5a respondents | ≥ 100 SMEs collected |
| F4 (alert effectiveness, DiD) | Real alert dispatches | Phase-4 4b fan-out running for real |
| F6 (classifier) | **nothing** | now |

Before believing any lag median: check `gazette_published_date` coverage. Lag is `first_seen_at − gazette_published_date`, and rows with a NULL publication date **silently drop out of the views** rather than erroring.

### 5b-D — Honour the pre-registration retroactively (📋)

The pre-registration is committed, which is good practice worth highlighting in the thesis. The risk it does not protect against: analyses have so far run only on synthetic data, and **seeing synthetic results can drift analysis choices before real data arrives**. Before the first real-data run, re-read `preregistration.md` and record any deviation as a deviation, with its reason — do not silently update the document.

---

## 5c — Retraining cadence and canary rollout

### 5c-A — The drift trigger cannot fire on the current backend (📋 — decide, don't drift)

**New as of the classifier freeze, and it is not a bug in Phase 5.** The 4c drift check computes KL divergence over `classifier_confidence`. On the LinearSVC backend that column is NULL by design. The branch is guarded by `len(baseline) >= 20`, so it will no-op forever and silently.

Three options, in order of preference:

1. **Compute drift over `classifier_decision_margin` instead.** The column now exists with a partial index, and the distribution of margins is a legitimate drift signal — it just is not a probability. Requires changing the metric's interpretation, not its machinery.
2. **Compute drift over the predicted-category distribution.** Model-agnostic, works on any backend, and arguably closer to what "the world changed" means for this task.
3. **Leave drift dormant and rely on the quarterly schedule.** Acceptable, but then say so explicitly rather than leaving a code path that looks live and is not — the same class of failure as the review queue that matched zero rows and looked healthy.

**Do not** synthesize a pseudo-probability from a margin to feed the existing code path.

### 5c-B — Close the auto-rollback DoD today (✅ one unit test)

`promotion.decide(prod_f1, candidate_f1, gate=0.92, regression_tol=0.01)` is pure stdlib and unit-testable. The DoD asks for a fired rollback on a synthetic F1 drop. Assert the full truth table:

| prod_f1 | candidate_f1 | Expected |
|---:|---:|---|
| 0.93 | 0.80 | `rollback` — below gate |
| 0.93 | 0.915 | `rollback` — regression > 1 pp |
| 0.93 | 0.925 | `promote` |
| 0.93 | `None` | `hold` — no candidate metric |

This is the cheapest open item in the entire module. Close it and record the result next to the DoD.

### 5c-C — The `dry_run=True` default (📋)

`run_retraining` defaults to `dry_run=True`, so the quarterly Beat job will never actually retrain unless invoked explicitly. That is a **sensible safety default and should stay** — but it means the only DoD that can currently pass is "quarterly retraining dry-run completes end-to-end on staging".

There is also a mismatch to resolve: `retrain.py` orchestrates `m1.model.train_xlmr` → `m1.model.eval` → `promotion.decide`. **The production model is no longer an XLM-R checkpoint.** Either retarget the retraining path at the LinearSVC pipeline (cheap — it is a `joblib` fit, no GPU) or state that automated retraining applies to a model line that is not currently in production. The second is honest but leaves the quarterly Beat job pointing at nothing.

**Recommendation:** retarget. A LinearSVC refit is minutes on CPU, which makes a genuine quarterly retrain *actually achievable* for the first time — an argument in favour of the frozen model that is worth making in the write-up.

---

## Dependency chain (why Phase 5 cannot be parallelised away)

```text
gold labels ──▶ trained model ──▶ real classifications ──┐
                                                          ├──▶ propagation + lag data ──┐
secondary-source watchers ────────────────────────────────┘                              ├──▶ F1–F6 findings
survey portal ──▶ recruitment ──▶ respondents ────────────────────────────────────────────┘
```

The first branch is now **closed** — the model is frozen and wired. The bottom branch has not started, and it is the slowest. Everything upstream slipping lands directly on the thesis timeline.

---

## Verification checklist

| # | Check | Gate |
|---|---|---|
| 1 | `promotion.decide` truth table unit test | 4/4 cases pass |
| 2 | 9-regulation selection SQL returns a defensible nine | manual review |
| 3 | `/portal/m1/survey` reachable without login; pilot completion rate recorded | ≥ 5 pilot responses |
| 4 | `classification_source` filter is the loader default | unfiltered load requires an explicit argument |
| 5 | Matching-precision audit recorded per `match_method` | ≥ 0.90 before any lag figure |
| 6 | `gazette_published_date` coverage | reported alongside every lag median |
| 7 | Respondents per sector | ≥ 10 each, ≥ 100 total |
| 8 | Drift-signal decision recorded (§5c-A) | one option chosen and written down |
| 9 | Retraining path retargeted or explicitly scoped out (§5c-C) | decision recorded |
| 10 | F6 written with all three caveats stated | present in the text, not a footnote |

---

## Fastest defensible path

1. **Today:** close 5c-B (unit test) and write F6 against the frozen model — both are unblocked.
2. **This week:** the 9-regulation selection SQL and the `/portal/m1/survey` route; begin partner outreach the moment the route exists.
3. **In parallel:** Phase-4 watcher URL triage and the matching-precision audit, because F1/F2 cannot be published without them.
4. **Do not wait** for perfect upstream data before starting recruitment. Recruitment latency, not code, is the critical path to a defensible thesis.

---

*Scope note: this document covers Phase 5 only. Phase 1 → `PHASE1_FOUNDATION/PHASE1_GAP_CLOSURE_PLAN.md`; Phase 2 → `PHASE2_INGEST_EXTRACTION/PHASE2_GAP_CLOSURE_PLAN.md`; Phase 3 → `PHASE3_ANNOTATION_CLASSIFICATION/PHASE3_GAP_CLOSURE_PLAN.md`; Phase 4 → `PHASE4_SCHEDULERS_ALERTS/PHASE4_GAP_CLOSURE_PLAN.md`.*
