# Plan: Gazette pipeline idempotency / retry / reconcile + auto-copy plan files to vault

## Context

Two distinct gaps in the SME platform need closing:

**Stream A — Gazette pipeline UX & idempotency.** The `/admin/m1/pipeline/extraction` flow already has a date-range trigger, polling, and a status board, but operators have no way to:
- recover from per-PDF extraction failures without leaving the UI,
- re-run extraction or preprocessing on a PDF that already succeeded (e.g. after changing extractor code), or
- back-fill regulations from PDFs that ended up on disk but never got inserted into the DB (the missing reconciliation step).

The download is already idempotent (`pipelines.py:93-101` skips PDFs that exist on disk; DB inserts catch `IntegrityError`), so this work is purely about exposing the existing skip behaviour, adding the missing reverse direction (filesystem → DB), and giving each row three explicit actions.

**Stream B — Claude plan files don't reach the Obsidian vault.** Plans land at `C:\Users\Administrator\.claude\plans\*.md` and stay there. There is no `plans/` subfolder in `C:\sme\08-Findings-Log\` and no hook copies them across, so research/architecture decisions made during planning are invisible to the vault graph.

Outcome: operators can self-serve recovery for any one PDF, the raw/ folder and the DB stay reconciled automatically, and every approved plan is preserved alongside the findings log.

## Stream A — Backend changes

### New endpoints (all under `/api/v1/admin/m1/extraction/`)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/regulations/{regulation_id}/retry` | For rows in `extraction_failed`. Resets status → `ingested`, clears `raw_text` / `extraction_method` / `extracted_at`, enqueues `extract_gazette.delay(regulation_id)`. Returns 409 if status is anything other than `extraction_failed`. |
| `POST` | `/regulations/{regulation_id}/re-extract` | Force re-run from extract stage regardless of current status (`extracted`, `preprocessed`, `extraction_failed`). Resets status → `ingested`, enqueues `extract_gazette.delay()`. The full chain runs because `extract_gazette` already chains preprocess on success. |
| `POST` | `/regulations/{regulation_id}/re-preprocess` | Re-run preprocess only. Requires current status in (`extracted`, `preprocessed`). Resets status → `extracted`, clears `cleaned_text` / `amendment_type`, deletes child rows in `m1_regulation_penalties` and `m1_sub_documents`, enqueues `preprocess_gazette_task.delay()`. |
| `POST` | `/reconcile` | Walks `STORAGE_LOCAL_PATH/m1/raw/*.pdf`. For each PDF whose `gazette_number` (recovered by reversing the slug; e.g. `2468_44.pdf` → `2468/44`) is **not** in `m1_regulations`, insert a stub row (`status='ingested'`, `regulation_short_code='GZT_<slug>'`, `raw_pdf_path='m1/raw/<slug>.pdf'`, `title_en=f"Gazette {n} (reconciled)"`, `pdf_sha256` computed) and enqueue `extract_gazette.delay(regulation_id)`. Returns `{scanned, already_in_db, inserted, queued}`. |

All four endpoints follow the existing admin-auth + `MAdmin1Service` pattern in `app/api/v1/admin/m1_gazette_extraction.py`.

### New files / functions

- **`C:\Reasearch\xyz\enigmatrix-backend\app\tasks\m1\reconcile_raw.py`** — new Celery task `reconcile_raw_pdfs(self) -> dict[str, int]`. Reuses the slug-reverse helper that mirrors `scraper/pipelines.py:49` (`_SLUG_RE`); add it as a shared util in `app/services/m1_pipeline_service.py` so both pipelines and the task call the same function. The task reads the directory, queries the DB for existing `gazette_number`s in one `SELECT ... WHERE gazette_number IN (...)`, and inserts the missing ones in a single transaction, then `.delay()`s each new `regulation_id` to `extract_gazette`.
- **`C:\Reasearch\xyz\enigmatrix-backend\app\api\v1\admin\m1_gazette_extraction.py`** — add the four endpoints above. The retry/re-extract/re-preprocess handlers all share a small helper `_reset_and_enqueue(regulation_id, target_status, child_tables_to_clear, next_task)` that runs in a single SQLAlchemy `async with session.begin():` block.
- **Auto-reconcile inside trigger.** In `trigger_extraction` (currently `m1_gazette_extraction.py:56-81`), call `reconcile_raw_pdfs.delay()` immediately before `run_gazette_spider.delay(...)`. The two tasks are independent; reconcile picks up files dropped manually into `raw/`, the spider picks up new gazettes for the requested date range.

### Schema / model touches

- Add `last_error: Mapped[str | None]` and `last_error_at: Mapped[datetime | None]` to `M1Regulation` (`app/models/regulation.py`). Populate inside the `except` clauses of `extract_gazette.py` and `preprocess_gazette.py` (currently they just flip status to `extraction_failed`). New Alembic migration: `app/db/migrations/versions/<rev>_m1_regulation_last_error.py`.
- No status enum changes — existing values (`ingested`, `extracted`, `preprocessed`, `extraction_failed`) cover everything. Retry/re-extract/re-preprocess move status back along the existing chain.

