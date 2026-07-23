# Module 1 — Phase 3 (Annotation + Classification): Complete Analysis

> Single-file analysis of **Phase 3 — Annotation + Classification (BUILD_07 §C–D + BUILD_11)** *only*: scope, technologies, what is actually built vs. not-yet-executed across annotation → training → export → inference, the full data journey, and the approaches missed. Grounded in the live codebase (`enigmatrix-ml/m1/model`, `m1/data`, backend `app/m1/tasks/classify_gazette.py` + `services/classifier_service.py`) and the vault (`E:\Obsidian\sme` — `16_M1_Development_Roadmap.md §Phase 3`, `FEATURES.md` F-199/F-216–F-243, STATUS 2026-06-28).
>
> Generated 2026-07-18; **gap-closure status refreshed 2026-07-21 (Session 70)**. **Honest status: Phase 3 is *code-complete but not executed*.** The whole train→eval→ONNX→classify chain is written and wired, but no model has been trained, so the classifier pipeline is a wired no-op. The code-addressable gaps around that inert core (#3, #4-measurement, #5, #6-backend) are now closed; the critical path (#1 train, #2 gold labels) is human/GPU work with a recorded-gate runbook. Details below.

---

## 0. The one-paragraph truth

Every module of Phase 3 exists as **real code** — the XLM-R + LoRA dual-head model (`architecture.py`), the 3-seed training loop (`train_xlmr.py`), slice evaluation (`eval.py`), ONNX export (`export_onnx.py`), the inference engine (`inference.py`), and the backend `classify_gazette` task that auto-chains after preprocessing. But three things have **not happened**: (1) the gold-standard annotation set was never finished through Label Studio + IAA; (2) the model was never trained (no checkpoint, and `storage/models/m1/onnx/v1` does not exist); (3) nothing is deployed to Fly.io — and, per the Session-70 decision, **nothing should be**: serving is deliberately in-process ONNX. So a gazette flows `preprocessed → classify_gazette.delay() → classifier_service` and then **fails to load a model** — but that state is now *visible* (`classifier: no_model` in the health check) rather than silently swallowed. The 800-PDF corpus that exists (F-199) was classified by a **regex/heuristic** statute matcher, *not* the XLM-R model, and is now explicitly marked `classification_source='heuristic'`. Phase 3 is therefore ~"built, instrumented, not yet trained."

---

## 1. What Phase 3 is (scope + goal)

**Goal (roadmap):** the model classifies new gazettes at **macro-F1 ≥ 0.92** and serves predictions via **ONNX** (roadmap said Fly.io; amended to in-process ONNX in Session 70), auto-populating `m1_regulations.change_category` + `affected_sectors[]` + `confidence`.

| Step | Deliverable | Real status |
|---|---|---|
| **3a** | Label Studio config + 20-doc calibration set; annotators pass κ ≥ 0.80 | 🟡 config + calibration built; annotation env stood up (`mydata/`, untracked, F-243); κ test not recorded → runbook Stage A |
| **3b** | `sample_for_labeling.py` — 200 stratified + 40 k-means + 10 minority | 🟢 `m1/data/samplers.py` + script; `batch_01` demo produced |
| **3c** | Iterate to 800 gold labels w/ active learning; IAA ≥ 0.75 κ | 🟡 AL baseline coded (`baselines.py`); 800-PDF corpus exists but **heuristically** classified (F-199), not gold-annotated → runbook Stage B |
| **3d** | Train XLM-R + LoRA; 3-seed macro-F1 ≥ 0.92 | 🟡 **code complete** (`architecture.py`, `train_xlmr.py`) — **never trained** → runbook Stage C |
| **3e** | Eval + slice analysis (lang/quarter/length/method) | 🟡 `eval.py` exists — **not run** (no model) → runbook Stage D |
| **3f** | ONNX export + deploy; INT8 within 1.5 pp; p95 ≤ 2 s | 🟡 `export_onnx.py` + `inference.py` + backend wiring exist — **no artifact**; serving is local in-process ONNX (decided, not a divergence) → runbook Stage E |

---

## 2. Technologies used in Phase 3

### Used (as written code)
| Technology | Layer | Phase-3 role |
|---|---|---|
| **XLM-RoBERTa + LoRA (PEFT) + PyTorch** | ML | `GazetteClassifier` — CLS-pooled XLM-R + LoRA adapters + **dual heads** (12-way category single-label, 10-way sector multi-label) |
| **scikit-learn + scipy** | ML | TF-IDF + LR **active-learning baseline** (`baselines.py`), k-means topical diversity sampling (`samplers.py`) |
| **ONNX Runtime** | Serving | `GazetteInference` CPU INT8 engine (`inference.py`), loaded by `classifier_service` |
| **Label Studio** | Annotation | gold-label project XML + calibration set; `mydata/` instance stood up |
| **Celery** | Queue | `classify_gazette_task` (auto-chained after `preprocess_gazette`); per-call `latency_ms` logged (Session 70) |
| **transformers tokenizer** | ML/prep | XLM-R tokenizer (chunking + training) |
| **pdfplumber + regex** | interim | F-199 one-shot heuristic classification of 800 PDFs (**not** the XLM-R model; now `classification_source='heuristic'`) |

### Not yet exercised
The actual **training run**, quantization validation, and the review-queue *UI* (backend is done). `torch/transformers/peft` are an optional `training` extra, imported lazily — the production API image doesn't ship them (correct and unchanged; see gap #7).

---

## 3. Step-by-step: planned vs. built (with code files)

### 3a — Annotation infra (🟡)
Label Studio project XML + `research/data/calibration_set_v1.csv` (20 reference docs across 12 categories × EN/SI/TA + edge cases). Annotation environment (`mydata/`) stood up but untracked (F-243). **Gap:** annotator recruitment + first-attempt κ ≥ 0.80 not recorded → [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/19_PHASE3_GAP_CLOSURE_PLAN]] Stage A gives the κ-gated runbook that records the matrix to `FEATURES.md`.

