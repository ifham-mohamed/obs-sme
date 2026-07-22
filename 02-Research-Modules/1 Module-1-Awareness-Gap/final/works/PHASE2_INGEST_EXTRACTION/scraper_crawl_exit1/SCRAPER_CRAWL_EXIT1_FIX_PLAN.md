# Phase 2 · Ingest — Scraper "crawl exited 1": Fix + Plan

> Group: `PHASE2_INGEST_EXTRACTION / scraper_crawl_exit1`. Companion: [[SCRAPER_CRAWL_EXIT1_ANALYSIS]].
> **Status: implemented (2026-07-22).** Code in `C:\Reasearch\xyz\enigmatrix-backend`.

## Two fixes, one root-cause + one diagnosability

### Fix 1 — run Scrapy through the worker's own interpreter ✅ (the likely root cause)

Replace the bare console-script invocation with the same Python that runs the worker:

```python
# before
cmd = ["scrapy", "crawl", meta.spider_name]
# after
cmd = [sys.executable, "-m", "scrapy", "crawl", meta.spider_name]
```

`sys.executable -m scrapy` guarantees the subprocess uses the **exact environment** the Celery worker is already running in — the one that has `scrapy`, the project deps, and the `app` package importable. It eliminates both failure modes from cause #1 (no `scrapy` on PATH, or a foreign global `scrapy` that can't import `app`). This is the change most likely to make the crawl succeed.

### Fix 2 — surface the real error ✅ (so the next failure is self-explaining)

- Wrap `subprocess.run` in `try/except FileNotFoundError` → a clear "is scrapy installed in the worker's environment?" message instead of a bare `OSError`.
- On non-zero exit, embed the **tail of the captured stderr** (falling back to stdout) in the `RuntimeError`, so the actual Scrapy traceback reaches the Celery result + admin pipeline trace — not just the worker log:

```python
tail = ((result.stderr or "").strip() or (result.stdout or "").strip())[-1500:]
raise RuntimeError(
    f"scrapy crawl {meta.spider_name} exited {result.returncode}."
    + (f"\n--- last output ---\n{tail}" if tail else "")
)
```

## Files changed

| File | Change |
|---|---|
| `app/m1/tasks/run_scraper.py` | `import sys`; `sys.executable -m scrapy`; `FileNotFoundError` guard; stderr tail in the raised error |
| `app/m1/tasks/gazette_scraper.py` | same three changes (the Beat-scheduled `run_gazette_spider` had the identical bare-`scrapy` pattern) |

No migration, no schema change, no API change. Both scraper entry points (`run_scraper` polymorphic dispatcher + `run_gazette_spider` Beat task) now behave identically.

## Verification (deferred to user — sandbox lacks Postgres/Redis/network)

1. `cd enigmatrix-backend && python -m compileall app/m1/tasks/run_scraper.py app/m1/tasks/gazette_scraper.py`.
2. Confirm the worker env has scrapy on the module path: `python -c "import scrapy; print(scrapy.__version__)"` in the same interpreter that launches the worker (e.g. `uv run python -c ...`).
3. Re-trigger the extraction from the admin pipeline for the same scope (`2026-06-28 → 2026-07-22`).
   - **If it now succeeds** → root cause was the environment (cause #1); done.
   - **If it still fails** → the `RuntimeError` now carries the real Scrapy traceback in its `--- last output ---` block. Read the first exception line:
     - `ModuleNotFoundError: No module named 'app'` / `ImportError …` → an import problem in `scraper.pipelines` → `app.*` (cause #2). Fix the offending import.
     - Pydantic `ValidationError` for `APP_SECRET_KEY`/`JWT_SECRET`/`DATABASE_URL` → the subprocess is missing env (cause #3); ensure the worker's `.env` / env vars are exported where Celery runs.
4. Manual smoke, same interpreter: `uv run python -m scrapy crawl gazette_spider -a date_from=2026-06-28 -a date_to=2026-07-22` from `enigmatrix-backend/` — should reach the listing and either ingest rows or close `scope_exhausted` (exit 0).
5. `graphify update .`.

## Follow-ups

- The twice-weekly **crawl canary** (Session 64, [[PHASE2_GAP_CLOSURE_PLAN]] §6.3) detects *listing markup* drift; it does not cover this *environment/startup* class — the two are complementary. Consider adding a one-line startup assertion to the canary job that runs `python -m scrapy list` (exit 0 ⇒ the project + pipelines import cleanly in that environment).
- If the worker is deployed on Railway via `start_railway.sh`, confirm the worker and the `python -m scrapy` subprocess resolve the same venv there too (the fix makes this automatic, but worth a one-time check in the deploy log).
- Optional: pin the raised-error tail length behind a setting if 1500 chars proves too short for some tracebacks.
