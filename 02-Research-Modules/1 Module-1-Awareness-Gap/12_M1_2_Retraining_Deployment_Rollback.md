# 12_M1_2 — Retraining, Deployment & Rollback

> Companion to [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md) — full retraining workflow code, A/B testing strategy, auto-rollback trigger, backfill orchestration.
> **Implementation status:** 🔲 Deferred (BUILD_11 — `scripts/retrain.py`, `scripts/deploy_canary.py`)

## Purpose

Parent doc §3.4 lays out the retraining workflow at a high level. This companion makes each step concrete with the actual scripts, the canary-testing measurement protocol, and the auto-rollback trigger code.

## Detailed process

### Day 0 — Trigger fires

```python
# backend/app/tasks/m1/analytics.py — nightly retraining-trigger check
async def check_retraining_triggers(db):
    f1 = await estimate_production_f1(db)
    drift = await check_confidence_drift(db)
    new_label_count = await count_new_expert_labels_since_last_train(db)
    annual_due = await annual_review_due(db)

    triggers = []
    if f1["macro_f1"] < 0.85 and f1["reliability"] in ("medium","high"):
        triggers.append("f1_regression")
    if drift["kl_divergence"] > 0.15:
        triggers.append("confidence_drift")
    if new_label_count >= 200:
        triggers.append("label_target_met")
    if annual_due:
        triggers.append("annual_review")

    if triggers:
        await db.execute(insert(M1RetrainingRun).values(
            triggered_at=datetime.utcnow(),
            triggers_json=triggers,
            status='triggered',
        ))
        await slack_notify("#enigmatrix-ml", f"Retraining triggered: {triggers}")
```

### Day 0 — Data collection

```bash
python scripts/collect_retraining_data.py --since "$(date -d '6 months ago' +%Y-%m-%d)" \
    --include verified=true \
    --include needs_review=false \
    --output research/data/retraining_v$(date +%Y%m%d).parquet
```

The script:

1. Pulls the last 6 months of `expert_verified=true` rows.
2. Pulls all new annotator-labelled batches.
3. Validates against `m1_validate_pipeline.py` rules.
4. Writes Parquet + computes SHA-256.
5. Records the hash in `M1RetrainingRun.input_data_sha256`.

### Day 1 — Label review

A 50-doc random sample is reviewed by the domain expert against existing gold labels. IAA against the prior gold set must be ≥ 0.75 — otherwise the retraining run is *aborted* (the new labels may have introduced drift).

### Day 1–3 — Training

```bash
python scripts/train_model.py --data research/data/retraining_v$DATE.parquet \
    --seeds 42 1 2 \
    --base-model facebook/xlm-roberta-base \
    --output-dir storage/models/m1/staging \
    --report storage/models/m1/staging/training_report.json
```

Three seeds run sequentially. Mean ± std macro-F1 written to `model_registry.json`. If mean F1 < current production F1 − 0.5 pp, run is **aborted** and notification sent.

### Day 3 — ONNX export + integration test

```bash
python scripts/export_onnx.py --checkpoint storage/models/m1/staging/best.pt \
                               --out storage/models/m1/staging/gazette_classifier.onnx
python scripts/quantize_onnx.py --input ... --out staging/gazette_classifier_int8.onnx
python scripts/integration_test.py --model staging/gazette_classifier_int8.onnx \
                                    --test-set research/data/test_split.parquet
# Asserts test-set F1 matches the training F1 ± 0.5 pp
```

### Day 3 — Canary rollout (10%)

```bash
# Upload staging model to Fly volume as v(N+1)
fly ssh sftp shell -a enigmatrix-m1-classifier
sftp> put storage/models/m1/staging/* /app/storage/models/m1/v1.1/

# Flip canary
fly secrets set M1_MODEL_VERSION=v1.1 \
                 M1_PREVIOUS_MODEL_VERSION=v1.0 \
                 M1_MODEL_CANARY_PCT=10 \
                 -a enigmatrix-m1-classifier
```

Monitor for 24 h. Compare per-version production F1:

```sql
SELECT model_version,
       COUNT(*) FILTER (WHERE expert_verified=true AND change_category = expert_category)::float
       / NULLIF(COUNT(*) FILTER (WHERE expert_verified=true), 0) AS verified_acc,
       AVG(confidence) AS avg_conf
FROM m1_regulations
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY model_version;
```

### Day 4 — 50% rollout

If canary metrics within target (verified_acc within 1 pp of baseline; avg_conf not lower):

```bash
fly secrets set M1_MODEL_CANARY_PCT=50 -a enigmatrix-m1-classifier
```

Monitor 24 h.

### Day 5 — Full rollout + backfill

```bash
fly secrets set M1_MODEL_CANARY_PCT=100 -a enigmatrix-m1-classifier
python scripts/backfill_classifications.py --model v1.1 --since "30 days ago"
```

Backfill re-classifies the last 30 days of regulations with v1.1, stores the new prediction alongside the v1.0 prediction (for ablation), and promotes v1.1's prediction to the canonical column.

### Auto-rollback (any stage)

A nightly check fires the rollback if production F1 (reliability=`high`) drops > 5 pp in 24 h compared to the pre-rollout baseline:

