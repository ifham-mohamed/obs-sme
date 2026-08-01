# 2026-08-01 — M1 Integration, Reorganization and Documentation-Sync Work Record

> What was executed after the frozen LinearSVC primary model was produced: backend wiring, documentation correction, workspace reorganization, doc-mirror sync, and the first commit of the frozen Phase-3 evidence. Every claim below is backed by a generated log in `C:\Reasearch\xyz\documentation\m1\structure_audit\`.
>
> Session date: 2026-08-01 · Nothing was pushed to any remote · Nothing was deleted.

---

## 0. Starting position

The frozen primary classifier existed on disk and had been verified, but:

- `datasets/`, `models/` and `documentation/` were **untracked** — the V6 parquets and the frozen model existed only on one machine.
- `LinearSVCGazetteInference` existed in the ML package but nothing called it.
- The backend classifier service loaded only the never-promoted ONNX model.
- Docs 05/06/11 still described XLM-R as the production architecture.
- The repo's `enigmatrix-docs/m1/` doc mirror had drifted badly from the vault.

---

## 1. Backend wiring — the classifier service now uses the frozen model

### 1.1 The bug that a naive swap would have caused

`classify_gazette.py` did this:

```python
row.classifier_confidence = Decimal(str(round(result["confidence"], 2)))
result["confidence"] < MIN_CONFIDENCE
```

The LinearSVC engine returns `confidence: None` by design — its `decision_function` output is an uncalibrated margin, not a probability. Pointing the existing service at the new engine would have raised `TypeError` on **every row**. This was found by reading the call site before switching, not by running it.

### 1.2 What was implemented

`enigmatrix-backend/app/m1/services/classifier_service.py` — rewritten as a two-backend service:

| Setting | Default | Meaning |
|---|---|---|
| `M1_CLASSIFIER_BACKEND` | `linearsvc` | `linearsvc` (frozen primary) or `onnx` (XLM-R dual-head) |
| `M1_MODEL_LINEARSVC_DIR` | `models/m1/linearsvc_v6_primary` | Resolved against cwd, then the workspace root |
| `M1_MODEL_ONNX_DIR` | `storage/models/m1/onnx/v1` | Unchanged |
| `M1_CLASSIFIER_MIN_CONFIDENCE` | `0.55` | ONNX path only — calibrated probability threshold |
| `M1_CLASSIFIER_MIN_MARGIN` | *(unset)* | LinearSVC path — margin threshold, **disabled by default** |

Path resolution matters because the model lives at the workspace root (`models/m1/...`) one level above the backend package, and the service can be started from either directory. `_resolve()` tries cwd first, then the workspace root, and falls back to the cwd form so error messages name the path the operator expects.

**`M1_CLASSIFIER_MIN_MARGIN` is deliberately unset.** No empirically validated margin cut-off exists yet. Inventing one would produce a review queue whose behaviour nobody can justify; leaving it off means no rows are auto-flagged on the LinearSVC path until a threshold is derived from the frozen validation errors.

`enigmatrix-backend/app/m1/tasks/classify_gazette.py`:

- `classifier_confidence` is written **only** when the backend supplies a calibrated probability. On the LinearSVC path the column is left NULL rather than being fed a raw margin.
- The log line now carries `backend`, `conf` (or `n/a`), and `margin`.
- The task result payload gains `decision_margin` and `model_name` when available.
- The stale "12-category" docstring was corrected to the frozen 8-category V6 taxonomy.

### 1.3 The one thing not done, and why

The review queue currently reads:

```sql
WHERE status='classified' AND classifier_confidence < 0.55 AND NOT expert_verified
```

On the LinearSVC backend `classifier_confidence` stays NULL, so **that predicate silently matches nothing**. Fixing it properly needs two new columns and an Alembic migration:

```text
classifier_decision_margin  NUMERIC
classifier_model_name       TEXT
```

A schema migration was not written blind in this session — it needs to be authored against a live database and verified with `alembic upgrade head`. The requirement is recorded in the task docstring so the next person hits it immediately. Until then the margin is logged, not persisted.

**Verification:** `py_compile` on both modules → exit 0. Non-slow M1 model tests → **26 passed, 2 deselected**.

---

## 2. Documentation corrections

Three documents asserted things that the evidence now contradicts. They were **annotated, not rewritten** — the design reasoning that led to XLM-R was sound and deleting it would falsify the research narrative. What changed is that each now states its own outcome.

| Document | Correction |
|---|---|
| `05_M1_Model_Architecture.md` §4 | Callout: the architecture was built, trained, and **not promoted** — 0.9693 train / 0.9027 val / **0.7436 test**, below the 0.92 gate and 0.204 behind the baseline. Production is lexical. Category head sized to the superseded taxonomy; V6 uses 8 categories. |
| `06_M1_Training_Evaluation.md` | The acceptance criterion "XLM-R beats TF-IDF+LR by ≥ 0.10 macro-F1" now records **NOT MET** with the numbers, and notes the criterion did its job: it stopped a worse model being promoted on its validation score. |
| `11_M1_API_Reference.md` | Backend change: default backend is `linearsvc`, `confidence` is nullable, sectors empty, margins must not be rendered as percentages; ONNX remains available via env and is still the only sector-predicting engine. |

Also updated earlier in the same pass: `03_FEATURE_CHECKLIST.md` (new dated section), `15_M1_Folder_Reference.md` (§13 + corrected status rows).

---

## 3. Workspace reorganization

Applied via `scripts/_docs_sync_and_reorg.py --apply`; full before/after in `MOVE_MANIFEST.md`.

**Vault:** `PROGRAM_READINESS/log and works/` → `LOG_AND_WORKS/` · byte-identical duplicate master index → `_archive/duplicates/` · `_REORGANIZE_works.ps1` → `_tooling/`.

**Repo:** five root planning documents → `documentation/{plans,manuals,_archive}/` via `git mv` · generated records and audits consolidated under `documentation/m1/`.

**Deliberately not done — `scripts/` was left flat.** 26 files reference scripts by their current path: `enigmatrix-docs/`, the Phase-3 annotation runbooks, `AI_WORK_LOG.md`, `enigmatrix-ml/tests/evaluation/test_baseline_script.py`, and the frozen end-to-end record's own appendices. Subfoldering would break every documented command for cosmetic gain. The lifecycle grouping is indexed in `STRUCTURE.md` §4 instead.

**Verification:** `scripts/_verify_reorg.py` → `missing=0 stale=0`. The only two remaining mentions of the old folder name are in documents that *describe the rename*.

---

## 4. Documentation mirror sync

`enigmatrix-docs/m1/` was refreshed **from** the vault, one-way.

| Measure | Value |
|---|---:|
| Files refreshed | **33** |
| Kept — repo copy newer | 1 (`04_API_AND_PAGES_REFERENCE.md`) |
| Kept — already identical | 2 |

Every overwritten repo file was copied first to `enigmatrix-docs/_pre_sync_backup_<timestamp>/`. The direction was decided by evidence, not preference: of 36 shared filenames, 34 had diverged and the vault was newer in 31 — `15_M1_Folder_Reference.md` was 5.9 KB in the repo against 101.6 KB in the vault.

The repo set also holds **52 files the vault does not** — the `NN_M1_N_*` deep-dive sub-series. Those were left untouched; they are companion documents, not stale duplicates, and merging them into the vault is a separate decision.

---

## 5. Version control — the frozen evidence is now committed

Three local commits. **Nothing was pushed.**

| Repo | Commit | Contents |
|---|---|---|
| `enigmatrix-backend` | `8930d2a` | Backend selection + optional-confidence handling |
| `enigmatrix-ml` | `9c96e30` | `LinearSVCGazetteInference`, dual exports, 2 test files, gitignore (5 files, +670) |
| workspace root | *(see log)* | **265 files changed, 231,653 insertions** — frozen V6 dataset, frozen model + evidence tables, producing scripts, labelling gold standard, documentation reorg, `STRUCTURE.md` |

### Ignore decisions

| Path | Decision | Reason |
|---|---|---|
| `mydata/` | Ignored | Label Studio server DB, `.bak` snapshots, media uploads and raw exports — carries annotator account data and is rebuildable from the exported batches |
| `*.sqlite3`, `*.sqlite3.bak` | Ignored | Same |
| `tmp/`, `runs/` | Ignored | Scratch / generated |
| `kaggle_m1_training_v1.zip` | Ignored | Rebuildable from the tracked `kaggle_bundle/` |
| `enigmatrix-ml/datasets/` | Ignored | Superseded pre-V4 generations; the canonical frozen sets are tracked at the workspace root |
| `research/data/labeling/` | **Tracked** | Irreplaceable human annotation evidence — gold standards, IAA reports, batch provenance |

### Left uncommitted on purpose

```text
enigmatrix-ml:  m1/data/samplers.py · m1/model/architecture.py
                m1/model/config.py  · pyproject.toml
