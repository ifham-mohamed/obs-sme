# Phase 2 · Extraction — Deep-Linkable Run Page + Real-Time Stage Counts: Plan

> Group: `PHASE2_INGEST_EXTRACTION / extraction_run_page_realtime`. Related: [[EXTRACTION_WS_HEARTBEAT_DISCONNECT_FIX_PLAN]] (the WS this rides on).
> **Status: implemented (2026-07-23), verification deferred (sandbox VHDX down).** Two operator asks: (1) starting a crawl should open the run on its own full page keyed by task_id, and (2) the per-stage counts (ingested / extracting / preprocessing) should update in real time, not on a 5 s poll.

## 1. What was happening

- The live extraction UI is `/admin/m1/pipeline/sources/[sourceId]/extraction`. After you hit **Start extraction**, the progress cards render **inline on that same page**; nothing is keyed by task_id in the URL, so a refresh loses the view and you can't share/deep-link a run.
- The aggregate counts (`in_scope / ingested / extracted / preprocessed / extraction_failed`) came only from **5 s polling** of `/extraction/summary` + `/extraction/progress`. The WebSocket (`/ws/m1/extraction/{task_id}`) only carried the single "currently working on X" **substep** line — it never moved the tallies. So the numbers felt laggy and it wasn't obvious that extraction runs many PDFs concurrently.

## 2. Design decisions (confirmed with the operator)

1. **Page delivery:** new **deep-linkable route** opened in a **new browser tab** — `…/sources/[sourceId]/extraction/runs/[taskId]`. task_id lives in the URL (refresh-survivable, shareable).
2. **Real-time:** **WebSocket push + poll fallback.** Backend now publishes coarse per-regulation **stage** frames at each boundary; the frontend uses any frame as a "poke" to refetch the authoritative counts immediately. Polling stays on (faster, 2.5 s) purely as fallback/reconciler.

Why "poke → refetch" rather than pushing full counts from the worker: a worker only knows its *own* regulation, not the run's date-range totals. Computing scoped totals inside every task is race-prone and duplicates the `/summary` query that already exists and is correct. Pushing a 1-line stage event and letting the client refetch the authoritative snapshot gives real-time feel with zero risk of drift.

## 3. Backend changes

**`app/m1/services/extraction_live_feed.py`** — new `publish_stage(source_id, regulation_id, stage, display=None)`. Publishes `{"type":"stage","regulation_id":…,"stage":…,"display":…}` on the existing `source:<id>` channel (plus `reg:<id>`). Best-effort via the existing `publish` (swallows Redis errors). **No WS-endpoint change needed** — the endpoint already pumps every frame on that channel straight through.

**`app/m1/tasks/extract_gazette.py`** — emit `publish_stage(...)` at each terminal boundary already in the body: `"extracted"` after the success commit; `"extraction_failed"` in the no-URL branch, the PDF-load failure branch, and the extraction-exception branch. `source_id` + `display` are already resolved at the top of the body for the substep feed, so this reuses them.

**`app/m1/tasks/preprocess_gazette.py`** — load `gazette_item` in the row query (for `source_id` + `document_number`) and emit `publish_stage(..., "preprocessed", …)` after the success commit.

Result: ingested→extracted→preprocessed→(failed) each fire exactly one lightweight frame. Ingest itself is emitted by the scrapy insert pipeline in a **follow-up** (see §6) — for now the ingest count still advances on the fallback poll, which is fine because ingest is the fast phase.

## 4. Frontend changes

**`lib/hooks/useExtractionLiveFeed.ts`** — added a `"stage"` frame type (`LiveStage`) and an **optional** third arg `onFrame?(frame)` invoked for every non-ping frame. Kept in a ref so a changing callback identity doesn't re-dial the socket. Existing 2-arg callers (the inline page) are unchanged; the returned value is still `LiveSubStep | null`.

**`app/(admin)/admin/m1/pipeline/sources/[sourceId]/extraction/runs/[taskId]/page.tsx`** (new) — full run page:
- Reconstructs the run's scope from `listRuns({sourceId, includeArchived})` keyed by `task_id` (the URL carries only source + task; date_from/date_to/queued_at come from the run row). Polls until the just-created row appears; shows a "run not found" card for a bad/deleted id.
- Reuses `PipelineRunStatusCard`, `MissingGazettesPanel`, `ExtractionSummaryCard`, `ExtractionProgressPanel` — no new progress UI to maintain.
- `getStatus` poll (3 s until terminal) for Celery state; `getSummary` fast poll (2.5 s, stops when settled) for counts.
- `useExtractionLiveFeed(taskId, token, onFrame)` where `onFrame` debounces (400 ms) then invalidates the `m1-extraction-summary` + `m1-extraction-progress` query prefixes → counts + rows refetch within ~1 s of any pipeline advance; polling is the fallback.

**`…/extraction/page.tsx`** — on trigger success, `window.open(runUrl, "_blank", "noopener,noreferrer")` and updated the toast ("opened its live page in a new tab"). The inline cards stay as a same-tab fallback.

## 5. Docs updated

- `enigmatrix-docs/m1/final/04_API_AND_PAGES_REFERENCE.md` — new run route + the `stage` WS frame.
- `AI_WORK_LOG.md` — session entry.

## 6. Verification & follow-ups (deferred — sandbox VHDX down)

1. `python -m compileall enigmatrix-backend/app/m1/services/extraction_live_feed.py enigmatrix-backend/app/m1/tasks/extract_gazette.py enigmatrix-backend/app/m1/tasks/preprocess_gazette.py`.
2. Frontend: `pnpm -C enigmatrix-frontend tsc --noEmit` (typecheck) + `pnpm -C enigmatrix-frontend build`.
3. Manual: start a crawl → a new tab opens at `…/runs/<taskId>`; confirm counts climb ingested→extracted→preprocessed live (watch several advance concurrently) and the "currently working on X" line moves. Kill Redis mid-run → counts keep advancing on the 2.5 s poll (fallback proven). Refresh the run tab → state restored from the URL.
4. Deep-link a bad task id → "run not found" card.
5. `pytest` (extract/preprocess task suites — assert `publish_stage` is called; monkeypatch as the substep tests do).
6. **Follow-up:** emit `publish_stage(source_id, regulation_id, "ingested", …)` from the scrapy insert pipeline (`scraper/pipelines.py`, right after the `INSERTED … status=ingested` dispatch) so the ingest tally is WS-driven too. Low priority — ingest is fast and already reflected by the poll.
7. `graphify update .`.
