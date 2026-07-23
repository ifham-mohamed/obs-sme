# Module 1 — Phase 4 (Schedulers, Alerts, Lag Tracking): Complete Analysis

> Single-file analysis of **Phase 4 — Schedulers, alerts, lag tracking (BUILD_12)** *only*: scope, technologies, what is actually built vs. unexercised across watchers → propagation events → alerts → lag views, the full data journey, and the approaches missed. Grounded in the live codebase (`app/m1/tasks/{portal_watcher,rss_watcher,alert_dispatch,analytics}.py`, `app/m1/services/{propagation_*,secondary_sources,sources_catalogue,alert_*,drift}.py`, `app/m1/models/{propagation_event,alert,source}.py`, migrations `202606300004_m1_lag_views` + `202607210006_m1_sources_and_sms_contact`, `app/m1/api/{alerts,admin_pipeline}.py`, `app/alerts/`) and the vault (`16_M1_Development_Roadmap.md §Phase 4`, `FEATURES.md` F-232/F-235/F-236).
>
> Generated 2026-07-18; **gap-closure status refreshed 2026-07-21 (Session 71)**. **Honest status: Phase 4 is *fully coded, wired, and Beat-scheduled*.** As of Session 71 the two code-addressable structural gaps (4a source registry, 4b SMS leg) are closed; what remains is *exercising it with production data*, which is gated on the upstream classifier (Phase 3) being trained and on an autonomous run populating propagation events / lag views / alerts at scale.

---

## 0. The one-paragraph truth

All three Phase-4 subsystems exist as **real, registered code**: the portal + RSS watchers run every 2 h on Celery Beat and write `m1_propagation_events`; `alert_dispatch` creates idempotent sector-matched `m1_alerts` and sends **email and SMS** in batches of 50 through a genuine SendGrid/Twilio httpx client (graceful `skipped` without keys); the nightly `analytics` task refreshes two materialized lag views and runs a KL-divergence drift check that can auto-trigger retraining. The SME-facing `/alerts` feed (public + logged-in) is built. **Session 71 closed the two structural gaps:** (1) the watchers now read the **DB-backed `m1_sources` registry seeded to 15 sources** (with per-source health + admin API), not a static 4-source catalogue; (2) **SMS is now wired into the dispatch loop** — the real root cause was a *missing phone column*, now added (`sme_profiles.phone` + `alert_sms_opt_in`) with a dedicated SI/TA-safe SMS body. What is **still** not true: nothing has run autonomously against live portals with a *working classifier* (Phase 3 inert), so `m1_propagation_events` / the lag views / real alert sends are effectively empty; and the runtime DoDs (1 h p99 for ≥ 500 SMEs, drift-fires-on-synthetic, matching precision ≥ 0.90) are **coded but not yet measured** (runbooks in the gap-closure plan).

---

## 1. What Phase 4 is (scope + goal)

**Goal (roadmap):** the pipeline runs autonomously on cron; alerts dispatch within 24 h; lag data accumulates in `m1_propagation_events`.

| Step | Deliverable | Real status |
|---|---|---|
| **4a** | Portal + RSS watchers; every 2 h scan 15 sources → `m1_propagation_events` with match_method/confidence | ✅ watchers coded + Beat-scheduled; **`m1_sources` table seeded to 15 + per-source health + admin API (Session 71)** |
| **4b** | Alert dispatch (SendGrid + Twilio, batched, idempotent on `(regulation_id, sme_id, channel)`) | ✅ email **and SMS** paths real + idempotent (Session 71); ⏳ ≥500-SME/1 h-p99 fan-out not yet load-tested |
| **4c** | Nightly REFRESH of lag views + KL-divergence drift | 🟢 coded + Beat 21:00; 🟡 **unrun with real data** (views empty until watchers + classifier populate) |

---

## 2. Technologies used in Phase 4

