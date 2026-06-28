# 11 — Module 1: API Reference

> **Cross-references:** [07_M1_Deployment_Integration.md](07_M1_Deployment_Integration.md) · [08_M1_Full_System_Architecture.md](08_M1_Full_System_Architecture.md) · [02_M1_Data_Requirements.md](02_M1_Data_Requirements.md)
> **See also:** [13_M1_Folder_Structure_and_Implementation_Flow.md](13_M1_Folder_Structure_and_Implementation_Flow.md) — `backend/app/api/v1/m1_regulations.py` + `services/m1_regulation_service.py`.
> **Sub-step companions:** [11_M1_1_API_Authentication_Authorization.md](11_M1_1_API_Authentication_Authorization.md) · [11_M1_2_API_Integration_Examples.md](11_M1_2_API_Integration_Examples.md)

---

## Abstract

This document provides the complete API reference for all Module 1 endpoints exposed by the Enigmatrix FastAPI backend. All endpoints are prefixed `/api/v1/m1/` and defined in `backend/app/api/v1/m1_regulations.py`, with business logic in `backend/app/services/m1_regulation_service.py`. Endpoints are grouped into: Regulation CRUD, Classification & Verification, Sector Management, Propagation Events, SME Survey, Public endpoints (no auth), and Analytics. Request/response schemas follow the Pydantic models defined in `backend/app/schemas/m1.py`. Authentication uses JWT Bearer tokens.

---

## 1. Authentication

All admin endpoints require a JWT Bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

| Role | Permissions |
|---|---|
| `admin` | Full access to all endpoints |
| `expert` | Read + verify/unverify regulations |
| `sme` | Read public list + submit surveys |
| (none) | Public endpoints only |

### 1.1 Role-Permission Matrix

The full matrix by endpoint group, with the role-specific HTTP responses. `R` = read, `W` = write, `A` = admin-only operations (verify, override, hard delete), `403` = forbidden:

| Endpoint group | `admin` | `expert` | `sme` | (anon) |
|---|---|---|---|---|
| `GET /regulations` (admin list) | R | R | `403` | `401` |
| `POST /regulations` (manual create) | W | `403` | `403` | `401` |
| `PATCH /regulations/{id}` | W | `403` | `403` | `401` |
| `DELETE /regulations/{id}` (soft delete `is_active=false`) | A | `403` | `403` | `401` |
| `POST /regulations/{id}/classify` (re-classify) | W | `403` | `403` | `401` |
| `POST /regulations/{id}/verify` | A | A | `403` | `401` |
| `GET /regulations/{id}/sectors` | R | R | R (via public path) | `401` |
| `PATCH /regulations/{id}/sectors` (override) | W | `403` | `403` | `401` |
| `GET /propagation-events` | R | R | `403` | `401` |
| `POST /propagation-events` (manual) | W | `403` | `403` | `401` |
| `POST /survey-responses` (SME submits answer) | W | `403` | W | `401` |
| `GET /regulations/public` (sector-filtered list) | R | R | R | R |
| `GET /analytics/lag` | R | R | `403` | `401` |
| `GET /analytics/channel-effectiveness` | R | R | `403` | `401` |
| `GET /admin/audit-logs/m1` | A | `403` | `403` | `401` |

Note `(none)` = no token at all yields `401 Unauthorized`; an authenticated user *with the wrong role* yields `403 Forbidden`. The distinction is enforced by separate FastAPI dependencies (`require_auth` for any valid token vs `require_role('admin')` for elevation). Public endpoints accept missing tokens. A worked permission-failure example is in [11_M1_1_API_Authentication_Authorization.md](11_M1_1_API_Authentication_Authorization.md).

### 1.2 Standard Error Response Schema

All M1 endpoints emit a uniform error body so client code can decode failures consistently. The `request_id` lets the support team correlate a client-visible error to the backend log line:

```json
{
  "error": {
    "code": "REGULATION_NOT_FOUND",
    "message": "No regulation found with id 3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "request_id": "req_01J2Z3K4P5Q6R7S8T9V0W1X2Y3",
    "timestamp": "2026-05-14T03:17:42Z",
    "details": {
      "regulation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    }
  }
}
```

Top-level error codes used across the M1 surface:

