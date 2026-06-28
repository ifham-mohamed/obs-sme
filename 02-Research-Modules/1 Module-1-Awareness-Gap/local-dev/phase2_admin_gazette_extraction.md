---
tags: [tracker, m1, local-dev, phase2, admin]
source: synthesised
layer: tracker
module: m1
---

# Phase 2 — Admin Gazette Extraction trigger (what runs when the admin clicks "Start extraction")

> **Shipped:** Session 38 / F-161.
> **Finding-detail:** [findings/2026-05-17-m1-admin-gazette-extraction.md](../findings/2026-05-17-m1-admin-gazette-extraction.md).
> **Predecessors:** [phase2_step2a_scrapy_spider.md](phase2_step2a_scrapy_spider.md), [phase2_step2b_celery_extract.md](phase2_step2b_celery_extract.md), [phase2_step2e_preprocessing.md](phase2_step2e_preprocessing.md), [phase2_step2f_celery_wiring.md](phase2_step2f_celery_wiring.md).

## ⚠️ Are you on Aiven cloud Postgres? (read first)

If `DATABASE_URL` in `enigmatrix-backend/.env` points at `*.aivencloud.com` (or any other managed cloud Postgres), the docker-compose `max_connections=200` override doesn't apply — your app talks to the cloud DB, not the local container. **Aiven entry-tier plans cap total connections at ~20-25.** Use the smaller engine pool already shipped in `app/db/session.py` (`pool_size=1, max_overflow=2, pool_timeout=10`) AND run Celery with:

```bash
uv run celery -A app.celery_config worker -l info --concurrency=2
```

Math: `2 workers × (1+2) + uvicorn × (1+2) = 9 conns peak` — fits in Aiven's 20-conn budget. With the default `--concurrency=8` you'd request `8×3 + 3 = 27 conns`, exceed Aiven's cap, and hit `asyncpg TimeoutError` / `TooManyConnectionsError`.

If you're on local docker Postgres only, you can raise the pool back to `(pool_size=2, max_overflow=3)` and skip `--concurrency=2` — the local container is configured for `max_connections=200` (Session 40 / F-166).

## 1 · What this feature does

Adds an admin-only "Gazette Extraction" page at `/admin/m1/pipeline/extraction` (sidebar entry under the existing M1 Pipeline group). Admin picks:

- **Date range** (Session 42 / F-169 — single popover-triggered calendar with `mode="range"`). Click a start date + an end date inside the same calendar year. Two-month side-by-side calendar inside the popover. Trigger button shows the current range as `Jan 15, 2026 → Feb 28, 2026`.
- **Quick-pick chips** above the calendar: `Last 7 days · Last 30 days · This year · Q1 · Q2 · Q3 · Q4` — each writes a complete range with one click.
- Client-side validation enforces: both ends selected, `from ≤ to`, same calendar year, year ∈ [2010, today].

Clicking "Start extraction":

1. Frontend `POST /api/v1/admin/m1/extraction/trigger` with `{ date_from: "YYYY-MM-DD", date_to: "YYYY-MM-DD" }` (ISO strings).
2. Backend enqueues `run_gazette_spider.delay(date_from_iso, date_to_iso)` to Celery → returns the Celery `task_id`.
3. Celery worker picks up the task → invokes `scrapy crawl gazette_spider -a date_from=YYYY-MM-DD -a date_to=YYYY-MM-DD` as a subprocess.
4. Scrapy spider derives the year from `date_from`, crawls `https://documents.gov.lk/view/egz/egz_<year>.html`, and filters rows by the bounded date range (out-of-scope rows are dropped **before** PDF download — efficient).
5. For each in-scope row: `PDFDownloadPipeline` saves the PDF → `M1RegulationsInsertPipeline` INSERTs an `m1_regulations` row with `status='ingested'` → calls `extract_gazette.delay(reg_id)`.
6. `extract_gazette` picks up the row → runs the PDF extraction chain → flips `status='extracted'` → enqueues `preprocess_gazette.delay(reg_id)`.
7. `preprocess_gazette` runs cleaning + metadata + chunking + segmenter → flips `status='preprocessed'` → writes `m1_regulation_penalties` + `m1_sub_documents` rows.

