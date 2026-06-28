# BUILD 10 — Module 4: Misinformation Detection & Verification

> **Goal:** Build the end-to-end pipeline that ingests regulatory posts from public social media, cleans and translates them, classifies veracity on a nine-way scale, verifies claims against the Module 1 regulation corpus via RAG, and exposes a public claim-check tool. This module turns Enigmatrix from a one-way information system into a feedback loop that detects and corrects regulatory misinformation in the SME ecosystem.

> **Read first:** `research/04_Technology_Stack_Justification.md`, `research/05_Literature_Review_Guide.md`, `research/06_Data_Collection_and_Management.md`, `research/15_Module4_Misinformation_Architecture.md`, `research/module_1_and_4_data_architecture.md`, `BUILD_07_Module1_Awareness.md`, `BUILD_11_ML_Training_Pipeline.md`, `BUILD_12_Data_Ingestion_and_Scheduling.md`.

> **Scope:** This file covers the runtime pieces — per-platform ingest connectors, cleaning and translation, PII scrubbing, the Label Studio annotation loop, classifier *serving*, the RAG verifier, spread tracking, and the public claim-check API and UI. Classifier **training** lives in `BUILD_11` (HF Trainer + W&B + MLflow registry). The Celery beat schedules that drive the connectors live in `BUILD_12`. The RAG verifier reuses the existing ChromaDB collection `regulations_chunks_v1` built in `BUILD_08` — no parallel index is created.

---

## 1. Component map

```
backend/app/modules/m4/
├── models.py                   # SQLAlchemy 2.0 ORM for the six m4_* tables
├── language.py                 # fastText lid.176 + NLLB-200 + Google fallback
├── pii.py                      # NIC / phone / email scrubbers
├── classify.py                 # XLM-R inference, MLflow registry loader
├── verify.py                   # Claim extraction → RAG → NLI verifier
├── spread.py                   # Reach / virality / cross-platform graph
└── sources/
    ├── base.py                 # SourceConnector ABC + content_hash dedup
    ├── twitter.py              # tweepy v2 Academic API (canonical template)
    ├── facebook.py             # Graph API, public pages/groups only
    ├── reddit.py               # PRAW, sri_lanka + sl_business subs
    ├── youtube.py              # YouTube Data API v3, comments + descriptions
    ├── factcheck_lk.py         # FactCheck.lk pre-labeled scrape
    ├── tiktok_manual.py        # CSV import for manually collected TikTok URLs
    └── whatsapp_voluntary.py   # Survey-form upload ingester (BUILD_05 hook)

backend/app/api/v1/m4.py        # /verify/claim, /m4/misinformation-stats, admin ingest
backend/app/integrations/label_studio.py   # webhook + import / export

frontend/app/verify/page.tsx    # Public claim-check form, EN / SI / TA
frontend/components/m4/VerdictCard.tsx
```

Targets locked in the proposal: **≥ 500** consensus-labeled posts, Cohen's κ **≥ 0.70** inter-annotator agreement, classifier **macro-F1 ≥ 0.75** with accuracy **≥ 0.80**, and a statistically significant (**p < 0.05**) difference in virality between true and false posts.

---

## 2. Schema

The six tables below are owned by Module 4 and are kept in the `m4` Postgres schema. The DDL matches `module_1_and_4_data_architecture.md`. JSONB is used for `mechanics_flags` and `linguistic_features` so that we can add new flags without a migration.

