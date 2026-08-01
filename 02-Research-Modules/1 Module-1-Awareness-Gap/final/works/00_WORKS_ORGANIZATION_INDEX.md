# 00 — `works/` Organization Index

> How the `final/works/` tree is laid out, what belongs in each folder, and the naming rules for anything added next. Read this before creating a new document here.
>
> Last reorganized: 2026-08-01. Move record: `C:\Reasearch\xyz\documentation\m1\structure_audit\MOVE_MANIFEST.md`.

---

## 1. The layout

```text
final/works/
├── 01_MASTER_PROJECT_OVERVIEW.md          ← numbered program-level documents
├── 02_MEMBER1_MODULE1_REPORT.md
├── 03_FEATURE_CHECKLIST.md                ← the living status ledger
├── 04_API_AND_PAGES_REFERENCE.md
├── 05_MANUAL_TESTING_GUIDE.md
├── 06_CLEANUP_REPORT.md
├── 07_SETUP_AND_USER_MANUAL.md
├── 08_M1_MODULE_REORG_PLAN.md
├── 09_PHASE2_MEASUREMENT_EQS_UPGRADE.md
├── 10_PIPELINE_STAGING_AND_MANUAL_STEPPING.md
├── 11_CLASSIFIER_FREEZE_AND_INTEGRATION.md
├── 12_TRILINGUAL_TRANSLATION_PIPELINE.md
│
├── PHASE1_FOUNDATION/                     ← one folder per delivery phase
├── PHASE2_INGEST_EXTRACTION/
├── PHASE3_ANNOTATION_CLASSIFICATION/
├── PHASE4_SCHEDULERS_ALERTS/
├── PHASE5_RESEARCH_FINDINGS/
│
├── PROGRAM_READINESS/                     ← operator manuals + runbooks
│   └── LOG_AND_WORKS/                     ← dated session logs and chronologies
├── RESEARCH_DESIGN/                       ← scope and methodology decisions
│
├── _tooling/                              ← scripts that maintain this tree
└── _archive/                              ← superseded / duplicate documents
    └── duplicates/
```

**Two kinds of document live here.** Numbered files at the root are *program-level and durable* — they describe the whole module and get updated in place. Everything inside a `PHASE*/` folder is *incident- or workstream-scoped* — it is written once about one problem and then mostly read, not revised.

---

## 2. What goes where

| Folder | Contains | Naming |
|---|---|---|
| root, numbered | Program-level documents that stay current | `NN_TITLE_IN_CAPS.md`, next free number |
| `PHASE<N>_<NAME>/` | Phase analysis + gap-closure plan | `PHASE<N>_<NAME>_ANALYSIS.md`, `PHASE<N>_GAP_CLOSURE_PLAN.md` |
| `PHASE<N>_<NAME>/<issue_slug>/` | One folder per concrete issue | `<ISSUE_SLUG>_ANALYSIS.md` + `<ISSUE_SLUG>_FIX_PLAN.md` |
| `PROGRAM_READINESS/` | Manuals and runbooks a human follows | `M1_<TOPIC>_MANUAL.md` / `_RUNBOOK.md` / `_PLAN.md` |
| `PROGRAM_READINESS/LOG_AND_WORKS/` | Dated execution logs and chronologies | `YYYY-MM-DD_<TOPIC>.md` or `NN_<TOPIC>_YYYY-MM-DD.md` |
| `RESEARCH_DESIGN/` | Scope, sampling, methodology decisions | `<TOPIC>_PLAN.md` |
| `_tooling/` | Maintenance scripts | leading underscore |
| `_archive/` | Anything superseded | keep the original filename |

### Naming rules

1. **`SCREAMING_SNAKE_CASE.md` for documents, `lower_snake_case/` for issue folders.** This is already the dominant pattern; it is now the rule.
2. **No spaces in folder names.** `log and works` was renamed to `LOG_AND_WORKS` on 2026-08-01 for exactly this reason.
3. **A document lives in exactly one place.** If two folders both want it, one gets the file and the other gets a link.
4. **Analysis and plan are separate files.** `_ANALYSIS.md` states what is true; `_FIX_PLAN.md` states what will change. Keeping them apart is what makes the analysis reusable after the fix ships.
5. **Dated documents carry an ISO date** (`2026-07-31`), never `final`, `new`, or `v2`.
6. **Nothing is deleted.** Superseded material is demoted to `_archive/` with its filename intact.
7. **Escape the pipe in wikilinks inside tables.** `[[Target#Heading\|Alias]]`, not `[[Target#Heading|Alias]]`. An unescaped `|` is a column separator to the Markdown parser, so the link silently splits the row into an extra column. This was wrong in 136 cells of `03_FEATURE_CHECKLIST.md` until 2026-08-01.
8. **A phase folder carries both halves of the pair.** If a `PHASE<N>_*_ANALYSIS.md` exists, a `PHASE<N>_GAP_CLOSURE_PLAN.md` should exist beside it — an analysis with no plan reads as a phase nobody intends to finish.

