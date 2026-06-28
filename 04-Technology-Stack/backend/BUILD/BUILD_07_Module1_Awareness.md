# BUILD 07 — Module 1: Regulatory Awareness Pipeline

> **Goal:** wire up the full Module 1 pipeline — gazette scraper → PDF extractor → text segmenter → XLM-R classifier → multilingual summarizer → secondary-source watcher → lag computer → alert engine.
>
> **Scope:** **Inference + ingestion only.** The classifier *training* loop (data labeling, baseline + fine-tuning, evaluation harness, error analysis) lives in `BUILD_11_ML_Training_Pipeline.md`. Research deep-dive on training is in `research/11_Module1_NLP_Classifier_Training.md`.
>
> **Read first:** research files `09_Module1_Architecture_Overview.md`, `10_Module1_Gazette_PDF_Extraction_Pipeline.md`, `11_Module1_NLP_Classifier_Training.md`, `12_Module1_End_to_End_Workflow.md`. This BUILD file translates those into concrete code locations.

---

## 1. Component Map (Backend)

| Concern | Code path | Talks to |
|---------|-----------|----------|
| Scheduler | `app/ingestion/scheduler.py` | APScheduler (or Celery beat) |
| Gazette listing | `app/ingestion/gazette/lister.py` | documents.gov.lk |
| PDF download | `app/ingestion/gazette/downloader.py` | object storage |
| PDF extraction | `app/ingestion/gazette/extractor.py` | PyMuPDF / pdfplumber / Tesseract |
| Cleaning + segmentation | `app/ingestion/gazette/extractor.py` | regex utilities |
| Persist regulation | `app/services/module1/persistence.py` | `regulations` table |
| Classify | `app/services/module1/classifier.py` | `model_versions` (production XLM-R) |
| Summarize | `app/services/module1/summarizer.py` | local LLM or API |
| Secondary watcher | `app/ingestion/news_watcher.py`, `portal_watcher.py` | RSS, IRD/EPF/SLSI portals |
| Lag analysis | `app/services/module1/lag_analyzer.py` | SQL aggregations |
| Alert engine | `app/services/module1/alert_engine.py`, `app/services/notification_service.py` | `sme_alert_subscriptions`, email/SMS provider |

> **Watcher coverage in this file:** the **news watcher** is implemented inline below (§7).
> **Portal watchers** (IRD, EPF, ETF, SLSI, eROC, Customs) are detailed in `BUILD_12_Data_Ingestion_and_Scheduling.md` §4.
> **Social watchers** (FB groups, Twitter/X, Reddit) — see `BUILD_12` §5 and `BUILD_10_Module4_Misinformation.md` §5 (Module 4 is the primary owner of social ingest).

### Cross-module linkage

This file is the **ingest** half of M1 — it populates `m1_regulations`. The **survey** half ("M1 Awareness" / module 1 (`module_number=1`) — the `awareness.v1.qNN` questions plus per-regulation awareness questions) lives in `survey_questions` and is documented in [`../SETUP/11_Survey_System.md`](../SETUP/11_Survey_System.md) §3 (Contract **C1**) and §10. The link: an awareness question carries a `linked_regulation_id` (+ a `survey_question_regulations` junction row) pointing at an ingested `m1_regulations` row, plus `next_question_rules` routing the answer to the M2 knowledge follow-up. The seeded `VAT_SSCL_MERGE_2026` regulation + its `awareness.v1.q13 → VAT_SSCL_MERGE_FACT_001 → M3_VAT_SSCL_MERGE_*` chain (SETUP/11 §10.3) is the worked example of the data shape this pipeline should produce per SME-relevant regulation. Contract **C3** (M1 corpus → M2 RAG / M4 verification) is the join key for [`BUILD_08`](BUILD_08_Module2_Knowledge.md) §8 and [`BUILD_10`](BUILD_10_Module4_Misinformation.md).

---

## 2. Stage A — Scheduled Gazette Listing

