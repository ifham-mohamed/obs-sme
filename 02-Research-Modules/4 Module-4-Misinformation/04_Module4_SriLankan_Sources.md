# Module 4 — Sri Lankan source registry

> **Purpose:** the structured pick-list of named sources (Facebook groups, YouTube channels, Twitter / X handles, fact-check outlets, Reddit threads, scam-SMS patterns, search keywords) that the Module 4 misinformation-detection pipeline ingests from. Read at design-time by humans; loaded at runtime by the BUILD_10 connectors.
>
> **How to populate:** run the prompt in [`module_4_perplexity_prompt.md`](module_4_perplexity_prompt.md) every ~6 months and merge the output into the matching sections below. Verify each URL resolves before committing.
>
> **Related docs:**
> - [`module_4_data_collection.md`](module_4_data_collection.md) — methodology that drives the *use* of these sources (volume targets, language balance, sampling).
> - [`module_1_and_4_data_architecture.md`](module_1_and_4_data_architecture.md) — schema (`m4_*` tables, 9-way veracity).
> - [`docs/BUILD_PLAN/BUILD_10_Module4_Misinformation.md`](../../backend/BUILD_PLAN/BUILD_10_Module4_Misinformation.md) — runtime build that consumes this registry.

---

## Conventions

| Field | Meaning |
|---|---|
| `trust_score` | 1 (mostly accurate) → 5 (mostly misinformation). See [`module_4_perplexity_prompt.md`](module_4_perplexity_prompt.md) "How to use this prompt" for the rubric. |
| `language` | `en` / `si` / `ta` / `mixed` |
| `first_seen` | ISO date when this source was first added to the registry |
| `last_active` | ISO date of last observed activity (best-effort; leave blank if unknown) |
| `archived` | `yes` if the source is no longer live but kept here for retrospective analysis |

**URL hygiene:** every row must carry a verifiable URL or `[unverified]`. The connector code (`backend/app/services/m4_*.py`) fails loudly on a 404, so populate carefully.

**Pre-filled rows:** sections below are pre-seeded with confidently-known sources (e.g. FactCheck.lk, the canonical sub-reddits). All other rows are TODO until the Perplexity prompt is run.

---

## 1. Facebook (groups + pages)

| name | url | type | language | members | last_active | trust_score | notes |
|------|-----|------|----------|---------|-------------|-------------|-------|
| TODO — populate via Perplexity prompt §Task 1 | | | | | | | |

`type` ∈ { `regulator_official`, `accounting_firm`, `sme_forum`, `news_outlet`, `anon_advice`, `chamber`, `educational` }.

The connector ([`backend/app/services/m4_ingest_facebook.py`](../../backend/app/services/) — to be created in BUILD_10) reads only rows where `type` ≠ `anon_advice` AND the page is not gated (Graph API public-page tier).

---

## 2. YouTube channels

| name | url | channel_id | language | subscribers | last_upload | trust_score | notes |
|------|-----|-----------|----------|-------------|-------------|-------------|-------|
| TODO — populate via Perplexity prompt §Task 2 | | | | | | | |

`channel_id` is the canonical ID (e.g. `UCxxxxxxxxxx` from `youtube.com/channel/UC...` URLs, or the `@handle` from new-style URLs). The runtime connector calls YouTube Data API v3 `channels.list` + `commentThreads.list`.

---

## 3. Twitter / X handles

| name | handle | url | language | followers | verified | trust_score | notes |
|------|--------|-----|----------|-----------|----------|-------------|-------|
| TODO — populate via Perplexity prompt §Task 3 | | | | | | | |

`handle` includes the `@`. Handles are queried via the Twitter Academic API tier; the runtime connector does keyword-AND-handle queries (e.g. `#VAT from:@IRDSriLanka`) to capture both regulator updates and reactions.

---

## 4. Fact-check outlets

| name | url | tax_category_url | language | trust_score | notes |
|------|-----|------------------|----------|-------------|-------|
| FactCheck.lk | https://factcheck.lk | https://factcheck.lk/category/economy/ | en, si | 1 | The canonical Sri Lankan fact-check outlet; pre-labeled verdicts seed the M4 consensus labels. |
| Hashtag Generation | https://hashtaggeneration.org | [unverified] | en | 1 | Civic-tech / digital-rights NGO that occasionally fact-checks tax claims. Confirm tax-category URL via Perplexity §Task 4. |
| TODO — Watchdog Sri Lanka, others | | | | | |

The runtime connector (`backend/app/services/m4_ingest_factcheck.py`) scrapes pre-labeled verdicts at 1 req/sec, mapping the outlet's verdict labels to the 9-way M4 taxonomy via a small `_VERDICT_MAP` constant.

---

## 5. Reddit (subreddits + sample threads)

### 5.1 Canonical subreddits

