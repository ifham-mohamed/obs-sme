# Module 1 — Phase 2 Gap #4: Continuous Extraction-Quality Monitoring

> Companion to [[PHASE2_INGEST_EXTRACTION_ANALYSIS]] §6.4 and [[PHASE2_GAP_CLOSURE_PLAN]] §6.4. **Status: implemented (Session 65, 2026-07-21)** — this doc records the design, why each metric was chosen, and what remains.

## Problem

The Phase-2 DoDs (PDF-classification accuracy ≥95%, OCR CER ≤10%, language detection ≥95%) were verified by **one-off hand audits at ship time**. Nothing re-measures extraction quality afterwards. The nightly drift job (`analytics.py`) applies KL-divergence to the *classifier's* confidence (Phase 3+) — the *extractor* has no equivalent. A Tesseract regression, a new gazette layout, or a font the Wijesekara maps don't cover would degrade output silently for months.

## Design decision: DB-derivable proxies, not re-audits

The ship-time DoDs need ground truth (hand-labelled PDFs, reference transcriptions) — that can't run unattended. Instead the probe computes **proxy metrics from data the pipeline already persists**, chosen so each one shadows a DoD:

| Probe metric | Shadows which DoD / failure mode | Source |
|---|---|---|
| `failed_rate` | extractor health (any regression) | `status='extraction_failed'` share in window |
| `empty_text_rate` | silent extraction loss | advanced rows with `length(raw_text) < 500` |
| `cid_rate` | font-decode failures (CID garbage) | `'(cid:'` occurrences in sampled texts |
| `wijesekara_rate` | SI garbling (§9.8.1 regression, continuously measured) | `is_wijesekara_encoded` on sampled `language='sin'` cleaned texts |
| `ocr_share` | **PDF-classification accuracy** — a jump in Tesseract-routed share means the char-density classifier is misrouting | `extraction_method='tesseract'` share |
| `unknown_lang_rate` | **language-detection accuracy** | `language='unknown'` share |
| `meta_<field>_rate` ×4 | metadata-extractor brittleness (§6.6) | non-null share of the 4 Phase-2 fields over preprocessed rows |

No PDF re-fetch, no OCR re-run → cheap enough for unattended monthly runs. True CER re-measurement stays a *quarterly manual audit* (see "Not covered" below) — the probe's job is to tell you *when* that audit is worth doing early.

## How it works

- **Task**: `app/m1/tasks/quality_probe.py` (`app.tasks.m1.quality_probe.run_quality_probe`), Beat-scheduled monthly (1st, 04:00 UTC — after the nightly analytics window). Follows the house task pattern: sync entry → `asyncio.run` → engine dispose in `finally` (the asyncpg/loop rule from extract/preprocess).
- **Window**: trailing 30 days by `extracted_at`; skips cleanly (`status: skipped`) on an empty window. Aggregate metrics via SQL `count()`; content checks (CID/Wijesekara) on the newest 25 texts only. `is_wijesekara_encoded` is a lazy ml-workspace import (same pattern as `preprocess_gazette`) — unavailable ⇒ metric is `None`, never faked.
- **Persistence**: new `m1_quality_probes` table (migration `202607210001`): window bounds, `window_n`/`sampled_n`, `metrics` JSONB, `degraded` flag, `alerts` JSONB. One row per run ⇒ the table *is* the trend.
- **Degradation detection**, two layers:
  1. **Absolute floors** (work from probe #1): `failed_rate>0.20`, `empty_text_rate>0.15`, `cid_rate>0.20`, `unknown_lang_rate>0.15`.
  2. **Drift**: >2σ from the trailing ≤6 probes' mean (needs ≥3 probes of history; σ=0 falls back to a relative band). Direction-aware — `meta_*` completeness degrades *downward*, error rates *upward*.
- **Alerting**: a degraded probe logs CRITICAL and writes an `m1.quality_probe.degraded` audit row (actor `system:quality_probe`) with full metrics + alerts — it surfaces in the admin Activity Log immediately, same zero-frontend reuse as the gap-#7 read-audit.

## Files changed

`app/m1/models/quality_probe.py` (new), `app/m1/tasks/quality_probe.py` (new), `alembic/versions/202607210001_m1_quality_probes.py` (new), `app/models/__init__.py` (register), `app/celery_config.py` (include + beat entry).

## Verification (deferred to user — sandbox lacks Postgres/Redis)

1. `alembic upgrade head`; `python -m compileall app`.
2. Manual first run: `celery -A app.celery_config call app.tasks.m1.quality_probe.run_quality_probe` → expect one `m1_quality_probes` row; with <3 probes of history only floor alerts can fire.
3. Synthetic degradation: flip a few window rows to `extraction_failed` so `failed_rate` breaches 0.20 → rerun → `degraded=true` + `m1.quality_probe.degraded` visible in the admin Activity Log.
4. `pytest` (add a unit test for `_detect_degradation` — pure function over dicts, easy to cover both floor and drift branches).
5. `graphify update .`

## Not covered (deliberate) + follow-ups

- **True CER / accuracy re-measurement** needs ground truth → stays a quarterly *manual* measurement run over the Slice-7 calibration corpus via the existing measurement engine; the probe tells you when to pull that forward.
- **Unknown-legacy-font instrumentation** (§9.8.3): add a `unknown_fonts` list to probe metrics once the font names are persisted at extraction time — currently they're only visible inside profile runs; fold in with the §9.8.1 auto-chain work.
- **Portal sparkline**: `GET /admin/m1/pipeline/quality-probes` + a small trend card in the pipeline portal — the Activity Log covers alerting until then.
- **Threshold tuning**: floors are first-guess; revisit after ~3 real probes.