```python
# FILE: backend/app/ingestion/gazette/lister.py
from datetime import date
from typing import Iterable, NamedTuple
import httpx
from bs4 import BeautifulSoup

class GazetteRef(NamedTuple):
    gazette_number: str
    gazette_date: date
    pdf_url: str

LISTING_URL = "https://documents.gov.lk/en/gazette.php"

async def list_recent_gazettes() -> Iterable[GazetteRef]:
    async with httpx.AsyncClient(timeout=20) as c:
        resp = await c.get(LISTING_URL)
    soup = BeautifulSoup(resp.text, "lxml")
    refs: list[GazetteRef] = []
    for row in soup.select("table.gazette-list tr"):     # adjust selector after inspection
        # parse number, date, link
        ...
    return refs
```

> See research file 10 §3 for the manual inspection workflow before you write the selector.

---

## 3. Stage B — PDF Extraction

```python
# FILE: backend/app/ingestion/gazette/extractor.py
from dataclasses import dataclass
from pathlib import Path
import fitz                 # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
import io

@dataclass
class ExtractedDoc:
    text: str
    method: str             # 'pymupdf'|'pdfplumber'|'ocr'
    confidence: float       # heuristic
    detected_language: str  # 'en'|'si'|'ta'|'mixed'

def extract(pdf_path: Path) -> ExtractedDoc:
    # 1. try PyMuPDF
    text = _pymupdf(pdf_path)
    if _looks_text(text):
        return ExtractedDoc(text, "pymupdf", 0.95, _detect_lang(text))
    # 2. try pdfplumber (better for tables)
    text = _pdfplumber(pdf_path)
    if _looks_text(text):
        return ExtractedDoc(text, "pdfplumber", 0.85, _detect_lang(text))
    # 3. fallback to OCR (Tesseract eng+sin+tam)
    text = _ocr(pdf_path)
    return ExtractedDoc(text, "ocr", 0.6, _detect_lang(text))

def _pymupdf(p): return "\n".join(page.get_text() for page in fitz.open(p))
def _pdfplumber(p):
    with pdfplumber.open(p) as d:
        return "\n".join(page.extract_text() or "" for page in d.pages)
def _ocr(p):
    out = []
    for page in fitz.open(p):
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        out.append(pytesseract.image_to_string(img, lang="eng+sin+tam"))
    return "\n".join(out)
def _looks_text(t: str) -> bool: return len(t.strip()) > 200 and t.count("\n") > 5
def _detect_lang(t: str) -> str:
    has_si = any("\u0d80" <= ch <= "\u0dff" for ch in t)
    has_ta = any("\u0b80" <= ch <= "\u0bff" for ch in t)
    has_la = any(ch.isascii() and ch.isalpha() for ch in t)
    flags = [("si", has_si), ("ta", has_ta), ("en", has_la)]
    on = [k for k,v in flags if v]
    return "mixed" if len(on) > 1 else (on[0] if on else "en")
```

### Cleaning + segmentation (per research file 10 §5)

Research file `10_Module1_Gazette_PDF_Extraction_Pipeline.md` §5 specifies **three segmentation strategies** in fallback order. The production default is the heading-based regex below; the other two are wired in when the regex returns < 2 segments on a > 4-page PDF.

| Strategy | When it fires | Implementation |
|----------|---------------|----------------|
| **A — Heading regex** (default) | All gazettes with NOTICE/Order/Regulation headings | `NOTICE_BOUNDARY_RE.split` (below) |
| **B — Block-gap heuristic** | Headingless gazettes (some Extraordinary issues) | Split on ≥2 consecutive blank lines AND ≥18px y-gap from PyMuPDF block coords |
| **C — LLM fallback** | Strategies A and B both yield < 2 segments | Few-shot prompt to a local Llama-3-8B-Instruct (or OpenAI cheap tier) returning JSON segments — never the default; logged + flagged for manual review |

