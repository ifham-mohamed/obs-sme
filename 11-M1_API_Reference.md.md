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
      "affected_sectors": ["grocery_retail", "food_service", "general_retail"],
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
  "affected_sectors": ["grocery_retail", "general_retail"],
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
  "affected_sectors": ["grocery_retail", "food_service", "general_retail"],
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
  "change_category": "SECTOR_SPECIFIC",
  "affected_sectors": [],
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
  "affected_sectors": ["grocery_retail", "food_service", "general_retail"],
  "sector_probabilities": {
    "grocery_retail": 0.821,
    "food_service": 0.763,
    "general_retail": 0.741
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
  "sectors": ["grocery_retail", "food_service", "general_retail"]
}
```

---

### `PUT /api/v1/m1/regulations/{id}/sectors`

Replace sector assignments (full replacement, not append).

**Auth:** Admin JWT

**Request Body:**

```json
{
  "sectors": ["grocery_retail", "general_retail"]
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
      "affected_sectors": ["grocery_retail", "food_service", "general_retail"],
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


# 11_M1_1 — API Authentication & Authorization

> Companion to [11_M1_API_Reference.md](11_M1_API_Reference.md) — JWT payload structure, role-permission matrix, token expiry/refresh, error codes with examples + request-id propagation.
> **Implementation status:** 🟡 Partial — auth is shipped (JWT + role checks via FastAPI deps); endpoint coverage matches the admin-CRUD slice. Full matrix lights up with BUILD_07.

## Purpose

Parent doc §1 has the role list + the role-permission matrix added in §1.1. This companion is the operational deep-dive: the JWT payload contract, refresh-token flow, request-id propagation, and the full error-code table with example responses.

## Detailed process

### Step 1 — JWT payload structure

```json
{
  "sub": "user_alpha",
  "role": "admin",
  "scope": ["m1:read", "m1:write", "m1:admin"],
  "iat": 1715680800,
  "exp": 1715684400,
  "jti": "tok_01J2Z3K4P5Q6R7S8T9V0W1X2Y3"
}
```

- `sub` — user UUID.
- `role` — one of `admin | expert | sme | (none — public token)`.
- `scope` — explicit endpoint groups; allows revoking write access without changing the role.
- `iat` / `exp` — issued-at / expiry; access tokens valid 60 minutes.
- `jti` — JWT ID; allows revocation by token-ID (logout, security incident).

### Step 2 — Refresh token flow

```
[Login] POST /api/v1/auth/login (email + password)
   → Response: {access_token (60 min), refresh_token (30 days)}

[Use access] GET /api/v1/m1/regulations
   → 200 OK if token valid + scope matches

[Token expired] GET /api/v1/m1/regulations
   → 401 {code: "TOKEN_EXPIRED"}

[Refresh] POST /api/v1/auth/refresh (refresh_token in body)
   → Response: {access_token (new 60 min), refresh_token (rotated)}

[Logout] POST /api/v1/auth/logout
   → Server adds the access token's `jti` to a Redis blacklist (until exp);
     refresh token deleted from `user_refresh_tokens` table
```

### Step 3 — Role enforcement

```python
# backend/app/api/v1/m1_regulations.py
from app.dependencies import require_role

@router.post("/regulations/{id}/verify", dependencies=[Depends(require_role("admin", "expert"))])
async def verify_regulation(id: UUID, ...): ...

@router.delete("/regulations/{id}", dependencies=[Depends(require_role("admin"))])
async def deactivate_regulation(id: UUID, ...): ...
```

`require_role` is a FastAPI dependency that:

1. Parses the JWT.
2. Checks the JWT signature + `exp`.
3. Checks `jti` not in revocation blacklist.
4. Checks `role` is in the allowed list.
5. Checks `scope` covers the endpoint.

### Step 4 — Permission-failure example

A `sme`-token user attempts an admin endpoint:

```
POST /api/v1/m1/regulations/{id}/verify
Authorization: Bearer <sme_token>

Response: 403 Forbidden
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Role 'sme' lacks required scope 'm1:admin' for this endpoint",
    "request_id": "req_01J3...",
    "timestamp": "2026-05-14T03:17:42Z",
    "details": {
      "required_role": ["admin", "expert"],
      "required_scope": "m1:admin",
      "actual_role": "sme"
    }
  }
}
```

### Step 5 — Request-id propagation

Every request gets a `request_id` from middleware:

```python
# backend/app/middleware/request_id.py
@app.middleware("http")
async def add_request_id(request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req_{ulid.new()}"
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

The same `request_id` flows into:
- Every backend log line (`logger.bind(request_id=request.state.request_id)`).
- Every audit-log row (`audit_log.request_id`).
- Every error response body (`error.request_id`).
- Every Celery task spawned (`X-Request-ID` header propagated to broker).

Client-side support flow: if the user reports an error, support staff use the `request_id` to find the exact backend log entry without searching by timestamp + endpoint.

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| JWT (chosen) | Stateless verification, scales horizontally | ✅ Industry standard for SPA + API | Switch to opaque tokens + Redis backend if logout latency becomes problematic. |
| 60-minute access token | Balance of security + UX | ✅ Short enough to limit theft window; long enough to avoid refresh churn | If users complain about constant refreshes, raise to 4 h. |
| Refresh-token rotation | Detects refresh-token theft | ✅ Each refresh issues a new refresh-token; old one invalidated | If we add `refresh_token_family` tracking, can detect theft retrospectively. |
| Role + scope | Fine-grained without proliferating roles | ✅ 4 roles × scope = ~100 effective permissions without 100 roles | If the matrix grows beyond 200 entries — consider RBAC library. |
| ULID for request_id | Sortable, URL-safe | ✅ Better than UUID for log correlation | Never. |

## Worked example

A full login-to-protected-call flow:

```
[POST /api/v1/auth/login]
  body: {email: "admin@enigmatrix.lk", password: "..."}
  response 200: {access_token: "eyJhbGc...", refresh_token: "ref_...", expires_in: 3600}

[GET /api/v1/m1/regulations]
  header: Authorization: Bearer eyJhbGc...
  header: X-Request-ID: req_01J3K4P5
  middleware logs: 'request_id=req_01J3K4P5 user_id=admin@enigmatrix.lk role=admin'
  Pydantic validates query params (page, page_size, etc.)
  service returns paginated list
  response 200: [paginated regulations]
  response header: X-Request-ID: req_01J3K4P5

[Hour later — token expired]
GET /api/v1/m1/regulations
  Response 401: {code: "TOKEN_EXPIRED", request_id: req_01J3M..., ...}

[POST /api/v1/auth/refresh]
  body: {refresh_token: "ref_..."}
  response 200: {access_token: "eyJhbGc...new", refresh_token: "ref_new", expires_in: 3600}
```

## Failure modes & edge cases

- **Stolen access token.** Mitigated by 60-minute TTL + revocation blacklist on logout.
- **Stolen refresh token.** Rotation detects theft on next legitimate refresh (old refresh-token has already been used → reject + force re-login of the legitimate user).
- **JWT signature mismatch.** Server rotated its signing secret; old tokens invalidated. Caught at signature-verify; returns 401 `INVALID_TOKEN`.
- **Clock skew between client and server.** If client clock is > 60 s ahead, the token's `iat` is in the future → server rejects. Mitigated by accepting 120 s clock skew on `iat` verification.
- **Concurrent refresh-token use.** Two browser tabs both refresh simultaneously. Mitigation: rotation marks the *family*; the second refresh sees its parent already used → soft-fails with a "retry with current token" hint.

## Validation & acceptance criteria

- **Token signature verifiable** with the public key in `auth/jwks.json`.
- **Logout revokes** — second request with the same token returns 401.
- **Request-ID present** in every log line + every error response.
- **Per-endpoint role check** — CI test calls every M1 endpoint with each role; asserts the expected 200/403/401.

## Cross-references

- Parent: [11_M1_API_Reference.md](11_M1_API_Reference.md) §1, §1.1, §1.2
- Related: Session-14 audit middleware (already shipped — `backend/app/middleware/audit_middleware.py`)
- BUILD phase: BUILD_07 §auth (already mostly shipped)
- Code: `backend/app/dependencies.py` (require_role), `backend/app/middleware/request_id.py`, `backend/app/api/v1/auth.py`


# 11_M1_2 — API Integration Examples

> Companion to [11_M1_API_Reference.md](11_M1_API_Reference.md) — cURL + Python + Postman examples per endpoint group, common error troubleshooting.
> **Implementation status:** 🟡 Admin-CRUD examples reflect the shipped API; the rest are forward-looking (the Stage-D/E/F endpoints land with BUILD_07).

## Purpose

The parent doc lists endpoints + request/response shape. This companion is the *how do I actually call this from my code* deep-dive — copy-pasteable examples in cURL, Python (`httpx.AsyncClient`), and a Postman collection JSON.

## Detailed process

### Section 1 — Authentication (cURL)

```bash
# Login (development environment)
curl -X POST https://api.enigmatrix.lk/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@enigmatrix.lk","password":"<dev-password>"}'
# → {"access_token":"eyJ...","refresh_token":"ref_...","expires_in":3600}

# Use the access token
export ACCESS_TOKEN="eyJ..."

curl -X GET https://api.enigmatrix.lk/api/v1/m1/regulations \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### Section 2 — Regulation CRUD (cURL + Python)

**List regulations (paginated, filtered):**

```bash
curl -X GET "https://api.enigmatrix.lk/api/v1/m1/regulations?change_category=TAX_RATE_CHANGE&page=1&page_size=20" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Python equivalent:**

```python
import httpx
import asyncio

async def list_regulations(token: str, category: str = "TAX_RATE_CHANGE"):
    async with httpx.AsyncClient(base_url="https://api.enigmatrix.lk", timeout=10.0) as client:
        r = await client.get(
            "/api/v1/m1/regulations",
            headers={"Authorization": f"Bearer {token}"},
            params={"change_category": category, "page": 1, "page_size": 20},
        )
        r.raise_for_status()
        return r.json()

asyncio.run(list_regulations(ACCESS_TOKEN))
```

**Get a single regulation:**

```bash
curl -X GET https://api.enigmatrix.lk/api/v1/m1/regulations/3fa85f64-5717-4562-b3fc-2c963f66afa6 \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Create (manual entry):**

```bash
curl -X POST https://api.enigmatrix.lk/api/v1/m1/regulations \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "gazette_number":"2491/15",
    "gazette_date":"2026-05-14",
    "title_en":"Sample Regulation",
    "change_category":"PRODUCT_STANDARD",
    "affected_sectors":["general_retail"],
    "primary_language":"en"
  }'
```

### Section 3 — Trigger reclassification

```bash
curl -X POST https://api.enigmatrix.lk/api/v1/m1/regulations/{id}/classify \
  -H "Authorization: Bearer $ACCESS_TOKEN"
# → 202 Accepted; classify task enqueued
# Response: {"task_id":"celery_task_uuid","status":"queued"}
```

### Section 4 — Sector overrides

```bash
curl -X PATCH https://api.enigmatrix.lk/api/v1/m1/regulations/{id}/sectors \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sectors":["grocery_retail","food_service","general_retail"]}'
```

### Section 5 — Propagation events

```bash
curl -X GET "https://api.enigmatrix.lk/api/v1/m1/propagation-events?regulation_id=3fa85f64-..." \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### Section 6 — SME survey submission

```bash
curl -X POST https://api.enigmatrix.lk/api/v1/m1/survey-responses \
  -H "Authorization: Bearer $SME_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "regulation_id":"3fa85f64-...",
    "awareness_date":"2026-05-12",
    "awareness_source":"news",
    "action_taken":"yes_in_progress",
    "consent_acknowledged_at":"2026-05-20T09:14:00Z"
  }'
