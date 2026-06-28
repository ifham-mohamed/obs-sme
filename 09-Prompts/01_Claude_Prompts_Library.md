# BUILD 17 — Claude Prompts Library

> **Goal:** every prompt from BUILD_01–16 in one searchable place. Drop these into a fresh Claude chat to generate the actual code/config for that step. Each prompt is verbatim from its source file — back-references included.

> **Read first:** the source BUILD file before pasting a prompt; prompts assume context (file paths, model versions, DB schemas) established earlier in the package.

---

## 1. How to use

These prompts assume the conventions, file paths, stack versions, and inter-module contracts laid down across BUILD_01 through BUILD_16 — and especially the canonical paths and contracts in `BUILD_00_INDEX.md`. A prompt that says "backend/app/services/regulation_service.py" is referring to the exact tree from `BUILD_02_Folder_Structure.md`; a prompt that mentions "the production XLM-R artifact" is referring to the model registry rules in `BUILD_11_ML_Training_Pipeline.md`. Pasting a prompt without that context will produce code that does not compose with the rest of the system.

Most prompts contain UPPERCASE_PLACEHOLDER tokens (or `<...>` placeholders, or things like `YYYY-MM-DD`) that are intentionally meant to be replaced by the human pasting the prompt. Read each prompt end-to-end and substitute every placeholder before sending — Claude will otherwise generate code with literal placeholder strings inside it. Common placeholders include repo names, tenant identifiers, MLflow run IDs, dates, and IP/host values.

Prompts work best in a fresh Claude chat where the only previously-loaded context is the relevant BUILD file (and, for cross-module prompts, the BUILD files it cross-references). Avoid mixing prompts from different BUILD files in the same chat — context from BUILD_03 about FastAPI scaffolding can leak into a BUILD_11 ML-training prompt and produce hybrid output that doesn't satisfy either contract.

---

## 2. Index by source file

| BUILD file | # prompts | One-line summary |
|---|---|---|
| BUILD_01_Project_Initialization.md | 3 | Bootstrap repo, verify bootstrap, onboarding doc |
| BUILD_02_Folder_Structure.md | 3 | Scaffold tree, per-folder READMEs, monorepo ADR |
| BUILD_03_Backend_API.md | 3 | FastAPI skeleton, request-logging middleware, service test |
| BUILD_04_Database_and_Storage.md | 3 | ORM models, first migration, dev seed script |
| BUILD_05_Frontend_App.md | 3 | UI primitives, localized survey page, OpenAPI→TS sync |
| BUILD_06_Auth_and_Users.md | 3 | Auth backend, frontend auth flow, audit-log middleware |
| BUILD_07_Module1_Awareness.md | 5 | Gazette scraper, PDF extractor, classify endpoint, summarizer, lag dashboard |
| BUILD_08_Module2_Knowledge.md | 5 | M2 migration, scoring, RAG ingest, RAGAS eval, multilingual survey UI |
| BUILD_09_Module3_Risk.md | 5 | Feature pipeline, SDV synth, XGBoost+Optuna, SHAP, drift cron |
| BUILD_10_Module4_Misinformation.md | 5 | Twitter ingester, Label Studio + κ, M4 trainer, RAG verifier, κ report |
| BUILD_11_ML_Training_Pipeline.md | 4 | BaseTrainer, eval-gate decorator, model-card generator, promotion CLI |
| BUILD_12_Data_Ingestion_and_Scheduling.md | 4 | Source registry, token bucket, Celery beat, IRD defaulter scrape |
| BUILD_13_Admin_and_Annotation.md | 3 | Admin route group, Label Studio webhook, audit immutability |
| BUILD_14_Deployment_Cloud.md | 3 | Backend Dockerfile + compose, nginx config, GitHub Actions deploy |
| BUILD_15_Observability_Testing.md | 3 | Prometheus + OTel wiring, integration testcontainers, k6 load script |
| BUILD_16_Progress_Tracker_Template.md | 2 | Weekly standup generator, supervisor-summary generator |

**Total: 57 prompts** across BUILD_01–16 (recapped verbatim under §5), plus **5 reusable meta-prompts** in §6.

---

## 3. Index by module

Module-1 (M1, BUILD_07) — 5 prompts.
Module-2 (M2, BUILD_08) — 5 prompts.
Module-3 (M3, BUILD_09) — 5 prompts.
Module-4 (M4, BUILD_10) — 5 prompts.

Cross-cutting (everything else) — 37 prompts:

- **BUILD_01** Project Initialization — 3
- **BUILD_02** Folder Structure — 3
- **BUILD_03** Backend API — 3
- **BUILD_04** Database & Storage — 3
- **BUILD_05** Frontend App — 3
- **BUILD_06** Auth & Users — 3
- **BUILD_11** ML Training Pipeline — 4
- **BUILD_12** Data Ingestion & Scheduling — 4
- **BUILD_13** Admin & Annotation — 3
- **BUILD_14** Deployment / Cloud — 3
- **BUILD_15** Observability & Testing — 3
- **BUILD_16** Progress Tracker — 2

---

## 4. Index by task

- **Scaffolding** — BUILD_01 #1–3, BUILD_02 #1–3, BUILD_03 #1, BUILD_05 #1, BUILD_06 #1–2.
- **Schema / migration** — BUILD_04 #1–2, BUILD_08 #1, BUILD_13 #3.
- **Scraper / ingest** — BUILD_07 #1–2, BUILD_10 #1, BUILD_12 #1, #4.
- **Trainer / eval** — BUILD_08 #2, #4, BUILD_09 #1–5, BUILD_10 #3–5, BUILD_11 #1–4.
- **UI / frontend** — BUILD_05 #1–3, BUILD_06 #2, BUILD_08 #5, BUILD_13 #1.
- **Deployment** — BUILD_14 #1–3.
- **Testing** — BUILD_03 #3, BUILD_15 #2, #3.
- **Observability** — BUILD_03 #2, BUILD_15 #1.
- **Annotation** — BUILD_10 #2, BUILD_13 #2.
- **Admin** — BUILD_06 #3, BUILD_13 #1, #3, BUILD_16 #1–2.
- **RAG / inference** — BUILD_07 #3–4, BUILD_08 #3, BUILD_10 #4.
- **Data seeding / fixtures** — BUILD_04 #3.
- **Scheduling / cron** — BUILD_07 #5, BUILD_09 #5, BUILD_12 #3.

---

## 5. Prompts

### From BUILD_01 — Project Initialization

#### Prompt 1 — Bootstrap repo files