root:           mydata/label_studio.sqlite3 (already tracked — gitignore
                cannot untrack it) · uv.lock · raw/
enigmatrix-frontend, enigmatrix-backend: pre-existing unrelated changes
```

These predate this session. Committing changes whose intent was not verified would put unreviewed work into the record under a message that does not describe it. Review each diff and commit separately.

---

## 6. Evidence files

```text
C:\Reasearch\xyz\documentation\m1\structure_audit\
├── STRUCTURE_AUDIT.md          full tree, sizes, git state, duplicate scan
├── DOCS_SYNC_REPORT.md         vault-vs-repo divergence, file by file
├── MOVE_MANIFEST.md            every move, source → destination
├── VERIFY.txt                  post-move verification (missing=0 stale=0)
└── SYNC_AND_COMMIT_LOG.txt     mirror refresh, compile, tests, commits
```

Regenerate any of them:

```powershell
py -3 C:\Reasearch\xyz\scripts\_audit_structures.py
py -3 C:\Reasearch\xyz\scripts\_docs_sync_and_reorg.py     # dry-run
py -3 C:\Reasearch\xyz\scripts\_verify_reorg.py
```

---

## 6b. Stage 2 — margin persistence, review queue, threshold derivation

Executed immediately after the above. Log: `documentation/m1/structure_audit/STAGE2_VERIFY_LOG.txt`.

### 6b.1 The threshold was derived, not chosen

`scripts/derive_m1_margin_threshold.py` computes decision margins on the **V6 validation split only** — the test split stays reserved, because picking an operating point on it would invalidate the reported 0.9472 test macro-F1.

The margin separates cleanly:

| Group | n | min | median | max |
|---|---:|---:|---:|---:|
| Correct | 157 | 0.1129 | **1.5954** | 2.1852 |
| Incorrect | 9 | 0.0929 | **0.3896** | 1.4632 |

Sweep (flag when `margin < threshold`):

| Threshold | Flagged | % of split | Errors caught | Error recall | Flag precision |
|---:|---:|---:|---:|---:|---:|
| 0.20 | 5 | 3.0% | 2 | 22.2% | 40.0% |
| **0.40** | **11** | **6.6%** | **5** | **55.6%** | **45.5%** |
| 0.70 | 21 | 12.7% | 7 | 77.8% | 33.3% |
| 1.00 | 32 | 19.3% | 7 | 77.8% | 21.9% |

**Candidate: `M1_CLASSIFIER_MIN_MARGIN=0.40`. It ships unset.** Nine errors in 166 rows means one reclassified row moves error recall by ~11%; that is a starting point to revise against production review data, not a tuned constant. Two errors are also unreachable by any margin rule — `GZT_2487_01` (1.2670) and `GZT_2479_56` (1.4632) are confidently wrong, which is what an uncalibrated margin cannot tell you.

Sanity check worth recording: validation accuracy recomputed from the frozen joblib came out **0.9457831325301205** — identical to the frozen figure, confirming the artifact loads and predicts as recorded.

### 6b.2 Migration 202608010001

```text
classifier_decision_margin  NUMERIC(10,6)  CHECK (>= 0)  + partial index
classifier_model_name       VARCHAR(64)
```

`classifier_confidence` was deliberately left alone — it keeps its `[0,1]` CHECK and is still filled by the ONNX backend. A row carries a confidence **or** a margin depending on which engine classified it, and never a margin coerced into the confidence column.

Chain verified: 53 migrations, **single head `202608010001`**, no dangling parents. The one diamond in the tree (`202605280001` → two children) is the normal alembic branch-and-merge, already rejoined by merge migration `202605300001`.

> The first run of my chain checker reported four heads and two dangling parents. That was a defect in the checker, not the schema: its regex missed `revision = "x"` declarations without a type annotation and could not parse the tuple `down_revision` of a merge migration. Fixed, re-run, and the verdict line now keys on head count.

**Not applied to any database.** `alembic upgrade head` still has to be run.

### 6b.3 Review queue repointed

`GET /classifier-review` now picks its signal from the active backend and reports which one it used:

| Backend | Predicate | `mode` |
|---|---|---|
| `onnx` | `classifier_confidence < 0.55` | `confidence` |
| `linearsvc` + threshold set | `classifier_decision_margin < threshold` | `margin` |
| `linearsvc`, no threshold | *(no query)* | `disabled` |

The third row is the point. Applying the confidence predicate on a backend that never writes confidence returns zero rows — indistinguishable from "nothing needs review". `mode='disabled'` says why the queue is empty.

Response gains `classifier_decision_margin` and `classifier_model_name`; both are additive and nullable.

### 6b.4 Frontend

No component consumes `classifier-review` or renders `classifier_confidence` yet, so there was nothing to break. Two stale strings in `lib/m1/docs.ts` still described a 12-category XLM-R dual-head with a `confidence < 0.70` rule; both corrected.

### 6b.5 Verification and commits

`py_compile` on five backend modules → exit 0 · backend imports resolve (`backend=linearsvc`, `min_margin=None`, `model_dir` resolved to the workspace-root artifact) · M1 model tests **26 passed, 2 deselected**.

| Repo | Commit |
|---|---|
| `enigmatrix-backend` | `e967e88` — migration, model columns, persistence, review queue |
| `enigmatrix-frontend` | `1c36b37` — corrected pipeline description |
| workspace root | `eae890c` — `.env.example` contract, margin analysis, scripts |

### 6b.6 New risk found

The frozen pipeline was fitted under **scikit-learn 1.5.2**; the workspace `.venv` now carries **1.8.0** and raises `InconsistentVersionWarning` on unpickle. Predictions still reproduced exactly, so this artifact is unaffected in practice — but the serving environment must pin 1.5.2 or the model must be re-verified and re-frozen under the newer version. An unpinned deploy is a silent-behaviour-change risk.

---

## 6c. Stage 3 — migration applied, scikit-learn pinned

### 6c.1 Blast radius was checked before anything was applied

`scripts/_alembic_state_check.py` (read-only) showed the database was **two** revisions behind, not one:

```text
current: 202607270001   (widen ck_m1_regulations_extraction_method)
      -> 202607310001   m1_translation_jobs + m1_translation_workers (NLLB MT queue)
      -> 202608010001   classifier margin + model name   (head)
