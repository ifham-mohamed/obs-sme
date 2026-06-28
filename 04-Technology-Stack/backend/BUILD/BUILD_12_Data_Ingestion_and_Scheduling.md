# BUILD 12 — Data Ingestion & Scheduling

> **Goal:** stand up the platform-wide ingestion fabric — a single source registry, Scrapy spiders for static portals and news, Playwright workers for JS-rendered sites, social watchers for Twitter/X, Reddit, and Facebook public pages, an outbound rate limiter, idempotent dedup, and the dev (APScheduler) + prod (Celery + Redis) schedulers that drive every recurring job in the system.
>
> **Scope:** the seam between the wider internet and Enigmatrix's databases. Module-specific *consumers* (gazette PDF extraction in BUILD_07, misinformation classifiers in BUILD_10, IRD compliance scoring in M3) live in their own files and import from the registry defined here.
>
> **Read first:** `research/06_Data_Collection_and_Management.md`, `BUILD_06_Auth_and_Users.md`, `BUILD_07_Module1_Awareness.md`.

---

## 1. Source Registry

A single dict is the authoritative seam between "places we fetch from" and "modules that consume them". Every spider, watcher, scheduler entry, and ToS audit reads from this file. BUILD_07's gazette pipeline imports `SOURCES["documents_gov_lk_gazettes"]` to resolve URL patterns and cadence; M3's defaulter scoring imports `SOURCES["ird_defaulter_list"]`.

