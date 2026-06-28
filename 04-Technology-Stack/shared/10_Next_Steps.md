# 10 — Next Steps

> **Goal:** know what to build next and how to slot your work into the existing tracker.

The MVP is intentionally a *vertical slice*: only enough auth + survey + admin machinery to prove the stack works end to end. Everything else is documented as a BUILD spec waiting to be picked up.

---

## 1. Roadmap — one paragraph per remaining BUILD file

Pick the slice that interests you, read the corresponding BUILD file end to end, then file new feature rows in [`docs/tracker/FEATURES.md`](../../tracker/FEATURES.md) before you start writing code.

### [`BUILD_07`](../../backend/BUILD_PLAN/BUILD_07_Module1_Awareness.md) — Module 1: Regulatory Awareness

Gazette ingestion → PDF extraction (PyMuPDF / pdfplumber / Tesseract OCR) → segmentation → XLM-RoBERTa classifier → multilingual summarisation → secondary-source watchers → lag computation → alert engine. Module 1 is the data backbone for Modules 2 and 4. **Start with:** `app/ingestion/gazette/lister.py` against `documents.gov.lk`. Walk the seven-stage pipeline in [`research/10_Module1_Gazette_PDF_Extraction_Pipeline.md`](../../backend/research/10_Module1_Gazette_PDF_Extraction_Pipeline.md). The current 501 stub at `/api/v1/regulations` becomes a list endpoint backed by the new `regulations` table.

### [`BUILD_08`](../../backend/BUILD_PLAN/BUILD_08_Module2_Knowledge.md) — Module 2: Compliance Knowledge & RAG

All three SME survey instruments (M1 awareness, M2 knowledge, M3 vulnerability) are **complete** as of Sessions 8–19. The rule-based scoring engine (`m2_scoring.py`) and `GET /api/v1/m2/sme/{sme_id}/knowledge_score` are already live. The remaining BUILD_08 work is: ML-assisted scoring (deferred) and the RAG knowledge base built from Module 1 summaries (ChromaDB + multilingual-e5-base embeddings). **Start with:** gazette ingest (BUILD_07) to build the RAG corpus, then wire ChromaDB into `/api/v1/qa/ask`.

### [`BUILD_09`](../../backend/BUILD_PLAN/BUILD_09_Module3_Risk.md) — Module 3: Compliance Risk

Feature engineering across firmographic, behavioural, sectoral, M1-exposure, and M2-knowledge signals → XGBoost/LightGBM with optional LSTM → SHAP per prediction → calibrated serving via MLflow registry → drift monitoring. Targets: ROC-AUC ≥ 0.75, P@10% ≥ 0.60. **Start with:** `ml/m3/features.py` and the four `m3_*` tables. Module 3 must not start until Module 1 + Module 2 produce real data.

### [`BUILD_10`](../../backend/BUILD_PLAN/BUILD_10_Module4_Misinformation.md) — Module 4: Misinformation

Multi-platform ingestion (Twitter/X Academic API, Reddit, Facebook public pages, voluntary WhatsApp uploads) → fastText language detection → NLLB-200 translation → 9-way veracity classifier (XLM-R) → RAG verifier against the M1 corpus → claim-check public tool. **Start with:** the `m4_raw_posts` table + the Twitter ingester template in [`BUILD_10`](../../backend/BUILD_PLAN/BUILD_10_Module4_Misinformation.md) §5. The 501 stub at `/api/v1/verify/claim` becomes the public claim-check endpoint.

### [`BUILD_11`](../../ml/BUILD_PLAN/BUILD_11_ML_Training_Pipeline.md) — Shared ML training pipeline

Cross-module training infra: dataset versioning, MLflow tracking, Optuna sweeps, eval gates (M1 ≥ 0.80, M2 RAGAS ≥ 0.85, M3 AUC ≥ 0.75, M4 ≥ 0.75), registry promotion that flips `model_versions.is_production`. **Start with:** `ml/common/trainer.py` base class and the `ml/datasets/manifest.yaml` versioning convention. Should land before Modules 1 / 3 / 4 do their first training runs.

