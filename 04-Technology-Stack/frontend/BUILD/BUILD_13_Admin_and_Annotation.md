# BUILD 13 — Admin Console & Annotation

> **Goal:** ship the operator-facing admin console (Next.js route group), the Label Studio annotation bridge, and the append-only audit trail that records every override across Modules 1–4.
>
> **Read first:** `BUILD_04_Database_and_Storage.md`, `BUILD_05_Frontend_App.md`, `BUILD_06_Auth_and_Users.md`, `BUILD_07_Module1_Awareness.md`, `BUILD_08_Module2_Knowledge.md`, `BUILD_09_Module3_Risk.md`, `BUILD_10_Module4_Misinformation.md`. Authentication, JWT issuance, and the role hierarchy (`sme_user`, `chartered_accountant`, `annotator`, `admin`, `superadmin`) are defined there and are **not** re-implemented in this file.
>
> **Scope:** the **admin frontend** route group, the **Label Studio bridge** (project sync + webhook + import), the **audit trail extension**, and **bulk CSV** operations for the question bank and labeled examples. The actual review *business logic* — what counts as a valid M1 reclassification, what kappa threshold gates an M4 release, how an M3 override propagates back to the model registry — remains owned by the module BUILD files cited above. This file only specifies the surfaces (HTTP routes, UI pages, DB writes) that those modules plug into.

> **M1 admin-tracking surfaces deferred to this build:**
> - **`/admin/m1/review-queue`** — needs-review queue triage. See [../SETUP/14_M1_2_Admin_Review_Queue_Triage.md](../../m1/14_M1_2_Admin_Review_Queue_Triage.md) for the intended user workflow.
> - **`/admin/m1/analytics`** — lag analytics + propagation tracker (4 cards: F1–F4 findings). See [../SETUP/14_M1_4_Admin_Lag_Analytics.md](../../m1/14_M1_4_Admin_Lag_Analytics.md).
> - **`/admin/m1/pipeline`** — Stage A–F dashboard for at-a-glance bottleneck spotting. See [../SETUP/14_M1_1_Admin_Pipeline_State_Tracking.md](../../m1/14_M1_1_Admin_Pipeline_State_Tracking.md).
> - **SME tracker `/portal/m1/my-regulations`** — action-taken/compliance ledger. See [../SETUP/14_M1_7_SME_Compliance_Action_Tracking.md](../../m1/14_M1_7_SME_Compliance_Action_Tracking.md).
> - **SME deadlines + alerts `/portal/m1/deadlines`** — deadline countdown widget + alert delivery history. See [../SETUP/14_M1_8_SME_Deadline_Alert_History.md](../../m1/14_M1_8_SME_Deadline_Alert_History.md).
>
> These surfaces are documented in the `14_M1_*` companions with status badge 🔲 deferred + the *intended* user workflow drawn from the backend M1 docs. When BUILD_13 lands them, the badges flip to ✅.

---

## 1. Component Map

| Concern | Code path | Talks to |
|---------|-----------|----------|
| Admin route group | `frontend/app/(admin)/...` | Next.js App Router, `/api/v1/users/me` |
| Role-gated middleware | `frontend/middleware.ts` | JWT cookie from BUILD_06 |
| M1 review pages | `frontend/app/(admin)/regulations/...` | `/api/v1/admin/regulations` |
| M4 label correction | `frontend/app/(admin)/posts/...` | `/api/v1/admin/posts`, `m4_labeled_posts` |
| M3 prediction audit | `frontend/app/(admin)/predictions/...` | `m3_predictions`, SHAP service |
| M2 question editor | `frontend/app/(admin)/questions/...` | `qna_questions`, `qna_question_versions` |
| Audit log | `backend/app/services/audit.py` | extends `audit_log` from BUILD_04 |
| Label Studio bridge | `backend/app/integrations/label_studio.py` | LS REST API, webhook receiver |
| Bulk CSV | `backend/app/admin/bulk.py` | `qna_questions`, `labeled_examples` |
| Postgres trigger | `backend/migrations/versions/20260201_audit_immutable.py` | `audit_log` table |