| HTTP status | `code` | When emitted |
|---|---|---|
| 400 | `INVALID_REQUEST` | Body fails Pydantic validation (e.g. missing required field) |
| 401 | `UNAUTHORIZED` | Missing or expired JWT |
| 403 | `FORBIDDEN` | Valid JWT but role lacks the permission |
| 404 | `REGULATION_NOT_FOUND` / `EVENT_NOT_FOUND` / `SOURCE_NOT_FOUND` | Referenced resource absent |
| 409 | `DUPLICATE_GAZETTE` / `DUPLICATE_PROPAGATION` | Unique constraint violation |
| 422 | `VALIDATION_FAILED` | Server-side semantic check (e.g. attempt to verify a regulation already verified) |
| 429 | `RATE_LIMITED` | Per-IP or per-token rate cap exceeded |
| 500 | `INTERNAL_ERROR` | Unhandled exception; backend stack trace logged separately |
| 503 | `SERVICE_UNAVAILABLE` | Downstream dependency (Postgres, Redis, ONNX Runtime) failed health check |

### 1.3 Regulation Short-Code Exposure

`regulation_short_code` (e.g. `REG-TAX-2024-001`) is **not** a secret. It appears in alert emails (so SMEs can reference it in support conversations), is the canonical URL fragment for the public SME-facing detail page (`/portal/regulations/REG-TAX-2024-001`), and is logged in audit events. Treat it like a public ticket number. By contrast, the internal UUID (`m1_regulations.id`) is *also* not a secret but is harder for humans to quote — short codes exist for that user-experience reason, not for access control.

---

## 2. Regulation CRUD

### `GET /api/v1/m1/regulations`

List all regulations with filtering and pagination.

**Auth:** Admin JWT

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Items per page (max 100) |
| `change_category` | str | — | Filter by category code (e.g. `TAX_RATE_CHANGE`) |
| `sector` | str | — | Filter by sector code (e.g. `manufacturing`) |
| `status` | str | — | Filter by pipeline status |
| `needs_review` | bool | — | If true, return only needs_review=true |
| `is_verified` | bool | — | Filter by verification status |
| `primary_language` | str | — | `en`/`si`/`ta`/`mixed` |
| `gazette_date_from` | date | — | ISO date, inclusive |
| `gazette_date_to` | date | — | ISO date, inclusive |
| `search` | str | — | Full-text search on title_en, summary_en |

**Response `200 OK`:**

```json
{
  "items": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "regulation_short_code": "REG-TAX-2024-001",
      "gazette_number": "2486/22",
      "gazette_date": "2024-09-15",
      "gazette_type": "extraordinary",
      "title_en": "Income Tax (Amendment) Act No. 8 of 2024",
      "change_category": "TAX_RATE_CHANGE",
      "confidence": 0.947,
      "affected_sectors": ["manufacturing", "retail", "services"],
      "is_sme_relevant": true,
      "needs_review": false,
      "is_verified": true,
      "status": "alerted",
      "primary_language": "en"
    }
  ],
  "total": 847,
  "page": 1,
  "page_size": 20,
  "pages": 43
}
```

---

### `POST /api/v1/m1/regulations`

Create a regulation record manually (pre-classifier phase or manual entry).

**Auth:** Admin JWT

**Request Body:**

```json
{
  "gazette_number": "2501/14",
  "gazette_date": "2024-11-01",
  "gazette_type": "extraordinary",
  "source_url": "https://gazette.lk/gazette/2501/14",
  "title_en": "Customs (Amendment) Regulations 2024",
  "change_category": "IMPORT_EXPORT",
  "affected_sectors": ["manufacturing", "retail"],
  "is_sme_relevant": true,
  "penalty_range_lkr": "LKR 50,000 – 500,000",
  "effective_date": "2024-12-01",
  "real_world_example_en": "A textile importer bringing in cotton fabric will now require a new Category B import licence."
}
```

**Response `201 Created`:** Full `RegulationOut` schema (same as GET item).

---

### `GET /api/v1/m1/regulations/{id}`

Get a single regulation by UUID.

**Auth:** Admin JWT

