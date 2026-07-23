# Module 1 — Phase 2 Gap-Closure Plan

> Companion to [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/11_PHASE2_INGEST_EXTRACTION_ANALYSIS]] — one entry per residual gap (§6.1–7, §9.8.1–5), each with status and a concrete plan. Gap #3 (CI live-crawl coverage) is **implemented** as of Session 64 (2026-07-21); the rest are specified here in priority order. Code lives in `C:\Reasearch\xyz`.

---

## Priority order (what to do first and why)

1. **§9.8.1 — auto-chain not font-aware** (correctness: routine ingestion still garbles SI/TA)
2. **§6.5 + §9.8.5 — unasserted runtime artifacts** (silent degradation in prod)
3. **§6.2 — PDF archiving** (link-rot makes failures unrecoverable)
4. **§6.3 — CI crawl canary** ✅ done
5. **§6.6 — metadata confidence + review queue**
6. **§6.4 — continuous extraction-quality monitoring**
7. **§6.7 — chunk contract freeze** (cheap, do before Phase 3 starts)
8. **§6.1 — gazette.lk second source** (new capability, not a defect)
9. **§9.8.3 / §9.8.4 — font-coverage growth** (fold into §6.4 monitoring)

---

## §6.3 — CI coverage of live crawls ✅ IMPLEMENTED (Session 64)

**The insight that unlocks it:** the Twisted-reactor singleton only forbids `CrawlerProcess` *in-process* under pytest. It does not forbid (a) fetching live HTML and running `spider.parse()` on it — the same `HtmlResponse` composition the offline fixture test already uses — or (b) running `scrapy crawl` as a **subprocess**, which is exactly how production invokes it (`gazette_scraper.run_gazette_spider`). The "no CI live crawl" constraint was never technical for these two forms; it just hadn't been decomposed.

**What was built:**

- `app/tests/live/test_live_crawl_canary.py` —
  - *Selector canary*, parametrized over all 4 spiders (EGZ / weekly / acts / bills): httpx-GET the current-year listing (previous-year fallback for the January boundary), wrap in `HtmlResponse`, run `parse()`, assert ≥1 item, document-number + `.pdf` URL present on every item, and ≥50% of items carry a parsed date (guards `_DATE_RE` format drift). Failure message names the regression class.
  - *Subprocess E2E smoke*: `python -m scrapy crawl gazette_spider -s ITEM_PIPELINES={} -s CLOSESPIDER_ITEMCOUNT=3 -O items.jl:jsonlines` — full reactor/scheduler/robots/throttle path, no DB, ≤3 items politeness cap; asserts exit 0 + well-formed feed items.
  - Marked `live_crawl` **and** `slow` — the existing per-PR fast run (`-m "not slow"`) never touches them.
- `pyproject.toml` — `markers` registered (`slow`, `live_crawl`).
- `.github/workflows/crawl-canary.yml` — scheduled Mon+Thu 02:30 UTC + `workflow_dispatch`; deliberately **not** part of PR CI (a third-party site outage must never block merges); failure emits a triage runbook (check listing URL → fix selectors/regex → refresh the offline fixture).

**Residual:** the canary detects listing-markup drift, not PDF-content drift (covered by §6.4). Detection latency is ≤3–4 days; acceptable vs. the 6-hour Beat cadence because the insert pipeline is idempotent (UNIQUE gazette_number) — a broken spider yields zero rows, not bad rows, and the canary catches the zero.

**Verify (user):** `cd enigmatrix-backend && uv run pytest app/tests/live -m live_crawl -v` once locally; confirm the workflow appears under Actions and a `workflow_dispatch` run goes green; confirm the fast suite still collects no live tests (`uv run pytest -q -m "not slow" --collect-only | grep live` → empty).

---

## §9.8.1 — Wire font-aware extraction into the auto-chain (highest impact)

**Problem:** `extract_gazette` (hot path) uses backend `app/extraction/*` with no Wijesekara/font-aware pass; correct SI/TA only comes from a manual profile re-run (`wijesekara_routing_v1`). Newly scraped gazettes land garbled.

**Plan — make the profile path the default, don't duplicate it:**

1. Add `M1_DEFAULT_EXTRACTION_PROFILE=wijesekara_routing_v1` setting (env-overridable; empty = legacy behaviour → instant rollback switch).
2. In `extract_gazette`, replace the direct `classify_pdf → extract_*` calls with a call into the profile dispatcher (`load_profile(settings.M1_DEFAULT_EXTRACTION_PROFILE)` + the per-page loop `run_extraction.py` already implements). Extract that loop into a shared function (e.g. `m1/extraction/apply_profile.py`) so the task and the dataset runner call one implementation — the current duplication (backend mirror vs. ML package) is the root cause of this divergence.
3. Persist the profile's quality metrics (`wijesekara_applied`, `cid_marker_count_before/after`) onto the regulation row or `m1_extraction_runs` — they exist in the profile path and are currently dropped in the auto-chain.
4. Acceptance: re-ingest a known pre-2010 SI gazette (e.g. the `2468/44` doc from the Slice-7 dashboard) through the *auto* chain → CID count 0; EN docs byte-identical to legacy output (regression corpus: 5 EN + 3 SI + 2 TA fixtures, golden-file test).
5. Backfill: one-off admin bulk re-extraction (existing scoped-run UI) over rows where `raw_text` shows Wijesekara indicators (`is_wijesekara_encoded(raw_text)` as the selection predicate).

