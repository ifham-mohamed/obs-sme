# M1 Module Reorganization — Plan, Execution Record & Multi-Module Convention

> Goal: make every piece of **Module 1 (Awareness Gap)** code trivially identifiable by living under a single per-layer `m1/` parent folder, while shared "startup / config / sign-in / cross-module" code stays common. The same folder shape then becomes the **template** every future module (M2, M3, M4) slots into.
>
> Generated for the `xyz/` monorepo (backend / frontend / infrastructure / ml — each a git submodule). This file is both the design rationale and the rollback map.

---

## 0. Guiding principles

1. **One parent folder per module, per layer.** `m1/` (and later `m2/`, `m3/`, `m4/`) is the single home for that module's code inside each layer. Grouping beats prefixes: you can `ls m1/`, delete it, own it, or hand it to a teammate as a unit.
2. **Shared stays shared.** Startup/bootstrapping (`main.py`, `settings.py`, Celery app, Alembic env, Next.js root layout), authentication / sign-in, RBAC, audit, the base `regulation`/`sector`/`domain` domain models, and the survey engine are **cross-module** and must NOT move into `m1/`. They are the platform the modules stand on.
3. **Identity is decoupled from location.** Celery task _names_, HTTP route _paths_, and DB _table names_ are public contracts. Moving a file changes its import path but must **not** change these contracts. (Enforced below.)
4. **History-preserving moves.** Every move uses `git mv` so `git log --follow` and `git blame` survive.
5. **Repeatable, not bespoke.** The move is driven by a deterministic mapping so M2/M3/M4 can be reorganized the same way.

---

## 1. The M1-vs-shared boundary (decided by import analysis)

**Moved into `m1/` (true Module-1 code):** everything with the `m1_` prefix (models, services, schemas, API routers), the `admin_m1_pipeline` router, and the whole `tasks/m1/` task package. On the frontend: the M1 admin pages, the `m1` / `m1-extraction` / `m1-pipeline` component & lib folders, and M1 docs. In ML: the already-existing `m1/` package plus its tests and model artifacts.

**Kept shared (verified by `grep` of cross-module imports):**

