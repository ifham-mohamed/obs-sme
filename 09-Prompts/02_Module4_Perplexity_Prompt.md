# Module 4 — Perplexity Research Prompt (Sri Lanka source intelligence)

> **Use:** paste the **prompt block** below verbatim into Perplexity Pro (or Claude / GPT-Pro with web search enabled). The model returns a structured Markdown artefact that backfills the empty TODO rows in [`module_4_sri_lankan_sources.md`](module_4_sri_lankan_sources.md).
>
> **Why a prompt and not a scraper:** the goal of this exercise is *named source identification* (which Facebook groups, which YouTube channels, which fact-check outlets) — a one-time research deliverable. Once the registry is populated, the runtime BUILD_10 connectors do the actual ingestion. We only need to run this prompt every ~6 months as the platform landscape shifts.
>
> **Recommended runtime:** Perplexity Pro (best web-grounding for non-English-dominant content). Fallback: GPT-5 Pro with browsing enabled. Avoid models without live web access; the source list goes stale within months.
>
> **Cost estimate:** one Perplexity Pro query (~50K tokens output). USD 5–20 depending on model + searches.

---

## How to use this prompt

1. Open Perplexity Pro, set the focus mode to "Web" (not "Academic" — we want platform discovery, not papers).
2. Paste the entire `### PROMPT START` … `### PROMPT END` block below into the input.
3. Wait ~3–5 minutes. The model will fan out across multiple searches per task.
4. Copy the response.
5. Open [`module_4_sri_lankan_sources.md`](module_4_sri_lankan_sources.md) and merge each task's table into the matching section.
6. For each row, **manually verify** the URL still resolves (Perplexity occasionally hallucinates fragments) — the registry is consumed by runtime connectors that will fail loudly if a URL 404s.
7. Commit the merge. The tracker entry is **F-90** (Module 4 data-collection research).

If the model returns fewer rows than asked for, do not pad — empty rows are better than fabricated ones. The connector code (`BUILD_10`) is resilient to a partially-populated registry.

---

## What the prompt asks for

Seven tasks, each producing one Markdown table:

1. Facebook groups + pages (10–20 rows).
2. YouTube channels (8–12 rows).
3. Twitter / X handles (5–10 rows).
4. Fact-check outlets (3–6 rows).
5. Reddit threads (5–10 rows).
6. Common scam SMS / phishing patterns (5–15 rows).
7. Top 30 search keywords in EN + SI + TA.

Output is one Markdown response with seven sub-headings matching the registry's section structure, so paste-merging is mechanical.

---

## The prompt

### PROMPT START

You are a Sri Lankan compliance-research analyst building a misinformation-detection dataset. Your task is to enumerate the **named information sources** — public Facebook groups, YouTube channels, Twitter/X handles, fact-check outlets, Reddit threads, scam SMS patterns, and search keywords — that carry, amplify, or correct **regulatory and tax misinformation in Sri Lanka**.

**Domain:** Sri Lankan tax, EPF, ETF, SSCL, WHT, company registration, customs, business licensing, fines, penalties, VAT, income tax, exemptions. Anything an SME owner or accounting student in Sri Lanka would Google when confused about a tax rule.

**Strict scope:**

- Sri Lanka only. Not generic Indian or South Asian sources unless they have explicit Sri Lankan content.
- Tax / compliance / business-registration only. **Exclude** political-misinformation sources, health-misinformation sources, celebrity / personal-attack content.
- Sources must be **public** — not private groups requiring approval, not DM-only channels.
- If you cannot verify a claim with at least one citable URL, mark the row `[unverified]` rather than fabricating.
- Do not invent member counts, follower counts, or last-active dates. Leave the cell blank if not in evidence.

**Output format:** seven Markdown sections, each section a single Markdown table. No prose between tables. Each row must include a verifiable URL (or `[unverified]`).

For every table use the `trust_score` column as a 1-to-5 integer:

