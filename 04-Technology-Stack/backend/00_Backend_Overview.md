# Backend Domain

FastAPI · Python 3.11 · PostgreSQL 16 · SQLAlchemy 2.0 async · Alembic · structlog

## What's implemented (Session 20)

| Feature | Files |
|---------|-------|
| Session-based survey API — 6 endpoints (start/next-question/answer/complete/history) | `survey_sessions.py` |
| M1 admin CRUD — create/update/verify/archive/restore/duplicate/bulk-verify regulations | `m1_regulation_service.py` |
| M2 auto-scoring engine — 5 formats (mcq, scenario, numeric, ordered_steps, open) | `m2_scoring.py` |
| M2 linkage rules — 3 awareness→knowledge rules (VAT threshold/rate, official channel boost) | `m2_linkage_rules.py` |
| M3 dual-snapshot projection — fan-out to `m3_compliance_history` + `m3_behavioural_signals` | `m3_service.py` |
| Survey limits singleton — per-role caps (sme_limit, annotator_limit, admin_limit) | `survey_limits_service.py` |
| Admin translations queue — union of untranslated questions + regulations | `admin_translations.py` |
| Dashboard pending-regulations — sector-relevant active regulations not yet touched | `dashboard.py` |

## Stubs (not yet built)

| Feature | BUILD file |
|---------|------------|
| Gazette scraper, PDF extractor, XLM-R classifier, alert engine | BUILD_07 |
| ChromaDB RAG pipeline, `/api/v1/qa/ask` endpoint | BUILD_08 |
| XGBoost/LightGBM risk model, SHAP, MLflow | BUILD_09 |
| M4 misinformation classifier, social scrapers | BUILD_10 |

## Files

### SETUP/
| File | Description |
|------|-------------|
| [04_Backend_Development.md](SETUP/04_Backend_Development.md) | Day-to-day commands, directory map, 5-step endpoint pattern |
| [06_Database_and_Migrations.md](SETUP/06_Database_and_Migrations.md) | PostgreSQL schema, Alembic workflow, m2_knowledge_scores / m3_* tables |
| [07_Auth_and_Roles.md](SETUP/07_Auth_and_Roles.md) | Three roles, JWT + refresh-token flow, endpoint access matrix |
| [11_Survey_System.md](SETUP/11_Survey_System.md) | M1/M2/M3 storage spine, M2 scoring engine, M3 snapshot projection, M4 stub note |

### BUILD_PLAN/
| File | Description |
|------|-------------|
| [BUILD_03_Backend_API.md](BUILD_PLAN/BUILD_03_Backend_API.md) | FastAPI scaffold spec: main.py, settings, logging, health check, v1 router |
| [BUILD_06_Auth_and_Users.md](BUILD_PLAN/BUILD_06_Auth_and_Users.md) | JWT + bcrypt, role hierarchy, refresh-token rotation, RBAC middleware |
| [BUILD_07_Module1_Awareness.md](BUILD_PLAN/BUILD_07_Module1_Awareness.md) | M1 ingest pipeline spec: gazette scraper → XLM-R → alert engine (pending) |
| [BUILD_08_Module2_Knowledge.md](BUILD_PLAN/BUILD_08_Module2_Knowledge.md) | M2 survey instruments + RAG KB spec (scoring engine delivered; RAG pending) |
| [BUILD_09_Module3_Risk.md](BUILD_PLAN/BUILD_09_Module3_Risk.md) | M3 ML risk model spec: XGBoost, SHAP, MLflow (data capture delivered; model pending) |
| [BUILD_10_Module4_Misinformation.md](BUILD_PLAN/BUILD_10_Module4_Misinformation.md) | M4 classifier spec: social scrapers, 9-way veracity taxonomy (stub only) |
| [BUILD_12_Data_Ingestion_and_Scheduling.md](BUILD_PLAN/BUILD_12_Data_Ingestion_and_Scheduling.md) | Source registry, Scrapy + Playwright workers, APScheduler / Celery Beat |

### research/
| File | Description |
|------|-------------|
| [09_Module1_Architecture_Overview.md](research/09_Module1_Architecture_Overview.md) | M1 research question, pipeline overview, lag measurement methodology |
| [10_Module1_Gazette_PDF_Extraction_Pipeline.md](research/10_Module1_Gazette_PDF_Extraction_Pipeline.md) | 7-stage extraction: discover → download → extract → clean → segment → store → dedup |
| [12_Module1_End_to_End_Workflow.md](research/12_Module1_End_to_End_Workflow.md) | M1 runtime: background jobs, event-driven pipeline, dashboards |
| [module_1_and_4_data_architecture.md](research/module_1_and_4_data_architecture.md) | m1_regulations table, M4 raw posts table, junction tables, example data |
| [module_2_and_3_data_architecture.md](research/module_2_and_3_data_architecture.md) | M2 knowledge_scores schema, M3 compliance_history + behavioural_signals |
| [Module_1_Regulatory_Change_Awareness_Gap.md.pdf](research/Module_1_Regulatory_Change_Awareness_Gap.md.pdf) | M1 research paper (PDF) |