```

### Section 7 — Public listing (no auth)

```bash
curl -X GET "https://api.enigmatrix.lk/api/v1/m1/regulations/public?sector=manufacturing&page=1"
# → 200 OK (no auth header needed)
```

### Section 8 — Analytics

```bash
curl -X GET https://api.enigmatrix.lk/api/v1/m1/analytics/lag \
  -H "Authorization: Bearer $ACCESS_TOKEN"
# → returns v_m1_regulation_lag_summary data
```

## Technology choices

| Option | Trade-off | Decision | When to reconsider |
|---|---|---|---|
| `httpx.AsyncClient` (Python recommendation) | Async-native, modern | ✅ Recommended for Python integrators | Use `requests` if sync-only client. |
| Bearer-token auth | Standard | ✅ Same as Auth0/Okta convention | Never. |
| Pagination via `page` / `page_size` | Most common | ✅ Same as Session-14 admin endpoints | If we need cursor pagination (very large lists), revisit. |
| Idempotency keys | Important for POST | ⚠️ Not yet enforced — recommendation: clients send `Idempotency-Key` header | Add server-side checking in BUILD_07. |

## Worked example

A full "fetch + analyse" Python script for a research dashboard:

```python
import httpx, asyncio, pandas as pd

API_BASE = "https://api.enigmatrix.lk"

