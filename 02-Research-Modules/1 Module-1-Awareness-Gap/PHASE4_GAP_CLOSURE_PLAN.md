# Module 1 — Phase 4 Gap-Closure Plan (Schedulers + Alerts)

> Companion to [[PHASE4_SCHEDULERS_ALERTS_ANALYSIS]]. **Session 71 (2026-07-21) implemented 4a (source registry) and 4b (SMS leg)**; 4c and the load-test DoD get step-by-step runbooks below — they need real data / a staging environment, not code.

## Status

| Step | Gap | Status |
|---|---|---|
| 4a | Static 4/9-source catalogue, not the 15-source `m1_sources` table | ✅ implemented — table, seed to 15, DB-backed watchers, per-source health, admin API |
| 4b | SMS provider exists but never called | ✅ implemented — root cause was a **missing phone column**, not a missing call |
| 4b | ≥500-SME / p99 ≤ 1 h fan-out never load-tested | 📋 protocol below |
| 4c | Views + drift coded but unrun (empty until watchers + classifier populate) | 📋 activation sequence below |

---

## 4a — Source registry ✅ IMPLEMENTED

**Problem.** `secondary_sources.py` was a frozen tuple: 4 portals + 5 RSS. Adding, disabling, or re-pointing a source needed a code deploy, and a source that quietly died (URL moved, portal offline) only produced a log line — so it would contribute nothing to the lag dataset indefinitely without anyone noticing.

**What was built.**