### Tests

- `app/tests/api/v1/admin/test_m1_extraction_retry.py` — happy path + 409 on wrong status for each new endpoint.
- `app/tests/tasks/m1/test_reconcile_raw.py` — temp dir with a fake `2999_01.pdf`, assert insert + extract.delay called once; assert no duplicate insert if regulation already exists.
- `app/tests/api/v1/admin/test_m1_extraction_trigger.py` — extend existing test to assert `reconcile_raw_pdfs.delay()` is called by `trigger_extraction`.

## Stream A — Frontend changes

### New API client methods

In `C:\Reasearch\xyz\enigmatrix-frontend\lib\api\m1-gazette-extraction.ts`, extend `M1GazetteExtractionApi`:

```typescript
retry:        (token, regulationId) => api.post(`/api/v1/admin/m1/extraction/regulations/${regulationId}/retry`, {}, token),
reExtract:    (token, regulationId) => api.post(`/api/v1/admin/m1/extraction/regulations/${regulationId}/re-extract`, {}, token),
rePreprocess: (token, regulationId) => api.post(`/api/v1/admin/m1/extraction/regulations/${regulationId}/re-preprocess`, {}, token),
reconcile:    (token) => api.post<ReconcileResultOut>(`/api/v1/admin/m1/extraction/reconcile`, {}, token),
```

### New row actions in `RegulationProgressCard`

`C:\Reasearch\xyz\enigmatrix-frontend\components\m1-extraction\regulation-progress-card.tsx`:

- **Retry** — render only when `row.status === "extraction_failed"`. Calls `M1GazetteExtractionApi.retry`, shows `row.last_error` in a tooltip on hover. Variant: `default`.
- **Re-extract** — always rendered. Confirmation dialog ("This re-runs extract + preprocess. Existing cleaned_text and penalty rows will be cleared."). Variant: `outline`.
- **Re-preprocess** — rendered when `row.status in {"extracted", "preprocessed"}`. Confirmation dialog ("This clears `cleaned_text`, penalties, and sub-documents and re-runs preprocess only."). Variant: `outline`.

After each click invalidate the React-Query `progress` key so the row refreshes on the next 5 s tick.

### "Reconcile raw folder" button

On `C:\Reasearch\xyz\enigmatrix-frontend\app\(admin)\admin\m1\pipeline\extraction\page.tsx`, add a button next to the existing "Start extraction". Click → `M1GazetteExtractionApi.reconcile()` → toast with the result shape (`{scanned: N, already_in_db: N, inserted: N, queued: N}`). The trigger endpoint already auto-reconciles, so this button is for ad-hoc use without launching a spider crawl.

### Surface `last_error`

Extend `ExtractionRowStatus` to carry an optional `last_error: string | null` field (the GET `/progress` response already has the column once the backend migration lands). In the failed-row card, render the first 200 chars under the status badge with a "copy full" affordance.

## Stream B — Auto-copy plan files to the Obsidian vault

### Hook configuration

Edit `C:\Users\Administrator\.claude\settings.json` and add (merge with existing `hooks` key if present):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "ExitPlanMode",
        "hooks": [
          {
            "type": "command",
            "command": "powershell -NoProfile -ExecutionPolicy Bypass -File C:\\Users\\Administrator\\.claude\\scripts\\copy-plan-to-vault.ps1"
          }
        ]
      }
    ]
  }
}
```

### New script

**`C:\Users\Administrator\.claude\scripts\copy-plan-to-vault.ps1`** — does the copy. Logic:

```powershell
$ErrorActionPreference = 'Stop'
$plansDir = 'C:\Users\Administrator\.claude\plans'
$vaultDir = 'C:\sme\08-Findings-Log\plans'
New-Item -ItemType Directory -Path $vaultDir -Force | Out-Null
$src = Get-ChildItem $plansDir -Filter *.md -File |
       Sort-Object LastWriteTime -Descending |
       Select-Object -First 1