### Used
| Technology | Layer | Phase-4 role |
|---|---|---|
| **Celery + Redis + Beat** | Queue | `portal-watcher-every-2h`, `rss-watcher-every-2h`, `lag-analytics-nightly` (21:00 UTC), + retraining hook |
| **httpx** | Integration | portal HTML fetch **and** SendGrid/Twilio REST calls |
| **feedparser** | Integration | news RSS parsing (`rss_watcher`); dead-feed `bozo` now treated as a source failure (Session 71) |
| **SendGrid + Twilio** | Alerts | `alert_providers.send_email` / `send_sms` (real REST, graceful skip); SMS leg now dispatched |
| **PostgreSQL** | Storage | materialized views `v_m1_regulation_lag_summary`, `v_m1_channel_effectiveness` (unique-indexed for concurrent refresh); **`m1_sources` registry (Session 71)** |
| **scikit-learn / scipy (custom)** | ML/Stats | KL-divergence confidence-drift (`services/drift.py`: `histogram` + `kl_divergence`) |
| **Next.js 14 + shadcn** | Frontend | `/alerts` public + SME feed |

### Not exercised
No new ML. The alert *content* uses the classifier's `change_category`/`affected_sectors`, so Phase 4's usefulness is gated on Phase 3 producing real predictions. Autonomous production run + load test are the missing "technologies-in-anger."

---

## 3. Step-by-step: planned vs. built (with code files)