> **Audit-table reuse note.** BUILD_04 already defines an `audit_log` table for compliance evidence (M3). Rather than introduce a parallel `audit_events` relation, this build **extends** `audit_log` with the columns enumerated in §8 and treats it as the single append-only event store. References to `audit_events` in earlier drafts should be read as "the audit_log table, post-extension." A migration in §8 adds the missing columns and the immutability trigger.

---

## 2. Admin Route Group (Next.js App Router)

The admin UI lives under a route **group** `(admin)` so the URL stays flat (`/admin/...`) while sharing one layout, one middleware, and one design-system shell. Server components do data fetching against the FastAPI backend with the user's JWT (forwarded from cookies); client components carry interactivity (forms, tables, drag handlers).

```tsx
// FILE: frontend/app/(admin)/layout.tsx
import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { AdminShell } from "@/components/admin/shell";
import { fetchMe } from "@/lib/api/users";

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const token = cookies().get("access_token")?.value;
  if (!token) redirect("/login?next=/admin");
  const me = await fetchMe(token);
  if (!me || !["admin", "superadmin", "annotator"].includes(me.role)) {
    redirect("/forbidden");
  }
  return <AdminShell user={me}>{children}</AdminShell>;
}
```

```ts
// FILE: frontend/middleware.ts
import { NextRequest, NextResponse } from "next/server";

const ADMIN_PREFIX = "/admin";

export function middleware(req: NextRequest) {
  if (!req.nextUrl.pathname.startsWith(ADMIN_PREFIX)) return NextResponse.next();
  const token = req.cookies.get("access_token")?.value;
  if (!token) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", req.nextUrl.pathname);
    return NextResponse.redirect(url);
  }
  // Deep role check happens in the (admin) layout server component
  // (we cannot decode JWT safely in edge runtime without the verify key here).
  return NextResponse.next();
}

export const config = { matcher: ["/admin/:path*"] };
```

```tsx
// FILE: frontend/app/(admin)/page.tsx
import Link from "next/link";

const TILES = [
  { href: "/admin/regulations", label: "M1 Regulation review" },
  { href: "/admin/posts", label: "M4 Post label correction" },
  { href: "/admin/predictions", label: "M3 Prediction audit" },
  { href: "/admin/questions", label: "M2 Question bank" },
  { href: "/admin/audit", label: "Audit log" },
];

export default function AdminHome() {
  return (
    <ul className="grid grid-cols-2 gap-4 p-6">
      {TILES.map((t) => (
        <li key={t.href} className="border rounded p-4">
          <Link href={t.href} className="font-medium">{t.label}</Link>
        </li>
      ))}
    </ul>
  );
}
```

The layout above performs the **authoritative** role check by hitting `/api/v1/users/me`, which reuses the BUILD_06 dependency `require_role(...)`. The edge middleware only redirects unauthenticated users; it never grants access by itself.

---

## 3. M1 Regulation Review (`/admin/regulations`)

The page lists regulations whose classifier confidence falls below the routing threshold (see BUILD_07 §5) or that an SME user has flagged. Each detail page shows the original PDF text, the predicted classification, and an override form.

```tsx
// FILE: frontend/app/(admin)/regulations/page.tsx
import { listRegulationsForReview } from "@/lib/api/admin";
import { ReviewTable } from "@/components/admin/review-table";

export default async function RegulationsReview() {
  const rows = await listRegulationsForReview();
  return (
    <section className="p-6">
      <h1 className="text-xl font-semibold">M1 — Regulations awaiting review</h1>
      <ReviewTable rows={rows} hrefBase="/admin/regulations" />
    </section>
  );
}
```

