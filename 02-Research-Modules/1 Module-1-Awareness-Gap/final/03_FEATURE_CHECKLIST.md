# Enigmatrix — Master Feature Checklist

**Generated:** 2026-07-15 · synced with vault `FEATURES.md` (F-01…F-242) and code at 2026-07-03 commits.
Legend: `[✓]` shipped+verified · `[~]` code-complete, pending env/data gate · `[ ]` not started

## Platform Foundation
- [✓] Monorepo + docker-compose dev infra + Makefile targets (F-01…F-04)
- [✓] FastAPI app, settings, logging, exceptions, deps (F-05…F-09)
- [✓] Auth: bcrypt + HS256 JWT access/refresh, register/login/refresh (F-10, F-11)
- [✓] RBAC: sme / admin / annotator deps + route gating (F-12)
- [✓] Rate limiting on auth endpoints (slowapi) (F-13)
- [✓] Audit log on auth events + every admin mutation (F-16, Session 14)
- [✓] Admin user management (create/patch/activate/deactivate/reset-password/delete)
- [✓] Seeds: admin + annotator + sample SME + demo dashboards (F-18, Session 22)

## Frontend Foundation
- [✓] Next.js 14 App Router + shadcn-pattern UI + trust-blue/amber themes light+dark (F-19…F-22)
- [✓] Trilingual: next-intl EN/SI/TA + Noto Sinhala/Tamil fonts + locale switcher (F-23, F-24)
- [✓] API client + server-side requireUser()/requireRole() session guards (F-25, F-26)
- [✓] App-shell redesign, breadcrumbs, empty states, animated UI suite, theme-transition polish (Sessions 8, 44, 52)
- [✓] Dashboard streaming + perf overhaul (bundle tuning, recharts code-split) (F-174)

## Surveys (M0/M2/M3 instruments)
- [✓] Unified survey wizard `/surveys` + regulation-scoped flows + history (Sessions 6, 12, 15)
- [✓] Awareness survey 12 questions EN/SI/TA + admin responses view
- [✓] Admin question bank: CRUD, verify, bulk-verify, translations, next-code, ordering
- [✓] Survey sessions engine (start / next-question / answer / complete)
- [✓] Admin-manageable survey limits (F-16x, Session 16)
- [✓] M2 knowledge auto-scoring + admin scores UI
- [✓] M3 compliance-history + behavioural signals + risk-signals snapshot

## M1 — Ingest & Extraction (Phase 2)
- [✓] Scrapy spiders: gazette, weekly, acts, bills; date-scoped; EN→SI→TA fallback (F-145+, F-170, F-177)
- [✓] Completeness verify + re-fetch endpoints, hardened (timeout/CORS/WS) (F-177, F-178)
- [✓] PDF classifier text/hybrid/scanned + calibration CLI (F-149)
- [✓] Extractors: PyMuPDF, pdfplumber, pypdfium2 + per-page engines (F-149, Session 58-ml)
- [✓] OCR: Tesseract eng+sin+tam @300dpi + per-page timeout + CER calculator (F-149)
- [✓] Surya OCR fallback profile + page-routing + Wijesekara-routing profiles (ml 2026-06-02)
- [✓] Font-aware Wijesekara→Unicode conversion + fastText language ID (F-153)
- [✓] Preprocessing chain: cleaning, metadata, penalties (multi-penalty), chunking, sub-docs (F-154…F-157)
- [✓] Celery pipeline ingested→extracted→preprocessed + WebSocket live progress (F-152, F-173)
- [✓] Admin extraction portal: date-range picker, run history, cancel/rollback, PDF Records, trace (F-185…F-198)
- [✓] 800 raw PDFs bulk-extracted, 11 batches (F-199)
- [✓] Railway + Vercel + Aiven production deployment (F-193…F-198)

