# 07 — System Architecture

> Goal: define the complete system architecture for the SME Regulatory Intelligence Platform. Cover layers, components, contracts, deployment, and how the four modules plug into one platform.

---

## 1. Architectural Goals

The platform must satisfy:

1. **Multi-tenant** — each SME has its own profile and risk view.
2. **Multilingual** — UI and content in Sinhala, Tamil, English.
3. **Modular** — each research module is a separable service or sub-system.
4. **Scalable** — start at 100 concurrent users, scalable to 10k.
5. **Reproducible** — every model version is deployable and rollback-able.
6. **Auditable** — every prediction, alert, and survey response is logged.
7. **Affordable** — runs on a single VM during research, scales out only if needed.

---

## 2. The Five Layers

```
┌──────────────────────────────────────────────────────────────┐
│ Layer 5 — Presentation                                       │
│   Next.js (React, TypeScript, TailwindCSS) Web App + Mobile  │
└──────────────────────────────────────────────────────────────┘
                            │ HTTPS / JSON
┌──────────────────────────────────────────────────────────────┐
│ Layer 4 — API Gateway / Backend                              │
│   FastAPI (Python) + Pydantic + Auth + Rate Limiting         │
└──────────────────────────────────────────────────────────────┘
                            │ Function calls / message queue
┌──────────────────────────────────────────────────────────────┐
│ Layer 3 — Domain / Service Layer                             │
│   Module 1 service, Module 2 RAG, Module 3 risk,             │
│   Module 4 verifier, Notification service, Survey service    │
└──────────────────────────────────────────────────────────────┘
                            │
┌──────────────────────────────────────────────────────────────┐
│ Layer 2 — Data Layer                                         │
│   PostgreSQL (relational) + ChromaDB (vectors)               │
│   + Object Storage (PDFs, model artifacts)                   │
└──────────────────────────────────────────────────────────────┘
                            │
┌──────────────────────────────────────────────────────────────┐
│ Layer 1 — Ingestion / ETL                                    │
│   Scheduled scrapers (gazette, news, social),                │
│   PDF extractors, NLP classifiers, data validators           │
└──────────────────────────────────────────────────────────────┘
```

Each layer has a single responsibility. Crossing layers happens only via well-defined contracts.

---

## 3. Layer 5 — Presentation (Next.js)

### Pages
- `/` — landing page (public, multilingual)
- `/auth/login`, `/auth/register` — SME registration
- `/dashboard` — personalized risk score, recent regulations, alerts
- `/regulations` — searchable list of regulatory changes
- `/regulations/[id]` — detailed view with multilingual summary
- `/qa` — compliance Q&A chat (Module 2)
- `/verify` — claim verification UI (Module 4)
- `/profile` — SME profile and preferences
- `/admin/annotation` — internal annotation UI
- `/admin/training` — internal training run dashboard
- `/admin/datasets` — internal data management
- `/admin/models` — model version registry

### Component principles
- One language file per language (`en.json`, `si.json`, `ta.json`).
- Use `next-intl` for translations.
- Tailwind for styling — no separate CSS files.
- Server-side rendering for SEO-relevant public pages.
- Client-side rendering for interactive dashboards.

### State management
- For server data: **TanStack Query** (React Query) — handles caching, retries, refetching.
- For UI state: built-in React state. Avoid Redux for a project this size.

---

## 4. Layer 4 — Backend (FastAPI)

### Project structure
```
backend/
├── app/
│   ├── main.py                # FastAPI app entry
│   ├── config.py              # Pydantic settings
│   ├── deps.py                # Dependency injection
│   ├── routers/
│   │   ├── auth.py
│   │   ├── regulations.py     # Module 1 endpoints
│   │   ├── qa.py              # Module 2 endpoints
│   │   ├── risk.py            # Module 3 endpoints
│   │   ├── verify.py          # Module 4 endpoints
│   │   ├── surveys.py
│   │   ├── annotation.py
│   │   ├── datasets.py
│   │   ├── training.py
│   │   └── admin.py
│   ├── models/                # Pydantic models (request/response)
│   ├── db/
│   │   ├── session.py         # SQLAlchemy session
│   │   ├── models.py          # ORM tables
│   │   └── migrations/        # Alembic
│   ├── services/
│   │   ├── module1_service.py # Module 1 business logic
│   │   ├── module2_rag.py
│   │   ├── module3_risk.py
│   │   ├── module4_verifier.py
│   │   ├── notification.py
│   │   └── survey_service.py
│   └── ml/                    # Model loading and inference
│       ├── classifier.py
│       ├── rag_pipeline.py
│       ├── risk_model.py
│       └── verifier.py
├── tests/
├── pyproject.toml
└── Dockerfile
```

### Key endpoints (representative subset)

```
POST /auth/register
POST /auth/login

GET  /regulations?category=&from=&to=&q=
GET  /regulations/{id}
GET  /regulations/{id}/translations/{lang}

POST /qa/ask                 → returns cited answer
POST /verify/claim            → returns verdict + evidence

GET  /risk/me                 → returns risk score for logged-in SME
GET  /risk/me/explanations    → returns SHAP feature attributions

POST /surveys/{instrument}/submit
GET  /surveys/{instrument}/questions

# Admin
GET  /admin/annotation/queue?module=1
POST /admin/annotation/label
GET  /admin/datasets/module/{n}?status=untrained
POST /admin/datasets/module/{n}/mark-trained
GET  /admin/training/runs
POST /admin/models/promote/{version_id}
```

