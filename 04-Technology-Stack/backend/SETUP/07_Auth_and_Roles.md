# 07 — Auth & Roles

> **Goal:** understand what each role can do, how the JWT-and-cookie machinery works, and how to elevate a dev user.
>
> **Reference:** [`backend/app/core/security.py`](../../backend/app/core/security.py), [`backend/app/services/auth_service.py`](../../backend/app/services/auth_service.py), [`frontend/lib/auth/session.ts`](../../frontend/lib/auth/session.ts), [`frontend/app/api/auth/`](../../frontend/app/api/auth/), and [`docs/BUILD_PLAN/BUILD_06_Auth_and_Users.md`](../BUILD_PLAN/BUILD_06_Auth_and_Users.md) for the underlying spec.

---

## 1. Three roles, one rule

| Role | Can register? | Can submit a survey? | Can view their own data? | Can list any user / response? |
|------|--------------|----------------------|-------------------------|------------------------------|
| `sme` | ✅ (via `/register`) | ✅ | ✅ (`/dashboard`, `/me`) | ❌ |
| `annotator` | ❌ (created by an admin, e.g. via `seed_dev.py`) | ✅ | ✅ | ❌ today; future: see [`BUILD_13`](../../frontend/BUILD_PLAN/BUILD_13_Admin_and_Annotation.md) |
| `admin` | ❌ (same) | ✅ | ✅ | ✅ |

**Hierarchy rule** — admin implies annotator. Both `require_admin` and `require_annotator` deps respect this. Source: [`backend/app/deps.py`](../../backend/app/deps.py).

```python
async def require_annotator(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("admin", "annotator"):
        raise ForbiddenError("Annotator role required")
    return user
```

The frontend mirrors this in [`frontend/lib/auth/roles.ts`](../../frontend/lib/auth/roles.ts) via `hasAtLeast(role, required)`.

---

## 2. Endpoint-by-endpoint matrix

