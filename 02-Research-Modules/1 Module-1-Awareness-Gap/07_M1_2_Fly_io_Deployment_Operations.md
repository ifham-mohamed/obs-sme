# 07_M1_2 — Fly.io Deployment Operations

> Companion to [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md) — fly.toml deep-dive, machine sizing, persistent volume layout, health checks, region failover, cost monitoring.
> **Implementation status:** 🔲 Deferred (BUILD_07 — Fly app provisioned + `fly.toml` in repo root)

## Purpose

Parent doc §5.1 shows the basic `fly.toml`. This companion makes the operational reality explicit — machine-size upgrade path, volume layout (current + previous model), the canary traffic-split implementation, and how cost alerts are wired.

## Detailed process

### Step 1 — Production fly.toml (annotated)

```toml
# fly.toml — production
app           = "enigmatrix-m1-classifier"
primary_region = "sin"                              # Singapore — closest to SL
kill_signal   = "SIGINT"
kill_timeout  = 30                                  # grace period for in-flight tasks

[build]
  dockerfile = "Dockerfile.ml"

[mounts]
  source      = "ml_models"                          # Fly volume name
  destination = "/app/storage/models"
  # Volume layout:
  # /app/storage/models/m1/
  #   v1.1/    (current)
  #   v1.0/    (previous — rollback target)
  #   baseline/ (TF-IDF baseline — keep for ablation reporting)

[env]
  M1_MODEL_VERSION          = "v1.1"               # flipped to v1.0 to rollback
  M1_MODEL_CANARY_PCT       = "100"                # 10/50/100 during canary rollout
  M1_PDF_TEXT_THRESHOLD     = "200"
  M1_PDF_SCANNED_THRESHOLD  = "30"

[[services]]
  internal_port = 8000
  protocol      = "tcp"
  auto_stop_machines  = "off"                       # never stop — eliminates cold start
  auto_start_machines = "on"
  min_machines_running = 1

  [[services.ports]]
    port     = 443
    handlers = ["tls", "http"]
  [[services.ports]]
    port     = 80
    handlers = ["http"]
    force_https = true

  [services.concurrency]
    type     = "requests"
    soft_limit = 20
    hard_limit = 25

  [[services.tcp_checks]]
    interval = "15s"
    timeout  = "5s"
    grace_period = "30s"
  [[services.http_checks]]
    interval     = "30s"
    timeout      = "5s"
    method       = "get"
    path         = "/health"
    protocol     = "http"
    tls_skip_verify = false

[[vm]]
  size      = "shared-cpu-1x"
  memory_mb = 1024                                  # see upgrade path below
  cpu_kind  = "shared"
```

### Step 2 — Machine-size upgrade path

| Size | Memory | $/mo | When to use |
|---|---|---|---|
| `shared-cpu-1x` | 256 MB | $2 | NEVER for M1 — too little for ONNX session |
| `shared-cpu-1x` | 1 GB (default) | $3 | Today; up to ~5 gazettes/day |
| `shared-cpu-2x` | 2 GB | $12 | When inference latency p95 exceeds 3 s |
| `shared-cpu-4x` | 4 GB | $24 | When batching needed for > 30 gazettes/day burst |
| `performance-2x` | 8 GB dedicated | $62 | High-throughput steady state (> 100 gaz/day) |
| Multiple `shared-cpu-2x` machines | per-machine cost | additive | Horizontal scale + sticky-session for canary |

The default is `shared-cpu-1x` with 1 GB; upgrade triggered by the SLA alert (parent doc §6).

### Step 3 — Canary traffic split

Implemented in Python — Fly doesn't have native canary routing, so the decision happens at the Celery task level:

```python
# backend/app/tasks/m1/classify_gazette.py
import os, hashlib

def model_version_for_gazette(gazette_id: str) -> str:
    """Hash gazette_id to a 0-99 bucket; route by M1_MODEL_CANARY_PCT."""
    canary_pct = int(os.environ.get("M1_MODEL_CANARY_PCT", "100"))
    if canary_pct == 100:
        return os.environ["M1_MODEL_VERSION"]
    bucket = int(hashlib.sha256(gazette_id.encode()).hexdigest()[:8], 16) % 100
    if bucket < canary_pct:
        return os.environ["M1_MODEL_VERSION"]                       # new
    return os.environ.get("M1_PREVIOUS_MODEL_VERSION", "v1.0")      # old
```

The version is stored on the `m1_regulations` row for A/B analysis. Note: hash-based routing produces **sticky** assignment — the same gazette is always routed to the same version, so re-running the task is idempotent.

### Step 4 — Health checks + region failover