```

So `alembic upgrade head` would also create two tables belonging to the translation workstream. Both pending migrations are additive — new tables, new nullable columns, nothing rewritten — but applying someone else's pending migration is not a decision to make silently. Approved, then applied.

### 6c.2 Applied and verified against the live schema

Verification queries `information_schema` / `pg_constraint` / `pg_indexes` directly rather than trusting alembic's exit code:

| Object | Live state |
|---|---|
| `classifier_decision_margin` | `numeric(10,6)`, nullable ✓ |
| `classifier_model_name` | `character varying(64)`, nullable ✓ |
| `classifier_confidence` | `numeric(3,2)`, nullable — unchanged ✓ |
| `ck_m1_regulations_classifier_decision_margin` | `CHECK (margin IS NULL OR margin >= 0)` ✓ |
| `ix_m1_regulations_classifier_decision_margin` | btree, `WHERE classifier_decision_margin IS NOT NULL` ✓ |
| `m1_translation_jobs`, `m1_translation_workers` | created ✓ |
| `alembic_version` | `202608010001` ✓ |

Target: `postgresql+asyncpg://…@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres`. Log: `documentation/m1/structure_audit/MIGRATION_APPLIED.txt`.

Incidental observation: `ck_m1_reg_classifier_confidence_range` is `NOT VALID` in Postgres — pre-existing, from the corrective-migration pattern used elsewhere in this schema. It constrains new rows but was never back-validated. Harmless here; worth a `VALIDATE CONSTRAINT` at some point.

