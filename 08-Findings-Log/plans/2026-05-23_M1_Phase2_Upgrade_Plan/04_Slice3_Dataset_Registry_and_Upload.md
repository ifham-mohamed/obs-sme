---
tags: [m1, phase-2, slice-3, datasets, versioning, alembic, frontend]
date: 2026-05-23
status: 🔲 not started
estimated-effort: 1 week
prerequisites: slice 1 complete (vocabulary locked)
---

# 04 — Slice 3: Dataset Registry, Versioning, and Excel Upload

## What this slice produces

Three new database tables (`m1_datasets`, `m1_dataset_versions`, `m1_dataset_rows`), one Alembic migration, three Pydantic schemas, one service module (`app/services/m1_dataset_upload.py`), eight new API endpoints under `/api/v1/m1/datasets`, and one new frontend page family (`/admin/m1/datasets/*`). When this slice is done you can upload the canonicalised Excel from slice 1 through a real web form, see the parse summary, confirm, view the version in the database UI, and promote it to ground truth.

Nothing in `m1_regulations` changes. Nothing in the extraction code changes. This slice is purely additive.

## Why this slice is bigger than it looks

Three things make it more than "just an Excel upload form":

1. The version semantics are load-bearing for the rest of Phase 2 — every measurement run references a version, every extraction run produces a version, the comparison UI dereferences a version. Get the API surface wrong here and slice 5 / 6 / 7 inherit pain.
2. The Excel parser has to be tolerant. Real-world Excels have merged cells, misordered columns, sheets that aren't `Sheet1`, dates as numbers vs strings, Sinhala in cells where the column header thinks "English". This slice spends a day on parser robustness.
3. The `is_ground_truth` constraint is a partial unique index in Postgres. Promoting one dataset to ground-truth must atomically demote the previous holder. Get this wrong and you have two ground-truth datasets, the measurement engine picks one arbitrarily, and your numbers become non-reproducible.

## Tasks

### Task 3.1 — Alembic migration `202605240002_m1_datasets_versioning.py` (½ day)

Down-revision: `202605300001_merge_gazette_items_and_extraction_runs` (current tip as of 2026-05-22).

Creates:

```sql
CREATE TABLE m1_datasets (
    dataset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    kind VARCHAR(20) NOT NULL CHECK (kind IN ('manual_excel','extraction_run','expert_review')),
    is_ground_truth BOOLEAN NOT NULL DEFAULT FALSE,
    owner_user_id UUID NOT NULL REFERENCES users(id),
    tags TEXT[] NOT NULL DEFAULT '{}',
    current_version_id UUID,  -- FK added after m1_dataset_versions exists
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ  -- soft-delete column for AGENTS.md convention
);
CREATE UNIQUE INDEX ux_m1_datasets_one_ground_truth ON m1_datasets ((is_ground_truth))
    WHERE is_ground_truth = TRUE;

CREATE TABLE m1_dataset_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES m1_datasets(dataset_id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    source VARCHAR(20) NOT NULL CHECK (source IN ('excel_upload','csv_upload','extraction_run','manual_edit','backfill')),
    extraction_profile_id UUID,  -- FK added in slice 4 when m1_extraction_profiles exists
    extraction_run_id UUID REFERENCES m1_extraction_runs(run_id),  -- existing table
    row_count INTEGER NOT NULL DEFAULT 0,
    content_sha256 CHAR(64),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    frozen_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ,
    UNIQUE (dataset_id, version_number)
);
CREATE INDEX ix_m1_dataset_versions_active ON m1_dataset_versions (dataset_id, version_number DESC)
    WHERE retired_at IS NULL;

ALTER TABLE m1_datasets
    ADD CONSTRAINT fk_m1_datasets_current_version FOREIGN KEY (current_version_id)
    REFERENCES m1_dataset_versions(version_id);

CREATE TABLE m1_dataset_rows (
    row_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID NOT NULL REFERENCES m1_dataset_versions(version_id) ON DELETE CASCADE,
    regulation_key VARCHAR(50) NOT NULL,
    fields JSONB NOT NULL,
    raw_text TEXT,
    cleaned_text TEXT,
    extraction_method VARCHAR(20),
    confidence JSONB,
    error_signals JSONB,
    validation_warnings JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (version_id, regulation_key)
);
CREATE INDEX ix_m1_dataset_rows_key ON m1_dataset_rows (regulation_key);
CREATE INDEX ix_m1_dataset_rows_fields_gin ON m1_dataset_rows USING GIN (fields);
```

