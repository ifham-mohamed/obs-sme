# 3_setup — Step 2c setup + verification guide

> Companion to [3.md](2026-05%20Step%202c%20-%20canonical%20ml-m1-extraction%20chain%20(PDF%20classifier%20+%20extractors%20+%20OCR).md) — user-actionable setup + verification for the canonical `ml/m1/extraction/` chain.
> **Status:** 📋 planned (will be executed by a future "execute the 3.md plan" turn).

## 1. Deployment context

`enigmatrix-ml/` is **training + research code**. It does NOT deploy to Vercel (Vercel is serverless; ML code is process-style with file-system caches, long-running models, OCR subprocesses). The Step 2b Celery worker (which we stood up in Session 26) is what *runs* the extractor in production — Step 2c just moves the implementation to its canonical home and pulls it in as a dependency.

Live deployments unchanged from Session 24's note:
- Backend health: <https://enigmatrix-backend.vercel.app/health> → `{"status":"ok","service":"enigmatrix-api"}`.
- Frontend: <https://enigmatrix-frontend.vercel.app/>.
- Celery worker: local dev today; Fly.io machine when Step 4a lands.

## 2. Prerequisites

Same as [2_setup.md](2_setup.md):

| Tool | Why | Install |
|---|---|---|
| Python 3.11–3.12 | runtime | `brew install python@3.12` |
| `uv` | package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `tesseract` 5.3+ | OCR | `brew install tesseract` (macOS) / `apt-get install tesseract-ocr` (Linux/Docker) |
| `tesseract-lang` (sin + tam) | Sinhala + Tamil OCR | `brew install tesseract-lang` / `apt-get install tesseract-ocr-sin tesseract-ocr-tam` |
| `poppler` | `pdf2image` PDF→PNG | `brew install poppler` / `apt-get install poppler-utils` |
| `redis` | Celery broker (already from Step 2b) | `brew install redis` |
| Docker | testcontainer Postgres (integration tests) | Docker Desktop |

Quick verify:
```bash
which tesseract pdftoppm redis-server
tesseract --list-langs | grep -E '^(eng|sin|tam)$'  # expect all three
```

## 3. Workspace wiring (`enigmatrix-ml` ↔ `enigmatrix-backend`)

Step 2c stands up `enigmatrix-ml/` as a real Python package. Two paths to install — try them in order:

### Path A — uv workspace (preferred)
From the monorepo root, add a workspace `pyproject.toml`:

```bash
cd /Users/arqm7/Documents/Github\ Repos/xyz
cat > pyproject.toml <<'EOF'
[tool.uv.workspace]
members = ["enigmatrix-backend", "enigmatrix-ml"]
EOF
uv sync --workspace
```

Verify:
```bash
cd enigmatrix-backend
uv run python -c "import m1.extraction; print(m1.extraction.classify_pdf.__module__)"
# expect: m1.extraction.pdf_classifier
```

### Path B — editable install (fallback)
If uv workspace mode is unavailable or finicky:
```bash
cd enigmatrix-backend
uv add --editable ../enigmatrix-ml
```
Same verify step as Path A.

### Path C — `sys.path` shim (last resort)
If A and B both fail, add `sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "enigmatrix-ml"))` near the top of `enigmatrix-backend/app/__init__.py`. Ugly but unblocks.

## 4. Run the new `enigmatrix-ml` test suite

```bash
cd enigmatrix-ml
uv run pytest tests/m1/extraction -v
```

Expected output:
- `test_pdf_classifier.py` — 3 passes (shape, determinism, routing) + 1 skip (50-doc audit).
- `test_text_extractors.py` — 3 passes (PyMuPDF, pdfplumber, per-page hybrid routing).
- `test_ocr.py` — 4 passes (CER calculator × 3, Wijesekara stub raises) + 1 conditional pass/skip (Tesseract smoke, only if binary present) + 1 skip (CER DoD on real corpus).

**≥ 10 collected, ≥ 7 passing, ≤ 3 environmental skips.**

## 5. Re-run the backend suite (proves the adapter is byte-stable)

```bash
cd enigmatrix-backend
uv run pytest app/tests/unit/test_pdf_classifier.py \
              app/tests/unit/test_text_extractors.py \
              app/tests/unit/test_gazette_scraper_task.py -v
```

Expected: all 6 pass identically to Session 26's run. The `from app.extraction import ...` in those tests now resolves through the adapter → `m1.extraction` — but the test outputs are unchanged. If they pass, the adapter is transparent.

For the integration test (needs Docker):
```bash
# Start Docker Desktop first
uv run pytest app/tests/integration/test_celery_extract_gazette.py -v
```
Expected: 2 passes. Same DoD as Session 26 — the row flips `ingested → extracted`.

## 6. Threshold calibration drill

Once a contributor hand-labels 50 PDFs (the research-side audit deliverable):

```bash
# Layout:
# enigmatrix-ml/tests/m1/fixtures/audit/
#   labels.csv          # columns: filename, true_label ∈ {text_pdf, hybrid, scanned}
#   gazette_1.pdf
#   gazette_2.pdf
#   ...

cd enigmatrix-ml
uv run python -m m1.extraction.pdf_classifier --calibrate tests/m1/fixtures/audit/
```

Output:
- Tested threshold pairs: `(150,25), (180,30), (200,30), (220,35), (250,40)`.
- Per-pair confusion matrix vs `labels.csv`.
- Recommended pair: the one maximising `min(text_pdf_recall, scanned_precision)`.
- Current production pair `(200, 30)` from `M1_PDF_TEXT_THRESHOLD` + `M1_PDF_SCANNED_THRESHOLD`.

