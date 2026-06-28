# 11_M1_1 — API Authentication & Authorization

> Companion to [11_M1_API_Reference.md](11_M1_API_Reference.md) — JWT payload structure, role-permission matrix, token expiry/refresh, error codes with examples + request-id propagation.
> **Implementation status:** 🟡 Partial — auth is shipped (JWT + role checks via FastAPI deps); endpoint coverage matches the admin-CRUD slice. Full matrix lights up with BUILD_07.

## Purpose

Parent doc §1 has the role list + the role-permission matrix added in §1.1. This companion is the operational deep-dive: the JWT payload contract, refresh-token flow, request-id propagation, and the full error-code table with example responses.

## Detailed process

### Step 1 — JWT payload structure

```json
{
  "sub": "user_alpha",
  "role": "admin",
  "scope": ["m1:read", "m1:write", "m1:admin"],
  "iat": 1715680800,
  "exp": 1715684400,
  "jti": "tok_01J2Z3K4P5Q6R7S8T9V0W1X2Y3"
}
```

- `sub` — user UUID.
- `role` — one of `admin | expert | sme | (none — public token)`.
- `scope` — explicit endpoint groups; allows revoking write access without changing the role.
- `iat` / `exp` — issued-at / expiry; access tokens valid 60 minutes.
- `jti` — JWT ID; allows revocation by token-ID (logout, security incident).

### Step 2 — Refresh token flow

```
[Login] POST /api/v1/auth/login (email + password)
   → Response: {access_token (60 min), refresh_token (30 days)}

[Use access] GET /api/v1/m1/regulations
   → 200 OK if token valid + scope matches

[Token expired] GET /api/v1/m1/regulations
   → 401 {code: "TOKEN_EXPIRED"}

[Refresh] POST /api/v1/auth/refresh (refresh_token in body)
   → Response: {access_token (new 60 min), refresh_token (rotated)}

[Logout] POST /api/v1/auth/logout
   → Server adds the access token's `jti` to a Redis blacklist (until exp);
     refresh token deleted from `user_refresh_tokens` table
```

### Step 3 — Role enforcement

```python
# backend/app/api/v1/m1_regulations.py
from app.dependencies import require_role

@router.post("/regulations/{id}/verify", dependencies=[Depends(require_role("admin", "expert"))])
async def verify_regulation(id: UUID, ...): ...

@router.delete("/regulations/{id}", dependencies=[Depends(require_role("admin"))])
async def deactivate_regulation(id: UUID, ...): ...
```

`require_role` is a FastAPI dependency that:

1. Parses the JWT.
2. Checks the JWT signature + `exp`.
3. Checks `jti` not in revocation blacklist.
4. Checks `role` is in the allowed list.
5. Checks `scope` covers the endpoint.

### Step 4 — Permission-failure example

A `sme`-token user attempts an admin endpoint:

```
POST /api/v1/m1/regulations/{id}/verify
Authorization: Bearer <sme_token>

Response: 403 Forbidden
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Role 'sme' lacks required scope 'm1:admin' for this endpoint",
    "request_id": "req_01J3...",
    "timestamp": "2026-05-14T03:17:42Z",
    "details": {
      "required_role": ["admin", "expert"],
      "required_scope": "m1:admin",
      "actual_role": "sme"
    }
  }
}
```

### Step 5 — Request-id propagation

Every request gets a `request_id` from middleware:

```python
# backend/app/middleware/request_id.py
@app.middleware("http")
async def add_request_id(request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req_{ulid.new()}"
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

The same `request_id` flows into:
- Every backend log line (`logger.bind(request_id=request.state.request_id)`).
- Every audit-log row (`audit_log.request_id`).
- Every error response body (`error.request_id`).
- Every Celery task spawned (`X-Request-ID` header propagated to broker).

Client-side support flow: if the user reports an error, support staff use the `request_id` to find the exact backend log entry without searching by timestamp + endpoint.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| JWT (chosen) | Stateless verification, scales horizontally | ✅ Industry standard for SPA + API | Switch to opaque tokens + Redis backend if logout latency becomes problematic. |
| 60-minute access token | Balance of security + UX | ✅ Short enough to limit theft window; long enough to avoid refresh churn | If users complain about constant refreshes, raise to 4 h. |
| Refresh-token rotation | Detects refresh-token theft | ✅ Each refresh issues a new refresh-token; old one invalidated | If we add `refresh_token_family` tracking, can detect theft retrospectively. |
| Role + scope | Fine-grained without proliferating roles | ✅ 4 roles × scope = ~100 effective permissions without 100 roles | If the matrix grows beyond 200 entries — consider RBAC library. |
| ULID for request_id | Sortable, URL-safe | ✅ Better than UUID for log correlation | Never. |

## Worked example

A full login-to-protected-call flow:

```
[POST /api/v1/auth/login]
  body: {email: "admin@enigmatrix.lk", password: "..."}
  response 200: {access_token: "eyJhbGc...", refresh_token: "ref_...", expires_in: 3600}

[GET /api/v1/m1/regulations]
  header: Authorization: Bearer eyJhbGc...
  header: X-Request-ID: req_01J3K4P5
  middleware logs: 'request_id=req_01J3K4P5 user_id=admin@enigmatrix.lk role=admin'
  Pydantic validates query params (page, page_size, etc.)
  service returns paginated list
  response 200: [paginated regulations]
  response header: X-Request-ID: req_01J3K4P5

[Hour later — token expired]
GET /api/v1/m1/regulations
  Response 401: {code: "TOKEN_EXPIRED", request_id: req_01J3M..., ...}

[POST /api/v1/auth/refresh]
  body: {refresh_token: "ref_..."}
  response 200: {access_token: "eyJhbGc...new", refresh_token: "ref_new", expires_in: 3600}
```

## Failure modes & edge cases

- **Stolen access token.** Mitigated by 60-minute TTL + revocation blacklist on logout.
- **Stolen refresh token.** Rotation detects theft on next legitimate refresh (old refresh-token has already been used → reject + force re-login of the legitimate user).
- **JWT signature mismatch.** Server rotated its signing secret; old tokens invalidated. Caught at signature-verify; returns 401 `INVALID_TOKEN`.
- **Clock skew between client and server.** If client clock is > 60 s ahead, the token's `iat` is in the future → server rejects. Mitigated by accepting 120 s clock skew on `iat` verification.
- **Concurrent refresh-token use.** Two browser tabs both refresh simultaneously. Mitigation: rotation marks the *family*; the second refresh sees its parent already used → soft-fails with a "retry with current token" hint.

## Validation & acceptance criteria

- **Token signature verifiable** with the public key in `auth/jwks.json`.
- **Logout revokes** — second request with the same token returns 401.
- **Request-ID present** in every log line + every error response.
- **Per-endpoint role check** — CI test calls every M1 endpoint with each role; asserts the expected 200/403/401.

## Cross-references

- Parent: [11_M1_API_Reference.md](11_M1_API_Reference.md) §1, §1.1, §1.2
- Related: Session-14 audit middleware (already shipped — `backend/app/middleware/audit_middleware.py`)
- BUILD phase: BUILD_07 §auth (already mostly shipped)
- Code: `backend/app/dependencies.py` (require_role), `backend/app/middleware/request_id.py`, `backend/app/api/v1/auth.py`
