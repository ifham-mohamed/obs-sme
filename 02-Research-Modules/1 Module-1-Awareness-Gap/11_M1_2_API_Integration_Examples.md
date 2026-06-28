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
    "affected_sectors":["manufacturing"],
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
  -d '{"sectors":["manufacturing","retail","services"]}'
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
DEADLINE_EXTENSION    14.5
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
