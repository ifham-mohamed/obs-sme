---
tags: [m1, phase-5, plan, retraining, canary, rollback, mlops]
date: 2026-06-30
author: Mohamed M.R.I (215075J) — Module 1 owner
session: 70
status: 🟡 in-execution — built this session (Session 70)
features: F-239 (m1_retraining_runs + canary promotion) · F-240 (retrain.py + retraining task + triggers)
---

# M1 Phase 5c — Retraining + auto-rollback

> **Goal (roadmap Phase 5, Step 5c):** a retraining pipeline — quarterly (Beat) and **drift-triggered** (from 4c) — that trains a candidate, evaluates it, and **canary-promotes** it only if it clears the F1 gate and doesn't regress; otherwise **rolls back**.
>
> **Why:** sustains classifier quality as the gazette corpus grows; the 4c KL-divergence drift check is the automatic trigger.

## Approach
- **`m1_retraining_runs`** table records every run: `trigger` (scheduled/drift/manual), `status`, `candidate_f1`, `prod_f1`, `action` (promote/rollback/hold), `reason`, `promoted`/`rolled_back`, timings.
- **Canary decision (pure, tested)** — `m1/model/promotion.decide(prod_f1, candidate_f1, gate=0.92, regression_tol=0.01)`:
  - candidate below the **absolute gate (0.92)** → **rollback**;
  - candidate regresses vs production beyond `regression_tol` → **rollback**;
  - else → **promote**. (Missing candidate → **hold**.)
- **`scripts/retrain.py`** — trains a candidate (`m1.model.train_xlmr`) + evaluates (`m1.model.eval`) + `decide()` → writes `retrain_result.json`. `--dry-run` exercises the decision path without a GPU.
- **`run_retraining` Celery task** — records the run, invokes `retrain.py` as a subprocess (GPU-friendly, decoupled), parses the result, and applies the promote/rollback decision to the run row. **Quarterly Beat** (1st of Jan/Apr/Jul/Oct, 03:00) + **drift trigger** enqueued from the 4c analytics task.

## Files
`app/models/m1_retraining_run.py` · migration `202606300005_m1_retraining_runs.py` (down-rev `202606300004`) · `enigmatrix-ml/m1/model/promotion.py` (pure, tested) · `enigmatrix-ml/scripts/retrain.py` · `app/tasks/m1/retraining.py` · `app/celery_config.py` (register + Beat) · `app/tasks/m1/analytics.py` (drift → enqueue) · `enigmatrix-ml/tests/m1/model/test_promotion.py`.

## Definition of Done
- `promotion.decide` returns promote/rollback/hold per the rules — unit-tested.
- `retrain.py --dry-run` runs end-to-end (no GPU) and writes a `retrain_result.json` with a decision.
- `run_retraining` records a `m1_retraining_runs` row + applies the decision; on Beat quarterly; enqueued on 4c drift.

## How to run (manual test — T-19)
```bash
cd enigmatrix-backend && uv run alembic upgrade head            # 202606300005
cd ../enigmatrix-ml && uv run pytest tests/m1/model/test_promotion.py -v
uv run python scripts/retrain.py --data datasets/m1_regulations --out storage/models/m1/retrain_dry --dry-run
# expect: {"candidate_f1":…, "action":"promote|rollback|hold", "reason":…}
# via Celery (records a run):
cd ../enigmatrix-backend && uv run python -c "from app.tasks.m1.retraining import run_retraining; print(run_retraining.apply(kwargs={'trigger':'manual','dry_run':True}).result)"
```

## Risks / follow-ups
- Real retraining needs the 3d/3e model + gold data + a GPU; `--dry-run` is the interim path.
- **Production-pointer flip** (`model_versions.is_production`) lands with the 3d model registry — the run row records the decision until then.
- Canary rollout (serve N% traffic to the candidate) is deferred; the gate+regression rule is the safe interim.

## Cross-refs
`12_M1_Monitoring_Maintenance.md` · roadmap §Phase 5 5c · trigger from 4c `analytics.py` (drift).
