# BUILD 15 — Observability & Testing

> **Goal:** Make Enigmatrix observable in production and verifiable in CI. Every request emits structured logs with a correlation ID, every module exports Prometheus metrics, every cross-service call is traced through OpenTelemetry, every dashboard renders against live data, and every layer of the stack is covered by an automated test suite that runs on every pull request.
>
> **Read first:** BUILD_03 (backend API + structlog wiring), BUILD_04 (audit_log table + storage), BUILD_07 (Module 1 metric naming convention), BUILD_14 (deployment topology, where Prometheus + Grafana + Tempo run).

> **Scope:** logs, metrics, tracing, alerts, dashboards, and the four-layer test pyramid (unit / integration / e2e / load). ML data validation belongs to this file too — pandera schemas, golden-set regression tests, and PSI drift alerts all live alongside the rest of the observability surface because they share the same dashboards and the same on-call rotation.

---

## 1. Structured logging (recap from BUILD_03)

BUILD_03 prompt 2 already wired `structlog` and a `correlation_id` contextvar. This section nails down the contract every later module must follow.

**Contract:**
- Every log line is JSON, single line, UTF-8.
- Every log line contains: `timestamp`, `level`, `event`, `correlation_id`, `service`, `module`.
- `correlation_id` is generated at the edge (FastAPI middleware) if the inbound request lacks an `X-Correlation-ID` header, and propagated outbound on every HTTP/Celery call.
- Logs go to stdout only. Docker captures stdout. The cluster log shipper (Promtail in the BUILD_14 topology) forwards to Loki. No file logging, no syslog.

**Middleware (already in `backend/app/core/logging.py` from BUILD_03 — repeated here for reference):**

```python
# backend/app/core/middleware.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.logging import correlation_id_var, logger

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cid = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        token = correlation_id_var.set(cid)
        try:
            response = await call_next(request)
            response.headers["x-correlation-id"] = cid
            return response
        finally:
            correlation_id_var.reset(token)
```

**Outbound propagation — httpx client:**

```python
# backend/app/core/http_client.py
import httpx
from app.core.logging import correlation_id_var

async def request(method: str, url: str, **kwargs) -> httpx.Response:
    headers = kwargs.pop("headers", {}) or {}
    headers.setdefault("x-correlation-id", correlation_id_var.get(""))
    async with httpx.AsyncClient(timeout=30) as client:
        return await client.request(method, url, headers=headers, **kwargs)
```

**Celery task header propagation:**

```python
# backend/app/workers/celery_app.py
from celery.signals import before_task_publish, task_prerun
from app.core.logging import correlation_id_var

@before_task_publish.connect
def _inject_cid(headers=None, **_):
    headers["correlation_id"] = correlation_id_var.get("")

@task_prerun.connect
def _restore_cid(task=None, **_):
    cid = (task.request.headers or {}).get("correlation_id", "")
    correlation_id_var.set(cid)
```

---

## 2. Metrics — Prometheus

