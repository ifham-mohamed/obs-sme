# 04 — Backend Development

> **Goal:** add a new endpoint end-to-end without inventing a pattern. Every convention here is already followed by `auth` and `surveys`; copy them.
>
> **Prerequisite:** [`02_Quickstart.md`](02_Quickstart.md) ran to completion; `make dev-backend` shows the OpenAPI UI at `http://localhost:8000/docs`.

---

## 1. Day-to-day commands

All run from the `backend/` directory.

| Command | What it does |
|---------|--------------|
| `uv sync` | Install / update Python dependencies from [`pyproject.toml`](../../backend/pyproject.toml). |
| `uv run uvicorn app.main:app --reload --port 8000` | Run the API with autoreload. (Or `make dev-backend` from the repo root.) |
| `uv run python -m app.scripts.seed_dev` | Re-seed the dev DB. Idempotent. |
| `uv run alembic revision --autogenerate -m "..."` | Generate a migration after editing models. Always review the generated file before committing. |
| `uv run alembic upgrade head` | Apply pending migrations. |
| `uv run alembic downgrade -1` | Roll back one migration. |
| `uv run pytest -q` | Run every test (unit + integration). |
| `uv run pytest app/tests/integration/test_survey_flow.py -v` | Run a single file. |
| `uv run ruff check .` | Lint. |
| `uv run ruff format .` | Auto-format. |

`uv run` is the canonical entrypoint — it activates the project's virtualenv on the fly. No need to `source .venv/bin/activate` anywhere.

---

## 2. Directory map

```
backend/app/
├── main.py              ← create_app(): CORS, rate-limit, exception handlers, routers
├── settings.py          ← Pydantic Settings (env-driven)
├── logging_config.py    ← structlog setup
├── exceptions.py        ← DomainError + register_exception_handlers()
├── deps.py              ← get_db, get_current_user, require_admin, require_annotator
│
├── api/
│   ├── health.py
│   └── v1/
│       ├── router.py               ← aggregates all v1 routers
│       ├── auth.py                 ← register / login / refresh, rate-limited
│       ├── users.py                ← /me + admin /
│       ├── surveys.py              ← submit + admin list (legacy direct-submit)
│       ├── survey_flow.py          ← regulation-scoped flow (GET start, POST answer)
│       ├── survey_sessions.py      ← session lifecycle (start, next-question, answer, complete, history)
│       ├── m1_regulations.py       ← regulation CRUD (admin) + SME list
│       ├── m2.py                   ← M2 knowledge: GET /m2/sme/{id}/knowledge_score, GET /m2/questions/for-sector/{code}
│       ├── m3.py                   ← M3 vulnerability: POST /m3/compliance-history, POST /m3/behavioural, GET /m3/sme/{id}/risk-signals
│       ├── admin_survey_questions.py ← question CRUD + M:N linkage + branching validation
│       ├── admin_survey_limits.py  ← survey_limits singleton read/write (admin)
│       ├── admin_audit.py          ← activity log read (admin)
│       ├── admin_translations.py   ← translation queue: union read + PATCH for SI/TA fields
│       ├── dashboard.py            ← GET /dashboard/pending-regulations (sector-relevant regs not yet touched)
│       └── regulations.py / qa.py / risk.py / verify.py   ← 501 stubs (BUILD_07/08/10)
│
├── core/
│   ├── security.py      ← hash_password, JWT make/decode
│   └── rate_limit.py    ← slowapi limiter + install_rate_limiter()
│
├── db/
│   ├── session.py       ← async engine + SessionLocal
│   └── base.py          ← DeclarativeBase + TimestampMixin
│
├── models/              ← one file per aggregate
│   ├── user.py / sme_profile.py / survey.py / audit_log.py
│   ├── survey_question.py / survey_session.py / survey_limits.py
│   └── __init__.py      ← MUST import every model (Alembic discovery)
│
├── schemas/             ← Pydantic DTOs, one file per resource
│   └── auth.py / user.py / survey.py / survey_question.py / survey_session.py
│
├── services/            ← business logic, the layer you write the most
│   ├── auth_service.py / survey_service.py / audit_service.py
│   ├── m1_regulation_service.py    ← regulation CRUD, verify, archive/restore, duplicate, audit
│   ├── m2_service.py               ← questions_for_sme, recompute_knowledge_score, get_latest_score
│   ├── m2_scoring.py               ← auto-scorer (mcq_single/multi/numeric/ordered_steps/open) — pure logic, no DB
│   ├── m2_linkage_rules.py         ← 3 awareness→M2 rules (VAT threshold, VAT rate, official channel boost)
│   ├── m3_service.py               ← submit_compliance_history, submit_behavioural, get_risk_signals
│   ├── survey_question_service.py  ← question fetch, branching engine, code generation
│   ├── survey_session_service.py   ← session creation, cap enforcement, answer recording
│   └── survey_limits_service.py    ← singleton read/write with ProgrammingError resilience
│
├── scripts/
│   └── seed_dev.py / seed_awareness_questions.py / seed_m23_questions.py / seed_regulations.py
│
└── tests/
    ├── conftest.py      ← Postgres testcontainer + ASGI client fixtures
    ├── unit/
    └── integration/
```