## M1 — Extraction Accuracy Measurement
- [✓] Dataset registry: datasets / immutable sealed versions / rows + SHA-256 (F-200…F-205)
- [✓] Excel ground-truth upload + parser (F-203)
- [✓] Extraction-profile registry + run dispatcher (F-160s / slice 4)
- [✓] Measurement engine: per-field metrics, aggregates, strata, completeness (slice 5)
- [✓] Dynamic date-range measurement + date-scope filter (Session 58, F-Slice9)
- [✓] Re-extraction overlap alert + auto v1→v2 versioning (Session 58)
- [✓] Measurement dashboard + drill-downs + worst-N + calibration + sparkline + shortcuts (Sessions 58–60)
- [✓] Accuracy-report Markdown export `GET /m1/measurements/{run_id}/report.md` (F-242)
- [✓] Data-quality expectation suites + post-seal validation task (F-210s)
- [✓] Legacy-baseline backfill script + retention policy task (F-209, F-213)
- [✓] Thesis artefact generator (tables 4_1–4_3, figures, provenance) (F-212)
- [ ] FE report-download button + CSV export + audit upgrade list (Session-72 audit)

## M1 — Annotation & Classification (Phase 3)
- [✓] Label Studio config XML: 12 categories + 10 sectors + relevance + confidence (F-216)
- [✓] Calibration set: 20 trilingual docs with expert labels + rationales (F-217)
- [✓] Samplers: stratified + k-means + active-learning + `sample_for_labeling.py` → batch_01.csv (F-218…F-220)
- [~] Label Studio instance stood up locally (`mydata/`) — labels not yet collected
- [ ] Phase 3c: calibration test κ≥0.80 → 200-doc batch → AL batches → ≥800 gold (F-222)
- [✓] Model package: labels/config/temporal data loader/XLM-R+LoRA architecture/trainer (F-226)
- [~] 3-seed GPU training run @ macro-F1 ≥ 0.92 (F-223) — needs gold labels
- [✓] Eval: per-slice F1 + slice-cliff check + error analysis + TF-IDF baselines (F-227)
- [~] Real eval run on trained checkpoint (F-224)
- [✓] ONNX export (+INT8) + GazetteInference runtime (F-228)
- [~] `classify_gazette` live in prod (F-225) — needs model + migration `202606300001`

## M1 — Watchers, Alerts, Analytics (Phase 4, code-complete)
- [✓] `m1_propagation_events` + 2-step matcher (exact → fuzzy ≥0.78), unit-tested (F-231)
- [~] Portal watcher (IRD/EPF/ETF/eROC) — Beat 2 h; URLs to confirm + live run (F-229)
- [~] RSS watcher (5 news feeds) — Beat 2 h; live run pending (F-230)
- [✓] `m1_alerts` model + content builder + SendGrid/Twilio providers + idempotent dispatch (F-232)
- [~] Alerts API public/SME/mark-read — live after migration `202606300003` (F-233)
- [~] `/alerts` website page — needs middleware + nav wiring (F-234)
- [✓] Lag materialized views + KL-divergence drift helper, unit-tested (F-235)
- [~] Nightly `refresh_lag_analytics` Beat task — live run pending data (F-236)

## M1 — Findings & Retraining (Phase 5, code-complete)
- [✓] `findings_common.py` + preregistration F1–F6 (F-237)
- [~] 4 findings notebooks — demo verified; real data pending survey + propagation + model (F-238)
- [✓] `m1_retraining_runs` + canary promotion.decide() (F-239)
- [~] `retrain.py` + quarterly/drift-triggered retraining task — real run needs model + GPU (F-240)
- [ ] Phase 5a survey fieldwork ≥100 SMEs

## Knowledge Portal
- [✓] Vault-backed `/knowledge/*` (23 surfaces) + chokidar→SSE live sync + ⌘K palette (Session 57)
- [✓] Sessions/features/changes/build-tracker/plans/modules/graph pages + obsidian:// links
- [ ] Fuzzy search index, D3 force graph, kanban/gantt views (deferred)

## Modules 2–4
- [✓] M2 Knowledge Hub: sector question banks + scoring + verify + admin UI
- [✓] M3 risk snapshot: compliance-history + behavioural + risk-signals endpoints + admin UI
- [ ] M3 ML risk model
- [ ] M4 misinformation verifier (`/verify/claim`, `/qa/ask` = 501 stubs)

## Ops / Infra
- [✓] CI workflow `ci-m1-phase2.yml` (pytest + lint + typecheck + playwright + alembic check) (F-214)
- [~] Migrations `202606300001–005` applied in production
- [ ] Docker digests pinned (placeholders); Railway PAT rotation; worker/beat split
- [ ] `graphify update .` (graph stale since `94ae62d0`, 2026-05-23)
