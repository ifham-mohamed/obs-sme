# 02_M1_1 — Data Sources Catalogue (deep dive)

> Companion to [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) — expands the 15-source registry with per-source scrape frequency, auth requirements, URL pattern, failure modes, and fallback strategy.
> **Implementation status:** 🔲 Deferred (BUILD_07, BUILD_12)

## Purpose

The parent doc lists the 15 sources in a single table (source_id, name, URL pattern, languages, update frequency, scrape method). That table fits a one-page reference but elides the operational reality of each source: which require login, which return HTTP 429 vs 200-with-empty-body when rate-limited, which silently change their URL pattern. This companion provides the full per-source operations spec — what each spider must do, what failures look like, and the fallback path when the source goes offline.

## Detailed process

For each source, the spider follows the standard pattern: (1) probe last-scraped index page → (2) compare to `m1_sources.last_check_status` → (3) for new entries, download + store + create a `m1_regulations` row in `status='ingested'` → (4) update `m1_sources.last_scraped_at`. The per-source variations are below. Each spider is implemented as a Scrapy `Spider` subclass under `scraper/spiders/` plus a Celery wrapper in `backend/app/tasks/m1/`.

```python
# scraper/spiders/_base.py
class M1SourceSpider(scrapy.Spider):
    source_id: str                            # e.g. "SRC_GOV_EGZ"
    auth_required: bool = False
    rate_limit_sleep_s: float = 2.0           # politeness delay between requests
    fallback_strategy: Literal["wayback", "manual", "rss"] = "wayback"

    def parse(self, response):
        # ... source-specific parsing
        yield {"source_id": self.source_id, "url": response.url, "html": response.text}
```

The 15 sources are grouped by tier: **primary** (gazette + bills + acts on `documents.gov.lk` and `gazette.lk`), **secondary-official** (IRD, EPF, ETF, eROC, SLSI, CBSL portals), and **secondary-news** (5 RSS feeds).

| Source ID | Scrape every | Auth? | URL pattern | Pagination style | Failure mode | Fallback |
|---|---|---|---|---|---|---|
| `SRC_GOV_BILL` | 2 h | No | `documents.gov.lk/view/bill/bl_{year}.html` | Year-by-year list page | HTTP 500 on quarterly site rebuild | Wayback Machine (10–15 min delay) |
| `SRC_GOV_ACT` | 2 h | No | `documents.gov.lk/view/act/acts_{year}.html` | Year-by-year list page | Same as `SRC_GOV_BILL` | Wayback |
| `SRC_GOV_EGZ` | 2 h | No | `documents.gov.lk/view/egz/egz_{year}.html` | Year, then month folders | Frequent — partial outages 2–3×/month | Wayback + admin manual-trigger |
| `SRC_GOV_GZ` | 6 h (weekly Fri publication) | No | `documents.gov.lk/view/gz/{year}.html` | Year, then issue-number folders | Same as `SRC_GOV_EGZ` | Wayback |
| `SRC_IRD` | 6 h | No | `ird.gov.lk/en/pages/news.aspx` (ASP.NET viewstate) | Postback pagination — needs viewstate handling | Frequent viewstate-token expiry | Admin manual URL list |
| `SRC_EPF` | 12 h | No | `epf.lk/circulars/` | Static HTML list | Site rebuilt 2024 — URL changed once | Maintain URL override table |
| `SRC_ETF` | 12 h | No | `etfb.lk/circulars/` | Static HTML list | Rare downtime | Wayback |
| `SRC_EROC` | 24 h | No | `drc.gov.lk/circulars/` | Static HTML list | Rare | Wayback |
| `SRC_SLSI` | 24 h | No | `slsi.lk/news-and-events/` | Pagination via `?page=N` | Rare | Wayback |
| `SRC_CBSL` | 4 h | No | `cbsl.gov.lk/en/publications/circulars` | Static HTML + RSS | CBSL also publishes via RSS (preferred) | RSS feed |
| `SRC_NEWS_FT` | 1 h | No | `ft.lk/rss.xml` | RSS | Paywall on full article (RSS headline only) | RSS-only — no full-text scraping |
| `SRC_NEWS_LBO` | 1 h | No | `lankabusinessonline.com/feed` | RSS | Same | RSS |
| `SRC_NEWS_MIRROR` | 1 h | No | `dailymirror.lk/rss.xml` | RSS | Same | RSS |
| `SRC_NEWS_ADA` | 1 h | No | `adaderana.lk/rss.xml` (3 language feeds) | RSS | Some entries duplicated across feeds | Dedup by article URL |
| `SRC_NEWS_HIRU` | 1 h | No | `hirunews.lk/rss.xml` (3 language feeds) | RSS | Same as ADA | Dedup |

The scrape frequencies are chosen to balance freshness against the source's tolerance: gazette portals on `documents.gov.lk` get 2 h (matches the 6 h ingestion SLA with 3× safety margin); news RSS gets 1 h (RSS is cheap and we want the first-mention timestamp); statutory portals are slower (12–24 h) because they re-post the gazette content rather than break news.

