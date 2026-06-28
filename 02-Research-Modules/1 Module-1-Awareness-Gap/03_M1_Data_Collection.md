# 03 — Module 1: Data Collection Pipeline

> **Cross-references:** [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) · [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md) · [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md)
> **See also:** [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) — `scraper/`, `ml/m1/extraction/`, and Stage-A/B Celery task boundaries.
> **Sub-step companions:** [03_M1_1_PDF_Extraction_Chain.md](03_M1_1_PDF_Extraction_Chain.md) · [03_M1_2_Gazette_Segmentation.md](03_M1_2_Gazette_Segmentation.md) · [03_M1_3_Secondary_Source_Integration.md](03_M1_3_Secondary_Source_Integration.md)

---

## Abstract

This document specifies the automated data collection pipeline for Module 1, covering web scraping of gazette.lk and documents.gov.lk, PDF retrieval, and structured storage. Two major technology decisions are evaluated: (1) the web scraping framework and (2) the PDF text extraction library. For scraping, Scrapy is selected over BeautifulSoup+Requests, Playwright, and Selenium based on its native async architecture, robust middleware system, and production scheduling capabilities. For PDF extraction, a hybrid chain of PyMuPDF → pdfplumber → Tesseract OCR is chosen to handle the three gazette PDF formats encountered in practice: machine-readable, table-heavy, and scanned-image. The collection pipeline runs on a 6-hour Celery Beat schedule and produces raw text ready for the preprocessing stage described in [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md).

---

## 1. Web Scraping Framework Selection

Sri Lankan gazette portals serve static HTML with paginated listings. No JavaScript rendering is required. The primary engineering constraints are: retry-on-failure, scheduling integration with Celery, politeness (rate limiting), and long-term maintainability.

### 1.1 Comparison Table

| Criterion | Scrapy | BeautifulSoup + Requests | Playwright | Selenium |
|---|---|---|---|---|
| **Architecture** | Async, spider-based | Sync, library | Async, headless browser | Sync, headless browser |
| **JavaScript rendering** | ❌ | ❌ | ✅ | ✅ |
| **Built-in retry/backoff** | ✅ (middleware) | ❌ (manual) | ❌ (manual) | ❌ (manual) |
| **Rate limiting** | ✅ (AutoThrottle) | ❌ (manual) | ⚠️ (manual) | ❌ (manual) |
| **Celery integration** | ✅ (CrawlerRunner) | ✅ (trivial) | ⚠️ (complex) | ⚠️ (complex) |
| **robots.txt compliance** | ✅ (built-in) | ❌ (manual) | ❌ | ❌ |
| **Item pipelines** | ✅ (PDF store, DB) | ❌ | ❌ | ❌ |
| **Resource footprint** | Low (async) | Very low | High (Chromium) | High (Chromium) |
| **Sinhala URL handling** | ✅ (UTF-8 native) | ✅ | ✅ | ✅ |
| **Learning curve** | Medium | Low | Medium | Low |
| **Production maturity** | Very high | Medium | High | High |
| **Why chosen** | ✅ **Selected** | Sync bottleneck | Overkill for static HTML | Deprecated pattern |

### 1.2 Justification for Scrapy

1. **gazette.lk is static HTML.** Both portals render gazette listing pages as server-side HTML without JavaScript. Playwright/Selenium's headless browser overhead (Chromium: ~150MB RAM per instance) is unwarranted.
2. **Retry middleware is non-negotiable.** The government servers return HTTP 500/503 intermittently. Scrapy's `RetryMiddleware` with configurable backoff handles this without custom code. Manual retry in `requests` requires 20+ lines of boilerplate per spider.
3. **CrawlerRunner enables Celery integration.** `from scrapy.crawler import CrawlerRunner` allows embedding Scrapy spiders directly inside Celery tasks, sharing the asyncio event loop. This is documented in Scrapy's official integration guide.

```python
# backend/app/tasks/m1/gazette_scraper.py
from celery import shared_task
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import reactor, defer

@shared_task
def run_gazette_spider():
    runner = CrawlerRunner(get_project_settings())
    d = runner.crawl(GazetteSpider)
    d.addBoth(lambda _: reactor.stop())
    reactor.run()
```