```python
# FILE: backend/app/api/v1/admin/regulations.py
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import require_role, get_session
from app.services.audit import write_audit
from app.schemas.admin import ClassificationOverride

router = APIRouter(prefix="/admin/regulations", tags=["admin"])

@router.post("/{reg_id}/classification")
async def override_classification(
    reg_id: str,
    payload: ClassificationOverride,
    user = Depends(require_role("admin", "annotator")),
    session = Depends(get_session),
):
    reg = await session.get_regulation(reg_id)
    if reg is None:
        raise HTTPException(404)
    await session.upsert_classification(
        regulation_id=reg_id,
        category=payload.category,
        confidence=1.0,
        source="manual",
        reviewed_by=user.user_id,
    )
    await write_audit(
        session, event_type="m1.classification.override",
        actor_user_id=user.user_id, target_table="regulation_classifications",
        target_id=reg_id, payload={"category": payload.category, "reason": payload.reason},
    )
    await session.commit()
    return {"ok": True}
```

The endpoint is intentionally thin: it writes one row to `regulation_classifications`, one row to `audit_log`, and commits in the same transaction so a partial state (override without audit) is impossible.

---

## 4. M4 Post Label Correction (`/admin/posts`)

The annotator queue surfaces the **disagreement set** identified by the kappa job in BUILD_10 §7. The UI offers single-record correction and bulk re-label with a mandatory free-text reason.

```tsx
// FILE: frontend/app/(admin)/posts/page.tsx
import { fetchPostQueue, fetchKappa } from "@/lib/api/admin";
import { KappaCard } from "@/components/admin/kappa-card";
import { PostQueue } from "@/components/admin/post-queue";

export default async function PostsReview() {
  const [queue, kappa] = await Promise.all([fetchPostQueue(), fetchKappa()]);
  return (
    <section className="p-6 space-y-6">
      <KappaCard kappa={kappa} />
      <PostQueue items={queue} />
    </section>
  );
}
```

```python
# FILE: backend/app/api/v1/admin/posts.py
from fastapi import APIRouter, Depends
from app.api.deps import require_role, get_session
from app.services.audit import write_audit
from app.schemas.admin import BulkLabel

router = APIRouter(prefix="/admin/posts", tags=["admin"])

@router.post("/bulk-label")
async def bulk_label(
    payload: BulkLabel,
    user = Depends(require_role("admin", "annotator")),
    session = Depends(get_session),
):
    if not payload.reason or len(payload.reason) < 10:
        return {"ok": False, "error": "reason_required"}
    for post_id in payload.post_ids:
        await session.upsert_post_label(
            post_id=post_id, label=payload.label, labeler_id=user.user_id,
        )
        await write_audit(
            session, event_type="m4.label.bulk",
            actor_user_id=user.user_id, target_table="m4_labeled_posts",
            target_id=post_id, payload={"label": payload.label, "reason": payload.reason},
        )
    await session.commit()
    return {"ok": True, "count": len(payload.post_ids)}
```

Cohen's kappa is recomputed nightly by the BUILD_11 training pipeline; the dashboard reads the most recent value rather than computing on every page load.

---

## 5. M3 Prediction Audit (`/admin/predictions`)

Each row shows the input features, the model's predicted compliance class, and the **top-five SHAP contributions** (from BUILD_09 §6). The override form writes to `m3_predictions.override_label` and creates an audit row; the BUILD_09 inference path already prefers `override_label` when reading back predictions.

```tsx
// FILE: frontend/app/(admin)/predictions/[id]/page.tsx
import { fetchPrediction } from "@/lib/api/admin";
import { ShapBars } from "@/components/admin/shap-bars";
import { OverrideForm } from "@/components/admin/override-form";

export default async function PredictionDetail({ params }: { params: { id: string } }) {
  const p = await fetchPrediction(params.id);
  return (
    <article className="p-6 space-y-4">
      <header>
        <h1 className="text-xl font-semibold">Prediction {p.id}</h1>
        <p className="text-sm text-gray-600">SME {p.sme_id} · model {p.model_version}</p>
      </header>
      <ShapBars contributions={p.shap_top5} />
      <OverrideForm predictionId={p.id} current={p.predicted_label} />
    </article>
  );
}
```