```python
# FILE: backend/app/ingest/registry.py
"""
Canonical source registry. Editing this file is a code-review event:
every entry is reviewed against the source's robots.txt and ToS before
the corresponding spider is enabled in production.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Literal

OwnerModule = Literal["m1_awareness", "m2_knowledge", "m3_compliance",
                      "m4_misinformation", "platform"]

@dataclass(frozen=True)
class SourceSpec:
    name: str
    base_url: str
    url_pattern: str               # printf-style or list pattern
    parser: str                    # dotted path to spider/worker class
    cadence_cron: str              # APScheduler-compatible cron
    owner_module: OwnerModule
    transport: Literal["scrapy", "playwright", "rss", "api", "praw", "tweepy"]
    tos_notes: str
    robots_compliance: bool = True
    download_delay_s: float = 1.5
    priority_queue: Literal["urgent", "default", "bulk"] = "default"
    tags: tuple[str, ...] = field(default_factory=tuple)


SOURCES: dict[str, SourceSpec] = {
    # --- Government portals ---
    "documents_gov_lk_gazettes": SourceSpec(
        name="documents_gov_lk_gazettes",
        base_url="https://documents.gov.lk",
        url_pattern="https://documents.gov.lk/en/gazette.php",
        parser="app.ingest.scrapers.gazette.spider.GazetteSpider",
        cadence_cron="0 */6 * * *",
        owner_module="m1_awareness",
        transport="scrapy",
        tos_notes="Public records; robots.txt allows /en/. Attribute as 'documents.gov.lk'.",
        download_delay_s=2.0,
        priority_queue="default",
        tags=("regulation", "primary"),
    ),
    "ird_defaulter_list": SourceSpec(
        name="ird_defaulter_list",
        base_url="https://www.ird.gov.lk",
        url_pattern="https://www.ird.gov.lk/en/Type%20of%20Taxes/SitePages/Defaulter%20List.aspx",
        parser="app.ingest.scrapers.ird.defaulter.IRDDefaulterSpider",
        cadence_cron="0 3 1 * *",          # monthly, 1st @ 03:00
        owner_module="m3_compliance",
        transport="scrapy",
        tos_notes="Public defaulter list. robots.txt: User-agent: * Disallow: none on this path. Honour download_delay; do not crawl /Login.",
        download_delay_s=3.0,
        priority_queue="bulk",
        tags=("compliance", "defaulter"),
    ),
    "ird_circulars": SourceSpec(
        name="ird_circulars",
        base_url="https://www.ird.gov.lk",
        url_pattern="https://www.ird.gov.lk/en/publications/SitePages/Circulars.aspx",
        parser="app.ingest.scrapers.ird.circulars.IRDCircularsSpider",
        cadence_cron="0 */4 * * *",
        owner_module="m1_awareness",
        transport="scrapy",
        tos_notes="Public circulars page. Same ToS as defaulter list.",
        download_delay_s=2.0,
    ),
    "epf_lk_notices": SourceSpec(
        name="epf_lk_notices",
        base_url="https://www.epf.lk",
        url_pattern="https://www.epf.lk/notices/",
        parser="app.ingest.scrapers.epf.spider.EPFSpider",
        cadence_cron="0 */3 * * *",
        owner_module="m1_awareness",
        transport="scrapy",
        tos_notes="Public notices. robots.txt allows /notices/.",
    ),
    "etf_lk_notices": SourceSpec(
        name="etf_lk_notices",
        base_url="https://www.etfb.lk",
        url_pattern="https://www.etfb.lk/notices",
        parser="app.ingest.scrapers.etf.spider.ETFSpider",
        cadence_cron="0 */6 * * *",
        owner_module="m1_awareness",
        transport="scrapy",
        tos_notes="Public notices. Verify robots.txt before each release; sometimes blocks /admin/*.",
    ),
    "slsi_standards": SourceSpec(
        name="slsi_standards",
        base_url="https://www.slsi.lk",
        url_pattern="https://www.slsi.lk/standards-news/",
        parser="app.ingest.scrapers.slsi.spider.SLSISpider",
        cadence_cron="0 */6 * * *",
        owner_module="m1_awareness",
        transport="scrapy",
        tos_notes="Public standards news. No login required.",
    ),
    "eroc_filings": SourceSpec(
        name="eroc_filings",
        base_url="https://eroc.drc.gov.lk",
        url_pattern="https://eroc.drc.gov.lk/public/filings",
        parser="app.ingest.workers.eroc.EROCWorker",
        cadence_cron="0 */6 * * *",
        owner_module="m2_knowledge",
        transport="playwright",
        tos_notes="Public filings, JS-rendered. respect rate-limit headers; no scraping behind /auth.",
        download_delay_s=4.0,
    ),
    "neda_grants": SourceSpec(
        name="neda_grants",
        base_url="https://www.neda.gov.lk",
        url_pattern="https://www.neda.gov.lk/programmes",
        parser="app.ingest.workers.neda.NEDAWorker",
        cadence_cron="0 */6 * * *",
        owner_module="m2_knowledge",
        transport="playwright",
        tos_notes="Public programmes. JS-rendered.",
    ),
    "chamber_of_commerce_news": SourceSpec(
        name="chamber_of_commerce_news",
        base_url="https://www.chamber.lk",
        url_pattern="https://www.chamber.lk/news",
        parser="app.ingest.workers.chamber.ChamberWorker",
        cadence_cron="0 */6 * * *",
        owner_module="m2_knowledge",
        transport="playwright",
        tos_notes="Public news. JS-rendered hero carousel; selectors are brittle — verify monthly.",
    ),
    "lawnet_judgments": SourceSpec(
        name="lawnet_judgments",
        base_url="https://www.lawnet.gov.lk",
        url_pattern="https://www.lawnet.gov.lk/category/judgments/",
        parser="app.ingest.scrapers.lawnet.spider.LawNetSpider",
        cadence_cron="0 4 * * *",
        owner_module="m2_knowledge",
        transport="scrapy",
        tos_notes="Public judgments. robots.txt allows /category/. Honour download_delay=3 (slow infra).",
        download_delay_s=3.0,
        priority_queue="bulk",
    ),

    # --- News (RSS-first, HTML fallback) ---
    "daily_ft_business": SourceSpec(
        name="daily_ft_business",
        base_url="https://www.ft.lk",
        url_pattern="https://www.ft.lk/rss",
        parser="app.ingest.scrapers.news.daily_ft.DailyFTSpider",
        cadence_cron="0 */1 * * *",
        owner_module="m1_awareness",
        transport="rss",
        tos_notes="RSS is offered for syndication. Attribute 'Daily FT'. Do not republish full body.",
    ),
    "daily_mirror_business": SourceSpec(
        name="daily_mirror_business",
        base_url="https://www.dailymirror.lk",
        url_pattern="https://www.dailymirror.lk/rss/business",
        parser="app.ingest.scrapers.news.daily_mirror.DailyMirrorSpider",
        cadence_cron="0 */1 * * *",
        owner_module="m1_awareness",
        transport="rss",
        tos_notes="RSS public. Headlines + excerpt only.",
    ),
    "lbo_news": SourceSpec(
        name="lbo_news",
        base_url="https://www.lankabusinessonline.com",
        url_pattern="https://www.lankabusinessonline.com/feed/",
        parser="app.ingest.scrapers.news.lbo.LBOSpider",
        cadence_cron="0 */2 * * *",
        owner_module="m1_awareness",
        transport="rss",
        tos_notes="WordPress RSS. Honour rel=canonical.",
    ),
    "ada_derana_business": SourceSpec(
        name="ada_derana_business",
        base_url="https://bizenglish.adaderana.lk",
        url_pattern="https://bizenglish.adaderana.lk/rss/",
        parser="app.ingest.scrapers.news.ada_derana.AdaDeranaSpider",
        cadence_cron="0 */2 * * *",
        owner_module="m1_awareness",
        transport="rss",
        tos_notes="Public RSS. Attribute 'Ada Derana'.",
    ),
    "hiru_news_business": SourceSpec(
        name="hiru_news_business",
        base_url="https://www.hirunews.lk",
        url_pattern="https://www.hirunews.lk/rss/business-news.xml",
        parser="app.ingest.scrapers.news.hiru.HiruSpider",
        cadence_cron="0 */2 * * *",
        owner_module="m1_awareness",
        transport="rss",
        tos_notes="Public RSS. Headlines + excerpt only.",
    ),

    # --- Social ---
    "twitter_keywords": SourceSpec(
        name="twitter_keywords",
        base_url="https://api.twitter.com",
        url_pattern="2/tweets/search/all",
        parser="app.ingest.social.twitter_watcher.TwitterWatcher",
        cadence_cron="0 */6 * * *",
        owner_module="m4_misinformation",
        transport="tweepy",
        tos_notes="Academic/Research API tier. Rate limit 300 req/15min. ToS forbids redistribution of raw tweets — store IDs + classification only.",
    ),
    "reddit_subs": SourceSpec(
        name="reddit_subs",
        base_url="https://www.reddit.com",
        url_pattern="r/srilanka,r/SriLankanBusiness/new.json",
        parser="app.ingest.social.reddit_watcher.RedditWatcher",
        cadence_cron="0 */6 * * *",
        owner_module="m4_misinformation",
        transport="praw",
        tos_notes="PRAW + script app. 60 req/min. ToS: research use OK; no PII export.",
    ),
    "facebook_public_pages": SourceSpec(
        name="facebook_public_pages",
        base_url="https://graph.facebook.com",
        url_pattern="v19.0/{page_id}/posts",
        parser="app.ingest.social.facebook_watcher.FacebookWatcher",
        cadence_cron="0 */6 * * *",
        owner_module="m4_misinformation",
        transport="api",
        tos_notes="Graph API only. Public pages, business-verified app. NO scraping of groups or feeds. App must hold pages_read_engagement permission.",
    ),
}
```

