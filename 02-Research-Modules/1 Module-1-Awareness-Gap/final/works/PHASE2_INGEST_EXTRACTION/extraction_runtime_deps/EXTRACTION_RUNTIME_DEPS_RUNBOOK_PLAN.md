# Phase 2 · Extraction — Missing Runtime Artifacts on the Windows Host: Runbook

> Group: `PHASE2_INGEST_EXTRACTION / extraction_runtime_deps`.
> **Status: no code change — environment setup + docs (2026-07-23).** The two boot-time `CRITICAL EXTRACTION RUNTIME DEGRADED` lines are the health check doing its job, not a bug. Recorded here so the exact log line maps to the fix.

## 1. What was seen

Starting the worker (`uv run celery -A app.celery_config worker --pool=threads --concurrency=4`) logged:

```
CRITICAL EXTRACTION RUNTIME DEGRADED — tesseract: tesseract binary not on PATH
CRITICAL EXTRACTION RUNTIME DEGRADED — fasttext_model: lid.176.bin not found —
  ML-profile language routing will fall back (searched: storage\models\m1\baseline\lid.176.bin)
```

## 2. Are these issues? — Yes, but non-blocking, and not code bugs

`app/m1/health.py::check_extraction_runtime()` runs on the `worker_ready` signal and **shouts (never crashes)** when a required runtime artifact is absent — by design (a mis-built environment otherwise boots green and fails rows later). Both messages are that check firing. The worker runs normally; the earlier run extracted 37 PDFs successfully with these same two warnings present.

**Impact, precisely:**
- **tesseract missing** — only *scanned / image-only* gazettes need OCR. The auto-chain runs `wijesekara_routing_v1` (font-aware text extraction) first, so text-based extraordinary gazettes — the large majority — extract fine (proven). A genuinely scanned PDF extracts empty text and is marked `extraction_failed` at preprocess (`raw_text` empty check) — handled gracefully, no retry storm. So: reduced coverage on scanned docs, nothing else.
- **lid.176.bin missing** — degrades the ML profile's *language routing* to a fallback. The DB `language` column is still populated by the backend codepoint heuristic (`pdf_metadata.detect_language`, no model). Low impact.

Two of the four required components (poppler, ml_package) were **not** flagged, so they're present — only the OCR engine and the LID model are missing.

## 3. Fix (host setup — already in 07_SETUP_AND_USER_MANUAL.md, repeated here)

1. **Tesseract 5 + languages:**
   `winget install UB-Mannheim.TesseractOCR` → add `C:\Program Files\Tesseract-OCR` to PATH → drop `sin.traineddata` + `tam.traineddata` into `…\Tesseract-OCR\tessdata\`. Verify: `tesseract --list-langs` lists `eng`, `sin`, `tam`.
2. **fastText LID model:**
   `cd C:\Reasearch\xyz\enigmatrix-ml && uv run python scripts/download_lid_model.py` — idempotent, ~127 MB → `storage/models/m1/baseline/lid.176.bin` (override path via `M1_LID_MODEL_PATH`).
3. Restart the worker; confirm clean:
   `uv run python -m app.m1.health` → every required component `ok` (Surya stub may remain, it never counts against `ok`).

## 4. Optional convenience (not done — flag for decision)

- Poppler is required too (`winget install oschwartz10612.Poppler`) — it passed here, so no action.
- If scanned gazettes are common in scope, consider a follow-up to route `extraction_failed`-on-empty-text rows to OCR once Tesseract is installed (re-extract action already does this).

## 5. Docs updated

- `enigmatrix-docs/m1/final/07_SETUP_AND_USER_MANUAL.md` — two troubleshooting rows mapping the exact boot lines → fix.
- `AI_WORK_LOG.md` — session entry.

## 6. Verification

1. After the two installs + worker restart: `uv run python -m app.m1.health` shows `tesseract: ok` (with sin/tam) and `fasttext_model: ok`.
2. Trigger a run that includes a scanned gazette; confirm it now extracts text (non-empty) instead of `extraction_failed`.