### 3b — Sampling (🟢)
`enigmatrix-ml/m1/data/samplers.py`: `stratified_sample` (year × language), `kmeans_diversity_sample` (TF-IDF + MiniBatchKMeans), `find_minority_candidates`, `select_uncertainty_batch` (margin AL), `sample_for_labeling` (200+40+10). Driven by `scripts/sample_for_labeling.py` (DB or `--demo`). `batch_01.csv` produced.

### 3c — 800 labels + active learning (🟡)
AL baseline in `m1/model/baselines.py` (`ALBaseline`/`ProductionBaseline`, TF-IDF+LR). **The 800-PDF corpus that exists (F-199, Session 56) is heuristic** — `pdfplumber` + a regex/statute classifier (`outputs/build_csv.py`) wrote `m1_regulations` CSVs. That is **seed/interim data, not gold annotation** and not model output — now mechanically separable via `classification_source='heuristic'` (gap #3), so the gold exporter excludes it. True gold labeling (Label Studio + dual-annotation κ) is the runbook Stage B.

### 3d — Train XLM-R + LoRA (🟡 code-complete, unrun)
`m1/model/architecture.py` — `GazetteClassifier` (peft `get_peft_model` + `category_head` 12 + `sector_head` 10, `compute_loss`). `m1/model/train_xlmr.py` — real 3-seed loop: `_GazetteDS` DataLoader, `set_seed`, AdamW, `_macro_f1`, epochs/fp16, temporal split, writes model-registry hash. `data.py` (parquet splits), `config.py` (`ModelConfig`: LoRA r, lr, epochs), `labels.py` (taxonomy). **Never executed** — no gold data, no checkpoint.

### 3e — Eval + slices (🟡 unrun)
`m1/model/eval.py` (122 lines) — per-language / per-quarter / per-length / per-extraction-method slices, confidence-bucket monotonicity. No results (no model). Stage D of the runbook adds two watch-items: SI/TA slice F1 (leaking Wijesekara-era text quality — cross-check the [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/17_PHASE2_TRILINGUAL_AUTOCHAIN_PLAN]] backfill) and the extraction_method slice (OCR CER as binding constraint).