> Cross-ref: `BUILD_07 §2` imports `SOURCES["documents_gov_lk_gazettes"]`; `BUILD_10 §5` imports the social entries; M3 imports `ird_defaulter_list`. Every consumer is forbidden from hardcoding URLs.

A small base class normalises lifecycle for non-Scrapy fetchers:

```python
# FILE: backend/app/ingest/base.py
import time, structlog, uuid
from abc import ABC, abstractmethod
from app.ingest.registry import SourceSpec

log = structlog.get_logger()

class BaseWatcher(ABC):
    def __init__(self, spec: SourceSpec):
        self.spec = spec

    @abstractmethod
    async def fetch(self) -> list[dict]: ...

    async def run(self) -> dict:
        run_id = str(uuid.uuid4())
        t0 = time.monotonic()
        items_seen = items_inserted = errors = 0
        try:
            items = await self.fetch()
            items_seen = len(items)
            items_inserted = await self._persist(items)
        except Exception:
            errors = 1
            log.exception("ingest_event", run_id=run_id, source=self.spec.name)
            raise
        finally:
            log.info(
                "ingest_event",
                run_id=run_id, source=self.spec.name,
                items_seen=items_seen, items_inserted=items_inserted,
                duration_ms=int((time.monotonic() - t0) * 1000),
                errors_count=errors,
            )
        return {"run_id": run_id, "items_inserted": items_inserted}

    async def _persist(self, items: list[dict]) -> int: ...
```

---

## 2. Scrapy Projects

One Scrapy "project" lives at `backend/app/ingest/scrapers/`, with sub-packages per source. We use Scrapy `>=2.11` for its async middleware and Twisted-on-asyncio reactor. `ROBOTSTXT_OBEY = True` is non-negotiable.

```python
# FILE: backend/app/ingest/scrapers/settings.py
BOT_NAME = "enigmatrix"
USER_AGENT = "EnigmatrixBot/0.1 (+https://enigmatrix.lk/bot; research@enigmatrix.lk)"
ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 1.5
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 3600
DOWNLOADER_MIDDLEWARES = {
    "app.ingest.scrapers.middleware.HostBucketMiddleware": 543,
}
ITEM_PIPELINES = {
    "app.ingest.scrapers.pipelines.DedupPipeline": 200,
    "app.ingest.scrapers.pipelines.PersistPipeline": 800,
}
```

Template spider — one of the news sources, fully fleshed:

```python
# FILE: backend/app/ingest/scrapers/news/daily_ft.py
import scrapy
from datetime import datetime
from app.ingest.registry import SOURCES

class DailyFTSpider(scrapy.Spider):
    name = "daily_ft"
    custom_settings = {
        "DOWNLOAD_DELAY": SOURCES["daily_ft_business"].download_delay_s,
        "ROBOTSTXT_OBEY": True,
    }
    start_urls = [SOURCES["daily_ft_business"].url_pattern]

    def parse(self, response):
        # RSS first
        for item in response.xpath("//item"):
            link = item.xpath("link/text()").get()
            if not link:
                continue
            yield response.follow(link, callback=self.parse_article, meta={
                "rss_title": item.xpath("title/text()").get(),
                "rss_pubdate": item.xpath("pubDate/text()").get(),
            })

    def parse_article(self, response):
        # Selectors verified by inspection on 2026-04-22 — re-verify each release
        title = response.css("h1.inner-article-title::text").get() \
                or response.meta.get("rss_title")
        body = " ".join(response.css("div.inner-content p::text").getall()).strip()
        author = response.css("span.author-name::text").get(default="").strip()
        pub = response.css("meta[property='article:published_time']::attr(content)").get()
        if not (title and body):
            self.logger.warning("missing fields on %s", response.url)
            return
        yield {
            "source": "daily_ft_business",
            "url": response.url,
            "title": title.strip(),
            "body": body[:8000],          # excerpt only — ToS
            "author": author or None,
            "published_at": pub or response.meta.get("rss_pubdate"),
            "fetched_at": datetime.utcnow().isoformat(),
        }
```

