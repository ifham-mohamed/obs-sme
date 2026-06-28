# BUILD 04 — Database & Storage Layer

> **Goal:** PostgreSQL is the single source of truth (per research file 06). ChromaDB holds vectors. Object storage holds PDFs and model artifacts. By the end of this file, all three are running, migrated, seeded, and accessible from the backend.

---

## 1. Three Stores, Three Responsibilities

| Store | Holds | Why this store |
|-------|-------|----------------|
| **PostgreSQL** | Regulations, users, profiles, survey responses, labeled examples, training runs, model versions, audit log | Relational integrity, transactions, joins, the *one* source of truth |
| **ChromaDB** | Vector embeddings of regulation chunks (Module 2/4 RAG) | Cosine search at meaningful scale; built-in persistence |
| **Object storage** | Raw PDF gazettes, scraped HTML, trained model artifacts (large `.bin`) | Cheap, scales, keeps Postgres slim |

> **Rule:** never duplicate authoritative data. Vectors and files are *derivatives*; if either is lost, regenerate from Postgres + the source URL.

---

## 2. Postgres — Local & Compose

### `docker-compose.dev.yml` (excerpt)

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: enigmatrix
      POSTGRES_PASSWORD: devpass
      POSTGRES_DB: enigmatrix
    ports: ["5432:5432"]
    volumes:
      - pg-data:/var/lib/postgresql/data
      - ./infra/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U enigmatrix"]
      interval: 5s
      timeout: 5s
      retries: 5

  chromadb:
    # Pin to the 0.5.x line; 0.6 changes the embedding-function API (breaking)
    image: chromadb/chroma:0.5.5
    environment:
      IS_PERSISTENT: "TRUE"
      PERSIST_DIRECTORY: /data
    ports: ["8001:8000"]
    volumes:
      - chroma-data:/data

volumes:
  pg-data:
  chroma-data:
```

### `infra/postgres/init.sql`

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- fast ILIKE search
CREATE EXTENSION IF NOT EXISTS unaccent;
```

---

## 3. SQLAlchemy Async Setup

```python
# FILE: backend/app/db/session.py
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.settings import get_settings

s = get_settings()
# DATABASE_URL must use the postgresql+asyncpg:// scheme for SQLAlchemy 2.0 async.
# Plain postgresql:// will silently fall back to the sync driver and break async sessions.
engine = create_async_engine(
    str(s.DATABASE_URL),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=(s.APP_ENV == "development"),
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
```

```python
# FILE: backend/app/db/base.py
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
        nullable=False
    )
```

---

## 4. Alembic — Migrations

### Initialize once

```bash
# RUN
cd backend
uv run alembic init alembic
```

### `backend/alembic/env.py` (key edits)

```python
import asyncio
from logging.config import fileConfig
from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool
from app.settings import get_settings
from app.db.base import Base
# Import all models so Alembic sees them
from app.models import (   # noqa: F401
    user, sme_profile, regulation, labeled_example,
    training_run, model_version, survey, alert, claim, audit_log,
)

config = context.config
config.set_main_option("sqlalchemy.url", str(get_settings().DATABASE_URL))
fileConfig(config.config_file_name)
target_metadata = Base.metadata

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata,
                      compare_type=True, compare_server_default=True)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section), prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

asyncio.run(run_async_migrations())
```

### Make a migration after each model change

```bash
# RUN
uv run alembic revision --autogenerate -m "add regulations table"
uv run alembic upgrade head
```

> **Tip:** every PR that touches `backend/app/models/` MUST include a corresponding `alembic/versions/` file.

---

## 5. Core Models — The Schema

> Source: research file `06_Data_Collection_and_Management.md` §4 plus extensions from file 09. Reproduced here in SQLAlchemy form.

```python
# FILE: backend/app/models/user.py
from uuid import UUID, uuid4
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    password_hash: Mapped[str]
    role: Mapped[str] = mapped_column(default="sme")           # 'sme' | 'admin' | 'annotator'
    preferred_language: Mapped[str] = mapped_column(default="en")
    is_active: Mapped[bool] = mapped_column(default=True)
    sme_profile = relationship("SMEProfile", uselist=False, back_populates="user")
```

```python
# FILE: backend/app/models/sme_profile.py
from uuid import UUID, uuid4
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

class SMEProfile(Base, TimestampMixin):
    __tablename__ = "sme_profiles"
    sme_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    sector: Mapped[str | None]
    sub_sector: Mapped[str | None]
    employee_count_band: Mapped[str | None]    # '1-10' | '11-50' | '51-200'
    annual_turnover_band: Mapped[str | None]
    business_age_years: Mapped[int | None]
    region: Mapped[str | None]
    primary_language: Mapped[str | None]
    consent_given: Mapped[bool] = mapped_column(default=True)
    consent_text_version: Mapped[str | None]
    user = relationship("User", back_populates="sme_profile")
```