### 6c.3 scikit-learn pinned to the 1.5.x line

`enigmatrix-ml/pyproject.toml` had `scikit-learn>=1.4,<2` — which is precisely how the workspace ended up on 1.8.0 while the frozen pipeline was fitted on 1.5.2. Now pinned `>=1.5.2,<1.6` in **both** extras:

- `serving` — the backend must be able to unpickle the frozen artifact. Also now declares `joblib` explicitly instead of relying on it arriving as a transitive dependency of scikit-learn.
- `training` — a model trained under 1.8 and served under 1.5 would silently produce an artifact the server cannot load. Both sides move together or neither does.

**The existing `.venv` still has 1.8.0.** The pin constrains future resolutions; it does not rewrite the current environment. Run `uv sync --extra serving` before trusting a deploy.

---

## 7. What remains

1. ~~Alembic migration for the margin columns~~ — **applied and schema-verified** (§6c.2).
2. ~~Derive `M1_CLASSIFIER_MIN_MARGIN`~~ — **done** (§6b.1). Decide whether to enable `0.40` now or wait for production review data. Nothing is flagged until you set it.
3. ~~Frontend nullable-confidence audit~~ — **done** (§6b.4): nothing consumes the field yet; the stale doc strings were corrected. Re-check when the triage UI is built.
4. ~~Pin scikit-learn~~ — **pinned** in both extras (§6c.3). Still to do: `uv sync --extra serving` so the running environment actually drops from 1.8.0 to the 1.5.x line.
5. ~~Build the triage UI~~ — done after this record. `/admin/m1/pipeline/classifier-review` consumes `GET /classifier-review`, handles `mode='disabled' | 'margin' | 'confidence'`, shows margin as a rank/review signal rather than a percentage, and tolerates `classifier_confidence: null`.
6. **Review and commit the four remaining `enigmatrix-ml` changes** (§5).
7. **`git rm --cached mydata/label_studio.sqlite3`** to stop tracking the annotation DB now that `mydata/` is ignored — deliberately not done here, as it rewrites what future commits contain.
8. **Push** — everything is local. Nothing has left this machine.
9. **Collect genuine EPF/ETF regulations.** 4 training rows and 1 test row means that class's F1 is a one-sample estimate; only more documents fix it, not resampling.
10. ~~Sector-head decision~~ — closed after this record. Do **not** keep a split LinearSVC-category + ONNX-sector production arrangement. The frozen primary is category-only; sector routing remains from existing or expert-maintained `m1_regulation_sectors` rows until a separately evaluated sector model is promoted.

**Standing constraint:** the V6 test split is spent for model selection. Further tuning against it invalidates the 0.9472.

---

## 8. Related

- [[17_M1_Repo_Structure_Map]] · [[18_M1_Dataset_And_Model_Lineage]]
- [[03_FEATURE_CHECKLIST]] — 2026-08-01 section
- [[15_M1_Folder_Reference]] §13
- `00_WORKS_ORGANIZATION_INDEX.md` · `C:\Reasearch\xyz\STRUCTURE.md`
- `documentation/m1/records/ENIGMATRIX_M1_COMPLETE_END_TO_END_RECORD_2026-07-31_2313_IST.md`
