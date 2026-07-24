# M1 — Non-Coding Tasks & Go-Live Readiness Plan

> Group: `PROGRAM_READINESS` (cross-cutting; maps to PHASE1–4 below). Companion to the per-phase gap-closure plans and the doc set 00–04.
> **Purpose.** Answer the standing question: *the code across docs 00–04 (and 05+) is largely built — so what's left, apart from coding, to actually reach the research target?* This is the operator / researcher / annotator runbook. Written 2026-07-24, grounded in AI_WORK_LOG Sessions 66–77 and the phase gap-closure plans.

## 0. Where the code stands (honest snapshot)

| Area (doc) | Code status | The gap to the target is… |
|---|---|---|
| 00 Index / 01 Problem | n/a (framing) | — |
| 02_M1_1 Sources catalogue + health | **shipped** | *run* the watchers + triage dead URLs (ops) |
| 02_M1_2 Schema validation (3-layer) | **shipped** (migration 202607230001) | `VALIDATE CONSTRAINT` after cleaning offenders (ops) |
| 02_M1_3 Governance/retention | **shipped** (Beat-scheduled, dry-run default) | flip dry-run off when ready; PDPA export/erasure endpoints still *coded-deferred* |
| 02_M1_4 Worked examples | **shipped** (idempotent seed) | run the seed; view-assertion tests pending |
| 03_M1_1 Extraction chain | **shipped** | needs Tesseract on host for scanned PDFs (setup) |
| 03_M1_2 Segmentation | **shipped** | — |
| 03_M1_3 Secondary-source matching (3-tier) | **shipped** (202607230002) | *run* watchers to populate propagation events; embedding tier opt-in |
| 04 Preprocessing (noise/metadata/chunking) | **shipped** | — |
| **Phase 3 classifier (05+)** | **code present but INERT** — `no_model` | **the keystone: gold labels → train → export.** Human + GPU, not code |
| Phase 4 schedulers/alerts | **shipped** | Beat on; alert creds optional (ops/config) |

Bottom line: **ingest → extract → preprocess is code-complete and running.** The target (classified, SME-relevant regulatory alerts + the awareness-gap measurement for the thesis) is blocked not on more code but on **environment setup, operational runs, human annotation, and model training/evaluation.** Those are enumerated below in dependency order.

---

## 1. One-time environment setup — PHASE1_FOUNDATION (owner: you, operator)

Blocking for everything. Mostly done; the two open items are from Session 77.

1. Services up: Postgres + Redis reachable; `.env` complete (DB, `CELERY_BROKER_URL`, `M1_DEFAULT_EXTRACTION_PROFILE=wijesekara_routing_v1`).
2. **`alembic upgrade head`** — the DB must reach `202607230004` (the language-check fix). Verify `alembic current`.
3. **Tesseract 5 + `sin`/`tam` traineddata** on PATH (Session 77) — needed for scanned gazettes.
4. **`lid.176.bin`** downloaded to `storage/models/m1/baseline/` (Session 77) — `enigmatrix-ml> uv run python scripts/download_lid_model.py`.
5. Poppler on PATH (already present here).
6. Worker launched with concurrency: `--pool=threads --concurrency=4` (Windows) / `--concurrency=4` prefork (Linux) — safe post-NullPool (Session 74).
7. `uv run python -m app.m1.health` → all required components green.
8. `uv run python -m app.scripts.seed_dev` (admin + annotator + sample SME).

## 2. Data-operations runs — PHASE2_INGEST_EXTRACTION (owner: you, operator)

Turns the empty pipeline into a populated corpus. All code exists; these are *runs*.