1. **`m1_sources` table** (`app/m1/models/source.py`, migration `202607210006`) — `source_id` PK (deliberately: it's the value written to `m1_propagation_events.source_id`, so renaming would orphan lag history — add a new row instead), `name`, `kind` ∈ {portal, rss} CHECK, `url`, `active`, `notes`, plus operability columns the tuple couldn't carry: `last_checked_at`, `last_ok_at`, `consecutive_failures`, `last_error`.
2. **Seeded to 15** — the 9 existing + 6 new portals (BOI, CBSL, Customs, Labour, SLSI, Consumer Affairs), matching the roadmap's "15 sources". URLs are best-known defaults; **confirm each before trusting its lag numbers** (see verification).
3. **`load_sources(session, kind)`** — DB-backed, with the static tuple as fallback when the table is missing/empty, so a pre-migration or fresh-DB worker still watches something instead of silently scanning zero sources. Both watchers now use it; `iter_sources()` stays as the fallback.
4. **`mark_source_result(...)`** — each watcher pass records ok/failure per source. Never raises (health bookkeeping must not break a watcher); a no-op for static-fallback sources that have no row. **RSS special case:** `feedparser` never raises on a dead feed — it returns empty `entries` with `bozo` set — so the watcher now explicitly treats that as a failure. Previously a permanently-broken feed looked identical to "no news this cycle".
5. **Admin API** (`admin_pipeline.py`): `GET /admin/m1/pipeline/sources` (registry + health), `PUT /sources/{id}` (create/replace), `PATCH /sources/{id}` (usually just flipping `active` to park a broken source) — both audited.

**Verify:** `alembic upgrade head` → `GET /sources` returns 15; run `run_portal_watcher` + `run_rss_watcher` once manually → `last_ok_at` set on reachable sources, `consecutive_failures` rising on the rest; fix or park the bad URLs (that triage pass is the point of the health columns).

**Follow-up:** admin UI table (mirrors the metadata-review pattern); alert when `consecutive_failures ≥ 3` (fold into the Phase-2 quality probe rather than a new job).

## 4b — SMS dispatch ✅ IMPLEMENTED

**Root cause found.** The analysis reads as "the email loop just forgot to call `send_sms`". The actual blocker: **there was no phone number anywhere in the schema** — `sme_profiles` has sector/region/language/consent but no contact number. Wiring the call without a recipient field would have been a no-op.

**What was built.**

1. **`sme_profiles.phone` (E.164) + `alert_sms_opt_in`** (migration `202607210006`), opt-in defaulting FALSE — SMS costs money per message and unsolicited SMS is a compliance problem; explicit opt-in also keeps the `(regulation_id, sme_id, 'sms')` idempotency key meaningful instead of filling the table with permanently-'skipped' rows.
2. **Alert creation** (`alert_service.py`) now creates an `sms` row only for SMEs with `alert_sms_opt_in AND phone`, using the same `_exists` idempotency check as the other channels.
3. **Separate SMS body** (`alert_content.build_alert` → new `sms` key). Not a length quibble: one Twilio segment is 160 GSM-7 chars, and **Sinhala/Tamil force UCS-2 at 70 chars/segment** — reusing the ≤1000-char email body would silently send expensive multi-part messages to exactly the SMEs the trilingual work targets. The SMS rendering leads with category / gazette / effective date and caps at 300.
4. **Dispatch leg** (`alert_dispatch.py`) — mirrors the email loop exactly: same `_BATCH=50`, same best-effort status semantics (`sent|failed|skipped`; missing Twilio key ⇒ `skipped`, never `failed`, so dev/CI stay quiet), commits per batch. Task result now reports `sms_pending`/`sms_sent` and logs both legs.

**Verify:** set `phone` + `alert_sms_opt_in=true` on a test SME → `dispatch_regulation_alerts` → `sms` row created, status `skipped` without Twilio creds / `sent` with them; re-run → no duplicate row (idempotency); confirm the SMS body is ≤300 chars and readable in SI/TA.

**Follow-ups:** expose phone + opt-in in the SME profile UI (required before any real SMS traffic); per-SME quiet hours / daily cap; Twilio delivery-status webhook → flip `sent`→`delivered|undelivered`.

## 4b (second gap) — Fan-out load test (📋 protocol)

DoD: ≥500 SMEs, p99 dispatch ≤ 1 h. Currently untested, and the shape of the code says where it will hurt: `create_alerts_for_regulation` runs **two `_exists` SELECTs per SME per channel** inside a Python loop — 500 SMEs ≈ 1500+ round-trips before a single send.

1. **Seed**: script 500 SME users + profiles across sectors (100 with `alert_sms_opt_in`), in a staging DB with production-like latency.
2. **Measure baseline**: time `dispatch_regulation_alerts` end-to-end; instrument creation vs send separately (they have different bottlenecks).
3. **Expected fix if creation dominates** — replace the per-SME `_exists` loop with one bulk `INSERT … ON CONFLICT (regulation_id, sme_id, channel) DO NOTHING` (the unique constraint already exists, so the DB does the idempotency the loop is emulating). This is the single highest-leverage change and should be made *after* the measurement confirms it.
4. **Expected fix if sending dominates** — the loop `await`s each provider call serially; batch with `asyncio.gather` bounded by a semaphore (≈10), and respect provider rate limits (SendGrid ~10 k/s is not the constraint; Twilio ~1 msg/s/number is — 100 SMS ≈ 100 s serial, which is fine for a 1 h DoD but not for 5 000).
5. **Re-measure**, record p50/p99 + row counts in the tracker next to the DoD. Gate: p99 ≤ 1 h with 500 SMEs.
6. **Failure-path test**: revoke the SendGrid key mid-run → all rows land `skipped`, none `failed`, no exception escapes; re-run resumes cleanly (statuses are per-row, so re-dispatch only retries non-`sent` rows).

## 4c — Lag views + drift: activation sequence (📋)

The code is right; it has nothing to chew on. Dependencies, in order:

1. **Watchers must produce events** — needs 4a's URL triage pass (above) to be done, else most sources contribute nothing. Check: `SELECT source_id, count(*) FROM m1_propagation_events GROUP BY 1` after a few 2-hourly cycles.
2. **Matching must be validated** — `propagation_matching.match()` assigns `match_method`/`match_confidence`, and nobody has ever eyeballed its output. Sample 30 events across methods; measure precision by hand. A false match inflates "awareness" and corrupts the headline lag finding, so this gate matters more than it looks. Record precision per `match_method` in the tracker.
3. **`gazette_published_date` must be populated** — lag = `first_seen_at − gazette_published_date`; rows with a NULL publication date silently drop out of the views. Check coverage before believing any median.
4. **Then refresh**: run `refresh_lag_analytics` manually → both matviews non-empty → sanity-check `v_m1_channel_effectiveness.median_lag_days` (expect portals faster than news; a negative lag means a date bug, not a fast portal).
5. **Drift half stays dormant until Phase 3 ships a model** — `classifier_confidence` is NULL everywhere today, so the KL branch no-ops by design (`len(baseline) >= 20` guard). After the model lands, the *first* month's distribution is the baseline; don't act on drift alerts until ≥2 windows exist. Cross-ref [[PHASE3_GAP_CLOSURE_PLAN]] Stage E.
6. **Admin lag UI (14_M1_4)** stays deferred to BUILD_13 — data is query-ready; the SME feed already ships.

## §6.5 — Delivery guarantees / retry + DLQ for alerts (📋)

Today a provider failure records `status='failed'` and nothing ever retries it — against a "within 24 h" SLA that's a silent miss. Plan (small, do with the load test):

1. Add `attempts` (int) + `last_attempt_at` to `m1_alerts` (one migration).
2. New Beat task `retry_failed_alerts` (hourly): re-send rows with `status='failed' AND attempts < 3`, exponential spacing (1 h / 4 h / 12 h — all inside the 24 h SLA), incrementing `attempts`.
3. At `attempts = 3` set `status='dead'` (widen the CHECK) — that's the DLQ, queryable in one line and surfaceable next to the sources health view.
4. Alert on `dead` count > 0 via the existing audit/probe path rather than a new channel.
5. Keep `skipped` outside this machinery — a missing API key is a config state, not a delivery failure, and retrying it forever is noise.

## §6.7 — Matching precision audit (📋 — do before publishing any lag finding)

`propagation_matching.match()` stamps `match_method` + `match_confidence` and nothing has ever validated them. A false positive dates "awareness" earlier than reality and **biases the module's headline finding downward** — this is a research-validity gate, not an engineering nicety.

1. Export 30 events stratified by `match_method` (and confidence bands) once watchers have produced volume.
2. Hand-label each as true/false match against the regulation; compute precision per method + per band.
3. Gate: precision ≥ 0.90 on the methods you keep. Below it, either raise the confidence floor used when recording, or drop the weakest method entirely (better fewer, trustworthy events than a large noisy set).
4. Record the audit table + date in the tracker; re-run after any matcher change. Recall is harder (needs a gold set of "was this actually mentioned") — treat as optional; precision is what protects the finding.

## §6.2 (second half) — WhatsApp is not a channel (📋 — decide, don't drift)

The research cites WhatsApp as the ~72% primary SME channel, yet `channel` ∈ {in_app, email, sms}. Options, in cost order: (a) **document the omission** and justify SMS as the proxy in the thesis limitations — free, honest, and probably right for the research timeline; (b) Twilio's WhatsApp Business API — same provider, template pre-approval required, ~weeks of lead time; (c) WhatsApp Cloud API direct. **Recommendation: (a) now, (b) only if a real deployment follows the research.** Whichever is chosen, write it down — the risk is silently shipping "SMS = the mobile channel" without saying so.

## §6.3 — Phase-4 validation is gated on Phase 3

Not a Phase-4 defect: alerts key off `change_category`/`affected_sectors`/confidence. Until [[PHASE3_GAP_CLOSURE_PLAN]] Stage E drops the ONNX artifact, alerts can only fire on heuristic-seeded rows — which are now explicitly marked (`classification_source='heuristic'`, Session 70), so **when validating Phase 4, filter alert-triggering rows by source** or you'll be measuring the regex seed's behaviour, not the pipeline's.

## Session 71 verification checklist (deferred to user)

1. `alembic upgrade head`; `python -m compileall app`; `pytest`.
2. `GET /admin/m1/pipeline/sources` → 15 rows; trigger both watchers; re-check health columns; park/fix dead URLs.
3. SMS smoke per 4b above (with and without Twilio creds).
4. `graphify update .`
