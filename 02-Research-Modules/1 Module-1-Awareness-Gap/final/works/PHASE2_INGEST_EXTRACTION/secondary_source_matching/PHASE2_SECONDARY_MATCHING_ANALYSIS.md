# Phase 2 · Data Collection — Secondary-Source 3-Tier Matching: Analysis

> Group: `PHASE2_INGEST_EXTRACTION / secondary_source_matching`. Companion: [[PHASE2_SECONDARY_MATCHING_PLAN]].
> Builds [[03_M1_Data_Collection|03_M1_3_Secondary_Source_Integration]] into code. **Status: implemented 2026-07-23 (verification deferred — sandbox VHDX down).**

## 1. What existed vs the doc

The Phase-4a watchers (`portal_watcher`, `rss_watcher`) already call `propagation_service.record_items`, which runs `propagation_matching.match` — a **2-tier** matcher:

1. exact gazette-number (`\d{3,4}/\d+`) → `exact_gazette`, confidence 1.0;
2. `difflib.SequenceMatcher` fuzzy title/act ≥ 0.78 → `fuzzy_title`.

The de-duplication / **earliest-wins** contract the doc's Step 5 describes is already correct: `record_items` is idempotent on `(regulation_id, source_id)` and keeps the first `first_seen_at`. So Steps 1 and 5 were done.

The genuine gaps were Steps 2–4: the **semantic-embedding tier** (`multilingual-e5-base` cosine, not lexical difflib), the **0.60–0.78 review band**, and the **review-queue flow**.

## 2. Why embeddings are opt-in, not always-on

The doc's Tier-2/3 needs `intfloat/multilingual-e5-base` (~280 MB) via sentence-transformers. This project deliberately keeps large models out of the base API/worker image (the same reason `lid.176.bin` is avoided for language ID and torch is a training-only extra). Forcing that dependency into the always-running watcher path — unverifiable this session — would risk breaking the watchers on every deploy that doesn't ship the model.

So the embedding tier is **opt-in** (`M1_PROP_EMBEDDING_ENABLED`, default OFF): `embeddings.get_embedder()` lazily loads the model and returns None if the setting is off or the import/model-load fails, and `match_tiered` falls back to the pre-existing exact + difflib tiers. Turning embeddings on is a config flag + a `pip install sentence-transformers` + model availability — zero regression when off.

## 3. Key schema/interface deltas

- **`match_method` enum had to grow.** The prior build's `ck_m1_prop_match_method` (migration `202607230001`) allowed only `exact_gazette`/`fuzzy_title`. The new tiers emit `embedding_similarity` and (future) `pending_review`/`human_confirmed`, so migration `202607230002` widens the CHECK. Without this, an embedding-confirmed insert would raise `IntegrityError`.
- **Channels + unique key differ from the doc.** Real channels are `official_portal`/`news_rss` (not `portal_{id}`/`news_{id}`); the unique key is `(regulation_id, source_id)` (not `(regulation_id, channel)`). Earliest-wins is enforced on the real key.
- **No review table (by design, for now).** The doc puts Tier-3 in a separate `m1_propagation_events_review` table so unconfirmed rows never reach the lag/channel-effectiveness views. Rather than add an unverified table + admin UI, this build **counts** Tier-3 `pending_review` candidates and returns them in the batch result but does **not** persist them — achieving the same "views stay clean" guarantee with no schema churn. The review table + `/admin/m1/propagation-review` remains the documented follow-up.

## 4. Purity preserved

`propagation_matching` is intentionally stdlib-only (unit-testable, no ORM/ML import). The new `match_tiered` keeps that: embeddings are computed by the caller (`record_items`, which precomputes the regulation-pool vectors once per batch) and injected as plain float lists; the matcher only does dot-product cosine (math). So the ML dependency lives in one optional module (`embeddings.py`) and never leaks into the pure matcher or its tests.

## 5. Risk posture

Embeddings default OFF → the running system behaves exactly as before this change until an operator opts in. The only always-active change is the widened CHECK (superset of the old values, added `NOT VALID`) and the counting of Tier-3 candidates. Nothing can reject or corrupt existing propagation data on deploy.