`extraction_profile_id` is left without a FK at this stage; slice 4's migration adds the FK after `m1_extraction_profiles` is created.

The `archived_at` column on `m1_datasets` is the soft-delete pattern documented in `AGENTS.md`. `archive_dataset()` / `restore_dataset()` service methods set / clear it.

### Task 3.2 — ORM models (½ day)

In `enigmatrix-backend/app/models/m1_dataset.py`:

```python
class M1Dataset(Base, TimestampMixin):
    __tablename__ = "m1_datasets"
    dataset_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    is_ground_truth: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("m1_dataset_versions.version_id"))
    archived_at: Mapped[datetime | None]
    # relationships
    versions: Mapped[list["M1DatasetVersion"]] = relationship(back_populates="dataset", cascade="all, delete-orphan", foreign_keys="M1DatasetVersion.dataset_id")
    current_version: Mapped["M1DatasetVersion | None"] = relationship(foreign_keys=[current_version_id], post_update=True)

class M1DatasetVersion(Base, TimestampMixin):
    __tablename__ = "m1_dataset_versions"
    # ... per schema above
    rows: Mapped[list["M1DatasetRow"]] = relationship(back_populates="version", cascade="all, delete-orphan")

class M1DatasetRow(Base, TimestampMixin):
    __tablename__ = "m1_dataset_rows"
    # ... per schema above
```

Register in `app/models/__init__.py` so Alembic autogenerate sees them.

### Task 3.3 — Pydantic schemas (½ day)

In `enigmatrix-backend/app/schemas/m1_dataset.py`:

- `DatasetCreateRequest`: `name`, `description`, `kind`, `tags`.
- `DatasetResponse`: full read shape including `version_count`, `current_version_summary`.
- `DatasetVersionResponse`: read shape with `row_count`, `frozen_at`, `content_sha256`.
- `DatasetRowResponse`: read shape with the JSONB `fields` flattened in the response.
- `ExcelUploadResponse`: parse summary with `rows_parsed`, `rows_with_warnings`, `validation_errors[]`, `proposed_version_id`.

All schemas inherit `ConfigDict(from_attributes=True)` for the SQLAlchemy mapping.

### Task 3.4 — Upload service (1 day)