### 3f — ONNX export + serving (🟡 wired, no artifact)
`m1/model/export_onnx.py` + `inference.py` (`GazetteInference` ONNX engine) + `promotion.py` (canary/promotion). Backend `app/m1/services/classifier_service.py` loads ONNX from `M1_MODEL_ONNX_DIR` (default `storage/models/m1/onnx/v1`) **in-process** — a **deliberate decision** (Session 70), not an accidental divergence. `app/m1/tasks/classify_gazette.py` writes `change_category` + `classifier_confidence` + `classification_source='model'`, `preprocessed → classified`, logs `latency_ms`, flags `< 0.55` for the review queue, and never overwrites `expert_verified` rows. **No ONNX file on disk yet**, so the engine can't load — a state `classifier_status()` reports as `no_model`.

---

## 4. How it was developed (stages)

- **S60–61 / F-216–F-220** — Label Studio config, calibration set, `samplers.py`, `sample_for_labeling.py` (3a+3b).
- **S56 / F-199** — parallel Cowork data-population: 800 raw gazette PDFs extracted + heuristically classified (seed data, not the model path).
- Model package (`architecture/train_xlmr/eval/export_onnx/inference/baselines/promotion`) authored and the backend `classify_gazette` + `classifier_service` + DB migration `202606300001_m1_classifier_confidence` wired — the *scaffolding* for 3d–3f.
- **S73 / F-243** — doc sync flags the `mydata/` Label Studio env as stood up but untracked; higher-level status docs added (`2026-07-15_Phase3-5_Build_Addendum`).
- **S70 (2026-07-21) — gap closure**: `classification_source` marker (`202607210005`), classifier readiness in health, backend classifier-review queue + override endpoint, in-process-ONNX decision + `latency_ms` logging; critical-path runbook authored. See [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/19_PHASE3_GAP_CLOSURE_PLAN]].

---

## 5. Verification present today

- Unit-level: model modules import and construct (with the `training` extra); `samplers.py` demo produces a batch; `eval.py` slice functions unit-tested on synthetic data.
- Session-70 code checks (deferred to user): `alembic upgrade head` + `classification_source` backfill counts; `python -m app.m1.health` → `classifier: no_model`; `GET /admin/m1/pipeline/classifier-review` empty-but-valid with `threshold: 0.55`; override endpoint sets source='expert' + audit row.
- **Absent:** an end-to-end training run hitting the ≥ 0.92 macro-F1 DoD; per-language F1 (EN ≥ 0.93 / SI ≥ 0.88 / TA ≥ 0.86); INT8-vs-FP32 within 1.5 pp; p95 ≤ 2 s measured on a real artifact; a real `classify_gazette` producing a non-null `change_category` from the XLM-R model.

---

## 6. Gaps & missed approaches (the analytical part)

1. **The model was never trained → the classifier pipeline is inert.** `classify_gazette` runs, `classifier_service` tries to load `storage/models/m1/onnx/v1`, fails — but no `change_category` is ever written by the model. This is the single blocking gap: **finish gold labels → train → export → drop the ONNX artifact.** → 📋 runbook Stages A–E.
2. **Gold annotation not completed / not κ-gated in the tracker.** The IAA ≥ 0.75 κ gate (3c) and the 3a calibration κ ≥ 0.80 have no recorded pass. → 📋 every gate in the runbook now names where its evidence is recorded.
3. **Heuristic corpus can be mistaken for model output.** F-199's 800 rows are regex-classified; downstream analytics reading `change_category` without distinguishing "heuristic seed" from "model prediction" would be biased. → ✅ **Closed (Session 70):** `classification_source` ('heuristic'|'model'|'expert'), migration `202607210005` with backfill; **analytics rule: every consumer of `change_category` filters/facets by `classification_source`**, gold exporters exclude heuristic mechanically.
4. **Serving diverges from the plan.** Local in-process ONNX in the Celery worker instead of a Fly.io service. → ✅ **Decided (Session 70):** amend the DoD to in-process ONNX (worker already ships the runtime; ~dozens/day never queues; a network hop only adds a failure mode). What was lost was the *measurement*, now restored via per-call `latency_ms` logging; deploy/rollback DoDs map to `onnx/vN` versioning + `promotion.py` canary. Revisit Fly only at 100× volume.
5. **Silent-failure ergonomics.** Swallowing the missing-model error is right for resilience but hid that classification does nothing. → ✅ **Closed (Session 70):** `classifier_status()` → `no_model`|`ready`|`load_error`, wired into `app/m1/health.py`, surfaced at worker boot / `/admin/m1/pipeline/health` / container start.
6. **Review-queue UI deferred.** → ✅ **Backend closed (Session 70):** `GET /admin/m1/pipeline/classifier-review` (paginated, lowest-confidence first, returns the threshold) + audited `POST …/{id}/override` (sets category, `classification_source='expert'`, `expert_verified=TRUE`). The triage UI (`14_M1_2`) remains a frontend slice, specced in the plan.
7. **`training` extra is heavy + optional.** → 📋 pin the `training` extra (`uv lock`), write `TRAINING.md` (GPU reqs, `uv sync --extra training`, Stage C–E commands, artifact upload), optional `Dockerfile.train`; API image keeps excluding it. See [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/19_PHASE3_GAP_CLOSURE_PLAN]] gap #7.