**Response `200 OK`:** Full `RegulationDetailOut` including all text fields:

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "regulation_short_code": "REG-TAX-2024-001",
  "gazette_number": "2486/22",
  "gazette_date": "2024-09-15",
  "gazette_type": "extraordinary",
  "title_en": "Income Tax (Amendment) Act No. 8 of 2024",
  "title_si": "ආදායම් බදු (සංශෝධන) පනත",
  "title_ta": "வருமான வரி (திருத்தம்) சட்டம்",
  "summary_en": "Increases the corporate income tax rate from 24% to 30% for financial institutions. Effective 1 January 2025.",
  "summary_si": "මූල්‍ය ආයතන සඳහා ආදායම් බදු අනුපාතය...",
  "summary_ta": "நிதி நிறுவனங்களுக்கான வருமான வரி விகிதம்...",
  "change_category": "TAX_RATE_CHANGE",
  "category_baseline": "TAX_RATE_CHANGE",
  "confidence": 0.947,
  "domain_code": "TAX",
  "severity_level": "high",
  "is_sme_relevant": true,
  "affected_sectors": ["manufacturing", "retail", "services", "finance"],
  "penalty_range_lkr": null,
  "principal_act_amended": "Inland Revenue Act No. 24 of 2017",
  "effective_date": "2025-01-01",
  "real_world_example_en": "A manufacturing company with annual revenue over LKR 500M will see their tax liability increase by ~6%.",
  "needs_review": false,
  "is_verified": true,
  "expert_verified_by": "Nalaka Perera, CA Sri Lanka",
  "expert_verified_at": "2024-09-17T09:30:00Z",
  "status": "alerted",
  "raw_pdf_path": "./storage/m1/raw/2486_22.pdf",
  "created_at": "2024-09-15T06:12:00Z",
  "updated_at": "2024-09-17T09:30:00Z"
}
```

---

### `PATCH /api/v1/m1/regulations/{id}`

Partial update of a regulation (admin override). All fields optional.

**Auth:** Admin JWT

**Request Body (partial):**

```json
{
  "change_category": "FINANCIAL_REGULATION",
  "affected_sectors": ["finance", "services"],
  "is_sme_relevant": false,
  "is_active": true
}
```

**Response `200 OK`:** Updated `RegulationOut`.

---

### `DELETE /api/v1/m1/regulations/{id}`

Soft-delete a regulation (`is_active = false`).

**Auth:** Admin JWT

**Response `204 No Content`**

---

## 3. Classification & Verification

### `POST /api/v1/m1/regulations/{id}/classify`

Trigger on-demand reclassification of a specific regulation using the ONNX inference engine.

**Auth:** Admin JWT

**Response `200 OK`:**

```json
{
  "regulation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "change_category": "TAX_RATE_CHANGE",
  "confidence": 0.947,
  "affected_sectors": ["manufacturing", "retail", "services"],
  "sector_probabilities": {
    "manufacturing": 0.821,
    "retail": 0.763,
    "services": 0.541,
    "agriculture": 0.112,
    "construction": 0.087,
    "it_bpo": 0.073,
    "hospitality": 0.054,
    "transport": 0.043,
    "healthcare": 0.031,
    "finance": 0.498
  },
  "needs_review": false,
  "classified_at": "2024-09-15T06:14:22Z"
}
```

---

### `POST /api/v1/m1/regulations/{id}/verify`

Mark a regulation as expert-verified.

**Auth:** Admin JWT (role: `expert` or `admin`)

**Request Body:**

```json
{
  "verified": true,
  "verifier_name": "Nalaka Perera, CA Sri Lanka",
  "notes": "Category confirmed correct. Sector assignment reviewed — added finance sector."
}
```

**Response `200 OK`:**

```json
{
  "regulation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "is_verified": true,
  "expert_verified_by": "Nalaka Perera, CA Sri Lanka",
  "expert_verified_at": "2024-09-17T09:30:00Z"
}
```

---

## 4. Sector Management

### `GET /api/v1/m1/regulations/{id}/sectors`

Get sector assignments for a regulation.

**Auth:** Admin JWT

**Response `200 OK`:**

```json
{
  "regulation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "sectors": ["manufacturing", "retail", "services", "finance"]
}
```

---

### `PUT /api/v1/m1/regulations/{id}/sectors`

Replace sector assignments (full replacement, not append).

**Auth:** Admin JWT

**Request Body:**

```json
{
  "sectors": ["manufacturing", "retail", "finance"]
}
```

**Response `200 OK`:** Updated sector list.

---

## 5. Propagation Events

### `GET /api/v1/m1/regulations/{id}/propagation`

Get all propagation events for a regulation across all channels.

**Auth:** Admin JWT

**Response `200 OK`:**

```json
{
  "regulation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "events": [
    {
      "channel": "gazette",
      "first_seen_at": "2024-09-15T00:30:00Z",
      "match_method": "exact_gazette_number",
      "match_confidence": 1.0,
      "is_confirmed": true,
      "source_url": "https://gazette.lk/gazette/2486/22"
    },
    {
      "channel": "portal_ird",
      "first_seen_at": "2024-09-16T14:20:00Z",
      "match_method": "exact_gazette_number",
      "match_confidence": 1.0,
      "is_confirmed": true,
      "source_url": "https://www.ird.gov.lk/en/pages/news.aspx"
    },
    {
      "channel": "news_daily_news",
      "first_seen_at": "2024-09-17T06:00:00Z",
      "match_method": "embedding_similarity",
      "match_confidence": 0.831,
      "is_confirmed": true,
      "source_url": "https://dailynews.lk/gazette-2486-22"
    },
    {
      "channel": "alert_delivery",
      "first_seen_at": "2024-09-15T06:30:00Z",
      "match_method": "human_confirmed",
      "match_confidence": 1.0,
      "is_confirmed": true,
      "source_url": null
    }
  ],
  "lag_summary": {
    "gazette_to_ird_days": 1.57,
    "gazette_to_news_days": 2.23,
    "gazette_to_alert_days": 0.25
  }
}
```

---

## 6. SME Survey

### `POST /api/v1/m1/survey-responses`

Submit an SME awareness survey response for a regulation.

**Auth:** SME JWT

**Request Body:**

```json
{
  "regulation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "awareness_date": "2024-09-20",
  "awareness_source": "accountant",
  "action_taken": "yes_in_progress"
}
```

**Awareness source values:** `gazette_direct`, `accountant`, `association`, `social_media`, `news`, `peer`, `government_sms`, `other`

**Action taken values:** `yes_complied`, `yes_in_progress`, `no_not_aware_of_deadline`, `no_not_applicable`

**Response `201 Created`:**

```json
{
  "id": "7abc1234-0000-0000-0000-000000000001",
  "regulation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "awareness_date": "2024-09-20",
  "awareness_source": "accountant",
  "action_taken": "yes_in_progress",
  "response_date": "2024-10-01T10:15:00Z"
}
```

---

## 7. Public Endpoint (No Auth)

### `GET /api/v1/m1/regulations/public`

SME-facing read-only list of classified, summarised, SME-relevant regulations.

**Auth:** None

**Query Parameters:** `sector`, `page`, `page_size`, `language` (`en`/`si`/`ta`)

**Response `200 OK`:**

```json
{
  "items": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "regulation_short_code": "REG-TAX-2024-001",
      "gazette_date": "2024-09-15",
      "title_en": "Income Tax (Amendment) Act No. 8 of 2024",
      "summary_en": "Increases corporate income tax from 24% to 30%...",
      "change_category": "TAX_RATE_CHANGE",
      "affected_sectors": ["manufacturing", "retail", "services", "finance"],
      "severity_level": "high",
      "effective_date": "2025-01-01",
      "real_world_example_en": "A manufacturing company with annual revenue...",
      "source_url": "https://gazette.lk/gazette/2486/22"
    }
  ],
  "total": 412,
  "page": 1,
  "page_size": 20
}
```

---

## 8. Analytics

### `GET /api/v1/m1/analytics/lag`

Aggregated propagation lag statistics for research output (RQ3, RQ4).

**Auth:** Admin JWT

**Query Parameters:** `category`, `sector`, `date_from`, `date_to`

**Response `200 OK`:**

```json
{
  "total_regulations": 200,
  "channels": [
    {
      "channel": "gazette",
      "median_lag_days": 0.0,
      "mean_lag_days": 0.0,
      "p95_lag_days": 0.0,
      "count": 200
    },
    {
      "channel": "portal_ird",
      "median_lag_days": 1.8,
      "mean_lag_days": 3.2,
      "p95_lag_days": 14.0,
      "count": 142
    },
    {
      "channel": "news_daily_news",
      "median_lag_days": 2.1,
      "mean_lag_days": 4.7,
      "p95_lag_days": 21.0,
      "count": 178
    },
    {
      "channel": "alert_delivery",
      "median_lag_days": 0.25,
      "mean_lag_days": 0.31,
      "p95_lag_days": 0.5,
      "count": 200
    }
  ]
}
```

---

## 9. Backfill Classification

Batch inference endpoint for classifying all regulations whose `change_category` is still `NULL`. This endpoint is admin-only and is run once after model training to bring the historical corpus up to date.

### `POST /api/v1/m1/regulations/backfill`

**Auth:** Admin JWT (requires `role=admin`)

**Request Body:** None required. Optional filter parameters:

```json
{
  "date_from": "2015-01-01",
  "date_to": "2024-12-31",
  "dry_run": false
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `date_from` | ISO date string | `null` (all dates) | Only backfill regulations published on or after this date |
| `date_to` | ISO date string | `null` (all dates) | Only backfill regulations published on or before this date |
| `dry_run` | boolean | `false` | If `true`, count and return without writing classifications |

**Behaviour:**
1. Queries `SELECT id FROM m1_regulations WHERE change_category IS NULL AND status != 'FAILED'`
2. Batches rows in groups of 32
3. Runs ONNX-exported XLM-R dual-head forward pass for each batch
4. Writes `change_category`, `sector_tags`, `classification_confidence` to each row
5. Sets `needs_review=true` for any row where `classification_confidence < 0.80`

**Response `200 OK`:**

```json
{
  "total_unclassified": 423,
  "classified_this_run": 421,
  "skipped_failed": 2,
  "needs_review_flagged": 38,
  "duration_seconds": 142.7,
  "model_version_used": "xlmr-lora-v3",
  "dry_run": false
}
```

**cURL:**
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}' \
  "https://api.enigmatrix.lk/api/v1/m1/regulations/backfill"
