# 15_M1_3 — Scraper Folder Build Guide (`enigmatrix-backend/scraper/`)

> Companion to [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) — build guide for the Scrapy slice of the M1 tree.
> **Repo note (2026-07-24):** the Scrapy project is **shipped** and lives at **`enigmatrix-backend/scraper/`** (project root `enigmatrix-backend/scrapy.cfg`), *not* a top-level `scraper/`. Secondary-source watchers were **not** built as Scrapy spiders — they're Celery tasks under `enigmatrix-backend/app/m1/tasks/` (`portal_watcher.py`, `rss_watcher.py`) backed by `services/secondary_sources.py`.
> **Implementation status snapshot:** ✅ Shipped — Stage A spiders (gazette + weekly + acts + bills) + settings + pipelines. Phase-2 ingest is live.

## Purpose

The Scrapy project owns **Stage A** (Ingestion) — discovers new gazettes/acts/bills on `gazette.lk` + `documents.gov.lk`, downloads PDFs, deduplicates against the DB, and hands off to Stage B. It sits *inside* `enigmatrix-backend/` (shares the backend venv + DB session) and is driven in production by the `run_scraper` / `gazette_scraper` Celery tasks.

## Files in this folder

| File | Owns | Status | Primary doc | Notes |
|---|---|---|---|---|
| `scraper/settings.py` | Scrapy global config — autothrottle, retry, user-agent, ROBOTSTXT_OBEY | ✅ Shipped | [03_M1_Data_Collection.md §1.3](03_M1_Data_Collection.md) | `DOWNLOAD_DELAY` + AUTOTHROTTLE + retry codes |
| `scraper/pipelines.py` | PDF → `storage/m1/raw/` write pipeline + dedup + row insert | ✅ Shipped | [03_M1_Data_Collection.md §1.2](03_M1_Data_Collection.md) | SHA-256 the bytes; skip duplicate `gazette_number` |
| `scraper/spiders/_base.py` | Shared base spider (common parsing/item shape) | ✅ Shipped | [03_M1_Data_Collection.md](03_M1_Data_Collection.md) | The 4 concrete spiders subclass this |
| `scraper/spiders/gazette_spider.py` | Extraordinary-gazette spider (`gazette.lk` / `documents.gov.lk`) | ✅ Shipped | [03_M1_Data_Collection.md §1.2 + §1.3](03_M1_Data_Collection.md) | Yields `{url, gazette_number, gazette_date, pdf_url}` |
| `scraper/spiders/weekly_gazette_spider.py` | Weekly-gazette spider | ✅ Shipped | [03_M1_Data_Collection.md](03_M1_Data_Collection.md) | Weekly issue cadence |
| `scraper/spiders/acts_spider.py` | Acts spider | ✅ Shipped | [02_M1_1_Data_Sources_Catalogue.md](02_M1_1_Data_Sources_Catalogue.md) | Parliament acts |
| `scraper/spiders/bills_spider.py` | Bills spider | ✅ Shipped | [02_M1_1_Data_Sources_Catalogue.md](02_M1_1_Data_Sources_Catalogue.md) | Draft bills |
| _Secondary sources_ (IRD/EPF/eROC/SLSI/CBSL + news RSS) | Not Scrapy spiders — Celery tasks | ✅ Shipped elsewhere | [03_M1_3_Secondary_Source_Integration.md](03_M1_3_Secondary_Source_Integration.md) | `app/m1/tasks/portal_watcher.py` + `rss_watcher.py` + `services/secondary_sources.py` — see [15_M1_2](15_M1_2_Backend_Folder_Guide.md) |

## How to start building

This folder is **already built** (Phase 2, roadmap [Step 2a](16_M1_Development_Roadmap.md)). The notes below are how to *run + extend* it; the build history is retained for context.

> **Run it (local dev):** from `enigmatrix-backend/` (where `scrapy.cfg` lives): `scrapy list` shows `gazette_spider`, `weekly_gazette_spider`, `acts_spider`, `bills_spider`. `scrapy crawl gazette_spider -s CLOSESPIDER_ITEMCOUNT=5` fetches 5 issues into `storage/m1/raw/` + inserts `status='ingested'` rows. Production runs the same spiders inside the `run_scraper` / `gazette_scraper` Celery tasks.

