# Plan: Vault recovery from Write-tool truncation (incident response)

## Context

After a full-stack feature session, `npm run build` reported walls of TS17008 / TS1005 / TS1010 / TS1002 errors. Hex dumps of the affected files revealed widespread mid-content truncation:

- `components/providers.tsx` — 16 lines, ends mid-comment.
- `next.config.mjs` — 15 lines, ends `swcMinify: t` (cut mid-property-name).
- `app/(app)/dashboard/page.tsx` — 359 lines, ends mid-string-literal.
- `app/(auth)/login/page.tsx` — 192 lines, ends mid-className.
- `components/layout/sidebar.tsx` — 899 lines (expected ~960), ends `email: str`.
- `components/layout/theme-toggle.tsx` — 79 lines, ends `duration`.
- `components/m1-pipeline/funnel-chart.tsx` — 117 lines, ends with corrupt UTF-8.
- `components/m1-pipeline/pipeline-flow-diagram.tsx` — 138 lines.
- `app/(admin)/layout.tsx` — 27 lines.
- `app/(admin)/admin/m1/pipeline/page.tsx` — 289 lines, ends `icon: Icon,`.
- `app/(admin)/admin/m1/pipeline/sources/[sourceId]/extraction/page.tsx` — 631 lines.
- `app/globals.css` — 381 lines, ends mid-rule.
- `app/api/auth/establish/route.ts` — 22 lines.

The Write / Edit tools all returned "file created successfully" but the actual disk content was incomplete. Backend file `extract_gazette.py` additionally had 755 trailing NUL bytes (Python's parser rejects null bytes outright). The pattern correlates strongly with long writes containing em-dashes, special quotes, or emoji characters.

## Goal

Restore the corrupted files to a clean baseline; establish a new write protocol resilient to whatever is causing the truncation on this Windows-mounted FS.

## Scope

- **In:** Per-file restoration via `git restore` (frontend) and python-atomic-write of clean content (backend). New write protocol: python-atomic-write for files >~25KB; verify-after-write protocol.
- **Out:** Root-cause fix of the Write/Edit tools themselves (out of session scope).

## Steps

1. Inventory affected files via `wc -l` + `tail -3` + `tail -c 100 | xxd` — confirm truncation point and final bytes.
2. Run `git status --short` to confirm modified-but-not-committed state.
3. Emit the exact PowerShell `git restore` command covering all 13 frontend files:
   ```powershell
   cd C:\Reasearch\xyz\enigmatrix-frontend
   git restore components/providers.tsx `
               components/layout/sidebar.tsx `
               components/layout/theme-toggle.tsx `
               components/m1-pipeline/funnel-chart.tsx `
               components/m1-pipeline/pipeline-flow-diagram.tsx `
               "app/(admin)/layout.tsx" `
               "app/(app)/dashboard/page.tsx" `
               "app/(auth)/login/page.tsx" `
               app/api/auth/establish/route.ts `
               "app/(admin)/admin/m1/pipeline/page.tsx" `
               "app/(admin)/admin/m1/pipeline/sources/[sourceId]/extraction/page.tsx" `
               app/globals.css `
               next.config.mjs
   ```
4. Backend `extract_gazette.py`:
   - Remove the misplaced `_emit(...)` block at lines 200-211 — my prior edit placed it at 4-space indent (outside `async with`), which left the next `if not download_url` block at 8-space dangling and produced an `IndentationError` at line 212.
   - Strip 755 trailing NUL bytes via `data.rstrip(b'\x00').rstrip()`; ensure file ends with one newline.
   - Verify via `python3 -c "import ast; ast.parse(open('app/tasks/m1/extract_gazette.py').read())"`.
5. Sweep sibling backend / ML files (`m1_extraction_live_feed.py`, `m1_extraction_ws.py`, `router.py`, ML `progress.py`, ML `__init__.py`) for NUL bytes — all confirmed 0.
6. Adopt the new write protocol going forward:
   ```python
   tmp = path + ".tmp"
   with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
       fh.write(out)
   os.replace(tmp, path)
   ```
   Always followed by `wc -l`, `tail -3`, `python3 -c "print(open(path,'rb').read().count(b'\x00'))"`. For Python sources, additionally run `ast.parse`.

## Decisions taken

- Recommend `git restore` over my own re-writes because the same write path corrupted them once and could again. Bash-driven `git show HEAD:<path> > <path>` is the fallback for cases where `git restore` is blocked (e.g. stale `.git/index.lock` from a crashed `git status`).
- All subsequent vault and code edits in this session use python-atomic-write. The Edit tool itself is treated as unreliable for files >~25KB.

## Open questions / risks

- Root cause unknown. The Edit tool reported success on every truncating call. Future writes could truncate again on any large file with non-ASCII content.

## Acceptance criteria

- All 13 frontend files plus `extract_gazette.py` parse cleanly.
- `git status` clean (or only intentional changes) after recovery.
- `npm run build` completes without parse errors.
- Subsequent vault edits in this session use python-atomic-write and verify successfully.

## Linked trackers

- [CHANGES.md](../CHANGES.md)
- [FEATURES.md](../FEATURES.md) — F-178 (incident response, not a delivered feature)
- [SESSIONS.md](../SESSIONS.md) — Session 48
- [SETUP_COVERAGE.md](../SETUP_COVERAGE.md) — Edit-tool truncation policy entry
