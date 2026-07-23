# Module 1 — Phase 2 Gap #7: Chunk Contract — Verify, Freeze, Align

> Companion to [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/11_PHASE2_INGEST_EXTRACTION_ANALYSIS]] §6.7 and [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/12_PHASE2_GAP_CLOSURE_PLAN]] §6.7. **Status: implemented (Session 68, 2026-07-21).** The gap asked to "confirm the chunk contract matches what the classifier will expect, before Phase 3 locks in" — the audit found it already **didn't** match, so this session verified, froze, and aligned it.

## What the audit found (worse than "unconsumed")

The gap text assumed chunking output sat idle until Phase 3. Actually Stage-D (`classify_gazette`, Phase 3f) is already live, and the contract had **silently forked**:

1. **The producer runs and is discarded.** `m1.preprocessing.preprocess_gazette` runs `chunk_hybrid()` in the hot path and returns `classification_chunk` — the section-aware head chunk, computed over the **EN bucket** for mixed-language docs — plus `section_chunks`. The backend task persisted neither.
2. **The consumer re-derives its own input.** `classify_gazette` fed `row.cleaned_text` (full document, all languages mixed) into `GazetteInference.classify`, which truncates at `max_length=512`.

So the two heads differ exactly where it matters: **mixed-language gazettes** (contract says classify the EN bucket; live path classified mixed text) and **multi-section docs with boilerplate covers** (contract says head of first *detected section*; live path took the raw document head). For short single-section EN docs they coincide — which is why nothing visibly broke.

## What was done

**1. Frozen by test** — `enigmatrix-ml/tests/m1/preprocessing/test_chunk_contract.py`:

- `Chunk` dataclass field-shape freeze (each test's docstring names the consumer that breaks if it fails).
- `classification_input` ≡ head-chunk invariant (with the retraining warning in the docstring — training consumed head text, so changing this needs a retrain).
- **Head-window ≡ 512-truncation equivalence** for single-section docs — the mechanized answer to the gap's "confirm it matches" ask; plus sliding-window/stride layout freeze.
- Fake-tokenizer layer runs everywhere (no 1.1 GB download, uses `chunk_section(tokenizer=)` injection); real-XLM-R layer gated on `is_tokenizer_cached()` (existing house pattern).

**2. Aligned in the backend** — the contract's output now flows to its intended consumer:

- Migration `202607210003`: `m1_regulations.classification_chunk` (Text).
- `preprocess_gazette` persists `pp.classification_chunk` instead of discarding it.
- `classify_gazette` consumes `row.classification_chunk or cleaned_text or raw_text` — pre-migration rows keep the old truncation behaviour via the fallback, so no backfill is required for correctness (re-preprocess backfills naturally).

## Risk note — training-distribution skew (read before trusting new outputs)

Inference input changed (mixed-text head → EN-bucket section head) while the model is unchanged. For most docs the inputs are identical; for mixed/multi-section docs the new input is *closer to what the contract designed* but possibly *further from what the model saw in training*, depending on how the training set was built. **Before relying on Stage-D outputs for mixed-language gazettes:** run `m1/model/eval.py` on the calibration set twice (cleaned_text-head vs classification_chunk input) and compare per-language accuracy. If the delta is negative, revert `classify_gazette` to `cleaned_text` (one-line) and schedule the input switch together with the next retraining cycle instead. This check is deliberately left to a runtime-capable environment.

## Verification (deferred to user)

1. `cd enigmatrix-ml && uv run pytest tests/m1/preprocessing/test_chunk_contract.py -v` (fake-tokenizer layer must pass everywhere; real layer where the tokenizer is cached).
2. Backend: `alembic upgrade head`, `python -m compileall app`, `pytest`.
3. Re-preprocess one mixed-language (EN/SI) gazette → `classification_chunk` populated and ≠ head of `cleaned_text`; re-classify → task log shows it ran; confidence comparable.
4. The eval A/B from the risk note above.
5. `graphify update .`.

## Phase-3 follow-ups

- **Per-chunk classification + aggregation** for multi-notice weekly gazettes (head bias misses tail notices): classify every `section_chunk`, aggregate (max-confidence per category or per-section labels on `m1_sub_documents`). The contract already carries `section_idx`/`window_idx` for exactly this.
- Persist `section_chunks` (JSONB or junction) when the summariser (gap #8 auto-summarize plan) becomes its consumer — `summarise_input()` is its designated entry.
- Fold the eval A/B result into the retraining decision (Phase 5c) — if EN-bucket heads win, rebuild the training set the same way.