```python
# FILE: backend/app/api/v1/admin/predictions.py
from fastapi import APIRouter, Depends
from app.api.deps import require_role, get_session
from app.services.audit import write_audit
from app.schemas.admin import PredictionOverride

router = APIRouter(prefix="/admin/predictions", tags=["admin"])

@router.post("/{pred_id}/override")
async def override_prediction(
    pred_id: str, payload: PredictionOverride,
    user = Depends(require_role("admin", "chartered_accountant")),
    session = Depends(get_session),
):
    await session.set_prediction_override(pred_id, payload.label, user.user_id)
    await write_audit(
        session, event_type="m3.prediction.override",
        actor_user_id=user.user_id, target_table="m3_predictions",
        target_id=pred_id, payload={"override_label": payload.label, "reason": payload.reason},
    )
    await session.commit()
    return {"ok": True}
```

A non-admin chartered accountant is allowed here because compliance overrides are a CA judgement; this mirrors BUILD_06's `require_role("admin", "chartered_accountant")` composition.

---

## 6. M2 Question-Bank Editor (`/admin/questions`)

Questions are versioned with semver (`MAJOR.MINOR.PATCH`). A **draft** version can be created by any annotator; **promotion** to `published` requires a chartered accountant to sign off, populating `verified_by`, `verified_at`, and a SHA-256 `signature_hash` over the question body.

```python
# FILE: backend/app/api/v1/admin/questions.py
from fastapi import APIRouter, Depends, HTTPException
import hashlib, json
from datetime import datetime, timezone
from app.api.deps import require_role, get_session
from app.services.audit import write_audit
from app.schemas.admin import PromoteVersion

router = APIRouter(prefix="/admin/questions", tags=["admin"])

@router.post("/{qid}/versions/{version}/promote")
async def promote_version(
    qid: str, version: str, payload: PromoteVersion,
    user = Depends(require_role("chartered_accountant", "admin")),
    session = Depends(get_session),
):
    if user.role != "chartered_accountant" and not payload.delegated_ca_id:
        raise HTTPException(403, "ca_signoff_required")
    v = await session.get_question_version(qid, version)
    if v is None:
        raise HTTPException(404)
    body_hash = hashlib.sha256(json.dumps(v.body, sort_keys=True).encode()).hexdigest()
    await session.promote_question_version(
        qid=qid, version=version,
        verified_by=payload.delegated_ca_id or user.user_id,
        verified_at=datetime.now(timezone.utc),
        signature_hash=body_hash,
    )
    await write_audit(
        session, event_type="m2.question.promote",
        actor_user_id=user.user_id, target_table="qna_question_versions",
        target_id=f"{qid}:{version}", payload={"signature_hash": body_hash},
    )
    await session.commit()
    return {"ok": True, "signature_hash": body_hash}
```

```tsx
// FILE: frontend/app/(admin)/questions/[id]/page.tsx
import { fetchQuestion, fetchVersions } from "@/lib/api/admin";
import { VersionTimeline } from "@/components/admin/version-timeline";

export default async function QuestionEditor({ params }: { params: { id: string } }) {
  const [q, versions] = await Promise.all([
    fetchQuestion(params.id),
    fetchVersions(params.id),
  ]);
  return (
    <section className="p-6 space-y-4">
      <h1 className="text-xl font-semibold">{q.title}</h1>
      <VersionTimeline questionId={q.id} versions={versions} />
    </section>
  );
}
```

The `published` flag on `qna_question_versions` is **never** set without a non-null `verified_by` whose role at write time was `chartered_accountant`; this is enforced by a `CHECK` constraint plus a row-level trigger that resolves the role from `users` at INSERT time (see BUILD_05 §11).

