# Plan: Per-PDF metadata schema and population

## Context

Stage 2 of the four-stage push. The existing `m1_regulations` schema captured `raw_pdf_path`, `gazette_number`, `gazette_published_date`, `source_url`, `status`, `extraction_method`, `extracted_at`, `last_error/last_error_at`, `cleaned_text`, `amendment_type` — most of the operator's "metadata wish list" was already there. Missing: `file_size_bytes`, `sha256`, `pdf_pages`, `language`. Those four are now added so the upcoming Stage 3 PDF Records browse view can render rich per-PDF cards without round-tripping to disk on every render.

Storage layout was verified during Stage 0 (Railway deploy): PDFs live at `${STORAGE_LOCAL_PATH}/m1/raw/<source_id>/<gazette_number>.pdf` (e.g. `/data/storage/m1/raw/BILL/2486-15.pdf`). The DB does NOT hold PDF bytes — only the relative path. This contract is preserved by Stage 2; the new columns are metadata-about-the-file, not the file itself.

## Goal

1. Add four metadata columns to `m1_regulations` via migration `202605280001`.
2. Compute and write those columns inside the existing `extract_gazette` Celery task, immediately after the text extraction succeeds.
3. Surface the new fields via existing `/progress` + `/unknown` endpoints so the frontend can consume them via the same `ExtractionProgressRow` shape.
4. Mirror the new fields on the TypeScript `ExtractionProgressRow` interface so Stage 3 can read them.

## Steps / tasks

1. ✅ **Migration** — Created `enigmatrix-backend/alembic/versions/202605280001_m1_pdf_metadata.py` (NEW). `revision="202605280001"`, `down_revision="202605270001"`. Adds four columns to `m1_regulations`: `file_size_bytes` (BigInteger, nullable), `sha256` (String(64), nullable), `pdf_pages` (SmallInteger, nullable), `language` (String(10), nullable). Two indexes: `ix_m1_regulations_language` (UI filter), `ix_m1_regulations_sha256` (dedup checks). Clean `downgrade()` provided.
2. ✅ **Model** — Edited `enigmatrix-backend/app/models/regulation.py`. Added `BigInteger` to the SQLAlchemy import line. Appended four `Mapped[...]` declarations on `M1Regulation` matching the migration. Comment block explains the design intent (NULL on legacy rows until `/re-extract` reruns them; language detection uses lightweight Unicode-codepoint heuristic, not fasttext, to avoid the 125 MB model file in the Railway image).
3. ✅ **Metadata helper** — Created `enigmatrix-backend/app/extraction/pdf_metadata.py` (NEW). Five exports: `compute_file_size`, `compute_sha256` (streamed in 1 MiB chunks), `compute_pdf_pages` (via PyMuPDF `fitz.open(...).page_count`), `detect_language` (Unicode codepoint ratio across Sinhala U+0D80-0DFF / Tamil U+0B80-0BFF / Latin), `compute_pdf_metadata` (resilient aggregator — any single field that fails to compute is logged + skipped, never breaks the extraction). Returns a `TypedDict[PdfMetadata]`.
   - **Note:** the module was subsequently revised (by user/linter) to accept either `bytes` or `Path` input (`PdfSource = Union[bytes, Path]`) and to use ISO 639-1 two-letter codes (`'si'/'ta'/'en'`) matching the ml repo's `m1/extraction/language_detection.py`. Original draft used `'sin'/'tam'/'eng'`. The revised version documents the **intentional divergence** from ml's fastText-based detector (image-size constraints) and aligns the output format.
4. ✅ **Extract task wiring** — Edited `enigmatrix-backend/app/tasks/m1/extract_gazette.py`. Added `from app.extraction.pdf_metadata import compute_pdf_metadata`. After the successful extraction block (where `raw_text`, `extraction_method`, `extracted_at`, `status='extracted'`, `last_error=None` are set), call `compute_pdf_metadata(pdf_path, raw_text=text)` and write the four fields onto `row`. Uses `.get()`-style semantics — fields missing from the returned dict are skipped.
5. ✅ **Schema response** — Edited `enigmatrix-backend/app/schemas/m1_pipeline.py`. `ExtractionProgressRow` gains five new nullable fields: `file_size_bytes`, `sha256`, `pdf_pages`, `language`, `source_url` (also adding source_url since the model already had it and Stage 3 will display it).
6. ✅ **Service row builder** — Edited `enigmatrix-backend/app/services/m1_pipeline_service.py` `get_extraction_progress()`. The row-dict comprehension populates the five new fields from `row.file_size_bytes / row.sha256 / row.pdf_pages / row.language / row.source_url`.
7. ✅ **Unknown-list row builder** — Edited `enigmatrix-backend/app/api/v1/m1_gazette_extraction.py` `list_unknown_regulations()` to populate the same five fields in its `ExtractionProgressRow.model_validate({...})` call.
8. ✅ **Frontend types** — Edited `enigmatrix-frontend/lib/api/m1-gazette-extraction.ts`. `ExtractionProgressRow` TypeScript interface gains `file_size_bytes: number | null`, `sha256: string | null`, `pdf_pages: number | null`, `language: string | null`, `source_url: string | null`. Comment notes the language codes will be `'si' | 'ta' | 'en' | 'unknown'` after the helper revision.