## §6.5 + §9.8.5 — Assert heavy runtime artifacts at startup

**Plan:** a single `app/m1/health.py` with `check_extraction_runtime()` returning `{tesseract: ok|missing, tesseract_langs: [eng,sin,tam], fasttext_model: ok|missing(path), surya: enabled|stub}`:

1. Called at **worker** startup (`worker_ready` Celery signal) — log CRITICAL + set a degraded flag; do not crash (extraction of EN text PDFs still works without Tesseract).
2. Exposed at `GET /api/v1/admin/m1/pipeline/health` → surfaced as a banner in the existing pipeline observability portal (red if any component missing).
3. CI: a `docker build` job step runs `python -c "from app.m1.health import check_extraction_runtime as c; import sys; sys.exit(0 if all(...) else 1)"` inside the production image — the "image actually ships Tesseract+langs+model" property becomes a build gate.

## §6.2 — Archive raw PDF bytes (link-rot insurance)

**Plan:** keep in-memory extraction, add a write-through archive:

1. Settings: `M1_PDF_ARCHIVE_ENABLED`, `M1_PDF_ARCHIVE_BUCKET` (S3-compatible; MinIO locally — boto3 already a transitive dep, else add `aioboto3`).
2. In `extract_gazette`, after the httpx fetch succeeds: `put_object(key=f"m1/raw/{source_id}/{gazette_number_slug}.pdf", bytes)` — fire-and-forget with retry; archive failure logs but never fails extraction.
3. Migration: `m1_regulations.raw_pdf_object_key` (nullable). Re-extraction order: archive → `download_url` → `extraction_failed` with `last_error="source and archive both unavailable"`.
4. Backfill task for existing `preprocessed` rows (fetch while links still live — this is the urgent half; schedule it soon after ship).
5. Retire `reconcile_raw_pdfs` once backfill coverage ≥95% (tracked in the pipeline portal completeness view).

## §6.6 — Metadata confidence + review queue

**Plan:** `metadata_extractor.py` returns per-field `(value, confidence, pattern_id)` instead of bare values (confidence from which regex tier matched + sanity checks: date within [gazette_date−30d, +365d], penalty range ordered, act name in known-acts list). Persist as `m1_regulations.metadata_confidence` JSONB. Rows with any field < 0.7 get `needs_metadata_review=true` → new tab in the existing completeness/pipeline portal listing them with inline edit (PATCH already exists + audit). No new ML — this is plumbing confidence that the regex tiers already imply.

## §6.4 — Continuous extraction-quality monitoring

**Plan:** monthly Celery Beat task `extraction_quality_probe`: sample N=25 recent `preprocessed` rows → recompute CID-marker count, empty/short-text ratio, fastText confidence distribution, per-field metadata completeness → write one `m1_measurement_runs`-style row → dashboard sparkline in the measurement UI; alert (existing M1 alerts channel) when any metric degrades >2σ from the trailing 6-run mean. Reuses the Slice-7 measurement machinery — this is scheduling + thresholding, not new metrics. Fold §9.8.3 here: log unknown-legacy-font names seen per run; a new name appearing = signal to grow the 12-font list and cut `wijesekara_routing_v1.1`.

## §6.7 — Freeze the chunk contract before Phase 3

**Plan:** define `ChunkRecord` (Pydantic: `text`, `index`, `char_span`, `language`, `source_regulation_id`, `token_estimate`) in `enigmatrix-ml/m1/preprocessing/chunk_schema.py`; make `chunking.py` emit it; golden-file test freezes the output for 3 fixture docs; Phase-3 classifier imports the same model. One session, prevents a silent contract drift that would otherwise surface mid-Phase-3.

## §6.1 — gazette.lk second source

**Plan (Step-2c hardening, do last):** ASP.NET viewstate site → subclass `_base` with an overridden request flow: GET the search page, harvest `__VIEWSTATE`/`__EVENTVALIDATION`, emit `FormRequest` postbacks per results page. No headless browser — Scrapy `FormRequest` reproduces the postback. Dedupe is free (UNIQUE `gazette_number` + existing `DropItem`). Feature-flag the spider out of Beat until the canary (extend `SPIDERS` list in the live test) is green for two consecutive scheduled runs. Risk: viewstate churn — the canary catches it, same as documents.gov.lk drift.

## §9.8.2 — Surya (unchanged)

Stays Phase 3 (GPU-gated). Only note: §6.5's health check reports it as `stub` so nobody assumes the fallback exists in prod.

## §9.8.4 — Legacy Tamil fonts

**Plan:** one-off audit — sample 20 pre-2010 TA gazettes, run `is_wijesekara_encoded`-style indicator analysis on extracted TA text; if legacy encodings appear, replicate the `font_aware_wijesekara` machinery with Tamil maps (Bamini/Baamini families are the likely suspects); if not, close the gap as "not present in corpus" with the audit as evidence.
