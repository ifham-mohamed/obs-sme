# M1 — Model Integration, Workspace Reorganization and Documentation Sync
## Complete session record, 2026-08-01

> Everything executed in one working session: from generating the frozen end-to-end research record, through auditing and reorganizing both the code workspace and the Obsidian vault, to wiring the frozen classifier into the backend and applying its database migration.
>
> **Scope of authority:** all work is local. Nothing was pushed to any remote. Nothing was deleted — superseded material was demoted to `_archive/` folders. One database was modified (§7), with explicit approval and a read-only blast-radius check first.
>
> Companion documents: the stage-by-stage detail lives in `LOG_AND_WORKS/2026-08-01_M1_INTEGRATION_REORG_AND_SYNC_WORK_RECORD.md`. This file is the session-level index and decision record.

---

## 1. Starting position

The frozen LinearSVC primary classifier existed and had been verified, but nothing downstream knew about it:

| Area | State at session start |
|---|---|
| Frozen V6 dataset + model | On disk, **untracked** — existed only on one machine |
| `LinearSVCGazetteInference` | Written in the ML package, called by nothing |
| Backend classifier service | Loaded only the never-promoted ONNX model |
| Docs 05 / 06 / 11 | Still described XLM-R as the production architecture |
| `enigmatrix-docs/m1/` | Second copy of the doc series, silently drifted |
| Workspace root | 15 loose planning `.md` files, duplicate index in the vault |

---

## 2. Environment constraint that shaped the whole session

**The Linux sandbox was unavailable for the entire session** (`VM service not running`). Every command therefore ran on the Windows host through the Run dialog (`cmd /k py -3 …`), because terminal applications are granted at click-only tier and cannot be typed into directly.

Consequences worth recording, because they explain the shape of the work:

- Nothing could be piped or explored interactively — each step had to be written as a complete, self-verifying Python script that wrote its own log file.
- That constraint turned out to be a benefit: every stage left a regenerable artifact (`STRUCTURE_AUDIT.md`, `DOCS_SYNC_REPORT.md`, `MOVE_MANIFEST.md`, `VERIFY.txt`, `MIGRATION_APPLIED.txt`) instead of scrollback that disappears.
- One chained `cmd` invocation silently dropped its second half; it was replaced with a `.cmd` file and a `-F` message file (§9).

---

## 3. Stage 0 — the frozen end-to-end research record

The generator was written verbatim to `scripts/build_enigmatrix_m1_complete_record.py` (2,068 lines) and executed.

| Run | Output | Bytes | Lines | SHA256 |
|---|---|---:|---:|---|
| First | `documentation/…RECORD_2026-07-31_2313_IST.md` | 299,954 | 5,642 | `E9557A23…E011F` |
| After the reorganization | `documentation/m1/records/…` (same filename) | 299,967 | 5,642 | `C959B4A5…E40E` |

All seventeen parts populated: static chronology, live artifact hashes, live git state, and thirteen source appendices.

**First substantive finding.** The document's *live* git section contradicted its own retained Step-40 record: the static log claimed two modified files, the live query found six modified plus untracked `datasets/`. The document records both truthfully rather than reconciling them — retained history as history, measured state as measurement.

---

## 4. Stage 1 — audit of both trees

`scripts/_audit_structures.py` produced a 178,899-byte inventory.

### 4.1 The workspace is mostly not source

| Category | Size |
|---|---:|
| `storage/` (runtime artifacts) | 7.7 GB |
| `.venv/` | 1.4 GB |
| `graphify-out/` (generated graph) | 225 MB |
| `raw/` | 92 MB |
| **The research work that matters** — `datasets/`, `models/`, `research/`, `documentation/` | **< 50 MB** |

A backup of the whole workspace is 95% noise. This is now stated in `STRUCTURE.md` so the distinction is not rediscovered each time.

### 4.2 The vault duplicate

`M1_PROGRAM_READINESS_MASTER_INDEX.md` existed twice with **byte-identical** content (both `9B328ADC38BB5BFF`) — once in `PROGRAM_READINESS/` and once in `PROGRAM_READINESS/log and works/`.

