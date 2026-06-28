# Step 2a — Scrapy gazette spider (M1 Phase 2 — Ingest + extraction, MVP slice)

## Context

The user wants to start executing the M1 Development Roadmap ([16_M1_Development_Roadmap.md](enigmatrix-docs/m1/16_M1_Development_Roadmap.md)). First concrete step is **Phase 2 — Step 2a: Scrapy gazette spider**, with the _minimum-viable_ scope (Celery wiring deferred to Step 2b). New procedural rule from this turn onward: **every prompt's changes get logged in the tracker folder** (SESSIONS / CHANGES / FEATURES + AI_WORK_LOG).

**Step 2a's roadmap goal:** `scrapy crawl gazette_spider` against a sample-day URL produces N PDF files in `storage/m1/raw/` + N new rows in `m1_regulations` with `status='ingested'`.

**Decisions locked with the user this turn:**

1. **Build root** = `enigmatrix-backend/scraper/` (filesystem truth; doc 13's `backend/` + root `scraper/` canon stays a future-state target — Session 21's doc-path sweep is intentionally a doc-only forward declaration; reconciliation is a separate task).
2. **Scope** = **Minimum-viable spider only.** Celery infra (broker, `celery_config.py`, `tasks/m1/extract_gazette.py`) is **deferred to Step 2b**. The spider logs a `TODO: enqueue extract_gazette(<reg_id>)` line where the Celery dispatch will go. Roughly 8-10 file touches (vs ~15 for the full Step 2a).
3. **Verification** = **Both** — a mocked-fixture integration test for CI + a documented manual smoke-check section in the tracker entry (with the gazette.lk URL + expected row count).

**Hard constraints:**

- **One feature, one tracker entry.** This prompt ships **Session 23 / F-144**, recorded in SESSIONS.md + CHANGES.md + FEATURES.md + AI_WORK_LOG.md (above the existing Session 22 entry the user just added).
- **No code drift outside the scraper + model + migration + test fixtures.** Frontend untouched.
- **No real network call in CI.** Spider integration test points at a `localhost` fixture server.
- **No Celery in this PR.** Spider's pipeline writes the DB row + a TODO log; Step 2b wires the actual dispatch.

---

## Files (≈ 13 touches: 10 new + 3 modified + 4 tracker)

### NEW — Scrapy project + spider (8 files)

| Path                                                   | Purpose                                                                                                                                                                                                                                                     |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `enigmatrix-backend/scrapy.cfg`                        | Scrapy project config — points at `scraper.settings`                                                                                                                                                                                                        |
| `enigmatrix-backend/scraper/__init__.py`               | Package marker                                                                                                                                                                                                                                              |
| `enigmatrix-backend/scraper/items.py`                  | `GazetteItem` (gazette_number, source_url, gazette_date, gazette_type, pdf_url)                                                                                                                                                                             |
| `enigmatrix-backend/scraper/settings.py`               | Scrapy settings: `ITEM_PIPELINES`, USER_AGENT, RETRY, AUTOTHROTTLE per [03_M1_Data_Collection.md §1.3](enigmatrix-docs/m1/03_M1_Data_Collection.md)                                                                                                         |
| `enigmatrix-backend/scraper/pipelines.py`              | Two pipelines: (a) `PDFDownloadPipeline` — downloads PDF to `storage/m1/raw/<gazette_number>.pdf` with SHA-256 verification; (b) `M1RegulationsInsertPipeline` — INSERT `m1_regulations` row with `status='ingested'` + log `TODO: enqueue extract_gazette` |
| `enigmatrix-backend/scraper/spiders/__init__.py`       | Package marker                                                                                                                                                                                                                                              |
| `enigmatrix-backend/scraper/spiders/gazette_spider.py` | `GazetteSpider(scrapy.Spider)` — the §1.3 scaffold verbatim + a `parse()` method that yields `GazetteItem` per listing entry                                                                                                                                |
| `enigmatrix-backend/scraper/tests/__init__.py`         | Package marker                                                                                                                                                                                                                                              |

### NEW — Test fixtures + integration test (3 files)

| Path                                                               | Purpose                                                                                                                                                                                                               |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `enigmatrix-backend/app/tests/integration/test_gazette_spider.py`  | Stands up a `localhost` fixture HTTP server, runs the spider against it, asserts: 1 PDF written to tmp dir, 1 row in `m1_regulations` with `status='ingested'`, `raw_pdf_path` set, `gazette_number` parsed correctly |
| `enigmatrix-backend/app/tests/fixtures/gazette_listing.html`       | Mock gazette.lk listing — 1 entry pointing at the local PDF fixture                                                                                                                                                   |
| `enigmatrix-backend/app/tests/fixtures/sample_gazette_2486_22.pdf` | Tiny 1-page valid PDF (binary, ~5 KB) used as the downloaded artifact                                                                                                                                                 |

### NEW — Alembic migration (1 file)

| Path                                                                                | Purpose                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `enigmatrix-backend/alembic/versions/202605160001_m1_regulations_status_columns.py` | Adds 3 columns to `m1_regulations`: `status VARCHAR(20) NOT NULL DEFAULT 'ingested'` (per [02_M1_2_Database_Schema_Validation.md §Step 1](enigmatrix-docs/m1/02_M1_2_Database_Schema_Validation.md) constraints), `raw_pdf_path TEXT`, `gazette_number TEXT`. Indexes: `ix_m1_regulations_status` (partial WHERE `status != 'archived'`), `ix_m1_regulations_gazette_number` (UNIQUE NULLS NOT DISTINCT). `down_revision` = the most-recent existing migration (`202605150001_*` per the m1/16 roadmap context). |

