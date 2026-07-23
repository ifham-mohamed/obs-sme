# Module 1 — Phase 1 Gap-Closure Plan (Foundation: Auth / Session / Survey)

> Companion to [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/09_PHASE1_FOUNDATION_ANALYSIS]] §6. One entry per foundation-hardening gap. **Session 72 (2026-07-21) implemented the code-addressable auth/session/survey gaps (#2, #5, #6, #10) + tests (#11)**; #1 and #7 were found **already closed in code** (the analysis was stale); #3 (email verification) and #8/#9 are deferred by design. Code lives in `C:\Reasearch\xyz\enigmatrix-backend` (+ `enigmatrix-frontend/middleware.ts`).

## Status summary

| # | Gap (from PHASE1 §6) | Status |
|---|---|---|
| 1 | No refresh-token rotation / server-side revocation / logout-all | ✅ **already in code** — `refresh_tokens` table, rotation + reuse-detection, `logout_all`, `token_version` (analysis was stale) |
| 2 | No self-service password reset | ✅ implemented — token table + forgot/reset endpoints + email stub |
| 3 | No email verification on register | 📋 deferred (needs the same mail infra; plan below) |
| 5 | Weak password policy (`min_length=8` only) | ✅ implemented — complexity + identity-guard + denylist + optional HIBP |
| 6 | Edge JWT check is presence-only | ✅ implemented — middleware now also checks `exp` |
| 7 | Reads not audited | ✅ **already in code** — `audit_service.record_read` on the PII list (SME-PII single-record reads still open) |
| 8 | Regulation summaries hand-entered | 📋 by design (auto-summarize is Phase 4/5) |
| 9 | M1/M3 answers unscored | 📋 by design (descriptive, not right/wrong) |
| 10 | `next_question_rules` untyped — bad rule only caught at runtime | ✅ implemented — structural write-time validator (complements the existing semantic soft-warns) |
| 11 | Auth failure/expiry paths thinly tested | ✅ improved — policy + rule-validator unit tests; fixed a stale `make_refresh_token` test; integration cases specced below |

---

## Gap #5 — Password policy: one rule, every password-setting path ✅ IMPLEMENTED

**Problem.** `RegisterIn.password = Field(min_length=8)` was the *entire* policy. Eight lowercase letters passed; `password` (the literal string) passed; a password equal to the user's email passed. Nothing checked reuse-of-identity or known-breached passwords, and each password-setting path could have drifted its own rule.

**Design — split by what each layer needs.** `app/core/password_policy.py`:

- `check_complexity(password, *, email=None)` — **pure, synchronous**, raises `ValueError` so it drops straight into a Pydantic validator (→ 422 at the schema boundary, before any service runs). Rules: length ≥ `PASSWORD_MIN_LENGTH` (default **10**); at least **3 of 4** character classes (lower/upper/digit/symbol); not in a small common-password denylist; does not contain the email local-part (len ≥ 3).
- `check_breached(password)` — **async**, HaveIBeenPwned **k-anonymity** (only the first 5 chars of the SHA-1 leave the process; the full hash never does), `Add-Padding` on. **Fail-open**: any network error logs and returns `False`, so a HIBP outage can never lock out registration. Opt-in via `PASSWORD_HIBP_CHECK` (default off — no surprise outbound calls in dev/CI).
- `enforce(password, *, email=None)` — service-layer entry: complexity (as `ValidationError`) + optional HIBP.

**Wiring.** Pydantic validators on `RegisterIn` / `AdminCreateUserIn` / `AdminResetPasswordIn` / `ResetPasswordIn` (complexity, + a `model_validator` for the email-vs-password check where both fields exist). Service-layer `enforce(...)` in `register`, `admin_create_user`, `reset_password`, `reset_password_with_token` adds the HIBP layer. **Login is deliberately NOT policy-checked** — existing accounts (incl. the seed admin) must still sign in; the policy only gates *setting* a new password.

**Files.** `app/core/password_policy.py` (new); `app/schemas/auth.py` (validators); `app/services/auth_service.py` (`enforce` calls); `app/settings.py` (`PASSWORD_MIN_LENGTH`, `PASSWORD_HIBP_CHECK`).

**Blast radius (fixed).** Integration tests that registered via the API with `smepass1234` (lower+digit = 2 classes) now correctly fail the policy — updated to `Smepass-1234` in `test_survey_flow.py` / `test_m2_flow.py` / `test_m3_flow.py`. The seed passwords (`admin12345`, …) are created via `hash_password` directly (bypass the schema) and are only ever used to *log in*, so they still work — **but rotate them before any real deployment** (this was the original gap #5 warning).

## Gap #2 — Self-service password reset ✅ IMPLEMENTED

**Problem.** Only `POST /users/{id}/reset-password` (admin-driven) existed. An SME who forgot their password had no path.

**Design — hashed, single-use, time-boxed tokens; no user enumeration; mail-optional.**

- **`password_reset_tokens` table** (`app/models/password_reset_token.py`, migration `202607210007`) — stores only the **SHA-256 hash** of the token (the raw value is emailed, never persisted, so a DB read can't be replayed), plus `expires_at`, `used_at`, `created_at`. Single-use + time-boxed; requesting a new reset invalidates the user's prior unused rows.
- **`request_password_reset(db, email)`** — **no enumeration**: returns `None` and behaves identically whether or not the email maps to an active user; only the side effects (a token row + an email) differ, and neither is observable. Writes a non-identifying `auth.password_reset.requested` audit row either way.
- **`reset_password_with_token(db, token, new_password)`** — validates (exists / unused / unexpired), enforces the password policy, sets the new hash, marks the token used, and **revokes every session** (`_revoke_user_sessions` — shared with the admin reset: revoke all live refresh tokens + bump `token_version`). Invalid/expired/used → 401.
- **Mail is optional** (`app/services/auth_email.py`) — mirrors the Phase-4 `alert_providers` skip pattern exactly: no `SENDGRID_API_KEY` ⇒ **log the reset link and return `skipped`**, so dev/CI drive the whole flow by reading the log; real SendGrid delivery drops in the moment the key is set, zero flow changes.
- **Endpoints** (`app/api/v1/auth.py`, both rate-limited 5/min): `POST /auth/forgot-password` (always 202, identical body), `POST /auth/reset-password` (204 on success). The emailed link is `FRONTEND_BASE_URL/reset-password?token=…`.

**Files.** `app/models/password_reset_token.py` (new), `alembic/versions/202607210007_password_reset_tokens.py` (new), `app/services/auth_email.py` (new), `app/services/auth_service.py` (`request_password_reset`, `reset_password_with_token`, `_hash_reset_token`, `_revoke_user_sessions`), `app/schemas/auth.py` (`ForgotPasswordIn`, `ResetPasswordIn`), `app/api/v1/auth.py` (2 routes), `app/models/__init__.py` (register), `app/settings.py` (`PASSWORD_RESET_TOKEN_TTL_MINUTES`, `FRONTEND_BASE_URL`).

**Frontend follow-up (not built here):** the `/reset-password?token=…` page + a "forgot password?" link on `/login`. The backend contract is complete and testable now.

## Gap #6 — Edge JWT expiry check ✅ IMPLEMENTED

**Problem.** `middleware.ts` checked only cookie *presence*; a present-but-expired (or garbled) `access` cookie slipped through the edge and relied entirely on the server-side layout check.

**Design.** The edge still can't verify the HS256 *signature* (no secret at the edge — that stays authoritative in the layout), but it can now cheaply decode the payload and check `exp`: base64url-decode the middle segment, read `exp`, and if it's missing/unparseable or past (with a 30 s clock-skew allowance to avoid flapping) redirect to `/login?next=…` **and clear the stale `access`/`refresh` cookies** so the browser stops re-sending a dead token. Signature verification remains server-side.

**Files.** `enigmatrix-frontend/middleware.ts`.

## Gap #10 — Structural validation of `next_question_rules` ✅ IMPLEMENTED

**Problem.** Branching rules were persisted as free JSON; a malformed rule (unknown predicate key, empty `when`, missing `goto_question_code`, wrong value type) was only "caught" at runtime by the flow engine silently ignoring it and falling back to linear progression — so a typo stayed invisible until an SME hit it.

**Design — hard structural gate at write time, distinct from the existing semantic soft-warn.** `app/schemas/survey_rules.py` (`validate_rules_structure`) validates each rule against a Pydantic grammar that mirrors `_answer_matches` exactly: each `when` must carry **exactly one** of `answer_eq | answer_in | answer_lt | answer_gt` (unknown keys forbidden), `answer_in` non-empty, `goto_question_code` present and non-empty. Wired into `create_question` / `update_question` right after `_serialise_rules`, so a bad rule set is a **422** before it ever persists. This complements — does not replace — `survey_question_service.validate_branching`, which stays a *semantic* soft-warn (forward-refs / cycles / archived targets) surfaced to the admin UI. Structure = hard error; semantics = advisory. No retroactive breakage: validation only runs when `next_question_rules` is in the create/update payload.

**Files.** `app/schemas/survey_rules.py` (new), `app/services/survey_question_service.py` (two call-sites).

## Gap #11 — Auth tests ✅ IMPROVED

- `app/tests/unit/test_password_policy.py` — complexity floors (length, common, class-count, email-part), short-local-part skip, and the reset-token hash helper (deterministic, hides raw, 64-hex).
- `app/tests/unit/test_survey_rule_validation.py` — well-formed pass; non-list / unknown-key / empty-`when` / two-predicate / missing-goto / empty-goto / empty-`answer_in` all rejected.
- Fixed a **stale** `test_security.py` case that still called `make_refresh_token("user-1")` (the gap #1 rotation work changed the signature to `(user_id, jti, family_id)`); added a jti/family round-trip assertion.

**Still deferred (need DB / testcontainers → user-run, WSL):** expired-access rejection end-to-end, refresh-rotation + reuse-detection family revocation, last-active-admin guard, and a full forgot→reset→login integration test. Specced in the verification section.

---

## Gaps left open by design / deferred

- **#1, #7 — already closed in code** (the analysis was stale). #7's remaining edge: single-record SME-PII reads (not just the list) still have no trail — fold into a read-audit dependency on the sensitive read endpoints when they land.
- **#3 — email verification.** Same mail dependency as #2. Plan: `users.email_verified` (bool) + a `email_verification_tokens` table reusing the exact `auth_email` skip-provider; a soft flag at first (unverified users can log in but see a banner), hardening to gated actions later. Cheap once #2's mail path is real.
- **#8 — hand-entered summaries** (auto-summarize is Phase 4/5). **#9 — M1/M3 unscored** (descriptive by design). Both are correct-as-is; documented so they aren't mistaken for defects.

## Session 72 verification checklist (deferred to user — sandbox lacks Postgres/Redis)

1. `cd enigmatrix-backend && python -m compileall app` (import/syntax).
2. `alembic upgrade head` → `202607210007` applies; `\d password_reset_tokens` shows the hashed-token table.
3. Unit: `uv run pytest app/tests/unit/test_password_policy.py app/tests/unit/test_survey_rule_validation.py app/tests/unit/test_security.py -v`.
4. Policy at the boundary: `POST /auth/register` with `smepass1234` → 422; with `Str0ng-Passw0rd` → 201.
5. Reset flow (no mail creds): `POST /auth/forgot-password` {registered email} → 202; grab the link from the worker/app log (`[password-reset:skipped]`); `POST /auth/reset-password` {token, new strong password} → 204; old sessions rejected (bumped `token_version`); reused token → 401; expired token (wait TTL or edit `expires_at`) → 401. Unregistered email → identical 202, no token row.
6. Rule gate: `PATCH` a survey question with `{"when":{"answer_equals":"y"},"goto_question_code":"Q10"}` → 422; the valid `answer_eq` form → 200.
7. Middleware: hit `/dashboard` with an expired `access` cookie → redirect to `/login` + cookies cleared.
8. Integration (WSL): the updated `test_survey_flow` / `test_m2_flow` / `test_m3_flow` still pass with `Smepass-1234`.
9. `graphify update .`

## Follow-ups

- Frontend: `/reset-password` page + "forgot password?" link (backend ready).
- Rotate the seed passwords before any real deployment (original gap #5 warning).
- Email verification (#3) once the mail provider is real.
- Optional HIBP in prod: set `PASSWORD_HIBP_CHECK=true` (fail-open) once outbound egress is confirmed.
- Read-audit for single-record SME-PII reads (finish #7).