1. **Extraction over the thesis scope.** Trigger crawls per source/date range for the study window (the diffusion analysis needs history — plan the year span you'll claim in the thesis, e.g. 2010→2026 for EGZ). Uses the new run page (Session 73) — watch ingested→extracted→preprocessed climb (Session 76 priority makes them interleave).
2. **Completeness pass.** Per source: pipeline → *Verify completeness* → re-fetch any gaps (EN→SI→TA fallback).
3. **Run the secondary-source watchers** (portal + RSS) so `m1_propagation_events` fill — this is what powers the **propagation-lag** (T0–T9) analysis, a core research output. Triage dead source URLs via the health columns.
4. **Seed worked examples** (`seed_m1_worked_examples.py`) so the two analytical views compute over real rows.
5. **`ALTER TABLE … VALIDATE CONSTRAINT …`** for the Layer-1 checks once the nightly Layer-3 job (`validate_pipeline` → `m1_pipeline_audits`) reports no offenders.
6. Refresh lag/analytics views (nightly Beat job exists; can run on demand).

## 3. Annotation / gold labels — PHASE3_ANNOTATION_CLASSIFICATION (owner: you + annotators) ★ critical path

This is the **keystone** and the single biggest non-coding effort. No model can be trained without it (AI_WORK_LOG S70 runbook).

1. **Label Studio** set up (happiest on Linux/venv) and connected to the preprocessed corpus.
2. **Calibration round** — small shared batch, measure inter-annotator agreement; gate **κ ≥ 0.80** on the 12-category scheme before scaling.
3. **Dual-annotation batches** + adjudication; running **κ ≥ 0.75**.
4. **Active-learning loop** — prioritise low-confidence / disagreement items.
5. Reach **~800 gold labels**, drawn *excluding* the heuristic-seeded rows (use `classification_source` to exclude — Session 70) so train/eval isn't contaminated.
6. Freeze a held-out test split (stratified, incl. SI/TA slices).

## 4. Model training & evaluation — PHASE3 (owner: you, on GPU)

Code path exists (in-process ONNX serving, health flips to `ready` when the artifact lands — Session 70). The *work* is training + gating.

1. **Train XLM-R** on the gold set (pinned training extra + `TRAINING.md` + `Dockerfile.train` — Session 70 plan).
2. **Gates:** 3-seed **macro-F1 ≥ 0.92**; **slice eval** incl. SI/TA + extraction-method watchpoints + chunk-contract A/B.
3. **Export ONNX** (+ INT8 gate); **drop the artifact** to the storage volume (no image rebuild).
4. Activation checklist flips `classifier_status()` → `ready` (reuses the health flag); `classify_gazette` starts populating `change_category` with `classification_source='model'`.
5. **Interim evaluation** (your near-term milestone) — report the eval tables.
6. Feed the low-confidence rows into the **classifier-review queue** (backend shipped S70) for expert override.

## 5. Research / thesis outputs (owner: you, researcher)

The reason the pipeline exists — none are code, all are analysis/writing.

1. **Awareness-gap measurement** answering the 4 research questions (01_M1) — the "34% of penalties from amendments gazetted >90 days prior" line needs the populated corpus + propagation data to reproduce/extend.
2. **Propagation-lag (T0–T9)** analysis from `m1_propagation_events` (needs §2.3 watchers to have run for a while — start them early).
3. **Evaluation write-up**: classifier metrics, slice results, extraction-quality probe (`quality_probe`), matching precision ≥0.90 as a validity gate.
4. **Documented limitations**: WhatsApp channel (recommend as limitation — S71), mixed-language rows, scanned-PDF coverage (until Tesseract), classifier trained on N gold labels.

## 6. Config / integrations — PHASE4_SCHEDULERS_ALERTS (owner: you, optional)

Not blocking the thesis, needed for a live alert demo.

1. `SENDGRID_API_KEY` (email + password-reset) / `TWILIO_*` (SMS) — without them alerts return `skipped` (dev-safe); in-app alerts still work.
2. Per-SME `phone` (E.164) + `alert_sms_opt_in=true` for the SMS leg (S71).
3. Flip `M1_RETENTION_DRY_RUN` off when you actually want retention jobs to act.

## 7. Testing / QA (owner: you)

1. `pytest` (unit) after `alembic upgrade head`.
2. Integration tests via testcontainers — **Linux/WSL** (needs a Linux Docker socket).
3. Data-quality suites (`post_extraction_check`) + the nightly Layer-3 audit.
4. `graphify update .` after code changes (keeps the knowledge graph current — CLAUDE.md rule).

## 8. Still-deferred CODE (for completeness — not "non-coding", flagged so nothing's forgotten)

- PDPA data-export/erasure endpoints + `audit_log_archive` (02_M1_3).
- Spider-side Wayback/viewstate fallback (02_M1_1).
- Tier-3 propagation review-queue UI polish (03_M1_3 — backend + `m1_propagation_reviews` persisted 2026-07-23; admin surface exists).
- View-assertion tests (02_M1_4).
- Optional: exclude deterministic `IntegrityError` from `extract_gazette` autoretry (S75 follow-up).

---

## Critical path to the target (the short version)

**setup (§1) → run extraction + watchers (§2) → annotate to 800 gold labels (§3) → train + gate XLM-R + interim eval (§4) → thesis analysis (§5).**
Everything else is parallelisable. The long pole is **§3 annotation** — start it as soon as §2 has a preprocessed corpus, and start the **§2.3 watchers early** so propagation-lag data accrues over calendar time.