Why this split → [`docs/BUILD_PLAN/BUILD_02_Folder_Structure.md`](../../infra/BUILD_PLAN/BUILD_02_Folder_Structure.md) §2.

---

## 3. Add a new endpoint — the canonical 5 steps

Worked example: `GET /api/v1/sectors` returning the distinct sectors of all SMEs (admin-only).

### Step 1 — Schema

If you need a request DTO too, add it here. For a list endpoint we only need the response.

```python
# FILE: backend/app/schemas/sector.py
from pydantic import BaseModel

class SectorOut(BaseModel):
    name: str
    sme_count: int
```

### Step 2 — Service (business logic)

Services own SQL, transactions, and validation. Routers never touch the ORM directly.

```python
# FILE: backend/app/services/sector_service.py
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sme_profile import SMEProfile


async def list_sectors(db: AsyncSession) -> list[dict]:
    rows = (
        await db.execute(
            select(SMEProfile.sector, func.count().label("n"))
            .where(SMEProfile.sector.is_not(None))
            .group_by(SMEProfile.sector)
            .order_by(func.count().desc())
        )
    ).all()
    return [{"name": s, "sme_count": int(n)} for s, n in rows]
```

### Step 3 — Router

Routers parse, authorize, call the service. That's it.

```python
# FILE: backend/app/api/v1/sectors.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_admin
from app.models.user import User
from app.schemas.sector import SectorOut
from app.services import sector_service

router = APIRouter()


@router.get("", response_model=list[SectorOut])
async def list_sectors(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[SectorOut]:
    return [SectorOut.model_validate(r) for r in await sector_service.list_sectors(db)]
```

### Step 4 — Register the router

```python
# FILE: backend/app/api/v1/router.py
from app.api.v1 import auth, qa, regulations, risk, sectors, surveys, users, verify
#                                                  ^^^^^^^

api_router.include_router(sectors.router, prefix="/sectors", tags=["admin"])
```

### Step 5 — Test

```python
# FILE: backend/app/tests/integration/test_sectors.py
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_admin_lists_sectors(client: AsyncClient) -> None:
    # Use the existing register/login pattern from test_survey_flow.py
    ...
```

The `client` fixture is defined in [`backend/app/tests/conftest.py`](../../backend/app/tests/conftest.py) and gives you a fresh ASGI app wired to a disposable Postgres testcontainer.

Restart `make dev-backend` (autoreload picks up the new files), then `curl -H "Authorization: Bearer <admin_token>" http://localhost:8000/api/v1/sectors`.

---

## 4. Conventions

