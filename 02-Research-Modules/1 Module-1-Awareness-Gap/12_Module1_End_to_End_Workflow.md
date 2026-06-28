# 12 — Module 1: End-to-End Workflow

> Goal: connect everything from files 09–11 into a running system. This file covers the parts that turn extracted+classified regulations into a deployed alert service AND into the research-grade information-lag dataset that constitutes Module 1's novel contribution.

If file 10 is the "data layer" and file 11 is the "model layer," this file is the **system layer** — orchestration, secondary-source tracking, lag computation, summarization, alerts, dashboards, validation methodology, and how you extract publishable research findings from the live system.

---

## 1. The Full Module 1 Runtime — One Picture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                  CONTINUOUS BACKGROUND JOBS (Celery / cron)               │
├──────────────────────────────────────────────────────────────────────────┤
│  • gazette_scraper       — every 6 hours                                   │
│  • secondary_watcher     — every 1 hour (IRD, EPF, ETF, eROC, news, RSS)  │
│  • social_watcher        — every 6 hours (Module 4 reuses this)           │
│  • alert_dispatcher      — every 15 minutes                                │
│  • daily_lag_aggregator  — once per day at 02:00                          │
└────────────────────────────┬─────────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                  EVENT-DRIVEN PIPELINE (per new regulation)               │
├──────────────────────────────────────────────────────────────────────────┤
│   download → extract → classify → summarize → match SMEs → enqueue alerts │
└──────────────────────────────────────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│   DASHBOARDS                                                              │
├──────────────────────────────────────────────────────────────────────────┤
│  • Researcher dashboard:  pipeline health, lag distributions, slice plots  │
│  • SME dashboard:         personalized regulation feed                     │
│  • Admin dashboard:       labeling queue, model versions, error logs       │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Orchestration — Who Runs What When

### 2.1 The job table

Every scheduled or event-driven task is a Celery task. A minimal `celery_beat_schedule.py`:

```python
from celery.schedules import crontab

beat_schedule = {
    "scrape_gazettes": {
        "task": "tasks.gazette.discover_and_queue",
        "schedule": crontab(minute="0", hour="*/6"),
    },
    "secondary_watchers": {
        "task": "tasks.secondary.poll_all",
        "schedule": crontab(minute="15", hour="*"),
    },
    "social_watcher": {
        "task": "tasks.social.poll_all",
        "schedule": crontab(minute="30", hour="*/6"),
    },
    "alert_dispatcher": {
        "task": "tasks.alerts.dispatch_pending",
        "schedule": crontab(minute="*/15"),
    },
    "daily_lag_aggregation": {
        "task": "tasks.research.aggregate_lag_daily",
        "schedule": crontab(minute="0", hour="2"),
    },
}
```

### 2.2 The end-to-end "happy path" for a new regulation

```
T+0:00   gazette_scraper finds new PDF URL → enqueues process_gazette
T+0:01   process_gazette downloads PDF
T+0:02   extracts text (PyMuPDF) → segments into N notices
T+0:03   for each notice:
            a. clean + language-detect                  (file 10)
            b. INSERT into regulations table
            c. enqueue classify_notice
T+0:05   classify_notice runs the XLM-R classifier     (file 11)
            → updates regulations.category + confidence
            → if confidence < 0.55, flag for human review (no auto-alert)
            → enqueue summarize_notice
T+0:07   summarize_notice produces EN/SI/TA summaries
            → INSERT into regulation_summaries
T+0:08   match_smes selects subscribed SMEs by sector + category
            → INSERT into alerts_sent (status='pending')
T+0:15   alert_dispatcher sends pending alerts via email + dashboard push
            → updates alerts_sent.delivered_at
```

This entire chain typically completes in **8–15 minutes from gazette publication** for a text-based PDF — a number you'll want to measure and report.

---

## 3. Secondary-Source Watchers (the Lag-Tracking Layer)

This is where Module 1's research novelty lives. You're not just classifying gazettes — you're measuring **how regulatory information diffuses across channels**. That means tracking *where else* a given regulation appears, and *when*.

### 3.1 The sources to watch

