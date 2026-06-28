---
tags: [setup, backend, local-dev, wsl]
source: synthesised
layer: meta
module: shared
---

# Backend Local Development (WSL)

> **Prereqs**: complete [00_LOCAL_DEV_HANDBOOK §1](../../00_LOCAL_DEV_HANDBOOK.md) first (WSL install + uv + apt deps). This doc assumes you're inside Ubuntu 24.04 (WSL2) with the repo cloned at `~/repos/xyz/`.

The backend (`enigmatrix-backend/`) is a FastAPI app with async SQLAlchemy 2.0, Alembic migrations, Pydantic v2 schemas, and Celery tasks for the M1 ingestion pipeline. Production runs on Vercel + Fly.io (worker); local dev runs entirely inside WSL with Postgres + Redis from Docker Desktop.

---

## 1 · Pre-flight check

Run from inside WSL:

```bash
which uv          # /home/<user>/.local/bin/uv
which tesseract   # /usr/bin/tesseract
which poppler-utils 2>/dev/null || which pdftoppm   # /usr/bin/pdftoppm
docker ps         # lists running containers (Docker Desktop must be running)
```

If any of these fail, jump back to [00_LOCAL_DEV_HANDBOOK §1.3](../../00_LOCAL_DEV_HANDBOOK.md).

---

## 2 · Environment configuration

```bash
cd ~/repos/xyz/enigmatrix-backend
cp .env.example .env
```

Edit `.env` (use `nano .env` or VS Code) and set the values:

| Var                        | Local dev value                                                            | Notes                                                                     |
| -------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `DATABASE_URL`             | `postgresql+asyncpg://enigmatrix:enigmatrix@localhost:5432/enigmatrix_dev` | matches the `docker-compose.dev.yml` Postgres service                     |
| `JWT_SECRET`               | `dev-secret-change-me-1234567890abcdef`                                    | any 32+ char string; production uses a real secret                        |
| `CORS_ORIGINS`             | `http://localhost:3000`                                                    | frontend dev port                                                         |
| `CELERY_BROKER_URL`        | `redis://localhost:6379/0`                                                 | matches the Redis container                                               |
| `STORAGE_LOCAL_PATH`       | `./storage`                                                                | relative to the backend root; gazette PDFs land under `./storage/m1/raw/` |
| `M1_PDF_TEXT_THRESHOLD`    | `200`                                                                      | chars/page above this → PyMuPDF                                           |
| `M1_PDF_SCANNED_THRESHOLD` | `30`                                                                       | chars/page below this → Tesseract                                         |
| `M1_LID_MODEL_PATH`        | `../enigmatrix-ml/storage/models/m1/baseline/lid.176.bin`                  | fastText model (Session 30 / F-153)                                       |

---

## 3 · Bring up Postgres + Redis (one-time per session)

From the repo root in WSL:

```bash
cd ~/repos/xyz
docker compose -f docker-compose.dev.yml up -d postgres redis
docker compose ps
# Expect: postgres "Up" + healthy, redis "Up"
```

Stop later with `docker compose down` or just leave it running.

---

## 4 · Install Python deps (`uv sync`)

```bash
cd ~/repos/xyz/enigmatrix-backend
uv sync
```

This reads the root `pyproject.toml` workspace + backend's local `pyproject.toml` and installs both backend + `enigmatrix-ml` deps into a single `.venv/`. First run takes ~2 minutes; subsequent runs are instant (cached).

Verify:

```bash
uv run python -c "import fastapi, sqlalchemy, celery, alembic; print('OK')"
uv run python -c "from m1.preprocessing import preprocess_gazette; print('ml workspace OK')"
```

---

## 5 · Run database migrations

```bash
uv run alembic upgrade head
```

Expected output (newest migration depending on session):

```
INFO  [alembic.runtime.migration] Running upgrade -> 202605080001, initial_schema
...
INFO  [alembic.runtime.migration] Running upgrade 202605250001 -> 202605260001, m1_sub_documents
```

Round-trip check (proves all migrations are reversible):

```bash
uv run alembic downgrade -1   # back out the latest
uv run alembic upgrade head   # forward again
```

---

## 6 · Seed + revert dev data

Everything below assumes you're in `~/repos/xyz/enigmatrix-backend`. Every
seeder is idempotent.

### 6.1 First-time seed (apply everything)

```bash
make migrate                                     # alembic upgrade head — required if schema is empty
make seed                                        # full chain (users + lookups + content + demo)
# equivalent to: uv run python -m app.scripts.seed_dev
```

### 6.2 Seeded surfaces

