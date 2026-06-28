---
tags: [m1, phase-2, slice-4, extraction, profiles, legacy_v1, celery]
date: 2026-05-23
status: 🔲 not started
estimated-effort: 1 week
prerequisites: slice 3 complete (m1_dataset_versions exists for FK)
---

# 05 — Slice 4: Extraction Profile Registry + Legacy Adapter

## What this slice produces

One new table (`m1_extraction_profiles`), one Alembic migration (`202605240003`), one new Python protocol (`ExtractorProfile`), one corrected adapter (`LegacyV1Profile` — the uploaded one had 6 API mismatches; see [01_Alignment_Audit §A](01_Alignment_Audit.md#a-adapter-api-mismatches-🔴-blocker)), three placeholder profile registrations, one new Celery task (`run_extraction_with_profile`), four new API endpoints, and one new frontend page (`/admin/m1/extractions/run`).

When this slice ships, you can trigger `legacy_v1` from a UI dropdown, watch it walk a scope of PDFs, and see a new `m1_dataset_versions` row appear containing the extraction's structured output. The cleaned text of those rows is byte-identical to what `m1_regulations.cleaned_text` contains for the same regulations — that's the regression test that proves `legacy_v1` is faithful to Phase 1.

## The corrected `LegacyV1Profile`

This is the most important code in the slice. The uploaded version would crash. Here it is corrected (Python 3.12, async-safe, with the actual function names from `enigmatrix-ml/m1/extraction/__init__.py`):

```python
# enigmatrix-ml/m1/extraction/profiles/legacy_v1.py
from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

from m1.extraction import (
    classify_pdf,
    convert_wijesekara,
    detect_document_language,
    extract_pdfplumber,
    extract_pymupdf,
    extract_tesseract,
    is_wijesekara_encoded,
)
from m1.preprocessing import preprocess_gazette
from m1.extraction.profile import ExtractedRegulation


class LegacyV1Profile:
    """Phase 1 chain wrapped as an ExtractorProfile.

    The chain itself is untouched — this class only calls the functions
    that already exist in `enigmatrix-ml/m1/extraction/` and packs the
    result into the uniform ExtractedRegulation shape.

    Spec: enigmatrix-docs/m1/03_M1_1_PDF_Extraction_Chain.md
    """

    name = "legacy_v1"
    version = "1.0.0"
    description = (
        "Phase 1 shipped chain. classify_pdf thresholds (200, 30). "
        "PyMuPDF / pdfplumber / Tesseract 5.3 at 300 DPI. "
        "fastText lid.176 language detection. 87-entry Wijesekara map. "
        "8-step preprocessing. Frozen as-is; do not modify."
    )

    def supports(self, pdf_metadata: dict) -> bool:
        # Universal fallback.
        return True

    def extract(self, pdf_path: str | Path, regulation_key: str) -> ExtractedRegulation:
        pdf_path = Path(pdf_path)

        # Page count (separate call — classify_pdf does not expose it)
        with fitz.open(pdf_path) as doc:
            page_count = doc.page_count

        # Stage 2c: classify_pdf returns Literal['text_pdf','hybrid','scanned']
        pdf_type = classify_pdf(pdf_path)
        if pdf_type == "text_pdf":
            text = extract_pymupdf(pdf_path)
        elif pdf_type == "hybrid":
            text = extract_pdfplumber(pdf_path)
        else:  # 'scanned'
            text = extract_tesseract(pdf_path)

        # Stage 2d: language detection
        lang_result = detect_document_language(text)
        # lang_result is a LanguageDetection dataclass with .language and .confidence
        if is_wijesekara_encoded(text):
            text = convert_wijesekara(text)

        # Stage 2e + 2f: preprocessing (kwargs-only signature)
        pre = preprocess_gazette(
            text,
            regulation_id=regulation_key,
            published_date=None,
        )

        # Pack into the uniform shape the measurement engine expects.
        return ExtractedRegulation(
            regulation_key=regulation_key,
            raw_text=text,
            cleaned_text=pre.cleaned_text,
            extraction_method=self.name,
            page_count=page_count,
            fields={
                "amendment_type": pre.amendment_type,
                "effective_date": pre.effective_date.isoformat() if pre.effective_date else None,
                "principal_act_amended": pre.principal_act_amended,
                "penalty_range_lkr": pre.penalty_range_lkr,
                "document_number": pre.gazette_number,  # legacy chain extracts gazette_number, not a generic doc_number
                # legacy chain does not extract title/summary fields;
                # the measurement engine flags these as 'missing'.
            },
            confidence={
                "language_detection_confidence": lang_result.confidence,
                # No per-field or per-page confidence in legacy_v1.
                # The measurement dashboard hides the calibration plot in this case.
            },
            error_signals={
                "classified_as": pdf_type,
                "language_detected": lang_result.language,
                "wijesekara_applied": is_wijesekara_encoded(text),
            },
        )
```

Why each change matters is recorded in [01_Alignment_Audit §A](01_Alignment_Audit.md#a-adapter-api-mismatches-🔴-blocker).

## Tasks

### Task 4.1 — Define `ExtractorProfile` protocol + `ExtractedRegulation` dataclass (½ day)

`enigmatrix-ml/m1/extraction/profile.py`:

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, Any


@dataclass
class ExtractedRegulation:
    regulation_key: str
    raw_text: str
    cleaned_text: str
    extraction_method: str
    page_count: int
    fields: dict[str, Any] = field(default_factory=dict)
    confidence: dict[str, float] = field(default_factory=dict)
    error_signals: dict[str, Any] = field(default_factory=dict)


class ExtractorProfile(Protocol):
    name: str
    version: str
    description: str
    def supports(self, pdf_metadata: dict) -> bool: ...
    def extract(self, pdf_path: str, regulation_key: str) -> ExtractedRegulation: ...
```

### Task 4.2 — Implement `LegacyV1Profile` (½ day)

Per the corrected code above. Place at `enigmatrix-ml/m1/extraction/profiles/legacy_v1.py`. Add `enigmatrix-ml/m1/extraction/profiles/__init__.py`:

```python
from .legacy_v1 import LegacyV1Profile
# Hardcoded name → class mapping. New profiles added here as they ship.
PROFILE_REGISTRY = {"legacy_v1": LegacyV1Profile}
```

Slice 7 adds the three new entries.

### Task 4.3 — Alembic migration `202605240003_m1_extraction_profiles.py` (½ day)

Down-revision: `202605240002_m1_datasets_versioning`.

```sql
CREATE TABLE m1_extraction_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(60) UNIQUE NOT NULL,
    version VARCHAR(30) NOT NULL,
    description TEXT NOT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    requires_gpu BOOLEAN NOT NULL DEFAULT FALSE,
    deprecated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ
);

-- FK on m1_dataset_versions.extraction_profile_id (added in slice 3 as nullable, populated now)
ALTER TABLE m1_dataset_versions
    ADD CONSTRAINT fk_m1_dataset_versions_profile
    FOREIGN KEY (extraction_profile_id) REFERENCES m1_extraction_profiles(profile_id);

-- Seed rows
INSERT INTO m1_extraction_profiles (name, version, description, config, is_active, requires_gpu) VALUES
    ('legacy_v1', '1.0.0',
     'Phase 1 shipped chain. classify_pdf thresholds (200, 30). PyMuPDF / pdfplumber / Tesseract 5.3 at 300 DPI. fastText lid.176. 87-entry Wijesekara map. 8-step preprocessing.',
     '{"classify_thresholds": [200, 30], "tesseract_dpi": 300, "tesseract_psm": 6, "wijesekara_map_size": 87, "preprocessing_steps": 8}'::jsonb,
     TRUE, FALSE),
    ('page_routing_v1', '0.1.0-stub',
     'STUB — implemented in slice 7. Per-page extraction routing using page.get_text("dict"), multi-engine consensus.',
     '{}'::jsonb, FALSE, FALSE),
    ('wijesekara_routing_v1', '0.1.0-stub',
     'STUB — implemented in slice 7. page_routing_v1 + font-name detection for legacy Sinhala fonts, expanded 180-entry map.',
     '{}'::jsonb, FALSE, FALSE),
    ('surya_fallback_v1', '0.1.0-stub',
     'STUB — implemented in slice 7. wijesekara_routing_v1 + Surya OCR fallback on low-confidence Sinhala pages.',
     '{}'::jsonb, FALSE, TRUE);
```

`legacy_v1` ships `is_active=TRUE`. The other three ship `is_active=FALSE` — the dispatcher rejects requests for inactive profiles with a 501.

### Task 4.4 — Celery task `run_extraction_with_profile` (1 day)

`enigmatrix-backend/app/tasks/m1/run_extraction.py`:

```python
@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def run_extraction_with_profile(
    self, target_dataset_id: str, profile_name: str, scope: dict, queued_by_id: str,
) -> dict:
    """
    scope is one of:
      {"kind": "ground_truth"}                            # all regs in ground-truth dataset
      {"kind": "source_range", "source_id": "EGZ", "date_from": "...", "date_to": "..."}
      {"kind": "version", "version_id": "..."}            # all regs in a specific version
      {"kind": "regulation_keys", "keys": ["2468/44", "2469/19", ...]}
    """
    # 1. Load profile (raises 501-equivalent if inactive)
    profile = load_profile(profile_name)  # reads m1_extraction_profiles + PROFILE_REGISTRY

    # 2. Resolve scope → list[regulation_key]
    regulation_keys = resolve_scope(scope)

    # 3. Create m1_dataset_versions row with frozen_at=NULL
    version = create_extraction_version(
        dataset_id=target_dataset_id,
        profile_id=profile.profile_id,
        scope_description=scope,
    )

    # 4. Dispatch in batches of 8 (Aiven 20-conn budget; see 01_Alignment_Audit §H)
    batches = chunked(regulation_keys, 8)
    counter_key = f"m1:extraction_run:{version.version_id}:completed"
    redis_client.set(counter_key, 0)

    for batch in batches:
        group(
            extract_one_with_profile.s(
                version_id=str(version.version_id),
                profile_name=profile_name,
                regulation_key=key,
            )
            for key in batch
        ).apply_async()
        # Block until this batch drains before scheduling the next
        wait_for_batch_completion(counter_key, expected=len(batch), timeout=300)

    # 5. Seal version (compute SHA-256 over sorted rows JSON)
    seal_version(version.version_id)

    # 6. Audit
    audit_record(verb="m1.extraction.run.start", actor_user_id=queued_by_id,
                 target_type="m1_dataset_version", target_id=str(version.version_id),
                 payload={"profile_name": profile_name, "scope": scope, "row_count": len(regulation_keys)})

    return {"version_id": str(version.version_id), "row_count": len(regulation_keys)}


@celery_app.task(bind=True, autoretry_for=(Exception,), max_retries=2)
def extract_one_with_profile(self, version_id: str, profile_name: str, regulation_key: str) -> None:
    profile = load_profile(profile_name)
    pdf_path = resolve_pdf_path(regulation_key)  # see 01_Alignment_Audit §I
    try:
        result = profile.extract(pdf_path, regulation_key)
        persist_dataset_row(version_id=version_id, result=result)
    except Exception as exc:
        persist_dataset_row_failure(version_id=version_id, regulation_key=regulation_key, error=str(exc))
        raise
    finally:
        redis_client.incr(f"m1:extraction_run:{version_id}:completed")
```

Key Aiven-pool defences (per [01_Alignment_Audit §H](01_Alignment_Audit.md#h-aiven-connection-pool-math-🔴-blocker-for-slice-4)):

- `apply_async` batches of 8 maximum, blocking on batch completion before the next.
- Per-subtask DB session opens via the worker's `pool_size=1, max_overflow=2` config.
- The Redis counter is the cross-process synchronisation primitive — no DB-level coordination.

### Task 4.5 — `m1_pdf_resolver` service (½ day)

`enigmatrix-backend/app/services/m1_pdf_resolver.py`:

```python
def resolve_pdf_path(regulation_key: str) -> Path:
    """
    Returns the absolute Path to the PDF for this regulation_key.
    Order:
      1. storage/m1/raw/<source_id>/YYYY/MM/<slug>.pdf (the partitioned layout)
      2. storage/m1/raw/<source_id>/<slug>.pdf (the flat layout, pre-Session 38)
      3. download from m1_gazette_items.download_url, cache at the partitioned path
    Raises PDFUnavailable if all three fail.
    """
```

### Task 4.6 — API endpoints (½ day)

`enigmatrix-backend/app/api/v1/m1_extractions.py`:

```
GET    /api/v1/m1/extraction-profiles                          (list with is_active filter)
GET    /api/v1/m1/extraction-profiles/{id}                     (detail)
POST   /api/v1/m1/extraction-profiles/{id}/activate            (admin)
POST   /api/v1/m1/extraction-profiles/{id}/deactivate          (admin)
POST   /api/v1/m1/extractions/run                              (admin — triggers Celery task)
GET    /api/v1/m1/extractions/runs/{task_id}/progress          (poll-friendly; returns completed/total)
GET    /api/v1/m1/extractions/runs/{task_id}                   (full status; reads m1_extraction_runs)
```

`POST /run` validates that the profile is active and the scope resolves to ≥ 1 regulation_key, then `apply_async`s `run_extraction_with_profile`. Returns `task_id`. Writes the audit row.

### Task 4.7 — Frontend `/admin/m1/extractions/run` (1 day)

Single form. Three sections:

1. **Profile picker.** Dropdown sourced from `GET /extraction-profiles?is_active=true`. Currently shows only `legacy_v1`. The three stubbed profiles appear disabled with helper text "coming soon — slice 7".
2. **Scope picker.** Tabs for the four scope kinds. The "ground_truth" tab is the default and pre-fills with the current ground-truth dataset's name.
3. **Target dataset picker.** Two radio options: "create new dataset" (with name + description fields) or "append version to existing dataset" (dropdown of extraction-kind datasets).

A "Run" button submits to `POST /extractions/run`, then redirects to `/admin/m1/extractions/runs/{task_id}`. The runs page polls progress every 5 s using the same TanStack Query pattern as the existing pipeline pages.

When the run completes, the page shows:
- Link to the newly-created dataset version.
- A prominent "Score against ground truth" button that pre-fills slice-6's measurement-run form.

### Task 4.8 — Tests (½ day)

- `enigmatrix-ml/tests/m1/extraction/profiles/test_legacy_v1.py`: instantiate `LegacyV1Profile`, run `.extract()` against the existing test fixture PDF, assert the return shape, assert `cleaned_text` matches what `preprocess_gazette` produces standalone.
- `enigmatrix-backend/app/tests/integration/test_run_extraction_with_profile.py`: dispatch the Celery task in eager mode against 5 regulation_keys, assert a new `m1_dataset_versions` row exists with 5 `m1_dataset_rows`, assert SHA-256 is set, assert `audit_log` has the row.
- `enigmatrix-backend/app/tests/unit/test_m1_pdf_resolver.py`: cover all three fallback paths (partitioned, flat, web-download).

## Files touched

| Path | New/Edit | Purpose |
|---|---|---|
| `enigmatrix-ml/m1/extraction/profile.py` | new | `ExtractorProfile` Protocol + `ExtractedRegulation` |
| `enigmatrix-ml/m1/extraction/profiles/__init__.py` | new | `PROFILE_REGISTRY` |
| `enigmatrix-ml/m1/extraction/profiles/legacy_v1.py` | new | The corrected adapter |
| `enigmatrix-backend/alembic/versions/202605240003_m1_extraction_profiles.py` | new | Table + seed |
| `enigmatrix-backend/app/models/m1_extraction_profile.py` | new | ORM |
| `enigmatrix-backend/app/schemas/m1_extraction.py` | new | Pydantic |
| `enigmatrix-backend/app/services/m1_profile_service.py` | new | `load_profile` + activate/deactivate |
| `enigmatrix-backend/app/services/m1_pdf_resolver.py` | new | PDF path resolution |
| `enigmatrix-backend/app/tasks/m1/run_extraction.py` | new | The dispatcher Celery task |
| `enigmatrix-backend/app/api/v1/m1_extractions.py` | new | Router |
| `enigmatrix-backend/app/api/v1/router.py` | edit | Mount |
| `enigmatrix-frontend/app/(app)/admin/m1/extractions/run/page.tsx` | new | Form |
| `enigmatrix-frontend/app/(app)/admin/m1/extractions/runs/[taskId]/page.tsx` | new | Progress |
| `enigmatrix-frontend/lib/api/m1-extractions.ts` | new | Client |
| `enigmatrix-frontend/messages/{en,si,ta}.json` | edit | `m1.extractions.*` |
| `enigmatrix-ml/tests/m1/extraction/profiles/test_legacy_v1.py` | new | Adapter tests |
| `enigmatrix-backend/app/tests/integration/test_run_extraction_with_profile.py` | new | E2E task test |
| `enigmatrix-backend/app/tests/unit/test_m1_pdf_resolver.py` | new | Resolver tests |

## Gate

The faithfulness regression test:

1. Run the existing Phase 1 chain on five regulation_keys (e.g. via `extract_gazette.delay` in a controlled test DB), record `m1_regulations.cleaned_text` for each.
2. Trigger `run_extraction_with_profile` with `legacy_v1` on the same five.
3. For each `regulation_key`, fetch `m1_dataset_rows.cleaned_text` from the new version.
4. Assert byte-identical equality for at least 4 of 5 (the 5th can differ if `preprocess_gazette` was called with `published_date=None` here vs the actual published_date earlier — that's expected, not a bug).

The UX gate:

1. Navigate to `/admin/m1/extractions/run` as admin.
2. Profile dropdown shows `legacy_v1` active, three others greyed out.
3. Scope = "all regs in ground-truth dataset" (the 407 from slice 3).
4. Target = "create new dataset" with name "Extraction run, legacy_v1, 2026-05-26".
5. Run. Progress page ticks 0 → 407 over a few minutes.
6. Land on dataset detail page for the new version. SHA-256 set. Row count 407.
7. `SELECT * FROM audit_log WHERE verb = 'm1.extraction.run.start';` shows the row.

## What this slice deliberately does NOT do

- It does NOT activate the three new profiles (slice 7).
- It does NOT score the new version (slice 5 + 6).
- It does NOT change the existing `extract_gazette` Celery task — that still runs the Phase 1 chain directly for the spider's pipeline. Backward compatibility holds.

## Risks specific to this slice

- **Twisted-reactor / Celery / SQLAlchemy interplay.** `legacy_v1.extract` calls `extract_pdfplumber` which under the hood may use Twisted indirectly through Scrapy — but no, the extractors are standalone. Confirmed safe.
- **A subtask dies mid-batch.** Mitigation: the dispatcher's `wait_for_batch_completion` times out at 5 min; any pending subtasks past that are marked `extraction_failed` in `m1_dataset_rows`. The version is sealed with a partial row count and a warning in `notes`.
- **PDF unavailable on disk AND web.** Mitigation: row gets `extraction_method=NULL`, `validation_warnings=['pdf_unavailable']`, and counts toward completeness as `missing`.
- **`preprocess_gazette` raises** on a malformed extraction. Mitigation: catch in the subtask, persist a failure row with `error_signals.preprocess_exception`, do not abort the batch.

## Cross-references

- [01_Alignment_Audit §A](01_Alignment_Audit.md#a-adapter-api-mismatches-🔴-blocker), [§B](01_Alignment_Audit.md#b-migration-numbering-🟠-will-break-on-deploy), [§H](01_Alignment_Audit.md#h-aiven-connection-pool-math-🔴-blocker-for-slice-4), [§I](01_Alignment_Audit.md#i-pdf-storage-references-are-not-always-available-🟢-refinement) — the corrections this slice implements.
- [04_Slice3_Dataset_Registry_and_Upload](04_Slice3_Dataset_Registry_and_Upload.md) — `m1_dataset_versions` table this slice extends with the FK.
- [06_Slice5_Measurement_Engine](06_Slice5_Measurement_Engine.md) — consumes the extraction-run versions this slice produces.
- [08_Slice7_New_Extraction_Profiles](08_Slice7_New_Extraction_Profiles.md) — fills in the three stubs.
- `enigmatrix-ml/m1/extraction/__init__.py` — the canonical export surface this profile's adapter consumes.