### 4.3 The documentation set had forked

This was the largest finding of the session. `C:\Reasearch\xyz\enigmatrix-docs\m1\` holds a second copy of the numbered M1 series:

| Measure | Value |
|---|---:|
| Repo markdown files | 88 |
| Vault markdown files | 117 |
| Shared filenames | 36 |
| Byte-identical | **2** |
| Diverged | **34** |
| Vault copy newer | **31 of 34** |

Not marginal drift. `15_M1_Folder_Reference.md` was 5,932 B in the repo against **101,608 B** in the vault; `14_M1_Tracking_Workflows.md` 7,733 B against 109,896 B. The repo copies were May/July snapshots abandoned when the vault became the working surface.

**Decision: the vault is canonical.** The repo mirror is refreshed *from* it, never merged back. Recorded in `STRUCTURE.md` §5, `17_M1_Repo_Structure_Map` §6 and `15_M1_Folder_Reference` §13.4.

The repo set does hold **52 files the vault lacks** — the `NN_M1_N_*` deep-dive sub-series. Those are companions, not stale duplicates, and were left untouched.

---

## 5. Stage 1 — reorganization

Applied through a dry-run-first script; every move recorded in `MOVE_MANIFEST.md`.

### 5.1 Vault

| Change | Reason |
|---|---|
| `PROGRAM_READINESS/log and works/` → `LOG_AND_WORKS/` | Spaces in a path break shell commands and code-block references |
| Duplicate master index → `_archive/duplicates/` | Two canonical indexes is one too many; demoted, not deleted |
| `_REORGANIZE_works.ps1` → `_tooling/` | A maintenance script among documents reads like a document |

No wikilinks broke: Obsidian resolves `[[…]]` by basename, and no `.md` spelled out the old folder path. Only `.obsidian/workspace.json` (recent files) referenced it, and that self-heals.

### 5.2 Repository

Five root planning documents moved into `documentation/{plans,manuals,_archive}/` via **`git mv`**, so `log --follow` survives — the same history-preserving rule §0.4 of the module reorg plan set for code. Generated records and audits consolidated under `documentation/m1/`.

### 5.3 The move that was rejected

Grouping the 31 flat scripts into `dataset/`, `model/`, `eval/` subfolders was evaluated and **not done**. A path search found **26 files** referencing scripts by their current path: `enigmatrix-docs/`, the Phase-3 annotation runbooks, `AI_WORK_LOG.md`, `enigmatrix-ml/tests/evaluation/test_baseline_script.py`, and the frozen record's own appendices.

Tidiness was not worth invalidating 26 documented commands. The lifecycle grouping is indexed in `STRUCTURE.md` §4 instead. *A documented path is a contract* — the same principle the backend reorg used to preserve Celery task names.

Verification: `missing=0 stale=0`.

### 5.4 Mirror refresh

33 files refreshed vault → repo; 1 kept because the repo copy was genuinely newer (`04_API_AND_PAGES_REFERENCE.md`); 2 already identical. Every overwritten file was copied to `enigmatrix-docs/_pre_sync_backup_<timestamp>/` first.

---

## 6. Stage 2 — backend integration

### 6.1 A crash found by reading, not by running

`classify_gazette.py` contained:

```python
row.classifier_confidence = Decimal(str(round(result["confidence"], 2)))
result["confidence"] < MIN_CONFIDENCE
```

The LinearSVC engine returns `confidence: None` by design — its `decision_function` output is an uncalibrated margin, not a probability. Pointing the existing service at the new engine would have raised `TypeError` on **every row**. Found by reading the call site before switching backends.

### 6.2 What was built

`classifier_service.py` became a two-backend service:

| Setting | Default |
|---|---|
| `M1_CLASSIFIER_BACKEND` | `linearsvc` (or `onnx`) |
| `M1_MODEL_LINEARSVC_DIR` | `models/m1/linearsvc_v6_primary` |
| `M1_CLASSIFIER_MIN_CONFIDENCE` | `0.55` — ONNX path only |
| `M1_CLASSIFIER_MIN_MARGIN` | *unset* — LinearSVC path |

Model paths resolve against the process cwd first, then the workspace root, because artifacts live one level above the backend package and the service may start from either directory.

### 6.3 The threshold was derived, not chosen

`scripts/derive_m1_margin_threshold.py`, on the **validation split only** — the test split stays reserved, since selecting an operating point on it would invalidate the reported 0.9472 test macro-F1.

Margins separate cleanly:

| Group | n | median margin |
|---|---:|---:|
| Correct | 157 | **1.5954** |
| Incorrect | 9 | **0.3896** |

| Threshold | Flagged | % of split | Error recall | Flag precision |
|---:|---:|---:|---:|---:|
| 0.20 | 5 | 3.0% | 22.2% | 40.0% |
| **0.40** | **11** | **6.6%** | **55.6%** | **45.5%** |
| 0.70 | 21 | 12.7% | 77.8% | 33.3% |

**It ships unset.** Nine errors in 166 rows means one reclassified row moves error recall by ~11%. Two errors are also unreachable by any margin rule — `GZT_2487_01` (1.2670) and `GZT_2479_56` (1.4632) are *confidently wrong*, which is exactly what an uncalibrated margin cannot detect.

Sanity check: validation accuracy recomputed from the frozen artifact came out `0.9457831325301205` — identical to the frozen figure.

### 6.4 The review queue's real defect

Applying `classifier_confidence < 0.55` on a backend that never writes confidence returns zero rows — **indistinguishable from "nothing needs review"**. The endpoint now selects its signal from the active backend and reports which one it used:

| Backend | Predicate | `mode` |
|---|---|---|
| `onnx` | `classifier_confidence < 0.55` | `confidence` |
| `linearsvc` + threshold | `classifier_decision_margin < threshold` | `margin` |
| `linearsvc`, no threshold | *(no query)* | `disabled` |

### 6.5 Frontend

Nothing consumes `classifier-review` or renders `classifier_confidence` yet, so there was nothing to break. Two stale strings in `lib/m1/docs.ts` still described a 12-category XLM-R dual-head with a `confidence < 0.70` rule; both corrected.

---

## 7. Stage 3 — database migration

### 7.1 Blast radius checked before acting

A read-only state check showed the database was **two** revisions behind, not one:

```text
current: 202607270001
      -> 202607310001   m1_translation_jobs + m1_translation_workers
      -> 202608010001   classifier margin + model name   (head)