### [`BUILD_12`](../../backend/BUILD_PLAN/BUILD_12_Data_Ingestion_and_Scheduling.md) — Ingestion & scheduling

All scrapers + watchers + schedulers in one place: source registry, Scrapy projects, Playwright workers, social-media connectors, IRD defaulter scrape, court records, APScheduler (dev) / Celery beat + Redis (prod), token-bucket outbound rate limiter, idempotency via content hashes. **Start with:** `app/ingest/registry.py` — one dict naming every source, parser, cadence, and ToS note. The Module 1 scraper that lives in [`BUILD_07`](../../backend/BUILD_PLAN/BUILD_07_Module1_Awareness.md) is a *consumer* of this registry.

### [`BUILD_13`](../../frontend/BUILD_PLAN/BUILD_13_Admin_and_Annotation.md) — Admin & annotation

Admin frontend + Label Studio bridge + append-only audit-log enforcement + bulk CSV ops. **Start with:** the audit-log Postgres trigger that prevents UPDATE/DELETE on `audit_log`. The current admin pages (`/admin/surveys/awareness/responses`, `/admin/users`) live inside the same `(admin)` route group this BUILD expands.

### [`BUILD_14`](../../infra/BUILD_PLAN/BUILD_14_Deployment_Cloud.md) — Production deployment

Single-VM (4 vCPU / 16 GB) docker-compose, nginx + certbot, secrets via sops/Doppler, pg_dump + Chroma snapshots, blue/green deploy, GitHub Actions CI/CD. **Start with:** the production `Dockerfile` for the backend (multi-stage, slim runtime). The dev compose in [`docker-compose.dev.yml`](../../docker-compose.dev.yml) is *not* the production compose.

### [`BUILD_15`](../../infra/BUILD_PLAN/BUILD_15_Observability_Testing.md) — Observability + CI

Prometheus + OpenTelemetry + Grafana dashboards + alertmanager + the full test pyramid (Vitest unit, testcontainers integration, Playwright e2e, k6 load) + GH Actions CI. **Start with:** `prometheus-fastapi-instrumentator` on the backend and the four custom counters per module. CI itself is the last item — local-only tests until then.

---

## 2. Where each BUILD plugs into the live MVP

| BUILD | Today's hook |
|-------|-------------|
| 07 (M1) | `/api/v1/regulations` 501-stub → list endpoint. New table `regulations`. New page `/regulations`. |
| 08 (M2) | `SupportedInstrument` extends from `["awareness"]` to include `knowledge` + `vulnerability`. New ChromaDB collection `regulations_chunks_v1`. New endpoints `/api/v1/m2/...`. |
| 09 (M3) | M3 data capture complete: `m3_compliance_history`, `m3_behavioural_signals` tables live; `GET /api/v1/m3/sme/{id}/risk-signals` live; `/risk` page implemented (M2 score + M3 signals two-card layout). Remaining: XGBoost/LightGBM ML risk model training (requires ≥200 responses), SHAP, MLflow registry. |
| 10 (M4) | `/api/v1/verify/claim` 501-stub → real endpoint. New tables `m4_*`. New page `/verify`. |
| 11 | New `ml/` tree. Backend reads model versions from the new MLflow registry instead of file paths. |
| 12 | Backend imports `app/ingest/registry.py`. APScheduler boots inside the lifespan in [`app/main.py`](../../backend/app/main.py). |
| 13 | Admin route group expands. New tables for review queues. |
| 14 | New production `Dockerfile`s + nginx config; `make up` is replaced for prod. |
| 15 | New `prometheus_fastapi_instrumentator` middleware in `app/main.py`; new `.github/workflows/`. |

---

## 3. Contribution flow (today, MVP-sized team)

