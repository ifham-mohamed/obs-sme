---
tags: [tracker, m1, local-dev, phase2, step-2d]
source: synthesised
layer: tracker
module: m1
---

# Phase 2 Step 2d — fastText language detection + Wijesekara + per-page OCR fallback (local dev)

> **Shipped:** Session 30 / F-153.
> **Spec**: [planned-for-development/4_setup.md](../planned-for-development/4_setup.md) · [10_M1_1_Language_Detection_Routing](../10_M1_1_Language_Detection_Routing.md) · [10_M1_2_OCR_Wijesekara_Conversion](../10_M1_2_OCR_Wijesekara_Conversion.md).

## 1 · What this step does

Three deliverables:

1. **fastText document-level language detection** at `m1/extraction/language_detection.py` (500-char window, 0.70 confidence threshold, top-3 prediction; primary ∈ `{en, si, ta, mixed}`).
2. **Per-line Unicode-range router** in the same file (`is_sinhala_char`, `is_tamil_char`, `is_latin_char`, `line_language`, `route_lines_by_language`, `primary_language_by_line_count`) per doc-04 §3.2.
3. **Wijesekara → Unicode conversion** at `m1/extraction/wijesekara.py` (87-entry mapping table + 0.40 indicator-char ratio heuristic + greedy longest-match converter). Replaces the Step 2c stub.
4. **Per-page OCR fallback wiring** in `extract_with_chain` — low-yield PyMuPDF pages get rasterised, language-routed, Tesseract'd, Wijesekara-converted.

## 2 · Prerequisites

- Step 2c passing.
- `fasttext-wheel`, `numpy<2`, `PyYAML` installed (handled by `uv sync`).
- `lid.176.bin` (125 MB) staged at `storage/models/m1/baseline/lid.176.bin`.

```bash
cd ~/repos/xyz
uv sync   # ensures fasttext-wheel + numpy<2 pin
```

## 3 · Download the fastText model

```bash
cd ~/repos/xyz/enigmatrix-ml
uv run python scripts/download_lid_model.py --target storage/models/m1/baseline/lid.176.bin
```

> **Note**: bare `python`/`pytest` resolve to the system interpreter on
> Ubuntu 24.04 and lack the project deps (`pytesseract`, `fitz`/PyMuPDF,
> `fasttext-wheel`, …). All invocations below use `uv run` to select the
> workspace venv produced by `uv sync`.

Idempotent. Re-runs skip when the file exists with size ≥ 100 MB.

Verify:

```bash
ls -la storage/models/m1/baseline/lid.176.bin   # ~125 MB
```

## 4 · Run the Step 2d tests

```bash
cd ~/repos/xyz/enigmatrix-ml
M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin uv run pytest tests/m1/extraction -v
```