## Technology choices

The "scraper framework" choice (Scrapy vs alternatives) is in the parent doc (§1.1). The per-source choices that need to be made operationally:

| Decision | Chosen | Alternatives | Rationale |
|---|---|---|---|
| RSS parsing | `feedparser` (Python) | `feedgen`, raw XML | `feedparser` handles malformed RSS that all 5 Sri Lankan news feeds emit; the others crash. |
| ASP.NET viewstate (IRD) | `httpx` with explicit cookie jar | Scrapy default | Scrapy's cookie handling drops the viewstate token; explicit `httpx` session preserves it. |
| Wayback Machine fallback | `wayback` Python package | `archive.org` HTTP API directly | The package handles the rate-limited search-then-fetch sequence; saves ~30 lines of glue code. |
| URL override table | Postgres `m1_sources.override_url` column | Hardcoded in spider | Admin can fix a broken source via the admin UI without redeploying the scraper. |

## Worked example

`SRC_GOV_EGZ` spider invocation, end-to-end (Celery + Scrapy):

```python
# backend/app/tasks/m1/gazette_scraper.py
@shared_task(autoretry_for=(), retry_backoff=True, max_retries=2)
def scrape_egz():
    runner = CrawlerRunner(get_project_settings())
    d = runner.crawl(EgzSpider)
    items = []                                          # collected via item pipeline
    d.addCallback(lambda _: items)
    reactor.run()

    for item in items:
        if not GazetteNumber.exists(item["gazette_number"]):
            download_pdf(item["pdf_url"], dest=f"storage/m1/raw/{item['gazette_number']}.pdf")
            insert_regulation_row(item)                 # status='ingested'
            extract_gazette.delay(item["gazette_number"])  # chord into Stage B
```

Sample produced row in `m1_regulations`:

```json
{
  "gazette_number": "2486/22",
  "gazette_date": "2026-04-15",
  "gazette_type": "extraordinary",
  "source_url": "https://documents.gov.lk/view/egz/2486/2486_22.pdf",
  "raw_pdf_path": "./storage/m1/raw/2486_22.pdf",
  "status": "ingested",
  "primary_language": null,                            // determined in Stage B
  "change_category": null                              // determined in Stage D
}
```

## Failure modes & edge cases

- **`documents.gov.lk` 500 errors.** Happens ~2–3 times per month, typically 15–60 minutes. Scrapy's retry middleware sleeps 30s/60s/120s/240s/480s. After 5 retries, the spider task is logged as failed; the next 2-h cron picks up the missed gazettes.
- **IRD viewstate token expiry.** The ASP.NET site rotates the viewstate every ~10 minutes; a long-running spider session needs to re-fetch the form page when a request returns the "session expired" HTML. Detected by string-matching the response body for `"Session has expired"`.
- **RSS deduplication across language feeds.** ADA and Hiru publish the same news story to all three (en/si/ta) language feeds with different URLs. The de-duplication uses a fuzzy match: `article_canonical_id = SHA256(slugify(title)[:50] + published_date)`. Cross-language matches yield three `m1_propagation_events` rows, one per language — that's intentional and feeds the F5 (language lag) finding.
- **Wayback Machine rate limit.** ~2 requests/second sustained; bursts above that trigger 429. The fallback uses `wayback`'s built-in adaptive throttle; if we exhaust the budget, the spider falls back to "admin manual" — emits a Slack notification + skips the cycle.
- **Source URL silently changes.** EPF's site was rebuilt in 2024; the legacy URLs returned a soft 404 (200 status with empty body). Detected by `m1_sources.last_check_status = 'empty_response'` for 3 consecutive cycles — admin reviews via dashboard.

## Validation & acceptance criteria

- **Per-source uptime metric.** `m1_sources.uptime_30d_pct` rolling 30-day uptime; alert below 90 %.
- **Discovery completeness.** Monthly audit (manually identify 50 known gazette publications and confirm they appear in `m1_regulations`); ≥ 98 % recall.
- **De-duplication correctness.** Zero duplicate `gazette_number` rows in `m1_regulations` (enforced by UNIQUE index, audited weekly).
- **Cross-language RSS coverage.** F5 measurement requires ≥ 30 cross-language story pairs; alert if monthly count falls below 5.

## Cross-references

- Parent: [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) §1.3 (15-source catalogue), §2.5 (`m1_sources` schema)
- Related: [03_M1_Data_Collection.md](03_M1_Data_Collection.md) §1 (Scrapy framework), §5 (cron schedule)
- BUILD phase: BUILD_07 §Scrapy spiders, BUILD_12 §portal watchers
- Code (when shipped): `scraper/spiders/*`, `backend/app/tasks/m1/portal_watcher.py`, `rss_watcher.py`
