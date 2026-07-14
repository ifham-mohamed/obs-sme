---
tags: [m1, phase-4, plan, watchers, propagation, lag]
date: 2026-06-30
author: Mohamed M.R.I (215075J) — Module 1 owner
session: 66
status: 🟡 in-execution — code scaffolded this session (Session 66)
features: F-229 (portal_watcher) · F-230 (rss_watcher) · F-231 (m1_propagation_events + matcher)
---

# M1 Phase 4a — Portal + RSS watchers → propagation events

> **Goal (roadmap Phase 4, Step 4a):** every 2 h, watchers scan the secondary sources (IRD / EPF / ETF / eROC portals + news RSS) and write `m1_propagation_events` rows — one per (regulation × channel) with `first_seen_at` + match confidence.
>
> **Why:** the information lag `gazette → portal → news → SME` (RQ3/RQ4) can only be measured if each downstream appearance of a regulation is **timestamped**. This is the data source for Findings F1/F2/F4.

## Approach — 2-step matching (per 03_M1_3_Secondary_Source_Integration.md)
1. **Exact gazette-number match** — if a portal block / news item mentions a gazette number that matches a known regulation → confidence 1.0, `match_method='exact_gazette'`.
2. **Fuzzy title/act match** — otherwise, `difflib` similarity between the normalised item text and the regulation title + principal act; if ≥ **0.78** → `match_method='fuzzy_title'`, confidence = the ratio. (Embedding match ≥ 0.78 is a later upgrade; difflib keeps this dependency-free and testable now.)

**Idempotency:** unique on `(regulation_id, source_id)` — the FIRST sighting wins (earliest `first_seen_at`), so re-running the watcher never double-counts a channel.

## Files (this session)
- `enigmatrix-backend/app/models/m1_propagation_event.py` — ORM model.
- `enigmatrix-backend/alembic/versions/202606300002_m1_propagation_events.py` — table + indexes + unique constraint (down-rev `202606300001`).
- `enigmatrix-backend/app/services/m1_secondary_sources.py` — code-only registry (4 portals + 5 RSS; URLs to confirm).
- `enigmatrix-backend/app/services/m1_propagation_matching.py` — **pure** matcher (stdlib only; unit-testable).
- `enigmatrix-backend/app/services/m1_propagation_service.py` — load active regulations → match items → upsert events.
- `enigmatrix-backend/app/tasks/m1/portal_watcher.py` — `run_portal_watcher` (httpx fetch → strip → match).
- `enigmatrix-backend/app/tasks/m1/rss_watcher.py` — `run_rss_watcher` (feedparser → match).
- `enigmatrix-backend/app/celery_config.py` — register both tasks + Beat (every 2 h).
- `enigmatrix-backend/pyproject.toml` — add `feedparser`.
- `enigmatrix-backend/app/tests/unit/test_m1_propagation_matching.py` — matcher unit tests.

## Definition of Done
- Migration `202606300002` creates `m1_propagation_events` with the unique `(regulation_id, source_id)` and the `first_seen_at` index.
- The matcher returns `exact_gazette` on a gazette-number hit and `fuzzy_title` above threshold; unit tests pass.
- `run_portal_watcher` / `run_rss_watcher` are registered + on Beat (every 2 h); a manual run writes `m1_propagation_events` rows for any matched mentions (per-source network errors are non-fatal).

## How to run (manual test — T-14)
```bash
cd enigmatrix-backend && uv sync                    # pulls feedparser
uv run alembic upgrade head                         # applies 202606300002
uv run pytest app/tests/unit/test_m1_propagation_matching.py -v
uv run celery -A app.celery_config worker -l info   # + beat for the 2h schedule
# manual trigger:
uv run python -c "from app.tasks.m1.rss_watcher import run_rss_watcher; print(run_rss_watcher.apply().result)"
# expect: {'sources': N, 'detail': [{'source_id':…, 'new_events': k}, …]} and rows in m1_propagation_events
```

## Risks / follow-ups
- **Source URLs** in the registry are best-known defaults — confirm each before production.
- **Portal HTML parsing** is a crude tag-strip + block split; per-portal parsers can refine precision later.
- **Embedding match** (≥ 0.78 cosine) deferred — difflib is the interim; upgrade when the classifier's encoder is available.
- Next: **4b** alert dispatch (SendGrid/Twilio) + **4c** nightly `v_m1_regulation_lag_summary` refresh + drift.

## Cross-refs
Roadmap [06-Timeline/02_Module1_Roadmap.md](../../06-Timeline/02_Module1_Roadmap.md) §Phase 4 · design [02_M1_1_Data_Sources_Catalogue] · [03_M1_3_Secondary_Source_Integration].
