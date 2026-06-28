# Plan: Completeness verify endpoint hardening — timeout, CORS, WS URL, state reset

## Context

The verify-completeness feature shipped in the previous session worked in principle but hit a cascade of operational issues during integration:

1. **404 on first click** — frontend client URLs missed the `/api/v1` prefix.
2. **`httpx.ReadTimeout`** — documents.gov.lk's listing body trickled in over 60-90s; the bare `_HTTP_TIMEOUT_S = 30.0` budget wasn't enough.
3. **500 without CORS headers** — unhandled exceptions bubbled past Starlette's `ServerErrorMiddleware` (which sits above CORS middleware in the stack); the resulting 500 had no `Access-Control-Allow-Origin` header so the browser blocked it.
4. **WebSocket dialling the frontend** — `useExtractionLiveFeed.ts` built `ws://window.location.host/...` which resolves to the Next.js dev port (3000); backend is on 8000.
5. **WebSocket reconnect storm** — after a terminal task the server's `done` frame closed the connection, and the client's `onclose` exponentially reconnected every ~7 seconds, each attempt re-running the DB query that resolved the task → source mapping.
6. **`AttributeError: 'URL' object has no attribute 'human_repr'`** — installed `httpx` predates 0.27 where `URL.human_repr()` was added.
7. **Stale panel state on task switch** — switching to a different historical run kept the previous run's "No gaps detected" banner until the new verify finished.

## Goal

Take the feature from "works on the happy path" to "robust under real-world slow upstreams, errors, network blips, and user navigation".

## Scope

- **In:** `lib/api/m1-completeness.ts`, `app/services/m1_completeness_check.py`, `app/api/v1/m1_completeness.py`, `lib/hooks/useExtractionLiveFeed.ts`, `app/api/v1/m1_extraction_ws.py`, `components/m1-extraction/missing-gazettes-panel.tsx`.
- **Out:** Per-task_id WS channel routing.

## Steps

1. **`/api/v1` prefix** — `lib/api/m1-completeness.ts` `Edit replace_all`: `/admin/m1/extraction/` → `/api/v1/admin/m1/extraction/` (3 occurrences). Matches the existing client convention.
2. **httpx timeout per-leg + retry** — `m1_completeness_check.py`:
   ```python
   _HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)
   _HTTP_RETRY_ATTEMPTS = 2
   for attempt in range(1, _HTTP_RETRY_ATTEMPTS + 1):
       try:
           async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, ...) as client:
               resp = await client.get(url); resp.raise_for_status(); break
       except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.PoolTimeout):
           if attempt >= _HTTP_RETRY_ATTEMPTS: raise
   ```
3. **API-edge timeout mapping** — `_run_verify` in `m1_completeness.py`:
   - `except httpx.TimeoutException` → `HTTPException(504, "The source website (documents.gov.lk) didn't respond in time...")`.
   - `except httpx.HTTPError` → `HTTPException(502, "The source website returned an error...")`.
   - `except HTTPException: raise` (let already-structured ones through).
   - `except Exception as exc:` → catch-all → `HTTPException(500, detail=f"Verification failed: {type(exc).__name__}: {first_line[:240]}")` plus `logger.exception(...)`. Keeps response inside FastAPI's exception handler so CORS middleware can add headers on the way out.
4. **WebSocket URL** — `useExtractionLiveFeed.ts` `getWebSocketUrl`:
   ```ts
   const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
   const wsBase = apiBase.replace(/^http/i, "ws");
   return `${wsBase}/api/v1/ws/m1/extraction/${taskId}?token=${encodeURIComponent(token)}`;
   ```
5. **WS terminal flag + clean close** — `m1_extraction_ws.py` `_celery_terminal_watcher`:
   ```python
   await ws.send_text(json.dumps({"type": "done", "celery_status": state, "terminal": True}))
   await asyncio.sleep(3.0)
   await ws.close(code=1000, reason="task terminal")
   ```
6. **WS client stops reconnecting on terminal** — `useExtractionLiveFeed.ts`:
   - `ServerFrame` done branch typed `{ type: "done"; terminal?: boolean; celery_status?: string }`.
   - `onmessage`: if `frame.terminal`, flip `cancelledRef.current = true`.
   - `onclose`: if `event.code === 1000`, flip `cancelledRef.current = true` and bail.
7. **`human_repr` → `str(...)`** — `m1_completeness_check.py`: `resp.url.human_repr()` → `str(resp.url)` at both call sites (lines 192, 193).
8. **Panel state reset on task switch** — `missing-gazettes-panel.tsx`: add `useEffect(() => { setResult(null); setRefetchResult(null); setAutoRan(false); }, [taskId])` BEFORE the auto-trigger effect.

## Decisions taken

- `httpx.TimeoutException` → 504 surfaces upstream slowness distinctly from 5xx coming from this app.
- `_HTTP_RETRY_ATTEMPTS = 2` (one retry total) is enough to ride out a single bursty failure without piling on a struggling upstream.
- Belt-and-braces for WS termination: server sends `terminal: true` AND uses close code 1000; client honours either signal independently.
- `str(resp.url)` works on every httpx version; `human_repr()` is httpx ≥ 0.27 only.
- Panel state reset placed before the auto-trigger effect so `autoRan = false` is observable when `autoVerifyTrigger` fires for the new task.

## Open questions / risks

- The error message capping at 240 chars is generous but could still expose internal paths in some error messages. Acceptable since admin-only.
- Removing the WS reconnect on code 1000 means a genuinely-terminal task never re-establishes; future fix is to short-circuit the connection in the hook when the parent says the task is terminal.

## Acceptance criteria

- Verify button on a slow upstream completes within ~120s + retry, returns either a successful result or a clean 504 with CORS headers.
- WebSocket connects once per page load on a terminal task; closes cleanly with code 1000; client stops trying.
- Switching between historical runs shows fresh panel state immediately; auto-verify fires once for each new task.
- Unexpected exceptions surface as `Verification failed: <ExceptionClass>: <message>` in the panel instead of forcing log-diving.

## Linked trackers

- [CHANGES.md](../CHANGES.md)
- [FEATURES.md](../FEATURES.md) — F-178 (hardening pass tied to the F-177 feature)
- [SESSIONS.md](../SESSIONS.md) — Session 51