### Auth pattern
- JWT tokens for SMEs (passed in `Authorization: Bearer <token>` header).
- Separate admin role for annotation/training endpoints.
- Rate limiting via `slowapi` middleware.

---

## 5. Layer 3 — Service Layer

Each service encapsulates one module's logic and exposes a clean Python interface to the API layer.

```python
# app/services/module1_service.py
class Module1Service:
    def __init__(self, db: Session, classifier: RegulatoryClassifier):
        self.db = db
        self.classifier = classifier

    def classify_new_regulation(self, regulation_id: UUID) -> Classification:
        reg = self.db.get(Regulation, regulation_id)
        result = self.classifier.predict(reg.cleaned_text)
        cls = Classification(
            regulation_id=regulation_id,
            model_version=self.classifier.version,
            predicted_category=result.category,
            confidence=result.confidence,
            all_probs_json=result.all_probs
        )
        self.db.add(cls)
        self.db.commit()
        self.notify_subscribed_smes(reg, cls)
        return cls

    def notify_subscribed_smes(self, reg, cls):
        # Find SMEs whose sector matches the regulation
        ...
```

This separation lets you test services in isolation and swap implementations.

---

## 6. Layer 2 — Data Layer

### PostgreSQL
Single relational database for all structured data. Schema in file `06`.

### ChromaDB
Vector database for embeddings used by RAG (Modules 2, 4). Lives alongside PostgreSQL.

```python
# Stored vectors per module
chroma_client.create_collection(name="mod2_compliance_kb")    # verified regulations chunks
chroma_client.create_collection(name="mod4_factcheck_corpus") # FactCheck.lk + verified statements
```

### Object Storage
Local filesystem during development, optional S3-compatible (MinIO) for production.

```
storage/
├── raw/
│   ├── gazettes/
│   ├── news/
│   └── social/
├── processed/
│   └── datasets/
└── models/
    └── mod1/v1.2.0/
```

---

## 7. Layer 1 — Ingestion / ETL

This layer runs on a schedule and is **not user-facing**.

### Components
- **Gazette scraper** — runs daily at 6 AM. Pulls new gazettes from `documents.gov.lk`.
- **News scraper** — runs every 4 hours. Pulls coverage of regulatory topics.
- **Social media collectors** — Module 4 specific. Daily collection from public groups.
- **PDF extraction worker** — triggered when new PDFs land. Extracts text, classifies.
- **Translation worker** — generates Sinhala/Tamil summaries for newly classified regulations.

### Scheduling
Use one of:
- **APScheduler** — Python-native, simple, runs in-process.
- **Celery + Redis** — heavier, supports retry, monitoring.
- **System cron** — simplest, calls Python scripts.

For a research project, **APScheduler** is sufficient. Move to Celery only if scaling demands it.

### Pattern (APScheduler example)
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler(timezone="Asia/Colombo")
scheduler.add_job(scrape_gazettes, trigger="cron", hour=6, minute=0)
scheduler.add_job(scrape_news, trigger="interval", hours=4)
scheduler.add_job(retrain_check, trigger="cron", hour=2, minute=0, day_of_week="mon")
scheduler.start()
```

---

## 8. ML Serving Pattern

Models are loaded **once** at API startup, not per request:

```python
# app/ml/loader.py
from functools import lru_cache
from transformers import AutoTokenizer, AutoModelForSequenceClassification

@lru_cache(maxsize=1)
def load_classifier(version="latest"):
    base_path = f"./storage/models/mod1/{version}"
    return {
        "tokenizer": AutoTokenizer.from_pretrained(base_path),
        "model": AutoModelForSequenceClassification.from_pretrained(base_path),
        "version": version,
    }

# app/main.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.classifier = load_classifier("latest")
    app.state.rag = load_rag_pipeline()
    app.state.risk_model = load_risk_model()
    yield

app = FastAPI(lifespan=lifespan)
```

Model lookup at request time:
```python
@router.post("/classify")
def classify(req: ClassifyRequest, request: Request):
    classifier = request.app.state.classifier
    inputs = classifier["tokenizer"](req.text, return_tensors="pt", truncation=True)
    with torch.no_grad():
        logits = classifier["model"](**inputs).logits
    ...
```

---

## 9. Inter-Module Data Flow (How They Connect)

```
┌────────────────────────────────────────────────────────────┐
│ MODULE 1 — Awareness                                        │
│ Gazette scraper → PDF extractor → Classifier → DB           │
│                                                ↓            │
│                                  Notification service       │
└────────────────────────────────────────────────────────────┘
                                                ↓
                                  ┌─────────────────────────┐
                                  │ MODULE 2 — Knowledge     │
                                  │ DB-stored regulations →  │
                                  │ Chunked → Embedded →     │
                                  │ Stored in ChromaDB       │
                                  │ Retrieved by RAG on Q&A  │
                                  └─────────────────────────┘
                                                ↓