```python
# FILE: backend/app/models/regulation.py
from datetime import date
from uuid import UUID, uuid4
from sqlalchemy import Date, Float, Index, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

class Regulation(Base, TimestampMixin):
    __tablename__ = "regulations"
    regulation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    gazette_number: Mapped[str]
    gazette_date: Mapped[date] = mapped_column(Date, index=True)
    source_url: Mapped[str]
    source_pdf_path: Mapped[str]
    raw_text: Mapped[str] = mapped_column(Text)
    cleaned_text: Mapped[str | None] = mapped_column(Text)
    detected_language: Mapped[str | None]                # en|si|ta|mixed
    title: Mapped[str | None]
    issuing_agency: Mapped[str | None]
    effective_date: Mapped[date | None]
    text_hash: Mapped[str] = mapped_column(unique=True)  # for dedup
    extraction_method: Mapped[str | None]
    extraction_confidence: Mapped[float | None] = mapped_column(Float)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Denormalized hot fields from latest classification
    predicted_category: Mapped[str | None] = mapped_column(index=True)
    classifier_confidence: Mapped[float | None]
    summary_en: Mapped[str | None] = mapped_column(Text)
    summary_si: Mapped[str | None] = mapped_column(Text)
    summary_ta: Mapped[str | None] = mapped_column(Text)

    classifications = relationship("RegulationClassification", back_populates="regulation",
                                   cascade="all, delete-orphan")
    secondary_appearances = relationship("RegulationSecondaryAppearance",
                                         back_populates="regulation",
                                         cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_regulations_agency", "issuing_agency"),
        Index("ix_regulations_text_trgm", "cleaned_text",
              postgresql_using="gin", postgresql_ops={"cleaned_text": "gin_trgm_ops"}),
    )

class RegulationClassification(Base, TimestampMixin):
    __tablename__ = "regulation_classifications"
    classification_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    regulation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True),
                                                 # FK in real migration
                                                 index=True)
    model_version: Mapped[str]
    predicted_category: Mapped[str]
    confidence: Mapped[float]
    all_probs_json: Mapped[dict | None] = mapped_column(JSONB)
    regulation = relationship("Regulation", back_populates="classifications",
                              foreign_keys=[regulation_id],
                              primaryjoin="RegulationClassification.regulation_id==Regulation.regulation_id")

class RegulationSecondaryAppearance(Base, TimestampMixin):
    __tablename__ = "regulation_secondary_appearances"
    appearance_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    regulation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    source_type: Mapped[str]   # 'ird_portal'|'epf_portal'|'news'|'twitter'|'fb_group'
    source_url: Mapped[str]
    first_seen_at: Mapped["datetime"]
    matching_method: Mapped[str | None]
    matching_confidence: Mapped[float | None]
    regulation = relationship("Regulation", back_populates="secondary_appearances",
                              foreign_keys=[regulation_id],
                              primaryjoin="RegulationSecondaryAppearance.regulation_id==Regulation.regulation_id")
```

```python
# FILE: backend/app/models/labeled_example.py
from uuid import UUID, uuid4
from sqlalchemy import Boolean, Float, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin

class LabeledExample(Base, TimestampMixin):
    __tablename__ = "labeled_examples"
    example_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    module_number: Mapped[int] = mapped_column(index=True)         # 1|2|3|4
    source_record_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    text: Mapped[str] = mapped_column(Text)
    label: Mapped[str]
    annotator: Mapped[str]
    is_gold: Mapped[bool] = mapped_column(Boolean, default=False)
    inter_annotator_agreement: Mapped[float | None] = mapped_column(Float)
    used_in_training: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    used_in_split: Mapped[str | None]                              # 'train'|'val'|'test'
    last_trained_run_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    text_hash: Mapped[str] = mapped_column(index=True)
```

```python
# FILE: backend/app/models/training_run.py
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Integer, Float, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin

class TrainingRun(Base, TimestampMixin):
    __tablename__ = "training_runs"
    run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    module_number: Mapped[int]
    base_model: Mapped[str]                              # 'xlm-roberta-base'
    hyperparameters_json: Mapped[dict] = mapped_column(JSONB)
    train_size: Mapped[int]
    val_size: Mapped[int]
    test_size: Mapped[int]
    val_macro_f1: Mapped[float | None] = mapped_column(Float)
    test_macro_f1: Mapped[float | None] = mapped_column(Float)
    artifact_path: Mapped[str | None] = mapped_column(Text)
    git_commit: Mapped[str | None]
    notes: Mapped[str | None] = mapped_column(Text)
```

```python
# FILE: backend/app/models/model_version.py
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Boolean, ForeignKey, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin

class ModelVersion(Base, TimestampMixin):
    __tablename__ = "model_versions"
    version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    module_number: Mapped[int]
    version_string: Mapped[str] = mapped_column(unique=True)   # 'mod1-classifier-v1.2.0'
    training_run_id: Mapped[UUID | None] = mapped_column(ForeignKey("training_runs.run_id"))
    is_production: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
```

