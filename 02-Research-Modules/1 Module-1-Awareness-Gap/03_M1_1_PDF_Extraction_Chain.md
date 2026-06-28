# 03_M1_1 — PDF Extraction Chain (deep dive)

> Companion to [03_M1_Data_Collection.md](03_M1_Data_Collection.md) — `classify_pdf()` deep-dive, threshold-calibration procedure, per-PDF-type examples, full Tesseract 5.3.x config.
> **Implementation status:** ✅ Shipped Session 28 / F-149 (Step 2c — `ml/m1/extraction/{pdf_classifier,text_extractors,ocr}.py` — PyMuPDF / pdfplumber / Tesseract chain with `classify_pdf()` router; threshold calibration harness + CER calculator). Per-page OCR fallback wired in Session 30 / F-153 (Step 2d).

## Purpose

The parent doc shows `classify_pdf()` (§2.4) and the three-stage chain (PyMuPDF → pdfplumber → Tesseract). This companion details the *operational* corners: what each PDF type looks like, exactly how Tesseract is configured (full flag set + Docker pin), and how to *recalibrate* the thresholds when a new gazette typesetting standard appears.

## Detailed process

### Step 1 — `classify_pdf()` returns one of three labels

The function emits `text_pdf | hybrid | scanned`. The chain branches on the label:

- `text_pdf` → PyMuPDF only (fast, ~80 ms/page).
- `hybrid` → PyMuPDF for pages with text + Tesseract for the rest (per-page decision).
- `scanned` → `pdf2image` → Tesseract on every page (slow, ~3 s/page).

### Step 2 — Threshold calibration procedure

Run **quarterly** (after any change to PDF-extraction libraries or to the Tesseract version):

1. Hand-label 50 gazettes as `text_pdf / hybrid / scanned`.
2. For each candidate threshold pair `(text_thresh, scanned_thresh)` in `{(150,25), (180,30), (200,30), (220,35), (250,40)}`:
   - Run `classify_pdf()` with that pair.
   - Compute confusion matrix vs hand labels.
3. Pick the pair maximising `min(text_pdf_recall, scanned_precision)`.
4. Write the chosen pair to `storage/models/m1/v<X>/model_registry.json:classify_pdf_thresholds`.
5. Update the Postgres-side env vars `M1_PDF_TEXT_THRESHOLD` and `M1_PDF_SCANNED_THRESHOLD`.

The parent doc's table (§2.4) is the result of this procedure on the current corpus; the chosen pair is `(200, 30)`.

### Step 3 — PyMuPDF extraction (text-PDF path)

```python
import fitz
def extract_with_pymupdf(path: str) -> ExtractedText:
    doc = fitz.open(path)
    pages = [page.get_text("text", flags=fitz.TEXTFLAGS_TEXT) for page in doc]
    doc.close()
    return ExtractedText(text="\n".join(pages), method="pymupdf",
                         char_count=sum(len(p) for p in pages))
```

`TEXTFLAGS_TEXT` excludes vector ligatures (preserves Sinhala/Tamil glyphs that ligature-mode collapses). Adds ~3 % runtime.

### Step 4 — pdfplumber fallback (hybrid path)

```python
import pdfplumber
def extract_with_pdfplumber(path: str) -> ExtractedText:
    with pdfplumber.open(path) as pdf:
        chunks = []
        for page in pdf.pages:
            text = page.extract_text(layout=True) or ""
            tables = page.extract_tables() or []
            for table in tables:
                chunks.append("\n".join("\t".join(cell or "" for cell in row) for row in table))
            chunks.append(text)
    return ExtractedText(text="\n".join(chunks), method="pdfplumber",
                         char_count=sum(len(c) for c in chunks))
```

`extract_text(layout=True)` preserves multi-column ordering — critical for bilingual gazettes.

### Step 5 — Tesseract OCR (scanned path)

```python
import pytesseract
from pdf2image import convert_from_path

TESSERACT_CMD_PREFIX = ["tesseract", "--oem", "1", "--psm", "6",
                       "--lang", "eng+sin+tam",
                       "--tessdata-dir", "/usr/share/tesseract-ocr/5/tessdata"]

def extract_with_tesseract(path: str) -> ExtractedText:
    images = convert_from_path(path, dpi=300, fmt="png", thread_count=2)
    pages = [pytesseract.image_to_string(img, config="--oem 1 --psm 6",
                                          lang="eng+sin+tam") for img in images]
    return ExtractedText(text="\n".join(pages), method="tesseract",
                         char_count=sum(len(p) for p in pages))
```