┌──────────────────────────────────┐    ┌─────────────────────────┐
│ MODULE 3 — Risk                   │    │ MODULE 4 — Misinformation │
│ Pulls SME profile + history       │    │ Pulls verified facts from │
│ + recently affected regulations   │    │ Module 2 KB to verify     │
│ from Module 1 → updates risk      │    │ claims                    │
└──────────────────────────────────┘    └─────────────────────────┘
```

Module 1 is the **upstream** — every other module consumes its output.

---

## 10. Deployment Topology

### Development (your laptops)
- Run everything locally.
- PostgreSQL via Docker Compose.
- ChromaDB via Docker.
- Object storage = local `./storage/` directory.
- FastAPI + Next.js as separate processes.

### Single-VM deployment (recommended for thesis demo)
```
                     ┌─────────────┐
       Internet ───>│   nginx      │ (reverse proxy + TLS)
                    └──────┬──────┘
                           │
       ┌───────────────────┴───────────────┐
       ▼                                   ▼
┌──────────────┐                  ┌────────────────┐
│ Next.js      │                  │ FastAPI        │
│ port 3000    │                  │ port 8000      │
└──────────────┘                  └────────┬───────┘
                                           │
                              ┌────────────┴────────────┐
                              ▼                         ▼
                        ┌──────────┐             ┌──────────────┐
                        │ Postgres │             │ ChromaDB     │
                        │ port 5432│             │ port 8001    │
                        └──────────┘             └──────────────┘
```

A 4-vCPU 16-GB-RAM VM (e.g. DigitalOcean droplet, AWS t3.xlarge) is sufficient for the demo and pilot.

### Containers
- One Dockerfile per service (`Dockerfile.backend`, `Dockerfile.frontend`).
- Single `docker-compose.yml` orchestrates all of them.
- For production, optionally migrate to Kubernetes (Kompose can convert).

---

## 11. CI/CD

Minimum viable pipeline:

```yaml
# .github/workflows/ci.yml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests/
      - uses: actions/setup-node@v4
      - run: cd frontend && npm install && npm run build
```

For deployment, simplest = SSH + git pull + restart (perfectly acceptable for a research demo).

---

## 12. Observability

| Concern | Tool |
|---------|------|
| Application logs | Python `logging` → file + stdout |
| Request logs | FastAPI middleware or nginx logs |
| Model prediction logs | Application-level table in PostgreSQL |
| Metrics | Prometheus + Grafana (optional, recommended) |
| Errors | Sentry (free tier) |
| Database queries | `pg_stat_statements` extension |

For a research project, **structured logging to file + nightly summary** is sufficient. Add Sentry if you have time.

---

## 13. Security Essentials

- HTTPS only (Let's Encrypt via certbot).
- Bcrypt for passwords (built into `passlib`).
- JWT with short expiry (15 min) + refresh tokens (7 days).
- No personally identifying SME information in logs.
- Database backups encrypted at rest.
- API rate limiting per IP.
- `.env` file for secrets (never commit).

---

## 14. Cost Estimate (for your scope)

| Item | Cost |
|------|------|
| Hosting (single VM) | ~$25/month |
| Domain | ~$15/year |
| Object storage (~50 GB) | included with VM |
| Database backups | included |
| Google Translate API | ~$20 for project lifetime |
| OpenAI / Anthropic API for baseline LLMs | ~$30 for project lifetime |
| **Total project budget** | **< $100** |

Free alternatives exist for everything (Hugging Face Inference API free tier, Colab for training). The above is the convenience cost.

---

## 15. Architectural Decisions to Defend in Viva

| Decision | Defense |
|----------|---------|
| Why monolith over microservices? | Project scale does not justify operational complexity of microservices. Monolith is faster to build and deploy. |
| Why PostgreSQL + ChromaDB instead of one DB? | Vector search at meaningful scale needs a specialized engine. pgvector is an option but ChromaDB has better built-in tooling for embedding pipelines. |
| Why FastAPI over Django? | Async support, built-in OpenAPI docs, type-safety via Pydantic, minimal boilerplate for an API-only backend. |
| Why Next.js over plain React? | SSR, built-in routing, SEO, production defaults — faster development, no need to assemble a build pipeline. |
| Why local model serving instead of cloud LLM? | Cost (zero per-call), privacy (no data leaves your VM), reproducibility (fixed model version). |
| Why APScheduler over Celery? | Project scale has at most a few scheduled jobs; Celery would be over-engineering. |
| Why single VM instead of Kubernetes? | One developer-team, single deployment, demo scale. K8s introduces complexity that delays research. |

---

## Summary

The architecture is a five-layer monolith: Next.js frontend, FastAPI backend, service layer with one service per module, PostgreSQL + ChromaDB + object storage data layer, and scheduled ETL ingestion. All four modules share infrastructure but are independently developable. Deploy on a single 4-vCPU/16-GB VM behind nginx with HTTPS. The architecture is small enough to fully understand in one sitting, large enough to handle every research and demo requirement, and explicitly justified at every choice.
