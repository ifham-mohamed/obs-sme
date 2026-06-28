# 3 — Step 2c: canonical `ml/m1/extraction/` chain (PDF classifier + extractors + OCR)

> Companion plan to [3_setup.md](3_setup.md). Successor to [2.md](2026-05%20Step%202b%20-%20Celery%20task%20wiring%20+%20Stage-B%20extraction%20(M1%20Phase%202).md) (Session 26 Step 2b — runtime MVP shipped at `enigmatrix-backend/app/extraction/`).
> **Status:** 📋 planned · execution lands in a future "execute the 3.md plan" turn (Session 28 / F-149).

## Context

Session 26 (Step 2b) shipped a working PDF-extraction chain at `enigmatrix-backend/app/extraction/{pdf_classifier,text_extractors}.py`. That code is the **runtime MVP** — enough for the Celery `extract_gazette` task to flip rows from `status='ingested'` to `status='extracted'`.

Step 2c moves the implementation to its **canonical home** per doc 13 + [15_M1_1_ML_Folder_Guide.md](../15_M1_1_ML_Folder_Guide.md): `ml/m1/extraction/` (which on this monorepo's filesystem is `enigmatrix-ml/m1/extraction/`). It also adds the **research-grade rigour** that the runtime MVP deliberately deferred:

- The full Tesseract 5.3.x flag set from [03_M1_1_PDF_Extraction_Chain.md §5](../03_M1_1_PDF_Extraction_Chain.md) (`--oem 1 --psm 6 --lang eng+sin+tam`, `tessdata-dir` pin, `dpi=300`).
- Per-page hybrid routing (some pages PyMuPDF, some Tesseract — vs Session 26's whole-document routing).
- A `_threshold_calibration(audit_set)` helper that runs the quarterly recalibration procedure from `03_M1_1 §2` (5 candidate threshold pairs, confusion matrix, pick the pair maximising `min(text_pdf_recall, scanned_precision)`).
- `character_error_rate(pred, gold)` for the OCR CER acceptance metric (≤ 10 % per `03_M1_1 §validation`).
- A Wijesekara conversion hook (the table itself stays a stub — Step 2d).

The Celery task in `enigmatrix-backend/app/tasks/m1/extract_gazette.py` stays byte-stable. `enigmatrix-backend/app/extraction/__init__.py` becomes a thin re-export adapter that imports from `enigmatrix_ml.m1.extraction` — so `from app.extraction import classify_pdf, extract_pymupdf, ...` keeps working with zero churn at the call sites.

## Decisions

- **Build root = `enigmatrix-ml/m1/extraction/`** (filesystem truth maps to doc 13's `ml/m1/extraction/`). The long-running doc-vs-filesystem drift is documented again here; reconciliation is deferred to a future monorepo restructure.
- **Packaging = uv workspace** if uv supports it cleanly on the user's machine; **editable install** (`uv add --editable ../enigmatrix-ml`) as the fallback. A `sys.path` shim is the third-line fallback if both fail. Picked at execution time.
- **50-PDF audit set = harness only, no dataset this turn.** We ship the calibration script + a placeholder `tests/m1/fixtures/audit/` directory + the procedure documented in [3_setup.md](3_setup.md) §6 telling future-us how to populate it. Today's tests use the Session-23 fixture PDF + 2 synthetic fixtures (one rasterised, one empty).
- **OCR CER ≤ 10 % = test is parametrised + skipped today** (no gold corpus). The `character_error_rate` calculator ships with unit tests against synthetic gold strings; the real metric becomes binding once research delivers the corpus.
- **Wijesekara table = stub.** `ocr.py` exports a `wijesekara_to_unicode(text)` function that raises `NotImplementedError("see Step 2d / [10_M1_2_OCR_Wijesekara_Conversion.md](../10_M1_2_OCR_Wijesekara_Conversion.md)")`. Step 2d ships the greedy longest-match table.
- **Session-26 `app/extraction/` becomes a thin re-export adapter.** Local `pdf_classifier.py` + `text_extractors.py` are deleted; `__init__.py` re-exports the same symbols from `enigmatrix_ml.m1.extraction`. Zero source-code churn in `extract_gazette.py`.
- **`language_detection.py` is out of scope.** Per the 15_M1_1 guide it's a sibling file in `extraction/`, but the roadmap places it in Step 2c.5 / Step 2d (consumes raw_text from Step 2b). Step 2c sticks to the 3 files the user named.

## Files (≈ 18 touches — 6 new in ml + 4 modified in ml-scaffold + 3 modified/2 deleted in backend + 3 tests + 4 tracker)

### NEW — `enigmatrix-ml/` Python package + module (6 files)

| Path | Purpose |
|---|---|
| `enigmatrix-ml/pyproject.toml` | Project metadata. Name `enigmatrix-ml`, deps `PyMuPDF`, `pdfplumber`, `pytesseract`, `pdf2image` (mirroring backend pins). `[tool.hatch.build.targets.wheel] packages = ["m1"]` (top-level package = `m1` for now; renames to `enigmatrix_ml` once the package surface stabilises — keep both options open). |
| `enigmatrix-ml/m1/__init__.py` | Package marker. |
| `enigmatrix-ml/m1/extraction/__init__.py` | Public API: re-export `classify_pdf`, `extract_pymupdf`, `extract_pdfplumber`, `extract_tesseract`, `extract_with_chain`, `ExtractedText`, `character_error_rate`. |
| `enigmatrix-ml/m1/extraction/types.py` | `ExtractedText` dataclass (`text: str`, `method: Literal["pymupdf","pdfplumber","tesseract"]`, `char_count: int`, `per_page: list[PageResult]`); `PageResult` dataclass (`page_index: int`, `text: str`, `method: str`, `char_count: int`). |
| `enigmatrix-ml/m1/extraction/pdf_classifier.py` | `classify_pdf(path) -> Literal["text_pdf","hybrid","scanned"]` per `03_M1_1 §2.4` (sample first N pages — default 3 — branch on mean chars/page). Env-tuned thresholds via `os.environ` so backend's settings still drive them. `_threshold_calibration(audit_dir)` walks the 5 candidate pairs from §2 and emits the confusion matrix. CLI hook: `python -m m1.extraction.pdf_classifier --calibrate <dir>`. |
| `enigmatrix-ml/m1/extraction/text_extractors.py` | `extract_pymupdf(path)` with `TEXTFLAGS_TEXT` for Sinhala/Tamil glyph preservation. `extract_pdfplumber(path)` with `layout=True` + table extraction. `_per_page_pymupdf(path)` returns `list[PageResult]` for per-page hybrid decisions. `extract_with_chain(path) -> ExtractedText` driving the worked-example logic from §worked example (per-page: PyMuPDF first, fall back to Tesseract if < 100 chars). |
| `enigmatrix-ml/m1/extraction/ocr.py` | `extract_tesseract(path, dpi=300, lang="eng+sin+tam", config="--oem 1 --psm 6", timeout=60)` per the exact §5 spec; uses `concurrent.futures.ThreadPoolExecutor` for per-page timeout. `character_error_rate(pred: str, gold: str) -> float` for CER. `wijesekara_to_unicode(text)` stub raising `NotImplementedError` with a pointer to `10_M1_2`. CLI hook: `python -m m1.extraction.ocr --measure-cer <pred> <gold>`. |

### MODIFIED — `enigmatrix-ml/` scaffold (3 files)

| Path | Change |
|---|---|
| `enigmatrix-ml/Dockerfile` | Append `tesseract-ocr tesseract-ocr-sin tesseract-ocr-tam poppler-utils` to the apt-get install line so the production image carries the OCR runtime. |
| `enigmatrix-ml/requirements.txt` | Add `PyMuPDF>=1.24,<2`, `pdfplumber>=0.11,<1`, `pytesseract>=0.3.13,<1`, `pdf2image>=1.17,<2`. |
| `enigmatrix-ml/Makefile` | Add `test-extraction:` target — `pytest tests/m1/extraction -v`. |

### MODIFIED — `enigmatrix-backend/` (3 modified + 2 deleted)

| Path | Change |
|---|---|
| `enigmatrix-backend/pyproject.toml` | Add the workspace dependency. Three forms tried in order: (1) `[tool.uv.sources] enigmatrix-ml = { workspace = true }` + root `pyproject.toml` with `[tool.uv.workspace] members = ["enigmatrix-backend", "enigmatrix-ml"]`; (2) `"enigmatrix-ml @ file://../enigmatrix-ml"` in `[project.dependencies]`; (3) drop the dep entry and rely on `sys.path` insertion in `app/__init__.py` (last-resort hack — only if 1 & 2 both fail). |
| `enigmatrix-backend/app/extraction/__init__.py` | Replace local imports with `from m1.extraction import classify_pdf, extract_pymupdf, extract_pdfplumber, extract_tesseract, ExtractedText`. The `__all__` stays identical to Session 26 — call sites unchanged. |
| `enigmatrix-backend/app/extraction/pdf_classifier.py` | **DELETED** — superseded by `enigmatrix-ml/m1/extraction/pdf_classifier.py`. |
| `enigmatrix-backend/app/extraction/text_extractors.py` | **DELETED** — superseded by `enigmatrix-ml/m1/extraction/text_extractors.py`. |
| `enigmatrix-backend/app/tasks/m1/extract_gazette.py` | **NO CHANGE** — proves the adapter works. The `_EXTRACTORS` map and the `classify_pdf()` call resolve through the re-export adapter. |

### NEW — `enigmatrix-ml/tests/m1/extraction/` (3 files)

| Path | Purpose |
|---|---|
| `tests/m1/extraction/test_pdf_classifier.py` | (a) Shape + determinism (same shape as backend's existing test, mirrored). (b) Routing: synthesise a text PDF with > 200 chars/page → asserts `text_pdf`; an empty PDF → asserts `scanned`. (c) 50-doc audit DoD scaffold — `test_audit_set_accuracy()` skipped today with `pytest.skip("populate tests/m1/fixtures/audit/ with 50 labelled PDFs first; see 3_setup.md §6")`. |
| `tests/m1/extraction/test_text_extractors.py` | (a) PyMuPDF + pdfplumber happy-path on Session-23 fixture (mirrors backend). (b) Per-page hybrid routing on a 2-page synthetic fixture (page 1 text, page 2 blank → asserts `extract_with_chain` returns `PageResult.method='pymupdf'` for page 1 and `pymupdf` or `tesseract` for page 2 depending on chars). |
| `tests/m1/extraction/test_ocr.py` | (a) Tesseract smoke test on a rasterised fixture, **skipped unless `shutil.which('tesseract')`** is truthy. (b) CER calculator: `character_error_rate("HELLO","HALLO")==0.2`, `character_error_rate("","X")==1.0`, identity returns `0.0`. (c) `wijesekara_to_unicode("anything")` raises `NotImplementedError`. (d) DoD CER skipped (no gold corpus yet). |

### MODIFIED — Tracker (4 files, **deferred to the execute turn**)

| Path | Change (when Step 2c executes) |
|---|---|
| `AI_WORK_LOG.md` | New Session 28 entry above Session 27/26. |
| `enigmatrix-docs/tracker/SESSIONS.md` | New Session 28 entry. |
| `enigmatrix-docs/tracker/CHANGES.md` | New F-149 row above F-148. |
| `enigmatrix-docs/tracker/FEATURES.md` | New `## Session 28 — Step 2c canonical extraction chain` section with F-149 row. |

## Execution order (future "execute 3.md" turn)

1. **Stand up `enigmatrix-ml/` as a Python package.** Write `pyproject.toml` + `m1/__init__.py` + `m1/extraction/__init__.py`. Confirm `cd enigmatrix-ml && uv sync` succeeds.
2. **Move + extend Session-26 code.** Copy `app/extraction/pdf_classifier.py` → `m1/extraction/pdf_classifier.py` and extend with the calibration helper + `--calibrate` CLI. Copy `text_extractors.py` and add `TEXTFLAGS_TEXT`, `extract_pdfplumber` with `layout=True`, `_per_page_pymupdf`, `extract_with_chain`.
3. **Write `ocr.py`** — full Tesseract flag set + `character_error_rate` + Wijesekara stub.
4. **Wire `enigmatrix-backend` to depend on `enigmatrix-ml`.** Try workspace first; fall back to editable.
5. **Replace `app/extraction/` with the adapter.** Delete the 2 originals; rewrite `__init__.py` as re-exports.
6. **Write the 3 tests** under `enigmatrix-ml/tests/m1/extraction/`.
7. **Run both suites:** `cd enigmatrix-ml && uv run pytest tests/m1/extraction -v` then `cd enigmatrix-backend && uv run pytest -k extraction -v`.
8. **Update 4 tracker files** with Session 28 / F-149 entry.
9. **Verify zero non-target drift:** `git diff --stat enigmatrix-frontend/ enigmatrix-infrastructure/` empty.

## Verification

1. `enigmatrix-backend/app/tests/unit/test_pdf_classifier.py` + `test_text_extractors.py` + `test_gazette_scraper_task.py` still pass byte-identically (proves the adapter is transparent).
2. `enigmatrix-backend/app/tests/integration/test_celery_extract_gazette.py` still passes (Docker permitting) — proves the Celery task didn't break.
3. New `enigmatrix-ml/tests/m1/extraction/` suite: ≥ 7 tests pass.
4. `cd enigmatrix-backend && uv run python -c "from app.extraction import classify_pdf; from m1.extraction import classify_pdf as direct; assert classify_pdf is direct"` — proves the adapter is a literal re-export.
5. `python -m m1.extraction.pdf_classifier --calibrate enigmatrix-ml/tests/m1/fixtures/audit/` runs end-to-end on the 3 synthetic fixtures and emits a confusion matrix.
6. `git diff --stat enigmatrix-frontend/ enigmatrix-infrastructure/` empty.

## Risks / open items

- **Packaging is the fragile part.** uv workspaces are the cleanest path; if uv on the user's machine doesn't support them, the fallback editable install adds a `file://` reference that's slightly less portable (CI cache invalidation may bite). If both fail, the `sys.path` shim works but is ugly — flag in the tracker entry as a follow-up to revisit when uv tooling matures.
- **Celery task path stability.** The whole exercise rests on `from app.extraction import classify_pdf` resolving through the adapter. If the import path needs to be widened (e.g. the Celery task imports submodules directly instead of via the package), the adapter must mirror those too. Spot-check: `grep -rn "from app.extraction" enigmatrix-backend/app/` — currently only `extract_gazette.py` imports from it.
- **50-PDF audit + 10 % CER are research DoDs.** They can't be enforced in CI without a labelled corpus. The plan ships the *apparatus*; the data is a separate research-side ticket. Documented in `3_setup.md` §6/§7.
- **Tesseract 5.3.x vs 5.5.x.** Production Docker pins 5.3.x via `apt-get` distro packages; dev macOS uses 5.5.2 from Homebrew. Spec was written against 5.3.x. Risk: subtle differences in Sinhala LSTM behaviour. Mitigation: the test suite is *binary-presence* gated, not version-gated; calibration must be re-run on each version. Documented in `3_setup.md` §8.
- **`m1` is a generic top-level package name.** Risk of collision with other `m1` packages in a future user's Python env. Plan calls this out as a follow-up rename (`m1` → `enigmatrix_m1` or land under `enigmatrix_ml`) once the package surface stabilises and we're confident about naming.
- **`language_detection.py` still missing.** Per `15_M1_1`, the fourth file in `extraction/` is `language_detection.py` (fastText `lid.176.bin`). Step 2c stops at 3 files per the user's quoted roadmap text; `language_detection.py` is Step 2c.5 / Step 2d. Documented in `3_setup.md` §10.

## Cross-references

- Parent spec: [03_M1_1_PDF_Extraction_Chain.md](../03_M1_1_PDF_Extraction_Chain.md) — the deep-dive driving every numeric parameter here.
- Folder guide: [15_M1_1_ML_Folder_Guide.md](../15_M1_1_ML_Folder_Guide.md) `ml/m1/extraction/` rows — the canonical file list.
- Predecessor: [2.md](2026-05%20Step%202b%20-%20Celery%20task%20wiring%20+%20Stage-B%20extraction%20(M1%20Phase%202).md) (Session 26 Step 2b — runtime MVP at `app/extraction/`).
- Successor companions: [3_setup.md](3_setup.md) (user-facing setup + verification).
- Roadmap: [16_M1_Development_Roadmap.md](../16_M1_Development_Roadmap.md) Phase 2 Step 2c.
- Deferred to Step 2d: [10_M1_2_OCR_Wijesekara_Conversion.md](../10_M1_2_OCR_Wijesekara_Conversion.md), [10_M1_1_Language_Detection_Routing.md](../10_M1_1_Language_Detection_Routing.md).