```python
# FILE: backend/app/ingestion/gazette/segmenter.py
import re

NOTICE_BOUNDARY_RE = re.compile(r"^(?:NOTICE|Order|Regulation|නියෝගය|அறிவிப்பு)\b", re.MULTILINE)

def segment_into_notices(text: str) -> list[str]:
    """Strategy A — heading regex. See research file 10 §5 for B (block-gap) and C (LLM fallback)."""
    parts = NOTICE_BOUNDARY_RE.split(text)
    return [p.strip() for p in parts if len(p.strip()) > 100]

def is_regulatory(notice: str) -> bool:
    # rule-based filter: file 10 §7.3
    keywords = ("regulation", "notice", "amendment", "act", "rule", "deadline",
                "tax", "duty", "rate", "EPF", "ETF", "VAT", "SVAT")
    return any(k.lower() in notice.lower() for k in keywords)
```

---

## 4. Stage C — Persist + Dedup

```python
# FILE: backend/app/services/module1/persistence.py
import hashlib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.regulation import Regulation

def text_hash(t: str) -> str:
    return hashlib.sha256(t.strip().encode()).hexdigest()

async def upsert_regulation(db: AsyncSession, *,
    gazette_number, gazette_date, source_url, source_pdf_path, raw_text,
    cleaned_text, detected_language, extraction_method, extraction_confidence,
) -> Regulation | None:
    h = text_hash(cleaned_text or raw_text)
    existing = (await db.execute(
        select(Regulation).where(Regulation.text_hash == h)
    )).scalar_one_or_none()
    if existing:
        return None
    reg = Regulation(
        gazette_number=gazette_number, gazette_date=gazette_date,
        source_url=source_url, source_pdf_path=source_pdf_path,
        raw_text=raw_text, cleaned_text=cleaned_text,
        detected_language=detected_language, text_hash=h,
        extraction_method=extraction_method,
        extraction_confidence=extraction_confidence,
    )
    db.add(reg); await db.commit(); await db.refresh(reg)
    return reg
```

---

## 5. Stage D — Classifier (Inference)

> Training is in BUILD_11. Here we only *load* the production model and serve predictions.

```python
# FILE: backend/app/ml_serving/registry.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.model_version import ModelVersion
from app.exceptions import NotFoundError

async def get_production_model(db: AsyncSession, module_number: int) -> ModelVersion:
    mv = (await db.execute(
        select(ModelVersion)
        .where(ModelVersion.module_number == module_number,
               ModelVersion.is_production.is_(True))
        .order_by(ModelVersion.deployed_at.desc())
    )).scalar_one_or_none()
    if not mv:
        raise NotFoundError(f"No production model for module {module_number}")
    return mv
```

```python
# FILE: backend/app/services/module1/classifier.py
from functools import lru_cache
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

ID2LABEL = {  # must match ml/module1/train_xlmr.py
    0: "TAX_INCOME", 1: "TAX_VAT_SVAT", 2: "TAX_CUSTOMS_TARIFF",
    3: "EPF_ETF", 4: "IMPORT_EXPORT_CONTROL", 5: "HEALTH_SAFETY",
    6: "ENVIRONMENTAL", 7: "EMPLOYMENT_LABOUR", 8: "COMPANY_REGISTRATION",
    9: "SECTOR_SPECIFIC", 10: "CONSUMER_PROTECTION", 11: "OTHER_REGULATORY",
}

@lru_cache(maxsize=2)
def _load(artifact_path: str):
    tok = AutoTokenizer.from_pretrained(artifact_path)
    mdl = AutoModelForSequenceClassification.from_pretrained(artifact_path).eval()
    return tok, mdl

def classify(text: str, artifact_path: str) -> dict:
    tok, mdl = _load(artifact_path)
    enc = tok(text[:5000], truncation=True, max_length=512, return_tensors="pt")
    with torch.no_grad():
        logits = mdl(**enc).logits
    probs = torch.softmax(logits, dim=-1)[0].tolist()
    idx = int(max(range(len(probs)), key=probs.__getitem__))
    return {
        "category": ID2LABEL[idx],
        "confidence": probs[idx],
        "all_probs": {ID2LABEL[i]: p for i, p in enumerate(probs)},
    }
```

