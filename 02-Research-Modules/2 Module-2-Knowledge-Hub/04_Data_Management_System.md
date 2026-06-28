# 06 — Data Collection & Management

> Goal: replace ad-hoc spreadsheet collection with a proper research-data management pipeline. Cover survey design, public-record collection, database-driven training (your idea), trained-status tracking, and duplicate handling.
>
> **April 2026 thresholds — read first.** Any survey-instrument or schema example that mentions VAT/SSCL thresholds or VAT rates must use the **post-April-2026 budget figures** (VAT registration threshold **LKR 36M**, SSCL threshold **LKR 36M**, standard VAT rate **18%**). The canonical question bank is `docs/research/module_2_and_3_data_architecture.md`. If you extend the SME schema or add survey items in this file, mirror those values exactly — pre-April-2026 figures (60M / 15%) are out of date and will get flagged in viva. See `docs/BUILD_PLAN/BUILD_00_INDEX.md` → "April 2026 Budget — Threshold Truth".

---

## 1. The Three Sources of Data

Across all four modules, every piece of data comes from one of three sources:

| Source                           | Examples in Enigmatrix                                                     | Volume                 | Quality                                 |
| -------------------------------- | -------------------------------------------------------------------------- | ---------------------- | --------------------------------------- |
| **Public records**               | Gazettes, court records, IRD defaulter lists, news, social media           | Large (10k+ items)     | Raw, needs cleaning                     |
| **Surveys / primary collection** | SME owner surveys, compliance knowledge tests, vulnerability questionnaire | Small (100–500)        | Carefully designed = high signal        |
| **Synthetic generation**         | Calibrated SME profiles for Module 3                                       | Configurable (1k–100k) | Use to augment, never replace real data |

---

## 2. Why Spreadsheets Fail Past a Certain Point

You correctly identified that Excel / Google Sheets / Google Forms have limits. They fail at:

| Spreadsheet limitation | Real consequence |
|------------------------|-------------------|
| No referential integrity | Survey response refers to a regulation that no longer exists in another sheet |
| No real-time concurrency | Two annotators overwrite each other's labels |
| No deduplication primitives | Same SME submits the survey twice; you do not notice |
| No status tracking | Cannot distinguish "trained on" vs "not yet trained on" rows |
| No versioning | Cannot reconstruct the dataset as it was on 2026-04-15 |
| No audit log | Cannot prove your dataset was not edited after results were computed |
| No structured types | A "deadline" column has dates, text, and numbers mixed |
| Slow for >50k rows | Module 4 social media data will hit this fast |

A web app + PostgreSQL fixes every one of these.

---

## 3. The Recommended Database-Driven Architecture

Your proposed architecture is correct. Here is the refined version:

```
┌──────────────────────────┐         ┌─────────────────────────┐
│   Frontend (Next.js)     │ ──────> │  Backend API (FastAPI)  │
│ - Annotator UI           │         │ - Auth                  │
│ - Survey forms           │         │ - Validation (Pydantic) │
│ - Status dashboards      │         │ - Business logic        │
│ - Data export UI         │         │ - Background jobs       │
└──────────────────────────┘         └────────────┬────────────┘
                                                  │
                                                  ▼
                       ┌──────────────────────────────────────────┐
                       │       PostgreSQL (single source of truth)│
                       │  - regulations                           │
                       │  - regulation_classifications            │
                       │  - sme_profiles                          │
                       │  - survey_responses                      │
                       │  - labeled_examples                      │
                       │  - training_runs                         │
                       │  - model_versions                        │
                       │  - audit_log                             │
                       └────────────┬──────────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
   ┌──────────────────┐   ┌──────────────────┐  ┌──────────────────┐
   │ Scrapers / ETL   │   │  ML Training     │  │  Inference API   │
   │ - gazette        │   │  - reads "is_    │  │  - serves model  │
   │ - news           │   │    untrained"    │  │  - logs          │
   │ - social media   │   │  - writes        │  │    predictions   │
   │ (run on schedule)│   │    "is_trained"  │  │                  │
   └──────────────────┘   └──────────────────┘  └──────────────────┘
```

The key insight is that **PostgreSQL is the single source of truth**. Scrapers write to it, annotators write to it, training reads from and writes to it, the inference API logs to it.

---

## 4. Database Schema — Core Tables

This schema covers all four modules. Adapt as needed.