### 4a — Portal + RSS watchers (✅ registry closed Session 71)
`app/m1/tasks/portal_watcher.py` — httpx-fetch each portal → `_blocks()` strip/split HTML → match active regulations → `record_items` → `m1_propagation_events` (first mention only; per-source errors non-fatal). `app/m1/tasks/rss_watcher.py` — `feedparser` parse each feed → match title+summary → propagation event with `first_seen_at`. Matching: `app/m1/services/propagation_matching.py` (`normalize`, `extract_gazette_numbers`, `match(...)` → `match_method` + `match_confidence`).
**Source registry (Session 71):** the watchers now call `secondary_sources.load_sources(session, kind=...)`, which reads the new **`m1_sources` table** (`app/m1/models/source.py`, migration `202607210006`) — `source_id` PK (never renamed: it's the FK written to `m1_propagation_events.source_id`), `name`, `kind ∈ {portal,rss}`, `url`, `active`, plus operability columns `last_checked_at`/`last_ok_at`/`consecutive_failures`/`last_error`. **Seeded to 15** (the 9 prior + BOI, CBSL, Customs, Labour, SLSI, Consumer Affairs). Each pass calls `mark_source_result(...)` (never raises); the RSS watcher now explicitly treats `feedparser`'s empty-`entries`+`bozo` as a *failure* (a permanently-dead feed previously looked identical to "no news"). The static tuple survives only as a fallback when the table is missing/empty. Admin API: `GET/PUT/PATCH /admin/m1/pipeline/sources` (audited). `m1_propagation_events` model: `match_method`, `match_confidence`, `channel`, `first_seen_at`, `UniqueConstraint(regulation_id, source_id)`.

### 4b — Alert dispatch (✅ SMS closed Session 71)
`app/m1/tasks/alert_dispatch.py` (`dispatch_regulation_alerts`) — for a regulation, create sector-matched alerts **idempotently**, then send `pending` alerts in batches of 50 (best-effort). **Session 71 added the SMS leg**, mirroring the email loop exactly (same `_BATCH=50`, same `sent|failed|skipped` semantics, missing Twilio key ⇒ `skipped`); the task result now reports `sms_pending`/`sms_sent`. `app/m1/services/alert_providers.py` — real `send_email` (SendGrid) + `send_sms` (Twilio) over httpx. `alert_content.build_alert` gained a dedicated **`sms` body** (≤300 chars, category/gazette/effective-date first): **not a length quibble — Sinhala/Tamil force UCS-2 at 70 chars/segment**, so reusing the ≤1000-char email body would have silently sent expensive multi-part messages to exactly the trilingual SMEs the module targets.
**Root-cause note:** the gap read as "the email loop forgot to call `send_sms`", but the real blocker was **no phone number anywhere in the schema**. Migration `202607210006` adds `sme_profiles.phone` (E.164) + `alert_sms_opt_in` (defaults FALSE — SMS costs money and unsolicited SMS is a compliance issue; opt-in also keeps the `(regulation_id, sme_id, 'sms')` idempotency key meaningful). Alert creation (`alert_service.py`) makes an `sms` row only for SMEs with `alert_sms_opt_in AND phone`. Model `m1_alerts`: one row per `(regulation × recipient × channel)`, `sme_id=NULL` = public broadcast, `UniqueConstraint(regulation_id, sme_id, channel)`, `channel ∈ {in_app,email,sms}`, `status ∈ {pending,sent,failed,skipped,read}`.
**Remaining:** the ≥ 500-SME / 1 h-p99 fan-out DoD is not load-tested (📋 protocol in the plan); WhatsApp (cited as the 72 %-primary SME channel) is still not a channel — recommendation is to document it as a limitation now.

### 4c — Nightly analytics + drift (🟢 code, 🟡 unrun)
`app/m1/tasks/analytics.py` (`refresh_lag_analytics`) — `REFRESH MATERIALIZED VIEW` for both views, then KL-divergence drift on classifier confidence (recent window vs baseline; `_DRIFT_THRESHOLD=0.15`); above threshold → log + `run_retraining.delay(trigger="drift")` (Phase-5c hook). `app/m1/services/drift.py` — `histogram` + `kl_divergence`. Migration `202606300004_m1_lag_views` creates `v_m1_regulation_lag_summary` (`portal_lag_days`, `news_lag_days` = event time − `gazette_published_date`) and `v_m1_channel_effectiveness` (`median_lag_days` per source/channel), both unique-indexed. Beat: nightly 21:00 UTC. The drift half stays dormant until Phase 3 ships a model (`classifier_confidence` NULL everywhere → the `len(baseline) ≥ 20` guard no-ops by design).

### SME-facing feed (built)
`app/m1/api/alerts.py`: `GET /m1/alerts/public` (no auth, in-app feed for anyone), `GET /m1/alerts` (logged-in SME's sector matches + public), `POST /{alert_id}/read`. Frontend `app/alerts/page.tsx`. The richer deadline/alert-history UI (`14_M1_8`) is deferred to BUILD_13.

---

## 4. How it was developed (stages)

- **Phase 4a/4b/4c** authored together with the DB scaffolding: `202606300002_m1_propagation_events`, `202606300003_m1_alerts`, `202606300004_m1_lag_views`; tasks registered in `celery_config.py` `include` + `beat_schedule` (2 h watchers, 21:00 analytics).
- **F-232** — alert dispatch; **F-235** — lag materialized views; **F-236** — nightly analytics + drift (tracker marks these 🟡 "compiles + registered; live run pending migration + propagation/classified data").
- `/alerts` public + SME feed shipped as the in-app channel.
- **S71 (2026-07-21) — gap closure**: `m1_sources` registry + per-source health + admin API (4a); `sme_profiles.phone`/`alert_sms_opt_in` + SMS dispatch leg + SI/TA-safe SMS body (4b), migration `202607210006`; runbooks for the load test, lag-view activation, retry/DLQ, and matching-precision audit. See [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/21_PHASE4_GAP_CLOSURE_PLAN]].

---

## 5. Verification present today

- Unit/task-level: watchers, dispatch, and analytics compile and are registered (`celery inspect registered` shows their names); providers return `skipped` without keys; idempotency enforced by DB constraints.
- Session-71 checks (deferred to user): `alembic upgrade head` → `GET /admin/m1/pipeline/sources` returns 15; trigger both watchers → `last_ok_at` set on reachable sources, `consecutive_failures` rising on the rest (then park/fix bad URLs); SMS smoke with/without Twilio creds → `sms` row `sent`/`skipped`, no duplicate on re-run, body ≤300 chars and readable in SI/TA.
- **Absent:** an autonomous multi-day run writing real `m1_propagation_events`; a populated pair of lag views; a real batched email/SMS send to a live SME base; drift firing on a synthetic-drift fixture; the 1 h-p99 fan-out measurement; the matching-precision audit.

---

## 6. Gaps & missed approaches (the analytical part)

1. **The 15-source `m1_sources` registry doesn't exist.** Watchers read a static 4-source catalogue; the admin-editable source table (and 11 of the 15 secondary sources) is unbuilt. → ✅ **Closed (Session 71):** `m1_sources` table (`202607210006`) seeded to **15** (9 prior + BOI/CBSL/Customs/Labour/SLSI/CAA); DB-backed `load_sources()` with static fallback; per-source health columns recorded each pass (incl. the RSS `bozo` dead-feed case); audited admin API `GET/PUT/PATCH /admin/m1/pipeline/sources`. **URLs are best-known defaults — confirm each before trusting its lag numbers.**
2. **SMS is coded but not dispatched.** `send_sms` works, but `dispatch_regulation_alerts` only iterated email. → ✅ **Closed (Session 71):** root cause was a **missing phone column**, not a missing call — `sme_profiles.phone` + `alert_sms_opt_in` added, opt-in-gated `sms` rows, SI/TA-safe ≤300-char body, batched SMS leg. WhatsApp (72 %-primary SME channel) remains not-a-channel — 📋 decide/document (recommendation: thesis-limitation now, Twilio WhatsApp Business only for a real deployment).
3. **Phase 4 usefulness is gated on Phase 3.** Alert content and lag views key off `change_category`/`affected_sectors`/`confidence`; with the classifier inert, alerts fire (if at all) only on heuristic-seeded rows and the lag views stay empty. → 📋 not a Phase-4 defect; **when validating Phase 4, filter alert-triggering rows by `classification_source`** (Session 70) so the regex seed isn't mistaken for pipeline behaviour.
4. **Lag views + drift are unrun** — no rows until watchers populate `m1_propagation_events` over time; KL-drift never fired on real/synthetic data. → 📋 activation sequence in the plan: URL triage → matching-precision gate → `gazette_published_date` coverage → refresh; drift stays dormant until a model exists (≥2 windows before acting).
5. **No delivery guarantees / retry-DLQ for alerts.** A `failed` status is recorded but nothing retries it — risky for the "within 24 h" SLA. → 📋 planned: `attempts`/`last_attempt_at` + hourly `retry_failed_alerts` (1 h/4 h/12 h spacing inside the SLA) + `dead` status as the DLQ; `skipped` (config state) stays outside it.
6. **Fan-out not load-tested.** The ≥ 500-SME / 1 h-p99 DoD has no benchmark. → 📋 protocol names the likely bottleneck (two `_exists` SELECTs per SME per channel in a Python loop → replace with bulk `INSERT … ON CONFLICT DO NOTHING` once measured; bounded `asyncio.gather` if sending dominates).
7. **Matching precision unmeasured.** `propagation_matching.match` writes `match_confidence` but nothing has validated it — false matches date "awareness" early and bias the module's headline lag finding *downward*. → 📋 research-validity gate: stratified 30-event hand-audit, precision ≥ 0.90 per method you keep, recorded in the tracker before publishing any lag finding.

Items 3–7 are runbook/data work; the structural build gaps (1, 2) are closed. Once Phase 3 yields live predictions and the source URLs are triaged, Phase 4 can finally *run* and generate the diffusion dataset it exists to measure.

> **Session 71 status (2026-07-21)** — from [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/21_PHASE4_GAP_CLOSURE_PLAN]]:
>
> | Step | Gap | Status |
> |---|---|---|
> | 4a | Static 4/9-source catalogue → 15-source `m1_sources` | ✅ table + seed + DB watchers + health + admin API |
> | 4b | SMS provider exists but never called | ✅ phone column + opt-in + SMS body + dispatch leg |
> | 4b | ≥500-SME / p99 ≤ 1 h fan-out never load-tested | 📋 protocol (bulk upsert / bounded gather) |
> | 4c | Views + drift coded but unrun | 📋 activation sequence (URLs → precision → dates → refresh) |
> | §6.5 | No retry/DLQ for failed alerts | 📋 attempts + `retry_failed_alerts` + `dead` DLQ |
> | §6.7 | Matching precision never audited | 📋 ≥0.90 precision gate before any lag finding |