async def fetch_all_lag_data(token: str) -> pd.DataFrame:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30.0) as client:
        r = await client.get(
            "/api/v1/m1/analytics/lag",
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        data = r.json()["items"]
    return pd.DataFrame(data)

df = asyncio.run(fetch_all_lag_data(ACCESS_TOKEN))
print(df.groupby("change_category")["median_sme_lag_days"].median())
```

Output:

```
change_category
BUSINESS_REGISTRATION 14.5
EPF_ETF_CHANGE        42.0
ENVIRONMENTAL         55.0
LABOUR_LAW            38.0
TAX_RATE_CHANGE       31.0
...
```

## Failure modes & edge cases

- **HTTP 429 (rate limited).** Default: 60 req/min/IP for unauthenticated; 600 req/min/user authenticated. Mitigation: exponential backoff client-side; honour `Retry-After` header.
- **HTTP 5xx.** Retry only idempotent GETs. POST should *not* auto-retry without an idempotency key (might create duplicate rows).
- **Token rotation surprise.** A long-running client never refreshes → tokens expire. Mitigation: client should refresh proactively at 90 % of `expires_in`.
- **Stale list response.** Pagination on a mutating list can yield duplicates or skips. Mitigation: client uses the `?after=<id>` cursor parameter (forthcoming) instead of `?page=`.

## Validation & acceptance criteria

- **Every example produces a 2xx.** CI runs a smoke test against staging.
- **Postman collection imported successfully.** `tests/m1/test_postman_collection.sh` validates the JSON.
- **Response shapes match the parent doc.** Schema-validation via Pydantic from the OpenAPI spec.

## Cross-references

- Parent: [11_M1_API_Reference.md](11_M1_API_Reference.md) §2–§8
- Related: [11_M1_1_API_Authentication_Authorization.md](11_M1_1_API_Authentication_Authorization.md)
- BUILD phase: BUILD_07 §integration tests
- Code: `tests/m1/integration/`, Postman collection at `tests/m1/integration/postman.json`