1. **Project is scaffolded.** `enigmatrix-backend/scrapy.cfg` + `scraper/settings.py` are in place; there is no `items.py`/`middlewares.py` (ad-hoc item dicts + default middlewares).
2. **Write `scraper/settings.py`.** Copy the `custom_settings` dict from [03_M1_Data_Collection.md §1.3](03_M1_Data_Collection.md). Critical settings: `DOWNLOAD_DELAY=2` + `AUTOTHROTTLE_ENABLED=True` + `RETRY_HTTP_CODES=[500, 503, 429]` + `USER_AGENT='EnigmatrixResearchBot/1.0 (+https://enigmatrix.lk/bot)'`.
3. **Write `scraper/pipelines.py`.** `FilesPipeline` subclass that:
   - downloads each PDF into `storage/m1/raw/{gazette_number}.pdf`
   - SHA-256 hashes the bytes (stored in `m1_regulations.pdf_hash`)
   - skips if the `gazette_number` already exists in the DB
4. **Write `scraper/spiders/gazette_spider.py`.** Two `start_urls` (gazette.lk + documents.gov.lk). Parse the pagination + emit per-issue items. Use `scrapy crawl gazette_spider` against a fixture date first to validate; only enable in Celery once stable.
5. **Test locally.** `scrapy crawl gazette_spider --limit 5` produces 5 PDFs in `storage/m1/raw/` + 5 rows in `m1_regulations` (`status='ingested'`).
6. **Secondary sources are NOT Scrapy spiders.** IRD/EPF/ETF/eROC/SLSI/CBSL + news RSS diffusion tracking is handled by `app/m1/tasks/portal_watcher.py` + `rss_watcher.py` (+ `services/secondary_sources.py` + `propagation_matching.py`), which write `m1_propagation_events`. See [15_M1_2](15_M1_2_Backend_Folder_Guide.md).

The Scrapy CLI works standalone for local testing. Production runs the spiders *inside* the `run_scraper` / `gazette_scraper` Celery tasks (see [15_M1_2_Backend_Folder_Guide.md](15_M1_2_Backend_Folder_Guide.md)) — the cooperative retry boundary between Scrapy and Celery is documented in [03_M1_Data_Collection.md §6.1](03_M1_Data_Collection.md). Integration test: `enigmatrix-backend/app/tests/integration/test_gazette_spider.py`.

## Dependencies

- **`storage/m1/raw/`** ([15_M1_5_Storage_Folder_Guide.md](15_M1_5_Storage_Folder_Guide.md)) — destination for downloaded PDFs. Must be writable.
- **Postgres `m1_regulations` table** — dedup check + new-row insert. ORM in `enigmatrix-backend/app/m1/models/` ([15_M1_2_Backend_Folder_Guide.md](15_M1_2_Backend_Folder_Guide.md)).
- **`enigmatrix-backend/app/m1/tasks/run_scraper.py` + `gazette_scraper.py`** ([15_M1_2_Backend_Folder_Guide.md](15_M1_2_Backend_Folder_Guide.md)) — the Celery wrappers that trigger Scrapy on a schedule. Scrapy CLI handles local dev; the wrappers handle production.
- **Wayback Machine + admin URL override table** — fallback when a source URL changes (see [02_M1_1 §source-specific fallbacks](02_M1_1_Data_Sources_Catalogue.md)).

## Tests & acceptance criteria

- **Discovery completeness.** Quarterly audit: hand-identify 50 known gazettes from `gazette.lk` → confirm Scrapy picks all 50 up; ≥ 98 % recall.
- **Download integrity.** SHA-256 hash check on every download; 0 % corruption.
- **De-duplication.** Running the spider twice on the same date produces zero duplicate rows in `m1_regulations` (enforced by the `UNIQUE` constraint on `gazette_number`).
- **Rate-limit politeness.** Honour `DOWNLOAD_DELAY=2` + `AUTOTHROTTLE_TARGET_CONCURRENCY=2`. Monitor 429 rate from each source; alert if > 1 % of requests get 429.
- **Spider health.** `m1_sources.last_check_status` tracks consecutive-failure count per source; alert if any source fails ≥ 3 consecutive checks.

## Cross-references

- Folder map spec: [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md)
- Roadmap: [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md) §Phase 2a
- Detail docs: [02_M1_1_Data_Sources_Catalogue.md](02_M1_1_Data_Sources_Catalogue.md), [03_M1_Data_Collection.md](03_M1_Data_Collection.md), [03_M1_3_Secondary_Source_Integration.md](03_M1_3_Secondary_Source_Integration.md)
- Phase doc: BUILD_07 §Stage A (ingestion)
- Sibling folders: [15_M1_2_Backend_Folder_Guide.md](15_M1_2_Backend_Folder_Guide.md), [15_M1_5_Storage_Folder_Guide.md](15_M1_5_Storage_Folder_Guide.md)