---

## 7. Traceability (capability → code → doc → F-id)

| Capability | Code path(s) | Doc | F-id |
|---|---|---|---|
| Portal watcher | `app/m1/tasks/portal_watcher.py`, `services/{secondary_sources,propagation_service,propagation_matching}.py` | `03_M1_3_Secondary_Source_Integration` | — |
| RSS watcher | `app/m1/tasks/rss_watcher.py` (feedparser) | `03_M1_3` | — |
| Source registry + health | `app/m1/models/source.py`, `services/secondary_sources.load_sources`, migration `202607210006`, `admin_pipeline.py` | [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/21_PHASE4_GAP_CLOSURE_PLAN]] 4a | S71 |
| Propagation events | `app/m1/models/propagation_event.py`, migration `202606300002` | `02_M1_1_Data_Sources_Catalogue` | — |
| Alert dispatch (email + SMS) | `app/m1/tasks/alert_dispatch.py`, `services/{alert_service,alert_content,alert_providers}.py` | `08_M1 §8.1` | F-232 |
| SMS contact + opt-in | `app/models/sme_profile.py` (`phone`, `alert_sms_opt_in`), migration `202607210006` | [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/21_PHASE4_GAP_CLOSURE_PLAN]] 4b | S71 |
| Alerts model | `app/m1/models/alert.py`, migration `202606300003` | `14_M1_8` | F-232 |
| Lag views | migration `202606300004_m1_lag_views.py` | `12_M1_Monitoring_Maintenance` | F-235 |
| Nightly analytics + drift | `app/m1/tasks/analytics.py`, `services/drift.py` | `12_M1_1_Performance_Monitoring` | F-236 |
| SME alerts feed | `app/m1/api/alerts.py`, `app/alerts/page.tsx` | `14_M1_8` | — |

