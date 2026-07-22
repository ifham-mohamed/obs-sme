# Enigmatrix (`xyz/`) — Complete Setup Guide & User Manual

**Generated:** 2026-07-15 · **updated 2026-07-21** for the Session 64–71 gap-closure work (font-aware auto-chain, quality probe, runtime health check, metadata/classifier review queues, `m1_sources` registry + SMS, migrations `202607210001–006`) · verified against the actual repo at `C:\Reasearch\xyz` (root Makefile, `docker-compose.dev.yml`, `.env.example`, pyprojects, submodule Makefiles — not against assumptions).
**Audience:** anyone standing the project up from scratch on Windows, in **PowerShell** and/or **WSL Ubuntu**, through to running every pipeline end-to-end.
**Companions:** `01_MASTER_PROJECT_OVERVIEW.md` (what the system is) · `04_API_AND_PAGES_REFERENCE.md` (every route/page) · `05_MANUAL_TESTING_GUIDE.md` (how to verify features) · `PHASE1`–`PHASE5_*_ANALYSIS.md` (per-phase deep dives) · `PHASE2_GAP_CLOSURE_PLAN.md` + the per-gap plan docs (what the Session 64–71 fixes did and how to verify them).

> **PowerShell vs WSL — the honest rule.** Everything *core* (Docker services, backend API, frontend, migrations, unit tests) runs fine from PowerShell. Three things want WSL/Linux: **OCR system packages** (Tesseract + poppler install cleanly via apt), **backend integration tests** (testcontainers needs a Linux Docker socket), and **Label Studio** (happiest on Linux/venv). Commands below are shown for both wherever they differ.

---

## 1. What Each Folder Is (scope + why it exists)

| Folder | What | Why it exists |
|---|---|---|
| `enigmatrix-backend/` | FastAPI app: 26 routers (~130 routes), SQLAlchemy 2.0 async models, Alembic migrations, 38 services, Celery tasks + Beat, Scrapy spiders, data-quality suites | The platform server: auth/RBAC/audit, surveys, and the whole M1 pipeline ops surface. Scrapy lives here (not in ml) because spiders write directly to the DB |
| `enigmatrix-frontend/` | Next.js 14 App Router: 90+ pages, shadcn-pattern UI, next-intl EN/SI/TA | All user surfaces: SME app, admin portal, knowledge portal, alerts page |
| `enigmatrix-ml/` | Python package `m1`: `extraction/` (PDF→text engines+profiles), `preprocessing/`, `evaluation/` (accuracy metrics), `data/` (samplers), `model/` (XLM-R+LoRA, ONNX), `research/` (notebooks) | ML logic is a standalone installable package so the backend imports it as a library (uv workspace member) and research code stays backend-independent |
| `enigmatrix-docs/` | MkDocs site: 61+ M1 design docs, BUILD plans, tracker | The engineering design record — specs the code was built against |
| `enigmatrix-infrastructure/` | infra configs | Deployment scaffolding (largely superseded by Railway/Vercel) |
| `graphify-out/` | knowledge graph (11,284 nodes · 731 communities) + wiki | AI-assistant navigation map. Rebuilt 2026-07-21 (commit `23b3dc21`) — refresh with `graphify update .` after the Session 64–71 code changes if `git rev-parse HEAD` has moved |
| `research/data/` | Label Studio XML config, calibration set, labeling batches | Phase-3 annotation assets (versioned, unlike `mydata/`) |
| `scripts/` | cross-repo scripts: `sample_for_labeling.py`, `regenerate_thesis_tables.py` | Operate on multiple submodules at once, so they live at root |
| `storage/` | raw gazette PDFs + models (126 MB) | Pipeline working storage (`STORAGE_LOCAL_PATH`); fastText model lands in `storage/models/m1/baseline/` |
| `mydata/` | **live Label Studio instance data** (sqlite + media) | Your Phase-3c annotation environment. Untracked — back it up |
| `data/thesis/` | generated thesis tables/figures | Output of `make thesis-artifacts` |
| Root files | `Makefile`, `docker-compose.dev.yml`, `.env.example`, `pyproject.toml` + `uv.lock` (uv **workspace**: backend + ml share one resolution), `AGENTS.md`/`CLAUDE.md`/`AI_WORK_LOG.md` (AI context), `venv/` (stale — removable) | Monorepo glue |

