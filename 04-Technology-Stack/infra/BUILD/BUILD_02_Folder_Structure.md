# BUILD 02 — Monorepo Folder Structure

> **Goal:** lock the folder layout for the entire project before any code is written. Changing this later is expensive.
>
> **Read first:** research files `07_System_Architecture.md` (the layered architecture this folder layout instantiates) and `06_Data_Collection_and_Management.md` §4 (the data pipelines that map to `backend/app/ingestion/` and `ml/`).

The structure is a **monorepo with three top-level apps** (`backend/`, `frontend/`, `ml/`) plus shared infrastructure (`infra/`, `docs/`). It is small enough for a 4-person team and large enough to scale.

---

## 1. Top-Level Tree

```
enigmatrix-platform/
├── backend/                      # FastAPI Python service
├── frontend/                     # Next.js TypeScript app
├── ml/                           # Training scripts, notebooks, model artifacts
├── infra/                        # Dockerfiles, compose, nginx, deploy scripts
├── docs/
│   ├── BUILD_PLAN/               # this package
│   ├── research/                 # files 00–12 from the research guide
│   ├── progress/                 # weekly trackers (BUILD_16 templates)
│   └── thesis/                   # IMRaD chapter drafts
├── scripts/                      # cross-cutting one-off scripts
├── .github/workflows/            # CI/CD
├── docker-compose.yml            # production-ish full stack
├── docker-compose.dev.yml        # dev overrides (volumes, hot reload)
├── Makefile
├── .env.example
├── README.md
└── ... (config files from BUILD_01)
```

---

