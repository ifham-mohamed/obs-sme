# BUILD 06 — Authentication, Users & RBAC

> **Goal:** secure end-to-end auth (JWT access + refresh, bcrypt password hashing), three roles (`sme`, `admin`, `annotator`), and SME-profile binding so that risk and alerts are personalized.

---

## 1. Auth Model in One Picture

```
[ Browser ]                       [ FastAPI ]                [ Postgres ]
   │  POST /auth/register          │                            │
   │ ────────────────────────────▶│  hash pw → insert User      │
   │                               │ ──────────────────────────▶│
   │ ◀──────────────────  201      │                            │
   │  POST /auth/login             │                            │
   │  email + password             │  verify → issue access+refresh tokens
   │ ────────────────────────────▶│                            │
   │ ◀────  200 { access, refresh }                              │
   │                               │                            │
   │  GET /api/v1/...              │                            │
   │  Authorization: Bearer ...    │  decode → load user        │
   │ ────────────────────────────▶│ ──────────────────────────▶│
   │ ◀────  resource               │                            │
   │                               │                            │
   │  POST /auth/refresh           │  rotate refresh, issue new access
```

- Access token: short-lived (15 min), used for every API call
- Refresh token: long-lived (7 d), HTTP-only cookie OR returned in JSON; rotated on use
- Password hashing: bcrypt (`passlib[bcrypt]`)
- Roles: `sme | admin | annotator` (an `admin` is also implicitly an `annotator`)

---

## 2. Backend — Security Helpers

```python
# FILE: backend/app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.settings import get_settings
from app.exceptions import UnauthorizedError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str: return pwd_context.hash(password)
def verify_password(password: str, hashed: str) -> bool: return pwd_context.verify(password, hashed)

def _encode(payload: dict, expires: timedelta, kind: str) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode({**payload, "iat": now, "exp": now + expires, "kind": kind},
                      s.JWT_SECRET, algorithm="HS256")

def make_access_token(user_id: str, role: str) -> str:
    s = get_settings()
    return _encode({"sub": user_id, "role": role},
                   timedelta(minutes=s.JWT_ACCESS_EXPIRE_MINUTES), "access")

def make_refresh_token(user_id: str) -> str:
    s = get_settings()
    return _encode({"sub": user_id}, timedelta(days=s.JWT_REFRESH_EXPIRE_DAYS), "refresh")

def decode_token(token: str, expected_kind: str = "access") -> dict[str, Any]:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.JWT_SECRET, algorithms=["HS256"])
        if payload.get("kind") != expected_kind:
            raise UnauthorizedError("Invalid token kind")
        return payload
    except JWTError as e:
        raise UnauthorizedError("Invalid or expired token") from e
```

---

## 3. Auth Service

```python
# FILE: backend/app/services/auth_service.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.sme_profile import SMEProfile
from app.core.security import hash_password, verify_password, make_access_token, make_refresh_token
from app.exceptions import UnauthorizedError, ValidationError
from app.schemas.auth import RegisterIn

async def register(db: AsyncSession, payload: RegisterIn) -> User:
    existing = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing:
        raise ValidationError("Email already registered")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="sme",
        preferred_language=payload.preferred_language or "en",
    )
    db.add(user); await db.flush()
    if payload.profile:
        db.add(SMEProfile(user_id=user.id, **payload.profile.model_dump()))
    await db.commit(); await db.refresh(user)
    return user

async def login(db: AsyncSession, email: str, password: str) -> tuple[str, str, User]:
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid credentials")
    if not user.is_active:
        raise UnauthorizedError("Account disabled")
    return make_access_token(str(user.id), user.role), make_refresh_token(str(user.id)), user

async def refresh(db: AsyncSession, refresh_token: str) -> tuple[str, str]:
    from app.core.security import decode_token
    payload = decode_token(refresh_token, expected_kind="refresh")
    user = (await db.execute(select(User).where(User.id == payload["sub"]))).scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedError("Account not found")
    return make_access_token(str(user.id), user.role), make_refresh_token(str(user.id))
```

---

## 4. Auth Schemas

```python
# FILE: backend/app/schemas/auth.py
from typing import Literal
from pydantic import BaseModel, EmailStr, Field

class SMEProfileIn(BaseModel):
    sector: str | None = None
    sub_sector: str | None = None
    employee_count_band: Literal["1-10","11-50","51-200"] | None = None
    annual_turnover_band: str | None = None
    business_age_years: int | None = Field(default=None, ge=0, le=200)
    region: str | None = None
    primary_language: Literal["en","si","ta"] | None = None

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    preferred_language: Literal["en","si","ta"] | None = None
    profile: SMEProfileIn | None = None

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshIn(BaseModel):
    refresh_token: str
```

---

## 5. Auth Router

