---
tags: [tracker, m1, local-dev, phase2, step-2c]
source: synthesised
layer: tracker
module: m1
---

# Phase 2 Step 2c — Canonical `ml/m1/extraction/` chain (local dev)

> **Shipped:** Session 28 / F-149 (extraction chain moved to its canonical home + research-grade rigour added).
> **Spec**: [planned-for-development/3_setup.md](../planned-for-development/3_setup.md) · [03_M1_1_PDF_Extraction_Chain](../03_M1_1_PDF_Extraction_Chain.md).

## 1 · What this step does

Promotes the Session-26 Step 2b runtime MVP from `enigmatrix-backend/app/extraction/` to its canonical home at `enigmatrix-ml/m1/extraction/`. The backend `app/extraction/` becomes a thin re-export adapter — `from app.extraction import classify_pdf, ...` still works, but resolves through `from m1.extraction import ...`. Adds threshold-calibration harness + CER calculator + per-page hybrid routing + Tesseract 5.3.x full flag set.

## 2 · Prerequisites

- Steps 2a + 2b passing.
- `enigmatrix-ml/` workspace member of the root `pyproject.toml`.
- `uv sync` from the repo root has installed both backend + ml.
- Tesseract 5.3+ on PATH (`tesseract --version`).
- poppler on PATH (`pdftoppm --version`).

```bash
cd ~/repos/xyz
uv sync   # ensures workspace is in sync
```

## 3 · Run the ml extraction tests

> **Use `uv run` for every Python invocation.** Bare `pytest` / `python`
> resolve to the system interpreter (e.g. `/usr/bin/python3.14` on Ubuntu
> 24.04) which lacks the project deps (`pytesseract`, `fitz`/PyMuPDF,
> `fasttext-wheel`). `uv run` selects the workspace venv built by
> `uv sync`; `PYTHONPATH=$PWD` is unnecessary because `uv run` resolves
> the `m1` package automatically.

```bash
cd ~/repos/xyz/enigmatrix-ml
uv run pytest tests/m1/extraction -v
```

Expected (per Session 28 baseline; Step 2d/Session-34 add more):
- **12 passed, 2 skipped** for the Step 2c slice alone (`test_pdf_classifier.py`, `test_text_extractors.py`, `test_ocr.py` selectively).
- Full extraction-tests count after Step 2d + Session 34: **55 passed / 6 skipped**.

The 2 intentional skips are:
- 50-doc audit-set calibration (`test_calibration_50_doc_audit_set` skipped without `tests/m1/fixtures/audit/` corpus).
- OCR CER DoD (`test_ocr_cer_dod_skipped_without_gold` skipped without `tests/m1/fixtures/ocr_gold/`).

## 4 · Run the backend regression (proves re-export adapter is byte-stable)

```bash
cd ~/repos/xyz/enigmatrix-backend
uv run pytest app/tests/unit/test_pdf_classifier.py \
              app/tests/unit/test_text_extractors.py \
              app/tests/unit/test_gazette_scraper_task.py -v
```

Expected: **6 passed**. Confirms `from app.extraction import classify_pdf` still resolves correctly through the re-export adapter at `enigmatrix-backend/app/extraction/__init__.py`.

## 5 · Threshold calibration CLI (research-grade DoD harness)

The `_threshold_calibration(audit_dir)` runs 5 candidate threshold pairs over a 50-doc hand-labelled audit set and emits a confusion matrix:

```bash
cd ~/repos/xyz/enigmatrix-ml
uv run python -m m1.extraction.pdf_classifier --calibrate tests/m1/fixtures/audit/
```

Without the corpus you'll see:

```
[calibration] audit_dir ./tests/m1/fixtures/audit/ is empty or missing.
[calibration] Populate per 3_setup.md §6 (50 hand-labelled PDFs).
```

Populate the fixture per [planned-for-development/3_setup.md §6](../planned-for-development/3_setup.md) when you have the corpus assembled.

## 6 · CER measurement CLI

For OCR accuracy on hand-transcribed gold text:

```bash
uv run python -m m1.extraction.ocr --measure-cer pred.txt gold.txt
# CER(pred.txt vs gold.txt) = 0.0741
```

CER target per spec: **≤ 10% (0.10)** on the Sinhala/Tamil OCR-gold corpus (when populated).

## 7 · CLI smoke: classify a single PDF

```bash
uv run python -c "
from m1.extraction import classify_pdf
result = classify_pdf('tests/m1/fixtures/sample_gazette_2486_22.pdf')
print(f'PDF type: {result}')   # text_pdf | hybrid | scanned
"
```

## 8 · Verify the public surface

```bash
cd ~/repos/xyz/enigmatrix-ml
uv run python -c "
from m1.extraction import (
    classify_pdf,
    extract_pymupdf, extract_pdfplumber, extract_tesseract,
    extract_with_chain, extract_tesseract_full,
    character_error_rate, wijesekara_to_unicode,
    ExtractedText, PageResult,
)
print('All Step 2c exports importable')
"
```

Backend re-export still works:

```bash
cd ~/repos/xyz/enigmatrix-backend
uv run python -c "
from app.extraction import classify_pdf, extract_pymupdf
print('Backend re-export resolves through m1.extraction')
"
```

## 9 · Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ImportError: m1.extraction` | Workspace not synced | `cd ~/repos/xyz && uv sync` |
| `ModuleNotFoundError: m1` from backend | Workspace dep not registered | Verify `enigmatrix-backend/pyproject.toml` has `enigmatrix-ml` in `dependencies` |
| `classify_pdf` returns dict instead of literal | Pre-Session-28 import path | Restart shell + verify `enigmatrix-backend/app/extraction/__init__.py` is the adapter, NOT the old standalone |
| `tesseract: command not found` | apt deps missing | `sudo apt install tesseract-ocr tesseract-ocr-sin tesseract-ocr-tam` |
| `pdf2image fails: poppler not found` | apt deps missing | `sudo apt install poppler-utils` |
| 50-doc calibration always skipped | Corpus not populated | Expected — research deliverable; see `3_setup.md` §6 |

## 10 · After verifying

```powershell
graphify update C:\Reasearch\xyz
```

## 11 · Cross-references

- [planned-for-development/3_setup.md](../planned-for-development/3_setup.md) — Step 2c full setup spec
- [phase2_step2b_celery_extract](phase2_step2b_celery_extract.md) — predecessor (runtime MVP)
- [phase2_step2d_language_wijesekara](phase2_step2d_language_wijesekara.md) — successor (lang detect + Wijesekara)
- [03_M1_1_PDF_Extraction_Chain](../03_M1_1_PDF_Extraction_Chain.md) — full extraction spec