## 2. `backend/` — FastAPI Service

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI() entrypoint, mounts routers
│   ├── settings.py               # Pydantic Settings (reads .env)
│   ├── deps.py                   # FastAPI dependencies (db session, auth user)
│   ├── exceptions.py             # custom exception classes + handlers
│   ├── logging_config.py         # structured logging
│   │
│   ├── api/                      # HTTP layer (one folder per resource)
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py         # aggregates all v1 routers
│   │   │   ├── auth.py           # /auth/login, /auth/register, /auth/refresh
│   │   │   ├── users.py          # /users/me
│   │   │   ├── regulations.py    # Module 1 read endpoints
│   │   │   ├── qa.py             # Module 2 endpoints
│   │   │   ├── risk.py           # Module 3 endpoints
│   │   │   ├── verify.py         # Module 4 endpoints
│   │   │   ├── surveys.py        # all 4 survey instruments
│   │   │   └── admin.py          # admin-only endpoints
│   │   └── health.py             # /health
│   │
│   ├── core/                     # cross-cutting concerns
│   │   ├── security.py           # JWT, password hashing
│   │   ├── i18n.py               # language detection helpers
│   │   └── pagination.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py            # async engine + SessionLocal
│   │   ├── base.py               # SQLAlchemy DeclarativeBase
│   │   └── seed.py               # dev seed function
│   │
│   ├── models/                   # SQLAlchemy ORM (one file per aggregate)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── sme_profile.py
│   │   ├── regulation.py         # regulations + classifications + secondary_appearances
│   │   ├── labeled_example.py
│   │   ├── training_run.py
│   │   ├── model_version.py
│   │   ├── survey.py             # survey_responses, awareness_responses, etc.
│   │   ├── alert.py
│   │   ├── claim.py              # Module 4 claims
│   │   └── audit_log.py
│   │
│   ├── schemas/                  # Pydantic DTOs (request/response)
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── regulation.py
│   │   ├── qa.py
│   │   ├── risk.py
│   │   ├── verify.py
│   │   └── survey.py
│   │
│   ├── services/                 # business logic (the "domain layer")
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── module1/              # awareness pipeline
│   │   │   ├── __init__.py
│   │   │   ├── classifier.py     # loads & runs the XLM-R model
│   │   │   ├── lag_analyzer.py
│   │   │   ├── alert_engine.py
│   │   │   └── summarizer.py
│   │   ├── module2/              # RAG
│   │   │   ├── __init__.py
│   │   │   ├── chunker.py
│   │   │   ├── embedder.py
│   │   │   ├── retriever.py
│   │   │   └── rag_pipeline.py
│   │   ├── module3/              # risk
│   │   │   ├── __init__.py
│   │   │   ├── feature_builder.py
│   │   │   ├── risk_model.py     # XGBoost loader + predict
│   │   │   ├── temporal_model.py # LSTM
│   │   │   └── shap_explainer.py
│   │   ├── module4/              # misinformation
│   │   │   ├── __init__.py
│   │   │   ├── verifier.py
│   │   │   └── claim_normalizer.py
│   │   └── notification_service.py
│   │
│   ├── ingestion/                # scrapers, watchers, schedulers
│   │   ├── __init__.py
│   │   ├── scheduler.py          # APScheduler / Celery wiring
│   │   ├── gazette/
│   │   │   ├── __init__.py
│   │   │   ├── lister.py         # documents.gov.lk listing scraper
│   │   │   ├── downloader.py
│   │   │   └── extractor.py      # PDF → text (PyMuPDF/pdfplumber/OCR)
│   │   ├── news_watcher.py
│   │   ├── portal_watcher.py     # IRD/EPF/SLSI portal watcher
│   │   ├── social_scraper.py     # Module 4 inputs
│   │   └── factcheck_scraper.py
│   │
│   ├── ml_serving/               # thin wrappers around models in inference path
│   │   ├── __init__.py
│   │   ├── registry.py           # picks "production" model from DB
│   │   ├── classifier_loader.py
│   │   └── embeddings_loader.py
│   │
│   ├── storage/                  # file storage abstraction
│   │   ├── __init__.py
│   │   ├── local.py
│   │   └── s3.py
│   │
│   ├── tasks/                    # background jobs (Celery tasks or APS jobs)
│   │   ├── __init__.py
│   │   ├── ingest_gazettes.py
│   │   ├── classify_pending.py
│   │   ├── compute_lag.py
│   │   ├── send_alerts.py
│   │   └── refresh_kb.py
│   │
│   ├── scripts/                  # invoked via `python -m app.scripts.X`
│   │   ├── __init__.py
│   │   ├── seed_dev.py
│   │   ├── export_dataset.py
│   │   ├── mark_examples_trained.py
│   │   └── promote_model.py
│   │
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── unit/
│       ├── integration/
│       └── e2e/
│
├── alembic/                      # DB migrations
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
├── pyproject.toml                # ruff, pytest, project metadata
├── uv.lock
├── Dockerfile
└── README.md
```

### Why these subdivisions?

- **`api/` ↔ `services/` ↔ `models/` separation** = classic three-layer architecture. API layer is thin; logic lives in services; persistence in models. Easy to test and easy to swap.
- **`services/moduleN/`** = each research module is its own package, enabling parallel team work without merge conflicts.
- **`ingestion/` is separate** = scrapers run on a schedule independently of the request path; isolating them prevents one slow scraper from blocking API requests.
- **`ml_serving/` is *not* `ml/`** = the in-API path that loads model weights at request time. The standalone `ml/` folder is for *training*, which never runs inside the API process.

---

## 3. `frontend/` — Next.js 14 (App Router)

```
frontend/
├── app/
│   ├── layout.tsx                # root layout (theme, providers)
│   ├── page.tsx                  # marketing home
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── (app)/                    # logged-in shell
│   │   ├── layout.tsx            # sidebar + topbar
│   │   ├── dashboard/page.tsx
│   │   ├── regulations/
│   │   │   ├── page.tsx          # list (Module 1)
│   │   │   └── [id]/page.tsx     # detail
│   │   ├── qa/page.tsx           # Module 2 chat
│   │   ├── verify/page.tsx       # Module 4 verifier
│   │   ├── risk/page.tsx         # Module 3 score + SHAP
│   │   └── surveys/
│   │       ├── awareness/page.tsx
│   │       ├── knowledge/page.tsx
│   │       ├── vulnerability/page.tsx
│   │       └── misinformation/page.tsx
│   ├── (admin)/                  # role-guarded admin
│   │   ├── layout.tsx
│   │   ├── annotation/page.tsx
│   │   ├── training/page.tsx
│   │   ├── models/page.tsx
│   │   ├── datasets/page.tsx
│   │   └── lag/page.tsx          # research dashboard
│   ├── api/                      # Next.js route handlers (proxy/SSR helpers only)
│   └── [locale]/                 # i18n root if using locale segments
├── components/
│   ├── ui/                       # primitives (Button, Input, Card…)
│   ├── layout/                   # Sidebar, TopBar, MobileNav
│   ├── module1/                  # RegulationCard, LagBadge, AlertBanner
│   ├── module2/                  # ChatBubble, CitationPopover
│   ├── module3/                  # RiskGauge, ShapBarChart
│   ├── module4/                  # VerdictBadge, EvidenceList
│   ├── forms/                    # SurveyForm, ConsentBlock, RatingSlider
│   └── charts/                   # wraps recharts
├── lib/
│   ├── api/
│   │   ├── client.ts             # fetch wrapper with auth
│   │   ├── auth.ts
│   │   ├── regulations.ts
│   │   ├── qa.ts
│   │   ├── risk.ts
│   │   └── verify.ts
│   ├── auth/                     # session helpers
│   ├── i18n/
│   │   ├── config.ts             # locales: en, si, ta
│   │   ├── messages/
│   │   │   ├── en.json
│   │   │   ├── si.json
│   │   │   └── ta.json
│   │   └── server.ts
│   ├── hooks/
│   ├── utils/
│   └── types/                    # shared TS types (mirror Pydantic schemas)
├── public/                       # static assets, fonts (Sinhala/Tamil)
├── styles/
│   └── globals.css
├── tests/
│   ├── unit/
│   └── e2e/                      # Playwright
├── next.config.mjs
├── tailwind.config.ts
├── postcss.config.mjs
├── tsconfig.json
├── package.json
├── pnpm-lock.yaml
├── playwright.config.ts
├── Dockerfile
└── README.md
```

### Frontend conventions

- **App Router** (Next 14) with route groups `(auth)`, `(app)`, `(admin)` for layout sharing.
- **One folder per module** under `components/` — keeps research-module code visually grouped.
- **`lib/api/`** = strongly-typed API client, one file per backend resource. **All `fetch` goes through `client.ts`** — single place for auth headers and base URL.
- **i18n**: `next-intl` with three locales (en/si/ta). Locale-aware fonts via `next/font`.

---

## 4. `ml/` — Training, Notebooks, Artifacts

```
ml/
├── pyproject.toml                # separate Python project (heavier deps: torch, transformers)
├── uv.lock
├── module1/
│   ├── data/
│   │   ├── pull_from_db.py       # exports labeled_examples to parquet
│   │   └── splits.py             # temporal train/val/test split
│   ├── baselines/
│   │   ├── tfidf_lr.py
│   │   └── zero_shot_llm.py
│   ├── train_xlmr.py             # main fine-tuning script
│   ├── evaluate.py
│   ├── error_analysis.ipynb
│   └── README.md
├── module2/
│   ├── build_kb.py               # chunk + embed regulations into ChromaDB
│   ├── tune_retrieval.py
│   └── eval_ragas.py
├── module3/
│   ├── feature_engineering.py
│   ├── train_xgboost.py
│   ├── train_lstm.py
│   ├── shap_analysis.ipynb
│   └── synthetic_data.py         # SDV / CTGAN
├── module4/
│   ├── train_verifier.py
│   ├── spread_analysis.ipynb
│   └── annotation_export.py
├── shared/
│   ├── tracking.py               # wandb / mlflow init helpers
│   ├── seeds.py
│   ├── metrics.py
│   └── promote.py                # writes model_versions row, sets is_production
├── artifacts/                    # gitignored — model weights
│   └── .gitkeep
├── mlruns/                       # MLflow local backend (gitignored)
└── notebooks/                    # exploratory; convert to .py before merging
```

> Why split `backend/` and `ml/`? The API container should be **small and CPU-only**. Training requires `torch` + GPU + datasets — hundreds of MB. Keeping them separate means the production image is < 1 GB.

---

## 5. `infra/` — Containers, Configs, Deploy

```
infra/
├── docker/
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── ml-trainer.Dockerfile     # GPU-friendly, used in CI / Colab / Lambda
├── nginx/
│   ├── nginx.conf
│   └── sites-available/
│       └── enigmatrix.conf
├── deploy/
│   ├── provision_vm.sh           # idempotent VM bootstrap
│   ├── deploy.sh                 # SSH deploy script
│   └── backup_db.sh              # nightly pg_dump → S3
├── postgres/
│   └── init.sql                  # extensions: pgcrypto, uuid-ossp
├── chromadb/
│   └── persist/                  # volume mount target (gitignored)
└── monitoring/
    ├── prometheus.yml
    └── grafana/
        └── dashboards/
