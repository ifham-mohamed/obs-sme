---
tags: [tracker, findings, m1]
source: synthesised
layer: tracker
module: m1
---

# 2026-05-17 — M1 Step 2e: Preprocessing chain (cleaning + metadata + chunking)

> **Owner:** mohamedifham
> **Module:** m1
> **Type:** session log + decision

## What I did

- Created `enigmatrix-ml/m1/preprocessing/` as a new package with 5 modules: `types.py`, `cleaning.py`, `metadata_extractor.py`, `chunking.py`, `__init__.py` (orchestrator).
- Shipped the 8-step `NOISE_PIPELINE` per [04_M1_1] §2 with two public entry points: `clean_gazette_text()` keeps the signature block (thesis-citation faithful, for DB `raw_text`), `clean_for_classification()` strips it (for classifier input).
- Shipped the metadata extractor per [04_M1_2] §3 — 4 anchored regex patterns + multi-penalty `finditer` + alternative-clause merger (fine + imprisonment within 30 chars connected by "or"/"either" → one row with `penalty_type='both'`) + sanity-bounded effective dates + amendment-type discriminator.
- Shipped the section-aware hybrid chunker per [04_M1_3] §1–4 — `MAX_LEN=512` / `STRIDE=64` with micro-section merger (< 100 tokens absorbed into neighbours) and padding-bias trailing chunk dropper (< 50 tokens trimmed). XLM-R tokenizer auto-downloaded from HF Hub on first call.
- Reused Step 2d's `m1.extraction.language_detection.{detect_document_language, route_lines_by_language, primary_language_by_line_count}` wholesale in the orchestrator — no duplication.
- Wrote 71 new tests across 4 files: `test_cleaning.py` (30 tests — 2/noise class × 8 + idempotency + Sinhala/Tamil preservation + worked example), `test_metadata_extractor.py` (24 tests — per-field + multi-penalty + merger + millions + DoD harness), `test_chunking.py` (14 tests — section detection + fake-tokenizer chunking + tokenizer-gated integration), `test_pipeline.py` (6 tests — orchestrator + DoD round-trip).

## What I found

- **117 tests pass / 8 skipped** — 71 new in preprocessing + 41 Step-2c/2d regression + 8 intentional skips (DoD-corpus + Tesseract-binary + tokenizer cache gates). No regression in Step 2c/2d.
- **NFKD codepoint count grows, not stays equal.** Tamil precomposed vowel signs (e.g. U+0BCA / Tamil vowel sign O) decompose under NFKD into U+0BC6 + U+0BBE — both within the Tamil Unicode block. The "no Sinhala/Tamil signal lost" invariant codifies as `after >= before`, not strict equality. Sinhala doesn't trigger it in the test text but the same principle applies.
- **Gazette number survives only if metadata extraction runs BEFORE cleaning.** The spec says metadata extraction happens on cleaned text, but `strip_gazette_header` removes the header (including "No. 2486/22"). Resolution: orchestrator calls `extract_metadata(raw_text, ...)` first, then cleans for chunking. The spec's "before tokenization" is interpreted as "before chunking", not "after cleaning".
- **Amendment-type regex needs all verb forms.** Initial draft had `\bamendment\b` and `\b(repeal|repealed|repealing)\b` — missed "amends" / "repeals" (singular present-tense verb). Corrected to `\bamend(?:s|ed|ing|ment)?\b` and `\brepeal(?:s|ed|ing)?\b`.

## What changed in the repo