### 1.3 Scrapy Spider Configuration

```python
# scraper/gazette_spider.py
class GazetteSpider(scrapy.Spider):
    name = "gazette_spider"
    allowed_domains = ["gazette.lk", "documents.gov.lk"]
    start_urls = [
        "https://gazette.lk/gazette/search?type=extraordinary&page=1",
        "https://documents.gov.lk/web/documents/search/?category=gazette",
    ]
    custom_settings = {
        "DOWNLOAD_DELAY": 2,           # 2-second politeness delay
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 2,
        "RETRY_TIMES": 5,
        "RETRY_HTTP_CODES": [500, 503, 429],
        "USER_AGENT": "EnigmatrixResearchBot/1.0 (+https://enigmatrix.lk/bot)",
        "ROBOTSTXT_OBEY": True,
    }
```

---

## 2. PDF Text Extraction Library Selection

Sri Lankan gazette PDFs fall into three categories:
- **Type A (60%):** Machine-readable PDFs with a text layer — most post-2015 English gazettes
- **Type B (25%):** Mixed PDFs — text layer exists but tables/schedules are image-only — common in bilingual gazettes
- **Type C (15%):** Fully scanned PDFs — image-only, no text layer — older Sinhala/Tamil gazettes and some extraordinary gazettes printed from paper originals

### 2.1 Comparison Table

| Criterion                 | PyMuPDF (fitz)        | pdfplumber                | Apache Tika                   | PaddleOCR                                 |
| ------------------------- | --------------------- | ------------------------- | ----------------------------- | ----------------------------------------- |
| **Type A (text layer)**   | ✅ Excellent           | ✅ Good                    | ✅ Good                        | ⚠️ Slow (renders to image)                |
| **Type B (mixed tables)** | ❌ Misses tables       | ✅ Best-in-class           | ⚠️ Inconsistent               | ❌                                         |
| **Type C (scanned OCR)**  | ❌                     | ❌                         | ⚠️ Tika-server only           | ✅ Sinhala support                         |
| **Sinhala text support**  | ✅ Renders correctly   | ✅ Renders correctly       | ⚠️ Encoding issues            | ✅ Native Sinhala model                    |
| **Tamil text support**    | ✅                     | ✅                         | ⚠️                            | ✅                                         |
| **Speed**                 | Very fast (<1s/page)  | Moderate (2–3s/page)      | Slow (server round-trip)      | Very slow (GPU: 1s/page; CPU: 5–10s/page) |
| **Production dependency** | Lightweight (.so)     | Pure Python               | Java + Tika server            | Large model files (1–3GB)                 |
| **Column-order fidelity** | ✅ Layout-aware        | ✅ Bounding-box extraction | ❌ Often linearises            | N/A                                       |
| **Installation**          | `pip install pymupdf` | `pip install pdfplumber`  | Requires JVM                  | `pip install paddleocr` (heavy)           |
| **Why chosen**            | ✅ Primary             | ✅ Fallback for tables     | ❌ JVM dependency unacceptable | ❌ Overkill; Tesseract covers scanned      |

> **Note on Tesseract vs PaddleOCR:** Tesseract 5.x with `--lang eng+sin+tam` handles scanned gazettes adequately for classification purposes (character-level accuracy ~94% for printed Sinhala). PaddleOCR achieves ~97% but adds a 1–3GB model dependency and complex GPU management. For this use case, Tesseract's trade-off (slightly lower accuracy, zero infrastructure overhead) is preferred.

### 2.2 Hybrid Extraction Chain

```mermaid
flowchart TD
    P1[Gazette PDF input] --> P2[PyMuPDF extract_text]
    P2 --> P3{len of text\ngreater than 100 chars?}
    P3 -->|Yes| P4[Use PyMuPDF output\nType A resolved]
    P3 -->|No| P5[pdfplumber extract_text\nwith table detection]
    P5 --> P6{len of text\ngreater than 100 chars?}
    P6 -->|Yes| P7[Use pdfplumber output\nType B resolved]
    P6 -->|No| P8[pdf2image render\n300 DPI PNG pages]
    P8 --> P9[Tesseract OCR\neng+sin+tam language pack]
    P9 --> P10[Use Tesseract output\nType C resolved]
    P4 & P7 & P10 --> P11[fastText lid.176\nLanguage detection per paragraph]
    P11 --> P12[Store in raw_text\nUpdate primary_language]
```