```python
# backend/app/api/v1/health.py
@router.get("/health")
async def health():
    onnx_loaded = inference_engine.session is not None
    redis_ok = redis_client.ping()
    db_ok = (await db.execute(text("SELECT 1"))).scalar() == 1
    if all([onnx_loaded, redis_ok, db_ok]):
        return {"status": "ok", "model_version": MODEL_VERSION}
    raise HTTPException(503, "unhealthy")
```

`/health` is hit every 30 s by Fly. If it fails 3 times consecutively, Fly restarts the machine. If `min_machines_running=1` is breached (machine permanently failing), Fly attempts to migrate to another node in `sin`. If `sin` is unavailable, the secondary region `bom` (Mumbai) takes over automatically when configured with `regions = ["sin", "bom"]` — but failover takes ~3 min during which the API is degraded.

### Step 5 — Cost monitoring

Set Fly budget alerts:

```bash
fly orgs billing notification create --budget 50 --period monthly
```

Alert at 50 % budget consumption + at 80 % (gives time to upgrade plan or pause traffic). Logs to PagerDuty integration in `infra/pagerduty/fly_budget_alerts.yaml`.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Fly.io (chosen) | No cold start; persistent volume; cheap Singapore region | ✅ See parent doc §1.2 | Re-evaluated annually. |
| Always-on (`auto_stop=off`) | No cold-start; constant cost | ✅ Need it for the 2s SLA | If traffic drops below 1 req/hour. |
| Single machine | Simplest | ✅ At < 30 gaz/day | Add second machine when p99 > 5s. |
| Sticky-session hash routing for canary | Idempotent + simple | ✅ One env var controls the split | Move to feature-flag service (LaunchDarkly, GrowthBook) if multiple flags compound. |

## Worked example

A canary rollout flow:

```
[Day 0: deploy v1.1 to volume — but traffic still on v1.0]
fly ssh console -a enigmatrix-m1-classifier
$ cp -r /app/storage/models/m1/v1.0 /app/storage/models/m1/v1.1   # placeholder
$ scp local:storage/models/m1/v1.1/* /app/storage/models/m1/v1.1/

[Day 0: 10% canary]
fly secrets set M1_MODEL_VERSION=v1.1 M1_PREVIOUS_MODEL_VERSION=v1.0 M1_MODEL_CANARY_PCT=10 -a enigmatrix-m1-classifier
# Fly restarts machine; 10% of new gazettes hit v1.1, 90% hit v1.0

[Day 1: review canary metrics]
SELECT model_version, COUNT(*) AS n, AVG(confidence) AS avg_conf
FROM m1_regulations
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY model_version;
#  v1.0  108 gaz  avg_conf 0.81
#  v1.1   12 gaz  avg_conf 0.83  → +2 pp, looks good

[Day 1: ramp to 50%]
fly secrets set M1_MODEL_CANARY_PCT=50 -a enigmatrix-m1-classifier

[Day 2: full rollout if metrics hold]
fly secrets set M1_MODEL_CANARY_PCT=100 -a enigmatrix-m1-classifier

[Day 30: clean up old version]
fly ssh console -a enigmatrix-m1-classifier -C "rm -rf /app/storage/models/m1/v1.0"
```

## Failure modes & edge cases

- **Volume full.** ONNX models are 100 MB (INT8) – 470 MB (FP32). Two versions = ~1 GB; the default Fly volume is 3 GB but baseline + extra calibration data can grow. Mitigation: `fly vol extend` is online + free.
- **Region outage.** `sin` rarely fails. When it does, manual `fly regions set bom` flips region. Documented in runbook.
- **Health check flapping.** A slow-to-load ONNX file makes the first `/health` after deploy fail. Mitigation: `grace_period=30s` on the HTTP check.
- **Budget overrun.** A runaway worker can spike costs. Mitigation: hard limit `concurrency.hard_limit=25` + per-day spend alert.

## Validation & acceptance criteria

- **Deploy + rollback completes in < 90 s.** Measured by CI smoke test.
- **Health check stable.** No `unhealthy` events in normal operation > 1/week.
- **Canary fairness.** Hash-based bucketing produces ~50 % split at `CANARY_PCT=50` (chi-sq test on 1000-gazette sample).
- **Cost.** Monthly Fly spend within $50 budget (or alert).

## Cross-references

- Parent: [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md) §5
- Related: [12_M1_2_Retraining_Deployment_Rollback.md](12_M1_2_Retraining_Deployment_Rollback.md)
- BUILD phase: BUILD_07 §deployment, §canary
- Code (when shipped): `fly.toml`, `backend/app/api/v1/health.py`, `backend/app/tasks/m1/classify_gazette.py`