```python
# FILE: backend/app/models/audit_log.py
from datetime import datetime
from uuid import UUID
from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class AuditLog(Base):
    __tablename__ = "audit_log"
    log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(index=True)
    table_name: Mapped[str | None]
    record_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    user_name: Mapped[str | None]
    event_data_json: Mapped[dict | None] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
```

> Add survey, alert, claim models per their respective module specs (`08_SME_Questionnaire_Design.md`, `12_Module1_End_to_End_Workflow.md`, `module_2_and_3_data_architecture.md`, `module_1_and_4_data_architecture.md`).

---

## 6. ChromaDB Client

```python
# FILE: backend/app/db/chroma.py
from functools import lru_cache
import chromadb
from app.settings import get_settings

@lru_cache
def chroma_client():
    s = get_settings()
    return chromadb.HttpClient(host=s.CHROMA_HOST, port=s.CHROMA_PORT)

def get_collection(name: str):
    return chroma_client().get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )

# Names — one collection per module that needs vectors
COLLECTION_REG_CHUNKS = "regulations_chunks_v1"   # Module 2 KB
COLLECTION_CLAIMS = "verified_claims_v1"          # Module 4 evidence
```

---

## 7. Object Storage Abstraction

```python
# FILE: backend/app/storage/__init__.py
from abc import ABC, abstractmethod
from pathlib import Path
from app.settings import get_settings

class Storage(ABC):
    @abstractmethod
    def put(self, key: str, data: bytes) -> str: ...
    @abstractmethod
    def get(self, key: str) -> bytes: ...
    @abstractmethod
    def url(self, key: str) -> str: ...

class LocalStorage(Storage):
    def __init__(self, root: str):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)
    def put(self, key, data):
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)
    def get(self, key):
        return (self.root / key).read_bytes()
    def url(self, key):
        return f"file://{(self.root / key).absolute()}"

# Add an S3Storage in app/storage/s3.py for production.

def get_storage() -> Storage:
    s = get_settings()
    if s.STORAGE_BACKEND == "local":
        return LocalStorage(s.STORAGE_LOCAL_PATH)
    raise NotImplementedError(s.STORAGE_BACKEND)
```

Use it like:

```python
storage = get_storage()
storage.put(f"gazettes/{gazette_number}.pdf", pdf_bytes)
```

---

## 8. Seeding Dev Data

```python
# FILE: backend/app/scripts/seed_dev.py
import asyncio
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import hash_password

async def main():
    async with SessionLocal() as db:
        admin = User(email="admin@enigmatrix.lk",
                     password_hash=hash_password("admin"),
                     role="admin")
        db.add(admin)
        await db.commit()
        print("Seeded admin@enigmatrix.lk / admin")

if __name__ == "__main__":
    asyncio.run(main())
```

```bash
# RUN
make migrate
make seed
```

---

## 9. Backups (Even In Dev)

```bash
# infra/deploy/backup_db.sh
#!/usr/bin/env bash
set -euo pipefail
TS=$(date -u +%Y%m%dT%H%M%SZ)
docker exec enigmatrix-postgres pg_dump -U enigmatrix enigmatrix \
  | gzip > "backups/enigmatrix_${TS}.sql.gz"
# keep last 14
ls -1t backups/ | tail -n +15 | xargs -I{} rm -f "backups/{}"
```

Cron once a day; mirror weekly snapshot off-VM (S3 or another VM) — see BUILD_14.

---

## 10. Acceptance Criteria

- [ ] `make up` brings up Postgres + ChromaDB cleanly
- [ ] `make migrate` succeeds on a fresh DB
- [ ] `make seed` creates the admin user
- [ ] All tables in research file 06 §4 + file 09 §7 are present (verify with `psql \dt`)
- [ ] `pg_trgm` and `uuid-ossp` extensions are loaded
- [ ] A `python -c "from app.db.chroma import get_collection; print(get_collection('test'))"` works
- [ ] `app/storage/` can `put` and `get` a 1 MB file with no errors
- [ ] One nightly backup file appears in `backups/`

---

## 11. Claude Prompts for This Section

### Prompt 1 — Generate ORM models

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

### Prompt 2 — First migration

```
Given the model files above, write the initial Alembic migration manually
(not via autogenerate). Name: 202604010001_initial_schema.py.
Include all tables, all foreign keys, all indexes from the models, and
`op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")` etc. at the top.
Provide both upgrade() and downgrade().
```

### Prompt 3 — Seed dev data

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

---

**Prev:** `BUILD_03_Backend_API.md` &nbsp;·&nbsp; **Next:** `BUILD_05_Frontend_App.md`