| Method + path | Required role | Source |
|---------------|---------------|--------|
| `POST /api/v1/auth/register` | unauth (rate-limited 10/min) | [`api/v1/auth.py`](../../backend/app/api/v1/auth.py) |
| `POST /api/v1/auth/login` | unauth (rate-limited 5/min) | same |
| `POST /api/v1/auth/refresh` | unauth, requires valid refresh JWT (30/min) | same |
| `GET /api/v1/users/me` | any authenticated | [`api/v1/users.py`](../../backend/app/api/v1/users.py) |
| `GET /api/v1/users` | admin | same — list every user with profile |
| `POST /api/v1/users` | admin | same — admin-driven create (role-pickable, audit-logged as `user.admin_create`) |
| `PATCH /api/v1/users/{id}` | admin | F-96 — admin update (role + preferred_language + profile fields). Refuses to demote the last active admin. Audit `user.admin_update`. |
| `POST /api/v1/users/{id}/activate` | admin | F-96 — flips `is_active=true`. Audit `user.activate`. |
| `POST /api/v1/users/{id}/deactivate` | admin | F-96 — flips `is_active=false`. Refuses to deactivate the last active admin. Audit `user.deactivate`. |
| `POST /api/v1/users/{id}/reset-password` | admin | F-96 — body `{ new_password }`; ≥ 8 chars enforced. Audit `user.password_reset` (the password is never logged). |
| `DELETE /api/v1/users/{id}` | admin | F-96 — soft-delete via `is_active=false`; same last-admin guard. Distinct audit event `user.delete`. |
| `POST /api/v1/surveys/{instrument}/submit` | any authenticated | [`api/v1/surveys.py`](../../backend/app/api/v1/surveys.py) |
| `GET /api/v1/surveys/{instrument}/responses` | admin | same |
| `GET /api/v1/survey-flow/start` | sme | [`api/v1/survey_flow.py`](../../backend/app/api/v1/survey_flow.py) — returns the first unanswered `FlowQuestion` + progress |
| `POST /api/v1/survey-flow/answer` | sme | same — persists one answer, returns next `FlowState` |
| `GET /api/v1/m1/regulations` | admin | [`api/v1/m1_regulations.py`](../../backend/app/api/v1/m1_regulations.py) — list with filters |
| `POST /api/v1/m1/regulations` | admin | same — create regulation |
| `GET /api/v1/m1/regulations/{id}` | admin | same — full `RegulationAdminOut` |
| `PATCH /api/v1/m1/regulations/{id}` | admin | same — partial update |
| `POST /api/v1/m1/regulations/{id}/verify` | admin | same — flips `expert_verified` + sets `expert_verified_by` / `expert_verified_at` |
| `POST /api/v1/m1/regulations/bulk-verify` | admin | F-97 — body `{ regulation_ids: UUID[], verified_by }`. Atomic + idempotent (already-verified rows are no-ops); returns `{ verified: <count> }`. Audit `m1_regulation.bulk_verified`. |
| `DELETE /api/v1/m1/regulations/{id}` | admin | F-97 — soft-archive (flips `is_active=false`). Audit `m1_regulation.archived`. |
| `POST /api/v1/m1/regulations/{id}/restore` | admin | F-97 — flips `is_active=true`. Audit `m1_regulation.restored`. |
| `POST /api/v1/m1/regulations/{id}/duplicate` | admin | F-97 — clones the row with a fresh UUID + `_COPY_<hex>` suffix; copies M2M sectors; resets `expert_verified=false`. Audit `m1_regulation.duplicated`. |
| `GET /api/v1/m1/regulations/{id}/public` | sme | same — `RegulationPublicOut` subset (title, summary, effective_date, penalty, real-world example). 404s archived rows. |
| `POST /api/v1/survey-sessions/start` | any authenticated | [`api/v1/survey_sessions.py`](../../backend/app/api/v1/survey_sessions.py) — creates session row; enforces `survey_limits` cap |
| `GET /api/v1/survey-sessions/my-history` | any authenticated (own sessions only) | same — paginated session list for current user |
| `GET /api/v1/survey-sessions/{id}` | owner or admin | same — session detail |
| `GET /api/v1/survey-sessions/{id}/next-question` | owner or admin | same — next unanswered question in session |
| `POST /api/v1/survey-sessions/{id}/answer` | owner or admin | same — record answer, advance session |
| `POST /api/v1/survey-sessions/{id}/complete` | owner or admin | same — mark session completed |
| `GET /api/v1/admin/survey-questions` | admin | [`api/v1/admin_survey_questions.py`](../../backend/app/api/v1/admin_survey_questions.py) — list with filters |
| `POST /api/v1/admin/survey-questions` | admin | same — create question |
| `PATCH /api/v1/admin/survey-questions/{code}` | admin | same — update question |
| `DELETE /api/v1/admin/survey-questions/{code}` | admin | same — archive question |
| `POST /api/v1/admin/survey-questions/bulk-verify` | admin | same — bulk ground-truth verify |
| `GET /api/v1/admin/survey-limits` | admin | [`api/v1/admin_survey_limits.py`](../../backend/app/api/v1/admin_survey_limits.py) — read singleton |
| `PATCH /api/v1/admin/survey-limits` | admin | same — update per-role caps |
| `GET /api/v1/admin/activity-log` | admin | [`api/v1/admin_audit.py`](../../backend/app/api/v1/admin_audit.py) — paginated audit log |
| `GET /api/v1/m2/questions/for-sector/{sector_code}` | any authenticated | [`api/v1/m2.py`](../../backend/app/api/v1/m2.py) — universal + sector-specific M2 questions |
| `GET /api/v1/m2/sme/{sme_id}/knowledge_score` | sme (own) or admin | same — cached knowledge score with domain breakdown |
| `POST /api/v1/m3/compliance-history` | sme | [`api/v1/m3.py`](../../backend/app/api/v1/m3.py) — submit compliance history snapshot |
| `POST /api/v1/m3/behavioural` | sme | same — submit behavioural signals snapshot |
| `GET /api/v1/m3/sme/{sme_id}/risk-signals` | sme (own) or admin | same — combined M2 score + latest M3 snapshots |
| `GET /api/v1/dashboard/pending-regulations` | any authenticated | [`api/v1/dashboard.py`](../../backend/app/api/v1/dashboard.py) — sector-relevant active regulations not yet assessed by the SME |
| `GET /api/v1/admin/translations` | admin | [`api/v1/admin_translations.py`](../../backend/app/api/v1/admin_translations.py) — union of untranslated questions + regulations |
| `PATCH /api/v1/admin/translations/{kind}/{id}` | admin | same — patch SI/TA fields; auto-marks translated |
| `POST /api/v1/admin/translations/bulk-mark-translated` | admin | same — mark N questions translated in one call |
| `GET /api/v1/regulations`, `/api/v1/qa/ask`, `/api/v1/verify/claim` | (501 stubs — BUILD_07/08/10) | the 501-stub routers for deferred ML features |

