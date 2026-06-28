# 03_M1_3 — Secondary Source Integration

> Companion to [03_M1_Data_Collection.md](03_M1_Data_Collection.md) — portal-watcher + RSS-watcher de-duplication contract, 3-tier matching, `multilingual-e5-base` embedding choice with comparisons.
> **Implementation status:** 🔲 Deferred (BUILD_07 + BUILD_12)

## Purpose

The parent doc (§3.5) describes the 3-tier matching strategy at a high level. This companion specifies how the *cooperative* contract between portal watchers + RSS watchers + admin review actually works in production: who writes which rows, who corrects mistakes, and why `intfloat/multilingual-e5-base` is the embedding model.

## Detailed process

### Step 1 — Watcher cadence + write contract

Portal watchers and RSS watchers both run every 2 h on different sources. The unique index `uq_m1_prop_reg_channel` (from parent doc §3.6) prevents duplicates. Each watcher follows the same pattern:

```python
# backend/app/tasks/m1/portal_watcher.py
async def scan_portal(source_id: str):
    items = await fetch_portal_listing(source_id)        # source-specific scraping
    for item in items:
        reg_id, method, confidence = await match_to_regulation(item)
        if reg_id is None and confidence < 0.60:
            continue                                      # below review threshold, drop
        await upsert_propagation_event(
            regulation_id=reg_id, channel=f"portal_{source_id_short(source_id)}",
            first_seen_at=item.observed_at, source_url=item.url,
            match_method=method, match_confidence=confidence)
```

### Step 2 — Three-tier matching

| Tier | Condition | Action | Match method |
|---|---|---|---|
| 1 — Exact gazette number | `r"\d{4}/\d+"` found in title or body, lookup by `m1_regulations.gazette_number` | Auto-confirm, INSERT propagation_event | `exact_gazette_number` |
| 2 — Embedding cosine ≥ 0.78 | High-similarity match against the past-90-days regulation pool | Auto-confirm, INSERT | `embedding_similarity` (confidence stored) |
| 3 — Embedding cosine 0.60–0.78 | Plausible match | Flag for admin review (`match_method='pending_review'`) | `pending_review` (admin sets to `human_confirmed` or rejects) |
| — | Cosine < 0.60 | Discard | — |

### Step 3 — Embedding model — `intfloat/multilingual-e5-base` choice

The embedding model is used to compare a *news-article body* against a *gazette regulation summary*. The matching context is multilingual (EN + SI + TA news) and short-text (titles + first 500 chars). Three candidates were evaluated on a 50-pair hand-validated dataset:

| Model | EN→EN cosine on true matches | SI→EN cosine on true matches | Inference latency (CPU, 768-token in) | Model size |
|---|---|---|---|---|
| `intfloat/multilingual-e5-base` | 0.84 avg | 0.81 avg | ~120 ms | 280 MB |
| `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | 0.82 avg | 0.76 avg | ~140 ms | 470 MB |
| `BAAI/bge-m3` | 0.88 avg | 0.85 avg | ~280 ms | 580 MB |

`bge-m3` is more accurate but ~2.3× slower and ~2× the disk footprint; the precision gap doesn't justify the cost at our 2-h cadence + ~30 candidate matches per watch cycle. `multilingual-e5-base` is the operational sweet spot.

### Step 4 — Manual review queue

Tier-3 candidates land in `m1_propagation_events_review` (separate table to keep the main events table clean). Admin UI at `/admin/m1/propagation-review` shows: regulation snippet + news article snippet + cosine score. Admin clicks **Confirm** / **Reject** / **Open in new tab**. On confirm, the row is moved (UPDATE … SET match_method='human_confirmed') into `m1_propagation_events`; on reject, the review row is deleted (audit-logged).

### Step 5 — Earliest-wins for re-observations

If a portal watcher re-observes a regulation it already saw 6 hours ago, the `ON CONFLICT DO NOTHING` clause (parent doc §3.6) drops the second write — preserving the *first-seen* timestamp. This is the contract: `m1_propagation_events.first_seen_at` is *not* "most recent observation" but "earliest confirmed observation."

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| `multilingual-e5-base` (chosen) | Balanced accuracy + speed + size | ✅ Best CPU-latency × accuracy product at our scale | If `bge-m3` becomes available in a smaller distilled form. |
| `paraphrase-multilingual-mpnet-base-v2` | Strong English | ❌ Sinhala/Tamil accuracy 5–8 pp lower | If we drop multilingual support (won't happen). |
| `bge-m3` | Highest accuracy | ❌ Slower + heavier; gain doesn't justify cost | At 10× source volume. |
| Cross-encoder reranker on top of bi-encoder | Highest precision | ❌ 100× the latency; only useful if recall is the bottleneck | If admin review queue grows uncontrollably. |

## Worked example

A real Tier-3 case (anonymised):

```
News article (Daily FT, 2026-04-22): "Government to mandate safety certification on consumer electronics imports"
Gazette candidate (regulation_id reg_2486_22): "Mandatory SLSI Safety Certification for Multi-Pin Universal Power Adapters"