| Channel | Source | Tech |
|---------|--------|------|
| Tax notices | `ird.gov.lk/notices` | Scrapy / Playwright |
| Provident funds | `epf.lk` and ETF site | Scrapy |
| Company registry | `eroc.drc.gov.lk` | Playwright (JS-heavy) |
| Customs notifications | `customs.gov.lk` | Scrapy |
| Mainstream news | Daily Mirror, Sunday Times, Daily FT, Lankadeepa, Veerakesari | RSS + Scrapy |
| Business associations | NEDA, FCCISL, Chamber bulletins | Manual + RSS where available |
| Social mentions | Public Facebook pages, Twitter/X | Module 4's pipeline |

### 3.2 The watcher pattern

```python
# tasks/secondary.py
from celery import shared_task
from datetime import datetime
from .matching import match_to_known_regulation

@shared_task
def poll_ird_notices():
    items = scrape_ird_notice_list()  # returns list of dicts
    for item in items:
        # try to link this item back to a known gazette regulation
        reg_id = match_to_known_regulation(item["title"], item["body"])
        if not reg_id:
            # we saw it before the gazette? that itself is a finding — store it
            store_unmatched_secondary_appearance(item, channel="ird")
            continue
        # record first-seen timestamp on this channel
        upsert_secondary_appearance(
            regulation_id=reg_id,
            channel="ird",
            url=item["url"],
            first_seen_at=item["published_at"] or datetime.utcnow(),
        )
```

The matching function is the interesting part. You're trying to determine "is this IRD notice about gazette regulation #7841?"

### 3.3 Matching strategy

A two-step approach:

**Step 1 — High-precision rules first:**
- Exact gazette number mention ("Gazette Extraordinary No. 2421/12")
- Exact Act/Section reference ("Section 84 of the Inland Revenue Act")
- Exact section IDs in title

**Step 2 — Embedding similarity for the rest:**
- Embed both the IRD notice and recent gazette regulations using XLM-R or a sentence-transformer
- Cosine similarity > threshold (e.g., 0.78) → propose a match
- Manual review queue for proposed matches with similarity 0.6–0.78

```python
# matching.py
from sentence_transformers import SentenceTransformer
import numpy as np

embedder = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")

def match_to_known_regulation(title, body, recent_regs):
    # 1. exact references
    if m := re.search(r"Gazette\s+(?:Extraordinary\s+)?No\.?\s*(\d+/\d+)", title + body, re.I):
        return lookup_by_gazette_no(m.group(1))
    # 2. embedding similarity
    query_vec = embedder.encode(title + "\n" + body[:1500])
    reg_vecs = np.stack([r.embedding for r in recent_regs])
    sims = reg_vecs @ query_vec / (np.linalg.norm(reg_vecs, axis=1) * np.linalg.norm(query_vec))
    best_idx = sims.argmax()
    if sims[best_idx] > 0.78:
        return recent_regs[best_idx].id
    elif sims[best_idx] > 0.6:
        queue_for_human_review(...)
    return None
```

Document this matching protocol in your methodology — it's a non-trivial engineering decision and the panel will ask.

---

## 4. The Lag Computation Engine

### 4.1 The data model (recap)

