---
tags: [m1, phase-2, alignment, audit, code-review]
date: 2026-05-23
status: blocking for slice 4
---

# 01 — Alignment Audit: Uploaded Plan vs Live Codebase

> This file lists every concrete drift between the six uploaded planning documents (`00_Phase2_Master_Plan.md` through `05_Build_Sequence_and_Risks.md`) and the live xyz codebase as of commit `f9854d59` (knowledge-graph snapshot) + the Session-57 vault sync. Each finding has a severity, the offending location in the upload, the reality in the codebase, and the fix that lands in this upgrade plan.
>
> **The single most important takeaway:** the proposed `LegacyV1Profile.extract()` code in `03_Extraction_Profiles_System.md §The legacy adapter` would crash at runtime because six of its function references do not match the actual exports. The corrected adapter is included in [05_Slice4_Extraction_Profile_Registry](05_Slice4_Extraction_Profile_Registry.md).

## Severity scale

- 🔴 **Blocker** — the proposal as written cannot ship; code must be rewritten.
- 🟠 **Will-break-on-deploy** — proposal looks plausible but will fail in CI / migrate / runtime.
- 🟡 **Convention drift** — proposal violates a documented project rule but won't crash.
- 🟢 **Refinement** — proposal is fine, this upgrade just sharpens it.

---

## A. Adapter API mismatches (🔴 blocker)

### A.1 `classify_pdf()` returns a Literal, not a dict

**Upload says** (file 03, lines 99–106):
```python
classification = pdf_classifier.classify_pdf(pdf_path)
if classification["type"] == "text_pdf":
    text = text_extractors.extract_with_pymupdf(pdf_path)
elif classification["type"] == "hybrid":
    text = text_extractors.extract_with_pdfplumber(pdf_path)
else:
    text = ocr.extract_with_tesseract(pdf_path)
```

**Codebase reality** (`enigmatrix-ml/m1/extraction/pdf_classifier.py`, Session 28 / F-149):
```python
def classify_pdf(pdf_path: PdfSource) -> PdfType:
    """Return one of 'text_pdf' | 'hybrid' | 'scanned' per §2.4."""
```

`PdfType` is `Literal['text_pdf','hybrid','scanned']`. There is no `.type`, no `.confidence`, no `.page_count` key.

**Fix:** use the string directly. Compute `page_count` separately via `fitz.open(path).page_count` if needed.

### A.2 Extractor function names

**Upload says:** `extract_with_pymupdf`, `extract_with_pdfplumber`, `ocr.extract_with_tesseract`.
**Codebase reality** (`enigmatrix-ml/m1/extraction/text_extractors.py` + `ocr.py`):
- `extract_pymupdf(pdf_path)` → `str`
- `extract_pymupdf_per_page(pdf_path)` → `list[PageResult]`
- `extract_pdfplumber(pdf_path)` → `str`
- `extract_with_chain(pdf_path, *, enable_ocr_fallback=True)` → `ExtractedText` (the orchestrator)
- `extract_tesseract(pdf_path)` and `extract_tesseract_full(pdf_path)`

**Fix:** drop the `with_` prefix. (And consider routing through `extract_with_chain` instead of branching by hand — it already implements the legacy decision tree.)

### A.3 Language detection signature

**Upload says:**
```python
lang, lang_conf = language_detection.detect_language(text.text)
if lang == "si_legacy": ...
```

**Codebase reality** (`enigmatrix-ml/m1/extraction/language_detection.py`):
```python
def detect_document_language(text: str) -> LanguageDetection: ...
# LanguageDetection is a dataclass with .language ('eng'|'sin'|'tam'|'unknown') and .confidence
```

There is no `si_legacy` return code. Wijesekara detection is a **separate** heuristic — `is_wijesekara_encoded(text) -> bool` — that runs alongside language detection, not as a return value of it.

**Fix:** call `detect_document_language(text)` to get language + confidence, then `is_wijesekara_encoded(text)` to decide whether to call `convert_wijesekara`.

### A.4 Wijesekara converter call

**Upload says:** `wijesekara.convert(text.text)`.
**Codebase reality** (`enigmatrix-ml/m1/extraction/wijesekara.py` + `__init__.py` re-export):
- `wijesekara_to_unicode(text: str) -> str` (canonical)
- `convert_wijesekara(text: str) -> str` (alias)

**Fix:** import either, not `wijesekara.convert`.

### A.5 `preprocess_gazette` signature

