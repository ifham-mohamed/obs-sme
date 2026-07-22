# Phase 2 · Ingest — Scraper "crawl exited 1" Pipeline Failure: Analysis

> Group: `PHASE2_INGEST_EXTRACTION / scraper_crawl_exit1`. Companion: [[SCRAPER_CRAWL_EXIT1_FIX_PLAN]].
> Symptom captured 2026-07-22 · Task `151bd1d3-a3e5-4e97-8571-6db387819ffc` · Scope `2026-06-28 → 2026-07-22`.

## Symptom

The admin pipeline showed **"Pipeline failed · Celery: FAILURE · 0/0 preprocessed"** with:

```
File ".../run_scraper.py", line 91, in run_scraper
    raise RuntimeError(...)
RuntimeError: scrapy crawl gazette_spider exited 1
```

Stage 1 (Scraping) failed; stages 2 (Extract) and 3 (Preprocess) never ran → `0/0`.

## What "exited 1" actually means (and doesn't)

`run_scraper` shells out to Scrapy as a subprocess (to keep Twisted's non-restartable reactor out of the Celery worker) and raises when the process returns non-zero. **Exit code 1 from `scrapy crawl` is a *startup / configuration* failure — Scrapy could not build the crawl** (bad settings, a pipeline/middleware that won't import, or the wrong Scrapy environment).

Critically, it is **not** "the site returned nothing" or "no gazettes in range": a spider that runs but yields zero items closes with a `finish_reason` and exits **0**. The scope-exhaustion early-exit and the `CLOSESPIDER_TIMEOUT_NO_ITEM=60` guard also exit **0**. So a network hiccup or an empty listing would show up as a clean run with 0 items — *not* this error. Exit 1 means the crawl never got off the ground.

## The diagnosability gap (why the message was useless)

`run_scraper` already captured `stdout`/`stderr` and logged them at ERROR **to the worker log** — but the `RuntimeError` it raised said only `"scrapy crawl gazette_spider exited 1"`. That string is what propagates to the Celery result and the admin pipeline trace, so the person looking at the UI sees the *effect* with **none of the cause**. The real Scrapy traceback was sitting in the worker log, disconnected from the failure the user actually saw.

## Ranked root causes (most → least likely)

1. **Wrong Scrapy environment (most likely).** The task ran a **bare** `["scrapy", "crawl", …]`, which resolves `scrapy` from the subprocess `PATH`. When the Celery worker is launched under `uv run` / a virtualenv, that PATH may not include the venv's `bin`, so either (a) no `scrapy` is found, or (b) a *different* global `scrapy` is found that has neither the project's deps nor the `app` package on its import path. In case (b), Scrapy starts, tries to import `scraper.pipelines` → `app.db.session` / `app.models.*`, fails the import, and **exits 1**. This is the classic subprocess-tool-in-a-venv footgun and is the primary target of the fix.
2. **An `app`-package import error at Scrapy startup.** Scrapy loads `ITEM_PIPELINES` → `scraper/pipelines.py`, which imports `app.db.session`, `app.models.m1_gazette_item`, `app.models.regulation`. Importing any `app.models.*` submodule runs `app/models/__init__.py`, which imports *every* model. If any model module is broken, Scrapy exits 1. (Checked this session: the recent activity-log / auth-hardening edits are **not** in this import chain — `app/services/__init__.py` is empty, and the new `password_reset_token` model imports cleanly — so they are not the cause.)
3. **Missing settings env in the subprocess.** `app.settings.Settings` has no defaults for `APP_SECRET_KEY` / `JWT_SECRET` / `DATABASE_URL`; if a module in the import chain calls `get_settings()` at import time and those vars aren't present, Pydantic raises and Scrapy exits 1. Unlikely here — `subprocess.run` inherits the worker's environment — but it becomes visible once the real stderr is surfaced (fix below).
4. **Network / site markup / empty range — ruled out** as the cause of *this* error (they exit 0, see above). The twice-weekly crawl canary (Session 64) covers markup drift separately.

## How the exact cause gets confirmed

Before the fix, you had to open the Celery **worker log** and find the `run_scraper: … exited 1` ERROR line with the `stderr:` block. After the fix ([[SCRAPER_CRAWL_EXIT1_FIX_PLAN]]) the tail of that stderr is embedded in the `RuntimeError` itself, so it appears directly in the admin pipeline trace / task result — the first line of the Scrapy traceback (e.g. `ModuleNotFoundError: No module named 'app'` vs `ImportError: cannot import name …` vs a Pydantic settings error) tells you which of causes 1–3 it was.