---

## 6. Stage E — Multilingual Summarizer

Two strategies; choose by Settings:

| Strategy | Quality | Cost | Use when |
|----------|---------|------|----------|
| Local NLLB-200 + extractive lead-3 | Acceptable | Free | Default research project |
| OpenAI/Anthropic prompt | High | ~$0.001/regulation | Final demo if budget allows |

```python
# FILE: backend/app/services/module1/summarizer.py
def summarize_extractive_then_translate(text: str) -> dict[str, str]:
    en = " ".join(text.split(". ")[:3]) + "."
    # local NLLB call (cached)
    si = nllb_translate(en, "sin_Sinh")
    ta = nllb_translate(en, "tam_Taml")
    return {"summary_en": en, "summary_si": si, "summary_ta": ta}
```

> NLLB integration boilerplate generated by Claude Prompt 4 below.

---

## 7. Stage F — Secondary Source Watchers

```python
# FILE: backend/app/ingestion/news_watcher.py
import feedparser, httpx
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.regulation import Regulation, RegulationSecondaryAppearance

NEWS_FEEDS = [
    "https://www.ft.lk/rss",
    "https://www.dailymirror.lk/rss/business",
    # add per file 12 §4
]

async def scan_news(db: AsyncSession):
    for url in NEWS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            text = (entry.title + " " + entry.get("summary", "")).lower()
            # keyword-match against open regulations
            recent = (await db.execute(
                select(Regulation).order_by(Regulation.gazette_date.desc()).limit(200)
            )).scalars().all()
            for reg in recent:
                if reg.title and reg.title.lower()[:40] in text:
                    db.add(RegulationSecondaryAppearance(
                        regulation_id=reg.regulation_id,
                        source_type="news",
                        source_url=entry.link,
                        first_seen_at=_parse_date(entry.published),
                        matching_method="keyword",
                        matching_confidence=0.7,
                    ))
        await db.commit()
```

For semantic matching (fewer false negatives) replace keyword check with a sentence-embedding similarity ≥ 0.7 — see file 12 §5.

---

## 8. Stage G — Lag Computation

```sql
-- FILE: backend/app/services/module1/sql/lag.sql
-- Per-stage lag for each regulation: gazette → portal → news → SME awareness
WITH portal_first AS (
  SELECT regulation_id, MIN(first_seen_at) AS portal_at
  FROM regulation_secondary_appearances
  WHERE source_type IN ('ird_portal','epf_portal','slsi_portal')
  GROUP BY 1
),
news_first AS (
  SELECT regulation_id, MIN(first_seen_at) AS news_at
  FROM regulation_secondary_appearances
  WHERE source_type = 'news'
  GROUP BY 1
)
SELECT
  r.regulation_id,
  r.gazette_date,
  EXTRACT(EPOCH FROM (p.portal_at - r.gazette_date::timestamptz))/86400 AS lag_gazette_to_portal_days,
  EXTRACT(EPOCH FROM (n.news_at  - p.portal_at))/86400 AS lag_portal_to_news_days,
  EXTRACT(EPOCH FROM (n.news_at  - r.gazette_date::timestamptz))/86400 AS lag_gazette_to_news_days,
  r.predicted_category
FROM regulations r
LEFT JOIN portal_first p USING (regulation_id)
LEFT JOIN news_first   n USING (regulation_id);
```

```python
# FILE: backend/app/services/module1/lag_analyzer.py
async def aggregate_lag_distribution(db) -> dict:
    """Returns per-category percentile distribution. Use for /admin/lag dashboard."""
    ...
```

---

## 9. Stage H — Alerts

```python
# FILE: backend/app/services/module1/alert_engine.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.regulation import Regulation
from app.models.alert import Alert
from app.services.notification_service import send

async def fan_out_alerts(db: AsyncSession, reg: Regulation):
    if not reg.predicted_category or (reg.classifier_confidence or 0) < 0.55:
        return  # uncertain → admin review queue
    # Match against sme_alert_subscriptions
    matches = await _matching_subscriptions(db, reg)
    for sub in matches:
        alert = Alert(sme_id=sub.sme_id, regulation_id=reg.regulation_id,
                      channel=sub.channel, status="queued")
        db.add(alert)
    await db.commit()
    for a in matches:
        await send(channel=a.channel, sme_id=a.sme_id, regulation=reg)
```