| subreddit | url | language | subscribers | notes |
|-----------|-----|----------|-------------|-------|
| r/srilanka | https://www.reddit.com/r/srilanka/ | en | ~600k | General-purpose; tax discussion appears in megathreads + occasional standalone posts. |
| r/AskSriLanka | https://www.reddit.com/r/AskSriLanka/ | en | ~80k | Q&A format; tax confusion threads common. |
| r/sl_business | https://www.reddit.com/r/sl_business/ | en | ~5k | Specifically business / regulatory discussion; smaller but high signal-to-noise. |
| r/lka | https://www.reddit.com/r/lka/ | en, si | ~30k | More informal; some Sinhala-language posts. |

### 5.2 Sample threads

| subreddit | url | thread_title | posted_at | top_comment_count | language | confusion_present | notes |
|-----------|-----|--------------|-----------|-------------------|----------|-------------------|-------|
| TODO — populate via Perplexity prompt §Task 5 | | | | | | | |

Sample threads are *seed examples* for the runtime connector's relevance triage, not the full ingestion. The connector uses PRAW to subscribe to live posts in the four canonical subs and filters by keyword (see §7).

---

## 6. SMS / scam patterns

| pattern_name | sample_text_en | sample_text_si | sample_text_ta | source_url | first_seen | trust_score | notes |
|--------------|----------------|----------------|----------------|------------|------------|-------------|-------|
| TODO — populate via Perplexity prompt §Task 6 | | | | | | | |

All scam-pattern rows have `trust_score = 5` by definition. These are bootstrap negative-class examples for the classifier; the runtime connector does not actively ingest SMS (no API access). Patterns are kept here so that incoming WhatsApp uploads / Twitter posts containing the phrasings can be auto-flagged.

---

## 7. Search keywords (top 30 per language)

These keywords drive the runtime connectors' query loops — Twitter Academic API queries, YouTube search queries, Reddit search queries. Volume-weighted where possible.

### 7.1 English (EN)

```
TODO — populate via Perplexity prompt §Task 7
1. VAT registration Sri Lanka
2. VAT 18%
3. EPF rate Sri Lanka
…
```

### 7.2 Sinhala (SI)

Both Sinhala-script and Latin-letter transliterations. The connector queries both forms because mobile keyboards in Sri Lanka often default to Latin letters even for Sinhala text.

```
TODO — populate via Perplexity prompt §Task 7
1. වැට් නියාම — VAT regulation
2. VAT eka — transliterated, common Facebook form
3. EPF gevuma — EPF payment, transliterated
…
```

### 7.3 Tamil (TA)

```
TODO — populate via Perplexity prompt §Task 7
1. வரி — Tax (Tamil-script)
2. vari — transliterated
3. வரி பதிவு — Tax registration
…
```

---

## 8. Connector configuration

The runtime connectors load this registry at startup. Configuration mapping:

| Connector | Section consumed | What it does |
|---|---|---|
| `m4_ingest_facebook.py` | §1 (where `type` ≠ `anon_advice`) | Polls Graph API public-page tier, captures posts + comments, hashes for dedup |
| `m4_ingest_youtube.py` | §2 + §7 | Polls top-N comments per channel + keyword-search results |
| `m4_ingest_twitter.py` | §3 + §7 | Twitter Academic API; resumes from last `since_id` |
| `m4_ingest_factcheck.py` | §4 | Scrapes pre-labeled fact-check verdicts at 1 req/sec |
| `m4_ingest_reddit.py` | §5.1 + §7 | PRAW; subscribes to live posts in the four canonical subs |
| `m4_ingest_whatsapp.py` | n/a (survey-driven) | Reads voluntary uploads; cross-references against §6 patterns to auto-flag scams |
| `m4_classify_sms.py` | §6 | Applies the scam-pattern lexicon to incoming text from any connector |

All connectors share the dedup pass described in [`module_4_data_collection.md`](module_4_data_collection.md) §4.

---

## 9. Refresh log

| Date | Editor | Change | Sources added | Sources archived |
|------|--------|--------|---------------|------------------|
| 2026-05-09 | (init) | Initial registry skeleton; pre-filled FactCheck.lk + canonical subreddits | 5 | 0 |
| TODO | (research lead) | First Perplexity-driven population | TBD | 0 |

Each refresh writes a new row here. Removed sources go to `archived = yes` rather than being deleted — they remain useful for retrospective analysis of the labelled dataset.

---

## 10. Open question on registry-as-data

OQ19 (per the session plan): should this Markdown registry be auto-loaded by the connector code at runtime (parse the tables → DB seed), or treated as a doc-only artefact with a manual seed step?

**Provisional decision:** doc-only for now. The connectors read environment-variable-named lists (`M4_FACEBOOK_PAGE_IDS=...`, `M4_YOUTUBE_CHANNEL_IDS=...`, etc.), which a small seed script in BUILD_10 populates from this Markdown by parsing the tables. Keeps the registry human-readable; keeps the runtime path simple.

Reconsider if the registry grows past ~200 rows or refresh cadence rises above quarterly.
