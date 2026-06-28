# Plan: Completeness check + re-fetch + spider EN→SI→TA language fallback

## Context

User manually compared the source website's published gazette list against the DB across two months — found a 12% miss rate in Feb 2026 (25 of 207 missing) and a 40% miss rate in Jan 2026 (103 of 260 missing, including a 10-day blackout Jan 19-28). Substantive regulatory gazettes were in the gap (Emergency Regulation No. 01/2026, PUCSL tariff rules, etc).

Separately: the existing `gazette_spider.py` dropped any URL ending `_s.pdf` / `_t.pdf` — so Sinhala-only and Tamil-only gazettes were silently ignored.

Planning questions confirmed: language storage → fallback EN→SI→TA (no schema change), verification → both manual button + auto-trigger on terminal, missing items → table with per-row + bulk Re-fetch, unlinked rows → show all known fields with "unparsed" pills.

## Goal

Detect gazettes the source publishes but the DB doesn't have; let an admin re-fetch missing items per-row or in bulk. Ingest Sinhala-only / Tamil-only gazettes that the spider was previously dropping.

## Scope

- **In:** New backend service + endpoints, new typed frontend API client, new MissingGazettesPanel component, spider rewrite to pick best-available language.
- **Out:** Per-language `raw_text_en` / `_si` / `_ta` columns (schema migration deferred — user explicitly chose against), auto-enqueue without user confirmation, missing-panel showing per-row refetch progress (handled by existing summary polling).

## Steps

1. **Backend** — `app/services/m1_completeness_check.py` (~265 lines):
   - `_YEAR_LISTING_TEMPLATES` dict per source (EGZ/GZ/BILL/ACT).
   - `_NUMBER_RE` dict per source (gazette-style `NNNN/NN` vs `Bill No. N` vs `Act No. N of YYYY`).
   - `fetch_website_rows(source_id, year)` — httpx + lxml fetch; group anchors by `document_number` preferring EN for the displayed URL.
   - `find_missing(*, source_id, date_from, date_to, session)` — fetch rows, filter to scope, SELECT existing `m1_gazette_items.document_number`, return list of dicts (`document_number`, `document_date`, `title`, `download_url`, `source_url`, `unparsed_fields`).
2. **Backend** — `app/api/v1/m1_completeness.py` (~382 lines):
   - `POST /verify/{task_id}` — looks up run by task_id, calls `find_missing`.
   - `POST /verify` — `{source_id, date_from, date_to}` payload; same call.
   - `POST /refetch-missing` — inserts `m1_regulations` + `m1_gazette_items` rows mirroring `M1RegulationsInsertPipeline._insert_rows`, then enqueues `extract_gazette.delay(...)`. Returns per-row outcomes: `queued | duplicate | missing_download_url | error`.
   - Pydantic schemas: `MissingItemOut`, `VerifyResultOut`, `VerifyByScopeIn`, `RefetchMissingIn`, `RefetchOneOut`, `RefetchMissingOut`.
3. **Backend** — register router in `app/api/v1/router.py` under `prefix="/admin/m1/extraction"`.
4. **Frontend** — `lib/api/m1-completeness.ts` typed API client with `verifyByTask`, `verifyByScope`, `refetchMissing`.
5. **Frontend** — `components/m1-extraction/missing-gazettes-panel.tsx` (~372 lines):
   - "Verify completeness" button.
   - `autoVerifyTrigger` prop — fires once on Celery terminal (guarded by `autoRan` ref).
   - Result banner (success tone when no gaps, warning tone with count).
   - Missing-items table with `unparsed` pills + per-row "Re-fetch" button + header "Re-fetch all" bulk action.
   - "Refetch summary" block showing `queued / duplicates / skipped` + expandable errors.
6. **Frontend** — wire panel into `app/(admin)/admin/m1/pipeline/sources/[sourceId]/extraction/page.tsx` via python-atomic-write (import + render block above `<ExtractionSummaryCard>` with `autoVerifyTrigger={isTerminal}`).
7. **Spider** — `scraper/spiders/gazette_spider.py`:
   - Replace "drop `_s.pdf` / `_t.pdf` suffixes" filter with buffer-then-pick.
   - `_LANG_PRIORITY = {"en": 0, "si": 1, "ta": 2}` class constant.
   - `_language_for(url) -> str` static helper.
   - Rewrite `parse()` to collect into `best_by_number[document_number] = (priority, item_dict)`; yield one `GazetteItem` per group.
   - Anchors with no language suffix → treated as English-priority (back-compat for test fixtures + pre-multilang docs).

## Decisions taken

- Endpoints in their own module (`m1_completeness.py`) rather than appended to the 1000+ line `m1_gazette_extraction.py` — keeps edit safety on the Windows-mounted FS.
- Year-listing URL templates are deliberately duplicated between spider and completeness service — avoids importing the Scrapy module from the API request path.
- Refetch inserts rows mirroring `M1RegulationsInsertPipeline._insert_rows` so DB shape matches spider-created rows exactly.
- Display name for live-feed events uses `gazette_item.document_number` (the actual column name; not `gazette_number`).

## Open questions / risks

- documents.gov.lk is government infrastructure and slow; the verify HTTP fetch needs a generous timeout. Addressed in the follow-up hardening session.
- Refetch panel reflects queued counts but doesn't itself stream per-row progress — that flows through the existing summary polling.

## Acceptance criteria

- Verify button + auto-trigger return the missing list with `document_number / date / title / source_url`.
- Re-fetch (per-row or bulk) inserts rows + enqueues extract_gazette; new rows show up in the polled summary on the next 5s tick.
- Spider ingests Sinhala-only / Tamil-only gazettes that previously got dropped; English-priority preserved when all three exist.
- Existing Session-23 integration test still passes after the spider rewrite.

## Linked trackers

- [CHANGES.md](../CHANGES.md)
- [FEATURES.md](../FEATURES.md) — F-177
- [SESSIONS.md](../SESSIONS.md) — Session 50