| Seeder module | Produces |
|---|---|
| `seed_dev` (users portion) | `admin@enigmatrix.lk`, `annotator@enigmatrix.lk`, `sme@enigmatrix.lk` + SME profile |
| `seed_lookups` | `regulatory_domains` (9 rows) + `sectors` (12 rows) — FK targets for everything below |
| `seed_regulations` | 5 demo regulations (`VAT_2024_AMD`, `EPF_2024_RATE`, …) |
| `seed_phase4` | MRP/SLSI/DPDPA + sector map + M1–M4 cross-module questions |
| `seed_vulnerability_questions` | M3 codes (must exist before awareness rules reference them) |
| `seed_m23_questions` | M2 knowledge bank (~44 questions) |
| `seed_awareness_questions` | M0 awareness questions (12) |
| `seed_demo_responses` | 6 demo SMEs + ~336 synthetic survey responses, 6 M2 score rows, 6 M3 snapshots each |

**Default credentials (seeded by `seed_dev`):**

| Email | Password | Role |
|---|---|---|
| `admin@enigmatrix.lk` | `admin12345` | admin |
| `annotator@enigmatrix.lk` | `annotator12345` | annotator |
| `sme@enigmatrix.lk` | `sme12345678` | sme |

Plus 6 demo SMEs (`demo.{retail,manufacturing,it,tourism,construction,foodbev}@enigmatrix.lk` / `demo12345678`) if `seed_demo_responses` ran.

### 6.3 Selective seeding — `seed_dev` flags

```bash
# Only the 3 user accounts + the SME profile (no content):
uv run python -m app.scripts.seed_dev --users-only

# Everything EXCEPT the demo SMEs / synthetic survey responses:
uv run python -m app.scripts.seed_dev --skip-demo

# Full chain (default — same as `make seed`):
uv run python -m app.scripts.seed_dev
```

### 6.4 Selective seeding — single-module standalone

Each `seed_*.py` exposes `__main__` + async `main()` — runnable on its own.

```bash
uv run python -m app.scripts.seed_lookups                  # regulatory_domains + sectors
uv run python -m app.scripts.seed_regulations              # 5 demo regulations
uv run python -m app.scripts.seed_phase4                   # MRP/SLSI/DPDPA + sector map + M1-M4 Qs
uv run python -m app.scripts.seed_vulnerability_questions  # M3 codes
uv run python -m app.scripts.seed_m23_questions            # M2 knowledge bank (~44 questions)
uv run python -m app.scripts.seed_awareness_questions      # M0 awareness questions (12)
uv run python -m app.scripts.seed_demo_responses           # 6 demo SMEs + synthetic survey activity
```

**Dependency order** matters because of FK chains:

```
seed_lookups            → regulatory_domains + sectors (FK targets for everything)
   ↓
seed_regulations        → references regulatory_domains + sectors
   ↓
seed_phase4             → MRP/SLSI/DPDPA + sector map + cross-module questions
   ↓
seed_vulnerability_questions → M3 codes (before awareness rules reference them)
   ↓
seed_m23_questions      → cross-module routing rules FK back to regulations
   ↓
seed_awareness_questions → references M2 + M3 question codes
   ↓
seed_demo_responses     → demo SMEs + synthetic survey activity (needs everything)
```

Running a downstream seeder before its upstream dependency → `ForeignKeyViolation`.

### 6.5 Reverting seeded data — `db-truncate`

Wipes every row, **keeps the schema** + `alembic_version`. Schema-aware revert; no migration replay.

```bash
# Wipe ALL seeded rows (every public-schema table except alembic_version):
make db-truncate

# Wipe only specific tables (CASCADE handles FKs automatically):
make db-truncate TABLES=survey_responses,m2_knowledge_scores
make db-truncate TABLES=m1_regulations,m1_regulation_penalties,m1_sub_documents
make db-truncate TABLES=users,sme_profiles

# Wipe + immediately re-seed in one go (most common cycle):
make db-reseed                                   # = db-truncate + seed
```

Direct script form (same as the Makefile target):

```bash
uv run python -m app.scripts.db_truncate
uv run python -m app.scripts.db_truncate --tables m1_regulations,survey_responses
```

**`db-truncate` vs `db-reset`:**

- `db-truncate` — empties rows. Schema + `alembic_version` intact. Fast. No migration replay.
- `db-reset` — runs `alembic downgrade base`. Drops every table. Requires `make migrate` afterwards.

### 6.6 Full schema reset

When migrations themselves changed and you need to re-exercise the migration chain:

```bash
make db-fresh                                    # alembic downgrade base + migrate + seed
```

If `db-fresh` chokes on a fragile downgrade, drop+create the database directly:

```bash
docker compose -f ~/repos/xyz/docker-compose.dev.yml exec postgres \
  psql -U enigmatrix -d postgres -c \
  "DROP DATABASE IF EXISTS enigmatrix; CREATE DATABASE enigmatrix OWNER enigmatrix;"

make migrate seed                                # alembic upgrade head + full seed
```

### 6.7 Diagnostic snippets

