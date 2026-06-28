---
tags: [meta, m1, local-dev, index]
source: synthesised
layer: meta
module: m1
---

# M1 Local Development — Phase 2 Run + Verify Index

> **Prereqs**: complete [Local Dev Handbook](../../../04-Technology-Stack/00_LOCAL_DEV_HANDBOOK.md) §1 (one-time prerequisites) + §3 (day-zero bring-up). The per-phase guides below assume Postgres + Redis are running and `uv sync` has installed both backend + ml workspace deps.

This index lists every shipped M1 Phase 2 step in dependency order. Each linked doc tells you which terminal to use, what to run, and how to verify the result. They mirror the retrospective specs in [planned-for-development/](../planned-for-development/) — the planning docs describe **what was built**; these describe **how to run + check it locally**.

---

## Phase 2 — Ingest + extraction (✅ complete)

| Step | Session / F-ID | Terminal | What it ships | Local-dev doc |
|---|---|---|---|---|
| 2a | Session 23 / F-145 | WSL | Scrapy gazette spider → `m1_regulations` rows at `status='ingested'` | [phase2_step2a_scrapy_spider](phase2_step2a_scrapy_spider.md) |
| 2b | Session 26 / F-148 | WSL | Celery + Stage-B PDF extraction; rows advance `ingested → extracted` | [phase2_step2b_celery_extract](phase2_step2b_celery_extract.md) |
| 2c | Session 28 / F-149 | WSL | Canonical `ml/m1/extraction/` chain (PyMuPDF / pdfplumber / Tesseract) | [phase2_step2c_extraction_chain](phase2_step2c_extraction_chain.md) |
| 2d | Session 30 / F-153 | WSL | fastText language detection + Wijesekara conversion + per-page OCR fallback | [phase2_step2d_language_wijesekara](phase2_step2d_language_wijesekara.md) |
| 2e | Session 31 / F-154 | WSL | Preprocessing chain (cleaning + metadata + chunking) — ml-package only | [phase2_step2e_preprocessing](phase2_step2e_preprocessing.md) |
| 2f | Session 32 / F-155 | WSL | Wire preprocessing into Celery + DB persistence; rows advance to `status='preprocessed'` | [phase2_step2f_celery_wiring](phase2_step2f_celery_wiring.md) |
| Cleanup | Session 34 / F-157 | WSL | Segmenter promotion + penalty enum widening + `is_admin_set` + `m1_sub_documents` | [phase2_session34_cleanup](phase2_session34_cleanup.md) |

---

## Recommended walkthrough (first-time)

If you've never run any of this locally, walk the docs in **table order** (top to bottom). Each step's verify-step proves the prior step still works, so a clean walkthrough of all 7 confirms the full pipeline is green.

Total time: **~45-60 minutes** if all the prerequisites are already installed (model downloads + Docker pulls excluded — those are one-time).

---

## Per-step quick-launch (returning user)

If you've already done the walkthrough once and just need to spot-check a specific step:

```bash
# Get the Postgres + Redis containers up
cd ~/repos/xyz && docker compose -f docker-compose.dev.yml up -d postgres redis

# Bring DB to latest:
cd enigmatrix-backend && uv run alembic upgrade head

# Then jump to the step's doc above.
```

Common debug paths:

- **Spider not finding gazettes** → [phase2_step2a §6 (Troubleshooting)](phase2_step2a_scrapy_spider.md)
- **Extraction task hangs** → [phase2_step2b §7 (Troubleshooting)](phase2_step2b_celery_extract.md)
- **Wrong PDF classifier output** → [phase2_step2c §5 (Threshold calibration)](phase2_step2c_extraction_chain.md)
- **Sinhala/Tamil text mis-routed** → [phase2_step2d §4 (CLI smoke)](phase2_step2d_language_wijesekara.md)
- **Preprocessing returns wrong gazette_number** → [phase2_step2e §6 (Verifying changes)](phase2_step2e_preprocessing.md)
- **Row stuck at `status='extracted'`** → [phase2_step2f §5 (Manual smoke)](phase2_step2f_celery_wiring.md)
- **`m1_sub_documents` empty after task** → [phase2_session34_cleanup §5](phase2_session34_cleanup.md)

---

## Cross-references

- **Roadmap**: [16_M1_Development_Roadmap](../16_M1_Development_Roadmap.md) (the canonical phase plan)
- **Retrospective specs**: [planned-for-development/](../planned-for-development/4_setup.md) (1_setup.md → 6_setup.md cover Steps 2a-2f)
- **Top-level handbook**: [04-Technology-Stack/00_LOCAL_DEV_HANDBOOK](../../../04-Technology-Stack/00_LOCAL_DEV_HANDBOOK.md)
- **Findings log**: [08-Findings-Log/SESSIONS](../../../08-Findings-Log/SESSIONS.md) (newest entries first)
- **Next milestone**: Phase 3 Step 3a — Label Studio setup + 20-doc calibration test (not yet implemented; spec at [09_M1_Annotation_Guidelines](../09_M1_Annotation_Guidelines.md))