## Errors fixed (during implementation)

- None during the writes themselves. The language-code format question (`'sin'/'tam'/'eng'` vs `'si'/'ta'/'en'`) was caught downstream during the Stage 4 audit — the ml repo's `language_detection.py` uses ISO 639-1 two-letter codes, so the backend helper was subsequently aligned to match.

## Technical notes

- **NULL-on-legacy strategy** — Rows extracted before migration `202605280001` stay NULL on the four new columns until `/re-extract` reruns them. No backfill script in this PR; the existing per-row `/re-extract` admin action is sufficient for opportunistic migration. A bulk `backfill_m1_pdf_metadata.py` script could be added later if needed.
- **Streaming sha256** — `compute_sha256()` reads 1 MiB chunks. Bigger buffers don't help (CPU-bound update step, not I/O-bound); smaller buffers add syscall overhead. Streaming matters because gazette PDFs can hit 50 MB and the worker is on a Railway dyno with bounded memory.
- **PyMuPDF page count** — `fitz.open(...)` is already a hard dep (`pymupdf>=1.24`). The helper guards `ImportError` defensively but the install never fails on the deploy image because the apt-get layer also pulls tesseract + poppler.
- **Why not fasttext for language detection** — `fasttext-wheel` was downloaded during the deploy build (visible in the log: `Downloading fasttext-wheel (4.4MiB)`), but the actual language ID model (`lid.176.bin`) is 125 MB. The ml repo has `scripts/download_lid_model.py` for that, and the model itself is gitignored. The backend's Unicode-codepoint heuristic is plenty accurate for Sri Lankan gazettes — Sinhala, Tamil, and English sit in disjoint Unicode blocks, so the dominant block wins.
- **`source_url` was already in the model** (`app/models/regulation.py` line 105) but wasn't on `ExtractionProgressRow`. This PR adds it because the Stage 3 PDF Records page wants to render an "Open original source" icon button per row.

## Decisions taken

- **Unicode-codepoint heuristic over fasttext** — image-size cost not worth it for this use case. Document the intentional divergence from the ml repo's heavier implementation.
- **ISO 639-1 codes (`'si'/'ta'/'en'`)** — match ml's existing output format. Future code that compares language values across the two systems doesn't need a code-mapping table.
- **Resilient `compute_pdf_metadata`** — Any single-field failure logs + skips; extraction itself never fails because metadata couldn't be computed. The metadata is an enhancement, not a load-bearing extract step.
- **Indexed `sha256` and `language` only** — Other fields (file_size_bytes, pdf_pages) aren't filtered on in the UI today. Add indexes later if a usage pattern emerges.

## Open questions

- Should an opt-in bulk backfill script (`app/scripts/backfill_m1_pdf_metadata.py`) be added so all pre-existing rows get the new fields without per-row re-extraction?
- Should `sha256` participate in a dedup check during the spider's `_insert_rows` (skip rows whose hash already exists in the DB)?
- Should `pdf_pages` be computed by the spider at download time instead of `extract_gazette`, so the page count is visible before extraction has even started?

## Acceptance criteria

- [x] `alembic upgrade head` on Railway applies migration `202605280001` cleanly.
- [x] New rows extracted by `extract_gazette` populate all four metadata columns.
- [x] `/progress` and `/unknown` responses include the five new fields (4 metadata + `source_url`).
- [x] Frontend `ExtractionProgressRow` TS type matches the backend schema.
- [x] Legacy rows show NULL on the new fields and `/re-extract` repopulates them.

## Linked trackers

- [CHANGES.md](../CHANGES.md) — F-196
- [FEATURES.md](../FEATURES.md) — F-196
- [SESSIONS.md](../SESSIONS.md) — Session 55
- Related plan: [2026-05-22_Plan PDF Records browse-all admin page](./2026-05-22_Plan%20PDF%20Records%20browse-all%20admin%20page.md) (consumes these fields)
- Related plan: [2026-05-22_Plan Cross-repo code quality audit — Stage 4](./2026-05-22_Plan%20Cross-repo%20code%20quality%20audit%20—%20Stage%204.md) (flagged the `'sin'/'tam'/'eng'` vs `'si'/'ta'/'en'` divergence that was subsequently fixed)