**Upload says:** `preprocess_gazette(text_str, regulation_key, None)`.
**Codebase reality** (`enigmatrix-ml/m1/preprocessing/__init__.py`):
```python
def preprocess_gazette(raw_text, *, regulation_id, published_date) -> PreprocessedGazette: ...
```
Two keyword-only arguments. Positional call will raise `TypeError: missing required keyword arguments`.

**Fix:** call as `preprocess_gazette(text_str, regulation_id=regulation_key, published_date=None)`.

### A.6 `ExtractedText` shape

**Upload assumes** `text.text` (a `.text` attribute on the return of `extract_with_pymupdf`).
**Codebase reality:** `extract_pymupdf` returns a plain `str`. `extract_with_chain` returns the `ExtractedText` dataclass with a `.full_text` attribute and a `.pages: list[PageResult]` attribute.

**Fix:** if you want a single string, call `extract_pymupdf` and use the return value directly. If you want the per-page detail, call `extract_with_chain` and read `.full_text` / `.pages`.

---

## B. Migration numbering (🟠 will-break-on-deploy)

**Upload says** the new migrations are `010_m1_datasets_versioning.py`, `011_m1_extraction_profiles.py`, `012_m1_measurement.py`.

**Codebase reality** (`enigmatrix-backend/alembic/versions/`):
- Convention is `YYYYMMDDNNNN_<short_name>.py`
- Current tip (latest revision): `202605300001_merge_gazette_items_and_extraction_runs.py`
- Alembic chain has 22 migrations all using this format

**Fix:** rename in the order they ship in slices 3 / 4 / 5:

| Slice | Filename | Down-revision |
|---|---|---|
| 3 | `202605240002_m1_datasets_versioning.py` | `202605300001_merge_gazette_items_and_extraction_runs` |
| 4 | `202605240003_m1_extraction_profiles.py` | `202605240002_m1_datasets_versioning` |
| 5 | `202605240004_m1_measurement.py` | `202605240003_m1_extraction_profiles` |

