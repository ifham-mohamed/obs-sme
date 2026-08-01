# Module 1 — Phase 3 Gap-Closure Plan (Annotation + Classification)

> Companion to [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/18_PHASE3_ANNOTATION_CLASSIFICATION_ANALYSIS]]. One entry per gap (#1–#7), each with status and step-by-step execution. **Session 70 (2026-07-21) implemented the code-addressable gaps (#3, #5, #6-backend, #4-measurement)**; #1–#2 are the human/GPU critical path and get the detailed runbook below — they cannot be closed by code alone.

## Status summary

| # | Gap | Status |
|---|---|---|
| 1 | Full model never trained/exported — pipeline inert | 📋 runbook below (critical path); CPU LoRA smoke passed but is not promotable |
| 2 | Gold annotation not completed / κ not gated | ✅ 800 resolved gold rows from Batches 02-05; category kappa 0.871534 |
| 3 | Heuristic corpus mistakable for model output | ✅ implemented — `classification_source` |
| 4 | Serving diverges from plan (in-process vs Fly) | ✅ decision + latency now measured; plan below |
| 5 | Silent-failure ergonomics (no model = invisible) | ✅ implemented — classifier readiness in health |
| 6 | Review-queue UI deferred | ✅ backend implemented; UI slice specced |
| 7 | Training env heavy + optional | 🟡 local extras usable for smoke; full CUDA/GPU environment still required |

---

## Current Phase 3 State (2026-07-30)

This plan remains the original gap-closure sequence, but the annotation gap has progressed:

- Annotator calibration was run and retested where needed.
- Batches 02, 03, 04, and 05 were dual-annotated and reduced into `gold_standard.csv`.
- Current accepted gold set: 800 rows, category kappa 0.871534, mean sector kappa 0.863776, SME relevance kappa 0.723518.
- `manual_resolutions.csv` contains 40 adjudicated disagreement rows; `gold_standard.csv` has 760 `auto_agree` rows and 40 `manual_review` rows.
- Frozen v1 files exist: `gold_standard_v1_800.csv`, `iaa_report_v1_800.json`, and `iaa_report_summary_v1_800.csv`.
- Deterministic `--by key` parquet split exists: train 560, validation 120, test 120.
- TF-IDF baselines are complete: LogReg macro-F1 0.4980 and LinearSVC macro-F1 0.6167.
- CPU LoRA smoke is complete and wrote `storage\models\m1\xlmr_lora_smoke\model_registry.json`, but `gate_pass=false`; this proves the training loop only, not model quality.
- Immediate action: decide rare-domain top-up vs. limitation wording, then run full LoRA training/evaluation on a CUDA/GPU machine.
- Full LoRA training is no longer blocked by row count or category IAA, but rare-domain coverage and GPU availability remain validity/execution limitations.

---

## Gaps #1 + #2 — The critical path: gold labels → κ gates → train → export → activate

Everything else is downstream of this. Detailed runbook, in order; each stage names its gate and where the evidence gets recorded (the analysis flagged that κ gates had "no recorded pass" — every gate below writes to the tracker).

### Stage A — Calibration (3a gate: first-attempt κ ≥ 0.80)

1. Recruit 2–3 annotators (law/compliance background preferred; EN required, SI/TA at least one each).
2. Stand up Label Studio from the existing `research/data/label_studio_config.xml`; import `calibration_set_v1.csv` (20 reference docs, expert labels withheld).
3. Each annotator labels all 20 **independently** (no discussion). Budget ~2 h.
4. Compute κ per annotator-pair AND per annotator-vs-expert on `change_category` (Cohen's κ; the existing kappa script — `tests/evaluation/test_kappa_script.py` exercises it — is the tool). Gate: **κ ≥ 0.80 vs expert**.
5. Below gate → adjudication session over every disagreement using the calibration set's `annotator_notes` rationales → re-test on the same 20 (order shuffled). Two failures → revise the taxonomy decision hints in the XML, not the annotator.
6. **Record**: κ matrix + date + annotator ids → `FEATURES.md` (close the F-243 open end) + session log. This is the "recorded pass" the tracker lacks.

### Stage B — Batch annotation with the AL loop (3b/3c gate: IAA κ ≥ 0.75, 800 gold)

1. `batch_01.csv` (250 docs: 200 stratified + 40 k-means diversity + 10 minority) already exists — import to Label Studio, **dual-annotate** every doc.
2. Per batch: compute pairwise κ. Gate **κ ≥ 0.75**; disagreements → adjudicate → single gold label per doc. Record κ per batch in the tracker.
3. Train the AL baseline (`m1/model/baselines.py` ALBaseline, TF-IDF+LR) on gold-so-far → `select_uncertainty_batch` (margin sampling) picks batch_02 (~200) from the unlabelled pool → repeat. Expect 3–4 batches to reach **800 gold**.
4. Export gold as parquet via `m1/model/data.py` conventions. Current v1 split uses `--by key` because reliable gazette dates are absent in the accepted gold file; replace with a temporal/stratified split if stronger evaluation evidence is required. **The F-199 heuristic rows are NOT gold and never enter this set** (they're now marked `classification_source='heuristic'` — gap #3 — so the exporter can exclude them mechanically).
5. Minority floor: every category ≥ 20 gold docs; if a category can't reach it, merge per taxonomy rules BEFORE training, not after.

### Stage C — Train (3d gate: 3-seed mean macro-F1 ≥ 0.92)

1. Environment: the separate ML env from gap #7 (GPU box / Colab Pro / Lambda; `uv sync --extra training` per the plan below). Local CPU smoke has already passed, but the final run must verify CUDA: `python -c "import torch; assert torch.cuda.is_available()"`.
2. Run `m1/model/train_xlmr.py` — the 3-seed loop, temporal split, model-registry hash are already coded. Config via `ModelConfig` (LoRA r, lr, epochs); start with defaults.
3. Gate: mean macro-F1 across the 3 seeds ≥ 0.92 on the held-out temporal split. Below gate, in order: more gold (another AL batch — usually the answer), then LoRA r / lr sweep, then category-merge review. Record all runs + seeds + F1s in the tracker.

### Stage D — Eval + slices (3e)

1. `m1/model/eval.py` on the winning seed: per-language / per-quarter / per-length / per-extraction-method slices + confidence-bucket monotonicity.
2. Watch specifically: **SI/TA slice F1** (if >5 pp below EN, the Wijesekara-era text quality is leaking into labels — cross-check rows extracted pre-Session-69 against the font-aware backfill in [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/17_PHASE2_TRILINGUAL_AUTOCHAIN_PLAN]]), and **extraction_method slice** (tesseract-extracted docs materially worse → OCR CER is the binding constraint, feeds the Surya decision).
3. Also run the chunk-contract A/B from [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/13_PHASE2_CHUNK_CONTRACT_PLAN]] (cleaned_text-head vs classification_chunk) — decide the inference input on evidence before the artifact ships.

### Stage E — Export + activate (3f gate: INT8 within 1.5 pp; p95 ≤ 2 s)

1. `m1/model/export_onnx.py` (fp32 + `--int8`); gate INT8 macro-F1 within 1.5 pp of fp32 on the eval set — else ship fp32.
2. Drop the artifact at `$M1_MODEL_ONNX_DIR` (default `storage/models/m1/onnx/v1` — on Railway that's the `/data/storage` volume, so it's a one-time `scp`/console upload, NOT an image rebuild).
3. Activation checklist: worker health flips `classifier: no_model → ready` (gap #5 surface, zero code); re-run `classify_gazette` on a small preprocessed sample; check `latency_ms` in worker logs against p95 ≤ 2 s (gap #4 measurement); `classification_source='model'` rows appear (gap #3); low-confidence rows appear in `GET /admin/m1/pipeline/classifier-review` (gap #6).
4. Bulk-classify the backlog (rows at `status='classified'` with heuristic source can be re-run; `expert_verified` rows are never overwritten — enforced in task code).
5. Later model versions go through `m1/model/promotion.py` canary flow — v1 is a direct drop because there's nothing to canary against.

---

## Gap #3 — `classification_source` marker ✅ IMPLEMENTED

Migration `202607210005`: `classification_source` CHECK ('heuristic'|'model'|'expert') + backfill — every currently categorised row predates the model, so `expert_verified → 'expert'`, else `'heuristic'` (exactly the F-199 seed). `classify_gazette` writes `'model'`; the review-queue override writes `'expert'`. **Analytics rule from now on: any consumer of `change_category` filters or facets by `classification_source`** — the Phase-4/5 findings queries must treat 'heuristic' rows as covariate-shifted seed data, not predictions. Gold-set exporters exclude them mechanically (Stage B.4).

## Gap #4 — Serving divergence: decide in-process, measure the DoDs ✅ DECIDED + MEASURED

**Recommendation: amend the roadmap DoD to in-process ONNX, don't build Fly.** Grounds: the worker already ships the runtime; gazette volume (~dozens/day) never queues; a network hop adds a failure mode to a Celery task that retries anyway; INT8 XLM-R on CPU comfortably meets 2 s per doc. What was actually *lost* was the measurement, not the architecture — so Session 70 added per-call `latency_ms` logging in `classify_gazette` (visible in worker logs; p95 computable from logs or a later probe metric). Rollback/deploy DoDs map to: artifact-directory versioning (`onnx/v1`, `v2`, …) + `promotion.py` canary. Revisit Fly only if Phase-5 retraining makes model swaps frequent or volume grows 100×.

## Gap #5 — Classifier readiness signal ✅ IMPLEMENTED

`classifier_service.classifier_status()` → `no_model` (empty/missing `$M1_MODEL_ONNX_DIR` — the *expected* state until Stage E, worded to say "change_category is NOT being model-populated") | `ready` | `load_error` (artifact present, engine broken — a deploy bug, not an expected state). Wired as a `classifier` component into `app/m1/health.py`, so it surfaces automatically at worker boot, `GET /admin/m1/pipeline/health`, and container start ([[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/16_PHASE2_RUNTIME_DEPS_PLAN]] surfaces). Informational — never fails overall `ok` (the extraction runtime is healthy without a model). Portal tile = the same small frontend slice as the Phase-2 health banner.

## Gap #6 — Review queue ✅ BACKEND IMPLEMENTED, UI specced

Backend (in `admin_pipeline.py`): `GET /admin/m1/pipeline/classifier-review` — paginated, `status='classified' AND confidence < MIN_CONFIDENCE AND NOT expert_verified AND is_active`, lowest confidence first, returns the threshold so the UI needn't hardcode it. `POST …/{id}/override` — admin sets the category (confirming the model's own guess = same call), flips `classification_source='expert'` + `expert_verified=TRUE` (which `classify_gazette` already respects on re-runs), audits with old→new pair.

UI slice (14_M1_2, frontend follow-up): table mirroring the metadata-review pattern — columns gazette#/title/predicted category/confidence bar; row expands to `classification_chunk` text; category dropdown (taxonomy from `labels.py`) + Confirm button → override endpoint. Empty state must distinguish "queue empty" from "classifier: no model loaded" (read the health endpoint).

## Gap #7 — Reproducible training environment

1. `enigmatrix-ml/pyproject.toml`: `[project.optional-dependencies] training = [torch, transformers, peft, accelerate, onnx, onnxruntime]` with **pinned versions**, locked (`uv lock`). The API image keeps excluding it — correct and unchanged.
2. `enigmatrix-ml/TRAINING.md`: GPU requirements (fits a T4/16 GB with LoRA + fp16), `uv sync --extra training`, the Stage C–E commands verbatim, expected wall-times, artifact upload step.
3. Optional `Dockerfile.train` (CUDA base + the extra) for a rentable GPU box; not CI — training is launched by a human against gold data.
4. Reproducibility invariants already in code (keep them): `set_seed` 3-seed loop, model-registry hash written by `train_xlmr.py`, temporal split determinism from `data.py`. Record the winning run's hash in the tracker next to the κ evidence.
5. Local smoke evidence: `C:\Reasearch\xyz\storage\models\m1\xlmr_lora_smoke\model_registry.json` was written from one seed/one epoch on a tiny smoke split. Treat it as an environment check only; do not export it to ONNX or use it in RQ1.

## Verification of Session 70's code (deferred to user)

1. `alembic upgrade head` → check backfill: `SELECT classification_source, count(*) FROM m1_regulations GROUP BY 1` — heuristic ≈ the F-199 corpus, expert = verified rows, NULL = never-categorised.
2. `python -m app.m1.health` → `classifier: no_model` with the "NOT being model-populated" wording.
3. `GET /admin/m1/pipeline/classifier-review` → empty-but-valid page with `threshold: 0.55`.
4. Override endpoint on a test row → category set, source='expert', audit row `m1_regulation.classifier_review.override` with old/new.
5. `pytest`, `graphify update .`.
