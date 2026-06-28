---
tags: [meta, setup, local-dev]
source: synthesised
layer: meta
module: shared
---

# Local Development Handbook

> **First page for any new contributor.** Walk through this end-to-end on a fresh Windows machine and you'll have backend + frontend + ml all running locally in under 60 minutes.

**Stack at a glance:**

| Area | Stack | Where it runs | Doc |
|---|---|---|---|
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui | **PowerShell** on Windows | [frontend/SETUP/00_LOCAL_DEV_POWERSHELL](frontend/SETUP/00_LOCAL_DEV_POWERSHELL.md) |
| Backend | FastAPI + SQLAlchemy 2.0 async + Alembic + Pydantic v2 + Celery | **WSL2 (Ubuntu)** | [backend/SETUP/00_LOCAL_DEV_WSL](backend/SETUP/00_LOCAL_DEV_WSL.md) |
| ML | Python uv workspace (`enigmatrix-ml/m1/`) — fastText, transformers, PyMuPDF, pdfplumber, Tesseract, pdf2image | **WSL2 (Ubuntu)** | [ml/SETUP/00_LOCAL_DEV_WSL](ml/SETUP/00_LOCAL_DEV_WSL.md) |
| Infra | PostgreSQL + Redis via Docker Desktop | **Docker Desktop on Windows** (WSL2 backend) | [infra/SETUP/01_Prerequisites](infra/SETUP/01_Prerequisites.md), [infra/SETUP/02_Quickstart](infra/SETUP/02_Quickstart.md) |
| Knowledge graph | graphify (`graphify-out/` in code + vault) | PowerShell | (per-repo; see memory `reference_graphify_outputs.md`) |

