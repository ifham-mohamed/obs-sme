---
tags: [tracker, findings, m1]
source: synthesised
layer: tracker
module: m1
---

# 2026-05-17 — M1 Step 2d: language detection + Wijesekara conversion + per-page OCR fallback

> **Owner:** mohamedifham
> **Module:** m1
> **Type:** session log + experiment + finding

## What I did

- Built `m1/extraction/language_detection.py` with the two-layer detection from [10_M1_1_Language_Detection_Routing.md](../10_M1_1_Language_Detection_Routing.md): fastText `lid.176.bin` document-level (top-3 with 0.70 confidence threshold, 500-char window) + Unicode-range per-line router (`is_sinhala_char` / `is_tamil_char` / `is_latin_char` / `line_language` / `route_lines_by_language` / `primary_language_by_line_count`) from [04_M1_Preprocessing_Pipeline.md §3.2](../04_M1_Preprocessing_Pipeline.md).
- Downloaded `lid.176.bin` (125.2 MB) to `enigmatrix-ml/storage/models/m1/baseline/lid.176.bin` via an idempotent `scripts/download_lid_model.py`. Path matches the verbatim directive `storage/models/m1/baseline/`.
- Built `m1/extraction/wijesekara.py` + 87-entry `wijesekara_map.yaml` per [10_M1_2_OCR_Wijesekara_Conversion.md](../10_M1_2_OCR_Wijesekara_Conversion.md). Heuristic `is_wijesekara_encoded` (0.40 indicator-char ratio, min 50 ASCII-alpha chars) + greedy longest-match `convert_wijesekara` (4→3→2→1 chars; unmapped passes through). Replaced the `wijesekara_to_unicode` `NotImplementedError` stub with a thin delegate.
- Wired per-page OCR fallback into `extract_with_chain` — new signature with `enable_ocr_fallback=True` default. Low-yield pages get rasterised, language-detected, Tesseract'd with the right `--lang`, Wijesekara-converted if heuristic triggers, spliced back as `PageResult(method='tesseract')`. Document-level method becomes `'hybrid'` when any page was OCR'd.
- Wrote 31 new tests (`test_language_detection.py` + `test_wijesekara.py`) and updated 2 existing files (`test_ocr.py` + `test_text_extractors.py`).

## What I found

- **fastText `lid.176.bin` works out of the box for SI/TA detection.** `detect_document_language("ශ්‍රී ලංකා රජයේ අතිවිශේෂ ගැසට් පත්‍රය ...").primary == "si"` with confidence ≥ 0.70 on a synthetic Sinhala paragraph. English detection equally clean.
- **NumPy 2.x breaks `fasttext-wheel` 0.9.2** — `self.f.predict()` returns tuples, the wrapper does `np.array(probs, copy=False)` which raises `ValueError` under NumPy 2.x. Pinned `numpy<2.0` until upstream catches up.
- **87 Wijesekara map entries cover the spec-canonical core.** All independent vowels (අ–ඖ), all 5 consonant series (velar/palatal/retroflex/dental/labial), all vowel signs, special marks, and 12 high-frequency conjuncts. Unmapped chars pass through — extending coverage is no-API-change tuning against the 100-doc DoD corpus.
- **41/41 extraction tests pass.** 5 intentional skips (4 DoD harnesses + 1 Tesseract-binary-gated smoke). The new fallback test monkeypatches `pdf2image.convert_from_path` + `m1.extraction.ocr._ocr_one_page` so it runs without Tesseract installed.
- **Greedy match works correctly on compound vowels.** `convert_wijesekara("wd!")` returns `ඈ` (long-ae compound) rather than `ආ`+`!` (3-char key wins over 2-char prefix + 1-char remainder).

## What changed in the repo

