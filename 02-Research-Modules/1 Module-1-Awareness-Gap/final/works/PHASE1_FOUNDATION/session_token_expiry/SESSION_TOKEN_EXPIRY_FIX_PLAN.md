# Phase 1 · Foundation — Webapp Session/Token Expiry: Fix Plan

> Group: `PHASE1_FOUNDATION / session_token_expiry`. Companion: [[SESSION_TOKEN_EXPIRY_ANALYSIS]].
> **Status: implemented (2026-07-23).** Session standardised to **30 days** end-to-end.

## 1. Backend — `enigmatrix-backend/app/settings.py`

```python
JWT_ACCESS_EXPIRE_MINUTES: int = 43200  # 30 days = 30*24*60  (was 15)
JWT_REFRESH_EXPIRE_DAYS:   int = 30     # (was 90)
```

The access token is now the 30-day session — it is the value the edge middleware and the layout `me()` actually check. `expires_in` returned at login is derived from `JWT_ACCESS_EXPIRE_MINUTES`, so it flows to the frontend automatically. Comment in the file records *why* the access token is long (no server-side refresh) and that revocation still works via cookie-clear + `token_version`.

## 2. Frontend cookies — align every ceiling to 30 days

Both route handlers hardcoded the refresh cookie to 7 days; the establish handler also fell back to a 15-min access cookie. Fixed both:

- **`app/api/auth/establish/route.ts`** — `const THIRTY_DAYS = 30*24*60*60;` access cookie `maxAge` falls back to `THIRTY_DAYS` (still prefers the backend `expires_in`, now 30 days); refresh cookie `maxAge: THIRTY_DAYS`.
- **`app/api/auth/refresh/route.ts`** — same `THIRTY_DAYS` for both the rotated access and refresh cookies.

Now no layer expires before 30 days: access token (30d), refresh token (30d), access cookie (30d), refresh cookie (30d), middleware `exp` gate (passes for 30d).

## 3. Middleware — left as-is (correct under the new lifetime)

`middleware.ts` still redirects to `/login` on an expired/garbled access token with a 30-second skew. With a 30-day access token this only fires at genuine end-of-session (or a tampered cookie), which is the desired behaviour — so no change was needed. The redirect path still clears cookies, so a clean re-login happens at day 30.

## 4. Security tradeoff (recorded, accepted)

A 30-day access token cannot be *silently* revoked before expiry the way a 15-min one can. Mitigations that remain in force:
- **Logout / logout-all** clear the `access` + `refresh` cookies immediately (browser can no longer send them).
- **`token_version`** is validated by `/me`; bumping it (logout-all, password reset) rejects the access token on its next `me()` call.
- HttpOnly + SameSite=Lax + Secure(prod) cookies unchanged.

This is an acceptable posture for the current single-tenant research deployment; if stricter revocation is later required, the correct upgrade is an **edge/server refresh exchange** (middleware or layout swaps a valid refresh cookie for a fresh short access token) rather than shortening the access token again — noted as a follow-up.

## 5. Verification (deferred to user — sandbox VHDX still down)

1. Backend: `python -m compileall app/settings.py`; confirm `/auth/login` response `expires_in == 2592000`.
2. Frontend: `pnpm typecheck && pnpm lint`.
3. Log in, note the `access`/`refresh` cookie `Expires` ≈ now + 30 days in devtools. Wait past 15 min, navigate to a protected page → **no** redirect to `/login` (previously failed here).
4. Logout → cookies cleared, protected route redirects. Logout-all from another device → `me()` rejects on next use.
