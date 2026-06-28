# 02_M1_3 — Data Governance & Retention

> Companion to [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) — PDPA compliance checklist, audit-log retention, storage growth projections, S3 cold-archive YAML.
> **Implementation status:** 🔲 Deferred (BUILD_07 retention jobs + BUILD_12 S3 archive policy). PDPA Sri Lanka compliance checklist is **applicable today** to the manual-CRUD admin slice.

## Purpose

Section 6 of the parent doc states retention rules in two short bullets ("Raw PDFs retained indefinitely", "Survey responses anonymised after 5 years"). This companion turns those rules into operationally enforceable jobs: PDPA Sri Lanka compliance steps, S3 lifecycle YAML, audit-log purge cadence, and storage projections that decide *when* (not just whether) we hit the cost cliff.

## Detailed process

### Step 1 — PDPA Sri Lanka compliance checklist

PDPA No. 9 of 2022 covers personal data processed by Enigmatrix. The relevant obligations for M1:

- **Consent.** SME survey respondents must consent to data use at submission time. The portal form embeds a `consent_acknowledged_at` timestamp; submissions with NULL consent are rejected.
- **Right of access.** An SME can request a dump of their data (`GET /api/v1/sme/me/data-export`). The endpoint returns all `m1_sme_awareness_responses` rows plus the `sme_profiles` row.
- **Right of erasure.** An SME can request deletion (`DELETE /api/v1/sme/me`). The implementation **anonymises** rather than deletes: `sme_profile_id` is replaced with a tombstone UUID; `awareness_source` is preserved (we still need it for aggregate research) but `awareness_date` is generalised to month-precision.
- **Data minimisation.** `m1_sme_awareness_responses` stores only the answers + a foreign key — no email, phone, or address (those live in `sme_profiles` with controlled access).
- **Purpose limitation.** Survey data is used only for research findings F1–F6; the database has no other code paths that read these rows.
- **Cross-border transfer.** Postgres + S3 are hosted in `ap-south-1` (Mumbai) or `ap-southeast-1` (Singapore) — both region choices have a data-residency justification documented in the privacy notice.

### Step 2 — Retention windows

| Asset | Retention | Anonymisation step | Where enforced |
|---|---|---|---|
| Raw gazette PDFs | Indefinite (public docs) | None — public records | `storage/m1/raw/`; S3 lifecycle moves > 2 y to Glacier |
| Extracted text in `m1_regulations.raw_text` | Indefinite | None | Postgres; same retention as regulation row |
| `m1_sme_awareness_responses` | 5 years from `response_date` | Anonymise at year 5 (see Step 1 right-of-erasure) | Nightly cron `anonymise_aged_survey_responses.py` |
| `sme_profiles` of inactive SMEs (no login > 2 y) | 5 years | Soft-anonymise after year 2; hard-delete after year 5 | Same nightly cron |
| `audit_log` | 7 years (IRD audit requirement) | None | Nightly cron `archive_old_audit_logs.py` moves > 5 y to cold storage |
| `m1_pipeline_audits` | 1 year | Aggregate to weekly summaries at year 1 | Nightly cron |
| OCR cache, inference cache (Redis) | 30 days (TTL) | N/A | Redis TTL auto-expires |

### Step 3 — Storage growth projection

At steady state (500 new gazettes/yr × ~2 MB each = ~1 GB/yr):

| Year | PDFs on disk (hot) | PDFs in Glacier | Total Postgres rows | Postgres on-disk (with 30 % overhead) | Survey rows |
|---|---|---|---|---|---|
| Y1 | 1 GB | 0 | ~10 k regulations + ~50 k events | ~200 MB | ~5 k |
| Y3 | 1 GB (2 y rolling) | 2 GB | ~30 k + ~150 k | ~600 MB | ~15 k |
| Y5 | 1 GB | 4 GB | ~50 k + ~250 k | ~1.0 GB | ~25 k (after anonymisation: same row count) |
| Y10 | 1 GB | 9 GB | ~100 k + ~500 k | ~2.0 GB | ~50 k |

The Postgres on-disk total stays under Supabase Pro's 8 GB plan ($25/mo) for the project's foreseeable lifetime; S3 storage costs are dominated by Glacier ($0.001/GB-month → < $0.10/month at Y10).

### Step 4 — S3 lifecycle YAML

```yaml
# infra/aws/s3_m1_lifecycle.yaml
Bucket: enigmatrix-m1-pdfs
LifecycleConfiguration:
  Rules:
    - Id: move-pdfs-to-glacier-after-2y
      Status: Enabled
      Filter:
        Prefix: "raw/"
      Transitions:
        - Days: 730                           # 2 years
          StorageClass: GLACIER
        - Days: 1825                          # 5 years
          StorageClass: DEEP_ARCHIVE
    - Id: delete-orphaned-ocr-cache
      Status: Enabled
      Filter:
        Prefix: "ocr_cache/"
      Expiration:
        Days: 30
```

Glacier retrieval takes 3–5 hours; Deep Archive takes 12 hours. Acceptable for research re-extraction; **not** for live alerts (the live alert path only touches the last 90 days of PDFs, which stay in S3 Standard).

