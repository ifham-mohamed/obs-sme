# 01 — Prerequisites

> **Goal:** by the end of this file, you have every tool installed at the right version and you have verified each one runs. After this, [`02_Quickstart.md`](02_Quickstart.md) is five commands.

---

## OS support

The repo targets **macOS** and **Linux** as primary development OSes. **Windows** developers should run the project from inside **WSL2** with the Ubuntu distribution and follow the Linux recipes below; native PowerShell + native Postgres is fragile and not supported. To set up WSL2 once: `wsl --install -d Ubuntu` in PowerShell as admin → reboot → log into Ubuntu → run the Linux recipe inside it. The rest of these docs assume the Linux recipe applies inside WSL2 unless noted.

---

## Required tools

| Tool | Version | Why | Verify |
|------|---------|-----|--------|
| Git | ≥ 2.40 | Version control. | `git --version` |
| Python | **3.11.x** (not 3.12+) | Backend + ML. Pinned in [`backend/pyproject.toml`](../../backend/pyproject.toml) → `requires-python = ">=3.11,<3.13"`. | `python3 --version` |
| `uv` | ≥ 0.4 | Fast Python package manager and venv tool. The `Makefile` calls `uv run` directly. | `uv --version` |
| Node.js | **20 LTS** | Frontend. | `node --version` |
| pnpm | ≥ 9 | Faster, disk-efficient package manager. The `Makefile` calls `pnpm` directly. | `pnpm --version` |
| Docker Desktop (or Engine + Compose v2) | latest | Postgres + ChromaDB containers. | `docker --version && docker compose version` |
| `psql` (PostgreSQL client) | ≥ 15 | Inspecting the dev DB by hand. | `psql --version` |
| `pre-commit` | ≥ 3 | Git hooks (ruff, prettier, etc.). | `pre-commit --version` |

Optional — only needed once you start working:

| Tool | When you need it |
|------|------------------|
| Playwright browsers | First time you run `pnpm e2e`; auto-installed by `pnpm exec playwright install`. |
| `make` | Pre-installed everywhere except a fresh Windows; comes with Xcode CLT on macOS and `build-essential` on Linux. |

---

## Install recipes

### macOS (Homebrew)

```bash
# Once: install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Core tools
brew install git python@3.11 node@20 pnpm docker docker-compose libpq pre-commit
brew link --force libpq                              # makes `psql` visible
brew install --cask docker                           # Docker Desktop (GUI app)

# uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
exec $SHELL -l                                       # reload PATH

# Verify
git --version && python3 --version && uv --version && node --version \
  && pnpm --version && docker --version && psql --version && pre-commit --version
```

If you already have a different Python via pyenv or system Python, point `uv` at 3.11 explicitly: `uv python install 3.11`.

### Linux (Debian / Ubuntu / WSL2)

```bash
sudo apt update
sudo apt install -y git curl build-essential ca-certificates \
                    postgresql-client \
                    pipx
pipx ensurepath
pipx install pre-commit

# Python 3.11 — the simplest path is the deadsnakes PPA on Ubuntu 22.04+
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3.11-dev

# Node 20 via NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pnpm@9

# Docker Engine + Compose (skip if Docker Desktop is already installed on WSL2 host)
# Follow https://docs.docker.com/engine/install/ubuntu/ for the official repo setup.
sudo usermod -aG docker $USER          # then log out + back in

# uv
curl -LsSf https://astral.sh/uv/install.sh | sh
exec $SHELL -l
```

On WSL2 specifically: install Docker Desktop on **Windows** (not inside the WSL distro), then enable WSL2 integration in Docker Desktop → Settings → Resources → WSL Integration. The `docker` CLI inside Ubuntu will then talk to the Windows-hosted daemon.

### Windows (native — not supported)

Use WSL2 + the Linux recipe above. If you must use native Windows for some reason, expect to debug Postgres + asyncpg + uv issues that are not documented here.

---

## Post-install configuration

