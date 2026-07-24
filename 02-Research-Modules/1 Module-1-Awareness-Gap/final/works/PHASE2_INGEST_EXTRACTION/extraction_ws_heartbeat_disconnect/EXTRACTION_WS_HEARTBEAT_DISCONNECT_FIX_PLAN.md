# Phase 2 · Extraction — Live-Feed WS Heartbeat Crash on Disconnect: Fix Plan

> Group: `PHASE2_INGEST_EXTRACTION / extraction_ws_heartbeat_disconnect`.
> **Status: implemented (2026-07-23).** Root-cause fix for the `Task exception was never retrieved` noise on the extraction live-feed WebSocket, plus a prompt disconnect watcher so a closed tab tears down cleanly.

## 1. Symptom

Watching an extraction run and then closing/navigating away logs a full traceback in the backend:

```
Task exception was never retrieved
future: <Task ... coro=<_heartbeat() done, defined at ...\extraction_ws.py:154> exception=WebSocketDisconnect()>
...
websockets.exceptions.ConnectionClosedOK: received 1005 (no status received [internal])
uvicorn.protocols.utils.ClientDisconnected
...
starlette.websockets.WebSocketDisconnect
  File "...\extraction_ws.py", line 158, in _heartbeat
    await ws.send_text(json.dumps({"type": "ping"}))
```

Not fatal — the request is already over — but it's alarming log noise on a normal user action, and it points at a real lifecycle gap.

## 2. Root cause (two linked defects)

**File:** `enigmatrix-backend/app/m1/api/extraction_ws.py`.

1. **Unguarded sends in the loop tasks.** `_heartbeat` (and `_pump_pubsub`, and the `done` send in `_celery_terminal_watcher`) call `ws.send_text(...)` with no guard. When the browser has gone, Starlette raises `WebSocketDisconnect` (or `RuntimeError` for a send after close) straight out of the coroutine.
2. **Finished-task exceptions were never consumed.** The handler multiplexes the loop tasks with `asyncio.wait(..., FIRST_COMPLETED)`, then cancels only the `pending` set — it never calls `.result()`/`.exception()` on the `done` set. So the task that ended by *raising* is garbage-collected with its exception unretrieved, which is exactly what asyncio's `Task exception was never retrieved` warns about.

Compounding both: none of the three original loops *reads* from the socket, so a client-initiated close was only ever noticed on the next outbound send (up to 25 s later at the heartbeat), and when noticed it surfaced as a crash rather than a clean teardown.

## 3. The fix (code)

- **Shared "client gone" tuple:** `_CLIENT_GONE = (WebSocketDisconnect, RuntimeError)` — the two ways a send/receive signals the browser has left.
- **New `_wait_for_disconnect(ws)` loop** added to the multiplex set. It awaits `ws.receive()` and returns on `WebSocketDisconnect`, so a closed tab is detected *promptly* instead of at the next heartbeat. Inbound frames are ignored.
- **Guarded every send** in `_heartbeat`, `_pump_pubsub`, and the `done` frame in `_celery_terminal_watcher` with `except _CLIENT_GONE: return` — a send racing a disconnect ends that loop quietly.
- **Drain the `done` set:** after `asyncio.wait`, iterate finished tasks and call `.exception()`; a `_CLIENT_GONE` error is expected and swallowed, anything else is logged. This is what actually silences the "never retrieved" warning.

Net shape: four loops (pubsub pump · 25 s heartbeat · Celery terminal watcher · disconnect watcher), first to finish tears the rest down; the `finally` block still unsubscribes, closes pubsub/redis, and closes the socket.

## 4. Why this is the right shape

The endpoint is explicitly best-effort (degrades to polling if Redis is down). A user closing the tab is the *normal* end of its life, not an error — so the disconnect path must be a clean return, not an exception that escapes into asyncio's GC. Guarding the sends handles the race; the dedicated receive loop makes detection immediate; draining `done` closes the last hole where an unexpected error could still go unlogged. No behavioural change for the happy path (live sub-step frames + heartbeats still flow identically).

## 5. Docs updated

- `enigmatrix-docs/m1/final/04_API_AND_PAGES_REFERENCE.md` — corrected the WS path (`/ws/extraction/{task_id}` → `/ws/m1/extraction/{task_id}`) and documented the four-loop / prompt-disconnect behaviour.
- `AI_WORK_LOG.md` — session entry.

## 6. Verification (deferred to user — sandbox VHDX still down)

1. `python -m compileall enigmatrix-backend/app/m1/api/extraction_ws.py` (syntax).
2. Start the backend, open an extraction run in the admin UI, confirm live sub-step frames + `{"type":"ping"}` heartbeats still arrive.
3. Close the tab mid-run. Backend log should show `ws/m1/extraction: client disconnected task_id=...` and **no** `Task exception was never retrieved` traceback.
4. Let a run reach a terminal Celery state with the tab open — confirm the `{"type":"done", terminal:true}` frame still fires and the socket closes 1000.
5. `pytest` (WS/pipeline suites).
6. `graphify update .`.
