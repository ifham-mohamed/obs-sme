# Research Data Management System
## Database-Driven Data Collection & AI Training Architecture
## Enigmatrix | SME Regulatory Intelligence Platform | University of Moratuwa 2026

---

## Why Web-Based Data Collection Beats Spreadsheets

| Feature | Excel / Google Sheets | PostgreSQL + Next.js Web App |
|---|---|---|
| Duplicate detection | Manual | Automatic (DB constraints + hash check) |
| Data validation | Formula-based, error-prone | Server-side validation with Pydantic |
| Multi-user access | Conflicts, version issues | Concurrent access with transactions |
| Model integration | Manual export → CSV → script | Direct DB query for untrained records |
| Training status tracking | Not possible | `training_status` column per record |
| Audit trail | None | `created_at`, `updated_at`, `trained_at` |
| Scalability | Breaks at ~10,000 rows | Handles millions of records |

---

## PostgreSQL Database Schema

### Core Tables

```sql
CREATE TABLE research_modules (
    id SERIAL PRIMARY KEY,
    module_name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE sme_respondents (
    id SERIAL PRIMARY KEY,
    respondent_hash VARCHAR(64) UNIQUE,
    business_sector VARCHAR(50),
    employee_count INTEGER,
    province VARCHAR(50),
    years_operating INTEGER,
    language_preference VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE survey_responses (
    id SERIAL PRIMARY KEY,
    module_id INTEGER REFERENCES research_modules(id),
    respondent_id INTEGER REFERENCES sme_respondents(id),
    question_key VARCHAR(100),
    response_value TEXT,
    response_numeric FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    training_status VARCHAR(20) DEFAULT 'untrained',
    trained_at TIMESTAMP,
    model_version VARCHAR(20)
);

CREATE TABLE regulatory_changes (
    id SERIAL PRIMARY KEY,
    gazette_reference VARCHAR(50) UNIQUE,
    publication_date DATE,
    change_type VARCHAR(50),
    gazette_text TEXT,
    portal_publication_date DATE,
    first_news_date DATE,
    lag_gazette_to_portal INTEGER,
    lag_portal_to_news INTEGER,
    lag_news_to_awareness_avg FLOAT,
    source_url TEXT,
    training_status VARCHAR(20) DEFAULT 'untrained',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE social_media_claims (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(30),
    post_url TEXT,
    claim_text TEXT,
    original_language VARCHAR(20),
    translated_text TEXT,
    likes_count INTEGER,
    shares_count INTEGER,
    annotation_label VARCHAR(30),
    annotation_confidence FLOAT,
    annotator_count INTEGER,
    cohen_kappa FLOAT,
    training_status VARCHAR(20) DEFAULT 'untrained',
    content_hash VARCHAR(64) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE sme_risk_profiles (
    id SERIAL PRIMARY KEY,
    respondent_id INTEGER REFERENCES sme_respondents(id),
    compliance_violation_history JSONB,
    ird_defaulter_flag BOOLEAN DEFAULT FALSE,
    predicted_risk_score FLOAT,
    risk_category VARCHAR(20),
    shap_feature_importance JSONB,
    data_source VARCHAR(30),
    training_status VARCHAR(20) DEFAULT 'untrained',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE model_training_runs (
    id SERIAL PRIMARY KEY,
    module_id INTEGER REFERENCES research_modules(id),
    model_name VARCHAR(100),
    model_version VARCHAR(20),
    training_started_at TIMESTAMP,
    training_completed_at TIMESTAMP,
    records_used INTEGER,
    train_accuracy FLOAT,
    val_accuracy FLOAT,
    test_f1 FLOAT,
    hyperparameters JSONB,
    model_artifact_path TEXT
);
```

---

## Database-Driven Training Workflow

```
Step 1: Data Entry via Web App (Next.js)
        ↓
Step 2: Server-side validation (FastAPI + Pydantic)
        ↓
Step 3: Deduplication check (content_hash UNIQUE constraint)
        ↓
Step 4: Store in PostgreSQL with training_status = 'untrained'
        ↓
Step 5: Training script queries untrained records
        SELECT * FROM survey_responses WHERE training_status = 'untrained';
        ↓
Step 6: Model training on fetched batch
        ↓
Step 7: UPDATE training_status = 'trained' for trained record IDs
        ↓
Step 8: Log training run in model_training_runs table
```

---

## FastAPI Backend Structure

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

app = FastAPI(title='Enigmatrix Research API')

@app.post('/api/modules/{module_id}/responses')
async def submit_response(module_id: int, data: ResponseSchema, db: Session = Depends(get_db)):
    # Validate -> deduplicate -> store
    pass

@app.get('/api/training/untrained/{module_id}')
async def get_untrained_records(module_id: int, db: Session = Depends(get_db)):
    # Returns all untrained records for a module
    pass

@app.post('/api/training/mark-trained')
async def mark_trained(payload: TrainingBatchSchema, db: Session = Depends(get_db)):
    # Updates training_status for a batch of record IDs
    pass

@app.get('/api/analytics/module/{module_id}')
async def get_module_analytics(module_id: int, db: Session = Depends(get_db)):
    # Returns data collection progress, training coverage, duplicates caught
    pass
```

---

## Minimum Data Requirements per Module

| Module | Min Respondents | Min Records | Reason |
|---|---|---|---|
| M1 Survey | 100 SME owners | 100 awareness records | Statistical significance for lag analysis |
| M2 Knowledge Test | 80-120 | 80-120 knowledge scores | Enough for gap score calculation |
| M3 Vulnerability | 100+ | 100+ profiles + synthetic | Class imbalance needs oversampling |
| M4 Annotation | N/A | 500+ social media claims | Minimum corpus for classifier training |

---

## Deduplication Logic

```python
import hashlib

def generate_respondent_hash(email: str) -> str:
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()

def generate_content_hash(text: str) -> str:
    normalized = ' '.join(text.lower().strip().split())
    return hashlib.sha256(normalized.encode()).hexdigest()
```

---

## Next.js Frontend Route Structure

```
/app
  /dashboard              -> Analytics, training status overview
  /modules
    /awareness-gap        -> Module 1 data entry
    /knowledge-gap        -> Module 2 survey management
    /risk-prediction      -> Module 3 SME profile entry
    /misinformation       -> Module 4 annotation queue
  /data-management
    /export               -> Download trained/untrained data
    /training-status      -> View which records are trained
    /duplicates           -> Review flagged duplicates
  /sme-portal             -> SME-facing survey forms (public)
```

---
*Generated by Perplexity AI for Enigmatrix Research Group - University of Moratuwa 2026*