From file 09, you have:
- `regulations.publication_date` — when the gazette officially published
- `regulation_secondary_appearances(regulation_id, channel, first_seen_at)` — when each secondary channel first carried it
- `survey_responses` — when SMEs report becoming aware of the regulation (Module 1's awareness survey)

### 4.2 Lag definitions

```
lag_to_portal       = first_seen_at(channel='ird' or 'epf' …) − publication_date
lag_to_news         = first_seen_at(channel='news_*')         − publication_date
lag_to_social       = first_seen_at(channel='social_*')       − publication_date
lag_to_sme_aware    = sme_reported_aware_date                  − publication_date
lag_news_to_aware   = sme_reported_aware_date                  − first_seen_at(news)
```

These are your **dependent variables** for the research analysis.

### 4.3 The aggregation query

```sql
-- daily_lag_aggregator output
WITH first_per_channel AS (
    SELECT regulation_id, channel,
           MIN(first_seen_at) AS first_seen_at
    FROM regulation_secondary_appearances
    GROUP BY regulation_id, channel
),
gazette AS (
    SELECT id, publication_date, category
    FROM regulations
    WHERE category IS NOT NULL
)
SELECT g.id, g.category, g.publication_date,
       MAX(CASE WHEN f.channel LIKE 'portal_%' THEN f.first_seen_at END) AS first_portal,
       MAX(CASE WHEN f.channel LIKE 'news_%'   THEN f.first_seen_at END) AS first_news,
       MAX(CASE WHEN f.channel LIKE 'social_%' THEN f.first_seen_at END) AS first_social,
       EXTRACT(EPOCH FROM (MIN(f.first_seen_at) - g.publication_date))/86400.0 AS days_to_first_secondary
FROM gazette g
LEFT JOIN first_per_channel f USING (regulation_id)
GROUP BY g.id, g.category, g.publication_date;
```

Materialize this as a view (`reg_lag_summary`) refreshed nightly. Your dashboards and statistical analyses read from it.

### 4.4 SME-awareness lag (the survey-side input)

A short follow-up survey (or in-app prompt) asks SMEs:
> "Were you aware of [regulation summary] before today? If yes, approximately when did you first hear about it? Where?"

Each response becomes a row:
```
sme_awareness_events(sme_id, regulation_id, became_aware_on, channel_self_reported)
```

`days_to_sme_aware = became_aware_on − publication_date`. With 100+ SMEs and 50+ regulations sampled, you have **5,000+ awareness data points** — a serious empirical contribution.

---

## 5. Summarization & Translation

### 5.1 What to generate per regulation

Three summaries (EN / SI / TA) at three lengths:
- **Headline** (≤ 15 words) — for alert subject line and SMS
- **Plain-language summary** (3–5 sentences) — for email body and dashboard
- **Action checklist** (3–5 bullet points) — what does an SME need to *do*?

### 5.2 The generation strategy

**For English source notices:**
- Use a local LLM (Llama-3-8B-Instruct or similar) with retrieval grounding, OR
- Use a hosted API (Claude / GPT-4) for higher quality
- Prompt engineering with strict format requirements (see below)

**For Sinhala / Tamil source notices:**
- Translate to English with NLLB-200 (Meta's no-language-left-behind model)
- Summarize in English
- Translate summary back to Sinhala / Tamil
- Have a native-speaker reviewer spot-check 30+ outputs and report quality

```python
# summarize.py
SYSTEM_PROMPT = """You are summarizing a Sri Lankan regulatory notice for a small business owner.
Output strict JSON with three keys: 'headline' (max 15 words),
'summary' (3-5 sentences, plain language),
'actions' (list of 3-5 imperative bullet points).
Do not invent facts. Do not include a deadline unless the source explicitly states one.
"""

def summarize(notice_text: str) -> dict:
    response = llm.complete(SYSTEM_PROMPT, notice_text)
    return json.loads(response)

def to_sinhala(en_text: str) -> str:
    return nllb_translate(en_text, src_lang="eng_Latn", tgt_lang="sin_Sinh")
```

### 5.3 Quality assurance for generated summaries

You cannot publish auto-summaries unchecked. Build a **two-tier system**:
- **Auto-approve** if confidence-checks pass (action keywords match notice; deadlines verified by regex; no hallucination markers)
- **Hold for review** otherwise

Use RAGAS or a simple rubric (factuality, completeness, fluency) to score 50 generated summaries against ground truth, and report quality numbers in your thesis.

---

## 6. Alert Delivery Service

### 6.1 The matching logic — which SMEs get which alert

```python
# tasks/alerts.py
def find_relevant_smes(reg_id: int) -> list[int]:
    reg = get_regulation(reg_id)
    return query_db("""
        SELECT s.id
        FROM sme_profiles s
        JOIN sme_alert_subscriptions sub ON s.id = sub.sme_id
        WHERE sub.is_active = TRUE
          AND ( sub.category IS NULL OR sub.category = :cat )
          AND ( sub.sector IS NULL   OR sub.sector   = ANY(s.sectors) )
        AND NOT EXISTS (
              SELECT 1 FROM alerts_sent a
              WHERE a.sme_id = s.id AND a.regulation_id = :rid
        )
    """, cat=reg.category, rid=reg.id)
```

### 6.2 Channels and policies

| Channel | When used | Service |
|---------|-----------|---------|
| In-app notification | Always | Internal pubsub (Redis pub/sub) |
| Email | Default for all subscribed SMEs | SMTP / SendGrid / Postmark |
| SMS | Critical (deadline within 14 days) | Dialog / Mobitel local API |
| WhatsApp | Optional opt-in | WhatsApp Business API |

Policy: **never send the same alert twice on the same channel**. Track delivery in `alerts_sent`. Idempotency is non-negotiable — you cannot have your research system spam SMEs.

### 6.3 The delivered-data feedback loop

Every alert delivery generates an event:
```
alerts_sent: {sme_id, regulation_id, channel, sent_at, delivered_at, opened_at, clicked_at, dismissed_at}
```

These open/click rates become a secondary research output: *which alert formats and channels are most effective at driving SME engagement?*

---

## 7. SME Subscription Manager

The SME profile (collected via Module 1's awareness survey or a sign-up flow) drives alert relevance. Minimum fields:

```
sme_profiles:
  id, name, sector[] (multi), business_size, district,
  preferred_languages[], registration_status,
  email, phone, whatsapp_optin
```

```
sme_alert_subscriptions:
  sme_id, category (NULL = all), channel_preferences,
  frequency (immediate / daily_digest / weekly_digest), is_active
```

Build a self-service settings page in the Next.js frontend so SMEs can adjust subscriptions — and *log every change* in `audit_log`. Subscription churn is itself a finding.

---

## 8. The Dashboards (What Each Audience Sees)

### 8.1 Researcher Dashboard (`/research/module1`)

- Pipeline health: gazettes scraped today / classified today / failed
- Distribution of lag (histogram) across all completed lag samples
- Lag table by category × channel
- Per-language classifier metric trends over time
- Active model version and last training run summary
- Latest 100 unmatched secondary appearances awaiting review

### 8.2 SME Dashboard (`/sme`)

- "New for you" feed — regulations matching profile, with read/unread status
- Per-regulation page: summary, full text, action checklist, related news links
- Subscription preferences
- Personal compliance timeline (regulations subscribed to with deadlines)

### 8.3 Admin Dashboard (`/admin`)

- Labeling queue (low-confidence classifier outputs awaiting review)
- Model version manager (activate/rollback)
- Error log viewer (extraction failures, matching ambiguities)
- Survey response monitor

Build the researcher dashboard first — you'll use it daily during the project.

---

## 9. Validation Methodology (How You Defend the System)

This is the section your thesis examiners will read most carefully. Build it before you need it.

### 9.1 Pipeline reliability validation

| Component | Method | Sample size | Target |
|-----------|--------|-------------|--------|
| Discovery | Cross-check with manually maintained gazette list | 100 weeks | ≥ 98% recall |
| Extraction | CER on hand-transcribed pages | 50 pages | ≤ 5% (text), ≤ 10% (OCR) |
| Segmentation | Boundary F1 vs gold annotation | 30 gazettes | ≥ 0.85 F1 |
| Classification | Macro-F1 on held-out test | ≥ 200 examples | Beats baselines, with significance |
| Matching | Precision / recall vs hand-linked gold | 80 secondary appearances | ≥ 0.85 precision |
| Summarization | Faithfulness rubric on rated outputs | 50 outputs | ≥ 4/5 mean |
| Alert delivery | End-to-end timing measurement | 30 alerts | Median ≤ 24 hours after gazette |

### 9.2 Research-finding validation

The headline research findings from Module 1 — like *"median lag from gazette to SME awareness in target sector is 18 days"* — must each be defensible:
- Sample size disclosed
- Confidence intervals computed
- Sub-group breakdowns where the data permits
- Sensitivity analysis: does the finding hold if you remove the largest 10% of lags? if you stratify by sector? by language?

### 9.3 The retrospective validation experiment

For 10 historic gazettes from 2024:
- Run the full pipeline against them
- Compare extracted/classified output to your hand-coded ground truth
- Report end-to-end pipeline accuracy as a single bottom-line number

This single experiment is a major asset for your viva.

---

## 10. Extracting Research Findings from the Live System

Module 1 produces **two simultaneous outputs**: the deployed alert system (the artifact) and the empirical findings (the contribution). Plan how findings get extracted.

### 10.1 The findings table — what you'll publish

For your final paper, target this structure:

| Finding | Statistic | Method | Evidence |
|---------|-----------|--------|----------|
| Median lag, gazette → official portal | X.X days (IQR …) | DB query, n=… | reg_lag_summary view |
| Median lag, gazette → news | X.X days | DB query, n=… | reg_lag_summary |
| Median lag, gazette → SME awareness | X.X days | survey + DB join, n=… | sme_awareness_events |
| Lag varies significantly by sector | F=…, p=… | One-way ANOVA | survey + sector |
| Lag varies by language of source | …, p=… | Kruskal-Wallis | regulations.language |
| Alert system reduced lag for subscribed SMEs by | … days (pre/post) | DiD-style comparison | post-deployment cohort |
| Per-language classifier F1 | EN=…, SI=…, TA=… | Held-out test | model_versions |

### 10.2 The notebook setup

Keep one Jupyter notebook per finding category:
- `notebooks/findings_lag_analysis.ipynb`
- `notebooks/findings_classifier_evaluation.ipynb`
- `notebooks/findings_alert_effectiveness.ipynb`
- `notebooks/findings_secondary_diffusion.ipynb`

Each notebook reads from the database, produces the figures and tables for the corresponding thesis section, and is itself committed to git. Reproducibility = passing the viva calmly.

---

## 11. Edge Cases and Failure Modes

| Situation | What happens | What you do about it |
|-----------|--------------|----------------------|
| Gazette PDF is corrupt or 404s | Download fails, retried 3x, then logged | Daily error report; manual queue |
| OCR returns gibberish | Low extraction confidence flag | Skip auto-classification; mark for review |
| Classifier confidence < 0.55 | No automatic alert | Queue for human review in admin dashboard |
| Two gazettes mention each other circularly | Matching returns both | Merge logic in matching module; document as a known case |
| New government agency starts publishing | Watcher doesn't cover it | Monthly review of alerts vs ground truth surfaces this |
| Secondary source goes offline | Watcher fails; lag artificially increases | Track watcher uptime separately; report data caveat in findings |
| SME profile fields change mid-study | Subscription matching changes mid-stream | Immutable `audit_log` allows post-hoc reconstruction |
| Holiday / non-business gazette | Notice classified as regulatory in error | NOT_REGULATORY filter (file 10 §7.3) needs strengthening |

Document these in your thesis "Limitations" section — every honest research project has them, and being upfront strengthens your viva position.

---

## 12. Module 1 Definition of Done

By thesis submission, Module 1's owner should be able to demonstrate, on demand:

- [ ] A new gazette from the past week, ingested → extracted → classified → summarized → alerted to a test SME, with median end-to-end time displayed
- [ ] The researcher dashboard showing 6+ months of pipeline run history
- [ ] At least 800 labeled training examples; ≥ 1,500 ideally
- [ ] An XLM-R classifier reproducible from a single command (`python train.py --seed 42`)
- [ ] At least 50 SMEs with awareness-survey responses linked to ≥ 30 specific regulations
- [ ] A `findings.csv` table with statistics, sample sizes, p-values for each headline claim
- [ ] All 4 new tables (file 09 §7) populated with realistic data volumes
- [ ] Annotated notebooks for each finding category
- [ ] One end-to-end retrospective experiment on historic data with reported numbers
- [ ] Limitations and known failure modes documented honestly

---

## 13. Connecting Module 1 to the Other Modules

Module 1 is the upstream supplier for the rest of the platform:

- **To Module 2 (Compliance Knowledge Gap):** the regulation_summaries table feeds the RAG knowledge base. Each new regulation auto-updates Module 2's chatbot. Knowledge stays current without manual curation — a system-level finding worth highlighting.
- **To Module 3 (Risk Invisibility):** classifier categories and SME profiles together drive risk scoring — an SME with no compliance evidence on a regulation that strongly applies to their sector is high-risk.
- **To Module 4 (Misinformation Spread):** Module 1's authoritative summaries are the *ground truth* against which Module 4 detects and corrects misinformation circulating on social channels.

When you write the integration chapter, lead with Module 1 — it's the data backbone for everything else.

---

## Summary

The Module 1 end-to-end workflow is a continuously-running system: scheduled scrapers and watchers feed an event-driven pipeline that extracts, classifies, summarizes, and alerts; lag aggregation runs nightly; three dashboards expose the system to researchers, SMEs, and administrators. Validation runs at every stage with measurable targets; findings are extracted via dedicated notebooks; honest documentation of edge cases and limitations completes the picture. By the end of Module 1's 12-week build, you have a deployed alert system, a labeled multilingual corpus, a published-quality classifier, and an empirical lag dataset that nobody else has produced for the Sri Lankan regulatory context — that combination is your contribution.