- `--oem 1` = LSTM (best accuracy on printed Sinhala/Tamil).
- `--psm 6` = single uniform block of text (gazette page layout).
- `--lang eng+sin+tam` = always include English — bilingual headers + Sinhala/Tamil body.
- `--tessdata-dir` pinned to `/usr/share/tesseract-ocr/5/tessdata` to enforce the Tesseract 5.3.x model bundle.
- `dpi=300` is the sweet spot — `dpi=200` loses Sinhala diacritics; `dpi=400` doubles runtime for negligible gain.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Tesseract 5.3.x | Open-source; offline; trained on Sinhala/Tamil | ✅ Chosen — pinned version in [10_M1_Sinhala_Tamil_NLP.md §4.2](10_M1_Sinhala_Tamil_NLP.md). | If Tesseract 5.5+ ships a better Sinhala LSTM and we re-calibrate against it. |
| PaddleOCR 2.7 | +3 pp Sinhala CER vs Tesseract | ❌ 1.5 GB model + GPU benefit only. Cost > value at our volume. | If we deploy GPU inference and want maximum OCR quality for a research-grade re-extraction pass. |
| Google Vision API | Highest accuracy + cheap | ❌ Cloud-only — fails the offline-capable requirement from [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md). | If the offline requirement is dropped. |
| Tesseract 4.x | Legacy LSTM model | ❌ Bundled Sinhala model is ~4 pp worse than 5.3.x | Never. |

## Worked example

A real hybrid PDF — `gazette_2486_22.pdf` (multi-pin adapter regulation, 12 pages):

- Pages 1–3: English text layer present (~ 2,800 chars/page). PyMuPDF extracts directly.
- Pages 4–6: Sinhala text layer present (~ 1,200 chars/page). PyMuPDF extracts.
- Pages 7–9: scanned image of Tamil translation (~ 25 chars/page from PyMuPDF — just headers). `classify_pdf()` flags as hybrid.
- Pages 10–12: blank or signature page (~ 15 chars/page).

Per-page chain decision:

| Page | PyMuPDF chars | pdfplumber chars | Tesseract used? | Final method |
|---|---|---|---|---|
| 1 | 2,847 | n/a | ❌ | pymupdf |
| 4 | 1,238 | n/a | ❌ | pymupdf |
| 7 | 23 | 31 | ✅ (Tamil OCR) | tesseract |
| 11 | 14 | 18 | ❌ (under 100-char min for OCR — page treated as blank) | pymupdf (empty) |

Total runtime: ~ 8 s (PyMuPDF) + ~ 9 s (Tesseract on 3 pages) = ~ 17 s. Single-shot latency well below the 30 s timeout in `backend/app/tasks/m1/extract_gazette.py`.

## Failure modes & edge cases

- **Garbled PyMuPDF output.** Some PDFs have a text layer but with broken font encoding → PyMuPDF returns `"..."`. Mitigation: validate the extracted text contains > 70 % printable ASCII or Sinhala/Tamil Unicode chars; if not, fall through to Tesseract.
- **PDF password-protected.** `fitz.open()` raises `mupdf.MuPDFError`. The Celery task catches, sets `status='extraction_failed'`, and writes the reason to `m1_pipeline_errors`.
- **Tesseract subprocess timeout.** Long scanned PDFs occasionally hang OCR. Wrap `image_to_string` in `concurrent.futures.ThreadPoolExecutor` with a 60 s per-page timeout.
- **`pdf2image` requires `poppler-utils`.** Easy to miss in Dockerfile. CI smoke test runs extraction on a sample scanned PDF; failure means poppler is missing.
- **Bilingual page boundary errors.** A Sinhala paragraph that straddles a column boundary occasionally has its lines interleaved with the next column. Mitigated by `extract_text(layout=True)` in pdfplumber; not perfect for Tesseract's PSM 6.

## Validation & acceptance criteria

- **Threshold-calibration accuracy.** Quarterly: ≥ 95 % correct PDF-type classification on the 50-doc audit set.
- **OCR CER.** Quarterly: ≤ 10 % character error rate on a 5-doc Sinhala sample (vs hand transcription); ≤ 8 % on a 5-doc Tamil sample.
- **End-to-end test.** `tests/m1/extraction/test_pdf_classifier.py` covers a fixture PDF of each type (text/hybrid/scanned); asserts the chain emits the expected text within a tolerance.
- **Smoke test in CI.** `make test-extraction` runs the full chain on three fixture PDFs in < 60 s.

## Cross-references

- Parent: [03_M1_Data_Collection.md](03_M1_Data_Collection.md) §2 (PDF extraction)
- Related: [10_M1_2_OCR_Wijesekara_Conversion.md](10_M1_2_OCR_Wijesekara_Conversion.md) (Wijesekara conversion + Tesseract config)
- BUILD phase: BUILD_07 §Extraction pipeline
- Code (when shipped): `ml/m1/extraction/pdf_classifier.py`, `text_extractors.py`, `ocr.py`
