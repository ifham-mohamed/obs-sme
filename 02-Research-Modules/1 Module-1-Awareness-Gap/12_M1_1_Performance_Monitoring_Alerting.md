# 12_M1_1 — Performance Monitoring & Alerting

> Companion to [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md) — confidence-drift worked example, SLA dashboard layout, escalation paths, per-sev runbook.
> **Implementation status:** 🔲 Deferred (BUILD_12 — Prometheus + Alertmanager + Grafana + runbook docs)

## Purpose

Parent doc §3 covers performance monitoring at a high level. §4.4 (added in this pass) gives the escalation table. This companion provides the operational depth: a worked KL-divergence drift detection, the Grafana dashboard layout (panel-by-panel), and a per-severity runbook so the on-call has a checklist.

## Detailed process

### Step 1 — Confidence-drift worked example

The detector compares production confidence distribution vs the baseline computed during training:

```python
import numpy as np
from scipy.special import kl_div

# Baseline (computed at training time, stored in model_registry.json)
BASELINE_HIST = np.array([0.02, 0.03, 0.05, 0.08, 0.12, 0.15, 0.18, 0.15, 0.12, 0.10])
# (20 bins from 0.0 to 1.0; stored normalised)

def check_confidence_drift(production_confidences: list[float]) -> dict:
    bins = np.linspace(0, 1, 21)
    prod_hist, _ = np.histogram(production_confidences, bins=bins, density=True)
    prod_hist = prod_hist / (prod_hist.sum() + 1e-8)
    divergence = float(kl_div(prod_hist + 1e-8, BASELINE_HIST + 1e-8).sum())
    return {
        "kl_divergence": divergence,
        "drift_detected": divergence > 0.15,
        "production_low_conf_share": float((np.array(production_confidences) < 0.50).mean()),
    }
```

A 30-day production-data example:

```
Baseline (training): low-conf < 0.5  share = 8%
                     KL vs baseline = 0.00

Day 1–30 production: low-conf share = 22% (gradual increase)
                     KL = 0.18  → DRIFT DETECTED
                     
Interpretation: production gazettes are systematically harder than training set.
Likely cause: a new gazette type appeared (e.g. supply-chain regulation).
Action: open ticket "investigate Day-1 to Day-30 needs_review queue".
```

### Step 2 — Grafana dashboard layout (`m1_classifier_health`)

| Row | Panels (left → right) | Source |
|---|---|---|
| 1 — SLAs | (a) Uptime gauge (target 99.9%) (b) p95 inference latency (c) Pipeline failure rate 7d | UptimeRobot + Prometheus |
| 2 — Confidence drift | (a) KL divergence sparkline (b) Low-conf share | Daily Celery task results |
| 3 — Throughput | (a) Gazettes/hour (b) Celery queue depth per queue | Prometheus + Celery Flower |
| 4 — Model quality | (a) Expert-verified F1 (last 90d) (b) Confidence histogram | `m1_pipeline_audits` |
| 5 — Per-language slice F1 | EN / SI / TA (rolling) | Same |
| 6 — Recent alerts | List of recent Prometheus alerts | Alertmanager |

JSON definition stored at `infra/grafana/dashboards/m1_classifier_health.json` — committed to repo for reproducibility.

### Step 3 — Severity matrix (recap from parent doc §4.4)

| Severity | Example trigger | Channel | SLA |
|---|---|---|---|
| `info` | `mixed` rate > 5 % | Slack `#enigmatrix-info` | Best effort |
| `warn` | Extraction failure > 10 % | Slack `#enigmatrix-alerts` + email | 24 h |
| `error` | Two metrics warn simultaneously | Slack + email + PagerDuty low | 4 h |
| `critical` | Production F1 drop > 5 pp / 24 h | PagerDuty high | 30 min |

### Step 4 — Per-severity runbook

**`info` runbook.** No action required. The data team reviews `info` Slack channel weekly to spot trends.

**`warn` runbook.**
1. Open the alert; read the trigger metric + the threshold.
2. Open Grafana dashboard `m1_classifier_health`; inspect related panels.
3. Check the `m1_pipeline_errors` table for the failing class (extraction / classification / dispatch).
4. If error count > 50 per hour → escalate to `error`.
5. Otherwise: open a Jira ticket, assign to the M1 owner, link the alert.

**`error` runbook.**
1. PagerDuty fires; on-call gets notified.
2. On-call confirms acknowledgement within 4 h.
3. Inspect the Grafana dashboard + Slack channel.
4. If the root cause is in Stage A (Scrapy / portal watcher) → see if a source URL has changed.
5. If in Stage B (extraction) → check the `extraction_method` distribution for an OCR spike (signals a new gazette format).
6. If in Stage D (classifier) → check confidence histogram; if shifted left, escalate to `critical` and consider rollback.
7. Communicate status in `#enigmatrix-incidents` Slack every 30 minutes.