```python
# backend/app/tasks/m1/analytics.py
async def check_auto_rollback(db):
    f1 = await estimate_production_f1(db)
    if f1["reliability"] != "high":
        return                                           # not enough data
    baseline_f1 = await fetch_pre_rollout_baseline(db)
    if baseline_f1 - f1["macro_f1"] > 0.05:
        await trigger_rollback()
        await pagerduty_high(f"Auto-rollback fired: F1 dropped {baseline_f1 - f1['macro_f1']:.3f}")

async def trigger_rollback():
    await fly_secrets_set({
        "M1_MODEL_VERSION": os.environ["M1_PREVIOUS_MODEL_VERSION"],
        "M1_MODEL_CANARY_PCT": "0",
    })
    await db.execute(update(M1RetrainingRun).where(...).values(
        status='rolled_back', rolled_back_at=datetime.utcnow(),
        rollback_reason='auto_f1_regression'))
```

The retraining-run row is annotated with the rollback reason; post-mortem in `research/incidents/`.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Canary by gazette-id hash (chosen) | Sticky; idempotent | ✅ See [07_M1_2_Fly_io_Deployment_Operations.md](07_M1_2_Fly_io_Deployment_Operations.md) | If a feature-flag service (GrowthBook) is adopted, switch. |
| 10/50/100 rollout (chosen) | Conservative; 24h dwell time per stage | ✅ Matches the SLA reliability requirements | If we need faster iteration (rare). |
| Auto-rollback (chosen) | Fast recovery from bad deploys | ✅ < 60s rollback time; no humans in the loop | If false-positive rate exceeds 5 % (no real F1 drop but rollback fires). |
| 5 pp auto-rollback threshold | Conservative — small drops don't roll back | ✅ Empirical — tighter triggers cause too many rollbacks during noisy weeks | Re-tune after 6 months of production data. |
| Backfill after rollout | Consistent classification across the table | ✅ Required for thesis-time analysis | Drop if backfill cost becomes prohibitive (unlikely at 30 gaz/day). |

## Worked example

A retraining cycle from trigger to full rollout:

```
[Day 0 02:00] analytics task fires:
   estimated production F1 = 0.842 (reliability=medium, n=63)
   triggers = ['f1_regression']
   Slack: 'Retraining triggered: f1_regression — current F1 0.842 < threshold 0.85'

[Day 0 09:00] M1 lead reviews triggers; approves retraining

[Day 0 10:00] collect_retraining_data.py runs:
   exported 287 verified labels + 156 new annotator labels = 443 rows
   SHA: ab12cd...

[Day 1 14:00] domain expert reviews 50-doc sample
   IAA against gold labels: κ=0.84 → PASS

[Day 1 15:00] train_model.py starts
[Day 3 09:00] training done
   v1.1 macro F1 = 0.928 ± 0.011 (vs v1.0 production 0.842)
   per-language: en 0.94, si 0.89, ta 0.86
   Slack: 'v1.1 ready: F1 0.928. Canary @ 10% starting now.'

[Day 3 10:00] export_onnx + quantize + integration test
   INT8 F1 = 0.919 (Δ -0.9 pp) → PASS (< 1.5 pp threshold)

[Day 3 11:00] canary at 10%; metrics monitored

[Day 4 11:00] 24h dwell complete
   v1.1: verified_acc 0.91, avg_conf 0.84
   v1.0: verified_acc 0.84, avg_conf 0.79
   → ramp to 50%

[Day 5 11:00] another 24h dwell complete; metrics stable
   → ramp to 100%

[Day 5 12:00] backfill last 30 days with v1.1
   reclassified 850 regulations; 23 changed change_category (3% rate)
   23 changes audited; all are improvements

[Day 5 16:00] retraining run marked complete; v1.0 retained on volume for 30 days
```

## Failure modes & edge cases

- **Auto-rollback fires falsely.** Caused by a small `expert_verified` sample with bad luck. Mitigation: `reliability='high'` requirement means N ≥ 100 — small samples won't trigger.
- **Multiple triggers simultaneously.** Don't queue multiple retrains — only one active retraining-run at a time. New triggers during an active run are recorded but don't fire.
- **v1.1 training aborts mid-run.** GPU crash. The retraining-run is marked `status='aborted'`; data preserved; admin can resume manually.
- **Fly secrets propagation delay.** `fly secrets set` triggers a machine restart that can take ~30 s. During the gap, both v1.0 and v1.1 may serve requests. Acceptable — both versions are valid; the gap doesn't cause errors.
- **Backfill conflicts with new ingestion.** The backfill job is rate-limited (10 gaz/min) so it doesn't starve the live classify queue.

## Validation & acceptance criteria

- **End-to-end staging dry-run.** Quarterly: trigger a fake retraining; complete every step on staging; rollback fires correctly when given a synthetic F1 drop.
- **Auto-rollback < 90 seconds.** From PagerDuty page to v1.0 serving traffic.
- **Backfill correctness.** Audited weekly: 10 random regulations re-classified by hand; v1.1 prediction matches manual label ≥ 90 % of the time.
- **Retraining-run table complete.** Every retraining run has a row with all fields populated (triggered_at, completed_at, F1, rollback_status).

## Cross-references

- Parent: [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md) §3
- Related: [07_M1_2_Fly_io_Deployment_Operations.md](07_M1_2_Fly_io_Deployment_Operations.md), [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) §9 (versioning)
- BUILD phase: BUILD_11 §retraining pipeline, BUILD_12 §auto-rollback
- Code (when shipped): `scripts/retrain.py`, `scripts/deploy_canary.py`, `backend/app/tasks/m1/analytics.py:check_auto_rollback`