The `/admin/*` route group on the frontend is gated at the layout level by `requireRole("admin")` in [`frontend/app/(admin)/layout.tsx`](../../frontend/app/(admin)/layout.tsx). The backend doesn't trust the frontend; every admin endpoint also has `Depends(require_admin)`.

---

## 3. JWT lifecycle

```
   POST /api/v1/auth/login (email + password)
        │
        ▼  bcrypt verify, audit log row, then:
   {
     access_token:  HS256(JWT) — 15 min, claims { sub, role, kind: "access" }
     refresh_token: HS256(JWT) —  7 d,   claims { sub,        kind: "refresh" }
     token_type: "bearer", expires_in: 900
   }
```

Settings → [`backend/app/settings.py`](../../backend/app/settings.py) (`JWT_ACCESS_EXPIRE_MINUTES`, `JWT_REFRESH_EXPIRE_DAYS`, `JWT_SECRET`).
Helpers → [`backend/app/core/security.py`](../../backend/app/core/security.py).

### Token kind enforcement

Every token carries a `kind` claim. `decode_token(token, expected_kind="access")` rejects a token of the wrong kind with `UnauthorizedError`. So a refresh token can never be used as an access token even if the caller sends it in `Authorization: Bearer …`.

### Refresh rotation

`POST /auth/refresh` returns a *new* refresh token alongside the new access token. The previous refresh token is **not invalidated** in MVP (no allowlist or denylist) — it stays valid until expiry. A revocation list ships with [`BUILD_14`](../../infra/BUILD_PLAN/BUILD_14_Deployment_Cloud.md) when Redis is in play.

### What the JWT does NOT contain

- No email, no permissions array, no expiry timezone tags. The role is included; everything else is fetched via `GET /users/me`.
- No CSRF token. Cookies are HTTP-only + SameSite=Lax, which prevents the most common CSRF; same-origin requests use the cookie automatically.

---

## 4. Cookie strategy

Tokens live in **HTTP-only cookies** in the browser. The backend never sets cookies directly — it returns tokens in the JSON body, and a thin Next.js route handler writes the cookies:

```
   Browser POST /api/auth/establish  { access_token, refresh_token, expires_in }
        │
        ▼  Next.js route handler
   Set-Cookie: access  HttpOnly; SameSite=Lax; Path=/; Max-Age=900
   Set-Cookie: refresh HttpOnly; SameSite=Lax; Path=/; Max-Age=604800
```

Source → [`frontend/app/api/auth/establish/route.ts`](../../frontend/app/api/auth/establish/route.ts).
Logout clears both cookies via [`frontend/app/api/auth/logout/route.ts`](../../frontend/app/api/auth/logout/route.ts).
Server components read the access cookie via [`frontend/lib/auth/session.ts`](../../frontend/lib/auth/session.ts) and pass it to `AuthApi.me()`.