---

## 10. The Orchestration

```python
# FILE: backend/app/tasks/ingest_gazettes.py
from app.db.session import SessionLocal
from app.ingestion.gazette import lister, downloader, extractor
from app.ingestion.gazette.segmenter import segment_into_notices, is_regulatory
from app.services.module1 import persistence, classifier, summarizer, alert_engine
from app.ml_serving.registry import get_production_model
from app.storage import get_storage

async def run():
    storage = get_storage()
    async with SessionLocal() as db:
        mv = await get_production_model(db, module_number=1)
        for ref in await lister.list_recent_gazettes():
            pdf_bytes = await downloader.fetch(ref.pdf_url)
            key = f"gazettes/{ref.gazette_number}.pdf"; storage.put(key, pdf_bytes)
            doc = extractor.extract(storage.path(key))
            for notice in segment_into_notices(doc.text):
                if not is_regulatory(notice): continue
                reg = await persistence.upsert_regulation(
                    db, gazette_number=ref.gazette_number, gazette_date=ref.gazette_date,
                    source_url=ref.pdf_url, source_pdf_path=key,
                    raw_text=notice, cleaned_text=notice,
                    detected_language=doc.detected_language,
                    extraction_method=doc.method, extraction_confidence=doc.confidence,
                )
                if not reg: continue
                pred = classifier.classify(notice, mv.training_run.artifact_path)  # eager-loaded
                reg.predicted_category = pred["category"]
                reg.classifier_confidence = pred["confidence"]
                sums = summarizer.summarize_extractive_then_translate(notice)
                reg.summary_en = sums["summary_en"]; reg.summary_si = sums["summary_si"]; reg.summary_ta = sums["summary_ta"]
                await db.commit()
                await alert_engine.fan_out_alerts(db, reg)
```

Trigger via the scheduler:

```python
# FILE: backend/app/ingestion/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.tasks.ingest_gazettes import run as ingest_gazettes
from app.tasks.compute_lag import run as compute_lag
from app.tasks.send_alerts import flush as flush_alerts

def build_scheduler() -> AsyncIOScheduler:
    s = AsyncIOScheduler(timezone="Asia/Colombo")
    s.add_job(ingest_gazettes,   "cron", hour="*/2",    id="ingest_gazettes")
    s.add_job(flush_alerts,      "cron", minute="*/15", id="flush_alerts")
    s.add_job(compute_lag,       "cron", hour=2,        id="compute_lag")
    return s
```

Wire into `lifespan` in `main.py` (see BUILD_12 for full Celery alternative).

---

## 11. Frontend — Module 1 UI