Once everything is installed:

```bash
# Tell Git who you are (skip if already set globally)
git config --global user.name "Your Name"
git config --global user.email "you@example.com"

# After cloning the repo, install pre-commit hooks once
cd enigmatrix
pre-commit install
```

The hooks defined in [`.pre-commit-config.yaml`](../../.pre-commit-config.yaml) will run on every commit: trailing-whitespace, end-of-file-fixer, ruff (backend), prettier (frontend).

---

## Environment variables

Copy the example file and fill the two secrets:

```bash
cp .env.example .env
# Generate two strong values
python3 -c 'import secrets; print(secrets.token_hex(32))'   # paste into JWT_SECRET
python3 -c 'import secrets; print(secrets.token_hex(32))'   # paste into APP_SECRET_KEY
```

Every variable in [`.env.example`](../../.env.example) and where it's read:

| Variable | Read by | Purpose |
|----------|---------|---------|
| `APP_ENV` | [`backend/app/settings.py`](../../backend/app/settings.py) | `development` toggles SQLAlchemy `echo=True` and pretty-print logs |
| `APP_SECRET_KEY` | same | Reserved for future Fernet/CSRF; required by Pydantic settings validation |
| `JWT_SECRET` | [`backend/app/core/security.py`](../../backend/app/core/security.py) | HS256 signing key for access + refresh JWTs |
| `JWT_ACCESS_EXPIRE_MINUTES` | same | Default 15. Short-lived access tokens. |
| `JWT_REFRESH_EXPIRE_DAYS` | same | Default 7. Long-lived refresh tokens, rotated on use. |
| `DATABASE_URL` | [`backend/app/db/session.py`](../../backend/app/db/session.py) | Must be `postgresql+asyncpg://...`, not plain `postgresql://`. |
| `CHROMA_HOST` / `CHROMA_PORT` | [`backend/app/settings.py`](../../backend/app/settings.py) | Wired but unused in the MVP slice. |
| `STORAGE_BACKEND` / `STORAGE_LOCAL_PATH` | same | Object-storage abstraction (used once Module 1 ships PDFs). |
| `EMBEDDING_MODEL` | same | Consumed by Module 2 RAG ingestion ([`BUILD_08`](../../backend/BUILD_PLAN/BUILD_08_Module2_Knowledge.md)). |
| `HUGGINGFACE_TOKEN`, `SENTRY_DSN` | same | Optional; leave empty. |
| `CORS_ORIGINS` | [`backend/app/main.py`](../../backend/app/main.py) | Must include the frontend origin (default `http://localhost:3000`). |
| `NEXT_PUBLIC_API_BASE_URL` | [`frontend/lib/api/client.ts`](../../frontend/lib/api/client.ts) | Frontend API base URL. |

Detail on the auth-related variables → [`07_Auth_and_Roles.md`](07_Auth_and_Roles.md).

---

## Accounts to create (free tiers are enough)

| Service | Why | Required for the MVP slice? |
|---------|-----|-----------------------------|
| GitHub | Source control + CI later. | Yes |
| Hugging Face | Model downloads (NLLB, XLM-R) when Module 1/4 ships. | No — leave `HUGGINGFACE_TOKEN` empty |
| Sentry | Error tracking. | No — leave `SENTRY_DSN` empty |

---

## Quick verification of the install

After running the recipe for your OS, run all of these in order. They should all succeed:

```bash
git --version
python3 --version            # should print Python 3.11.x
uv --version
node --version               # should print v20.x
pnpm --version               # should print 9.x
docker --version
docker compose version
psql --version
pre-commit --version
```

If any step fails, see [`09_Troubleshooting.md`](09_Troubleshooting.md). When everything passes, jump to [`02_Quickstart.md`](02_Quickstart.md).

---

**Prev:** [`00_INDEX.md`](00_INDEX.md) &nbsp;·&nbsp; **Next:** [`02_Quickstart.md`](02_Quickstart.md)