```python
# FILE: backend/app/modules/m4/models.py
from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Integer, Float, Boolean, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB, ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

VERACITY = PgEnum(
    "true", "mostly_true", "partially_true", "misleading",
    "mostly_false", "false", "unverifiable", "opinion", "outdated",
    name="m4_veracity", create_type=True,
)

PLATFORM = PgEnum(
    "facebook", "twitter", "reddit", "youtube", "tiktok",
    "whatsapp", "factcheck_lk",
    name="m4_platform", create_type=True,
)


class M4RawPost(Base):
    __tablename__ = "m4_raw_posts"
    __table_args__ = (
        UniqueConstraint("platform", "platform_post_id", name="uq_raw_platform_postid"),
        Index("ix_raw_posted_at", "posted_at"),
        Index("ix_raw_content_hash", "content_hash"),
        {"schema": "m4"},
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(PLATFORM, nullable=False)
    platform_post_id: Mapped[str] = mapped_column(String(128), nullable=False)
    author_handle: Mapped[Optional[str]] = mapped_column(String(128))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    reach: Mapped[int] = mapped_column(Integer, default=0)
    engagement: Mapped[int] = mapped_column(Integer, default=0)


class M4CleanedPost(Base):
    __tablename__ = "m4_cleaned_posts"
    __table_args__ = {"schema": "m4"}
    id: Mapped[int] = mapped_column(primary_key=True)
    raw_post_id: Mapped[int] = mapped_column(ForeignKey("m4.m4_raw_posts.id", ondelete="CASCADE"), unique=True)
    text_original: Mapped[str] = mapped_column(Text)
    text_english: Mapped[str] = mapped_column(Text)
    detected_language: Mapped[str] = mapped_column(String(8))
    lang_confidence: Mapped[float] = mapped_column(Float)
    translation_engine: Mapped[str] = mapped_column(String(32))   # nllb-200 | google
    pii_redactions: Mapped[int] = mapped_column(Integer, default=0)
    cleaned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class M4LabeledPost(Base):
    __tablename__ = "m4_labeled_posts"
    __table_args__ = (
        Index("ix_labeled_consensus", "is_consensus_label"),
        Index("ix_labeled_veracity", "veracity"),
        {"schema": "m4"},
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    cleaned_post_id: Mapped[int] = mapped_column(ForeignKey("m4.m4_cleaned_posts.id", ondelete="CASCADE"))
    annotator_id: Mapped[str] = mapped_column(String(64))
    veracity: Mapped[str] = mapped_column(VERACITY, nullable=False)
    mechanics_flags: Mapped[dict] = mapped_column(JSONB, default=dict)   # wrong_numbers, fake_authority, ...
    rationale: Mapped[Optional[str]] = mapped_column(Text)
    is_consensus_label: Mapped[bool] = mapped_column(Boolean, default=False)
    labeled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class M4SpreadEvent(Base):
    __tablename__ = "m4_spread_events"
    __table_args__ = {"schema": "m4"}
    id: Mapped[int] = mapped_column(primary_key=True)
    raw_post_id: Mapped[int] = mapped_column(ForeignKey("m4.m4_raw_posts.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(32))   # share, retweet, quote, reply
    actor_handle: Mapped[Optional[str]] = mapped_column(String(128))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    parent_post_platform_id: Mapped[Optional[str]] = mapped_column(String(128))


class M4LinguisticFeatures(Base):
    __tablename__ = "m4_linguistic_features"
    __table_args__ = {"schema": "m4"}
    cleaned_post_id: Mapped[int] = mapped_column(ForeignKey("m4.m4_cleaned_posts.id"), primary_key=True)
    features: Mapped[dict] = mapped_column(JSONB, default=dict)
    # readability, sentiment, urgency_score, exclamations, all_caps_ratio, ...


class M4ClaimVerification(Base):
    __tablename__ = "m4_claim_verifications"
    __table_args__ = {"schema": "m4"}
    id: Mapped[int] = mapped_column(primary_key=True)
    cleaned_post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("m4.m4_cleaned_posts.id"), nullable=True)
    claim_text: Mapped[str] = mapped_column(Text)
    verdict: Mapped[str] = mapped_column(VERACITY)
    nli_label: Mapped[str] = mapped_column(String(16))   # entailment | contradiction | neutral
    confidence: Mapped[float] = mapped_column(Float)
    supporting_regulations: Mapped[list] = mapped_column(JSONB, default=list)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
```

The Alembic migration is generated with `alembic revision --autogenerate -m "m4 schema"` and reviewed manually before commit.

---

## 3. Ingest connectors

Each connector inherits from a small ABC that handles deduplication via `content_hash` (SHA-256 of normalised text), pacing, and a structured `IngestRecord` output that the writer persists into `m4_raw_posts`. Connectors are pure async functions; the schedules that call them on a cadence are defined in `BUILD_12`.

```python
# FILE: backend/app/modules/m4/sources/base.py
from __future__ import annotations
import hashlib, re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator, Optional


@dataclass(slots=True)
class IngestRecord:
    platform: str
    platform_post_id: str
    author_handle: Optional[str]
    raw_text: str
    raw_payload: dict
    posted_at: datetime
    reach: int = 0
    engagement: int = 0
    content_hash: str = field(init=False)

    def __post_init__(self) -> None:
        norm = re.sub(r"\s+", " ", self.raw_text).strip().lower()
        self.content_hash = hashlib.sha256(norm.encode("utf-8")).hexdigest()


class SourceConnector(ABC):
    platform: str

    @abstractmethod
    async def fetch(self, since: datetime) -> AsyncIterator[IngestRecord]:
        ...
```

### 3.1 Twitter / X — canonical template

We use the Academic Research API v2 via `tweepy`. The query is the union of regulatory keywords (English / Sinhala / Tamil) plus a small set of authoritative handles. Cursor pagination is mandatory — the `next_token` is persisted in `m4_ingest_state` so re-runs resume cleanly. The Academic API permits research crawls of public tweets; we **do not** scrape protected accounts.