---

## 7. Label Studio Bridge

Label Studio runs as a sidecar container reachable at `LABEL_STUDIO_URL`. Three flows connect it to Enigmatrix:

1. **Project sync (push):** a periodic job ships unlabeled examples from `m4_labeled_posts` (where `label IS NULL`) into a Label Studio project as JSON tasks.
2. **Webhook (pull):** Label Studio posts to `/api/v1/integrations/label-studio/webhook` whenever an annotator submits an annotation. Requests are HMAC-signed with `LABEL_STUDIO_WEBHOOK_SECRET`.
3. **Backfill import:** an offline script imports a JSON export from Label Studio into `labeled_examples` / `m4_labeled_posts`, idempotent by `content_hash`.

```python
# FILE: backend/app/integrations/label_studio.py
import hmac, hashlib, json
from fastapi import APIRouter, Header, HTTPException, Request, Depends
from app.api.deps import get_session
from app.core.config import settings
from app.services.audit import write_audit

router = APIRouter(prefix="/integrations/label-studio", tags=["label-studio"])

def _verify(sig: str, body: bytes) -> bool:
    mac = hmac.new(settings.LS_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, sig or "")

@router.post("/webhook")
async def webhook(
    request: Request,
    x_signature: str = Header(default=""),
    session = Depends(get_session),
):
    body = await request.body()
    if not _verify(x_signature, body):
        raise HTTPException(401, "bad_signature")
    payload = json.loads(body)
    if payload.get("action") != "ANNOTATION_CREATED":
        return {"ignored": True}
    task = payload["task"]; ann = payload["annotation"]
    post_id = task["data"]["post_id"]
    label = ann["result"][0]["value"]["choices"][0]
    await session.upsert_post_label(
        post_id=post_id, label=label, labeler_id=ann["completed_by"]["email"],
    )
    await write_audit(
        session, event_type="m4.label.via_label_studio",
        actor_user_id=ann["completed_by"]["email"], target_table="m4_labeled_posts",
        target_id=post_id, payload={"ls_annotation_id": ann["id"], "label": label},
    )
    await session.commit()
    return {"ok": True}
```

```python
# FILE: backend/scripts/ls_sync_push.py
import asyncio, httpx
from app.db.session import session_scope
from app.core.config import settings

LS_PROJECT_ID = settings.LS_PROJECT_ID_M4

async def main():
    async with session_scope() as s, httpx.AsyncClient() as c:
        rows = await s.fetch_unlabeled_posts(limit=500)
        tasks = [{"data": {"post_id": r.id, "text": r.body, "lang": r.lang}} for r in rows]
        r = await c.post(
            f"{settings.LS_URL}/api/projects/{LS_PROJECT_ID}/import",
            headers={"Authorization": f"Token {settings.LS_TOKEN}"},
            json=tasks,
        )
        r.raise_for_status()

if __name__ == "__main__":
    asyncio.run(main())
```

The webhook secret rotates on the same cadence as JWT signing keys (BUILD_06 §9). A failed signature returns 401 and is logged at WARN; three failures within five minutes from the same source IP trip a Prometheus alert.

---

## 8. Audit Log (extending `audit_log` from BUILD_04)

BUILD_04's `audit_log` originally captured only M3 evidence references. This build extends it so every override across all four modules lands in the same table, then enforces immutability with a Postgres trigger.

