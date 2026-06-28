---
tags: [tracker, m1, local-dev, phase2, step-2a]
source: synthesised
layer: tracker
module: m1
---

# Phase 2 Step 2a — Scrapy gazette spider (local dev)

> **Shipped:** Session 23 / F-145 (`Enigmatrixx/enigmatrix-backend@<sha>`; spider lives at `enigmatrix-backend/scraper/`).
> **Spec**: [planned-for-development/1_setup.md](../planned-for-development/1_setup.md) · [03_M1_Data_Collection](../03_M1_Data_Collection.md) §1.3 · [03_M1_1_PDF_Extraction_Chain](../03_M1_1_PDF_Extraction_Chain.md).

## 1 · What this step does

Crawls `documents.gov.lk`'s extraordinary-gazette listing → downloads gazette PDFs to `storage/m1/raw/` → INSERTs one `m1_regulations` row per gazette with `status='ingested'`. Celery dispatch (to chain Step 2b extraction) is wired but lazy-tolerant — works without a live broker.

## 2 · Prerequisites

- Backend ready per [backend/SETUP/00_LOCAL_DEV_WSL §1-§5](../../../04-Technology-Stack/backend/SETUP/00_LOCAL_DEV_WSL.md).
- Postgres container running (`docker compose ps`).
- Migration `202605220001_m1_regulations_status_columns.py` applied (adds `status` + `raw_pdf_path` + `gazette_number` columns).

```bash
cd ~/repos/xyz/enigmatrix-backend
uv run alembic upgrade head   # idempotent — confirms 202605220001 is applied
```

## 3 · Run the integration tests (no network)

```bash
uv run pytest app/tests/integration/test_gazette_spider.py -v
```

Expected: **4 passed**:
- `test_spider_parse_yields_gazette_item` — XPath extracts the gazette number + PDF URL.
- `test_pdf_download_pipeline_writes_file` — PDF download step writes to `storage/m1/raw/`.
- `test_db_insert_pipeline_creates_row` — INSERT pipeline writes one m1_regulations row.
- `test_duplicate_pipeline_skips_idempotently` — re-running the same gazette doesn't duplicate.

If any fail, the spider definition has drifted from the test expectations — investigate `enigmatrix-backend/scraper/spiders/gazette_spider.py`.

## 4 · Manual real-network smoke (~30s)

```bash
cd ~/repos/xyz/enigmatrix-backend
uv run scrapy crawl gazette_spider -s CLOSESPIDER_PAGECOUNT=2 -L INFO
```

- `CLOSESPIDER_PAGECOUNT=2` rate-limits to 2 pages of the listing (≈ 5-10 PDFs); without it the spider walks the whole index.
- Expected stdout: scrapy log lines showing the PDFs being fetched + DB INSERTs.

Watch the log for:

```
[scrapy.pipelines.files] File ... downloaded
[scraper.pipelines] M1RegulationsInsertPipeline: inserted m1_regulations row for gazette 2491/14
```

## 5 · Verify the result

```bash
# Inside WSL — open psql:


```

```sql
-- Count ingested rows
SELECT count(*) FROM m1_regulations WHERE status = 'ingested';

-- Inspect the freshest entries
SELECT regulation_id, regulation_short_code, gazette_number, raw_pdf_path, status, created_at
FROM m1_regulations
WHERE status = 'ingested'
ORDER BY created_at DESC
LIMIT 5;
\q
```

PDFs on disk:

```bash
ls -la ~/xyz/enigmatrix-backend/storage/m1/raw/
# Expect: gazette_NNNN_NN.pdf files matching the rows you saw in psql
```

## 6 · Troubleshooting

| Symptom                                            | Cause                              | Fix                                                                                                               |
| -------------------------------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `0 items scraped` on real network                  | Site layout changed OR XPath drift | Re-check `gazette_spider.py:parse()` XPath against `documents.gov.lk/view/egz/egz_2026.html`                      |
| `DropItem: duplicate gazette_number`               | Already-ingested row               | Expected — the pipeline is idempotent; no action needed                                                           |
| `OperationalError: could not connect`              | Postgres container not up          | `docker compose -f ~/repos/xyz/docker-compose.dev.yml up -d postgres`                                             |
| `enigmatrix-backend/storage/m1/raw/` doesn't exist | First run; pipeline auto-creates   | Re-run the spider; verify `STORAGE_LOCAL_PATH=./storage` in `.env`                                                |
| `WARNING: failed to enqueue extract_gazette`       | No Celery broker running           | Expected in dev without Redis worker; rows stay at `status='ingested'` — Step 2b's worker will pick them up later |

## 7 · After verifying, the standing cadence

```bash
# Update vault triplet — append a "Session N: ran Step 2a locally" entry if useful (optional for dev smoke; required when you actually ship a change).
# Then:
graphify update C:\Reasearch\xyz
graphify update C:\sme
```

## 8 · Cross-references

- [planned-for-development/1_setup.md](../planned-for-development/1_setup.md) — full spec + verification per Session 24/25 plan
- [phase2_step2b_celery_extract](phase2_step2b_celery_extract.md) — next step (Celery wiring + extraction)
- [03_M1_Data_Collection](../03_M1_Data_Collection.md) §1.3 — Scrapy framework rationale