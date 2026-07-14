---
tags: [m1, phase-4, plan, lag, materialized-view, drift, analytics]
date: 2026-06-30
author: Mohamed M.R.I (215075J) — Module 1 owner
session: 68
status: 🟡 in-execution — built this session (Session 68)
features: F-235 (lag materialized views + drift helper) · F-236 (nightly analytics task + Beat)
---

# M1 Phase 4c — Nightly lag-view refresh + confidence drift

> **Goal (roadmap Phase 4, Step 4c):** nightly, REFRESH the lag materialized views (built on the 4a `m1_propagation_events`) and run a KL-divergence check on the classifier-confidence distribution to catch model drift.
>
> **Why:** keeps the lag analytics (RQ3/RQ4) fresh for the admin dashboard + findings notebooks, and flags classifier drift so retraining (5c) is triggered on evidence, not a guess.

## Design
- **Materialized views** (migration `202606300004`):
  - `v_m1_regulation_lag_summary` — per regulation: `gazette_published_date`, first portal/news `first_seen_at`, `portal_lag_days`, `news_lag_days`, `propagation_count` (from `m1_propagation_events`). Unique index on `regulation_id`.
  - `v_m1_channel_effectiveness` — per `(source_id, channel)`: `mentions` + **median lag days** (`percentile_cont(0.5)`), ranked → produces the channel-effectiveness finding (F4).
- **Drift** — pure `m1_drift.py`: `histogram(values, bins=10)` + `kl_divergence(recent, baseline)` over `m1_regulations.classifier_confidence` (from 3f). If `KL > 0.15` on a sufficient sample → log a drift alert (retraining trigger).
- **Nightly task** — `refresh_lag_analytics` (Celery Beat 21:00 UTC): `REFRESH MATERIALIZED VIEW` both + compute drift + return a summary.

## Files
`app/services/m1_drift.py` (pure, tested) · `alembic/versions/202606300004_m1_lag_views.py` · `app/tasks/m1/analytics.py` · `app/celery_config.py` (register + Beat) · `app/tests/unit/test_m1_drift.py`.

## Definition of Done
- Migration `202606300004` creates both materialized views (+ unique indexes) chaining off `202606300003`.
- `kl_divergence` ≈ 0 for identical distributions and grows as they diverge — unit-tested.
- `refresh_lag_analytics` refreshes both views + returns `{drift_kl, drift_alert}`; on Beat nightly; registered in celery include.

## How to run (manual test — T-16)
```bash
cd enigmatrix-backend && uv run alembic upgrade head          # 202606300004
uv run pytest app/tests/unit/test_m1_drift.py -v
uv run python -c "from app.tasks.m1.analytics import refresh_lag_analytics as r; print(r.apply().result)"
# expect: {'views_refreshed':2, 'confidence_n':N, 'drift_kl':x, 'drift_alert':bool}
psql -c "SELECT * FROM v_m1_channel_effectiveness ORDER BY median_lag_days;"
```

## Risks / follow-ups
- Views need propagation data (run 4a watchers first) + classified regulations (3f) for the drift signal to be meaningful.
- `REFRESH` is plain (brief lock); switch to `CONCURRENTLY` once the views are large (needs the unique index, already added).
- Admin lag-analytics dashboard UI is deferred (roadmap BUILD_13).

## Cross-refs
Roadmap §Phase 4 4c · `12_M1_Monitoring_Maintenance.md` · predecessor `2026-06-30_Plan_M1_Phase4b_...`.