We use [`prometheus-fastapi-instrumentator`](https://github.com/trallnag/prometheus-fastapi-instrumentator) for the standard HTTP histograms plus a thin `app.core.metrics` module for the four module-specific counters.

**Standard exposure:**

```python
# backend/app/core/metrics.py
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

# Module 1 — Awareness / gazette ingestion
m1_gazettes_ingested_total = Counter(
    "m1_gazettes_ingested_total",
    "Number of gazette items ingested by source",
    labelnames=("source", "status"),
)

# Module 2 — RAG
m2_rag_queries_total = Counter(
    "m2_rag_queries_total",
    "Number of RAG queries served",
    labelnames=("collection", "cache"),
)
m2_rag_retrieval_latency_seconds = Histogram(
    "m2_rag_retrieval_latency_seconds",
    "ChromaDB retrieval latency",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Module 3 — Predictive
m3_predictions_total = Counter(
    "m3_predictions_total",
    "Number of model predictions served",
    labelnames=("model", "outcome"),
)
m3_inference_latency_seconds = Histogram(
    "m3_inference_latency_seconds",
    "Model inference latency",
    labelnames=("model",),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

# Module 4 — Verification
m4_claims_verified_total = Counter(
    "m4_claims_verified_total",
    "Number of claims verified",
    labelnames=("verdict",),  # supported | refuted | not_enough_info
)

def install_metrics(app) -> None:
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/metrics", "/healthz"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
```

**Wiring at app startup:**

```python
# backend/app/main.py (excerpt)
from app.core.metrics import install_metrics
from app.core.middleware import CorrelationIdMiddleware

app.add_middleware(CorrelationIdMiddleware)
install_metrics(app)
```

**Module use sites — examples:**

```python
# Module 1 ingest worker
m1_gazettes_ingested_total.labels(source="federal_register", status="ok").inc(batch_size)

# Module 2 retriever
with m2_rag_retrieval_latency_seconds.time():
    docs = await chroma.query(...)
m2_rag_queries_total.labels(collection=name, cache="miss").inc()

# Module 3 inference
with m3_inference_latency_seconds.labels(model="lstm_v3").time():
    pred = model.predict(features)
m3_predictions_total.labels(model="lstm_v3", outcome=pred.label).inc()

# Module 4 verifier
m4_claims_verified_total.labels(verdict=verdict.value).inc()
```

**VM and host metrics:** `node_exporter` runs on every host (BUILD_14 systemd unit). CPU, memory, disk, file descriptor counts, and network are collected automatically.

**Push gateway:** only used for ad-hoc training runs that finish before Prometheus' scrape interval. The standard nightly retraining job in BUILD_11 pushes `m3_train_run_duration_seconds`, `m3_train_loss`, `m3_train_eval_auc` to a `pushgateway` instance under job label `ml_training`.

**Scrape config (excerpt of `infra/prometheus/prometheus.yml`):**

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: enigmatrix-backend
    metrics_path: /metrics
    static_configs:
      - targets: ["backend:8000"]
  - job_name: enigmatrix-celery
    metrics_path: /metrics
    static_configs:
      - targets: ["celery-exporter:9540"]
  - job_name: node
    static_configs:
      - targets: ["node-exporter:9100"]
  - job_name: pushgateway
    honor_labels: true
    static_configs:
      - targets: ["pushgateway:9091"]

rule_files:
  - /etc/prometheus/alerts/*.yml
```

---

## 3. Tracing — OpenTelemetry

We trace every backend request end-to-end: HTTP entry → SQLAlchemy queries → outbound httpx calls → Celery task spans (linked, not nested, since they cross a queue boundary).

**Dependencies:**

```
opentelemetry-api
opentelemetry-sdk
opentelemetry-exporter-otlp-proto-grpc
opentelemetry-instrumentation-fastapi
opentelemetry-instrumentation-sqlalchemy
opentelemetry-instrumentation-httpx
opentelemetry-instrumentation-celery
```

**Bootstrap:**

```python
# backend/app/core/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor

from app.core.config import settings

def install_tracing(app, engine) -> None:
    sample_ratio = 0.01 if settings.ENV == "production" else 1.0
    provider = TracerProvider(
        resource=Resource.create({"service.name": "enigmatrix-backend",
                                  "service.namespace": "enigmatrix",
                                  "deployment.environment": settings.ENV}),
        sampler=TraceIdRatioBased(sample_ratio),
    )
    provider.add_span_processor(BatchSpanProcessor(
        OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_ENDPOINT, insecure=True)
    ))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app, excluded_urls="healthz,metrics")
    SQLAlchemyInstrumentor().instrument(engine=engine)
    HTTPXClientInstrumentor().instrument()
    CeleryInstrumentor().instrument()
```

The exporter target is **Tempo** in the BUILD_14 cluster topology. Jaeger is used only for local docker-compose development and points at the same OTLP endpoint on `localhost:4317`.

**Trace ID ↔ correlation ID join:** the OTel FastAPI instrumentor emits a `trace_id` log attribute when used with structlog's processors; we add a structlog processor that copies the active span's trace ID into every log record, so a single Grafana panel can pivot from a slow trace to its log lines:

```python
# backend/app/core/logging.py (excerpt)
from opentelemetry import trace as otel_trace

def add_trace_ids(_logger, _name, event_dict):
    span = otel_trace.get_current_span()
    ctx = span.get_span_context()
    if ctx.is_valid:
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict
```

---

## 4. Grafana dashboards

Four dashboards are committed to `infra/grafana/dashboards/` and provisioned automatically by Grafana's filesystem provider.

| Dashboard | UID | Panels |
|-----------|-----|--------|
| `enigmatrix-ingest` | `eg-ingest` | items/min by source, error rate by source, lag (now − last_ingested_at), backlog depth |
| `enigmatrix-models` | `eg-models` | inference p50/p95/p99 by model, throughput, PSI drift, training run AUC |
| `enigmatrix-rag` | `eg-rag` | retrieval p95, queries/sec, hit-rate (cache vs Chroma), RAGAS faithfulness/context_precision |
| `enigmatrix-ops` | `eg-ops` | HTTP 5xx rate, request rate by route, DB pool saturation, Celery queue depth, container CPU/RAM |

**Compact dashboard JSON example (`enigmatrix-ingest`):**

```json
{
  "uid": "eg-ingest",
  "title": "Enigmatrix - Ingest",
  "schemaVersion": 39,
  "tags": ["enigmatrix", "module-1"],
  "panels": [
    {
      "type": "timeseries",
      "title": "Items ingested per minute (by source)",
      "targets": [{
        "expr": "sum by (source) (rate(m1_gazettes_ingested_total{status=\"ok\"}[1m])) * 60",
        "legendFormat": "{{source}}"
      }]
    },
    {
      "type": "stat",
      "title": "Ingest error rate (5m)",
      "targets": [{
        "expr": "sum(rate(m1_gazettes_ingested_total{status=\"error\"}[5m])) / sum(rate(m1_gazettes_ingested_total[5m]))"
      }],
      "fieldConfig": {"defaults": {"unit": "percentunit",
        "thresholds": {"steps": [{"color": "green", "value": 0},
                                  {"color": "yellow", "value": 0.01},
                                  {"color": "red", "value": 0.05}]}}}
    },
    {
      "type": "timeseries",
      "title": "Source freshness (seconds since last item)",
      "targets": [{
        "expr": "time() - max by (source) (m1_last_ingested_timestamp)"
      }]
    }
  ]
}
```

The other three dashboards follow the same structure; each is committed in full under `infra/grafana/dashboards/`.

---

## 5. Alertmanager rules

`infra/prometheus/alerts/enigmatrix.yml`:

```yaml
groups:
  - name: enigmatrix-backend
    rules:
      - alert: BackendHighErrorRate
        expr: |
          sum(rate(http_requests_total{job="enigmatrix-backend",status=~"5.."}[5m]))
            / sum(rate(http_requests_total{job="enigmatrix-backend"}[5m])) > 0.01
        for: 5m
        labels: { severity: page }
        annotations:
          summary: "Backend 5xx rate >1% for 5m"
          runbook: "https://enigmatrix.dev/runbooks/backend-5xx"

      - alert: CeleryQueueDepthHigh
        expr: max(celery_queue_length) > 1000
        for: 10m
        labels: { severity: page }
        annotations:
          summary: "Celery queue depth >1000 for 10m"

      - alert: ChromaDBUnreachable
        expr: up{job="chromadb"} == 0
        for: 2m
        labels: { severity: page }
        annotations:
          summary: "ChromaDB scrape target down"

  - name: enigmatrix-ml
    rules:
      - alert: ModelDriftPSI
        expr: max by (model, feature) (m3_feature_psi) > 0.25
        for: 30m
        labels: { severity: ticket }
        annotations:
          summary: "PSI > 0.25 on {{ $labels.model }} / {{ $labels.feature }}"
          runbook: "https://enigmatrix.dev/runbooks/drift"

      - alert: DailyIngestMissed
        # the daily job is expected by 06:30 UTC; this fires at 07:00 UTC if no success
        expr: |
          (time() - max(m1_last_successful_run_timestamp{job="ingest-daily"})) > 90000
        for: 5m
        labels: { severity: page }
        annotations:
          summary: "Daily ingest missed window"
```

Alertmanager routes `severity=page` to PagerDuty, `severity=ticket` to a GitHub Issues webhook, and everything else to Slack `#enigmatrix-alerts`.

---

## 6. Backend tests (pytest)

**Layout:**

```
backend/app/tests/
  conftest.py
  unit/
    test_routing.py
    test_schemas.py
    test_security.py
  integration/
    conftest.py
    test_users_repo.py
    test_rag_pipeline.py
    test_claims_pipeline.py
  e2e/
    test_verify_claim_flow.py
```

**Unit tests:** plain `pytest` — no DB, no network. Anything that needs a fixture beyond a function call belongs in `integration/`.

**Integration tests:** real Postgres + real ChromaDB via `testcontainers-python`. The container fixture is session-scoped; the per-test database is created from a template inside that container so each test gets a clean schema in <100 ms.

**`backend/app/tests/integration/conftest.py`:**

```python
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
from testcontainers.chroma import ChromaContainer  # 0.0.x ships this; otherwise GenericContainer

from app.main import app
from app.core.db import Base, get_db
from app.core.config import settings


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def pg_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def chroma_container():
    with ChromaContainer("chromadb/chroma:0.5.5") as ch:
        yield ch


@pytest_asyncio.fixture(scope="session")
async def engine(pg_container):
    url = pg_container.get_connection_url().replace("psycopg2", "asyncpg")
    eng = create_async_engine(url, future=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncSession:
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.connect() as conn:
        trans = await conn.begin()
        async with Session(bind=conn) as session:
            yield session
        await trans.rollback()


@pytest_asyncio.fixture
async def client(db_session, chroma_container) -> AsyncClient:
    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    settings.CHROMA_HOST = chroma_container.get_container_host_ip()
    settings.CHROMA_PORT = int(chroma_container.get_exposed_port(8000))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()
```

**Sample integration test:**

```python
# backend/app/tests/integration/test_claims_pipeline.py
import pytest

@pytest.mark.asyncio
async def test_verify_claim_returns_supported_for_well_known_fact(client):
    r = await client.post(
        "/api/v1/verify/claim",
        json={"text": "The capital of France is Paris."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] in {"supported", "refuted", "not_enough_info"}
    assert "evidence" in body and len(body["evidence"]) >= 1
    assert r.headers.get("x-correlation-id")
```

**Coverage gate (`pyproject.toml`):**

```toml
[tool.coverage.report]
fail_under = 80
exclude_lines = ["pragma: no cover", "raise NotImplementedError"]
```

CI invocation: `pytest --cov=app --cov-report=xml --cov-fail-under=80`.

---

## 7. Frontend tests

**Vitest** for components and utility functions; **Playwright** for full user journeys.

**`frontend/vitest.config.ts`:**

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      thresholds: { lines: 70, branches: 60, functions: 70, statements: 70 },
    },
  },
});
```

**Component test example:**

```ts
// frontend/src/components/__tests__/VerdictBadge.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { VerdictBadge } from "../VerdictBadge";

describe("VerdictBadge", () => {
  it("renders supported in green", () => {
    render(<VerdictBadge verdict="supported" />);
    expect(screen.getByText(/supported/i)).toHaveClass("text-green-700");
  });
});
```

**Playwright e2e — `frontend/tests/e2e/verify-claim.spec.ts`:**

```ts
import { test, expect } from "@playwright/test";

test("login then verify a claim from the dashboard", async ({ page }) => {
  await page.goto("/login");
  await page.fill("[name=email]", "qa@enigmatrix.dev");
  await page.fill("[name=password]", "qa-password");
  await page.click("button[type=submit]");

  await expect(page).toHaveURL(/\/dashboard/);
  await page.click("text=Verify a claim");
  await page.fill("textarea[name=claim]", "Water boils at 100C at sea level.");
  await page.click("button:has-text('Verify')");

  await expect(page.locator("[data-testid=verdict]")).toBeVisible({ timeout: 15_000 });
  await expect(page.locator("[data-testid=evidence-list] > li")).toHaveCount(3, { timeout: 15_000 });
});
```

CI runs Playwright against a docker-compose stack (backend + frontend + postgres + chroma) brought up by the workflow's `services:` block. Traces and videos are uploaded as artifacts on failure.

---

## 8. ML tests

Three flavours: **schema validation** (pandera, runs at training time and in CI), **regression on a golden set** (load the model artifact, score, compare against a tolerance), and **smoke** (one assertion per module that the production pipeline imports cleanly).

**`ml/common/schemas.py`:**

```python
import pandera as pa
from pandera.typing import DataFrame, Series

class ClaimsTrainingSchema(pa.DataFrameModel):
    claim_id: Series[str] = pa.Field(unique=True)
    text: Series[str] = pa.Field(str_length={"min_value": 5, "max_value": 4096})
    source: Series[str] = pa.Field(isin=["federal_register", "ap", "reuters", "wiki"])
    label: Series[str] = pa.Field(isin=["supported", "refuted", "not_enough_info"])
    published_at: Series[pa.DateTime]

    class Config:
        strict = True
        coerce = True


def validate_training_frame(df) -> DataFrame[ClaimsTrainingSchema]:
    return ClaimsTrainingSchema.validate(df, lazy=True)
```

**Golden-set regression test — `ml/tests/test_model_regression.py`:**

```python
import json
import pytest
from pathlib import Path
import pandas as pd
import joblib
from sklearn.metrics import roc_auc_score, f1_score

GOLDEN = Path("ml/tests/golden/claims_v3.parquet")
MODEL = Path("ml/artifacts/claims_classifier_v3.joblib")
TOLERANCE = {"auc_min": 0.84, "f1_min": 0.78}


@pytest.mark.skipif(not MODEL.exists(), reason="model artifact not present")
def test_claims_classifier_meets_baseline():
    df = pd.read_parquet(GOLDEN)
    model = joblib.load(MODEL)
    proba = model.predict_proba(df["text"].tolist())[:, 1]
    pred = (proba >= 0.5).astype(int)

    auc = roc_auc_score(df["label_bin"], proba)
    f1 = f1_score(df["label_bin"], pred)

    assert auc >= TOLERANCE["auc_min"], f"AUC regressed: {auc:.3f}"
    assert f1 >= TOLERANCE["f1_min"], f"F1 regressed: {f1:.3f}"
```

The golden set is tagged in DVC; CI checks out the version pinned in `ml/tests/golden.lock` so the tolerance is meaningful across reruns. Smoke tests live at `ml/tests/test_smoke_<module>.py` and only assert that the module's `train.py` imports and that its CLI prints help.

---

## 9. Load tests — k6

`infra/loadtest/login.js` and `infra/loadtest/claim_verify.js`. Target: **100 RPS sustained for 5 minutes**, **p95 < 800 ms**.

**`infra/loadtest/claim_verify.js`:**

```js
import http from "k6/http";
import { check, sleep } from "k6";
import { Trend, Rate } from "k6/metrics";

const BASE = __ENV.BASE_URL || "https://staging.enigmatrix.dev";
const TOKEN = __ENV.AUTH_TOKEN;

const verifyLatency = new Trend("verify_latency_ms", true);
const verifyErrors = new Rate("verify_errors");

export const options = {
  scenarios: {
    sustained: {
      executor: "constant-arrival-rate",
      rate: 100,
      timeUnit: "1s",
      duration: "5m",
      preAllocatedVUs: 200,
      maxVUs: 400,
    },
  },
  thresholds: {
    "verify_latency_ms": ["p(95)<800"],
    "verify_errors": ["rate<0.01"],
    "http_req_failed": ["rate<0.01"],
  },
};

const claims = [
  "The capital of France is Paris.",
  "Water boils at 100C at sea level.",
  "The Eiffel Tower is in Berlin.",
  "Mount Everest is the tallest mountain on Earth.",
];

export default function () {
  const text = claims[Math.floor(Math.random() * claims.length)];
  const res = http.post(
    `${BASE}/api/v1/verify/claim`,
    JSON.stringify({ text }),
    {
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${TOKEN}`,
        "X-Correlation-Id": `k6-${__VU}-${__ITER}`,
      },
      timeout: "30s",
    },
  );
  verifyLatency.add(res.timings.duration);
  const ok = check(res, {
    "status is 200": (r) => r.status === 200,
    "has verdict": (r) => r.json("verdict") !== undefined,
  });
  verifyErrors.add(!ok);
  sleep(0.1);
}
```

**`infra/loadtest/login.js`:**

```js
import http from "k6/http";
import { check } from "k6";

export const options = {
  vus: 50,
  duration: "1m",
  thresholds: { "http_req_duration": ["p(95)<400"] },
};

export default function () {
  const res = http.post(
    `${__ENV.BASE_URL}/api/v1/auth/login`,
    JSON.stringify({
      email: `loadtest+${__VU}@enigmatrix.dev`,
      password: __ENV.LOADTEST_PASSWORD,
    }),
    { headers: { "Content-Type": "application/json" } },
  );
  check(res, {
    "200": (r) => r.status === 200,
    "token present": (r) => !!r.json("access_token"),
  });
}
```

The k6 jobs run nightly against staging and on demand against PR preview environments. Results post to a Grafana k6 datasource for trend tracking.

---

## 10. Coverage gates (CI summary)

| Layer | Tool | Threshold | CI step |
|-------|------|-----------|---------|
| Backend unit + integration | pytest + coverage.py | lines ≥80% | `pytest --cov=app --cov-fail-under=80` |
| Frontend components | Vitest v8 coverage | lines ≥70% | `pnpm test --coverage` |
| Frontend e2e | Playwright | green on auth + claim-check + dashboard flows | `pnpm playwright test` |
| ML | pandera + golden set | ≥1 smoke test per module; AUC/F1 within tolerance | `pytest ml/tests` |
| Load | k6 | p95 < 800 ms at 100 RPS, error rate < 1% | nightly job + manual workflow |

PRs that drop backend coverage below 80% or frontend below 70% are blocked by the GitHub Actions check.

---

## Acceptance Criteria

1. Every backend HTTP request emits at least one structured log line containing `correlation_id`, `trace_id`, `service`, `module`, and the request method/path/status.
2. `/metrics` on the backend exposes all four module counters (`m1_gazettes_ingested_total`, `m2_rag_queries_total`, `m3_predictions_total`, `m4_claims_verified_total`) plus the `prometheus-fastapi-instrumentator` HTTP histograms.
3. Grafana renders all four dashboards (`enigmatrix-ingest`, `enigmatrix-models`, `enigmatrix-rag`, `enigmatrix-ops`) with live data on staging.
4. A single trace in Tempo links a `/api/v1/verify/claim` request through FastAPI → SQLAlchemy → Chroma httpx → model inference span, with the correlation ID present as a span attribute on every span.
5. `pytest` in CI achieves ≥80% line coverage on `backend/app/` and the run completes in under 6 minutes.
6. The Playwright suite passes the login → dashboard → claim-check flow on a clean docker-compose stack.
7. Vitest coverage on `frontend/src/` is ≥70% lines, ≥60% branches.
8. The pandera schema validation runs in the training pipeline and the golden-set regression test enforces the configured AUC and F1 tolerances.
9. The k6 `claim_verify.js` scenario sustains 100 RPS for 5 minutes against staging with p95 < 800 ms and error rate < 1%.
10. Alertmanager fires the `BackendHighErrorRate` and `ModelDriftPSI` alerts in a rehearsed game-day exercise and they reach PagerDuty within 90 seconds.

---

## Claude Prompts

### Prompt 1 — Add Prometheus + OpenTelemetry to the backend

```
You are working in the Enigmatrix FastAPI backend at backend/app/.
Goal: add Prometheus metrics and OpenTelemetry tracing without breaking
existing structlog correlation IDs from BUILD_03.

Tasks:
1. Add to backend/pyproject.toml:
   prometheus-fastapi-instrumentator, prometheus-client,
   opentelemetry-api, opentelemetry-sdk,
   opentelemetry-exporter-otlp-proto-grpc,
   opentelemetry-instrumentation-fastapi,
   opentelemetry-instrumentation-sqlalchemy,
   opentelemetry-instrumentation-httpx,
   opentelemetry-instrumentation-celery.
2. Create backend/app/core/metrics.py defining the four module counters
   (m1_gazettes_ingested_total, m2_rag_queries_total,
   m3_predictions_total, m4_claims_verified_total) plus the latency
   histograms shown in BUILD_15 section 2, and an install_metrics(app).
3. Create backend/app/core/tracing.py exposing install_tracing(app, engine)
   with TraceIdRatioBased(0.01 in production, 1.0 otherwise), OTLP gRPC
   exporter, and FastAPI/SQLAlchemy/httpx/Celery instrumentors.
4. Add a structlog processor add_trace_ids in backend/app/core/logging.py
   that copies the active OTel span's trace_id and span_id into every log
   record. Insert it after the existing correlation_id processor.
5. Wire install_metrics and install_tracing in backend/app/main.py after
   the CorrelationIdMiddleware is added. Pass the SQLAlchemy engine from
   backend/app/core/db.py.
6. Add unit tests at backend/app/tests/unit/test_metrics.py asserting:
   - GET /metrics returns 200 and contains "m4_claims_verified_total".
   - install_metrics is idempotent.

Constraints:
- Do not change existing endpoint behaviour.
- Do not log secrets; OTLP endpoint comes from settings.OTEL_EXPORTER_ENDPOINT.
- /metrics and /healthz must be excluded from tracing and from
  http_requests_total histograms.

Deliverables: the new files, the edited main.py and logging.py, the new
test file, and a one-paragraph note in the PR body listing the four
counter names so reviewers can grep dashboards.
```

### Prompt 2 — Testcontainers integration fixture for Postgres + Chroma

```
You are setting up backend integration tests for Enigmatrix.

Goal: build backend/app/tests/integration/conftest.py that gives every
async test a clean database and a live ChromaDB, using
testcontainers-python and pytest-asyncio.

Requirements:
1. Session-scoped PostgresContainer("postgres:16-alpine"). Build an async
   engine from its connection URL (replace psycopg2 with asyncpg) and
   create_all() Base.metadata once.
2. Session-scoped ChromaContainer("chromadb/chroma:0.5.5"). Override
   settings.CHROMA_HOST and settings.CHROMA_PORT inside the client fixture.
3. Function-scoped db_session that opens a connection, begins a
   transaction, yields an AsyncSession bound to that connection, and
   rolls back on teardown so tests are isolated.
4. Function-scoped client that overrides app.dependency_overrides[get_db]
   to return db_session, builds an httpx.AsyncClient on
   ASGITransport(app=app), and clears overrides on teardown.
5. Custom session-scoped event_loop fixture so pytest-asyncio works with
   session-scoped async fixtures.
6. Add backend/app/tests/integration/test_claims_pipeline.py with one
   test that POSTs /api/v1/verify/claim and asserts the response contains
   a verdict and an x-correlation-id header.

Constraints:
- pytest-asyncio mode=auto in pyproject.toml.
- Do not pull in real OpenAI keys; mock any external LLM with respx if
  the verify endpoint calls one.
- Tests must run on a fresh checkout with only `pytest` invoked.

Deliverables: conftest.py, the new test file, any pyproject.toml edits,
and a short README block at backend/app/tests/integration/README.md
explaining how to run only this layer.
```

### Prompt 3 — k6 load script for /api/v1/verify/claim

```
Generate infra/loadtest/claim_verify.js for the Enigmatrix backend.

Requirements:
1. Use k6's constant-arrival-rate executor at 100 RPS for 5 minutes,
   preAllocatedVUs=200, maxVUs=400.
2. Read BASE_URL and AUTH_TOKEN from __ENV.
3. Send POST /api/v1/verify/claim with a JSON body chosen randomly from
   a list of at least four sample claims (mix of true/false/ambiguous).
4. Set an X-Correlation-Id header of the form `k6-${__VU}-${__ITER}` so
   load test traffic is filterable in Grafana.
5. Define custom metrics verify_latency_ms (Trend) and verify_errors (Rate).
6. Thresholds: verify_latency_ms p(95)<800, verify_errors rate<0.01,
   http_req_failed rate<0.01.
7. Use check() to assert status === 200 and that the response body has a
   "verdict" field.
8. Add a setup() that hits /healthz once and aborts with fail() if
   non-200.

Also generate infra/loadtest/login.js as a 50-VU/1-minute warm-up
that issues POST /api/v1/auth/login and checks that access_token is in
the response.

Deliverables: the two .js files plus a short README.md at
infra/loadtest/README.md showing the exact `k6 run` invocations and the
required environment variables.
```

---

**Prev:** BUILD_14_Deployment_Cloud.md  ·  **Next:** BUILD_16_Progress_Tracker_Template.md
