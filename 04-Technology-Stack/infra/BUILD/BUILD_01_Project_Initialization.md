# BUILD 01 — Project Initialization

> **Goal:** by the end of this file, the team has a working monorepo, all required tools installed, accounts created, and a `hello world` from both backend and frontend visible in the browser.
>
> **Read first:** research files `04_Technology_Stack_Justification.md` (the canonical stack you are installing) and `07_System_Architecture.md` §10 (the deployment topology this initialization targets).

---

## 1. Prerequisites — Tools to Install on Every Dev Machine

| Tool | Version | Why |
|------|---------|-----|
| Git | ≥ 2.40 | Version control |
| Python | 3.11.x | Backend, ML training |
| Node.js | 20 LTS | Frontend |
| pnpm | ≥ 8 | Faster, disk-efficient package manager (use over npm) |
| Docker Desktop | latest | Postgres, ChromaDB, full-stack run |
| Docker Compose | v2 | Bundled with Docker Desktop |
| VS Code | latest | Recommended editor |
| PostgreSQL client (`psql`) | 15+ | Manual DB inspection |
| pre-commit | latest | Git hooks for lint/format |
| `uv` (optional) | latest | 10–100× faster Python env manager |

**VS Code extensions (install via the Workspace recommendations file in §6):**
- Python
- Pylance
- Ruff
- ESLint
- Prettier
- Tailwind CSS IntelliSense
- GitLens
- Docker
- Even Better TOML
- DotENV

---

## 2. Accounts to Create (Free Tiers Are Enough)

| Service                             | Purpose                         | Tier                          |
| ----------------------------------- | ------------------------------- | ----------------------------- |
| GitHub                              | Code, Actions, Issues, Projects | Free                          |
| Hugging Face                        | Model hub, datasets             | Free                          |
| Weights & Biases                    | Experiment tracking             | Free academic                 |
| Sentry                              | Error monitoring                | Free dev                      |
| DigitalOcean / AWS / Azure students | Single VM hosting               | $25–50/mo or student credit   |
| Cloudflare                          | DNS + free TLS                  | Free                          |
| Google Cloud (optional)             | Translation API                 | Free trial                    |
| OpenAI / Anthropic (optional)       | Zero-shot baselines             | Pay-as-you-go (~$30 lifetime) |

> **Rule:** never commit API keys. They live in `.env` files and `${{ secrets.* }}` in CI.

---

## 3. Repository Bootstrap

### 3.1 Create the repo

```bash
# RUN
mkdir enigmatrix-platform && cd enigmatrix-platform
git init -b main
gh repo create enigmatrix/platform --private --source=. --push   # if using GitHub CLI
```

### 3.2 Top-level scaffolding files

Create these at the repo root:

```
enigmatrix-platform/
├── .gitignore
├── .editorconfig
├── .pre-commit-config.yaml
├── .python-version
├── .nvmrc
├── README.md
├── LICENSE
├── docker-compose.yml
├── docker-compose.dev.yml
├── Makefile
├── .env.example
├── .vscode/
│   ├── settings.json
│   └── extensions.json
└── docs/
    ├── BUILD_PLAN/        # this package
    ├── research/          # files 00–12 from the research guide
    └── research/          # weekly tracker (see BUILD_16)
```

### 3.3 `.gitignore` (essentials)

```gitignore
# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/

# Node
node_modules/
.next/
.turbo/
dist/
build/

# Env
.env
.env.local
.env.*.local

# IDE
.vscode/*
!.vscode/settings.json
!.vscode/extensions.json
.idea/

# Data / models / artifacts (LFS or S3 instead)
data/raw/
data/processed/
ml/artifacts/
ml/wandb/
*.parquet
*.pkl

# OS
.DS_Store
Thumbs.db
```

### 3.4 `.env.example` (commit this; copy to `.env` and fill locally)