```python
# FILE: backend/app/api/v1/auth.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_db
from app.schemas.auth import RegisterIn, LoginIn, RefreshIn, TokenPair
from app.services import auth_service
from app.settings import get_settings

router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    user = await auth_service.register(db, payload)
    return {"id": str(user.id), "email": user.email}

@router.post("/login", response_model=TokenPair)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    s = get_settings()
    access, refresh, _user = await auth_service.login(db, payload.email, payload.password)
    return TokenPair(access_token=access, refresh_token=refresh,
                     expires_in=s.JWT_ACCESS_EXPIRE_MINUTES * 60)

@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshIn, db: AsyncSession = Depends(get_db)):
    s = get_settings()
    access, refresh = await auth_service.refresh(db, payload.refresh_token)
    return TokenPair(access_token=access, refresh_token=refresh,
                     expires_in=s.JWT_ACCESS_EXPIRE_MINUTES * 60)
```

---

## 6. Role-Based Access Control

```python
# FILE: backend/app/deps.py  (extension)
from app.exceptions import UnauthorizedError
from app.models.user import User
from fastapi import Depends

def require_roles(*allowed: str):
    async def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise UnauthorizedError(f"Requires role {allowed}")
        return user
    return _checker

# Usage in routers:
# @router.get("/admin/...")
# async def admin_only(user = Depends(require_roles("admin"))): ...
```

Apply consistently:

| Endpoint group | Roles allowed |
|----------------|---------------|
| `/auth/*` | public |
| `/users/me`, `/regulations/*`, `/qa/*`, `/risk/me/*`, `/verify/*`, `/surveys/*` | `sme`, `admin`, `annotator` |
| `/admin/datasets/*`, `/admin/training/*`, `/admin/models/*` | `admin` |
| `/admin/annotation/*` | `admin`, `annotator` |

---

## 7. Frontend — Session Helpers

```ts
// FILE: frontend/lib/auth/session.ts
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { api } from "@/lib/api/client";

export type Session = { userId: string; role: "sme" | "admin" | "annotator"; token: string };

export async function getSession(): Promise<Session | null> {
  const c = cookies();
  const access = c.get("access")?.value;
  const refresh = c.get("refresh")?.value;
  if (!access) return refresh ? await tryRefresh(refresh) : null;
  // (Optional) validate by calling /users/me
  const me = await api.get<{ id: string; role: Session["role"] }>("/api/v1/users/me", access)
    .catch(() => null);
  return me ? { userId: me.id, role: me.role, token: access } : (refresh ? tryRefresh(refresh) : null);
}

async function tryRefresh(refresh: string): Promise<Session | null> {
  try {
    const r = await api.post<{ access_token: string; refresh_token: string }>(
      "/api/v1/auth/refresh", { refresh_token: refresh });
    const c = cookies();
    c.set("access", r.access_token, { httpOnly: true, sameSite: "lax", secure: true, path: "/" });
    c.set("refresh", r.refresh_token, { httpOnly: true, sameSite: "lax", secure: true, path: "/" });
    const me = await api.get<{ id: string; role: Session["role"] }>(
      "/api/v1/users/me", r.access_token);
    return { userId: me.id, role: me.role, token: r.access_token };
  } catch { return null; }
}

export async function requireUser(): Promise<Session> {
  const s = await getSession();
  if (!s) redirect("/login");
  return s;
}
```

```ts
// FILE: frontend/lib/auth/use-session.ts
"use client";
import { useEffect, useState } from "react";
export function useSession() {
  const [token, setToken] = useState<string | null>(null);
  useEffect(() => {
    fetch("/api/auth/token").then(r => r.json()).then(d => setToken(d.access));
  }, []);
  return { token };
}
```

---

## 8. Login & Register Pages

```tsx
// FILE: frontend/app/(auth)/login/page.tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api/client";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  const r = useRouter();
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      const tokens = await api.post<{ access_token: string; refresh_token: string }>(
        "/api/v1/auth/login",
        { email: fd.get("email"), password: fd.get("password") }
      );
      // Pass tokens to a Next API route that sets HTTP-only cookies
      await fetch("/api/auth/establish", { method: "POST", body: JSON.stringify(tokens),
        headers: { "Content-Type": "application/json" } });
      r.push("/dashboard");
    } catch (e: any) { setErr(e.message); }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto mt-24 max-w-sm space-y-4">
      <h1 className="text-xl font-semibold">Sign in</h1>
      <input name="email" type="email" required className="w-full rounded border p-2" placeholder="email" />
      <input name="password" type="password" required className="w-full rounded border p-2" placeholder="password" />
      {err && <p className="text-sm text-danger">{err}</p>}
      <Button>Sign in</Button>
    </form>
  );
}
```

```ts
// FILE: frontend/app/api/auth/establish/route.ts
import { NextResponse } from "next/server";
export async function POST(req: Request) {
  const { access_token, refresh_token } = await req.json();
  const res = NextResponse.json({ ok: true });
  res.cookies.set("access", access_token, { httpOnly: true, sameSite: "lax", secure: true, path: "/" });
  res.cookies.set("refresh", refresh_token, { httpOnly: true, sameSite: "lax", secure: true, path: "/" });
  return res;
}
```

