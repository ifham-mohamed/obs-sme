# BUILD 03 — Backend API (FastAPI)

> **Goal:** a runnable FastAPI app with health check, settings, structured logging, error handling, dependency injection, and the skeleton for v1 routers — all four modules consume this same framework.

---

## 1. Why FastAPI (One-Line Recap)

Type-safe via Pydantic, async-friendly, auto-generates OpenAPI docs, same language as ML code. Justification details: see research file `04_Technology_Stack_Justification.md` §6.

---

## 2. Initialize the Backend Project

```bash
# RUN
cd backend
uv init --package app
uv venv
source .venv/bin/activate
uv add fastapi[standard] uvicorn[standard] pydantic pydantic-settings
uv add sqlalchemy[asyncio] asyncpg alembic
uv add passlib[bcrypt] python-jose[cryptography]
uv add httpx tenacity python-multipart
uv add structlog
uv add --dev pytest pytest-asyncio pytest-cov ruff httpx
```

(If you don't want `uv`, replace with `pip install` + `requirements.txt`.)

### `backend/pyproject.toml` (essentials)

```toml
[project]
name = "enigmatrix-backend"
version = "0.1.0"
requires-python = ">=3.11,<3.13"

[tool.ruff]
line-length = 100
target-version = "py311"
[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "N", "S", "C4", "SIM", "ARG"]
ignore = ["S101"]   # allow asserts in tests

[tool.pytest.ini_options]
testpaths = ["app/tests"]
asyncio_mode = "auto"
```

---

## 3. Settings — Single Source of Config

```python
# FILE: backend/app/settings.py
from functools import lru_cache
from pydantic import PostgresDsn, AnyHttpUrl     # Pydantic v2 — pin pydantic>=2.5,<3
from pydantic_settings import BaseSettings, SettingsConfigDict   # pin pydantic-settings>=2.2,<3

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    APP_SECRET_KEY: str
    JWT_SECRET: str
    JWT_ACCESS_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    # MUST use the asyncpg driver, e.g. postgresql+asyncpg://user:pass@host:5432/db
    DATABASE_URL: PostgresDsn
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    EMBEDDING_MODEL: str = "intfloat/multilingual-e5-base"   # consumed by BUILD_08 RAG ingestion

    STORAGE_BACKEND: str = "local"
    STORAGE_LOCAL_PATH: str = "./storage"

    HUGGINGFACE_TOKEN: str | None = None
    SENTRY_DSN: str | None = None

    CORS_ORIGINS: list[AnyHttpUrl] = ["http://localhost:3000"]

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

> **Rule:** never read `os.environ` outside this file. All config flows through `get_settings()`.

---

## 4. Structured Logging

```python
# FILE: backend/app/logging_config.py
import logging
import structlog

def setup_logging(env: str = "development") -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
    ]
    if env == "production":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )

log = structlog.get_logger()
```

Usage everywhere: `from app.logging_config import log; log.info("event_name", key=value)`.

---

## 5. Custom Exceptions + Handlers

```python
# FILE: backend/app/exceptions.py
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from app.logging_config import log

class DomainError(Exception):
    status_code = 400
    code = "domain_error"
    def __init__(self, message: str, **extra):
        self.message, self.extra = message, extra

class NotFoundError(DomainError):
    status_code = 404; code = "not_found"

class UnauthorizedError(DomainError):
    status_code = 401; code = "unauthorized"

class ValidationError(DomainError):
    status_code = 422; code = "validation_error"

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError):
        log.warning("domain_error", code=exc.code, message=exc.message, **exc.extra)
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, **exc.extra},
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("unhandled_error", path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"code": "internal_error", "message": "Something went wrong"},
        )
```

---

## 6. Dependency Wiring

```python
# FILE: backend/app/deps.py
from typing import AsyncIterator
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import SessionLocal
from app.exceptions import UnauthorizedError
from app.core.security import decode_token
from app.models.user import User
from sqlalchemy import select

async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session

async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    user = (await db.execute(select(User).where(User.id == payload["sub"]))).scalar_one_or_none()
    if not user:
        raise UnauthorizedError("User not found")
    return user

async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise UnauthorizedError("Admin role required")
    return user