```python
# FILE: backend/app/modules/m4/sources/twitter.py
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator
import tweepy
from app.core.config import settings
from app.modules.m4.sources.base import SourceConnector, IngestRecord

KEYWORDS_TRI = (
    '("EPF" OR "ETF" OR "VAT" OR "BOI" OR "IRD" OR "Inland Revenue" '
    'OR "රෙගුලාසි" OR "බදු" OR "ஒழுங்குமுறை" OR "வரி") lang:en OR lang:si OR lang:ta'
)


class TwitterConnector(SourceConnector):
    """Public-only crawl via Twitter/X Academic API. Respects developer ToS;
    no protected tweets, no private DMs, no automation against rate limits."""
    platform = "twitter"

    def __init__(self) -> None:
        self.client = tweepy.Client(bearer_token=settings.TWITTER_BEARER, wait_on_rate_limit=True)

    async def fetch(self, since: datetime) -> AsyncIterator[IngestRecord]:
        next_token: str | None = None
        while True:
            resp = await asyncio.to_thread(
                self.client.search_all_tweets,
                query=KEYWORDS_TRI,
                start_time=since,
                max_results=500,
                next_token=next_token,
                tweet_fields=["created_at", "public_metrics", "lang", "author_id"],
                expansions=["author_id"],
            )
            if not resp.data:
                return
            users = {u.id: u for u in (resp.includes or {}).get("users", [])}
            for t in resp.data:
                m = t.public_metrics or {}
                yield IngestRecord(
                    platform=self.platform,
                    platform_post_id=str(t.id),
                    author_handle=getattr(users.get(t.author_id), "username", None),
                    raw_text=t.text,
                    raw_payload={"lang": t.lang, "metrics": m},
                    posted_at=t.created_at or datetime.now(timezone.utc),
                    reach=m.get("impression_count", 0),
                    engagement=m.get("like_count", 0) + m.get("retweet_count", 0),
                )
            next_token = (resp.meta or {}).get("next_token")
            if not next_token:
                return
```

### 3.2 Facebook — Graph API, public pages and groups only

```python
# FILE: backend/app/modules/m4/sources/facebook.py
# ToS: Graph API v18 with a Page-scoped access token. We crawl only public
# Pages and explicitly *public* Groups whose admins have allowed app access.
# Private groups are off-limits and never touched.
import httpx, asyncio
from datetime import datetime
from app.core.config import settings
from app.modules.m4.sources.base import SourceConnector, IngestRecord

GRAPH = "https://graph.facebook.com/v18.0"

class FacebookConnector(SourceConnector):
    platform = "facebook"
    PAGE_IDS = ("BOISriLanka", "IRDSriLanka", "EPFSriLanka")

    async def fetch(self, since):
        async with httpx.AsyncClient(timeout=30) as c:
            for pid in self.PAGE_IDS:
                url = f"{GRAPH}/{pid}/posts"
                params = {"access_token": settings.FB_TOKEN, "since": int(since.timestamp()),
                          "fields": "id,message,created_time,reactions.summary(total_count),shares"}
                while url:
                    r = (await c.get(url, params=params)).json()
                    for p in r.get("data", []):
                        if not p.get("message"):
                            continue
                        yield IngestRecord(
                            platform=self.platform, platform_post_id=p["id"],
                            author_handle=pid, raw_text=p["message"], raw_payload=p,
                            posted_at=datetime.fromisoformat(p["created_time"].replace("Z", "+00:00")),
                            reach=(p.get("shares") or {}).get("count", 0),
                            engagement=(p.get("reactions") or {}).get("summary", {}).get("total_count", 0),
                        )
                    url = (r.get("paging") or {}).get("next"); params = None
```

### 3.3 Reddit — PRAW

```python
# FILE: backend/app/modules/m4/sources/reddit.py
# ToS: PRAW with a registered script app, read-only, complies with Reddit
# Data API rate limits and the "no aggressive scraping" clause.
import asyncio, praw
from datetime import datetime, timezone
from app.core.config import settings
from app.modules.m4.sources.base import SourceConnector, IngestRecord

class RedditConnector(SourceConnector):
    platform = "reddit"
    SUBS = ("srilanka", "lka", "sl_business")

    def __init__(self) -> None:
        self.r = praw.Reddit(client_id=settings.REDDIT_ID, client_secret=settings.REDDIT_SECRET,
                             user_agent="enigmatrix-research/0.1 by u/uom_research")

    async def fetch(self, since):
        for sub in self.SUBS:
            for s in await asyncio.to_thread(lambda: list(self.r.subreddit(sub).new(limit=200))):
                if datetime.fromtimestamp(s.created_utc, tz=timezone.utc) < since:
                    continue
                yield IngestRecord(
                    platform=self.platform, platform_post_id=s.id,
                    author_handle=str(s.author) if s.author else None,
                    raw_text=f"{s.title}\n\n{s.selftext or ''}", raw_payload={"sub": sub, "url": s.url},
                    posted_at=datetime.fromtimestamp(s.created_utc, tz=timezone.utc),
                    reach=s.num_comments * 10, engagement=s.score,
                )
```