Frontend polls `GET /api/v1/admin/m1/extraction/status/{task_id}` every 5 s (visibility-paused) until terminal state. On `SUCCESS`, surfaces a "View recent runs →" link to the existing `/admin/m1/pipeline/recent` page (F-160 portal) where rows progress through `ingested → extracted → preprocessed`.

## 2 · Five services to start (in this order)

The end-to-end flow has 5 moving parts. Start them in this order — earlier services are dependencies of later ones.

### 2.1 · Postgres + Redis containers (Docker)

```bash
cd ~/repos/xyz   # or /mnt/c/Reasearch/xyz
docker compose -f docker-compose.dev.yml up -d postgres redis
docker ps
```

Expected: both `enigmatrix-postgres` and `enigmatrix-redis` show `Up … (healthy)`.

### 2.2 · Alembic migrations (one-time per fresh DB)

```bash
cd ~/repos/xyz/enigmatrix-backend
uv run alembic upgrade head
```

Expected: ends at the latest migration (the M1 chain through `202605260001_m1_sub_documents`).

### 2.3 · Celery worker (terminal A)

```bash
cd ~/repos/xyz/enigmatrix-backend
uv run celery -A app.celery_config worker -l info
```

Expected: stdout shows `[tasks]` block listing `app.tasks.m1.gazette_scraper.run_gazette_spider`, `app.tasks.m1.extract_gazette.extract_gazette`, `app.tasks.m1.preprocess_gazette.preprocess_gazette_task`, etc., then `celery@<hostname> ready.`.

#### 2.3.1 · ⚠️ Restart the worker after editing any task file

The Python interpreter caches imports at worker boot. Edits to `app/tasks/**` or the spider don't take effect until the worker is restarted — until you do, calls hit the stale function (e.g. you'll see `TypeError: takes 1 positional argument but 4 were given` when the new task signature is on disk but the worker is running the pre-edit version).

```bash
# Ctrl+C in the worker terminal, then re-run:
uv run celery -A app.celery_config worker -l info
```

**Optional dev convenience** — auto-restart on file change (needs `watchdog`):

```bash
uv pip install watchdog   # one-time
uv run watchmedo auto-restart --recursive --patterns="*.py" \
  --directory=app -- celery -A app.celery_config worker -l info
```

Don't ship `watchmedo` to production; it's a dev-loop optimisation.

### 2.4 · FastAPI backend (terminal B)

```bash
cd ~/repos/xyz/enigmatrix-backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected: `Uvicorn running on http://0.0.0.0:8000` + `Application startup complete.`.

### 2.5 · Frontend dev server (terminal C — PowerShell on Windows)

```powershell
cd C:\Reasearch\xyz\enigmatrix-frontend
pnpm dev
```

Expected: `▲ Next.js 14.2.13` + `- Local: http://localhost:3000` + `✓ Ready`.

## 3 · End-to-end flow when admin clicks "Start extraction"

This is the 7-hop chain. Each hop happens in a different process/service — watching all five terminals tells you where you are.