```

---

## 7. App Factory + Mount

```python
# FILE: backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.settings import get_settings
from app.logging_config import setup_logging, log
from app.exceptions import register_exception_handlers
from app.api.v1.router import api_router as v1_router
from app.api.health import router as health_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    setup_logging(s.APP_ENV)
    log.info("backend_starting", env=s.APP_ENV)
    # warm caches, ping DB, load tiny defaults here
    yield
    log.info("backend_stopping")

def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="Enigmatrix API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(o) for o in s.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(v1_router, prefix="/api/v1")
    return app

app = create_app()
```

---

## 8. v1 Router Aggregator

```python
# FILE: backend/app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1 import auth, users, regulations, qa, risk, verify, surveys, admin

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(regulations.router, prefix="/regulations", tags=["module1"])
api_router.include_router(qa.router, prefix="/qa", tags=["module2"])
api_router.include_router(risk.router, prefix="/risk", tags=["module3"])
api_router.include_router(verify.router, prefix="/verify", tags=["module4"])
api_router.include_router(surveys.router, prefix="/surveys", tags=["surveys"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
```

---

## 9. Health Endpoint

```python
# FILE: backend/app/api/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.deps import get_db

router = APIRouter()

@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "service": "enigmatrix-api"}
```

---

## 10. Pattern: A Resource Router

Use this as the template for every module's router.

```python
# FILE: backend/app/api/v1/regulations.py
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_db, get_current_user
from app.schemas.regulation import RegulationOut, RegulationListOut
from app.services.module1 import classifier  # noqa: F401 (warm-loaded at import)
from app.services import regulation_service

router = APIRouter()

@router.get("", response_model=RegulationListOut)
async def list_regulations(
    db: Annotated[AsyncSession, Depends(get_db)],
    user = Depends(get_current_user),
    category: str | None = None,
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    q: str | None = None,
    page: int = 1, size: int = 20,
):
    return await regulation_service.list_regulations(
        db, category=category, from_date=from_date, to_date=to_date, q=q,
        page=page, size=size,
    )

@router.get("/{regulation_id}", response_model=RegulationOut)
async def get_regulation(regulation_id: UUID, db: AsyncSession = Depends(get_db),
                         user = Depends(get_current_user)):
    return await regulation_service.get_regulation(db, regulation_id)
```

> **Convention:** routers are *thin*. They parse, authorize, call a service. No SQL or model-loading code in routers.

---

## 11. Pattern: A Service Module

```python
# FILE: backend/app/services/regulation_service.py
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.regulation import Regulation
from app.exceptions import NotFoundError

async def get_regulation(db: AsyncSession, regulation_id: UUID) -> Regulation:
    obj = (await db.execute(
        select(Regulation).where(Regulation.regulation_id == regulation_id)
    )).scalar_one_or_none()
    if not obj:
        raise NotFoundError("Regulation not found", regulation_id=str(regulation_id))
    return obj

async def list_regulations(db: AsyncSession, *, category, from_date, to_date, q, page, size):
    stmt = select(Regulation)
    if category:
        stmt = stmt.where(Regulation.predicted_category == category)
    if from_date:
        stmt = stmt.where(Regulation.gazette_date >= from_date)
    if to_date:
        stmt = stmt.where(Regulation.gazette_date <= to_date)
    if q:
        stmt = stmt.where(Regulation.cleaned_text.ilike(f"%{q}%"))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    items = (await db.execute(
        stmt.order_by(Regulation.gazette_date.desc()).offset((page-1)*size).limit(size)
    )).scalars().all()
    return {"items": items, "page": page, "size": size, "total": total}
```

---

## 12. Pattern: A Pydantic Schema

```python
# FILE: backend/app/schemas/regulation.py
from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, Field

class RegulationOut(BaseModel):
    regulation_id: UUID
    gazette_number: str
    gazette_date: date
    title: str | None = None
    issuing_agency: str | None = None
    predicted_category: str | None = None
    confidence: float | None = None
    summary_en: str | None = None
    summary_si: str | None = None
    summary_ta: str | None = None
    effective_date: date | None = None
    source_url: str
    created_at: datetime
    class Config: from_attributes = True

class RegulationListOut(BaseModel):
    items: list[RegulationOut]
    page: int = Field(ge=1)
    size: int = Field(ge=1, le=200)
    total: int = Field(ge=0)
```

---

## 13. Module-Level Endpoint Inventory (the contract)

| Method | Path | Purpose | Module |
|--------|------|---------|--------|
| POST | `/api/v1/auth/register` | Create user + SME profile | core |
| POST | `/api/v1/auth/login` | Email + password → tokens | core |
| POST | `/api/v1/auth/refresh` | Refresh access token | core |
| GET  | `/api/v1/users/me` | Current user + profile | core |
| GET  | `/api/v1/regulations` | List/filter regulations | M1 |
| GET  | `/api/v1/regulations/{id}` | Get one regulation | M1 |
| GET  | `/api/v1/regulations/{id}/translations/{lang}` | Localized summary | M1 |
| POST | `/api/v1/qa/ask` | RAG QA with citations | M2 |
| GET  | `/api/v1/risk/me` | Risk score for current SME | M3 |
| GET  | `/api/v1/risk/me/explanations` | SHAP attributions | M3 |
| POST | `/api/v1/verify/claim` | Verify a claim, return verdict | M4 |
| POST | `/api/v1/surveys/{instrument}/submit` | Save responses | core |
| GET  | `/api/v1/admin/datasets/module/{n}` | Admin: examples by status | core |
| POST | `/api/v1/admin/datasets/module/{n}/mark-trained` | Admin: flip flag | core |
| GET  | `/api/v1/admin/training/runs` | Admin: list training runs | core |
| POST | `/api/v1/admin/models/{id}/promote` | Admin: set production | core |

This is the **inter-module data contract** referenced in the proposal — lock it by end of week 3.

---

## 14. Run Locally

```bash
# RUN — backend only, against a Postgres in Docker
docker compose -f docker-compose.dev.yml up -d postgres chromadb
cd backend
uv run uvicorn app.main:app --reload --port 8000
# → open http://localhost:8000/docs
```

---

## 15. Acceptance Criteria

- [ ] `GET /health` returns `{"status":"ok"}` and ALSO confirms DB connectivity
- [ ] `/docs` renders the OpenAPI UI with all routers visible
- [ ] Logs emit JSON in production mode and pretty console in dev
- [ ] An invalid JWT returns `401` with a `{"code":"unauthorized"}` body
- [ ] An unhandled error returns `500` with a `{"code":"internal_error"}` body and a logged stack trace
- [ ] All endpoints in §13 exist (returning 501 stubs is fine for now)

---

## 16. Claude Prompts for This Section

### Prompt 1 — Generate the FastAPI skeleton

```
You are scaffolding a FastAPI backend for the Enigmatrix platform.
Generate these files exactly, matching the conventions in BUILD_03:

- backend/app/settings.py
- backend/app/logging_config.py
- backend/app/exceptions.py
- backend/app/deps.py
- backend/app/main.py
- backend/app/api/health.py
- backend/app/api/v1/router.py
- backend/app/api/v1/auth.py        (501 stubs)
- backend/app/api/v1/users.py       (501 stubs)
- backend/app/api/v1/regulations.py (working list+get against models)
- backend/app/api/v1/qa.py          (501 stubs)
- backend/app/api/v1/risk.py        (501 stubs)
- backend/app/api/v1/verify.py      (501 stubs)
- backend/app/api/v1/surveys.py     (501 stubs)
- backend/app/api/v1/admin.py       (501 stubs)

Use async SQLAlchemy with AsyncSession.
Output as fenced blocks with `# FILE: <path>` headers. No prose outside code blocks.
```

### Prompt 2 — Add structured request logging

```
Add a FastAPI middleware to backend/app/main.py that emits a structured log
for every request: method, path, status_code, duration_ms, user_id (if auth'd),
and a generated request_id (uuid4) propagated via contextvars so all downstream
log calls in the same request include it.
Output the patched main.py and any new helper file.
```

### Prompt 3 — Write a service test

```
Write pytest-asyncio tests for app.services.regulation_service.list_regulations
covering: empty DB, filtering by category, pagination boundaries, and case-insensitive
text search. Use a sqlite-in-memory fixture (or Postgres testcontainer).
Place the file at backend/app/tests/unit/test_regulation_service.py.
```

---

**Prev:** `BUILD_02_Folder_Structure.md` &nbsp;·&nbsp; **Next:** `BUILD_04_Database_and_Storage.md`