```

`upgrade head` would therefore also create two tables belonging to the translation workstream. Both additive — but applying someone else's pending migration is not a silent decision. **Approved explicitly, then applied.**

### 7.2 Verified against the live schema

Verification queried `information_schema`, `pg_constraint` and `pg_indexes` directly rather than trusting alembic's exit code:

| Object | Live state |
|---|---|
| `classifier_decision_margin` | `numeric(10,6)`, nullable ✓ |
| `classifier_model_name` | `varchar(64)`, nullable ✓ |
| `classifier_confidence` | `numeric(3,2)` — unchanged ✓ |
| CHECK constraint | `margin IS NULL OR margin >= 0` ✓ |
| Partial index | `WHERE classifier_decision_margin IS NOT NULL` ✓ |
| `m1_translation_jobs`, `m1_translation_workers` | created ✓ |
| `alembic_version` | `202608010001` ✓ |

Target: Supabase session pooler, `aws-0-ap-southeast-1`, port 5432.

`classifier_confidence` was deliberately left alone. A row now carries a confidence **or** a margin depending on which engine classified it, and never a margin coerced into the probability column.

### 7.3 scikit-learn pinned

`enigmatrix-ml/pyproject.toml` had `scikit-learn>=1.4,<2` — precisely how the workspace reached 1.8.0 while the frozen pipeline was fitted under 1.5.2. Now `>=1.5.2,<1.6` in **both** the `serving` and `training` extras: a model trained under one line must be loadable by the other. `joblib` is now an explicit serving dependency rather than a transitive one.

---

## 8. Commits — all local

| Repo | Hash | Subject |
|---|---|---|
| `enigmatrix-backend` | `8930d2a` | Backend selection, optional confidence |
| `enigmatrix-ml` | `9c96e30` | `LinearSVCGazetteInference` + dual exports + tests |
| root | `18cc93f` | Frozen V6 evidence + workspace reorganization — **265 files, 231,653 insertions** |
| `enigmatrix-backend` | `e967e88` | Migration, model columns, persistence, review queue |
| `enigmatrix-frontend` | `1c36b37` | Corrected in-app pipeline description |
| root | `eae890c` | `.env.example` contract + margin analysis |
| root | `d21b7be` | Alembic chain-checker fix |
| `enigmatrix-ml` | `45e99c3` | scikit-learn 1.5.x pin |
| root | `9036041` | Migration applied + live schema record |

The root commit `18cc93f` is the important one: the frozen V6 parquets, the LinearSVC pipeline, the scripts that produced them and the labelling gold standard entered version control **for the first time**.

### Ignore decisions

| Path | Decision | Reason |
|---|---|---|
| `mydata/` | Ignored | Label Studio DB + exports — annotator account data, rebuildable from exported batches |
| `tmp/`, `runs/`, `*.sqlite3` | Ignored | Scratch / generated |
| `enigmatrix-ml/datasets/` | Ignored | Superseded pre-V4 generations; canonical sets tracked at root |
| `research/data/labeling/` | **Tracked** | Irreplaceable human annotation evidence |

---

## 9. Problems hit, and how they were handled

| Problem | Resolution |
|---|---|
| Linux sandbox unavailable all session | Every step written as a self-logging script, executed via the Windows Run dialog |
| Terminal apps typing-blocked (click tier) | Run dialog is full tier; used for all invocations |
| A chained `cmd` invocation silently dropped its second half | Replaced with a `.cmd` file plus a `-F` commit-message file |
| **My alembic chain checker reported 4 heads and 2 dangling parents on a healthy tree** | Checker defect, not schema: its regex missed `revision = "x"` without a type annotation and could not parse a merge migration's tuple `down_revision`. Fixed, re-run, verdict now keys on head count: **53 migrations, single head** |
| Markdown hard-break trailing spaces stripped when transcribing the generator | Cosmetic; noted rather than silently "fixed" |
| Frozen pipeline unpickled under a newer scikit-learn | Predictions verified identical, then the version pinned (§7.3) |

Recording the checker defect matters: a verification script that cries wolf is worse than none, because the next person learns to ignore it.

---

## 10. Documents created and updated

**Created**

```text
17_M1_Repo_Structure_Map.md                        (vault, module root)
18_M1_Dataset_And_Model_Lineage.md                 (vault, module root)
final/works/00_WORKS_ORGANIZATION_INDEX.md
final/works/PROGRAM_READINESS/LOG_AND_WORKS/2026-08-01_M1_INTEGRATION_REORG_AND_SYNC_WORK_RECORD.md
final/works/PROGRAM_READINESS/M1_MODEL_INTEGRATION_AND_REORGANIZATION_SESSION_RECORD_2026-08-01.md   (this file)
C:\Reasearch\xyz\STRUCTURE.md
```

**Updated**

```text
03_FEATURE_CHECKLIST.md          new 2026-08-01 section + 3 status rows
15_M1_Folder_Reference.md        §13 added, model status rows corrected
05_M1_Model_Architecture.md      §4 outcome callout — architecture not promoted
06_M1_Training_Evaluation.md     acceptance criterion marked NOT MET, with numbers
11_M1_API_Reference.md           nullable confidence + backend switch
```

Docs 05, 06 and 11 were **annotated, not rewritten**. The reasoning that led to XLM-R was sound; deleting it would falsify the research narrative. Each now states its own outcome instead.

**Evidence artifacts** (all regenerable)

```text
C:\Reasearch\xyz\documentation\m1\
├── records\ENIGMATRIX_M1_COMPLETE_END_TO_END_RECORD_2026-07-31_2313_IST.md
├── analysis\MARGIN_THRESHOLD_ANALYSIS.md · margin_threshold_summary.json
└── structure_audit\
    ├── STRUCTURE_AUDIT.md · DOCS_SYNC_REPORT.md · MOVE_MANIFEST.md
    ├── VERIFY.txt · SYNC_AND_COMMIT_LOG.txt
    └── STAGE2_VERIFY_LOG.txt · ALEMBIC_STATE.txt · MIGRATION_APPLIED.txt