```python
# FILE: backend/migrations/versions/20260201_audit_immutable.py
"""extend audit_log and forbid UPDATE/DELETE"""
from alembic import op
import sqlalchemy as sa

revision = "20260201_audit_immutable"
down_revision = "20260115_m3_overrides"

def upgrade():
    op.add_column("audit_log", sa.Column("event_type", sa.Text, nullable=False, server_default="legacy"))
    op.add_column("audit_log", sa.Column("target_table", sa.Text, nullable=True))
    op.add_column("audit_log", sa.Column("target_id", sa.Text, nullable=True))
    op.add_column("audit_log", sa.Column("payload_json", sa.JSON, nullable=True))
    op.create_index("ix_audit_event_type", "audit_log", ["event_type"])
    op.execute("""
    CREATE OR REPLACE FUNCTION audit_log_immutable() RETURNS trigger AS $$
    BEGIN
      RAISE EXCEPTION 'audit_log is append-only (op=%)', TG_OP;
    END $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    CREATE TRIGGER trg_audit_log_no_update BEFORE UPDATE ON audit_log
      FOR EACH ROW EXECUTE FUNCTION audit_log_immutable();
    """)
    op.execute("""
    CREATE TRIGGER trg_audit_log_no_delete BEFORE DELETE ON audit_log
      FOR EACH ROW EXECUTE FUNCTION audit_log_immutable();
    """)

def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trg_audit_log_no_update ON audit_log;")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_log_no_delete ON audit_log;")
    op.drop_index("ix_audit_event_type", table_name="audit_log")
    op.drop_column("audit_log", "payload_json")
    op.drop_column("audit_log", "target_id")
    op.drop_column("audit_log", "target_table")
    op.drop_column("audit_log", "event_type")
```

```python
# FILE: backend/app/services/audit.py
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import insert
from app.db.models import AuditLog

async def write_audit(
    session, *, event_type: str, actor_user_id: str,
    target_table: str, target_id: str, payload: dict[str, Any],
) -> None:
    stmt = insert(AuditLog).values(
        event_type=event_type, actor_user_id=actor_user_id,
        target_table=target_table, target_id=target_id,
        payload_json=payload, occurred_at=datetime.now(timezone.utc),
    )
    await session.execute(stmt)
```

The trigger raises on any UPDATE or DELETE, so application code that tries to "fix" an audit row will receive a `raise_application_error`-style exception. The only sanctioned remediation is a **new** audit row with `event_type="audit.correction"` referencing the original `event_id` in `payload_json`.

---

## 9. Bulk CSV Import / Export

Bulk operations exist for two surfaces: the M2 question bank (CA-curated content) and labeled examples for M1/M4 (training data). Both are idempotent by `content_hash` — re-uploading the same CSV produces zero new rows.

```python
# FILE: backend/app/admin/bulk.py
import csv, hashlib, io
from fastapi import APIRouter, Depends, UploadFile
from app.api.deps import require_role, get_session
from app.services.audit import write_audit

router = APIRouter(prefix="/admin/bulk", tags=["admin"])

def _hash(row: dict) -> str:
    return hashlib.sha256(repr(sorted(row.items())).encode()).hexdigest()

@router.post("/labeled-examples")
async def import_labeled_examples(
    file: UploadFile,
    user = Depends(require_role("admin", "annotator")),
    session = Depends(get_session),
):
    text = (await file.read()).decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    inserted = skipped = 0
    for row in reader:
        h = _hash(row)
        if await session.labeled_example_exists(h):
            skipped += 1
            continue
        await session.insert_labeled_example(content_hash=h, **row)
        inserted += 1
    await write_audit(
        session, event_type="bulk.labeled_examples.import",
        actor_user_id=user.user_id, target_table="labeled_examples",
        target_id=file.filename, payload={"inserted": inserted, "skipped": skipped},
    )
    await session.commit()
    return {"inserted": inserted, "skipped": skipped}
```

Export endpoints stream CSV with `StreamingResponse` and an `attachment` content-disposition; they do not write to `audit_log` because reads of admin data are already captured by the access-log layer in BUILD_06 §12.

---

## Acceptance Criteria