`enigmatrix-backend/app/services/m1_dataset_upload.py` implements the five-step pipeline from the original `02_Datasets_and_Versioning.md`, with the upgrades from [01_Alignment_Audit §K](01_Alignment_Audit.md#k-excel-security-🟢-refinement) and [§L](01_Alignment_Audit.md#l-idempotency-🟢-refinement):

```python
async def upload_excel_version(
    *, dataset_id: UUID, file: UploadFile, owner_user_id: UUID, seal: bool,
    audit: AuditService, db: AsyncSession,
) -> ExcelUploadResponse:
    # 1. Security checks
    if file.size > 50 * 1024 * 1024:
        raise HTTPException(413, "file_too_large")
    if file.content_type not in {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}:
        raise HTTPException(415, "unsupported_media_type")
    if not file.filename.endswith((".xlsx", ".csv")):
        raise HTTPException(415, "extension_not_allowed")

    # 2. Storage + SHA-256
    payload_bytes = await file.read()
    sha = hashlib.sha256(payload_bytes).hexdigest()
    storage_path = Path(settings.STORAGE_LOCAL_PATH) / "m1/datasets" / str(dataset_id) / "uploads" / f"{uuid.uuid4()}.xlsx"
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(payload_bytes)

    # 3. Idempotency
    last_frozen = await db.scalar(
        select(M1DatasetVersion).where(M1DatasetVersion.dataset_id == dataset_id, M1DatasetVersion.frozen_at.isnot(None))
        .order_by(M1DatasetVersion.version_number.desc()).limit(1)
    )
    if last_frozen and last_frozen.content_sha256 == sha:
        raise HTTPException(409, "version_already_exists")
    pending = await db.scalar(
        select(M1DatasetVersion).where(M1DatasetVersion.dataset_id == dataset_id, M1DatasetVersion.frozen_at.is_(None))
    )
    if pending:
        raise HTTPException(423, "upload_in_progress")

    # 4. Parse + validate (openpyxl read_only=True, data_only=True)
    parsed_rows, warnings = parse_xlsx_to_canonical_rows(payload_bytes)

    # 5. Persist
    next_version_number = await db.scalar(
        select(func.coalesce(func.max(M1DatasetVersion.version_number), 0) + 1)
        .where(M1DatasetVersion.dataset_id == dataset_id)
    )
    version = M1DatasetVersion(
        dataset_id=dataset_id, version_number=next_version_number,
        source="excel_upload", row_count=len(parsed_rows), content_sha256=sha,
    )
    db.add(version)
    await db.flush()

    db.add_all([
        M1DatasetRow(
            version_id=version.version_id,
            regulation_key=r.pop("regulation_key"),
            fields=r,
            validation_warnings=warnings.get(r["regulation_key"], []),
        ) for r in parsed_rows
    ])

    # 6. Optional seal
    if seal:
        version.frozen_at = datetime.now(UTC)

    # 7. Audit
    await audit.record(
        actor_user_id=owner_user_id, verb="m1.dataset.version.upload",
        target_type="m1_dataset_version", target_id=str(version.version_id),
        payload={"dataset_id": str(dataset_id), "row_count": len(parsed_rows), "sealed": seal},
    )

    await db.commit()
    return ExcelUploadResponse(...)
```

The parser `parse_xlsx_to_canonical_rows` lives in `app/services/m1_xlsx_parser.py`. It:
- Opens with `openpyxl.load_workbook(io.BytesIO(payload_bytes), read_only=True, data_only=True)`.
- Picks the first non-empty sheet.
- Detects header row by scanning the first 5 rows for one matching ≥ 3 canonical column aliases.
- Maps headers via `CANONICAL_FIELD_ALIASES` (a dict of e.g. `"Gazette No."` → `regulation_key`, `"ශීර්ෂය (සිංහල)"` → `title_si`).
- For each data row: builds the canonical dict, validates via Pydantic in `lax` mode (warnings, not errors), accumulates results.

### Task 3.5 — API endpoints (½ day)

In `enigmatrix-backend/app/api/v1/m1_datasets.py`:

```
GET    /api/v1/m1/datasets                                      (list, with filters)
POST   /api/v1/m1/datasets                                      (create)
GET    /api/v1/m1/datasets/{id}                                 (detail)
PATCH  /api/v1/m1/datasets/{id}                                 (update name/description/tags)
DELETE /api/v1/m1/datasets/{id}                                 (soft-delete via archived_at)
POST   /api/v1/m1/datasets/{id}/restore                         (un-archive)
GET    /api/v1/m1/datasets/{id}/versions                        (list versions)
GET    /api/v1/m1/datasets/{id}/versions/{vid}                  (version detail + paginated rows)
POST   /api/v1/m1/datasets/{id}/versions/upload                 (upload Excel/CSV)
POST   /api/v1/m1/datasets/{id}/versions/{vid}/seal             (freeze)
POST   /api/v1/m1/datasets/{id}/versions/{vid}/retire           (hide from default queries)
GET    /api/v1/m1/datasets/{id}/versions/{vid}/rows/{key}       (single-row detail)
POST   /api/v1/m1/datasets/{id}/promote-to-ground-truth         (admin only)
```

All write endpoints require `require_admin` dependency. Every write records to `audit_log`.

`promote-to-ground-truth` is implemented as a single transaction:

```sql
BEGIN;
UPDATE m1_datasets SET is_ground_truth = FALSE WHERE is_ground_truth = TRUE;
UPDATE m1_datasets SET is_ground_truth = TRUE WHERE dataset_id = $1;
COMMIT;
```

The partial unique index ensures no transient violation: the demotion happens first.

### Task 3.6 — Frontend pages (1½ days)

Three pages under `enigmatrix-frontend/app/(app)/admin/m1/datasets/`:

**`page.tsx`** — list view. Shows all datasets in a `data-table` with columns: name, kind (badge), version count, current row count, ground-truth badge, owner, created. Filter chips: kind, ground-truth-only, owner-me. CTA: "Upload new dataset" button at top-right.

**`upload/page.tsx`** — upload form. Two-step: (1) drop a file, (2) review parse summary and confirm. Uses `react-dropzone` (no new dep — check if already installed; if not, use plain `<input type="file">`). The parse summary card shows rows-parsed, rows-with-warnings (collapsible list), and a "Confirm and seal" button.

**`[datasetId]/page.tsx`** — dataset detail. Header with name, description, kind, ground-truth badge, "Promote to ground truth" button (admin only). Tabs: "Versions" (default), "Settings", "Audit log". The Versions tab shows the version stream with row count, SHA, frozen-at timestamp, and per-version action buttons: "View rows", "Seal", "Retire", "Use as baseline for measurement", "Use as candidate for measurement" (the last two are stubs in this slice; slice 5 wires them).

**`[datasetId]/versions/[versionId]/page.tsx`** — version detail. Header with version metadata. A paginated table of rows showing `regulation_key`, `title_en`, `gazette_published_date`, and validation-warning badges. Click into a row → modal with the full JSONB `fields` blob rendered as a key-value list with EN/SI/TA grouped tabs.

i18n strings under `frontend/messages/{en,si,ta}.json` keyed at `m1.datasets.*`. EN ships first; SI/TA can land with English placeholders and a follow-up translation pass.

### Task 3.7 — Tests (½ day)

- `enigmatrix-backend/app/tests/integration/test_m1_dataset_upload.py`: upload-then-query roundtrip, idempotency (same SHA → 409), in-flight conflict (concurrent → 423), validation-warning capture, audit-log row written.
- `enigmatrix-backend/app/tests/unit/test_m1_xlsx_parser.py`: parser handles the test fixture `tests/fixtures/m1_master_sample.xlsx` (small 5-row file representative of the real Excel).
- Playwright `frontend/tests/admin-m1-datasets.spec.ts`: end-to-end upload via the UI, see the dataset appear, promote to ground truth, see the badge. Skip if Playwright isn't set up yet; otherwise tests gate slice 8's CI promotion.

## Files touched

| Path | New/Edit | Purpose |
|---|---|---|
| `enigmatrix-backend/alembic/versions/202605240002_m1_datasets_versioning.py` | new | The 3 tables + indexes + constraints |
| `enigmatrix-backend/app/models/m1_dataset.py` | new | ORM |
| `enigmatrix-backend/app/models/__init__.py` | edit | Register new models |
| `enigmatrix-backend/app/schemas/m1_dataset.py` | new | Pydantic |
| `enigmatrix-backend/app/services/m1_dataset_upload.py` | new | Upload logic |
| `enigmatrix-backend/app/services/m1_xlsx_parser.py` | new | Parser |
| `enigmatrix-backend/app/api/v1/m1_datasets.py` | new | Router |
| `enigmatrix-backend/app/api/v1/router.py` | edit | Mount router |
| `enigmatrix-backend/app/tests/integration/test_m1_dataset_upload.py` | new | Integration tests |
| `enigmatrix-backend/app/tests/unit/test_m1_xlsx_parser.py` | new | Parser unit tests |
| `enigmatrix-backend/app/tests/fixtures/m1_master_sample.xlsx` | new | Tiny test Excel |
| `enigmatrix-frontend/app/(app)/admin/m1/datasets/page.tsx` | new | List view |
| `enigmatrix-frontend/app/(app)/admin/m1/datasets/upload/page.tsx` | new | Upload form |
| `enigmatrix-frontend/app/(app)/admin/m1/datasets/[datasetId]/page.tsx` | new | Detail |
| `enigmatrix-frontend/app/(app)/admin/m1/datasets/[datasetId]/versions/[versionId]/page.tsx` | new | Version detail |
| `enigmatrix-frontend/lib/api/m1-datasets.ts` | new | Client |
| `enigmatrix-frontend/lib/validators/m1-dataset.ts` | new | Zod (mirrors backend schema) |
| `enigmatrix-frontend/messages/{en,si,ta}.json` | edit | i18n keys under `m1.datasets.*` |
| `enigmatrix-frontend/tests/admin-m1-datasets.spec.ts` | new | Playwright E2E |

## Gate

End-to-end flow works:

1. `make migrate` brings the three tables up cleanly.
2. Log in as admin at `/auth/login`.
3. Navigate to `/admin/m1/datasets`. Empty state shows.
4. Click "Upload new dataset". Enter name "Manual ground truth — May 2026", kind = `manual_excel`. Drop the canonicalised Excel from slice 1.
5. Parse summary shows "407 rows parsed, 12 with warnings, 0 errors". Confirm.
6. Land on dataset detail page. Version 1 shows with row count 407, SHA-256 visible, frozen-at timestamp set.
7. Click "Promote to ground truth". Green badge appears.
8. Re-upload the same Excel. 409 Conflict returned with `version_already_exists`.
9. `SELECT * FROM audit_log WHERE verb LIKE 'm1.dataset.%' ORDER BY created_at DESC LIMIT 5;` shows the upload + promote rows.
10. Query `SELECT COUNT(*) FROM m1_dataset_rows WHERE version_id = <v1>` returns 407.

## What this slice deliberately does NOT do

- Backfill of existing `m1_regulations` into `m1_dataset_rows` (slice 8).
- Cross-dataset row comparison (slice 5/6).
- Edit-rows-in-an-unsealed-version UI (deferred — sealing on upload is the default; per-row editing post-slice-3 is rare enough to defer).
- Excel-format auto-detection that's smarter than "header row in first 5 rows" (deferred).
- ClamAV / antivirus scan of uploads (deferred to slice 8 polish).

## Risks specific to this slice

- **Parser brittleness on a Sinhala-heavy Excel.** Mitigation: the parser handles cells as Python `str` directly (openpyxl returns Unicode); no codec conversions. Test fixture includes Sinhala title rows. If any header is unmatched, the row's `_extras` key in the JSONB preserves it — no silent loss.
- **Ground-truth promotion race.** Mitigation: single `BEGIN ... COMMIT` for the demote-then-promote. Partial unique index makes it impossible to observe two ground-truth rows even transiently.
- **`current_version_id` chicken-and-egg.** Mitigation: column is nullable; populated after the version row exists. The schema has `post_update=True` on the relationship.
- **JSONB GIN index size.** Mitigation: only add the GIN index if pg version ≥ 11 (the project uses pg16 so this is fine). If the index slows down inserts significantly, defer the GIN to slice 5 when measurement queries actually use it.

## Cross-references

- [02_Slice1_Measurement_Scaffolding](02_Slice1_Measurement_Scaffolding.md) — produces the `structured_v1.xlsx` this slice uploads.
- [05_Slice4_Extraction_Profile_Registry](05_Slice4_Extraction_Profile_Registry.md) — slice 4 adds `extraction_profile_id` FK on `m1_dataset_versions` and produces extraction-run versions.
- [06_Slice5_Measurement_Engine](06_Slice5_Measurement_Engine.md) — slice 5 reads from `m1_dataset_rows` for both baseline and candidate.
- [01_Alignment_Audit §E](01_Alignment_Audit.md#e-the-audit_log-rule-🟡-convention-drift), [§K](01_Alignment_Audit.md#k-excel-security-🟢-refinement), [§L](01_Alignment_Audit.md#l-idempotency-🟢-refinement) — the upgrades this slice incorporates.
- `enigmatrix-docs/m1/02_M1_Data_Requirements.md` — original Phase 1 schema spec; the canonical field names trace back here.
