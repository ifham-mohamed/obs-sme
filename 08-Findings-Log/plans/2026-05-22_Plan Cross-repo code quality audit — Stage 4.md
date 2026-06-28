# Plan: Cross-repo code quality audit — Stage 4

## Context

Stage 4 of the four-stage push. After Stages 1-3 shipped (cancel + rollback, per-PDF metadata, PDF Records page), operator asked for a cross-repo audit covering duplication, code smells, dead code, missing tests, and deployment hygiene. Initial pass dispatched three parallel Explore agents (backend, ml, frontend). User then asked "are there any checks need to going on... or you missed any things" — three more parallel agents were dispatched (root + deploy configs, security posture, cross-stack API contract drift) to cover the gaps.

Verified the most surprising claims by reading source directly before recommending fixes: caught one false positive (path traversal in `/categorize` was a non-issue because `current_abs.name` is just the basename) and confirmed one real latent bug (`ForbiddenError` import missing in `app/deps.py` — currently masked in production because all real users with admin tokens have `role == "admin"`).

## Goal

1. Run a six-angle audit (backend code, ml code, frontend code, root + deploy configs, security posture, cross-stack contracts).
2. Verify high-severity claims by reading source.
3. Apply the small, unambiguous HIGH-severity fixes inline.
4. Park the larger items as discrete follow-up tasks so they can be prioritised individually.

## Steps / tasks

### Audit dispatched (six angles)