```

---

## 6. `docs/` — All Markdown

```
docs/
├── BUILD_PLAN/                   # this package (BUILD_00..BUILD_17)
├── research/                     # files 00..12 (research guide)
├── progress/
│   ├── milestones.md
│   ├── weekly/
│   │   ├── 2026-w01.md
│   │   ├── 2026-w02.md
│   │   └── ...
│   └── modules/
│       ├── module1.md
│       ├── module2.md
│       ├── module3.md
│       └── module4.md
├── thesis/
│   ├── 01_introduction.md
│   ├── 02_literature_review.md
│   ├── 03_methodology.md
│   ├── 04_module1.md
│   ├── 05_module2.md
│   ├── 06_module3.md
│   ├── 07_module4.md
│   ├── 08_results.md
│   ├── 09_discussion.md
│   └── 10_conclusion.md
└── adr/                          # Architecture Decision Records
    ├── 0001-monolith-over-microservices.md
    ├── 0002-postgres-as-source-of-truth.md
    └── 0003-xlm-r-over-mbert.md
```

---

## 7. Naming Conventions

| Thing | Convention | Example |
|-------|------------|---------|
| Python module/file | `snake_case.py` | `gazette_extractor.py` |
| Python class | `PascalCase` | `GazetteExtractor` |
| Python function/var | `snake_case` | `extract_text()` |
| Database table | `snake_case`, plural | `regulations`, `labeled_examples` |
| Database column | `snake_case` | `gazette_date` |
| API path | `kebab-case`, plural | `/api/v1/regulations`, `/api/v1/labeled-examples` |
| TS file | `camelCase.ts` for utils, `PascalCase.tsx` for components | `apiClient.ts`, `RegulationCard.tsx` |
| TS variable | `camelCase` | `regulationId` |
| TS type/interface | `PascalCase` | `Regulation`, `RiskScore` |
| Branch | `feature/<short>` / `fix/<short>` | `feature/m1-pdf-extractor` |
| Migration file | `YYYYMMDDHHMM_<desc>.py` | `202604110900_add_regulations.py` |

---

## 8. Module-Owner Cheat Sheet

| Owner | Daily working dirs |
|-------|--------------------|
| Module 1 | `backend/app/services/module1/`, `backend/app/ingestion/gazette/`, `backend/app/api/v1/regulations.py`, `frontend/app/(app)/regulations/`, `frontend/components/module1/`, `ml/module1/` |
| Module 2 | `backend/app/services/module2/`, `backend/app/api/v1/qa.py`, `frontend/app/(app)/qa/`, `frontend/components/module2/`, `ml/module2/` |
| Module 3 | `backend/app/services/module3/`, `backend/app/api/v1/risk.py`, `frontend/app/(app)/risk/`, `frontend/components/module3/`, `ml/module3/` |
| Module 4 | `backend/app/services/module4/`, `backend/app/ingestion/social_scraper.py`, `backend/app/api/v1/verify.py`, `frontend/app/(app)/verify/`, `frontend/components/module4/`, `ml/module4/` |

---

## 9. Acceptance Criteria

- [ ] All directories from §1–§6 exist with `.gitkeep` placeholders where empty
- [ ] `backend/`, `frontend/`, `ml/` each have their own `pyproject.toml` / `package.json` and run independently
- [ ] `docs/BUILD_PLAN/` is populated with files from this package
- [ ] `docs/research/` is populated with files `00_INDEX.md` through `12_Module1_End_to_End_Workflow.md`
- [ ] All files match the naming conventions in §7
- [ ] One ADR exists in `docs/adr/` recording the choice of monorepo layout

---

## 10. Claude Prompts for This Section

### Prompt 1 — Generate the empty tree

```
Generate a single bash script `scripts/scaffold_tree.sh` that creates the exact
directory layout described in BUILD_02 §1–§6 of the Enigmatrix build plan.
Use `mkdir -p` and `touch .gitkeep` in empty dirs.
Make the script idempotent (re-runnable) and add a final `tree -L 2` to print results.
```

### Prompt 2 — Generate per-folder READMEs

```
For each of these folders, generate a 10–20 line README.md describing its purpose,
what lives there, and what does NOT live there:
- backend/app/api/
- backend/app/services/
- backend/app/ingestion/
- backend/app/models/
- ml/
- ml/shared/
- infra/

Output as separate fenced code blocks with `# FILE: <path>/README.md` headers.
```

### Prompt 3 — Architecture Decision Record

```
Write an ADR (Architecture Decision Record) in standard format
(Status, Context, Decision, Consequences) for:
"Use a monorepo with backend/, frontend/, ml/ separated by language and runtime
rather than a polyrepo or a single Python project."

Length: ~250 words. Reference Sri Lankan SME platform context where relevant.
Save as `docs/adr/0001-monorepo-layout.md`.
```

---

**Prev:** `BUILD_01_Project_Initialization.md` &nbsp;·&nbsp; **Next:** `BUILD_03_Backend_API.md`
