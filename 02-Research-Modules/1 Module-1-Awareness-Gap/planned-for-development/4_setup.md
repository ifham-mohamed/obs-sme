# 4_setup — Step 2d setup + verification guide

> Companion to [4.md](4.md) — user-actionable setup + verification for `m1.extraction.language_detection` + `m1.extraction.wijesekara` + per-page OCR fallback.
> **Status:** ✅ Shipped Session 30 / F-153.

## 1. Deployment context

`enigmatrix-ml` is the workspace member that runs the language router + Wijesekara converter. Production Celery workers (the Fly.io machines that will host Step 2b's `extract_gazette`) need:

- `lid.176.bin` staged at `storage/models/m1/baseline/lid.176.bin` (or wherever `M1_LID_MODEL_PATH` points). 125 MB binary; not git-committed.
- Tesseract 5.3+ system binary + `tesseract-ocr-sin` + `tesseract-ocr-tam` (already in the Step 2c Dockerfile).
- `poppler-utils` for `pdf2image` (already in Step 2c Dockerfile).

Live URLs unchanged from Session 24:
- Backend health: <https://enigmatrix-backend.vercel.app/health>
- Frontend: <https://enigmatrix-frontend.vercel.app/>
- Celery worker: local dev today; Fly.io machine when Step 4a lands.

## 2. Prerequisites

Same as [3_setup.md](3_setup.md) §2 + 3 new Python deps:

| Dep | Why |
|---|---|
| `fasttext-wheel>=0.9.2,<1` | Pre-built fastText wheels (no C++ toolchain needed). |
| `numpy<2.0` | fasttext-wheel 0.9.2 hits a `np.array(probs, copy=False)` ValueError under NumPy 2.x — pin until upstream catches up. |
| `PyYAML>=6,<7` | Loads `wijesekara_map.yaml` at module import time. |

## 3. Download the lid.176.bin model

> **Use `uv run` for every Python invocation.** Bare `python` / `pytest`
> resolve to the system interpreter (e.g. `/usr/bin/python3.14` on Ubuntu
> 24.04) which lacks the project deps (`pytesseract`, `fitz`/PyMuPDF,
> `fasttext-wheel`, `transformers`). `uv run` selects the workspace venv
> built by `uv sync`. `PYTHONPATH=$PWD` is unnecessary because `uv run`
> resolves the `m1` package automatically.

```bash
cd enigmatrix-ml
uv run python scripts/download_lid_model.py --target storage/models/m1/baseline/lid.176.bin
# Or set M1_LID_MODEL_PATH and skip --target:
# M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin uv run python scripts/download_lid_model.py
```

The script is idempotent (skips if the file already exists and is ≥ 100 MB). Expected:

```
Downloading https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin -> .../storage/models/m1/baseline/lid.176.bin
  100.0% — 125.2MB / 125.2MB
Downloaded 125.2MB -> .../storage/models/m1/baseline/lid.176.bin
```

## 4. Run the test suite

```bash
cd enigmatrix-ml
M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin \
  uv run pytest tests/m1/extraction -v
```

Expected: **41 passed, 5 skipped** (DoD-corpus gates + Tesseract-binary gates).

Without the model, the fastText tests skip cleanly:
```bash
uv run pytest tests/m1/extraction/test_language_detection.py -v
# 12 passed / 6 skipped (fastText tests skipped when M1_LID_MODEL_PATH missing).
```

## 5. CLI smoke checks

```bash
cd enigmatrix-ml

# 5a — Language detection on an English string
uv run python -m m1.extraction.language_detection --detect "Hello world this is English"
# primary=en confidence=0.99.. is_mixed=False
#   __label__en: 0.99..
#   __label__de: 0.00..
#   __label__sv: 0.00..

# 5b — Sinhala
uv run python -m m1.extraction.language_detection --detect "ශ්‍රී ලංකා රජයේ අතිවිශේෂ ගැසට් පත්‍රය"
# primary=si confidence=0.99.. is_mixed=False

# 5c — Wijesekara conversion (canonical letter A)
uv run python -m m1.extraction.wijesekara --convert "w"
# අ

# 5d — Wijesekara heuristic detect
uv run python -m m1.extraction.wijesekara --detect "wdwsdfgknfpqhxXLcCwd wkn pPqQ.,;[ ... at least 50 chars ..."
# is_wijesekara_encoded: True
```

## 6. Manual smoke on a real gazette PDF (optional)

```bash
cd enigmatrix-ml
uv run python - <<'EOF'
from pathlib import Path
from m1.extraction import extract_with_chain
result = extract_with_chain(Path("tests/m1/fixtures/sample_gazette_2486_22.pdf"))
print(f"method={result.method} char_count={result.char_count}")
for p in result.per_page:
    print(f"  page {p.page_index}: method={p.method} chars={p.char_count}")
EOF
```

For a text-heavy gazette: all pages report `method='pymupdf'`, `method='pymupdf'` at document level (no OCR fallback fired). For a scanned gazette: low-yield pages flip to `method='tesseract'` and document-level becomes `method='hybrid'`.

## 7. Rollback

```bash
# Code-side rollback (drops the new modules):
cd enigmatrix-ml
git revert d6c571c     # Step 2d commit on Enigmatrixx/enigmatrix-ml@main

# Or rollback only the per-page OCR fallback (keep language + Wijesekara modules):
# Edit text_extractors.extract_with_chain to call with enable_ocr_fallback=False default.
```

The Step 2c surface (`extract_with_chain(pdf_path)`) still works after rollback because the new fallback is opt-in via the keyword arg.

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `FileNotFoundError: fastText model not found at .../lid.176.bin` | Model not downloaded | Re-run `uv run python scripts/download_lid_model.py --target storage/models/m1/baseline/lid.176.bin` |
| `ValueError: Unable to avoid copy while creating an array as requested` | NumPy 2.x installed despite the pin | `pip install "numpy<2.0"` |
| `convert_wijesekara` returns input unchanged | Heuristic returned False → conversion was skipped at the caller level | Check `is_wijesekara_encoded` threshold; lower `WIJESEKARA_THRESHOLD` if working on borderline cases |
| `extract_with_chain` returns `method='pymupdf'` on a clearly scanned PDF | All pages had ≥ 100 chars (PyMuPDF picked up watermarks/headers) | Lower `_MIN_PAGE_CHARS_FOR_PYMUPDF` in `text_extractors.py` |
| HF cache fills the disk | xlm-roberta-base downloaded later in Step 2e (~1.1 GB) | `rm -rf ~/.cache/huggingface/hub/models--xlm-roberta-base/` if Step 2e isn't running yet |

## 9. What's deferred

- **`lid_gold.tsv`** (100 hand-labelled docs for the LID accuracy DoD). Research deliverable.
- **`wijesekara_gold.tsv`** (100 pre-2010 Sinhala docs with hand transcriptions for the conversion DoD). Research deliverable.
- **Production Dockerfile pre-warm of lid.176.bin**. Add `RUN python scripts/download_lid_model.py` to the worker Dockerfile when Fly.io deployment lands.
- **Extended Wijesekara map** (87 → ~200 entries). No-API-change tuning against the DoD corpus.

## 10. Cross-references

- Plan: [4.md](4.md)
- Predecessor setup: [3_setup.md](3_setup.md) (Step 2c)
- Successor setup: [5_setup.md](5_setup.md) (Step 2e)
- Spec: [../10_M1_1_Language_Detection_Routing.md](../10_M1_1_Language_Detection_Routing.md) + [../10_M1_2_OCR_Wijesekara_Conversion.md](../10_M1_2_OCR_Wijesekara_Conversion.md)
- Tracker: F-153 in `c:\sme\08-Findings-Log\FEATURES.md`; Session 30 in `SESSIONS.md`.