if ($null -eq $src) { exit 0 }
$date = (Get-Date).ToString('yyyy-MM-dd')
$dest = Join-Path $vaultDir ("${date}_" + $src.Name)
Copy-Item $src.FullName $dest -Force
# Log line in CHANGES-friendly format (one line, append to a sidecar log)
$logLine = "{0}  plan-copied  {1}" -f (Get-Date -Format 'yyyy-MM-ddTHH:mm:ssK'), $dest
Add-Content -Path (Join-Path $vaultDir '_plan-copies.log') -Value $logLine
```

Picking "most recent" rather than parsing tool input avoids depending on `ExitPlanMode`'s argument shape (it has none); the plan file is whichever was just written by `Write` in plan mode.

### Belt-and-suspenders documentation

Append a one-line entry to `C:\Users\Administrator\.claude\CLAUDE.md` so the behaviour is also discoverable to Claude reading its own instructions:

```markdown
# plan-vault sync
Approved plan files (created via ExitPlanMode) are auto-copied to `C:\sme\08-Findings-Log\plans\YYYY-MM-DD_<slug>.md` by the PostToolUse hook configured in `~/.claude/settings.json`. If the hook fails (e.g. on Linux/Mac), copy the plan manually after ExitPlanMode.
```

## Critical files

**Backend (new + modified):**
- `app/api/v1/admin/m1_gazette_extraction.py` — add 4 endpoints, wire auto-reconcile into trigger
- `app/tasks/m1/reconcile_raw.py` — new file
- `app/tasks/m1/extract_gazette.py:103-118` — populate `last_error` in except
- `app/tasks/m1/preprocess_gazette.py` — same as extract
- `app/models/regulation.py` — add `last_error` columns
- `app/db/migrations/versions/<rev>_m1_regulation_last_error.py` — new
- `app/services/m1_pipeline_service.py` — shared slug-reverse helper
- `scraper/pipelines.py:49` — reference (slug regex; do not duplicate, move to service)

**Frontend (new + modified):**
- `lib/api/m1-gazette-extraction.ts` — 4 new API methods
- `components/m1-extraction/regulation-progress-card.tsx` — 3 row buttons + last_error display
- `app/(admin)/admin/m1/pipeline/extraction/page.tsx` — "Reconcile raw folder" button + toast
- (no new components — reuse `Button`, `Dialog`, `Toast` from `components/ui/`)

**Vault sync (new):**
- `C:\Users\Administrator\.claude\settings.json` — add `PostToolUse[ExitPlanMode]` hook
- `C:\Users\Administrator\.claude\scripts\copy-plan-to-vault.ps1` — new script
- `C:\Users\Administrator\.claude\CLAUDE.md` — add `# plan-vault sync` section

## Reuse — existing code that should NOT be re-implemented

- `scraper/pipelines.py:93-101` — PDF disk-exists skip (call it from reconcile to compute sha256)
- `scraper/pipelines.py:49` `_SLUG_RE` — slug ↔ gazette number mapping (promote to shared service)
- `app/tasks/m1/extract_gazette.py:94-100` and `preprocess_gazette.py:87-94` — existing status-guarded skip is the model for the retry endpoints
- `app/services/m1_admin_service.py` (`MAdmin1Service`) — auth + service injection used by every admin endpoint
- `M1GazetteExtractionApi` client pattern in `lib/api/m1-gazette-extraction.ts:101-125` — copy verbatim for the 4 new methods
- `DateRangePicker`, `StatusBadge`, `Button`, `Dialog`, `Toast` — all already in `components/ui/`

## Verification

**Backend (run from `enigmatrix-backend/`):**
```
uv run pytest app/tests/api/v1/admin/test_m1_extraction_retry.py -v
uv run pytest app/tests/tasks/m1/test_reconcile_raw.py -v
uv run alembic upgrade head     # verify last_error migration applies clean
```

**End-to-end smoke (dev stack running):**
1. Drop `99_99.pdf` (any small PDF) into `enigmatrix-backend/storage/m1/raw/` manually.
2. Hit `POST /api/v1/admin/m1/extraction/reconcile` — response should report `inserted: 1, queued: 1`.
3. Within 30 s, `GET /api/v1/admin/m1/extraction/progress` should show the new row at status `extracted` then `preprocessed`.
4. Force a failure: monkeypatch the extractor to raise, drop another PDF, reconcile — row should land at `extraction_failed` with `last_error` populated.
5. From the frontend, click **Retry** on that row → row returns to `ingested` then `extracted`.
6. Click **Re-preprocess** on a succeeded row → child tables clear and repopulate; row returns to `preprocessed`.
7. Click **Reconcile raw folder** with no new PDFs → toast shows `inserted: 0`.

**Stream B verification:**
1. Restart Claude Code so the new hook loads.
2. In a throwaway conversation, plan something trivial and call `ExitPlanMode`.
3. Confirm a file appears at `C:\sme\08-Findings-Log\plans\YYYY-MM-DD_<slug>.md` matching the source.
4. Open `C:\sme\08-Findings-Log\plans\_plan-copies.log` and confirm one new line was appended.

## Post-run vault sync

After implementation, per the project convention:
- Append a Session entry to `C:\sme\08-Findings-Log\SESSIONS.md` (next session number) summarising the four endpoints, three frontend buttons, hook + script, with file lists under **Done** / **Files (this slice)**.
- Add one or two F-### rows to `C:\sme\08-Findings-Log\CHANGES.md` (one for the pipeline UX, one for the plan-vault sync).
- Add corresponding rows / flips to `C:\sme\08-Findings-Log\FEATURES.md`.
- Run `/graphify --update` on both `C:\Reasearch\xyz\graphify-out\` (code) and `C:\sme\graphify-out\` (vault).