### 3.4 YouTube, FactCheck.lk, TikTok, WhatsApp

- **YouTube** (`youtube.py`) — YouTube Data API v3, comments and descriptions of videos from authoritative regulator channels and the top-50 results for the keyword set. ToS: standard API quota, no Innertube reverse-engineering.
- **FactCheck.lk** (`factcheck_lk.py`) — Polite HTML scrape (1 req/sec, `robots.txt` honoured). Each fact-check article is imported with its **pre-labeled verdict**, which seeds `m4_labeled_posts` with `is_consensus_label = TRUE` and `annotator_id = "factcheck_lk"`.
- **TikTok** (`tiktok_manual.py`) — TikTok has no research API tier we can rely on; we ingest via a CSV that research assistants populate by hand from public videos. The connector simply parses the CSV.
- **WhatsApp** (`whatsapp_voluntary.py`) — **Voluntary forwards only.** SMEs upload screenshots or copy-pasted forwards through the survey form built in `BUILD_05`. We **never** scrape WhatsApp groups, never use unofficial WA Web tooling, and never store phone numbers. The ingester reads survey rows where `consent_misinfo_research = TRUE`.

---

## 4. Language pipeline

```python
# FILE: backend/app/modules/m4/language.py
from __future__ import annotations
import fasttext, httpx
from functools import lru_cache
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
from app.core.config import settings

LID_PATH = "models/lid.176.bin"
NLLB_NAME = "facebook/nllb-200-distilled-600M"
NLLB_TGT = "eng_Latn"
LANG_MAP = {"si": "sin_Sinh", "ta": "tam_Taml", "en": "eng_Latn"}


@lru_cache(maxsize=1)
def _lid():
    return fasttext.load_model(LID_PATH)


@lru_cache(maxsize=1)
def _nllb():
    tok = AutoTokenizer.from_pretrained(NLLB_NAME)
    mdl = AutoModelForSeq2SeqLM.from_pretrained(NLLB_NAME).eval()
    return tok, mdl


def detect(text: str) -> tuple[str, float]:
    labels, probs = _lid().predict(text.replace("\n", " ")[:2000], k=1)
    return labels[0].replace("__label__", ""), float(probs[0])


def translate_to_en(text: str, src: str) -> tuple[str, str]:
    """Return (english_text, engine_used). Falls back to Google when NLLB
    confidence is below 0.6 or src is outside NLLB's distilled vocabulary."""
    if src == "en":
        return text, "passthrough"
    tok, mdl = _nllb()
    src_code = LANG_MAP.get(src)
    if src_code is None:
        return _google(text), "google"
    tok.src_lang = src_code
    enc = tok(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        out = mdl.generate(**enc, forced_bos_token_id=tok.convert_tokens_to_ids(NLLB_TGT),
                           max_new_tokens=512, num_beams=4, return_dict_in_generate=True,
                           output_scores=True)
    text_en = tok.batch_decode(out.sequences, skip_special_tokens=True)[0]
    score = float(torch.softmax(out.scores[0], dim=-1).max())
    if score < 0.6:
        return _google(text), "google"
    return text_en, "nllb-200"


def _google(text: str) -> str:
    r = httpx.post("https://translation.googleapis.com/language/translate/v2",
                   params={"key": settings.GTRANSLATE_KEY},
                   json={"q": text, "target": "en", "format": "text"}, timeout=20)
    r.raise_for_status()
    return r.json()["data"]["translations"][0]["translatedText"]
```

A small `m4_translation_cache` table (key = SHA-256 of source text + src lang) avoids paying NLLB or Google twice for the same string.

---

## 5. PII scrubbing

Every cleaned post is stripped of personal data before persistence. The Sri Lankan NIC has two formats — the legacy 9-digit + V/X form and the post-2016 12-digit form.