| File / area                                                                                                               | Why it stays shared                                                                                                                                      |
| ------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/models/regulation.py` (`M1Regulation`, `M1RegulationSector`)                                                         | Imported by `survey_sessions`, `survey_question_service`, `dashboard`, `admin_translations` and seed scripts — it is the base domain model, not M1-only. |
| `app/models/{sector,regulatory_domain,sme_profile,user,audit_log,survey*}.py`                                             | Cross-module domain + platform models.                                                                                                                   |
| `app/services/{auth_service,audit_service,survey*,i18n_utils}.py`                                                         | Sign-in, RBAC, audit, survey engine — the common platform.                                                                                               |
| `app/{main,settings,deps,exceptions,logging_config,celery_config}.py`, `app/core`, `app/db`, `app/middleware`, `alembic/` | Startup / config / bootstrap.                                                                                                                            |
| Frontend `app/(auth)/*`, root `layout.tsx`, `middleware.ts`, `lib/api`, `components/common`, `components/layout`          | Sign-in and shared shell.                                                                                                                                |
| All `infra/` (nginx, postgres, docker-compose)                                                                            | Single shared runtime; M1 has no separate infra.                                                                                                         |

Verification performed: `grep` confirmed **no** M2/M3/survey module imports any `m1_` service/model, so the boundary is clean on the consumer side.

---

## 2. Target layout

### Backend (`enigmatrix-backend/app/`)

```
app/
  main.py  settings.py  deps.py  celery_config.py   # shared startup (unchanged)
  core/  db/  middleware/  utils/                     # shared
  models/    # shared domain models ONLY (regulation, sector, user, survey, m2_, m3_ …)
  services/  # shared services ONLY (auth, audit, survey …)
  api/v1/    # shared routers (auth, users, dashboard, surveys, m2, m3 …)
  schemas/   # shared schemas
  m1/                       # ← Module 1 home
    __init__.py
    api/          # was api/v1/m1_*.py + admin_m1_pipeline.py   (prefix dropped)
    models/       # was models/m1_*.py
    schemas/      # was schemas/m1_*.py
    services/     # was services/m1_*.py
    tasks/        # was tasks/m1/*  (Celery task *names* preserved as "app.tasks.m1.*")
```

Prefix is dropped on move (`m1_alert.py` → `m1/models/alert.py`) because the folder already carries the namespace — matching how `enigmatrix-ml/m1/` is organized.

### Frontend (`enigmatrix-frontend/`)

Route groups stay (Next.js App Router semantics); M1 code is consolidated and labelled:

```
app/(admin)/admin/m1/…              # M1 admin pages (already grouped)
app/(app)/…                          # shared user shell
components/m1/                        # canonical M1 component home
  extraction/  pipeline/  docs/       # merged from components/m1-extraction, -pipeline, docs/m1
lib/m1/                               # merged from lib/m1-extraction, m1-pipeline, m1-docs.generated
app/(auth)/…                          # sign-in — SHARED, untouched
```

### ML (`enigmatrix-ml/`)

Already module-first (`m1/` with `data/ extraction/ model/ preprocessing/ evaluation/`). Aligned so `tests/m1/` and `storage/models/m1/` sit beside it consistently.

### Infra (`enigmatrix-infrastructure/`, `infra/`)

Shared runtime; **not** split by module. Documented as such; any M1-specific ops (scraper cron, worker) are expressed in the shared compose/Celery beat, which already labels them by module.

---

## 3. Contract-preservation rules (the risky bits)

1. **Celery task names unchanged.** All 17 tasks use explicit `@task(name="app.tasks.m1.<mod>.<fn>")`. The move rewrites _import paths_ (`app.tasks.m1.x` → `app.m1.tasks.x`) and the Celery `include=[…]` list, but **leaves the `name=` strings and beat-schedule `"task":` strings exactly as `app.tasks.m1.*`**. Result: no in-flight task, no queued message, and no beat entry breaks on deploy.
2. **Test monkeypatch targets follow the code.** `patch("app.tasks.m1.<mod>.<attr>")` targets _are_ rewritten to the new location — they must match where the object now lives.
3. **HTTP routes unchanged.** Router `prefix=`/`tags=` are untouched; only the `from app.api.v1 import m1_*` wiring in `router.py` changes to `from app.m1.api import …`.
4. **DB tables/migrations unchanged.** `__tablename__` and SQLAlchemy relationship string refs use _class names_, not import paths, so they are inert to the move. `models/__init__.py` re-imports the moved model classes from `app.m1.models.*` so Alembic autogenerate still sees every table.

---

## 4. Execution order (all on the working tree; reversible via git)

1. Backend — scripted `git mv` + mapping-driven import rewrite → byte-compile all → grep for stale paths.
2. Frontend — consolidate `m1*` component/lib folders → rewrite `@/` imports → `tsc --noEmit` (user runs full `next build`).
3. ML — align `tests/m1`, `storage/models/m1` references.
4. Infra — document shared status; no code move.
5. Update `models/__init__.py`, `router.py`, `celery_config.py` wiring; refresh `graphify update .`; update `AI_WORK_LOG.md` + tracker.

**Verification I can run here:** `python -m py_compile` across the whole backend, static grep that zero stale `app.(models|services|schemas|api.v1).m1_` / `app.tasks.m1` import paths remain, and `tsc` on the frontend. **Verification you must run before deploy:** `pytest` (needs Postgres/Redis), `next build`, `alembic upgrade head`, and a Celery worker boot (`celery -A app.celery_config inspect registered`) to confirm the 17 task names resolve.

---

## 5. Future adaptation — the multi-module convention

To add **M2 / M3 / M4** (or refactor them into this shape):

1. **Create the parent:** `app/m<N>/{api,models,services,schemas,tasks}/` in backend; `components/m<N>/`, `lib/m<N>/`, `app/(admin)/admin/m<N>/` in frontend; `enigmatrix-ml/m<N>/` in ML.
2. **Move, don't prefix:** relocate `m<N>_*` files in, drop the prefix.
3. **Keep contracts:** preserve Celery `name=`, route prefixes, table names during the move.
4. **Re-export models** from the shared `models/__init__.py` so Alembic keeps seeing them.
5. **Leave shared alone:** auth/sign-in, settings, survey engine, base `regulation`/`sector` models, infra — never move these into a module folder.
6. **One PR per module per layer**, each independently byte-compile/`tsc`/test-green, so review and rollback stay small.

A module is then a vertical slice you can read, test, hand off, or (later) extract into its own service by lifting its `m<N>/` folder — which is exactly what principle #6 in §0 buys us.

---

_Execution status and the exact file map are appended in §6 below as the work is applied._

## 6. Execution record (applied 2026-07-18)

**Backend — DONE.** 67 files moved into `app/m1/{api(10),models(11),schemas(8),services(25),tasks(17)}` (counts include `__init__.py`). `m1_` prefix dropped on move; `admin_m1_pipeline.py`→`m1/api/admin_pipeline.py`. Imports rewritten in 57 files. Celery `include=[...]`→`app.m1.tasks.*`; all 17 `@task(name=...)` identities and 6 beat `"task":` entries preserved. `models/__init__.py` and `router.py` re-point/alias to the new locations. Verified: `compileall` clean, static import resolver 0 missing.

**Frontend — DONE.** `components/{m1-extraction→m1/extraction, m1-pipeline→m1/pipeline, docs/m1→m1/docs}`; `lib/{m1-extraction→m1/extraction, m1-pipeline→m1/pipeline, m1-docs.ts→m1/docs.ts, m1-docs.generated(.json)→m1/docs.generated(.json)}`. 27 files rewritten. Static resolver: 0 unresolved. Shared `components/forms/m1-extraction-run-form.tsx` + `lib/api/m1-pipeline.ts` deliberately left in cross-cutting folders.

**ML — NO CHANGE.** Already module-first (`m1/` import root, `tests/m1/`, `storage/models/m1/`). It is the reference for this convention.

**Infra — NO CHANGE.** Single shared runtime; module ops already labelled in the shared compose/Celery beat.

**Verification run here:** backend `python -m compileall app` → exit 0; backend static `app.*` import resolver → 0 missing; frontend `@/…/m1/…` resolver → 0 unresolved.

**Verification you must run before deploy (needs services the sandbox lacks):**

```
# backend
cd enigmatrix-backend && pytest -q
alembic upgrade head            # expect no new migration (tables unchanged)
celery -A app.celery_config inspect registered   # confirm 17 task names present
# frontend
cd enigmatrix-frontend && pnpm build   # or: npx tsc --noEmit
# graph
graphify update .
```

**Cleanup (host-locked during the session — a running worker/editor held them):**
delete `enigmatrix-backend/app/tasks/m1/__pycache__/` (stale `.pyc`, sources already moved) and `enigmatrix-backend/_m1_migrate.py` (the one-shot migration script) after stopping that process.

**Commit guidance:** commit each submodule separately; `git add -A` will record the moves as renames (rename detection survives the small import edits), preserving `git log --follow`/`blame`. A stale `.git/index.lock` in `enigmatrix-backend` (and `enigmatrix-infrastructure`) blocked `git mv` here — remove it (`rm .git/index.lock`) before committing if it persists.
