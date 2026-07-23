# Phase 2 · Data Requirements — Source Catalogue + Worked Examples: Plan

> Group: `PHASE2_INGEST_EXTRACTION / data_sources_and_worked_examples`. Companion: [[PHASE2_SOURCES_WORKED_EXAMPLES_ANALYSIS]].
> **Status: implemented 2026-07-23.** Verification deferred to operator (sandbox VHDX down). Completes the 02 · Data Requirements series (02_1–02_4).

## 1. Files added / changed

**02_M1_1 — source catalogue + monitoring**
- `app/m1/services/source_catalogue.py` (new) — `SourceOps` dataclass + `CATALOGUE` for the 15 real secondary sources (cadence, auth, URL pattern, pagination, failure mode, fallback); `PRIMARY_GAZETTE_OPS` reference; helpers `get_source_ops`, `due_after` (cadence gate), `in_backoff` (exponential backoff, cap 48 h).
- `app/m1/tasks/source_health.py` (new) — `run_source_health` (daily 05:00 UTC): flags sources with ≥3 consecutive failures / never-OK / stale >48 h; writes an `m1.source_health.degraded` audit row; read-only over `m1_sources`.
- `app/celery_config.py` (edit) — `include` += `source_health`; Beat `m1-source-health-daily`.

**02_M1_4 — worked-examples seed**
- `app/scripts/seed_m1_worked_examples.py` (new) — three `WEX_` examples across `m1_regulations` / `m1_regulation_sectors` / `m1_regulation_penalties` / `m1_propagation_events` / `survey_responses`. Idempotent + FK-defensive + per-example transaction.

## 2. Design decisions

- **Didn't touch the health contract** — `mark_source_result`/`load_sources` already work and are wired into both watchers; re-implementing would duplicate/regress. The catalogue + backoff helpers are *available* utilities (and the monitoring task consumes the catalogue), leaving watcher loops unchanged to avoid unverifiable behavioural churn.
- **Catalogue keyed by real ids** — matches `m1_sources.source_id`, so `get_source_ops(src.id)` resolves directly from a registry row.
- **Seed uses `WEX_` prefixes** — never collides with `seed_regulations.py`; safe to run alongside existing seeds.
- **Seed satisfies its own Layer-1 constraints** — real enums + a category on every `status='alerted'` row, so running it after migration `202607230001` won't hit a CHECK violation.

## 3. Verification (deferred to operator)

1. `python -m compileall app` — covers the 2 new modules + the seed + edits.
2. Seed run (after `seed_dev` + `seed_regulations` + `seed_phase4`): `uv run python -m app.scripts.seed_m1_worked_examples` → prints seeded `WEX_*` codes; re-run → "already seeded" (idempotent). Then `SELECT * FROM v_m1_regulation_lag_summary WHERE gazette_number IN ('2486/22','2369/14','2370/05');` returns lag rows, and `v_m1_channel_effectiveness` shows the portal/news channels.
3. `run_source_health` once → returns `{status, checked, healthy, problems}`; force a source's `consecutive_failures` up and confirm it appears in `problems` + an audit row is written.
4. Catalogue unit checks: `due_after` respects cadence; `in_backoff` grows then caps at 48 h; every `m1_sources.source_id` has a `CATALOGUE` entry (parity test).
5. `graphify update .`.

## 4. Follow-ups (not in this build)

Spider-side fallback (Wayback for `documents.gov.lk` 500s; IRD ASP.NET viewstate re-fetch; EPF `override_url`); `m1_sources.override_url` + `uptime_30d_pct` columns; wiring `in_backoff`/`due_after` into the watcher loops (needs `load_sources` to carry health fields); `tests/m1/test_worked_examples.py` view round-trip assertions. With 02_1–02_4 now built, the natural next targets are the 03/04 extraction-chain gaps or the deferred model/eval layers (05–07).
