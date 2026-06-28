# 15 — M1 Folder Reference (per-folder build guides)

> Pick the folder you're working in; open the matching sub-folder guide; read what every file owns + why + how to build. Each guide cross-links into the deeper m1 doc that explains the spec.
> **See also:** [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) (the spec — *what* every file owns) · [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md) (sequenced *when* to build each step).
> **Audience:** the developer implementing M1. Status-aware: every guide marks files ✅ / 🟡 / 🔲 to match doc 13.

---

## Why this doc exists

Doc 13 specifies *every* file in the future M1 codebase. The 53 m1 docs explain the *why* + the *spec* for each major piece. But a new contributor opening doc 13's tree has no entry point for "I'm going to start by writing `ml/m1/extraction/pdf_classifier.py` — show me how." This reference closes that gap. Each sub-folder guide collects every file in that folder into one table — owner, status, primary doc, 1-liner on how to build — plus a "How to start building" section that sequences the work inside that folder.

The folders track doc 13's tree exactly:

```
xyz/
├── ml/         → 15_M1_1_ML_Folder_Guide.md
├── backend/    → 15_M1_2_Backend_Folder_Guide.md
├── scraper/    → 15_M1_3_Scraper_Folder_Guide.md
├── research/   → 15_M1_4_Research_Folder_Guide.md
├── storage/    → 15_M1_5_Storage_Folder_Guide.md
└── enigmatrix-docs/m1/  → 15_M1_6_Docs_Folder_Guide.md
```

---

## Index

| Guide | Folder it covers | File count (approx) | Status snapshot |
|---|---|---|---|
| [15_M1_1_ML_Folder_Guide.md](15_M1_1_ML_Folder_Guide.md) | `ml/` (everything ML — training, inference, extraction, preprocessing, shared helpers, tests) | ~30 files | 🔲 Mostly deferred (BUILD_07/11) |
| [15_M1_2_Backend_Folder_Guide.md](15_M1_2_Backend_Folder_Guide.md) | `backend/app/` (API routes, services, Celery tasks, models, schemas, migrations, scripts, middleware) | ~25 files | 🟡 Admin-CRUD slice + audit-log shipped; the rest deferred |
| [15_M1_3_Scraper_Folder_Guide.md](15_M1_3_Scraper_Folder_Guide.md) | `scraper/` (Scrapy project — settings, pipelines, spiders) | ~5 files | 🔲 Deferred (BUILD_07) |
| [15_M1_4_Research_Folder_Guide.md](15_M1_4_Research_Folder_Guide.md) | `research/` (notebooks, figures, labeling data, test splits) | ~10 files | 🔲 Deferred (notebooks scaffold post-BUILD_07/11) |
| [15_M1_5_Storage_Folder_Guide.md](15_M1_5_Storage_Folder_Guide.md) | `storage/` (raw PDFs, OCR cache, inference cache, model artifacts) | ~5 directories | 🟡 Conventions documented; populated by Phase 2/3 |
| [15_M1_6_Docs_Folder_Guide.md](15_M1_6_Docs_Folder_Guide.md) | `enigmatrix-docs/m1/` (this folder — 61 docs after this pass) | 61 files | ✅ Shipped — the docs themselves |

---

## How each guide is structured

All 6 sub-folder guides follow the same locked skeleton (mirrors the precedent from the previous m1 companion passes):

1. **Purpose.** What the folder owns in the M1 pipeline; what stage(s) it serves.
2. **Files in this folder.** Table per file: owner / status / primary doc link / 1-liner on how to build.
3. **How to start building.** Concrete sequenced first-tasks per file. References the linked detail doc for the *why* + the spec — this section only sequences the work.
4. **Dependencies.** Which other folders / files must exist before this one builds; cross-links to other 15_M1_X guides.
5. **Tests & acceptance criteria.** Per file or per folder: unit / integration / acceptance metric. Usually the existing doc's "Validation" section quoted + cross-linked.
6. **Cross-references.** Doc 13 (folder map) + Roadmap (16_M1_*) + relevant detail docs + BUILD phase.

The skeleton is identical across the 6 guides so a developer learns once + skips between folders.

---

## How to start (the 30-second start-here)

1. **Don't know where to begin?** Open [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md). The roadmap is phase-by-phase; it tells you the first concrete task.
2. **Already know which folder you're building in?** Open the matching guide above. Find the file you're touching in the "Files in this folder" table. Click the primary-doc link for the spec.
3. **Need the bigger picture?** Open [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) for the full tree + stage-A-to-G implementation flow.
4. **Need to add a new module (M2/M3/M4)?** [13_M1_Folder_Structure §5 (per-module template)](13_M1_Folder_Structure_and_Implementation_Flow.md) tells you how to clone M1's tree.

## Conventions used in the guides

- **Status badges** (per file, in each table): ✅ Shipped (works in production today) · 🟡 Partial (exists but incomplete) · 🔲 Deferred (file doesn't exist yet; will land in a future BUILD).
- **Owner column** describes *what state or behaviour* the file controls — one line, no jargon.
- **"How to build" column** is ≤ 1 sentence. Anything longer means the underlying detail doc is the right place — the guide just sequences + links, doesn't duplicate.
- **Primary doc column** links to ONE doc per file (the canonical reference). Secondary references go in the "Cross-references" section at the bottom of each guide.

## Cross-references

- [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) — the folder-map spec
- [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md) — sequenced "start here" guide
- [README.md](README.md) — full m1 doc index (61 files)
- [14_M1_Tracking_Workflows.md](14_M1_Tracking_Workflows.md) — frontend tracking workflow surfaces (the *what users do*, this folder spec is the *what code lives where*)