Other news spiders (`DailyMirrorSpider`, `LBOSpider`, `AdaDeranaSpider`, `HiruSpider`) follow the same shape; each declares its own selectors and the corresponding registry entry. Government portal spiders (`EPFSpider`, `ETFSpider`, `SLSISpider`, `IRDCircularsSpider`) reuse `parse` patterns but emit different item shapes — `notice_id`, `effective_date`, etc.

---

## 3. Playwright Workers

JS-rendered portals (NEDA, Chamber of Commerce, eROC) cannot be parsed by Scrapy alone. We use Playwright with Chromium in headless mode, behind the same host rate limiter (§8).

```python
# FILE: backend/app/ingest/workers/eroc.py
from playwright.async_api import async_playwright
from app.ingest.base import BaseWatcher
from app.ingest.registry import SOURCES
from app.core.host_rate_limit import bucket_for

class EROCWorker(BaseWatcher):
    def __init__(self):
        super().__init__(SOURCES["eroc_filings"])

    async def fetch(self) -> list[dict]:
        await bucket_for("eroc.drc.gov.lk").acquire()
        items: list[dict] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(
                user_agent="EnigmatrixBot/0.1 (+https://enigmatrix.lk/bot)",
                locale="en-LK",
            )
            page = await ctx.new_page()
            await page.goto(self.spec.url_pattern, wait_until="networkidle")
            # selector verified 2026-04 — re-verify monthly
            rows = await page.query_selector_all("table.filings-table tbody tr")
            for row in rows:
                cells = await row.query_selector_all("td")
                if len(cells) < 4:
                    continue
                items.append({
                    "filing_id": (await cells[0].inner_text()).strip(),
                    "title":     (await cells[1].inner_text()).strip(),
                    "filed_on":  (await cells[2].inner_text()).strip(),
                    "doc_url":   await cells[3].query_selector("a") and
                                 await (await cells[3].query_selector("a")).get_attribute("href"),
                })
            await browser.close()
        return items
```

NEDA and Chamber workers share the same shape: launch context, navigate, wait for network idle, extract via `query_selector_all`. Each respects its registry entry's `download_delay_s` by acquiring its host bucket before navigation.

---

## 4. Social Watchers

Cross-ref: BUILD_10 (Module 4 misinformation) is the **primary consumer** of social ingest. This file is responsible only for fetching, rate-limit compliance, and persisting raw payloads to `social_posts_raw`. Classification happens downstream.

```python
# FILE: backend/app/ingest/social/twitter_watcher.py
import tweepy, os
from app.ingest.base import BaseWatcher
from app.ingest.registry import SOURCES

KEYWORDS = ["VAT Sri Lanka", "EPF Sri Lanka", "IRD circular",
            "gazette Sri Lanka", "SVAT", "PAYE Sri Lanka"]

class TwitterWatcher(BaseWatcher):
    """
    Academic API only. Rate limit: 300 requests / 15 min for search/all.
    ToS: do NOT redistribute raw tweet text. We persist tweet_id +
    classification labels; full text is fetched on-demand for review only.
    """
    def __init__(self):
        super().__init__(SOURCES["twitter_keywords"])
        self.client = tweepy.Client(
            bearer_token=os.environ["TWITTER_ACADEMIC_BEARER"],
            wait_on_rate_limit=True,
        )

    async def fetch(self) -> list[dict]:
        query = "(" + " OR ".join(f'"{k}"' for k in KEYWORDS) + ") lang:en -is:retweet"
        resp = self.client.search_recent_tweets(
            query=query, max_results=100,
            tweet_fields=["created_at", "lang", "public_metrics", "author_id"],
        )
        return [{
            "platform": "twitter",
            "tweet_id": str(t.id),
            "author_id": str(t.author_id),
            "lang": t.lang,
            "created_at": t.created_at.isoformat(),
            "metrics": t.public_metrics,
        } for t in (resp.data or [])]
```

```python
# FILE: backend/app/ingest/social/reddit_watcher.py
import os, praw
from app.ingest.base import BaseWatcher
from app.ingest.registry import SOURCES

SUBS = ["srilanka", "SriLankanBusiness"]

class RedditWatcher(BaseWatcher):
    """PRAW script app. 60 req/min, enforced by PRAW internally."""
    def __init__(self):
        super().__init__(SOURCES["reddit_subs"])
        self.r = praw.Reddit(
            client_id=os.environ["REDDIT_CLIENT_ID"],
            client_secret=os.environ["REDDIT_CLIENT_SECRET"],
            user_agent="EnigmatrixBot/0.1 by u/enigmatrix_research",
        )

    async def fetch(self) -> list[dict]:
        out: list[dict] = []
        for sub in SUBS:
            for post in self.r.subreddit(sub).new(limit=50):
                out.append({
                    "platform": "reddit",
                    "post_id": post.id,
                    "subreddit": sub,
                    "title": post.title,
                    "selftext": (post.selftext or "")[:4000],
                    "score": post.score,
                    "created_utc": post.created_utc,
                    "permalink": post.permalink,
                })
        return out
```