---

## 3. What changed on 2026-08-01

| Change | Reason |
|---|---|
| `PROGRAM_READINESS/log and works/` → `PROGRAM_READINESS/LOG_AND_WORKS/` | Spaces in a path break shell commands and code-block references; the rest of the tree is already SCREAMING_CASE |
| `LOG_AND_WORKS/M1_PROGRAM_READINESS_MASTER_INDEX.md` → `_archive/duplicates/` | Byte-identical duplicate (both `9B328ADC38BB5BFF`) of the copy in `PROGRAM_READINESS/`; two canonical indexes is one too many |
| `_REORGANIZE_works.ps1` → `_tooling/` | A maintenance script sitting among documents reads like a document |
| Added `00_WORKS_ORGANIZATION_INDEX.md` | This file — the tree had no map |

---

## 3a. What changed later on 2026-08-01 — documentation gap-closure

A second pass audited all 19 module-root documents and all files in this tree against the repository's actual state, and added the five documents that shipped work had no home for.

| Added | Why it did not exist |
|---|---|
| `11_CLASSIFIER_FREEZE_AND_INTEGRATION.md` | The frozen classifier lived only in a session record and in vault docs 17/18 — no program-level document in this tree |
| `12_TRILINGUAL_TRANSLATION_PIPELINE.md` | The NLLB pipeline shipped 2026-07-31 and was mentioned in five files but specified in none of them |
| `PHASE5_RESEARCH_FINDINGS/PHASE5_GAP_CLOSURE_PLAN.md` | Phase 5 was the only phase with an `_ANALYSIS` and no `_GAP_CLOSURE_PLAN` — rule 4 of §2 says analysis and plan are separate files, and Phase 5 had only half the pair |
| `PHASE3_ANNOTATION_CLASSIFICATION/classifier_model_training/CLASSIFIER_MODEL_SELECTION_ANALYSIS.md` | The issue folder held a *readiness plan* with no record of what the training produced |
| `PHASE2_INGEST_EXTRACTION/observability_console/OBSERVABILITY_CONSOLE_ANALYSIS.md` | The 2026-07-28 console rebuild had zero coverage anywhere in this tree |

Numbered root documents now run **00–12**. The next free number is **13**.

Also corrected in `03_FEATURE_CHECKLIST.md`: 136 wikilink cells contained an unescaped `|` inside a Markdown table, which splits every such row into a spurious extra column in Obsidian. All are now `\|`, and 7 section headers that had been padded to 5 columns to compensate are back to 3. **When adding a `[[Target#Heading|Alias]]` link inside a table, escape the pipe** — this is now a naming rule (§2, rule 7).

---

The canonical program-readiness index is now, and only is:

```text
final/works/PROGRAM_READINESS/M1_PROGRAM_READINESS_MASTER_INDEX.md
```

No wikilinks needed rewriting: Obsidian resolves `[[M1_PROGRAM_READINESS_MASTER_INDEX]]` by basename, and a repository-wide search found no `[[...]]` link that spelled out the old folder path. Only `.obsidian/workspace.json` (the recent-files list) still references it, and that self-heals.

---

## 4. Related indexes

- **Program readiness master index:** `PROGRAM_READINESS/M1_PROGRAM_READINESS_MASTER_INDEX.md`
- **Final-report context index:** `PROGRAM_READINESS/LOG_AND_WORKS/00_FINAL_REPORT_CONTEXT_INDEX.md`
- **Module documentation map:** [[00_INDEX]]
- **Status ledger:** [[03_FEATURE_CHECKLIST]]
- **Repository/workspace map:** [[17_M1_Repo_Structure_Map]]
- **Dataset and model lineage:** [[18_M1_Dataset_And_Model_Lineage]]
- **Classifier freeze and integration:** [[11_CLASSIFIER_FREEZE_AND_INTEGRATION]]
- **Trilingual translation pipeline:** [[12_TRILINGUAL_TRANSLATION_PIPELINE]]