`secure: false` in dev (HTTP localhost), `secure: true` in production (HTTPS). The flag is auto-set from `process.env.NODE_ENV`.

---

## 5. Inbound rate limit

[`backend/app/core/rate_limit.py`](../../backend/app/core/rate_limit.py) installs `slowapi` middleware keyed on remote address. The current limits:

| Endpoint | Limit |
|----------|-------|
| `POST /auth/register` | 10/minute |
| `POST /auth/login` | 5/minute |
| `POST /auth/refresh` | 30/minute |
| (default fallback) | 100/minute |

A 6th login attempt within a minute returns 429. To raise/lower, edit the `@limiter.limit("5/minute")` decorator in [`api/v1/auth.py`](../../backend/app/api/v1/auth.py).

Outbound rate limiting (scrapers) is a different concern — see [`BUILD_12_Data_Ingestion_and_Scheduling.md`](../BUILD_PLAN/BUILD_12_Data_Ingestion_and_Scheduling.md).

---

## 6. Audit-log subsystem

### 6.1 One write path

Every data-mutating action across the app writes an `audit_log` row through a **single helper** — [`audit_service.record(db, *, event_type, actor, table_name=None, record_id=None, record_key=None, data=None)`](../../backend/app/services/audit_service.py) (Session 14). The write joins the caller's transaction (no separate commit), so an audit row only persists if the mutation did. `actor` may be a `User` (its `.email` is stored as `user_name`) or a bare email string (system / pre-auth callers like `auth.login.failure`). `auth_service._audit(...)` is kept as a thin shim over `record(...)` so its eleven call-sites stay terse.

`record_key` (added in `202605140001`, indexed) carries the natural key for string-keyed entities — `survey_questions.question_code` — so the Activity Log can be filtered by question code without a UUID. `record_id` stays UUID-only (`users`, `m1_regulations`, …).

### 6.2 Event registry