1. **Pick a slice.** Read the relevant BUILD file end to end. Read this `docs/SETUP/` track for the conventions.
2. **File feature rows** in [`docs/tracker/FEATURES.md`](../../tracker/FEATURES.md) — one row per acceptance-criterion-sized chunk. New ids continue the `F-NN` numbering. Status starts at 🔲.
3. **Open a session** in [`docs/tracker/SESSIONS.md`](../../tracker/SESSIONS.md). One entry per work session, dated, with "Done", "Decisions", "Next session", "Blockers".
4. **Branch.** `git checkout -b feature/<slug>` (e.g. `feature/m2-knowledge-survey`).
5. **Flip status.** Move features from 🔲 to 🟡 as you start them.
6. **Code + tests.** Match the conventions in [`04_Backend_Development.md`](04_Backend_Development.md) and [`05_Frontend_Development.md`](05_Frontend_Development.md). Always add a test (integration preferred for backend; Playwright for cross-page flows).
7. **Run** `make test && make lint` until green.
8. **Update tracker.** Flip 🟡 → 🟢 only when acceptance criteria are met *and* the smoke test passes. Add a row to [`docs/tracker/CHANGES.md`](../../tracker/CHANGES.md) referencing the feature ids.
9. **Open a PR.** Summarise which features flipped state.
10. **Merge.** No CI gate yet (BUILD_15 ships that). Reviewer should at least eyeball the diff and the tracker change.

---

## 4. Project-level open questions

These are not blockers for engineering Layer 1, but every one must be resolved before thesis submission. Re-read whenever you start a new slice — the answer to OQ3 / OQ4 may change *what* you build.

| # | Gap | Owner | Tracked in |
|---|-----|-------|-----------|
| OQ1 | Library *versions* not pinned across the stack (only ranges in `pyproject.toml` / `package.json`). The canonical lock files are committed but not yet enforced as the deployment artifact. | DevOps lead, BUILD_14 implementer | [`BUILD_00_INDEX.md`](../BUILD_PLAN/BUILD_00_INDEX.md) |
| OQ2 | Per-module training hyperparameters (LR, batch size, epochs) not locked. | Each module owner before the first training run | [`BUILD_00_INDEX.md`](../BUILD_PLAN/BUILD_00_INDEX.md) |
| OQ3 | Ethics committee approval reference missing. Required for survey deployment beyond the dev seed. | Project lead | [`BUILD_00_INDEX.md`](../BUILD_PLAN/BUILD_00_INDEX.md) |
| OQ4 | NEDA / Chamber of Commerce survey-distribution partnership unconfirmed. Survey n-targets at risk. | Project lead, by week 5 | [`BUILD_00_INDEX.md`](../BUILD_PLAN/BUILD_00_INDEX.md) |
| OQ5 | ~~Survey-question schema migration policy.~~ **RESOLVED (Session 16).** Policy confirmed: append-only `survey_responses` with versioned `question_code` (`awareness.v1.qNN`). All four instruments shipped. The `survey_sessions` table now groups responses per run and enforces admin-configurable limits (`survey_limits`). | — | Shipped F-134–F-140 |
| OQ6 | Server-side `confirmPassword` validation. Currently frontend-only via zod. | Auth owner | [`docs/tracker/FEATURES.md`](../../tracker/FEATURES.md) |

---

## 5. Recommended next slice (opinion)

The all-four-module SME survey surface is complete as of Session 19. The session-based architecture (`survey_sessions`, `survey_limits`) is live. The remaining work is ML/ingest-heavy.

If you're picking the project up cold and want the highest-impact next step:

1. **Gazette ingest (BUILD_07)** — stand up the PDF lister + OCR pipeline against `documents.gov.lk`. This is the data backbone that feeds M2 (RAG), M3 (training data), and M4 (claim checking). Start with `app/ingestion/gazette/lister.py`.
2. **Collect M2 + M3 survey responses** — the session-based survey surface is live; get real SME respondents to generate the training data needed for M3's ML risk model (BUILD_09 §4).
3. **M3 risk model (BUILD_09)** — M3 data capture and the `/risk` dashboard are already live. Once ≥200 M2+M3 response rows exist, run feature engineering → XGBoost baseline → SHAP → MLflow registry. The ML model replaces the current signal-display view with a calibrated risk score.

These are sequentially dependent: ingest first, then responses, then model training.

---

**Prev:** [`09_Troubleshooting.md`](09_Troubleshooting.md) &nbsp;·&nbsp; **End of SETUP track.**

Once you've finished a slice, log it in [`docs/tracker/SESSIONS.md`](../../tracker/SESSIONS.md) and consider opening a follow-up entry in this file pointing at the next milestone.