**Per-phase how-to-run guides** (for testing the work that's been shipped): [02-Research-Modules/1 Module-1-Awareness-Gap/local-dev/00_INDEX](../02-Research-Modules/1%20Module-1-Awareness-Gap/local-dev/00_INDEX.md).

---

## 1 · One-time prerequisites

Run these once per Windows machine. Most of these are 5-minute installs.

### 1.1 Windows side

```powershell
# PowerShell 7+ (open Windows Terminal — comes with Win 11)
winget install --id Microsoft.PowerShell -e

# Git for Windows
winget install --id Git.Git -e

# Docker Desktop (with WSL2 backend — enable in Settings → Resources → WSL Integration)
winget install --id Docker.DockerDesktop -e

# VS Code + WSL extension
winget install --id Microsoft.VisualStudioCode -e
code --install-extension ms-vscode-remote.remote-wsl

# Node.js 20 LTS (frontend runs here)
winget install --id OpenJS.NodeJS.LTS -e
# OR via volta (cleaner version management):
#   winget install --id Volta.Volta -e
#   volta install node@20

# pnpm (NOT npm — enigmatrix-frontend uses pnpm-lock.yaml)
npm install -g pnpm@9
```

### 1.2 WSL2 + Ubuntu

```powershell
# Install WSL2 with Ubuntu 24.04 (one-time; reboots Windows)
wsl --install -d Ubuntu-24.04

# After reboot, set a username + password when prompted.
# Then enable systemd (lets Postgres / Redis run as services if needed):
wsl -d Ubuntu-24.04 -- sudo bash -c "echo -e '[boot]\nsystemd=true' > /etc/wsl.conf"
wsl --shutdown
```

### 1.3 Inside WSL (Ubuntu shell)

```bash
# System deps for backend + ml
sudo apt update && sudo apt install -y \
    build-essential \
    libpq-dev \
    tesseract-ocr tesseract-ocr-sin tesseract-ocr-tam \
    poppler-utils \
    redis-server \
    python-is-python3 \
    git \
    curl

# Why `python-is-python3`?
# Ubuntu 24.04 does NOT symlink `python` to `python3` by default.
# Without this package, `python …` commands fail with
# `Command 'python' not found`. The setup docs below mostly call
# `uv run python …` (which always works), but the apt package is a
# safety net for muscle-memory `python …` invocations.

# Verify Tesseract has the Sinhala + Tamil language packs
tesseract --list-langs | grep -E '^(eng|sin|tam)$'   # expect all three

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Verify
uv --version    # expect uv 0.4+
python3 --version    # 3.11 or 3.12; uv installs its own anyway
```

### 1.4 SSH keys (Git access)

```bash
# Inside WSL:
ssh-keygen -t ed25519 -C "<your-email>"   # accept defaults
cat ~/.ssh/id_ed25519.pub                  # copy this
# Paste into github.com → Settings → SSH and GPG keys → New SSH key
ssh -T git@github.com                      # expect "Hi <user>! You've successfully authenticated..."
```

The same key also works from PowerShell if you symlink. **Optional — skip this
unless you push from PowerShell.** Backend + ml work happens in WSL where the
SSH key already lives at `~/.ssh/`; only the frontend `pnpm` flow on PowerShell
needs the shared key (and only if you use SSH remotes vs HTTPS + a PAT).

```powershell
# 1. Find your WSL username (in a WSL shell run `whoami`). Substitute it
#    for <wsl-user> below. Common values: your Windows username lowercased,
#    or `administrator` if that's what `whoami` returned in WSL.

# 2. (One-time) Remove any pre-existing $HOME\.ssh on Windows. mklink refuses
#    to create the symlink if a folder already exists at the target path.
#    Skip this step if `Test-Path $HOME\.ssh` returns False.
Remove-Item -Recurse -Force $HOME\.ssh   # only if it exists + you've backed it up

# 3. Create the symlink. Run PowerShell AS ADMINISTRATOR — symbolic links
#    require admin rights on Windows unless Developer Mode is enabled.
cmd /c mklink /D "$HOME\.ssh" "\\wsl$\Ubuntu-24.04\home\<wsl-user>\.ssh"

# 4. Verify from PowerShell:
ssh -T git@github.com   # expect: Hi <user>! You've successfully authenticated...
```

---

## 2 · Clone the repo

Two filesystem options — pick one (recommended: **option A**).

### Option A (Recommended) — WSL-native clone + Windows symlink

The repo lives natively in WSL filesystem (fast I/O for Python work). A Windows symlink lets PowerShell + graphify see the same files.

```bash
# Inside WSL:
mkdir -p ~/repos && cd ~/repos
git clone git@github.com:ifham-mohamed/xyz.git
cd xyz
```

```powershell
# In PowerShell (Admin), create the symlink for graphify + frontend access:
New-Item -ItemType SymbolicLink -Path "C:\Reasearch\xyz" -Target "\\wsl$\Ubuntu-24.04\home\<wsl-user>\repos\xyz"

# Verify both paths resolve to the same files:
ls C:\Reasearch\xyz\enigmatrix-frontend\package.json
wsl ls ~/repos/xyz/enigmatrix-frontend/package.json
```

### Option B — Windows-only clone

Slower I/O on the Python/ml side but no symlink fiddling.

```powershell
mkdir C:\Reasearch
cd C:\Reasearch
git clone git@github.com:ifham-mohamed/xyz.git
```

Then in WSL, access via `cd /mnt/c/Reasearch/xyz` (be prepared for 5–10× slower file ops on `uv sync`).

---

## 3 · Day-zero bring-up (full stack from scratch)

Run these in **strict order** the first time you set up the local environment.

### 3.1 Start Docker Desktop

Open Docker Desktop from Windows. Wait until the bottom-left "Engine running" indicator is green. Verify:

```powershell
docker info | Select-String "Server Version"
```

### 3.2 Bring up Postgres + Redis (Docker)

```bash
# In WSL:
cd ~/repos/xyz
docker compose -f docker-compose.dev.yml up -d postgres redis
docker compose -f docker-compose.dev.yml ps   # expect both "Up" + healthy
```

If you see `no such service: redis`, the compose file is out of date.
The Redis service was added with the M1 Celery pipeline (Step 2b); make
sure your working tree has `services.redis` (image `redis:7-alpine`) in
`c:\Reasearch\xyz\docker-compose.dev.yml`. Run `git pull` if you cloned
before that change shipped.

### 3.3 Backend (WSL)

```bash
cd ~/repos/xyz/enigmatrix-backend
cp .env.example .env                  # fill in JWT_SECRET, CORS_ORIGINS at minimum
uv sync                                # installs backend + ml workspace deps
uv run alembic upgrade head            # applies all migrations through 202605260001 (Session 34)
uv run python -m app.scripts.seed_dev  # seeds admin user + 5 demo regulations + survey questions
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> **Selective seeding + revert workflows** (`--users-only`, `--skip-demo`,
> per-module re-seed, `make db-truncate TABLES=…`, `make db-reseed`, full
> schema reset, diagnostics) live in
> [backend/SETUP/00_LOCAL_DEV_WSL.md §6](backend/SETUP/00_LOCAL_DEV_WSL.md).
> Use that doc as the day-to-day reference for dev-DB state.

Verify (from PowerShell or browser): `http://localhost:8000/health` → `{"status":"ok","service":"enigmatrix-api"}`.

### 3.4 Frontend (PowerShell)

```powershell
cd C:\Reasearch\xyz\enigmatrix-frontend
pnpm install
Copy-Item .env.example .env.local
notepad .env.local        # set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
pnpm dev
```

Verify: open `http://localhost:3000` in browser → should redirect to `/login`. Sign in with `admin@enigmatrix.lk` / `admin12345678` (from the seed script).

### 3.5 ML workspace (WSL) — optional for backend-only work

> **Important:** always invoke through `uv run …`. Bare `python` /
> `pytest` resolve to the **system** interpreter, which does NOT have the
> project's deps (`pytesseract`, `fitz`/PyMuPDF, `fasttext-wheel`,
> `transformers`, …). `uv run` resolves to the uv-managed workspace venv
> that was populated by `uv sync` in §3.3.