1. A user with role `admin` (or `superadmin`) can load every page under `/admin/...`; a user with role `sme_user` is redirected to `/forbidden` by the layout, and never sees admin HTML.
2. An `annotator` can reach `/admin/regulations`, `/admin/posts`, and `/admin/questions` (draft only) but is rejected by `require_role` on the M3 override endpoint.
3. Every successful override on M1 classifications, M4 post labels, and M3 predictions writes exactly one row to `audit_log` in the same transaction as the data mutation; aborting the transaction rolls back both.
4. The Label Studio webhook rejects any request whose `X-Signature` HMAC does not match `LABEL_STUDIO_WEBHOOK_SECRET`, returning HTTP 401 and emitting a structured log line.
5. Promoting a question-bank version to `published` requires a non-null `verified_by` whose user role is `chartered_accountant`; the request is rejected with `ca_signoff_required` otherwise, and the `signature_hash` column is the SHA-256 of the canonical-JSON body.
6. Re-uploading the same labeled-examples CSV twice yields zero additional rows in `labeled_examples` (idempotency by `content_hash`); the audit row from the second upload reports `inserted=0`.
7. Direct `UPDATE` or `DELETE` against `audit_log` from a psql session raises `audit_log is append-only`; only INSERT succeeds.
8. Cohen's kappa surfaced on `/admin/posts` matches the most recent value written by the BUILD_11 training pipeline, and is stamped with the computation timestamp so stale values are visible.
9. A failed Label Studio annotation import (malformed payload, unknown `post_id`) is logged and audited as `m4.label.via_label_studio.failed`, never silently dropped.

---

## Claude Prompts

**(a) Admin route group with role-gated middleware.**
> Generate the Next.js App Router route group `frontend/app/(admin)/` for the Enigmatrix admin console. Produce: (1) `layout.tsx` server component that calls `/api/v1/users/me` with the `access_token` cookie and redirects non-{admin, superadmin, annotator} users to `/forbidden`; (2) `frontend/middleware.ts` matching `/admin/:path*` that redirects unauthenticated users to `/login?next=...` but defers role checks to the layout; (3) the index page `(admin)/page.tsx` rendering tiles for `/admin/regulations`, `/admin/posts`, `/admin/predictions`, `/admin/questions`, `/admin/audit`. Use TypeScript, no `any`. Do not re-implement JWT decoding — `fetchMe(token)` is provided. Output one file per code block.

**(b) Label Studio webhook handler with HMAC verification + import.**
> Implement `backend/app/integrations/label_studio.py` for FastAPI. Provide a `POST /integrations/label-studio/webhook` route that (1) verifies the `X-Signature` header is `hmac.compare_digest`-equal to `HMAC-SHA256(LS_WEBHOOK_SECRET, raw_body)`, (2) handles only `action == "ANNOTATION_CREATED"`, (3) extracts `task.data.post_id` and the first choice in `annotation.result[0].value.choices`, (4) calls `session.upsert_post_label(...)` and `write_audit(...)` in the same async transaction. Return 401 on bad signature, 200 with `{"ok": true}` on success. Use SQLAlchemy 2.0 async style and Pydantic v2 schemas.

**(c) Audit-log Postgres trigger preventing UPDATE/DELETE.**
> Write an Alembic migration that (1) adds columns `event_type TEXT NOT NULL DEFAULT 'legacy'`, `target_table TEXT`, `target_id TEXT`, `payload_json JSONB` to the existing `audit_log` table from BUILD_04, (2) creates an index on `event_type`, (3) defines a PL/pgSQL function `audit_log_immutable()` that `RAISE EXCEPTION` on any operation, (4) attaches `BEFORE UPDATE` and `BEFORE DELETE` row-level triggers on `audit_log` invoking that function, and (5) supplies a complete `downgrade()` that drops the triggers, the function, the index, and the new columns in reverse order. Target Postgres 15+.

---

**Prev:** BUILD_12_Data_Ingestion_and_Scheduling.md  ·  **Next:** BUILD_14_Deployment_Cloud.md