```
You are setting up a Python + TypeScript monorepo named "enigmatrix-platform".
Generate exactly these files with sensible content:
- .gitignore (Python + Node + ML artifacts)
- .editorconfig
- .pre-commit-config.yaml (ruff + prettier + standard hooks)
- .env.example (matching the variables in BUILD_01 §3.4)
- Makefile (matching BUILD_01 §5)
- README.md (≤ 60 lines, runnable steps)
- .vscode/settings.json and .vscode/extensions.json

Output each file as a separate fenced code block with a `# FILE: <path>` header.
Do not include any explanation outside the code blocks.
```

*Source: BUILD_01_Project_Initialization.md → Section "Claude Prompts for This Section" → Prompt 1*

#### Prompt 2 — Verify the bootstrap

```
Given the repo files above, write a single bash script `scripts/verify_bootstrap.sh`
that checks: Python 3.11+, Node 20+, Docker running, .env exists, pre-commit installed,
and prints a green/red status for each. Exit 1 on any failure.
```

*Source: BUILD_01_Project_Initialization.md → Section "Claude Prompts for This Section" → Prompt 2*

#### Prompt 3 — Onboarding doc

```
Write a 1-page onboarding doc for a new team member joining "enigmatrix-platform".
Audience: a final-year IT student who has used Python and React but never set up a monorepo.
Cover: installing tools, cloning, env setup, first command to run, who to contact when stuck.
Length: 400–500 words. Markdown.
```

*Source: BUILD_01_Project_Initialization.md → Section "Claude Prompts for This Section" → Prompt 3*

---

### From BUILD_02 — Folder Structure

#### Prompt 1 — Generate the empty tree

```
Generate a single bash script `scripts/scaffold_tree.sh` that creates the exact
directory layout described in BUILD_02 §1–§6 of the Enigmatrix build plan.
Use `mkdir -p` and `touch .gitkeep` in empty dirs.
Make the script idempotent (re-runnable) and add a final `tree -L 2` to print results.
```

*Source: BUILD_02_Folder_Structure.md → Section "Claude Prompts for This Section" → Prompt 1*

#### Prompt 2 — Generate per-folder READMEs

```
For each of these folders, generate a 10–20 line README.md describing its purpose,
what lives there, and what does NOT live there:
- backend/app/api/
- backend/app/services/
- backend/app/ingestion/
- backend/app/models/
- ml/
- ml/shared/
- infra/

Output as separate fenced code blocks with `# FILE: <path>/README.md` headers.
```

*Source: BUILD_02_Folder_Structure.md → Section "Claude Prompts for This Section" → Prompt 2*

#### Prompt 3 — Architecture Decision Record

```
Write an ADR (Architecture Decision Record) in standard format
(Status, Context, Decision, Consequences) for:
"Use a monorepo with backend/, frontend/, ml/ separated by language and runtime
rather than a polyrepo or a single Python project."

Length: ~250 words. Reference Sri Lankan SME platform context where relevant.
Save as `docs/adr/0001-monorepo-layout.md`.
```

*Source: BUILD_02_Folder_Structure.md → Section "Claude Prompts for This Section" → Prompt 3*

---

### From BUILD_03 — Backend API (FastAPI)

#### Prompt 1 — Generate the FastAPI skeleton

```
You are scaffolding a FastAPI backend for the Enigmatrix platform.
Generate these files exactly, matching the conventions in BUILD_03:

- backend/app/settings.py
- backend/app/logging_config.py
- backend/app/exceptions.py
- backend/app/deps.py
- backend/app/main.py
- backend/app/api/health.py
- backend/app/api/v1/router.py
- backend/app/api/v1/auth.py        (501 stubs)
- backend/app/api/v1/users.py       (501 stubs)
- backend/app/api/v1/regulations.py (working list+get against models)
- backend/app/api/v1/qa.py          (501 stubs)
- backend/app/api/v1/risk.py        (501 stubs)
- backend/app/api/v1/verify.py      (501 stubs)
- backend/app/api/v1/surveys.py     (501 stubs)
- backend/app/api/v1/admin.py       (501 stubs)