```bash
# Which alembic revision is the DB on?
make db-current

# What tables exist right now?
docker compose -f ~/repos/xyz/docker-compose.dev.yml exec postgres \
  psql -U enigmatrix -d enigmatrix -c "\dt public.*"

# Row counts per table:
docker compose -f ~/repos/xyz/docker-compose.dev.yml exec postgres \
  psql -U enigmatrix -d enigmatrix -c \
  "SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC"

# Open connections (diagnose TooManyConnectionsError):
docker compose -f ~/repos/xyz/docker-compose.dev.yml exec postgres \
  psql -U enigmatrix -d enigmatrix -c \
  "SELECT count(*) AS conns, state FROM pg_stat_activity GROUP BY state"
```

### 6.8 Decision table

| Symptom | Run |
|---|---|
| `relation "users" does not exist` after seeding | `make migrate && make seed` |
| Want to start over with same schema | `make db-reseed` |
| Iterating on one seeder's content | `make db-truncate TABLES=<that_table>` then `uv run python -m app.scripts.<seeder>` |
| Want only admin login, nothing else | `make migrate && uv run python -m app.scripts.seed_dev --users-only` |
| Migrations themselves changed; need full chain | `make db-fresh` |
| `make db-fresh` fails on a fragile downgrade | drop+create DB (§6.6) then `make migrate seed` |
| Celery worker hits `TooManyConnectionsError` | stop worker, `docker compose ... restart postgres`, restart worker |

### 6.9 Common selective workflows

```bash
# Working admin login + lookup tables only — nothing else:
make migrate
uv run python -m app.scripts.seed_dev --users-only
uv run python -m app.scripts.seed_lookups

# Iterating on M2 questions — re-seed just that bank:
make db-truncate TABLES=survey_questions
uv run python -m app.scripts.seed_m23_questions

# Admin dashboards empty — only seed demo SMEs (rest already seeded):
uv run python -m app.scripts.seed_demo_responses

# Iterating on Phase 2 Scrapy pipeline — wipe ONLY pipeline data,
# keep auth + lookups + questions:
make db-truncate TABLES=m1_regulations,m1_regulation_sectors,m1_regulation_penalties,m1_sub_documents

# Clean slate WITHOUT the synthetic demo noise (faster, smaller DB):
make db-truncate
uv run python -m app.scripts.seed_dev --skip-demo
```

---

## 7 · Run the dev server

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The `--host 0.0.0.0` matters — from PowerShell / Windows browsers you'll hit `http://localhost:8000`, which WSL forwards. (`127.0.0.1`-only binding doesn't cross the WSL boundary.)

Verify in a different terminal (or browser):

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"enigmatrix-api"}
```

Press `Ctrl+C` to stop.

---

## 8 · Run the test suite

### Unit tests (fast — no Postgres needed)

```bash
uv run pytest app/tests/unit/ -v
# ~30 tests, < 5s
```

### Integration tests (Postgres + Celery eager mode)

```bash
uv run pytest app/tests/integration/ -v
# ~25 tests; needs Docker for testcontainer Postgres
```

The integration tests spin up an ephemeral Postgres via `testcontainers` library — Docker daemon must be running.

### Targeted: the M1 Celery chain

```bash
# Test the spider → DB pipeline:
uv run pytest app/tests/integration/test_gazette_spider.py -v   # 4 tests, Session 23 / F-145
# Test the extract → preprocess chain:
uv run pytest app/tests/integration/test_celery_extract_gazette.py -v       # 2 tests, Session 26 / F-148
uv run pytest app/tests/integration/test_celery_preprocess_gazette.py -v    # 6 tests, Session 32 + 34
```

### Whole suite

```bash
uv run pytest -v
```

---

## 9 · Celery worker (for end-to-end pipeline smoke tests)

Production has 3 terminals running: worker + Beat + the app. Local dev can collapse them.

### Terminal 1 — Redis (if not already via Docker)

```bash
# Either:
docker compose -f ../docker-compose.dev.yml up -d redis
# Or:
redis-server
```

### Terminal 2 — Celery worker

```bash
cd ~/repos/xyz/enigmatrix-backend
uv run celery -A app.celery_config worker -l info
```

### Terminal 3 — Celery Beat (cron-style scheduler, optional)

```bash
uv run celery -A app.celery_config beat -l info
# Fires `run_gazette_spider` on the `0 */6 * * *` schedule.
```

### Trigger a task manually

```bash
# Terminal 4 (or use the dev server's REPL):
uv run python
>>> from app.tasks.m1 import extract_gazette
>>> extract_gazette.delay("<regulation_uuid>")
```

Watch the worker logs flip the row through the pipeline stages.

---

## 10 · Verifying changes after each edit

A typical edit-test-verify loop:

1. **Code change** in `app/...`.
2. **Type check** (optional, fast): `uv run mypy app/ --ignore-missing-imports`.
3. **Re-run affected tests**: `uv run pytest app/tests/integration/test_celery_preprocess_gazette.py::test_preprocess_gazette_persists_sub_documents -v`.
4. **Re-run alembic** if you added a migration: `uv run alembic upgrade head`.
5. **Smoke the dev server**: hit the route via `curl` or open the frontend.
6. **Verify in psql**:
   ```bash
   docker compose exec postgres psql -U enigmatrix -d enigmatrix_dev
   \dt m1_*           # list M1 tables
   \d m1_regulations  # inspect schema
   SELECT regulation_id, status, gazette_number FROM m1_regulations ORDER BY created_at DESC LIMIT 5;
   \q
   ```

For the M1 pipeline specifically, the per-phase guides at [02-Research-Modules/1 Module-1-Awareness-Gap/local-dev/](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/local-dev/00_INDEX.md) walk through the run + verify cycle for each shipped step.

---

## 11 · psql cheatsheet (Postgres inspection from WSL)

```bash
# Connect:
docker compose -f ~/repos/xyz/docker-compose.dev.yml exec postgres psql -U enigmatrix -d enigmatrix_dev

