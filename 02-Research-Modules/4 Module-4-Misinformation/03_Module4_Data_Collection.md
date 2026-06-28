# Module 4 — Data Collection Methodology

> **Companion to:** [`module_1_and_4_data_architecture.md`](module_1_and_4_data_architecture.md) (the schema source) and [`BUILD_10_Module4_Misinformation.md`](../../backend/BUILD_PLAN/BUILD_10_Module4_Misinformation.md) (the runtime build).
>
> **Purpose:** the architecture doc says *what shape* the data takes (`m4_*` tables, 9-way veracity, FactCheck.lk seed, fastText LID + NLLB-200 translation). This doc says *how the data is collected*: volumes, language balance, annotation workforce, deduplication, time normalisation, PII boundaries, ethics. It is the answer to the open questions §7 of the architecture doc.

---

## 1. Scope: what counts as "regulatory misinformation"

**In scope** — claims about Sri Lankan tax / compliance / business-registration rules that are demonstrably wrong or misleading when checked against the M1 regulations corpus:

- Tax rates, thresholds, deadlines (VAT 15 % vs. 18 %, threshold LKR 36 M vs. LKR 80 M, filing dates).
- Penalty / enforcement claims (EPF "3-month default = jail", IRD "automatic audit" claims).
- Authority-fabrication ("Ministry of Finance announced", "IRD circular says…" — when no such announcement exists).
- Outdated information (claims that *were* true under a previous regime — pre-July-2026 VAT thresholds, pre-2024 Inland Revenue Act amendments — passed off as current).
- Misleading framings of optional vs. mandatory rules ("you can avoid VAT by structuring sales as…", "EPF is voluntary for small businesses").
- Procedural misinformation (wrong filing portal, wrong calculation method, wrong rounding rule).

**Out of scope** — explicit non-goals:

- Political misinformation unrelated to tax / compliance.
- Public-health misinformation (COVID, dengue, vaccines).
- Commercial fraud / scam advice that doesn't reference a specific regulation.
- Personal-attack content directed at named regulators (handled separately as a moderation task).
- Any claim whose evidence isn't reachable via M1's regulation corpus (out of scope until M1 BUILD_07 ships).

**Threshold for inclusion:** a post is in-scope if at least one **claim** in it can be verified or refuted against the M1 corpus. A post can carry multiple claims; each is verified separately by the M4 verifier (see architecture doc §6).

---

## 2. Volume + class-balance targets

### 2.1 Headline numbers