| `event_type` | When | `table_name` / `record_*` | `event_data_json` |
|--------------|------|---------------------------|-------------------|
| `auth.register` | Successful registration | `users` / `record_id` | `{}` |
| `auth.login.success` | Valid creds | `users` / `record_id` | `{}` |
| `auth.login.failure` | Wrong creds OR inactive account | `users` / `record_id?` | `{ "email": "...", "reason"?: "inactive" }` |
| `auth.refresh` | Refresh token traded | `users` / `record_id` | `{}` |
| `user.admin_create` | Admin creates a user via `POST /users` (F-94). | `users` / `record_id` | `{ "created_by": "...", "role": "..." }` |
| `user.admin_update` | Admin patches a user via `PATCH /users/{id}` (F-96). | `users` / `record_id` | `{ "updated_by": "...", "fields": [ "role", "profile.sector", … ] }` |
| `user.activate` / `user.deactivate` | `POST /users/{id}/activate` or `/deactivate` (F-96). | `users` / `record_id` | `{ "actor": "..." }` |
| `user.password_reset` | `POST /users/{id}/reset-password` (F-96). The new password is never written. | `users` / `record_id` | `{ "reset_by": "..." }` |
| `user.delete` | `DELETE /users/{id}` (F-96) — soft-delete, distinct from a manual deactivate. | `users` / `record_id` | `{ "actor": "..." }` |
| `m1_regulation.created` | Admin creates an `m1_regulations` row via `POST /m1/regulations`. | `m1_regulations` / `record_id` | `{ "regulation_short_code": "...", "document_type": "..." }` |
| `m1_regulation.updated` | Admin patches a regulation via `PATCH /m1/regulations/{id}`. | `m1_regulations` / `record_id` | `{ "regulation_id": "...", "changed": [...] }` |
| `m1_regulation.verified` | Admin flips `expert_verified` via `POST /m1/regulations/{id}/verify`. | `m1_regulations` / `record_id` | `{ "regulation_id": "...", "verified_by": "..." }` |
| `m1_regulation.bulk_verified` | Admin batch-verify via `POST /m1/regulations/bulk-verify` (F-97). | `m1_regulations` | `{ "verified_by": "...", "count": N, "regulation_ids": [...] }` — *one* row per batch. |
| `m1_regulation.archived` | Admin soft-archive via `DELETE /m1/regulations/{id}` (F-97). | `m1_regulations` / `record_id` | `{ "short_code": "..." }` |
| `m1_regulation.restored` | Admin un-archive via `POST /m1/regulations/{id}/restore` (F-97). | `m1_regulations` / `record_id` | `{ "short_code": "..." }` |
| `m1_regulation.duplicated` | Admin clone via `POST /m1/regulations/{id}/duplicate` (F-97). | `m1_regulations` / `record_id` (the clone) | `{ "source_regulation_id": "...", "source_short_code": "...", "new_short_code": "..." }` |
| `survey_question.created` | Admin creates a `survey_questions` row (F-100). | `survey_questions` / `record_key` | `{ "question_code": "...", "module_number": 0, "actor": "..." }` |
| `survey_question.updated` | Admin patches via `PATCH /admin/survey-questions/{code}` (F-100). | `survey_questions` / `record_key` | `{ "question_code": "...", "fields_changed": [...], "actor": "..." }` |
| `survey_question.archived` | Admin soft-archive via `DELETE /admin/survey-questions/{code}` (F-100). | `survey_questions` / `record_key` | `{ "question_code": "...", "actor": "..." }` |
| `survey_question.restored` | Admin un-archive via `POST …/{code}/restore` (F-100). | `survey_questions` / `record_key` | `{ "question_code": "...", "actor": "..." }` |
| `survey_question.duplicated` | Admin clone via `POST …/{code}/duplicate` (F-100). | `survey_questions` / `record_key` (the clone) | `{ "source_code": "...", "new_code": "...", "actor": "..." }` |
| `survey_question.verified` | Admin verifies via `POST …/{code}/verify` (F-100). | `survey_questions` / `record_key` | `{ "question_code": "...", "verified_by": "...", "actor": "..." }` |
| `survey_question.bulk_verified` | Admin batch-verify via `POST …/bulk-verify` (F-100) — *one* row per batch. | `survey_questions` | `{ "verified_by": "...", "count": N, "question_codes": [...], "actor": "..." }` |
| `survey_question.linked_to_regulation` | Admin links a question to a regulation via the M:N endpoints (F-107/F-113). | `survey_questions` / `record_key` | `{ "question_code": "...", "regulation_id": "...", "actor": "..." }` |
| `survey_question.unlinked_from_regulation` | Admin unlinks (F-107/F-113). | `survey_questions` / `record_key` | `{ "question_code": "...", "regulation_id": "...", "actor": "..." }` |
| `survey_question.primary_regulation_changed` | Admin re-points the cached primary regulation (F-107). | `survey_questions` / `record_key` | `{ "question_code": "...", "regulation_id": "...", "actor": "..." }` |
| `translation.completed` | Admin patches SI/TA on a question or regulation, or bulk-marks questions translated, via `/admin/translations/*` (F-109). | `survey_questions` (`record_key`) or `m1_regulations` (`record_id`); none on bulk | single: `{ "fields_changed": [...] }`; bulk: `{ "bulk": true, "count": N }` |
| `survey.submitted` | An SME submits a survey batch via `survey_service.submit` (Session 14). *One* row per submit — the M2 score recompute and M3 snapshot projection are deterministic side-effects of the same submit, flagged here rather than as their own rows. | `survey_responses` (no `record_id`) | `{ "instrument": "knowledge", "answered_count": 31, "regulation_ids": ["…"] \| null, "m2_scored": true, "m3_snapshots_projected": false }` |

### 6.3 Reading the trail

Admins read the trail at **`/admin/activity-log`** (server-rendered, behind `require_admin`) — filters by event type / table / actor email / record / date range, newest-first, colour-coded event badges + type-specific detail rendering. Backed by `GET /api/v1/admin/activity-log` (paginated, same filters) and `GET /api/v1/admin/activity-log/event-types` (distinct types for the filter dropdowns). The regulation- and question-edit pages carry a "Created by … · Last edited by …" line that deep-links into that record's slice (`?record_id=` / `?record_key=`).