| Page | Components | Behavior |
|------|------------|----------|
| `/regulations` | `RegulationList`, filters (category, date-range, agency) | Server component, calls `RegulationsApi.list` |
| `/regulations/[id]` | `RegulationDetail` w/ EN/SI/TA tabs, "First mention" timeline | Calls `RegulationsApi.get` |
| `/dashboard` | `RecentRegulations` (last 7 days for SME's sector) | Filters by SME profile |

```tsx
// FILE: frontend/components/module1/regulation-card.tsx
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import type { Regulation } from "@/lib/types";

const CATEGORY_BADGE: Record<string, string> = {
  TAX_VAT_SVAT: "bg-amber-100 text-amber-800",
  EPF_ETF: "bg-blue-100 text-blue-800",
  // ...
};

export function RegulationCard({ reg }: { reg: Regulation }) {
  return (
    <Link href={`/regulations/${reg.regulation_id}`} className="block rounded-md border p-4 hover:bg-muted">
      <div className="flex items-center justify-between">
        <span className="text-xs text-fg/60">{reg.gazette_date}</span>
        <Badge className={CATEGORY_BADGE[reg.predicted_category ?? ""]}>{reg.predicted_category}</Badge>
      </div>
      <h3 className="mt-1 font-medium">{reg.title ?? reg.gazette_number}</h3>
      <p className="mt-1 text-sm text-fg/70">{reg.summary_en?.slice(0, 200)}…</p>
    </Link>
  );
}
```

---

## 12. Acceptance Criteria

- [ ] `python -m app.tasks.ingest_gazettes` run once produces ≥ 1 row in `regulations`
- [ ] Each row has `predicted_category`, `classifier_confidence`, and three summaries
- [ ] Re-running the task does not create duplicates (verified by `text_hash`)
- [ ] News watcher inserts at least one `regulation_secondary_appearances` row
- [ ] `/api/v1/regulations` returns the rows; `/regulations/[id]` renders all three languages
- [ ] Lag SQL returns rows for at least 5 regulations
- [ ] An alert is created for at least one SME with a matching subscription
- [ ] OCR fallback path is exercised by at least one scanned PDF

---

## 13. Claude Prompts for This Section

### Prompt 1 — Gazette listing scraper

```
You're scraping documents.gov.lk to produce a list of GazetteRef
(gazette_number, gazette_date, pdf_url) for the last 30 days.
Step 1: Inspect the page structure (assume the table contains <a href> with gazette PDFs)
Step 2: Output a robust async httpx + BeautifulSoup implementation in
        backend/app/ingestion/gazette/lister.py with:
   - Retry up to 3x with exponential backoff (use tenacity)
   - Date parsing tolerant of multiple formats
   - Skip rows that look like Bills (not Acts/Gazettes)
   - 30-second timeout
Include a CLI: `python -m app.ingestion.gazette.lister --since 2026-01-01`.
```

### Prompt 2 — Robust PDF extractor

```
Extend backend/app/ingestion/gazette/extractor.py to:
- Try PyMuPDF first; if `_looks_text` fails, try pdfplumber
- If both fail, run Tesseract OCR with eng+sin+tam at 300 dpi
- Return ExtractedDoc with method and confidence
- Detect language by Unicode block presence (Sinhala 0D80–0DFF, Tamil 0B80–0BFF)
- Add unit tests using the three sample PDFs in `backend/app/tests/data/`:
  one text PDF, one scanned, one mixed-language.
```

### Prompt 3 — Inference endpoint with model registry

```
Wire up backend/app/api/v1/regulations.py with a POST /classify endpoint
(admin-only, used for retroactive classification) that:
- loads the production XLM-R artifact via app.ml_serving.registry
- accepts {"text": "..."} and returns {"category", "confidence", "all_probs"}
- caches the loaded model in-process (lru_cache by artifact_path)
- logs every prediction to a `model_predictions` table (auto-generate the model)
```

### Prompt 4 — Local multilingual summarizer

```
Add backend/app/services/module1/summarizer.py implementing:
- `summarize_extractive_then_translate(text) -> {summary_en, summary_si, summary_ta}`
- Lead-3 extraction in English (or extract from the original-language text first
  then translate using NLLB-200 via `transformers`)
- Use Hugging Face NLLB checkpoint `facebook/nllb-200-distilled-600M`
- Cache the model with lru_cache(maxsize=1)
- Strip phone numbers (regex) before storage (per misinformation module ethics)
- Provide a CLI for ad-hoc summarization
```

### Prompt 5 — Lag dashboard endpoint

```
Implement GET /api/v1/admin/lag/distribution returning JSON for the lag dashboard:
- For each category: median lag in days, p25, p75, p95, sample size
- For each diffusion stage: gazette→portal, portal→news, gazette→news
- Use the SQL from BUILD_07 §8 as a starting point and parameterize by date range.
Add a Recharts bar chart on /admin/lag in the frontend.
```

---

**Prev:** `BUILD_06_Auth_and_Users.md` &nbsp;·&nbsp; **Next:** `BUILD_08_Module2_Knowledge.md`
