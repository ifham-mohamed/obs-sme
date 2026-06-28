---
tags: [m1, phase-2, slice-5, measurement, scoring, celery]
date: 2026-05-23
status: 🔲 not started
estimated-effort: 1 week
prerequisites: slices 3 + 4 complete (m1_dataset_rows populated for both baseline and candidate)
---

# 06 — Slice 5: Measurement Engine (Backend)

## What this slice produces

Two new tables (`m1_measurement_runs`, `m1_measurement_scores`), one Alembic migration (`202605240004`), one Celery task (`run_measurement`), six new API endpoints under `/api/v1/m1/measurements`, and zero frontend code (slice 6 builds the UI). The engine reads any two sealed `m1_dataset_versions`, runs the field-metric registry from slice 1, and writes a scorecard.

The engine is pure: it does not modify the versions being scored, never retriggers extraction, never touches `m1_regulations`. Running it twice on the same pair just creates two identical scoring runs (useful when you change a metric implementation and want to compare).

## Schema

```sql
CREATE TABLE m1_measurement_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    baseline_version_id UUID NOT NULL REFERENCES m1_dataset_versions(version_id),
    candidate_version_id UUID NOT NULL REFERENCES m1_dataset_versions(version_id),
    triggered_by_id UUID NOT NULL REFERENCES users(id),
    celery_task_id VARCHAR(60),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','running','complete','failed')),
    overall_score NUMERIC(5,4),
    regulation_count INTEGER,
    field_count INTEGER,
    metric_invocations INTEGER,
    completeness_summary JSONB,  -- {"title_si": {"exact": 142, "partial": 87, ...}, ...}
    field_summary JSONB,         -- {"title_si": {"mean": 0.71, "ci_low": 0.65, ...}, ...}
    metrics_override JSONB,      -- if non-null, restricts which metrics ran
    error TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_m1_measurement_runs_baseline ON m1_measurement_runs(baseline_version_id);
CREATE INDEX ix_m1_measurement_runs_candidate ON m1_measurement_runs(candidate_version_id);

CREATE TABLE m1_measurement_scores (
    score_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES m1_measurement_runs(run_id) ON DELETE CASCADE,
    regulation_key VARCHAR(50) NOT NULL,
    field_name VARCHAR(60) NOT NULL,
    metric_name VARCHAR(60) NOT NULL,
    metric_version VARCHAR(20) NOT NULL,           -- per 01_Alignment_Audit §N
    score NUMERIC(6,5),                            -- nullable when metric is undefined
    status VARCHAR(10) NOT NULL
        CHECK (status IN ('exact','partial','mismatch','missing','extra')),
    is_primary BOOLEAN NOT NULL,
    baseline_value TEXT,    -- truncated to 4 KB for storage hygiene
    candidate_value TEXT,
    diagnostic JSONB        -- metric-specific blob (e.g. LaBSE embedding distance, regex captures)
);
CREATE INDEX ix_m1_measurement_scores_run ON m1_measurement_scores(run_id);
CREATE INDEX ix_m1_measurement_scores_run_field ON m1_measurement_scores(run_id, field_name);
CREATE INDEX ix_m1_measurement_scores_run_status ON m1_measurement_scores(run_id, status) WHERE status IN ('mismatch','missing','extra');
```

Storage budget: 16 fields × 2 metrics × 407 regulations = 13 K rows per run. At ~200 bytes each, ~2.6 MB per run. Even 100 runs is sub-300 MB — well within Aiven entry-tier.

## Tasks

### Task 5.1 — Alembic migration `202605240004_m1_measurement.py` (½ day)

Per the schema above. Down-revision: `202605240003_m1_extraction_profiles`.

### Task 5.2 — ORM + Pydantic (½ day)

`enigmatrix-backend/app/models/m1_measurement.py` — `M1MeasurementRun`, `M1MeasurementScore`.
`enigmatrix-backend/app/schemas/m1_measurement.py` — request + response models including the heatmap aggregate, calibration block, worst-N list.

### Task 5.3 — The Celery task `run_measurement` (1½ days)

`enigmatrix-backend/app/tasks/m1/run_measurement.py`:

```python
@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=2)
def run_measurement(self, run_id: str) -> dict:
    db = SessionLocal()
    run = db.query(M1MeasurementRun).filter_by(run_id=run_id).one()
    run.status = "running"
    run.started_at = datetime.now(UTC)
    db.commit()

    try:
        # 1. Load both versions and pull all rows keyed by regulation_key
        baseline_rows = load_rows_by_key(db, run.baseline_version_id)
        candidate_rows = load_rows_by_key(db, run.candidate_version_id)
        all_keys = set(baseline_rows) | set(candidate_rows)

        # 2. Pre-load expensive models (LaBSE, BERTScore) once
        labse = SentenceTransformer("sentence-transformers/LaBSE", device="cpu")
        bert_scorer = None  # lazy: only construct if any summary field is in scope

        # 3. Score loop
        scores_to_persist: list[M1MeasurementScore] = []
        from m1.evaluation.field_metrics import FIELD_METRICS
        from m1.evaluation.completeness import compute_status

        for regulation_key in all_keys:
            b = baseline_rows.get(regulation_key, {})
            c = candidate_rows.get(regulation_key, {})

            for field_name, metric_specs in FIELD_METRICS.items():
                if run.metrics_override and field_name not in run.metrics_override:
                    continue
                bv = (b.get("fields") or {}).get(field_name)
                cv = (c.get("fields") or {}).get(field_name)

                primary_score = None
                for i, (metric_fn, threshold, metric_version) in enumerate(metric_specs):
                    if bv is None and cv is None:
                        continue  # omit from scorecard entirely
                    try:
                        score = metric_fn(bv, cv, labse=labse) if metric_fn.needs_labse else metric_fn(bv, cv)
                    except Exception:
                        score = None
                    is_primary = (i == 0)
                    status = compute_status(bv, cv, primary_score=score if is_primary else primary_score, threshold=threshold)
                    if is_primary:
                        primary_score = score
                    scores_to_persist.append(M1MeasurementScore(
                        run_id=run.run_id, regulation_key=regulation_key,
                        field_name=field_name, metric_name=metric_fn.__name__,
                        metric_version=metric_version,
                        score=score, status=status, is_primary=is_primary,
                        baseline_value=truncate(str(bv) if bv is not None else None),
                        candidate_value=truncate(str(cv) if cv is not None else None),
                    ))

            # Persist in chunks of 500 to bound memory
            if len(scores_to_persist) > 500:
                db.bulk_save_objects(scores_to_persist)
                db.commit()
                scores_to_persist.clear()

        if scores_to_persist:
            db.bulk_save_objects(scores_to_persist)
            db.commit()

        # 4. Aggregate
        run.overall_score = compute_overall(db, run.run_id)
        run.regulation_count = len(all_keys)
        run.field_summary = compute_field_summary(db, run.run_id)
        run.completeness_summary = compute_completeness_summary(db, run.run_id)
        run.metric_invocations = db.query(func.count(M1MeasurementScore.score_id)).filter_by(run_id=run.run_id).scalar()
        run.status = "complete"
        run.completed_at = datetime.now(UTC)
        db.commit()

        return {"run_id": str(run.run_id), "overall_score": float(run.overall_score)}

    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)[:4096]
        run.completed_at = datetime.now(UTC)
        db.commit()
        raise
```

The aggregate functions live in `app/services/m1_measurement_aggregates.py`. They run pure SQL (`SELECT field_name, AVG(score) WHERE run_id = ?, is_primary = TRUE GROUP BY field_name`) for performance.

Performance budget: 16 K rows × ~3 ms per metric (LaBSE batched) = ~50 s on CPU. Acceptable for an admin-initiated run; user sees progress via slice 6's polling page.

### Task 5.4 — API endpoints (½ day)

`enigmatrix-backend/app/api/v1/m1_measurements.py`:

```
POST   /api/v1/m1/measurements/run                       (admin — body: {baseline_version_id, candidate_version_id, metrics_override?})
GET    /api/v1/m1/measurements                           (list, filter by baseline/candidate/date)
GET    /api/v1/m1/measurements/{run_id}                  (full detail)
GET    /api/v1/m1/measurements/{run_id}/per-field        (heatmap data)
GET    /api/v1/m1/measurements/{run_id}/regulations/{key} (per-reg comparison)
GET    /api/v1/m1/measurements/{run_id}/worst?n=20       (worst-N list)
GET    /api/v1/m1/measurements/{run_id}/calibration?bins=15 (calibration plot data, 404 if candidate has no confidence)
GET    /api/v1/m1/measurements/{run_id}/scores           (paginated raw scores, CSV-exportable via Accept header)
GET    /api/v1/m1/measurements/{run_id}/progress         (poll-friendly; returns status + rows_scored)
```

`POST /run`:
- Validates that both versions are sealed (`frozen_at IS NOT NULL`).
- Validates that they belong to different datasets, or to the same dataset (both allowed — same-dataset comparison audits self-corrections).
- Creates an `m1_measurement_runs` row with `status='pending'`.
- Dispatches `run_measurement.delay(run_id)`.
- Returns the run id + Celery task id.
- Writes the `m1.measurement.run.start` audit row.

`GET /calibration` returns 404 with body `{"detail": "candidate_has_no_confidence"}` when the candidate version's rows have all-null `confidence`. This is the legacy-profile case per [01_Alignment_Audit §J](01_Alignment_Audit.md#j-confidence-scoring-for-legacy_v1-🟢-refinement).