Or straight SQL:

```sql
SELECT occurred_at, event_type, user_name, record_key, event_data_json
FROM audit_log ORDER BY occurred_at DESC LIMIT 50;
```

### 6.4 Authorship columns

`AuthorshipMixin` (`backend/app/db/mixins.py`) adds `created_by` / `updated_by` — denormalised acting-user email strings, **not** FKs (they survive user deletion, matching the existing `user_name` / `*_verified_by` convention) — to `m1_regulations`, `survey_questions`, `survey_question_regulations`, `users`, `sme_profiles`. The service layer stamps them on every create / update / verify / archive / restore / link / translation-patch — *including soft-deletes* (`is_active=false` is an update, so `updated_by` is set). Static lookups (`regulatory_domains`, `sectors`), the append-only `audit_log`, and the append-only response/score/snapshot tables (which already carry `sme_id`) are intentionally excluded. Surfaced in `RegulationAdminOut`, `SurveyQuestionAdminOut`, `UserOut`. Existing rows keep `NULL` — historical authorship is genuinely unknown; new writes populate going forward.

---

## 7. Elevating a dev user to admin

Three ways, in increasing reusability:

### Option A — direct SQL (fastest)

```bash
PGPASSWORD=devpass psql -h localhost -U enigmatrix -d enigmatrix -c \
  "UPDATE users SET role = 'admin' WHERE email = 'you@example.com';"
```

The user's existing JWT still claims their old role — they have to log out and back in.

### Option B — extend `seed_dev.py`

Add a row to [`backend/app/scripts/seed_dev.py`](../../backend/app/scripts/seed_dev.py) with `role="admin"`. Idempotent: re-running creates the user once, then is a no-op.

### Option C — one-shot CLI script (non-MVP)

A `python -m app.scripts.set_role <email> <role>` helper is a sensible follow-up. It's not in the MVP because direct SQL is fast enough during development.

---

## 8. Frontend RBAC patterns

Two layers, both required:

| Layer | What it does |
|-------|--------------|
| `frontend/middleware.ts` | Fast path: if the `access` cookie is missing on a protected path prefix, redirect to `/login?next=…` *before* the page renders. Never trusts the cookie's contents. |
| `frontend/app/(app)/layout.tsx` and `(admin)/layout.tsx` | Server-side: `await requireUser()` / `await requireRole("admin")`. If the call fails or the role is wrong, redirect. This is the actual security boundary. |

The middleware is an optimisation, not a security check. Don't put role logic in it.

To require a specific role on a single page (instead of the whole route group), call `requireRole("admin")` at the top of the page's server component — it returns the user object, so you can use `user.email` immediately.

---

## 9. Pitfalls and limitations

- **No password reset flow.** A future slice will add `POST /auth/password-reset/request` + `POST /auth/password-reset/confirm`. For now, dev users go through `seed_dev.py` or direct SQL.
- **No email verification.** Anyone can register with any address.
- **No account lockout.** Slowapi rate-limits by IP; brute force per email isn't tracked yet.
- **`confirmPassword` is frontend-only.** The backend `RegisterIn` schema doesn't validate it — the password match is enforced only in the zod schema. (See OQ6 in [`docs/tracker/FEATURES.md`](../../tracker/FEATURES.md).)
- **No revoke-on-logout.** Logout clears the cookies; the JWT itself remains valid until expiry. Acceptable for the MVP; replace with a denylist when Redis lands ([`BUILD_14`](../../infra/BUILD_PLAN/BUILD_14_Deployment_Cloud.md)).

---

**Prev:** [`06_Database_and_Migrations.md`](06_Database_and_Migrations.md) &nbsp;·&nbsp; **Next:** [`08_Testing.md`](08_Testing.md)