| Target | Value | Rationale |
|---|---|---|
| Consensus-labeled posts (training set) | **≥ 500** | Architecture doc §4 minimum; BUILD_10 acceptance criterion |
| Inter-annotator agreement (Cohen's κ) | **≥ 0.70** | Standard threshold for non-trivial-difficulty annotation tasks; below 0.70 → quarantine the cohort |
| Classifier macro-F1 on held-out test | **≥ 0.75** | BUILD_10 release gate; matches the published XLM-R baseline on multilingual claim-detection |
| Mann-Whitney U (false vs. true virality) | **p < 0.05** | The "misinformation outperforms accurate content" finding the architecture doc references; fails-to-reject means the dataset doesn't show the differential and we re-collect |

### 2.2 Veracity-class distribution target

The 9-way taxonomy is `true / mostly_true / partially_true / misleading / mostly_false / false / unverifiable / opinion / outdated`.

Real-world distribution of regulatory posts skews heavily toward `unverifiable` (posts that don't make a checkable claim) and `opinion` ("VAT is too high" — not factually checkable). Naïve sampling produces a useless training set. Target distribution after sampling:

| Class | Target % of consensus-labeled set | Notes |
|---|---|---|
| `false` | 20 % | The minority class we most want to detect; oversample via FactCheck.lk seed + active search for known-false claims |
| `mostly_false` | 12 % | |
| `misleading` | 10 % | |
| `outdated` | 8 % | The most subtle class — claims that were once true; high inter-annotator-disagreement risk |
| `partially_true` | 8 % | |
| `mostly_true` | 12 % | |
| `true` | 15 % | Includes regulator posts (IRD/EPF official) — used as anchor points for the classifier's "definitely-true" boundary |
| `unverifiable` | 10 % | Cap the upward pressure — too many makes the classifier defensive |
| `opinion` | 5 % | Cap; opinion is a separate task and shouldn't dominate |

**Sampling strategy:** stratified inverse-rejection. After each weekly ingest pass, check current per-class counts; over-sampled classes have their post-acceptance probability reduced for the next batch (e.g. once we hit 100 `unverifiable` posts, reject 80 % of new `unverifiable` candidates until the other classes catch up).

### 2.3 Language balance

Sri Lanka is trilingual. Misinformation circulates in different platforms in different languages. WhatsApp + Facebook are SI/TA-heavy; Twitter/X is EN-heavy; YouTube is mixed.

| Language | Target % | Sourcing notes |
|---|---|---|
| Sinhala (SI) | 35 % | Facebook groups + WhatsApp uploads + YouTube comments dominate |
| Tamil (TA) | 25 % | Northern + Eastern Province FB groups, Tamil-language YouTube channels (e.g. accountants in Jaffna), regional newspapers |
| English (EN) | 30 % | Twitter/X, Reddit, English business news, accounting-firm blogs |
| Mixed-script | 10 % | Real WhatsApp posts often mix EN + SI Sinhala-letters; transliterated Sinhala in EN-letters ("budget eka", "tax eka") |

**Why not 33/33/33:** SI carries more high-engagement misinformation in volume, which reflects the actual platform reality. The model should be calibrated to that reality. We don't want to train an EN-dominant classifier and have it underperform on the channels that matter most.

---

## 3. Annotation workforce + protocol

### 3.1 Three-tier model

| Tier | Role | Headcount | Rate | Notes |
|---|---|---|---|---|
| 1 | Primary annotator (SI-native) | 1 | LKR 50 / labeled post | CA student, contracted; reads SI + EN |
| 1 | Primary annotator (TA-native) | 1 | LKR 50 / labeled post | Same; reads TA + EN |
| 2 | Adjudicator (senior CA) | 1 | LKR 250 / adjudicated tie | Resolves disagreements where κ for the (A, B) pair < 0.65 |
| 3 | Quality auditor (researcher) | 1 (the project lead) | n/a | Reviews 5 % random sample weekly; reports κ trends |

**Total budget for the 500-post target:**
- 500 posts × 2 primary annotators × LKR 50 = **LKR 50,000**
- ~20 % expected disagreement rate → 100 ties × LKR 250 = **LKR 25,000**
- Total: **~LKR 75,000** (≈ USD 250)

### 3.2 Recruitment

- Primary annotators sourced via the Sri Lankan accounting-student community: CA Sri Lanka student body, ICASL articulation programmes, Univ of Colombo accounting department.
- Selection criteria: (a) at least one year of CA training, (b) demonstrably native in SI or TA, (c) signed NDA + ethics consent.
- Adjudicator recruited from CA Sri Lanka membership, paid per-tie not per-hour.

### 3.3 Annotation protocol (ties into BUILD_10 §Label Studio)

For each post:

1. Annotator sees: post text (original-language) + machine-translated EN + post metadata (platform, posted_at, reach, engagement) + retrieval-card (top-3 M1 regulation snippets the verifier flagged as related).
2. Annotator picks **veracity** (radio, 9-way; mandatory).
3. Annotator ticks any of the **5 misleading-mechanics** flags (`wrong_numbers`, `wrong_dates`, `fake_authority`, `fear_appeal`, `urgency_appeal`).
4. Annotator types a 1-line **rationale** (optional but encouraged; required if veracity is `false` or `outdated`).
5. Submit.

Each post goes to **two** primary annotators. A post is `is_consensus_label = TRUE` only if both annotators picked the **same** veracity.

### 3.4 κ monitoring + quarantine

Nightly cron computes Cohen's weighted κ per (annotator-A, annotator-B) cohort over the trailing 7 days:

- κ ≥ 0.70 → cohort's labels retained as gold.
- 0.65 ≤ κ < 0.70 → labels retained but **flagged**; the auditor reviews 20 % of disagreements; if systematic bias, re-train the annotator pair.
- κ < 0.65 → cohort's labels quarantined (not used for training); the adjudicator resolves every tie in that cohort.

The `m4_labeled_posts.is_consensus_label` boolean is recomputed nightly based on the current cohort's κ status — labels that retroactively fall below the threshold get unflagged.

### 3.5 Tie-breaker policy (resolves OQ from architecture doc §7)

A "tie" = two primary annotators picked **different** veracity values. Tie-breaker:

- If the disagreement is *adjacent* (e.g. `mostly_false` vs. `false`, or `partially_true` vs. `mostly_true`) AND the cohort's running κ ≥ 0.70 → no adjudicator needed; the post is left unlabeled (consensus = false). It re-enters the queue in the next cycle for a new pair.
- If the disagreement is *not adjacent* (e.g. `false` vs. `mostly_true`) → adjudicator resolves immediately. Adjudicator's pick is gold.
- If the cohort's κ < 0.65 → adjudicator resolves every tie in that cohort, regardless of distance.

---

## 4. Deduplication + cross-platform identity

### 4.1 Two-tier dedup

| Tier | Method | Threshold | Action |
|---|---|---|---|
| 1 (exact) | SHA-256 over normalised text (lowercased, whitespace-collapsed, URLs replaced with `<URL>`, mentions replaced with `<HANDLE>`) | exact match | New row in `m4_raw_posts`; foreign-keys to existing `m4_cleaned_posts.cleaned_post_id` |
| 2 (near-duplicate) | MinHash (k=128) over translated EN text, Jaccard estimate | ≥ 0.85 | Cluster — share `m4_cleaned_posts` row, increment a `cluster_size` counter |

A canonical claim like "VAT reduced to 15 % effective today" reposted across 3 platforms with minor wording changes → **one** `m4_cleaned_posts` row, **three** `m4_raw_posts` rows pointing at it. `virality_score` aggregates across the cluster.

### 4.2 Cross-language clusters

A post in SI ("වැට් 15% දක්වා අඩු කරලා") and the same claim in EN ("VAT reduced to 15 %") translate to similar EN strings — caught by the MinHash. We track `language_detected` per row but cluster on translated text.

### 4.3 What does NOT trigger dedup

- Same regulator account posting daily updates → distinct dates, distinct content. Each row stands alone.
- Same person making slightly different claims (e.g. "VAT is 15 %" today, "VAT is 12 %" tomorrow) → these are *different* claims, separate rows.
- Reply chains where the parent and child both make claims → separate rows. (Threading is a separate slice; out of scope here.)

---

## 5. Time-normalised virality

Architecture doc §5 (lines ~629 of BUILD_10) defines `virality_score = log10(1 + reach) * (1 + engagement_rate)`. Replace with:

```
virality_score = log10(1 + reach / max(1, hours_visible)) * (1 + engagement_rate)
```

where `hours_visible = max(1, (now - posted_at) in hours)`.

This corrects the "ancient post with 100k reach" vs. "fresh post with 10k reach in 6 hours" comparison. The 6-hour fresh post should score higher per the empirical observation that misinformation travels faster than corrections.

For the Mann-Whitney U test (false vs. true virality), use the time-normalised score on posts ≥ 24 h old (so all posts have had time to develop spread). Posts < 24 h old enter the dataset but don't enter the U test until they age in.

---

## 6. PII + bias-mitigation boundaries

### 6.1 What gets scrubbed (per BUILD_10 §410-436)

Already-scrubbed before storage in `m4_cleaned_posts.text_*`:

- NIC numbers (old + new format).
- Phone numbers (Sri Lankan + international formats).
- Email addresses.
- Account numbers (banking).
- Government employee IDs.

### 6.2 What is NOT scrubbed

- Author handle / username (kept in `m4_raw_posts.author_handle` for spread analysis).
- Public-figure full names (politicians, regulators, named accountants in business profiles).
- Group names (Facebook group titles).

### 6.3 Annotator-bias mitigation

Annotators see the **post text + metadata** but **not** the author's account history (so they can't anchor on "this person always lies" or "this is the IRD official account"). The retrieval-card showing M1 regulation snippets *does* show the regulator name (the source citation), which is the only authority signal the annotator gets.

`author_handle` is shown to annotators (they need it to recognise "this is a regulator" vs. "this is a random account"), but in any export beyond the platform (research papers, public datasets), `author_handle` is hashed.

### 6.4 Consent

For the WhatsApp voluntary upload survey:

> "We are researchers at [University / NGO] studying misinformation about tax and business rules in Sri Lanka. If you upload a WhatsApp message you've received, we will store the message text only — no phone numbers, no contact info, no group names visible to anyone outside our team. You can ask us to delete your upload at any time. By uploading, you consent to us using the message text for research and to train an automated misinformation-detection tool. We will not share your upload with any third party except in aggregate, anonymised statistics."

Survey form gates upload on a tickbox: "I understand and consent to the above."

---

## 7. Manual-collection scope (TikTok + WhatsApp)

| Channel | Method | Quarterly target | Sampling strategy |
|---|---|---|---|
| TikTok | Manual CSV import (no API) | 50 clips/quarter | Random sample from search results for top-30 keywords (see §B.2 of `module_4_perplexity_prompt.md` for the keyword list); over-sample SI/TA |
| WhatsApp | Voluntary upload survey | 100 forwards/quarter | Survey link distributed via NEDA + CA Sri Lanka student newsletter; consent-required |
| SMS scams | Manual entry from anti-scam reports | 20/quarter | Sourced from Sri Lanka Computer Emergency Readiness Team (SLCERT) reports, anti-fraud ICTA bulletins |

These three combined produce ~170 manual-collection rows per quarter. Most of the 500 target comes from Twitter/X + Facebook + Reddit + YouTube via the runtime connectors.

---

## 8. Class balance for training (resolves OQ from architecture doc)

`WeightedRandomSampler` weights are **recomputed nightly** by a cron job:

```python
# pseudocode
counts = SELECT veracity, COUNT(*) FROM m4_labeled_posts WHERE is_consensus_label = TRUE GROUP BY veracity
total = sum(counts.values())
weights_per_class = { v: total / (len(counts) * c) for v, c in counts.items() }
```

This produces an inverse-frequency weighting. The training script (BUILD_11) reads `weights_per_class` from a versioned JSON in `ml/artifacts/m4_class_weights/<date>.json`.

The training script also stratifies the 80/10/10 train/val/test split by veracity, so all three classes are represented in the held-out test set.

---

## 9. Ethics + IRB

This research falls under standard "publicly-posted social media + voluntary survey" ethics. Sri Lanka has no formal central IRB for non-medical social-science research; we self-bind to:

1. **NEDA partnership confirmation** (OQ4 in [`docs/tracker/FEATURES.md`](../../tracker/FEATURES.md)) — once NEDA signs on, their research-ethics protocol governs.
2. **CA Sri Lanka professional ethics** for the contracted CA-student annotators.
3. **GDPR-equivalent baseline:** no NIC, no phone, no email, no consent-less private-group scraping. Public posts only, plus opt-in WhatsApp survey.
4. **Right to deletion:** any subject can email a takedown request; we delete within 30 days. (Implemented via the existing `audit_log` `posting_takedown` event in BUILD_13.)

Out-of-scope from the ethics protocol but worth noting in the methodology doc:

- We do **not** pay platforms for API access (Twitter Academic API tier is free for research; FB Graph API public-page tier is free).
- We do **not** scrape private groups or DM threads.
- We do **not** use captured posts for any commercial purpose; the dataset and the trained model stay open-research.

---

## 10. Open questions (deferred from this slice)

- **Multimodal misinformation:** ~30 % of viral misinformation in Sri Lanka now circulates as **screenshot images** (e.g. fake "IRD letter" PDFs, fake gazette excerpts). Image OCR + image-claim verification is a separate slice. Until then, we ingest the post's caption text only and flag image-only posts as `unverifiable` by default.
- **Audio misinformation:** TikTok / YouTube Shorts audio is not transcribed in the v1 pipeline. Whisper integration is a follow-up.
- **WhatsApp at scale:** the voluntary-upload survey caps at ~100 posts/quarter. Reaching the 500-target SI/TA balance via WhatsApp alone is infeasible; we lean on Facebook + YouTube comments to supplement.
- **Adversarial robustness:** if the classifier ships publicly, malicious actors will try to jailbreak it (e.g. via emoji-substitution: "VAT reduced to 1️⃣5️⃣ %"). Out of scope for v1; track in a future slice.
- **Active learning loop:** can the classifier triage incoming posts and prioritise the high-uncertainty ones for annotation? Implementation belongs in BUILD_11.

---

## 11. References

- [`docs/research/module_1_and_4_data_architecture.md`](module_1_and_4_data_architecture.md) — schema source.
- [`docs/research/module_4_perplexity_prompt.md`](module_4_perplexity_prompt.md) — the research prompt that populates the source registry.
- [`docs/research/module_4_sri_lankan_sources.md`](module_4_sri_lankan_sources.md) — the source registry the connectors consume.
- [`docs/BUILD_PLAN/BUILD_10_Module4_Misinformation.md`](../../backend/BUILD_PLAN/BUILD_10_Module4_Misinformation.md) — the runtime build plan.
- [`docs/BUILD_PLAN/BUILD_11_ML_Training_Pipeline.md`](../BUILD_PLAN/BUILD_11_ML_Training_Pipeline.md) — classifier training (consumer of `weights_per_class`).
- Cohen, J. (1968). Weighted kappa: nominal scale agreement provision for scaled disagreement or partial credit. — the κ formula used in §3.4.
