---
tags: [m1, phase-2, slice-8, backfill, polish, thesis, ci]
date: 2026-05-23
status: 🟢 done
completed: 2026-06-29
estimated-effort: 1 week
prerequisites: slices 1–7 shipped
---

# 09 — Slice 8: Backfill, Polish, and Thesis Artefacts

## What this slice produces

A one-off backfill that materialises the existing `m1_regulations` rows into a `legacy_baseline_v1` dataset version so historical extractions become first-class measurement targets. A Great Expectations test suite that enforces the schema invariants documented across Phase 2. A `make thesis-artifacts` target that regenerates every table and figure Chapter 4 needs from the latest measurement runs. A retention policy that auto-retires dataset versions older than 30 days. A handful of UX polish items collected from slice-7 dogfooding. The Phase-2-complete tag on the repo and a Phase-3 handoff document.

When this slice ships, Phase 2 is done. Chapter 4 of the thesis writes itself from the artefacts. Phase 3 (XLM-R + LoRA training) has a clean dataset card pointing at the right dataset version.

## Tasks

### Task 8.1 — `legacy_baseline_v1` backfill (½ day)

`enigmatrix-backend/scripts/backfill_legacy_baseline.py`:

1. Creates a `m1_datasets` row: name = "Legacy baseline (snapshot of m1_regulations 2026-05-23)", kind = `extraction_run`.
2. Creates a `m1_dataset_versions` row: source = `backfill`, frozen_at = NOW().
3. For every row in `m1_regulations` where `status IN ('preprocessed', 'extracted')` and `archived_at IS NULL`, copies the row into `m1_dataset_rows` with the existing fields mapped into the JSONB `fields` blob.
4. Computes content SHA-256 and sets it on the version.
5. Writes an audit row `m1.dataset.version.backfill`.

This is the dataset version slice 7's profiles can be scored against to produce a clean "before/after" comparison from the historical corpus, not just the manual GT.

### Task 8.2 — Great Expectations suites (1 day)

Under `enigmatrix-backend/data_quality/`:

```
data_quality/
├── expectations/
│   ├── m1_dataset_rows.json
│   ├── m1_extraction_profiles.json
│   ├── m1_measurement_scores.json
│   └── m1_regulations.json
└── checkpoints/
    └── post_extraction_check.yaml
```

The `m1_dataset_rows` suite expects:
- `regulation_key` matches `^\d+/\d+$`.
- `fields` is a non-empty object.
- `raw_text` is null-or-non-empty (catches the Session-1-documented `2469_20` failure mode where `extraction_method='pdfplumber'` but `raw_text=''`).
- If `extraction_method` ∈ ('pymupdf','pdfplumber','tesseract') then `raw_text` is non-empty.
- `fields.gazette_published_date` parseable as ISO date.

The `m1_regulations` suite mirrors the existing CHECK constraints + the empty-text rule for paranoia.

Suites run via a post-extraction Celery hook: when `run_extraction_with_profile` seals a version, it dispatches `validate_dataset_version.delay(version_id)`, which runs the suite and writes `validation_warnings` on the version row if anything fires. The dashboard surfaces these warnings on the version detail page.

### Task 8.3 — `make thesis-artifacts` (1 day)

`scripts/regenerate_thesis_tables.py` reads the latest sealed measurement runs and emits:

- `data/thesis/table_4_1_per_field_accuracy.csv` — rows × profiles, cells = primary-metric mean.
- `data/thesis/table_4_2_per_stratum_cer.csv` — strata × profiles, cells = mean CER + bootstrap CI.
- `data/thesis/table_4_3_profile_comparison.csv` — pairwise per-field delta + paired Wilcoxon p-values.
- `data/thesis/figure_4_1_calibration.svg` — reliability diagram for the best-confidence profile.
- `data/thesis/figure_4_2_status_distribution.svg` — stacked bar of `{exact, partial, mismatch, missing, extra}` per profile.
- `data/thesis/RUN_PROVENANCE.md` — for each artefact, the measurement run id + git SHA + dataset version SHAs.

Makefile target:

```makefile
.PHONY: thesis-artifacts
thesis-artifacts:
	cd enigmatrix-backend && uv run python ../scripts/regenerate_thesis_tables.py
```

### Task 8.4 — Retention policy (½ day)

`enigmatrix-backend/app/tasks/m1/retire_old_versions.py` — Celery Beat task that runs nightly at 02:00 LKT:

```python
@celery_app.task
def retire_old_dataset_versions():
    cutoff = datetime.now(UTC) - timedelta(days=30)
    # Retire all versions older than cutoff except:
    #   - the current_version_id of any dataset
    #   - the immediately-previous version (so you can always diff one step back)
    #   - any version tagged `keep: TRUE` in notes JSONB
```

Beat schedule entry in `app/celery_config.py`:

```python
beat_schedule = {
    "retire-old-dataset-versions": {
        "task": "app.tasks.m1.retire_old_versions.retire_old_dataset_versions",
        "schedule": crontab(hour=2, minute=0),
    },
}
```

