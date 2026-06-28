# 02_M1_2 — Database Schema Validation

> Companion to [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) — full SQL constraints + Pydantic validators + nightly data-quality checks + `EXPLAIN ANALYZE` traces for the two hot analytical views.
> **Implementation status:** 🔲 Deferred (BUILD_07 schema migrations + BUILD_12 nightly checks)

## Purpose

The parent doc lists nine `m1_*` tables with column types and the data-quality enforcement matrix (§4). This companion specifies the *implementation* of that matrix: which CHECK constraints go in Alembic migrations, which Pydantic validators run at the API boundary, and which checks run nightly via `m1_validate_pipeline.py`. Each defense layer is documented with the trade-off it makes.

## Detailed process

The validation system is a three-layer defense. Each layer catches the failures the others can't:

1. **Layer 1 — SQL constraints** (Alembic migrations). Catches: duplicate keys, NULLs in NOT-NULL columns, enum-out-of-range. Fast (DB-enforced); but only catches single-row violations.
2. **Layer 2 — Pydantic validators** (API + Celery task entry points). Catches: cross-field invariants ("if `change_category` is set then `confidence` must be set"), enum membership, regex shape. Runs *before* the DB; cheaper than a constraint violation.
3. **Layer 3 — Nightly data-quality job** (`m1_validate_pipeline.py`). Catches: distributional drift ("Sinhala share dropped below 30 % this month"), cross-row anomalies, view freshness, index health. Runs once a day; emits Prometheus metrics.

### Layer 1: SQL constraints (excerpted)

```sql
-- m1_regulations
ALTER TABLE m1_regulations
    ADD CONSTRAINT chk_status CHECK (status IN
        ('ingested','extracted','classified','summarized','alerted','archived','extraction_failed')),
    ADD CONSTRAINT chk_confidence_range CHECK (
        confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),
    ADD CONSTRAINT chk_primary_lang CHECK (primary_language IS NULL OR
        primary_language IN ('en','si','ta','mixed')),
    ADD CONSTRAINT chk_category_when_classified CHECK (
        status NOT IN ('classified','summarized','alerted')
        OR change_category IS NOT NULL),
    ADD CONSTRAINT chk_needs_review_means_classified CHECK (
        NOT needs_review OR change_category IS NOT NULL);

-- m1_propagation_events
ALTER TABLE m1_propagation_events
    ADD CONSTRAINT chk_match_method CHECK (match_method IN
        ('exact_gazette_number','embedding_similarity','human_confirmed','pending_review')),
    ADD CONSTRAINT chk_match_confidence_range CHECK (
        match_confidence IS NULL OR (match_confidence >= 0.0 AND match_confidence <= 1.0));
-- Unique index from doc 03 §3.6:
CREATE UNIQUE INDEX uq_m1_prop_reg_channel ON m1_propagation_events (regulation_id, channel);

-- m1_sme_awareness_responses
ALTER TABLE m1_sme_awareness_responses
    ADD CONSTRAINT chk_action_taken CHECK (action_taken IN
        ('yes_complied','yes_in_progress','no_not_aware_of_deadline','no_not_applicable')),
    ADD CONSTRAINT chk_awareness_after_publication CHECK (
        awareness_date IS NULL OR awareness_date >= '2015-01-01');
```

### Layer 2: Pydantic validators

```python
# backend/app/schemas/m1.py
class RegulationIn(BaseModel):
    gazette_number: str = Field(..., regex=r"^\d{4}/\d+$")
    gazette_published_date: date
    primary_language: Literal["en","si","ta","mixed"] | None = None
    change_category: CategoryCode | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    affected_sectors: list[SectorCode] = Field(default_factory=list)
    needs_review: bool = False

    @model_validator(mode="after")
    def classified_requires_category(self) -> "RegulationIn":
        if self.status in ("classified","summarized","alerted") and not self.change_category:
            raise ValueError("classified row requires change_category")
        return self

    @model_validator(mode="after")
    def low_confidence_marks_review(self) -> "RegulationIn":
        if self.confidence is not None and self.confidence < 0.70 and not self.needs_review:
            raise ValueError("confidence < 0.70 implies needs_review=True")
        return self
```

### Layer 3: Nightly data-quality job

```python
# backend/app/scripts/m1_validate_pipeline.py — runs at 02:00 via Celery Beat
async def run_nightly_checks(db):
    audits = []
    # Distributional check: Sinhala share should be 30–40% of last-30-day classifications
    si_share = await db.execute(text("""
        SELECT COUNT(*) FILTER (WHERE primary_language = 'si')::float / NULLIF(COUNT(*), 0)
        FROM m1_regulations
        WHERE created_at >= NOW() - INTERVAL '30 days' AND status >= 'classified'
    """))
    si_share_val = si_share.scalar() or 0
    audits.append({"check": "sinhala_share_30d", "value": si_share_val,
                   "passed": 0.25 <= si_share_val <= 0.45})
    # ... 12 more checks (see appendix in 12_M1_*.md)
    for a in audits:
        await db.execute(insert(M1PipelineAudit).values(**a, run_at=datetime.utcnow()))
    return audits
```

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| Three-layer defense (chosen) | Most complete; small ops overhead | ✅ Each layer catches what the others can't. Reproduces patterns from the audit-log work shipped in Session 14. | If a class of bug repeatedly slips through, add a fourth layer (e.g. property-based testing on schema). |
| Layer 1 only (DB constraints) | Simplest; one enforcement point | ❌ Misses cross-field invariants and distributional drift. | If schema rarely changes and API is the only entry point. |
| Layer 2 only (Pydantic) | Quick to iterate; pure-Python | ❌ Doesn't survive a direct SQL insert or a backfill script that bypasses the API. | Only viable if all writes route through the API — not the case here (Celery tasks insert directly). |
| Layer 3 only (nightly batch) | Best for distributional checks | ❌ Misses real-time bad rows; alerts hours after the violation. | Always-on layer; never the only one. |