### MODIFIED — Backend support (3 files)

| Path                                             | Change                                                                                                                                                                                                   |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | ------------------------------------------------------------- |
| `enigmatrix-backend/pyproject.toml`              | Add `scrapy>=2.11,<3` to `[project.dependencies]`. (Defer `PyMuPDF`, `pdfplumber`, `pdf2image`, `pytesseract`, `feedparser`, `celery[redis]` to Steps 2b/2c — they're not needed for the spider itself.) |
| `enigmatrix-backend/app/models/m1_regulation.py` | Add three column declarations matching the migration: `status: Mapped[str] = mapped_column(String(20), nullable=False, default='ingested')`, `raw_pdf_path: Mapped[str                                   | None]`, `gazette_number: Mapped[str | None]`. Keep `is_active`+ the`expert_verified` fields intact. |
| `enigmatrix-backend/.gitignore`                  | Add `storage/m1/raw/` (and `storage/m1/ocr_cache/` for forward-compatibility with Steps 2b/2c).                                                                                                          |

### MODIFIED — Tracker (4 files)

| Path                                  | Change                                                                                                        |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `AI_WORK_LOG.md`                      | New entry above the existing Session 22 "Backend seed refactor" entry (which the user added between turns).   |
| `enigmatrix-docs/tracker/SESSIONS.md` | New Session 23 entry (newest-first) above Session 21.                                                         |
| `enigmatrix-docs/tracker/CHANGES.md`  | New F-144 table row prepended above F-143.                                                                    |
| `enigmatrix-docs/tracker/FEATURES.md` | New `## Session 23 — M1 Phase 2 Step 2a` section with F-144 row, inserted below the F-143 Session 21 section. |

---

## Execution order

1. Add `scrapy` to `pyproject.toml`. (Run `uv sync` is out of scope for me — user will do it; my plan notes this prerequisite.)
2. Write the Alembic migration. Add `status`/`raw_pdf_path`/`gazette_number` to the ORM model. Update `.gitignore`.
3. Create the Scrapy project skeleton (`scrapy.cfg`, `scraper/__init__.py`, `scraper/items.py`, `scraper/settings.py`, `scraper/spiders/__init__.py`).
4. Write the spider (`scraper/spiders/gazette_spider.py`) — the §1.3 scaffold + a parse loop that yields `GazetteItem` from `documents.gov.lk` listing pages (the simpler shape; gazette.lk listing can be a follow-up parse method).
5. Write the two pipelines (`scraper/pipelines.py`): `PDFDownloadPipeline` then `M1RegulationsInsertPipeline`. Both `async def process_item`. Use `AsyncSession` from `app.db.session.get_db()` for the INSERT.
6. Write fixture files + integration test. Test spins up an `aiohttp` mock HTTP server on a random port, points the spider's `start_urls` at it via a custom setting override, runs the spider via `scrapy.crawler.CrawlerProcess`, asserts the DB state.
7. **Tracker step (mandatory per the new rule):** write the 4 tracker entries. The Session-23 SESSIONS entry must include a **"Manual smoke check"** subsection with: the real gazette.lk listing URL, the command (`cd enigmatrix-backend && scrapy crawl gazette_spider`), the expected row count (1-5 from the latest week), and the rollback (`alembic downgrade -1`).

---

## Verification

1. **Migration round-trip.** `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` succeeds on a fresh test DB.
2. **CI integration test.** `pytest enigmatrix-backend/app/tests/integration/test_gazette_spider.py` passes with the mocked fixture server: asserts 1 PDF written + 1 `m1_regulations` row with `status='ingested'`, correct `raw_pdf_path`, parsed `gazette_number='2486/22'`.
3. **Manual smoke check (documented but not executed in this PR).** Following the tracker entry, the user (or me, in a separate turn) runs `scrapy crawl gazette_spider` against the live `documents.gov.lk` listing. Expected: ≥ 1 PDF in `enigmatrix-backend/storage/m1/raw/`, ≥ 1 new row in `m1_regulations` with the latest extraordinary-gazette number.
4. **No code drift outside intended scope.** `git diff --stat enigmatrix-frontend/ enigmatrix-ml/ enigmatrix-infrastructure/ enigmatrix-docs/m1/` is empty (frontend / ML / infra / m1 docs all untouched).
5. **Tracker freshness.** All four tracker files reference `Session 23` / `F-144` / `2026-05-15`.

## Risks / open items

- **Scrapy + async SQLAlchemy compatibility.** Scrapy's reactor is Twisted; SQLAlchemy 2.0 async uses asyncio. The pipeline runs the INSERT via `asyncio.get_event_loop().run_until_complete(...)` inside a synchronous Scrapy callback. Documented as a follow-up cleanup for Step 2b (where Celery owns the async loop properly).
- **Doc-canon vs filesystem drift.** Building at `enigmatrix-backend/scraper/` directly conflicts with the canonical paths I normalised in Session 21 (which said `scraper/` at root). The tracker entry must call this out explicitly so it doesn't get re-flagged in a future consistency sweep. **Resolution:** docs stay future-state; code is current-state; a separate "monorepo restructure" task will reconcile them later.
- **`gazette_number` UNIQUE constraint** on a column with existing data (5 demo rows). The migration sets it nullable, so the UNIQUE allows multiple NULLs (with NULLS NOT DISTINCT off — the default Postgres behaviour). Existing demo rows have `gazette_number=NULL` and don't collide.
- **`status` field collision with the existing `is_active` soft-delete.** They serve different purposes (`status` is the pipeline state machine; `is_active=false` is admin soft-delete). Both stay. Documented in the tracker entry.
- **Test isolation.** The fixture server runs on a random port; tests must skip if port-binding fails (CI environments occasionally restrict). Use `pytest.skip` with a clear message.

---

# (Historical) Previous plan — Folder-path consistency sweep — align older m1 docs to doc 13's canonical layout

## Context

`13_M1_Folder_Structure_and_Implementation_Flow.md` is the canonical M1 folder spec — it was modified between turns and now declares the _current_ project tree (`backend/app/...`, `ml/m1/...`, `scraper/spiders/...`, etc.). The newer docs (14*M1*_, 15*M1*_, 16*M1*\*) align to it because they were authored against it. **The older docs (01–12) pre-date the canonical and carry stale paths** — missing `backend/` prefixes, missing per-module `m1/` subdirs under `backend/app/tasks/`, and obsolete `pipeline/inspect.py` / `app/ml/inference.py` module names.

A recon sweep across all 61 m1/\*.md files found **15 divergent path mentions across 6 files**. Every divergence falls into one of three patterns:

1. **Missing `backend/` prefix** (9 occurrences). Older docs write `app/api/v1/m1_regulations.py`; canonical is `backend/app/api/v1/m1_regulations.py`.
2. **Missing `m1/` subdir under `tasks/`** (3 occurrences). Older docs write `backend/app/tasks/classify_gazette.py`; canonical is `backend/app/tasks/m1/classify_gazette.py`.
3. **Obsolete module names** (3 occurrences). Older docs write `pipeline/inspect.py`, `app/ml/inference.py`, `app/services/gazette_extractor.py`; canonical uses `ml/m1/extraction/pdf_classifier.py`, `ml/m1/model/inference.py`, `ml/m1/extraction/text_extractors.py`.

A future contributor searching for code by following an old doc's path lands in the wrong place — or worse, creates a new file at the wrong path. This pass aligns every old path mention to doc 13's canonical, so the docs + the code (when it lands) match.

**Hard constraints:**

- **Docs-only.** No code in `frontend/`, `backend/`, `ml/`, etc. is touched.
- **Path renames only.** No prose rewriting — strictly the file paths inside code-blocks, file-header comments, backtick mentions, and Cross-references sections.
- **Doc 13 is the authority.** Where the audit was uncertain, defer to the matching newer sub-step companion (which was authored against doc 13) for tiebreaking.
- **No new divergences.** Every replacement must be verifiable against doc 13's tree + the `15_M1_N_*` folder guides.

---

## Divergences by file

### `02_M1_Data_Requirements.md` (1 line, 2 paths)

- Line 80: `app/models/m1_regulation.py` and `app/services/m1_regulation_service.py` → add `backend/` prefix to both.

### `03_M1_Data_Collection.md` (4 paths)

- Line 43: `app/tasks/gazette_scraper.py` → `backend/app/tasks/m1/gazette_scraper.py` (adds both `backend/` + `m1/`).
- Line 125: `app/services/gazette_extractor.py` → `ml/m1/extraction/text_extractors.py`. _Rationale:_ the surrounding code is the PyMuPDF → pdfplumber → Tesseract chain, which doc 13 places in `ml/m1/extraction/text_extractors.py`. The `app/services/` location is obsolete.
- Line 163: `pipeline/inspect.py` → `ml/m1/extraction/pdf_classifier.py`.
- Line 246: `pipeline/segment.py` → `ml/m1/extraction/segmenter.py`. _Rationale:_ the newer companion [03_M1_2_Gazette_Segmentation.md](enigmatrix-docs/m1/03_M1_2_Gazette_Segmentation.md) already uses `ml/m1/extraction/segmenter.py` — match it.

### `07_M1_Deployment_Integration.md` (3 paths)

- Line 74 (Python import inside a code block): `from app.ml.gazette_classifier import GazetteClassifier` → `from ml.m1.model.architecture import GazetteClassifier`.
- Line 125 (code-header comment): `# app/ml/inference.py` → `# ml/m1/model/inference.py`.
- Line 231 (code-header comment): `# app/tasks/classify_gazette.py` → `# backend/app/tasks/m1/classify_gazette.py`.

### `08_M1_Full_System_Architecture.md` (1 line, 2 paths in cross-refs)

- Line 408 ("Enigmatrix Backend" bullet): `app/api/v1/m1_regulations.py · app/services/m1_regulation_service.py` → add `backend/` prefix to both.

### `11_M1_API_Reference.md` (3 lines, 5 paths)

- Line 11: three paths in one Abstract sentence — `app/api/v1/m1_regulations.py`, `app/services/m1_regulation_service.py`, `app/schemas/m1.py` → add `backend/` prefix to all three.
- Line 793 (Cross-references): `app/api/v1/m1_regulations.py` → `backend/app/api/v1/m1_regulations.py`.
- Line 795 (Cross-references): `app/schemas/m1.py` → `backend/app/schemas/m1.py`.

### `12_M1_Monitoring_Maintenance.md` (2 code-header comments)

- Line 36: `# app/tasks/analytics.py` → `# backend/app/tasks/m1/analytics.py`.
- Line 226: `# app/main.py` → `# backend/app/main.py`.

**Total: 15 path replacements across 6 files.**

---

## Critical files

- [enigmatrix-docs/m1/02_M1_Data_Requirements.md](enigmatrix-docs/m1/02_M1_Data_Requirements.md)
- [enigmatrix-docs/m1/03_M1_Data_Collection.md](enigmatrix-docs/m1/03_M1_Data_Collection.md)
- [enigmatrix-docs/m1/07_M1_Deployment_Integration.md](enigmatrix-docs/m1/07_M1_Deployment_Integration.md)
- [enigmatrix-docs/m1/08_M1_Full_System_Architecture.md](enigmatrix-docs/m1/08_M1_Full_System_Architecture.md)
- [enigmatrix-docs/m1/11_M1_API_Reference.md](enigmatrix-docs/m1/11_M1_API_Reference.md)
- [enigmatrix-docs/m1/12_M1_Monitoring_Maintenance.md](enigmatrix-docs/m1/12_M1_Monitoring_Maintenance.md)

**Not touched (out of scope):**

- Doc 13 itself (it's the canonical).
- `14_M1_*`, `15_M1_*`, `16_M1_*` (the recon confirmed these are already canonical).
- The other `01_*`, `04_*`–`06_*`, `09_*`, `10_*` main docs + all sub-step companions (recon found no divergences in these).
- `README.md` (no path mentions divergent from doc 13).
- All code under `frontend/`, `backend/`, `ml/`, `scraper/`, etc.

---

## Execution order

1. Re-read each target file at the indicated lines to confirm the audit's exact text (the audit's line numbers are approximate; the exact `old_string` must match the file byte-for-byte for the `Edit` tool).
2. Apply each path replacement using `Edit` with `replace_all=false` and enough surrounding context to disambiguate (e.g. include the `#` for code-comment headers, the `from X import Y` for Python imports).
3. After all 6 files are edited, run a verification grep across all 61 m1 docs for any remaining mention of the **old patterns**:
   - `\bapp/api/v1/m1_regulations\b` (without `backend/` prefix)
   - `\bapp/services/m1_regulation_service\b` (without `backend/` prefix)
   - `\bapp/tasks/(?!m1)` (without `m1/` subdir)
   - `\bapp/ml/`
   - `\bpipeline/(inspect|segment)\.py`
   - `\bapp/services/gazette_extractor\b`
     The grep should return zero matches (or only matches in doc-13 historical context, which are out of scope).

---

## Verification (read-only)

1. **Per-file diff sanity.** `git diff --stat enigmatrix-docs/m1/` shows exactly 6 files changed (the 6 in the critical-files list above).
2. **No code drift.** `git diff --stat frontend/ backend/ ml/ scripts/ scraper/ enigmatrix-backend/ enigmatrix-frontend/ enigmatrix-ml/ enigmatrix-infrastructure/` is empty.
3. **Old-pattern grep.** Run these patterns and confirm zero matches in m1/\*.md (excluding doc 13):
   ```bash
   cd enigmatrix-docs/m1
   grep -nE '\bapp/api/v1/m1_regulations' [01][0-9]*.md 2>&1 | grep -v 13_M1_Folder
   grep -nE '\bapp/services/m1_regulation_service' [01][0-9]*.md 2>&1 | grep -v 13_M1_Folder
   grep -nE '\bapp/tasks/(classify|gazette|summarise|alert|analytics|portal|rss|extract)' [01][0-9]*.md 2>&1 | grep -v 13_M1_Folder
   grep -nE '\bapp/ml/' [01][0-9]*.md 2>&1 | grep -v 13_M1_Folder
   grep -nE '\bpipeline/(inspect|segment)\.py' [01][0-9]*.md 2>&1 | grep -v 13_M1_Folder
   grep -nE '\bapp/services/gazette_extractor' [01][0-9]*.md 2>&1 | grep -v 13_M1_Folder
   ```
4. **Cross-ref integrity.** Re-run the cross-ref resolution check from prior verifications — all `.md` links still resolve.
5. **Spot-check 3 random replacements.** Open the edited files at the changed lines and read the surrounding paragraph to confirm the prose still reads sensibly.

## Risks / open items

- **Line numbers in the audit are from the recon agent's read** and may have shifted slightly if the user edited any file between recon and this plan. Mitigation: each `Edit` call uses `old_string` matching with surrounding context, not line numbers — drift is harmless.
- **`app/celery_config.py`** (mentioned in 03_M1_Data_Collection.md line ~432) was _not_ flagged by the audit. Spot-check during execution: if it's still `app/celery_config.py` rather than `backend/app/celery_config.py`, fix it too.
- **`app/main.py`** (12_M1 line 226) — the canonical lives at `backend/app/main.py` (per doc 13). Confirmed.
- **Audit completeness.** The recon agent scanned all 61 m1 docs. If a divergence was missed, the post-edit grep in §verification will surface it.

---

# (Historical) Previous plan — Close the interrupted session — final 1-line fix in 15_M1_6

## Status snapshot (verified by audit just now)

The previous session was interrupted mid-move of the 10 `14_M1_*` tracking-workflow files from `enigmatrix-docs/frontend/SETUP/` → `enigmatrix-docs/m1/`. Since then (either by the user or another session) the move **and** the larger follow-on plan (per-folder M1 build guides + development roadmap) have both landed:

- ✅ 10 `14_M1_*` files now live in `enigmatrix-docs/m1/`; `frontend/SETUP/` no longer holds them
- ✅ 8 new docs created: `15_M1_Folder_Reference.md`, `15_M1_1_ML_Folder_Guide.md` through `15_M1_6_Docs_Folder_Guide.md`, `16_M1_Development_Roadmap.md`
- ✅ `m1/README.md` indexes rows 15 + 16 + the 6 sub-folder companions
- ✅ `13_M1_Folder_Structure_and_Implementation_Flow.md` has the new See-also pointer (line 44)
- ✅ All 5 of `15_M1_1`..`15_M1_5` carry the locked 6-section skeleton (Purpose / Files in this folder / How to start building / Dependencies / Tests / Cross-references)
- ✅ 0 broken cross-references across 61 m1/ files; word counts confirm every doc is populated (not stub)

## The single remaining loose end

`15_M1_6_Docs_Folder_Guide.md` has different section headers from the other five 15_M1 guides:

| Locked skeleton                  | What 15_M1_6 has today                                                                     |
| -------------------------------- | ------------------------------------------------------------------------------------------ |
| `## Purpose`                     | ✅ `## Purpose`                                                                            |
| `## Files in this folder`        | ✅ `## Files in this folder`                                                               |
| `## How to start building`       | ❌ has `## How to add a new doc` + `## How to start (if you're writing a new doc)` instead |
| `## Dependencies`                | ✅ `## Dependencies`                                                                       |
| `## Tests & acceptance criteria` | ✅ `## Tests & acceptance criteria`                                                        |
| `## Cross-references`            | ✅ `## Cross-references`                                                                   |

The doc body covers the same ground as "How to start building" — both "How to add a new doc" and "How to start (if you're writing a new doc)" describe the workflow for adding a new doc to `m1/`. The fix is cosmetic: align the section headers so the skeleton-conformance check passes uniformly across all six 15_M1_N guides.

## The fix

In `enigmatrix-docs/m1/15_M1_6_Docs_Folder_Guide.md`:

1. Rename `## How to start (if you're writing a new doc)` (line 62) → `## How to start building`.
2. Leave `## How to add a new doc` (line 26) as-is — it remains the body of the "how to start building" guidance, just under a different sub-header. Optionally promote it to an h3 (`### How to add a new doc`) under the renamed h2 to make the nesting explicit.

That's one file, one heading rename + optional h2→h3 adjustment. No new files; no cross-reference changes elsewhere (the m1/README.md row + doc 13 link reference the file, not the internal sections).

## Critical files

- [enigmatrix-docs/m1/15_M1_6_Docs_Folder_Guide.md](enigmatrix-docs/m1/15_M1_6_Docs_Folder_Guide.md) — only file edited

## Verification (read-only)

After the edit, re-run the skeleton-conformance grep loop from the prior verification pass:

```bash
cd enigmatrix-docs/m1
for f in 15_M1_[1-6]_*.md; do
  s=0
  grep -qE '^## Purpose' "$f" && s=$((s+1))
  grep -qE '^## Files in this folder' "$f" && s=$((s+1))
  grep -qE '^## How to start building' "$f" && s=$((s+1))
  grep -qE '^## Dependencies' "$f" && s=$((s+1))
  grep -qE '^## Tests' "$f" && s=$((s+1))
  grep -qE '^## Cross-references' "$f" && s=$((s+1))
  echo "$(basename $f): $s / 6 sections"
done
```

Expected: all six guides report `6 / 6 sections`. Also: `git diff --stat` should show only `15_M1_6_Docs_Folder_Guide.md` changed; no other files; no code drift.

---

# (Historical) Previous plan — Per-folder M1 build guides + sequenced development roadmap

> The plan below was approved + executed by the user (or another session) between turns. Retained here as the audit trail of what's now in `enigmatrix-docs/m1/`. The above 1-line fix is the only remaining task.

## Context

The user is asking, with reference to [13_M1_Folder_Structure_and_Implementation_Flow.md](enigmatrix-docs/m1/13_M1_Folder_Structure_and_Implementation_Flow.md), for two related additions to `enigmatrix-docs/m1/`:

1. **Per-folder/file build guides.** Doc 13 lists every folder + file the future M1 codebase will have (under `ml/`, `backend/`, `scraper/`, `research/`, `storage/`, `enigmatrix-docs/m1/`). For each, the user wants the _what / why / how_ documented — linked to the relevant existing m1 doc where one already covers it, and a freshly-written md file where the instruction is missing.
2. **A "where do I start" development roadmap.** A sequenced, status-aware guide that tells the user _exactly_ the next steps to take to start the M1 research/dev work — what's already done, what comes next, in what dependency order, with a link to the detail doc that explains each step.

Today the 53 m1 docs cover concepts + sub-step companions (research problem, data requirements, classifier architecture, etc.) and the 14*M1** tracking workflows, but they don't aggregate the *per-folder build instructions\* in one place, nor do they sequence the dev work. A new developer arriving cold has to map doc 13's tree onto the existing companion docs manually, then guess the build order from BUILD_07/11/12 references. This pass closes both gaps with one parent doc + 6 sub-folder guides + one roadmap.

**Intended outcome:** a contributor opens `enigmatrix-docs/m1/15_M1_Folder_Reference.md`, picks the folder they want to build in, opens the matching sub-folder guide, reads what every file owns + why + how — with cross-links to the deeper existing m1 doc. Then they open `16_M1_Development_Roadmap.md` and follow it phase-by-phase to know what to build first.

**Hard constraints:**

- **Docs-only.** No code in `frontend/`, `backend/`, `ml/`, etc. is touched.
- **No content duplication.** Where an existing m1 doc covers a file/folder, the new guide links to it instead of repeating. The new docs are _index + start-here pointers + what's-not-covered-elsewhere instructions_ — not encyclopedias.
- **Status-badge honesty.** Every folder + file carries `✅ Shipped` / `🟡 Partial` / `🔲 Deferred` consistent with doc 13's tree annotations.
- **Locked sub-step skeleton** for the 6 folder guides: Purpose → Files in this folder (table) → How to start building → Dependencies → Tests & acceptance → Cross-references. Mirrors the precedent from the previous m1 companion passes.
- **Roadmap is sequenced + actionable.** Not "here are the phases" — concrete "do X next, here's the doc that explains how, here's the definition of done".

---

## Files to add (8 new)

All in `enigmatrix-docs/m1/`.

### Parent: `15_M1_Folder_Reference.md`

Index of the 6 sub-folder guides. Brief overview of the per-folder split. Status snapshot per folder. Cross-link to doc 13 (the source of the folder tree) + the 6 sub-folder guides.

### Sub-folder guides (6)

| #    | File                               | Covers                                                                                                                                                                                                                            | Cross-links into existing m1 docs                                                                                                                                                                     |
| ---- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 15.1 | `15_M1_1_ML_Folder_Guide.md`       | `ml/shared/`, `ml/m1/*` (data, extraction, preprocessing, model, summarization, schema, utils), `ml/tests/m1/`                                                                                                                    | 03_M1_1 (extraction), 04_M1_1..3 (preprocessing), 05_M1_1..3 (model + sampling + LoRA), 06_M1_1..2 (training + augmentation + slice), 07_M1_1 (ONNX export), 10_M1_1..2 (lang detection + Wijesekara) |
| 15.2 | `15_M1_2_Backend_Folder_Guide.md`  | `backend/app/api/v1/m1_regulations.py`, `services/m1_regulation_service.py`, `tasks/m1/*` (all 8 Celery tasks), `models/m1_regulation.py`, `schemas/m1.py`, `config/feature_flags.py`, `db/migrations/versions/*`, `scripts/m1_*` | 03_M1_Data_Collection §6.1 (Celery), 11_M1_API_Reference, 11_M1_1..2 (auth + integration), 12_M1_Monitoring (analytics task), 12_M1_2 (retrain workflow)                                              |
| 15.3 | `15_M1_3_Scraper_Folder_Guide.md`  | `scraper/settings.py`, `pipelines.py`, `spiders/gazette_spider.py`, `spiders/portal_spiders.py`                                                                                                                                   | 03_M1_Data_Collection §1 (Scrapy choice), 02_M1_1 (15-source catalogue), 03_M1_3 (secondary source integration)                                                                                       |
| 15.4 | `15_M1_4_Research_Folder_Guide.md` | `research/notebooks/*` (4 finding notebooks), `figures/`, `data/labeling/`, `data/test_split.parquet`                                                                                                                             | 08_M1_Full_System §10 (findings F1–F6), 08_M1_1 (findings extraction methodology), 09_M1_Annotation_Guidelines §9 (survey instrument), 09_M1_2 (annotator workflow + IAA)                             |
| 15.5 | `15_M1_5_Storage_Folder_Guide.md`  | `storage/m1/raw/`, `ocr_cache/`, `inference_cache/`, `storage/models/m1/v*/`, `baseline/`                                                                                                                                         | 02_M1_3 (retention + cold archive), 06_M1_Training §9 (`model_registry.json` shape), 07_M1_Deployment §5 (Fly volume layout), 07_M1_2 (Fly ops)                                                       |
| 15.6 | `15_M1_6_Docs_Folder_Guide.md`     | `enigmatrix-docs/m1/*` — the 53 docs themselves: how they're organised, how to add a new one, when to update which                                                                                                                | 13_M1_Folder_Structure §5 (per-module template), README.md (the m1 index itself), 14_M1_Tracking_Workflows (cross-doc pattern example)                                                                |

### Roadmap: `16_M1_Development_Roadmap.md`

Sequenced "start here" guide. Structure:

- **Where M1 stands today** — snapshot: ✅ admin-CRUD slice, audit log, demo seed (5 regs), unified survey flow, 53-doc research base. 🔲 ingest pipeline, ML training, schedulers, alerts, lag-analytics UI.
- **Phase 1 — Foundation (✅ done).** Brief summary; readers skip to Phase 2.
- **Phase 2 — Ingest + extraction (BUILD_07 §A–B).** Concrete order: (a) Scrapy spider — see [03_M1_Data_Collection.md](03_M1_Data_Collection.md) + [03_M1_1_PDF_Extraction_Chain.md](03_M1_1_PDF_Extraction_Chain.md); (b) Celery task wiring — see [03_M1_Data_Collection.md §6.1](03_M1_Data_Collection.md); (c) language detection + per-line routing — see [10_M1_1_Language_Detection_Routing.md](10_M1_1_Language_Detection_Routing.md); (d) preprocessing — see [04*M1*\*.md](04_M1_Preprocessing_Pipeline.md). DoD: gazettes flow from URL → `m1_regulations.status='extracted'` with cleaned text.
- **Phase 3 — Annotation + classification (BUILD_07 §C–D + BUILD_11).** Order: (a) Label Studio setup + calibration test — see [09_M1_2_Annotation_Workflow_IAA_Protocol.md](09_M1_2_Annotation_Workflow_IAA_Protocol.md); (b) sampling for first 300 labels — see [05_M1_1_Sampling_Strategy.md](05_M1_1_Sampling_Strategy.md); (c) train XLM-R + LoRA — see [05_M1_Model_Architecture.md](05_M1_Model_Architecture.md) + [05_M1_3_LoRA_Hyperparameter_Justification.md](05_M1_3_LoRA_Hyperparameter_Justification.md); (d) eval + slice analysis — see [06_M1_Training_Evaluation.md](06_M1_Training_Evaluation.md) + [06_M1_2_Slice_Analysis_Framework.md](06_M1_2_Slice_Analysis_Framework.md); (e) ONNX export + Fly deploy — see [07_M1_1_ONNX_Export_Quantization.md](07_M1_1_ONNX_Export_Quantization.md). DoD: macro-F1 ≥ 0.92; model serving from Fly.
- **Phase 4 — Schedulers + alerts (BUILD_12).** Portal + RSS watchers, alert dispatch, lag-view nightly refresh. Links to 02_M1_1, 03_M1_3, 08_M1_Full_System §8.1 (alert batching), 12_M1_Monitoring.
- **Phase 5 — Research findings + survey (BUILD_07 + manual).** SME survey deployment (09_M1_3), F1–F6 extraction (08_M1_1), monitoring dashboard (14_M1_4 — deferred frontend), retraining cadence (12_M1_2).
- **At any phase: tracking-workflow surfaces.** Cross-reference table — admin tracking surfaces ship with Phase 2/4 (A1, A3); deferred surfaces (A2, A4) ship with BUILD_13 frontend. SME surfaces (S2) ship with Phase 1 (already done); S1/S3/S4 ship with Phase 4 + BUILD_13.

Each phase has a _concrete first task_ call-out: "Open [the relevant doc] and do [the first thing]". The roadmap is the developer's daily start screen.

---

## Files to edit (2 existing)

| File                                                                   | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `enigmatrix-docs/m1/README.md`                                         | Add row 15 (Folder Reference) + row 16 (Roadmap) to Document Index; add 7-row "Folder Build Guides" + 1-row "Development Roadmap" to the Sub-Step Companions table; bump file count from 53 → 61.                                                                                                                                                                                                                                                                                                                                     |
| `enigmatrix-docs/m1/13_M1_Folder_Structure_and_Implementation_Flow.md` | At the top of `## M1 folder map`, add a "See also" callout: "Per-folder build guides — [15_M1_1_ML_Folder_Guide.md](15_M1_1_ML_Folder_Guide.md), [15_M1_2_Backend_Folder_Guide.md](15_M1_2_Backend_Folder_Guide.md), ... and the sequenced [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md)." Inside the `## File-by-file role description` table, add a "Build guide" column linking each row to the relevant 15_M1_X guide. (Optional — skipped if it makes the table too wide; the See-also callout is the must-have.) |

**Total: 8 new + 2 edited = 10 file touches.**

---

## Locked skeleton for the 6 sub-folder guides

```markdown
# 15*M1_N*<Folder>\_Folder_Guide

> Companion to [15_M1_Folder_Reference.md](15_M1_Folder_Reference.md) — build guide for the `<folder>` slice of doc 13's M1 tree.
> **Implementation status snapshot:** ✅ N shipped · 🟡 N partial · 🔲 N deferred

## Purpose

<1 paragraph: what this folder owns in the M1 pipeline, what stage(s) it serves, what it produces.>

## Files in this folder

| File              | Owns | Status | Primary doc               | How to build (1-liner)          |
| ----------------- | ---- | ------ | ------------------------- | ------------------------------- |
| `path/to/file.py` | ...  | 🔲     | [link to existing m1 doc] | "Implement <func> per [doc] §X" |
| ...               |      |        |                           |                                 |

## How to start building

<Concrete first-3-tasks per file: pick the entry-point, write the test fixture, implement the function. References the linked m1 doc for the _why_ + the spec; the guide only sequences the work.>

## Dependencies

<Which other folders / files must exist before this one builds. Cross-link to the relevant 15_M1_X guide.>

## Tests & acceptance criteria

<Per file or per folder: unit-test scope, integration-test scope, acceptance metric. Often = existing doc's "Validation" section quoted + cross-linked.>

## Cross-references

- Doc 13 (folder map): [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md)
- Roadmap: [16_M1_Development_Roadmap.md](16_M1_Development_Roadmap.md)
- Phase docs: BUILD_07 / BUILD_11 / BUILD_12
- Detail docs: [...link list...]
```

The roadmap doc (`16_M1_Development_Roadmap.md`) uses a different shape — phased sections, not the 7-section companion skeleton — because it's a sequenced guide, not a reference.

---

## Critical files (paths)

**New (will be created):**

- `enigmatrix-docs/m1/15_M1_Folder_Reference.md` (parent)
- `enigmatrix-docs/m1/15_M1_1_ML_Folder_Guide.md`
- `enigmatrix-docs/m1/15_M1_2_Backend_Folder_Guide.md`
- `enigmatrix-docs/m1/15_M1_3_Scraper_Folder_Guide.md`
- `enigmatrix-docs/m1/15_M1_4_Research_Folder_Guide.md`
- `enigmatrix-docs/m1/15_M1_5_Storage_Folder_Guide.md`
- `enigmatrix-docs/m1/15_M1_6_Docs_Folder_Guide.md`
- `enigmatrix-docs/m1/16_M1_Development_Roadmap.md`

**Existing (will be edited):**

- `enigmatrix-docs/m1/README.md`
- `enigmatrix-docs/m1/13_M1_Folder_Structure_and_Implementation_Flow.md`

**Not touched (out of scope):**

- All code under `frontend/`, `backend/`, `ml/`, `scripts/`, `scraper/`, `enigmatrix-*/`
- All non-m1 docs (`enigmatrix-docs/backend/`, `frontend/`, `infra/`, `ml/`, `shared/`, `tracker/`)
- The other 51 m1/ files (only `m1/README.md` and `m1/13_*.md` are touched; the 7 new files + 1 roadmap are additive)
- **Frontend `/docs/m1` route wiring.** The previously-drafted plan to surface 14*M1*_ on the frontend `/docs/m1` page is separate — not in scope this turn. The 8 new 15*M1*_/16*M1*\*.md files will be similarly orphaned from the frontend until a later turn wires them in.

---

## Execution order

1. Write `16_M1_Development_Roadmap.md` first — it's the bird's-eye view; the folder guides cross-reference it.
2. Write `15_M1_Folder_Reference.md` (parent) — indexes the 6 sub-folder guides; lighter content.
3. Write the 6 sub-folder guides in tree order (`15_M1_1` ML → `15_M1_2` backend → `15_M1_3` scraper → `15_M1_4` research → `15_M1_5` storage → `15_M1_6` docs). ML and backend are the longest (more files); scraper, research, storage, docs are shorter.
4. Edit `m1/README.md` — add the 8 new entries to the indices.
5. Edit `m1/13_M1_Folder_Structure_and_Implementation_Flow.md` — add the See-also callout.
6. Verification pass.

Word budget: ~800 words per sub-folder guide, ~600 for the parent, ~1200 for the roadmap = ~7,000 words new content.

---

## Verification

All checks read-only:

1. **File count.** `ls enigmatrix-docs/m1/*.md | wc -l` returns 61 (53 prior + 8 new).
2. **Cross-ref integrity.** Every link from the 8 new docs resolves (run the Python URL-checker from the previous turn).
3. **Status-badge honesty.** Each folder guide's "Files in this folder" table uses the same ✅/🟡/🔲 marks as doc 13's tree. Spot-check 3 random rows.
4. **No content duplication.** Each folder guide's "How to build" section is ≤ 200 words per file — anything longer means the guide is starting to duplicate the linked detail doc. Spot-check.
5. **Roadmap actionability.** Every phase in `16_M1_Development_Roadmap.md` ends with a "do this next" call-out + a link to a specific m1 doc + a measurable DoD. CI test: regex-grep for `do this next:` per phase.
6. **No code drift.** `git diff --stat frontend/ backend/ ml/ scripts/ scraper/ enigmatrix-backend/ enigmatrix-frontend/ enigmatrix-ml/ enigmatrix-infrastructure/` is empty.
7. **README index completeness.** `m1/README.md` Document Index includes rows for 15 + 16; Sub-Step Companions table includes the 6 sub-folder guides under a "Folder Build Guides" parent + the Roadmap.

---

## Risks / open items

- **Overlap with existing docs.** The 6 folder guides necessarily summarise things the existing 53 m1 docs already say. Mitigation: each "How to build" entry is ≤ 200 words and ends with "Full spec → [doc-X.md]"; the guide's value is _sequencing_ + _cross-link discoverability_, not duplication.
- **Doc 13 already has a "File-by-file role description" table.** The 6 folder guides go deeper, but reviewers might ask why both exist. Justification: doc 13 is the _spec_ (per-file roles), the 15*M1** guides are the *build instructions\* (sequenced how-to per folder). The proposed See-also callout in doc 13 makes the relationship explicit.
- **Roadmap dependencies on BUILD_07/11/12 specs that don't fully exist yet.** The roadmap will reference `enigmatrix-docs/backend/BUILD_PLAN/BUILD_07_Module1_Awareness.md` etc.; some of those may not be fleshed out in detail. The roadmap will link to them anyway with a "may need to expand the BUILD doc first" note.
- **Frontend wiring deferred.** The previous-turn plan to surface tracking-workflow docs at `/docs/m1` is still outstanding. These 8 new docs will be similarly orphaned from the frontend route until a follow-up wiring pass. Documented as a follow-up risk; not blocking.
- **Translation cost.** The new docs are EN-only, matching the existing m1 docs convention. SI/TA translations are deferred indefinitely (consistent with the 53 existing docs).