| File | Change |
|---|---|
| `enigmatrix-ml/pyproject.toml` | +3 deps: `fasttext-wheel>=0.9.2,<1`, `numpy<2.0`, `PyYAML>=6,<7` |
| `enigmatrix-ml/scripts/download_lid_model.py` | NEW — idempotent download with size-verify and progress bar |
| `enigmatrix-ml/m1/extraction/language_detection.py` | NEW — fastText document detection + Unicode-range per-line router; CLI for DoD measurement |
| `enigmatrix-ml/m1/extraction/wijesekara.py` | NEW — heuristic detection + greedy longest-match conversion; CLI for detect/convert/measure-accuracy |
| `enigmatrix-ml/m1/extraction/wijesekara_map.yaml` | NEW — 87 canonical Wijesekara → Unicode mappings |
| `enigmatrix-ml/m1/extraction/ocr.py` | Removed `NotImplementedError` stub; `wijesekara_to_unicode` now delegates to `convert_wijesekara` |
| `enigmatrix-ml/m1/extraction/text_extractors.py` | `extract_with_chain` signature gains `enable_ocr_fallback`/`ocr_dpi`/`ocr_timeout`; wires per-page OCR fallback |
| `enigmatrix-ml/m1/extraction/__init__.py` | Re-exports the new public surface alongside Step 2c |
| `enigmatrix-ml/tests/m1/extraction/test_ocr.py` | Replaced stub-raise test with re-export round-trip test |
| `enigmatrix-ml/tests/m1/extraction/test_text_extractors.py` | Split into `_no_fallback` + `_invokes_tesseract` (monkeypatched) |
| `enigmatrix-ml/tests/m1/extraction/test_language_detection.py` | NEW — 17 tests (per-line router + fastText, model-gated) |
| `enigmatrix-ml/tests/m1/extraction/test_wijesekara.py` | NEW — 14 tests (map loading + heuristic + greedy conversion + DoD harness) |
| `enigmatrix-ml/storage/models/m1/baseline/lid.176.bin` | NEW (artifact, 125.2 MB — needs `.gitignore`) |

## What's next

- [ ] Populate `enigmatrix-ml/tests/m1/fixtures/lid_gold.tsv` (100 hand-labelled docs) → DoD: ≥ 95% accuracy
- [ ] Populate `enigmatrix-ml/tests/m1/fixtures/wijesekara_gold.tsv` (100 pre-2010 Sinhala docs with hand transcriptions) → DoD: ≥ 95% character-level accuracy
- [ ] Add `storage/models/` to repo-root `.gitignore` (lid.176.bin must not be committed)
- [ ] Lift `numpy<2.0` pin when `fasttext-wheel` 0.9.3+ ships with NumPy 2 compatibility
- [ ] Extend Wijesekara map from 87 → ~200 entries when accuracy < 95% on the DoD corpus (no API change required — tuning only)
- [ ] CI: pin `tesseract-ocr=5.3.*` so the per-page fallback path is exercised in integration tests, not just monkeypatched

## Blockers

None — Step 2d is complete with apparatus in place. The DoD datasets are research deliverables that follow the same fixture-gated pattern as Step 2c's 50-doc audit.

## Cross-references

- Related session: [Session 30 — 2026-05-17](../../../08-Findings-Log/SESSIONS.md)
- Predecessor: [Session 28 / F-149 — Step 2c canonical extraction chain](../../../08-Findings-Log/SESSIONS.md) (Wijesekara stub + per-page OCR fallback explicitly deferred to Step 2d in Session 28's "Risks / open follow-ups")
- Spec docs: [10_M1_1_Language_Detection_Routing](../10_M1_1_Language_Detection_Routing.md), [10_M1_2_OCR_Wijesekara_Conversion](../10_M1_2_OCR_Wijesekara_Conversion.md), [04_M1_Preprocessing_Pipeline §3.2](../04_M1_Preprocessing_Pipeline.md)
- Related: [03_M1_1_PDF_Extraction_Chain](../03_M1_1_PDF_Extraction_Chain.md) (PyMuPDF/pdfplumber/Tesseract chain that this hooks into)
- Feature: F-153 in [FEATURES](../../../08-Findings-Log/FEATURES.md)