```bash
cd ~/repos/xyz/enigmatrix-ml
uv run python scripts/download_lid_model.py --target storage/models/m1/baseline/lid.176.bin
# Pre-warm xlm-roberta-base tokenizer (~1.1 GB; one-time)
uv run python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('xlm-roberta-base')"
M1_LID_MODEL_PATH=storage/models/m1/baseline/lid.176.bin uv run pytest tests/m1 -v
# Expect: 127 passed / 8 skipped
```

---

## 4 · Day-N workflow

Once everything is set up, the typical daily loop:

```bash
# WSL — pull latest + apply any new migrations
cd ~/repos/xyz
git pull
cd enigmatrix-backend && uv sync && uv run alembic upgrade head

# PowerShell — pull latest frontend deps
cd C:\Reasearch\xyz\enigmatrix-frontend
pnpm install
```

Then start services as in §3.3 / §3.4. Stop them with `Ctrl+C`.

---

## 5 · Per-area deep dives

Once the day-zero bring-up works, the area-specific docs cover the day-to-day workflow:

- [backend/SETUP/00_LOCAL_DEV_WSL.md](backend/SETUP/00_LOCAL_DEV_WSL.md) — Alembic, Celery worker, pytest layout, debugging routes
- [frontend/SETUP/00_LOCAL_DEV_POWERSHELL.md](frontend/SETUP/00_LOCAL_DEV_POWERSHELL.md) — pnpm scripts, env vars, build/typecheck/lint, port conflicts
- [ml/SETUP/00_LOCAL_DEV_WSL.md](ml/SETUP/00_LOCAL_DEV_WSL.md) — uv workspace, model downloads, CLI smoke checks per module, HF cache management

And the cross-cutting docs that already exist:

- [infra/SETUP/01_Prerequisites](infra/SETUP/01_Prerequisites.md) — Docker, env vars, port matrix
- [infra/SETUP/02_Quickstart](infra/SETUP/02_Quickstart.md) — original quickstart (pre-WSL emphasis)
- [infra/SETUP/09_Troubleshooting](infra/SETUP/09_Troubleshooting.md) — known gotchas
- [shared/03_Architecture](shared/03_Architecture.md) — system architecture overview
- [shared/08_Testing](shared/08_Testing.md) — test pyramid + conventions
- [backend/SETUP/06_Database_and_Migrations](backend/SETUP/06_Database_and_Migrations.md) — Alembic conventions
- [backend/SETUP/07_Auth_and_Roles](backend/SETUP/07_Auth_and_Roles.md) — JWT, RBAC, session wiring

---

## 6 · Per-phase how-to-run (M1)

To **run** specific Phase 2 work locally and verify it produces the expected result, see the per-phase guides:

[02-Research-Modules/1 Module-1-Awareness-Gap/local-dev/00_INDEX.md](../02-Research-Modules/1%20Module-1-Awareness-Gap/local-dev/00_INDEX.md)

Each phase doc tells you which terminal to use, which command to run, what the expected output is, and how to verify the database state matches the spec.

---

## 7 · Standing cadence (end-of-session)

Per the `feedback_vault_sync_cadence.md` memory:

1. **Append to vault tracker triplet** — new `## Session N` entry in `c:\sme\08-Findings-Log\SESSIONS.md` + one row per F-### in `CHANGES.md` + a feature row in `FEATURES.md`.
2. **(Per-module) finding entry** when the change is substantive M1/M2/M3/M4 architectural — file at `c:\sme\02-Research-Modules\<N module>\findings\YYYY-MM-DD-<slug>.md`.
3. **Run graphify update** (free, no Claude):
   ```powershell
   graphify update C:\Reasearch\xyz   # code monorepo
   graphify update C:\sme              # Obsidian vault
   ```
