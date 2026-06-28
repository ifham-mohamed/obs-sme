# Research & Build Progress Tracker

Status legend: 🟢 Done · 🟡 In progress · 🔲 Not started · 🔴 Blocked · ⚪ Dropped / out of scope

Last updated: 2026-05-22 (Session 56 — M1 raw PDF bulk extraction + classification: 800 PDFs across 11 batches, full corpus coverage)

---

## Module 0 — Regulations / Awareness (M0)

### Infrastructure
| Item | Status | Notes |
|------|--------|-------|
| `m1_regulations` DB table | 🟢 | Migration `202605100001` |
| `m1_regulation_sectors` junction | 🟢 | Many-to-many with `sectors` |
| `survey_questions` (M0 rows) | 🟢 | Migrated from hardcoded TS bank; 12 questions seeded |
| Regulation seed data (5 regulations) | 🟢 | `seed_regulations.py` |
| Domain + Sector lookup seeds | 🟢 | `seed_lookups.py` |

### Backend API
| Item | Status | Notes |
|------|--------|-------|
| `GET /api/v1/m1/regulations` (public list) | 🟢 | Filtered by SME sector |
| `POST/PATCH/DELETE /api/v1/m1/regulations` (admin) | 🟢 | Soft-delete via `is_active` |
| `GET /api/v1/survey-flow/start` | 🟢 | Regulation-scoped or baseline |
| `POST /api/v1/survey-flow/answer` | 🟢 | Cross-module branching engine |
| Gazette PDF ingest pipeline | 🔲 | BUILD_07 §5; NLP classifier not yet wired |
| **Raw PDF corpus extraction + classification (Cowork data-population, Session 56)** | 🟢 | 800/800 PDFs in `C:\sme\03-Data-Sources\m1\raw\pdf\` extracted via `pdfplumber` (+ `pdftotext` fallback for files exceeding the bash 45s timeout) and classified by regex/heuristic statute matcher (`outputs/build_csv.py`). 7 batch CSVs (`m1_regulations_next50_batch{5..11}.csv`) + 2 tracker addenda (`m1_extraction_tracker_v11_addendum.csv` 203 rows + `m1_extraction_tracker_v12_addendum.csv` 145 rows) in `C:\sme\03-Data-Sources\m1\raw\csv\`. Classifier extensions made permanent in `outputs/build_csv.py`: Pradeshiya Sabha Act 15/1987, Sri Lanka Electricity (Amendment) Act 36/2024, Sri Lanka Export Development Act 40/1979, Companies Act 07/2007, doubled-Tamil Land Acquisition Act Ch 460 variants, Armed Services Long Service Medal typo/newline tolerance, `PREFIX_FALLBACK` extended for gazette prefixes 2483–2486. **Not production BUILD_07 — Cowork-mode seed data only.** See [plan](plans/2026-05-22_Plan%20M1%20raw%20PDF%20bulk%20extraction%20and%20classification%20—%20800%20PDFs%20across%2011%20batches.md) and [CHANGES.md](CHANGES.md) F-199. |
| **`m1_extraction_runs` table + API + frontend history (Session 54)** | 🟢 | `m1_extraction_runs` DB table (migration `202605210002`); `GET /api/v1/admin/m1/extraction/runs` paginated endpoint; frontend `listRuns()` + API-backed history table with localStorage write-through cache. SQLAlchemy pool fix (`pool_size=3`, `max_overflow=5`). See [plan](plans/2026-05-22_Plan%20M1%20extraction%20run%20history%20—%20server-side%20persistence%20and%20pool%20fix.md) and [CHANGES.md](CHANGES.md) F-189–F-192. |
| **M1 extraction page UX improvements (Session 54)** | 🟢 | Sticky inner sidebar fix (layout.tsx); `ResumeExtractionCard` for mid-pipeline recovery; full history table (`ExtractionHistoryTable`) with live Celery status polling; auto-scroll to progress panel on row click. See [plan](plans/2026-05-22_Plan%20M1%20extraction%20page%20UX%20improvements%20—%20sticky%20sidebar%20resume%20restart%20history%20auto-scroll.md) and [CHANGES.md](CHANGES.md) F-185–F-188. |
| **M1 pipeline admin UX audit (Session 53)** | 🟢 | 14 UX/UI findings documented across all 6 pipeline admin pages; Word report delivered. See [plan](plans/2026-05-22_Plan%20M1%20pipeline%20admin%20UX%20audit%20—%2014%20findings%20report.md) and [CHANGES.md](CHANGES.md) F-184. Critical blocker identified: `/admin/m1/pipeline/recent` returns HTTP 503 on every RSC data fetch. |

### Frontend
| Item | Status | Notes |
|------|--------|-------|
| `/regulations` — SME regulation list | 🟢 | |
| `/surveys` — unified hub (By Reg / By Module tabs) | 🟢 | |
| `/surveys/regulation/[id]` — unified wizard | 🟢 | Module accent CSS swap |
| `/surveys/awareness` — standalone M0 survey | 🟢 | DB-driven as of Session 12 |
| `/surveys/awareness/thank-you` | 🟢 | |
| Admin regulations CRUD | 🟢 | List, new, edit |
| Admin authoring wizard | 🟢 | 3-step flow builder |
| Admin flow canvas | 🟢 | CSS-grid visual builder |
| RAG context card in wizard | 🔲 | BUILD_07 §6; needs gazette ingest |

### Open follow-ups (M0)
- ~~`survey_responses.linked_regulation_id` not populated by `_build_row`~~ **RESOLVED** in Session 15 (F-129) — all rows now carry `linked_regulation_id`.
- ~~`/regulations` vs `/surveys` sidebar link overlap~~ **RESOLVED** in Session 15 (F-133) — sidebar now links to `/surveys` (unified hub).
- Session-based survey (`survey_sessions`) additive layer introduced in Session 16; `POST /survey-sessions/start` enforces limits from `survey_limits` singleton.

---

## Module 2 — Knowledge Assessment (M2)

### Infrastructure
| Item | Status | Notes |
|------|--------|-------|
| `survey_questions` (M2 rows) | 🟢 | ~40 questions seeded |
| `m2_knowledge_scores` cache table | 🟢 | Recomputed eagerly on each M2 submit |
| `survey_question_regulations` junction | 🟢 | M:N question↔regulation linkage |
| Authorship columns (`created_by`, `updated_by`) | 🟢 | Session 14 migration |

### Backend
| Item | Status | Notes |
|------|--------|-------|
| Auto-scoring engine (`m2_scoring.py`) | 🟢 | mcq_single, multi, numeric, ordered_steps (partial credit), open (keyword) |
| Score recompute + cache | 🟢 | `m2_service.recompute_knowledge_score()` |
| Bulk verify endpoint | 🟢 | `POST /admin/survey-questions/bulk-verify` |
| M2 linkage rules | 🟢 | `m2_linkage_rules.py` (legacy; superseded by `next_question_rules` JSONB) |
| Domain breakdown in score | 🟢 | `by_domain_json` in `m2_knowledge_scores` |

### Frontend
| Item | Status | Notes |
|------|--------|-------|
| `/surveys/knowledge` — standalone M2 survey | 🟢 | |
| `/surveys/knowledge/thank-you` (with score) | 🟢 | |
| Admin question bank (unified) `/admin/questions` | 🟢 | |
| Admin question new/edit (`/admin/questions/new`, `/[code]/edit`) | 🟢 | 5-card form |
| Admin M2 scores `/admin/m2/scores` | 🟢 | Paginated; link-mode |
| Question branching rules editor | 🟢 | `branching-rules-editor.tsx` |
| Duplicate / restore / archive actions | 🟢 | |
| Authorship footer on edit page | 🟢 | Session 14 |

### Open follow-ups (M2)
- Backend tests blocked by `CORS_ORIGINS` pydantic-settings env issue (Session 14)
- No `test_admin_survey_questions.py` yet (test coverage for question CRUD + bulk-verify)
- `scoring_rubric_json` for `open` format (keyword list) not surfaced in admin UI card

---

## Module 3 — Vulnerability / Risk (M3)

### Infrastructure
| Item | Status | Notes |
|------|--------|-------|
| `m3_compliance_history` table | 🟢 | Append-only snapshot |
| `m3_behavioural_signals` table | 🟢 | Append-only snapshot |
| `survey_questions` (M3 rows) | 🟢 | ~32 questions (4 sections) seeded |

### Backend
| Item | Status | Notes |
|------|--------|-------|
| M3 submit + snapshot projection | 🟢 | `_project_m3_snapshots()` in `survey_service` |
| `GET /api/v1/m3/sme/{id}/risk-signals` | 🟢 | Combined M2 + M3 view |
| Risk score ML model | 🔲 | BUILD_09 §4; needs training data |
| `GET /api/v1/risk` (composite score) | 🔴 | Returns 501; needs ML model |

### Frontend
| Item | Status | Notes |
|------|--------|-------|
| `/surveys/vulnerability` — standalone M3 | 🟢 | |
| `/surveys/vulnerability/thank-you` | 🟢 | |
| Admin M3 risk signals `/admin/m3/risk-signals` | 🟢 | Combined view |
| `/risk` — SME risk dashboard | 🔴 | Coming soon; needs ML score endpoint |

---

## Module 4 — Misinformation Detection

| Item | Status | Notes |
|------|--------|-------|
| Architecture research | 🟢 | `research/15_Module4_Misinformation_Architecture.md` |
| Data collection plan | 🟢 | `research/module_4_data_collection.md` |
| Backend route stub | 🟢 | `/api/v1/verify` returns 501 |
| Frontend `/verify` | 🟢 | "Coming soon" placeholder |
| NLP classifier | 🔲 | BUILD_10; needs training data |
| Sri Lankan sources list | 🟢 | `research/module_4_sri_lankan_sources.md` |

---

## ML Pipeline

| Item | Status | Notes |
|------|--------|-------|
| Architecture design | 🟢 | `research/02_Complete_ML_Lifecycle.md` |
| Data collection framework | 🟢 | `research/06_Data_Collection_and_Management.md` |
| Module 1 NLP (gazette classifier) | 🔲 | BUILD_11 §3; no training data yet |
| Module 2 scoring (rule-based) | 🟢 | `m2_scoring.py` — already in prod |
| Module 3 risk model | 🔲 | BUILD_11 §4; needs M2+M3 response data |
| Module 4 misinformation classifier | 🔲 | BUILD_11 §5; needs labelled data |
| Training pipeline (Airflow / cron) | 🔲 | BUILD_12 |
| MLflow experiment tracking | 🔲 | BUILD_11 §7 |

---

## Infrastructure & Deployment

| Item | Status | Notes |
|------|--------|-------|
| `docker-compose.dev.yml` (Postgres) | 🟢 | `make up` works |
| Alembic migrations | 🟢 | 11 versions through `202605180001_rename_awareness_module_number` |
| Rate limiting (slowapi) | 🟢 | Auth endpoints |
| Structured logging (structlog) | 🟢 | `logging_config.py` |
| Audit log | 🟢 | Session 14 — full coverage |
| Cloud deployment (GCP/AWS) | 🔲 | BUILD_14 |
| CI / CD (GitHub Actions) | 🔲 | BUILD_15 §2 |
| E2E tests (Playwright) | 🔲 | BUILD_15 §3 |
| Backend integration tests | 🟡 | Some passing; blocked by CORS env issue in conftest |

---

## Session Log (newest first)

| Session | Date | Key deliverables | F-IDs |
|---------|------|-----------------|-------|
| 54 | 2026-05-22 | Sticky sidebar fix; resume/restart extraction card; full history table (replaces pill strip); auto-scroll; `m1_extraction_runs` DB table + migration `202605210002`; trigger INSERT + status/cancel UPDATE + `GET /runs` endpoint; frontend API-backed history (localStorage write-through); QueuePool fix (`pool_size=3`, `max_overflow=5`) | F-185–F-192 |
| 53 | 2026-05-22 | M1 pipeline admin UX audit — 14 findings (1 Critical, 4 High, 6 Medium, 3 Low); Word report `M1_Pipeline_UX_Audit.docx` delivered | F-184 |
| 52 | 2026-05-22 | AnimatedList + FuzzyText component suite (scroll-triggered entrance, canvas fuzz/glitch, theme-aware); sticky table headers (13 tables); theme toggle: dropdown → circular-reveal toggle button (View Transitions API) | F-179–F-183 |
| 19 | 2026-05-12 | Rename `module_number` 0→1 for Awareness (migration, 7 backend files, 10 frontend files, 5 doc files) | F-140 |
| 18 | 2026-05-12 | Documentation sync — survey modes, session schema, session API, survey limits docs | F-139 |
| 17 | 2026-05-11 | Hotfix — survey_limits ProgrammingError resilience | F-138 |
| 16 | 2026-05-11 | Admin-manageable survey limits (`survey_limits` DB singleton, admin settings page) | F-134–F-137 |
| 15 | 2026-05-15 | Unified survey flow plumbing, VAT/SSCL scenario, data-driven M3 mapping | F-129–F-133 |
| 14 | 2026-05-14 | Audit service consolidation, authorship tracking, Activity Log UI | F-124–F-128 |
| 13 | 2026-05-13 | Animated loading skeleton, Pagination component, UI screen docs | F-119–F-123 |
| 12 | 2026-05-12 | Regulation-scoped flows, survey hub tabs, DB-driven awareness questions | F-110–F-118 |
| 11 | 2026-05-11 | Admin question bank (5-card form), branching rules editor, flow canvas | F-97–F-109 |
| 10 | 2026-05-10 | Unified survey spine, survey_questions table, cross-module branching | F-85–F-96 |
| 9 | 2026-05-09 | M3 vulnerability survey, m3_compliance_history + behavioural_signals | F-73–F-84 |
| 8 | 2026-05-08 | M2 knowledge survey, auto-scoring engine, m2_knowledge_scores | F-60–F-72 |
| 7 | 2026-05-07 | Admin regulations CRUD, domain/sector lookups, regulation list UI | F-47–F-59 |
| 6 | 2026-05-06 | Unified survey wizard, regulation-scoped flow API | F-34–F-46 |
| 5 | 2026-05-05 | Admin users CRUD, role enforcement, audit log (auth events) | F-27–F-33 |
| 1–4 | 2026-05-01–04 | Project scaffold, backend foundation, auth flow, awareness survey | F-01–F-26 |

---

## Known Blockers

| Blocker | Affected items | Fix needed |
|---------|---------------|-----------|
| `CORS_ORIGINS` env type