```python
# FILE: backend/app/modules/m4/pii.py
import re
from dataclasses import dataclass

NIC_OLD = re.compile(r"\b\d{9}[VvXx]\b")
NIC_NEW = re.compile(r"\b(?:19|20)\d{10}\b")
PHONE   = re.compile(r"\b(?:\+?94|0)\d{9}\b")
EMAIL   = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")


@dataclass(slots=True)
class Scrub:
    text: str
    redactions: int


def scrub(text: str) -> Scrub:
    n = 0
    def sub(p, repl, s):
        nonlocal n
        new, k = p.subn(repl, s); n += k; return new
    out = sub(NIC_OLD, "[NIC]", text)
    out = sub(NIC_NEW, "[NIC]", out)
    out = sub(PHONE,   "[PHONE]", out)
    out = sub(EMAIL,   "[EMAIL]", out)
    return Scrub(out, n)
```

`scrub` is called from the cleaning task before `m4_cleaned_posts` is written. A unit test in `tests/m4/test_pii.py` runs synthetic NICs (`123456789V`, `199512345678`), Sri Lankan phone numbers (`0771234567`, `+94771234567`), and emails through it and asserts that none of the originals survive in the output.

---

## 6. Annotation with Label Studio

Annotation is the bottleneck for veracity classification, so the protocol is enforced in the Label Studio config itself: every post is shown to **two** annotators, the nine-way veracity radio is mandatory, and the five misleading-mechanics checkboxes are independent.

```xml
<!-- FILE: ops/label_studio/m4_veracity.xml -->
<View>
  <Text name="post" value="$text_english"/>
  <Text name="orig" value="$text_original" granularity="paragraph"/>
  <Header value="Veracity (choose one)"/>
  <Choices name="veracity" toName="post" choice="single" required="true">
    <Choice value="true"/><Choice value="mostly_true"/><Choice value="partially_true"/>
    <Choice value="misleading"/><Choice value="mostly_false"/><Choice value="false"/>
    <Choice value="unverifiable"/><Choice value="opinion"/><Choice value="outdated"/>
  </Choices>
  <Header value="Misleading mechanics (any that apply)"/>
  <Choices name="mechanics" toName="post" choice="multiple">
    <Choice value="wrong_numbers"/><Choice value="wrong_dates"/>
    <Choice value="fake_authority"/><Choice value="fear_appeal"/>
    <Choice value="urgency_appeal"/>
  </Choices>
  <TextArea name="rationale" toName="post" placeholder="One-line rationale" maxSubmissions="1"/>
</View>
```

```python
# FILE: backend/app/integrations/label_studio.py
# Webhook receives ANNOTATION_CREATED events. When two annotators have
# submitted for the same cleaned_post_id, we compute pairwise agreement.
# A post is promoted to is_consensus_label = TRUE only if both annotators
# chose the SAME veracity label. Disagreements go to a third adjudicator.
# A nightly job recomputes the cohort-level Cohen's kappa; we ship only
# when kappa >= 0.70 for the labelled sample.
from fastapi import APIRouter, Request
from app.modules.m4 import models
router = APIRouter()

@router.post("/webhooks/label-studio")
async def ls_webhook(req: Request, db = ...):
    payload = await req.json()
    if payload.get("action") != "ANNOTATION_CREATED":
        return {"ok": True}
    ann = payload["annotation"]; task = payload["task"]
    veracity = _pick(ann, "veracity")
    mechs = {m: True for m in _pick_multi(ann, "mechanics")}
    db.add(models.M4LabeledPost(cleaned_post_id=task["data"]["cleaned_post_id"],
        annotator_id=ann["completed_by"]["email"], veracity=veracity,
        mechanics_flags=mechs, rationale=_pick(ann, "rationale")))
    await db.commit()
    await _maybe_promote_consensus(db, task["data"]["cleaned_post_id"])
    return {"ok": True}
```

A separate script `scripts/m4/kappa_report.py` (cross-ref `BUILD_13_DataOps`) computes Cohen's κ across all (annotator-A, annotator-B) pairs and emits a markdown report. **The `is_consensus_label = TRUE` flag is only retained when the rolling cohort κ ≥ 0.70**; below that the labels are quarantined and re-trained against the protocol.

---

## 7. Classifier inference

Training is owned by `BUILD_11_ML_Training_Pipeline.md`, which fine-tunes `xlm-roberta-base` on the consensus-labeled subset and registers the artifact in MLflow as `m4-veracity`. This module only *serves* the model.