```
┌──────────────────┐  POST /api/v1/admin/m1/extraction/trigger
│ Frontend (3000)  │ ──────────────────────────────────────────────────┐
│ Combobox form    │                                                   │
└──────────────────┘                                                   ▼
                                                          ┌─────────────────────┐
                                                          │ FastAPI (8000)      │
                                                          │ require_admin gate  │
                                                          │ _validate_scope()   │
                                                          │ run_gazette_spider  │
                                                          │   .delay(y, ms, me) │
                                                          └─────────┬───────────┘
                                                                    │ task pushed to Redis
                                                                    ▼
┌──────────────────┐                                      ┌─────────────────────┐
│ Redis (6379)     │ ◀──────  Celery broker  ──────────▶  │ Celery worker       │
│ Broker + result  │                                      │ run_gazette_spider  │
│ backend          │ ──────  AsyncResult status  ──────▶  │   subprocess.run    │
└──────────────────┘                                      └─────────┬───────────┘
                                                                    │ scrapy crawl … -a year=… -a month_start=… -a month_end=…
                                                                    ▼
                                                          ┌─────────────────────┐
                                                          │ scrapy subprocess   │
                                                          │ GazetteSpider       │
                                                          │ documents.gov.lk    │
                                                          │ /view/egz/egz_<y>   │
                                                          │ _in_scope() filter  │
                                                          └─────────┬───────────┘
                                                                    │ in-scope rows only
                                                                    ▼
                                                          ┌─────────────────────┐
                                                          │ PDFDownloadPipeline │
                                                          │ writes raw/<gz>.pdf │
                                                          └─────────┬───────────┘
                                                                    │
                                                                    ▼
                                                          ┌─────────────────────┐
                                                          │ M1RegulationsInsert │
                                                          │ Pipeline            │
                                                          │ INSERT ... status   │
                                                          │   ='ingested'       │
                                                          │ extract_gazette     │
                                                          │   .delay(reg_id) ───┼─┐
                                                          └─────────────────────┘ │
                                                                                  │ task enqueued
                                                                                  ▼
                                                          ┌─────────────────────┐
                                                          │ Celery worker       │
                                                          │ extract_gazette     │
                                                          │ → status='extracted'│
                                                          │ preprocess_gazette  │
                                                          │   .delay(reg_id) ───┼─┐
                                                          └─────────────────────┘ │
                                                                                  │
                                                                                  ▼
                                                          ┌─────────────────────┐
                                                          │ Celery worker       │
                                                          │ preprocess_gazette  │
                                                          │ → 'preprocessed'    │
                                                          │ writes penalties +  │
                                                          │ sub_documents       │
                                                          └─────────────────────┘
```

Meanwhile, the frontend polls `GET /api/v1/admin/m1/extraction/status/{task_id}` every 5 s. The `task_id` corresponds to the `run_gazette_spider` task at the top — once it finishes (SUCCESS), the spider has finished its crawl. The downstream `extract_gazette` + `preprocess_gazette` tasks have their own task_ids and keep running after the trigger task returns SUCCESS; their state is visible at `/admin/m1/pipeline/recent`.

## 4 · Health-check checklist

Before clicking "Start extraction", verify each service is reachable:

```bash
# Postgres + Redis containers
docker ps
#   → enigmatrix-postgres  Up (healthy)  0.0.0.0:5432->5432/tcp
#   → enigmatrix-redis     Up (healthy)  0.0.0.0:6379->6379/tcp

# Postgres direct
docker exec -it enigmatrix-postgres psql -U enigmatrix_user -d enigmatrix_dev -c "SELECT version();"

# Redis direct
docker exec -it enigmatrix-redis redis-cli ping
#   → PONG

# Celery worker reachable through broker
cd ~/repos/xyz/enigmatrix-backend
uv run celery -A app.celery_config inspect ping
#   → {'celery@<host>': {'ok': 'pong'}}

# FastAPI
curl http://localhost:8000/health
#   → 200 {"status": "ok"}

# Frontend
curl -I http://localhost:3000
#   → HTTP/1.1 200 OK
```

Or visit `/admin/m1/pipeline` as admin — the overview page's `<CeleryHealthCard>` shows worker count + queue size + broker reachability live.

## 5 · What to watch in logs during a trigger

**Terminal A (Celery worker)** — should show three task pickups, in this order:

```
[tasks]
. app.tasks.m1.gazette_scraper.run_gazette_spider
. app.tasks.m1.extract_gazette.extract_gazette
. app.tasks.m1.preprocess_gazette.preprocess_gazette_task

[INFO/MainProcess] Task app.tasks.m1.gazette_scraper.run_gazette_spider[…] received
[INFO/MainProcess] run_gazette_spider: launching scrapy in /…/enigmatrix-backend (scope: year=2024 months=3..5)
[INFO/MainProcess] run_gazette_spider: scrapy completed cleanly (scope: year=2024 months=3..5)
[INFO/MainProcess] Task app.tasks.m1.gazette_scraper.run_gazette_spider[…] succeeded

[INFO/MainProcess] Task app.tasks.m1.extract_gazette.extract_gazette[…] received
[INFO/MainProcess] extract_gazette: regulation <uuid> extracted via pymupdf (12345 chars)
[INFO/MainProcess] Task app.tasks.m1.extract_gazette.extract_gazette[…] succeeded

[INFO/MainProcess] Task app.tasks.m1.preprocess_gazette.preprocess_gazette_task[…] received
[INFO/MainProcess] preprocess_gazette: regulation <uuid> preprocessed (cleaned_text=N chars, penalties=M, sub_documents=K, primary_language=en)
[INFO/MainProcess] Task app.tasks.m1.preprocess_gazette.preprocess_gazette_task[…] succeeded
```

