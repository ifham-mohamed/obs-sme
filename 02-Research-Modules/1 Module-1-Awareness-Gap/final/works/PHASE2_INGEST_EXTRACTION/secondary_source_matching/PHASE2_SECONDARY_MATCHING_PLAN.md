# Phase 2 · Data Collection — Secondary-Source 3-Tier Matching: Plan

> Group: `PHASE2_INGEST_EXTRACTION / secondary_source_matching`. Companion: [[PHASE2_SECONDARY_MATCHING_ANALYSIS]].
> **Status: implemented 2026-07-23.** Verification deferred to operator (sandbox VHDX down).

## 1. Files added / changed

- `alembic/versions/202607230002_widen_prop_match_method.py` (new) — widens `ck_m1_prop_match_method` to `{exact_gazette, fuzzy_title, embedding_similarity, pending_review, human_confirmed}`, `NOT VALID`. `down_revision="202607230001"`.
- `app/m1/services/embeddings.py` (new) — lazy, optional `intfloat/multilingual-e5-base` backend (`get_embedder()` → callable or None); e5 `query:`/`passage:` prefixes + normalised vectors; graceful degrade.
- `app/m1/services/propagation_matching.py` (edit) — `cosine()` + `match_tiered()` (Tier-1 exact → Tier-2 embedding auto-confirm → Tier-3 `pending_review` → discard; difflib fallback when no vectors). Pure/stdlib — embeddings injected by the caller. `match()` unchanged (back-compat).
- `app/m1/services/propagation_service.py` (edit) — `record_items` precomputes regulation-pool vectors once, embeds each item query, calls `match_tiered`; persists Tier-1/2, **counts** Tier-3 (`pending_review`) without persisting; returns `{new_events, pending_review, embeddings}`.
- `app/settings.py` (edit) — `M1_PROP_EMBEDDING_ENABLED` (False), `M1_PROP_EMBED_MODEL`, `M1_PROP_EMBED_AUTO_THRESHOLD` (0.78), `M1_PROP_EMBED_REVIEW_THRESHOLD` (0.60).

No watcher edits — `portal_watcher`/`rss_watcher` call `record_items` unchanged.

## 2. Migration head note

Chain is now `…202607220001 → 202607230001 (validation+governance) → 202607230002 (this)`. Apply both new revisions with a single `alembic upgrade head`.

## 3. Design decisions

- **Opt-in embeddings** — default OFF; difflib fallback means the running matcher is byte-for-byte unchanged until an operator sets `M1_PROP_EMBEDDING_ENABLED=true` and provides sentence-transformers + the model.
- **Tier-3 counted, not persisted** — protects `v_m1_regulation_lag_summary` / `v_m1_channel_effectiveness` from unconfirmed rows without a new table.
- **Pure matcher** — the ML dependency is isolated in `embeddings.py`; the matcher takes injected float vectors so its unit tests need no model.
- **CHECK widened, not dropped** — keeps Layer-1 enforcement of `match_method` while allowing the new tiers.

## 4. Verification (deferred to operator)

1. `python -m compileall app` — covers `embeddings.py`, matcher + service edits.
2. `alembic upgrade head` → `\d+ m1_propagation_events` shows the widened `ck_m1_prop_match_method`; downgrade `-1` round-trips.
3. **Embeddings OFF (default):** run a watcher on a fixture → identical behaviour to before (exact + difflib); `record_items` result has `embeddings=false`.
4. **Embeddings ON:** `pip install sentence-transformers`, set `M1_PROP_EMBEDDING_ENABLED=true`; feed an item that difflib misses but is semantically the same → an `embedding_similarity` event is written; a 0.60–0.78 case increments `pending_review` and writes nothing.
5. Earliest-wins CI: invoke a watcher twice on the same fixture → propagation row count unchanged.
6. `pytest tests/m1/` — add `test_match_tiered` (exact/auto/review/discard bands with injected vectors) alongside the existing difflib matcher tests.
7. `graphify update .`.

## 5. Follow-ups (not in this build)

Dedicated `m1_propagation_events_review` table + `/admin/m1/propagation-review` confirm/reject UI (moving `pending_review` → `human_confirmed`); cross-language threshold tightening (0.82 for SI↔EN) + `pre_gazette_leak` flag; stale-review auto-reject at 14 days; embedding-version pinning in a model registry. This closes the code-addressable 03_M1_3 gap; the remaining 03-series item is the parent `03_M1_Data_Collection` itself (largely shipped — extraction chain + segmentation are already ✅).