```python
# FILE: backend/app/modules/m4/classify.py
from __future__ import annotations
from functools import lru_cache
import mlflow, torch
from transformers import AutoTokenizer

LABELS = ["true","mostly_true","partially_true","misleading","mostly_false",
          "false","unverifiable","opinion","outdated"]


@lru_cache(maxsize=1)
def _bundle():
    model = mlflow.pytorch.load_model("models:/m4-veracity/Production").eval()
    tok = AutoTokenizer.from_pretrained("xlm-roberta-base")
    return model, tok


def classify(text_en: str) -> dict:
    model, tok = _bundle()
    enc = tok(text_en, return_tensors="pt", truncation=True, max_length=256)
    with torch.no_grad():
        logits = model(**enc).logits[0]
    probs = torch.softmax(logits, dim=-1).tolist()
    idx = int(torch.argmax(logits))
    return {"label": LABELS[idx], "confidence": probs[idx],
            "all_probs": dict(zip(LABELS, probs))}
```

`classify()` is an in-process call. The LRU cache keeps the model resident; the worker process is sized for one model instance per pod (about 1.4 GB resident).

---

## 8. RAG verifier

The verifier turns a free-text claim (or the cleaned text of a post) into a verdict that is grounded in actual regulations. It **reuses the existing ChromaDB collection `regulations_chunks_v1`** built in `BUILD_07` / `BUILD_08`. We do **not** create a parallel index — the same retrieval surface used by the chat assistant is used here, so the citations are guaranteed to be the same documents end users see in Module 2.

The pipeline is: claim extraction → top-5 retrieval from `regulations_chunks_v1` → per-evidence NLI scoring with `joeddav/xlm-roberta-large-xnli` → verdict aggregation.

```python
# FILE: backend/app/modules/m4/verify.py
from __future__ import annotations
import re, torch
from functools import lru_cache
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from app.core.config import settings
from app.services.vectorstore import get_chroma_collection
from app.services.llm import claim_extract_llm

NLI_NAME = "joeddav/xlm-roberta-large-xnli"
NLI_LABELS = ["contradiction", "neutral", "entailment"]

CLAIM_HINT = re.compile(r"(?:must|shall|required|deadline|\bby\b|\b%\b|\bRs\.?\b|\bLKR\b)", re.I)


@lru_cache(maxsize=1)
def _nli():
    tok = AutoTokenizer.from_pretrained(NLI_NAME)
    mdl = AutoModelForSequenceClassification.from_pretrained(NLI_NAME).eval()
    return tok, mdl


def extract_claims(text_en: str) -> list[str]:
    """Regex shortlist; if the post passes the hint filter we ask the LLM
    to atomise it into independently verifiable factual claims."""
    sents = re.split(r"(?<=[.!?])\s+", text_en)
    candidates = [s.strip() for s in sents if CLAIM_HINT.search(s)]
    if not candidates:
        return []
    return claim_extract_llm(candidates)   # returns list[str], capped at 5


def verify(claim: str, k: int = 5) -> dict:
    coll = get_chroma_collection("regulations_chunks_v1")
    res = coll.query(query_texts=[claim], n_results=k,
                     include=["documents", "metadatas", "distances"])
    docs = res["documents"][0]; metas = res["metadatas"][0]
    if not docs:
        return {"verdict": "unverifiable", "nli_label": "neutral",
                "confidence": 0.0, "supporting_regulations": []}
    tok, mdl = _nli()
    pairs = tok([claim] * len(docs), docs, return_tensors="pt",
                truncation=True, padding=True, max_length=512)
    with torch.no_grad():
        logits = mdl(**pairs).logits
    probs = torch.softmax(logits, dim=-1)
    best = int(torch.argmax(probs[:, 2]))   # most-entailing chunk
    p_ent = float(probs[best, 2]); p_con = float(probs[best, 0])
    if max(p_ent, p_con) < 0.55:
        verdict = "unverifiable"; nli = "neutral"; conf = max(p_ent, p_con)
    elif p_ent >= p_con:
        verdict = "true" if p_ent >= 0.85 else "mostly_true"
        nli = "entailment"; conf = p_ent
    else:
        verdict = "false" if p_con >= 0.85 else "mostly_false"
        nli = "contradiction"; conf = p_con
    return {
        "verdict": verdict, "nli_label": nli, "confidence": conf,
        "supporting_regulations": [
            {"title": m.get("doc_title"), "section": m.get("section_id"),
             "snippet": d[:400], "url": m.get("source_url")}
            for d, m in zip(docs, metas)
        ],
    }
```

The full claim-check flow stitches these together: `extract_claims` → for each claim call `verify` → persist into `m4_claim_verifications` → return the list to the API caller.

---

## 9. Spread tracking

Every share / retweet / quote / reply we ingest writes a row into `m4_spread_events`. The graph view lets us answer the proposal's research question: *do false posts spread differently from true ones?*

