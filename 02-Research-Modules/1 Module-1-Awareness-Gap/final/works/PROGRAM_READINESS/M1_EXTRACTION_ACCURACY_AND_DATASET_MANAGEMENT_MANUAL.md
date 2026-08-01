# M1 Extraction Accuracy And Dataset Management Manual

> Updated: 2026-07-30  
> Repo: `C:\Reasearch\xyz`  
> Purpose: document how the extraction-accuracy measurement feature works, how datasets are stored, and what still needs to be evidenced for the thesis/demo.

## 1. What Was Built

The extraction-accuracy feature measures how close an extracted regulation dataset is to a ground-truth Excel dataset.

It includes:

- Excel ground-truth upload.
- Dataset registry.
- Immutable sealed dataset versions.
- DB snapshot versions from extraction runs.
- Per-row and per-field measurement scoring.
- Aggregated accuracy summaries.
- Measurement dashboard and detail screens.
- Markdown report export.
- Data-quality expectation suites.
- Thesis table/figure generation scripts.

This is the missing documentation area that was under-represented in the feature checklist. It should be treated as a real shipped feature set, but it still needs a real production run with screenshots/run IDs for final viva evidence.

## 1.1 Development Approach

The feature was developed as a reproducible dataset-versioning and measurement system, not as a one-off spreadsheet comparison.

The approach is:

1. Store human ground truth as a sealed dataset version.
2. Store extracted DB output as another sealed dataset version.
3. Compare sealed versions only, never mutable live tables.
4. Score per field and per regulation.
5. Persist every score row for audit and slice analysis.
6. Generate dashboards and a Markdown report from the stored run.

Why this approach is correct:

- A sealed baseline/candidate pair gives reproducible thesis evidence.
- Excel uploads and DB snapshots can be compared with the same evaluator.
- Measurement run IDs, dataset version IDs, hashes, and report exports make the result defensible in the final review.
- The same infrastructure can later measure title/summary fields after the trilingual summarization workflow is implemented.

Current evidence status:

```text
Code and UI paths exist.
Unit/E2E tests exist for key pieces.
Final production measurement run evidence is still missing.
Screenshots and run IDs must be captured before marking this item fully complete.
```

## 2. Important Code Paths

| Area | Path |
|---|---|
| Dataset APIs | `enigmatrix-backend\app\m1\api\datasets.py` |
| Measurement APIs | `enigmatrix-backend\app\m1\api\measurements.py` |
| Extraction profile/run APIs | `enigmatrix-backend\app\m1\api\extractions.py` |
| Dataset ORM | `enigmatrix-backend\app\m1\models\dataset.py` |
| Measurement ORM | `enigmatrix-backend\app\m1\models\measurement.py` |
| Excel parser | `enigmatrix-backend\app\m1\services\xlsx_parser.py` and `enigmatrix-ml\m1\evaluation\xlsx_reader.py` |
| Dataset upload service | `enigmatrix-backend\app\m1\services\dataset_upload.py` |
| Snapshot service | `enigmatrix-backend\app\m1\services\snapshot_service.py` |
| Measurement task | `enigmatrix-backend\app\m1\tasks\run_measurement.py` |
| Aggregates/reporting | `enigmatrix-backend\app\m1\services\measurement_aggregates.py`, `measurement_report.py`, `measurement_slices.py` |
| Data-quality suites | `data_quality\expectations\m1_dataset_rows.json`, `data_quality\expectations\m1_measurement_scores.json` |
| Thesis artifacts | `scripts\regenerate_thesis_tables.py` |
| Join verification helper | `scripts\verify_measurement_join.py` |

Frontend/operator surfaces:

| Surface | Path |
|---|---|
| Dataset list and create | `enigmatrix-frontend\app\(admin)\admin\datasets\m1\page.tsx` |
| Dataset upload | `enigmatrix-frontend\app\(admin)\admin\datasets\m1\[datasetId]\upload\page.tsx` |
| Dataset version rows | `enigmatrix-frontend\app\(admin)\admin\datasets\m1\[datasetId]\versions\[versionId]\page.tsx` |
| Measurement run form | `enigmatrix-frontend\app\(admin)\admin\datasets\m1\measurements\run\page.tsx` |
| Measurement dashboard | `enigmatrix-frontend\app\(admin)\admin\datasets\m1\measurements\[runId]\page.tsx` |
| Per-regulation comparison | `enigmatrix-frontend\app\(admin)\admin\datasets\m1\measurements\[runId]\regulations\[regulationKey]\page.tsx` |
| Extraction DB snapshot control | `enigmatrix-frontend\components\m1\extraction\batch-stage-control.tsx` |

## 3. Data Storage Model

| Table | Meaning |
|---|---|
| `m1_datasets` | Named dataset container, for example ground truth or extracted candidate |
| `m1_dataset_versions` | Immutable version of a dataset; stores source, scope, hash, status, and validation warnings |
| `m1_dataset_rows` | One regulation row inside a sealed dataset version; canonical fields stored as JSON plus indexed keys |
| `m1_measurement_runs` | One comparison between a baseline version and a candidate version |
| `m1_measurement_scores` | Per-row, per-field metric results for a measurement run |

Why sealed versions exist:

- The same Excel upload or DB snapshot must be reproducible later.
- A measurement run must point to stable baseline/candidate versions.
- Thesis tables must be traceable to exact data hashes.

## 4. User Flow In The Admin UI

Use this flow for a thesis-ready extraction accuracy run.

1. Start the backend/frontend normally.
2. Open the admin dataset area:

```text
/admin/datasets/m1
```