```python
# FILE: backend/app/ingest/social/facebook_watcher.py
import os, httpx
from app.ingest.base import BaseWatcher
from app.ingest.registry import SOURCES

PUBLIC_PAGE_IDS = ["IRDSriLanka", "EPFSriLanka", "SLSI.LK"]

class FacebookWatcher(BaseWatcher):
    """
    Graph API ONLY. NO scraping of groups, profiles, or unverified pages.
    Requires app review with pages_read_engagement scope.
    """
    def __init__(self):
        super().__init__(SOURCES["facebook_public_pages"])
        self.token = os.environ["FB_PAGE_ACCESS_TOKEN"]

    async def fetch(self) -> list[dict]:
        out: list[dict] = []
        async with httpx.AsyncClient(timeout=30) as c:
            for pid in PUBLIC_PAGE_IDS:
                resp = await c.get(
                    f"https://graph.facebook.com/v19.0/{pid}/posts",
                    params={"fields": "id,message,created_time,permalink_url",
                            "access_token": self.token, "limit": 25},
                )
                resp.raise_for_status()
                for p in resp.json().get("data", []):
                    out.append({
                        "platform": "facebook",
                        "post_id": p["id"],
                        "page": pid,
                        "message": (p.get("message") or "")[:4000],
                        "created_time": p.get("created_time"),
                        "permalink": p.get("permalink_url"),
                    })
        return out
```

---

## 5. IRD Defaulter Scrape (M3 Input)

The IRD defaulter list is the canonical compliance signal for Module 3. We scrape monthly, normalise into `(taxpayer_tin, name, default_amount, period)` tuples, and **diff** against the previous snapshot stored in `m3_compliance_history`. New, dropped, or amount-changed rows are emitted as compliance events.

```python
# FILE: backend/app/ingest/scrapers/ird/defaulter.py
import scrapy, hashlib
from app.ingest.registry import SOURCES

class IRDDefaulterSpider(scrapy.Spider):
    name = "ird_defaulter"
    custom_settings = {
        "DOWNLOAD_DELAY": 3.0,
        "ROBOTSTXT_OBEY": True,
        "USER_AGENT": "EnigmatrixBot/0.1 (+https://enigmatrix.lk/bot)",
    }
    start_urls = [SOURCES["ird_defaulter_list"].url_pattern]

    def parse(self, response):
        # Sharepoint-rendered table; selectors verified 2026-04
        rows = response.css("table.ms-listviewtable tr")
        for r in rows[1:]:                         # skip header
            cells = r.css("td::text").getall()
            if len(cells) < 4:
                continue
            tin, name, amount, period = (c.strip() for c in cells[:4])
            yield {
                "source": "ird_defaulter_list",
                "tin": tin,
                "name": name,
                "amount_lkr": _parse_amount(amount),
                "period": period,
                "row_hash": hashlib.sha256(
                    f"{tin}|{name}|{amount}|{period}".encode()
                ).hexdigest(),
            }

def _parse_amount(s: str) -> float:
    return float(s.replace(",", "").replace("LKR", "").strip() or 0)
```

```python
# FILE: backend/app/services/m3/defaulter_diff.py
from sqlalchemy import select
from app.models.m3 import ComplianceHistory, ComplianceEvent

async def apply_snapshot(db, rows: list[dict]) -> dict:
    """Diff today's snapshot against the most recent stored snapshot."""
    prev = {r.tin: r for r in (await db.execute(
        select(ComplianceHistory).where(ComplianceHistory.is_latest.is_(True))
    )).scalars()}
    now = {r["tin"]: r for r in rows}

    added   = [t for t in now  if t not in prev]
    removed = [t for t in prev if t not in now]
    changed = [t for t in now if t in prev and now[t]["row_hash"] != prev[t].row_hash]

    for t in added:
        db.add(ComplianceEvent(tin=t, event="defaulter_added",
                               amount_lkr=now[t]["amount_lkr"]))
    for t in removed:
        db.add(ComplianceEvent(tin=t, event="defaulter_removed"))
    for t in changed:
        db.add(ComplianceEvent(tin=t, event="defaulter_amount_changed",
                               amount_lkr=now[t]["amount_lkr"]))

    # Mark previous snapshot as not-latest, insert new rows
    for h in prev.values():
        h.is_latest = False
    for r in rows:
        db.add(ComplianceHistory(is_latest=True, **r))

    await db.commit()
    return {"added": len(added), "removed": len(removed), "changed": len(changed)}
```

---

## 6. Court Records (lawnet.gov.lk)

LawNet is a low-bandwidth public infrastructure. We crawl with `download_delay=3`, never parallel beyond `CONCURRENT_REQUESTS_PER_DOMAIN=1`, and hand off PDFs to the gazette extractor pipeline from BUILD_07 (which knows OCR, language detection, and segmentation).