- **1** — mostly accurate (e.g. official regulators, established fact-check outlets, named accountants in good standing).
- **2** — mostly accurate but occasional misinformation.
- **3** — mixed; deliberately neutral framings of unverified claims.
- **4** — mostly misinformation but occasionally accurate.
- **5** — mostly misinformation (anonymous "tax tips", scam channels, deliberately misleading framing).

The trust_score is a **research signal** for class-balancing the training set — sources marked 4–5 are over-sampled when collecting `false`/`misleading` labels; sources marked 1 are anchor points for `true` labels. Don't refuse to assign — best-effort is fine.

---

### Task 1 — Facebook groups + pages (target: 10–20 rows)

Find Facebook groups and pages that publish or amplify Sri Lankan tax / SME content. Prioritise groups with > 5,000 members where possible. Include both **legitimate** sources (official regulator pages, accounting-firm pages with significant followings) and **misinformation-prone** sources (anonymous "tax advice" pages, "SME owners forum"-type groups where unverified claims circulate). Aim for a mix of trust scores.

| name | url | type | language | members | last_active | trust_score | notes |
|------|-----|------|----------|---------|-------------|-------------|-------|

For `type`, use one of: `regulator_official`, `accounting_firm`, `sme_forum`, `news_outlet`, `anon_advice`, `chamber`, `educational`.

---

### Task 2 — YouTube channels (target: 8–12 rows)

YouTube is where Sri Lankan SME owners go for "explain VAT to me in 5 minutes" content. Find:

- **Legitimate channels**: regulators (IRD, EPF, ETF official channels if they exist), CA Sri Lanka, university accounting departments, established accounting firms with explainer-content channels.
- **Informal channels**: independent accountants who post tax advice, business / finance educators, some of which may include subtle misinformation due to outdated content or oversimplification.
- Cover all three languages. SI-medium tax-explainer channels are particularly important to surface — they reach the largest SME audience.

| name | url | channel_id | language | subscribers | last_upload | trust_score | notes |
|------|-----|-----------|----------|-------------|-------------|-------------|-------|

Include the channel ID (after the `/channel/` or `/@` URL segment) so the connector can use the YouTube Data API directly.

---

### Task 3 — Twitter / X handles (target: 5–10 rows)

X is where regulatory news *breaks* in Sri Lanka, then either gets clarified by named accountants or distorted by anonymous accounts. Find:

- Regulator handles (IRD Sri Lanka, EPF, Ministry of Finance, CA Sri Lanka if they tweet).
- Influential accountants / tax columnists.
- Anonymous "Sri Lanka tax" accounts that comment on rate / threshold changes.
- Business-news handles (Daily FT, EconomyNext, etc.) that cover tax stories.

| name | handle | url | language | followers | verified | trust_score | notes |
|------|--------|-----|----------|-----------|----------|-------------|-------|

`handle` includes the `@`. `verified` = blue tick yes/no.

---

### Task 4 — Fact-check outlets (target: 3–6 rows)

Sri Lanka-specific fact-checking organisations. The known ones include FactCheck.lk and Hashtag Generation; surface any others. For each, find the URL pattern of their tax-related fact-checks (e.g. tag pages, category pages) so the connector can scrape just those.

| name | url | tax_category_url | language | trust_score | notes |
|------|-----|------------------|----------|-------------|-------|

`tax_category_url` is the most-specific URL that lists the outlet's tax-related fact-checks. If they have no tax category, leave blank and note in `notes`.

---

### Task 5 — Reddit threads (target: 5–10 sample threads)

Reddit-style discussion of Sri Lankan tax issues happens in r/srilanka, r/AskSriLanka, r/sl_business, r/lka. Find sample threads from the past 12 months where users discuss tax confusion — both the threads where misinformation was *spread* and threads where it was *corrected*. The samples train the classifier on both directions.

| subreddit | url | thread_title | posted_at | top_comment_count | language | confusion_present | notes |
|-----------|-----|--------------|-----------|-------------------|----------|-------------------|-------|

`confusion_present` = `yes` if the thread shows users confused about a tax rule, `no` if it's settled discussion.