4. **Commit + push** to the relevant repos (`enigmatrix-frontend`, `enigmatrix-backend`, `enigmatrix-ml`, `enigmatrix-docs` for Org repos; `xyz` for the personal monorepo mirror). No `Co-Authored-By` line.

---

## 8 · Where everything lives (filesystem map)

```
WSL (~/repos/xyz/)                           Windows (C:\Reasearch\xyz/)
├── docker-compose.dev.yml                   (symlink — same file)
├── enigmatrix-backend/                      (WSL: uv sync, alembic, uvicorn)
│   ├── app/                                 (FastAPI + ORM + tasks)
│   ├── alembic/versions/                    (DB migrations — 202605XXNN)
│   ├── scraper/                             (Scrapy spider)
│   └── storage/                             (raw PDF cache)
├── enigmatrix-ml/                           (WSL: uv workspace member)
│   ├── m1/extraction/                       (Step 2c/2d code)
│   ├── m1/preprocessing/                    (Step 2e code)
│   ├── scripts/                             (download_lid_model.py)
│   ├── storage/models/m1/baseline/          (lid.176.bin lives here)
│   └── tests/m1/                            (ml test suite)
├── enigmatrix-frontend/                     (PowerShell: pnpm)
│   ├── app/                                 (Next.js routes)
│   ├── components/                          (shadcn + custom UI)
│   └── lib/                                 (api clients, i18n, utils)
├── enigmatrix-docs/                         (markdown specs — mirror of c:\sme except vault-only files)
└── graphify-out/                            (auto-generated — gitignored)

c:\sme\ (Obsidian vault — NOT a git repo)
├── 04-Technology-Stack/                     (THIS doc + per-area SETUP/BUILD)
├── 02-Research-Modules/                     (M1-M4 specs + planned-for-development + local-dev)
├── 08-Findings-Log/                         (SESSIONS, CHANGES, FEATURES)
├── _Templates/                              (Findings-Entry-Template.md)
└── graphify-out/                            (vault knowledge graph — gitignored)
```

---

## 9 · Quick troubleshooting

| Symptom | Likely cause | Quick fix |
|---|---|---|
| `pnpm: command not found` (PowerShell) | npm path not in PATH | `npm install -g pnpm@9` + restart terminal |
| `psycopg2` build fails (WSL `uv sync`) | Missing `libpq-dev` | `sudo apt install libpq-dev` |
| `tesseract: command not found` (WSL) | apt deps missing | `sudo apt install tesseract-ocr tesseract-ocr-sin tesseract-ocr-tam poppler-utils` |
| Port 3000 busy (PowerShell) | Prior `pnpm dev` still running | `netstat -ano \| findstr :3000` then `taskkill /PID <pid> /F` |
| Port 8000 busy (WSL) | Prior uvicorn still running | `lsof -i :8000` then `kill <pid>` |
| Docker daemon not running | Docker Desktop closed | Open Docker Desktop from Start menu; wait for green indicator |
| `wsl: command not found` (PowerShell) | WSL2 not installed | `wsl --install -d Ubuntu-24.04` then reboot |
| Slow `uv sync` on `/mnt/c/...` | WSL accessing Windows filesystem | Move repo into WSL home (`~/repos/xyz`) — see §2 Option A |
| Frontend can't reach backend | CORS or wrong API_BASE_URL | Check `.env.local` has `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`; confirm backend started with `--host 0.0.0.0` |

For deeper issues, see [infra/SETUP/09_Troubleshooting](infra/SETUP/09_Troubleshooting.md).

---

## 10 · Cross-references

- **Per-area dev docs**: [backend/SETUP/00_LOCAL_DEV_WSL](backend/SETUP/00_LOCAL_DEV_WSL.md), [frontend/SETUP/00_LOCAL_DEV_POWERSHELL](frontend/SETUP/00_LOCAL_DEV_POWERSHELL.md), [ml/SETUP/00_LOCAL_DEV_WSL](ml/SETUP/00_LOCAL_DEV_WSL.md)
- **Per-phase guides**: [M1 local-dev INDEX](../02-Research-Modules/1%20Module-1-Awareness-Gap/local-dev/00_INDEX.md)
- **Roadmap**: [M1 Development Roadmap](../02-Research-Modules/1%20Module-1-Awareness-Gap/16_M1_Development_Roadmap.md)
- **Cadence**: see memory `feedback_vault_sync_cadence.md` (Claude reads this automatically)
- **Vault structure**: see memory `reference_obsidian_vault.md`
- **Graphify**: see memory `reference_graphify_outputs.md`