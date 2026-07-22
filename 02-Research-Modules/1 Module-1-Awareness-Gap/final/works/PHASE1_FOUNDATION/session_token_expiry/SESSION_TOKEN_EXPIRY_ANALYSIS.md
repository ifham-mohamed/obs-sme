# Phase 1 · Foundation — Webapp Session/Token Expiry: Analysis

> Group: `PHASE1_FOUNDATION / session_token_expiry`. Companion: [[SESSION_TOKEN_EXPIRY_FIX_PLAN]].
> **Status: root cause found + fixed (2026-07-23).** Supersedes the earlier "90-day refresh" change, which did not fix the symptom for the reason below.

## 1. Symptom

The webapp logs the user out / "token expired" well inside any reasonable session, even though a previous change set the backend **refresh** token to 90 days. Owner request: make the session **30 days** and stop the mid-session expiry.

## 2. Why the 90-day refresh change didn't help

The session model was designed as *short access token (15 min) + long refresh token, silently rotated*. That only works if **something exchanges the refresh token for a fresh access token** when the access token expires. In this webapp, at full-page-navigation time, **nothing does:**

- **Edge middleware** (`enigmatrix-frontend/middleware.ts`) reads the **access** cookie, decodes its `exp`, and on expiry **redirects to `/login` and deletes both cookies** (`readExp` → `redirectToLogin`). It never looks at the refresh cookie. So 15 min after login, the very next protected navigation nukes the session — including the still-valid 90-day refresh token.
- **Server layout** (`lib/auth/session.ts` → `requireUser` → `AuthApi.me(access_token)`) also has **no refresh path**: if `me()` fails on an expired access token, it `redirect("/login")`.
- The `/api/auth/refresh` route **exists** but is only reachable via a client-side 401 interceptor — never triggered for a hard navigation that the middleware has already bounced.

So the effective session was capped at the **15-minute access-token lifetime**, regardless of the refresh setting. The 90-day refresh token was dead weight.

## 3. Second, compounding bug: refresh cookie hardcoded to 7 days

Both `/api/auth/establish` and `/api/auth/refresh` route handlers set the **refresh** cookie with `maxAge: 7 * 24 * 60 * 60` — a hardcoded **7 days**, independent of the backend's `JWT_REFRESH_EXPIRE_DAYS`. Even if the refresh flow *had* been wired at the edge, the browser would have dropped the refresh cookie after 7 days. Two independent expiry ceilings (15 min access via middleware, 7 day refresh cookie) both sat below any 30/90-day intent.

## 4. Root cause (one sentence)

There is no server-/edge-side token refresh, so the session is gated by the **access token's own lifetime** (15 min) at the middleware and layout — the long refresh token is never consumed on navigation, and the refresh cookie was independently capped at 7 days.

## 5. Chosen fix strategy

Rather than build an edge/server refresh exchange (larger surface, more failure modes for a research build), make the **access token itself** the 30-day session — it is the value that actually gates both the middleware `exp` check and the layout `me()` call — and align every other ceiling (refresh token, both cookie `maxAge`s) to 30 days so nothing expires earlier. Revocation still functions: logout / logout-all clear the cookies immediately, and `token_version` is validated by `/me`, so a bumped version rejects the access token on its next use. Details in the plan.
