# 10 — Module 1: Gazette PDF Extraction Pipeline

> Goal: take you from "Sri Lanka publishes a gazette PDF on a government website" all the way to "individual cleaned, language-tagged regulatory notices stored in PostgreSQL, ready for the classifier in file 11."

This is the **data layer** for Module 1. Without good extraction, no model — however sophisticated — will produce useful results. This stage is unglamorous but is where 60% of your research engineering effort will go. Plan accordingly.

---

## 1. What This Pipeline Must Produce

Input: a URL like `http://documents.gov.lk/files/gz/2025/3/2025-03-14(I-I)E.pdf`

Output: zero, one, or many rows in the `regulations` table where each row is a single regulatory notice (not the whole gazette) with:

- `source_url`, `gazette_no`, `publication_date`
- `raw_text` (cleaned), `language` (en/si/ta)
- `extraction_method` (text / ocr / hybrid)
- `extraction_confidence` (0.0–1.0)
- `page_range` (where in the PDF this notice was found)
- `extracted_at` timestamp

Plus the original PDF stored on disk (or S3-compatible object storage) for reproducibility.

---

## 2. The Seven Stages of Extraction

```
1. DISCOVER     →  find new gazette URLs not yet seen
2. DOWNLOAD     →  fetch PDF (with rate limiting, retries)
3. INSPECT      →  determine if PDF is text-based or scanned
4. EXTRACT      →  text via PyMuPDF, tables via pdfplumber, OCR if scanned
5. SEGMENT      →  split full gazette into individual notices/rules
6. CLEAN        →  normalize whitespace, fix encoding, detect language
7. STORE        →  write to PostgreSQL + filesystem
```

Each stage has its own failure modes and its own code module. Build them as separate, testable functions — not one monolithic script.

---

## 3. Stage 1 — Discover New Gazettes

The Department of Government Printing publishes weekly gazettes at `documents.gov.lk`. Older years are organized by year/month/issue.

### 3.1 The discovery strategy

Two complementary approaches — use **both**:

**A. Index-page crawling (Scrapy spider)**
- Crawl the year/month index pages
- Extract all PDF links matching the gazette URL pattern
- Compare against `regulations.source_url` already in DB
- Queue new ones for download

**B. RSS / known-URL polling (cron)**
- Some government portals expose RSS — subscribe where available
- Maintain a hand-curated list of related sources (CBSL circulars, IRD notices) — not all "regulatory information" arrives via the gazette

### 3.2 Sample Scrapy spider skeleton

```python
# scrapers/gazette_spider.py
import scrapy
from datetime import datetime

class GazetteSpider(scrapy.Spider):
    name = "gazette"
    allowed_domains = ["documents.gov.lk"]
    custom_settings = {
        "DOWNLOAD_DELAY": 2.0,        # be polite — 2 sec between requests
        "CONCURRENT_REQUESTS": 2,
        "USER_AGENT": "EnigmatrixResearchBot/0.1 (+contact: your-email@uom.lk)",
        "ROBOTSTXT_OBEY": True,
    }

    def start_requests(self):
        # iterate year/month index pages
        for year in range(2018, datetime.now().year + 1):
            for month in range(1, 13):
                url = f"http://documents.gov.lk/en/gazette.php?year={year}&month={month:02d}"
                yield scrapy.Request(url, callback=self.parse_index)

    def parse_index(self, response):
        for href in response.css("a::attr(href)").getall():
            if href and href.lower().endswith(".pdf") and "/gz/" in href.lower():
                full_url = response.urljoin(href)
                yield {
                    "source_url": full_url,
                    "discovered_at": datetime.utcnow().isoformat(),
                }
```

The spider produces a stream of URLs. Your pipeline writes them to a `gazettes_to_process` queue table (or a file-based queue), de-duped against what's already in the DB.

### 3.3 Ethics / legal note

Government gazettes are **public information** — there is no copyright concern in downloading them. But:
- Identify your bot honestly via User-Agent
- Respect `robots.txt`
- Use polite delays (≥ 1 sec)
- If a site blocks you, don't fight it — email the agency and ask

Document this in your research methodology section under "Data collection ethics."

---

## 4. Stage 2 — Download

```python
# pipeline/download.py
import requests, hashlib, os
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential

RAW_DIR = Path("/data/gazettes/raw")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2))
def download_gazette(url: str) -> Path:
    response = requests.get(url, timeout=60, stream=True,
                            headers={"User-Agent": "EnigmatrixResearchBot/0.1"})
    response.raise_for_status()

    # store as content-addressable: hash(url)/filename.pdf
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:12]
    filename = url.split("/")[-1]
    target = RAW_DIR / url_hash / filename
    target.parent.mkdir(parents=True, exist_ok=True)

    with open(target, "wb") as f:
        for chunk in response.iter_content(8192):
            f.write(chunk)
    return target
```