```bash
# ---- Backend ----
APP_ENV=development
APP_SECRET_KEY=change-me-in-prod
JWT_SECRET=change-me-too
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7

# ---- Database ----
POSTGRES_USER=enigmatrix
POSTGRES_PASSWORD=devpass
POSTGRES_DB=enigmatrix
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://enigmatrix:devpass@localhost:5432/enigmatrix

# ---- Vector DB ----
CHROMA_HOST=localhost
CHROMA_PORT=8001

# ---- Storage ----
STORAGE_BACKEND=local             # local | s3
STORAGE_LOCAL_PATH=./storage

# ---- ML ----
HUGGINGFACE_TOKEN=
WANDB_API_KEY=
MLFLOW_TRACKING_URI=file:./ml/mlruns

# ---- External APIs (optional) ----
GOOGLE_TRANSLATE_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# ---- Sentry ----
SENTRY_DSN=

# ---- Frontend ----
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_DEFAULT_LOCALE=en
```

### 3.5 `.editorconfig`

```ini
root = true
[*]
end_of_line = lf
insert_final_newline = true
charset = utf-8
indent_style = space
indent_size = 2
trim_trailing_whitespace = true

[*.py]
indent_size = 4

[Makefile]
indent_style = tab
```

### 3.6 `.python-version` and `.nvmrc`

```
# .python-version
3.11.9
```
```
# .nvmrc
20
```

---

## 4. Pre-commit Hooks

Pre-commit catches formatting and linting issues before they reach CI.

### `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1024']
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
        args: [--fix]
        files: ^backend/
      - id: ruff-format
        files: ^backend/

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.1.0
    hooks:
      - id: prettier
        files: ^frontend/
        types_or: [javascript, jsx, ts, tsx, css, json, yaml, markdown]
```

```bash
# RUN
pip install pre-commit
pre-commit install
```

---

## 5. Top-Level `Makefile`

The Makefile is the single entry point for common dev commands.

```makefile
.PHONY: help up down logs backend frontend test lint fmt migrate seed

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up:                        ## Start all services (postgres, chroma, backend, frontend)
	docker compose -f docker-compose.dev.yml up -d
	@echo "Backend → http://localhost:8000/docs"
	@echo "Frontend → http://localhost:3000"

down:                      ## Stop all services
	docker compose -f docker-compose.dev.yml down

logs:                      ## Tail logs from all services
	docker compose -f docker-compose.dev.yml logs -f

backend:                   ## Run backend in foreground (uvicorn reload)
	cd backend && uv run uvicorn app.main:app --reload --port 8000

frontend:                  ## Run frontend in foreground
	cd frontend && pnpm dev

test:                      ## Run all tests
	cd backend && uv run pytest -q
	cd frontend && pnpm test

lint:                      ## Lint everything
	cd backend && uv run ruff check .
	cd frontend && pnpm lint

fmt:                        ## Format everything
	cd backend && uv run ruff format .
	cd frontend && pnpm format

migrate:                   ## Apply DB migrations
	cd backend && uv run alembic upgrade head

seed:                      ## Seed dev data
	cd backend && uv run python -m app.scripts.seed_dev
```

---

## 6. VS Code Workspace Settings

### `.vscode/settings.json`

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/bin/python",
  "python.analysis.typeCheckingMode": "basic",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": { "source.fixAll": "explicit" }
  },
  "[typescript]": { "editor.defaultFormatter": "esbenp.prettier-vscode", "editor.formatOnSave": true },
  "[typescriptreact]": { "editor.defaultFormatter": "esbenp.prettier-vscode", "editor.formatOnSave": true },
  "tailwindCSS.experimental.classRegex": [
    ["cva\\(([^)]*)\\)", "[\"'`]([^\"'`]*).*?[\"'`]"]
  ],
  "files.exclude": {
    "**/__pycache__": true,
    "**/.pytest_cache": true,
    "**/.ruff_cache": true,
    "**/node_modules": true
  }
}
```

### `.vscode/extensions.json`

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "bradlc.vscode-tailwindcss",
    "eamodio.gitlens",
    "ms-azuretools.vscode-docker",
    "tamasfe.even-better-toml",
    "mikestead.dotenv"
  ]
}
```