Retirement = setting `retired_at = NOW()`. The row stays in the database; default queries (and the UI list) skip it.

### Task 8.5 — Phase-3 handoff doc (½ day)

`enigmatrix-docs/phase3_dataset_card.md`:

- Which dataset version to train on (the most recent `manual_excel` ground-truth, version pinned by `version_id`).
- The 12-category + 10-sector label schema.
- The temporal 70/15/15 split rule (from `enigmatrix-docs/m1/06_M1_Training_Evaluation.md`).
- The augmentation policy (back-translation ≤ 5×, training only).
- The model registry conventions (`model_registry.json` schema).
- The Phase 3 acceptance criteria (macro F1 ≥ 0.92, per-lang gates, slice cliff < 8 pp).

### Task 8.6 — Polish items collected from dogfooding (½ day)

Slice 7 produces a list of small UX irritations. Address them here:

- Sortable columns in the runs list (added if missing).
- Keyboard shortcut `n` opens "New measurement" modal from any measurements page.
- `?` opens a keyboard-shortcut help modal.
- Recent-runs sparkline next to the overall-score KPI card.
- Dataset detail page — empty-state copy when there are no versions yet.
- Failed-extraction drill-down chevron (the Session-53 bug from the M1 pipeline audit).
- "Compare run" button on the comparison view goes directly to the profile-delta panel anchor.

### Task 8.7 — CI / git tag (½ day)

- Add `.github/workflows/ci-m1-phase2.yml` (or similar) running:
  - `uv run pytest enigmatrix-backend enigmatrix-ml -m "not slow"` (fast tests only).
  - `pnpm --filter enigmatrix-frontend lint` + `pnpm --filter enigmatrix-frontend test:e2e --grep "@phase2"`.
  - Alembic check: `alembic check` to ensure migrations linearise cleanly.
- Tag the repo at `m1-phase2-complete`.
- Pin the Docker image hash in `infra/` so future runs of the pipeline are reproducible byte-for-byte.

## Files touched

| Path | New/Edit | Purpose |
|---|---|---|
| `enigmatrix-backend/scripts/backfill_legacy_baseline.py` | new | Backfill |
| `enigmatrix-backend/data_quality/**` | new | GE suites + checkpoints |
| `enigmatrix-backend/app/tasks/m1/validate_dataset_version.py` | new | Post-extraction GE hook |
| `enigmatrix-backend/app/tasks/m1/retire_old_versions.py` | new | Retention policy |
| `enigmatrix-backend/app/celery_config.py` | edit | Beat entry |
| `scripts/regenerate_thesis_tables.py` | new | Thesis artefact generator |
| `Makefile` | edit | `make thesis-artifacts` target |
| `enigmatrix-docs/phase3_dataset_card.md` | new | Phase 3 handoff |
| `enigmatrix-frontend/...` | edits | Polish items |
| `.github/workflows/ci-m1-phase2.yml` | new | CI |
| `infra/docker-image-pin.txt` | new | Reproducibility |

## Gate

1. `python scripts/backfill_legacy_baseline.py` runs cleanly. A new dataset version exists with row count = pre-existing `m1_regulations.WHERE status IN ('preprocessed','extracted')`.
2. GE suites all pass against the production replica (or document any expected failures).
3. `make thesis-artifacts` writes all six files in `data/thesis/`.
4. The retention Celery beat task fires successfully in staging once (no actual data retired the first night).
5. CI passes on a fresh PR.
6. Git tag `m1-phase2-complete` exists.

## What this slice deliberately does NOT do

- It does NOT start Phase 3 ML training.
- It does NOT productionise the Surya profile (it ships as a research toggle even if shipped).
- It does NOT remove `m1_regulations` — backward compatibility holds; future phases can revisit.

## Risks specific to this slice

- **Backfill row count mismatches**. Mitigation: dry-run mode produces a count summary; reconcile against the source table before committing.
- **GE suites are too strict** (production has legacy rows that violate them). Mitigation: suites run in "report" mode for the first week; promote to "fail" only after the warnings stabilise.
- **`make thesis-artifacts` requires a recent measurement run**. Mitigation: the script emits a helpful error if no measurement run is found.
- **CI flakiness on first run**. Mitigation: keep the LaBSE / BERTScore tests on the `slow` marker; CI only runs the fast suite. Slow suite runs nightly.

## Cross-references

- [02_Slice1_Measurement_Scaffolding](02_Slice1_Measurement_Scaffolding.md) — the registry used by `make thesis-artifacts`.
- [01_Alignment_Audit](01_Alignment_Audit.md) — `Session 53 known bugs` are addressed in task 8.6.
- `enigmatrix-docs/m1/06_M1_Training_Evaluation.md` — informs the Phase 3 handoff doc.
- `enigmatrix-docs/m1/12_M1_Monitoring_Maintenance.md` — informs the retention policy + GE wiring.