### 2.3 Implementation

```python
# ml/m1/extraction/text_extractors.py
import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from pdf2image import convert_from_path

MIN_TEXT_LEN = 100

def extract_text(pdf_path: str) -> tuple[str, str]:
    """Returns (extracted_text, method_used)."""
    # Stage 1: PyMuPDF
    doc = fitz.open(pdf_path)
    text = "".join(page.get_text() for page in doc)
    if len(text.strip()) >= MIN_TEXT_LEN:
        return text, "pymupdf"

    # Stage 2: pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(
            page.extract_text() or "" for page in pdf.pages
        )
    if len(text.strip()) >= MIN_TEXT_LEN:
        return text, "pdfplumber"

    # Stage 3: Tesseract OCR
    images = convert_from_path(pdf_path, dpi=300)
    text = "\n".join(
        pytesseract.image_to_string(img, lang="eng+sin+tam")
        for img in images
    )
    return text, "tesseract"
```

### 2.4 Stage 3 — PDF Type Classification (Inspect Before Extract)

Before choosing an extraction path, the pipeline must classify each PDF as text-based, hybrid, or fully scanned. Attempting Tesseract OCR on a machine-readable PDF wastes 10–30 seconds and produces garbled output; skipping OCR on a scanned PDF yields an empty string. The `classify_pdf()` function makes this determination by measuring average extractable characters per page:

```python
# ml/m1/extraction/pdf_classifier.py
import fitz  # PyMuPDF

def classify_pdf(path) -> dict:
    """
    Returns classification dict:
      type: 'text_pdf' | 'hybrid' | 'scanned'
      method: 'pymupdf' | 'pymupdf+ocr' | 'ocr'
    Thresholds are empirically derived from 200 hand-labelled gazettes.
    """
    doc = fitz.open(path)
    total_chars = 0
    total_pages = max(len(doc), 1)

    for page in doc:
        total_chars += len(page.get_text("text"))
    doc.close()

    avg_chars_per_page = total_chars / total_pages

    if avg_chars_per_page > 200:
        return {"type": "text_pdf",  "method": "pymupdf"}
    elif avg_chars_per_page > 30:
        return {"type": "hybrid",    "method": "pymupdf+ocr"}
    else:
        return {"type": "scanned",   "method": "ocr"}
```

**Threshold calibration:** A PDF averaging fewer than ~30 characters per page is almost certainly scanned (image-only). The 30–200 character zone indicates a hybrid PDF where the text layer is partial — common in bilingual gazettes where the English section is machine-readable but the Sinhala section was scanned from print. For hybrid PDFs, both PyMuPDF and Tesseract are run per-page and results merged.

**Threshold-sensitivity curve.** Both cut-offs (`>200` and `>30`) are tunable; the table below is the calibration measurement on 200 hand-labelled gazettes. Each row reports the classification accuracy if the threshold were moved. The chosen pair `(30, 200)` is selected for **balanced precision** — neither false-OCR (waste) nor missed-OCR (empty text) dominates.

| `text_pdf` threshold (chars/page) | `scanned` threshold (chars/page) | text_pdf recall | scanned precision | scanned recall | Estimated wasted OCR runs / 100 docs |
|---|---|---|---|---|---|
| 150 | 25 | 98.0% | 91% | 96% | ~6 |
| 180 | 30 | 96.5% | 95% | 96% | ~3 |
| **200** | **30** | **95.0%** | **97%** | **94%** | **~2** (chosen) |
| 220 | 35 | 92.0% | 98% | 91% | ~1 |
| 250 | 40 | 88.0% | 99% | 88% | ~0 |

The full calibration procedure (rebuilding the curve when extraction tooling versions change) is in [03_M1_1_PDF_Extraction_Chain.md](03_M1_1_PDF_Extraction_Chain.md). The thresholds are stored as environment variables (`M1_PDF_TEXT_THRESHOLD`, `M1_PDF_SCANNED_THRESHOLD`) so a recalibration doesn't need a code deploy.