---

## 7. README — One-Page Onboarding

Keep the root `README.md` short and runnable:

```markdown
# Enigmatrix Platform

SME Regulatory Intelligence Platform — final year research project (2026).

## Quick start (15 minutes)

1. Install prerequisites (see `docs/BUILD_PLAN/BUILD_01_Project_Initialization.md`)
2. Copy `.env.example` → `.env` and fill secrets
3. `make up` — starts Postgres + ChromaDB + backend + frontend
4. Visit `http://localhost:3000`

## Documentation

- Build instructions: `docs/BUILD_PLAN/`
- Research methodology: `docs/research/`
- Weekly progress: `docs/progress/`

## Architecture

5-layer monolith (see research file `07_System_Architecture.md`).
```

---

## 8. First Verifiable Milestone

Before moving to file 02, prove this works:

```bash
# RUN
git clone <repo>
cp .env.example .env
make up
# Wait 30s
curl http://localhost:8000/health     # → {"status":"ok"}
open http://localhost:3000             # → "Hello, Enigmatrix"
```

(The placeholder backend `/health` and the placeholder frontend page are scaffolded in files 03 and 05 respectively. For now, you can verify Docker, env files, and the Makefile work by spinning up an empty Postgres + Chroma.)

---

## 9. Branching Strategy

- `main` — protected, always deployable.
- `develop` — integration branch.
- `feature/<module>-<short-desc>` — e.g. `feature/m1-gazette-scraper`.
- `fix/<short-desc>` — bug fixes.
- `chore/<short-desc>` — refactors, deps.

Pull request reviews required for `develop` and `main`. Squash-merge by default.

---

## 10. Acceptance Criteria

- [ ] All four team members have the same Python and Node versions (`python --version`, `node --version`)
- [ ] `git clone` + `cp .env.example .env` + `make up` produces no errors
- [ ] `pre-commit run --all-files` passes
- [ ] `.env` is in `.gitignore` (verify with `git check-ignore -v .env`)
- [ ] GitHub repo has `main` and `develop` branches with branch protection
- [ ] All four members have access to: GitHub, W&B project, Hugging Face org

---

## 11. Claude Prompts for This Section

> Paste these into a fresh Claude chat. Replace `<...>` placeholders with your repo specifics.

### Prompt 1 — Bootstrap repo files

```
You are setting up a Python + TypeScript monorepo named "enigmatrix-platform".
Generate exactly these files with sensible content:
- .gitignore (Python + Node + ML artifacts)
- .editorconfig
- .pre-commit-config.yaml (ruff + prettier + standard hooks)
- .env.example (matching the variables in BUILD_01 §3.4)
- Makefile (matching BUILD_01 §5)
- README.md (≤ 60 lines, runnable steps)
- .vscode/settings.json and .vscode/extensions.json

Output each file as a separate fenced code block with a `# FILE: <path>` header.
Do not include any explanation outside the code blocks.
```

### Prompt 2 — Verify the bootstrap

```
Given the repo files above, write a single bash script `scripts/verify_bootstrap.sh`
that checks: Python 3.11+, Node 20+, Docker running, .env exists, pre-commit installed,
and prints a green/red status for each. Exit 1 on any failure.
```

### Prompt 3 — Onboarding doc

```
Write a 1-page onboarding doc for a new team member joining "enigmatrix-platform".
Audience: a final-year IT student who has used Python and React but never set up a monorepo.
Cover: installing tools, cloning, env setup, first command to run, who to contact when stuck.
Length: 400–500 words. Markdown.
```

---

**Prev:** `BUILD_00_INDEX.md` &nbsp;·&nbsp; **Next:** `BUILD_02_Folder_Structure.md`