3. Create or select the ground-truth dataset.
4. Upload the Excel ground-truth file.
5. Seal the uploaded dataset version.
6. Run or select an extraction profile over the same scope.
7. Create a DB snapshot dataset version from the extracted rows.
8. Run a measurement comparing:

```text
baseline = sealed Excel ground-truth version
candidate = sealed DB snapshot / extractor output version
```

9. Open the measurement detail page.
10. Download the Markdown report:

```text
GET /api/v1/m1/measurements/{run_id}/report.md
```

11. Store the run ID, dataset version IDs, report, and screenshots in the thesis evidence folder.

## 5. Excel Ground-Truth Requirements

The Excel sheet must include a stable join key. Preferred:

```text
regulation_key
```

Acceptable supporting identifiers:

```text
gazette_number
document_number
published_date
```

Canonical fields already handled by the parser/evaluator include:

```text
title_en
title_si
title_ta
summary_en
summary_si
summary_ta
raw_text
cleaned_text
change_category
affected_sectors
is_sme_relevant
effective_date
principal_act
penalty_amount
extraction_method
confidence
```

Why this matters:

- The measurement engine compares matching rows by key.
- Missing or inconsistent keys make the accuracy score meaningless.
- Sinhala/Tamil title fields are optional in the headline score, but they are still useful for trilingual readiness.

## 6. DB Snapshot Workflow

A DB snapshot freezes current extracted regulations into `m1_dataset_versions` and `m1_dataset_rows`.

It should include:

- extracted title fields.
- extracted summary fields if present.
- raw/cleaned text.
- classification fields.
- extraction method/profile.
- confidence/provenance.
- date/source scope.

Why snapshots are needed:

- The live `m1_regulations` table changes over time.
- A thesis measurement must compare a stable candidate version to stable ground truth.
- A failed later extractor run must not change old scores.

## 7. Useful Commands

Run unit tests for parser/measurement pieces:

```powershell
cd C:\Reasearch\xyz\enigmatrix-backend

uv run pytest app\tests\unit\test_m1_xlsx_parser.py
uv run pytest app\tests\unit\test_m1_measurement_report.py
uv run pytest app\tests\unit\test_m1_measurement_join_key.py
uv run pytest app\tests\unit\test_m1_measurement_aggregates.py
```

Verify the measurement join if a run gives strange missing-row counts:

```powershell
cd C:\Reasearch\xyz

uv run python scripts\verify_measurement_join.py --auto
```

Run a baseline/demo measurement when a live DB run is not ready:

```powershell
cd C:\Reasearch\xyz

uv run python scripts\run_baseline_measurement.py --demo --skip-labse
```

Regenerate thesis tables after complete measurement runs exist:

```powershell
cd C:\Reasearch\xyz

uv run python scripts\regenerate_thesis_tables.py
```

## 8. What To Capture For The Thesis

For each important measurement run, capture:

- baseline dataset ID and version ID.
- candidate dataset ID and version ID.
- measurement run ID.
- extraction profile name and version.
- source/date scope.
- row counts.
- field-level mean/median scores.
- completeness summary.
- worst-N examples.
- downloaded `report.md`.
- screenshots of upload, sealed version, run detail, dashboard, and report export.

## 9. Current Improvement List

| Gap | Why it matters | Action |
|---|---|---|
| Real production measurement evidence still missing from docs | Code-complete is not enough for viva proof | Run one real Excel-vs-DB measurement and attach screenshots/run IDs |
| Rare title/summary fields may be incomplete | Summary/title accuracy cannot be measured if candidate rows are blank | Build the summarization/translation workflow before final trilingual measurement |
| Join-key mismatch risk | Wrong joins create false missing/mismatch scores | Use `verify_measurement_join.py --auto` before final reporting |
| UI evidence incomplete | Reviewers need to see the operator workflow | Add screenshots of Excel upload, sealed version, DB snapshot, measurement detail, and report download |
| Production migrations not verified in final environment | Local code may differ from deployed DB | Run `alembic current` and `alembic upgrade head` in the final demo environment |

Parent documentation sections to update after the first real measurement run:

| Parent doc | What to add |
|---|---|
| `02_M1_Data_Requirements.md` | Final ground-truth Excel contract, required join key, and canonical fields actually measured. |
| `03_M1_Data_Collection.md` | Extraction profile used for the candidate snapshot and evidence that the snapshot covers the same scope as the ground truth. |
| `08_M1_Full_System_Architecture.md` | End-to-end dataset versioning and measurement flow from Excel upload to report export. |
| `11_M1_API_Reference.md` | Final endpoint list for dataset upload, sealing, snapshot-range, measurement run, scores, and report export. |
| `12_M1_Monitoring_Maintenance.md` | How failed measurement runs, stale snapshots, and join mismatches are detected and handled. |
| `14_M1_Tracking_Workflows.md` | Admin workflow screenshots: upload, seal, snapshot, run measurement, inspect dashboard, download report. |

## 10. Acceptance Checklist

Mark the extraction-accuracy feature ready when:

- [ ] Ground-truth Excel upload succeeds.
- [ ] Uploaded dataset version is sealed and has a content hash.
- [ ] DB snapshot version is created from extracted rows.
- [ ] Measurement run completes.
- [ ] `m1_measurement_scores` has per-row/per-field scores.
- [ ] Dashboard shows overall and field-level metrics.
- [ ] Markdown report downloads successfully.
- [ ] Data-quality suites run after sealing.
- [ ] Thesis tables regenerate from latest complete measurement runs.
- [ ] Screenshots and run IDs are stored in the Obsidian vault.