The last two tasks repeat once per in-scope gazette PDF the spider found.

**Terminal B (FastAPI)** — shows the POST + the polling GETs:

```
INFO:     127.0.0.1:… - "POST /api/v1/admin/m1/extraction/trigger HTTP/1.1" 202 Accepted
INFO:     127.0.0.1:… - "GET /api/v1/admin/m1/extraction/status/<task_id> HTTP/1.1" 200 OK
…
```

**Terminal C (frontend)** — should be quiet except for the `pnpm dev` HMR lines. The actual UI feedback is in the browser.

## 6 · Verify rows in SQL

After SUCCESS, confirm the in-scope rows landed:

```sql
SELECT
  regulation_short_code,
  gazette_number,
  gazette_published_date,
  status,
  amendment_type,
  length(raw_text) AS raw_len,
  length(cleaned_text) AS clean_len
FROM m1_regulations
WHERE gazette_published_date BETWEEN '2024-03-01' AND '2024-05-31'
ORDER BY created_at DESC
LIMIT 20;
```

Expected: rows have `status='preprocessed'`, `cleaned_text` non-empty, `amendment_type` populated. `gazette_published_date` should fall entirely within the picked range.

To confirm penalties + sub-documents wrote:

```sql
SELECT r.gazette_number, COUNT(p.*) AS penalties, COUNT(s.*) AS sub_docs
FROM m1_regulations r
LEFT JOIN m1_regulation_penalties p ON p.regulation_id = r.regulation_id
LEFT JOIN m1_sub_documents s ON s.regulation_id = r.regulation_id
WHERE r.gazette_published_date BETWEEN '2024-03-01' AND '2024-05-31'
GROUP BY r.gazette_number
ORDER BY r.gazette_number;
```