---

## 8. Data flow — how data travels through the stages (Phase 4)

Three concurrent journeys: **watchers → propagation events** (measuring diffusion), **classified regulation → alerts → SME feed** (dispatch), and **nightly → lag views + drift** (analytics). All three are Beat-driven; the frontend appears only at the SME `/alerts` feed.

### 8.0 Inputs / data sources
| Input | Where it enters | Becomes |
|---|---|---|
| Official portals (HTML) | `portal_watcher` via httpx | `m1_propagation_events` (channel=`portal`) |
| News RSS feeds | `rss_watcher` via feedparser | `m1_propagation_events` (channel=`news`) |
| A `classified` regulation + matched SME sectors | `dispatch_regulation_alerts` | `m1_alerts` rows + email/SMS sends |
| Accumulated propagation events | nightly `analytics` | refreshed lag materialized views |

### 8.1 Diffusion-measurement journey (watchers, every 2 h, no frontend)
```
Celery Beat (every 2h)
  → portal_watcher.run_portal_watcher   |  rss_watcher.run_rss_watcher
      → secondary_sources.load_sources(session, kind='portal'|'rss')   [m1_sources table, 15 rows; static fallback]
      → httpx fetch portal HTML  |  feedparser.parse(feed)
      → _blocks(html) / entry(title+summary)
      → propagation_matching.match(text, gazette_numbers, active_regulations)
            → match_method + match_confidence
      → propagation_service.record_items → INSERT m1_propagation_events        [DB]
            (UniqueConstraint(regulation_id, source_id) → first-mention only, idempotent)
      → mark_source_result(...) → update last_ok_at / consecutive_failures / last_error   [health]
            (RSS: empty entries + bozo ⇒ recorded as a failure, not "no news")
```

