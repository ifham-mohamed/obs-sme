# 15_M1_3 — `scraper/` Folder Build Guide

> Companion to [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) — build guide for the `scraper/` slice of doc 13's M1 tree.
> **Implementation status snapshot:** 🔲 5 deferred · 🟡 0 partial · ✅ 0 shipped (the whole `scraper/` folder lands with BUILD_07).

## Purpose

`scraper/` is the Scrapy project that owns **Stage A** (Ingestion) — discovers new gazettes on `gazette.lk` and `documents.gov.lk`, downloads PDFs, deduplicates against the DB, and hands off to Stage B via a Celery task. Lives outside `backend/` + `ml/` because Scrapy expects its own top-level project root with its own settings.

## Files in this folder

| File | Owns | Status | Primary doc | How to build (1-liner) |
|---|---|---|---|---|
| `scraper/__init__.py` | Marker | 🔲 | — | Empty file |
| `scraper/settings.py` | Scrapy global config — autothrottle, retry, user-agent, ROBOTSTXT_OBEY | 🔲 | [03_M1_Data_Collection.md §1.3](03_M1_Data_Collection.md) | Copy the `custom_settings` dict from doc 03; pin `DOWNLOAD_DELAY=2`, `RETRY_TIMES=5` |
| `scraper/pipelines.py` | PDF → `storage/m1/raw/` write pipeline + dedup check | 🔲 | [03_M1_Data_Collection.md §1.2](03_M1_Data_Collection.md) | `FilesPipeline` subclass; SHA-256 the bytes; skip on duplicate `gazette_number` |
| `scraper/spiders/gazette_spider.py` | Spider for `gazette.lk` + `documents.gov.lk` | 🔲 | [03_M1_Data_Collection.md §1.2 + §1.3](03_M1_Data_Collection.md) + [02_M1_1_Data_Sources_Catalogue.md §SRC_GOV_*](02_M1_1_Data_Sources_Catalogue.md) | One `Spider` class targeting both portals; yields `{url, gazette_number, gazette_date, pdf_url}` items |
| `scraper/spiders/portal_spiders.py` | Secondary-source spiders (IRD, EPF, eROC, SLSI, CBSL) | 🔲 | [02_M1_1_Data_Sources_Catalogue.md](02_M1_1_Data_Sources_Catalogue.md) + [03_M1_3_Secondary_Source_Integration.md](03_M1_3_Secondary_Source_Integration.md) | Per-source `Spider` subclass; ASP.NET viewstate handling for IRD (gotcha documented in 02_M1_1) |

## How to start building

This folder is the **first thing you build in Phase 2 of the roadmap** ([Step 2a](16_M1_Development_Roadmap.md)). The end-to-end pipeline can't start until Stage A produces PDFs.

1. **Scaffold the Scrapy project.** From the repo root: `scrapy startproject scraper` then prune the boilerplate `scraper/items.py` (we use ad-hoc dicts) and `scraper/middlewares.py` (defaults are fine).
2. **Write `scraper/settings.py`.** Copy the `custom_settings` dict from [03_M1_Data_Collection.md §1.3](03_M1_Data_Collection.md). Critical settings: `DOWNLOAD_DELAY=2` + `AUTOTHROTTLE_ENABLED=True` + `RETRY_HTTP_CODES=[500, 503, 429]` + `USER_AGENT='EnigmatrixResearchBot/1.0 (+https://enigmatrix.lk/bot)'`.
3. **Write `scraper/pipelines.py`.** `FilesPipeline` subclass that:
   - downloads each PDF into `storage/m1/raw/{gazette_number}.pdf`
   - SHA-256 hashes the bytes (stored in `m1_regulations.pdf_hash`)
   - skips if the `gazette_number` already exists in the DB
4. **Write `scraper/spiders/gazette_spider.py`.** Two `start_urls` (gazette.lk + documents.gov.lk). Parse the pagination + emit per-issue items. Use `scrapy crawl gazette_spider` against a fixture date first to validate; only enable in Celery once stable.
5. **Test locally.** `scrapy crawl gazette_spider --limit 5` produces 5 PDFs in `storage/m1/raw/` + 5 rows in `m1_regulations` (`status='ingested'`).
6. **Last — `scraper/spiders/portal_spiders.py`.** Per-source spider for IRD/EPF/ETF/eROC/SLSI/CBSL. The IRD spider needs ASP.NET viewstate handling (carry the cookie + form token across requests). Stage 4 of the roadmap (BUILD_12) uses these.

The Scrapy CLI works standalone for local testing. Production runs the spider *inside* a Celery task (see `tasks/m1/gazette_scraper.py` in [15_M1_2_Backend_Folder_Guide.md](15_M1_2_Backend_Folder_Guide.md)) — the cooperative retry boundary between Scrapy and Celery is documented in [03_M1_Data_Collection.md §6.1](03_M1_Data_Collection.md).

## Dependencies

- **`storage/m1/raw/`** ([15_M1_5_Storage_Folder_Guide.md](15_M1_5_Storage_Folder_Guide.md)) — destination for downloaded PDFs. Must be writable.
- **Postgres `m1_regulations` table** — dedup check + new-row insert. Schema lives in `backend/app/models/m1_regulation.py` ([15_M1_2_Backend_Folder_Guide.md](15_M1_2_Backend_Folder_Guide.md)).
- **`backend/app/tasks/m1/gazette_scraper.py`** ([15_M1_2_Backend_Folder_Guide.md](15_M1_2_Backend_Folder_Guide.md)) — the Celery wrapper that triggers Scrapy on a schedule. Scrapy CLI handles local dev; the wrapper handles production.
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