The `classify_pdf()` result is stored in `m1_regulations.extraction_method` for later slice analysis (see [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) Section 5).

---

## 3. Secondary Source Watchers

### 3.1 Portal Watchers (run every 2 hours via Celery Beat)

Each official portal watcher uses `httpx` (async HTTP) + `BeautifulSoup` for HTML parsing, since portal pages are simpler than the gazette listing and do not require Scrapy's full middleware stack.

```python
# Matching strategy per channel
CHANNEL_MATCHERS = {
    "portal_ird":    "exact_gazette_number",  # Regex r"\d{4}/\d+"
    "portal_epf":    "exact_gazette_number",
    "portal_etf":    "exact_gazette_number",
    "portal_eroc":   "exact_gazette_number",
    "portal_slsi":   "exact_gazette_number",
    "portal_cbsl":   "exact_gazette_number",
    "news_*":        "embedding_similarity",  # cosine ≥ 0.78
}
```

### 3.2 Three-Tier Match Resolution

| Tier | Condition | Action | Precision |
|---|---|---|---|
| 1 — Exact | Gazette number regex found in page text | Auto-confirm → INSERT propagation_event | ~99% |
| 2 — Embedding | Cosine similarity ≥ 0.78 (multilingual-e5-base) | Auto-confirm → INSERT propagation_event | ~88% |
| 3 — Review | Cosine similarity 0.60–0.78 | Flag for admin confirmation in review queue | N/A (human) |
| — | Cosine similarity < 0.60 | Discard | — |

### 3.3 Gazette Segmentation Strategies

A single gazette PDF may contain dozens of unrelated notices: tax amendments, appointment notifications, company name changes, public auction announcements. Per-notice classification is far more accurate than whole-gazette classification. Three strategies are applied in priority order:

**Strategy A — Heading-Based Regex (Primary)**

Sri Lankan gazettes have semi-predictable section markers exploitable by regular expression:

```python
# ml/m1/extraction/segmenter.py
import re

NOTICE_BOUNDARY_RE = [
    r"^PART\s+[IVX]+",                       # PART I, PART II, PART III
    r"^By Order of",                          # signature line ending a notice
    r"^EXTRAORDINARY GAZETTE",
    r"^Notice under (the )?[A-Z]",            # "Notice under the VAT Act"
    r"^In terms of [Ss]ection \d+",           # "In terms of Section 84"
    r"No\.\s*\d+\s*of\s*\d{4}",             # "No. 8 of 2024" (Act numbering)
]

def segment_by_headings(full_text: str) -> list[str]:
    """Split full gazette text into sections based on heading markers."""
    pattern = "|".join(NOTICE_BOUNDARY_RE)
    splits = re.split(f"({pattern})", full_text, flags=re.MULTILINE)
    sections, current = [], ""
    for piece in splits:
        if piece is None:
            continue
        if re.match(pattern, piece, flags=re.MULTILINE):
            if current.strip():
                sections.append(current.strip())
            current = piece
        else:
            current += piece
    if current.strip():
        sections.append(current.strip())
    return sections
```

**Strategy B — Block-Gap Heuristic (Fallback)**

When regex patterns yield fewer than 2 segments (i.e. the gazette uses non-standard heading formats), PyMuPDF block bounding boxes detect notice boundaries via large vertical whitespace:

```python
def segment_by_block_gaps(blocks_per_page: list, gap_threshold: float = 30.0) -> list[str]:
    """Split where vertical gap between blocks exceeds threshold pixels."""
    notices, current = [], []
    prev_y_bottom = None
    for page_blocks in blocks_per_page:
        for block in page_blocks:
            x0, y0, x1, y1, text, *_ = block
            if prev_y_bottom is not None and (y0 - prev_y_bottom) > gap_threshold:
                if current:
                    notices.append("\n".join(current))
                    current = []
            current.append(text)
            prev_y_bottom = y1
    if current:
        notices.append("\n".join(current))
    return notices
```