```python
# FILE: backend/app/modules/m4/spread.py
import math
import networkx as nx
from sqlalchemy import select
from app.modules.m4 import models


async def virality_score(db, raw_post_id: int) -> float:
    raw = await db.get(models.M4RawPost, raw_post_id)
    reach = max(raw.reach, 1)
    eng_rate = (raw.engagement / reach) if reach else 0.0
    return math.log10(1 + reach) * (1 + eng_rate)


async def build_cascade(db, raw_post_id: int) -> nx.DiGraph:
    g = nx.DiGraph()
    rows = (await db.execute(select(models.M4SpreadEvent)
                .where(models.M4SpreadEvent.raw_post_id == raw_post_id))).scalars()
    for e in rows:
        g.add_edge(e.parent_post_platform_id or "ROOT", e.actor_handle or e.id,
                   t=e.occurred_at, kind=e.event_type)
    return g
```

A nightly aggregation `scripts/m4/spread_stats.py` runs a Mann-Whitney U test between the virality scores of consensus-labeled `false`/`mostly_false` posts and `true`/`mostly_true` posts; the p-value is logged and surfaced on the dashboard. The proposal's success criterion is **p < 0.05**.

---

## 10. API endpoints

```python
# FILE: backend/app/api/v1/m4.py
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from app.core.deps import get_db, current_admin
from app.core.ratelimit import limiter   # slowapi instance from BUILD_06
from app.modules.m4 import verify as v, classify as c, language as lang
from app.modules.m4.pii import scrub

router = APIRouter(prefix="/v1", tags=["m4"])


class ClaimIn(BaseModel):
    text: str = Field(..., min_length=10, max_length=4000)


class ClaimOut(BaseModel):
    verdict: str
    confidence: float
    nli_label: str
    supporting_regulations: list


@router.post("/verify/claim", response_model=ClaimOut)
@limiter.limit("30/minute")
async def verify_claim(payload: ClaimIn, request: Request):
    src, _ = lang.detect(payload.text)
    text_en, _ = lang.translate_to_en(payload.text, src)
    text_en = scrub(text_en).text
    return v.verify(text_en)


@router.get("/m4/misinformation-stats")
async def stats(db = Depends(get_db)):
    # Aggregates: counts per veracity, per platform, weekly trend, virality split
    return await _aggregate(db)


@router.post("/m4/posts/raw", dependencies=[Depends(current_admin)])
async def admin_ingest(records: list[dict], db = Depends(get_db)):
    # Manual / CSV-driven ingest path (TikTok, WhatsApp uploads, etc.)
    return await _bulk_insert_raw(db, records)
```

`/verify/claim` is the only fully **public** Module 4 endpoint. It is rate-limited to 30 requests per minute per IP via the `slowapi` limiter wired up in `BUILD_06`. `/m4/posts/raw` is admin-only and is what the manual / CSV connectors POST against.

---

## 11. Frontend — public claim-check tool

```tsx
// FILE: frontend/app/verify/page.tsx
"use client";
import { useState } from "react";
import { VerdictCard } from "@/components/m4/VerdictCard";

export default function VerifyPage() {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<any>(null);

  async function submit() {
    setBusy(true);
    try {
      const r = await fetch("/api/v1/verify/claim", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (r.status === 429) throw new Error("Too many requests, slow down.");
      setRes(await r.json());
    } finally { setBusy(false); }
  }

  return (
    <main className="mx-auto max-w-2xl p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Check a regulatory claim</h1>
      <p className="text-sm text-muted-foreground">
        Paste a forwarded message in English, Sinhala or Tamil. We will verify
        it against published Sri Lankan regulations and show what they say.
      </p>
      <textarea className="w-full border rounded-md p-3 min-h-[160px]"
        value={text} onChange={(e) => setText(e.target.value)} />
      <button onClick={submit} disabled={busy || text.length < 10}
        className="px-4 py-2 rounded-md bg-primary text-primary-foreground">
        {busy ? "Checking..." : "Check this claim"}
      </button>
      {res && <VerdictCard {...res} />}
    </main>
  );
}
```

`VerdictCard` renders a coloured banner (`true` green, `false` red, `unverifiable` grey, `partially_true` / `misleading` amber), the confidence as a percentage, and a list of matched regulations with section anchors that deep-link into the Module 2 reader.

---

## Acceptance Criteria

