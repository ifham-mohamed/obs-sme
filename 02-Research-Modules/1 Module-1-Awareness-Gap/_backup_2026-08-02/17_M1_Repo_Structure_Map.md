# 17 — Module 1: Workspace and Repository Structure Map

> The physical map of `C:\Reasearch\xyz` — what every top-level folder is, which ones are code, which are data, which are generated, and which are safe to move. Companion to [[13_M1_Folder_Structure_and_Implementation_Flow]] (the designed tree) and [[15_M1_Folder_Reference]] (the per-folder build guides). This document describes the tree **as it exists on disk**, verified by a filesystem audit.
>
> Audit source: `C:\Reasearch\xyz\documentation\m1\structure_audit\STRUCTURE_AUDIT.md`
> Generated: 2026-08-01 · Workspace root spelling is `Reasearch` (not `Research`) and must not be silently corrected.

---

## 1. Why this document exists

Docs 13 and 15 describe the *intended* layout — six folders, one pipeline. The real workspace is larger: it is a monorepo-of-submodules that also accumulated research data, virtual environments, Kaggle bundles, model artifacts and a knowledge graph. Before this audit there was no single page that said which of the 24 top-level directories a contributor may touch and which are generated or disposable.

Three practical questions this answers:

1. If I clone this workspace, what is source and what is derived?
2. Where does a new dataset / model / script / document go?
3. What am I allowed to move without breaking a frozen artifact?

---

## 2. Top-level inventory (measured)

| Entry | Kind | Files | Size | Role | Movable? |
|---|---|---:|---:|---|---|
| `enigmatrix-backend/` | submodule | 474 | 90.3 MB | FastAPI + Celery service, `app/m1/` module home | No — submodule |
| `enigmatrix-frontend/` | submodule | 477 | 6.7 MB | Next.js app, `components/m1/`, `lib/m1/` | No — submodule |
| `enigmatrix-ml/` | submodule | 199 | 133.0 MB | ML package — the `m1/` import root | No — submodule |
| `enigmatrix-infrastructure/` | submodule | 7 | 12.6 KB | Shared runtime (nginx, compose) | No — submodule |
| `enigmatrix-docs/` | dir | 182 | 4.8 MB | **Stale mirror** of the M1 doc series — see §6 | Content only |
| `datasets/` | dir | 37 | 9.0 MB | Frozen M1 training datasets V4→V6 | **No** — hashed in manifests |
| `models/` | dir | 17 | 2.1 MB | Frozen model artifacts (`m1/linearsvc_v6_primary`) | **No** — hashed + path-bound |
| `scripts/` | dir | 31 | 367.9 KB | Flat research/ops script surface | **No** — see §5 |
| `documentation/` | dir | — | 293 KB | Generated records, plans, manuals, audits | Yes — reorganized 2026-08-01 |
| `kaggle_bundle/` | dir | 79 | 2.3 MB | Packaged repo + dataset uploaded to Kaggle | Yes |
| `storage/` | dir | 25 | **7.7 GB** | Runtime artifact store — raw PDFs, OCR cache, model runs | No — runtime |
| `raw/` | dir | 300 | 92.4 MB | Raw downloaded source material | No — data |
| `research/` | dir | 119 | 33.2 MB | Annotation surface, labeling batches, gold standard | No — data |
| `data/` | dir | 25 | 2.7 MB | Golden fixtures for extraction measurement | No — fixtures |
| `mydata/` | dir | 58 | 47.5 MB | Ad-hoc working data | Candidate for archive |
| `archive/` | dir | 31 | 24.0 MB | Retired material | Yes |
| `runs/` | dir | 36 | 878.6 KB | Run outputs / logs | Generated |
| `graphify-out/` | dir | 1747 | 225.4 MB | Knowledge graph — `GRAPH_REPORT.md`, `wiki/` | Generated — `graphify update .` |
| `.venv/` | dir | 59563 | 1.4 GB | Python environment | Generated |
| `venv/` | dir | 860 | 10.6 MB | Second, older environment — redundant | Generated |
| `infra/` | dir | 1 | 1.5 KB | Local infra shim | Yes |
| `.tmp/`, `tmp/`, `.codex-tmp/` | dirs | 12 | 12.5 MB | Tool scratch | Generated |

**Total working set is dominated by non-source data:** `storage/` (7.7 GB) and `.venv/` (1.4 GB) are 95%+ of the workspace. Neither belongs in a backup of the research work; `datasets/`, `models/`, `research/` and `documentation/` are the parts that matter and total under 50 MB.

---

## 3. Root files after the 2026-08-01 tidy

Kept at root because tooling reads them by fixed name:

```text
README.md              AGENTS.md          CLAUDE.md          CONVENTIONS.md
AI_SYNC.md             AI_WORK_LOG.md     STRUCTURE.md       Makefile
pyproject.toml         uv.lock            .python-version    .gitmodules
docker-compose.dev.yml .env / .env.example .pre-commit-config.yaml .aider.conf.yml
```

Moved out of root into `documentation/`:

| Was | Now |
|---|---|
| `AUDIT_READS_AND_SUMMARIES_PLAN.md` | `documentation/plans/` |
| `AUTH_TOKEN_ROTATION_PLAN.md` | `documentation/plans/` |
| `M1_MODULE_REORG_PLAN.md` | `documentation/plans/` |
| `SETUP_AND_USER_MANUAL.md` | `documentation/manuals/` |
| `ENIGMATRIX_FULL_CONTEXT_AND_M1_ANALYSIS.md` | `documentation/_archive/` — superseded, per `06_CLEANUP_REPORT.md` |
| `readme` (0 bytes) | `documentation/_archive/readme.empty` |

All moves used `git mv`, so `git log --follow` survives — the same rule §0.4 of [[08_M1_MODULE_REORG_PLAN|the module reorg plan]] set for code.

---

## 4. `documentation/` — the new shape

```text
documentation/
├── m1/
│   ├── records/          ENIGMATRIX_M1_COMPLETE_END_TO_END_RECORD_*.md   (5,642 lines)
│   └── structure_audit/  STRUCTURE_AUDIT.md · DOCS_SYNC_REPORT.md · MOVE_MANIFEST.md
├── plans/                cross-cutting design plans
├── manuals/              operator-facing manuals
└── _archive/             superseded documents (never deleted, only demoted)
```

`scripts/build_enigmatrix_m1_complete_record.py` writes into `documentation/m1/records/`; `scripts/_audit_structures.py` and `scripts/_docs_sync_and_reorg.py` write into `documentation/m1/structure_audit/`. Re-running any of them is idempotent.

---

## 5. Why `scripts/` was **not** reorganized

The obvious tidy — grouping 31 flat scripts into `dataset/`, `model/`, `eval/` subfolders — was evaluated and **rejected**. A path search found **26 files** that reference scripts by their current path, including:

- `enigmatrix-docs/m1/*` and `enigmatrix-docs/plans/*` documented commands,
- `research/data/PHASE3_ANNOTATION_RUNBOOK.md` and `research/data/labeling/*` runbooks,
- `AI_WORK_LOG.md` session entries,
- `enigmatrix-ml/tests/evaluation/test_baseline_script.py`,
- the frozen end-to-end record's own appendix paths.

Moving the scripts would invalidate every one of those references to buy cosmetic tidiness. The scripts stay flat; the **logical** grouping is documented instead in `C:\Reasearch\xyz\STRUCTURE.md` §4, which indexes each script by lifecycle stage. This is the same reasoning as the contract-preservation rule in the module reorg plan: identity is decoupled from location, and a documented path is a contract.

---

## 6. The two copies of this documentation set

`C:\Reasearch\xyz\enigmatrix-docs\m1\` contains a second copy of the numbered M1 doc series. A byte-level comparison on 2026-08-01 found:

| Measure | Result |
|---|---:|
| Markdown files — repo set | 88 |
| Markdown files — vault set | 117 |
| Shared filenames | 36 |
| Byte-identical | 2 |
| **Diverged** | **34** |
| Vault copy newer | 31 of 34 |

The divergence is not drift at the margins. `15_M1_Folder_Reference.md` is 5,932 B in the repo against 101,608 B in the vault; `14_M1_Tracking_Workflows.md` is 7,733 B against 109,896 B. The repo copies are May/July snapshots that were never updated after the vault became the working surface.

**Canonicity rule (adopted 2026-08-01):** the Obsidian vault at
`E:\Obsidian\sme\02-Research-Modules\1 Module-1-Awareness-Gap\` is the **single source of truth** for the M1 documentation set. `enigmatrix-docs/m1/` is a stale mirror and must be refreshed *from* the vault, never merged back into it.

The repo set does hold 52 files the vault lacks — the `NN_M1_N_*` deep-dive sub-series (for example `05_M1_3_LoRA_Hyperparameter_Justification.md`). Those are not stale duplicates; they are companion documents that were never migrated. Full evidence table: `documentation/m1/structure_audit/DOCS_SYNC_REPORT.md`.

---

## 7. Where things go

| I have… | It goes in… | Then |
|---|---|---|
| A new frozen dataset version | `datasets/m1_regulations_v<N>_<rows>_<variant>/` | Write `dataset_manifest_v<N>.json` with per-split SHA256 |
| A promoted model | `models/m1/<name>_v<N>_<role>/` | Include `model_registry.json`, `labels.json`, `SHA256SUMS.json` |
| A one-off analysis script | `scripts/` (flat) | Add a row to `STRUCTURE.md` §4 |
| A generated report | `documentation/m1/records/` | Never hand-edit; regenerate from its script |
| A design plan | `documentation/plans/` | Link it from `AI_WORK_LOG.md` |
| A research/writing document | The **vault**, not the repo | See §6 |
| Something superseded | `documentation/_archive/` | Demote, do not delete |

---

## 8. Cross-references

- **Designed tree and Stage A→G flow:** [[13_M1_Folder_Structure_and_Implementation_Flow]]
- **Per-folder build guides and status:** [[15_M1_Folder_Reference]]
- **Dataset and model lineage V4→V6:** [[18_M1_Dataset_And_Model_Lineage]]
- **Module reorg convention (`m<N>/` per layer):** [[08_M1_MODULE_REORG_PLAN]]
- **Works-folder layout and naming rules:** `final/works/00_WORKS_ORGANIZATION_INDEX.md`
- **Repo-side mirror of this map:** `C:\Reasearch\xyz\STRUCTURE.md`