Use async SQLAlchemy with AsyncSession.
Output as fenced blocks with `# FILE: <path>` headers. No prose outside code blocks.
```

*Source: BUILD_03_Backend_API.md → Section "Claude Prompts for This Section" → Prompt 1*

#### Prompt 2 — Add structured request logging

```
Add a FastAPI middleware to backend/app/main.py that emits a structured log
for every request: method, path, status_code, duration_ms, user_id (if auth'd),
and a generated request_id (uuid4) propagated via contextvars so all downstream
log calls in the same request include it.
Output the patched main.py and any new helper file.
```

*Source: BUILD_03_Backend_API.md → Section "Claude Prompts for This Section" → Prompt 2*

#### Prompt 3 — Write a service test

```
Write pytest-asyncio tests for app.services.regulation_service.list_regulations
covering: empty DB, filtering by category, pagination boundaries, and case-insensitive
text search. Use a sqlite-in-memory fixture (or Postgres testcontainer).
Place the file at backend/app/tests/unit/test_regulation_service.py.
```

*Source: BUILD_03_Backend_API.md → Section "Claude Prompts for This Section" → Prompt 3*

---

### From BUILD_04 — Database & Storage Layer

#### Prompt 1 — Generate ORM models

```
Generate SQLAlchemy 2.0 async models for these tables, matching the schema in
research file 06 §4 and BUILD_04 §5: users, sme_profiles, regulations,
regulation_classifications, regulation_secondary_appearances, sme_alert_subscriptions,
labeled_examples, training_runs, model_versions, survey_responses, alerts,
claims (Module 4), audit_log.

Use Mapped[] type hints, PGUUID for UUIDs, JSONB for json columns, and
add useful indexes (gazette_date, predicted_category, text_hash, used_in_training).
Use a TimestampMixin. Output one file per aggregate, with `# FILE:` headers.
```

*Source: BUILD_04_Database_and_Storage.md → Section "Claude Prompts for This Section" → Prompt 1*

#### Prompt 2 — First migration

```
Given the model files above, write the initial Alembic migration manually
(not via autogenerate). Name: 202604010001_initial_schema.py.
Include all tables, all foreign keys, all indexes from the models, and
`op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")` etc. at the top.
Provide both upgrade() and downgrade().
```

*Source: BUILD_04_Database_and_Storage.md → Section "Claude Prompts for This Section" → Prompt 2*

#### Prompt 3 — Seed dev data

```
Write app/scripts/seed_dev.py that creates:
- 1 admin user (admin@enigmatrix.lk / admin)
- 3 annotator users
- 5 sample SME profiles (across sectors: retail, food, garment, IT services, transport)
- 10 sample regulations spanning 3 categories with realistic Sri Lankan agency names
  (IRD, EPF/ETF, SLSI, ROC, Customs)
- 20 labeled_examples with used_in_training=False
Idempotent: re-running should not create duplicates.
Use `python -m app.scripts.seed_dev`.
```

*Source: BUILD_04_Database_and_Storage.md → Section "Claude Prompts for This Section" → Prompt 3*

---

### From BUILD_05 — Frontend (Next.js 14, App Router)

#### Prompt 1 — Generate UI primitives

```
Generate these UI primitive components for a Next.js 14 + TypeScript + Tailwind app
using class-variance-authority and Radix UI primitives:
button, input, textarea, select, label, card, dialog, dropdown,
tabs, toast (with provider), badge, skeleton, alert, pagination.

Each as `# FILE: frontend/components/ui/<name>.tsx`. Use the design tokens from
BUILD_05 §2 (--bg, --fg, --primary, --muted, etc.). No prose.
```

*Source: BUILD_05_Frontend_App.md → Section "Claude Prompts for This Section" → Prompt 1*

#### Prompt 2 — Generate localized survey

```
Build a complete `/surveys/awareness` page (Next.js 14 app router) that:
- Loads the question set from `lib/surveys/awareness.ts` (12 questions matching
  research file 08_SME_Questionnaire_Design.md §3)
- Uses react-hook-form + zod for validation
- Supports en/si/ta question text via next-intl
- Submits to POST /api/v1/surveys/awareness/submit with the access token
- Shows a thank-you screen on success

Output: page.tsx, the question set file, and a thank-you component.
```

*Source: BUILD_05_Frontend_App.md → Section "Claude Prompts for This Section" → Prompt 2*

#### Prompt 3 — Sync TS types from OpenAPI

```
Set up automatic generation of TypeScript types in frontend/lib/types/api.ts
from the FastAPI OpenAPI schema at http://localhost:8000/openapi.json
using openapi-typescript. Include:
- The pnpm script `gen:types`
- A pre-commit hook so types regenerate on backend schema changes
- A README block explaining the workflow
```

*Source: BUILD_05_Frontend_App.md → Section "Claude Prompts for This Section" → Prompt 3*

---

### From BUILD_06 — Authentication, Users & RBAC

#### Prompt 1 — Generate auth backend

```
Generate the complete Enigmatrix auth backend exactly as specified in BUILD_06 §2–§6:
- backend/app/core/security.py
- backend/app/services/auth_service.py
- backend/app/schemas/auth.py
- backend/app/api/v1/auth.py
- backend/app/api/v1/users.py (just GET /me)
- a require_roles dependency in backend/app/deps.py

Use SQLAlchemy 2.0 async, Pydantic v2, python-jose for JWT, passlib[bcrypt] for hashing.
Include unit tests at backend/app/tests/unit/test_auth_service.py covering:
- duplicate email rejection
- correct password verification
- refresh token rotation
- expired token rejection.

Output as `# FILE: <path>` blocks. No prose.
```

*Source: BUILD_06_Auth_and_Users.md → Section "Claude Prompts for This Section" → Prompt 1*

#### Prompt 2 — Generate frontend auth

```
Generate frontend auth for a Next.js 14 (App Router) app:
- frontend/lib/auth/session.ts (per BUILD_06 §7)
- frontend/lib/auth/use-session.ts
- frontend/app/(auth)/login/page.tsx
- frontend/app/(auth)/register/page.tsx (with SMEProfileIn fields)
- frontend/app/api/auth/establish/route.ts
- frontend/app/api/auth/token/route.ts
- frontend/app/api/auth/logout/route.ts (clears cookies)

Use react-hook-form + zod for forms. Tailwind. Show error states. Localize via next-intl.
```

*Source: BUILD_06_Auth_and_Users.md → Section "Claude Prompts for This Section" → Prompt 2*

#### Prompt 3 — Audit log middleware

```
Add a FastAPI middleware that, after every authenticated request to /api/v1/admin/*,
inserts a row into audit_log with: event_type='admin.access',
table_name='', record_id=None, user_name=user.email,
event_data_json={"path": request.url.path, "method": request.method, "status": response.status_code}.
Output the middleware file and the wiring change in main.py.
```

*Source: BUILD_06_Auth_and_Users.md → Section "Claude Prompts for This Section" → Prompt 3*

---

### From BUILD_07 — Module 1: Regulatory Awareness Pipeline

#### Prompt 1 — Gazette listing scraper

```
You're scraping documents.gov.lk to produce a list of GazetteRef
(gazette_number, gazette_date, pdf_url) for the last 30 days.
Step 1: Inspect the page structure (assume the table contains <a href> with gazette PDFs)
Step 2: Output a robust async httpx + BeautifulSoup implementation in
        backend/app/ingestion/gazette/lister.py with:
   - Retry up to 3x with exponential backoff (use tenacity)
   - Date parsing tolerant of multiple formats
   - Skip rows that look like Bills (not Acts/Gazettes)
   - 30-second timeout
Include a CLI: `python -m app.ingestion.gazette.lister --since 2026-01-01`.
```

*Source: BUILD_07_Module1_Awareness.md → Section "Claude Prompts for This Section" → Prompt 1*

#### Prompt 2 — Robust PDF extractor

```
Extend backend/app/ingestion/gazette/extractor.py to:
- Try PyMuPDF first; if `_looks_text` fails, try pdfplumber
- If both fail, run Tesseract OCR with eng+sin+tam at 300 dpi
- Return ExtractedDoc with method and confidence
- Detect language by Unicode block presence (Sinhala 0D80–0DFF, Tamil 0B80–0BFF)
- Add unit tests using the three sample PDFs in `backend/app/tests/data/`:
  one text PDF, one scanned, one mixed-language.
```

*Source: BUILD_07_Module1_Awareness.md → Section "Claude Prompts for This Section" → Prompt 2*

#### Prompt 3 — Inference endpoint with model registry

```
Wire up backend/app/api/v1/regulations.py with a POST /classify endpoint
(admin-only, used for retroactive classification) that:
- loads the production XLM-R artifact via app.ml_serving.registry
- accepts {"text": "..."} and returns {"category", "confidence", "all_probs"}
- caches the loaded model in-process (lru_cache by artifact_path)
- logs every prediction to a `model_predictions` table (auto-generate the model)
```

*Source: BUILD_07_Module1_Awareness.md → Section "Claude Prompts for This Section" → Prompt 3*

#### Prompt 4 — Local multilingual summarizer

```
Add backend/app/services/module1/summarizer.py implementing:
- `summarize_extractive_then_translate(text) -> {summary_en, summary_si, summary_ta}`
- Lead-3 extraction in English (or extract from the original-language text first
  then translate using NLLB-200 via `transformers`)
- Use Hugging Face NLLB checkpoint `facebook/nllb-200-distilled-600M`
- Cache the model with lru_cache(maxsize=1)
- Strip phone numbers (regex) before storage (per misinformation module ethics)
- Provide a CLI for ad-hoc summarization
```

*Source: BUILD_07_Module1_Awareness.md → Section "Claude Prompts for This Section" → Prompt 4*

#### Prompt 5 — Lag dashboard endpoint

```
Implement GET /api/v1/admin/lag/distribution returning JSON for the lag dashboard:
- For each category: median lag in days, p25, p75, p95, sample size
- For each diffusion stage: gazette→portal, portal→news, gazette→news
- Use the SQL from BUILD_07 §8 as a starting point and parameterize by date range.
Add a Recharts bar chart on /admin/lag in the frontend.
```

*Source: BUILD_07_Module1_Awareness.md → Section "Claude Prompts for This Section" → Prompt 5*

---

### From BUILD_08 — Module 2: Compliance Knowledge & RAG

#### Prompt 1 — Alembic migration for M2 tables

```
Generate backend/alembic/versions/0008_m2_tables.py for an async SQLAlchemy 2.0
project. Create exactly the four tables defined in BUILD_08 §2:
m2_questions, sme_profiles, survey_responses, sme_knowledge_scores.
- Match every column name, type, default, and CHECK constraint verbatim.
- Use op.create_table + op.create_index; emit an idempotent downgrade.
- Foreign keys to existing 'smes' (sme_id BIGINT) must use ON DELETE CASCADE.
- Add a CHECK ensuring m2_questions.instrument ∈ {awareness, knowledge_test, vulnerability}.
- Do NOT alter any base table; this migration only adds the M2 surface.
```

*Source: BUILD_08_Module2_Knowledge.md → Section "Claude Prompts for This Section" → Prompt 1*

#### Prompt 2 — Scoring service with weighted composite

```
Implement backend/app/modules/m2/scoring.py exactly as sketched in BUILD_08 §6
plus a recompute_for_all() that iterates every SME with at least one response and
upserts sme_knowledge_scores in batches of 200.
- Use SQLAlchemy 2.0 async syntax.
- Composite weights: awareness 0.25, knowledge_test 0.50, vulnerability 0.25.
- For mcq_multi, score by Jaccard against q.correct_answer.set.
- Honor q.reverse_scored on Likert items.
- Compute sector_percentile within sme_profiles.sector_code using PERCENT_RANK in SQL.
- Add unit tests covering: a perfectly correct test → 100, all-wrong → 0,
  reverse-scored Likert sanity, and a profile missing one instrument.
```

*Source: BUILD_08_Module2_Knowledge.md → Section "Claude Prompts for This Section" → Prompt 2*

#### Prompt 3 — RAG ingestion CLI with progress bar + idempotency

```
Implement ml/m2/build_kb.py per BUILD_08 §8.
- Read EMBEDDING_MODEL from env (default intfloat/multilingual-e5-base).
- Use RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64).
- ChromaDB collection name: regulations_chunks_v1 with cosine HNSW.
- Document IDs: f"{regulation_id}:{lang}:{idx}:{sha256(chunk)[:12]}".
- Skip IDs already present in the collection (idempotent re-runs).
- e5 prefix convention: "passage: " for docs, "query: " for queries.
- tqdm progress bar over regulations; final line prints the upsert count.
- Add a --dry-run flag that prints the would-be upsert count without writing.
```

*Source: BUILD_08_Module2_Knowledge.md → Section "Claude Prompts for This Section" → Prompt 3*

#### Prompt 4 — RAGAS eval script + golden-set fixture loader

```
Build ml/m2/eval_ragas.py and ml/m2/golden_set.yaml.
- Golden set: 50 Q/A pairs derived from real Sri Lankan gazettes (Jan 2025–Apr 2026),
  each with question, expected_answer, expected_regulation_ids, language ∈ {en,si,ta}.
- Use ragas metrics: faithfulness, answer_relevancy, context_precision, context_recall.
- Thresholds: faithfulness ≥ 0.85, answer_relevancy ≥ 0.80, context_precision ≥ 0.75.
- Exit non-zero on any threshold miss; write ml/m2/last_eval.json.
- Pull contexts via the actual retriever used by app.modules.m2.rag (top_k=5).
- Include 5 fully-worked example items in the YAML so the schema is unambiguous.
```

*Source: BUILD_08_Module2_Knowledge.md → Section "Claude Prompts for This Section" → Prompt 4*

#### Prompt 5 — Next.js multilingual survey form with next-intl + autosave

```
Build frontend/app/surveys/[instrument]/page.tsx and the supporting
lib/api/m2.ts client described in BUILD_08 §5.
- Use next-intl for EN/SI/TA prompt rendering; locale comes from useLocale().
- Use react-hook-form for state; do not introduce Redux.
- Autosave every 30s via POST /api/v1/m2/surveys/autosave with the resume_token.
- Persist the resume_token in the URL as ?rt=… so refresh resumes the session.
- Implement branching: hide a question if its branching.show_if condition is unmet.
- Render a shadcn/ui Progress bar reflecting (idx+1)/visible.length.
- Question types to support: likert5, mcq_single, mcq_multi, binary, numeric.
- A11y: every input has a label; radio groups have role=radiogroup and an aria-label.
```

*Source: BUILD_08_Module2_Knowledge.md → Section "Claude Prompts for This Section" → Prompt 5*

---

### From BUILD_09 — Module 3: Compliance Risk Prediction

#### Prompt 1 — Feature pipeline with leakage assertions

```
Implement ml/m3/features.py per BUILD_09 §3. Requirements:
- async function build_feature_row(db, sme_id, snapshot_date, knowledge_api_base)
- 40+ features across 5 families (firmographic, behavioral, sectoral JSONB-unfolded,
  M1-exposure, M2-knowledge via httpx GET to {knowledge_api_base}/m2/sme/{id}/knowledge_score)
- Compute the 24-month forward label using m3_compliance_history events strictly after snapshot
- Raise AssertionError on any contributing event with event_date > snapshot_date
- Return None label when the forward 24mo window is not yet observed (cold-start exclusion)
- Add pytest cases that construct in-memory fixtures and assert leakage detection fires.
```

*Source: BUILD_09_Module3_Risk.md → Section "Claude Prompts" → Prompt 1*

#### Prompt 2 — SDV synthesizer + constraint validation

```
Implement ml/m3/synth.py using sdv>=1.13,<2:
- fit_synthesizer(df) returns a GaussianCopulaSynthesizer with metadata auto-detected
  and constraints: ScalarRange on business_age_years (0–80) and FixedCombinations on
  (sector, employee_count_band).
- augment(real, synth, target_pos_rate=0.35, max_synth_ratio=0.30) over-samples then
  filters to a positive rate, asserts the synthetic ratio cap, and rejects rows that
  violate domain rules (employee_count_band whitelist, non-negative ages).
- Add a CLI: python -m ml.m3.synth --in real.parquet --out aug.parquet --cap 0.30.
```

*Source: BUILD_09_Module3_Risk.md → Section "Claude Prompts" → Prompt 2*

#### Prompt 3 — XGBoost + Optuna training script with MLflow logging

```
Implement ml/m3/train_xgb.py per §5:
- Stratified 5-fold CV inside an Optuna TPE study (n_trials=50) maximising mean fold AUC
- Hyperparameters: max_depth, learning_rate, n_estimators, min_child_weight, subsample,
  colsample_bytree, reg_lambda; tree_method='hist'
- scale_pos_weight = neg/pos on the training set
- Wrap the best model in CalibratedClassifierCV(method='isotonic', cv=5)
- Log params, holdout AUC, P@10%, ECE, scale_pos_weight, synthetic ratio, and the
  feature_columns.json artifact to MLflow
- Promote to models:/m3-risk/Production only if holdout AUC ≥ 0.75 AND P@10 ≥ 0.60.
```

*Source: BUILD_09_Module3_Risk.md → Section "Claude Prompts" → Prompt 3*

#### Prompt 4 — SHAP service returning JSON-friendly explanations

```
Implement ml/m3/explain.py with class M3Explainer:
- Construct shap.TreeExplainer from the underlying XGBoost booster inside the
  CalibratedClassifierCV wrapper.
- top_features(x_row, k=5) returns a list of {feature, value, shap, direction} dicts
  with all numpy scalars converted to Python types.
- Add a unit test that asserts the sum of returned shap values has the same sign
  as the model's logit prediction on a known fixture row.
```

*Source: BUILD_09_Module3_Risk.md → Section "Claude Prompts" → Prompt 4*

#### Prompt 5 — Drift-monitoring cron job

```
Implement ml/m3/drift.py per §9 and a APScheduler job that runs daily at 03:00 Asia/Colombo:
- Compute PSI per numeric feature against the baseline parquet pinned at registry promotion.
- Compute rolling 90-day AUC on real (non-synthetic) holdout predictions joined to labels
  that have aged past the 24mo forward window.
- If any feature PSI > 0.25 OR rolling AUC < 0.70, insert a TrainingRun row with
  status='queued' and notes='auto-drift-trigger'.
- Emit a structured log line and a metric to Prometheus (drift_psi_max, m3_rolling_auc).
```

*Source: BUILD_09_Module3_Risk.md → Section "Claude Prompts" → Prompt 5*

---

### From BUILD_10 — Module 4: Misinformation Detection & Verification

#### Prompt 1 — Twitter Academic API ingester with backfill + cursor pagination

```
Implement `app/modules/m4/sources/twitter.py` extending `SourceConnector`. Use `tweepy.Client.search_all_tweets` against the trilingual keyword query in this file. Persist `next_token` in a new `m4_ingest_state` table keyed by `(platform, query_hash)` so that re-runs resume from the last cursor. Add a `backfill(since, until)` method that walks the cursor backwards in 7-day windows, sleeps on rate-limit headers, and yields `IngestRecord` objects. Add `tests/m4/test_twitter.py` that mocks `tweepy.Client` with `respx`-style fixtures and asserts dedup via `content_hash`.
```

*Source: BUILD_10_Module4_Misinformation.md → Section "Claude Prompts" → Prompt (a)*

#### Prompt 2 — Label Studio config + import script with kappa report

```
Generate `ops/label_studio/m4_veracity.xml` matching the XML in `BUILD_10`. Then write `scripts/m4/import_to_ls.py` that pulls cleaned posts not yet sent to Label Studio (left join on `m4_labeled_posts`), calls the LS REST API to create tasks, and tags each task with the cleaned_post_id. Finally write `scripts/m4/kappa_report.py` that loads all consensus-eligible labels from `m4_labeled_posts`, computes pairwise Cohen's kappa via `sklearn.metrics.cohen_kappa_score`, and writes a markdown report to `reports/m4/kappa_<date>.md`. Fail with exit 1 if cohort kappa < 0.70.
```

*Source: BUILD_10_Module4_Misinformation.md → Section "Claude Prompts" → Prompt (b)*

#### Prompt 3 — XLM-R fine-tune script via HF Trainer + W&B (cross-ref BUILD_11)

```
In `BUILD_11_ML_Training_Pipeline.md` add `pipelines/m4_veracity_train.py` that loads `m4_labeled_posts where is_consensus_label = TRUE`, stratified-splits 80/10/10 by veracity, fine-tunes `xlm-roberta-base` with `transformers.Trainer` (epochs=4, lr=2e-5, batch=16, fp16), uses a `WeightedRandomSampler` for class imbalance, logs to W&B project `enigmatrix-m4`, computes macro-F1 + per-class F1 + confusion matrix, and registers the model to MLflow as `m4-veracity` with stage `Staging`. Promotion to `Production` is manual after macro-F1 ≥ 0.75 is confirmed.
```

*Source: BUILD_10_Module4_Misinformation.md → Section "Claude Prompts" → Prompt (c)*

#### Prompt 4 — RAG verifier chain returning verdict + citations

```
Implement `app/modules/m4/verify.py` exactly as in `BUILD_10`. Add a small benchmark `tests/m4/test_verify_golden.py` that loads `tests/m4/golden/claim_check.jsonl`, runs each claim through `verify`, computes accuracy of `verdict` against the gold label collapsed to `{supports, refutes, unverifiable}`, and asserts ≥ 0.80. Wire in RAGAS faithfulness via `ragas.metrics.faithfulness` evaluated on the (claim, retrieved chunks, verdict) triples and assert ≥ 0.85.
```

*Source: BUILD_10_Module4_Misinformation.md → Section "Claude Prompts" → Prompt (d)*

#### Prompt 5 — Cohen kappa report generator across annotators

```
Write `scripts/m4/kappa_report.py` that accepts an optional `--since` date, builds an N x N kappa matrix across all annotators with at least 30 overlapping items, prints per-pair κ, the cohort weighted κ, and an agreement breakdown by veracity class. Output is markdown plus a CSV. The script is run nightly by Celery beat (see `BUILD_12`); a κ < 0.70 trips a Slack alert via the integration in `BUILD_13`.
```

*Source: BUILD_10_Module4_Misinformation.md → Section "Claude Prompts" → Prompt (e)*

---

### From BUILD_11 — ML Training Pipeline

#### Prompt 1 — Base Trainer class

```
Generate ml/common/trainer.py implementing BaseTrainer (abstract) with:
- TrainConfig dataclass: module_number, experiment, dataset, dataset_version,
  seed, output_dir, hyperparams.
- run() that: seeds via ml.common.seeding; loads train/val/test from
  ml.common.dataset.load_split (which sha-checks against
  ml/datasets/manifest.yaml); opens an MLflow run via
  ml.common.mlflow_utils.start_run with full tag set (module_number,
  dataset_version, dataset_sha_train, git_sha, python_version, seed,
  gate_status=pending); snapshots env + freezes per-run requirements.txt as
  MLflow artifact; calls fit/evaluate/save abstract methods; inserts a row
  into Postgres training_runs (BUILD_04 §5) via
  ml.common.registry.write_training_run_row.
- Subclasses override fit, evaluate, save. Make evaluate() compatible with
  @enforce_gate. Include a docstring explaining the inter-module contract.
```

*Source: BUILD_11_ML_Training_Pipeline.md → Section "Claude Prompts for This Section" → Prompt 1*

#### Prompt 2 — Eval-gate decorator

```
Generate ml/common/gates.py defining GateFailure(RuntimeError) and
enforce_gate(*, metric: str, threshold: float) — a decorator that wraps an
evaluator method returning {metric_name: value}. It must: log the metric;
set MLflow tags gate_status=passed|failed, gate_metric, gate_threshold;
log a derived metric f"{metric}_vs_threshold"; raise GateFailure when
value < threshold. Hard-code a GATES dict for reference (so promotion code
can read it) — M1 f1_macro >= 0.80, M3 roc_auc >= 0.75, M4 f1_macro >= 0.75,
M2 ragas_faithfulness >= 0.85 — but the threshold actually applied must come
from the decorator argument. Include unit tests covering pass, fail, and
missing-metric cases.
```

*Source: BUILD_11_ML_Training_Pipeline.md → Section "Claude Prompts for This Section" → Prompt 2*

#### Prompt 3 — Model-card auto-generator

```
Generate ml/registry/card.py with render_card(run_id, model_name, version):
- Pulls run data from MLflow (tags, params, metrics).
- Renders ml/registry/card_template.md.j2 populating model_name, version,
  run_id, module_number, dataset_version, dataset_sha_train, git_sha,
  trained_at, metrics, hyperparams, intended_use, limitations, seed,
  python_version, cpu_count, ram_gb, gpu_available.
- gate_for(metric) helper returns ">= <threshold>" for the four canonical
  gates and "—" otherwise.
- Writes ml/registry/cards/{model_name}_v{version}.md and returns the
  markdown string (so promotion CLI can attach it as the registry version
  description). Provide _intended_use / _limitations stubs per module
  (M1 gazette classification, M3 fraud risk score, M4 claim stance).
```

*Source: BUILD_11_ML_Training_Pipeline.md → Section "Claude Prompts for This Section" → Prompt 3*

#### Prompt 4 — MLflow promotion CLI

```
Generate ml/registry/promote.py with CLI:
  python -m ml.registry.promote --run-id <id> --model-name <name> --module-number <n>
Behavior:
  1. Refuse if run.tags.gate_status != "passed".
  2. mlflow.register_model(f"runs:/{run_id}/model", model_name).
  3. transition_model_version_stage(..., stage="Production",
                                    archive_existing_versions=True).
  4. Render a card via ml.registry.card.render_card and attach it as the
     version description.
  5. In a single Postgres transaction (SQLAlchemy `with engine.begin()`):
       UPDATE model_versions SET is_production=FALSE
         WHERE module_number=:m AND is_production=TRUE;
       INSERT INTO model_versions (module_number, mlflow_run_id, registry_name,
         registry_version, training_run_id, is_production, deployed_at)
         VALUES (..., TRUE, now());
Print the new model_versions.id and registry version on success. Exit
non-zero on any failure and leave Postgres unchanged (rollback).
```

*Source: BUILD_11_ML_Training_Pipeline.md → Section "Claude Prompts for This Section" → Prompt 4*

---

### From BUILD_12 — Data Ingestion & Scheduling

#### Prompt 1 — Source registry + base watcher class

```
Generate backend/app/ingest/registry.py and backend/app/ingest/base.py per
BUILD_12 §1. Requirements:
- SourceSpec dataclass with fields: name, base_url, url_pattern, parser,
  cadence_cron, owner_module, transport, tos_notes, robots_compliance,
  download_delay_s, priority_queue, tags.
- A SOURCES dict with the 18 entries listed in BUILD_12 §1, exact cron
  strings preserved.
- BaseWatcher abstract class with async run() that emits an ingest_event
  structlog line (run_id, source, items_seen, items_inserted, duration_ms,
  errors_count) and delegates fetching to subclass `fetch()`.
- Add a unit test that verifies every SourceSpec.cadence_cron parses as a
  valid 5-field cron via croniter.
```

*Source: BUILD_12_Data_Ingestion_and_Scheduling.md → Section "Claude Prompts" → Prompt 1*

#### Prompt 2 — Token-bucket rate limiter

```
Generate backend/app/core/host_rate_limit.py per BUILD_12 §9.
Requirements:
- TokenBucket(capacity, refill_rate) with asyncio.Lock and monotonic clock.
- bucket_for(host) returns a singleton TokenBucket; refill rate derived
  from SOURCES[*].download_delay_s by matching urlparse(base_url).netloc.
- Default delay 1.5s for unknown hosts.
- Add a Scrapy DownloaderMiddleware HostBucketMiddleware that awaits
  bucket_for(host).acquire() before every request.
- Include a pytest that schedules 10 acquisitions on a 0.1s/refill bucket
  and asserts the wall-clock duration >= 0.9s.
- Add an inline docstring noting this is OUTBOUND and unrelated to
  BUILD_06's slowapi inbound limiter.
```

*Source: BUILD_12_Data_Ingestion_and_Scheduling.md → Section "Claude Prompts" → Prompt 2*

#### Prompt 3 — Celery beat config from registry

```
Generate backend/app/ingest/celery_app.py per BUILD_12 §8. Requirements:
- Celery app with Redis 7 broker/backend.
- task_routes mapping send_alerts.flush -> 'urgent', run_bulk_source ->
  'bulk', everything else default.
- Retry policy: max_retries=5, exponential backoff with jitter, capped
  at 600s.
- beat_schedule built programmatically from app.ingest.registry.SOURCES,
  with bulk-priority sources routed to run_bulk_source.
- Dead-letter signal handler that writes to a DeadLetter table on final
  retry exhaustion.
- Add a test that asserts every SOURCES key has a matching beat entry
  and that the queue routing matches the spec's priority_queue.
```

*Source: BUILD_12_Data_Ingestion_and_Scheduling.md → Section "Claude Prompts" → Prompt 3*

#### Prompt 4 — IRD defaulter scraper with snapshot diff

```
Generate backend/app/ingest/scrapers/ird/defaulter.py and
backend/app/services/m3/defaulter_diff.py per BUILD_12 §5. Requirements:
- IRDDefaulterSpider with DOWNLOAD_DELAY=3, ROBOTSTXT_OBEY=True, custom
  user agent. Selectors documented as 'verify by inspection (2026-04)'.
- _parse_amount tolerates 'LKR 1,234,567.00' and bare numbers.
- apply_snapshot(db, rows) computes added/removed/changed by row_hash
  (sha256 of tin|name|amount|period), writes ComplianceEvent rows, and
  flips the previous snapshot's is_latest flag in a single transaction.
- Idempotent: re-running with identical rows produces 0 new events.
- Include a pytest fixture with two synthetic snapshots and assert
  exactly 1 added, 1 removed, 1 amount_changed event when one TIN is
  added, one is dropped, and one has its amount changed.
```

*Source: BUILD_12_Data_Ingestion_and_Scheduling.md → Section "Claude Prompts" → Prompt 4*

---

### From BUILD_13 — Admin Console & Annotation

#### Prompt 1 — Admin route group with role-gated middleware

```
Generate the Next.js App Router route group `frontend/app/(admin)/` for the Enigmatrix admin console. Produce: (1) `layout.tsx` server component that calls `/api/v1/users/me` with the `access_token` cookie and redirects non-{admin, superadmin, annotator} users to `/forbidden`; (2) `frontend/middleware.ts` matching `/admin/:path*` that redirects unauthenticated users to `/login?next=...` but defers role checks to the layout; (3) the index page `(admin)/page.tsx` rendering tiles for `/admin/regulations`, `/admin/posts`, `/admin/predictions`, `/admin/questions`, `/admin/audit`. Use TypeScript, no `any`. Do not re-implement JWT decoding — `fetchMe(token)` is provided. Output one file per code block.
```

*Source: BUILD_13_Admin_and_Annotation.md → Section "Claude Prompts" → Prompt (a)*

#### Prompt 2 — Label Studio webhook handler with HMAC verification + import

```
Implement `backend/app/integrations/label_studio.py` for FastAPI. Provide a `POST /integrations/label-studio/webhook` route that (1) verifies the `X-Signature` header is `hmac.compare_digest`-equal to `HMAC-SHA256(LS_WEBHOOK_SECRET, raw_body)`, (2) handles only `action == "ANNOTATION_CREATED"`, (3) extracts `task.data.post_id` and the first choice in `annotation.result[0].value.choices`, (4) calls `session.upsert_post_label(...)` and `write_audit(...)` in the same async transaction. Return 401 on bad signature, 200 with `{"ok": true}` on success. Use SQLAlchemy 2.0 async style and Pydantic v2 schemas.
```

*Source: BUILD_13_Admin_and_Annotation.md → Section "Claude Prompts" → Prompt (b)*

#### Prompt 3 — Audit-log Postgres trigger preventing UPDATE/DELETE

```
Write an Alembic migration that (1) adds columns `event_type TEXT NOT NULL DEFAULT 'legacy'`, `target_table TEXT`, `target_id TEXT`, `payload_json JSONB` to the existing `audit_log` table from BUILD_04, (2) creates an index on `event_type`, (3) defines a PL/pgSQL function `audit_log_immutable()` that `RAISE EXCEPTION` on any operation, (4) attaches `BEFORE UPDATE` and `BEFORE DELETE` row-level triggers on `audit_log` invoking that function, and (5) supplies a complete `downgrade()` that drops the triggers, the function, the index, and the new columns in reverse order. Target Postgres 15+.
```

*Source: BUILD_13_Admin_and_Annotation.md → Section "Claude Prompts" → Prompt (c)*

---

### From BUILD_14 — Cloud Deployment

#### Prompt 1 — Backend Dockerfile + compose service

```
Write a multi-stage `apps/backend/Dockerfile` for an Enigmatrix FastAPI app using `python:3.11-slim` and `uv` with `uv.lock` in frozen mode, producing a non-root runtime image with a `/health` HEALTHCHECK and gunicorn launching two `uvicorn.workers.UvicornWorker`. Then emit the matching `backend` service block for `docker-compose.yml` with healthcheck, env_file layering, depends_on conditions on postgres, redis, and chromadb, and a 2 GB / 1 vCPU resource limit. Do not include torch.
```

*Source: BUILD_14_Deployment_Cloud.md → Section "Claude Prompts" → Prompt (a)*

#### Prompt 2 — nginx config

```
Generate `infra/nginx/enigmatrix.conf` that terminates TLS for `enigmatrix.app`, redirects HTTP to HTTPS, sets an HSTS header with `max-age=63072000; includeSubDomains; preload`, defines two `limit_req_zone`s (`auth_zone` 5 r/s and `api_zone` 30 r/s), proxies `/api/v1/auth/*` through `auth_zone`, the rest of `/api/*` through `api_zone`, `/annotate/` to Label Studio behind basic-auth, and `/` to the Next.js frontend. Include keepalive upstreams and a `/.well-known/acme-challenge/` location for certbot.
```

*Source: BUILD_14_Deployment_Cloud.md → Section "Claude Prompts" → Prompt (b)*

#### Prompt 3 — GitHub Actions deploy workflow

```
Write `.github/workflows/deploy.yml` that on push to `main` builds three images (backend, frontend, ml-worker) with `docker/build-push-action`, pushes them to GHCR tagged with both `${{ github.sha }}` and `latest`, and then in a gated `production` environment ssh-deploys to the VM. Use OIDC where possible (`permissions: id-token: write`) and fall back to an SSH key in `secrets.DEPLOY_SSH_KEY`. The remote step must read the active colour from `/etc/enigmatrix/active`, deploy to the opposite colour with `IMAGE_TAG=${{ github.sha }}`, and run `infra/deploy/promote.sh` to switch nginx.
```

*Source: BUILD_14_Deployment_Cloud.md → Section "Claude Prompts" → Prompt (c)*

---

### From BUILD_15 — Observability & Testing

#### Prompt 1 — Add Prometheus + OpenTelemetry to the backend

```
You are working in the Enigmatrix FastAPI backend at backend/app/.
Goal: add Prometheus metrics and OpenTelemetry tracing without breaking
existing structlog correlation IDs from BUILD_03.

Tasks:
1. Add to backend/pyproject.toml:
   prometheus-fastapi-instrumentator, prometheus-client,
   opentelemetry-api, opentelemetry-sdk,
   opentelemetry-exporter-otlp-proto-grpc,
   opentelemetry-instrumentation-fastapi,
   opentelemetry-instrumentation-sqlalchemy,
   opentelemetry-instrumentation-httpx,
   opentelemetry-instrumentation-celery.
2. Create backend/app/core/metrics.py defining the four module counters
   (m1_gazettes_ingested_total, m2_rag_queries_total,
   m3_predictions_total, m4_claims_verified_total) plus the latency
   histograms shown in BUILD_15 section 2, and an install_metrics(app).
3. Create backend/app/core/tracing.py exposing install_tracing(app, engine)
   with TraceIdRatioBased(0.01 in production, 1.0 otherwise), OTLP gRPC
   exporter, and FastAPI/SQLAlchemy/httpx/Celery instrumentors.
4. Add a structlog processor add_trace_ids in backend/app/core/logging.py
   that copies the active OTel span's trace_id and span_id into every log
   record. Insert it after the existing correlation_id processor.
5. Wire install_metrics and install_tracing in backend/app/main.py after
   the CorrelationIdMiddleware is added. Pass the SQLAlchemy engine from
   backend/app/core/db.py.
6. Add unit tests at backend/app/tests/unit/test_metrics.py asserting:
   - GET /metrics returns 200 and contains "m4_claims_verified_total".
   - install_metrics is idempotent.

Constraints:
- Do not change existing endpoint behaviour.
- Do not log secrets; OTLP endpoint comes from settings.OTEL_EXPORTER_ENDPOINT.
- /metrics and /healthz must be excluded from tracing and from
  http_requests_total histograms.

Deliverables: the new files, the edited main.py and logging.py, the new
test file, and a one-paragraph note in the PR body listing the four
counter names so reviewers can grep dashboards.
```

*Source: BUILD_15_Observability_Testing.md → Section "Claude Prompts" → Prompt 1*

#### Prompt 2 — Testcontainers integration fixture for Postgres + Chroma

```
You are setting up backend integration tests for Enigmatrix.

Goal: build backend/app/tests/integration/conftest.py that gives every
async test a clean database and a live ChromaDB, using
testcontainers-python and pytest-asyncio.

Requirements:
1. Session-scoped PostgresContainer("postgres:16-alpine"). Build an async
   engine from its connection URL (replace psycopg2 with asyncpg) and
   create_all() Base.metadata once.
2. Session-scoped ChromaContainer("chromadb/chroma:0.5.5"). Override
   settings.CHROMA_HOST and settings.CHROMA_PORT inside the client fixture.
3. Function-scoped db_session that opens a connection, begins a
   transaction, yields an AsyncSession bound to that connection, and
   rolls back on teardown so tests are isolated.
4. Function-scoped client that overrides app.dependency_overrides[get_db]
   to return db_session, builds an httpx.AsyncClient on
   ASGITransport(app=app), and clears overrides on teardown.
5. Custom session-scoped event_loop fixture so pytest-asyncio works with
   session-scoped async fixtures.
6. Add backend/app/tests/integration/test_claims_pipeline.py with one
   test that POSTs /api/v1/verify/claim and asserts the response contains
   a verdict and an x-correlation-id header.

Constraints:
- pytest-asyncio mode=auto in pyproject.toml.
- Do not pull in real OpenAI keys; mock any external LLM with respx if
  the verify endpoint calls one.
- Tests must run on a fresh checkout with only `pytest` invoked.

Deliverables: conftest.py, the new test file, any pyproject.toml edits,
and a short README block at backend/app/tests/integration/README.md
explaining how to run only this layer.
```

*Source: BUILD_15_Observability_Testing.md → Section "Claude Prompts" → Prompt 2*

#### Prompt 3 — k6 load script for /api/v1/verify/claim

```
Generate infra/loadtest/claim_verify.js for the Enigmatrix backend.

Requirements:
1. Use k6's constant-arrival-rate executor at 100 RPS for 5 minutes,
   preAllocatedVUs=200, maxVUs=400.
2. Read BASE_URL and AUTH_TOKEN from __ENV.
3. Send POST /api/v1/verify/claim with a JSON body chosen randomly from
   a list of at least four sample claims (mix of true/false/ambiguous).
4. Set an X-Correlation-Id header of the form `k6-${__VU}-${__ITER}` so
   load test traffic is filterable in Grafana.
5. Define custom metrics verify_latency_ms (Trend) and verify_errors (Rate).
6. Thresholds: verify_latency_ms p(95)<800, verify_errors rate<0.01,
   http_req_failed rate<0.01.
7. Use check() to assert status === 200 and that the response body has a
   "verdict" field.
8. Add a setup() that hits /healthz once and aborts with fail() if
   non-200.

Also generate infra/loadtest/login.js as a 50-VU/1-minute warm-up
that issues POST /api/v1/auth/login and checks that access_token is in
the response.

Deliverables: the two .js files plus a short README.md at
infra/loadtest/README.md showing the exact `k6 run` invocations and the
required environment variables.
```

*Source: BUILD_15_Observability_Testing.md → Section "Claude Prompts" → Prompt 3*

---

### From BUILD_16 — Progress Tracker Templates

#### Prompt 1 — Generate this week's standup from the four module trackers

```
You are given four markdown files: M1_awareness.md, M2_*.md, M3_*.md, M4_*.md
from docs/progress/module/.

Produce a single weekly standup file conforming to the template in
BUILD_16 §3. Rules:

1. Group "Last week — done" by module. Pull bullets from each module
   tracker's "Current status" line plus any items that flipped from 🟡 to 🟢
   since the previous weekly file (diff against docs/progress/weekly/<prev>).
2. "This week — plan" — pull from each module's "Blockers" + open 🔲 items
   in the same file, one bullet per module.
3. "Blockers" — every 🔴 status across all four files, plus any "Blockers:"
   line whose value is not "none".
4. "Risks" — list any risk-register row whose status changed in the last 7
   days (compare last-reviewed column).
5. Output a single markdown file named docs/progress/weekly/<YYYY-Www>_standup.md.
   Do not invent data; if a field is empty in the source, write "TBD".
```

*Source: BUILD_16_Progress_Tracker_Template.md → Section "Claude Prompts (status generation)" → Prompt 1*

#### Prompt 2 — Generate the supervisor-review summary from BUILD/research file checkboxes

```
You are given all files under docs/BUILD_PLAN/ and docs/research/.

For each file:
1. Locate the "## Acceptance Criteria" H2 block (skip files that do not have one,
   e.g., BUILD_00, BUILD_16, BUILD_17).
2. Count checklist items by status using the legend chars 🔲 🟡 🟢 🔴 ⚪.
3. Emit one row in a markdown table with columns:
   file | done (🟢) | in-progress (🟡) | blocked (🔴) | not-started (🔲) | dropped (⚪) | % complete

Then produce a "Highlights" section listing:
- All 🔴 items verbatim with their file path and line number.
- Files where % complete dropped vs the previous run (compare against the
  most recent docs/progress/weekly/*_supervisor_summary.md).

Write output to docs/progress/weekly/<YYYY-Www>_supervisor_summary.md.
Do not modify any source file.
```

*Source: BUILD_16_Progress_Tracker_Template.md → Section "Claude Prompts (status generation)" → Prompt 2*

---

## 6. Reusable meta-prompts

These are not tied to any single BUILD file. Use them anywhere they fit.

### Meta — Refactor for clarity

```
Refactor the function/module at FILE_PATH for clarity WITHOUT changing observable behavior.
Constraints:
- Public signatures (function names, arg lists, return types) must remain identical.
- All existing tests must still pass — do not modify test files.
- No new dependencies. Prefer standard-library and already-imported modules.
- Break long functions (> 60 lines) into helpers; rename obscure variables;
  collapse duplicate branches; inline single-use trivial helpers.
- Add or tighten type hints (Python) or generics (TypeScript) where a refactor
  exposes a missing one.
Output:
- The refactored file as a single fenced block with `# FILE: <path>`.
- A short bullet list of the structural changes you made.
- A note flagging any pre-existing bug you noticed but deliberately did NOT fix.
```

### Meta — Add tests

```
Add tests for the public API of FILE_PATH.
Stack:
- Python files → pytest + pytest-asyncio (if async). Use the existing fixtures
  from backend/app/tests/conftest.py and integration/conftest.py.
- TypeScript files → Vitest + @testing-library/react when a component is involved.
Coverage:
- One happy-path test per public function/class/component.
- One failure-mode test per `raise`, `if not ...:`, or thrown error you can see.
- Boundary cases: empty input, None/null, max length, negative numbers, 0.
- Idempotency where the function claims to be idempotent.
- For DB-touching code, use a transactional fixture and assert side effects, not just return values.
Output the test file at the conventional path
(backend/app/tests/unit/test_<module>.py or src/__tests__/<Component>.test.tsx).
Do not modify the source under test.
```

### Meta — Write docstrings

```
Add docstrings to every public symbol in FILE_PATH.
Style:
- Python → Google-style docstrings with Args, Returns, Raises, and a one-line summary.
  Include a Usage example for any function whose call site is non-obvious.
- TypeScript → TSDoc with @param, @returns, @throws, and an @example for non-trivial APIs.
Rules:
- Do NOT change runtime behavior — only add docstrings/comments.
- Do NOT document private symbols (leading underscore in Python, non-exported in TS)
  unless they are tricky enough to warrant it.
- Pull domain context (model versions, API contracts, Sri Lankan regulatory terms) from
  surrounding BUILD-file context rather than guessing.
Output the file as a single fenced block with `# FILE: <path>`.
```

### Meta — Security review

```
Perform a focused security review of FILE_PATH against the OWASP Top 10
(2021 edition) plus the API Security Top 10 where the file is an HTTP handler.
For each finding, output:
- Severity (Critical / High / Medium / Low / Informational).
- Category (e.g., A03 Injection, A07 Identification & Authentication Failures).
- Location: line number(s) in FILE_PATH.
- Description: one paragraph in plain English of what is exploitable.
- Suggested fix: a concrete code diff or a one-paragraph remediation.
- Confidence: High / Medium / Low (how sure are you this is a real vulnerability,
  not a false positive given the surrounding code you cannot see).
Hard rules:
- Do NOT auto-apply fixes. Output is a review report only.
- Flag uses of: raw SQL string interpolation, eval/exec, pickle, shell=True,
  unbounded user-controlled paths, hardcoded secrets, weak hashes (MD5/SHA1
  for security purposes), missing CSRF protection on state-changing endpoints,
  missing auth dependencies on routes, JWT decoded without signature verification,
  CORS allow_origins=['*'] paired with credentials.
- If you find no issues, say so explicitly with "No findings."
Output as a markdown report, not a code block.
```

### Meta — API-contract sync

```
Given the Pydantic v2 schema(s) at backend/app/schemas/<RESOURCE>.py,
generate or update the matching TypeScript type(s) in frontend/lib/types.ts
(or frontend/lib/types/<resource>.ts if the file already exists).
Rules:
- Map Pydantic types to TS as: str → string, int/float → number, bool → boolean,
  datetime/date → string (ISO 8601 — leave as string, do not import a Date library),
  UUID → string, Optional[T] → T | null, list[T] → T[], dict[str, T] → Record<string, T>,
  Literal[...] → a union of string literals.
- Preserve field order from the Pydantic schema.
- Convert snake_case field names verbatim — do NOT camelCase. The API ships snake_case.
- For every Pydantic class, emit one exported TS type with the same name.
- If the schema imports from another schema file, recursively translate that file too.
- Add a top-of-file comment: `// AUTO-GENERATED from backend/app/schemas/<RESOURCE>.py — re-run after schema changes`.
Output the resulting TS file as a single fenced block with `// FILE: <path>`.
```

---

## 7. Prompt-engineering conventions used in this package

- **Exact file paths.** Every prompt names the precise file path(s) where output should land — `backend/app/services/auth_service.py`, `ml/m3/train_xgb.py`, `frontend/app/(admin)/layout.tsx`. Claude must not invent locations; the canonical tree is locked in `BUILD_02_Folder_Structure.md`.
- **BUILD-file citation.** Every prompt cites the BUILD file (and section) it draws context from — "per BUILD_03 §2", "matching BUILD_07 §8". The cited section is non-optional context that the human pasting the prompt must already have loaded into the chat.
- **Explicit assumptions.** Every prompt lists pre-conditions (Pydantic v2, SQLAlchemy 2.0 async, Python 3.11, pnpm, Tailwind, structlog correlation IDs already wired, MLflow tracking server up, etc.) inline rather than relying on Claude to guess.
- **UPPERCASE placeholders.** Where a prompt requires user-supplied tokens (run IDs, dates, repo slugs, paths to artifacts), it uses UPPERCASE_PLACEHOLDER or `<...>` form so they are visually obvious. The reader-substitution step is a hard requirement — these tokens must be replaced before the prompt is sent.
- **DB / migration assumptions.** Prompts that touch the database name the Alembic migration version they assume is current (e.g. "extends `audit_log` from BUILD_04", "after `0008_m2_tables`"). A prompt that introduces a new migration always states the predecessor.
- **Output-shape contract.** Every prompt specifies *how* output should be returned (one fenced block per file with `# FILE: <path>` headers, no prose outside code blocks, exit-code semantics for CLIs, etc.).
- **Side-effect transparency.** Where the prompt's generated code writes to external state (Postgres, MLflow registry, S3, ChromaDB, Slack), the prompt names every side effect explicitly so reviewers can audit before running.

---

## 8. Acceptance Criteria

- [ ] Every prompt in BUILD_01–16 appears verbatim under §5
- [ ] Counts in §2's table match the actual count in §5
- [ ] Every prompt has a back-reference italicized below it
- [ ] §6 contains 5 meta-prompts

---

**Prev:** BUILD_16_Progress_Tracker_Template.md  ·  **End of BUILD_PLAN package.**
