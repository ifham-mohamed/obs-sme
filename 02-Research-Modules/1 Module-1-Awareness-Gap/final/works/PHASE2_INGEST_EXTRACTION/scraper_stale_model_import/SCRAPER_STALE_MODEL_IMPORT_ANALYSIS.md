# Phase 2 · Ingest — Scraper stale model import (`app.models.m1_gazette_item`): Analysis

> Group: `PHASE2_INGEST_EXTRACTION / scraper_stale_model_import`. Companion: [[SCRAPER_STALE_MODEL_IMPORT_FIX_PLAN]].
> Follows on from [[SCRAPER_CRAWL_EXIT1_ANALYSIS]] — the diagnosability fix there is what finally surfaced this true root cause.
> Symptom captured 2026-07-22 20:37 · Task `defc73da-175c-4a6a-8f19-85481453604f` · Scope `2026-06-01 → 2026-06-30`.

## Symptom (now with the real traceback)

The scraper still failed with `scrapy crawl gazette_spider exited 1`, but — because the exit-1 fix now embeds the subprocess stderr in the error — the actual cause is visible:

```
File "C:\Reasearch\xyz\enigmatrix-backend\scraper\pipelines.py", line 40, in <module>
    from app.models.m1_gazette_item import M1GazetteItem
ModuleNotFoundError: No module named 'app.models.m1_gazette_item'
```

The traceback shows Scrapy loading `ITEM_PIPELINES` at crawl setup → importing `scraper.pipelines` → that import failing. This is exactly the "cause #2 — an `app`-package import error at Scrapy startup" that [[SCRAPER_CRAWL_EXIT1_ANALYSIS]] predicted, and it was the real reason behind the earlier *opaque* "exited 1".

## Root cause — a reorg leftover

The M1 module reorganization ([[08_M1_MODULE_REORG_PLAN]]) moved the M1 model modules from `app/models/m1_*` into the `app/m1/models/` package:

| Model | Old path (gone) | New canonical path |
|---|---|---|
| `M1GazetteItem` | `app.models.m1_gazette_item` | `app.m1.models.gazette_item` |
| `M1Dataset` / `M1DatasetRow` / `M1DatasetVersion` | `app.models.m1_dataset` | `app.m1.models.dataset` |

`app/models/__init__.py` was updated to **re-export** from the new locations (e.g. `from app.m1.models.gazette_item import M1GazetteItem`). So anything that did `from app.models import M1GazetteItem` kept working, which masked the problem — but two call-sites still imported the **old submodule path directly**, and those break at import time:

1. **`scraper/pipelines.py:40`** — `from app.models.m1_gazette_item import M1GazetteItem`. This is the fatal one: Scrapy imports the pipeline module at startup, so the missing module aborts the crawl → **exit 1**. (Line 41, `from app.models.regulation import M1Regulation`, is fine — the regulation model stayed at `app/models/regulation.py`.)
2. **`scripts/backfill_legacy_baseline.py:117`** — `from app.models.m1_dataset import M1Dataset, …`. Not in the ingest hot path (a one-off backfill script), but the identical bug; it would fail whenever that script is run.

## Why it wasn't caught earlier

- The `app.models` package re-exports hid it from any code using the package-level name.
- The scraper runs in a **subprocess**, and until the exit-1 diagnosability fix its stderr never reached the task result — so the `ModuleNotFoundError` was invisible; all anyone saw was "exited 1".
- There's no import-smoke test that loads `scraper.pipelines` / the Scrapy settings, so a broken pipeline import isn't caught by the existing unit suite.

## Relationship to the earlier fixes this session

- The **`sys.executable -m scrapy`** change (exit-1 fix) was still correct and necessary hardening, but it was never going to fix *this* — the failure isn't the environment, it's a wrong import path. It did, however, guarantee the subprocess ran in the right venv so the traceback we now see is trustworthy.
- The **stderr-in-the-error** change is what turned "exited 1" into this precise, one-line-fixable diagnosis. Exactly the payoff intended in [[SCRAPER_CRAWL_EXIT1_FIX_PLAN]] step 3.