**`critical` runbook.**
1. PagerDuty fires *high urgency*; on-call gets paged.
2. On-call acknowledges within 30 minutes.
3. **Immediate action:** if F1 dropped > 5 pp in 24 h, *automatic rollback* fires (per [12_M1_2_Retraining_Deployment_Rollback.md](12_M1_2_Retraining_Deployment_Rollback.md)) — confirm rollback succeeded.
4. If rollback didn't fire (manual mode), execute: `fly secrets set M1_MODEL_VERSION=<previous> M1_MODEL_CANARY_PCT=0`.
5. Engineering manager paged at 30-minute mark if not acknowledged.
6. Post-mortem within 48 h, written to `research/incidents/`.

### Step 5 — Alertmanager routing rules (excerpt)

```yaml
# infra/prometheus/alertmanager.yml
route:
  receiver: 'enigmatrix-info'
  group_by: ['alertname']
  routes:
    - match: { severity: critical }
      receiver: 'pagerduty-high'
    - match: { severity: error }
      receiver: 'pagerduty-low'
    - match: { severity: warn }
      receiver: 'enigmatrix-alerts-slack'

receivers:
  - name: 'pagerduty-high'
    pagerduty_configs:
      - service_key: ${PAGERDUTY_HIGH_KEY}
  - name: 'enigmatrix-alerts-slack'
    slack_configs:
      - api_url: ${SLACK_WEBHOOK_URL}
        channel: '#enigmatrix-alerts'
```

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Prometheus + Alertmanager + Grafana (chosen) | Industry standard; self-hosted | ✅ Open-source; aligned with the Session-14 audit-log pattern | If we adopt a managed obs vendor (Datadog, New Relic). |
| KL divergence (chosen) for drift | Standard distribution-shift metric | ✅ Works on histogram; easy to interpret | If KL is noisy at small N, switch to PSI (Population Stability Index). |
| 0.15 KL threshold | Empirically chosen | ✅ Conservative — alerts before catastrophic drift | Re-tune after 6 months of production data. |
| PagerDuty | Standard on-call platform | ✅ Tied to the project's incident-management workflow | Switch to Opsgenie if PagerDuty pricing escalates. |

## Worked example

A typical `warn` alert flow:

```
[2026-05-20 13:00] Alertmanager fires:
   m1_extraction_failure_rate_7d = 12% (threshold 10%)
   Slack #enigmatrix-alerts: "WARN: M1 extraction failures elevated (12% over 7 days)"

[2026-05-20 14:30] On-call (M1 team lead) opens the alert during business hours
   - Grafana dashboard panel "Pipeline failure rate" shows spike on 2026-05-15
   - m1_pipeline_errors table query:
       SELECT reason, COUNT(*) FROM m1_pipeline_errors
       WHERE created_at >= NOW() - INTERVAL '7 days' GROUP BY reason
   - Top reason: 'tesseract_subprocess_timeout' (12 occurrences in last 7 days)
   - Hypothesis: scanned-PDF volume spiked

[2026-05-20 15:00] On-call action:
   - Open Jira M1-247: "Investigate scanned-PDF surge week of May 13"
   - Check: 18 of last 30 PDFs are 'scanned' type vs baseline 4/30 → confirmed surge
   - Likely cause: a backlog of older gazettes being added by a recent portal update
   - No immediate action; create monitoring follow-up to ensure surge subsides

[2026-05-25] Surge ends; Tesseract timeout count returns to <2/week
[2026-05-25] Jira M1-247 closed with no fix needed
```

## Failure modes & edge cases

- **Alert fatigue.** Too many `info` alerts → on-call ignores even `error`. Mitigation: severity-based channel routing; `info` goes only to a separate Slack channel reviewed weekly.
- **False positive on drift.** A small sample (< 100 production gazettes) gives noisy KL. Mitigation: only fire drift alerts after sample N > 200.
- **PagerDuty outage.** Critical alerts not delivered. Mitigation: secondary channel via SMS to on-call's phone.
- **Stale dashboard.** Grafana shows yesterday's data if Prometheus data pipeline is broken. Detected by a "Grafana liveness" widget on the dashboard itself.

## Validation & acceptance criteria

- **All 4 severities tested.** Quarterly: simulate each level on staging; confirm routing + on-call response.
- **Drift detector accuracy.** Synthetic-drift test: inject 20 % low-confidence predictions for 7 days → KL > 0.15 within 3 days.
- **Runbook freshness.** Quarterly review by the M1 lead; sign-off in `research/incidents/runbook_review_<YYYY-QN>.md`.
- **MTTR target.** Mean Time To Resolution for `error` < 4 h; for `critical` < 1 h. Tracked in PagerDuty.

## Cross-references

- Parent: [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md) §3, §4.4
- Related: [12_M1_2_Retraining_Deployment_Rollback.md](12_M1_2_Retraining_Deployment_Rollback.md), [06_M1_2_Slice_Analysis_Framework.md](06_M1_2_Slice_Analysis_Framework.md)
- BUILD phase: BUILD_12 §monitoring stack
- Code (when shipped): `infra/prometheus/`, `infra/grafana/dashboards/`, `backend/app/tasks/m1/analytics.py`