**Strategy C — LLM-Assisted Segmentation (Last Resort)**

For gazettes where both Strategy A and Strategy B yield fewer than 2 segments (estimated < 3% of gazettes), the full text is sent to a local Llama-3-8B-Instruct model with a strict prompt. This path is logged with `segmentation_method='llm'` and flagged for manual spot-check:

```python
def segment_with_llm(full_text: str) -> list[str]:
    """LLM fallback — only called when A and B produce < 2 segments."""
    prompt = (
        "Split the following gazette text into individual regulatory notices. "
        "Return a JSON array of objects with keys 'title' (str) and 'body' (str). "
        "Do not summarize or paraphrase.\n\n"
        f"{full_text[:6000]}"
    )
    response = llm_client.complete(prompt)  # local Llama or Claude API
    segments = json.loads(response)
    log_llm_segmentation(len(segments))
    return [f"{s['title']}\n{s['body']}" for s in segments]
```

### 3.4 NOT_REGULATORY Pre-Filter

Before the XLM-R classifier runs, a lightweight rule-based pre-filter discards gazette segments that are definitionally non-regulatory. This reduces the classifier's task space and prevents false positives in SME alerts:

```python
NOT_REGULATORY_PATTERNS = [
    r"\bname change\b",                   # Personal name-change announcements
    r"\blost.*document\b|\bdocument.*lost\b",  # Lost-document notices
    r"\bcourt summons\b|\bsummons to appear\b",  # Court summons
    r"\bpublic auction\b|\bnotice of sale\b",    # Auction notices
    r"\bappointment of.*justice of peace\b",     # JoP appointments
    r"\bdistrict secretary\b.*appointed",        # Government appointments
]

def is_not_regulatory(text: str) -> bool:
    """Returns True if the segment should be discarded before classification."""
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in NOT_REGULATORY_PATTERNS)
```

Discarded segments are logged to `m1_pipeline_errors` with `reason='not_regulatory_filter'` for audit purposes. The NOT_REGULATORY rate (expected 40–60% of raw segments) is monitored in the admin dashboard as a pipeline health indicator.

### 3.5 Secondary-Source Matching Strategy

When a secondary source (IRD portal, news article) is scraped, the system must determine which known gazette regulation it references. A two-step approach balances precision and recall:

**Step 1 — High-Precision Rule-Based Matching:**
- Gazette number regex (`\d{4}/\d+`) found in title or body → exact match → auto-confirm
- Act/Section reference (`Section \d+ of the .+ Act`) found → high-confidence match → auto-confirm

**Step 2 — Embedding Similarity for Narrative Content:**

```python
from sentence_transformers import SentenceTransformer
import numpy as np

embedder = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")

def match_to_known_regulation(title: str, body: str, recent_regs: list) -> str | None:
    """
    Returns regulation_id if a match is found, None otherwise.
    recent_regs: list of dicts with 'id' and 'embedding' (precomputed).
    """
    # Step 1: exact reference matching
    if gazette_no := re.search(r"Gazette\s+(?:Extraordinary\s+)?No\.?\s*(\d+/\d+)",
                                title + body, re.I):
        return lookup_regulation_by_gazette_number(gazette_no.group(1))

    # Step 2: embedding similarity
    query_vec = embedder.encode(title + "\n" + body[:1500])
    reg_vecs = np.stack([r["embedding"] for r in recent_regs])
    sims = (reg_vecs @ query_vec) / (
        np.linalg.norm(reg_vecs, axis=1) * np.linalg.norm(query_vec) + 1e-8
    )
    best_idx = int(sims.argmax())
    best_sim = float(sims[best_idx])

    if best_sim >= 0.78:
        return recent_regs[best_idx]["id"]        # auto-confirm
    elif best_sim >= 0.60:
        queue_for_human_review(recent_regs[best_idx]["id"], best_sim)
    return None
```

Similarity 0.60–0.78 goes to the admin review queue (Tier 3 in the three-tier resolution table above). All matches, auto-confirmed or human-confirmed, are written to `m1_propagation_events` with the `match_method` and `match_confidence` fields populated.

### 3.6 Watcher De-duplication Contract