Items 1–2 are the critical path; everything else is now either closed or downstream of having a trained model.

> **Session 70 status table (2026-07-21)** — from [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/19_PHASE3_GAP_CLOSURE_PLAN]]:
>
> | # | Gap | Status |
> |---|---|---|
> | 1 | Model never trained — pipeline inert | 📋 runbook (critical path) |
> | 2 | Gold annotation / κ not gated | 📋 runbook (critical path) |
> | 3 | Heuristic corpus mistakable for model output | ✅ `classification_source` |
> | 4 | Serving diverges from plan | ✅ decided in-process + latency measured |
> | 5 | Silent-failure ergonomics | ✅ classifier readiness in health |
> | 6 | Review-queue UI deferred | ✅ backend done; UI slice specced |
> | 7 | Training env heavy + optional | 📋 pinned extra + TRAINING.md plan |

---

## 7. Traceability (capability → code → doc → F-id)

| Capability | Code path(s) | Doc | F-id |
|---|---|---|---|
| Label Studio config + calibration | `research/data/label_studio_config.xml`, `calibration_set_v1.csv` | `09_M1_Annotation_Guidelines` | F-216 |
| Sampling (stratified/k-means/AL) | `m1/data/samplers.py`, `scripts/sample_for_labeling.py` | `05_M1_1_Sampling_Strategy` | F-217–F-220 |
| AL baseline | `m1/model/baselines.py` | `05_M1 §1.3` | — |
| Model (XLM-R + LoRA dual head) | `m1/model/architecture.py`, `config.py`, `labels.py`, `data.py` | `05_M1_Model_Architecture`, `05_M1_3_LoRA` | — |
| Training (3-seed) | `m1/model/train_xlmr.py` | `06_M1_Training_Evaluation` | — |
| Eval + slices | `m1/model/eval.py` | `06_M1_2_Slice_Analysis` | — |
| ONNX export + inference | `m1/model/export_onnx.py`, `inference.py`, `promotion.py` | `07_M1_1_ONNX_Export` | — |
| Backend classify wiring | `app/m1/tasks/classify_gazette.py`, `app/m1/services/classifier_service.py`, migration `202606300001` | `07_M1_Deployment_Integration` | — |
| classification_source marker | `app/models/regulation.py`, migration `202607210005` | [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/19_PHASE3_GAP_CLOSURE_PLAN]] #3 | S70 |
| Classifier readiness + review queue | `classifier_service.classifier_status`, `app/m1/health.py`, `admin_pipeline.py` | [[02-Research-Modules/1 Module-1-Awareness-Gap/final/works/19_PHASE3_GAP_CLOSURE_PLAN]] #5/#6 | S70 |
| Interim heuristic corpus | `outputs/build_csv.py` (Cowork) | — | F-199 |

---

## 8. Data flow — how data travels through the stages (Phase 3)

Phase 3 has two distinct journeys: an **offline training journey** (labels → model → ONNX artifact) and an **online inference journey** (gazette → prediction → DB → review). The inference journey is wired but dormant until the artifact from the training journey exists.