### Task 5.5 — Tests (1 day)

- `enigmatrix-backend/app/tests/unit/test_m1_measurement_aggregates.py`: hand-craft 30 score rows, call `compute_overall`/`compute_field_summary`, assert the aggregates.
- `enigmatrix-backend/app/tests/integration/test_run_measurement.py`: set up two synthetic dataset versions in a test DB (5 regulations each, hand-crafted fields), run the Celery task in eager mode, assert `overall_score`, `regulation_count`, `field_summary` populated.
- `enigmatrix-ml/tests/evaluation/test_metric_versions.py`: every metric in the registry has a non-empty `__version__`.

## Files touched

| Path | New/Edit | Purpose |
|---|---|---|
| `enigmatrix-backend/alembic/versions/202605240004_m1_measurement.py` | new | Two tables + indexes |
| `enigmatrix-backend/app/models/m1_measurement.py` | new | ORM |
| `enigmatrix-backend/app/schemas/m1_measurement.py` | new | Pydantic |
| `enigmatrix-backend/app/services/m1_measurement_aggregates.py` | new | Aggregate SQL |
| `enigmatrix-backend/app/tasks/m1/run_measurement.py` | new | Celery task |
| `enigmatrix-backend/app/api/v1/m1_measurements.py` | new | Router |
| `enigmatrix-backend/app/api/v1/router.py` | edit | Mount |
| `enigmatrix-backend/app/tests/unit/test_m1_measurement_aggregates.py` | new | Aggregate tests |
| `enigmatrix-backend/app/tests/integration/test_run_measurement.py` | new | E2E task test |
| `enigmatrix-ml/tests/evaluation/test_metric_versions.py` | new | Version-tag tests |

## Gate

The end-to-end measurement gate:

1. Two sealed versions exist: ground-truth manual (slice 3) + legacy_v1 extraction (slice 4).
2. POST `/api/v1/m1/measurements/run` with both version IDs.
3. The Celery task completes within 2 minutes.
4. `SELECT overall_score FROM m1_measurement_runs WHERE run_id = ?` returns a number in `[0, 1]`.
5. `GET /per-field` returns 16+ field rows with non-null `mean`.
6. **Honesty hand-check:** `GET /regulations/2468/44` returns scores where `title_si` is in `mismatch` with a low score (the Wijesekara case) and `title_en` (if `legacy_v1` extracts it) is `missing` (the legacy chain doesn't extract titles).

If the numbers do not match your gut, the bug is in the metrics or in the metric registry's primary-choice. The script `scripts/run_baseline_measurement.py` from slice 1 should produce a similar overall_score on the same pair — they're computing the same thing through different code paths (script vs Celery). Within 0.01 absolute is acceptable.

## What this slice deliberately does NOT do

- No UI yet — slice 6 builds the dashboard.
- No SSE emission of progress events (use polling for now).
- No retroactive re-scoring when a metric version bumps (deferred to slice 8).

## Risks specific to this slice

- **LaBSE model load is slow on cold start (~10 s).** Mitigation: load lazily inside the task, but at module level not per-row so it loads once per Celery worker process. Workers stay warm across runs.
- **Memory blow-up on 100 K-row runs.** Mitigation: chunked persistence (every 500 rows). Aggregate via SQL, not in-process Python.
- **Score variance under metric-version drift.** Mitigation: every score row carries `metric_version`. The slice 6 dashboard filters to a single metric_version per chart. Slice 8's `make thesis-artifacts` script always picks the latest available version.
- **Field set drift between baseline and candidate.** Mitigation: the engine scores the union of fields present in either side. Fields present only in baseline produce all-`missing` rows; only in candidate produce all-`extra` rows. Both are visible in the heatmap.
- **Celery task lost mid-run.** Mitigation: `status='running'` is set before scoring starts; on task-lost detection (Celery `task_revoked` signal in a follow-up patch), set `status='failed'`. The completed scores remain in the DB so partial progress is observable.

## Cross-references

- [02_Slice1_Measurement_Scaffolding](02_Slice1_Measurement_Scaffolding.md) — produces the `FIELD_METRICS` registry this task consumes.
- [04_Slice3_Dataset_Registry_and_Upload](04_Slice3_Dataset_Registry_and_Upload.md) — `m1_dataset_rows` is the input.
- [05_Slice4_Extraction_Profile_Registry](05_Slice4_Extraction_Profile_Registry.md) — the candidate version usually comes from here.
- [07_Slice6_Comparison_UI](07_Slice6_Comparison_UI.md) — consumes every endpoint this slice exposes.
- [01_Alignment_Audit §J](01_Alignment_Audit.md#j-confidence-scoring-for-legacy_v1-🟢-refinement) — confidence-plot 404 behaviour.