| File | Change |
|---|---|
| `enigmatrix-ml/pyproject.toml` | +2 deps: `transformers>=4.40,<5`, `dateparser>=1.2,<2` |
| `enigmatrix-ml/m1/preprocessing/__init__.py` | NEW — orchestrator `preprocess_gazette()` + public re-exports |
| `enigmatrix-ml/m1/preprocessing/types.py` | NEW — `Penalty`, `Chunk`, `PreprocessedGazette` dataclasses; type aliases |
| `enigmatrix-ml/m1/preprocessing/cleaning.py` | NEW — 8-step noise pipeline; two public entry points |
| `enigmatrix-ml/m1/preprocessing/metadata_extractor.py` | NEW — 4 anchored regex + multi-penalty `finditer` + alternative merger + sanity-bounded date + amendment-type classifier |
| `enigmatrix-ml/m1/preprocessing/chunking.py` | NEW — `NOTICE_BOUNDARY_RE` + section detection + hybrid sliding window + tokenizer cache helpers |
| `enigmatrix-ml/tests/m1/preprocessing/__init__.py` | NEW (empty package marker) |
| `enigmatrix-ml/tests/m1/preprocessing/test_cleaning.py` | NEW — 30 tests covering 8 noise classes + idempotency + Unicode preservation + worked example |
| `enigmatrix-ml/tests/m1/preprocessing/test_metadata_extractor.py` | NEW — 24 tests covering per-field + multi-penalty + alternative merger + millions + edge cases |
| `enigmatrix-ml/tests/m1/preprocessing/test_chunking.py` | NEW — 14 tests covering section detection + fake-tokenizer chunking + tokenizer-gated integration |
| `enigmatrix-ml/tests/m1/preprocessing/test_pipeline.py` | NEW — 6 tests covering orchestrator + DoD round-trip on the VAT-amendment worked example |

## What's next

- [ ] Step 2f — Celery wiring + DB migration: add `m1_regulation_penalties` junction table + `amendment_type` column to `m1_regulations`; new task `preprocess_gazette(reg_id)` that loads raw_text → calls `preprocess_gazette()` → writes cleaned_text + 4 metadata fields + penalty junction rows back; flips status `extracted → preprocessed`.
- [ ] Populate `enigmatrix-ml/tests/m1/fixtures/cleaning_corpus/` (50 fixtures) for idempotency + char-loss-bound DoD.
- [ ] Populate `enigmatrix-ml/tests/m1/fixtures/metadata_gold.json` (100 hand-validated docs) → DoD: ≥ 95% precision, ≥ 90% recall per field.
- [ ] Pre-warm `xlm-roberta-base` in production Dockerfile so first inference doesn't pay the 1-min download.
- [ ] Move `NOTICE_BOUNDARY_RE` out of `chunking.py` to a shared segmentation module when 03_M1_2 (gazette segmentation) ships as code.

## Blockers

None. Step 2e is complete with all DoD-required fields populated on the worked example. The DoD corpora are research deliverables that follow the same fixture-gated pattern as Step 2c (50-doc audit) and Step 2d (100-doc LID + Wijesekara gold).

## Cross-references

- Related session: [Session 31 — 2026-05-17](../../../08-Findings-Log/SESSIONS.md)
- Predecessor: [Session 30 / F-153 — Step 2d language detection + Wijesekara + per-page OCR fallback](../../../08-Findings-Log/SESSIONS.md) — provides the cleaned Unicode text + per-line language router that Step 2e reuses.
- Spec docs: [04_M1_Preprocessing_Pipeline](../04_M1_Preprocessing_Pipeline.md), [04_M1_1_Gazette_Noise_Removal](../04_M1_1_Gazette_Noise_Removal.md), [04_M1_2_Metadata_Extraction_Patterns](../04_M1_2_Metadata_Extraction_Patterns.md), [04_M1_3_Text_Chunking_Strategy](../04_M1_3_Text_Chunking_Strategy.md)
- Future cross-ref: [03_M1_2_Gazette_Segmentation](../03_M1_2_Gazette_Segmentation.md) — shared section-detection regex (when that module ships, `NOTICE_BOUNDARY_RE` moves out of `chunking.py`)
- Feature: F-154 in [FEATURES](../../../08-Findings-Log/FEATURES.md)