### 8.0 Inputs / data sources
| Input | Where it enters | Becomes |
|---|---|---|
| Phase-2 `preprocessed` gazettes | `sample_for_labeling.py` reads DB | labelling batches (`batch_NN.csv`) |
| Annotator decisions | Label Studio (`mydata/`) | `gold_standard.csv` (κ-gated) |
| Gold labels | `m1/model/data.py` | parquet train/val/test splits |
| A new `preprocessed` gazette (runtime) | `classify_gazette` task | `change_category` + `classifier_confidence` + `classification_source='model'` on the row |

### 8.1 Offline training journey (ML env, no browser)
```
Phase-2 extracted/preprocessed gazettes (DB)
  → scripts/sample_for_labeling.py → m1/data/samplers.py
        stratified(year×lang) + kmeans_diversity + select_uncertainty_batch(AL)
     → research/data/labeling/batch_NN.csv
  → Label Studio (mydata/) → annotators (12 cat + 10 sector) → dual-annotation κ gate (≥0.80 calib, ≥0.75 IAA)
     → gold_standard.csv  (≥ 20/category, heuristic rows excluded via classification_source)
  → m1/model/data.py → temporal parquet splits
  → m1/model/train_xlmr.py  (XLM-R + LoRA, 3 seeds, AdamW, fp16)  → checkpoint (macro-F1 ≥ 0.92 gate)
  → m1/model/eval.py  (per-language / quarter / length / method slices)
  → m1/model/promotion.py → m1/model/export_onnx.py (+ INT8 quantize, within 1.5 pp gate)
     → storage/models/m1/onnx/v1/*.onnx      ← THE ARTIFACT (does not exist yet; drop, don't rebuild image)
```

### 8.2 Online inference journey (auto-chained; currently dormant)
```
preprocess_gazette (Phase 2 tail)
  → classify_gazette_task.delay(regulation_id)          app/m1/tasks/classify_gazette.py
      (dispatched in try/except — a missing broker/model never breaks preprocessing)
    → classifier_service.classify_text(text or classification_chunk)   app/m1/services/classifier_service.py
        → m1.model.inference.GazetteInference (ONNX, loaded once from storage/models/m1/onnx/v1)
        ← {category, sectors[], confidence, needs_review}
    → UPDATE m1_regulations SET change_category, classifier_confidence,
             classification_source='model', status='classified'   (logs latency_ms)
       (confidence < M1_CLASSIFIER_MIN_CONFIDENCE=0.55 → needs_review=true; expert_verified rows never overwritten)
  → review queue = GET /admin/m1/pipeline/classifier-review
        (status='classified' AND confidence<0.55 AND NOT expert_verified; override endpoint ready; triage UI 14_M1_2 pending)
```
**Today:** the ONNX load fails (no artifact) → `classifier_status()` reports `no_model` (visible in health), and the task logs and returns without writing a model prediction.

### 8.3 Where each stage lives (quick map)
| Stage | Component | Code |
|---|---|---|
| Sample for labelling | ML sampler + CLI | `m1/data/samplers.py`, `scripts/sample_for_labeling.py` |
| Annotate | Label Studio | `research/data/label_studio_config.xml`, `mydata/` |
| Train | XLM-R + LoRA | `m1/model/{architecture,train_xlmr,data,config}.py` |
| Evaluate | slice analysis | `m1/model/eval.py` |
| Export + serve | ONNX (in-process) | `m1/model/{export_onnx,inference,promotion}.py`, `classifier_service.py` |
| Classify (runtime) | Celery task → DB | `app/m1/tasks/classify_gazette.py`, migrations `202606300001`, `202607210005` |
| Readiness + review | health + queue | `classifier_service.classifier_status`, `app/m1/health.py`, `admin_pipeline.py` |

---

*Scope note: this document covers Phase 3 only. Phase 1 → `PHASE1_FOUNDATION_ANALYSIS.md`; Phase 2 → `PHASE2_INGEST_EXTRACTION_ANALYSIS.md`; Phase 4 → `PHASE4_SCHEDULERS_ALERTS_ANALYSIS.md`; Phase 5 → `PHASE5_RESEARCH_FINDINGS_ANALYSIS.md`. Phase 3's classifier pipeline is wired end-to-end and now instrumented (readiness, source marker, review queue, latency) but inert until a trained ONNX artifact exists. Gap-closure companion: `PHASE3_GAP_CLOSURE_PLAN.md`.*
