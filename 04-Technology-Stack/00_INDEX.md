---
tags: [meta, index, stack]
source: synthesised
layer: meta
module: shared
---

# 04 — Technology Stack (Index)

> Engineering documentation organised by stack layer. Mirrors the 5-domain split from `enigmatrix-docs` (backend, frontend, infra, ml, shared). Each domain has SETUP (onboarding) and BUILD (engineering specs).

## Domains

### Backend — FastAPI · SQLAlchemy async · Alembic · PostgreSQL 16

- **Overview:** [backend/00_Backend_Overview](backend/00_Backend_Overview.md)
- **SETUP:**
  - [04_Backend_Development](backend/SETUP/04_Backend_Development.md)
  - [06_Database_and_Migrations](backend/SETUP/06_Database_and_Migrations.md)
  - [07_Auth_and_Roles](backend/SETUP/07_Auth_and_Roles.md)
  - [11_Survey_System](backend/SETUP/11_Survey_System.md)
- **BUILD:**
  - [BUILD_03_Backend_API](backend/BUILD/BUILD_03_Backend_API.md)
  - [BUILD_06_Auth_and_Users](backend/BUILD/BUILD_06_Auth_and_Users.md)
  - [BUILD_07_Module1_Awareness](backend/BUILD/BUILD_07_Module1_Awareness.md)
  - [BUILD_08_Module2_Knowledge](backend/BUILD/BUILD_08_Module2_Knowledge.md)
  - [BUILD_09_Module3_Risk](backend/BUILD/BUILD_09_Module3_Risk.md)
  - [BUILD_10_Module4_Misinformation](backend/BUILD/BUILD_10_Module4_Misinformation.md)
  - [BUILD_12_Data_Ingestion_and_Scheduling](backend/BUILD/BUILD_12_Data_Ingestion_and_Scheduling.md)

### Frontend — Next.js 14 (App Router) · Tailwind · next-intl (EN/SI/TA)

- **Overview:** [frontend/00_Frontend_Overview](frontend/00_Frontend_Overview.md)
- **User guide:** [frontend/APP_GUIDE](frontend/APP_GUIDE.md)
- **SETUP:** [05_Frontend_Development](frontend/SETUP/05_Frontend_Development.md) · [12_UI_Screens_and_Loading](frontend/SETUP/12_UI_Screens_and_Loading.md) · [13_Unified_Survey_Configuration](frontend/SETUP/13_Unified_Survey_Configuration.md)
- **BUILD:** [BUILD_05_Frontend_App](frontend/BUILD/BUILD_05_Frontend_App.md) · [BUILD_13_Admin_and_Annotation](frontend/BUILD/BUILD_13_Admin_and_Annotation.md)

### Infra — Docker Compose · PostgreSQL 16 · ChromaDB · Redis · nginx · GitHub Actions · Prometheus + Grafana

- **Overview:** [infra/00_Infra_Overview](infra/00_Infra_Overview.md)
- **SETUP:** [01_Prerequisites](infra/SETUP/01_Prerequisites.md) · [02_Quickstart](infra/SETUP/02_Quickstart.md) · [09_Troubleshooting](infra/SETUP/09_Troubleshooting.md)
- **BUILD:** [BUILD_01_Project_Initialization](infra/BUILD/BUILD_01_Project_Initialization.md) · [BUILD_02_Folder_Structure](infra/BUILD/BUILD_02_Folder_Structure.md) · [BUILD_04_Database_and_Storage](infra/BUILD/BUILD_04_Database_and_Storage.md) · [BUILD_14_Deployment_Cloud](infra/BUILD/BUILD_14_Deployment_Cloud.md) · [BUILD_15_Observability_Testing](infra/BUILD/BUILD_15_Observability_Testing.md)
- **Deployment (production):** [Railway-Deployment-Plan](infra/Railway-Deployment-Plan.md) (primary target) · [Render-Migration-Plan](infra/Render-Migration-Plan.md) (alternative reference)

### ML — PyTorch · HuggingFace · XLM-R + LoRA · XGBoost · MarianMT · MLflow · Optuna · ChromaDB

- **Overview:** [ml/00_ML_Overview](ml/00_ML_Overview.md)
- **BUILD:** [BUILD_11_ML_Training_Pipeline](ml/BUILD/BUILD_11_ML_Training_Pipeline.md)
- **Module-specific research:** see [Module 2](../02-Research-Modules/2%20Module-2-Knowledge-Hub/), [Module 3](../02-Research-Modules/3%20Module-3-Risk/), [Module 4](../02-Research-Modules/4%20Module-4-Misinformation/)

### Shared — cross-cutting architecture, testing, next-steps

- [03_Architecture](shared/03_Architecture.md) — 5-layer system architecture
- [08_Testing](shared/08_Testing.md) — test pyramid (unit · integration · E2E)
- [10_Next_Steps](shared/10_Next_Steps.md) — engineering roadmap

## Cross-references

- [SETUP_Master_Index](../00-Meta/SETUP_Master_Index.md) — original master onboarding index
- [BUILD_Master_Index](../00-Meta/BUILD_Master_Index.md) — original master build index
- [Timeline](../06-Timeline/00_Timeline_Overview.md) — when each BUILD ships
- [Findings-Log](../08-Findings-Log/00_Findings_Index.md) — what has actually been built