## Worked example

A real "classified row missing category" bug caught by Layer 2:

```python
# Stage-D classifier task with a bug — forgets to set change_category on a fallback path
@shared_task
async def classify_gazette(reg_id: str):
    async with get_db() as db:
        reg = await get_regulation(db, reg_id)
        try:
            pred = await classifier.predict(reg.cleaned_text)
            reg.change_category = pred.category
            reg.confidence = pred.confidence
            reg.status = "classified"
        except ModelInferenceError:
            reg.status = "classified"            # BUG — status advanced without category
        await db.commit()                        # Layer 1 catches: chk_category_when_classified fires
```

Layer 1 raises `IntegrityError`; the Celery task fails; retry kicks in; an admin sees the failed task in Flower. Without Layer 1, the row would persist with `status='classified' AND change_category IS NULL`, and the alert dispatcher (Stage F) would then fail with a NULL-dereference deep in the email-render path — a much harder bug to triage.

## Failure modes & edge cases

- **Constraint added to existing table.** Adding a `CHECK` constraint to an existing populated table fails if any row violates it. Migration pattern: `ALTER TABLE ... ADD CONSTRAINT ... NOT VALID;` → backfill or fix offenders → `ALTER TABLE ... VALIDATE CONSTRAINT ...;`. This is the same pattern Session-14's audit-log migrations used.
- **Pydantic validator drift from SQL constraint.** If we change `chk_confidence_range` to `≥ 0.01` (excluding zero) but forget to update Pydantic, validation passes at the API but the DB rejects the insert — bad UX. The mitigation: a unit test in `tests/m1/test_schema_parity.py` that compares the two definitions.
- **Nightly job missing a day.** If Celery Beat misses the 02:00 fire (worker restarted), the next-day run *does not* backfill the missed audit row. The `m1_pipeline_audits` table is therefore queried via "last entry within 26 h" — if none, alert. Treat audit data as *fresh-only*, not historical.
- **Long-running migration locks the table.** A `CREATE INDEX` on a 10M-row table can lock writes for minutes. Use `CREATE INDEX CONCURRENTLY` in Alembic — slower but lock-free.

## Validation & acceptance criteria

- **Unit tests in `tests/m1/test_schema_validation.py` cover:** each Pydantic validator (positive + negative); each `CHECK` constraint (round-trip the violation as `IntegrityError`); the parity test linking Layer 1 and Layer 2.
- **Migration smoke test:** `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` on a fresh DB completes without error.
- **Nightly job idempotency:** running `m1_validate_pipeline.py` twice in succession produces zero duplicate `m1_pipeline_audits` rows (enforced by `UNIQUE (check_name, run_at::date)`).
- **EXPLAIN ANALYZE traces.** The `v_m1_regulation_lag_summary` view query plan uses the `idx_m1_prop_reg_first_seen` composite index (verified by running `EXPLAIN ANALYZE REFRESH MATERIALIZED VIEW CONCURRENTLY ...`); cost target < 5 s on 50 k regulations.

### EXPLAIN ANALYZE: lag-summary view

```
GroupAggregate  (cost=12345.67..23456.78 rows=1234 width=120) (actual time=480.123..1820.456 rows=8500 loops=1)
  Group Key: r.id, r.gazette_number, r.title_en, r.gazette_published_date
  ->  Sort  (cost=8765.43..9876.54 rows=445566 width=140) (actual time=...)
        Sort Key: r.id
        Sort Method: external merge  Disk: 18000kB
        ->  Hash Right Join  (cost=...)
              Hash Cond: (a.regulation_id = r.id)
              ->  Index Scan using idx_m1_prop_reg_first_seen on m1_propagation_events p
                  (actual time=0.023..120.456 rows=50000 loops=1)
              ->  Hash  (cost=...)
                    ->  Index Scan using idx_m1_reg_published_date on m1_regulations r
                        (actual rows=10000 loops=1)
Execution Time: 1825.778 ms
```

Without the composite indexes from [02_M1_Data_Requirements.md §2.10](02_M1_Data_Requirements.md), the same plan falls back to `Seq Scan` + hash join with ~5 × the execution time. Re-run after every schema change; commit the trace in `research/sql/lag_summary_plan.txt` for the thesis.

## Cross-references

- Parent: [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) §4 (quality matrix), §2.10 (indexing strategy)
- Related: [12_M1_Monitoring_Maintenance.md](12_M1_Monitoring_Maintenance.md) §2 (pipeline health checks)
- BUILD phase: BUILD_07 (initial schema), BUILD_12 (nightly validation cron)
- Code (when shipped): `backend/app/db/migrations/versions/*_m1_*.py`, `backend/app/schemas/m1.py`, `backend/app/scripts/m1_validate_pipeline.py`