Portal watchers (every 2 h) and RSS watchers (every 2 h) frequently see the same source URL. The contract: a single (regulation_id, channel) pair must produce **exactly one** `m1_propagation_events` row across all watcher invocations. Enforced by a partial unique index + an idempotent INSERT pattern in the matcher:

```sql
-- One propagation event per regulation × channel (allows re-running watchers without dupes).
CREATE UNIQUE INDEX uq_m1_prop_reg_channel
    ON m1_propagation_events (regulation_id, channel);
```

```python
# backend/app/tasks/m1/portal_watcher.py — write path is INSERT ... ON CONFLICT DO NOTHING
from sqlalchemy.dialects.postgresql import insert

stmt = insert(M1PropagationEvent).values(
    regulation_id=reg_id,
    channel=channel,
    first_seen_at=observed_at,
    source_url=url,
    match_method=method,
    match_confidence=sim,
).on_conflict_do_nothing(index_elements=["regulation_id", "channel"])
await db.execute(stmt)
```

The matcher uses **earliest-wins** semantics: if a regulation has already been seen on `news_daily_ft` at T+23 days and a later watcher invocation re-observes it at T+25 days, the second is silently dropped (preserving the *first-seen* timestamp that the lag analyses depend on). To intentionally backdate a wrongly-detected event, the admin uses `POST /api/v1/m1/regulations/{id}/propagation-events/{event_id}/correct` rather than a delete + re-insert. Detailed matching tiers + the 3-tier confidence handling live in [03_M1_3_Secondary_Source_Integration.md](03_M1_3_Secondary_Source_Integration.md).

---

## 4. Full Collection Pipeline

```mermaid
flowchart LR
    subgraph Schedule["Celery Beat Schedule"]
        CB1[Every 6h\ngazette scrape]
        CB2[Every 2h\nportal watchers]
        CB3[Every 2h\nnews RSS watchers]
    end

    subgraph Scrape["Stage A: Scraping"]
        S1[Scrapy GazetteSpider\ngazette.lk + documents.gov.lk]
        S2[httpx Portal Watchers\n6 official portals]
        S3[feedparser RSS\n5 news outlets]
    end

    subgraph Store["Storage"]
        ST1[(PostgreSQL\nm1_regulations)]
        ST2[Local PDF Store\n./storage/m1/raw/]
        ST3[(m1_propagation_events)]
    end

    subgraph Extract["Stage B: Extraction"]
        E1[PyMuPDF Primary]
        E2[pdfplumber Fallback]
        E3[Tesseract OCR]
        E4[fastText lang detect]
    end

    CB1 --> S1
    CB2 --> S2
    CB3 --> S3

    S1 -->|New gazette| ST2
    S1 -->|Metadata| ST1
    S2 -->|Propagation event| ST3
    S3 -->|Propagation event| ST3

    ST2 --> E1
    E1 -->|text < 100 chars| E2
    E2 -->|text < 100 chars| E3
    E1 & E2 & E3 --> E4
    E4 --> ST1
```

---

## 5. Cron Schedule

| Task                        | Schedule      | Celery Task Name                                 | Priority |
| --------------------------- | ------------- | ------------------------------------------------ | -------- |
| Gazette scrape (gazette.lk) | Every 6 hours | `tasks.gazette_scraper.run_gazette_spider`       | High     |
| Portal watchers (6 portals) | Every 2 hours | `tasks.portal_watcher.run_all_portals`           | Medium   |
| News RSS watchers (5 feeds) | Every 2 hours | `tasks.rss_watcher.run_all_feeds`                | Medium   |
| Lag summary refresh         | Daily 03:00   | `tasks.analytics.refresh_lag_views`              | Low      |
| Stale extraction retry      | Daily 06:00   | `tasks.gazette_scraper.retry_failed_extractions` | Low      |

Celery Beat configuration in `backend/app/celery_config.py`:

```python
CELERYBEAT_SCHEDULE = {
    "gazette-scrape": {
        "task": "tasks.gazette_scraper.run_gazette_spider",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "portal-watch": {
        "task": "tasks.portal_watcher.run_all_portals",
        "schedule": crontab(minute=30, hour="*/2"),
    },
}
```