Expected: **41 passed / 5 skipped** (the 31 new Step 2d tests + Step 2c's 12 regression tests):

- `tests/m1/extraction/test_language_detection.py` — 17 tests covering per-line router (no model needed) + fastText detection (gated on `M1_LID_MODEL_PATH`).
- `tests/m1/extraction/test_wijesekara.py` — 14 tests covering heuristic + greedy conversion + map loading.
- `tests/m1/extraction/test_ocr.py` — updated for the Wijesekara delegate (stub-raises test replaced by re-export round-trip).
- `tests/m1/extraction/test_text_extractors.py` — split into `_no_fallback` + `_invokes_tesseract` (Step 2d's per-page OCR fallback wiring).

The 5 skips are:
- 1 Tesseract-binary-gated smoke (skips if `tesseract` not on PATH — should pass after [00_LOCAL_DEV_HANDBOOK §1.3](../../../04-Technology-Stack/00_LOCAL_DEV_HANDBOOK.md)).
- 2 DoD harnesses (LID gold corpus + Wijesekara gold corpus — research deliverables, see §6).
- 2 inherited from Step 2c (50-doc audit calibration + OCR CER DoD).

## 5 · CLI smoke checks

### 5.1 Document-level language detection

```bash
M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin \
  uv run python -m m1.extraction.language_detection --detect "Hello world this is English text"
# primary=en confidence=0.99.. is_mixed=False
#   __label__en: 0.99..
```

```bash
M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin \
  uv run python -m m1.extraction.language_detection --detect "ශ්‍රී ලංකා රජයේ අතිවිශේෂ ගැසට් පත්‍රය"
# primary=si confidence=0.99.. is_mixed=False
```

### 5.2 Wijesekara conversion

```bash
uv run python -m m1.extraction.wijesekara --convert "w"        # අ
uv run python -m m1.extraction.wijesekara --convert "wd"       # ආ
uv run python -m m1.extraction.wijesekara --convert "wd!"      # ඈ (greedy 3-char wins)
```

### 5.3 Wijesekara heuristic (≥ 50 ASCII-alpha chars required)

```bash
uv run python -m m1.extraction.wijesekara --detect "$(printf 'wdwsdfgknfpqhxXLcCwdwknpPqQ,;[%.0s' {1..3})"
# is_wijesekara_encoded: True
```

### 5.4 Per-line router (Python REPL)

```bash
uv run python - <<'EOF'
from m1.extraction import line_language, route_lines_by_language

print(line_language("The Gazette of Sri Lanka"))           # en
print(line_language("ක්‍රමවේදය යනු සිංහල භාෂාව"))         # si
print(line_language("தமிழ் மொழியின் சில எழுத்துக்கள்"))   # ta

text = """The Gazette of Sri Lanka
ක්‍රමවේදය යනු සිංහල භාෂාව
தமிழ் மொழியின் சில எழுத்துக்கள்"""
print(route_lines_by_language(text))
# {'en': 'The Gazette of Sri Lanka', 'si': '...', 'ta': '...'}
EOF
```

## 6 · DoD harnesses (corpus-gated)

```bash
# Language detection accuracy ≥ 95% on 100 hand-labelled docs
M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin \
  uv run python -m m1.extraction.language_detection --measure-accuracy tests/m1/fixtures/lid_gold.tsv
# Exits 0 iff accuracy ≥ 0.95

# Wijesekara character-level accuracy ≥ 95% on 100 pre-2010 Sinhala docs
uv run python -m m1.extraction.wijesekara --measure-accuracy tests/m1/fixtures/wijesekara_gold.tsv
```

Both gated on hand-labelled corpora that ship separately (research deliverable).

## 7 · Per-page OCR fallback smoke (end-to-end on a PDF)

```bash
M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin uv run python - <<'EOF'
from m1.extraction import extract_with_chain
result = extract_with_chain("tests/m1/fixtures/sample_gazette_2486_22.pdf")
print(f"method={result.method} char_count={result.char_count}")
for p in result.per_page:
    print(f"  page {p.page_index}: method={p.method} chars={p.char_count}")
EOF
```

For a text-heavy PDF: all pages `method='pymupdf'`, document-level method `pymupdf`. For a scanned PDF: low-yield pages flip to `method='tesseract'` and document-level becomes `hybrid`.

## 8 · Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ValueError: Unable to avoid copy while creating an array as requested` | NumPy 2.x + fasttext-wheel | pyproject pins `numpy<2.0`; re-run `uv sync` |
| `FileNotFoundError: fastText model not found at ...` | Model not downloaded | `uv run python scripts/download_lid_model.py --target storage/models/m1/baseline/lid.176.bin` |
| `ModuleNotFoundError: No module named 'pytesseract' / 'fitz'` during `pytest …` | Bare `pytest` ran on the system Python interpreter | Use `uv run pytest …` so the workspace venv (with project deps) is used |
| `Command 'python' not found` | Ubuntu 24.04 has no `python` symlink | Use `uv run python …` or run `sudo apt install python-is-python3` once |
| All fastText-gated tests skip | `M1_LID_MODEL_PATH` env var not set | `export M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin` |
| `convert_wijesekara` returns input unchanged | Heuristic returned False → caller skipped conversion | Lower `WIJESEKARA_THRESHOLD` (default 0.40) for borderline cases |
| `extract_with_chain` returns `method='pymupdf'` on clearly scanned PDF | All pages had ≥ 100 chars (watermarks/headers) | Lower `_MIN_PAGE_CHARS_FOR_PYMUPDF` in `text_extractors.py` |

## 9 · After verifying

```powershell
graphify update C:\Reasearch\xyz
```

## 10 · Cross-references

- [planned-for-development/4_setup.md](../planned-for-development/4_setup.md) — Step 2d setup spec
- [phase2_step2c_extraction_chain](phase2_step2c_extraction_chain.md) — predecessor
- [phase2_step2e_preprocessing](phase2_step2e_preprocessing.md) — successor (consumes the cleaned + routed text)
- [10_M1_1_Language_Detection_Routing](../10_M1_1_Language_Detection_Routing.md)
- [10_M1_2_OCR_Wijesekara_Conversion](../10_M1_2_OCR_Wijesekara_Conversion.md)