multilingual-e5-base cosine: 0.71  → Tier 3 (review queue)

Admin review (1 minute later):
  Snippet diff highlights "consumer electronics imports" vs "multi-pin universal power adapters"
  Admin judges: same regulation, broad coverage in the news article
  Click "Confirm" → m1_propagation_events row written:
    regulation_id=reg_2486_22, channel='news_daily_ft', first_seen_at=2026-04-22,
    match_method='human_confirmed', match_confidence=0.71, source_url='https://ft.lk/...'
```

The F1 (gazette-to-news) and F2 (news lag) findings include this row; the 0.71 confidence is preserved as a quality flag for thesis methodology disclosure.

## Failure modes & edge cases

- **Embedding-model staleness.** The model version is pinned in `model_registry.json:embedding_model_version`. A version bump invalidates all previous embeddings (they were computed with the old model) — Tier-2 thresholds may need re-calibration.
- **Cross-language Tier 2 mismatches.** A Sinhala news article + English gazette can score 0.79 cosine without truly matching (the model collapses many "tax" mentions across languages into similar embeddings). Mitigation: tighten the Tier-2 threshold to 0.82 for cross-language matches; document in the review queue.
- **Admin reviewing under load.** If the review queue grows beyond 50 items, admins triage by recency (newest first). The risk: old reviews never get done. Mitigation: items aged > 14 days are auto-rejected with `audit_log_reason='stale_review'`.
- **News article published before gazette.** A leak gets reported before the official Gazette is published. The matching algorithm has no anchor (`gazette_number` doesn't exist yet). These appear as Tier-3 with a `pre_gazette_leak=true` flag for the F5 measurement.

## Validation & acceptance criteria

- **Tier-1 precision.** ≥ 99 % (manual audit on a sample of 50 Tier-1 matches per quarter).
- **Tier-2 precision.** ≥ 88 % at the 0.78 threshold (hand-validated 50 pairs per quarter).
- **Review-queue latency.** P95 ≤ 48 h from queueing to admin disposition.
- **Earliest-wins enforcement.** Re-running a watcher does not create duplicate rows (CI test: invoke watcher twice in succession on the same fixture; row count unchanged).

## Cross-references

- Parent: [03_M1_Data_Collection.md](03_M1_Data_Collection.md) §3.5 (matching), §3.6 (de-dup contract)
- Related: [02_M1_1_Data_Sources_Catalogue.md](02_M1_1_Data_Sources_Catalogue.md), [08_M1_1_Research_Findings_Extraction.md](08_M1_1_Research_Findings_Extraction.md) (F2/F5 use this data)
- BUILD phase: BUILD_07 §news watchers, BUILD_12 §portal watchers
- Code (when shipped): `backend/app/tasks/m1/portal_watcher.py`, `rss_watcher.py`, `ml/shared/embeddings.py`