### regulations (Module 1 primary table)
```sql
CREATE TABLE regulations (
    regulation_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gazette_number       TEXT NOT NULL,
    gazette_date         DATE NOT NULL,
    source_url           TEXT NOT NULL,
    source_pdf_path      TEXT NOT NULL,
    raw_text             TEXT NOT NULL,
    cleaned_text         TEXT,
    detected_language    TEXT CHECK (detected_language IN ('en','si','ta','mixed')),
    title                TEXT,
    issuing_agency       TEXT,
    effective_date       DATE,
    text_hash            TEXT UNIQUE NOT NULL,        -- for dedup
    extraction_method    TEXT,                         -- pymupdf | pdfplumber | ocr
    extraction_confidence REAL,
    is_processed         BOOLEAN DEFAULT FALSE,
    created_at           TIMESTAMPTZ DEFAULT NOW(),
    updated_at           TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_regulations_gazette_date ON regulations(gazette_date);
CREATE INDEX idx_regulations_agency ON regulations(issuing_agency);
```

### regulation_classifications
```sql
CREATE TABLE regulation_classifications (
    classification_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    regulation_id        UUID NOT NULL REFERENCES regulations(regulation_id) ON DELETE CASCADE,
    model_version        TEXT NOT NULL,
    predicted_category   TEXT NOT NULL,
    confidence           REAL NOT NULL,
    all_probs_json       JSONB,
    classified_at        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (regulation_id, model_version)
);
```

### labeled_examples (THE KEY TABLE for training)
```sql
CREATE TABLE labeled_examples (
    example_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_number        INT NOT NULL,                 -- 1, 2, 3, or 4
    source_record_id     UUID,                         -- e.g. regulation_id
    text                 TEXT NOT NULL,
    label                TEXT NOT NULL,
    annotator            TEXT NOT NULL,
    annotated_at         TIMESTAMPTZ DEFAULT NOW(),
    is_gold              BOOLEAN DEFAULT FALSE,        -- gold = expert verified
    inter_annotator_agreement REAL,
    -- THE TRAINED-STATUS FLAG (your idea)
    used_in_training     BOOLEAN DEFAULT FALSE,
    used_in_split        TEXT,                         -- 'train' | 'val' | 'test' | NULL
    last_trained_run_id  UUID,                         -- references training_runs.run_id
    text_hash            TEXT NOT NULL                 -- for dedup
);
CREATE INDEX idx_labeled_module_untrained
    ON labeled_examples(module_number, used_in_training)
    WHERE used_in_training = FALSE;
```

### training_runs
```sql
CREATE TABLE training_runs (
    run_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_number        INT NOT NULL,
    run_started_at       TIMESTAMPTZ DEFAULT NOW(),
    run_completed_at     TIMESTAMPTZ,
    base_model           TEXT,                         -- e.g. 'xlm-roberta-base'
    hyperparameters_json JSONB,
    train_size           INT,
    val_size             INT,
    test_size            INT,
    val_macro_f1         REAL,
    test_macro_f1        REAL,
    artifact_path        TEXT,                         -- where weights are saved
    git_commit           TEXT,
    notes                TEXT
);
```

### model_versions
```sql
CREATE TABLE model_versions (
    version_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_number        INT NOT NULL,
    version_string       TEXT UNIQUE NOT NULL,         -- e.g. 'mod1-classifier-v1.2.0'
    training_run_id      UUID REFERENCES training_runs(run_id),
    is_production        BOOLEAN DEFAULT FALSE,
    deployed_at          TIMESTAMPTZ,
    notes                TEXT
);
```

### sme_profiles (Modules 1, 2, 3 surveys)
```sql
CREATE TABLE sme_profiles (
    sme_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sector               TEXT,
    sub_sector           TEXT,
    employee_count_band  TEXT,                         -- '1-10' | '11-50' | '51-200'
    annual_turnover_band TEXT,
    business_age_years   INT,
    region               TEXT,
    primary_language     TEXT,
    consent_given        BOOLEAN DEFAULT TRUE,
    consent_text_version TEXT,
    submitted_at         TIMESTAMPTZ DEFAULT NOW()
);
```

### survey_responses
```sql
CREATE TABLE survey_responses (
    response_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id           UUID NOT NULL REFERENCES survey_sessions(session_id) ON DELETE CASCADE,
    sme_id               UUID NOT NULL REFERENCES sme_profiles(sme_id),
    regulation_id        UUID,
    module_number        SMALLINT NOT NULL CHECK (module_number IN (1, 2, 3, 4)),
    survey_mode          TEXT NOT NULL CHECK (survey_mode IN (
                             'module_1', 'module_2', 'module_3', 'module_4', 'unified'
                         )),
    question_id          TEXT NOT NULL,
    answer_text          TEXT,
    answer_numeric       NUMERIC,
    answer_date          DATE,
    answer_options       JSONB,
    is_correct           BOOLEAN,
    submitted_at         TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (session_id, question_id)
);
```