**Why content-addressable storage:** if the same gazette is published at two URLs (mirror sites), or re-published with a fix, the hash differs → you keep both versions. Crucial for reproducible research.

**What to capture in DB even before extraction:**
```sql
INSERT INTO gazette_downloads (source_url, local_path, file_size_bytes,
                                sha256, downloaded_at)
VALUES (...);
```

This gives you an audit trail showing exactly which PDF version produced which extracted notice.

---

## 5. Stage 3 — Inspect (text vs scanned)

Some gazettes (especially pre-2018 or those scanned from print) have **no extractable text** — they are images of paper. You must detect this before extraction, because the strategy diverges sharply.

```python
# pipeline/inspect.py
import fitz  # PyMuPDF

def classify_pdf(path) -> dict:
    doc = fitz.open(path)
    total_chars = 0
    total_images = 0
    for page in doc:
        total_chars += len(page.get_text("text"))
        total_images += len(page.get_images())
    doc.close()

    avg_chars_per_page = total_chars / len(doc) if len(doc) else 0
    if avg_chars_per_page > 200:
        return {"type": "text_pdf", "method": "pymupdf"}
    elif avg_chars_per_page > 30:
        return {"type": "hybrid", "method": "pymupdf+ocr"}
    else:
        return {"type": "scanned", "method": "ocr"}
```

A PDF averaging fewer than ~200 characters per page is almost certainly scanned.

---

## 6. Stage 4 — Extract

### 6.1 Text-based PDFs (PyMuPDF)

```python
# pipeline/extract_text.py
import fitz

def extract_text_pymupdf(path) -> list[dict]:
    """Returns list of {page_num, text, bbox_blocks} dicts."""
    doc = fitz.open(path)
    pages = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")
        # also capture block-level layout — useful for segmentation later
        blocks = page.get_text("blocks")
        pages.append({
            "page_num": page_num,
            "text": text,
            "blocks": blocks,
        })
    doc.close()
    return pages
```

PyMuPDF (`fitz`) is the workhorse: fast, handles most modern PDFs cleanly, preserves reading order, and gives you bounding boxes for every text block — essential for segmentation.

### 6.2 Tables (pdfplumber)

Some gazettes (especially tax schedules, Customs HS-code lists) embed **tables** that lose meaning when flattened to plain text. For those, use `pdfplumber`:

```python
# pipeline/extract_tables.py
import pdfplumber

def extract_tables(path) -> list[list[list[str]]]:
    """Returns list of tables; each table is list of rows; each row is list of cells."""
    tables_per_page = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tables_per_page.append(page.extract_tables() or [])
    return tables_per_page
```

Store extracted tables as JSON alongside the text. The classifier can use them; downstream summarization can reference them.

### 6.3 Scanned PDFs (Tesseract OCR)

For scanned or hybrid PDFs:

```python
# pipeline/extract_ocr.py
from pdf2image import convert_from_path
import pytesseract

# Tesseract languages (must be installed on system):
#   sin = Sinhala, tam = Tamil, eng = English
LANGS = "eng+sin+tam"

def ocr_pdf(path) -> list[dict]:
    images = convert_from_path(path, dpi=300)  # 300 DPI = good OCR accuracy
    pages = []
    for i, img in enumerate(images, start=1):
        # Use the multi-language pack — Tesseract auto-detects within pages
        text = pytesseract.image_to_string(img, lang=LANGS, config="--psm 3")
        pages.append({"page_num": i, "text": text, "method": "ocr"})
    return pages
```

**Critical OCR notes:**
- Install Tesseract trained data for Sinhala (`sin`) and Tamil (`tam`) — these are NOT default
- 300 DPI minimum; below that, accuracy collapses
- Expect 5–15% character error rate on Sinhala / Tamil — much higher than English
- Run a manual spot-check on a sample → quantify and report this in your research limitations
- For pre-2010 scans with degraded paper, consider adding image preprocessing (deskew, denoise) via OpenCV before OCR

### 6.4 The hybrid case

Some PDFs have an embedded text layer that's *partial* — e.g., the cover page is text but the body is scanned. Strategy:
1. Extract text via PyMuPDF
2. For pages where `len(text) < threshold`, render that page as image and OCR it
3. Merge results with `extraction_method` flagged per page

---

## 7. Stage 5 — Segment (Find Individual Notices)

A single gazette PDF may contain **dozens of unrelated notices**: tax amendments, appointment notifications, company name changes, public auction announcements, regulatory rules. You need to split these into individual records.

### 7.1 Why segmentation matters

