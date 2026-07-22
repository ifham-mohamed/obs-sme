# Module 1 — Phase 2 Gap #5: Heavy/Optional Dependencies — Assert, Don't Assume

> Companion to [[PHASE2_INGEST_EXTRACTION_ANALYSIS]] §6.5 + §9.8.5 and [[PHASE2_GAP_CLOSURE_PLAN]] §6.5. **Status: implemented (Session 66, 2026-07-21).** Code in `C:\Reasearch\xyz\enigmatrix-backend`.

## Problem

The extraction chain degrades **silently** when system artifacts are missing — none of these break `import app`, so a mis-built image boots green:

| Missing artifact | Silent failure mode |
|---|---|
| `tesseract` binary | scanned PDFs quietly fail through the extractor chain |
| `sin`/`tam` traineddata | SI/TA OCR emits junk that *looks* like output |
| `poppler-utils` (`pdftoppm`) | pdf2image dies inside the OCR path |
| `lid.176.bin` (~127 MB) | ML-profile language routing falls back; **was a manual deploy-time copy with no assertion** |
| `enigmatrix-ml` (`m1` pkg) | preprocess/profile tasks fail at first runtime use |
| Surya | known Phase-3 stub — fine, but nobody could *see* that in prod |

Audit of the actual `Dockerfile` showed Tesseract + sin/tam + poppler **are** installed — the ship gap was real only for `lid.176.bin`. The assertion gap was real for everything.

## Design: one check, three surfaces, one build gate

**`app/m1/health.py` → `check_extraction_runtime()`** — per-component status (`ok | degraded | missing | error`, plus `stub | enabled` for Surya) with actionable `detail` strings. Checks: `tesseract --list-langs` must contain eng+sin+tam; `pdftoppm` on PATH; `lid.176.bin` resolved via `M1_LID_MODEL_PATH` env → `$STORAGE_LOCAL_PATH/models/m1/baseline/` → `./storage/...`, with a >100 MB size sanity check (catches truncated downloads, not just absence); `importlib.find_spec("m1")`; `find_spec("surya")`. Top-level `ok` requires the four *required* components; Surya's stub status is informational by design — the §6.5 ask was "make the stub visible", not "fail on it".

**Policy: report + shout, never crash.** An EN-text-only deployment still works without Tesseract, and killing the worker would take healthy task types down with it. The teeth live at build time instead (below).

Surfaces:

1. **Celery `worker_ready` signal** (`celery_config.py`) — one CRITICAL log line per problem at worker boot; INFO summary when healthy. Wrapped so a health-check bug can never kill the worker.
2. **`GET /api/v1/admin/m1/pipeline/health`** (`admin_pipeline.py`, `require_admin`) — same report for the pipeline portal; a degraded-runtime banner in the UI is a small follow-up (data's already there).
3. **Container-start banner** (`start_railway.sh`) — `python -m app.m1.health` prints the JSON report into the deploy log right after migrations, `|| true` (non-fatal at runtime).

Build gate (where failing *is* correct):

4. **`lid.176.bin` baked into the image** — new Dockerfile layer downloads it to `/opt/models/` (fixed image path, deliberately NOT `$STORAGE_LOCAL_PATH` — that's the runtime volume) with a size assertion, and sets `M1_LID_MODEL_PATH`. The "easy-to-miss deploy step" no longer exists.
5. **`RUN python -m app.m1.health --strict`** as the Dockerfile's final check — the image **fails to build** if the runtime it claims to ship is incomplete (dummy env vars supplied; `health.py` tolerates absent settings at build time). This is the "production image actually ships them" property from the gap text, enforced mechanically.

## Files changed

`app/m1/health.py` (new), `app/celery_config.py` (worker_ready hook), `app/m1/api/admin_pipeline.py` (GET /health), `scripts/start_railway.sh` (banner step), `Dockerfile` (model bake layer + `--strict` gate). No migration.

## Verification (deferred to user — sandbox lacks Docker/system deps)

1. `python -m compileall app`; locally `python -m app.m1.health` → expect honest per-component statuses for your dev box.
2. `docker build` → confirm the model layer downloads once and the `--strict` gate passes; then intentionally break it (comment out `tesseract-ocr-sin`) → build must fail with `tesseract: missing traineddata: ['sin']`.
3. Deployed: worker boot log shows the health line; `GET /api/v1/admin/m1/pipeline/health` as admin returns `ok: true` with `surya: stub`.
4. `pytest` + `graphify update .`.

## Follow-ups

- Pipeline-portal banner component reading `/health` (small frontend slice).
- When Phase 3 enables Surya: flip it into the required set + add its model-weights check here.
- Optional: pin `lid.176.bin` by checksum (SHA256) rather than size once the canonical hash is recorded.