### survey_sessions
```sql
CREATE TABLE survey_sessions (
    session_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sme_id               UUID NOT NULL REFERENCES sme_profiles(sme_id),
    survey_mode          TEXT NOT NULL CHECK (survey_mode IN (
                             'module_1', 'module_2', 'module_3', 'module_4', 'unified'
                         )),
    status               TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN (
                             'in_progress', 'completed', 'abandoned'
                         )),
    question_cap         INT NOT NULL,
    questions_answered   INT NOT NULL DEFAULT 0,
    started_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at         TIMESTAMPTZ
);
```

### survey_question_bank
```sql
CREATE TABLE survey_question_bank (
    question_id          TEXT PRIMARY KEY,
    regulation_id        UUID NOT NULL,
    module_number        SMALLINT NOT NULL CHECK (module_number IN (1, 2, 3, 4)),
    question_order       INT NOT NULL,
    version              TEXT NOT NULL DEFAULT 'v1',
    question_type        TEXT NOT NULL,
    trigger_condition    JSONB,
    answer_options       JSONB,
    correct_answer_json  JSONB,
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### survey_question_text
```sql
CREATE TABLE survey_question_text (
    question_id          TEXT NOT NULL REFERENCES survey_question_bank(question_id) ON DELETE CASCADE,
    lang_code            TEXT NOT NULL CHECK (lang_code IN ('en', 'si', 'ta')),
    question_text        TEXT NOT NULL,
    helper_text          TEXT,
    PRIMARY KEY (question_id, lang_code)
);
```

### regulation_sector_map
```sql
CREATE TABLE regulation_sector_map (
    regulation_id        UUID NOT NULL,
    sector_code          TEXT NOT NULL,
    impact_level         TEXT NOT NULL DEFAULT 'primary',
    PRIMARY KEY (regulation_id, sector_code)
);
```

> Terminology note
>
> In the current implementation, `m1_regulation_sectors` corresponds to `regulation_sector_map`, and `survey_questions` corresponds to `survey_question_bank`. This document uses the target-state names.

### audit_log (catches everything)
```sql
CREATE TABLE audit_log (
    log_id               BIGSERIAL PRIMARY KEY,
    event_type           TEXT NOT NULL,
    table_name           TEXT,
    record_id            UUID,
    user_name            TEXT,
    event_data_json      JSONB,
    occurred_at          TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 5. The "Trained vs Untrained" Workflow (your idea, formalized)

This is exactly what you proposed. Here is the implementation:

### Step 1 — Annotators add labels
- Frontend form writes to `labeled_examples` with `used_in_training = FALSE`.
- Each example gets a `text_hash` to enable duplicate detection.

### Step 2 — Duplicate prevention
- Before insert, the API checks: `SELECT 1 FROM labeled_examples WHERE text_hash = $1 AND module_number = $2`.
- If a row exists, reject the insert with a friendly error.

### Step 3 — Training script reads only untrained
```sql
SELECT example_id, text, label
FROM labeled_examples
WHERE module_number = 1
  AND used_in_training = FALSE
ORDER BY annotated_at;
```

### Step 4 — After training completes, mark as trained
```sql
UPDATE labeled_examples
SET used_in_training = TRUE,
    used_in_split = $split,                   -- 'train' | 'val' | 'test'
    last_trained_run_id = $run_id
WHERE example_id = ANY($example_ids);
```

### Step 5 — New annotations trigger retraining cycle
- Background job checks daily: `SELECT COUNT(*) FROM labeled_examples WHERE module_number = 1 AND used_in_training = FALSE`.
- If count exceeds threshold (e.g. 200 new examples), email the team — time for a retraining run.

### Step 6 — Retraining preserves split assignment
- Examples that were already in the test set must STAY in the test set (otherwise you contaminate evaluation across versions).
- New examples are added to train (default), unless flagged for test inclusion.

### Step 7 — Versioned export
- Each training run snapshots the dataset to a Parquet file in object storage (or a versioned table).
- This guarantees reproducibility — you can always reconstruct the exact dataset that produced model `mod1-classifier-v1.2.0`.

---

## 6. Survey Design Principles

For the surveys (Modules 1, 2, 3), follow these rules:

### Question count
- Per-module surveys should stay within **8–10 questions**.
- Unified surveys should stay within **15–20 questions total**.
- The cap exists to reduce abandonment while still collecting one block per applicable regulation.

### Question types
| Type | When to use | Example |
|------|-------------|---------|
| Single-choice | Most common — fast for respondent | "How did you first learn about VAT changes?" |
| Multi-select | When more than one answer is valid | "Which of these channels do you use weekly?" |
| Likert (5-point) | Attitudes and frequencies | "How confident are you in your VAT calculations?" |
| Date | Temporal recall | "When did you first hear about [specific 2025 change]?" |
| Numeric | Counts and amounts | "How many penalty notices in last 24 months?" |
| Short text | Free-form follow-up | "Briefly describe how you found out" |

### Multilingual delivery
- Primary form in **Sinhala** (largest SME owner population).
- Fully translated **Tamil** version.
- **English** version for finance-staff respondents.
- Use parallel question IDs across languages so analysis is unified.

### Pilot first
- Run with 5–10 SME owners before full deployment.
- Watch them fill it out. Note where they pause, ask questions, abandon.
- Revise. Then deploy.

---

## 7. Survey Distribution Channels

| Channel | Strength | Caveat |
|---------|----------|--------|
| Chamber of Commerce mailing lists | High legitimacy, biased sample (more formal SMEs) | Need to acknowledge in limitations |
| NEDA partnership | Excellent legitimacy and reach | Requires formal request |
| LinkedIn targeted posts | Cheap, broad | Skews toward digitally-native respondents |
| WhatsApp business groups | High response rate | Difficult to verify identity |
| Direct industrial-zone visits | High quality, qualitative depth | Time-intensive |
| Snowball sampling | Useful for hard-to-reach segments | Bias toward connected respondents |

**Best practice:** Use 3–4 channels, record source per response, report response rate per channel, analyze whether responses differ by channel.

---

## 8. Consent and Ethics

Every survey must include:

```
You are invited to participate in research conducted by [Group Enigmatrix],
Faculty of Information Technology, University of Moratuwa.

Purpose: To understand the information barriers that affect SME regulatory
compliance in Sri Lanka.

Your participation is voluntary. You may stop at any time. We will NOT collect:
- Your business name (only sector/size category)
- Your tax registration number
- Any financially identifying information

Data will be stored in encrypted form, used only for academic research, and
published only in aggregate form. You may request deletion of your responses
within 30 days by contacting [email].

By proceeding, you confirm that you have read this notice and consent to participate.
[ I CONSENT ]    [ I DO NOT CONSENT ]
```

Get **ethics committee approval** from FIT/UoM before deploying. Most universities require this for human-subject research, even surveys. Check with your supervisor and document the approval reference in your thesis.

---

## 9. Public-Record Scraping — Ethical and Legal Rules

| Source | Rule |
|--------|------|
| `documents.gov.lk` | Public domain. Scrape. Rate-limit (1 req / 2 sec) to be polite. |
| News archives | Check `robots.txt`. Honor it. Use one-second delay. |
| IRD defaulter lists | Public publication. Scrape and store. |
| Court records (lawnet.gov.lk) | Public. Same rules. |
| FactCheck.lk | Public. Same. |
| Facebook public groups | **Tighter rules.** Only public posts. Use Graph API where possible. Anonymize user IDs. |
| Twitter / X | Use the official API. Honor terms. |
| Reddit | Public, API-friendly. |
| WhatsApp | **Do NOT scrape.** Only voluntary forwarded-message submissions via your survey. |

**Always include in your thesis:** A "Data sources and access" subsection that lists every source, the access method, the rate-limit used, the date range collected, and a confirmation that all data was publicly accessible at time of collection.

---

## 10. Storage Layout

Combine database + object storage:

```
PostgreSQL (structured records, relationships, status, tiny text)
  └─ regulations table (no raw PDFs — only paths and extracted text)

Object Storage (S3 / MinIO / local disk)
  /raw/
    /gazettes/yyyy/mm/dd/<gazette-number>.pdf
    /news/<source>/<date>/<id>.html
    /social/<platform>/<date>/<id>.json
  /interim/
    /gazettes/<gazette-number>/extracted_text.txt
  /processed/
    /datasets/<module>/<version>/dataset.parquet
  /models/
    /mod1/<version>/  (HF model artifacts)
```

**Rule:** PostgreSQL stores metadata, paths, structured text. Object storage stores binary blobs and processed datasets. Never store large PDFs as bytea in the database.

---

## 11. Data Versioning

Use **DVC** (Data Version Control) or simple Parquet snapshots:

- Every time you run a training, write a `dataset_v1.parquet` to `/processed/datasets/mod1/v1/`.
- The training run record references that path.
- You can always reconstruct exactly the data version that produced any model.

For research reproducibility this is non-negotiable. Reviewers may ask: "produce the dataset that gave you the F1 = 0.83 result." If you cannot, your result is suspect.

---

## 12. The Data Quality Pipeline

For every record entering the database, run these checks:

```python
def validate_regulation_record(rec) -> list[str]:
    errors = []
    if not rec.gazette_number:
        errors.append("missing gazette number")
    if rec.gazette_date > date.today():
        errors.append("gazette date in future")
    if len(rec.raw_text) < 100:
        errors.append("text too short (extraction failed?)")
    if rec.detected_language not in ('en', 'si', 'ta', 'mixed'):
        errors.append("unknown language")
    if rec.text_hash in seen_hashes:
        errors.append("duplicate text hash")
    return errors
```

Record validation failures in `audit_log`. Do not silently drop bad records.

---

## 13. Comparison: Spreadsheet vs Web App

| Capability | Spreadsheet | Web App + DB |
|------------|-------------|--------------|
| Concurrent annotators | Conflicts | Safe with locking |
| Duplicate detection | Manual, error-prone | Automatic via UNIQUE constraint |
| Trained-status tracking | Manual flag column | Indexed column, partial index for speed |
| Audit log | None | Full row-level history |
| Multi-module organization | Multiple files | Foreign-keyed tables |
| API access for ML training | CSV export step | Direct SQL query |
| Validation | Drop-down lists | Pydantic schema enforcement |
| Survey responses | Google Forms (dead-end) | Custom forms with conditional logic |
| Reporting / analytics | Manual pivot tables | SQL queries, dashboard panels |
| Backup | Manual | Automated DB backups |
| Data export | Single CSV | Versioned dataset snapshots |
| Versioning | None | Per-record updated_at + audit_log |

---

## 14. Web App MVP — What to Build First (in this order)

If your team builds the data management web app, this is the minimum-viable feature order:

1. **Auth** (basic email + password; or just session tokens for the team).
2. **Survey form (multilingual)** writing to `sme_profiles` + `survey_responses`.
3. **Annotation UI** showing one record, label dropdown, save button → writes to `labeled_examples`.
4. **Annotation queue dashboard** — show how many untrained examples per module.
5. **Duplicate detection on insert.**
6. **Dataset export endpoint** — `GET /datasets/module/1?status=untrained` returns Parquet stream for training.
7. **Mark-as-trained endpoint** — `POST /datasets/module/1/mark-trained` with example IDs.
8. **Training-runs dashboard** — list of past runs with metrics and download links.
9. **Model-versions registry** — promote a run to production.
10. **Inference UI** — paste text, see model prediction.

You do **not** need to build all of this at once. (1)+(2)+(3)+(5) are enough to get started. (6)+(7) come when training begins. The rest are polish.

---

## 15. Benefits Summary (validating your list)

You listed these benefits. All of them are correct, with notes:

| Benefit | Validated? | Note |
|---------|-----------|------|
| Better organization | ✅ | Single source of truth |
| Centralized management | ✅ | One DB, one API, one UI |
| Easier tracking | ✅ | Status flags + audit log |
| Duplicate prevention | ✅ | Hash + UNIQUE constraint |
| Real-time updates | ✅ | API-backed |
| Scalable architecture | ✅ | Postgres handles millions of rows |
| Easier model integration | ✅ | Model reads via SQL or API |
| Automated export pipelines | ✅ | Versioned Parquet snapshots |
| Better data integrity | ✅ | Pydantic + DB constraints |
| Easier monitoring | ✅ | Dashboards + queries |

---

## 16. Common Pitfalls

| Pitfall | Avoidance |
|---------|-----------|
| Building the web app before knowing what data you need | First sketch your DB schema, THEN build forms |
| Letting the web app become a side project that delays research | Time-box web app to 3–4 weeks; survey-via-Google-Forms is acceptable as fallback |
| Storing large PDFs in the database | Use object storage, store paths in DB |
| No backups | Use `pg_dump` daily to a separate location |
| Frontend without API contract | Define API endpoints first, frontend second |

---

## Summary

The database-driven training architecture you proposed is correct and superior to spreadsheets in every dimension. The schema in §4, the trained-status workflow in §5, and the MVP order in §14 are sufficient to begin building immediately. PostgreSQL holds structured records and status; object storage holds raw blobs and dataset snapshots; the model layer reads untrained records and writes back trained-status atomically. Validate every record on insert, log every action to an audit table, and version every dataset that produces a model.