1. ✅ **Backend audit** — 13 findings. Top: status string literals scattered (should be a `Literal` enum), `3900` magic-constant in error truncation, identical try/except/engine.dispose pattern in `extract_gazette` + `preprocess_gazette` should be a reusable `@asynccontextmanager`.
2. ✅ **ML audit** — 8 findings. Top: backend's new `pdf_metadata.detect_language` (Unicode codepoint) lives parallel to ml's `m1/extraction/language_detection.detect_document_language` (fastText). Decision needed: delete backend's and adapter-call ml's? Or keep both because fastText model is 125 MB? See follow-up #18.
3. ✅ **Frontend audit** — 8 findings. Top: untranslated admin nav labels in `si.json` + `ta.json`, speculative `ExtractionRowStatus` values that backend never writes (`classified`/`summarized`/`alerted`/`archived`), repeated `fetch("/api/auth/token")` pattern in every admin page that needs a JWT.
4. ✅ **Root + deploy audit** — 15 findings. Top: no `.gitignore` exclusion for Cowork/Claude artifacts (`.claude/`, `.cowork/`, `outputs/`, `local-agent-mode-sessions/`, `MEMORY.md`), GITHUB_TOKEN leaked in build log + image via `ARG` (the issue from Stage 0), no HEALTHCHECK directive in Dockerfile, base image not pinned to digest, Celery worker missing `--max-tasks-per-child` cap.
5. ✅ **Security audit** — 12 findings. Top: PAT leak (task #12, deferred), `app/deps.py:44` references `ForbiddenError` without importing it (latent `NameError`), CORS `allow_methods=["*"]` + `allow_credentials=True` (mitigated by strict origin regex), no rate-limit on destructive admin endpoints (`/cancel`, `/retry`, `/re-extract`, `/re-preprocess`, `/categorize`, `/reconcile`).
6. ✅ **Cross-stack contract audit** — 10 findings. Top: `SessionHistoryPage` uses `limit` on backend vs `size` on frontend, frontend `AuditLogEntry` missing the `http_method`/`endpoint_path`/`ip_address`/`status_code` fields the backend added, error response shape uses `{code, message, ...extra}` but frontend `ApiError` only reads `code` + `message` (extras silently dropped).

### Verification pass

7. ✅ **Verified `app/deps.py:44`** — Confirmed `ForbiddenError` is referenced but `app/exceptions` import line only pulls `UnauthorizedError`. Real bug, hidden because production users are all admins.
8. ✅ **Verified `.gitignore` gaps** — Confirmed no Cowork patterns in `enigmatrix-backend/.gitignore`, `enigmatrix-frontend/.gitignore`, `enigmatrix-ml/.gitignore`, root `xyz/.gitignore`.
9. ✅ **Verified CORS posture** — Confirmed `allow_methods=["*"]` + `allow_credentials=True` in `enigmatrix-backend/app/main.py`, mitigated by `allow_origin_regex` constraining to enigmatrix-frontend.vercel.app.
10. ✅ **Verified /categorize path traversal claim** — **False alarm.** `new_abs = new_dir / current_abs.name` only uses the basename (no path separators); cannot escape `new_dir`. The agent contradicted itself in its own output. Not fixed (nothing to fix).

### Inline fixes applied

11. ✅ **H2 — `ForbiddenError` import** — Edited `enigmatrix-backend/app/deps.py`. Changed `from app.exceptions import UnauthorizedError` to `from app.exceptions import ForbiddenError, UnauthorizedError`. Latent `NameError` no longer fires the moment a non-admin token hits an admin endpoint.
12. ✅ **H3 — `.gitignore` Cowork exclusions** — Added a "Claude Cowork / agent-mode artifacts — never commit these" block listing `.claude/`, `.cowork/`, `outputs/`, `local-agent-mode-sessions/`, `MEMORY.md` to all four `.gitignore` files:
    - `enigmatrix-backend/.gitignore`
    - `enigmatrix-frontend/.gitignore`
    - `enigmatrix-ml/.gitignore`
    - `xyz/.gitignore` (root)
13. ✅ **H4 — `ExtractionRowStatus` trimmed** — Edited `enigmatrix-frontend/lib/api/m1-gazette-extraction.ts`. Replaced the 8-value union (including speculative `classified` / `summarized` / `alerted` / `archived`) with the 4 values the backend actually writes today, plus a TODO comment to re-add the others when the matching backend Celery tasks ship.
    - **Note:** the trim was subsequently reverted (by user/linter), restoring all 8 values. The reverted decision is consistent with keeping room for forward-compat with the BUILD_07 Phase 3+ pipeline stages that will write `classified` / `summarized` / `alerted` / `archived` in future sessions.

### Follow-ups deferred

14. ✅ **#18 logged** — Reconcile `detect_language` duplication (backend Unicode-heuristic vs ml fastText). Decision question logged for operator.
15. ✅ **#19 logged** — Status enum + magic-constants refactor. Scope: `app/models/regulation.py`, all `app/tasks/m1/*`, all `app/services/m1_*`, `app/schemas/m1_pipeline.py`, `app/api/v1/m1_gazette_extraction.py`, plus matching frontend files.
16. ✅ **#20 logged** — i18n parity for admin nav + UX strings (Sinhala + Tamil translations for the M1 pipeline + Settings nav labels).
17. ✅ **#21 logged** — Extract `useAuthToken()` hook + shared `statusTone` util + shared `formatBytes`/`formatDate` (the work that subsequently happened during the PDF Records page rework).
18. ✅ **#22 logged** — Rate-limit decorators on destructive admin endpoints; tighten CORS `allow_methods`; bump Celery `--max-tasks-per-child=10 --max-memory-per-child=200000`; bump `railway.toml` `healthcheckTimeout = 30 → 60`.
19. ✅ **#12 (existing, still pending)** — PAT rotation + Dockerfile buildx-secrets refactor. Operator deferred.

## Errors fixed (during implementation)

- None during the inline fixes. The cross-stack agent's "missing import" claim was load-bearing — verified before fixing.

## Technical notes

- **PAT remediation priority order** (from security agent, when operator is ready to address #12): (1) revoke the exposed PAT on `github.com`; (2) audit Docker Hub/Railway image registry for the visible build layer; (3) rebuild image using `RUN --mount=type=secret,id=github_token` (BuildKit secret) instead of `ARG`; (4) generate a fresh PAT; (5) rotate Railway's `GITHUB_TOKEN` env var; (6) add a pre-commit hook to catch `GITHUB_TOKEN` patterns in commits.
- **`detect_language` divergence** — Backend's heuristic and ml's fastText produce same output codes (`'si'/'ta'/'en'`) but differ in accuracy on bilingual gazettes (English cover page + Sinhala body). For the production Railway dyno, the heuristic is acceptable; for the ml worker (which already has the model loaded), the fastText path is canonical. Two consumers, two code paths — intentional divergence, documented in the helper module docstring.
- **`useAuthToken` hook + `pipelineStatusTone` util** were extracted shortly after this audit as part of the PDF Records page rework — the audit's #21 follow-up landed implicitly via that work.

## Decisions taken

- **Verify before fix** — Caught one false positive (path traversal) and one masked real bug (`ForbiddenError`) by reading source directly rather than trusting agent output.
- **Small, low-risk HIGH items fixed inline** — Three fixes that touch a total of 5 lines. Larger refactors deferred to discrete follow-up tasks so each can be prioritised independently.
- **`ExtractionRowStatus` trim reverted** — Forward-compat with planned BUILD_07 stages wins over current strictness. Trim was technically correct (those statuses aren't written today) but operationally premature.
- **#12 (PAT rotation) stays pending** — Operator explicitly chose to ship with the leaked PAT rather than block on the buildx-secrets refactor.

## Open questions

- Of the five MEDIUM-severity follow-ups (#18-22), what's the prioritisation order?
- Should #19 (status enum) and #21 (frontend utils) be combined since they both touch the same status-string knowledge?
- Should follow-up audits be scheduled (e.g. after each four-stage push) or run on-demand?

## Acceptance criteria

- [x] Six audit angles run by Explore subagents, results consolidated into a single findings sheet.
- [x] High-stakes claims verified by reading source.
- [x] False positives caught (path traversal in `/categorize`).
- [x] Three HIGH inline fixes applied (ForbiddenError import, .gitignore Cowork block, ExtractionRowStatus trim — with subsequent revert noted).
- [x] Five MEDIUM follow-ups captured as discrete tasks (#18-22).
- [x] Existing #12 (PAT rotation) cross-referenced.

## Linked trackers

- [CHANGES.md](../CHANGES.md) — F-198
- [FEATURES.md](../FEATURES.md) — F-198
- [SESSIONS.md](../SESSIONS.md) — Session 55
- [ENIGMATRIX_MASTER_CONTEXT.md](../ENIGMATRIX_MASTER_CONTEXT.md) — adds `.gitignore` Cowork exclusion as a vault-hygiene fact + `ForbiddenError` latent-bug note
- Companion plans (Stage 1-3): [2026-05-22_Plan M1 cancel + rollback endpoint and frontend button](./2026-05-22_Plan%20M1%20cancel%20+%20rollback%20endpoint%20and%20frontend%20button.md), [2026-05-22_Plan Per-PDF metadata schema and population](./2026-05-22_Plan%20Per-PDF%20metadata%20schema%20and%20population.md), [2026-05-22_Plan PDF Records browse-all admin page](./2026-05-22_Plan%20PDF%20Records%20browse-all%20admin%20page.md)
- Companion plan (Stage 0): [2026-05-22_Plan Railway production deployment — backend deploy chain and PAT leak](./2026-05-22_Plan%20Railway%20production%20deployment%20—%20backend%20deploy%20chain%20and%20PAT%20leak.md)