If you train a classifier on whole-gazette text, it will be confused — most gazettes contain multiple categories simultaneously. Per-notice classification is much more accurate AND gives you the right granularity for alerts (an SME wants the *specific notice*, not "gazette #2421").

### 7.2 Segmentation strategies

Sri Lankan gazettes have semi-predictable structure — exploit it.

**Strategy A — Heading-based (regex + layout)**

```python
# pipeline/segment.py
import re

# Common section markers in Sri Lanka gazettes
SECTION_PATTERNS = [
    r"^PART\s+[IVX]+",                          # PART I, PART II
    r"^By Order of",                             # signature line ending notice
    r"^EXTRAORDINARY GAZETTE",
    r"^Notice under (the )?[A-Z]",
    r"^In terms of section \d+",
    r"^G\.E\.\s*\d+",                            # gazette extract number
    r"No\.\s*\d+\s*of\s*\d{4}",                 # Act No. X of YYYY
]

def segment_by_headings(full_text: str) -> list[str]:
    """Split full gazette text into sections based on heading markers."""
    pattern = "|".join(SECTION_PATTERNS)
    splits = re.split(f"({pattern})", full_text, flags=re.MULTILINE)
    # re.split with capture group preserves the delimiters; recombine
    sections = []
    current = ""
    for piece in splits:
        if piece is None: continue
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

**Strategy B — Block-distance heuristic (using PyMuPDF blocks)**

Gazette notices are typically separated by larger vertical whitespace than internal paragraphs. If you have block bounding boxes (from `page.get_text("blocks")`), you can detect notice boundaries by gaps:

```python
def segment_by_block_gaps(blocks_per_page, gap_threshold=30):
    """Split where vertical gap between blocks exceeds threshold."""
    notices = []
    current = []
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

**Strategy C — LLM-assisted segmentation (fallback for hard cases)**

For gazettes where regex/layout fails, send pages to a local LLM (or Claude / GPT for prototyping) with a prompt like:

> "Split the following gazette text into individual regulatory notices. Return a JSON array of objects with 'title' and 'body'. Do not summarize."

Use this only when needed — it's slow and expensive — but it's a useful escape hatch for a few percent of difficult cases.

### 7.3 What to keep, what to discard

After segmentation, run a **NOT_REGULATORY filter** before the main classifier:
- Personal name-change announcements → discard
- Lost-document notices → discard
- Public auction notices → discard
- Court summons → discard

Either a small regex/keyword filter or a binary classifier. This keeps your downstream taxonomy clean.

---

## 8. Stage 6 — Clean and Detect Language

Raw extracted text is messy. Clean it before storage.

### 8.1 Text cleaning

```python
# pipeline/clean.py
import re
import unicodedata

def clean_text(text: str) -> str:
    # Normalize Unicode (important for Sinhala/Tamil — combining characters)
    text = unicodedata.normalize("NFC", text)
    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove form-feed, soft-hyphens, zero-width chars
    text = text.replace("\x0c", "").replace("\xad", "").replace("\u200b", "")
    # Strip page-header/footer artifacts (often "Gazette of the Democratic ..." repeated)
    return text.strip()
```

### 8.2 Language detection

```python
# pipeline/lang.py
import fasttext

# Pretrained model — download once: lid.176.bin from fastText
LID_MODEL = fasttext.load_model("/data/models/lid.176.bin")

def detect_language(text: str) -> tuple[str, float]:
    sample = text[:1000].replace("\n", " ")
    labels, probs = LID_MODEL.predict(sample, k=1)
    lang = labels[0].replace("__label__", "")
    # fastText returns ISO codes like 'en', 'si', 'ta'
    return lang, float(probs[0])
```

Why fastText `lid.176`: trained on 176 languages, handles Sinhala (`si`) and Tamil (`ta`) — most simpler libraries don't.

If a single notice contains multiple languages (common — a Sinhala notice may quote English Act titles), classify by the **majority language of the body**, but also store a `contains_languages` array.

---

## 9. Stage 7 — Store

```python
# pipeline/store.py
from sqlalchemy import insert
# (assumes you have a Regulation model — see schema in file 06)

def store_notice(notice: dict, conn):
    conn.execute(insert(Regulation).values(
        source_url=notice["source_url"],
        gazette_no=notice["gazette_no"],
        publication_date=notice["publication_date"],
        title=notice["title"],
        raw_text=notice["clean_text"],
        language=notice["language"],
        extraction_method=notice["extraction_method"],
        extraction_confidence=notice["confidence"],
        page_range=notice["page_range"],
        ingested_at=datetime.utcnow(),
        # classification columns initially NULL — to be filled by classifier
        category=None,
        category_confidence=None,
        labeled_for_training=False,
    ))
```

