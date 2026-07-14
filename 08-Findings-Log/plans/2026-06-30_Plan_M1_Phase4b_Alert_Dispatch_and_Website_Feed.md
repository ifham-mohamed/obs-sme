---
tags: [m1, phase-4, plan, alerts, sendgrid, twilio, in-app, website]
date: 2026-06-30
author: Mohamed M.R.I (215075J) — Module 1 owner
session: 67
status: 🟡 in-execution — backend built + frontend scaffold this session
features: F-232 (alerts model + service + dispatch) · F-233 (SME + public API) · F-234 (website alerts section)
---

# M1 Phase 4b — Alert dispatch (email/SMS) + in-app website alerts section

> **Goal (roadmap Phase 4, Step 4b):** when a regulation is classified/verified as SME-relevant, dispatch **sector-matched** alerts — **in-app** (website), **email** (SendGrid), and **SMS** (Twilio) — idempotent per `(regulation, sme, channel)`, batched, rate-limit-aware.
>
> **Extra requirement (yours):** the alerts also appear as a **separate section on the website**, visible to **logged-in SMEs** (matched to their sector) *and* to **non-logged-in visitors** (a public feed of general alerts).
>
> **Why:** the alert system is Objective-1's deliverable and the **treatment arm** for the DiD effect measurement (Finding F6). The in-app feed is the always-available channel (no email/SMS keys needed to demo).

## Design

**Channels & storage** — one `m1_alerts` row per `(regulation, sme_id, channel)`:
- `channel ∈ {in_app, email, sms}`; `sme_id = NULL` marks a **public/broadcast** in-app alert.
- `status ∈ {pending, sent, failed, skipped, read}`; `sent_at`, `read_at`.
- Unique `(regulation_id, sme_id, channel)` + service-level exists-check → **idempotent** (re-dispatch never double-sends).

**Who gets what**
- **Public in-app alert** (`sme_id=NULL`, `channel=in_app`, `status=sent`) — one per regulation → the **public website feed** (non-logged-in).
- **Sector-matched SMEs** (`sme_profiles.sector == regulation.domain_code`) → per-SME `in_app` (feed) + `email` (SendGrid). *SMS is wired in the provider but not populated until an SME phone field exists — follow-up.*

**Dispatch flow** — `dispatch_regulation_alerts(regulation_id)` Celery task:
1. `create_alerts_for_regulation` → public + per-SME rows (idempotent).
2. Send `pending` email rows in **batches of 50**; provider returns `sent|skipped|failed`; `skipped` when no SendGrid key (dev/CI safe).
Trigger: admin "notify" action or a Beat scan of newly verified SME-relevant regulations (kept explicit for now).

**Website section** — a public route `/alerts`:
- Always shows the **public feed** (`GET /api/v1/m1/alerts/public`, no auth).
- If a session token is present, also shows the SME's **personal sector-matched feed** (`GET /api/v1/m1/alerts`, auth) with unread count + mark-read (`POST /m1/alerts/{id}/read`).
- Route lives **outside** the authed `(app)` group so non-logged-in visitors can reach it (add `/alerts` to `middleware.ts` public routes + a top-nav link).

## Files (this session)
Backend: `app/models/m1_alert.py` · migration `202606300003_m1_alerts.py` · `app/schemas/m1_alert.py` · `app/services/m1_alert_content.py` (pure, tested) · `app/services/m1_alert_providers.py` (SendGrid/Twilio via httpx, graceful) · `app/services/m1_alert_service.py` · `app/tasks/m1/alert_dispatch.py` · `app/api/v1/m1_alerts.py` (+ register in `router.py`) · `app/settings.py` (+SendGrid/Twilio) · `app/celery_config.py` (register task) · `app/tests/unit/test_m1_alert_content.py`.
Frontend (scaffold): `lib/api/m1-alerts.ts` · `app/alerts/page.tsx` · `components/alerts/alerts-feed.tsx`.

## Definition of Done
- Migration `202606300003` creates `m1_alerts` (unique `(regulation_id, sme_id, channel)`).
- Alert content + sector-match helpers unit-tested; providers return `skipped` with no keys.
- `dispatch_regulation_alerts` creates public + sector-matched alerts idempotently and sends pending emails in batches.
- `/api/v1/m1/alerts/public` returns the public feed with no auth; `/m1/alerts` returns the SME feed with auth; mark-read works.
- The `/alerts` page renders the public feed (+ personal feed when logged in).

## How to run (manual test — T-15)
```bash
cd enigmatrix-backend && uv run alembic upgrade head           # 202606300003
uv run pytest app/tests/unit/test_m1_alert_content.py -v
# dispatch for one regulation (dev — no keys needed; email 'skipped', in-app created):
uv run python -c "from app.tasks.m1.alert_dispatch import dispatch_regulation_alerts as d; print(d.apply(args=['<regulation_uuid>']).result)"
curl http://localhost:8000/api/v1/m1/alerts/public         # public feed (no auth)
# frontend: add /alerts to middleware public routes; visit /alerts
```

## Risks / follow-ups
- **SMS**: needs an SME phone field on `sme_profiles` (add + populate) before Twilio delivers.
- **Provider keys**: set `SENDGRID_API_KEY` / `TWILIO_*` in prod; absent = in-app only.
- **Trigger**: currently explicit per-regulation; add a daily Beat scan (verified + SME-relevant + no alerts) as a fast-follow.
- **Frontend** is a scaffold — align `lib/api/client.ts` signature + `middleware.ts` allowlist + add the nav link.

## Cross-refs
Roadmap §Phase 4 · `08_M1_Full_System_Architecture.md §8.1 (alert batching)` · predecessor 4a plan `2026-06-30_Plan_M1_Phase4a_Portal_RSS_Watchers.md`.