### 8.2 Alert-dispatch journey (per regulation → SME feed)
```
(a classified regulation)                                app/m1/tasks/alert_dispatch.py
  → dispatch_regulation_alerts(regulation_id)
      → match SMEs by affected_sectors → create m1_alerts, idempotent
            in_app + email for all matched SMEs
            sms ONLY for SMEs with alert_sms_opt_in AND phone
            UniqueConstraint(regulation_id, sme_id, channel)
      → for pending EMAIL in batches of 50:
            alert_providers.send_email (SendGrid via httpx) → sent|skipped|failed
      → for pending SMS in batches of 50:                              [Session 71]
            alert_content sms body (≤300, SI/TA UCS-2-safe)
            alert_providers.send_sms (Twilio via httpx) → sent|skipped|failed
      → task result reports email + sms pending/sent
  → in-app alert always present (sme_id=NULL rows = public broadcast)
  → SME reads:  GET /m1/alerts/public (no auth)  |  GET /m1/alerts (their sectors + public)
       → frontend app/alerts/page.tsx  →  POST /m1/alerts/{id}/read
```

### 8.3 Nightly analytics journey (21:00 UTC)
```
Celery Beat (21:00)
  → analytics.refresh_lag_analytics                         app/m1/tasks/analytics.py
      → REFRESH MATERIALIZED VIEW v_m1_regulation_lag_summary   (portal_lag_days, news_lag_days
             = propagation first_seen_at − gazette_published_date)
      → REFRESH MATERIALIZED VIEW v_m1_channel_effectiveness    (median_lag_days per source/channel)
      → drift: histogram(recent conf) vs histogram(baseline) → kl_divergence
            if KL > 0.15 → log + run_retraining.delay(trigger='drift')   [Phase 5c hook; dormant until a model exists]
  → (admin lag-analytics UI 14_M1_4 deferred to BUILD_13; data is query-ready)
```

### 8.4 Where each stage lives (quick map)
| Stage | Component | Code |
|---|---|---|
| Scan sources | Celery watchers | `app/m1/tasks/{portal_watcher,rss_watcher}.py` |
| Source registry + health | `m1_sources` + loader | `app/m1/models/source.py`, `services/secondary_sources.py`, `admin_pipeline.py` |
| Match + record | matching + service | `services/{propagation_matching,propagation_service,secondary_sources}.py`, `models/propagation_event.py` |
| Create + send alerts | dispatch + providers | `app/m1/tasks/alert_dispatch.py`, `services/{alert_service,alert_content,alert_providers}.py`, `models/alert.py` |
| Lag + drift | analytics + views | `app/m1/tasks/analytics.py`, `services/drift.py`, migration `202606300004` |
| SME feed | API + page | `app/m1/api/alerts.py`, `app/alerts/page.tsx` |

---

*Scope note: this document covers Phase 4 only. Phase 1 → `PHASE1_FOUNDATION_ANALYSIS.md`; Phase 2 → `PHASE2_INGEST_EXTRACTION_ANALYSIS.md`; Phase 3 → `PHASE3_ANNOTATION_CLASSIFICATION_ANALYSIS.md`; Phase 5 (research findings F1–F6) → `PHASE5_RESEARCH_FINDINGS_ANALYSIS.md`. Phase 4's autonomous machinery is fully coded and scheduled and, as of Session 71, structurally complete (source registry + SMS); it produces its research dataset only once the source URLs are triaged and Phase 3 yields live predictions. Gap-closure companion: `PHASE4_GAP_CLOSURE_PLAN.md`.*