# Inside psql:
\l                                          # list databases
\dt                                         # list tables
\dt m1_*                                    # list M1 tables only
\d m1_regulations                           # describe a table
\d+ m1_regulation_penalties                 # include indexes + constraints
SELECT version();                           # Postgres version
SELECT count(*) FROM m1_regulations;        # row count
SELECT count(*) FROM m1_regulation_penalties WHERE is_admin_set = TRUE;  # admin-curated penalty count
SELECT regulation_id, status, gazette_number, length(cleaned_text) AS clean_len
FROM m1_regulations ORDER BY created_at DESC LIMIT 5;
\q                                          # quit
```

---

## 12 · Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ImportError: psycopg2` on `uv sync` | Missing `libpq-dev` | `sudo apt install libpq-dev` |
| `alembic upgrade head` fails on first run | Postgres container not up | `docker compose -f ../docker-compose.dev.yml up -d postgres` then retry |
| `ProgrammingError: relation "m1_regulations" does not exist` | Migrations not applied | `uv run alembic upgrade head` |
| `OperationalError: could not connect` | Postgres not running OR DATABASE_URL wrong | `docker compose ps` + check `.env` `DATABASE_URL` matches the Postgres container's port 5432 |
| `tesseract: command not found` (during Celery extract task) | apt deps missing | `sudo apt install tesseract-ocr tesseract-ocr-sin tesseract-ocr-tam` |
| `FileNotFoundError: lid.176.bin` (during preprocess task) | fastText model not staged | `cd ../enigmatrix-ml && uv run python scripts/download_lid_model.py --target storage/models/m1/baseline/lid.176.bin` |
| `xlm-roberta-base` slow first load | HF tokenizer downloading ~1.1 GB | Pre-warm: `cd ../enigmatrix-ml && uv run python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('xlm-roberta-base')"` |
| `ModuleNotFoundError: No module named 'pytesseract' / 'fitz'` (during `pytest`) | Bare `pytest` ran on the system Python (no project deps) | Use `uv run pytest …` from `enigmatrix-ml/` |
| `Command 'python' not found, did you mean: command 'python3' from deb python3` | Ubuntu 24.04 has no `python` symlink | Use `uv run python …` or run `sudo apt install python-is-python3` once |
| Frontend says "CORS error" | `CORS_ORIGINS` doesn't include frontend port | Update `.env` `CORS_ORIGINS=http://localhost:3000` + restart uvicorn |
| `task_always_eager=True` not picked up by tests | Wrong fixture | Use the `_eager_celery` autouse fixture from existing `test_celery_*.py` files |
| `uv` not on PATH after install | shell not reloaded | `source ~/.bashrc` or restart WSL terminal |

---

## 13 · Cross-references

- **Database & migrations**: [06_Database_and_Migrations](06_Database_and_Migrations.md) (conventions, naming, sequence)
- **Auth & roles**: [07_Auth_and_Roles](07_Auth_and_Roles.md) (JWT, RBAC, audit log)
- **Survey system**: [11_Survey_System](11_Survey_System.md) (unified survey flow)
- **Backend dev guide** (feature-by-feature): [04_Backend_Development](04_Backend_Development.md)
- **Architecture overview**: [../../shared/03_Architecture](../../shared/03_Architecture.md)
- **Testing conventions**: [../../shared/08_Testing](../../shared/08_Testing.md)
- **Per-phase M1 run + verify**: [../../../02-Research-Modules/1 Module-1-Awareness-Gap/local-dev/](../../../02-Research-Modules/1%20Module-1-Awareness-Gap/local-dev/00_INDEX.md)