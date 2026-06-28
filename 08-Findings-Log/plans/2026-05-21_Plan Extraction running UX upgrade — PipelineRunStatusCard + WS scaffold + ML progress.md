# Plan: Extraction running UX upgrade — PipelineRunStatusCard + WS sub-step scaffold + ML progress emission

## Context

User reported the source extraction page (`/admin/m1/pipeline/sources/EGZ/extraction`) said "Completed SUCCESS" while 2 rows were still at `ingested` and 154 had not yet been preprocessed. The page derived its top-line status purely from the Celery spider task's state — once the spider returned `SUCCESS`, the banner flipped even though the downstream `extract_gazette` → `preprocess_gazette` Celery chain was still working.

User asked for a true end-to-end pipeline status, per-step progress, and per-PDF sub-step detail. Confirmed via planning questions: all three detail levels, WebSocket as the live transport, end-to-end completion semantics, work across frontend + backend + ML.

## Goal

Replace the misleading Celery-only banner with a phase-aware status card driven by `status_counts` + Celery state. Scaffold a per-PDF sub-step WebSocket channel from ML emission → Celery `update_state` + Redis pub/sub → FastAPI WS → frontend hook.

## Scope

- **In:** New components, hook, WS endpoint, Redis pub/sub publisher, ML progress module, Celery task emit hooks.
- **Out:** Per-task_id WS channel routing (uses source_id pub/sub channel as a pragmatic scaffold).

## Steps

1. **Frontend** — Create `components/m1-extraction/pipeline-run-status-card.tsx`. Export `derivePipelinePhase(celeryStatus, counts) → "scraping" | "extracting" | "preprocessing" | "completed" | "partial" | "failed" | "cancelled"`. Three-phase tracker bars + live sub-step pill.
2. **Frontend** — Create `lib/hooks/useExtractionLiveFeed.ts`. WebSocket client with exponential backoff (1s → 30s). JSON frame decoder for `substep | ping | done`.
3. **Frontend** — Wire both into `app/(admin)/admin/m1/pipeline/sources/[sourceId]/extraction/page.tsx`. Replace single-line Celery banner with `<PipelineRunStatusCard>`. Keep cancel/traceback as a separate conditional card.
4. **ML** — Create `enigmatrix-ml/m1/extraction/progress.py`. Canonical `ExtractionPhase` literal (`classifying | extracting_text | ocr | language_detection | wijesekara | preprocessing | indexing`), `PHASE_LABELS` dict, dependency-free `emit(cb, ...)` helper. Re-export from package `__init__.py`.
5. **Backend** — Create `enigmatrix-backend/app/services/m1_extraction_live_feed.py`. Sync `redis-py` publisher reusing `CELERY_BROKER_URL`. `publish(key, event)` + `channel_for(key)` + `publish_done(task_id)`.
6. **Backend** — Modify `app/tasks/m1/extract_gazette.py`. Add `_emit(task_self, *, regulation_id, display, phase, source_id, fraction=None)` helper that calls `self.update_state(state="PROGRESS", meta=payload)` AND `publish_substep(...)` on both `reg:<regulation_id>` and `source:<source_id>` channels. Plumb `task_self` through `_extract_gazette_async` → `_extract_gazette_body`. Hook at three phase boundaries (`classifying`, extractor-specific `extracting_text`/`ocr`, `indexing`).
7. **Backend** — Create `app/api/v1/m1_extraction_ws.py`. FastAPI `@router.websocket("/extraction/{task_id}")` with token query-param auth via `decode_token(token, expected_kind="access")` from `app.core.security`. Resolve source via `m1_extraction_runs` row. Subscribe to source-scoped Redis pub/sub channel. Three concurrent loops (pubsub pump, 25s heartbeat, 2s Celery terminal watcher).
8. **Backend** — Register the new WS router in `app/api/v1/router.py`.

## Decisions taken

- Sub-step phase names defined in the ML package as the canonical surface; backend uses inline string constants mirroring the ML names rather than importing from ml-package (avoids workspace-install boot-order race).
- WS endpoint routes per source_id pub/sub channel as a pragmatic scaffold. Per-task_id routing requires plumbing the trigger task_id through the spider into every child `extract_gazette` call — a separate, larger refactor.
- Token auth via `?token=` query param because FastAPI WebSocket doesn't run HTTP dependencies.
- Live sub-step pill in the card is purely additive — the card derives its phase from poll-derived counts and degrades gracefully when the WS is unreachable.

## Open questions / risks

- Concurrent runs against the same source would interleave their frames on the shared channel. Acceptable for the scaffold; per-task routing is a follow-up.
- WS endpoint depends on Redis. Frontend hook degrades to null when the WS handshake fails; the polled `status_counts` keep the card useful.

## Acceptance criteria

- "Pipeline complete" only when every in-scope row reaches `preprocessed`.
- "Extracting PDFs · 154/156" shown while extract_gazette is still processing.
- WS connects (when wired) and surfaces "Running OCR (Tesseract) — 2486/29" as a pill at the bottom of the card.
- Page works fully without WS (degradation path).

## Linked trackers

- [CHANGES.md](../CHANGES.md)
- [FEATURES.md](../FEATURES.md) — F-173
- [SESSIONS.md](../SESSIONS.md) — Session 46