```ts
// FILE: frontend/app/api/auth/token/route.ts
import { NextResponse } from "next/server";
import { cookies } from "next/headers";
export async function GET() {
  const access = cookies().get("access")?.value ?? null;
  return NextResponse.json({ access });
}
```

---

## 9. Rate Limiting + Account Lockout

For a research demo:
- Add `slowapi` middleware: 5 login attempts / minute / IP
- After 10 failed logins for one email in 15 min → temporary lockout (mark `is_active=false` for 15 min, log in `audit_log`)

```python
# FILE: backend/app/core/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

def install_rate_limiter(app):
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, lambda r, e: e.get_response(r))
```

```python
# FILE: backend/app/main.py  — wire it up inside create_app()
from app.core.rate_limit import install_rate_limiter
install_rate_limiter(app)
```

```python
# FILE: backend/app/api/v1/auth.py — apply to login + refresh
from app.core.rate_limit import limiter

@router.post("/login")
@limiter.limit("5/minute")     # IP-level guard against brute force
async def login(request: Request, payload: LoginIn, db: AsyncSession = Depends(get_db)):
    ...
```

> **Production-grade ingest rate limiting** (token-bucket per upstream host, used by scrapers in BUILD_07/10/12) is a **different concern** and lives in `BUILD_12_Data_Ingestion_and_Scheduling.md` §10. The `slowapi`-based limiter above is only for inbound HTTP from end users.

---

## 10. Audit Logging

Every auth event writes to `audit_log`:
- `auth.register` (record_id = user.id)
- `auth.login.success` / `auth.login.failure`
- `auth.refresh`
- `auth.logout` (if you implement it)
- `auth.role_changed`

```python
# Pattern, used in auth_service:
await db.execute(insert(AuditLog).values(
    event_type="auth.login.success",
    table_name="users",
    record_id=user.id,
    user_name=user.email,
    event_data_json={"ip": request.client.host},
))
```

This satisfies the proposal's "every prediction, alert, and survey response is logged" requirement at the auth level.

---

## 11. Acceptance Criteria

- [ ] `POST /api/v1/auth/register` creates user + profile, returns 201
- [ ] `POST /api/v1/auth/login` returns access + refresh tokens
- [ ] `GET /api/v1/users/me` with a valid access token returns the user
- [ ] An expired access token can be exchanged via `/auth/refresh`
- [ ] `/admin/*` endpoints return 401 for SME role and 200 for admin role
- [ ] Frontend `/login` flow lands on `/dashboard` and `/login` redirects authenticated users away
- [ ] Tesseract OCR languages installed: `eng+sin+tam` (verified by `tesseract --list-langs`); pdfplumber and PyMuPDF pinned with `>=` ranges in `pyproject.toml`
- [ ] Auth events appear in `audit_log` with timestamps
- [ ] 6 failed logins in a minute return 429 (rate limit)

---

## 12. Claude Prompts for This Section

### Prompt 1 — Generate auth backend

```
Generate the complete Enigmatrix auth backend exactly as specified in BUILD_06 §2–§6:
- backend/app/core/security.py
- backend/app/services/auth_service.py
- backend/app/schemas/auth.py
- backend/app/api/v1/auth.py
- backend/app/api/v1/users.py (just GET /me)
- a require_roles dependency in backend/app/deps.py

Use SQLAlchemy 2.0 async, Pydantic v2, python-jose for JWT, passlib[bcrypt] for hashing.
Include unit tests at backend/app/tests/unit/test_auth_service.py covering:
- duplicate email rejection
- correct password verification
- refresh token rotation
- expired token rejection.

Output as `# FILE: <path>` blocks. No prose.
```

### Prompt 2 — Generate frontend auth

```
Generate frontend auth for a Next.js 14 (App Router) app:
- frontend/lib/auth/session.ts (per BUILD_06 §7)
- frontend/lib/auth/use-session.ts
- frontend/app/(auth)/login/page.tsx
- frontend/app/(auth)/register/page.tsx (with SMEProfileIn fields)
- frontend/app/api/auth/establish/route.ts
- frontend/app/api/auth/token/route.ts
- frontend/app/api/auth/logout/route.ts (clears cookies)

Use react-hook-form + zod for forms. Tailwind. Show error states. Localize via next-intl.
```

### Prompt 3 — Audit log middleware

```
Add a FastAPI middleware that, after every authenticated request to /api/v1/admin/*,
inserts a row into audit_log with: event_type='admin.access',
table_name='', record_id=None, user_name=user.email,
event_data_json={"path": request.url.path, "method": request.method, "status": response.status_code}.
Output the middleware file and the wiring change in main.py.
```

---

**Prev:** `BUILD_05_Frontend_App.md` &nbsp;·&nbsp; **Next:** `BUILD_07_Module1_Awareness.md`
