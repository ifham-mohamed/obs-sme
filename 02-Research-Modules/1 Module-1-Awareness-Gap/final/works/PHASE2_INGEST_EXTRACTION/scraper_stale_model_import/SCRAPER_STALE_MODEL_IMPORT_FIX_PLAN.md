# Phase 2 · Ingest — Scraper stale model import: Fix + Plan

> Group: `PHASE2_INGEST_EXTRACTION / scraper_stale_model_import`. Companion: [[SCRAPER_STALE_MODEL_IMPORT_ANALYSIS]].
> **Status: implemented (2026-07-22).** Code in `C:\Reasearch\xyz\enigmatrix-backend`.

## Fix — repoint the two stale imports to their canonical `app.m1.models.*` paths ✅

```python
# scraper/pipelines.py:40
- from app.models.m1_gazette_item import M1GazetteItem
+ from app.m1.models.gazette_item import M1GazetteItem

# scripts/backfill_legacy_baseline.py:117
- from app.models.m1_dataset import M1Dataset, M1DatasetRow, M1DatasetVersion
+ from app.m1.models.dataset import M1Dataset, M1DatasetRow, M1DatasetVersion
```

These are the same paths `app/models/__init__.py` already re-exports from, so they're guaranteed to resolve. The `M1GazetteItem` import is the one that unblocks the crawl; the backfill-script import is fixed in the same pass to remove the sibling landmine.

## Files changed

| File | Change |
|---|---|
| `scraper/pipelines.py` | line 40 import → `app.m1.models.gazette_item` |
| `scripts/backfill_legacy_baseline.py` | line 117 import → `app.m1.models.dataset` |

No migration, no schema/API change. Scrapy can now import `ITEM_PIPELINES` at startup, so the crawl builds and runs.

## Verification (deferred to user — sandbox lacks Postgres/Redis/network)

1. **Import smoke (the direct check):** from `enigmatrix-backend/`, run in the worker's interpreter:
   `uv run python -c "import scraper.pipelines; import scraper.settings; print('pipelines import OK')"` → must print OK (previously raised `ModuleNotFoundError`).
2. **Scrapy project loads:** `uv run python -m scrapy list` → prints the spider names (this alone exercises the settings → pipeline import path that was failing) and exits 0.
3. **End-to-end:** re-trigger the extraction for the same scope (`2026-06-01 → 2026-06-30`). Expected: the spider crawls documents.gov.lk and ingests `m1_regulations` rows (or closes `scope_exhausted`), the run's Celery state is SUCCESS, and stages 2–3 pick up from there.
4. `uv run python -m compileall app scraper scripts`.
5. `graphify update .`.

## Follow-ups — stop reorg-leftover imports from recurring

- **Add an import-smoke test** (`app/tests/unit/test_scraper_imports.py`): `import scraper.pipelines`, `import scraper.settings`, and assert `M1GazetteItem` is importable. Pure, no DB — it would have caught this in CI. This is the highest-value guard.
- **Wire `python -m scrapy list` into the crawl canary** (already suggested in [[SCRAPER_CRAWL_EXIT1_FIX_PLAN]]): a green `scrapy list` proves the project + pipelines import cleanly in the deployed environment, catching startup-import breakage separately from listing-markup drift.
- **One-time sweep** for any other pre-reorg paths: `grep -rn "app\.models\.m1_" enigmatrix-backend` should return nothing after this fix (the two known offenders are now corrected). Consider a ruff/flake rule or a `banned-api` check on the `app.models.m1_*` prefix so new code can't reintroduce it.
- Optional: since `app/models/__init__.py` re-exports the M1 models, prefer importing the package-level names (`from app.models import M1GazetteItem`) in non-ORM code, so a future move only touches `__init__.py`.