Once the recommended pair differs from production, update:
1. `enigmatrix-backend/.env` + `.env.example` with the new thresholds.
2. `storage/models/m1/v<X>/model_registry.json:classify_pdf_thresholds` (when that file lands).

## 7. OCR CER measurement drill

The 10 % CER DoD from [03_M1_1 §validation](../03_M1_1_PDF_Extraction_Chain.md) requires gold transcriptions. Once a contributor produces them:

```bash
# Layout:
# tests/m1/fixtures/ocr_gold/
#   sample_si_1.pdf
#   sample_si_1.gold.txt    # hand-transcribed
#   sample_si_2.pdf
#   sample_si_2.gold.txt
#   ...

cd enigmatrix-ml
uv run python -m m1.extraction.ocr --measure-cer \
    tests/m1/fixtures/ocr_gold/*.pdf
```

Output:
- Per-sample CER.
- Per-language mean CER (`sin` vs `tam` vs `eng`).
- Pass / fail vs the 10 % bar (Sinhala) + 8 % bar (Tamil).

## 8. Production Docker (Fly.io worker)

The `enigmatrix-ml/Dockerfile` is updated this Step to bake in the OCR runtime:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-sin \
        tesseract-ocr-tam \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*
```

The image is consumed by the Step 4a Fly.io worker (`enigmatrix-infrastructure/fly/worker.toml` when it lands).

Build locally to verify:
```bash
cd enigmatrix-ml
make docker-build
docker run --rm enigmatrix-ml tesseract --list-langs
# expect: eng, sin, tam
```

**Tesseract version note.** Debian's `tesseract-ocr` is 5.3.x; macOS Homebrew is 5.5.2. The Sinhala LSTM model is shared across both branches; calibration must be re-run when crossing minor versions. The plan deliberately doesn't pin `==5.3` in apt to keep the Dockerfile portable across Debian releases.

## 9. Rollback

If something breaks post-Step-2c, the rollback is clean:

```bash
git revert <step-2c-commit-sha>          # reverts code changes
# OR
git checkout HEAD~1 -- enigmatrix-backend/app/extraction enigmatrix-ml/
```

The Session-26 self-contained version of `enigmatrix-backend/app/extraction/` is restored from git history. The Celery task in `extract_gazette.py` was untouched by Step 2c, so it picks the local files back up immediately. No Alembic migration to roll back (Step 2c is code-only).

## 10. What's deferred to Step 2d / 2e

Step 2c stops where the user's quoted roadmap stops — 3 files at `ml/m1/extraction/`. Out of scope this slice:

- **Wijesekara conversion table** — `ocr.py::wijesekara_to_unicode` is a stub; the greedy longest-match table lives in [10_M1_2_OCR_Wijesekara_Conversion.md](../10_M1_2_OCR_Wijesekara_Conversion.md). Step 2d ships the table + a `test_wijesekara_roundtrip` test.
- **`language_detection.py`** — fastText `lid.176.bin` per [10_M1_1_Language_Detection_Routing.md](../10_M1_1_Language_Detection_Routing.md). Listed in `15_M1_1_ML_Folder_Guide.md` as a sibling extraction file; Step 2c.5 / Step 2d picks it up.
- **50-PDF audit dataset** — `tests/m1/fixtures/audit/` ships empty with a `README.md` pointing at the calibration procedure. Populating it is research work — a separate ticket, likely surfacing once Step 2b's spider has collected ≥ 50 real gazettes from `documents.gov.lk`.
- **OCR CER gold corpus** — `tests/m1/fixtures/ocr_gold/` ships empty. Populating it is research work too; requires a Sinhala/Tamil-fluent contributor to hand-transcribe ~5 pages × 10 PDFs.
- **Per-page hybrid routing edge cases** — Step 2c handles the common case (PyMuPDF first, Tesseract if < 100 chars). The full `03_M1_1 §failure modes` table (garbled font encoding, password-protected PDFs, bilingual paragraph straddle, 60s Tesseract timeout) gets exhaustive tests in Step 2d.
- **`storage/models/m1/v<X>/model_registry.json`** — the JSON registry that pins the calibrated thresholds. Lands when Step 3 (training) creates the `v1/` directory.

## 11. Cross-references

- Companion plan: [3.md](2026-05%20Step%202c%20-%20canonical%20ml-m1-extraction%20chain%20(PDF%20classifier%20+%20extractors%20+%20OCR).md).
- Parent spec: [03_M1_1_PDF_Extraction_Chain.md](../03_M1_1_PDF_Extraction_Chain.md).
- Folder guide: [15_M1_1_ML_Folder_Guide.md](../15_M1_1_ML_Folder_Guide.md).
- Predecessor: [2.md](2026-05%20Step%202b%20-%20Celery%20task%20wiring%20+%20Stage-B%20extraction%20(M1%20Phase%202).md) + [2_setup.md](2_setup.md) (Session 26 Step 2b).
- Roadmap: [16_M1_Development_Roadmap.md](../16_M1_Development_Roadmap.md) Phase 2 Step 2c.
- Deployment: [07_M1_Deployment_Integration.md](../07_M1_Deployment_Integration.md), [13_M1_Folder_Structure_and_Implementation_Flow.md](../13_M1_Folder_Structure_and_Implementation_Flow.md).
- Deferred: [10_M1_1_Language_Detection_Routing.md](../10_M1_1_Language_Detection_Routing.md), [10_M1_2_OCR_Wijesekara_Conversion.md](../10_M1_2_OCR_Wijesekara_Conversion.md).