```

---

## 10. Model Version Management

Endpoints for listing trained model versions and promoting a version to production. These endpoints support the model versioning schema described in [06_M1_Training_Evaluation.md §9](06_M1_Training_Evaluation.md).

### `GET /api/v1/m1/models`

List all trained model versions, ordered by training date descending.

**Auth:** Admin JWT

**Query Parameters:** `active_only=true|false` (default `false`)

**Response `200 OK`:**

```json
{
  "models": [
    {
      "id": 3,
      "model_name": "gazette_classifier",
      "version": "v3",
      "base_checkpoint": "xlm-roberta-base",
      "macro_f1_test": 0.934,
      "macro_f1_val": 0.941,
      "metrics_per_language": {
        "en": 0.951,
        "si": 0.918,
        "ta": 0.929
      },
      "artifact_path": "s3://enigmatrix-models/m1/xlmr-lora-v3/",
      "git_commit": "a3f81c2",
      "seed": 42,
      "is_production": true,
      "trained_at": "2026-04-10T14:22:00Z"
    }
  ],
  "total": 3
}
```

---

### `POST /api/v1/m1/models/{model_id}/activate`

Promote a model version to production. The previously active version is automatically demoted. The new version is loaded into the ONNX inference worker on next task execution.

**Auth:** Admin JWT

**Path Parameter:** `model_id` — integer ID from `model_versions.id`

**Request Body:** None

**Response `200 OK`:**

```json
{
  "activated_model_id": 3,
  "version": "v3",
  "previous_production_version": "v2",
  "macro_f1_test": 0.934,
  "status": "activated",
  "note": "Worker will load new ONNX model on next task start. Force-restart worker to apply immediately."
}
```

**Response `409 CONFLICT`:** Returned if the requested model version is already the active production model.

---

## 11. Channel Effectiveness Analytics

Returns the `v_m1_channel_effectiveness` view data — a ranked table of secondary-source channels by median lag, used to produce Finding F4 (RQ4) in the research findings (see [08_M1_Full_System_Architecture.md §10](08_M1_Full_System_Architecture.md)).

### `GET /api/v1/m1/analytics/channel-effectiveness`

**Auth:** Admin JWT

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `date_from` | ISO date | null | Filter propagation events on or after this date |
| `date_to` | ISO date | null | Filter propagation events on or before this date |
| `category` | string | null | Filter to one regulation category |
| `min_count` | integer | 10 | Exclude channels with fewer than N observations |

**Response `200 OK`:**

```json
{
  "generated_at": "2026-05-13T10:00:00Z",
  "channel_count": 6,
  "channels": [
    {
      "rank": 1,
      "channel": "alert_delivery",
      "median_lag_days": 0.01,
      "mean_lag_days": 0.01,
      "p25_lag_days": 0.01,
      "p75_lag_days": 0.02,
      "observation_count": 197
    },
    {
      "rank": 2,
      "channel": "portal_ird",
      "median_lag_days": 7.0,
      "mean_lag_days": 9.3,
      "p25_lag_days": 4.0,
      "p75_lag_days": 14.0,
      "observation_count": 143
    },
    {
      "rank": 3,
      "channel": "portal_slsi",
      "median_lag_days": 9.5,
      "mean_lag_days": 12.1,
      "p25_lag_days": 6.0,
      "p75_lag_days": 18.0,
      "observation_count": 87
    },
    {
      "rank": 4,
      "channel": "news_daily_ft",
      "median_lag_days": 23.0,
      "mean_lag_days": 28.4,
      "p25_lag_days": 14.0,
      "p75_lag_days": 41.0,
      "observation_count": 134
    },
    {
      "rank": 5,
      "channel": "news_lankadeepa",
      "median_lag_days": 27.0,
      "mean_lag_days": 31.2,
      "p25_lag_days": 18.0,
      "p75_lag_days": 45.0,
      "observation_count": 96
    },
    {
      "rank": 6,
      "channel": "sme_first_aware",
      "median_lag_days": 33.0,
      "mean_lag_days": 42.7,
      "p25_lag_days": 21.0,
      "p75_lag_days": 58.0,
      "observation_count": 100
    }
  ],
  "note": "Channels ranked by median_lag_days ASC. Finding F4: alert_delivery achieves 0.01-day median vs 33-day baseline SME awareness lag."
}
```

---

## 12. Error Responses

All endpoints return standard error envelopes:

| Status | Code | Meaning |
|---|---|---|
| `400` | `VALIDATION_ERROR` | Invalid request body or query params |
| `401` | `UNAUTHORIZED` | Missing or invalid JWT |
| `403` | `FORBIDDEN` | Authenticated but insufficient role |
| `404` | `NOT_FOUND` | Regulation ID not found |
| `409` | `DUPLICATE_GAZETTE` | gazette_number already exists |
| `422` | `UNPROCESSABLE_ENTITY` | Pydantic validation failure |
| `500` | `INTERNAL_ERROR` | Unhandled server error |

```json
{
  "detail": {
    "code": "NOT_FOUND",
    "message": "Regulation 3fa85f64-... not found"
  }
}
```

---

## 13. cURL Examples

```bash
# List regulations needing review
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.enigmatrix.lk/api/v1/m1/regulations?needs_review=true&page_size=10"

# Trigger reclassification
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "https://api.enigmatrix.lk/api/v1/m1/regulations/3fa85f64-.../classify"

# Submit expert verification
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"verified": true, "verifier_name": "Nalaka Perera, CA"}' \
  "https://api.enigmatrix.lk/api/v1/m1/regulations/3fa85f64-.../verify"

# Public SME endpoint — no auth
curl "https://api.enigmatrix.lk/api/v1/m1/regulations/public?sector=manufacturing&language=en"
```

---

## References

- Enigmatrix Backend: `backend/app/api/v1/m1_regulations.py`
- Enigmatrix Backend: `backend/app/services/m1_regulation_service.py`
- Enigmatrix Backend: `backend/app/schemas/m1.py`
- FastAPI. (2024). *OpenAPI Documentation*. [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- Pydantic. (2024). *Data validation using Python type hints*. [docs.pydantic.dev](https://docs.pydantic.dev)