```python
# FILE: backend/app/ingest/scrapers/lawnet/spider.py
import scrapy
from app.ingest.registry import SOURCES

class LawNetSpider(scrapy.Spider):
    name = "lawnet"
    custom_settings = {
        "DOWNLOAD_DELAY": 3.0,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "ROBOTSTXT_OBEY": True,
    }
    start_urls = [SOURCES["lawnet_judgments"].url_pattern]

    def parse(self, response):
        for card in response.css("article.judgment-card"):
            href = card.css("a.title::attr(href)").get()
            if href:
                yield response.follow(href, callback=self.parse_judgment)
        next_page = response.css("a.pagination-next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_judgment(self, response):
        pdf = response.css("a.judgment-pdf::attr(href)").get()
        yield {
            "source": "lawnet_judgments",
            "url": response.url,
            "case_no": response.css("h1.case-no::text").get("").strip(),
            "court": response.css("span.court::text").get("").strip(),
            "decided_on": response.css("time.decided::attr(datetime)").get(),
            "pdf_url": response.urljoin(pdf) if pdf else None,
            # PDF handoff: BUILD_07's extractor consumes pdf_url via the
            # `pdf_extraction` queue (see BUILD_07 §3 for the extractor).
            "_handoff": "build_07_extractor",
        }
```

---

## 7. APScheduler (Dev)

For local development and the research demo, APScheduler `>=3.10,<4` runs every job in-process. All cron strings use `Asia/Colombo`.

```python
# FILE: backend/app/ingest/scheduler_dev.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.ingest.registry import SOURCES

# Cross-module jobs (consumers, not scrapers)
from app.tasks.compute_lag import run as compute_lag
from app.tasks.send_alerts import flush as flush_alerts
from app.tasks.run_source import run_source

def build_scheduler() -> AsyncIOScheduler:
    s = AsyncIOScheduler(timezone="Asia/Colombo")

    # 1. Per-source jobs derived from registry
    for name, spec in SOURCES.items():
        s.add_job(
            run_source, CronTrigger.from_crontab(spec.cadence_cron),
            args=[name], id=f"src::{name}", coalesce=True, max_instances=1,
        )

    # 2. Cross-cutting jobs
    s.add_job(flush_alerts,  CronTrigger.from_crontab("*/15 * * * *"),
              id="flush_alerts")
    s.add_job(compute_lag,   CronTrigger.from_crontab("0 2 * * *"),
              id="compute_lag")                       # daily 02:00 Asia/Colombo

    return s
```

Effective cadence (read directly from the registry):

| Concern | Cron | Source(s) |
|---|---|---|
| Gazettes | `0 */6 * * *` | `documents_gov_lk_gazettes` |
| IRD circulars / EPF / ETF / SLSI / eROC / NEDA | `0 */3..6 * * *` | per-spec |
| News (FT, Mirror, LBO, Ada Derana, Hiru) | `0 */1..2 * * *` | per-spec |
| Social (Twitter, Reddit, FB) | `0 */6 * * *` | per-spec |
| Alert fan-out | `*/15 * * * *` | platform |
| Lag aggregation | `0 2 * * *` | platform |
| IRD defaulter snapshot | `0 3 1 * *` | `ird_defaulter_list` |

---

## 8. Celery + Redis (Prod)

Production runs Celery `>=5.3,<6` with Redis 7 as both broker and result backend. Queues are split by SLA: `urgent` (alerts), `default` (regulation ingest), `bulk` (court records, defaulter list, large PDFs).

```python
# FILE: backend/app/ingest/celery_app.py
from celery import Celery
from celery.schedules import crontab
from app.ingest.registry import SOURCES

app = Celery("enigmatrix",
             broker="redis://redis:6379/0",
             backend="redis://redis:6379/1")

app.conf.update(
    task_default_queue="default",
    task_routes={
        "app.tasks.send_alerts.flush":   {"queue": "urgent"},
        "app.tasks.run_source.run_source": {"queue": "default"},
        "app.tasks.run_source.run_bulk_source": {"queue": "bulk"},
    },
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_transport_options={"visibility_timeout": 3600},
    task_default_retry_delay=30,
    task_annotations={
        "*": {
            "max_retries": 5,
            "retry_backoff": True,
            "retry_backoff_max": 600,
            "retry_jitter": True,
        }
    },
    timezone="Asia/Colombo",
    enable_utc=False,
)

# Beat schedule generated from registry
def _cron(s: str) -> crontab:
    m, h, d, mo, dw = s.split()
    return crontab(minute=m, hour=h, day_of_month=d, month_of_year=mo, day_of_week=dw)

app.conf.beat_schedule = {
    f"src::{name}": {
        "task": "app.tasks.run_source.run_bulk_source"
                 if spec.priority_queue == "bulk"
                 else "app.tasks.run_source.run_source",
        "schedule": _cron(spec.cadence_cron),
        "args": (name,),
    }
    for name, spec in SOURCES.items()
} | {
    "flush_alerts": {"task": "app.tasks.send_alerts.flush",
                     "schedule": crontab(minute="*/15")},
    "compute_lag":  {"task": "app.tasks.compute_lag.run",
                     "schedule": crontab(hour=2, minute=0)},
}
```