Each notice is one row in `regulations`. The classifier (file 11) populates `category`, `category_confidence`. Subsequent stages (file 12) populate `summary_*` and feed alerts.

---

## 10. Putting It All Together — The Orchestrator

Wire the stages with a job queue. Don't run them inline — failures must be retryable.

```python
# pipeline/run.py — uses Celery, RQ, or APScheduler
from celery import Celery

app = Celery("enigmatrix", broker="redis://localhost:6379/0")

@app.task(bind=True, max_retries=3)
def process_gazette(self, source_url: str):
    try:
        local_path = download_gazette(source_url)
        info = classify_pdf(local_path)

        if info["type"] == "scanned":
            pages = ocr_pdf(local_path)
        elif info["type"] == "hybrid":
            pages = extract_hybrid(local_path)
        else:
            pages = extract_text_pymupdf(local_path)

        full_text = "\n\n".join(p["text"] for p in pages)
        sections = segment_by_headings(full_text)

        for sec in sections:
            cleaned = clean_text(sec)
            lang, lang_conf = detect_language(cleaned)
            store_notice({
                "source_url": source_url,
                "clean_text": cleaned,
                "language": lang,
                "extraction_method": info["method"],
                "confidence": min(lang_conf, 0.95),
                # ... other fields
            }, conn)
    except Exception as e:
        raise self.retry(exc=e, countdown=60)
```

---

## 11. Validation — How You Know This Pipeline Works

Don't take the output on faith. Build these validation checkpoints:

| Checkpoint | What you measure | Target |
|------------|-----------------|--------|
| Discovery completeness | Compare 100 manually-found gazettes against scraper output | ≥ 98% recall |
| Download integrity | SHA-256 mismatches, partial downloads | 0% corruption |
| Text-vs-scanned classification | Hand-label 50 PDFs, compare to classifier | ≥ 95% correct |
| Extraction accuracy (text PDFs) | Diff extracted text vs manually copy-pasted on 20 pages | ≥ 99% character match |
| OCR accuracy (scanned PDFs) | Hand-transcribe 5 pages, compute CER | ≤ 10% CER acceptable |
| Segmentation precision/recall | Hand-segment 10 gazettes; compare boundaries | ≥ 85% F1 on boundaries |
| Language detection | Hand-label 100 sections | ≥ 95% accuracy |

**Report all these numbers in your thesis.** They constitute "data-pipeline reliability" evidence and are exactly what a viva panel will probe.

---

## 12. Common Pitfalls and How to Avoid Them

| Pitfall | Why it happens | Mitigation |
|---------|---------------|------------|
| Only English notices in your dataset | fastText flags non-Roman scripts as "unknown" if charset is corrupted | Always Unicode-NFC normalize *before* language detection |
| Notices duplicated across runs | URL-only dedup misses re-publications at different URLs | Add content-hash dedup (SHA-256 of cleaned text) |
| OCR garbage gets into training data | No quality gate on OCR confidence | Reject pages with `pytesseract.image_to_data()` confidence < 60 |
| Segmentation explodes one notice into 50 fragments | Aggressive heading patterns | Always log and review segment count distribution; investigate outliers |
| Pipeline silently skips PDFs | Exceptions caught and swallowed | Always log to `pipeline_errors` table; have a Streamlit/dashboard view |
| Sinhala/Tamil text appears as `?????` | Wrong encoding handling at any stage | End-to-end UTF-8; never use ASCII-only string ops |

---

## 13. What You Need to Install

```bash
# System
sudo apt install tesseract-ocr tesseract-ocr-sin tesseract-ocr-tam poppler-utils

# Python
pip install pymupdf pdfplumber pdf2image pytesseract scrapy fasttext \
            sqlalchemy psycopg2-binary celery redis tenacity requests
```

Pin versions in `requirements.txt`. Document them in your thesis "Implementation environment" section — reproducibility matters.

---

## 14. Output of This Pipeline (What Feeds File 11)

After this pipeline runs, you have a populated `regulations` table where each row is a single, cleaned, language-tagged regulatory notice with provenance metadata — but **no category yet**. The next file (11) covers how to label these notices, train a classifier, and assign categories.

---

## Summary

The PDF extraction pipeline is the foundation. Seven stages: Discover → Download → Inspect → Extract → Segment → Clean → Store. Use PyMuPDF for text PDFs, Tesseract (with Sinhala/Tamil packs) for scans, regex+layout for segmentation, fastText for language ID. Validate every stage with measurable accuracy targets. Build modularly with a job queue so failures are retryable. Expect this stage to consume the majority of your engineering time — and to be the most viva-defensible part of your work, because it produces a reusable, novel dataset for Sri Lankan regulatory NLP.