### Step 5 — Audit log archival

`audit_log` is INSERT-ONLY (per Session 14 design). After 5 years, rows are moved to a separate table `audit_log_archive` with an identical schema; the `audit_log` table truncates the moved range. The archive table lives in a cheaper Postgres tier (read-only replica with smaller IOPS). After 7 years, archive rows are exported to S3 Glacier as Parquet for IRD audit and then deleted from Postgres.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| S3 lifecycle (chosen) | Standard pattern; managed by AWS; minimal code | ✅ Two-stage Standard → Glacier → Deep Archive matches the cost model in §3. | If we migrate off AWS (e.g. to Cloudflare R2 or Backblaze B2) the lifecycle rules need re-implementation in the new provider's idiom. |
| Custom Postgres + filesystem | Total control over move semantics | ❌ Re-implements AWS lifecycle in Python — error-prone, no automatic cost tier. | Only if AWS becomes a vendor-risk concern. |
| Glacier-only (skip Standard tier) | Cheapest storage from day 1 | ❌ Live alerts need < 1 s read access to recent PDFs; Glacier is 3–5 h. | Never — operational requirement. |
| Hard-delete instead of anonymise | Simpler legal posture | ❌ Loses aggregate research findings (F1–F6 use channel + source-of-awareness, both of which are kept). Anonymisation preserves research value while honouring PDPA. | Only if PDPA enforcement guidance specifically prohibits anonymisation. |

## Worked example

A right-of-erasure request from an SME (anonymised):

```
Day 0:  GET /api/v1/sme/me/data-export → returns 7 survey responses + profile
Day 0:  DELETE /api/v1/sme/me → endpoint queues:
        - anonymise_sme_profile(sme_profile_id=...)
        - anonymise_awareness_responses(sme_profile_id=...)
        - email_confirmation('done', user_email)
Day 0+5min: cron fires; rows updated:
        sme_profiles: email='deleted_<uuid>@erased.local', phone=NULL, address=NULL
        m1_sme_awareness_responses: sme_profile_id=tombstone_uuid,
                                    awareness_date=date_trunc('month', awareness_date)
Day 0+5min: audit_log row written: event='sme.erasure', actor=user_email_at_request_time
Day +30:    confirmation email + reference number retained 90 days for support purposes
```

The aggregate F4 (channel effectiveness) finding is unaffected — the user's 7 channel/awareness-date pairs still contribute to the per-channel medians, just at month-precision instead of day-precision.

## Failure modes & edge cases

- **Anonymisation runs partial.** If the cron crashes mid-batch, some rows are updated, some aren't. Mitigation: each batch is wrapped in a transaction with row-count assertion at the end (`SELECT COUNT(*) FROM m1_sme_awareness_responses WHERE sme_profile_id IN (...) AND awareness_date_full IS NOT NULL` must equal zero before commit).
- **S3 lifecycle doesn't fire.** AWS evaluates rules once per day around 00:00 UTC — a PDF written at 23:50 on day N-1 + 730 won't move until day N + 1. Acceptable but worth noting in any audit.
- **Glacier-retrieve cost surprise.** Retrieving 100 PDFs from Deep Archive costs ~$5 (storage class transition + egress). If a researcher requests a re-extraction over historical data, the cost is real. Mitigation: a `cold_archive_retrieval_cap_lkr` env var in `backend/app/config/feature_flags.py` and an admin-only endpoint that prompts for confirmation.
- **Postgres archive table grows unbounded.** `audit_log_archive` can balloon to 10s of GB at Y7. Mitigation: partition by year (`audit_log_archive_2026`, `_2027`, ...) so the Y7 → S3 export drops a single partition.

## Validation & acceptance criteria

- **PDPA dry run.** Quarterly: simulate a right-of-erasure request end-to-end on a staging DB; confirm all touch points (Postgres + Redis + S3 PDF references) are correct. Sign-off in `research/compliance/pdpa_drills/`.
- **Lifecycle rule test.** AWS-side: `aws s3api get-bucket-lifecycle-configuration --bucket enigmatrix-m1-pdfs` matches `s3_m1_lifecycle.yaml` byte-for-byte (CI assertion).
- **Storage projection accuracy.** Quarterly: actual storage usage compared to the Y1/Y3/Y5 projections; deviation > 30 % triggers a re-projection.
- **Anonymisation idempotency.** Re-running `anonymise_aged_survey_responses.py` twice produces zero new updates (test: dry-run mode comparing pre/post row hashes).

## Cross-references

- Parent: [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md) §6 (governance), §3.2 (storage growth)
- Related: [09_M1_3_SME_Survey_Instrument.md](09_M1_3_SME_Survey_Instrument.md) (consent collection), [12_M1_2_Retraining_Deployment_Rollback.md](12_M1_2_Retraining_Deployment_Rollback.md) (audit-log archive interaction)
- BUILD phase: BUILD_07 §retention crons, BUILD_12 §S3 lifecycle
- Code (when shipped): `backend/app/scripts/anonymise_aged_survey_responses.py`, `archive_old_audit_logs.py`; `infra/aws/s3_m1_lifecycle.yaml`
