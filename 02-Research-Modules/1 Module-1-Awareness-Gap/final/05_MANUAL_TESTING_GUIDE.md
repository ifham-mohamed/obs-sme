# Enigmatrix — Manual Testing Guide

**Generated:** 2026-07-15. Local setup: `make up && make migrate && make seed` → backend `make dev-backend` (http://localhost:8000/docs) + frontend `make dev-frontend` (http://localhost:3000). Seed admin: `admin@enigmatrix.lk` / `admin12345`.

## 1. Auth & RBAC
**Test:** register an SME (email + password + sector/region) at `/register`; login; hit an admin URL (`/admin/users`).
**Expect:** SME gets 403/redirect on admin routes; `/admin/activity-log` shows `auth.register` + `auth.login.success` rows. **Edge:** 6+ rapid logins → 429 (slowapi). **Failure:** wrong password → `auth.login.failure` audit row.

## 2. Survey Flow
**Test:** as SME, `/surveys` → Awareness Survey → answer 12 questions (switch locale mid-survey EN→SI).
**Expect:** progress persists (`survey_sessions`); completion visible at `/surveys/history`; admin sees responses at `/admin/surveys/awareness/responses`; M2 auto-score appears in `/admin/m2/scores`. **Edge:** re-taking beyond the configured survey limit → blocked with message.

## 3. Gazette Ingest + Extraction (pipeline)
**Test:** `/admin/m1/pipeline/extraction` → pick a small date range (single year) → trigger.
**Expect:** live progress via WebSocket (status card with sub-steps); funnel at `/admin/m1/pipeline` increments ingested→extracted→preprocessed; recent-runs table row; failed rows show red drill-down chevron. Re-trigger the same range → **overlap warning banner** (repeat-crawl).
**Verify PDFs:** `/admin/m1/pdf-records` lists raw PDFs; a regulation's raw PDF downloads via its trace page `/admin/m1/pipeline/trace/{id}`.
**Completeness:** pipeline sources page → verify → missing items reported → re-fetch attempts EN→SI→TA. **Failure case:** cancel a running extraction → status `cancelled`, rollback leaves no partial rows.

## 4. Extraction Accuracy Measurement (the accuracy feature)
Permissions: admin.
1. **Ground truth:** `/admin/datasets/m1/new` → create dataset → upload Excel ground truth (`/admin/datasets/m1/[id]/upload`) → version appears; **seal** it. Expect: SHA-256 shown; a data-quality validation runs post-seal (violations, if any, on the version page).
2. **Candidate extraction run:** `/admin/datasets/m1/extractions/run` → choose profile (e.g. `page_routing_v1`) + scope → run. Overlapping a prior version's range → **auto v1→v2 badge** in the form.
3. **Measure:** `/admin/datasets/m1/measurements/run` → pick baseline (ground-truth version) + candidate + optional date-range/source → run → open the run.
**Expect:** overall + per-field scores; worst-N list; per-regulation drill-down; calibration view; sortable columns (`n` / `?` shortcuts); sparkline of last 8 runs.
4. **Report export:** GET `http://localhost:8000/api/v1/m1/measurements/{run_id}/report.md` (or Swagger) → Markdown report with overall/per-field/worst-N. *(FE download button pending — Session-72 audit.)*
**Edge:** date-scoped candidate vs full ground truth → score is computed only on the date window (no unfair penalty).

## 5. Classification (after model deploy)
**Pre-req:** migrations `202606300001+` applied; `M1_MODEL_ONNX_DIR` set; trained model exported.
**Test:** run a fresh small extraction; watch a regulation move `preprocessed → classified`.
**Expect:** `change_category` + `classifier_confidence` populated; confidence < 0.55 flagged for review; an `expert_verified` regulation is never overwritten. **Without model/env:** task exits gracefully; status stays `preprocessed`.

## 6. Watchers & Propagation (Phase 4a)
**Pre-req:** migration `202606300002`; network; source URLs confirmed in `m1_secondary_sources.py`.
**Test:** `run_rss_watcher.apply()` (or wait for the 2-h Beat) with ≥1 active regulation whose gazette number appears in a feed item.
**Expect:** `m1_propagation_events` row (match_method `exact` conf 1.0, or `fuzzy` ≥ 0.78; `first_seen_at` = feed publish date); re-run → no duplicate (unique regulation × source).

## 7. Alerts (Phase 4b)
**Pre-req:** migration `202606300003`. Without SendGrid/Twilio keys, email/SMS return `skipped` (dev-safe); in-app always works.
**Test:** dispatch `dispatch_regulation_alerts` for a verified regulation → visit `/alerts` logged-out and as an SME in a matching sector.
**Expect:** public feed shows the broadcast; SME feed shows a sector-matched unread alert; mark-read clears the unread count; re-dispatch → no duplicates (idempotent). **Edge:** SME in a non-matching sector sees only the public entry.

## 8. Analytics, Drift, Retraining (Phases 4c/5c)
**Test:** apply migrations `202606300004–005`; run `refresh_lag_analytics.apply()`.
**Expect:** materialized views refresh; with classified rows, drift check computes KL (alert only if > 0.15). Retraining: `python enigmatrix-ml/scripts/retrain.py --dry-run` → `retrain_result.json` with `action: promote`; a `m1_retraining_runs` row when run via the task.

## 9. Findings Notebooks (Phase 5b)
**Test:** `uv sync --extra research` → `pytest tests/research/test_findings_common.py` → Run-All each `research/notebooks/findings_*.ipynb` without `DATABASE_URL`.
**Expect:** synthetic demo computes every finding (F1 ≈ 6.8 d portal lag, F6 DiD ≈ −19.9 d). With `DATABASE_URL` set → real data.

## 10. Knowledge Portal
**Test:** open `/knowledge`; edit a vault markdown file in Obsidian; save.
**Expect:** UI updates within ~2 s (SSE toast); ⌘K palette navigates; plan/chapter pages deep-link back via `obsidian://`.

## 11. Automated Suites
- Backend: `cd enigmatrix-backend && uv run pytest` (unit: alert content, drift, propagation matching, measurement report, pdf classifier, overlap…)
- ML: `cd enigmatrix-ml && uv run pytest` (extraction 12+, evaluation 19+, model labels/data/promotion, findings_common)
- Frontend: `pnpm exec playwright test` (E2E incl. `@phase2` tag) · CI: `.github/workflows/ci-m1-phase2.yml`.
