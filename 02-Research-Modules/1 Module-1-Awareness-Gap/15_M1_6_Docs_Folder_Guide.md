# 15_M1_6 — `enigmatrix-docs/m1/` Folder Build Guide

> Companion to [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) — build guide for the docs folder itself.
> **Implementation status snapshot:** ✅ 61 docs shipped (12 main + 29 backend sub-step companions + 1 folder spec + 1 tracking parent + 9 tracking companions + 1 folder-ref parent + 6 folder guides + 1 roadmap + this README).

## Purpose

`enigmatrix-docs/m1/` is the canonical knowledge base for Module 1 — research framing, technical specs, sub-step deep-dives, tracking workflows, folder + dev guides. It's the only folder in this guide series that's *fully shipped today*. The guide exists so a contributor adding a new M1 doc knows the conventions: numbering, skeleton, badges, cross-link patterns. It is also the entry point for "where in the docs do I write X?" — naming + placement decisions.

## Files in this folder

Doc 13's tree summary line for this folder is `enigmatrix-docs/m1/ ├── 01_M1_*.md … 12_M1_*.md ├── 13_M1_Folder_Structure_and_Implementation_Flow.md └── NN_M1_N_*.md (29 sub-step companions)`. As of this pass, 14, 15, and 16 also exist. The doc series is:

| Series | What it covers | Count | Skeleton |
|---|---|---|---|
| `01_M1_*` through `12_M1_*` | Main research + design docs (research problem, data, collection, preprocessing, model, training, deployment, system arch, annotation, multilingual, API, monitoring) | 12 | Long-form prose with section headings; each is a self-contained chapter |
| `NN_M1_M_*.md` (backend sub-step companions) | Sub-step deep-dives under each of `01..12` | 29 | Locked 7-section skeleton: Purpose → Detailed process → Tech choices → Worked example → Failure modes → Validation → Cross-references |
| `13_M1_Folder_Structure_*` | The folder spec (what every file owns) | 1 | Custom shape — folder map + per-file role table + implementation flow |
| `14_M1_Tracking_Workflows.md` + `14_M1_N_*.md` | Frontend tracking workflows (parent + 9 companions) | 10 | Parent is an index; sub-step companions use the locked 7-section skeleton |
| `15_M1_Folder_Reference.md` + `15_M1_N_*.md` | Per-folder build guides (this series — parent + 6 companions) | 7 | Locked sub-folder skeleton: Purpose → Files table → How to start → Dependencies → Tests → Cross-refs |
| `16_M1_Development_Roadmap.md` | Sequenced "start here" guide | 1 | Phase-based; each phase has steps with "Do this next" call-outs |
| `README.md` | Index of everything above | 1 | Document Index table + Sub-Step Companions table + cross-refs |

**Total: 61 files in `enigmatrix-docs/m1/`** as of this pass.

## How to add a new doc

The conventions are deliberate — a new doc should slot into one of these patterns:

### 1. Extending an existing main doc (`01..12`)

If the new content is a sub-step deep-dive that belongs under a parent (e.g. expanding `04_M1_Preprocessing_Pipeline.md` with a new chunking variant), add a sub-step companion: `04_M1_4_<Title>.md`. Use the locked 7-section skeleton. Update the parent doc's "Sub-step companions" header line to link to the new file. Update `README.md` Sub-Step Companions table.

### 2. New top-level main doc (rare)

If the new content is a *new* major topic that doesn't fit under 01–16, take the next available number (17, 18, ...) and pick a skeleton (long-form chapter or new sub-step parent). Add a row to `README.md` Document Index. Cross-link from related existing docs.

### 3. New folder build guide

If a new top-level project folder is added (e.g. an `infra/` folder lands), create `15_M1_<N>_<Folder>_Folder_Guide.md` using the locked sub-folder skeleton. Update `15_M1_Folder_Reference.md` Index table. Update `README.md`.

### 4. Conventions to obey