| Concern | Rule |
|---------|------|
| Path | `/api/v1/<kebab-case-plural>` for resources. Singular only for an action endpoint (`/auth/login`, `/verify/claim`). |
| Method | GET list / GET item / POST create / PATCH partial-update / DELETE. Avoid PUT unless you mean full replacement. |
| Status | 200 for read, 201 for create, 204 for delete-without-body. Never invent 4xx/5xx codes; raise a `DomainError` subclass instead. |
| Column | `snake_case`, plural table, singular FK column (`sme_id`, not `smes_id`). |
| Schema | `XxxIn` for request, `XxxOut` for response, `XxxRow` for DB-row mirrors. `from_attributes = True` on every Out schema that wraps an ORM row. |
| Service | One file per resource. Pure async functions taking `db: AsyncSession` first. Never instantiate the engine directly inside one. |
| Transactions | One transaction per request — `db.commit()` once at the end of the service function. The `get_db()` dependency makes this safe. |
| Logging | `from app.logging_config import log` then `log.info("event_name", key=value)`. Never `print()`. |
| Errors | Raise `NotFoundError`, `UnauthorizedError`, `ForbiddenError`, `ValidationError`, or `RateLimitedError` from [`app/exceptions.py`](../../backend/app/exceptions.py). They're auto-mapped to JSON responses. |
| Tests | Integration tests own request/response shape. Unit tests own pure helpers (e.g. `core/security.py`). |

---

## 5. Reusable dependencies

| Dep | Returns | Use when |
|-----|---------|----------|
| `get_db` | `AsyncSession` | Anywhere you need DB access. |
| `get_current_user` | `User` | Endpoint requires *any* logged-in user. |
| `require_annotator` | `User` (role ∈ {`annotator`, `admin`}) | Endpoint is annotator-or-admin. |
| `require_admin` | `User` (role = `admin`) | Endpoint is admin-only. |

All four live in [`backend/app/deps.py`](../../backend/app/deps.py). The role-elevation rule (admin implies annotator) is enforced there, not duplicated in callers.

---

## 6. Audit log

Every state-changing action that matters should write a row to `audit_log`. The pattern lives in [`auth_service.py`](../../backend/app/services/auth_service.py):

```python
from sqlalchemy import insert
from app.models.audit_log import AuditLog

await db.execute(
    insert(AuditLog).values(
        event_type="sector.created",          # dotted name
        table_name="sectors",
        record_id=new_sector_id,
        user_name=user.email,
        event_data_json={"name": new_sector.name},
    )
)
```

Today, only auth events emit audit rows. Wider coverage is part of [`BUILD_13_Admin_and_Annotation.md`](../../frontend/BUILD_PLAN/BUILD_13_Admin_and_Annotation.md).

---

## 7. Rate limiting

Inbound (per-user / per-IP) HTTP-rate limiting uses `slowapi`. Apply it as a decorator on the router function and add a `request: Request` parameter so the decorator can inspect it:

```python
from fastapi import Request
from app.core.rate_limit import limiter

@router.post("/expensive")
@limiter.limit("5/minute")
async def expensive(request: Request, ...): ...
```

Outbound rate-limiting (scrapers being polite to upstream hosts) is a different concern that lives in [`BUILD_12_Data_Ingestion_and_Scheduling.md`](../BUILD_PLAN/BUILD_12_Data_Ingestion_and_Scheduling.md).

---

## 8. Settings

Add a new setting by editing [`backend/app/settings.py`](../../backend/app/settings.py):

```python
class Settings(BaseSettings):
    ...
    NEW_FEATURE_FLAG: bool = False     # default if not in .env
```

Then update [`.env.example`](../../.env.example) with the same key + a comment explaining what it controls. **Never read `os.environ` outside `settings.py`** — it bypasses Pydantic validation and the `lru_cache` that `get_settings()` relies on.

---

## 9. Common pitfalls

- **`sqlalchemy.exc.MissingGreenlet`** — you called a sync ORM method (`relationship.something`) from an async path. Either use `selectinload`/`joinedload` in the query or `await db.refresh(obj, [field])`.
- **`PendingRollbackError`** — a previous query in the same session raised; `await db.rollback()` before the next query, or move the failing branch into its own service function with its own session scope.
- **JWT decoded but role is wrong** — you minted the token before changing the user's role. Force the user to re-login (their old token is still valid until expiry; revocation is not implemented in MVP).
- **A migration shows `op.alter_column` that you didn't expect** — Alembic detected a metadata diff. Inspect carefully; sometimes a `default` change in the model produces a migration that touches every row. See [`06_Database_and_Migrations.md`](06_Database_and_Migrations.md).

---

**Prev:** [`03_Architecture.md`](03_Architecture.md) &nbsp;·&nbsp; **Next:** [`05_Frontend_Development.md`](05_Frontend_Development.md)