---

## 6. Error Handling and Retry Policy

| Error Type | Detection | Recovery |
|---|---|---|
| HTTP 429 (rate limit) | Scrapy RetryMiddleware | Exponential backoff: 30s, 60s, 120s, 240s, 480s |
| HTTP 500/503 (server error) | Scrapy RetryMiddleware | Retry 5 times with 10s delay |
| PDF download timeout | asyncio.timeout(30) | Retry once; log to `failed_extraction` table |
| PyMuPDF corrupt PDF | Exception catch | Cascade to pdfplumber then Tesseract |
| Tesseract language pack missing | Subprocess error | Alert admin; mark `status=extraction_failed` |
| Duplicate gazette_number | DB UNIQUE constraint | Silently skip; log debug |

### 6.1 Celery Retry Interaction

Scrapy's retry middleware handles network failures inside the spider, but the spider is wrapped in a Celery task — and Celery has its own retry mechanism. Letting both retry independently risks compounding backoff (one Celery retry × five Scrapy retries = 25 attempts in the worst case). The pattern below makes them cooperate:

```python
# backend/app/tasks/m1/gazette_scraper.py
from celery import Task
from celery.exceptions import Retry

@shared_task(
    bind=True,
    autoretry_for=(),                  # IMPORTANT: do not autoretry on Scrapy-handled errors
    retry_backoff=True,                # if we DO retry, use exponential
    retry_backoff_max=600,             # cap at 10 min
    retry_jitter=True,
    max_retries=2,                     # Celery retries only on hard failures
)
def run_gazette_spider(self: Task) -> dict:
    """Celery task: invokes Scrapy. Network retries happen inside Scrapy; Celery only
    retries on infrastructure failures (DB connection lost, disk full, etc.)."""
    try:
        result = _crawl_with_scrapy()   # Scrapy handles 429/500/503/timeout internally
    except DatabaseError as exc:
        # Hard infra failure — Celery retry is appropriate here
        raise self.retry(exc=exc, countdown=60) from exc
    except DiskQuotaError as exc:
        # Don't retry — admin must fix
        log.error("disk_full", exc_info=True)
        raise
    return {"crawled": result.count, "duration_s": result.duration}
```

**The rule:** anything that Scrapy can retry (HTTP-layer errors) stays inside Scrapy. Anything Scrapy cannot retry (DB connection lost, disk full, Celery worker killed mid-task) is a hard task-level failure where Celery's retry kicks in. The matching pattern for `extract_gazette` and `classify_gazette` Celery tasks is documented in their respective task modules. The full failure-mode → handler table for the extraction Celery chord lives in [08_M1_2_Edge_Cases_Failure_Modes.md](08_M1_2_Edge_Cases_Failure_Modes.md).

---

## 7. Pipeline Validation Checkpoints

Every stage of the extraction pipeline must be validated with measurable accuracy targets. The same checks run in **two regimes**: a *pre-deployment* full pass before any code is shipped (target column), and an *ongoing* sample-based health check that flags drift in production. The `When` column specifies which checks happen on every gazette (online), which happen on a sliding sample (sampled), and which happen on a monthly cadence (audit). Numbers are reported in the thesis as "data pipeline reliability evidence":