(Bump the trailing date if you don't ship slices 3–5 on the same day. The middle four digits `0002`/`0003`/`0004` are sequence within the date.)

---

## C. Storage path (🟡 convention drift)

**Upload says** `storage/m1/raw/<source_id>/<slug>.pdf`.

**Codebase reality** (Session 38 / F-161 + Session 54 / F-185–F-192 + Railway `STORAGE_LOCAL_PATH`):
```
storage/m1/raw/<source_id>/YYYY/MM/<slug>.pdf
```
Partitioned by year + month. On Railway, mounted at `/data/storage`.

**Fix:** every path reference uses the partitioned form. `LegacyV1Profile.extract` accepts an absolute path passed in by the dispatcher, so the profile itself does not need to know the layout — but slice 4's scope-resolver does, and so does slice 8's backfill.

---

## D. Table-name collisions (🟢 refinement)

**Upload mentions** `m1_extraction_runs` only obliquely.

**Codebase reality:** `m1_extraction_runs` already exists (migration `202605210002`, Session 54, F-185 → F-192). It is the **trigger-run audit log** (one row per `POST /api/v1/admin/m1/extraction/trigger`), not a profile registry and not a dataset version.

**Fix:** keep all three tables distinct:

| Table | Purpose | Migration |
|---|---|---|
| `m1_extraction_runs` (existing) | One row per trigger call. Tracks Celery task id, source_id, date range, status. | `202605210002` |
| `m1_extraction_profiles` (new, slice 4) | One row per named profile (`legacy_v1`, `page_routing_v1`, …). | `202605240003` |
| `m1_dataset_versions.extraction_run_id` (FK, new, slice 4) | Links an `extraction_run` to the audit row that triggered it. | inside `202605240002` |

This gives you full provenance: `dataset version v3 was produced by run UUID-X, which was triggered by user Y at time Z with profile P`.

---

## E. The `audit_log` rule (🟡 convention drift)

**Upload is silent on `audit_log`** for the new admin actions (Excel upload, version seal, ground-truth promotion, profile activation, measurement-run trigger, version retire).

**Codebase rule** (from `AGENTS.md`):
> All admin actions write to `audit_log` via `audit_service.record()` (Community 30). Never bypass.

**Fix:** every new admin endpoint in slices 3–6 records to `audit_log`. The verb taxonomy:

| Endpoint | Audit action |
|---|---|
| `POST /api/v1/m1/datasets/{id}/versions/upload` | `m1.dataset.version.upload` |
| `POST /api/v1/m1/datasets/{id}/versions/{vid}/seal` | `m1.dataset.version.seal` |
| `POST /api/v1/m1/datasets/{id}/promote-to-ground-truth` | `m1.dataset.promote_ground_truth` |
| `DELETE /api/v1/m1/datasets/{id}/versions/{vid}/retire` | `m1.dataset.version.retire` |
| `POST /api/v1/m1/extraction-profiles/{id}/activate` | `m1.profile.activate` |
| `POST /api/v1/m1/extractions/run` | `m1.extraction.run.start` |
| `POST /api/v1/m1/measurements/run` | `m1.measurement.run.start` |

Each audit row carries `actor_user_id`, `verb`, `target_type`, `target_id`, `request_id`, and a small JSONB diff (e.g. "from old ground-truth dataset X to new ground-truth dataset Y").

---

## F. i18n (🟡 convention drift)

**Upload UI specs** use English strings inline.

**Codebase rule** (from `AGENTS.md`): every user-facing string must have EN/SI/TA translations via `next-intl`.

**Fix:** every UI label, button, badge, tooltip, and error message in slices 3 / 4 / 6 lives in `frontend/messages/{en,si,ta}.json` under a `m1.phase2.*` namespace. The translation work is small (≈ 80 strings) and can be done in parallel with the React work. If a Sinhala or Tamil string is genuinely unknown at PR time, the message file holds the English string with a `// TODO(translation)` comment, and a separate slice-8 task sweeps them.

---

## G. Progress UI: SSE, not polling-from-scratch (🟢 refinement)

**Upload UI** invents fresh polling endpoints for extraction-run and measurement-run progress.

**Codebase reality** (Session 57 / F-193–F-198 + Session 42 / F-169):
- The vault has chokidar + SSE at `/api/vault/stream` for file changes.
- The existing `/admin/m1/extraction/extraction` page polls `/api/v1/admin/m1/extraction/progress` every 5 s via TanStack Query, pausing when the tab is hidden.

**Fix:** reuse both:
- The new `/admin/m1/extractions/runs/{id}` page uses the same TanStack Query polling pattern (`POST /run` returns the run id; `GET /run/{id}/progress` polled every 5 s).
- The new measurement-run page does the same against `GET /measurements/{id}/progress`.
- The vault SSE channel can ALSO carry pipeline events (server emits `{kind: 'extraction_progress', run_id, completed, total}`) — slice 6 wires this as an enhancement, not the default.

---

## H. Aiven connection-pool math (🔴 blocker for slice 4)

**Upload says** "the dispatcher creates a Celery group, one subtask per PDF."

**Codebase math** (from `ENIGMATRIX_MASTER_CONTEXT.md §10.7`):
- Aiven entry tier: ~20 max connections
- `celery --concurrency=2` → 2 fork workers × 3 conn slots = 6
- uvicorn: ~3 conn slots
- `AuditMiddleware._write_passive_log` opens a fresh `SessionLocal()` per request via detached `asyncio.create_task` — invisible always-on consumer.

A Celery group of 400 PDF subtasks scheduled at once would happily try to open 400 DB connections. On Aiven, you would see `OperationalError: too many connections` within seconds.

**Fix:**
- `run_extraction_with_profile` dispatches **batches of 8**, not a single 400-element group.
- Each subtask opens one DB session via the worker's pool (`pool_size=1, max_overflow=2, pool_timeout=10`).
- The dispatcher tracks completion via a Redis counter and starts the next batch when the prior one drains.
- A future Phase 3 step can revisit this if/when we move off Aiven entry tier.

---

## I. PDF storage references are not always available (🟢 refinement)

**Upload assumes** every regulation has a downloadable PDF at `raw_pdf_path`.

**Codebase reality:** new spider rows (post-Session 55 / `m1_gazette_items` migration `202605290001`) **do not** populate `m1_regulations.raw_pdf_path` — that field is legacy. The actual PDF is referenced by `m1_gazette_items.download_url` (web URL, no local cache) and may need to be re-fetched.

**Fix:** the dispatcher in slice 4 resolves the PDF path as:
```
storage/m1/raw/<source_id>/<YYYY>/<MM>/<slug>.pdf  if the file is present locally
else download from m1_gazette_items.download_url and cache there
```
A helper `app/services/m1_pdf_resolver.py:resolve_pdf_path(regulation_id) -> Path` encapsulates this. If neither path resolves, the subtask fails with `validation_errors=['pdf_unavailable']` and the row's status becomes `extraction_failed`.

---

## J. Confidence scoring for `legacy_v1` (🟢 refinement)

**Upload's calibration plot** (file 04 §dashboard) requires per-regulation confidence.

**Codebase reality:** `legacy_v1` has classifier confidence (from `classify_pdf` internals) and language-detection confidence, but no per-field confidence. The dashboard's calibration plot is meaningless for `legacy_v1`.

**Fix:**
- The `confidence` dict in `ExtractedRegulation` carries only the two signals `legacy_v1` actually produces.
- The measurement dashboard's calibration plot renders only when the candidate version has ≥ 1 per-field confidence value. Otherwise it shows the message: *"Calibration plot unavailable — this profile does not produce per-field confidence."*
- `page_routing_v1` and `wijesekara_routing_v1` (slice 7) produce per-page confidence; that's where the calibration plot starts being interpretable.

---

## K. Excel security (🟢 refinement; missing from upload)

**Codebase reality:** there is no upload security policy today. Excel upload is a new attack surface.

**Fix:** slice 3 ships:
- 50 MB hard size cap (`UploadFile.size` check before reading).
- MIME validation (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` only).
- File extension on a hard whitelist (`.xlsx`, `.csv`; `.xlsm` rejected).
- `openpyxl` opened with `read_only=True, data_only=True` (no formula evaluation).
- ClamAV scan in a follow-up slice (deferred to slice 8 polish).
- Audit row per upload (see section E).

---

## L. Idempotency (🟢 refinement)

**Upload is silent on** what happens if the same Excel is uploaded twice while the first is still parsing.

**Fix:** each upload computes the SHA-256 of the file bytes during the storage step; if the dataset's most recent `frozen_at` version has the same SHA, the new version is rejected with a 409 Conflict (`"version_already_exists"`). If the previous version is still being parsed (frozen_at is null), the new upload returns 423 Locked (`"upload_in_progress"`).

---

## M. Plan-folder location (🟢 refinement)

**Upload assumes** documents are dropped somewhere.

**Codebase reality:** the vault has `08-Findings-Log/plans/<date>_<slug>.md` for short-form plans; the repo has `enigmatrix-docs/plans/<date>_<slug>/` for long-form plans (Session 57 introduced this convention). Module-specific step-by-step setup files live at `02-Research-Modules/1 Module-1-Awareness-Gap/planned-for-development/`.

**Fix:** this upgrade plan lives at:
- `C:\sme\08-Findings-Log\plans\2026-05-23_M1_Phase2_Upgrade_Plan\` (vault, source of truth)
- `C:\Reasearch\xyz\enigmatrix-docs\plans\2026-05-23_M1_Phase2_Upgrade_Plan\` (repo mirror, for the `/admin/m1/knowledge` portal)

Per-slice setup files (the hands-on "run these commands in this order" guides) are dropped into `02-Research-Modules/1 Module-1-Awareness-Gap/planned-for-development/<N>_setup.md` as each slice ships, following the existing naming pattern.

---

## N. What this audit changed in the original plan's deliverables

| Original | Upgraded | Rationale |
|---|---|---|
| `010_m1_datasets_versioning.py` | `202605240002_m1_datasets_versioning.py` | Alembic naming convention. |
| `LegacyV1Profile.extract` (uploaded) | corrected adapter in slice 4 | API mismatch on 6 functions; would crash. |
| Bare polling for run progress | Reuse TanStack Query 5 s polling + opt-in SSE | Pattern already in production. |
| 400-element Celery group | Batches of 8 with Redis counter | Aiven 20-conn budget. |
| No `audit_log` rows on Phase 2 mutations | Every admin endpoint records via `audit_service.record()` | Project rule from `AGENTS.md`. |
| English strings in UI specs | `next-intl` keys in `m1.phase2.*` namespace, EN/SI/TA | Project rule. |
| Confidence-required calibration plot | Plot hidden when candidate has no confidence | Honesty about `legacy_v1`. |
| `storage/m1/raw/<src>/<slug>.pdf` | `storage/m1/raw/<src>/YYYY/MM/<slug>.pdf` | Production layout. |
| Implicit re-fetch | Explicit `m1_pdf_resolver.resolve_pdf_path` helper | Web vs disk fallback. |
| No upload security | 50 MB cap + MIME whitelist + audit row | New attack surface. |
| No idempotency for Excel upload | SHA-256 + 409/423 responses | Concurrent-upload safety. |

The slice files (`02` through `09`) carry all of these corrections inline; this audit file exists so reviewers can see the rationale.