Dead-letter handling — failed tasks after `max_retries` go to a DLQ topic that is persisted to Postgres for manual replay:

```python
# FILE: backend/app/ingest/celery_dlq.py
from celery.signals import task_failure
from app.db.session import SessionLocal
from app.models.ingest import DeadLetter

@task_failure.connect
def on_task_failure(sender=None, task_id=None, exception=None, args=None, **_):
    if sender and sender.request.retries >= sender.max_retries:
        with SessionLocal() as db:
            db.add(DeadLetter(task_id=task_id, task_name=sender.name,
                              args=str(args), error=repr(exception)))
            db.commit()
```

---

## 9. Token-Bucket Rate Limiter (Outbound)

> **Distinction (important):** BUILD_06 §9 uses **slowapi** to limit *inbound* requests to FastAPI (login, registration, /me). The limiter below is the **opposite direction** — it caps how fast Enigmatrix's spiders and workers hit *external* hosts. The two systems share no code and serve no overlapping purpose. Conflating them is a frequent reviewer confusion.

In-process, asyncio-friendly, per-host token bucket. Each host's bucket is sized from the registry's `download_delay_s` (capacity = 1, refill rate = 1 / delay).

```python
# FILE: backend/app/core/host_rate_limit.py
import asyncio, time
from urllib.parse import urlparse
from app.ingest.registry import SOURCES

class TokenBucket:
    __slots__ = ("capacity", "tokens", "refill_rate", "_last", "_lock")

    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate           # tokens per second
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, n: float = 1.0) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                self.tokens = min(self.capacity,
                                  self.tokens + (now - self._last) * self.refill_rate)
                self._last = now
                if self.tokens >= n:
                    self.tokens -= n
                    return
                deficit = n - self.tokens
                await asyncio.sleep(deficit / self.refill_rate)


_buckets: dict[str, TokenBucket] = {}
_default_delay = 1.5

def _delay_for_host(host: str) -> float:
    for spec in SOURCES.values():
        if urlparse(spec.base_url).netloc == host:
            return spec.download_delay_s
    return _default_delay

def bucket_for(host: str) -> TokenBucket:
    b = _buckets.get(host)
    if b is None:
        delay = _delay_for_host(host)
        b = _buckets[host] = TokenBucket(capacity=1.0, refill_rate=1.0 / delay)
    return b
```

For Scrapy, the same bucket is wired in via a downloader middleware:

```python
# FILE: backend/app/ingest/scrapers/middleware.py
from urllib.parse import urlparse
from app.core.host_rate_limit import bucket_for

class HostBucketMiddleware:
    async def process_request(self, request, spider):
        await bucket_for(urlparse(request.url).netloc).acquire()
        return None
```

---

## 10. Idempotency & Dedup

A single `ingest_seen` table provides global, content-addressed dedup. Every spider/worker stages items through it before persistence.

```sql
-- FILE: backend/app/db/migrations/versions/0012_ingest_seen.py
CREATE TABLE ingest_seen (
    id            BIGSERIAL PRIMARY KEY,
    source_id     TEXT NOT NULL,
    content_sha256 CHAR(64) NOT NULL,
    item_url      TEXT,
    seen_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_id, content_sha256)
);
CREATE INDEX ix_ingest_seen_source_seen ON ingest_seen (source_id, seen_at DESC);
```

```python
# FILE: backend/app/ingest/scrapers/pipelines.py
import hashlib, json
from sqlalchemy.exc import IntegrityError
from app.db.session import SessionLocal
from app.models.ingest import IngestSeen

class DedupPipeline:
    def process_item(self, item, spider):
        sha = hashlib.sha256(
            json.dumps({k: item[k] for k in sorted(item) if not k.startswith("_")},
                       sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        with SessionLocal() as db:
            try:
                db.add(IngestSeen(source_id=item["source"],
                                  content_sha256=sha,
                                  item_url=item.get("url")))
                db.commit()
            except IntegrityError:
                db.rollback()
                raise scrapy.exceptions.DropItem(f"duplicate {sha[:8]}")
        return item
```

---

## 11. Observability Hooks

Every ingestion run emits a structured `ingest_event` log line through the structlog pipeline already wired in BUILD_03. The fields are stable and consumed by BUILD_15 (observability) for dashboards and alerts.

| Field | Type | Description |
|---|---|---|
| `run_id` | UUID | One per call to `BaseWatcher.run` or Scrapy crawl |
| `source` | str | Registry key |
| `items_seen` | int | Items returned by fetcher before dedup |
| `items_inserted` | int | Items that survived dedup + persistence |
| `duration_ms` | int | Wall clock |
| `errors_count` | int | Exceptions caught at run boundary |

Scrapy emits the same structure via a stats extension that converts `scrapy.statscollectors` into a single log line at `spider_closed`. See BUILD_15 §3 for the OpenSearch index template.

---

## Acceptance Criteria