```

---

## 11. Verification performed

| Check | Result |
|---|---|
| Post-move file verification | `missing=0 stale=0` |
| `py_compile`, 5 backend modules | exit 0 |
| Backend imports resolve | `backend=linearsvc`, `min_margin=None`, model dir resolved |
| Non-slow M1 model tests | **26 passed, 2 deselected** (run 3×) |
| Alembic chain | 53 migrations, **single head** `202608010001` |
| Live schema after migration | All 7 objects confirmed present |
| Frozen model reproduction | validation accuracy `0.9457831325301205`, identical to frozen |

---

## 12. Open items

**Blocking a deploy**

1. `uv sync --extra serving` — the pin constrains future resolution; the existing `.venv` still holds scikit-learn 1.8.0.
2. Decide whether to set `M1_CLASSIFIER_MIN_MARGIN=0.40`. The column and index now exist, so it is one environment variable away from live — but it routes ~6.6% of rows to human review, which is a capacity question.

**Next build work**

3. Triage UI against `GET /classifier-review`: must handle `mode='disabled'`, show the margin as a **rank** rather than a percentage, and tolerate `classifier_confidence: null`.
4. ~~Sector-head decision~~ — closed after this record. Do **not** keep a split LinearSVC-category + ONNX-sector production arrangement. The frozen primary is category-only; sector routing remains from existing or expert-maintained `m1_regulation_sectors` rows until a separately evaluated sector model is promoted.

**Housekeeping**

5. Review and commit the four remaining `enigmatrix-ml` changes (`samplers.py`, `architecture.py`, `config.py`, `pyproject.toml` predate this session).
6. `git rm --cached mydata/label_studio.sqlite3` — now ignored, but still tracked from before.
7. Push. Everything is local; nothing has left this machine.
8. `VALIDATE CONSTRAINT ck_m1_reg_classifier_confidence_range` — pre-existing `NOT VALID` constraint found incidentally.

**Research**

9. Collect genuine EPF/ETF regulations. 4 training rows and 1 test row makes that class's F1 a one-sample estimate; only more documents fix it, not resampling.
10. **The V6 test split is spent for model selection.** Further tuning against it invalidates the 0.9472.

---

## 13. Reproducing any of this

```powershell
py -3 C:\Reasearch\xyz\scripts\build_enigmatrix_m1_complete_record.py   # end-to-end record
py -3 C:\Reasearch\xyz\scripts\_audit_structures.py                     # tree + git + duplicates
py -3 C:\Reasearch\xyz\scripts\_docs_sync_and_reorg.py                  # vault-vs-repo divergence (dry-run)
py -3 C:\Reasearch\xyz\scripts\_verify_reorg.py                         # post-move verification
py -3 C:\Reasearch\xyz\scripts\derive_m1_margin_threshold.py            # margin threshold sweep
py -3 C:\Reasearch\xyz\scripts\_alembic_state_check.py                  # read-only migration state
```

## 14. Related

- **Stage detail:** `LOG_AND_WORKS/2026-08-01_M1_INTEGRATION_REORG_AND_SYNC_WORK_RECORD.md`
- **Program index:** `M1_PROGRAM_READINESS_MASTER_INDEX.md`
- **Status ledger:** [[03_FEATURE_CHECKLIST]]
- **Workspace map:** [[17_M1_Repo_Structure_Map]] · `C:\Reasearch\xyz\STRUCTURE.md`
- **Dataset and model lineage:** [[18_M1_Dataset_And_Model_Lineage]]
- **Folder reference:** [[15_M1_Folder_Reference]] §13
- **Works layout rules:** `../00_WORKS_ORGANIZATION_INDEX.md`