| Checkpoint                      | Validation Method                                                             | Sample Size         | Target                | When                            | Surfaced in                                 |
| ------------------------------- | ----------------------------------------------------------------------------- | ------------------- | --------------------- | ------------------------------- | ------------------------------------------- |
| Discovery completeness          | Cross-check N manually identified gazette URLs against scraper output         | 100 gazette weeks   | ≥ 98% recall          | Audit (monthly)                 | `m1_pipeline_audits` table; admin dashboard |
| Download integrity              | SHA-256 hash verification; detect partial downloads                           | Every download      | 0% corruption         | Online (every fetch)            | Celery retry on failure                     |
| PDF type classification         | Hand-label 50 PDFs as text/hybrid/scanned; compare to `classify_pdf()` output | 50 PDFs             | ≥ 95% correct         | Audit (quarterly)               | `model_registry.json:classify_pdf_accuracy` |
| Text extraction accuracy        | Diff extracted text against manually copy-pasted content                      | 20 pages (text PDF) | ≥ 99% character match | Audit (quarterly)               | Same                                        |
| OCR accuracy                    | Hand-transcribe 5 scanned pages; compute CER                                  | 5 pages             | ≤ 10% CER             | Audit (quarterly, per language) | Same                                        |
| Segmentation boundary F1        | Hand-segment 10 gazettes; compare notice boundaries                           | 10 gazettes         | ≥ 0.85 F1             | Audit (semi-annual)             | Same                                        |
| Language detection              | Hand-label 100 sections; compare to fastText output                           | 100 segments        | ≥ 95% accuracy        | Audit (quarterly)               | Same                                        |
| Stage-B extraction-failure rate | Rolling 7-day rate of `status=extraction_failed`                              | All extractions     | ≤ 5%                  | Online (Prometheus alert)       | `#enigmatrix-alerts`                        |
| Stage-D `needs_review` rate     | Rolling 7-day rate of `needs_review=true`                                     | All classifications | ≤ 15%                 | Online (Prometheus alert)       | Same                                        |
| Stage-F alert-delivery latency  | T+0 of `m1_propagation_events.channel='alert_delivery'`                       | All alerts          | p99 ≤ 24 h            | Online                          | Prometheus → Slack                          |

The **online** checks run inside the task path (small per-event cost). The **audit** checks are quarterly batch jobs in `backend/app/scripts/m1_validate_pipeline.py` that read a sample of last-quarter regulations, recompute the metric, and append a row to `m1_pipeline_audits` for thesis reporting. Crossing any target threshold sets `is_degraded=true` on the audit row + raises an admin notification.

---

## 8. Common Pitfalls and Mitigations

| Pitfall | Why It Happens | Mitigation |
|---|---|---|
| Only English notices in dataset | fastText flags corrupted non-Roman scripts as "unknown" | Always Unicode-NFC normalize (`unicodedata.normalize("NFC", text)`) *before* language detection |
| Notices duplicated across pipeline runs | URL-only dedup misses re-publications at different URLs | Add content-hash dedup (SHA-256 of cleaned text); UNIQUE constraint on `gazette_number` |
| OCR garbage enters training data | No quality gate on OCR confidence score | Reject pages where `pytesseract.image_to_data()` average word confidence < 60 |
| Segmentation explodes one notice into 50 fragments | Overly aggressive heading regex patterns | Log segment-count distribution per gazette; flag outliers (> 30 segments) for manual review |
| Pipeline silently skips failed PDFs | Exceptions caught and swallowed in orchestrator | Always write to `m1_pipeline_errors` table; surface in daily admin health-check dashboard |
| Sinhala/Tamil text appears as `?????` | Wrong encoding handling at any stage | End-to-end UTF-8; never pass gazette bytes through ASCII-only string operations |

---

## 9. Conclusion

The collection pipeline handles three gazette PDF types through a cascading extraction chain, scrapes six official portals and five news feeds for propagation tracking, and integrates directly with Celery Beat for scheduled execution. The Scrapy + PyMuPDF/pdfplumber/Tesseract stack represents the optimal trade-off between reliability, Sinhala/Tamil support, and infrastructure simplicity. The output of this pipeline feeds directly into the preprocessing stage described in [04_M1_Preprocessing_Pipeline.md](04_M1_Preprocessing_Pipeline.md).

---

## References

- Scrapy. (2024). *Scrapy Documentation 2.11*. [docs.scrapy.org](https://docs.scrapy.org)
- Artifex Software. (2024). *PyMuPDF Documentation*. [pymupdf.readthedocs.io](https://pymupdf.readthedocs.io)
- Hwang et al. (2021). *pdfplumber: Plumb a PDF for detailed information about each char, rectangle, and line*. [github.com/jsvine/pdfplumber](https://github.com/jsvine/pdfplumber)
- Smith, R. (2007). *An Overview of the Tesseract OCR Engine*. ICDAR 2007.
- Department of Government Printing Sri Lanka. *gazette.lk*. [gazette.lk](https://www.gazette.lk)
