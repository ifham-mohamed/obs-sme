# Module 1 — Phase 2 §9.8: Trilingual Extraction Gaps — Font-Aware Auto-Chain + Rest

> Companion to [[PHASE2_INGEST_EXTRACTION_ANALYSIS]] §9.8 and [[PHASE2_GAP_CLOSURE_PLAN]] §9.8.1. **Status: §9.8.1 implemented (Session 69, 2026-07-21)** — the highest-impact Phase-2 gap. §9.8.5 was closed in Session 66 ([[PHASE2_RUNTIME_DEPS_PLAN]]). §9.8.2/3/4 planned below.

---

## §9.8.1 — Auto-chain is now font-aware ✅ IMPLEMENTED

### Problem

The Slice-7 font-aware Sinhala fix (`wijesekara_routing_v1`: per-span legacy-font detection → per-font conversion tables → CID 4800→0 on the reference doc) lived only in the **manual profile path**. The automatic chain (`extract_gazette`, what Beat-driven ingestion runs) used the plain backend extractors — so **every routinely scraped pre-2010 SI gazette landed garbled** and stayed garbled until someone manually re-extracted it through a profile.

### Design: the profile IS the auto-chain, with a hard fallback guarantee

- **`M1_DEFAULT_EXTRACTION_PROFILE`** setting (default `wijesekara_routing_v1`, env-overridable, `""` = legacy chain). Rollback is an env change, no deploy.
- `extract_gazette` now tries the profile **first**: bytes → `NamedTemporaryFile` (the profile API takes paths — fitz + pdfplumber page engines open by path) → `PROFILE_REGISTRY[name]().extract()`. Uses the ml registry **directly**, not the backend's `load_profile` dispatcher — that one is DB-seeded + raises `HTTPException`, both wrong for a worker hot path.
- **Any** profile failure (ml package missing, registry typo, fitz error) logs a warning and falls through to the untouched legacy `classify_pdf → pymupdf/pdfplumber/tesseract` block. The invariant: **the auto-chain can never be less reliable than pre-§9.8.1** — worst case is exactly the old behaviour.
- `extraction_method` now records the profile name (migration `202607210004`: String(20)→String(40), CHECK enum widened to include the four profile names) — so profile-vs-legacy provenance is queryable per row.
- The profile's quality evidence (`wijesekara_applied`, `cid_marker_count_before/after`) is logged per row and surfaced in the Celery task result.
- **Watchdog**: the monthly quality probe ([[PHASE2_QUALITY_MONITORING_PLAN]]) gains `profile_share` — the fraction of window rows extracted via the default profile. A drift-down alert means the profile is silently falling back to the legacy chain (SI/TA regressing with zero task failures). Direction-aware in `_detect_degradation`.

### Notes / conscious trade-offs

- The profile internally runs `preprocess_gazette` to fill its `fields` — the auto-chain **discards** those and keeps only `raw_text` + signals; the chained `preprocess_gazette_task` remains the single writer of cleaned_text/metadata/penalties/`classification_chunk` (Sessions 67–68 work stays authoritative). Slightly duplicated compute, zero duplicated writes.
- Profile extraction is slower than the plain chain (multi-engine consensus per text page). Acceptable at gazette volumes; the extraction-runs UI already shows durations if it becomes a problem.
- Temp-file round-trip is required by the profile API today; an ml-side `extract_bytes()` overload is a nice-to-have (needs ML_GIT_REF bump).

### Backfill + verification (deferred to user)

1. `alembic upgrade head`; `python -m compileall app`; `pytest`.
2. Re-ingest the reference doc (`2468/44`) through the **auto** chain → log line shows `cid_before≈4800 → cid_after=0`, `extraction_method='wijesekara_routing_v1'`.
3. EN regression: extract 3 known-good EN gazettes → text substantively identical to legacy output (consensus rule may differ in whitespace).
4. **Backfill garbled rows**: admin bulk re-extraction (existing scoped-run UI) over rows where `extraction_method IN ('pymupdf','pdfplumber','tesseract') AND language='sin'` — those predate the font-aware chain.
5. Confirm rollback: set `M1_DEFAULT_EXTRACTION_PROFILE=""` → next extraction logs the legacy method.
6. `graphify update .`

---

## §9.8.2 — Surya stub (PLAN, Phase 3 as designed)

Stays deferred (GPU-gated). Already **visible** since Session 66: the health check reports `surya: stub` at worker boot, `/admin/m1/pipeline/health`, and container start — nobody can assume the fallback exists. When Phase 3 lands it: install extra + weights check into `health.py`'s required set, activate `surya_fallback_v1` via the existing profile-activation endpoint, and route only `scanned`+SI/TA pages to it (Tesseract stays the CPU default). Gate: CER ≤10% on the scanned-SI calibration stratum, measured via the existing measurement engine.

## §9.8.3 — Unknown fonts silently fall back (PLAN + partial follow-through)

Now partially covered: `profile_share` (above) catches the *chain-level* silent fallback. The *font-level* one — an unknown legacy font hitting the canonical map — still needs the slice-7.3 instrumentation to be **watched**, not just emitted:

1. ml-side (needs ML_GIT_REF bump): `_extract_pymupdf_page_font_aware` collects span fonts where `is_wijesekara_encoded(text)` is true but `is_legacy_font(font)` is false → add `unknown_suspect_fonts: [names]` to `error_signals`.
2. Backend: `extract_gazette` logs them; quality probe aggregates distinct names per window into `metrics`.
3. Process: a new name appearing = add a per-font YAML to `wijesekara_maps/` → ship `wijesekara_routing_v1.1` → bump registry + CHECK enum.

## §9.8.4 — Legacy Tamil fonts (PLAN — audit first, build only if real)

The Wijesekara machinery is Sinhala-specific; Tamil relies on Unicode + Tesseract `tam`. Whether legacy Tamil encodings (Bamini/Baamini families) exist in the corpus is an **empirical question — answer it before building**:

1. Query: TA rows (`language='tam'`) with high CID counts or low Tamil-Unicode-range ratio in `raw_text` (same indicator logic as `is_wijesekara_encoded`, Tamil ranges `U+0B80–0BFF`).
2. Sample 20 pre-2010 TA gazettes; eyeball the flagged ones.
3. If legacy encodings appear: replicate `font_aware_wijesekara` with Tamil maps (`tamil_maps/`, `is_legacy_tamil_font`, per-font YAML) inside the same profile — the per-span routing loop is already font-generic.
4. If not: close the gap as "not present in corpus", with the audit query + sample as evidence in this doc.

## §9.8.5 — `lid.176.bin` ✅ closed Session 66 — see [[PHASE2_RUNTIME_DEPS_PLAN]]