---

### Task 6 — SMS / scam patterns (target: 5–15 rows)

Sri Lanka has a documented IRD-impersonation SMS scam pattern (e.g. "Your tax refund of LKR 27,300 is pending. Click here…"). Surface the canonical scam phrasings in EN, SI, and TA so we can use them as bootstrap negative-class training examples.

| pattern_name | sample_text_en | sample_text_si | sample_text_ta | source_url | first_seen | trust_score | notes |
|--------------|----------------|----------------|----------------|------------|------------|-------------|-------|

For SMS scams `trust_score` is always 5 (mostly misinformation by definition). `source_url` should point at SLCERT / ICTA / news coverage that documents the scam, not at the scammer. SI / TA versions: provide the actual non-Latin-script text where available.

---

### Task 7 — Top 30 search keywords (in EN + SI + TA)

For each of the three languages, list the top 30 search keywords that surface tax / regulatory content (a mix of correctly-framed and misinformation-prone framings).

The connectors use these keywords as queries against the Twitter Academic API + YouTube search + Reddit search. Volume-weight where possible. Include both *correct framings* ("VAT registration Sri Lanka") and *misinformation-prone framings* ("avoid VAT Sri Lanka", "tax dodge SME", "EPF skip").

For SI, include both Sinhala-script and transliterated forms (transliterated forms are common on Facebook because mobile keyboards default to EN-letters). For TA, include both Tamil-script and transliterated.

Output as three subsections (### EN, ### SI, ### TA), each a markdown list with 30 items numbered and a one-line note per keyword:

```
### EN
1. **VAT registration Sri Lanka** — correct-framing baseline; high volume after July 2026 threshold change.
2. **VAT 18%** — most-shared rate query; misinformation surfaces around partial reductions.
…
```

---

### Final reminders

- One Markdown response, no prose padding.
- Mark every row with a verifiable URL or `[unverified]`. Do not fabricate.
- If you cannot find at least 5 rows for a task, output what you have and note in a one-line comment why (e.g. "Task 6: only 3 documented SMS-scam patterns found in public sources").
- Trust scores are best-effort; don't refuse to assign.
- Do NOT include political misinformation, health misinformation, or personal-attack content.
- Do NOT include private groups (membership-required) or DM-only channels.

### PROMPT END

---

## Refresh cadence

Run this prompt **every 6 months**. Sri Lankan tax-misinformation channels turn over fast — Facebook groups close, new YouTube channels emerge, scam SMS patterns evolve. The registry is a living document.

When refreshing:

1. Re-run the prompt with today's date (the model uses recency for its searches).
2. Diff the new output against the existing registry.
3. **Mark removed entries** as `archived` (don't delete — they're useful for retrospective analysis).
4. Add new entries with `first_seen = <today>`.
5. Commit with message `chore(m4-registry): refresh Sri Lanka source list <YYYY-MM-DD>`.

The runtime connectors should treat `archived` rows as historical-only (no live ingest, but the labelled posts produced from them stay in the dataset).

---

## Verification after merge

After merging the prompt's output into [`module_4_sri_lankan_sources.md`](module_4_sri_lankan_sources.md):

```bash
# every URL in the registry should be reachable
grep -oE 'https?://[^ )]+' docs/research/module_4_sri_lankan_sources.md \
  | sort -u | xargs -I{} curl -s -o /dev/null -w "%{http_code} {}\n" {}
```

Lines reporting `200` are good. `403` from Facebook is expected (login wall — the runtime connector handles auth). `404` rows should be flagged or removed.

---

## See also

- [`module_4_data_collection.md`](module_4_data_collection.md) — methodology that consumes this registry.
- [`module_4_sri_lankan_sources.md`](module_4_sri_lankan_sources.md) — the registry the prompt populates.
- [`docs/BUILD_PLAN/BUILD_10_Module4_Misinformation.md`](../../backend/BUILD_PLAN/BUILD_10_Module4_Misinformation.md) — the runtime that consumes the registry.