## 7 · Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| **"Start extraction" button stays disabled** even after page loads | Frontend `fetch("/api/auth/token")` returned `{ access }` but the page tried to read `d.accessToken`. (Fixed in this page; latent in 6 other M1 pages.) | Reload the page after signing in. If still disabled, check DevTools Network tab → `/api/auth/token` response. |
| **POST returns 400** | `_validate_scope` rejected the input: year < 2010, year > today, month outside 1–12, or `month_start > month_end`. | Check the response body — the error message names the failed check. Fix the form and retry. |
| **POST returns 401/403** | Not signed in as admin. | Sign in as a user with `role='admin'`. Use `seed_dev.py` if you need to create one. |
| **Status panel stays at "Queued" (PENDING) for > 30 s** | Celery worker isn't running OR can't reach Redis. | Terminal A: confirm `celery@<host> ready`. `docker ps` shows Redis healthy. Restart the worker. |
| **`TypeError: run_gazette_spider() takes 1 positional argument but 4 were given`** in worker log when the trigger fires | Worker was started **before** the new task signature was deployed and still holds the pre-edit 1-arg version of the function. Python imports are cached at worker boot. | `Ctrl+C` in the worker terminal → re-run `uv run celery -A app.celery_config worker -l info`. Repeat after **every** edit to any file under `app/tasks/`. See §2.3.1 for an optional `watchmedo auto-restart` recipe. |
| **Spider runs cleanly (worker says `scrapy completed cleanly`) but `m1_regulations` has zero new rows** | The chosen year + month range didn't match any gazette dates on that year-page (e.g. picked Jan 2026 when the page only lists May 2026 entries so far). Not a bug — the spider filters before download. | Open `https://documents.gov.lk/view/egz/egz_<year>.html` in a browser; pick months that have entries. Or widen to full year (From=January → To=December). If the listing URL itself 404s, that year hasn't been published yet. |
| **`extract_gazette: regulation <uuid> not found`** WARNING in worker log | Orphan task — a previous trigger / test deleted (or never committed) the row but the chained `extract_gazette.delay(reg_id)` was already queued in Redis. | Benign; the task returns `{"status": "missing"}` and the worker moves on. If the noise bothers you: `docker exec enigmatrix-redis redis-cli FLUSHDB` (clears the whole broker queue, also wipes any other pending tasks). |
| **Spider downloads the same gazette 3× then logs `DropItem`** on the 2nd + 3rd | Each table row on documents.gov.lk has 3 PDF anchors (English / Sinhala / Tamil) → spider yields 1 item per anchor → `gazette_number` UNIQUE constraint dedupes after the first insert. | Pre-existing behaviour (predates F-161). Two redundant downloads per gazette, no data corruption. Future enhancement (not scheduled): prefer the English anchor or store all three with a `language` discriminator in the unique key. |
| **Worker logs `scrapy crawl exited 1`** | Spider crashed mid-crawl (network blip, malformed HTML, etc.). | Check Terminal A — the worker captures scrapy's last 2000 chars of stdout + stderr. Retry; the `gazette_number` UNIQUE constraint makes the spider re-runnable. |
| **`docker ps` shows the containers but `docker exec` says "Cannot connect to the Docker daemon"** | Docker Desktop stopped after WSL was suspended. | Start Docker Desktop on Windows; wait for the whale icon to be solid; if it hangs > 2 min, `wsl --shutdown` from elevated PowerShell, then restart Docker Desktop. |
| **Tests fail with `asyncio.run() cannot be called from a running event loop`** | Old test pattern. | Use `_run_eager_task(task, *args, timeout)` from F-162 instead of calling `task.delay(...).get(...)` directly inside `@pytest.mark.asyncio`. |
| **FE shows FAILURE** immediately after submitting a date-range trigger, with `TypeError: '<=' not supported between instances of 'int' and 'str'` in the trace; **worker log shows `scope: year=YYYY months=N..N`** (old Session 38 format) instead of `scope: YYYY-MM-DD..YYYY-MM-DD` (new Session 42 format) | Celery worker is running pre-Session-42 bytecode. Either the worker was started before the F-169 source landed on disk, or a stale `__pycache__/*.pyc` is being preferred over the newer `.py` (WSL2 NTFS mtime quirk). When the FE sends the new `{date_from, date_to}` shape, the stale worker's old signature `(self, year, month_start, month_end)` receives strings into the int-typed `year` slot and the old `_MIN_YEAR <= year` comparison explodes. | `Ctrl+C` the worker (wait for `worker: Cold shutdown`) → clear bytecode cache `find /mnt/c/Reasearch/xyz/enigmatrix-backend -name __pycache__ -type d -exec rm -rf {} +` → re-launch `uv run celery -A app.celery_config worker -l info --concurrency=2`. **Verify by re-triggering**: worker log MUST emit `scope: 2026-01-04..2026-01-05` (or similar ISO-range format). If the old format persists, hunt leftover worker processes: `ps aux \| grep '[c]elery'` then `kill <pid>` any survivors. |
| **FE status panel still shows `STARTED`** for many minutes AFTER all in-scope regulations are already `preprocessed` in the rows list (Run summary pill shows e.g. `1m 21s` but task hasn't transitioned to SUCCESS at 10 min+) | The Celery `run_gazette_spider` task waits for the scrapy subprocess to exit. Scrapy's Twisted reactor only shuts down when its queue is empty AND all in-flight requests are retired. For a narrow scope (e.g. Jan 4–5 2026), scrapy walks the entire year listing page newest-first — even after the last in-scope item, it keeps walking remaining anchors + waiting for the reactor to drain under `DOWNLOAD_DELAY=2` + `AUTOTHROTTLE`. | Shipped in F-170 (Session 43): (a) spider's `parse()` now calls `crawler.engine.close_spider(self, "scope_exhausted")` once it walks past a row whose date is BEFORE `date_from` (the page is descending-date sorted, so no more in-scope items can appear). (b) Safety-net `CLOSESPIDER_TIMEOUT_NO_ITEM=60` in `custom_settings` — exit if 60 s elapse without yielding a new item. **To apply after pull:** restart Celery worker (Ctrl+C → re-launch with `--concurrency=2`). Worker log MUST show `closing spider (scope_exhausted): hit gazette … with date=… earlier than date_from=…` shortly after the last in-scope item; the run_gazette_spider task should transition to SUCCESS within ~1–2 min of the last download. |
| **`asyncpg.exceptions.TooManyConnectionsError: sorry, too many clients already`** (or `remaining connection slots are reserved for roles with the SUPERUSER attribute`) in worker logs during the extract→preprocess fan-out | SQLAlchemy pool sized too high relative to Postgres `max_connections`. With Celery's 8 prefork workers × 30 conns/worker (pool_size=10 + max_overflow=20), burst load exceeds 97 (default `max_connections=100` minus 3 superuser-reserved). | Shipped in F-166 (Session 40): `app/db/session.py` pool dropped to `pool_size=2, max_overflow=3, pool_recycle=300` (5 conns/worker × 8 = 40 + uvicorn ≤ 5 = 45 ≪ 200); postgres container `command: ["postgres", "-c", "max_connections=200"]` for headroom. **To apply after a pull:** `docker compose -f docker-compose.dev.yml up -d --force-recreate postgres` (re-creates the container with the new flag; volume + data preserved), then restart Celery worker + uvicorn to pick up the new pool config. Verify: `docker exec enigmatrix-postgres psql -U enigmatrix -d enigmatrix -c "SHOW max_connections;"` → `200`. |
| **`asyncpg TimeoutError`** on `/api/v1/admin/m1/extraction/summary` or `/progress` (or any API call) — the route hangs for ~60 s then returns 500 | `DATABASE_URL` points at Aiven cloud Postgres (or another managed plan with low `max_connections`); Session 40's `pool_size=2, max_overflow=3` combined with Celery `--concurrency=8` overshoots Aiven's ~20-conn cap. New asyncpg `connect()` calls then queue + time out at 60 s. | Shipped in F-168 (Session 41): `app/db/session.py` further dropped to `pool_size=1, max_overflow=2, pool_timeout=10` AND start Celery with `--concurrency=2`. See the ⚠️ callout at the top of this doc for the math. After pulling: restart Celery worker (with the new `--concurrency=2` flag) and uvicorn to pick up the new pool config. |
| **Pipeline-flow tiles show 0 rows even after a successful crawl** (e.g. "2a Scrapy: 0 rows", "2b extract: 0 rows", but "2e/2f preprocessed: 448 rows" — the user-reported symptom that triggered F-167) | Not a bug — each tile's number is "rows **currently at** that status", and once a row finishes preprocessing it sits at `'preprocessed'` permanently, leaving 0 at every earlier status. Fixed in F-167 by surfacing a **cumulative reached** count as the headline. | Already shipped in F-167 (Session 41): tiles now read "452 reached · 0 at ingested" so the "did scrapy run?" question is answered at a glance. No action required beyond a page refresh after pulling. |

## 8 · After verifying

```powershell
graphify update C:\Reasearch\xyz
```

Updates the code-side knowledge graph after edits. Run `graphify update c:\sme` for the vault graph.

## 9 · Cross-references

- Finding-detail: [findings/2026-05-17-m1-admin-gazette-extraction.md](../findings/2026-05-17-m1-admin-gazette-extraction.md)
- Predecessor pipeline steps:
  - [phase2_step2a_scrapy_spider.md](phase2_step2a_scrapy_spider.md) — F-145
  - [phase2_step2b_celery_extract.md](phase2_step2b_celery_extract.md) — F-148
  - [phase2_step2c_extraction_chain.md](phase2_step2c_extraction_chain.md) — F-149
  - [phase2_step2d_language_wijesekara.md](phase2_step2d_language_wijesekara.md) — F-153
  - [phase2_step2e_preprocessing.md](phase2_step2e_preprocessing.md) — F-154
  - [phase2_step2f_celery_wiring.md](phase2_step2f_celery_wiring.md) — F-155
  - [phase2_session34_cleanup.md](phase2_session34_cleanup.md) — F-157
- Observability portal: `/admin/m1/pipeline` (F-160, Session 37).
- Tracker triplet: [SESSIONS.md](../../../08-Findings-Log/SESSIONS.md) · [CHANGES.md](../../../08-Findings-Log/CHANGES.md) · [FEATURES.md](../../../08-Findings-Log/FEATURES.md) (Session 38 / F-161 + F-162).