⚠️ **Known trap:** the **root** `Makefile`'s `migrate`, `seed`, `dev-backend`, `dev-frontend`, `test`, `lint` targets `cd backend`/`cd frontend` — folders that **don't exist** (they're `enigmatrix-backend`/`enigmatrix-frontend`). `make up`/`make down` work. For the broken targets, either run the per-repo commands in §5–§7 (what this manual shows), fix the Makefile paths, or create junctions:
```powershell
cd C:\Reasearch\xyz
New-Item -ItemType Junction -Path backend  -Target .\enigmatrix-backend
New-Item -ItemType Junction -Path frontend -Target .\enigmatrix-frontend
```

---

## 2. Prerequisites (install once)

| Tool | Version | PowerShell install | WSL Ubuntu install |
|---|---|---|---|
| Docker Desktop | latest | `winget install Docker.DockerDesktop` (enable WSL2 backend) | uses Windows Docker Desktop (enable WSL integration in Docker settings) |
| Python | **3.11 or 3.12** (`>=3.11,<3.13` — 3.13 will not resolve) | `winget install Python.Python.3.12` | `sudo apt install python3.12 python3.12-venv` |
| uv | latest | `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 20 LTS | `winget install OpenJS.NodeJS.LTS` | `sudo apt install nodejs npm` (or nvm) |
| pnpm | latest | `npm install -g pnpm` | `npm install -g pnpm` |
| Git | latest | `winget install Git.Git` | `sudo apt install git` |
| GNU Make | any | `winget install GnuWin32.Make` (or use WSL for make) | preinstalled |
| Tesseract 5 + languages | 5.3.x | `winget install UB-Mannheim.TesseractOCR` then add `C:\Program Files\Tesseract-OCR` to PATH; install `sin`+`tam` traineddata into `tessdata\` | `sudo apt install tesseract-ocr tesseract-ocr-sin tesseract-ocr-tam` |
| Poppler (pdf2image) | any | `winget install oschwartz10612.Poppler` + add `bin` to PATH | `sudo apt install poppler-utils` |

Verify: `docker --version` · `uv --version` · `python --version` · `node --version` · `pnpm --version` · `tesseract --version` (should list `sin`, `tam` under `tesseract --list-langs`).

---

## 3. Clone & Configure

```powershell
# PowerShell (WSL: identical, use a Linux path like ~/xyz)
git clone <repo-url> xyz
cd xyz
git submodule update --init --recursive     # backend/frontend/ml/docs/infra are submodules

# Environment file — root .env feeds docker compose + backend
Copy-Item .env.example .env                  # WSL: cp .env.example .env
```

Edit `.env` — the two REQUIRED values are `APP_SECRET_KEY` and `JWT_SECRET` (32-byte hex):

```powershell
# generate secrets — PowerShell:
python -c "import secrets; print(secrets.token_hex(32))"   # run twice, paste into .env
```

Key `.env` entries (root `.env.example` is the reference; backend has its own superset with `DB_SSL`):

| Var | Dev value | Note |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://enigmatrix:devpass@localhost:5432/enigmatrix` | **must** keep the `+asyncpg` driver |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | must be a JSON array, even for one origin |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | broker + result backend (same Redis) |
| `STORAGE_BACKEND` / `STORAGE_LOCAL_PATH` | `local` / `./storage` | raw PDFs + models land here |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | frontend → backend |
| `M1_MODEL_ONNX_DIR` | *(unset until Phase 3d model exported)* | enables `classify_gazette`; empty ⇒ health reports `classifier: no_model` (Session 70) |
| `M1_DEFAULT_EXTRACTION_PROFILE` | `wijesekara_routing_v1` (default) | **Session 69** — the font-aware profile the auto-chain runs first; set `""` for the legacy chain (instant rollback, no deploy) |
| `M1_LID_MODEL_PATH` | *(optional override)* | resolves `lid.176.bin`; in the prod image it is baked to `/opt/models/` and this is set at build time (Session 66). Local dev: else falls back to `storage/models/m1/baseline/` |
| `SENDGRID_API_KEY` / `TWILIO_*` / `ALERT_EMAIL_FROM` | *(optional)* | without keys, email/SMS alerts return `skipped` (dev-safe); in-app alerts still work. **SMS also requires** `sme_profiles.phone` + `alert_sms_opt_in=true` per SME (Session 71) |

Also copy the env into the backend: `Copy-Item .env enigmatrix-backend\.env` (backend reads its own `.env` when run from its folder).

---

## 4. Start Infrastructure (Docker)

```powershell
cd C:\Reasearch\xyz
make up          # = docker compose -f docker-compose.dev.yml up -d postgres chromadb
docker compose -f docker-compose.dev.yml up -d redis    # Redis is defined but NOT in `make up` — start it explicitly (Celery needs it)
docker ps        # expect: enigmatrix-postgres (5432, max_connections=200), enigmatrix-redis (6379), enigmatrix-chromadb (8001)
```

Postgres runs with `max_connections=200` (headroom for the Celery prefork pool during spider→extract fan-out). ChromaDB (pinned 0.5.5 — 0.6 breaks the embedding API) is idle in the current slice but read by settings.

---

## 5. Backend Setup & Run (`enigmatrix-backend/`)

```powershell
cd C:\Reasearch\xyz\enigmatrix-backend
uv sync                          # installs backend + the enigmatrix-ml workspace member into .venv
                                 # (root pyproject declares [tool.uv.workspace] members = backend + ml)

# Database: apply ALL migrations — chain 202605080001 … 202607210006
uv run alembic upgrade head      # ⚠ pre-July DBs miss 202606300001–005 (classifier, propagation, alerts,
                                 #    lag views, retraining) AND the six Session 64–71 heads 202607210001–006:
                                 #    quality_probes · metadata_confidence · classification_chunk ·
                                 #    extraction_method_profiles · classification_source · m1_sources+SMS
uv run alembic current           # verify head
uv run python -m app.m1.health   # Session 66 — honest per-component runtime report (tesseract langs,
                                 #    lid.176.bin, ml package, surya stub, classifier readiness)
uv run python -m app.scripts.seed_dev   # seeds admin@enigmatrix.lk/admin12345 + annotator + sample SME
uv run python -m app.scripts.doctor     # optional: end-to-end auth diagnostics

# Run the API
uv run uvicorn app.main:app --reload --port 8000     # or: make dev
# → http://localhost:8000/docs (Swagger)
```

**Celery worker + Beat** (required for scraping, extraction, preprocessing, classification, watchers, alerts, analytics, retraining — separate terminals):

```powershell
cd C:\Reasearch\xyz\enigmatrix-backend
uv run celery -A app.celery_config:celery_app worker --loglevel=info --pool=solo   # PowerShell: use --pool=solo (prefork is unreliable on native Windows)
uv run celery -A app.celery_config:celery_app beat   --loglevel=info               # terminal 2 — the scheduler
```
```bash
# WSL (preferred for real extraction runs — prefork pool + clean Tesseract):
cd ~/xyz/enigmatrix-backend
uv run celery -A app.celery_config:celery_app worker --loglevel=info --concurrency=8
uv run celery -A app.celery_config:celery_app beat   --loglevel=info
```

Beat schedule (automatic once beat runs): gazette scraper every 6 h · portal/RSS watchers every 2 h · lag analytics 21:00 UTC · dataset-version retention 20:30 UTC · retraining quarterly · **extraction-quality probe monthly (1st, 04:00 UTC — Session 65)**. The **crawl canary** (Session 64) is a *GitHub Actions* schedule (Mon+Thu 02:30 UTC), deliberately NOT a Beat/PR job.

**One-time model/data downloads:**

```powershell
cd C:\Reasearch\xyz\enigmatrix-ml
uv run python scripts/download_lid_model.py   # fastText lid.176.bin (~127 MB) → storage/models/m1/baseline/ (idempotent; override path via M1_LID_MODEL_PATH)
```

**Useful DB maintenance (backend Makefile):** `make db-fresh` (wipe+migrate+seed) · `make db-truncate [TABLES=t1,t2]` · `make migrate-new name=add_foo` · `make db-check` (models-vs-migrations drift) · root `make db-shell` / `make db-users` / `make reset-db`.

---

## 6. Frontend Setup & Run (`enigmatrix-frontend/`)

```powershell
cd C:\Reasearch\xyz\enigmatrix-frontend
pnpm install                     # deps incl. chokidar/cmdk/fuse.js (knowledge portal)
pnpm dev                         # → http://localhost:3000
# other scripts: pnpm build · pnpm start · pnpm lint · pnpm typecheck ·
#                pnpm test (vitest) · pnpm e2e (playwright) · pnpm format
pnpm exec playwright install chromium        # once, before first e2e run
```

Login with the seed admin `admin@enigmatrix.lk` / `admin12345`. The knowledge portal (`/knowledge`) reads the Obsidian vault from the path configured in `lib/vault/` — historically `C:\sme`; retarget to `E:\Obsidian\sme` (canonical) or keep a one-way sync.

---

## 7. ML Package (`enigmatrix-ml/`) — extras, when and why

Base install already arrives via the backend's `uv sync` (workspace). Extras are opt-in because they're heavy:

| Extra | Contents | Install when |
|---|---|---|
| `evaluation` | openpyxl, jiwer, sentence-transformers, bert-score, rouge-score, rapidfuzz, torch | running accuracy-measurement scoring locally |
| `training` | torch, peft, datasets, scikit-learn, accelerate | Phase 3d GPU training |
| `serving` | onnxruntime | backend host that runs `classify_gazette` |
| `surya` | surya-ocr (~700 MB models) | opting into the Surya OCR fallback profile |
| `research` | pandas, numpy, scipy, jupyter, matplotlib | F1–F6 findings notebooks |

```bash
cd enigmatrix-ml
uv sync --extra evaluation            # combine as needed: --extra training --extra research
uv run pytest -q                      # extraction (12+), evaluation (19+), model, findings tests
uv run pytest tests/m1/extraction -v  # or: make test-extraction
```

**End-to-end ML workflow (after Phase-3c gold labels exist):**

```bash
uv sync --extra training
uv run python -m m1.model.data --input gold_standard.csv --out data/splits/     # temporal 70/15/15 split
uv run python -m m1.model.train_xlmr --data data/splits/ [GPU]                   # 3-seed train, gate macro-F1 ≥ 0.92
uv run python -m m1.model.eval --model <ckpt> --test data/splits/test.parquet    # per-slice F1 + cliff ≤ 8pp
uv run python -m m1.model.baselines --data data/splits/                          # TF-IDF baselines (RQ1 comparison)
uv run python -m m1.model.export_onnx --int8                                     # → ONNX; then set M1_MODEL_ONNX_DIR for the backend
uv run python scripts/retrain.py --dry-run                                       # verify the retraining loop wiring
```

---

## 8. Annotation Environment (Label Studio, Phase 3c)

```bash
# WSL recommended
python3 -m venv ~/ls-venv && source ~/ls-venv/bin/activate
pip install label-studio
LABEL_STUDIO_BASE_DATA_DIR=/mnt/c/Reasearch/xyz/mydata label-studio start   # reuses your existing instance data
```
Then in the UI: create/open the project → import `research/data/label_studio_config.xml` as the labeling config → import `research/data/calibration_set_v1.csv` (annotator calibration, κ ≥ 0.80 gate) → then `research/data/labeling/batch_01.csv` (200 docs). Generate later batches: `make labeling-batch BATCH=2` (live DB) or `make labeling-batch-demo` (synthetic). ⚠️ `mydata/` holds the sqlite DB + media for your existing instance — **back it up before upgrades**.

---

## 9. Docs Site & Knowledge Graph

```bash
cd enigmatrix-docs
pip install -r requirements.txt   # or: make install
mkdocs serve                      # → http://localhost:8000 (clashes with the API — use mkdocs serve -a localhost:8010)
```
Knowledge graph (repo root): `graphify query "<question>"` · `graphify path "A" "B"` · `graphify explain "Node"` · **`graphify update .`** after code changes (last rebuilt 2026-07-21, commit `23b3dc21`).

---

## 10. From-Scratch Quickstart (copy-paste order)

```powershell
# ── one time ──────────────────────────────────────────
git clone <repo-url> xyz; cd xyz; git submodule update --init --recursive
Copy-Item .env.example .env        # + fill APP_SECRET_KEY, JWT_SECRET
Copy-Item .env enigmatrix-backend\.env
make up; docker compose -f docker-compose.dev.yml up -d redis
cd enigmatrix-backend; uv sync; uv run alembic upgrade head; uv run python -m app.scripts.seed_dev
cd ..\enigmatrix-frontend; pnpm install
cd ..\enigmatrix-ml; uv run python scripts/download_lid_model.py
# ── every dev session (4 terminals) ───────────────────
# T1: cd enigmatrix-backend; uv run uvicorn app.main:app --reload --port 8000
# T2: cd enigmatrix-backend; uv run celery -A app.celery_config:celery_app worker --loglevel=info --pool=solo
# T3: cd enigmatrix-backend; uv run celery -A app.celery_config:celery_app beat --loglevel=info
# T4: cd enigmatrix-frontend; pnpm dev
# → http://localhost:3000  (admin@enigmatrix.lk / admin12345)
```

---

## 11. User Manual — Operating the Platform

**Roles:** `sme` (register at `/register`) · `admin` · `annotator` (both seeded).

1. **Ingest gazettes:** Admin → `/admin/m1/pipeline/extraction` → pick a date range (single calendar year per run — the scraper's rule) → trigger → watch live WebSocket progress. Re-running an overlapping range shows a repeat-crawl warning. Monitor the funnel at `/admin/m1/pipeline`; failures drill down in `/pipeline/recent`; raw PDFs at `/admin/m1/pdf-records`; per-regulation trace at `/pipeline/trace/{id}`. New in Session 64–71: **runtime health** at `GET /admin/m1/pipeline/health` (red if Tesseract/langs/`lid.176.bin`/ml-package missing), **metadata review queue** at `GET /admin/m1/pipeline/metadata-review` (low-confidence field extractions → fix via PATCH → resolve), and **source registry** at `GET/PUT/PATCH /admin/m1/pipeline/sources` (15 sources + per-source health). Newly scraped pre-2010 SI gazettes now extract font-aware by default (`wijesekara_routing_v1`); the monthly quality probe watches for silent fallback.
2. **Verify coverage:** pipeline sources page → completeness verify → re-fetch missing (EN→SI→TA fallback).
3. **Measure extraction accuracy:** `/admin/datasets/m1/new` → upload ground-truth Excel → **seal** the version (SHA-256 + auto data-quality validation) → `/admin/datasets/m1/extractions/run` (choose a profile: `legacy_v1` / `page_routing_v1` / `surya_fallback_v1` / `wijesekara_routing_v1`) → `/admin/datasets/m1/measurements/run` (baseline vs candidate, optional date scope) → inspect per-field scores, worst-N, calibration → download `/api/v1/m1/measurements/{run_id}/report.md`.
4. **Classify (after model deploy):** automatic — `preprocessed → classified` per gazette; confidence < 0.55 flags review; expert-verified rows never overwritten. Until the ONNX artifact is dropped at `M1_MODEL_ONNX_DIR`, health shows `classifier: no_model` and no model category is written. Session 70 adds `classification_source` ('heuristic'|'model'|'expert') on every row, a **classifier review queue** (`GET /admin/m1/pipeline/classifier-review`, lowest-confidence first) with an audited `POST …/{id}/override`, and per-call `latency_ms` logging (p95 ≤ 2 s DoD).
5. **Alerts:** dispatch per verified regulation (task `dispatch_regulation_alerts`) → in-app + email + **SMS** legs (Session 71) → SMEs see sector-matched feed at `/alerts`, public sees the broadcast feed. SMS only reaches SMEs with `phone` + `alert_sms_opt_in=true` and uses a dedicated ≤300-char SI/TA-safe body. No SendGrid/Twilio keys ⇒ those legs return `skipped`, in-app still works.
6. **Research loop:** watchers populate `m1_propagation_events` → nightly views refresh → notebooks in `enigmatrix-ml/research/notebooks/` compute F1–F6 → `make thesis-artifacts` regenerates Chapter-4 tables/figures → `make labeling-batch` samples annotation batches.
7. **Surveys & M2/M3:** SMEs take `/surveys` (trilingual wizard); admin manages questions/limits/translations; M2 scores at `/admin/m2/scores`; M3 signals at `/admin/m3/risk-signals`.
8. **Knowledge portal:** `/knowledge` mirrors the Obsidian vault live (edits push in ~1–2 s; ⌘K to navigate).

---

## 12. Testing & CI

| Suite | Command | Notes |
|---|---|---|
| Backend unit | `cd enigmatrix-backend && uv run pytest -q` | fine in PowerShell |
| Backend integration | same, but requires Docker via testcontainers | **WSL/Linux only** (documented in FEATURES F-203) |
| ML | `cd enigmatrix-ml && uv run pytest -q` | extras may be needed for some suites |
| Frontend unit | `pnpm test --run` (vitest) | |
| E2E | `pnpm e2e` (playwright; `@phase2` tag) | needs backend+frontend+seed running |
| Lint/type | `uv run ruff check .` · `pnpm lint` · `pnpm typecheck` | |
| CI | `.github/workflows/ci-m1-phase2.yml` | pytest + lint + typecheck + e2e + Alembic linearity |

## 13. Production Notes (Railway / Vercel / Aiven)

Backend deploys as a single Railway container: `scripts/start_railway.sh` runs **alembic upgrade → health banner (`python -m app.m1.health`, non-fatal) → Celery worker (bg) → Beat (bg) → uvicorn (fg)** from a prebuilt venv (no runtime uv resolve; the Dockerfile pins enigmatrix-ml). Session 66 hardening: the Dockerfile now **bakes `lid.176.bin` to `/opt/models/`** with a size assertion and runs **`python -m app.m1.health --strict` as a build gate** — the image *fails to build* if it doesn't ship Tesseract+sin/tam+poppler+model+ml-package, so a mis-built image can't reach prod. Storage on the Railway volume (`/data/storage`); Postgres = Aiven (`DB_SSL` on); Redis = Railway plugin; frontend = Vercel (`vercel.json` in backend repo handles rewrites). Open items: rotate the leaked PAT (Session 55), pin real digests in `infra/docker-image-pin.txt`, split worker/beat into a second service under load, `uv sync --extra serving` on the backend image once the ONNX model ships. The ONNX artifact is a **one-time volume upload to `/data/storage/models/m1/onnx/v1`, not an image rebuild** (Session 70 decision).

## 14. Troubleshooting (project-specific, from the session log)

| Symptom | Cause / fix |
|---|---|
| `make migrate`/`make seed`/`make dev-*` at root fail with "no such directory" | stale `backend`/`frontend` paths — see §1 trap (junctions or per-repo commands) |
| Celery worker dies instantly on Windows | use `--pool=solo` in PowerShell, or run in WSL |
| bcrypt "error reading version" becomes hard error | bcrypt must stay `<4.1` (pinned); `make doctor` diagnoses; `make reseed-users` after bcrypt changes |
| `CORS_ORIGINS` parse error at boot | must be a JSON array string: `["http://localhost:3000"]` |
| Postgres "too many connections" during extraction | compose already sets `max_connections=200`; don't lower; check Aiven pool sizing in prod (Session 54) |
| `/admin/m1/pipeline/recent` 503 in prod | environmental (Railway cold-start/DB pool) — not a code bug (Session 71); retry card handles it |
| Tesseract can't find `sin`/`tam` | install language packs; check `tesseract --list-langs`; PATH on Windows |
| Sinhala/Tamil text shows `(cid:…)` | legacy-font PDFs — the auto-chain now runs `wijesekara_routing_v1` by default (Session 69), so *new* ingests should be clean; a persistent CID means the profile silently fell back (check the monthly quality probe's `profile_share` + worker log). **Rows extracted before Session 69 are still garbled** — backfill via the admin scoped re-extraction over `extraction_method IN ('pymupdf','pdfplumber','tesseract') AND language='sin'` |
| `alembic upgrade` no-ops | you're on a DB that already stamped head — `uv run alembic current` vs `history`; commonly-missing heads are `202606300001–005` and the six Session-64–71 `202607210001–006` |
| `GET /admin/m1/pipeline/health` red / worker boot logs CRITICAL | a runtime component is missing (Tesseract langs, `lid.176.bin`, ml package) — the report names which; EN-text extraction still works, but SI/TA OCR + language routing degrade. Fix the dep or the model path; in prod the `--strict` build gate should have caught it |
| `/admin/m1/pipeline/sources` shows rising `consecutive_failures` | a seeded source URL is a best-known default and may be wrong/dead (Session 71) — PATCH the correct URL or set `active=false` to park it before trusting its lag numbers |
| Integration tests fail on Windows | testcontainers needs Linux Docker — run in WSL |
| Git shows ~240 modified files everywhere | CRLF noise — add `.gitattributes` (`* text=auto eol=lf`) + `git add --renormalize .` |
| Frontend knowledge portal shows stale vault | it reads `C:\sme` (divergent copy) — retarget to `E:\Obsidian\sme` |