- **Naming.** `NN_M1_<TitleSnakeCase>.md` for main docs; `NN_M1_M_<TitleSnakeCase>.md` for sub-step companions. `NN` zero-padded to 2 digits (`01`, `02`, …, `16`); sub-step suffix is just `1..9` (not zero-padded).
- **Status badges.** Every sub-step companion + folder guide opens with `> **Implementation status:** ✅ Shipped | 🟡 Partial | 🔲 Deferred` in the header. Honest — never `✅` for code that doesn't exist.
- **Cross-refs.** Every doc has a "Cross-references" section at the bottom. Link to the parent + roadmap + relevant detail docs.
- **Worked examples.** Use the seeded demo regulations (`VAT_2024_AMD`, `EPF_2024_RATE`, multi-pin adapter from [02_M1_4](02_M1_4_Worked_Examples_All_Tables.md)). No PII; no real SME names.
- **EN-only.** Doc body content is English. Trilingual labels go in `frontend/messages/{en,si,ta}.json`; doc body translation is deferred indefinitely.

## When to update which doc

| Trigger | Update |
|---|---|
| New M1 source code lands | The relevant `15_M1_N_*` folder guide's "Files in this folder" table — flip status badge from 🔲 to ✅ |
| Schema migration adds a column | [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) §2 (the table the column belongs to) + [02_M1_2_Database_Schema_Validation.md](02_M1_2_Database_Schema_Validation.md) constraint list |
| New regulation category added | [09_M1_Annotation_Guidelines.md §2](09_M1_Annotation_Guidelines.md) + [09_M1_1_Category_Taxonomy_Examples.md](09_M1_1_Category_Taxonomy_Examples.md) + `frontend/messages/*.json` |
| Classifier hyperparameter change | [05_M1_Model_Architecture.md §4.2](05_M1_Model_Architecture.md) + [05_M1_3_LoRA_Hyperparameter_Justification.md](05_M1_3_LoRA_Hyperparameter_Justification.md) |
| Retraining run completes | `storage/models/m1/v<X>/model_registry.json` + the F1 table in [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) |
| New tracking surface (frontend) | [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) parent table + new `14_M1_N_*` companion |
| Build phase ships | [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md) — flip the phase DoD checkmark |

## How to start building

1. **Decide which series.** Use the table at the top — main doc, sub-step companion, folder guide, or roadmap?
2. **Pick a number.** Look at `README.md` Document Index for the next available; for sub-step companions, the next available sub-number under the relevant parent.
3. **Copy the skeleton from a sibling.** Don't invent. `15_M1_1_ML_Folder_Guide.md` is a good model for any new folder guide; `04_M1_1_Gazette_Noise_Removal.md` is a good model for any new sub-step companion.
4. **Open `README.md` LAST.** Add your file to both the Document Index + the Sub-Step Companions table (if applicable). Bump the file-count line.
5. **Run the cross-ref check.** From `enigmatrix-docs/m1/`: the Python script from the previous turn's verification — assert no broken `.md` links.

## Dependencies

This folder is the *destination* of every other folder's work — every code change should produce a documentation update. There are no upstream dependencies in code, only in *content* (the detail docs build on each other; the cross-ref graph is the spec).

## Tests & acceptance criteria

- **Cross-ref integrity.** Every markdown link to a `.md` target resolves. CI runs the Python URL-only checker against `enigmatrix-docs/m1/*.md` on every PR.
- **Skeleton conformance.** Every sub-step companion + folder guide carries all 7/6 required sections (per the locked skeletons). CI grep.
- **Status-badge honesty.** Spot-check 3 random docs per quarter — does the badge match reality? Any `✅` claim that doesn't map to shipped code is a bug.
- **README index completeness.** Every file in the folder appears in `README.md`. CI test: `ls *.md | wc -l` matches the row count in README's table.
- **No accidental code drift.** This folder is docs-only. CI test: any PR touching only `enigmatrix-docs/m1/` should have zero changes outside that folder.

## Cross-references

- Folder map spec: [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md)
- Parent reference: [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md)
- Roadmap: [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md)
- Per-module template (how to clone for M2/M3/M4): [13_M1_Folder_Structure §5](13_M1_Folder_Structure_and_Implementation_Flow.md)
- M1 doc index: [README.md](README.md)
- Tracking workflows pattern: [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) (an example of a parent + companions series)
- Sibling folders: [15_M1_1_ML_Folder_Guide.md](15_M1_1_ML_Folder_Guide.md) … [15_M1_5_Storage_Folder_Guide.md](15_M1_5_Storage_Folder_Guide.md)