- [ ] `python -c "from app.ingest.registry import SOURCES; print(len(SOURCES))"` returns >= 18 entries.
- [ ] `scrapy crawl daily_ft` produces >= 1 row in `ingest_seen` and 0 ToS violations (verified by `ROBOTSTXT_OBEY` + `USER_AGENT` checks).
- [ ] Re-running the same crawl produces 0 new rows (dedup works end-to-end).
- [ ] `EROCWorker().run()` returns a non-empty list when run against a known-good fixture; selectors are documented as "verify by inspection".
- [ ] `TwitterWatcher`, `RedditWatcher`, and `FacebookWatcher` each persist to `social_posts_raw` without redistributing raw text beyond ToS limits (Twitter: IDs only by default).
- [ ] `IRDDefaulterSpider` + `apply_snapshot` produce at least one `ComplianceEvent` row when run against two synthetic snapshots that differ by one TIN.
- [ ] LawNet crawl honours `DOWNLOAD_DELAY=3.0` (verified by Scrapy stats `downloader/request_count` vs elapsed time).
- [ ] APScheduler `build_scheduler()` registers one job per registry entry plus `flush_alerts` and `compute_lag`.
- [ ] Celery `beat_schedule` regenerated from the registry contains the same set of tasks; `bulk` queue receives `lawnet_judgments` and `ird_defaulter_list`.
- [ ] Token bucket: 30 sequential calls to `bucket_for("www.lawnet.gov.lk").acquire()` complete in >= 87s (3s delay × 29 gaps).
- [ ] Every successful run emits exactly one `ingest_event` log with the documented field set.

---

## Claude Prompts

### Prompt 1 — Source registry + base watcher class

```
Generate backend/app/ingest/registry.py and backend/app/ingest/base.py per
BUILD_12 §1. Requirements:
- SourceSpec dataclass with fields: name, base_url, url_pattern, parser,
  cadence_cron, owner_module, transport, tos_notes, robots_compliance,
  download_delay_s, priority_queue, tags.
- A SOURCES dict with the 18 entries listed in BUILD_12 §1, exact cron
  strings preserved.
- BaseWatcher abstract class with async run() that emits an ingest_event
  structlog line (run_id, source, items_seen, items_inserted, duration_ms,
  errors_count) and delegates fetching to subclass `fetch()`.
- Add a unit test that verifies every SourceSpec.cadence_cron parses as a
  valid 5-field cron via croniter.
```

### Prompt 2 — Token-bucket rate limiter

```
Generate backend/app/core/host_rate_limit.py per BUILD_12 §9.
Requirements:
- TokenBucket(capacity, refill_rate) with asyncio.Lock and monotonic clock.
- bucket_for(host) returns a singleton TokenBucket; refill rate derived
  from SOURCES[*].download_delay_s by matching urlparse(base_url).netloc.
- Default delay 1.5s for unknown hosts.
- Add a Scrapy DownloaderMiddleware HostBucketMiddleware that awaits
  bucket_for(host).acquire() before every request.
- Include a pytest that schedules 10 acquisitions on a 0.1s/refill bucket
  and asserts the wall-clock duration >= 0.9s.
- Add an inline docstring noting this is OUTBOUND and unrelated to
  BUILD_06's slowapi inbound limiter.
```

### Prompt 3 — Celery beat config from registry

```
Generate backend/app/ingest/celery_app.py per BUILD_12 §8. Requirements:
- Celery app with Redis 7 broker/backend.
- task_routes mapping send_alerts.flush -> 'urgent', run_bulk_source ->
  'bulk', everything else default.
- Retry policy: max_retries=5, exponential backoff with jitter, capped
  at 600s.
- beat_schedule built programmatically from app.ingest.registry.SOURCES,
  with bulk-priority sources routed to run_bulk_source.
- Dead-letter signal handler that writes to a DeadLetter table on final
  retry exhaustion.
- Add a test that asserts every SOURCES key has a matching beat entry
  and that the queue routing matches the spec's priority_queue.
```

### Prompt 4 — IRD defaulter scraper with snapshot diff

```
Generate backend/app/ingest/scrapers/ird/defaulter.py and
backend/app/services/m3/defaulter_diff.py per BUILD_12 §5. Requirements:
- IRDDefaulterSpider with DOWNLOAD_DELAY=3, ROBOTSTXT_OBEY=True, custom
  user agent. Selectors documented as 'verify by inspection (2026-04)'.
- _parse_amount tolerates 'LKR 1,234,567.00' and bare numbers.
- apply_snapshot(db, rows) computes added/removed/changed by row_hash
  (sha256 of tin|name|amount|period), writes ComplianceEvent rows, and
  flips the previous snapshot's is_latest flag in a single transaction.
- Idempotent: re-running with identical rows produces 0 new events.
- Include a pytest fixture with two synthetic snapshots and assert
  exactly 1 added, 1 removed, 1 amount_changed event when one TIN is
  added, one is dropped, and one has its amount changed.
```

---

**Prev:** `BUILD_11_ML_Training_Pipeline.md` &nbsp;·&nbsp; **Next:** `BUILD_13_Admin_and_Annotation.md`