1. The six `m4_*` tables exist with the exact columns above; Alembic migration is reversible; `is_consensus_label` and `posted_at` are indexed.
2. **At least 500 unique consensus-labeled posts** (deduplicated by `content_hash`) exist in `m4_labeled_posts` covering all three languages.
3. The Cohen's κ report across all annotator pairs is **≥ 0.70**; the report and the underlying confusion matrices are committed under `reports/m4/kappa_*.md`.
4. The fine-tuned XLM-R classifier achieves **macro-F1 ≥ 0.75** and **accuracy ≥ 0.80** on a held-out test set; metrics are logged to MLflow and reproducible via `BUILD_11`.
5. Test coverage for `app.modules.m4.*` is **≥ 80 %** in `pytest --cov`.
6. RAGAS faithfulness on the claim-check golden set is **≥ 0.85**, with `answer_relevance ≥ 0.80`. The golden set lives at `tests/m4/golden/claim_check.jsonl`.
7. The public claim-check tool is deployed at `/verify`, rate-limited at 30 req/min, and works end-to-end for English, Sinhala, and Tamil inputs.
8. PII scrubbing tests pass: synthetic NIC (old + new format), Sri Lankan phone numbers, and emails are all redacted; no failures in `tests/m4/test_pii.py`.
9. The spread analysis script reports a Mann-Whitney U test with **p < 0.05** for virality difference between false-leaning and true-leaning posts; output is committed to `reports/m4/spread_stats.md`.
10. The verifier reuses ChromaDB collection `regulations_chunks_v1` with **zero** new collections created in this module — verified by an integration test that asserts `chroma.list_collections()` is unchanged after a verifier round-trip.

---

## Claude Prompts

**(a) Twitter Academic API ingester with backfill + cursor pagination.**
"Implement `app/modules/m4/sources/twitter.py` extending `SourceConnector`. Use `tweepy.Client.search_all_tweets` against the trilingual keyword query in this file. Persist `next_token` in a new `m4_ingest_state` table keyed by `(platform, query_hash)` so that re-runs resume from the last cursor. Add a `backfill(since, until)` method that walks the cursor backwards in 7-day windows, sleeps on rate-limit headers, and yields `IngestRecord` objects. Add `tests/m4/test_twitter.py` that mocks `tweepy.Client` with `respx`-style fixtures and asserts dedup via `content_hash`."

**(b) Label Studio config + import script with kappa report.**
"Generate `ops/label_studio/m4_veracity.xml` matching the XML in `BUILD_10`. Then write `scripts/m4/import_to_ls.py` that pulls cleaned posts not yet sent to Label Studio (left join on `m4_labeled_posts`), calls the LS REST API to create tasks, and tags each task with the cleaned_post_id. Finally write `scripts/m4/kappa_report.py` that loads all consensus-eligible labels from `m4_labeled_posts`, computes pairwise Cohen's kappa via `sklearn.metrics.cohen_kappa_score`, and writes a markdown report to `reports/m4/kappa_<date>.md`. Fail with exit 1 if cohort kappa < 0.70."

**(c) XLM-R fine-tune script via HF Trainer + W&B (cross-ref `BUILD_11`).**
"In `BUILD_11_ML_Training_Pipeline.md` add `pipelines/m4_veracity_train.py` that loads `m4_labeled_posts where is_consensus_label = TRUE`, stratified-splits 80/10/10 by veracity, fine-tunes `xlm-roberta-base` with `transformers.Trainer` (epochs=4, lr=2e-5, batch=16, fp16), uses a `WeightedRandomSampler` for class imbalance, logs to W&B project `enigmatrix-m4`, computes macro-F1 + per-class F1 + confusion matrix, and registers the model to MLflow as `m4-veracity` with stage `Staging`. Promotion to `Production` is manual after macro-F1 ≥ 0.75 is confirmed."

**(d) RAG verifier chain returning verdict + citations.**
"Implement `app/modules/m4/verify.py` exactly as in `BUILD_10`. Add a small benchmark `tests/m4/test_verify_golden.py` that loads `tests/m4/golden/claim_check.jsonl`, runs each claim through `verify`, computes accuracy of `verdict` against the gold label collapsed to `{supports, refutes, unverifiable}`, and asserts ≥ 0.80. Wire in RAGAS faithfulness via `ragas.metrics.faithfulness` evaluated on the (claim, retrieved chunks, verdict) triples and assert ≥ 0.85."

**(e) Cohen kappa report generator across annotators.**
"Write `scripts/m4/kappa_report.py` that accepts an optional `--since` date, builds an N x N kappa matrix across all annotators with at least 30 overlapping items, prints per-pair κ, the cohort weighted κ, and an agreement breakdown by veracity class. Output is markdown plus a CSV. The script is run nightly by Celery beat (see `BUILD_12`); a κ < 0.70 trips a Slack alert via the integration in `BUILD_13`."

---

**Prev:** `BUILD_09_Module3_Risk.md`  ·  **Next:** `BUILD_11_ML_Training_Pipeline.md`
